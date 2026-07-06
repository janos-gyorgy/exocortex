#!/usr/bin/env bash
# exocortex local setup. Idempotent. Assumes git + python3.11+ (+ uv recommended).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> installing exocortex (editable)"
if command -v uv >/dev/null 2>&1; then
  uv pip install -e .
else
  pip install -e . --break-system-packages
fi

echo "==> git init (audit trail for human + agent edits)"
[ -d .git ] || { git init -q; git add -A; git commit -qm "init: exocortex foundation"; }

echo "==> enabling reconciler hooks (post-commit/post-merge reindex)"
git config core.hooksPath .githooks

echo "==> building index"
exo index

echo "==> Basic Memory (note CRUD MCP) — install with: uvx basic-memory --version"
echo "    point it at: $(pwd)/vault"

cat <<'NEXT'

Done. Next:
  1. Open the vault in Obsidian:  ./vault   (enable 3D Graph + Dataview plugins)
  2. Register MCP servers with your client (see README 'MCP wiring').
  3. 3D viewer:   (cd viz/graph3d && python3 -m http.server 8080)  -> http://localhost:8080
  4. Try:         exo search "your topic"   |   exo garden
NEXT
