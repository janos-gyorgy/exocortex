# CLAUDE.md — Operating contract for agents in the exocortex

You are an agent working inside a **shared human+AI memory**. The markdown vault
is the source of truth. You are a librarian and gardener, not a hoarder.

## Golden rules
1. **Markdown is canonical.** Never treat the SQLite index as authoritative. If
   files and index disagree, the files win. Drift is detected (`exo status` /
   `vault_status`, Synced/OutOfSync) and auto-reconciled by git hooks
   (`.githooks/`, post-commit + post-merge). If a checkout lacks the hooks
   (`git config core.hooksPath .githooks`), fall back to `exo index` by hand.
2. **Every write is a reviewable git diff.** Make small, atomic commits. Set the
   `agent:` frontmatter field on notes you author or materially edit.
3. **Search before you write.** Call `hybrid_search` first. If a near-duplicate
   exists, extend or link it — do not create a parallel note.
4. **Link, don't pile.** A new note with no relations is half-done. Add at least
   one `relations:` edge (note IDs) and at least one body `[[Wikilink]]`.
5. **Explain non-trivial changes.** One line in the commit / note `summary:` is
   enough. No ceremony.

## Tools you have
- Retrieval & graph (this repo's MCP server `exocortex`): `hybrid_search`,
  `get_backlinks`, `get_neighbors`, `list_orphans`, `list_hubs`,
  `garden_report`, `reindex`, `vault_status`, `collide` (distant-pair
  serendipity; a "no connection" result is valid — only log genuine hits to
  claude-sparks).
- Note CRUD (Basic Memory MCP): create/read/edit/move notes. Use it for writes.
- Shell (Claude Code): `exo` CLI, git, ripgrep.

## Note shape (see vault/templates/note.md)
- `id` is a stable slug. `type` ∈ concept|claim|source|project|person|log|moc.
- Relations reference **note IDs as plain strings**. Wikilinks `[[...]]` go in
  the **body only** (YAML mangles brackets).
- Keep `summary:` to one line and current.

## Routine: nightly gardener
1. `garden_report` → review orphans, hubs, link suggestions, summary candidates.
2. Propose concrete edits. For each: search to confirm, then write via Basic
   Memory, then `reindex`.
3. Promote dense hubs to `type: moc` when a domain has >~8 connected notes.
4. Commit with message `garden: <what changed>`.

## Don'ts
- Don't delete a human's note; mark `status` or move to `90-meta/archive/`.
- Don't rewrite voice/wording of human-authored notes; append, don't overwrite.
- Don't invent citations. Empty `source:` is fine.

## Token discipline
Prefer `hybrid_search` snippets over reading whole files. Read full notes only
when editing them. Batch related edits before reindexing.
