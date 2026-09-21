---
sidebar_position: 2
title: Local Development
---

# Local Development

The repository contains separate backend and frontend development commands. Use the repository scripts and the environment examples instead of inventing local runtime values.

## Backend

```bash
cd src/backend_py
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 4000
```

## Frontend

```bash
cd src/frontend
npm ci
npm run dev:python
```

## Documentation site

The documentation site is independent from the application runtime and is published manually to the configured `gh-pages` branch.

```bash
cd docs-site
npm ci
npm run start
npm run build
npm run deploy
```

In GitHub repository settings, set Pages to **Deploy from a branch**, select `gh-pages`, and select the repository root (`/`). The configured `url`, `baseUrl`, and deployment branch must match the repository before the first publish.

## Verify the runtime

```bash
curl -sS http://127.0.0.1:4000/api/health
curl -sS 'http://127.0.0.1:4000/api/config/startup-readiness' | jq .
```

:::warning
Do not use a successful HTTP process check as proof that a project can execute Ask/NL2SQL. Use the project Runtime Readiness and QA Smoke results.
:::
