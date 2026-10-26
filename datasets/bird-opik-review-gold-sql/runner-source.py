"""Replay archived BIRD results through official metrics and native Opik suites."""

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode(value):
    if not isinstance(value, dict):
        return value
    if set(value) != {'type', 'value'}:
        raise ValueError('Unknown archived result encoding')
    constructors = {'Decimal': Decimal, 'date': date.fromisoformat,
                    'datetime': datetime.fromisoformat, 'time': time.fromisoformat}
    return constructors[value['type']](value['value'])


def official_f1(path, expected_sha256):
    if digest(path) != expected_sha256:
        raise ValueError('Official evaluator checksum differs')
    tree = ast.parse(Path(path).read_text())
    names = {'calculate_row_match', 'calculate_f1_score'}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in functions} != names:
        raise ValueError('Official metric functions are missing')
    namespace = {}
    # Execute the unmodified pure functions; the upstream CLI imports DB drivers.
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace['calculate_f1_score']


def readback(client, experiment_id, name, project, count):
    experiment = client.rest_client.experiments.get_experiment_by_id(experiment_id)
    raw = b''.join(client.rest_client.experiments.stream_experiment_items(
        experiment_name=name, project_name=project, limit=count + 1, truncate=False))
    items = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if experiment.status != 'completed' or len(items) != count:
        raise RuntimeError('Opik experiment is incomplete')
    return {'experiment': experiment.model_dump(mode='json'), 'items': items}


def compare_gold_assertion(report, suite_items, outcomes, assertion_name):
    items_by_id = {item['id']: item['data'] for item in suite_items}
    cases = []
    for item in report['items']:
        data = items_by_id[item['dataset_item_id']]
        if len(item['runs']) != 1:
            raise RuntimeError('Gold SQL assertion must have one archived run per case')
        run = item['runs'][0]
        if 'gold_sql' in run['input'] or run['output'].get('gold_sql') != data['gold_sql']:
            raise RuntimeError('Gold SQL reference was not isolated in the judge output')
        result = next((assertion for assertion in run['assertions']
                       if assertion['name'] == assertion_name), None)
        if result is None or result['scoring_failed']:
            raise RuntimeError('Gold SQL assertion result is missing or failed to score')
        ex = outcomes[data['case_id']]['EX'] == 1
        cases.append({'case_id': data['case_id'], 'question_id': data['question_id'],
                      'judge_passed': result['passed'], 'official_EX_passed': ex,
                      'agreed': result['passed'] == ex})
    if len(cases) != len(outcomes) or {case['case_id'] for case in cases} != set(outcomes):
        raise RuntimeError('Gold SQL assertion did not cover the pinned cohort')
    return {
        'assertion': assertion_name,
        'items_total': len(cases),
        'judge_passed': sum(case['judge_passed'] for case in cases),
        'official_EX_passed': sum(case['official_EX_passed'] for case in cases),
        'agreement_count': sum(case['agreed'] for case in cases),
        'agreement_rate': sum(case['agreed'] for case in cases) / len(cases),
        'false_positive_question_ids': [case['question_id'] for case in cases
                                        if case['judge_passed'] and not case['official_EX_passed']],
        'false_negative_question_ids': [case['question_id'] for case in cases
                                        if not case['judge_passed'] and case['official_EX_passed']],
        'cases': cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--baseline-run', type=Path, required=True)
    parser.add_argument('--dataset-lock', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--evaluator', type=Path, required=True)
    parser.add_argument('--model-env', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    policy, lock, bundle = read(args.policy), read(args.dataset_lock), read(args.records)
    records = bundle['records']
    calculate_f1 = official_f1(args.evaluator, policy['evaluator_sha256'])
    outcomes = {}
    for record in records:
        path = args.baseline_run / record['question_id'] / 'score.json'
        if digest(path) != record['score_sha256'] or read(path) != record['score']:
            raise ValueError('Archived score content differs: ' + record['question_id'])
        gold = [tuple(map(decode, row)) for row in record['score']['gold_rows']]
        actual = [tuple(map(decode, row)) for row in record['score']['predicted_rows']]
        ex = int(set(gold) == set(actual))
        if ex != record['ex']:
            raise ValueError('Archived EX cannot be reproduced: ' + record['question_id'])
        outcomes[record['case_id']] = {
            'case_id': record['case_id'], 'question_id': record['question_id'],
            'execution_mode': 'frozen_result_replay', 'source_experiment': bundle['experiment'],
            'sql': record['sql'], 'gold_rows': record['score']['gold_rows'],
            'actual_rows': record['score']['predicted_rows'], 'EX': ex,
            'BIRD_SoftF1': calculate_f1(actual, gold), 'original_ask_ms': record['ask_ms'],
            'original_query_id': record['queryId'], 'original_trace_id': record['traceId'],
            'source_score_sha256': record['score_sha256'],
        }
    if len(outcomes) != lock['version']['items_total'] or set(outcomes) != set(lock['case_ids']):
        raise ValueError('Cohort differs from the pinned baseline dataset')
    write(args.output_dir / 'official-metrics.json', list(outcomes.values()))
    config = {'execution_mode': 'frozen_result_replay', 'source_experiment': bundle['experiment'],
              'records_sha256': digest(args.records), 'policy_sha256': digest(args.policy),
              'script_sha256': digest(__file__), 'official_evaluator': policy['evaluator_url'],
              'official_evaluator_sha256': policy['evaluator_sha256'],
              'sdk_version': importlib.metadata.version('opik'), 'new_nl2sql_calls': 0,
              'sql_pair_knowledge_used': False, 'human_approved': False}
    write(args.output_dir / 'manifest.json', config)
    os.environ.update(OPIK_URL_OVERRIDE=lock['host'], OPIK_WORKSPACE=lock['workspace'],
                      OPIK_PROJECT_NAME=lock['project_name'])
    import opik
    from opik.evaluation import evaluate
    from opik.evaluation.metrics import BaseMetric
    from opik.evaluation.metrics.score_result import ScoreResult
    from dotenv import dotenv_values

    client = opik.Opik(host=lock['host'], workspace=lock['workspace'], project_name=lock['project_name'])
    dataset = client.get_dataset(lock['dataset_name'], project_name=lock['project_name'])
    version = dataset.get_version_view(lock['version']['version_name'])
    if dataset.id != lock['dataset_id'] or version.get_version_info().id != lock['version']['id']:
        raise ValueError('Opik dataset/version identity differs')
    items = version.get_items()
    if len(items) != len(records) or {item['case_id'] for item in items} != set(outcomes):
        raise ValueError('Opik dataset items differ')
    by_id = {record['case_id']: record for record in records}
    for item in items:
        for key in ('question', 'evidence', 'gold_sql'):
            if item[key] != by_id[item['case_id']][key]:
                raise ValueError('Opik input content differs')

    class OfficialMetrics(BaseMetric):
        def score(self, EX, BIRD_SoftF1, original_ask_ms, **ignored):
            return [ScoreResult(name='EX', value=EX, reason='Original strict BIRD EX, reproduced from complete archived rows'),
                    ScoreResult(name='BIRD_SoftF1', value=round(BIRD_SoftF1, 6),
                                reason='Unmodified official beta metric; preserves archived row order; not semantic correctness'),
                    ScoreResult(name='original_ask_ms', value=round(original_ask_ms, 6))]

    name = args.output_dir.name + '-official-metrics'
    result = evaluate(dataset=version, task=lambda item: outcomes[item['case_id']],
                      scoring_metrics=[OfficialMetrics(track=False)], experiment_name=name,
                      project_name=lock['project_name'], experiment_config=config,
                      task_threads=1, trial_count=1, verbose=0)
    write(args.output_dir / 'metrics-created.json', {'experiment_id': result.experiment_id,
                                                   'experiment_url': result.experiment_url})
    if len(result.test_results) != len(records) or any(
            score.scoring_failed for test in result.test_results for score in test.score_results):
        raise RuntimeError('Official metric evaluation failed')
    opik.flush_tracker(); client.flush()
    persisted = readback(client, result.experiment_id, name, lock['project_name'], len(records))
    if persisted['experiment']['dataset_version_id'] != lock['version']['id']:
        raise RuntimeError('Published experiment dataset version differs')
    for item in persisted['items']:
        expected = outcomes[item['output']['case_id']]
        scores = {score['name']: score['value'] for score in item['feedback_scores']}
        if item['output'] != expected or scores['EX'] != expected['EX'] or scores['BIRD_SoftF1'] != round(expected['BIRD_SoftF1'], 6):
            raise RuntimeError('Published official metric content differs')
    write(args.output_dir / 'metrics-readback.json', persisted)
    print('Official metrics published and read back:', result.experiment_id, flush=True)

    env = dotenv_values(args.model_env)
    profile = 'LLM_PROFILE_' + env['LLM_CHAT_PROFILE'] + '_'
    if env[profile + 'PROVIDER'] != 'openai-compatible':
        raise ValueError('This run requires the configured OpenAI-compatible provider')
    model = 'openai/' + env[profile + 'MODEL']
    os.environ.update(OPENAI_API_KEY=env[profile + 'API_KEY'],
                      OPENAI_API_BASE=env[profile + 'BASE_URL'], OPENAI_BASE_URL=env[profile + 'BASE_URL'])
    suite_name = args.output_dir.name + '-gold-sql-assertions'
    gold_assertion = next(assertion for assertion in policy['assertions'] if 'Gold SQL' in assertion)
    suite = client.create_evaluation_suite(name=suite_name, project_name=lock['project_name'],
        description='Native Opik assertions on 30 archived NL2SQL outputs. Each case includes its BIRD Gold SQL; the Gold assertion is LLM-judged and compared with official EX. No SQL is regenerated.',
        assertions=policy['assertions'], execution_policy={'runs_per_item': 1, 'pass_threshold': 1},
        tags=['BIRD', 'frozen-replay', 'no-sql-pair'])
    suite.add_items([{'data': {key: r[key] for key in ('case_id', 'question_id', 'question', 'evidence', 'gold_sql')}}
                     for r in records])
    suite_items = suite.get_items()
    if len(suite_items) != len(records) or suite.get_assertions() != policy['assertions']:
        raise RuntimeError('Native suite configuration readback differs')
    suite_data = {item['data']['case_id']: item['data'] for item in suite_items}
    if any(suite_data[r['case_id']]['gold_sql'] != r['gold_sql'] for r in records):
        raise RuntimeError('Per-question Gold SQL was not persisted in the Test Suite')
    suite_id = client.get_dataset(suite_name, project_name=lock['project_name']).id
    write(args.output_dir / 'suite-created.json', {'id': suite_id, 'name': suite_name,
           'assertions': suite.get_assertions(), 'items': suite_items, 'judge_model': model,
           'judge_temperature': 'SDK/provider default (not overridden)', 'generator_and_judge_same_model_family': True,
           'gold_sql_in_each_test_item': True, 'gold_sql_in_judge_output': True,
           'gold_sql_in_task_input': False})

    def archived_task(item):
        record = by_id[item['case_id']]
        return {'input': {key: record[key] for key in ('question', 'evidence')},
                'output': {'sql': record['sql'], 'rows': record['score']['predicted_rows'],
                           'gold_sql': record['gold_sql']}}

    suite_result = suite.run(task=archived_task, model=model, project_name=lock['project_name'],
        experiment_name=suite_name + '-run', experiment_config=config | {'judge_model': model},
        worker_threads=2, verbose=1, report_output_path=str(args.output_dir / 'suite-report.json'))
    report = suite_result.to_report_dict()
    write(args.output_dir / 'suite-report.json', report)
    gold_assertion_validation = compare_gold_assertion(report, suite_items, outcomes, gold_assertion)
    write(args.output_dir / 'gold-sql-assertion-validation.json', gold_assertion_validation)
    opik.flush_tracker(); client.flush()
    suite_readback = readback(client, suite_result.experiment_id, suite_name + '-run', lock['project_name'], len(records))
    write(args.output_dir / 'suite-readback.json', suite_readback)
    if suite_result.items_total != len(records) or any(score.scoring_failed
            for item in suite_result.item_results.values() for test in item.test_results for score in test.score_results):
        raise RuntimeError('Native assertion evaluation failed; not a semantic FAIL')

    definitions = client.rest_client.feedback_definitions.find_feedback_definitions(name='User feedback', size=100)
    if not any(d.name == 'User feedback' for d in definitions.content):
        raise ValueError('Existing native User feedback definition is missing')
    queue = client.create_traces_annotation_queue(name=args.output_dir.name + '-SME-review',
        project_name=lock['project_name'], description='30 archived outputs, awaiting actual human review.',
        instructions=policy['review_instructions'], comments_enabled=True,
        feedback_definition_names=['User feedback'])
    client.rest_client.annotation_queues.add_items_to_annotation_queue(
        queue.id, ids=[item['trace_id'] for item in persisted['items']])
    queue_remote = client.rest_client.annotation_queues.get_annotation_queue_by_id(queue.id)
    write(args.output_dir / 'queue-readback.json', queue_remote.model_dump(mode='json'))
    if queue_remote.items_count != len(records):
        raise RuntimeError('Annotation queue item count differs')
    summary = {'source_experiment': bundle['experiment'], 'execution_mode': 'frozen_result_replay',
               'EX': sum(o['EX'] for o in outcomes.values()) / len(outcomes),
               'BIRD_SoftF1': sum(o['BIRD_SoftF1'] for o in outcomes.values()) / len(outcomes),
               'records': len(outcomes), 'metrics_experiment_id': result.experiment_id,
               'suite_id': suite_id, 'suite_experiment_id': suite_result.experiment_id,
               'assertion_items_passed': suite_result.items_passed, 'assertion_items_total': suite_result.items_total,
               'gold_sql_assertion_passed': gold_assertion_validation['judge_passed'],
               'gold_sql_assertion_agreement_with_official_EX': gold_assertion_validation['agreement_rate'],
               'annotation_queue_id': queue.id, 'human_annotations_submitted': 0,
               'new_nl2sql_calls': 0, 'new_judge_evaluation': True}
    write(args.output_dir / 'summary.json', summary)
    write(args.output_dir / 'verification.json', {
        'persisted_assertion_items': suite_result.items_total,
        'persisted_assertion_passes': suite_result.items_passed,
        'gold_sql_present_on_all_suite_items': len(suite_data) == len(records),
        'gold_sql_present_in_judge_output': True,
        'gold_sql_excluded_from_task_input': True,
        'official_EX_passes': sum(o['EX'] for o in outcomes.values()),
        'gold_assertion_vs_official_EX': {
            'agreement_count': gold_assertion_validation['agreement_count'],
            'items_total': gold_assertion_validation['items_total'],
            'false_positive_question_ids': gold_assertion_validation['false_positive_question_ids'],
            'false_negative_question_ids': gold_assertion_validation['false_negative_question_ids'],
        },
        'source_scores_verified': True,
        'new_nl2sql_calls': 0,
        'human_approval_claimed': False,
    })
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
