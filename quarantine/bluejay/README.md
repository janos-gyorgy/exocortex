# quarantine/bluejay — untrusted serendipity sparks, NOT part of the vault

This directory lives **outside `vault/`** on purpose. The Bluejay
(`scripts/bluejay-run.sh`) is the weekly serendipity sibling of the Magpie: it
reads an allowlist of tech + science RSS feeds — **attacker-influenceable text**
— and collides their *summaries* against the vault to seed ideas. Its output
lands here.

## The boundary (why this is not in the vault)

- `exo index` and the web viewer serve `vault/` only. Nothing here is indexed,
  searched, or reachable from the graph.
- These files use **no YAML frontmatter and no `[[wikilinks]]`** — by design, so
  even an accidental move into `vault/` wouldn't auto-link untrusted text into
  the trust root every other agent reads.
- The wrapper enforces that a Bluejay run can change **only** `quarantine/bluejay/`.
  Anything it tries to write elsewhere is discarded and reported as a `violation`.
- **Summaries only:** the fetcher (`scripts/bluejay-fetch.py`) reads the RSS
  summary field, never the full article body. You click through by hand.

## Magpie vs Bluejay (why two birds)

- **Magpie** = relevance filter on structured sources (GitHub stars). Fires only
  on a live-work hit. → `quarantine/magpie/`.
- **Bluejay** = serendipity filter on open prose. Surfaces the *distant*
  connection — the idea seed that isn't in the projects yet. → here.

## What lands here

`YYYY-MM-DD.md`, one file per run that had sparks. A run with no sparks writes
nothing — "nothing sparked" is a successful run. Each spark names the item, the
vault note/idea it collides with, and one concrete seed (a new idea or question).

## Promotion is a human act

If a spark is worth keeping, **you** copy it into `vault/` by hand, rewrite it in
your own words, and add the wikilinks. The Bluejay never does this. Stale spark
files can be deleted freely — they are disposable.
