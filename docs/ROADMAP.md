# Roadmap

Phased so each stage is independently useful. Don't build ahead of need.

## Phase 0 — Foundation (this repo, shipped)
- Markdown vault + ontology + templates.
- SQLite hybrid index (BM25 + vectors + edges) + graph.json.
- exocortex MCP (search/graph/gardener) + Basic Memory (CRUD).
- Obsidian 2D/3D + standalone 3D viewer.
- CLI for cron/n8n.

## Phase 1 — Autonomous gardening (weeks)
- n8n nightly gardener wired to a Claude Code run with CLAUDE.md.
- Link-suggestion acceptance loop; orphan reduction metric.
- Summary regeneration for evergreen notes.
- Git-based audit dashboard (who/what changed).

## Phase 2 — Richer retrieval (month)
- Chunk-level embeddings for long notes (currently note-level).
- Cross-encoder rerank step (optional, local model).
- Query-time relation-aware expansion (follow `supports`/`contradicts`).
- Eval harness: a fixed Q→expected-notes set to catch retrieval regressions.

## Phase 3 — Multi-agent orchestration
- Named agents with roles: Librarian (organize), Researcher (ingest+synthesize),
  Critic (find contradictions/gaps via `contradicts` + structural-hole analysis).
- Coordinator pattern: gardener dispatches, agents propose diffs, human merges.
- Fits naturally as n8n workflows (your Angel/Devil pattern: detect → act).

## Phase 4 — Local models & ownership
- Swap Ollama embeddings to your Pi inference rig (NanoCamelid lineage).
- Local generation model for summaries/synthesis → zero external dependency.
- Fully air-gappable.

## Phase 5 — Sensing & expansion
- Voice capture → Whisper (local) → inbox note.
- Life-logging streams (calendar, git activity, reading) → `log` notes.
- Research automation: standing queries that ingest + synthesize on schedule.
- Distributed cognition: federate vaults (per-domain or per-device) with a
  shared link namespace.

## Explicit non-goals (for now)
- No Neo4j/graph-DB server until graph queries actually outgrow SQLite.
- No bespoke web app where Obsidian already wins.
- No cloud sync as the default path. Sync is git; cloud is opt-in.
