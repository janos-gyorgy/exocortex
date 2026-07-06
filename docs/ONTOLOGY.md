# Ontology & Folder Strategy

## Principle
Folders are coarse buckets for humans. **Links are the real structure.** Don't
build deep folder trees; build a dense link graph. A note's meaning comes from its
edges, not its path.

## Folders
```
vault/
  00-inbox/      Unprocessed capture. Agents/you triage out of here.
  10-notes/      Atomic notes — one idea each (Zettelkasten core).
  20-sources/    Ingested external material (articles, papers, clips).
  30-projects/   Active work with outcomes (e.g. Angel/Devil, NanoCamelid).
  40-maps/       Maps of Content (MOCs) — curated entry points.
  90-meta/       System notes, ontology, agent logs, archive/.
  templates/     Note templates.
```

## Frontmatter schema
| field      | required | values / notes |
|------------|----------|----------------|
| `id`       | yes      | stable slug, lowercase-hyphen |
| `type`     | yes      | `concept` `claim` `source` `project` `person` `log` `moc` |
| `title`    | yes      | human title |
| `tags`     | no       | flat list |
| `status`   | no       | `seedling` → `budding` → `evergreen` (note maturity) |
| `created`  | yes      | ISO date |
| `updated`  | no       | ISO date; agents bump on edit |
| `summary`  | no       | one line; kept current by the gardener |
| `relations`| no       | typed edges, **targets = note IDs** |
| `source`   | no       | url/citation |
| `agent`    | no       | which agent authored/edited |

## Relation vocabulary (typed edges)
Start small; extend deliberately. Targets are note **IDs** (plain strings), never
`[[wikilinks]]` (YAML mangles brackets).

| relation       | meaning |
|----------------|---------|
| `supports`     | this note provides evidence/argument for the target |
| `contradicts`  | this note opposes the target |
| `derived_from` | this note was produced from the target (source → note) |
| `part_of`      | this note is a component of the target (often a MOC) |
| `refines`      | this note sharpens/supersedes the target |
| `related`      | weak association when nothing stronger fits |

Plain `[[Wikilinks]]` in the body become `rel: link` edges — your default,
low-friction connection. Reserve typed relations for meaning you'll query on.

## Note maturity (status)
- `seedling` — raw, captured, may be wrong.
- `budding` — developed, linked, but still moving.
- `evergreen` — stable, trustworthy, safe to cite. Agents prefer evergreen notes
  as sources and are conservative about editing them.

## Naming
- Filenames = `id`.md where practical.
- One idea per note. If a note needs two `#` H1-level ideas, split it.
- MOCs are the exception: they're allowed to be broad indexes.

## Multi-agent etiquette (encoded in CLAUDE.md, summarized here)
- Agents stamp `agent:` and commit atomically.
- Agents never overwrite human prose; they append or link.
- Conflict resolution is git, not magic. Humans review diffs.
