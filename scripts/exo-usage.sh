#!/usr/bin/env bash
# exo-usage.sh — roll up the exocortex agent usage ledger (cost + tokens).
#
# Reads $EXO_USAGE_LEDGER (default ~/.local/state/exocortex-usage/ledger.jsonl),
# the JSON-lines written by scripts/lib/claude-metered.sh. Node-local telemetry.
#
# Usage:
#   exo-usage.sh            # last 30 days: totals by agent + per-week + grand total
#   exo-usage.sh 7          # last 7 days
#   exo-usage.sh all        # whole ledger
set -euo pipefail
export HOME="${HOME:-/home/you}"
: "${EXO_USAGE_DIR:=$HOME/.local/state/exocortex-usage}"
: "${EXO_USAGE_LEDGER:=$EXO_USAGE_DIR/ledger.jsonl}"
WINDOW="${1:-30}"

[ -f "$EXO_USAGE_LEDGER" ] || { echo "no ledger yet at $EXO_USAGE_LEDGER"; exit 0; }

EXO_USAGE_LEDGER="$EXO_USAGE_LEDGER" WINDOW="$WINDOW" python3 - <<'PY'
import json, os, datetime, collections

path = os.environ["EXO_USAGE_LEDGER"]
win = os.environ["WINDOW"]
today = datetime.date.today()
cutoff = None if win == "all" else today - datetime.timedelta(days=int(win))

rows = []
with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        try:
            day = datetime.date.fromisoformat(r.get("day", ""))
        except Exception:
            day = today
        if cutoff and day < cutoff:
            continue
        rows.append((day, r))

if not rows:
    print(f"ledger has no rows in window '{win}'")
    raise SystemExit

def num(x):
    return x or 0

label = "all time" if win == "all" else f"last {win} days"
print(f"exocortex agent usage — {label}  ({len(rows)} runs)\n")

by_agent = collections.defaultdict(lambda: [0, 0.0, 0, 0])  # runs, cost, in, out
for _, r in rows:
    a = by_agent[r.get("agent", "unknown")]
    a[0] += 1
    a[1] += num(r.get("cost_usd"))
    a[2] += num(r.get("input"))
    a[3] += num(r.get("output"))

print(f"  {'agent':<12} {'runs':>5} {'cost USD':>10} {'tok in':>10} {'tok out':>9}")
print(f"  {'-'*12} {'-'*5} {'-'*10} {'-'*10} {'-'*9}")
gc = gi = go = gr = 0
for agent in sorted(by_agent, key=lambda k: -by_agent[k][1]):
    runs, cost, ti, to = by_agent[agent]
    gr += runs; gc += cost; gi += ti; go += to
    print(f"  {agent:<12} {runs:>5} {cost:>10.4f} {ti:>10,} {to:>9,}")
print(f"  {'-'*12} {'-'*5} {'-'*10} {'-'*10} {'-'*9}")
print(f"  {'TOTAL':<12} {gr:>5} {gc:>10.4f} {gi:>10,} {go:>9,}")

by_week = collections.defaultdict(float)
for day, r in rows:
    monday = day - datetime.timedelta(days=day.weekday())
    by_week[monday] += num(r.get("cost_usd"))
print("\n  by week (Mon):")
for monday in sorted(by_week):
    print(f"    {monday}  ${by_week[monday]:.4f}")
PY
