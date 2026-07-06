#!/usr/bin/env python3
"""exo-retrieval-v1 — does hybrid_search earn its keep?

Adapter-pluggable retrieval benchmark for the exocortex vault, in the spirit of
agentmemory's eval harness (grep / bm25 / live side-by-side, same metrics). The
*method* is borrowed; the corpus + gold labels are this vault's own
(eval/queries.jsonl) — agentmemory's datasets are conversational (LongMemEval),
which don't map onto a markdown knowledge vault.

Adapters (query -> ranked note ids):
  grep   — naive substring term-count over title+body. The floor.
  bm25   — FTS5 BM25 only (exo.retrieval._bm25). Lexical baseline.
  live   — exactly what production search() does: RRF fusion of bm25 + vector
           + graph expansion. Vector is dark in this index (no notes_vec), so
           today this is bm25+graph. THIS is the thing under test.

Metrics @k=5: P@5, R@5, hit@5, MRR (over top-10), p50 latency (ms).
Outputs: a printed scorecard, NDJSON per-query, and a dated markdown scorecard
under docs/benchmarks/.

Honest caveats (see eval/README.md): gold is self-authored v1 (bias risk —
correct it); corpus is small (63 notes, gold-sparse); 'live' == bm25+graph until
embeddings are built, so this run answers "does GRAPH earn its keep over bm25",
not "do vectors help".

Usage:  python3 eval/run.py
"""
from __future__ import annotations

import json
import sqlite3
import statistics
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from exo.config import CONFIG  # noqa: E402
from exo import retrieval as R  # noqa: E402

HERE = Path(__file__).resolve().parent
QUERIES = HERE / "queries.jsonl"
K = 5


def _con() -> sqlite3.Connection:
    c = sqlite3.connect(CONFIG.index_db)
    c.row_factory = sqlite3.Row
    return c


def _rowids_to_ids(con, rowids):
    out = []
    for rid in rowids:
        row = con.execute("SELECT id FROM notes WHERE rowid=?", (rid,)).fetchone()
        if row:
            out.append(row["id"])
    return out


# ── adapters: (con, query, n) -> ranked list of note ids ──────────────────────
def adapter_grep(con, q, n):
    terms = R._terms(q)
    rows = con.execute(
        "SELECT id, lower(coalesce(title,'')||' '||coalesce(body,'')) t FROM notes"
    ).fetchall()
    scored = []
    for r in rows:
        s = sum(r["t"].count(t) for t in terms)
        if s > 0:
            scored.append((s, r["id"]))
    scored.sort(key=lambda x: -x[0])
    return [i for _, i in scored[:n]]


def adapter_bm25(con, q, n):
    return _rowids_to_ids(con, R._bm25(con, q, n))


def adapter_live(con, q, n):
    # the real production path (bm25 + vector(if any) + graph, fused via RRF)
    return [d["id"] for d in R.search(q, limit=n, expand=True)]


ADAPTERS = {"grep": adapter_grep, "bm25": adapter_bm25, "live": adapter_live}


def score(ranked, gold):
    top = ranked[:K]
    inter = [g for g in top if g in gold]
    p = len(inter) / K
    r = (len(inter) / len(gold)) if gold else 0.0
    hit = 1.0 if inter else 0.0
    mrr = 0.0
    for i, nid in enumerate(ranked[:10]):
        if nid in gold:
            mrr = 1.0 / (i + 1)
            break
    return p, r, hit, mrr


def main():
    queries = [json.loads(l) for l in QUERIES.read_text().splitlines() if l.strip()]
    con = _con()
    agg = {a: {"p": [], "r": [], "hit": [], "mrr": [], "lat": []} for a in ADAPTERS}
    nd = []

    for item in queries:
        q, gold = item["q"], set(item["gold"])
        for name, fn in ADAPTERS.items():
            t = time.perf_counter()
            ranked = fn(con, q, 10)
            lat = (time.perf_counter() - t) * 1000.0
            p, r, hit, mrr = score(ranked, gold)
            a = agg[name]
            a["p"].append(p); a["r"].append(r); a["hit"].append(hit)
            a["mrr"].append(mrr); a["lat"].append(lat)
            nd.append({
                "q": q, "kind": item.get("kind"), "adapter": name,
                "gold": sorted(gold), "top5": ranked[:K],
                "P@5": round(p, 3), "R@5": round(r, 3),
                "hit@5": hit, "MRR": round(mrr, 3), "ms": round(lat, 2),
            })

    n = len(queries)
    rows = []
    for name in ADAPTERS:
        a = agg[name]
        rows.append((
            name,
            statistics.mean(a["p"]),
            statistics.mean(a["r"]),
            sum(a["hit"]) / n,
            statistics.mean(a["mrr"]),
            statistics.median(a["lat"]),
        ))

    hdr = f"{'adapter':<8} {'P@5':>7} {'R@5':>7} {'hit@5':>7} {'MRR':>7} {'p50 ms':>8}"
    print(f"\nexo-retrieval-v1  ·  {n} queries  ·  {con.execute('SELECT count(*) FROM notes').fetchone()[0]} notes\n")
    print(hdr)
    print("-" * len(hdr))
    for name, p, r, hit, mrr, lat in rows:
        print(f"{name:<8} {p:>7.3f} {r:>7.3f} {hit:>7.3f} {mrr:>7.3f} {lat:>8.2f}")

    # ── artifacts ─────────────────────────────────────────────────────────────
    today = date.today().isoformat()
    nd_path = HERE / f"results-{today}.ndjson"
    nd_path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in nd) + "\n")

    bench_dir = ROOT / "docs" / "benchmarks"
    bench_dir.mkdir(parents=True, exist_ok=True)
    sc = bench_dir / f"{today}-exo-retrieval-v1.md"
    lines = [
        f"# exo-retrieval-v1 — {today}",
        "",
        f"{n} queries · {con.execute('SELECT count(*) FROM notes').fetchone()[0]} notes · "
        f"vector signal {'ON' if False else 'DARK (no notes_vec)'} · "
        "method borrowed from agentmemory's eval harness, corpus is this vault.",
        "",
        "| adapter | P@5 | R@5 | hit@5 | MRR | p50 ms |",
        "|---|---|---|---|---|---|",
    ]
    for name, p, r, hit, mrr, lat in rows:
        lines.append(f"| {name} | {p:.3f} | {r:.3f} | {hit:.3f} | {mrr:.3f} | {lat:.2f} |")
    lines += [
        "",
        "- **grep** — naive term-count substring floor.",
        "- **bm25** — FTS5 BM25 only (lexical baseline).",
        "- **live** — production `exo.retrieval.search` (RRF of bm25 + vector + graph). "
        "Vector is dark in this index, so this is **bm25+graph**.",
        "",
        "Reproduce: `python3 eval/run.py`. Per-query NDJSON in `eval/results-*.ndjson`. "
        "Gold labels are self-authored v1 (`eval/queries.jsonl`) — see `eval/README.md` for caveats.",
    ]
    sc.write_text("\n".join(lines) + "\n")
    con.close()
    print(f"\nwrote {nd_path.relative_to(ROOT)} and {sc.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
