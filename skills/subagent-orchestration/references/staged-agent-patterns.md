# Staged Subagent Patterns

This note captures model-agnostic multi-agent patterns for Codex ATTACK. Keep it
stable and avoid time-sensitive proper nouns so older and newer models interpret
the guidance consistently.

## Transferable Lessons

- Stages matter more than raw agent count: prepare, scan, validate/debate,
  deduplicate, prove, report or patch.
- Agent roles should have different prompts, tools, and stop criteria. An
  auditor, debater, and prover should not all be asked to do the same job.
- Disagreement is useful. A candidate that survives an independent attempt to
  refute reachability or impact is stronger than one auditor's claim.
- Domain knowledge belongs in plugins, scripts, harnesses, and scope files so it
  survives model changes.
- Proof is its own stage. Candidate findings should not become accepted findings
  until a verifier can reproduce or reason through the evidence.
- Vague target descriptions are a failure mode. Assignment packets should name
  files, functions, harness formats, vulnerability descriptions, or exact target
  boundaries whenever possible.

## Codex ATTACK Adaptation

- Use Codex's built-in `explorer` agents for mapper, auditor, debater, and
  deduper roles.
- Use `worker` agents only for bounded proof, patch, report, or artifact tasks
  with explicit write ownership.
- Keep fan-out small, usually two to six agents.
- Keep the parent agent responsible for scope, tracker state, final synthesis,
  and proof-gate decisions.
- Use `triage-verifier` for final proofing and `finding-tracker` for durable
  state.
