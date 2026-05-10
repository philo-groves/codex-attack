---
name: session-viewer
description: Automatically maintain and launch a lightweight HTML session monitor for substantial authorized cyber research. Use at the start of long-running Codex ATTACK workflows, vulnerability research, code or web security review, reversing, debugging, fuzzing, CVE triage, exploit-chain analysis, triage verification, or any session with active findings, escalations, de-escalations, proof status, blockers, or next actions. Open the viewer in the in-agent browser and update it after every meaningful escalation or de-escalation.
---

# Session Viewer

Use this skill to keep a small, stateful HTML view open beside long-running
security work. Markdown remains useful for reports and copyable handoffs; the
session viewer is for live monitoring while research is still moving.

Default paths in the active target workspace:

- State: `data/session-viewer.json`
- HTML: `data/session-viewer.html`

Keep viewer files in the target workspace, not in the skill directory.

## When To Use

Use this skill by default when:

- Starting a substantial authorized cyber research session or Codex ATTACK
  workflow.
- A workflow has multiple active findings, exploit-chain hypotheses, proof
  packets, blocked leads, or de-escalated paths.
- The user asks for HTML, a session view, dashboard, monitor, live status, or a
  stateful view instead of a Markdown log.
- `finding-tracker` changes a finding state, especially escalation to
  `confident` or `proofed`, or de-escalation to `de-escalated`.
- A chain analysis needs visible preconditions, blockers, and next actions.

Skip it for quick one-off answers, tiny code edits, or when the user explicitly
asks not to maintain a browser view.

Do not replace final vulnerability reports with this viewer. Use `report-writer`
for submission-ready Markdown or platform-specific report text.

## Helper Script

Use `scripts/session_viewer.py` for deterministic state and HTML rendering.

Launch a viewer at the start of a session:

```bash
python3 <skill-dir>/scripts/session_viewer.py launch \
  --title "Acme tenant isolation review" \
  --target "app.acme.test"
```

Run `launch` in a persistent command session. It renders the page, serves the
HTML directory on localhost, and prints a URL. Open that URL in the in-agent
browser immediately and keep the command running while research continues. The
page polls the JSON state every few seconds and updates in place as the state
changes.

Use the active Codex/in-agent browser capability to navigate to the printed URL.
Do not rely on `xdg-open`, `webbrowser.open`, or a system-default browser as the
primary monitoring surface, because those open outside the agent session.

Initialize without launching only when a browser is unavailable:

```bash
python3 <skill-dir>/scripts/session_viewer.py init \
  --title "Acme tenant isolation review" \
  --target "app.acme.test"
```

Sync from `finding-tracker` after tracker changes:

```bash
python3 <skill-dir>/scripts/session_viewer.py sync-findings \
  --findings data/findings.json
```

Record a manual transition or note:

```bash
python3 <skill-dir>/scripts/session_viewer.py event \
  --kind escalation \
  --subject F-0007 \
  --title "Invoice export crosses tenant boundary" \
  --from-state discovered \
  --to-state confident \
  --summary "Positive and negative controls now show tenant isolation failure." \
  --evidence "data/proofs/F-0007-export-controls.txt" \
  --next-action "Run triage-verifier with replayable request pair."
```

Use `--state-file` and `--html-file` for unusual workspaces.

## Required Discipline

At the start of substantial research:

1. Run `launch`.
2. Open the printed localhost URL in the in-agent browser.
3. Keep the browser tab visible or easy to return to during the session.

Update the viewer after every meaningful escalation or de-escalation:

- Escalation: evidence increases confidence, reachability is confirmed,
  exploitability is confirmed, a chain composes, or a finding becomes `proofed`.
- De-escalation: a guard debunks the issue, a duplicate is found, the target is
  out of scope, reproduction fails with a solid negative control, or impact
  does not exceed an existing finding.

When using `finding-tracker`, run `sync-findings` immediately after state
updates. The viewer detects state transitions from the previous synced state and
adds one timeline event per changed finding.

## UI Shape

The HTML should be a live research surface, not a wall of text:

- Show current state as cards grouped by state.
- Put escalations, de-escalations, proof events, and blockers in a compact
  timeline.
- Keep next actions visible on the relevant card.
- Prefer short evidence references to long pasted logs.
- Redact secrets, cookies, private keys, customer data, and unsafe payloads.

The generated page uses inline CSS, lightweight JavaScript, no external network
dependencies, embedded JSON state, and JSON polling so an already-open browser
tab tracks updates during the session without full-page refresh flashes.

## Handoff

When handing work to another agent or skill, mention the viewer path and the
latest important transition:

```text
Session viewer: http://127.0.0.1:<port>/session-viewer.html
Viewer file: data/session-viewer.html
Latest transition: F-0007 discovered -> confident after tenant negative control
Next action: triage-verifier proof run
```
