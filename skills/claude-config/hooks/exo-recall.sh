#!/usr/bin/env bash
# UserPromptSubmit hook — on the FIRST prompt of each session, search the
# exocortex vault for the prompt and inject the hits as context, so Claude
# consults the vault BEFORE answering. (György's rule: search exocortex at the
# start of meaningful work — this enforces it instead of relying on me.)
# Output of a UserPromptSubmit hook is added to the conversation as context.
export HOME="${HOME:-/home/you}"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

input="$(cat)"
sid="$(printf '%s' "$input" | jq -r '.session_id // "nosess"')"
msg="$(printf '%s' "$input" | jq -r '.prompt // .message // ""')"
mark="$HOME/.claude/.exo-recall-$sid"

# tidy stale per-session markers (>1 day)
find "$HOME/.claude" -maxdepth 1 -name '.exo-recall-*' -mtime +1 -delete 2>/dev/null || true

# once per session only
[ -f "$mark" ] && exit 0
: > "$mark"

[ -n "$msg" ] || exit 0
command -v exo >/dev/null 2>&1 || exit 0

hits="$(exo search "$msg" 2>/dev/null \
  | jq -r '.[0:5][] | "- **\(.title)** (\(.type)) — \(.snippet[0:160])"' 2>/dev/null)"
[ -n "$hits" ] || exit 0

printf '### Exocortex recall (auto · first prompt of session)\nThe vault was searched for this prompt; treat as background context, verify before relying on it.\n%s\n' "$hits"
