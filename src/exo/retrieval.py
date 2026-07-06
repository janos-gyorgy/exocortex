"""Hybrid retrieval — the core of 'transparent semantic systems'.

Three signals, fused with Reciprocal Rank Fusion (RRF):
  1. BM25 full-text (FTS5)         — lexical, exact, explainable
  2. Vector similarity (sqlite-vec) — semantic recall, optional
  3. Graph expansion               — pull in neighbours of top lexical hits

Each result carries WHY it matched (which signals fired). No black box.
"""
from __future__ import annotations

import sqlite3
import struct

from .config import CONFIG
from .embeddings import Embedder

K = 60  # RRF constant


def _con() -> sqlite3.Connection:
    con = sqlite3.connect(CONFIG.index_db)
    con.row_factory = sqlite3.Row
    return con


def _has_vec(con: sqlite3.Connection) -> bool:
    try:
        import sqlite_vec  # type: ignore

        con.enable_load_extension(True)
        sqlite_vec.load(con)
        con.enable_load_extension(False)
        con.execute("SELECT count(*) FROM notes_vec")
        return True
    except Exception:
        return False


def _bm25(con: sqlite3.Connection, query: str, n: int) -> list[int]:
    # FTS5 MATCH; sanitize to OR of terms to avoid syntax errors on punctuation
    safe = " OR ".join(t for t in _terms(query)) or query
    try:
        rows = con.execute(
            "SELECT rowid FROM notes_fts WHERE notes_fts MATCH ? ORDER BY rank LIMIT ?",
            (safe, n),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    return [r["rowid"] for r in rows]


def _terms(query: str) -> list[str]:
    import re

    return [w for w in re.findall(r"[\w]+", query.lower()) if len(w) > 1]


def _vector(con: sqlite3.Connection, query: str, n: int) -> list[int]:
    emb = Embedder()
    vecs = emb.embed([query])
    if not vecs:
        return []
    blob = struct.pack(f"{len(vecs[0])}f", *vecs[0])
    try:
        rows = con.execute(
            "SELECT rowid FROM notes_vec WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
            (blob, n),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [r["rowid"] for r in rows]


def _graph_expand(con: sqlite3.Connection, seed_ids: list[str], n: int) -> list[int]:
    if not seed_ids:
        return []
    q = ",".join("?" * len(seed_ids))
    rows = con.execute(
        f"SELECT DISTINCT dst FROM edges WHERE src IN ({q}) "
        f"UNION SELECT DISTINCT src FROM edges WHERE dst IN ({q})",
        seed_ids + seed_ids,
    ).fetchall()
    ids = [r[0] for r in rows][:n]
    if not ids:
        return []
    q2 = ",".join("?" * len(ids))
    rr = con.execute(f"SELECT rowid FROM notes WHERE id IN ({q2})", ids).fetchall()
    return [r["rowid"] for r in rr]


def _rrf(rankings: dict[str, list[int]], weights: dict[str, float]) -> dict[int, dict]:
    scores: dict[int, float] = {}
    why: dict[int, list[str]] = {}
    for signal, ids in rankings.items():
        w = weights.get(signal, 1.0)
        for rank, rid in enumerate(ids):
            scores[rid] = scores.get(rid, 0.0) + w * (1.0 / (K + rank + 1))
            why.setdefault(rid, []).append(signal)
    return {rid: {"score": s, "why": why[rid]} for rid, s in scores.items()}


def search(query: str, limit: int = 8, expand: bool = True) -> list[dict]:
    con = _con()
    has_vec = _has_vec(con)

    bm = _bm25(con, query, limit * 3)
    vec = _vector(con, query, limit * 3) if has_vec else []

    rankings = {"bm25": bm, "vector": vec}
    weights = {"bm25": CONFIG.w_bm25, "vector": CONFIG.w_vector, "graph": CONFIG.w_graph}

    if expand and bm:
        seed_ids = [
            r["id"] for r in con.execute(
                f"SELECT id FROM notes WHERE rowid IN ({','.join('?'*len(bm[:3]))})", bm[:3]
            ).fetchall()
        ]
        rankings["graph"] = _graph_expand(con, seed_ids, limit)

    fused = _rrf(rankings, weights)
    top = sorted(fused.items(), key=lambda kv: kv[1]["score"], reverse=True)[:limit]

    results = []
    for rid, meta in top:
        row = con.execute(
            "SELECT id,title,type,path,tags,body FROM notes WHERE rowid=?", (rid,)
        ).fetchone()
        if not row:
            continue
        results.append(
            {
                "id": row["id"], "title": row["title"], "type": row["type"],
                "path": row["path"], "tags": row["tags"],
                "snippet": (row["body"] or "")[:280].replace("\n", " "),
                "score": round(meta["score"], 5), "matched_on": meta["why"],
            }
        )
    con.close()
    return results
