# skills/ — Claude Code personal skills (versioned)

`claude/` is the live skills directory: `~/.claude/skills` is a **symlink**
pointing here, so every session loads these from any launch dir, and every
edit is a normal git diff in this repo.

- Edit a skill = edit `claude/<name>/SKILL.md`, commit.
- New skills appear in Claude's list on the next session.
- Outside `vault/` on purpose — the viewer serves all of vault/; these are
  tooling, not knowledge notes.
- If the symlink ever breaks: `ln -s ~/git/exocortex/skills/claude ~/.claude/skills`

## claude-config/

The global operating layer, same symlink pattern:
- `CLAUDE.md` — the working contract (`~/.claude/CLAUDE.md` symlinks here)
- `hooks/` — exo-recall/session hooks (`~/.claude/hooks` symlinks here)
- `settings.snapshot.json` — a tracked **copy** of `~/.claude/settings.json`,
  NOT a symlink: Claude Code rewrites that file itself and a rewrite would
  silently replace a symlink. Refresh the snapshot after changing settings.
- Never version `~/.claude.json` or `.credentials.json` — secrets.
