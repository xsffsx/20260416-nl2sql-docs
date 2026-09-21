---
sidebar_position: 1
title: Startup Blocked
---

# Startup Blocked

Start with the aggregate startup status:

```bash
curl -sS http://127.0.0.1:4000/api/config/startup-readiness | jq .
```

Then inspect the first project blocker:

```bash
curl -sS 'http://127.0.0.1:4000/api/config/runtime-readiness?projectId=equity' | jq '.checks[] | select(.status == "blocked")'
```

Common paths:

- No active snapshot: publish or activate the required artifact.
- Schema RAG blocked: repair the active snapshot or embedding/materialization dependency.
- QA Smoke failed: inspect the per-call MCP details and retry after repair.
- `phase=grace`: use the Dashboard and publish path before `graceDeadlineAt`.
- Process exited non-zero: inspect the final startup checklist and Kubernetes restart count.

:::tip
The Dashboard and publish APIs remain the recovery surface during the grace window. Normal Ask/NL2SQL execution remains protected by Runtime Readiness.
:::
