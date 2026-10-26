#!/usr/bin/env python3
"""Verify BIRD inputs, call the real MCP, score complete PostgreSQL results, and publish to Opik."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import tempfile
import zipfile
import time
import asyncio
import subprocess
import os
from collections import Counter
from datetime import date, time as time_value, datetime
from decimal import Decimal
from urllib.parse import urlsplit
from pathlib import Path


class InvalidBaseline(ValueError):
    """The measurement prerequisites cannot be established."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidBaseline(message)


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_file(path: Path, expected: str) -> None:
    require(path.is_file(), f'Missing input: {path}')
    require(sha256(path) == expected, f'SHA-256 mismatch: {path.name}')


def write_json(path: Path, value: object) -> None:
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, default=encode_value, allow_nan=False)
        stream.write('\n')


def encode_value(value):
    if isinstance(value, (Decimal, date, datetime, time_value)):
        return {'type': type(value).__name__, 'value': str(value)}
    raise TypeError(f'Unsupported result type: {type(value).__name__}')


def safe_query(sql: str) -> None:
    from sqlglot import exp, parse
    from sqlglot.errors import ParseError

    try:
        expressions = parse(sql, read='postgres')
    except ParseError as exc:
        raise InvalidBaseline('SQL cannot be parsed') from exc
    require(len(expressions) == 1 and isinstance(expressions[0], exp.Query), 'Exactly one read-only query is required')
    require(not any(isinstance(node, (exp.DML, exp.DDL, exp.Into, exp.Lock, exp.Command))
                    for node in expressions[0].walk()), 'Unsafe SQL structure')


def bird_ex(predicted: list[tuple], gold: list[tuple]) -> int:
    return int(set(predicted) == set(gold))


def score_case(conn, predicted_sql: str | None, gold_sql: str, timeout_ms: int) -> dict:
    import psycopg

    started = time.perf_counter()
    require(timeout_ms > 0, 'Statement timeout must be positive')
    safe_query(gold_sql)
    with conn.transaction():
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        conn.execute("SELECT set_config('statement_timeout', %s, true)", (str(timeout_ms),))
        try:
            gold = conn.execute(gold_sql).fetchall()
        except psycopg.Error as exc:
            raise InvalidBaseline(f'Gold execution failed: {exc.sqlstate}') from exc
        if not predicted_sql:
            return {'ex': 0, 'error': 'missing_sql', 'gold_rows': gold, 'predicted_rows': None,
                    'scorer_ms': (time.perf_counter() - started) * 1000}
        try:
            safe_query(predicted_sql)
        except (InvalidBaseline, ValueError) as exc:
            return {'ex': 0, 'error': 'unsafe_sql', 'diagnostic': str(exc), 'gold_rows': gold,
                    'predicted_rows': None, 'scorer_ms': (time.perf_counter() - started) * 1000}
        try:
            with conn.transaction():
                predicted = conn.execute(predicted_sql).fetchall()
        except psycopg.OperationalError as exc:
            if isinstance(exc, psycopg.errors.QueryCanceled):
                error = 'sql_timeout'
                diagnostic = exc.sqlstate
            else:
                raise InvalidBaseline(f'Scoring database unavailable: {exc.sqlstate}') from exc
        except psycopg.Error as exc:
            error = 'sql_error'
            diagnostic = exc.sqlstate
        else:
            return {'ex': bird_ex(predicted, gold), 'error': None, 'gold_rows': gold,
                    'predicted_rows': predicted, 'scorer_ms': (time.perf_counter() - started) * 1000}
        return {'ex': 0, 'error': error, 'diagnostic': diagnostic,
                'gold_rows': gold, 'predicted_rows': None, 'scorer_ms': (time.perf_counter() - started) * 1000}


def verify_query_data(conn, manifest: dict, pack: Path) -> list[dict]:
    from psycopg import sql

    convert = {'BIGINT': int, 'NUMERIC': Decimal, 'TEXT': str, 'DATE': date.fromisoformat, 'TIME': time_value.fromisoformat}
    report = []
    with conn.transaction():
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        for table in manifest['tables']:
            path = pack / table['csv_file']
            verify_file(path, table['sha256'])
            with path.open(newline='') as stream:
                reader = csv.reader(stream, quoting=csv.QUOTE_NOTNULL)
                header = next(reader)
                require(header == [c['csv_name'] for c in table['columns']], 'CSV header differs')
                expected = Counter(tuple(None if value is None else convert[col['postgres_type']](value)
                                         for value, col in zip(row, table['columns'], strict=True)) for row in reader)
            actual_types = conn.execute('SELECT column_name, data_type FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s ORDER BY ordinal_position', (table['csv_table'],)).fetchall()
            pg_types = {'BIGINT': 'bigint', 'NUMERIC': 'numeric', 'TEXT': 'text', 'DATE': 'date', 'TIME': 'time without time zone'}
            require(actual_types == [(c['csv_name'], pg_types[c['postgres_type']]) for c in table['columns']], f"Target columns/types differ: {table['csv_table']}")
            statement = sql.SQL('SELECT {} FROM {}').format(sql.SQL(',').join(sql.Identifier(c['csv_name']) for c in table['columns']), sql.Identifier(table['csv_table']))
            actual = Counter(conn.execute(statement).fetchall())
            require(actual == expected and actual.total() == table['row_count'], f"Target values differ: {table['csv_table']}")
            digest = hashlib.sha256(repr(sorted(expected.items())).encode()).hexdigest()
            report.append({'table': table['csv_table'], 'rows': actual.total(), 'typed_content_sha256': digest})
    return report


def question_input(case: dict) -> str:
    require(isinstance(case['question'], str) and isinstance(case['evidence'], str), 'Question/evidence must be strings')
    return 'Question:\n' + case['question'] + '\n\nEvidence:\n' + case['evidence']


def select_tool(server_name: str, tools: list[dict], project: str) -> dict:
    require(server_name == f'NL2SQL MCP Server - {project}', 'MCP project identity differs')
    candidates = [tool for tool in tools if tool['inputSchema'].get('required') == ['query']
                  and tool['inputSchema']['properties'].get('query', {}).get('type') == 'string'
                  and tool['inputSchema']['properties'].get('fastMode', {}).get('type') == 'boolean']
    require(len(candidates) == 1, 'Exactly one advertised modern Ask tool is required')
    return candidates[0]


async def ask_once(url: str, project: str, case: dict, timeout_seconds: float,
                   output_dir: Path, expected_tool: dict | None = None) -> dict:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    import httpx2

    started = time.perf_counter()
    async with httpx2.AsyncClient(timeout=httpx2.Timeout(timeout_seconds), trust_env=False) as transport:
        async with streamable_http_client(url, http_client=transport) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timeout_seconds) as session:
                initialize = await session.initialize()
                advertised = await session.list_tools()
                tool = select_tool(initialize.server_info.name,
                                   [t.model_dump(mode='json', by_alias=True, exclude_none=True) for t in advertised.tools], project)
                require(expected_tool is None or tool == expected_tool, 'Advertised MCP tool drifted')
                request = {'query': question_input(case)}
                write_json(output_dir / 'request.json', {'tool': tool, 'arguments': request})
                raw = await session.call_tool(tool['name'], request, read_timeout_seconds=timeout_seconds)
                ask_ms = (time.perf_counter() - started) * 1000
                write_json(output_dir / 'mcp-response.json', raw.model_dump(mode='json', by_alias=True))
                payload = raw.structured_content
                require(isinstance(payload, dict), 'Modern MCP structured result is missing')
                if isinstance(payload.get('resources'), dict) and payload['resources'].get('traceEvents'):
                    resource = await session.read_resource(payload['resources']['traceEvents'])
                    require(len(resource.contents) == 1 and hasattr(resource.contents[0], 'text'), 'Canonical trace resource is unreadable')
                    events = json.loads(resource.contents[0].text)
                    write_json(output_dir / 'trace-events.json', events)
                else:
                    events = None
                return {'payload': payload, 'events': events, 'ask_ms': ask_ms, 'tool': tool}


def read_json_api(client, path: str, project: str, **params) -> dict:
    response = client.get(path, params={'projectId': project, **params})
    response.raise_for_status()
    return response.json()


def frozen_runtime(client, project: str) -> dict:
    active = read_json_api(client, '/api/config/active', project)
    rows = active.pop('envConfig')
    allowed_suffixes = ('_MODEL', '_PROVIDER', '_TEMPERATURE', '_TIMEOUT_MS', '_DIMENSIONS', '_EMBEDDING_BATCH_SIZE', '_BASE_URL')
    model_config = {row['key']: row['active'] for row in rows
                    if (row['key'].startswith('LLM_') or row['key'].startswith('PROJECT_' + project.upper() + '_LLM_'))
                    and (row['key'].endswith(allowed_suffixes) or row['key'].endswith('_PROFILE'))}
    for key, value in model_config.items():
        if key.endswith('_BASE_URL') and value:
            require(not urlsplit(value).username and not urlsplit(value).query, 'Model endpoint contains credentials/query parameters')
    model_config['provider_option_sha256'] = {row['key']: hashlib.sha256(str(row['active']).encode()).hexdigest()
                                             for row in rows if '_PROVIDER_OPTION_' in row['key']}
    require(any(key.endswith('_MODEL') for key in model_config), 'Runtime model identity is missing')
    return {key: active[key] for key in ('projectId', 'artifactVersionId', 'bundleHash', 'runtimeIdentity', 'schemaRag', 'runtimePolicies')} | {'model_config': model_config}


def collect_knowledge_audit(client, project: str, query_id: str) -> list[dict]:
    listing = read_json_api(client, '/api/metadata/api-history', project, queryId=query_id, pageSize=100)
    require(listing['pagination']['total'] <= 100, 'API audit history is truncated')
    records = []
    for item in listing['data']:
        if item['api_path'].endswith('/sql-knowledge'):
            record = read_json_api(client, f"/api/metadata/api-history/{item['id']}", project)['data']
            records.append({key: record[key] for key in ('id', 'query_id', 'thread_key', 'trace_id', 'status_code', 'response_json')})
    return records


def validate_no_knowledge(snapshot: dict, frozen: dict, execution: dict, audits: list[dict], query: str) -> dict:
    payload, resource = execution['payload'], execution['events']
    require(snapshot['sqlPairs'] == [], 'Snapshot SQL Pair collection is not empty')
    for key in ('artifactVersionId', 'bundleHash', 'runtimeIdentity'):
        require(payload.get(key) == frozen[key], f'Actual Ask binding differs: {key}')
    require(all(isinstance(payload.get(key), str) and payload[key] for key in ('queryId', 'threadId', 'traceId')), 'Actual run identity is missing')
    require(isinstance(resource, dict) and resource.get('traceId') == payload['traceId'], 'Canonical trace correlation is missing')
    events = resource['events']
    require(bool(events), 'Canonical events are missing')
    require([event['seq'] for event in events] == list(range(1, len(events) + 1))
            and events[-1]['type'] == 'qa.trace.completed', 'Canonical event sequence is incomplete')
    for event in events:
        require(event.get('queryId') == payload['queryId'] and event.get('traceId') == payload['traceId'], 'Canonical event belongs to another execution')
        require(event.get('redacted') is not True and event.get('truncated') is not True, 'Canonical proof is redacted/truncated')
    starts = [event for event in events if event['type'] == 'qa.step.started']
    require(all(event.get('provenance') in ('live', 'persisted') for event in starts), 'Canonical input proof is reconstructed or unknown')
    phases = ('reasoning', 'generating', 'reason_and_generate', 'correcting')
    expected_nodes = {step['id'] for step in payload['steps'] if step['phase'] in phases}
    actual_nodes = {event['nodeId'] for event in starts if event['phase'] in phases}
    require(actual_nodes == expected_nodes, 'Canonical model-phase input events are missing')
    if (payload.get('queryResult') or {}).get('sql'):
        require(any(event['phase'] in ('generating', 'reason_and_generate') for event in starts), 'SQL has no generation input proof')
    first = next((e for e in starts if e['phase'] == 'understanding'), None)
    require(first is not None, 'Understanding input proof is missing')
    first_input = first['payload']['input']['artifacts']
    require(first_input.get('query') == query and first_input.get('histories') == [], 'Actual input differs or conversation is reused')
    calls = []
    for event in starts:
        phase = event['phase']
        if phase not in ('reasoning', 'generating', 'reason_and_generate', 'correcting'):
            continue
        artifacts = event['payload'].get('input', {}).get('artifacts', {})
        field = 'sqlKnowledge' if phase == 'correcting' else 'sql_samples_prompt'
        require(field in artifacts and isinstance(artifacts[field], str), f'Missing actual knowledge input: {phase}')
        require(artifacts[field] == '', f'Nonempty actual knowledge input: {phase}')
        no_call = any(e.get('nodeId') == event['nodeId'] and
                      e['payload'].get('output', {}).get('artifacts', {}).get('correction', {}).get('llmInvoked') is False for e in events)
        calls.append({'phase': phase, 'node_id': event['nodeId'], 'phase_occurrence': int(event['nodeId'].rsplit(':', 1)[1]),
                      'correction_attempt': artifacts.get('attempt'), 'sql_knowledge_chars': len(artifacts[field]),
                      'invocation': 'not_executed' if no_call else 'phase_entered'})
    searched = any(event['phase'] == 'searching' for event in starts)
    if searched and payload.get('type') != 'MISLEADING_QUERY':
        require(len(audits) == 1, 'Actual provider response proof is missing or duplicated')
    for audit in audits:
        require(audit['query_id'] == payload['queryId'] and audit['thread_key'] == payload['threadId']
                and audit['trace_id'] == payload['traceId'], 'Knowledge provider audit belongs to another execution')
        response = audit['response_json']
        require(audit['status_code'] == 200 and response.get('statusCode') == 200, 'Knowledge provider failed')
        require(response.get('sqlKnowledge') == '' and response.get('sqlKnowledgeChars') == 0, 'Provider knowledge is nonempty or unknown')
        rag = response.get('rag', {})
        require(rag.get('selectedCount') == 0 and rag.get('selectedIds') == [] and rag.get('selectedPairs') == [], 'Actual provider selection is not affirmatively empty')
    return {'provider': 'verified_empty' if audits else 'not_executed', 'calls': calls,
            'phases': {phase: 'input_verified' if any(c['phase'] == phase and c['invocation'] != 'not_executed' for c in calls) else 'not_executed'
                       for phase in ('reasoning', 'generating', 'reason_and_generate', 'correcting')}}


def summarize(cases: list[dict], outcomes: list[dict], status: str) -> dict:
    planned = [case['question_id'] for case in cases]
    actual = [record['question_id'] for record in outcomes]
    require(len(actual) == len(set(actual)) and set(actual) <= set(planned), 'Outcome case IDs differ')
    complete = status == 'complete' and actual == planned and all(record.get('ex') in (0, 1) for record in outcomes)
    require(status != 'complete' or complete, 'Cannot complete a partial/unscored run')
    return {'status': status, 'planned': len(planned), 'attempted': len(actual),
            'scored': sum(record.get('ex') in (0, 1) for record in outcomes),
            'remaining_ids': [qid for qid in planned if qid not in actual],
            'correct': sum(record['ex'] for record in outcomes if record.get('ex') in (0, 1)),
            'accuracy': sum(record['ex'] for record in outcomes) / len(planned) if complete else None,
            'unscored_ids': [record['question_id'] for record in outcomes if record.get('ex') not in (0, 1)],
            'errors': sum(bool(record.get('error')) for record in outcomes if record.get('ex') in (0, 1)),
            'timeouts': sum('timeout' in str(record.get('error')) for record in outcomes if record.get('ex') in (0, 1))}


def dataset_items(manifest: dict) -> list[dict]:
    return [{'case_id': case['db_id'] + ':' + case['question_id'],
             **{key: case[key] for key in ('question_id', 'db_id', 'question', 'evidence', 'difficulty')},
             'gold_sql': case['gold_sql_postgresql_poc'], 'source_gold_sql': case['gold_sql_postgresql_source']}
            for case in manifest['cases']]


def open_opik(lock: dict, manifest: dict):
    import opik

    os.environ.update(OPIK_URL_OVERRIDE=lock['host'], OPIK_WORKSPACE=lock['workspace'], OPIK_PROJECT_NAME=lock['project_name'])
    client = opik.Opik(host=lock['host'], workspace=lock['workspace'], project_name=lock['project_name'])
    dataset = client.get_dataset(lock['dataset_name'], project_name=lock['project_name'])
    require(dataset.id == lock['dataset_id'], 'Opik dataset identity differs')
    version = dataset.get_version_view(lock['version']['version_name'])
    require(version.get_version_info().id == lock['version']['id'], 'Opik dataset version differs')
    items = version.get_items()
    expected = {item['case_id']: item for item in dataset_items(manifest)}
    require(len(items) == len(expected), 'Opik dataset item count differs')
    for item in items:
        require(item.get('case_id') in expected, 'Unknown Opik dataset case')
        require(all(item.get(key) == value for key, value in expected[item['case_id']].items()), 'Opik dataset content differs')
    require(len({item['case_id'] for item in items}) == len(items), 'Duplicate Opik case IDs')
    return client, version, items


def publish_opik(client, version, items: list[dict], lock: dict, outcomes: list[dict], name: str, config: dict, output_dir: Path) -> dict:
    import opik
    from opik.evaluation import evaluate
    from opik.evaluation.metrics import BaseMetric
    from opik.evaluation.metrics.score_result import ScoreResult

    class ExecutionMetrics(BaseMetric):
        def score(self, ex: int, error: str | None, ask_ms: float, scorer_ms: float, **ignored):
            return [ScoreResult(name='EX', value=ex, reason=error or 'Complete PostgreSQL row-set comparison'),
                    ScoreResult(name='error', value=int(bool(error)), reason=error),
                    ScoreResult(name='timeout', value=int('timeout' in str(error))),
                    ScoreResult(name='ask_ms', value=round(ask_ms, 6)), ScoreResult(name='scorer_ms', value=round(scorer_ms, 6))]

    outputs = {record['case_id']: record for record in outcomes}
    selected = [item['id'] for item in items if item['case_id'] in outputs]
    require(len(selected) == len(outputs), 'Experiment inputs do not match scored case IDs')
    result = evaluate(dataset=version, task=lambda item: outputs[item['case_id']],
                      scoring_metrics=[ExecutionMetrics(track=False)], project_name=lock['project_name'],
                      experiment_name=name, experiment_config=config, dataset_item_ids=selected,
                      task_threads=1, trial_count=1, verbose=0)
    write_json(output_dir / 'opik-experiment-created.json', {'experiment_id': result.experiment_id, 'experiment_url': result.experiment_url})
    require(len(result.test_results) == len(outcomes), 'Opik evaluation omitted items')
    require(all(not score.scoring_failed for test in result.test_results for score in test.score_results), 'Opik metric publication failed')
    opik.flush_tracker()
    client.flush()
    experiment = client.rest_client.experiments.get_experiment_by_id(result.experiment_id)
    raw_items = b''.join(client.rest_client.experiments.stream_experiment_items(
        experiment_name=name, project_name=lock['project_name'], limit=len(outcomes) + 1, truncate=False))
    persisted = [json.loads(line) for line in raw_items.splitlines() if line.strip()]
    publication = {'experiment_id': result.experiment_id, 'experiment_url': result.experiment_url,
                   'experiment': experiment.model_dump(mode='json'), 'items': persisted}
    write_json(output_dir / 'opik-readback.json', publication)
    verify_publication(publication, lock, outcomes)
    return publication


def verify_publication(publication: dict, lock: dict, outcomes: list[dict]) -> None:
    experiment, items = publication['experiment'], publication['items']
    require(experiment['status'] == 'completed' and experiment['dataset_version_id'] == lock['version']['id'], 'Opik status/dataset version differs')
    require(experiment['project_name'] == lock['project_name'] and experiment['dataset_id'] == lock['dataset_id'], 'Opik destination differs')
    require(len(items) == len(outcomes), 'Opik experiment items are missing')
    expected = {record['case_id']: record for record in outcomes}
    require({item['output'].get('case_id') for item in items} == set(expected), 'Opik persisted case IDs differ')
    for item in items:
        record = expected[item['output']['case_id']]
        require(item['output'] == record, 'Opik persisted outcome/trace correlation differs')
        require(item['input']['case_id'] == record['case_id'], 'Opik dataset/output correlation differs')
        scores = {score['name']: score['value'] for score in item['feedback_scores']}
        values = {'EX': record['ex'], 'error': int(bool(record['error'])), 'timeout': int('timeout' in str(record['error'])),
                  'ask_ms': round(record['ask_ms'], 6), 'scorer_ms': round(record['scorer_ms'], 6)}
        require(all(key in scores and round(scores[key], 6) == value for key, value in values.items()), 'Opik persisted scores differ')


def classify_ask_failure(payload: dict) -> str | None:
    if payload['status'] == 'finished':
        return None
    error = payload.get('error') or {}
    require(not str(error.get('errorCode', '')).endswith('ASK_RUNTIME_DEPENDENCY_FAILED'), 'Ask runtime dependency failed')
    for step in payload.get('steps', []):
        validation = step.get('output', {}).get('artifacts', {}) or {}
        require(validation.get('validation', {}).get('errorType') != 'database_unavailable', 'Shared query database failed')
    for step in payload.get('steps', []):
        correction = (step.get('output', {}).get('artifacts', {}) or {}).get('correction', {})
        if correction.get('llmInvoked') is False and correction.get('error') and correction.get('attempt') == correction.get('maxRetries'):
            return 'correction_exhausted'
    require(error.get('phase') in ('understanding', 'reasoning', 'generating', 'reason_and_generate', 'correcting', 'sql_execution', 'validating'), 'Unknown/non-model Ask failure')
    return 'ask_timeout' if 'timeout' in str(error).lower() else 'ask_error'


def run(args: argparse.Namespace) -> int:
    import httpx
    import psycopg
    from dotenv import dotenv_values

    require(args.sql_timeout_ms > 0 and args.ask_timeout_seconds > 0, 'Timeouts must be positive')
    for address in (args.api_url, args.mcp_url):
        parsed = urlsplit(address)
        require(parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.query and not parsed.fragment, 'Endpoint must not contain credentials/query parameters')
    args.output_dir.mkdir(parents=True, exist_ok=False)
    cases, outcomes = [], []
    status, failure = 'invalid', None
    publishing = False
    directory, current_case = None, None
    try:
        manifest = json.loads((args.pack / 'input-manifest.json').read_text())
        source_lock = json.loads(args.source_lock.read_text())
        require(manifest['source_lock_sha256'] == sha256(args.source_lock), 'Prepared source lock differs')
        for key in ('tables', 'cases', 'sources', 'question_ids'):
            require(manifest[key] == source_lock[key], f'Prepared input differs: {key}')
        audit_gold(manifest, manifest['cases'])
        cases = manifest['cases'][:1] if args.smoke else manifest['cases']
        dataset_lock = json.loads(args.dataset_lock.read_text())
        parsed = urlsplit(dataset_lock['host'])
        require(parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.query, 'Invalid Opik endpoint')
        opik_client, version, items = open_opik(dataset_lock, manifest)
        dsn = dotenv_values(args.scorer_env)['BIRD_SCORER_DSN']
        with httpx.Client(base_url=args.api_url, trust_env=False, timeout=60) as client, psycopg.connect(dsn, autocommit=True) as conn:
            frozen = frozen_runtime(client, args.project)
            active_detail = read_json_api(client, '/api/artifact-versions/' + frozen['artifactVersionId'], args.project)
            snapshot = active_detail['bundle']
            require(snapshot['sqlPairs'] == [], 'Bound Snapshot is not an empty SQL Pair baseline')
            review = json.loads(args.prompt_review.read_text())
            hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in snapshot['prompts'].items()}
            require(review['bundle_hash'] == frozen['bundleHash'] and review['prompt_sha256'] == hashes and review['status'] == 'reviewed_no_cohort_answers', 'Prompt review does not match the actual Snapshot')
            health = client.post('/api/health', params={'mode': 'project', 'projectId': args.project})
            health.raise_for_status()
            require(health.json()['project']['qaAvailable'], 'Project is not QA ready')
            content = verify_query_data(conn, manifest, args.pack)
            gold_report = []
            for case in manifest['cases']:
                gold = score_case(conn, None, case['gold_sql_postgresql_poc'], args.sql_timeout_ms)
                gold_report.append({'question_id': case['question_id'], 'rows': gold['gold_rows'], 'status': 'verified'})
            write_json(args.output_dir / 'gold-preflight.json', gold_report)
            write_json(args.output_dir / 'run-manifest.json', {
                'scope': 'smoke' if args.smoke else 'baseline', 'project': args.project,
                'case_ids': [case['question_id'] for case in cases], 'evidence': 'on',
                'runtime': frozen, 'data': content, 'input_manifest_sha256': sha256(args.pack / 'input-manifest.json'),
                'source_lock_sha256': sha256(args.source_lock), 'dataset': dataset_lock,
                'prompt_review': review, 'sql_timeout_ms': args.sql_timeout_ms, 'ask_timeout_seconds': args.ask_timeout_seconds,
                'git_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'git_status': subprocess.check_output(['git', 'status', '--short'], text=True),
                'runner_sha256': sha256(Path(__file__)), 'api_url': args.api_url, 'mcp_url': args.mcp_url,
            })
            with (args.output_dir / 'runner-source.py').open('xb') as stream:
                stream.write(Path(__file__).read_bytes())
            used_threads, expected_tool = set(), None
            for case in cases:
                current_case = case
                directory = None
                require(frozen_runtime(client, args.project) == frozen, 'Runtime configuration drifted before Ask')
                directory = args.output_dir / case['question_id']
                directory.mkdir()
                execution = asyncio.run(ask_once(args.mcp_url, args.project, case, args.ask_timeout_seconds, directory, expected_tool))
                expected_tool = execution['tool']
                payload = execution['payload']
                audits = collect_knowledge_audit(client, args.project, payload.get('queryId', ''))
                write_json(directory / 'knowledge-audit.json', audits)
                proof = validate_no_knowledge(snapshot, frozen, execution, audits, question_input(case))
                write_json(directory / 'knowledge-proof.json', proof)
                require(payload['threadId'] not in used_threads, 'A benchmark conversation was reused')
                used_threads.add(payload['threadId'])
                require(frozen_runtime(client, args.project) == frozen, 'Runtime configuration drifted during Ask')
                ask_error = classify_ask_failure(payload)
                query_result = payload.get('queryResult') or {}
                prediction = query_result.get('sql')
                score = score_case(conn, prediction if ask_error is None else None, case['gold_sql_postgresql_poc'], args.sql_timeout_ms)
                write_json(directory / 'score.json', score)
                record = {'case_id': case['db_id'] + ':' + case['question_id'], 'question_id': case['question_id'],
                          'ex': 0 if ask_error else score['ex'], 'error': ask_error or score['error'],
                          'ask_ms': execution['ask_ms'], 'scorer_ms': score['scorer_ms'], 'sql': prediction,
                          **{key: payload[key] for key in ('queryId', 'threadId', 'traceId', 'artifactVersionId', 'bundleHash')},
                          'evidence_dir': str(directory.resolve()), 'difficulty': case['difficulty']}
                write_json(directory / 'outcome.json', record)
                outcomes.append(record)
                print(f"{case['question_id']}: EX={record['ex']} error={record['error']} ask_ms={record['ask_ms']:.0f}", flush=True)
            require(verify_query_data(conn, manifest, args.pack) == content, 'Query data drifted during the experiment')
            require(frozen_runtime(client, args.project) == frozen, 'Runtime configuration drifted after Ask')
        publishing = True
        publication = publish_opik(opik_client, version, items, dataset_lock, outcomes, args.output_dir.name,
                                   {'scope': 'smoke' if args.smoke else 'baseline', 'runtime': frozen,
                                    'source_revision': manifest['sources']['qa']['revision'], 'source_lock_sha256': sha256(args.source_lock)}, args.output_dir)
        write_json(args.output_dir / 'opik-publication.json', publication)
        status = 'complete'
    except KeyboardInterrupt:
        status, failure = 'interrupted', 'KeyboardInterrupt'
    except Exception as exc:
        status, failure = ('publication_incomplete' if publishing else 'invalid'), f'{type(exc).__name__}: {exc}'
    if directory is not None and (directory / 'request.json').exists() and not (directory / 'outcome.json').exists():
        raw_path = directory / 'mcp-response.json'
        raw_payload = json.loads(raw_path.read_text()).get('structuredContent') if raw_path.exists() else None
        identities = {key: (raw_payload or {}).get(key) for key in ('queryId', 'threadId', 'traceId')}
        failed = {'case_id': current_case['db_id'] + ':' + current_case['question_id'], 'question_id': current_case['question_id'],
                  'error': 'measurement_invalid', 'diagnostic': failure, **identities}
        write_json(directory / 'unscored-failure.json', failed)
        outcomes.append(failed)
    summary = summarize(cases, outcomes, status)
    summary['failure'] = failure
    summary['scope'] = 'smoke' if args.smoke else 'baseline'
    write_json(args.output_dir / 'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if status == 'complete' else 1


def load_cohort(pack: Path, official_qa: Path, revision: str) -> tuple[dict, list[dict]]:
    require(re.fullmatch(r'[a-f0-9]{40}', revision) is not None, 'QA revision must be an immutable commit SHA')
    manifest = json.loads((pack / 'manifest.json').read_text())
    with (pack / 'qa.csv').open(newline='') as stream:
        cases = list(csv.DictReader(stream))
    require(len(cases) == manifest['question_count'], 'Question count differs from the manifest')
    ids = [case['question_id'] for case in cases]
    require(len(ids) == len(set(ids)), 'Duplicate benchmark question IDs')
    official = json.loads(official_qa.read_text())
    source_cases = [case for case in official if case['db_id'] == manifest['db_id']]
    require({str(case['question_id']) for case in source_cases} == set(ids), 'Official cohort differs from local case IDs')
    source_by_id = {str(case['question_id']): case for case in source_cases}
    for case in cases:
        source = source_by_id[case['question_id']]
        for field, source_field in [('question', 'question'), ('evidence', 'evidence'), ('gold_sql_postgresql_source', 'SQL')]:
            require(case[field] == source[source_field], f"Source mismatch: case {case['question_id']} field {field}")
        require(case['db_id'] == manifest['db_id'], 'A case belongs to another database')
    return manifest, cases


def audit_gold(manifest: dict, cases: list[dict]) -> list[dict]:
    from sqlglot import exp, parse_one

    mapping = {}
    for table in manifest['tables']:
        for column in table['columns']:
            source, target = column['source_name'].lower(), column['csv_name']
            require(source not in mapping or mapping[source] == target, f'Ambiguous column mapping: {source}')
            mapping[source] = target
    audit = []
    for case in cases:
        source = parse_one(case['gold_sql_postgresql_source'], read='postgres')
        for column in source.find_all(exp.Column):
            if column.name.lower() in mapping:
                column.set('this', exp.to_identifier(mapping[column.name.lower()]))
        adapted = parse_one(case['gold_sql_postgresql_poc'], read='postgres')
        require(source == adapted, f"Unapproved Gold expression rewrite: {case['question_id']}")
        audit.append({'question_id': case['question_id'], 'status': 'identifier_mapping_only',
                      'canonical_postgresql': adapted.sql(dialect='postgres')})
    return audit


def prepare(args: argparse.Namespace) -> None:
    manifest = json.loads(args.source_lock.read_text())
    sources = manifest['sources']
    verify_file(args.official_qa, sources['qa']['sha256'])
    verify_file(args.source_archive, sources['database']['archive_sha256'])
    args.output_dir.mkdir(exist_ok=False, parents=True)
    (args.output_dir / 'tables').mkdir()
    with tempfile.TemporaryDirectory() as temporary:
        source_db = Path(temporary) / 'source.sqlite'
        with zipfile.ZipFile(args.source_archive) as archive:
            source_db.write_bytes(archive.read(sources['database']['member']))
        verify_file(source_db, sources['database']['member_sha256'])
        with sqlite3.connect(f'file:{source_db}?mode=ro', uri=True) as conn:
            for table in manifest['tables']:
                quote = lambda value: '"' + value.replace('"', '""') + '"'
                source_types = {row[1]: row[2] for row in conn.execute('PRAGMA table_info(' + quote(table['source_table']) + ')')}
                require(source_types == {col['source_name']: col['source_type'] for col in table['columns']}, 'Source column types differ')
                query = 'SELECT ' + ','.join(quote(col['source_name']) for col in table['columns']) + ' FROM ' + quote(table['source_table'])
                with (args.output_dir / table['csv_file']).open('x', newline='', encoding='utf-8') as stream:
                    writer = csv.writer(stream, lineterminator='\n')
                    writer.writerow([col['csv_name'] for col in table['columns']])
                    for row in conn.execute(query):
                        require(all(value is not None and value != '' for value in row), 'Frozen cohort NULL/empty-string contract differs')
                        writer.writerow(row)
    write_json(args.output_dir / 'manifest.json', manifest)
    with (args.output_dir / 'qa.csv').open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest['cases'][0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(manifest['cases'])
    manifest, cases = load_cohort(args.output_dir, args.official_qa, sources['qa']['revision'])
    require([case['question_id'] for case in cases] == manifest['question_ids'], 'Frozen case order differs')
    gold_audit = audit_gold(manifest, cases)
    tables = []
    for table in manifest['tables']:
        path = args.output_dir / table['csv_file']
        verify_file(path, table['sha256'])
        require(path.stat().st_size == table['csv_bytes'], f'CSV size mismatch: {path.name}')
        with path.open(newline='') as stream:
            reader = csv.reader(stream)
            header = next(reader)
            require(header == [column['csv_name'] for column in table['columns']], f'CSV header mismatch: {path.name}')
            count = 0
            for row in reader:
                require(len(row) == len(header), f'CSV row width mismatch: {path.name}')
                count += 1
        require(count == table['row_count'], f'CSV row count mismatch: {path.name}')
        tables.append({**table, 'sha256': sha256(path)})
    require(sum(table['row_count'] for table in tables) == manifest['row_count'], 'Total source row count differs')
    write_json(args.output_dir / 'input-manifest.json', {
        **manifest, 'tables': tables, 'cases': cases,
        'source_lock_sha256': sha256(args.source_lock),
        'preparation_status': 'source_values_and_gold_ast_verified_target_execution_pending',
    })
    write_json(args.output_dir / 'gold-audit.json', gold_audit)
    print(f'Rebuilt {len(tables)} complete tables and {len(cases)} source-verified questions; target Gold execution remains required.')


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest='command', required=True)
    preparation = commands.add_parser('prepare', help='Rebuild and verify the frozen official inputs')
    preparation.add_argument('--source-lock', type=Path, required=True)
    preparation.add_argument('--source-archive', type=Path, required=True)
    preparation.add_argument('--official-qa', type=Path, required=True)
    preparation.add_argument('--output-dir', type=Path, required=True)
    preparation.set_defaults(handler=prepare)
    execution = commands.add_parser('run', help='Call the real MCP, independently score, then publish and verify Opik')
    for name in ('pack', 'source-lock', 'dataset-lock', 'prompt-review', 'scorer-env', 'output-dir'):
        execution.add_argument('--' + name, type=Path, required=True)
    for name in ('api-url', 'mcp-url', 'project'):
        execution.add_argument('--' + name, required=True)
    execution.add_argument('--sql-timeout-ms', type=int, required=True)
    execution.add_argument('--ask-timeout-seconds', type=float, required=True)
    execution.add_argument('--smoke', action='store_true', help='Use only the first frozen case; never reports a 30-case baseline')
    execution.set_defaults(handler=run)
    return result


if __name__ == '__main__':
    arguments = parser().parse_args()
    raise SystemExit(arguments.handler(arguments))
