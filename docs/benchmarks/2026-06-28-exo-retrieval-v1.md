# exo-retrieval-v1 — 2026-06-28

30 queries · 101 notes · vector signal DARK (no notes_vec) · method borrowed from agentmemory's eval harness, corpus is this vault.

| adapter | P@5 | R@5 | hit@5 | MRR | p50 ms |
|---|---|---|---|---|---|
| grep | 0.060 | 0.283 | 0.300 | 0.216 | 2.30 |
| bm25 | 0.187 | 0.883 | 0.900 | 0.760 | 0.37 |
| live | 0.187 | 0.883 | 0.900 | 0.760 | 1.38 |

- **grep** — naive term-count substring floor.
- **bm25** — FTS5 BM25 only (lexical baseline).
- **live** — production `exo.retrieval.search` (RRF of bm25 + vector + graph). Vector is dark in this index, so this is **bm25+graph**.

Reproduce: `python3 eval/run.py`. Per-query NDJSON in `eval/results-*.ndjson`. Gold labels are self-authored v1 (`eval/queries.jsonl`) — see `eval/README.md` for caveats.
