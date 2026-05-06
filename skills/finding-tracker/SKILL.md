---
name: finding-tracker
description: Maintain centralized security finding state across authorized cyber workflows. Use when Codex discovers, validates, proofs, de-escalates, updates, searches, deduplicates, summarizes, or hands off potential vulnerabilities, bug bounty findings, audit findings, exploitability leads, crash findings, web/API issues, CVE exposure decisions, fuzzing crashes, or reverse-engineering leads. Always use before adding a new discovered bug to check for duplicates and reduce repeated effort.
---

# Finding Tracker

Use this skill as shared state for security findings across the plugin. It helps
agents avoid duplicate effort, remember recent milestones, and preserve why a
lead became stronger or was debunked.

Default tracker path: `data/findings.json` in the active target workspace. Keep
finding data in the target workspace, not in the skill directory.

## States

Every finding must be exactly one of:

- `discovered`: bug potentially found.
- `confident`: agent found evidence of the bug plus reachability or
  exploitability.
- `proofed`: successful run through the `triage-verifier` skill. Do not set this
  state without a verifier reference or result.
- `de-escalated`: potential bug was debunked at any point.

Do not delete de-escalated findings during normal work. They prevent future
agents from rediscovering and re-testing the same false lead. They may also
become useful context for `exploit-chain-analysis` when another finding changes
the preconditions that originally blocked the lead.

## Required Discipline

Before adding a new `discovered` finding:

1. Search for duplicates using target, title, category, affected locations, and
   evidence keywords.
2. If a likely duplicate exists, update that finding with a milestone instead of
   creating a new one.
3. If the apparent duplicate is materially different, add the new finding and
   explain why it is not a duplicate.

Update state as soon as the evidence changes. Add a milestone for meaningful
events: new evidence, reachability confirmed, exploitability confirmed,
triage-verifier run, reproduction failure, mitigation found, duplicate
decision, or de-escalation.

## Helper Script

Use `scripts/findings.py` for deterministic tracking.

```bash
# Initialize or summarize
python3 <skill-dir>/scripts/findings.py init
python3 <skill-dir>/scripts/findings.py summary
python3 <skill-dir>/scripts/findings.py list --state active

# Duplicate search before adding
python3 <skill-dir>/scripts/findings.py search \
  --title "IDOR in invoice export" \
  --target "billing.example.com" \
  --category "authorization" \
  --location "GET /api/invoices/{id}/export"

# Add a discovered finding. This refuses likely duplicates unless overridden.
python3 <skill-dir>/scripts/findings.py add \
  --title "IDOR in invoice export" \
  --target "billing.example.com" \
  --category "authorization" \
  --location "GET /api/invoices/{id}/export" \
  --summary "Standard user may be able to export invoices by changing invoice_id." \
  --evidence "Observed export endpoint accepts direct invoice_id parameter."

# Promote, proof, de-escalate, or add milestones
python3 <skill-dir>/scripts/findings.py update F-0001 --state confident \
  --note "Confirmed tenant B user can reach tenant A invoice export."
python3 <skill-dir>/scripts/findings.py update F-0001 --state proofed \
  --proof-ref "triage-verifier run 2026-05-06T18:42:00Z"
python3 <skill-dir>/scripts/findings.py update F-0001 --state de-escalated \
  --note "Server-side ownership check confirmed; earlier response was cached owner data."
python3 <skill-dir>/scripts/findings.py milestone F-0001 \
  --note "Added negative control with logged-out user."
```

Exploit chains are tracked as normal findings with category `exploit-chain` and
`--related` IDs for every component finding or de-escalated lead:

```bash
python3 <skill-dir>/scripts/findings.py add \
  --title "Upload metadata to admin import SSRF chain" \
  --target "admin.example.com" \
  --category "exploit-chain" \
  --related F-0003 \
  --related F-0007 \
  --related F-0002 \
  --summary "Upload metadata primitive may feed admin import SSRF sink." \
  --evidence "data/exploit-chains/upload-admin-import-ssrf-chain.md"
```

The script defaults to `data/findings.json`; pass `--file <path>` to use a
different tracker for tests or unusual workspaces.

## Finding Content

Keep entries compact and useful:

- Title: short, stable, and specific.
- Target: product, host, repository, binary, package, component, or asset.
- Category: vulnerability class such as authorization, SSRF, deserialization,
  memory-safety, supply-chain, business-logic, crypto, or AI/tool-boundary.
- Locations: routes, files, functions, offsets, endpoints, CVEs, package names,
  crash IDs, harness names, or other affected surfaces.
- Summary: current hypothesis or confirmed issue.
- Evidence: short references to requests, code lines, traces, crashes,
  screenshots, logs, or verifier results. Redact secrets and PII.
- Related IDs: finding IDs that share context, form an exploit chain, or explain
  why a de-escalated lead matters to a new chain hypothesis.
- Milestones: chronological notes that explain how the finding changed.

Do not store raw tokens, full cookies, private keys, customer data, exploit
payloads, high-volume logs, or unredacted third-party data in the tracker.

## State Transitions

Allowed normal transitions:

- `discovered` -> `confident`
- `discovered` -> `de-escalated`
- `confident` -> `proofed`
- `confident` -> `de-escalated`
- `proofed` -> `de-escalated` if later evidence debunks the proof

If a finding needs to move backward for a legitimate reason, add a milestone
explaining the evidence change. Do not silently rewrite history.

## Duplicate Policy

Treat a finding as a duplicate when it shares the same underlying bug, even if
the symptom differs. Examples:

- Same missing authorization check exposed through list, detail, and export
  endpoints.
- Same parser crash reached by different seed files.
- Same vulnerable dependency reported by multiple scanners.
- Same SSRF sink exposed by preview and import workflows.

Treat as separate findings when the root cause, affected boundary, required
privilege, tenant/account impact, or fix path is materially different.

Treat exploit chains as separate findings when the combination creates materially
greater impact than the component findings. If the chain does not increase
impact, add a milestone to the strongest existing finding instead.

When unsure, keep one finding and add milestones until evidence proves a split is
useful.

## Workflow Integration

At the start of a substantial security workflow, run `summary` or `list --state
active` to see current work. During review, use `search` before adding leads.
At handoff, include finding IDs and current states so the next skill or agent can
continue without redoing discovery.

`proofed` is reserved for `triage-verifier`; this skill records proof results but
does not perform that verification itself. Exploit-chain findings also require a
`triage-verifier` proof reference before they can become `proofed`.

## Output Format

When reporting tracker changes, keep it short:

```text
Finding tracker:
- F-0001 confident: IDOR in invoice export
- F-0002 de-escalated: SSRF in avatar fetcher (blocked by final egress proxy check)
- Added milestone to F-0001: negative control confirms tenant boundary
```

If a duplicate check blocked a new finding, report the existing finding ID and
the reason it matched.
