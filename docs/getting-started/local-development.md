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

The documentation site is independent from the application runtime. The private repository's `docs-site/` is the only editable source. The local `20260416-nl2sql-docs` path is a symlink to that same working tree; its independent public Git metadata is stored beside the private repository, not inside the shared files.

Run these commands from the private repository root:

```bash
./script/docs-publish.sh check
git status --short -- docs-site
git -C "$(pwd)/20260416-nl2sql-docs" \
  --git-dir="$(pwd)/../20260416-nl2sql-docs.git" \
  --work-tree="$(pwd)/20260416-nl2sql-docs" status --short
```

For local documentation work, edit only `docs-site/` and use its normal commands:

```bash
cd docs-site
npm ci
npm run start
npm run build
```

Publish the same working tree through the two independent Git repositories with one explicit command:

```bash
cd ..
./script/docs-publish.sh publish "docs: describe the documentation change"
```

The command verifies the shared tree, pushes the private repository, pushes public `main`, builds the site, deploys public `gh-pages`, and verifies the public URL. It stops at the first failed stage; it does not reconcile a second source tree or reuse either repository's Git metadata.

To tear down the local sharing layout, stop publication first, remove the `20260416-nl2sql-docs` symlink, restore the public working tree from the migration backup, and move the sidecar `20260416-nl2sql-docs.git` metadata back into the restored public repository. Do not delete either Git metadata store while the shared path is active.

In GitHub repository settings, set Pages to **Deploy from a branch**, select `gh-pages`, and select the repository root (`/`). The configured `url`, `baseUrl`, and deployment branch must match the public repository.

## Verify the runtime

```bash
curl -sS http://127.0.0.1:4000/api/health
curl -sS 'http://127.0.0.1:4000/api/config/startup-readiness' | jq .
```

:::warning
Do not use a successful HTTP process check as proof that a project can execute Ask/NL2SQL. Use the project Runtime Readiness and QA Smoke results.
:::
