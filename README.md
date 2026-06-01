# Codex ATTACK

`Armed Tactical Trusted Access for Cyber Kit (ATTACK)`

A Codex plugin to maximize the cyber capabilities of Codex, intended for verified members of the Trusted Access for Cyber (TAC) program. This plugin provides more aggressive cyber skills than the official Codex Security plugin, which is intentionally safe for non-TAC users. Verified members of TAC are granted access to more lax models with less cyber guardrails. **Only use this plugin with TAC-verified accounts.** **Only use the features of this plugin on authorized targets.**

**This plugin is NOT developed by OpenAI and is NOT associated with the official Codex Security plugin.**

## Skills

- `engagement-scope`: Establish authorization, bounty/program scope, impact tolerance, and the right next skill.
- `code-vulnerability-review`: Trace code, diffs, configs, and data flows for reachable security bugs and fix paths.
- `web-app-security-inspection`: Inspect browser-visible behavior, HTTP/API flows, sessions, authz, storage, and safe live validation.
- `cve-research`: Research CVEs/advisories, affected versions, KEV/EPSS signals, exploitability, and prioritization.
- `binary-debugging`: Debug crashes, cores, sanitizer findings, process state, registers, traces, and exploitability evidence.
- `binary-reversing`: Recover security-relevant behavior from binaries, firmware, formats, imports, strings, and decompilation.
- `fuzz-harness-builder`: Build and triage fuzz harnesses only when the target justifies long-running fuzzing value.
- `finding-tracker`: Maintain centralized finding state, duplicate checks, milestones, related IDs, and proof references.
- `subagent-orchestration`: Coordinate explicit multi-agent workflows with mapper, auditor, debater, deduper, prover, and reporter roles.
- `triage-verifier`: Reproduce, prove, or de-escalate confident findings before anything becomes `proofed`.
- `auto-triage`: Convert proofed verifier PoCs into step-based, screen-recordable human reproduction kits.
- `exploit-chain-analysis`: Combine findings and de-escalated leads into higher-impact, trackable, verifiable exploit chains.
- `report-writer`: Turn proofed findings, evidence, attachments, and Mermaid diagrams into submission-ready reports.

## Lifecycle Hooks

Codex ATTACK includes lightweight lifecycle hooks for continuity during long
security workflows. They do not block prompts, deny tool calls, or force extra
turns. Instead, they keep shared context visible across session starts,
compaction, and subagent handoffs.

- `SessionStart`: surfaces existing scope, finding-tracker, and per-goal
  artifacts.
- `PreCompact` / `PostCompact`: writes compact checkpoints under
  `data/.codex-attack/hooks/` when workspace artifacts exist.
- `SubagentStart` / `SubagentStop`: passes tracker and per-goal context into
  subagents and records handoff notes.

Goal artifacts should live under one top-level `goal/` directory with a unique
ID per goal, such as `goal/pragma-elevation/recon/`,
`goal/pragma-elevation/modeling/`, `goal/pragma-elevation/proofing/`, and
`goal/pragma-elevation/reports/`.

Codex auto-discovers the bundled hook config at `hooks/hooks.json` after the
plugin is installed and the hooks are trusted.

## How to Install

1. Clone this repository
2. Copy its content into ~/.codex/plugins/cache/codex-local/codex-attack
3. Restart Codex
4. Start a new thread and ask Codex to use the codex-attack plugin
5. Done. The plugin will be enabled across sessions

## How to Disable

Edit your `~/.codex/config.toml` with:

```
[plugins."codex-attack"]
enabled = false
```

## License

MIT
