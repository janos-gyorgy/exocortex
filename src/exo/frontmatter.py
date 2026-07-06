"""Parse a markdown note into structured form.

A note is: YAML frontmatter (optional) + markdown body. We extract:
  - frontmatter dict (id, type, tags, status, relations, ...)
  - wikilinks  [[Target]] / [[Target|alias]] / [[Target#heading]]
  - typed relations from frontmatter `relations:` (e.g. supports/contradicts)

The markdown stays the source of truth; this is pure read-side parsing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
FM_DELIM = re.compile(r"^---\s*$", re.MULTILINE)


@dataclass
class Note:
    path: Path
    title: str
    fm: dict[str, Any]
    body: str
    links: list[str] = field(default_factory=list)          # plain wikilink targets
    relations: list[tuple[str, str]] = field(default_factory=list)  # (rel_type, target)

    @property
    def id(self) -> str:
        return str(self.fm.get("id") or self.path.stem)

    @property
    def type(self) -> str:
        return str(self.fm.get("type") or "note")

    @property
    def tags(self) -> list[str]:
        t = self.fm.get("tags") or []
        if isinstance(t, str):
            return [x.strip() for x in re.split(r"[,\s]+", t) if x.strip()]
        return [str(x) for x in t]


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = FM_DELIM.split(text, maxsplit=2)
    # parts: ['', '<yaml>', '<body>'] when leading delimiter present
    if len(parts) >= 3:
        try:
            fm = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            fm = {}
        if not isinstance(fm, dict):
            fm = {}
        return fm, parts[2].lstrip("\n")
    return {}, text


def _flatten(x: Any) -> list[str]:
    """Flatten arbitrarily-nested YAML values to clean target strings.

    Tolerates the common footgun of writing `[[Wikilink]]` inside YAML (which
    parses to a nested list) — though the recommended form is a plain note id.
    """
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        out: list[str] = []
        for item in x:
            out.extend(_flatten(item))
        return out
    return [_clean_target(str(x))]


def extract_relations(fm: dict[str, Any]) -> list[tuple[str, str]]:
    """`relations:` is a dict {rel_type: [note-ids]} (preferred) or a list of
    'rel:: target' strings. Targets are note ids or titles."""
    out: list[tuple[str, str]] = []
    rel = fm.get("relations")
    if isinstance(rel, dict):
        for rtype, targets in rel.items():
            for t in _flatten(targets):
                if t:
                    out.append((str(rtype), t))
    elif isinstance(rel, list):
        for item in rel:
            s = str(item)
            if "::" in s:
                rtype, t = s.split("::", 1)
                out.append((rtype.strip(), _clean_target(t.strip())))
    return out


def _clean_target(t: str) -> str:
    m = WIKILINK.match(t)
    if m:
        return m.group(1).strip()
    return t.strip("[]'\" ").strip()


def parse(path: Path) -> Note:
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body = split_frontmatter(text)
    title = str(fm.get("title") or _first_heading(body) or path.stem)
    links = [m.group(1).strip() for m in WIKILINK.finditer(body)]
    relations = extract_relations(fm)
    # typed relations whose targets are wikilinks should also count as edges
    return Note(path=path, title=title, fm=fm, body=body, links=links, relations=relations)


def _first_heading(body: str) -> str | None:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None
