"""Collision engine — serendipity as a query.

Retrieval answers questions you ask. Collide surfaces pairs of notes you would
never think to ask about together: far apart in the graph, lexically disjoint,
from different corners and eras of the vault. The reader's only task is
"does anything connect?" — most pairs yield nothing, and that is the contract
(see vault/00-inbox/claude-sparks.md).

Like retrieval, every pair carries WHY it was chosen. Pairs are sampled with
score-weighted randomness rather than ranked top-k, so repeated runs interrupt
with different pairs instead of converging on one.
"""
from __future__ import annotations

import random
import re
import sqlite3
from collections import defaultdict, deque
from datetime import date

from .config import CONFIG

MIN_BODY = 120          # skip stubs — nothing to collide with
DISCONNECTED_HOPS = 8   # graph distance assigned to unreachable pairs
MAX_AGE_GAP_DAYS = 365  # age gaps cap out at a year

# weights: graph distance dominates, lexical disjointness second
W_HOPS, W_LEXICAL, W_AGE, W_FOLDER, W_TYPE = 2.0, 1.5, 1.0, 0.5, 0.5


def _con() -> sqlite3.Connection:
    con = sqlite3.connect(CONFIG.index_db)
    con.row_factory = sqlite3.Row
    return con


def _terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[\w]+", text.lower()) if len(w) > 3}


def _created(s: str) -> date | None:
    try:
        return date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        return None


def _hops_from(adj: dict[str, set[str]], src: str) -> dict[str, int]:
    dist = {src: 0}
    q = deque([src])
    while q:
        node = q.popleft()
        for nxt in adj.get(node, ()):
            if nxt not in dist:
                dist[nxt] = dist[node] + 1
                q.append(nxt)
    return dist


def pairs(n: int = 3, min_hops: int = 3, seed: int | None = None) -> list[dict]:
    """Sample `n` distant note pairs. `min_hops` floors the graph distance
    (disconnected pairs always qualify); `seed` makes a run reproducible."""
    con = _con()
    notes = [
        dict(r) for r in con.execute(
            "SELECT id,title,type,path,tags,created,body FROM notes"
            " WHERE length(body) >= ?", (MIN_BODY,)
        ).fetchall()
    ]
    adj: dict[str, set[str]] = defaultdict(set)
    for r in con.execute("SELECT src,dst FROM edges").fetchall():
        adj[r["src"]].add(r["dst"])
        adj[r["dst"]].add(r["src"])
    con.close()

    for note in notes:
        note["terms"] = _terms(f"{note['title']} {note['tags']} {note['body']}")
        note["date"] = _created(note["created"])
        note["folder"] = note["path"].split("/")[1] if "/" in note["path"] else ""

    candidates = []
    for i, a in enumerate(notes):
        hops_a = _hops_from(adj, a["id"])
        for b in notes[i + 1:]:
            hops = hops_a.get(b["id"], DISCONNECTED_HOPS)
            if hops < min_hops:
                continue
            shared = a["terms"] & b["terms"]
            union = a["terms"] | b["terms"]
            lexical = 1.0 - (len(shared) / len(union) if union else 0.0)
            age_days = (
                abs((a["date"] - b["date"]).days)
                if a["date"] and b["date"] else 0
            )
            score = (
                W_HOPS * min(hops, DISCONNECTED_HOPS) / DISCONNECTED_HOPS
                + W_LEXICAL * lexical
                + W_AGE * min(age_days, MAX_AGE_GAP_DAYS) / MAX_AGE_GAP_DAYS
                + W_FOLDER * (a["folder"] != b["folder"])
                + W_TYPE * (a["type"] != b["type"])
            )
            candidates.append((score, hops, sorted(shared), age_days, a, b))

    rng = random.Random(seed)
    picked: list[dict] = []
    used: set[str] = set()
    while candidates and len(picked) < n:
        weights = [c[0] ** 2 for c in candidates]  # sharpen toward distant pairs
        (score, hops, shared, age_days, a, b) = rng.choices(candidates, weights)[0]
        candidates = [
            c for c in candidates
            if c[4]["id"] not in (a["id"], b["id"]) and c[5]["id"] not in (a["id"], b["id"])
        ]
        if a["id"] in used or b["id"] in used:
            continue
        used |= {a["id"], b["id"]}
        picked.append(
            {
                "a": _public(a), "b": _public(b),
                "why": {
                    "hops": "disconnected" if hops >= DISCONNECTED_HOPS else hops,
                    "shared_terms": shared[:5],
                    "age_gap_days": age_days,
                    "score": round(score, 3),
                },
                "task": "Does anything connect? Nothing is a valid answer.",
            }
        )
    return picked


def _public(note: dict) -> dict:
    return {
        "id": note["id"], "title": note["title"], "type": note["type"],
        "path": note["path"],
        "snippet": (note["body"] or "")[:240].replace("\n", " "),
    }
