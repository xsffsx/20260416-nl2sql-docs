---
sidebar_position: 1
slug: /
title: Knowledge-grounded NL2SQL
hide_title: true
hide_breadcrumbs: true
hide_table_of_contents: true
---

import Link from '@docusaurus/Link';

<div className="docsLanding">
  <div className="docsLanding__eyebrow">Getting Started</div>
  <h1>Knowledge-grounded NL2SQL</h1>
  <p className="docsLanding__lead">
    The open-source natural-language SQL runtime for turning business questions into verified answers.
  </p>

  <p>
    NL2SQL combines runtime schema evidence, semantic knowledge, few-shot examples, LLM generation, and validation in one observable workflow.
  </p>

  <div className="docsLanding__cards">
    <Link className="docsLanding__card" to="/docs/getting-started/overview">
      <span className="docsLanding__icon" aria-hidden="true">↗</span>
      <h2>Quick Start</h2>
      <p>Run the first knowledge-grounded query locally.</p>
    </Link>
    <Link className="docsLanding__card" to="/docs/architecture/langgraph-pipeline">
      <span className="docsLanding__icon" aria-hidden="true">▣</span>
      <h2>Architecture</h2>
      <p>Follow the path from question to validated SQL.</p>
    </Link>
    <Link className="docsLanding__card" to="/docs/runtime/readiness-liveness">
      <span className="docsLanding__icon" aria-hidden="true">◈</span>
      <h2>Operations</h2>
      <p>Check readiness, runtime health, and artifact state.</p>
    </Link>
    <Link className="docsLanding__card" to="/docs/api/health-readiness">
      <span className="docsLanding__icon" aria-hidden="true">▢</span>
      <h2>API Reference</h2>
      <p>Inspect the health, readiness, and artifact contracts.</p>
    </Link>
  </div>
</div>
