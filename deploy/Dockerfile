# exocortex MCP + CLI image for k3s
FROM python:3.12-slim
RUN pip install --no-cache-dir uv
WORKDIR /opt/exocortex
COPY pyproject.toml ./
COPY src ./src
RUN uv pip install --system -e .
# vault mounted at runtime; index written to /data/index
ENV EXO_VAULT=/data/vault EXO_INDEX=/data/index EXO_EMBED_BACKEND=ollama \
    OLLAMA_URL=http://ollama.ai.svc.cluster.local:11434
VOLUME ["/data"]
# default: serve the standalone 3D viewer; override cmd for MCP/CLI
COPY viz ./viz
EXPOSE 8080
CMD ["sh","-c","exo index || true; cd viz/graph3d && python -m http.server 8080"]
