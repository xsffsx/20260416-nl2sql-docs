---
sidebar_position: 1
title: Overview
---

import useBaseUrl from '@docusaurus/useBaseUrl';

# Overview

The graph coordinates intent, retrieval, schema linking, generation, validation, execution, and answer rendering. Each node receives typed state and emits traceable updates.

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

## NL2SQL Pipeline Stage Contract

<div className="tableScroll pipelineContractTable" role="region" aria-label="NL2SQL pipeline stage table" tabIndex="0">

| Stage | Data flow | Remark |
| --- | --- | --- |
| Question | Natural-language question → Structured intent | **Ambiguity detection**<br />Normalize the question before schema lookup. Clarify missing constraints instead of guessing.<br /><br />**Question**<br />`Compare the equity geographic allocations between funds that invest in Asia developed markets versus those focused on the United States.` |
| Knowledge (RAG) | Targeted schema metadata, semantic mappings, business rules, value hints, few-shot SQL → Grounded context | **Schema linking + value profiling**<br />Retrieve relevant tables and fields through reviewable mappings.<br /><br /><table className="knowledgeMappingTable"><thead><tr><th>Business term</th><th>Meaning</th><th>Source field</th></tr></thead><tbody><tr><td><code>Asia Developed Markets</code></td><td>Developed Asian equity exposure</td><td><code>fund_master_view.equity_geographic_allocation_in_asia_developed</code></td></tr><tr><td><code>United States</code></td><td>US equity exposure</td><td><code>fund_master_view.equity_geographic_allocation_in_united_states</code></td></tr></tbody></table><br />**Few-shot examples**<br />`Which funds have the highest US allocation?`<br />→ `Few-shot SQL`<br /><br />`Find funds active in the US or Asia.`<br />→ `Few-shot SQL`<br /><br />`Compare Asia`<br />→ `SELECT fund_code, fund_full_name AS name,`<br />`equity_geographic_allocation_in_asia_developed,`<br />`equity_geographic_allocation_in_united_states`<br />`FROM fund_master_view`<br />`WHERE equity_geographic_allocation_in_asia_developed > 0;` |
| Generate SQL (LLM) | Structured intent and grounded context → Candidate SQL plus generation summary | **Generation trace**<br />Use selected tables and fields, dialect rules, canonical joins, safe limits, and no `SELECT *`.<br /><br />**Generated SQL — Attempt 1**<br />`SELECT fund_code, fund_full_name AS fund_name, equity_geographic_allocation_in_asia_developed, equity_geographic_allocation_in_united_states FROM fund_master_view WHERE equity_geographic_allocation_in_asia_developed > 0 ...` |
| Validate / Retry | Candidate SQL, schema contract, dialect rules, validator/dry-plan feedback → Validated SQL or actionable error | **Retry and repair**<br />Check syntax, references, joins, grain, permissions, and read-only constraints before execution. Retry only actionable errors with a bounded budget.<br /><br />**Validation feedback**<br />`invalid: SQL syntax error`<br />`invalid: UNION / ORDER BY clause` |
| Final SQL | Validated SQL, trace, policy checks, execution limits → SQL, rows/answer, provenance, trace | **Execution safety + Eval**<br />Execute through a governed read-only connector with timeout/row limits and retain evidence for Golden NL-SQL regression checks.<br /><br />**Validated SQL**<br />`SELECT fund_code,`<br />`       fund_full_name AS fund_name,`<br />`       equity_geographic_allocation_in_asia_developed,`<br />`       equity_geographic_allocation_in_united_states`<br />`FROM fund_master_view`<br />`WHERE equity_geographic_allocation_in_asia_developed > 0;` |

</div>

<div className="tableScrollHint">On narrow screens, swipe horizontally inside the table to view all columns.</div>

### Detailed stage view

<div className="tableScroll" role="region" aria-label="NL2SQL detailed stage table" tabIndex="0">

| Stage | Diagram detail | Review question |
| --- | --- | --- |
| Question | Business user question | Did the system preserve the user’s actual analytical intent? |
| Knowledge (RAG) | Schema Metadata, Business Knowledge Base, Few-shot Evidence | Did retrieval provide the right schema, business meaning, and examples? |
| Generate SQL (LLM) | Generated SQL from the retrieved context | Which requested fields, filters, joins, and aggregations were selected? |
| SQL Validate | Syntax and structural checks, including invalid SQL and invalid clause combinations | Is the generated SQL valid before it reaches the database? |
| Retry | Return validation feedback to the generation step | Was the correction bounded, visible, and based on the validation error? |
| Validated SQL | Final SQL ready for execution or review | Can a reviewer trace the final SQL back to its context and validation evidence? |

</div>

<div className="tableScrollHint">On narrow screens, swipe horizontally inside the table to view all columns.</div>

### Best-practice basis

- [LangGraph SQL agent tutorial](https://langchain-ai.github.io/langgraph/tutorials/sql-agent/): list tables → select relevant tables → inspect schema → generate SQL → check before execution → execute → correct actionable errors → answer.
- [Wren correctness architecture](https://docs.getwren.ai/oss/concepts/correctness): targeted retrieval, plan/validate before database access, governed connectors, and bounded correction.
- [Wren Architecture — Correctness is a system](https://docs.getwren.ai/oss/reference/architecture#correctness-is-a-system): ambiguity detection, value profiling, generation trace, retry/repair, and evaluation as explicit correctness primitives.
- [Wren memory system](https://docs.getwren.ai/oss/concepts/memory_system): retrieve relevant context and proven NL-SQL pairs before generation; store confirmed pairs after successful execution.
- [Schema linking research](https://aclanthology.org/2020.emnlp-main.564/): identify the subset of schema needed for the question instead of treating the whole database schema as equivalent context.
