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
# THE SECURITY CONTRACT LIVES IN scripts/lib/corvid.sh, NOT HERE. The Wanderer is
# a VAULT-EDITOR class bird, not a quarantine one: its diet is YOURNAME's own vault
# rather than stranger text, so it holds Edit and Bash (for `exo search`) — but it
# may still only change ONE file, and the chassis asserts that.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/corvid.sh"

# ── declared containment ──────────────────────────────────────────────────────
# NOTE 2026-09-11: this grant used to be written `--allowedTools`, which is a
# NO-OP under bypassPermissions — the 2026-07-02 correction never reached this
# bird. Declaring it here means the chassis emits `--tools`, so it is now real.
CORVID_TOOLS=(Read Edit Write Bash Glob Grep)   # Bash: `exo search` only, per the prompt
CORVID_COUNT_KEY="pairs"
CORVID_COUNT_VAR="PAIRS"
CORVID_EMIT_FINDS=0            # wanderer's n8n payload has never carried `finds`
CORVID_MAKE_QDIR=0             # writes into vault/, not quarantine/
CORVID_DEDUP=0
CORVID_OK_STATUS=spark
CORVID_AUTHOR=wanderer
CORVID_METER=wanderer          # keep the ledger history continuous (it has always been "wanderer")
CORVID_SCOPE_ALLOW=('^index/' '(^|/)__pycache__/[^/]*\.pyc$')   # wrapper/tooling-owned ignored artifacts

SPARKS="vault/00-inbox/claude-sparks.md"   # the only file the walk may touch
PAIRS=5

corvid_hook_precommit() { exo index >/dev/null; }
corvid_hook_commit_msg() {
  # heading format is "YYYY-MM-DD — title", so it already carries the date
  local h; h="$(git --no-pager diff --cached -- "$SPARKS" | grep '^+## ' | head -1 | sed 's/^+## //')"
  CORVID_DETAIL="${h:-new entry}"
  echo "spark: ${h:-$DAY — new entry}"
}

corvid_init wander "$@"
corvid_sync

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

corvid_think "$PROMPT_FILE"
CORVID_WRITE_SCOPE=("$SPARKS")   # the ONLY path this run may change
corvid_guard
corvid_ship "spark: $DAY" "walked $PAIRS pairs; nothing connected — successful run"
