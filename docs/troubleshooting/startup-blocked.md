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
- `startupDecision=continue`: the backend is serving; repair the project diagnostic through the UI and publish path.
- `startupDecision=fast-fail`: inspect the global dependency or imported-project QA failure in the final startup checklist.
- Process exited non-zero: inspect the final startup checklist and Kubernetes restart count.

:::tip
The Dashboard and publish APIs remain available for non-fatal project setup diagnostics. Normal Ask/NL2SQL execution remains protected by Runtime Readiness.
:::
