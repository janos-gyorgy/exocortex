# eval — retrieval benchmark for the exocortex vault

Answers one question with a number: **does `hybrid_search` earn its keep?**

Method borrowed from [agentmemory](https://github.com/rohitg00/agentmemory)'s eval
harness (adapter-pluggable, score side-by-side, NDJSON + scorecard). The *corpus*
is this vault's own — agentmemory's datasets (LongMemEval) are conversational QA,
which don't map onto a markdown knowledge vault, so only the methodology transfers.

## Run

```bash
python3 eval/run.py
```

Prints a scorecard, writes `eval/results-<date>.ndjson` (per-query) and
`docs/benchmarks/<date>-exo-retrieval-v1.md`. Sweep a fusion weight with an env
var, e.g. `EXO_W_GRAPH=0.1 python3 eval/run.py`.

## Adapters (query → ranked note ids)

- **grep** — naive substring term-count over title+body. The floor.
- **bm25** — FTS5 BM25 only (`exo.retrieval._bm25`). Lexical baseline.
- **live** — exactly the production `exo.retrieval.search`: RRF fusion of
  bm25 + vector + graph expansion. The thing under test.

## Metrics (@k=5)

P@5, R@5, hit@5, MRR (over top-10), p50 latency (ms). Standard IR metrics, same
ones agentmemory reports.

## Gold set — `queries.jsonl`

`{"q": "<query>", "gold": ["<note-id>", ...], "kind": "<query type>"}` per line.
Query kinds span lexical / concept / vocab-mismatch / multi-hop / nav / entity so
the benchmark can differentiate where each signal helps.

## Honest caveats (read before trusting a number)

- **Gold is self-authored (v1).** Bias risk — the author of the queries also
  picked the right answers. Correct/extend it; treat results as directional.
- **Small corpus.** 63 notes, gold-sparse. Findings are robust across the 30
  queries here but this isn't a public benchmark.
- **Vectors are dark.** This index has no `notes_vec` (homelab runs
  `EXO_EMBED_BACKEND=none`), so `live` == bm25+graph. The "vectors add recall"
  claim is currently **untested** — build embeddings and re-run to settle it.

See the dated scorecard in `docs/benchmarks/` for the current verdict.
