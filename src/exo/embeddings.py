"""Embedding backends. Local-first by default (Ollama on the homelab).

Order of preference, controlled by EXO_EMBED_BACKEND:
  ollama                -> POST {OLLAMA_URL}/api/embeddings  (nomic-embed-text)
  sentence-transformers -> local CPU model, no network
  none                  -> vector layer disabled; FTS + graph still fully work

Embeddings are derived artifacts. If the backend is unavailable, indexing still
succeeds — you just lose the semantic-recall booster, not the system.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Sequence

from .config import CONFIG


class Embedder:
    def __init__(self) -> None:
        self.backend = CONFIG.embed_backend
        self.dim = CONFIG.embed_dim
        self._st_model = None
        if self.backend == "sentence-transformers":
            self._load_st()

    def _load_st(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore

            model_name = CONFIG.embed_model
            if "/" not in model_name:
                model_name = "sentence-transformers/all-MiniLM-L6-v2"
            self._st_model = SentenceTransformer(model_name)
            self.dim = self._st_model.get_sentence_embedding_dimension()
        except Exception:
            self.backend = "none"

    @property
    def enabled(self) -> bool:
        return self.backend != "none"

    def embed(self, texts: Sequence[str]) -> list[list[float]] | None:
        if not self.enabled or not texts:
            return None
        if self.backend == "ollama":
            return self._embed_ollama(list(texts))
        if self.backend == "sentence-transformers" and self._st_model is not None:
            vecs = self._st_model.encode(list(texts), normalize_embeddings=True)
            return [list(map(float, v)) for v in vecs]
        return None

    def _embed_ollama(self, texts: list[str]) -> list[list[float]] | None:
        out: list[list[float]] = []
        url = f"{CONFIG.ollama_url}/api/embeddings"
        for t in texts:
            payload = json.dumps({"model": CONFIG.embed_model, "prompt": t}).encode()
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read().decode())
                vec = data.get("embedding")
                if not vec:
                    return None
                out.append([float(x) for x in vec])
                self.dim = len(vec)
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                # Ollama not reachable -> degrade gracefully
                self.backend = "none"
                return None
        return out
