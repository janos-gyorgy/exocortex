#!/usr/bin/env bash
# wander-run.sh — weekly exocortex idle walk (the Wanderer).
#
# Runs ON THE HOMELAB NODE (cron, Sunday morning, or by hand).
# Pipeline:  collide (exo collide) -> walk (claude -p) -> index -> commit -> push.
#
# The walk has ONE task: read 5 distant note pairs and ask "does anything
# connect?" A run that changes nothing is a SUCCESSFUL run — the wrapper
# always reports to n8n, so the agent never needs a finding to have a
# deliverable. See vault/30-projects/wanderer.md for the design contract.
#
# Isolation: dedicated checkout ($WORK), hard-reset each run, like the gardener.
# Blast radius: the ONLY file the walk may change is vault/00-inbox/claude-sparks.md.
# The wrapper ENFORCES this — any other change is discarded and flagged.
#
# Usage:
#   wander-run.sh             full run: walk, commit spark (if any), push
#   wander-run.sh --dry-run   walk + show diff, then STOP (no commit/push)
set -euo pipefail

# ── environment (cron hands us a minimal shell) ────────────────────────────────
export HOME="${HOME:-/home/you}"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

REMOTE="git@github.com:YOURNAME/exocortex.git"
WORK="$HOME/git/exocortex-wander"          # dedicated wanderer checkout (NOT the human tree)
BRANCH="main"
SPARKS="vault/00-inbox/claude-sparks.md"   # the only file the walk may touch
PAIRS=5
export EXO_ROOT="$WORK"
export EXO_EMBED_BACKEND=none

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

# ── logging + single-flight lock ──────────────────────────────────────────────
STATE="$HOME/.local/state/exocortex-wander"
mkdir -p "$STATE"
DAY="$(date -u +%Y-%m-%d)"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
LOG="$STATE/wander-$DAY.log"
exec > >(tee -a "$LOG") 2>&1
echo "==== wander run $TS  (dry_run=$DRY_RUN) ===="

# end-of-run notification to n8n; "nothing" is a success status, not a failure
WEBHOOK="${WANDER_N8N_WEBHOOK:-}"; STATUS="started"; DETAIL=""
notify() {
  [ -n "$WEBHOOK" ] || return 0
  commit="$(git -C "$WORK" --no-pager log --oneline -1 2>/dev/null || echo n/a)"
  curl -fsS -m 10 -X POST "$WEBHOOK" -H 'Content-Type: application/json' \
    -d "{\"status\":\"$STATUS\",\"day\":\"$DAY\",\"pairs\":$PAIRS,\"cost_usd\":${RUN_COST_USD:-0},\"tok_in\":${RUN_TOKENS_IN:-0},\"tok_out\":${RUN_TOKENS_OUT:-0},\"detail\":\"${DETAIL//\"/}\",\"commit\":\"${commit//\"/}\"}" \
    >/dev/null 2>&1 || true
}
trap '[ "$STATUS" = started ] && STATUS=failed; [ "$DRY_RUN" = 1 ] || notify' EXIT

exec 9>"$STATE/wander.lock"
if ! flock -n 9; then echo "another wander run is active; exiting"; exit 0; fi

# ── dedicated checkout: clone once, else hard-reset to remote HEAD ─────────────
if [ ! -d "$WORK/.git" ]; then
  echo "cloning wanderer checkout -> $WORK"
  git clone --branch "$BRANCH" "$REMOTE" "$WORK"
fi
cd "$WORK"
git fetch --quiet origin "$BRANCH"
git reset --hard "origin/$BRANCH"
git clean -fdxq                              # -x: also wipe ignored cruft (.env / stale index/*) → pristine

# ── collide: pick this week's walk ─────────────────────────────────────────────
exo index >/dev/null
COLLISIONS="$(exo collide -n "$PAIRS")"
RECENT="$(git --no-pager log --oneline --since='8 days ago' -- vault/ | head -20 || true)"
echo "walk: $PAIRS pairs sampled; $(echo "$RECENT" | grep -c . || true) vault commits this week"

# ── the walk (claude -p; uses the CC subscription; NO api key) ──────────────────
PROMPT_FILE="$STATE/prompt-$DAY.md"
cat > "$PROMPT_FILE" <<EOF
You are the exocortex Wanderer on your weekly idle walk through the markdown
knowledge vault in the CURRENT working directory ($WORK).

You have NO task except this: below are $PAIRS pairs of notes that are far
apart in the vault — different corners, different eras, few shared words.
For each pair, READ BOTH NOTES IN FULL (paths are in the JSON), then ask:
does anything genuinely connect? A new idea, a contradiction worth naming,
a thing worth trying that neither note contains alone.

This week's pairs:
<<<COLLISIONS
$COLLISIONS
COLLISIONS

Vault commits in the last week, for fresh context:
<<<RECENT
$RECENT
RECENT

The contract (this is the whole point — honor it exactly):
- "Nothing connects" is the EXPECTED outcome for most pairs and a fully
  successful walk. The wrapper reports your run either way; you do NOT need
  a finding to have done your job. Do not manufacture one.
- If — and only if — something genuinely fires, append an entry to ./$SPARKS in
  the [Type · Lens] shape defined at the TOP of that file (read its header first):
    ## [Type · Lens] short imperative title
    - **Do:** the concrete move, one line.
    - **Seed:** which two notes collided and what fired.
  Types: Build | Try | Learn | Blog | Change (can be fundamental) | or coin one if
  none fit. Lenses: Play | Work | Claude (only if it honestly pulls at YOU the
  agent — a manufactured Claude want is worse than none). Flag 🎫 GOLDEN TICKET if
  the collision seeds a product that could feed his family (rare, high bar, fuller
  note: what / who pays / why him / why now). Two lines per spark — if it needs an
  essay it isn't one. Quality bar: would a busy human stop and ACT? If not, skip.
- One entry per genuine hit; if several pairs truly fire, log them all.
  The bar does not drop because the first one passed it.
- $SPARKS is the ONLY file you may modify. The wrapper discards any other
  change. Do NOT run git or 'exo index' — the wrapper owns those.
- You may use Bash \`exo search "<terms>"\` to check whether an idea already
  exists in the vault before writing it. If it exists, it is not a spark.
EOF

echo "---- claude walk ----"
source "$WORK/scripts/lib/claude-metered.sh"
claude_metered wanderer "$(cat "$PROMPT_FILE")" \
  --append-system-prompt "$(cat CLAUDE.md)" \
  --permission-mode bypassPermissions \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --allowedTools Read Edit Write Bash Glob Grep

# ── enforce blast radius: ONLY $SPARKS may change — tracked, untracked OR ignored.
# A run that wrote anything else is TAINTED: commit/push NOTHING and exit nonzero.
# Allowlist index/ and __pycache__ — wrapper/tooling-owned ignored artifacts (the
# wrapper runs `exo index`; the model is told not to). `git status --ignored`
# catches .env / out-of-bounds writes that `git add` would silently skip.
STRAY="$(git status --porcelain --untracked-files=all --ignored=matching | cut -c4- \
         | grep -vE "^${SPARKS}$|^index/|__pycache__/" || true)"
if [ -n "$STRAY" ]; then
  echo "BLAST RADIUS VIOLATION — run tainted; committing/pushing NOTHING. Out-of-bounds paths:"
  echo "$STRAY"
  git reset -q 2>/dev/null || true; git checkout -- . 2>/dev/null || true; git clean -fdxq
  STATUS=violation; DETAIL="stray: ${STRAY//$'\n'/, }"
  exit 1   # trap fires notify(violation); tainted output never ships
fi

git add -- "$SPARKS" 2>/dev/null || true
if git diff --cached --quiet; then
  STATUS=nothing; echo "walked $PAIRS pairs; nothing connected — successful run"; exit 0
fi

echo "---- proposed spark ----"
git --no-pager diff --cached -- "$SPARKS"

if [ "$DRY_RUN" = "1" ]; then
  echo "---- DRY RUN: NOT committing/pushing ----"
  git reset -q
  exit 0
fi

# ── commit + push (wrapper-owned) ───────────────────────────────────────────────
# heading format is "YYYY-MM-DD — title", so it already carries the date
HEADING="$(git --no-pager diff --cached -- "$SPARKS" | grep '^+## ' | head -1 | sed 's/^+## //')"
exo index >/dev/null
git -c user.email=wanderer@example.com -c user.name='exocortex wanderer' \
    commit -q -m "spark: ${HEADING:-$DAY — new entry}"
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
STATUS=spark; DETAIL="${HEADING:-new entry}"
echo "pushed: $(git --no-pager log --oneline -1)"
