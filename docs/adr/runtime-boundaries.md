---
sidebar_position: 2
title: Runtime Boundaries
---

# Runtime Boundaries

The runtime has one owner for each truth:

| Truth | Owner |
| --- | --- |
| Active prompt/knowledge package | Active artifact snapshot |
| Runtime execution sequence | LangGraph pipeline |
| External tool boundary | MCP proxy and project tool definitions |
| Startup operator state | Startup-readiness service |
| Process lifecycle | Kubernetes probes and non-zero exit |

Avoid fallback composition across draft, active, and partially materialized state. If a required boundary is missing, surface the blocker and fail the affected operation.
