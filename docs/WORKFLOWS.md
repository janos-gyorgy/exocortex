# Recommended Workflows

## 1. Capture (low friction)
Drop anything into `vault/00-inbox/`. A line, a link, a thought. No schema
required at capture time. Triage later (you or the gardener).

## 2. Ingest a URL (n8n: automation/n8n/ingest-url.json)
Webhook → fetch → readability extract → write `20-sources/<slug>.md` from the
`source.md` template (`ingested_by: agent`) → `exo index`. Then an agent
summarizes and links it on the next gardener pass.

## 3. Ask the exocortex (Claude Code / Desktop)
> "What do I know about hybrid retrieval, and what contradicts it?"

Agent calls `hybrid_search("hybrid retrieval")`, then `get_neighbors` on the top
hit, follows `contradicts` edges. Answers from *your* notes, with paths to verify.

## 4. Autonomous maintenance (nightly)
CronJob/n8n → `exo garden` → feed report to an agent run with CLAUDE.md loaded.
The agent: links orphans, refreshes stale summaries, promotes hubs to MOCs,
commits as `garden: ...`. You review the diff over coffee.

## 5. Develop a thought
Search first. If a note exists, open it in Obsidian, extend it, add relations.
If not, `templates/note.md`, write the atomic idea, link it to ≥1 existing note.

## 6. Explore spatially
- Obsidian: native graph (2D) + 3D Graph plugin (local + global views).
- Standalone: `python -m http.server` in `viz/graph3d/` (reads `index/graph.json`),
  or deploy it to the homelab behind Traefik for a shareable 3D brain.

## Example agent session (Claude Code)
```
$ claude
> Reindex, then show me orphans and propose links for the top 3.
  [agent] reindex() → 142 notes
  [agent] list_orphans() → 9
  [agent] for each: hybrid_search(title) → candidates
  [agent] proposes edits, writes via Basic Memory, reindex()
  [agent] git commit -m "garden: linked 3 orphans into retrieval MOC"
```

## Commit conventions
- `note: <title>` new/edited human note
- `garden: <change>` autonomous maintenance
- `ingest: <source>` pipeline-added source
- `refactor: <scope>` structural reorg (split/merge/move)
