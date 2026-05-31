# Codex ATTACK Hooks

This plugin uses lifecycle hooks as a context-continuity layer. The hooks do not
block prompts, deny tools, or force continuation. They only surface concise
workspace context and write lightweight checkpoints for long-running work.

Codex auto-discovers `hooks/hooks.json` from the plugin root when the plugin is
enabled and the hooks are trusted.

## Hooks

- `SessionStart`: adds active scope, tracker, and goal context when available.
- `PreCompact`: writes a checkpoint before conversation compaction.
- `PostCompact`: writes a checkpoint after conversation compaction.
- `SubagentStart`: passes current tracker and goal context into child agents.
- `SubagentStop`: records a compact subagent handoff in the workspace.

Checkpoint files are written under `data/.codex-attack/hooks/` in the active
workspace only when Codex ATTACK workspace artifacts already exist.
