"""Vault ↔ index drift detection — the reconciler's eyes.

The vault is the source of truth and the index is derived state; this module
answers the GitOps question: are they in sync? Same contract as `argocd app
get`: Synced means the index was built from exactly these files, OutOfSync
lists what drifted (modified / new / deleted since last `exo index`).

CLAUDE.md rule #1 ("files win — run exo index") stops being a policy agents
must remember and becomes a state machines can check (exit code 0/1) and a
hook can repair (.githooks/post-commit).
"""
from __future__ import annotations

import sqlite3

from .config import CONFIG
from .indexer import file_hash


def check() -> dict:
    """Compare vault files against the index. Pure read; never repairs."""
    on_disk: dict[str, str] = {}
    for p in sorted(CONFIG.vault.rglob("*.md")):
        if "/templates/" in str(p) or "/.obsidian/" in str(p):
            continue
        on_disk[str(p.relative_to(CONFIG.root))] = file_hash(p)

    indexed: dict[str, str] = {}
    stale_schema = False
    try:
        con = sqlite3.connect(CONFIG.index_db)
        rows = con.execute("SELECT path, hash FROM notes").fetchall()
        con.close()
        indexed = {path: h for path, h in rows}
    except sqlite3.OperationalError:
        stale_schema = True  # no index yet, or index predates the hash column

    modified = sorted(
        p for p, h in on_disk.items() if p in indexed and indexed[p] != h
    )
    new = sorted(p for p in on_disk if p not in indexed)
    deleted = sorted(p for p in indexed if p not in on_disk)
    synced = not (stale_schema or modified or new or deleted)

    out = {
        "status": "Synced" if synced else "OutOfSync",
        "files": len(on_disk),
        "indexed": len(indexed),
        "modified": modified,
        "new": new,
        "deleted": deleted,
    }
    if stale_schema:
        out["note"] = "index missing or predates hash column — run `exo index`"
    if not synced:
        out["repair"] = "exo index"
    return out
