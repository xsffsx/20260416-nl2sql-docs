---
sidebar_position: 1
title: NL2SQL Pipeline
---

# NL2SQL Pipeline

The runtime keeps the generation path explicit and observable:

```mermaid
flowchart LR
  Q[Business question] --> I[Intent understanding]
  I --> K[Knowledge retrieval]
  K --> S[Schema linking]
  S --> G[SQL generation]
  G --> V[SQL validation]
  V -->|invalid| R[Correction retry]
  R --> V
  V -->|valid| E[Execution / answer]
```

Each stage consumes canonical state from the current project and active artifact snapshot. The final response includes the generated SQL and runtime evidence needed to explain how it was produced.
