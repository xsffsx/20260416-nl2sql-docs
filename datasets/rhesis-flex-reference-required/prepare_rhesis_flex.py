"""Freeze the three Rhesis FLEX cohorts and the real evaluation environment."""

import argparse
import csv
import hashlib
import json
import urllib.request
from pathlib import Path

import httpx
import psycopg
from dotenv import dotenv_values

from rhesis_bird_metrics import official_ex
from run_bird_baseline import audit_gold, frozen_runtime, read_json_api, score_case, sha256, write_json
from run_bird_opik_api import verify_database_content


VARIANTS = {"evidence": ("evidence",), "gold": ("gold_sql",), "combined": ("evidence", "gold_sql")}


def reference(case, variant):
    values = {"evidence": case["evidence"], "gold_sql": case["gold_sql_postgresql_poc"]}
    return json.dumps({key: values[key] for key in VARIANTS[variant]}, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-lock", "bundle", "scorer-env", "previous-summary", "token-file", "opencode-config"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("api-url", "project", "rhesis-url", "rhesis-model", "rhesis-endpoint", "judge-provider"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--sql-timeout-ms", type=int, required=True)
    parser.add_argument("--judge-timeout-seconds", type=int, required=True)
    parser.add_argument("--judge-max-tokens", type=int, required=True)
    parser.add_argument("--judge-reasoning-effort", required=True)
    args = parser.parse_args()
    source = json.loads(args.source_lock.read_text())
    bundle = args.bundle
    upstream = json.loads((bundle / "upstream/source-lock.json").read_text())
    for name, info in upstream["files"].items():
        if sha256(bundle / "upstream" / name) != info["sha256"]:
            raise ValueError("FLEX upstream source checksum differs: " + name)
    qa_path = bundle / "bird-mini-dev-pg.json"
    data = urllib.request.urlopen(source["sources"]["qa"]["url"], timeout=30).read()
    if hashlib.sha256(data).hexdigest() != source["sources"]["qa"]["sha256"]:
        raise ValueError("Official BIRD source checksum differs")
    qa_path.write_bytes(data)
    official = {str(x["question_id"]): x for x in json.loads(data)}
    cases = source["cases"]
    if len(cases) != 30 or len({x["question"] for x in cases}) != 30:
        raise ValueError("Exactly thirty unique source questions are required")
    for case in cases:
        item = official[str(case["question_id"])]
        if (case["question"], case["evidence"], case["gold_sql_postgresql_source"]) != (
            item["question"], item["evidence"], item["SQL"]
        ):
            raise ValueError("Case differs from pinned BIRD source: " + str(case["question_id"]))
    write_json(bundle / "gold-identifier-audit.json", audit_gold(source, cases))
    write_json(bundle / "references.json", cases)
    csv_hashes = {}
    for variant in VARIANTS:
        path = bundle / ("bird-flex-" + variant + "-30.csv")
        with path.open("x", newline="", encoding="utf-8") as stream:
            fields = ["category", "topic", "requirement", "prompt_content", "expected_response", "language_code", "metadata"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for case in cases:
                writer.writerow({"category": "BIRD Mini-Dev V2", "topic": case["db_id"],
                                 "requirement": "Generate read-only SQL for the question; score with FLEX-based " + variant,
                                 "prompt_content": case["question"], "expected_response": reference(case, variant),
                                 "language_code": "en", "metadata": json.dumps({
                                     "question_id": str(case["question_id"]), "db_id": case["db_id"], "variant": variant,
                                     "input_protocol": "question_only", "evidence_available": bool(case["evidence"]),
                                     "source_revision": source["sources"]["qa"]["revision"],
                                     "reference_sha256": hashlib.sha256(reference(case, variant).encode()).hexdigest()})})
        with path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 30
        assert [x["prompt_content"] for x in rows] == [x["question"] for x in cases]
        assert all(json.loads(x["expected_response"]) == json.loads(reference(c, variant)) for x, c in zip(rows, cases, strict=True))
        csv_hashes[path.name] = sha256(path)
    judge_profile = json.loads(args.opencode_config.read_text())["provider"][args.judge_provider]
    authorization = {"Authorization": "Bearer " + args.token_file.read_text().strip()}
    with httpx.Client(base_url=args.rhesis_url, headers=authorization, trust_env=False, timeout=30) as client:
        response = client.get("/models/" + args.rhesis_model)
        response.raise_for_status()
        model = response.json()
        response = client.get("/endpoints/" + args.rhesis_endpoint)
        response.raise_for_status()
        endpoint = response.json()
    if (model["endpoint"].rstrip("/") != judge_profile["options"]["baseURL"].rstrip("/")
            or not judge_profile["options"]["apiKey"]):
        raise ValueError("Judge credential profile does not match the existing Rhesis model")
    if endpoint["request_mapping"] != {"query": "{{ input }}"} or endpoint["response_mapping"] != {"output": "$.sql"}:
        raise ValueError("REST Endpoint differs from the question-only mapping")
    judge = {"rhesis_model_id": model["id"], "name": model["name"], "model": model["model_name"],
             "base_url": model["endpoint"], "provider": args.judge_provider, "temperature": 0,
             "max_tokens": args.judge_max_tokens, "timeout_seconds": args.judge_timeout_seconds,
             "thinking": {"type": "enabled"}, "reasoning_effort": args.judge_reasoning_effort,
             "parameter_source": "https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3"}
    dsn = dotenv_values(args.scorer_env)["BIRD_SCORER_DSN"]
    prior = json.loads(args.previous_summary.read_text())
    with httpx.Client(base_url=args.api_url, trust_env=False, timeout=60) as client:
        runtime = frozen_runtime(client, args.project)
        snapshot = read_json_api(client, "/api/artifact-versions/" + runtime["artifactVersionId"], args.project)["bundle"]
        if snapshot["sqlPairs"] != []:
            raise ValueError("Active Snapshot contains SQL Pairs")
        response = client.post("/api/health", params={"mode": "project", "projectId": args.project})
        response.raise_for_status()
        if not response.json()["project"]["qaAvailable"]:
            raise ValueError("NL2SQL project is not QA ready")
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("SET default_transaction_read_only=on")
        conn.execute("SET max_parallel_workers_per_gather=0")
        tables = verify_database_content(conn, source, prior["database_tables_verified_after_run"])
        columns = conn.execute("SELECT table_name,column_name,data_type,is_nullable FROM information_schema.columns "
                               "WHERE table_schema=current_schema() ORDER BY table_name,ordinal_position").fetchall()
        names = {x["csv_table"] for x in source["tables"]}
        columns = [x for x in columns if x[0] in names]
        privileges = {name: conn.execute("SELECT has_table_privilege(current_user,%s,'INSERT,UPDATE,DELETE,TRUNCATE')", (name,)).fetchone()[0] for name in sorted(names)}
        if any(privileges.values()):
            raise ValueError("Scorer role has write privileges")
        semantics = {"integer_division": conn.execute("SELECT 5/2").fetchone()[0],
                     "numeric_division": str(conn.execute("SELECT 5::numeric/2").fetchone()[0]),
                     "nullable_count": conn.execute("SELECT count(x),count(*) FROM (VALUES (NULL::int),(1)) t(x)").fetchone()}
        with conn.transaction():
            try:
                conn.execute("SELECT '1'::text = 1::integer")
            except psycopg.errors.UndefinedFunction:
                semantics["text_integer_comparison"] = "operator rejected; explicit compatible casts required"
            else:
                raise ValueError("Unexpected PostgreSQL text/integer comparison semantics")
        checks = []
        for case in cases:
            result = score_case(conn, case["gold_sql_postgresql_poc"], case["gold_sql_postgresql_poc"], args.sql_timeout_ms)
            if result["error"] or result["ex"] != 1:
                raise ValueError("Gold self-check failed: " + str(case["question_id"]))
            checks.append({"question_id": str(case["question_id"]), "ex": result["ex"], "rows": len(result["gold_rows"])})
    schema = "\n".join(f"{table}.{column}: {dtype}; nullable={nullable}" for table, column, dtype, nullable in columns)
    manifest = {"project": args.project, "api_url": args.api_url, "runtime": runtime, "tables": tables,
                "schema": schema, "schema_sha256": hashlib.sha256(schema.encode()).hexdigest(),
                "source_lock_sha256": sha256(args.source_lock), "references_sha256": sha256(bundle / "references.json"),
                "question_ids": [str(x["question_id"]) for x in cases], "csv_sha256": csv_hashes,
                "flex_revision": upstream["revision"], "judge": judge, "endpoint": {k: endpoint[k] for k in ["id", "url", "project_id", "environment", "request_mapping", "response_mapping"]},
                "sql_timeout_ms": args.sql_timeout_ms, "parallel_workers_per_gather": 0,
                "generation_protocol": "three independent Fresh Outputs runs; question only; no SQL Pair Knowledge",
                "evidence_internal_gold_dependency": "Gold used only for execution comparison/branch; never in evidence-only judge request",
                "scorer_write_privileges": privileges, "postgres_semantics": semantics, "gold_self_checks": checks}
    write_json(bundle / "manifest.json", manifest)
    print(json.dumps({"cases_per_set": 30, "sets": 3, "gold_self_checks": len(checks), "tables_verified": len(tables), "judge": model["name"]}))


if __name__ == "__main__":
    main()
