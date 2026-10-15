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
# THE SECURITY CONTRACT LIVES IN scripts/lib/corvid.sh, NOT HERE. The Gardener is
# the widest-scoped bird in the fleet: the quarantine birds may change one file,
# the Wanderer one file inside vault/, and this one may edit ANY note under vault/.
# Its diet is YOURNAME's own vault rather than stranger text — that is what buys it
# the wider scope. The chassis now asserts that subtree boundary, which this bird
# previously had no enforcement for at all.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/corvid.sh"

# ── declared containment ──────────────────────────────────────────────────────
# NOTE 2026-09-11: this grant used to be written `--allowedTools`, a NO-OP under
# bypassPermissions — the 2026-07-02 correction never reached this bird. Declared
# here, the chassis emits `--tools`, so the grant is now actually enforced.
CORVID_TOOLS=(Read Edit Write Bash Glob Grep)   # Bash: `exo search` only, per the prompt
CORVID_TIER=standard                  # model tier -> scripts/lib/models.sh (aliases, never IDs)
CORVID_GUARD_MODE=subtree
CORVID_SCOPE_ALLOW=('^index/' '(^|/)__pycache__/[^/]*\.pyc$')
CORVID_MAX_FILES=0             # 0 = uncapped, preserving today's behaviour exactly.
                               # Set to e.g. 25 to make MAX_NOTES *enforced* rather
                               # than merely requested — a deliberate tightening.
CORVID_CLEAN_IGNORED=0         # keep gitignored index/ so the nightly run need not rebuild it
CORVID_MAKE_QDIR=0             # writes into vault/, not quarantine/
CORVID_DEDUP=0
CORVID_EMIT_FINDS=0            # garden's n8n payload has never carried `finds`
CORVID_OK_STATUS=pushed
CORVID_NOTHING_STATUS=nochanges
CORVID_AUTHOR=gardener
CORVID_METER=gardener          # keep the ledger history continuous (it has always been "gardener")

MAX_NOTES=10                   # cap asked of the model in the prompt

corvid_hook_commit_msg() {
  local names; names="$(git diff --cached --name-only -- vault/ | sed 's#vault/##' | paste -sd', ' -)"
  CORVID_DETAIL="$names"
  echo "garden: $DAY — ${names:0:140}"
}

corvid_init garden "$@"
corvid_sync
CORVID_WRITE_SCOPE=("vault/" "logs/garden/")  # the only subtrees this run may change (pass logs live outside vault/, 2026-10-06)

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
- Finally, write a pass log at ./logs/garden/garden-$DAY.md (OUTSIDE vault/ — never indexed) with frontmatter
  (id: garden-$DAY, type: log, agent: claude-gardener, summary: <one line>) whose
  body lists exactly what you changed and what you deliberately skipped, and why.
- Do NOT run git or 'exo index' — the wrapper handles indexing, committing, pushing.
  Your only job is to edit files under ./vault.
EOF

corvid_think "$PROMPT_FILE"
exo index >/dev/null           # reflect the edits before the guard inspects the tree
corvid_guard
corvid_ship "garden: $DAY" "claude made no vault changes; nothing to commit"
