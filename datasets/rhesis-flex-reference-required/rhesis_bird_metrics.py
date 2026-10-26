"""Expose pinned official BIRD scoring through the Rhesis Code Metrics connector."""

import argparse
import ast
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
from dotenv import dotenv_values

from review_bird_opik import official_f1
from run_bird_baseline import encode_value, score_case


def official_ex(path, expected_sha256):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("Official EX evaluator checksum differs")
    functions = [node for node in ast.parse(path.read_text()).body
                 if isinstance(node, ast.FunctionDef) and node.name == "calculate_ex"]
    if len(functions) != 1:
        raise ValueError("Official calculate_ex function is missing")
    namespace = {}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["calculate_ex"]


class BirdMetric:
    def __init__(self, references, dsn, timeout_ms, calculate_ex, calculate_f1, parallel_workers, audit_dir=None):
        self.references = {}
        for row in references:
            question = row["prompt_content"]
            if question in self.references or not row["expected_response"].strip():
                raise ValueError("Duplicate question or missing Gold SQL")
            self.references[question] = row["expected_response"]
        if not self.references or timeout_ms <= 0 or parallel_workers < 0:
            raise ValueError("References and positive SQL timeout are required")
        self.dsn, self.timeout_ms = dsn, timeout_ms
        self.calculate_ex, self.calculate_f1 = calculate_ex, calculate_f1
        self.parallel_workers = parallel_workers
        self.audit_dir = audit_dir

    def evaluate(self, input, output, expected_output):
        if input not in self.references or expected_output != self.references[input]:
            raise ValueError("Rhesis question/Gold SQL differs from the frozen reference CSV")
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            conn.execute("SELECT set_config('max_parallel_workers_per_gather', %s, false)",
                         (str(self.parallel_workers),))
            result = score_case(conn, output, expected_output, self.timeout_ms)
        actual, gold = result["predicted_rows"], result["gold_rows"]
        ex = 0 if result["error"] else self.calculate_ex(actual, gold)
        soft_f1 = 0.0 if result["error"] else float(self.calculate_f1(actual, gold))
        details = {
            "reason": (result["error"] or ("Complete results match Gold SQL" if ex else "Complete results differ from Gold SQL")) + f"; BIRD Soft F1 = {soft_f1}",
            "BIRD_Soft_F1": soft_f1,
            "actual_sql": output,
            "gold_sql": expected_output,
            "actual_result": actual,
            "gold_result": gold,
            "sql_error": result["error"],
            "scorer_ms": result["scorer_ms"],
            "max_parallel_workers_per_gather": self.parallel_workers,
        }
        response = json.loads(json.dumps({"score": float(ex), "details": details}, default=encode_value, allow_nan=False))
        if self.audit_dir is not None:
            path = self.audit_dir / (str(uuid4()) + ".json")
            with path.open("x") as stream:
                json.dump({"recorded_at": datetime.now(timezone.utc).isoformat(), "question": input, **response}, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write("\n")
        return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--scorer-env", type=Path, required=True)
    parser.add_argument("--ex-evaluator", type=Path, required=True)
    parser.add_argument("--ex-sha256", required=True)
    parser.add_argument("--f1-evaluator", type=Path, required=True)
    parser.add_argument("--f1-sha256", required=True)
    parser.add_argument("--sql-timeout-ms", type=int, required=True)
    parser.add_argument("--parallel-workers-per-gather", type=int, required=True)
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--rhesis-url")
    parser.add_argument("--rhesis-project")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    dsn = dotenv_values(args.scorer_env).get("BIRD_SCORER_DSN")
    if not dsn:
        raise ValueError("BIRD_SCORER_DSN is missing")
    with args.references.open(newline="") as stream:
        references = list(csv.DictReader(stream))
    evaluator = BirdMetric(references, dsn, args.sql_timeout_ms,
                           official_ex(args.ex_evaluator, args.ex_sha256),
                           official_f1(args.f1_evaluator, args.f1_sha256), args.parallel_workers_per_gather)
    if args.self_check:
        for row in references:
            result = evaluator.evaluate(row["prompt_content"], row["expected_response"], row["expected_response"])
            assert result["score"] == 1.0 and result["details"]["BIRD_Soft_F1"] == 1.0, row["metadata"]
        print(json.dumps({"gold_self_checks_passed": len(references)}))
        return
    if not all((args.token_file, args.rhesis_url, args.rhesis_project, args.output_dir)):
        parser.error("Connector mode requires token-file, rhesis-url, rhesis-project and output-dir")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    evaluator.audit_dir = args.output_dir
    from rhesis.sdk import RhesisClient, metric

    client = RhesisClient(api_key=args.token_file.read_text().strip(),
                          base_url=args.rhesis_url, project_id=args.rhesis_project)

    @metric(name="BIRD Official Execution Accuracy", score_type="binary",
            description="Pinned BIRD calculate_ex on complete read-only PostgreSQL results. Official Soft F1 and actual/Gold results are diagnostic details; no LLM judge.")
    def bird_execution_accuracy(input: str, output: str, expected_output: str) -> dict:
        return evaluator.evaluate(input, output, expected_output)

    client.connect()


if __name__ == "__main__":
    main()
