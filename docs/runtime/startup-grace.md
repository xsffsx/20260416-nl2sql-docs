---
sidebar_position: 1
title: Startup Grace
---

# Startup Grace

The default startup policy is a bounded operator recovery window:

```env
STARTUP_FAIL_FAST=grace
STARTUP_FAIL_FAST_GRACE_SECONDS=600
```

```text
Process listens
    ↓
Dependency checks + final QA Smoke for every project
    ├── all ready → phase=ready
    └── blocker → phase=grace, HTTP 200
                    ├── Dashboard/publish available
                    ├── Ask/NL2SQL remains readiness-gated
                    └── deadline → non-zero exit → Kubernetes restart
```

The existing startup-readiness API is the canonical operator status. Auto-import is diagnostic input; final project QA Smoke is the completion gate.

## K8s probe split

```yaml
livenessProbe:
  httpGet: { path: /api/health, port: http }
startupProbe:
  httpGet: { path: /api/health, port: http }
readinessProbe:
  httpGet: { path: /api/config/startup-readiness, port: http }
```

See the [startup troubleshooting guide](/docs/troubleshooting/startup-blocked) for lifecycle logs and port-forward commands.
