# exocortex

An external cognitive layer: a shared long-term memory for you and your agents,
built on a plain-markdown vault you own outright.

**Design in one line:** markdown in git is the source of truth; the index,
hybrid search, graph, agents, and 3D visualization are all *derived layers* you
can delete and rebuild. No lock-in, no black box, no single SaaS to trust.

See `docs/ARCHITECTURE.md` for the full reasoning. Quickstart below.

> **Provenance:** this is the real system I run daily, extracted as-is — my
> private vault (a few hundred notes) is swapped for a 4-note demo vault, and
> personal endpoints are `example.com` placeholders. Everything else — CLI,
> MCP server, the bird agents, the gardener, hooks, eval harness — is exactly
> the code that tends my memory every night.

## The fleet — every moving part at a glance

The system is one vault plus a handful of small, single-purpose programs. Nothing
here is magic; each one is a script or a hook you can read.

| Part | What it does | When it runs | Where it lives |
|------|--------------|--------------|----------------|
| **Vault** | markdown source of truth (notes, wikilinks, relations) | always | `vault/` |
| **`exo` CLI** | index, search, garden, collide, status | on demand | `src/exo/` |
| **exocortex MCP** | retrieval/graph tools for agents | per agent session | `exo-mcp` |
| **Viewer** | 3D graph + web UI (single-user SSO) | live | `exocortex.example.com` |
| **Reconciler** | index Synced/OutOfSync + auto-reindex | on commit/merge | `.githooks/`, `exo status` |
| **Gardener** | nightly vault upkeep (orphans, links, summaries) → `garden:` commits | cron **daily 03:00** | `scripts/garden-run.sh` |
| **Wanderer** | task-less serendipity walk — collides *trusted* vault notes | cron **Sun 07:00** | `scripts/wander-run.sh` |
| **Magpie** | GitHub-stars watch — collides *untrusted* external text | cron **Sat 06:00** | `scripts/magpie-run.sh` |
| **WIP sweep** | snapshot dirty human tree → `wip/<host>` (never lose work) | cron **every 20 min** | `~/.local/bin/exo-wip-sweep.sh` |
| **Recall hook** | search the vault on the first prompt of a CC session | UserPromptSubmit | `~/.claude/hooks/exo-recall.sh` |
| **Session-start hook** | fetch/warn/pull this tree, nag about `wip/*` | SessionStart (in this repo) | `~/.claude/hooks/exo-session-start.sh` |
| **n8n receivers** | one-line run report per agent | webhook on each run | `automation/`, `n8n.example.com` |

**The one rule that ties it together — trust boundaries by destination:**
gardener and wanderer read already-trusted notes and write to `vault/` and push to
`main`. Magpie ingests attacker-influenceable text (stranger-written repo
descriptions), so it writes **only** to `quarantine/` (never indexed, never
auto-linked) and you promote finds by hand. The WIP sweep writes unfinished human
work to `wip/<host>` branches — recoverable, but it reaches `main` only by your
hand. Robot checkouts (`exocortex-{garden,wander,magpie}`) hard-reset every run, so
they self-heal and never strand work.

## What you get
- **Vault** (`vault/`) — typed markdown notes, wikilinks, typed relations.
- **Hybrid retrieval** — BM25 + local vectors + graph expansion, with `matched_on`
  explainability. One SQLite file; no extra servers.
- **Two MCP servers** for agents:
  - **Basic Memory** — note CRUD (adopted, not reinvented).
  - **exocortex** (this repo) — `hybrid_search`, `get_backlinks`, `get_neighbors`,
    `list_orphans`, `list_hubs`, `garden_report`, `reindex`, `vault_status`, `collide`.
- **Collision engine** — `exo collide` samples *distant* note pairs (graph hops,
  lexical disjointness, age gap) and asks one question: does anything connect?
  Serendipity as a query — retrieval answers, collide interrupts. Most pairs
  yield nothing by design; genuine hits land in `vault/00-inbox/claude-sparks.md`.
- **Reconciler** — GitOps for the index: `exo status` reports Synced/OutOfSync
  (exit 0/1) by hashing vault files against the index, and `.githooks/`
  (post-commit + post-merge) reindexes automatically. "Files win" is enforced
  by a machine, not remembered by agents.
- **Autonomous gardener** — `exo garden` *deterministically* finds orphans, stale
  summaries, and missing links; Claude acts on them as small, reviewable `garden:`
  git commits (it decides + writes, the detection is plain SQL/graph). Runs
  unattended nightly on the homelab — see "Nightly self-gardening" below.
- **Visualization** — Obsidian 2D + 3D Graph plugin, plus a standalone
  `3d-force-graph` web viewer (`viz/graph3d/`) deployable to the homelab.
- **Automation** — `scripts/garden-run.sh` (the nightly gardener) + an n8n webhook
  that records each run.
- **Homelab deploy** — Dockerfile + k3s manifests (Traefik IngressRoute) + Argo CD app.

## Install (local)
```bash
git clone <this> exocortex && cd exocortex
./scripts/setup.sh            # installs, git-inits, builds the index
# optional local embeddings via Ollama:
ollama pull nomic-embed-text  # then EXO_EMBED_BACKEND=ollama (default)
```
No Ollama? Set `EXO_EMBED_BACKEND=none` — lexical + graph search still work fully.

## MCP wiring (Claude Code / Desktop)
```json
{
  "mcpServers": {
    "basic_memory": { "command": "uvx", "args": ["basic-memory", "mcp"] },
    "exocortex":    { "command": "exo-mcp" }
  }
}
```
Point Basic Memory at `vault/`. Load `CLAUDE.md` as the agent's operating contract.

## Quickstart
```bash
exo index                      # (re)build the index from markdown
exo search "hybrid retrieval"  # explainable hybrid search
exo backlinks hybrid-retrieval
exo hubs                       # most-connected notes (MOC candidates)
exo garden                     # maintenance report for an agent to act on
(cd viz/graph3d && python3 -m http.server 8080)   # 3D brain at :8080
```

## Layout
```
vault/      the knowledge base (open this in Obsidian)
src/exo/    the cognition layer (indexer, retrieval, graph, gardener, MCP, CLI)
viz/        standalone 3D viewer
automation/ n8n workflows
deploy/     Dockerfile + k3s + Argo CD for tc-homelab
docs/       ARCHITECTURE · ONTOLOGY · WORKFLOWS · ROADMAP
CLAUDE.md   agent operating contract
```

## Nightly self-gardening (homelab)
The vault weeds itself. A node-side cron runs `scripts/garden-run.sh` nightly:

```
reset a disposable checkout → exo index → exo garden (deterministic report)
  → claude -p applies only high-confidence edits (≤10 notes), writes a dated
    audit note to vault/00-inbox/, skips anything uncertain
  → exo index → one `garden: <date> …` commit → push
  → POST a run summary to an n8n webhook (run history / notifications)
```

Design choices that keep it safe: a **dedicated checkout** (never touches your
working tree), a **per-night edit cap**, **hermetic** Claude (no MCP, restricted
tools), and — crucially — **every change is one `garden:` commit** you can read with
`git log -p` and undo with `git revert`. Detection is deterministic; the model only
*decides and writes*. (The trigger is node-cron rather than n8n-over-SSH because
Cilium blocks pod→host — see the blog write-up.)

## Why this and not X
- **vs Obsidian-alone:** Obsidian can't give agents structured read/write or
  hybrid retrieval. Here it's the *viewer*; the store is portable markdown.
- **vs embeddings-only RAG:** opaque and can't write back. This is transparent
  (every match explains itself) and bidirectional (agents author notes).
- **vs a graph DB (Neo4j):** unnecessary infra. The graph lives in wikilinks;
  SQLite materializes it. Add a graph DB only if/when queries outgrow this.
- **vs cloud knowledge SaaS:** lock-in. Here, `git clone` is your backup and any
  markdown tool is your fallback.
