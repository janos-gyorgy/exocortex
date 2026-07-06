# quarantine/magpie — untrusted finds, NOT part of the vault

This directory lives **outside `vault/`** on purpose. The [[Magpie]]
(`scripts/magpie-run.sh`) is a weekly agent that reads György's GitHub stars —
**attacker-influenceable text** — and collides them against the active projects.
Its output lands here.

## The boundary (why this is not in the vault)

- `exo index` and the web viewer serve `vault/` only. Nothing here is indexed,
  searched, or reachable from the graph.
- These files use **no YAML frontmatter and no `[[wikilinks]]`** — by design, so
  even an accidental move into `vault/` wouldn't auto-link untrusted text into
  the trust root every other agent reads.
- The wrapper enforces that a Magpie run can change **only** `quarantine/magpie/`.
  Anything it tries to write elsewhere is discarded and reported as a `violation`.

## What lands here

`YYYY-MM-DD.md`, one file per run that had finds. A run with no finds writes
nothing — "nothing connected" is a successful run. Each find names the repo, the
active project/hub it touches, and one concrete "so what."

## Promotion is a human act

If a find is worth keeping, **you** copy it into `vault/` by hand, rewrite it in
your own words, and add the wikilinks. The Magpie never does this. Stale find
files can be deleted freely — they are disposable.
