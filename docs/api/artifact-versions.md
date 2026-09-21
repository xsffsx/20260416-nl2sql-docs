---
sidebar_position: 2
title: Artifact Version APIs
---

# Artifact Version APIs

Artifact version APIs manage the publish and activation lifecycle. The active response includes the artifact version identity, bundle hash, runtime identity, schema RAG binding, and data-source fingerprint.

Use the Dashboard artifact review page for normal operator workflows. Use the API directly for scripted import validation, activation checks, and troubleshooting evidence.

:::warning
Do not treat an artifact row as servable until it is active, its runtime identity is consistent, and project Runtime Readiness plus QA Smoke are successful.
:::
