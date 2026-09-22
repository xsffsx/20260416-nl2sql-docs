---
sidebar_position: 2
title: Readiness and Liveness
---

# Readiness and Liveness

| Probe | Meaning | Failure behavior |
| --- | --- | --- |
| `/api/health` | Process and HTTP listener are alive | Kubernetes may restart the Pod |
| `/api/config/startup-readiness` | Canonical aggregate startup decision and project QA state | Consumers read `startupDecision`; `pending` means checks are still in progress; `grace` and `blocked` keep the Dashboard available |
| `/api/config/runtime-readiness?projectId=...` | Detailed dependency state | Ask/NL2SQL remains blocked when required checks fail |

Readiness is not a replacement for liveness. A Pod can be alive while a non-fatal project is being edited or published. Global failures and imported-project QA failures produce `startupDecision=fast-fail`; the configured `STARTUP_FAIL_FAST=grace|system` policy determines whether the API reports `grace` or `blocked` while serving.
