---
sidebar_position: 1
title: LangGraph Pipeline
---

import useBaseUrl from '@docusaurus/useBaseUrl';

# LangGraph Pipeline

The graph coordinates intent, retrieval, schema linking, generation, validation, execution, and answer rendering. Each node receives typed state and emits traceable updates.

<img
  src={useBaseUrl('/img/architecture/nl2sql-knowledge-grounded.drawio.svg')}
  alt="Knowledge-grounded NL2SQL flow"
  width="100%"
/>

:::tip Diagram source and downloads

- [View or edit the source `.drawio` file in GitHub](https://github.com/xsffsx/20260416-nl2sql-docs/blob/main/docs/20260301_langgraph-nl2sql/nl2sql-knowledge-grounded.drawio)
- <a href={useBaseUrl('/img/architecture/nl2sql-knowledge-grounded.drawio.png')}>Download the PNG preview</a>

The SVG is the page preview; the `.drawio` file in `main` remains the editable source of truth.

:::

## Design boundary

- The active artifact snapshot owns prompt and knowledge identity.
- The runtime graph owns execution sequencing.
- MCP owns the external tool boundary.
- Langfuse/trace state owns observability evidence.
