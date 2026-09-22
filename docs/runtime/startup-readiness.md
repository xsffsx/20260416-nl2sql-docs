---
sidebar_position: 1
title: Startup Readiness
---

# Startup Readiness

The backend exposes one startup decision through `GET /api/config/startup-readiness`:

```http
GET /api/config/startup-readiness
```

```text
Global Runtime Checks: System DB + LLM + Embedding
    ↓
Project QA Smoke: one result per configured project
    ↓
Startup Decision: fast-fail | continue
    ↓
Lifecycle: pending | ready | grace | blocked
```

`fast-fail` is returned when a global System DB, LLM, or Embedding check fails, or when a project with `IMPORT_DIR` enabled has an executed QA Smoke failure or timeout. The backend lifecycle is configured with:

```env
STARTUP_FAIL_FAST=grace|system
STARTUP_FAIL_FAST_GRACE_SECONDS=600
```

In `grace` mode, the Dashboard remains available until the deadline; unresolved blockers then make the backend exit non-zero. In `system` mode, the Dashboard remains available indefinitely while affected NL2SQL execution is blocked.

## Probe split

```yaml
livenessProbe:
  httpGet: { path: /api/health, port: http }
startupProbe:
  httpGet: { path: /api/health, port: http }
readinessProbe:
  httpGet: { path: /api/config/startup-readiness, port: http }
```

The API is the single operator-readable contract. It uses `pending`, `ready`, `grace`, and `blocked`; it does not expose `running`, `degraded`, or `expired` phases.

Use the [startup troubleshooting guide](/docs/troubleshooting/startup-blocked) for lifecycle logs and API checks.
