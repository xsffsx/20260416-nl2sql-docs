---
sidebar_position: 1
title: LangGraph Pipeline
---

# LangGraph Pipeline

The graph coordinates intent, retrieval, schema linking, generation, validation, execution, and answer rendering. Each node receives typed state and emits traceable updates.

![Knowledge-grounded NL2SQL flow](pathname:///img/architecture/nl2sql-knowledge-grounded.drawio.svg)

:::tip Diagram source and downloads

- [View or edit the source `.drawio` file in GitHub](https://github.com/xsffsx/20260416-nl2sql-docs/blob/main/docs/20260301_langgraph-nl2sql/nl2sql-knowledge-grounded.drawio)
- [Download the PNG preview](pathname:///img/architecture/nl2sql-knowledge-grounded.drawio.png)

The SVG is the page preview; the `.drawio` file in `main` remains the editable source of truth.

:::

## Design boundary

- The active artifact snapshot owns prompt and knowledge identity.
- The runtime graph owns execution sequencing.
- MCP owns the external tool boundary.
- Langfuse/trace state owns observability evidence.
