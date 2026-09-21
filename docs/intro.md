---
sidebar_position: 1
slug: /
---

# Knowledge-grounded NL2SQL

NL2SQL turns a business question into SQL by combining runtime schema evidence, semantic knowledge, few-shot examples, LLM generation, and validation.

## Start here

- [Getting Started](/docs/getting-started/overview) — understand the system and run the first query.
- [Architecture](/docs/architecture/langgraph-pipeline) — follow the end-to-end execution path.
- [Runtime Operations](/docs/runtime/startup-grace) — operate startup, readiness, QA Smoke, and snapshots.
- [API Reference](/docs/api/health-readiness) — inspect the health and readiness contracts.

## The core contract

```text
Business question
      ↓
Schema + semantic knowledge + few-shot evidence
      ↓
Generated SQL
      ↓
Validation and retry
      ↓
Verified answer with provenance
```
