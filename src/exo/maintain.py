"""The gardener — autonomous maintenance surface.

These functions DETECT work; an agent (Claude via MCP / Claude Code) DECIDES and
WRITES. Keeping detection deterministic and writes agent-driven keeps the system
auditable: every change is a git diff authored by an identifiable agent run.

Run `exo garden` nightly (cron/n8n). It emits a report; pipe it to an agent.
"""
from __future__ import annotations

import re
import sqlite3
import subprocess
from datetime import datetime, timezone

from .config import CONFIG
from . import graph, retrieval
from .frontmatter import parse


def _con() -> sqlite3.Connection:
    con = sqlite3.connect(CONFIG.index_db)
    con.row_factory = sqlite3.Row
    return con


def link_suggestions(max_notes: int = 25) -> list[dict]:
    """For orphan/under-linked notes, propose links via semantic neighbours."""
    suggestions = []
    for o in graph.orphans()[:max_notes]:
        hits = retrieval.search(o["title"], limit=4, expand=False)
        cand = [h for h in hits if h["id"] != o["id"]][:3]
        if cand:
            suggestions.append(
                {"note": o["id"], "title": o["title"],
                 "suggested_links": [{"id": c["id"], "title": c["title"]} for c in cand]}
            )
    return suggestions


def _git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args], cwd=CONFIG.root, capture_output=True, text=True, timeout=30
    ).stdout.strip()


def stale_summaries() -> list[dict]:
    """Notes whose `summary:` frontmatter is missing, or was last touched
    BEFORE the note's most recent commit (i.e. the note changed and nobody
    refreshed the summary). Asked of git, not guessed from note length."""
    out: list[dict] = []
    for p in sorted(CONFIG.vault.rglob("*.md")):
        if "/templates/" in str(p) or "/.obsidian/" in str(p):
            continue
        note = parse(p)
        rel = str(p.relative_to(CONFIG.root))
        if not str(note.fm.get("summary") or "").strip():
            if len(note.body) > 200:
                out.append({"id": note.id, "title": note.title, "reason": "summary missing"})
            continue
        try:
            lineno = next(
                i for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                if re.match(r"^summary:", line)
            )
            blame = _git(["blame", "-L", f"{lineno},{lineno}", "--line-porcelain", rel])
            m = re.search(r"^committer-time (\d+)", blame, re.MULTILINE)
            summary_t = int(m.group(1)) if m else 0
            note_t = int(_git(["log", "-1", "--format=%ct", "--", rel]) or 0)
        except (StopIteration, ValueError, OSError, subprocess.SubprocessError):
            continue  # unparseable or git unavailable — never crash the report
        if note_t and summary_t and note_t > summary_t:
            out.append(
                {"id": note.id, "title": note.title,
                 "reason": f"note changed after summary was last written "
                           f"({datetime.fromtimestamp(summary_t, timezone.utc).date()})"}
            )
    return out


def moc_drift(moc_id: str = "projects-moc") -> list[dict]:
    """`type: project` notes missing from the Projects MOC.

    The MOC calls itself the source of truth for "what György is building," but
    its lists are hand-maintained markdown — a new project note doesn't appear
    until someone edits the MOC. This flags that drift (the exact gap the
    gardener re-fixed by hand on 06-12 and 06-14) so it surfaces on signal,
    like an OutOfSync badge, instead of by spot-noticing. Detection only: an
    agent still writes the MOC edit."""
    notes = []
    moc = None
    for p in sorted(CONFIG.vault.rglob("*.md")):
        if "/templates/" in str(p) or "/.obsidian/" in str(p):
            continue
        note = parse(p)
        if note.id == moc_id:
            moc = note
        notes.append(note)
    if moc is None:
        return []
    # match case-insensitively: the MOC links short forms ([[Magpie]], [[Stoa]])
    # whose casing/alias differs from the note id/title — that's link hygiene,
    # not the "missing from the radar" drift we're hunting.
    referenced = {t.lower() for t in moc.links}
    out: list[dict] = []
    for note in notes:
        if note.id == moc_id or str(note.fm.get("type") or "") != "project":
            continue
        if note.id.lower() not in referenced and note.title.lower() not in referenced:
            out.append(
                {"id": note.id, "title": note.title,
                 "lifecycle": str(note.fm.get("lifecycle") or note.fm.get("status") or "?"),
                 "reason": "type:project note not listed in projects-moc"}
            )
    return out


def report() -> dict:
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "orphans": graph.orphans(),
        "hubs": graph.hubs(),
        "link_suggestions": link_suggestions(),
        "summary_candidates": stale_summaries(),
        "moc_drift": moc_drift(),
    }
