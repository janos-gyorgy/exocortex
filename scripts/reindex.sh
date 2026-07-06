#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exo index
echo "reindexed -> index/exocortex.db + index/graph.json"
