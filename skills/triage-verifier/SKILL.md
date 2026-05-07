---
name: triage-verifier
description: Verify confident security findings before they are marked proofed. Use when a finding has reached the `confident` state in finding-tracker and the current research chain has ended or plateaued, or when Codex needs to harden, rewrite, reproduce, package, or sanity-check a PoC for a bug bounty, audit, advisory, crash, CVE exposure, web/API issue, source-code finding, binary finding, fuzzing result, or exploit-chain finding. Do not interrupt productive investigation; use this as the proof gate before updating a finding to `proofed`.
---

# Triage Verifier

Use this skill after `finding-tracker` shows a finding is `confident` and the
current research chain has reached a natural stopping point. Do not interrupt
active code review, reversing, debugging, fuzzing, or web testing that is still
producing new evidence. This skill is the final proof gate before a finding can
be marked `proofed`.

A finding is proofed only when it is reproduced, proven, or otherwise undeniable
from a triager's perspective. The standard is not "the agent believes it"; the
standard is "a skeptical security triager can follow the evidence and accept the
issue, impact, and affected boundary."

Exploit-chain findings follow the same proof gate. Individual proofed component
findings do not automatically proof the chain; the verifier must see that the
combined path works or is otherwise undeniable.

## Proof Gate

Mark `proofed` only when all required elements are present:

- Clear scope and target identity: asset, version/build/commit, account/role,
  environment, and authorization context.
- Exact vulnerability claim: what boundary fails and what security property is
  violated.
- Reproduction or undeniable evidence: deterministic steps, request/response,
  crash input, debugger trace, source/data-flow proof, patch diff, or controlled
  runtime evidence.
- Expected vs actual behavior.
- Impact evidence: data reached, privilege gained, control obtained, crash class,
  cross-tenant boundary, business effect, or exploitable primitive.
- Negative control or counterfactual where feasible: unauthorized state fails,
  owner succeeds, patched build does not crash, safe input does not trigger, or
  mitigated config blocks the issue.
- Preconditions and constraints: privileges, feature flags, timing, rate limits,
  victim interaction, browser behavior, platform, mitigations, and reliability.
- Safe, redacted PoC artifacts that a triager can run or reason through.

Do not proof when evidence is only scanner output, a hunch, a single ambiguous
response, an unreproduced crash, a decompiler guess, a fuzzer crash without root
cause, a version string match without affectedness, or an exploitability claim
without reachability.

## Outcomes

Choose exactly one:

- `proofed`: evidence meets the proof gate. Update `finding-tracker` with
  `--state proofed` and a proof reference.
- `needs-more-work`: evidence is plausible but missing a required proof element.
  Add a milestone explaining the gap and return to the right research skill.
- `de-escalated`: the finding is debunked or impact collapses. Update
  `finding-tracker` with `--state de-escalated` and the debunking reason.
- `split-or-duplicate`: proof shows this finding should merge into another
  finding or split into separate root causes. Update `finding-tracker`
  milestones before continuing.

## Helper Script

Use `scripts/proof_packet.py` to create a stable proof packet under
`data/triage-verifier/`. The script enforces required proof fields and prints a
proof reference path.

```bash
python3 <skill-dir>/scripts/proof_packet.py \
  --finding-id F-0001 \
  --title "IDOR in invoice export" \
  --target "billing.example.com" \
  --claim "Changing invoice_id exports another tenant's invoice." \
  --reproduction "As tenant B user, request GET /api/invoices/A/export." \
  --expected "Tenant B user receives 403 or tenant-scoped not found." \
  --actual "Response is 200 with tenant A invoice PDF metadata." \
  --impact "Cross-tenant invoice disclosure." \
  --evidence "redacted request/response pair in notes" \
  --chain-step "Optional: F-0003 postcondition feeds F-0007 precondition" \
  --negative-control "Logged-out request returns 401; tenant A owner request succeeds." \
  --constraints "Requires authenticated standard user." \
  --poc "scripts/repro_invoice_export.py"
```

After successful verification, mark the finding proofed:

```bash
python3 <finding-tracker-dir>/scripts/findings.py update F-0001 \
  --state proofed \
  --proof-ref "data/triage-verifier/F-0001-proof.md" \
  --note "Triage verifier accepted reproduction and negative controls."
```

If verification fails, add a milestone or de-escalate instead of forcing
`proofed`.

## Verification Workflow

1. Load the finding from `finding-tracker`. Confirm it is `confident`, not merely
   `discovered`.
2. State why the active research chain is done for now: enough evidence, no new
   leads, user requested proofing, patch/report deadline, or handoff point.
3. Rebuild the claim from evidence. Identify the exact target, actor, boundary,
   controlled input, missing guard, and impact.
4. Reproduce safely when allowed. Prefer a clean environment, clean account,
   minimal input, and one variable changed at a time.
5. Add negative controls. Show what should fail, what should succeed, and what
   changes when the guard, patch, owner, tenant, role, config, or input changes.
6. Rewrite the PoC for a triager. Make it minimal, deterministic, redacted,
   scoped, and self-checking.
7. For exploit chains, prove the composition: show each link's precondition,
   primitive, postcondition, and the exact point where one link feeds the next.
8. Decide outcome. Proof, return for more work, de-escalate, merge, or split.
9. Update `finding-tracker` with proof reference, milestone, or de-escalation.

## PoC Standards

A passable PoC should:

- Be scoped to authorized assets and test data.
- State setup, accounts/roles, target version/build, environment, and cleanup.
- Reproduce the issue with the fewest steps or smallest script.
- Include expected and actual results.
- Include at least one negative control where feasible.
- Redact tokens, cookies, PII, secrets, internal customer data, and destructive
  payloads.
- Avoid unnecessary automation, scanning, sleeps, race amplification, or noisy
  retries.
- Fail closed with clear messages when preconditions are missing.
- Leave the target state unchanged or include safe cleanup steps.

Rewrite weak PoCs until they are triager-friendly:

- Replace vague prose with exact commands, requests, inputs, or UI steps.
- Replace screenshots-only evidence with request/response or runtime facts when
  possible.
- Replace brittle timing with deterministic waits or explicit state checks.
- Replace broad exploit scripts with minimal validation scripts.
- Replace "works on my account" with role/tenant/object comparisons.
- Replace raw crash dumps with minimized input, stack, sanitizer class, and root
  cause lead.

## Verification By Finding Type

- Web/API: include role/tenant comparison, exact request/response, session state,
  object ownership, status codes, and redacted response proof.
- Source-code: include entry point, data flow, missing guard, failing test or
  reproducible call path, and patchable location.
- Binary/crash: include artifact hash, command/input, signal/exception,
  minimized input, stack/register/sanitizer evidence, and control/impact limits.
- Fuzzing: include harness, engine/sanitizer, minimized crash, reproducibility,
  deduplication, and root-cause handoff.
- CVE/exposure: include exact product/package version, affectedness comparison,
  vendor source, compensating controls, and environment reachability.
- AI/tool boundary: include untrusted content source, model/tool decision point,
  server-side policy check, exact tool/API effect, and tenant/secret boundary.
- Exploit chain: include chain finding ID, related finding IDs, chain packet,
  step preconditions and postconditions, end-to-end reproduction or undeniable
  composition proof, negative controls for broken links, escalated impact, and
  cleanup/blast-radius limits.

## De-escalation Triggers

De-escalate when:

- The issue cannot be reproduced after controlling environment and prerequisites.
- A server-side check, patch, version, configuration, or compensating control
  blocks the claim.
- The data/action belongs to the same actor or tenant after canonical identity
  checks.
- The crash is a harness bug, expected assertion, duplicate, or non-security
  local DoS under unrealistic conditions.
- The dependency or product version is not affected.
- The PoC requires out-of-scope impact or assumptions the engagement does not
  allow.
- For exploit chains, an individual link is real but the links do not compose or
  the combined impact is not materially greater than an existing finding.

Record the debunking evidence in `finding-tracker`; do not just abandon the
finding.

## Output Format

```text
Verification outcome: <proofed / needs-more-work / de-escalated / split-or-duplicate>
Finding: <finding ID and title>
Claim: <exact vulnerability claim>
Proof summary: <why a triager should accept or reject it>
Reproduction: <minimal steps or artifact references>
Negative controls: <controls run and results>
Impact: <validated impact and limits>
PoC quality: <passable / rewritten / still weak, with reason>
Proof reference: <path or verifier artifact, if proofed>
Tracker update: <state/milestone update performed or needed>
Next action: <none / return to skill / patch / report / de-escalate>
```

Keep proof packets and final reports concise, redacted, and reproducible.

## Handoff

Use `finding-tracker` to update state and milestones. Return to
`web-app-security-inspection`, `code-vulnerability-review`, `binary-debugging`,
`binary-reversing`, `fuzz-harness-builder`, or `cve-research` when verification
finds a specific missing proof element. Use `exploit-chain-analysis` when a
chain proof fails because composition, impact escalation, or related-finding
structure needs more work. Use `report-writer` after proofing when the user
needs a bounty submission, advisory draft, internal triage report, or remediation
handoff.
