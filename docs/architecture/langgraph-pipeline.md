---
sidebar_position: 1
title: LangGraph Pipeline
---

# LangGraph Pipeline

The graph coordinates intent, retrieval, schema linking, generation, validation, execution, and answer rendering. Each node receives typed state and emits traceable updates.

![Knowledge-grounded NL2SQL flow](pathname:///img/architecture/nl2sql-knowledge-grounded.drawio.svg)

The diagram source remains editable in the repository at `docs/20260301_langgraph-nl2sql/nl2sql-knowledge-grounded.drawio`.

## Design boundary

- The active artifact snapshot owns prompt and knowledge identity.
- The runtime graph owns execution sequencing.
- MCP owns the external tool boundary.
- Langfuse/trace state owns observability evidence.
