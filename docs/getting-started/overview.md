---
sidebar_position: 1
title: Overview
---

# Overview

This project provides a knowledge-grounded NL2SQL runtime for project-scoped data sources. The active artifact snapshot is the versioned runtime boundary for prompts, knowledge, SQL examples, instructions, schema materialization, and runtime policies.

## Main components

| Component | Responsibility |
| --- | --- |
| React/Vite frontend | Dashboard, modeling, artifact review, QA, and Copilot Ask UI |
| FastAPI backend | Runtime APIs, LangGraph execution, MCP, readiness, and artifact lifecycle |
| Control-plane PostgreSQL | Artifact metadata, runtime bindings, QA history, and observability state |
| Query-side PostgreSQL | Business tables and views queried by generated SQL |
| LLM/embedding providers | SQL reasoning, answer generation, and retrieval embeddings |

## First reading path

1. Read the [NL2SQL pipeline](../concepts/nl2sql-pipeline).
2. Review [RAG and few-shot evidence](../concepts/rag-few-shot).
3. Run the local stack using [Local Development](./local-development).
4. Use the [Runtime Readiness API](../api/health-readiness) before debugging a query.
