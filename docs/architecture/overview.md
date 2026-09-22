---
sidebar_position: 1
title: Overview
---

import useBaseUrl from '@docusaurus/useBaseUrl';

# Overview

## What is NL2SQL?

Natural Language to SQL (NL2SQL), also known as Text-to-SQL, translates a user’s natural-language question into a SQL query over a relational database. A reliable system resolves ambiguity, links the question to the correct schema, and grounds generation with approved metadata and examples. To reduce hallucinations, it validates generated SQL against the schema, restricts execution to safe read-only operations, and keeps the generation and validation trace visible. These controls make errors detectable and traceable instead of silently guessing. [NL2SQL survey](https://arxiv.org/abs/2408.05109) · [Microsoft NL2SQL workflow](https://learn.microsoft.com/en-us/fabric/data-science/data-agent-sql-sources)

## From Chat Query to SQL

<a
  className="diagramZoomTrigger"
  href="#nl2sql-mcp-workflow-zoom"
  aria-label="Open the NL2SQL MCP workflow diagram"
>
  <img
    src={useBaseUrl('/img/architecture/nl2sql-mcp-workflow.drawio.svg')}
    alt="NL2SQL MCP workflow"
    width="100%"
  />
</a>

<div id="nl2sql-mcp-workflow-zoom" className="diagramZoom" role="dialog" aria-label="NL2SQL MCP workflow diagram">
  <a className="diagramZoom__backdrop" href="#" aria-label="Close enlarged diagram" />
  <img
    src={useBaseUrl('/img/architecture/nl2sql-mcp-workflow.drawio.svg')}
    alt="NL2SQL MCP workflow enlarged"
  />
  <a className="diagramZoom__close" href="#" aria-label="Close enlarged diagram">×</a>
</div>

<div className="workflowCaption" aria-label="NL2SQL MCP workflow summary">
  <div className="workflowCaption__eyebrow">Workflow at a glance</div>
  <p className="workflowCaption__lead">One conversational entry point. Three specialist paths.</p>
  <p className="workflowCaption__body">UI Chat sends each question to the Chat Agent, which orchestrates routing and aggregation across domain-specific MCPs.</p>
  <div className="workflowCaption__roles">
    <div className="workflowCaption__role"><strong>Chat Agent</strong><span>orchestration · routing · aggregation</span></div>
    <div className="workflowCaption__role"><strong>Equity MCP</strong><span><span className="workflowCaption__keyword">NL2SQL</span> · equity data</span></div>
    <div className="workflowCaption__role"><strong>News Insight MCP</strong><span>RAG · news context</span></div>
  </div>
</div>

## NL2SQL Pipeline Stage Contract

<a
  className="diagramZoomTrigger"
  href="#nl2sql-knowledge-grounded-zoom"
  aria-label="Open the knowledge-grounded NL2SQL flow diagram"
>
  <img
    src={useBaseUrl('/img/architecture/nl2sql-knowledge-grounded.drawio.svg')}
    alt="Knowledge-grounded NL2SQL flow"
    width="100%"
  />
</a>

<div id="nl2sql-knowledge-grounded-zoom" className="diagramZoom" role="dialog" aria-label="Knowledge-grounded NL2SQL flow diagram">
  <a className="diagramZoom__backdrop" href="#" aria-label="Close enlarged diagram" />
  <img
    src={useBaseUrl('/img/architecture/nl2sql-knowledge-grounded.drawio.svg')}
    alt="Knowledge-grounded NL2SQL flow enlarged"
  />
  <a className="diagramZoom__close" href="#" aria-label="Close enlarged diagram">×</a>
</div>

<div className="diagramSourceNote">
  [View or edit the source `.drawio` file in GitHub](https://github.com/xsffsx/20260416-nl2sql-docs/blob/main/docs/20260301_langgraph-nl2sql/nl2sql-knowledge-grounded.drawio) · <a href={useBaseUrl('/img/architecture/nl2sql-knowledge-grounded.drawio.png')}>Download the PNG preview</a> · SVG is the page preview; `.drawio` in `main` is the editable source of truth.
</div>

<div className="tableScroll pipelineContractTable" role="region" aria-label="NL2SQL pipeline stage table" tabIndex="0">

| Stage | Data flow | Remark |
| --- | --- | --- |
| Question | <span className="dataFlowValue"><span className="dataFlowValue__source">Natural-language question</span><span className="dataFlowValue__arrow" aria-hidden="true">→</span><span className="dataFlowValue__target">Structured intent</span></span> | **Ambiguity detection**<br />Normalize the question before schema lookup. Clarify missing constraints instead of guessing.<br /><br />**Question**<br /><code>Compare the equity geographic <span className="traceKeyword traceKeyword--allocation">allocations</span> between funds that invest in <span className="traceKeyword traceKeyword--asia">Asia developed markets</span> versus those focused on the <span className="traceKeyword traceKeyword--us">United States</span>.</code> |
| Knowledge (RAG) | <span className="dataFlowValue"><span className="dataFlowValue__source">Targeted schema metadata, semantic mappings, business rules, value hints, few-shot SQL</span><span className="dataFlowValue__arrow" aria-hidden="true">→</span><span className="dataFlowValue__target">Grounded context</span></span> | **Schema linking + value profiling**<br />Retrieve relevant tables and fields through reviewable mappings.<br /><br /><table className="knowledgeMappingTable"><thead><tr><th>Business term</th><th>Meaning</th><th>Source field</th></tr></thead><tbody><tr><td><code className="traceKeyword traceKeyword--asia">Asia Developed Markets</code></td><td>Developed Asian equity exposure</td><td><code className="traceKeyword traceKeyword--asia">fund_master_view.equity_geographic_allocation_in_asia_developed</code></td></tr><tr><td><code className="traceKeyword traceKeyword--us">United States</code></td><td>US equity exposure</td><td><code className="traceKeyword traceKeyword--us">fund_master_view.equity_geographic_allocation_in_united_states</code></td></tr></tbody></table><br />**Few-shot examples**<br /><code>Which funds have the highest <span className="traceKeyword traceKeyword--us">US</span> <span className="traceKeyword traceKeyword--allocation">allocation</span>?</code><br />→ `Few-shot SQL`<br /><br /><code>Find funds active in the <span className="traceKeyword traceKeyword--us">US</span> or <span className="traceKeyword traceKeyword--asia">Asia</span>.</code><br />→ `Few-shot SQL`<br /><br /><code>Compare <span className="traceKeyword traceKeyword--asia">Asia</span></code><br />→ <code>SELECT fund_code, fund_full_name AS name,</code><br /><code><span className="traceKeyword traceKeyword--asia">equity_geographic_allocation_in_asia_developed</span>,</code><br /><code><span className="traceKeyword traceKeyword--us">equity_geographic_allocation_in_united_states</span></code><br /><code>FROM fund_master_view</code><br /><code>WHERE <span className="traceKeyword traceKeyword--asia">equity_geographic_allocation_in_asia_developed</span> &gt; 0;</code> |
| Generate SQL (LLM) | <span className="dataFlowValue"><span className="dataFlowValue__source">Structured intent and grounded context</span><span className="dataFlowValue__arrow" aria-hidden="true">→</span><span className="dataFlowValue__target">Candidate SQL + generation summary</span></span> | **Generation trace**<br />Use selected tables and fields, dialect rules, canonical joins, safe limits, and no `SELECT *`.<br /><br />**Generated SQL — Attempt 1**<br /><code>SELECT fund_code, fund_full_name AS fund_name, <span className="traceKeyword traceKeyword--asia">equity_geographic_allocation_in_asia_developed</span>, <span className="traceKeyword traceKeyword--us">equity_geographic_allocation_in_united_states</span> FROM fund_master_view WHERE <span className="traceKeyword traceKeyword--asia">equity_geographic_allocation_in_asia_developed</span> &gt; 0 ...</code> |
| Validate / Retry | <span className="dataFlowValue"><span className="dataFlowValue__source">Candidate SQL, schema contract, dialect rules, validator/dry-plan feedback</span><span className="dataFlowValue__arrow" aria-hidden="true">→</span><span className="dataFlowValue__target">Validated SQL or actionable error</span></span> | **Retry and repair**<br />Check syntax, references, joins, grain, permissions, and read-only constraints before execution. Retry only actionable errors with a bounded budget.<br /><br />**Validation feedback**<br />`invalid: SQL syntax error`<br />`invalid: UNION / ORDER BY clause` |
| Final SQL | <span className="dataFlowValue"><span className="dataFlowValue__source">Validated SQL, trace, policy checks, execution limits</span><span className="dataFlowValue__arrow" aria-hidden="true">→</span><span className="dataFlowValue__target">SQL, rows/answer, provenance, trace</span></span> | **Execution safety + Eval**<br />Execute through a governed read-only connector with timeout/row limits and retain evidence for Golden NL-SQL regression checks.<br /><br />**Validated SQL**<br /><code>SELECT fund_code,</code><br /><code>       fund_full_name AS fund_name,</code><br /><code>       <span className="traceKeyword traceKeyword--asia">equity_geographic_allocation_in_asia_developed</span>,</code><br /><code>       <span className="traceKeyword traceKeyword--us">equity_geographic_allocation_in_united_states</span></code><br /><code>FROM fund_master_view</code><br /><code>WHERE <span className="traceKeyword traceKeyword--asia">equity_geographic_allocation_in_asia_developed</span> &gt; 0;</code> |

</div>

<div className="tableScrollHint">On narrow screens, swipe horizontally inside the table to view all columns.</div>

### Best-practice basis

- [LangGraph SQL agent tutorial](https://langchain-ai.github.io/langgraph/tutorials/sql-agent/): list tables → select relevant tables → inspect schema → generate SQL → check before execution → execute → correct actionable errors → answer.
- [Wren correctness architecture](https://docs.getwren.ai/oss/concepts/correctness): targeted retrieval, plan/validate before database access, governed connectors, and bounded correction.
- [Wren Architecture — Correctness is a system](https://docs.getwren.ai/oss/reference/architecture#correctness-is-a-system): ambiguity detection, value profiling, generation trace, retry/repair, and evaluation as explicit correctness primitives.
- [Wren memory system](https://docs.getwren.ai/oss/concepts/memory_system): retrieve relevant context and proven NL-SQL pairs before generation; store confirmed pairs after successful execution.
- [Schema linking research](https://aclanthology.org/2020.emnlp-main.564/): identify the subset of schema needed for the question instead of treating the whole database schema as equivalent context.
