#!/usr/bin/env bash
# garden-run.sh — nightly exocortex self-gardening.
#
# Runs ON THE HOMELAB NODE (invoked by n8n over SSH on a schedule, or by hand).
# Pipeline:  detect (exo garden) -> apply (claude -p) -> index -> commit -> push.
#
# Isolation: operates on a DEDICATED checkout ($WORK), never the human working
# tree at ~/git/exocortex. The checkout is disposable — hard-reset to origin each
# run. claude edits markdown directly under ./vault; the wrapper owns index+commit.
#
# Usage:
#   garden-run.sh             full run: edits, commits, pushes
#   garden-run.sh --dry-run   edits + reindex, then SHOW the diff and STOP (no commit/push)
set -euo pipefail

# ── environment (SSH/cron hand us a minimal shell) ─────────────────────────────
export HOME="${HOME:-/home/you}"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

REMOTE="git@github.com:YOURNAME/exocortex.git"
WORK="$HOME/git/exocortex-garden"          # dedicated gardener checkout (NOT the human tree)
BRANCH="main"
MAX_NOTES=10                               # cap blast radius per night
export EXO_ROOT="$WORK"                     # point exo at THIS checkout's vault/index
export EXO_EMBED_BACKEND=none               # match web-exocortex: FTS+graph, no Ollama dep

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

# ── logging + single-flight lock ──────────────────────────────────────────────
STATE="$HOME/.local/state/exocortex-garden"
mkdir -p "$STATE"
DAY="$(date -u +%Y-%m-%d)"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LOG="$STATE/garden-$DAY.log"
exec > >(tee -a "$LOG") 2>&1
echo "==== garden run $TS  (dry_run=$DRY_RUN) ===="

# end-of-run notification to n8n for visibility; no-op if unset, never fatal
WEBHOOK="${GARDEN_N8N_WEBHOOK:-}"; STATUS="started"; DETAIL=""
notify() {
  [ -n "$WEBHOOK" ] || return 0
  commit="$(git -C "$WORK" --no-pager log --oneline -1 2>/dev/null || echo n/a)"
  curl -fsS -m 10 -X POST "$WEBHOOK" -H 'Content-Type: application/json' \
    -d "{\"status\":\"$STATUS\",\"day\":\"$DAY\",\"cost_usd\":${RUN_COST_USD:-0},\"tok_in\":${RUN_TOKENS_IN:-0},\"tok_out\":${RUN_TOKENS_OUT:-0},\"detail\":\"${DETAIL//\"/}\",\"commit\":\"${commit//\"/}\"}" \
    >/dev/null 2>&1 || true
}
trap '[ "$STATUS" = started ] && STATUS=failed; [ "$DRY_RUN" = 1 ] || notify' EXIT

exec 9>"$STATE/garden.lock"
if ! flock -n 9; then echo "another garden run is active; exiting"; exit 0; fi

# ── dedicated checkout: clone once, else hard-reset to remote HEAD ─────────────
if [ ! -d "$WORK/.git" ]; then
  echo "cloning gardener checkout -> $WORK"
  git clone --branch "$BRANCH" "$REMOTE" "$WORK"
fi
cd "$WORK"
git fetch --quiet origin "$BRANCH"
git reset --hard "origin/$BRANCH"          # tree is disposable; always start clean from remote
git clean -fdq                             # drop stray files (keeps gitignored index/)

# ── detect ────────────────────────────────────────────────────────────────────
exo index >/dev/null
REPORT="$(exo garden)"
echo "$REPORT" | python3 -c 'import json,sys;d=json.load(sys.stdin);print("report: orphans=%d link_suggestions=%d summary_candidates=%d hubs=%d"%(len(d.get("orphans",[])),len(d.get("link_suggestions",[])),len(d.get("summary_candidates",[])),len(d.get("hubs",[]))))'

NEED="$(echo "$REPORT" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(len(d.get("orphans",[]))+len(d.get("link_suggestions",[]))+len(d.get("summary_candidates",[])))')"
if [ "$NEED" = "0" ]; then STATUS=clean; echo "garden clean; nothing to do"; exit 0; fi

# ── apply via claude (uses your CC subscription; NO api key) ────────────────────
PROMPT_FILE="$STATE/prompt-$DAY.md"
cat > "$PROMPT_FILE" <<EOF
You are the exocortex gardener performing ONE nightly maintenance pass on the
markdown knowledge vault in the CURRENT working directory ($WORK).

Tonight's deterministic garden report (JSON) is between the markers:
<<<REPORT
$REPORT
REPORT

Rules:
- FIRST read ./vault/90-meta/gardener-policy.md — standing case law graduated
  from earlier passes. Don't re-litigate what it rules on; if you're about to
  record a skip-reason that two prior logs already contain, amend the policy
  note (small diff, cite the logs) instead of writing it a third time.
- Operate ONLY on files under ./vault. Edit markdown DIRECTLY with your file tools.
  Do NOT use the Basic Memory MCP — its path points at a different checkout.
- To confirm two notes are really related before linking, search with Bash:
  \`exo search "<terms>"\`  (it is already configured for THIS checkout).
- Make small, atomic, HIGH-CONFIDENCE improvements only, touching at most $MAX_NOTES notes:
    * add [[wikilinks]] between clearly-related notes,
    * add or refresh a one-line frontmatter \`summary:\` where missing or stale,
    * set \`agent: claude-gardener\` on any note you edit.
- Do NOT delete notes, do NOT rewrite human prose, do NOT mass-edit. When unsure, SKIP.
- Finally, write a log note at ./vault/00-inbox/garden-$DAY.md with frontmatter
  (id: garden-$DAY, type: log, agent: claude-gardener, summary: <one line>) whose
  body lists exactly what you changed and what you deliberately skipped, and why.
- Do NOT run git or 'exo index' — the wrapper handles indexing, committing, pushing.
  Your only job is to edit files under ./vault.
EOF

echo "---- claude apply pass ----"
source "$WORK/scripts/lib/claude-metered.sh"
claude_metered gardener "$(cat "$PROMPT_FILE")" \
  --append-system-prompt "$(cat CLAUDE.md)" \
  --permission-mode bypassPermissions \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --allowedTools Read Edit Write Bash Glob Grep

# ── reindex (reflect edits) ─────────────────────────────────────────────────────
exo index >/dev/null

# stage first so NEW notes (untracked, e.g. the garden log) count as changes too
git add -A vault/
if git diff --cached --quiet -- vault/; then
  STATUS=nochanges; echo "claude made no vault changes; nothing to commit"; exit 0
fi

echo "---- proposed changes ----"
git --no-pager diff --cached --stat -- vault/

if [ "$DRY_RUN" = "1" ]; then
  echo "---- DRY RUN: full diff below; NOT committing/pushing ----"
  git --no-pager diff --cached -- vault/
  git reset -q                            # unstage; the checkout is disposable anyway
  echo "dry run complete. inspect above; re-run without --dry-run to commit + push."
  exit 0
fi

# ── commit + push (deterministic, wrapper-owned) ────────────────────────────────
NAMES="$(git diff --cached --name-only -- vault/ | sed 's#vault/##' | paste -sd', ' -)"
git -c user.email=gardener@example.com -c user.name='exocortex gardener' \
    commit -q -m "garden: $DAY — ${NAMES:0:140}"
git push origin "$BRANCH" || {
  echo "push rejected (remote moved mid-run); rebasing this run's commit and retrying once"
  git fetch -q origin "$BRANCH"
  if git rebase origin/"$BRANCH"; then
    git push origin "$BRANCH"
  else
    git rebase --abort 2>/dev/null || true
    STATUS=pushfail; DETAIL="push rebase conflict — left for human"; echo "$DETAIL"; exit 1
  fi
}
STATUS=pushed; DETAIL="$NAMES"
echo "pushed: $(git --no-pager log --oneline -1)"
