# FLEX-based Rhesis evaluation: expected_response required

This bundle records three new UI-launched Fresh Outputs runs. Each uses the same thirty BIRD questions, its own expected_response reference variant and one assigned GLM-5.3 LLM judge. SQL generation remains question-only, with no SQL Pair Knowledge.

## Required references

- Evidence-only parses the current testcase expected_response.evidence. Empty/whitespace evidence raises an evaluation error before SQL scoring or an LLM request. Original empty values in 1507/1528 are preserved.
- Gold-only parses the current expected_response.gold_sql. It must be nonempty; no evidence is supplied.
- Combined parses both expected_response fields. Gold SQL must be nonempty; source evidence may be empty.
- Schema, question and execution results provide context. Judge-visible answer/business references come only from the validated expected_response, never from private manifest substitution. Private Gold selects the Evidence-only branch but is not sent to that judge.

The user-required input prerequisite and reference wording are explicit adaptations to pinned FLEX. Business correctness criteria retain the upstream source; see postgresql-prompt.diff for all six system/user adaptations. No invented answer, numerical tolerance, alternate judge or silent retry is used.

## New runs

| Variant | Run | Native outcomes |
| --- | --- | --- |
| evidence | [refined-manta](http://localhost:3002/test-runs/2a8c44ee-49c8-4bb0-90ba-be034d59f88a?density=detail) | {"Pass": 16, "Fail": 11, "Evaluation error": 3} |
| gold | [crystal-yak](http://localhost:3002/test-runs/ddc1e3f8-fbd6-4cbc-a179-c7e3dd2bfb94?density=detail) | {"Pass": 12, "Fail": 16, "Evaluation error": 2} |
| combined | [fearless-gerbil](http://localhost:3002/test-runs/9ceb9564-b30d-41a5-87ce-e35b6c14ee41?density=detail) | {"Pass": 8, "Evaluation error": 8, "SQL execution error": 1, "Fail": 13} |

All 90 native results are retained. There are 76 accepted native LLM verdicts, two missing-reference errors, three invalid final JSON replies, three judge-provider HTTP 429 errors, five native scoring-call timeouts and one rejected non-SQL API output. Late model replies after native timeouts remain diagnostic; they are not promoted to scores. Native error scores of zero do not become valid semantic Fail verdicts.

Question 1528 now has no Evidence-only judgment, Gold-only Pass, and combined Fail. The combined actual SQL calculates transaction-amount share rather than the supplied Gold's station-count share. The three fresh outputs may differ; score differences do not isolate the causal effect of the reference type.

## Review files

- metric-definitions.json and ui/judge-*-binding.png: actual registered definitions and Test Set bindings.
- prompt-templates/{evidence,gold,combined}.md: complete system/user templates for both execution branches.
- judge-prompts/: complete actual prompts for all 87 attempted judge requests, including failed/late ones. No prompt is fabricated for 1507/1528 Evidence-only or for the rejected non-SQL output.
- ui-run-metric-audits/: all ninety scoring audits, including reference prerequisites, SQL results, full requests/replies and errors.
- runs/*/: native run/result JSON, native CSV exports, joined records and thirty question-only API/trace/empty-knowledge proofs per variant.
- comparison.json / comparison.csv: the new ninety outcomes and per-question reference, SQL and model reply.
- manifest.json, pre/post-run-verification.json, reference-contract-verification.json, history-verification.json and design-review.md: frozen inputs, data/config checks, actual call counts and review limitations.
- upstream/: unmodified FLEX revision 270abdba59306134adf0928b2ce92acb8fbd94eb and license. FLEX-NAACL-2025.pdf and paper-source.json retain paper provenance.

The original runs remain separately available in ../rhesis-flex and their native IDs. Their ninety outputs, scores and errors were read back and confirmed unchanged. The existing BIRD official execution score is also historical, not a score for these new FLEX generations.

## Run the three hosted judges

The included source hosts scoring only. Use the recorded dependencies in runtime-versions.json. Supply private credentials outside this bundle; do not publish API keys or the scorer connection string.

```bash
RHESIS_ENVIRONMENT=local python rhesis_flex_metrics.py \
  --bundle . \
  --scorer-env /path/to/private-scorer.env \
  --opencode-config /path/to/private-model-profile.json \
  --token-file /path/to/private-rhesis-token.txt \
  --audit-dir /path/to/new-run-audits \
  --ex-evaluator evaluation_ex.py \
  --ex-sha256 da1bbcd4530be83692d7c650c814ea9704bb710d0c953eb75d02ccb38233cf89 \
  --rhesis-url http://localhost:8080 \
  --rhesis-project 8aa58678-d952-469f-af75-afefce0176a6
```

This command registers exactly three scoring functions. Launch each Test Set through Rhesis UI: existing NL2SQL REST Endpoint, Fresh Outputs, Parallel, Test Set Metrics. Each CSV testcase retains one expected_response. Company deployments must freeze their actual schema/data, endpoint, project and model configuration rather than reuse local identities as proof.

## Verification and limits

The repository boundary tests cover reference tampering/missing fields/blank content, all three reference projections and both branches, actual reference propagation, Gold visibility, no database/LLM call on missing evidence, strict reply parsing, provider failure without retry and concurrent audit preservation. Twelve tests pass; contract-tests.txt contains the full output.

All actual prompts were reconstructed from current expected_response and pinned criteria and compared exactly. Runtime/data fingerprints and all ninety question-only/empty-knowledge proofs were verified. No Rhesis, NL2SQL, Snapshot or business-data implementation was changed.

Reference presence does not prove model reasoning quality. Evidence-only 1473 passes despite the explicit division-by-12 reference formula, and Gold-only 1521 passes a missing CZE condition because the current count matches. These are recorded review concerns, not human-approved answers. No human business labels were collected. FLEX's published expert-agreement score does not validate this adapted GLM setup.
