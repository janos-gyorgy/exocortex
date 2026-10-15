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

`hooks/` — the exo-recall / session hooks (`~/.claude/hooks` symlinks here): search
the vault on the first prompt of a Claude Code session and inject the hits.
