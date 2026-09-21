---
sidebar_position: 2
title: RAG and Few-shot Evidence
---

# RAG and Few-shot Evidence

Retrieval supplies evidence; it does not replace the runtime schema contract.

## Evidence layers

| Layer | Purpose | Example |
| --- | --- | --- |
| Schema metadata | Identifies valid tables and columns | `fund_master_view` |
| Semantic mappings | Connects business terms to canonical fields | `US allocation → ..._in_united_states` |
| Similar questions | Finds related user intent | “Which funds have the highest US allocation?” |
| Few-shot SQL | Provides a question-to-SQL pattern | `SELECT ... FROM fund_master_view` |
| User instructions | Applies project-specific policy | Alias and formatting rules |

The active artifact snapshot binds these inputs together so a query does not combine a draft prompt, an old SQL example, and a different live schema.
