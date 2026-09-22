---
sidebar_position: 1
title: Why WDV NL2SQL?
---

# Why WDV NL2SQL?

WDV NL2SQL is a governed query runtime for fund and equity data. It gives chat and agent clients a shared, versioned context, then turns natural-language questions into SQL, data, answers, and traceable execution evidence.

## The problem WDV solves

An LLM can write plausible SQL, but raw schemas rarely contain canonical business definitions, join intent, value meanings, or the active model version. WDV connects the chat experience to artifact-backed context, retrieval, validation, read-only execution, and MCP access.

## How WDV compares

|  | A raw LLM query | CLI Agents (OpenCode / Claude) | WrenAI | WDV NL2SQL |
| --- | --- | --- | --- | --- |
| 🧠 Writes or supports SQL | ⚠️ often ungoverned | ✅ through connected tools | ✅ governed | ✅ governed runtime |
| 📚 Knows business definitions | ❌ | ⚠️ depends on prompts, files, and tools | ✅ context + non-schema knowledge | ✅ artifacts + metadata + SQL pairs |
| 📊 Generates and deploys dashboards | ❌ | ❌ | ✅ agent-driven | ❌ |
| 🔌 Works through agents | ⚠️ depends on tooling | ✅ native CLI agent workflow | ✅ MCP + agent integrations | ✅ application API + MCP |
| 🗂️ Open, reviewable context | ❌ prompt-bound | ✅ project files and configuration | ✅ versionable context + knowledge | ✅ versioned artifacts + snapshot JSON file |
| 🔒 Governed execution | ❌ external or absent | ⚠️ depends on tools and environment | ✅ planning + connectors + controls | ✅ EXPLAIN + correction + read-only + row limits |
| ⚙️ Deployment · maintenance · architecture | 🟢 LLM API + database/tool connector | 🟡 OpenCode/Claude CLI + MCP/tools + project files | 🔴 Next.js/TypeScript UI + Apollo GraphQL · Python/FastAPI AI Service + Haystack/LiteLLM/Qdrant · Rust/DataFusion Core + PyO3 · MDL semantic modeling | 🟡 React/Vite frontend + LangGraph/Python backend |

A few distinctions are worth making precisely:

- **Compared with a raw LLM query:** WDV supplies an active, reviewable context and validates the generated SQL before execution.
- **Compared with CLI agents such as OpenCode or Claude:** CLI agents provide a flexible interaction surface; WDV adds a project-scoped artifact, retrieval, validation, execution, and provenance boundary.
- **Compared with WrenAI:** WrenAI provides a broader agentic GenBI surface; WDV focuses on governed SQL generation, execution evidence, and integration.

## WDV is for you if…

- you want users to ask business questions through chat or an agent;
- SQL generation must be tied to an active artifact with a **snapshot available** and project context;
- reviewers need to inspect SQL, rows, validation, provenance, and trace;
- the same query capability must be exposed through an application and MCP.

## Skip WDV if…

- you only need a one-off SQL experiment against a familiar database;
- your main requirement is an existing BI or semantic-serving platform rather than an application-owned NL2SQL runtime.

## Where to go next

- [From Chat Query to SQL](/docs/architecture/overview#from-chat-query-to-sql)
- [NL2SQL Pipeline](/docs/concepts/nl2sql-pipeline)
- [MCP Integration](/docs/architecture/mcp-integration)
- [Runtime Operations](/docs/runtime/startup-readiness)
- [Why Wren?](https://docs.getwren.ai/oss/concepts/why_wren)
- [Cube: Semantic Layer for AI Agents](https://cube.dev/articles/semantic-layer-for-ai-agents-2026)
