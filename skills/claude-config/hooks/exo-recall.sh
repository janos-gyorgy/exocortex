#!/usr/bin/env bash
# UserPromptSubmit hook — on the FIRST prompt of each session, search the
# exocortex vault for the prompt and inject the hits as context, so Claude
# consults the vault BEFORE answering. (YOURNAME's rule: search exocortex at the
# start of meaningful work — this enforces it instead of relying on me.)
# Output of a UserPromptSubmit hook is added to the conversation as context.
export HOME="${HOME:-/home/you}"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

input="$(cat)"
sid="$(printf '%s' "$input" | jq -r '.session_id // "nosess"')"
msg="$(printf '%s' "$input" | jq -r '.prompt // .message // ""')"
cwd="$(printf '%s' "$input" | jq -r '.cwd // ""')"
mark="$HOME/.claude/.exo-recall-$sid"

# NEVER run in the disposable robot checkouts (magpie/bluejay/...): `exo search`
# builds index/exocortex.db in-tree there, which trips the corvids' blast-radius
# guard and taints the whole run (bit us 07-04→07-12; exo-session-start.sh has
# the same exclusion). The corvids get curated prompts — no recall wanted anyway.
case "$cwd" in "$HOME/git/exocortex-"*) exit 0;; esac

# tidy stale per-session markers (>1 day)
find "$HOME/.claude" -maxdepth 1 -name '.exo-recall-*' -mtime +1 -delete 2>/dev/null || true

# once per session only
[ -f "$mark" ] && exit 0
: > "$mark"

[ -n "$msg" ] || exit 0
command -v exo >/dev/null 2>&1 || exit 0

# 2026-09-14: searching the whole prompt as one query missed the notes a prompt
# was actually about ("the rook, the playbooks…" → Kimchi notes, garden logs).
# Two deterministic fixes, no model call (an LLM query-split was built and
# measured at 6-27s per session start, so it was dropped — see the model-tiers
# build log):
#   1. NAMED NOTES FIRST: a note whose id appears in the prompt (hyphens/spaces
#      ignored, so "brewbuddy" finds brew-buddy) is shown first, longest id wins.
#   2. GARDEN LOGS DOWN: ~1/3 of the vault is garden-pass logs and they outrank
#      real notes on almost any word; drop them unless the prompt says "garden".
# Anything failing here falls back to the plain search below.
raw="$(exo search "$msg" 2>/dev/null)" || raw="[]"
hits="$(RAW="$raw" MSG="$msg" VAULT="$HOME/git/exocortex/vault" python3 - <<'PY' 2>/dev/null
import json, os, re
msg = os.environ["MSG"].lower()
vault = os.environ["VAULT"]
flat = re.sub(r"[^a-z0-9]+", "", msg)
words = " " + re.sub(r"[^a-z0-9]+", " ", msg) + " "
def front(path):
    meta = {}
    try:
        with open(path, encoding="utf-8") as f:
            if f.readline().strip() != "---":
                return meta
            for line in f:
                if line.strip() == "---":
                    break
                m = re.match(r"^(title|type|summary):\s*(.*)$", line)
                if m:
                    meta[m.group(1)] = m.group(2).strip().strip('"')
    except OSError:
        pass
    return meta
named = []
for root, dirs, files in os.walk(vault):
    dirs[:] = [d for d in dirs if d not in ("templates", ".obsidian")]
    for fn in files:
        if not fn.endswith(".md"):
            continue
        nid = fn[:-3]
        if nid.lower() == "readme" or re.match(r"^garden-\d", nid):
            continue
        spaced = " " + nid.lower().replace("-", " ") + " "
        squashed = nid.lower().replace("-", "")
        if len(squashed) < 4:
            continue
        if spaced in words or ("-" in nid and len(squashed) >= 8 and squashed in flat):
            named.append((len(squashed), nid, os.path.join(root, fn)))
named.sort(reverse=True)
out, seen = [], set()
for _, nid, path in named[:3]:
    m = front(path)
    out.append({"id": nid, "title": m.get("title") or nid,
                "type": m.get("type") or "note", "snippet": m.get("summary") or ""})
    seen.add(nid)
keep_garden = "garden" in msg
try:
    raw = json.loads(os.environ["RAW"])
except ValueError:
    raw = []
for h in raw:
    if len(out) >= 5:
        break
    hid = h.get("id", "")
    if hid in seen or (not keep_garden and re.match(r"^garden-\d", hid)):
        continue
    out.append(h)
    seen.add(hid)
for h in out:
    print("- **%s** (%s) — %s" % (h.get("title"), h.get("type"), (h.get("snippet") or "")[:160]))
PY
)" || hits=""
[ -n "$hits" ] || hits="$(printf '%s' "$raw" \
  | jq -r '.[0:5][] | "- **\(.title)** (\(.type)) — \(.snippet[0:160])"' 2>/dev/null)"
[ -n "$hits" ] || exit 0

printf '### Exocortex recall (auto · first prompt of session)\nThe vault was searched for this prompt; treat as background context, verify before relying on it.\n%s\n' "$hits"
