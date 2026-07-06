# tools

The session-continuity helpers that used to live here grew up and moved to
their own repos:

- **claude-watchtower** (`wt`) — session front-door / picker / SSH greeting →
  https://github.com/janos-gyorgy/claude-watchtower
- **claude-compass** — deterministic local hook-guard (blocks dangerous tool
  calls, warns on sycophancy/scope drift) →
  https://github.com/janos-gyorgy/claude-compass

Both pair naturally with this repo: watchtower manages the sessions whose
memory lives here; compass guards the agents that write here.
