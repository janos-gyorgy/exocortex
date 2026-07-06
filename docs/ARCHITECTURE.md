# Architecture

## One sentence
A plain-markdown vault is the durable substrate; everything else (index, search,
graph, agents, 3D viz) is a **derived, rebuildable layer** over it.

## Layer model

```
L5  Visualization     Obsidian 2D graph · Obsidian 3D Graph plugin · standalone 3d-force-graph web viewer
L4  Automation        n8n workflows (ingest, nightly gardener) · cron · Argo Workflows (homelab)
L3  Agent interface   MCP: Basic Memory (note CRUD) + exocortex (hybrid search, graph analytics, gardener)
L2  Index / retrieval SQLite — FTS5 (BM25) + sqlite-vec (embeddings) + materialized edges → graph.json
L1  Structure         Typed frontmatter ontology · wikilinks · typed relations (see ONTOLOGY.md)
L0  Substrate         Markdown files in git. Human-readable. Locally owned. The source of truth.
```

Delete L1–L5 and the knowledge survives in L0. That property is the whole point.

## Component decisions

**Vault = source of truth, Obsidian = a viewer.** Obsidian is the best human
front-end (2D/3D graph, plugin ecosystem) but it is *not* the store. The store is
a folder of markdown in git. This kills lock-in: Logseq, VS Code + Foam, `grep`,
or a future tool all read the same files.

**Basic Memory for note CRUD.** It already solves local-first markdown +
SQLite graph + MCP read/write, Obsidian-compatible, battle-tested. Reimplementing
CRUD would be effort spent on the boring, easy-to-get-wrong part. We adopt it and
spend our effort on what it lacks.

**exocortex MCP for retrieval + graph intelligence.** Hybrid search with
explainability (`matched_on`), graph analytics (backlinks, neighbours, orphans,
hubs), and the gardener report. This is the differentiated layer.

**Hybrid retrieval, not embeddings-only.** Three signals fused with Reciprocal
Rank Fusion: BM25 (lexical, exact, explainable), vectors (semantic recall, a
booster — not the spine), and graph expansion (pull neighbours of top lexical
hits). Each result reports which signals fired. Embeddings-only systems can't tell
you *why* something matched; this can.

**One SQLite file, not a stack of servers.** FTS5 + sqlite-vec + an edges table
live in `index/exocortex.db`. No Neo4j, no Chroma server, no Postgres. The graph's
real home is the wikilinks; SQLite just materializes it for queries. Fewer moving
parts = more robust, which matters for a system meant to last years.

**Local embeddings by default.** Ollama (`nomic-embed-text`) on the homelab, with
a `sentence-transformers` CPU fallback and a `none` mode where the vector layer is
simply off and FTS+graph still work. Nothing breaks if Ollama is down.

## Homelab integration (tc-homelab)

- **Vault repo** → GitLab. History = full audit trail of human + agent edits.
- **exocortex MCP + viewer** → containers in k3s; expose viewer via Traefik.
- **Embeddings** → Ollama service in-cluster (or your Pi inference rig later).
- **Secrets** (optional API embedding keys) → HashiCorp Vault.
- **GitOps** → Argo CD app syncs `deploy/k8s/`.
- **Scheduled gardener** → CronJob or n8n workflow → emits report → agent run.

## Data flow

```
human/agent writes .md ──► git commit ──► `exo index`
                                            │
                          ┌─────────────────┼──────────────────┐
                          ▼                 ▼                  ▼
                    SQLite FTS5        sqlite-vec          graph.json
                          └──────── hybrid_search ────────┘   │
                                       (MCP)                   ▼
                                                        3D viewer / Obsidian
```

## Failure modes & guarantees
- **Index corruption** → `rm index/*.db && exo index`. Zero data loss (derived).
- **Ollama down** → vector layer auto-disables; lexical + graph still serve.
- **Agent misbehaves** → it's a git diff; `git revert`.
- **Obsidian abandoned** → files are still plain markdown; pick any reader.
