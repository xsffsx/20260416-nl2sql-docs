---
sidebar_position: 2
title: Readiness and Liveness
---

# Readiness and Liveness

| Probe | Meaning | Failure behavior |
| --- | --- | --- |
| `/api/health` | Process and HTTP listener are alive | Kubernetes may restart the Pod |
| `/api/config/startup-readiness` | Aggregate startup and project QA state | During grace it stays HTTP 200 so operator traffic remains routable |
| `/api/config/runtime-readiness?projectId=...` | Detailed dependency state | Ask/NL2SQL remains blocked when required checks fail |

Readiness is not a replacement for liveness. A Pod can be alive and intentionally in `phase=grace` while an operator repairs a snapshot or provider dependency.
