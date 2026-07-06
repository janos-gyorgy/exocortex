---
id: hybrid-retrieval
type: concept
title: Hybrid Retrieval
tags: [retrieval, search]
status: budding
created: 2026-01-01
updated: 2026-01-01
summary: BM25 + vectors + graph expansion beats any single signal, and each signal is explainable.
relations:
  part_of: [demo-vault]
agent:
---

# Hybrid Retrieval

Combining lexical search (BM25) with vector similarity and graph expansion
produces more robust recall than embeddings alone. Each signal is explainable,
which matters for a system humans and agents must trust. See how
[[Demo Vault]] wires this into `exo search`.
