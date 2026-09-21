---
sidebar_position: 1
title: Health and Readiness APIs
---

# Health and Readiness APIs

## Process health

```http
GET /api/health
```

Returns a lightweight process/listener health response. It must remain cheap and must not execute QA Smoke.

## Aggregate startup readiness

```http
GET /api/config/startup-readiness
```

Returns the aggregate phase, grace deadline, per-project readiness, QA Smoke result, and blocker evidence.

## Project runtime readiness

```http
GET /api/config/runtime-readiness?projectId=equity
```

Returns the detailed checks for system database, business database, vector capability, providers, artifact proof, schema RAG, and observability.
