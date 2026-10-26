"""A manually written SDK entry point using the archived FLEX scoring engine."""

import json
import os
from pathlib import Path

from dotenv import dotenv_values
from rhesis.sdk import RhesisClient, metric

from rhesis_bird_metrics import official_ex
from rhesis_flex_metrics import FlexMetric, JudgeClient


bundle = Path(os.environ["FLEX_BUNDLE"]).resolve()
manifest = json.loads((bundle / "manifest.json").read_text())
checksums = json.loads((bundle / "checksums.json").read_text())
audit_dir = Path(os.environ["FLEX_AUDIT_DIR"]).resolve()
audit_dir.mkdir(parents=True, exist_ok=False)
prefix = os.environ["FLEX_METRIC_PREFIX"].strip()
if not prefix:
    raise ValueError("FLEX_METRIC_PREFIX must be nonempty")

judge_key = Path(os.environ["JUDGE_API_KEY_FILE"]).read_text().strip()
scorer_dsn = dotenv_values(os.environ["FLEX_SCORER_ENV"])["BIRD_SCORER_DSN"]
evaluator = FlexMetric(
    bundle=bundle,
    dsn=scorer_dsn,
    judge=JudgeClient(manifest["judge"], judge_key),
    audit_dir=audit_dir,
    calculate_ex=official_ex(bundle / "evaluation_ex.py", checksums["evaluation_ex.py"]),
)
client = RhesisClient(
    api_key=Path(os.environ["RHESIS_TOKEN_FILE"]).read_text().strip(),
    base_url=os.environ["RHESIS_BASE_URL"],
    project_id=os.environ["RHESIS_PROJECT_ID"],
)


@metric(name=f"{prefix} / FLEX Evidence Only", score_type="binary")
def evidence(input: str, output: str, expected_output: str) -> dict:
    return evaluator.evaluate("evidence", input, output, expected_output)


@metric(name=f"{prefix} / FLEX Gold SQL Only", score_type="binary")
def gold(input: str, output: str, expected_output: str) -> dict:
    return evaluator.evaluate("gold", input, output, expected_output)


@metric(name=f"{prefix} / FLEX Evidence and Gold SQL", score_type="binary")
def combined(input: str, output: str, expected_output: str) -> dict:
    return evaluator.evaluate("combined", input, output, expected_output)


if __name__ == "__main__":
    client.connect()
