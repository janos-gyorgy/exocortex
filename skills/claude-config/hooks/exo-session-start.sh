#!/usr/bin/env bash
# SessionStart hook — the READ side of the git-sync protocol. Only acts in the
# HUMAN exocortex working tree (~/git/exocortex); the disposable robot checkouts
# (garden/wander/magpie) hard-reset every run and are deliberately excluded.
# Fetches, warns on dirty/behind, auto-pulls only when clean, and nags about
# any wip/* safety branches so they get graduated or deleted.
export HOME="${HOME:-/home/you}"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

input="$(cat)"
cwd="$(printf '%s' "$input" | jq -r '.cwd // ""')"
[ "$cwd" = "$HOME/git/exocortex" ] || exit 0
cd "$cwd" 2>/dev/null || exit 0

git fetch -q origin main 2>/dev/null || true
dirty="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
behind="$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)"
wips="$(git ls-remote --heads origin 'wip/*' 2>/dev/null | wc -l | tr -d ' ')"

out="### exocortex tree status (SessionStart)"
[ "${dirty:-0}" -gt 0 ] && out="$out"$'\n'"- ⚠ ${dirty} uncommitted file(s) in this tree"
if [ "${behind:-0}" -gt 0 ]; then
  if [ "${dirty:-0}" -eq 0 ]; then
    git pull -q --rebase origin main 2>/dev/null \
      && out="$out"$'\n'"- pulled ${behind} commit(s) from origin/main (tree was clean)"
  else
    out="$out"$'\n'"- ⚠ behind origin/main by ${behind}; tree dirty → not auto-pulling, resolve by hand"
  fi
fi
[ "${wips:-0}" -gt 0 ] && out="$out"$'\n'"- 🌿 ${wips} wip/* branch(es) on origin — finish & merge to main, or delete"

# only emit if there's something worth saying beyond the header
[ "$out" != "### exocortex tree status (SessionStart)" ] && printf '%s\n' "$out"
exit 0
