#!/usr/bin/env bash
# exo-sync.sh — keep the HUMAN exocortex checkout (~/git/exocortex) current with
# the remote, SAFELY. The automations (gardener/bluejay/magpie/wander) push from
# their own disposable checkouts, so the human tree silently drifts behind.
#
# This does the ONLY reconciliation that is safe to run unattended:
#   - clean tree, behind only        -> git pull --ff-only (no merge, no conflict)
#   - local commits / dirty / diverged -> touch NOTHING, ping the phone via ntfy
#
# It NEVER merges, auto-commits, or resolves conflicts — those need your judgment
# (see the 2026-06-27 summary-vs-relations merge that proved why).
#
# Usage:
#   exo-sync.sh            sync if safe, else notify
# Cron suggestion (after the nightly gardener, e.g. 04:30):
#   30 4 * * * /home/you/git/exocortex/scripts/exo-sync.sh >> ~/.local/state/exo-sync.log 2>&1
set -uo pipefail

ROOT="${EXO_SYNC_ROOT:-$HOME/git/exocortex}"
BRANCH="main"
NTFY_URL="${EXO_SYNC_NTFY_URL:-http://ntfy.example.internal}"   # ntfy ClusterIP — in-house, no internet round-trip
NTFY_TOPIC="${EXO_SYNC_NTFY_TOPIC:-hl-warn}"

notify() {  # title, message — best-effort, never fails the script
  curl -fsS -m 10 -H "Title: $1" -H "Tags: file_cabinet" \
    -d "$2" "$NTFY_URL/$NTFY_TOPIC" >/dev/null 2>&1 || true
}

cd "$ROOT" || { echo "no exocortex checkout at $ROOT"; exit 1; }
git fetch -q origin "$BRANCH" || { echo "fetch failed"; exit 1; }

DIRTY="$(git status --porcelain)"
AHEAD="$(git rev-list --count "origin/$BRANCH..HEAD" 2>/dev/null || echo 0)"   # local-only
BEHIND="$(git rev-list --count "HEAD..origin/$BRANCH" 2>/dev/null || echo 0)"  # remote-only

if [ -n "$DIRTY" ]; then
  [ "$BEHIND" -gt 0 ] && notify "exocortex: sync skipped" \
    "uncommitted changes + $BEHIND new on remote — commit or stash, then pull"
  echo "dirty working tree; skipping (ahead=$AHEAD behind=$BEHIND)"; exit 0
fi

if [ "$AHEAD" -gt 0 ]; then
  notify "exocortex: $AHEAD unpushed commit(s)" \
    "human tree diverged (ahead $AHEAD / behind $BEHIND) — reconcile by hand, then push"
  echo "diverged: ahead=$AHEAD behind=$BEHIND; touching nothing. pinged."; exit 0
fi

if [ "$BEHIND" -gt 0 ]; then
  if git pull --ff-only -q origin "$BRANCH"; then
    echo "fast-forwarded $BEHIND commit(s); current."
  else
    notify "exocortex: ff-only failed" "could not fast-forward $BEHIND commit(s) — check by hand"
    exit 1
  fi
  exit 0
fi

echo "already current."
