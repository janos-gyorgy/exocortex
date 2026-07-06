"""`exo` CLI. Thin wrapper over the library; stable surface for cron/n8n/agents."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__, collide, graph, indexer, maintain, retrieval, status
from .config import CONFIG


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_index(_a) -> int:
    _print(indexer.build())
    return 0


def cmd_search(a) -> int:
    _print(retrieval.search(a.query, limit=a.limit, expand=not a.no_expand))
    return 0


def cmd_backlinks(a) -> int:
    _print(graph.backlinks(a.id))
    return 0


def cmd_neighbors(a) -> int:
    _print(graph.neighbors(a.id, depth=a.depth))
    return 0


def cmd_orphans(_a) -> int:
    _print(graph.orphans())
    return 0


def cmd_hubs(a) -> int:
    _print(graph.hubs(limit=a.limit))
    return 0


def cmd_garden(_a) -> int:
    _print(maintain.report())
    return 0


def cmd_collide(a) -> int:
    _print(collide.pairs(n=a.pairs, min_hops=a.min_hops, seed=a.seed))
    return 0


def cmd_status(_a) -> int:
    report = status.check()
    _print(report)
    return 0 if report["status"] == "Synced" else 1


def cmd_info(_a) -> int:
    _print({
        "version": __version__,
        "root": str(CONFIG.root),
        "vault": str(CONFIG.vault),
        "index_db": str(CONFIG.index_db),
        "embed_backend": CONFIG.embed_backend,
        "embed_model": CONFIG.embed_model,
    })
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="exo", description="exocortex cognition layer")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("index", help="(re)build the index from the vault").set_defaults(fn=cmd_index)
    sub.add_parser("status", help="vault vs index drift: Synced/OutOfSync (exit 0/1)").set_defaults(fn=cmd_status)
    sub.add_parser("info", help="show config").set_defaults(fn=cmd_info)
    sub.add_parser("orphans", help="list unlinked notes").set_defaults(fn=cmd_orphans)
    sub.add_parser("garden", help="emit maintenance report").set_defaults(fn=cmd_garden)

    s = sub.add_parser("search", help="hybrid search"); s.set_defaults(fn=cmd_search)
    s.add_argument("query"); s.add_argument("-l", "--limit", type=int, default=8)
    s.add_argument("--no-expand", action="store_true")

    s = sub.add_parser("collide", help="sample distant note pairs — serendipity, not search")
    s.set_defaults(fn=cmd_collide)
    s.add_argument("-n", "--pairs", type=int, default=3)
    s.add_argument("--min-hops", type=int, default=3)
    s.add_argument("--seed", type=int, default=None)

    s = sub.add_parser("backlinks"); s.set_defaults(fn=cmd_backlinks); s.add_argument("id")
    s = sub.add_parser("neighbors"); s.set_defaults(fn=cmd_neighbors)
    s.add_argument("id"); s.add_argument("-d", "--depth", type=int, default=1)
    s = sub.add_parser("hubs"); s.set_defaults(fn=cmd_hubs); s.add_argument("-l", "--limit", type=int, default=15)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
