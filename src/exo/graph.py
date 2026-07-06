"""Graph queries over the materialized edges table. Transparent, explainable.

No graph DB server: edges live in SQLite, the 'real' graph lives in the
markdown wikilinks. These helpers power agent tools and the gardener.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict

from .config import CONFIG


def _con() -> sqlite3.Connection:
    con = sqlite3.connect(CONFIG.index_db)
    con.row_factory = sqlite3.Row
    return con


def backlinks(note_id: str) -> list[dict]:
    con = _con()
    rows = con.execute(
        "SELECT e.src AS id, n.title, e.rel FROM edges e "
        "JOIN notes n ON n.id=e.src WHERE e.dst=?", (note_id,)
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def neighbors(note_id: str, depth: int = 1) -> dict:
    """Return the local subgraph around a node up to `depth` hops."""
    con = _con()
    adj: dict[str, set[str]] = defaultdict(set)
    for r in con.execute("SELECT src,dst FROM edges").fetchall():
        adj[r["src"]].add(r["dst"])
        adj[r["dst"]].add(r["src"])
    con.close()
    seen = {note_id}
    frontier = {note_id}
    for _ in range(max(1, depth)):
        nxt: set[str] = set()
        for node in frontier:
            nxt |= adj.get(node, set())
        nxt -= seen
        seen |= nxt
        frontier = nxt
    return {"center": note_id, "nodes": sorted(seen)}


def orphans() -> list[dict]:
    """Notes with no inbound and no outbound edges — candidates for linking."""
    con = _con()
    linked = set()
    for r in con.execute("SELECT src,dst FROM edges").fetchall():
        linked.add(r["src"])
        linked.add(r["dst"])
    rows = con.execute("SELECT id,title,type FROM notes").fetchall()
    con.close()
    return [dict(r) for r in rows if r["id"] not in linked]


def hubs(limit: int = 15) -> list[dict]:
    """Most-connected notes by degree — natural Maps of Content candidates."""
    con = _con()
    deg: dict[str, int] = defaultdict(int)
    for r in con.execute("SELECT src,dst FROM edges").fetchall():
        deg[r["src"]] += 1
        deg[r["dst"]] += 1
    titles = {r["id"]: r["title"] for r in con.execute("SELECT id,title FROM notes")}
    con.close()
    ranked = sorted(deg.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return [{"id": k, "title": titles.get(k, k), "degree": v} for k, v in ranked]
