---
sidebar_position: 4
title: Artifact Snapshot
---

# Artifact Snapshot

An active artifact snapshot is the versioned runtime boundary for prompts, SQL pairs, user instructions, semantic models, schema RAG, MCP tools, and runtime policies.

The snapshot gate compares draft and active truth. Publishing and activation are the promotion boundary; normal Ask/NL2SQL execution must not combine draft content with an older active runtime.

```text
Draft changes
    ↓ publish
Artifact version
    ↓ activate
Active snapshot + runtime materialization
    ↓ readiness + QA Smoke
Servable project runtime
```
