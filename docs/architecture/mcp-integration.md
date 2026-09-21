---
sidebar_position: 2
title: MCP Integration
---

# MCP Integration

MCP exposes project-scoped tools such as `ask` and `nl2sql`. The runtime resolves the project tool definition before calling the MCP endpoint and preserves query, thread, trace, and artifact identity in the result.

```text
Frontend / QA Smoke
        ↓
Backend MCP proxy
        ↓
Project tool definition
        ↓
MCP initialize + tools/call
        ↓
Structured result with provenance
```

QA Smoke uses the same project runtime path as user QA and therefore catches tool, provider, snapshot, and schema problems together.
