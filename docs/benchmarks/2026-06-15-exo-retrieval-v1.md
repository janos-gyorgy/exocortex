# exo-retrieval-v1 — 2026-06-15

30 queries · 63 notes · vector signal DARK (no notes_vec) · method borrowed from agentmemory's eval harness, corpus is this vault.

| adapter | P@5 | R@5 | hit@5 | MRR | p50 ms |
|---|---|---|---|---|---|
| grep | 0.100 | 0.467 | 0.467 | 0.307 | 1.04 |
| bm25 | 0.200 | 0.950 | 0.967 | 0.826 | 0.28 |
| live | 0.200 | 0.950 | 0.967 | 0.737 | 1.09 |

- **grep** — naive term-count substring floor.
- **bm25** — FTS5 BM25 only (lexical baseline).
- **live** — production `exo.retrieval.search` (RRF of bm25 + vector + graph). Vector is dark in this index, so this is **bm25+graph**.

Reproduce: `python3 eval/run.py`. Per-query NDJSON in `eval/results-*.ndjson`. Gold labels are self-authored v1 (`eval/queries.jsonl`) — see `eval/README.md` for caveats.

> Table above reflects the **fixed** config (`w_graph` default now **0.1**). `live`
> now matches BM25 on recall. Before the fix (`w_graph=0.5`) `live` scored R@5
> **0.650**, MRR **0.520** — the regression below.

## Conclusion — does hybrid_search earn its keep?

**Not as it was shipped.** At the old default `w_graph=0.5`, the production
"hybrid" was *worse* than plain BM25: R@5 **0.650 vs 0.950**, MRR **0.520 vs
0.826**. Graph expansion injected high-degree hub notes (`claude-sparks`,
`app-ideas`, `projects-moc`) as neighbours of the top hit, displacing the
genuinely relevant note out of the top-5. It broke **9 of 30** queries BM25 got
right (e.g. "who owns this knowledge system": BM25 ranks `the-owner-note` #5; old
`live` dropped it off the list). BM25 itself missed only **1 of 30**.

### `w_graph` sweep (monotonic — more graph = more harm)

| w_graph | R@5 | hit@5 | MRR |
|---|---|---|---|
| 0.0 (off) | 0.950 | 0.967 | 0.826 |
| **0.1 (new default)** | **0.950** | **0.967** | **0.737** |
| 0.25 | 0.817 | 0.833 | 0.564 |
| 0.5 (old default) | 0.650 | 0.667 | 0.520 |

### Action taken / remaining

1. **Done:** `w_graph` default dialed 0.5 → 0.1 in `src/exo/config.py`. Recall
   fully recovered; `live` now ties BM25. (Pure 0.0 edges out 0.1 on MRR — go
   there if you want precision-max and don't mind dropping the graph tiebreaker.)
2. Keep graph expansion for discovery/`collide`, not precision retrieval.
3. **Untested:** build `all-MiniLM-L6-v2` embeddings and re-run — settles whether
   the (currently dark) vector signal helps the 1 BM25 miss / vocab-mismatch queries.
4. Gold set is self-authored v1, corpus is small (63 notes) — directional, not gospel.
