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
    Schema evidence, business context, generation, validation, and execution in one observable workflow.
  </p>

  <div className="docsLanding__cards">
    <Link className="docsLanding__card" to="/docs/getting-started/overview">
      <span className="docsLanding__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M5 19 19 5M9 5h10v10" />
        </svg>
      </span>
      <h2>Quick Start</h2>
      <p>Run the first knowledge-grounded query locally.</p>
    </Link>
    <Link className="docsLanding__card" to="/docs/architecture/overview">
      <span className="docsLanding__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <rect x="4" y="5" width="16" height="5" rx="1" />
          <rect x="4" y="14" width="16" height="5" rx="1" />
          <path d="M8 8h.01M8 17h.01" />
        </svg>
      </span>
      <h2>Architecture</h2>
      <p>Follow the path from question to validated SQL.</p>
    </Link>
    <Link className="docsLanding__card" to="/docs/runtime/readiness-liveness">
      <span className="docsLanding__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="m12 3 7 3v5c0 4.5-2.8 7.7-7 10-4.2-2.3-7-5.5-7-10V6l7-3Z" />
          <path d="m9 12 2 2 4-4" />
        </svg>
      </span>
      <h2>Operations</h2>
      <p>Check readiness, runtime health, and artifact state.</p>
    </Link>
    <Link className="docsLanding__card" to="/docs/api/health-readiness">
      <span className="docsLanding__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <rect x="5" y="10" width="14" height="10" rx="2" />
          <path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v2" />
        </svg>
      </span>
      <h2>API Reference</h2>
      <p>Inspect the health, readiness, and artifact contracts.</p>
    </Link>
  </div>

</div>
