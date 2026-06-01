---
name: subagent-orchestration
description: Plan and coordinate authorized multi-agent cyber workflows with explicit subagent roles, bounded assignments, tracker discipline, debate, deduplication, proof handoffs, and synthesis. Use when the user explicitly asks for subagents, parallel agents, delegation, debate, multiple reviewers, or staged agentic security work.
---

# Subagent Orchestration

Use this skill after `engagement-scope` has established the authorized target,
scope evidence, impact tolerance, and deliverable. This skill plans and
coordinates subagents; it does not replace the technical skill that owns the
actual evidence, proof, patch, or report.

Codex only spawns subagents when the user explicitly asks for them. Treat that
as an intentional cost and latency boundary. Do not use this skill to justify
silent fan-out for ordinary depth, thoroughness, or codebase exploration.

## Staged Agent Model

Use a staged security workflow: prepare the target, scan with specialized
auditors, validate with separate debaters, deduplicate equivalent findings, and
prove candidates with dynamic or domain-specific proof helpers. The lesson is
not "spawn many agents." The lesson is role separation, independent evidence,
and a pipeline that turns candidates into proofed findings instead of a pile of
noisy claims.

Use the portable shape:

```text
Prepare -> Scan -> Validate/Debate -> Dedup -> Prove -> Report/Patch
```

Map Codex subagents onto that shape conservatively. The parent agent is the
orchestrator and owns scope, final decisions, tracker state, and synthesis.
Subagents own bounded assignments with clear stop criteria.

## When To Use

Use subagents when the user explicitly requests parallel or delegated agent work
and at least one of these is true:

- The target naturally splits into independent components, files, services,
  roles, tenants, binaries, parsers, harnesses, or vulnerability classes.
- A candidate finding needs independent skeptical validation before proofing.
- Multiple hypotheses can be investigated in parallel without sharing write
  scopes or blocking each other.
- A goal run has clear workstreams under `goal/<goal-id>/`.
- The user wants a staged audit, debate, dedup, or proof pipeline.

Do not use subagents when:

- The next step is a single blocking read, test, proof attempt, or fix.
- The work requires one shared mutable state that agents would race on.
- The task is quick enough for the parent to finish directly.
- The user has not explicitly asked for subagents, delegation, or parallel
  agents.
- The process is a proof gate that needs one coherent verifier decision; use
  `triage-verifier` directly unless debate is specifically requested first.

## Agent Roles

Use built-in Codex agent types unless project custom agents are available and
the user asks for them.

- `explorer`: read-only mapper, auditor, debater, deduper, or documentation
  researcher. Prefer this for source review, reachability reasoning, and
  adversarial validation.
- `worker`: bounded execution role for proof artifacts, harnesses, tests,
  patches, or report assembly. Give workers disjoint write ownership.
- `default`: fallback for work that does not fit the above.

Suggested security roles:

- Mapper: inventory entry points, trust boundaries, data flow, harness formats,
  or relevant code regions before scan.
- Auditor: inspect one target slice or vulnerability class and emit candidate
  findings with evidence and uncertainty.
- Debater: try to refute a specific candidate's reachability, controllability,
  impact, or assumptions. A debater is not another auditor.
- Deduper: compare candidates against each other and `finding-tracker` to group
  same-root-cause findings.
- Prover: create or harden minimal proof artifacts after a finding is already
  `confident`; coordinate with `triage-verifier`.
- Reporter or patcher: produce final report or fix artifacts only after proof or
  a confirmed remediation request.

## Fan-Out Rules

Keep fan-out small and purposeful:

- Start with two to six subagents. Six is a practical default ceiling because
  Codex's default `agents.max_threads` is six.
- Use one subagent per independent workstream, not one per vague question.
- When the user asks for one subagent per vulnerability family, generate one
  auditor packet per selected family and run them in batches if the family count
  exceeds the active thread budget.
- Prefer breadth in the `Scan` stage and skepticism in the `Validate/Debate`
  stage. Do not ask every agent to do every stage.
- Avoid recursive subagent spawning. Keep depth at one unless the user
  explicitly requests nested delegation and accepts the cost.
- Give every worker a disjoint write set. Explorers should normally be read-only
  and return evidence rather than editing files.
- Do not wait idly on sidecar agents when the parent can make independent
  progress.

## Assignment Packets

Before spawning agents, write or state an assignment packet for each subagent.
Use `scripts/assignment_packet.py` when a durable artifact is useful.

```bash
python3 <skill-dir>/scripts/assignment_packet.py \
  --goal-id sudo-elevation \
  --role auditor \
  --agent-type explorer \
  --stage scan \
  --title "Audit sudo helper environment handling" \
  --target "tools/sudo-helper and tests" \
  --objective "Find evidence for or against attacker-controlled environment reaching privileged execution." \
  --stop "Return after mapping the call chain and at most three candidate issues." \
  --output "Candidate findings with file references, confidence, and proof gaps." \
  --tracker "Search data/findings.json before proposing new finding IDs." \
  --write-scope "read-only"
```

For goal runs, assignment packets belong under
`goal/<goal-id>/modeling/subagents/`. For non-goal work, use
`data/subagents/`.

## Vulnerability Family Fan-Out

Use this mode when the user asks for one subagent per vulnerability family or a
broad family-based audit. Read `references/vulnerability-families.md` for the
stable family IDs. Create one `explorer` auditor assignment per selected family:

```bash
python3 <skill-dir>/scripts/family_assignment_packets.py \
  --goal-id sudo-elevation \
  --target "repo tools/sudo-helper and tests" \
  --family access-control \
  --family injection \
  --family memory-concurrency
```

Use `--all` only when the user wants broad coverage and the target is scoped
well enough to justify it. If more than six packets are created, run them in
waves and synthesize each wave before launching the next. The parent must dedup
cross-family findings because real bugs often straddle families.

Family auditor prompts should stay read-only and return at most a small number
of candidates with exact evidence, likely duplicates, refuted leads, and proof
gaps. Do not let family auditors proof, patch, or report unless a later
assignment explicitly changes their role.

## Spawn Prompt Template

Each subagent prompt should include:

```text
Role: <mapper / auditor / debater / deduper / prover / patcher / reporter>
Stage: <prepare / scan / validate-debate / dedup / prove / report-patch>
Authorized scope: <engagement brief subset>
Target slice: <files, routes, binary, finding ID, harness, account role>
Objective: <one bounded outcome>
Non-goals: <what to ignore>
Write ownership: <read-only or exact files/directories>
Tracker discipline: <summary/search/update expectations>
Evidence standard: <what counts as useful evidence>
Stop criteria: <when to return>
Output contract: <required structured handoff>
```

Tell code-edit workers they are not alone in the codebase, they must not revert
others' changes, and they must list changed files. Tell explorers to cite exact
files, symbols, requests, crashes, or commands and to avoid speculative final
claims.

## Debate And Validation

After auditors return candidates, use separate debater assignments before
promotion to `confident` when the claim is non-trivial. Debaters should:

- Attack the weakest premise: reachability, controllability, privilege,
  affected version, harness format, race feasibility, or impact.
- Compare against known-correct sibling patterns when relevant.
- Look for missing preconditions, alternate ownership, server-side checks,
  canonicalization, patched code paths, or duplicate root causes.
- Return one of: `not-refuted`, `refuted`, `needs-more-evidence`,
  `duplicate-likely`, or `out-of-scope`.

Disagreement is useful signal, not failure. Parent synthesis should preserve the
best contrary evidence and proof gaps.

## Dedup And Tracker Discipline

The parent owns final tracker mutations unless the assignment explicitly gives a
subagent that job. Before adding findings:

1. Run or request duplicate search with `finding-tracker`.
2. Group same-root-cause candidates across agent outputs.
3. Promote only candidates with evidence and a clear proof path.
4. Record de-escalated or refuted leads when they prevent repeated work.

Use exploit-chain findings only when the combination creates materially greater
impact than the components.

## Proof Handoff

Subagents can prepare proof ingredients, but `triage-verifier` remains the proof
gate. A candidate becomes `proofed` only after verifier evidence exists.

Use provers for bounded work such as:

- minimized crash input or harness-format correction;
- role/tenant negative-control script;
- local regression test;
- debugger trace or sanitizer reproduction;
- exploit-chain transition check.

Then send the resulting confident finding through `triage-verifier`.

## Parent Synthesis

After subagents finish, the parent should return:

```text
Subagent synthesis:
- Workstreams: <agent roles and target slices>
- Strong candidates: <finding IDs or pending titles with evidence>
- Refuted/de-escalated leads: <what was ruled out and why>
- Dedup decisions: <merged/split findings>
- Proof gaps: <exact next verifier/prover work>
- Tracker updates: <search/add/update/milestone performed>
- Next stage: <scan / debate / dedup / prove / report / patch / stop>
```

Prefer concise synthesis over pasting full agent transcripts. Keep the evidence
links and artifact paths durable enough that a later compacted context or
subagent can resume.
