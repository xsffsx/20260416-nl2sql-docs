"""Archive a UI-launched Rhesis FLEX run; never generate or rescore SQL."""

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

import httpx
import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from prepare_rhesis_flex import reference
from rhesis_flex_metrics import METRIC_NAMES, digest
from run_bird_baseline import collect_knowledge_audit, frozen_runtime, read_json_api, validate_no_knowledge, write_json


def classify(result, metric, audit):
    if not result["test_output"].get("output"):
        return "Generation error", None
    if audit and audit.get("execution", {}).get("error"):
        return "SQL execution error", None
    if metric.get("error") or result["execution"] != "ok":
        return "Evaluation error", None
    if not audit or audit["status"] != "scored":
        raise ValueError("Native result has no matching completed judge audit")
    score = metric["score"]
    if score not in (0, 1) or score != audit["score"]:
        raise ValueError("Native and archived judge scores differ")
    if metric["is_successful"] != bool(score) or result["verdict"] != ("pass" if score else "fail"):
        raise ValueError("Native verdict differs from the judge score")
    return ("Pass" if score else "Fail"), score


async def collect(args):
    bundle = args.bundle
    manifest = json.loads((bundle / "manifest.json").read_text())
    refs = json.loads((bundle / "references.json").read_text())
    by_question = {x["question"]: x for x in refs}
    bindings = json.loads((bundle / "bindings-readback.json").read_text())[args.variant]
    output_dir = bundle / "runs" / args.variant
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "api-proofs").mkdir()
    with httpx.Client(base_url=args.rhesis_url, trust_env=False, timeout=60,
                     headers={"Authorization": "Bearer " + args.token_file.read_text().strip()}) as client:
        response = client.get("/test_runs/" + args.run_id)
        response.raise_for_status()
        run = response.json()
        response = client.get("/test_results/", params={"$filter": f"test_run_id eq '{args.run_id}'", "limit": 100})
        response.raise_for_status()
        results = response.json()
    if len(results) != 30 or any(x["test_run_id"] != args.run_id for x in results):
        raise ValueError("Native run does not contain exactly thirty correlated results")
    if run["attributes"]["status"] not in ("Completed", "Partial", "Failed", "Cancelled") or not run["attributes"].get("completed_at"):
        raise ValueError("Native run is not terminal")
    if {x["test_id"] for x in results} != {x["id"] for x in bindings["tests"]}:
        raise ValueError("Run does not cover the bound Test Set")
    write_json(output_dir / "rhesis-run.json", run)
    write_json(output_dir / "rhesis-results.json", results)
    audits = [json.loads(p.read_text()) | {"file": str(p.relative_to(bundle))}
              for p in args.audit_dir.glob("*.json")]
    audits = [a for a in audits if a["variant"] == args.variant]
    if len({a["question"] for a in audits}) != len(audits):
        raise ValueError("Duplicate metric calls; audit join must be reviewed")
    by_audit = {a["question"]: a for a in audits}
    records = []
    with httpx.Client(base_url=manifest["api_url"], trust_env=False, timeout=60) as api:
        runtime = frozen_runtime(api, manifest["project"])
        if runtime != manifest["runtime"]:
            raise ValueError("Runtime configuration drift")
        snapshot = read_json_api(api, "/api/artifact-versions/" + runtime["artifactVersionId"], manifest["project"])["bundle"]
        async with httpx2.AsyncClient(timeout=60, trust_env=False) as transport:
            async with streamable_http_client(manifest["api_url"] + "/mcp/" + manifest["project"] + "/", http_client=transport) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    for result in results:
                        question = result["test"]["prompt"]["content"]
                        case = by_question[question]
                        qid = str(case["question_id"])
                        expected = reference(case, args.variant)
                        if result["test"]["prompt"]["expected_response"] != expected:
                            raise ValueError("Native reference differs from the frozen CSV")
                        output = result["test_output"]
                        request = output.get("raw_request")
                        if not request or request["body"] != {"query": question} or request["method"] != "POST":
                            raise ValueError("Actual API request is not question-only POST")
                        if request["url"] != manifest["endpoint"]["url"]:
                            raise ValueError("Actual request endpoint differs")
                        sql = output.get("output")
                        raw = output.get("raw_response", {})
                        if sql != raw.get("sql"):
                            raise ValueError("Actual SQL differs from native API response")
                        metric_map = result["test_metrics"].get("metrics", {})
                        if set(metric_map) != {METRIC_NAMES[args.variant]}:
                            raise ValueError("Run used an unexpected metric")
                        metric = metric_map[METRIC_NAMES[args.variant]]
                        audit = by_audit.get(question)
                        if audit and (audit["actual_sql"] != sql or audit["expected_response"] != expected):
                            raise ValueError("Metric audit belongs to another output/reference")
                        category, score = classify(result, metric, audit)
                        proof = {"request": request, "raw_response": raw}
                        if raw.get("traceId"):
                            trace = read_json_api(api, "/v1/traces/" + raw["traceId"] + "/result", manifest["project"])
                            resource = await session.read_resource(trace["resources"]["traceEvents"])
                            if len(resource.contents) != 1:
                                raise ValueError("Canonical events resource is incomplete")
                            events = json.loads(resource.contents[0].text)
                            provider = collect_knowledge_audit(api, manifest["project"], raw["queryId"])
                            knowledge = validate_no_knowledge(snapshot, runtime, {"payload": trace, "events": events}, provider, question)
                            for key in ("queryId", "threadId", "traceId"):
                                if trace[key] != raw[key]:
                                    raise ValueError("API response and trace identity differ")
                            proof.update(trace=trace, canonical_events=events, provider_audits=provider, knowledge_proof=knowledge)
                        else:
                            proof["knowledge_proof_error"] = "No API trace; input isolation cannot be verified"
                        write_json(output_dir / "api-proofs" / (qid + ".json"), proof)
                        execution = audit.get("execution") if audit else None
                        prompts = audit.get("prompts") if audit else None
                        records.append({"question_id": qid, "question": question, "variant": args.variant,
                            "evidence": case["evidence"], "gold_sql": case["gold_sql_postgresql_poc"],
                            "expected_response": expected, "actual_sql": sql, "actual_sql_sha256": digest(sql) if sql else None,
                            "category": category, "score": score, "native_execution": result["execution"],
                            "native_verdict": result["verdict"], "native_metric": metric, "result_id": result["id"],
                            "test_id": result["test_id"], "run_id": args.run_id, "audit_file": audit["file"] if audit else None,
                            "judge_reason": audit.get("judge_reason") if audit else None,
                            "error": metric.get("error") or (audit.get("error") if audit else None),
                            "branch": ("Matching results" if prompts["strict"] else "Different results") if prompts else None,
                            "execution_accuracy": int(prompts["strict"]) if prompts else None,
                            "execution": execution, "judge_visible_fields": list(prompts["visible_fields"]) if prompts else [],
                            "query_id": raw.get("queryId"), "thread_id": raw.get("threadId"), "trace_id": raw.get("traceId"),
                            "input_isolation_verified": "knowledge_proof" in proof})
    records.sort(key=lambda x: manifest["question_ids"].index(x["question_id"]))
    if [x["question_id"] for x in records] != manifest["question_ids"]:
        raise ValueError("Source case coverage differs")
    counts = Counter(x["category"] for x in records)
    summary = {"variant": args.variant, "run_id": args.run_id, "run_name": run["name"],
        "run_url": "http://localhost:3002/test-runs/" + args.run_id + "?density=detail",
        "native_status": run["attributes"]["status"], "test_set_id": bindings["test_set"]["id"],
        "metric_name": METRIC_NAMES[args.variant], "planned": 30, "recorded": len(records), "counts": dict(counts),
        "valid_judgments": sum(x["score"] is not None for x in records),
        "input_isolation_verified": sum(x["input_isolation_verified"] for x in records),
        "started_at": run["attributes"].get("started_at"), "completed_at": run["attributes"].get("updated_at")}
    write_json(output_dir / "records.json", records)
    write_json(output_dir / "summary.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--variant", choices=list(METRIC_NAMES), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--rhesis-url", required=True)
    asyncio.run(collect(parser.parse_args()))
