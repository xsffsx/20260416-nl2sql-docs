---
sidebar_position: 3
title: QA Smoke
---

# QA Smoke

QA Smoke executes real project-scoped `nl2sql` and `ask` MCP calls. It records both call results, duration, trace identifiers, and the agreed result value.

```bash
curl -sS -X POST \
  'http://127.0.0.1:4000/api/config/runtime-readiness/qa-smoke?projectId=equity' | jq .
```

Interpretation:

- `ready`: the project completed both real tool calls.
- `blocked`: a Runtime Readiness precondition is not satisfied.
- `failed`: a real MCP call failed or timed out.

The startup gate runs this check for every registered project. A successful explicit recheck updates the canonical startup status.
