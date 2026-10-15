"""Build the derived index from the vault.

Outputs:
  index/exocortex.db   notes table + FTS5 (BM25) + optional vec0 (sqlite-vec) table
  index/graph.json     {nodes:[...], links:[...]} for the 3D viewer & exports

Idempotent: re-running rebuilds cleanly. The DB is disposable.

Atomic: the new index is built in exocortex.db.tmp and renamed over the live one
only once it is complete, so a failed build leaves the last good index in place
and a concurrent `exo search` never sees half-built tables. A lock serialises
builds (the post-commit hook and a manual `exo index` used to overlap).
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
from pathlib import Path

from .config import CONFIG
from .embeddings import Embedder
from .frontmatter import Note, parse


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _connect(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def _try_load_vec(con: sqlite3.Connection) -> bool:
    try:
        import sqlite_vec  # type: ignore

        con.enable_load_extension(True)
        sqlite_vec.load(con)
        con.enable_load_extension(False)
        return True
    except Exception:
        return False


def _schema(con: sqlite3.Connection, vec_ok: bool, dim: int) -> None:
    con.executescript(
        """
        DROP TABLE IF EXISTS notes;
        DROP TABLE IF EXISTS edges;
        DROP TABLE IF EXISTS notes_fts;
        CREATE TABLE notes(
            rowid INTEGER PRIMARY KEY,
            id TEXT, title TEXT, type TEXT, path TEXT,
            tags TEXT, status TEXT, body TEXT,
            created TEXT, updated TEXT, hash TEXT
        );
        CREATE TABLE edges(
            src TEXT, dst TEXT, rel TEXT
        );
        CREATE VIRTUAL TABLE notes_fts USING fts5(
            title, tags, body, content='notes', content_rowid='rowid'
        );
        """
    )
    if vec_ok:
        con.execute("DROP TABLE IF EXISTS notes_vec;")
        con.execute(
            f"CREATE VIRTUAL TABLE notes_vec USING vec0(rowid INTEGER PRIMARY KEY, embedding float[{dim}]);"
        )


def _iter_notes() -> list[Note]:
    notes: list[Note] = []
    for p in sorted(CONFIG.vault.rglob("*.md")):
        if "/templates/" in str(p) or "/.obsidian/" in str(p):
            continue
        notes.append(parse(p))
    return notes


def build() -> dict:
    lock_path = CONFIG.index_db.parent / ".build.lock"
    with open(lock_path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # one build at a time; the next waits
        tmp_db = CONFIG.index_db.with_name(CONFIG.index_db.name + ".tmp")
        tmp_graph = CONFIG.graph_json.with_name(CONFIG.graph_json.name + ".tmp")
        for leftover in (tmp_db, Path(str(tmp_db) + "-journal"), tmp_graph):
            leftover.unlink(missing_ok=True)  # a crashed build's debris
        try:
            result = _build_into(tmp_db, tmp_graph)
            os.replace(tmp_db, CONFIG.index_db)
            os.replace(tmp_graph, CONFIG.graph_json)
        finally:
            tmp_db.unlink(missing_ok=True)
            tmp_graph.unlink(missing_ok=True)
    return result


def _build_into(db_path: Path, graph_path: Path) -> dict:
    embedder = Embedder()
    con = _connect(db_path)
    vec_ok = embedder.enabled and _try_load_vec(con)
    _schema(con, vec_ok, embedder.dim)

    notes = _iter_notes()
    title_to_id = {n.title: n.id for n in notes}
    title_to_id.update({n.id: n.id for n in notes})

    rows = []
    for i, n in enumerate(notes, start=1):
        rows.append(
            (
                i, n.id, n.title, n.type, str(n.path.relative_to(CONFIG.root)),
                ",".join(n.tags), str(n.fm.get("status") or ""), n.body,
                str(n.fm.get("created") or ""), str(n.fm.get("updated") or ""),
                file_hash(n.path),
            )
        )
    con.executemany(
        "INSERT INTO notes(rowid,id,title,type,path,tags,status,body,created,updated,hash)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    con.execute(
        "INSERT INTO notes_fts(rowid,title,tags,body) SELECT rowid,title,tags,body FROM notes"
    )

    # edges: plain wikilinks (rel='link') + typed relations
    edges = []
    for n in notes:
        for tgt in n.links:
            edges.append((n.id, title_to_id.get(tgt, tgt), "link"))
        for rel, tgt in n.relations:
            edges.append((n.id, title_to_id.get(tgt, tgt), rel))
    con.executemany("INSERT INTO edges(src,dst,rel) VALUES(?,?,?)", edges)

    # vectors
    if vec_ok:
        # Multi-field embedding (A-MEM "multiple angles of the same memory"):
        # fold title + summary + tags into the vector, not body alone — cheap
        # recall win for hybrid_search.
        texts = []
        for n in notes:
            parts = [n.title, str(n.fm.get("summary") or ""), " ".join(n.tags), n.body]
            texts.append("\n\n".join(p for p in parts if p)[:8000])
        vectors = embedder.embed(texts)
        if vectors:
            import struct

            for i, vec in enumerate(vectors, start=1):
                blob = struct.pack(f"{len(vec)}f", *vec)
                con.execute("INSERT INTO notes_vec(rowid,embedding) VALUES(?,?)", (i, blob))

    con.commit()

    # graph.json
    nodes = [
        {"id": n.id, "title": n.title, "type": n.type, "tags": n.tags,
         "path": str(n.path.relative_to(CONFIG.root))}
        for n in notes
    ]
    valid = {n["id"] for n in nodes}
    links = [
        {"source": s, "target": d, "rel": r}
        for (s, d, r) in edges if s in valid and d in valid
    ]
    graph_path.write_text(json.dumps({"nodes": nodes, "links": links}, indent=2))

    con.close()
    return {
        "notes": len(notes),
        "edges": len(edges),
        "vectors": vec_ok,
        "embed_backend": embedder.backend,
        "graph_json": str(CONFIG.graph_json),
    }
