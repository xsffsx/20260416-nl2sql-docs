"""Verify and publish the three archived UI runs; no model or SQL calls."""

import argparse
import csv
import json
import shutil
import zipfile
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import sqlglot

from rhesis_bird_metrics import official_ex
from rhesis_flex_metrics import FlexSource
from run_bird_baseline import sha256


def decode(value):
    if set(value) == {"type", "value"}:
        constructors = {"Decimal": Decimal, "date": date.fromisoformat,
                        "datetime": datetime.fromisoformat, "time": time.fromisoformat}
        return constructors[value["type"]](value["value"])
    return value


def build(args):
    bundle = args.bundle
    manifest = json.loads((bundle / "manifest.json").read_text())
    references = json.loads((bundle / "references.json").read_text())
    notes = json.loads((bundle / "case-analysis.json").read_text())
    assert set(notes) == set(manifest["question_ids"])
    source = FlexSource(bundle / "upstream")
    ex = official_ex(args.ex_evaluator, args.ex_sha256)
    prompt_dir = bundle / "judge-prompts"
    prompt_dir.mkdir(exist_ok=True)
    summaries, records = {}, {}
    for variant in ("evidence", "gold", "combined"):
        summaries[variant] = json.loads((bundle / f"runs/{variant}/summary.json").read_text())
        rows = json.loads((bundle / f"runs/{variant}/records.json").read_text())
        assert [x["question_id"] for x in rows] == manifest["question_ids"]
        assert len(rows) == 30 and summaries[variant]["recorded"] == 30
        native_run = json.loads((bundle / f"runs/{variant}/rhesis-run.json").read_text())
        config = native_run["test_configuration"]
        assert config["attributes"]["execution_mode"] == "Parallel"
        assert config["attributes"]["metrics_source"] == "test_set"
        assert config["attributes"]["evaluation_model_id"] == manifest["judge"]["rhesis_model_id"]
        assert config["endpoint"]["id"] == manifest["endpoint"]["id"]
        assert not native_run["attributes"].get("reference_run_id")
        for row in rows:
            assert row["input_isolation_verified"]
            audit = json.loads((bundle / row["audit_file"]).read_text(), object_hook=decode)
            assert audit["judge"] == manifest["judge"]
            row["judge_called"] = "prompts" in audit
            row["judge_reply"] = audit["judge_response"]["choices"][0]["message"]["content"] if audit.get("judge_response") else None
            if "prompts" in audit:
                case = next(x for x in references if str(x["question_id"]) == row["question_id"])
                execution = audit["execution"]
                strict = ex([tuple(r) for r in execution["predicted_rows"]], [tuple(r) for r in execution["gold_rows"]]) == 1
                replayed = source.prompts(variant, manifest["schema"], row["question"], row["actual_sql"],
                    row["expected_response"], execution["predicted_rows"], execution["gold_rows"], strict)
                assert audit["prompts"] == replayed, row["question_id"]
                assert replayed["visible_fields"]["expected_response"] == row["expected_response"]
                prompt_file = f"judge-prompts/{variant}-{row['question_id']}.md"
                (bundle / prompt_file).write_text(
                    f"# {variant} · question {row['question_id']}\n\n"
                    f"Run: {row['run_id']}\n\n"
                    f"## expected_response\n\n```json\n{row['expected_response']}\n```\n\n"
                    f"## System prompt\n\n```text\n{replayed['system']}\n```\n\n"
                    f"## User prompt\n\n```text\n{replayed['user']}\n```\n")
                row["prompt_file"] = prompt_file
                fields = replayed["visible_fields"]
                if variant == "evidence":
                    assert not {"gold_sql", "gold_result", "execution_match"} & fields.keys()
                if variant == "gold":
                    assert "evidence" not in fields and "**Hint**" not in replayed["user"]
                if variant == "combined":
                    assert {"gold_sql", "evidence"} <= fields.keys()
            else:
                row["prompt_file"] = None
                assert row["score"] is None
                assert "judge_response" not in audit
            row["sql_format_error"] = row["execution"]["error"] if row["category"] == "SQL execution error" else None
            row["actual_sql_formatted"] = None if row["sql_format_error"] else sqlglot.parse_one(row["actual_sql"], read="postgres").sql(dialect="postgres", pretty=True)
            row["gold_row_count"] = len(row["execution"]["gold_rows"]) if row["execution"] else None
            row["actual_row_count"] = len(row["execution"]["predicted_rows"]) if row["execution"] and row["execution"]["predicted_rows"] is not None else None
        records[variant] = rows
    all_rows = [x for rows in records.values() for x in rows]
    for key in ("query_id", "thread_id", "trace_id", "result_id", "test_id"):
        assert len({x[key] for x in all_rows}) == 90
    cases = []
    for index, case in enumerate(references):
        runs = {variant: rows[index] for variant, rows in records.items()}
        cases.append({"case_number": index + 1, "question_id": str(case["question_id"]),
            "question": case["question"], "evidence": case["evidence"],
            "analysis": notes[str(case["question_id"])],
            "gold_sql_formatted": sqlglot.parse_one(case["gold_sql_postgresql_poc"], read="postgres").sql(dialect="postgres", pretty=True),
            "same_actual_sql": len({r["actual_sql_sha256"] for r in runs.values()}) == 1, "runs": runs})
    report = {"runs": summaries, "cases": cases,
              "same_sql_questions": sum(c["same_actual_sql"] for c in cases),
              "valid_judgments": sum(r["score"] is not None for r in all_rows),
              "evaluation_errors": sum(r["category"] == "Evaluation error" for r in all_rows),
              "judge_request_replay_verified": sum("prompts" in json.loads((bundle / r["audit_file"]).read_text()) for r in all_rows)}
    (bundle / "comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    with (bundle / "comparison.csv").open("w", newline="") as stream:
        fields = ["question_id", "variant", "question", "expected_response", "actual_sql", "actual_sql_sha256",
                  "category", "score", "branch", "judge_called", "prompt_file", "judge_reply", "error", "run_id", "result_id", "query_id", "trace_id", "audit_file"]
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    # Keep full execution rows in downloads; the interactive page uses only counts.
    page_report = json.loads(json.dumps(report))
    for case in page_report["cases"]:
        for row in case["runs"].values():
            del row["execution"]
    args.page_data.write_text(json.dumps(page_report, ensure_ascii=False, indent=2) + "\n")
    for name in ("rhesis_flex_metrics.py", "collect_rhesis_flex.py", "build_rhesis_flex_report.py",
                 "prepare_rhesis_flex.py", "rhesis_bird_metrics.py", "run_bird_baseline.py",
                 "run_bird_opik_api.py", "review_bird_opik.py", "test_rhesis_flex_metrics.py"):
        shutil.copyfile(Path(__file__).parent / name, bundle / name)
    shutil.copyfile(args.ex_evaluator, bundle / "evaluation_ex.py")
    checks = {str(p.relative_to(bundle)): sha256(p) for p in sorted(bundle.rglob("*"))
              if p.is_file() and p.name not in ("checksums.json", "rhesis-flex-evidence.zip")}
    (bundle / "checksums.json").write_text(json.dumps(checks, indent=2) + "\n")
    profile = json.loads(args.opencode_config.read_text())["provider"][manifest["judge"]["provider"]]
    secrets = [args.token_file.read_text().strip(), profile["options"]["apiKey"]]
    for path in bundle.rglob("*"):
        if path.is_file() and path.suffix != ".zip":
            data = path.read_bytes()
            if any(secret and secret.encode() in data for secret in secrets):
                raise ValueError("Private credential found in export: " + str(path))
    args.static_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, args.static_dir, dirs_exist_ok=True)
    with zipfile.ZipFile(args.static_dir / "rhesis-flex-evidence.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                archive.write(path, str(path.relative_to(bundle)))
    print(json.dumps({key: report[key] for key in ("same_sql_questions", "valid_judgments", "evaluation_errors", "judge_request_replay_verified")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "page-data", "static-dir", "opencode-config", "token-file", "ex-evaluator"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--ex-sha256", required=True)
    build(parser.parse_args())
