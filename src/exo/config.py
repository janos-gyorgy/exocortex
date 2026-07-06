"""Central configuration. Everything is env-overridable; sane local defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _root() -> Path:
    # repo root = two parents up from this file (src/exo/config.py -> repo)
    env = os.environ.get("EXO_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    root: Path
    vault: Path
    index_db: Path
    graph_json: Path

    # embedding backend: "ollama" | "sentence-transformers" | "none"
    embed_backend: str
    ollama_url: str
    embed_model: str
    embed_dim: int

    # retrieval weights (hybrid fusion)
    w_bm25: float
    w_vector: float
    w_graph: float

    @classmethod
    def load(cls) -> "Config":
        root = _root()
        vault = Path(os.environ.get("EXO_VAULT", root / "vault")).expanduser().resolve()
        index_dir = Path(os.environ.get("EXO_INDEX", root / "index")).expanduser().resolve()
        index_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            root=root,
            vault=vault,
            index_db=index_dir / "exocortex.db",
            graph_json=index_dir / "graph.json",
            embed_backend=os.environ.get("EXO_EMBED_BACKEND", "ollama"),
            ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            embed_model=os.environ.get("EXO_EMBED_MODEL", "nomic-embed-text"),
            embed_dim=int(os.environ.get("EXO_EMBED_DIM", "768")),
            w_bm25=float(os.environ.get("EXO_W_BM25", "1.0")),
            w_vector=float(os.environ.get("EXO_W_VECTOR", "1.0")),
            # Graph expansion measurably HURTS ranked search and never helped:
            # 0.5 buried the right answer (2026-06-15); 0.1 still cost MRR
            # (live 0.683 vs bm25 0.760) until zeroed (2026-06-28) — at w_graph=0,
            # live === bm25 (MRR 0.760, R@5 0.883). Default off for hybrid_search
            # fusion; graph edges still drive collide/neighbors directly, not via this.
            # Revisit only if vectors come on and interact differently. Benchmarks:
            # docs/benchmarks/2026-06-{15,28}-exo-retrieval-v1.md.
            w_graph=float(os.environ.get("EXO_W_GRAPH", "0.0")),
        )


CONFIG = Config.load()
