import json
import tempfile
import unittest
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

import httpx

from prepare_rhesis_flex import reference
from rhesis_flex_metrics import FlexMetric, FlexSource, JudgeClient, parse_conclusion, parse_expected_response
from collect_rhesis_flex import classify


BUNDLE = Path(__file__).parents[2] / "docs/20261024_evaluation/rhesis-flex-reference-required-20261025"


def answer(correct):
    return {"choices": [{"finish_reason": "stop", "message": {
        "content": 'Comparison reason.\n```json\n' + json.dumps({"correct": correct}) + '\n```'}}]}


class FlexContractTests(unittest.TestCase):
    def test_native_error_zero_is_not_a_valid_judge_false(self):
        result = {"test_output": {"output": "SELECT 1"}, "execution": "error", "verdict": None}
        metric = {"score": 0, "error": "Invalid JSON conclusion", "is_successful": False}
        self.assertEqual(classify(result, metric, {"status": "error"}), ("Evaluation error", None))
        result.update(execution="ok", verdict="fail")
        metric.pop("error")
        self.assertEqual(classify(result, metric, {"status": "scored", "score": 0}), ("Fail", 0))
        metric["is_successful"] = True
        with self.assertRaises(ValueError):
            classify(result, metric, {"status": "scored", "score": 0})

    @classmethod
    def setUpClass(cls):
        cls.source = FlexSource(BUNDLE / "upstream")
        cls.case = json.loads((BUNDLE / "references.json").read_text())[0]

    def test_all_six_projections_keep_gold_out_of_evidence_judge(self):
        for strict in (False, True):
            for variant in ("evidence", "gold", "combined"):
                with self.subTest(strict=strict, variant=variant):
                    source = {"evidence": "SOURCE EVIDENCE", "gold_sql": "SECRET GOLD SQL"}
                    keys = ("evidence",) if variant == "evidence" else ("gold_sql",) if variant == "gold" else tuple(source)
                    expected = json.dumps({key: source[key] for key in keys})
                    value = self.source.prompts(variant, "schema", "question", "ACTUAL SQL", expected,
                                                [(1,)], [(2,)], strict)
                    self.assertNotIn("SQLite3", value["system"])
                    self.assertNotIn("schools.FundingType", value["user"])
                    self.assertEqual("gold_sql" in value["visible_fields"], variant != "evidence")
                    self.assertEqual("evidence" in value["visible_fields"], variant != "gold")
                    self.assertEqual("actual_result" in value["visible_fields"], not strict)
                    self.assertEqual(value["visible_fields"]["expected_response"], expected)
                    self.assertIn(expected, value["user"])
                    self.assertIn("sole answer/business reference", value["system"])
                    if variant == "evidence":
                        self.assertNotIn("SECRET GOLD SQL", value["user"])
                        self.assertNotIn("Note: two queries", value["user"])
                        self.assertNotIn("**Ground Truth Result**", value["user"])
                        self.assertNotIn("Ground Truth Query", value["system"])
                        self.assertNotIn("Reference Result", value["system"])
                        self.assertNotIn("Ground Truth Result", value["system"])

    def test_expected_response_requires_usable_reference_for_each_variant(self):
        case = {**self.case, "evidence": ""}
        self.assertEqual(json.loads(reference(case, "evidence")), {"evidence": ""})
        self.assertNotEqual(reference(case, "evidence"), "{}")
        for variant, invalid in [("evidence", '{"evidence":""}'), ("evidence", '{"evidence":"  "}'),
                                 ("gold", '{"gold_sql":""}'), ("combined", '{"evidence":"valid","gold_sql":""}'),
                                 ("evidence", '{}'), ("gold", '{"gold_sql":null}')]:
            with self.subTest(variant=variant, invalid=invalid), self.assertRaises(ValueError):
                parse_expected_response(variant, invalid)
        self.assertEqual(parse_expected_response("combined", '{"evidence":"","gold_sql":"SELECT 1"}'),
                         {"evidence": "", "gold_sql": "SELECT 1"})

    def test_empty_reference_stops_before_database_and_judge(self):
        cases = json.loads((BUNDLE / "references.json").read_text())
        empty = [case for case in cases if not case["evidence"].strip()]
        self.assertEqual(len(empty), 2)
        with tempfile.TemporaryDirectory() as folder:
            judge = Mock()
            evaluator = FlexMetric(BUNDLE, "unused", judge, folder, lambda a, b: 1)
            with patch("rhesis_flex_metrics.psycopg.connect") as database:
                for case in empty:
                    with self.assertRaisesRegex(ValueError, "Missing expected_response reference"):
                        evaluator.evaluate("evidence", case["question"], "SELECT 1", reference(case, "evidence"))
                database.assert_not_called()
            judge.assert_not_called()
            for path in Path(folder).glob("*.json"):
                audit = json.loads(path.read_text())
                self.assertIsNone(audit["score"])
                self.assertNotIn("prompts", audit)
                self.assertNotIn("judge_response", audit)
                self.assertEqual(audit["expected_response"], '{"evidence": ""}')

    def test_upstream_result_truncation_keeps_complete_shape(self):
        text, populated = self.source.format_result([(i,) for i in range(25)], deduplicate=False)
        self.assertTrue(populated)
        self.assertIn("...", text)
        self.assertIn("shape=(25, 1)", text)

    def test_parser_requires_one_final_boolean_and_has_no_text_match_path(self):
        self.assertTrue(parse_conclusion('reason\n```json\n{"correct": true}\n```'))
        self.assertTrue(parse_conclusion('{"correct": true}'))
        invalid = ['"correct": true', 'reason {"correct": true}', '```json\n{"correct": 1}\n```',
                   '```json\n{"correct": false}\n``` trailing',
                   '```json\n{"correct": true}\n```\n```json\n{"correct": false}\n```',
                   '```json\n{"correct": true,"other": 1}\n```', None]
        for text in invalid:
            with self.subTest(content=text), self.assertRaises((ValueError, TypeError)):
                parse_conclusion(text)

    def test_reference_tampering_is_rejected_before_sql_or_judge(self):
        with tempfile.TemporaryDirectory() as folder:
            judge = Mock()
            evaluator = FlexMetric(BUNDLE, "unused", judge, folder, lambda a, b: 1)
            with patch("rhesis_flex_metrics.psycopg.connect") as database:
                for input, expected in [("changed question", "{}"), (self.case["question"], "{}")]:
                    with self.assertRaisesRegex(ValueError, "frozen"):
                        evaluator.evaluate("evidence", input, "SELECT 1", expected)
                database.assert_not_called()
            judge.assert_not_called()
            self.assertEqual(len(list(Path(folder).glob("*.json"))), 2)

    def test_llm_verdict_controls_score_even_when_execution_disagrees(self):
        for execution_match, verdict in [(1, False), (0, True)]:
            with self.subTest(execution_match=execution_match), tempfile.TemporaryDirectory() as folder:
                judge = Mock(return_value=answer(verdict))
                evaluator = FlexMetric(BUNDLE, "unused", judge, folder, lambda a, b: execution_match)
                result = {"error": None, "gold_rows": [(1,)], "predicted_rows": [(2,)], "scorer_ms": 1}
                with patch("rhesis_flex_metrics.psycopg.connect"), patch("rhesis_flex_metrics.score_case", return_value=result):
                    scored = evaluator.evaluate("combined", self.case["question"], "SELECT 2", reference(self.case, "combined"))
                self.assertEqual(scored["score"], int(verdict))
                self.assertEqual(judge.call_args.args[0]["strict"], bool(execution_match))

    def test_judge_failure_has_no_fabricated_score_or_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            judge = Mock(side_effect=httpx.ReadTimeout("judge timed out"))
            evaluator = FlexMetric(BUNDLE, "unused", judge, folder, lambda a, b: 0)
            result = {"error": None, "gold_rows": [(1,)], "predicted_rows": [(2,)], "scorer_ms": 1}
            with patch("rhesis_flex_metrics.psycopg.connect"), patch("rhesis_flex_metrics.score_case", return_value=result):
                with self.assertRaises(httpx.ReadTimeout):
                    evaluator.evaluate("gold", self.case["question"], "SELECT 2", reference(self.case, "gold"))
            judge.assert_called_once()
            record = json.loads(next(Path(folder).glob("*.json")).read_text())
            self.assertIsNone(record["score"])
            self.assertEqual(record["status"], "error")
            self.assertEqual(record["error"]["type"], "ReadTimeout")

    def test_frozen_configuration_drift_stops_before_sql_and_judge(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("manifest.json", "references.json"):
                shutil.copyfile(BUNDLE / name, root / name)
            (root / "upstream").symlink_to(BUNDLE / "upstream", target_is_directory=True)
            judge = Mock()
            evaluator = FlexMetric(root, "unused", judge, root, lambda a, b: 0)
            manifest = json.loads((root / "manifest.json").read_text())
            manifest["judge"]["model"] = "changed-model"
            (root / "manifest.json").write_text(json.dumps(manifest))
            with patch("rhesis_flex_metrics.psycopg.connect") as database:
                with self.assertRaisesRegex(ValueError, "configuration drift"):
                    evaluator.evaluate("gold", self.case["question"], "SELECT 1", reference(self.case, "gold"))
                database.assert_not_called()
            judge.assert_not_called()

    def test_parallel_calls_keep_distinct_audits(self):
        with tempfile.TemporaryDirectory() as folder:
            evaluator = FlexMetric(BUNDLE, "unused", lambda p: answer(True), folder, lambda a, b: 1)
            result = {"error": None, "gold_rows": [(1,)], "predicted_rows": [(1,)], "scorer_ms": 1}
            with patch("rhesis_flex_metrics.psycopg.connect"), patch("rhesis_flex_metrics.score_case", return_value=result):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    values = list(pool.map(lambda _: evaluator.evaluate("gold", self.case["question"], "SELECT 1", reference(self.case, "gold")), range(8)))
            self.assertEqual(len(list(Path(folder).glob("*.json"))), 8)
            self.assertTrue(all(v["score"] == 1 for v in values))

    def test_provider_receives_frozen_parameters_and_no_automatic_retry(self):
        config = json.loads((BUNDLE / "manifest.json").read_text())["judge"]
        calls = []
        def handle(request):
            calls.append(json.loads(request.content))
            return httpx.Response(429, json={"error": {"message": "rate limited"}})
        client = JudgeClient(config, "test-only")
        client.client.close()
        client.client = httpx.Client(base_url="https://example.test/", transport=httpx.MockTransport(handle))
        with self.assertRaises(httpx.HTTPStatusError):
            client({"system": "rules", "user": "question"})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["reasoning_effort"], config["reasoning_effort"])
        self.assertEqual(calls[0]["messages"][0]["content"], "rules")


if __name__ == "__main__":
    unittest.main()
