---
name: exo-gardener
description: Working inside the exocortex vault (~/git/exocortex) — garden passes, writing or editing vault notes, checkpointing decisions. Load whenever touching vault/ markdown; encodes the golden rules, note shape, the gardening routine, and pointers to the standing case law so rulings aren't re-derived.
---

# Exocortex vault work

The vault is shared human+AI memory. Markdown is canonical; the index is a
cache. You are a librarian and gardener, not a hoarder.

## Golden rules (violations happen — check yourself)

1. **Search before you write**: `hybrid_search` (MCP) or `exo search` first.
   Near-duplicate exists → extend/link it, never create a parallel note.
2. **Every write is a small, reviewable git commit.** Set `agent:` on notes
   you author or materially edit.
3. **Link, don't pile**: a new note needs ≥1 `relations:` edge (plain note
   IDs in frontmatter) AND ≥1 body `[[Wikilink]]`. Body links and typed
   relations are different layers — don't mechanically mirror them.
4. After file edits: `EXO_EMBED_BACKEND=none exo index`, then commit; push
   with pull-rebase on rejection (parallel agents write too).

## Note shape

Frontmatter: stable `id` slug; `type` ∈ concept|claim|source|project|person|
log|moc; one-line current `summary:`; `relations:` as plain ID strings
(YAML mangles brackets — wikilinks go in the body only). Projects carry
`lifecycle:`. Template: `vault/templates/note.md`.

## Garden pass routine

1. **Read `vault/10-notes/gardener-policy.md` FIRST** — standing case law.
   Don't re-litigate what it rules on. Highlights (verify against the note):
   radar reconciliation before anything (the Projects MOC reliably lags new
   `lifecycle:` notes); ignore report "summary missing" on notes that carry a
   current summary; preserve original `agent:` on pure pointer appends; job-
   application prep notes stay OFF the Projects radar; garden logs are logs —
   don't enrich them.
2. `garden_report` → propose concrete edits → write → reindex → commit
   `garden: <what changed>`.
3. **Amendment rule**: same skip-reason recorded in two prior logs → graduate
   it into gardener-policy (small diff citing the logs) instead of writing it
   a third time.

## Don'ts

- Never delete a human's note — mark `status:` or move to `90-meta/archive/`.
- Append, don't overwrite human prose. No invented citations.
- **Reporting to János: plain language, outcomes.** He runs the system, not
  its plumbing — no "edges/graph/indexer" jargon.
- Family/private content lives OUTSIDE `vault/` (the viewer serves all of it).
