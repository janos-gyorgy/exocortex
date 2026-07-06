#!/usr/bin/env bash
# SessionStart(clear|compact) hook — wipe the per-session recall marker so the
# first prompt AFTER a /clear or /compact re-fires exo-recall.sh (the prompt-aware
# vault recall). /clear and /compact keep the SAME session_id, so without this the
# marker `.exo-recall-$sid` persists and recall never re-fires within the session.
export HOME="${HOME:-/home/you}"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
input="$(cat)"
sid="$(printf '%s' "$input" | jq -r '.session_id // "nosess"')"
rm -f "$HOME/.claude/.exo-recall-$sid" 2>/dev/null || true
exit 0
