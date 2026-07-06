"""exocortex MCP server — the *retrieval & graph intelligence* layer.

Pairs with Basic Memory (which owns note CRUD). This server exposes the things
Basic Memory does not: hybrid retrieval with explainability, graph analytics,
and the gardener report. Any MCP client (Claude Code, Claude Desktop) can call.

Run:  exo-mcp     (stdio transport)
"""
from __future__ import annotations

from . import graph, indexer, maintain, retrieval
from .collide import pairs as collide_pairs
from .status import check as status_check

try:
    from mcp.server.fastmcp import FastMCP
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "MCP SDK not installed. `pip install 'mcp[cli]'` or `uv add mcp`."
    ) from e

mcp = FastMCP("exocortex")


@mcp.tool()
def hybrid_search(query: str, limit: int = 8) -> list[dict]:
    """Search the knowledge base (BM25 + vector + graph). Returns results with
    `matched_on` showing which signals fired — use it to judge confidence."""
    return retrieval.search(query, limit=limit)


@mcp.tool()
def get_backlinks(note_id: str) -> list[dict]:
    """All notes linking TO this note, with relation type."""
    return graph.backlinks(note_id)


@mcp.tool()
def get_neighbors(note_id: str, depth: int = 1) -> dict:
    """Local subgraph around a note, up to `depth` hops. Use before reorganizing."""
    return graph.neighbors(note_id, depth=depth)


@mcp.tool()
def list_orphans() -> list[dict]:
    """Unlinked notes — candidates for connecting into the graph."""
    return graph.orphans()


@mcp.tool()
def list_hubs(limit: int = 15) -> list[dict]:
    """Highest-degree notes — natural Map-of-Content anchors."""
    return graph.hubs(limit=limit)


@mcp.tool()
def collide(pairs: int = 3, min_hops: int = 3) -> list[dict]:
    """Sample distant note pairs and ask only: does anything connect?
    Most pairs yield nothing — say so and move on. On a genuine hit, append it
    to vault/00-inbox/claude-sparks.md with provenance. Never force a finding."""
    return collide_pairs(n=pairs, min_hops=min_hops)


@mcp.tool()
def garden_report() -> dict:
    """Full maintenance report: orphans, hubs, link suggestions, summary candidates.
    Call this, then propose concrete edits the human can review as a git diff."""
    return maintain.report()


@mcp.tool()
def vault_status() -> dict:
    """Vault ↔ index drift check (GitOps-style): Synced or OutOfSync with the
    drifted files listed. If OutOfSync, call reindex() to reconcile."""
    return status_check()


@mcp.tool()
def reindex() -> dict:
    """Rebuild the derived index after files changed on disk."""
    return indexer.build()


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
