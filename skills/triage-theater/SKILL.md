---
name: triage-theater
description: Build human-friendly, screen-recordable proof-of-concept reproduction kits from already proofed triage-verifier evidence. Use after triage-verifier accepts a finding as proofed, or when Codex needs to turn an agent-focused PoC, proof packet, request log, crash repro, or verifier artifact into direct step-based human reproduction artifacts for bounty triagers, researchers, auditors, or screen recordings.
---

# Triage Theater

Use this skill after `triage-verifier` has already accepted the finding as
`proofed`. The verifier proves that the issue is real. Triage theater turns that
proof into a human-operated demo that is easy to screen record, inspect, and
submit without making triagers feel like the PoC hides the vulnerable action
inside a complicated harness.

Do not use this skill as the proof gate. If the claim is not already proofed,
return to `triage-verifier` first unless the user explicitly asks for a draft
demo and accepts that it is not submission-ready.

## Goal

Create a PoC package that a human can run step by step:

- The vulnerable command, request, UI action, file, or input is visible and
  triggered directly whenever possible.
- Setup is minimal and separated from the actual vulnerable step.
- Evidence appears on screen at each important step so it can be recorded.
- Screenshots supplement the flow, but the flow should still work as a live
  screen recording.
- Human-facing files do not include internal tracker IDs, agent notes, or
  research identifiers such as `F-0001`.

## Artifact Layout

Place output under a human-readable slug, not a finding ID:

```text
data/triage-theater/<short-vulnerability-slug>/
  steps.md
  screenshots/
  requests/
  commands/
  poc/
```

Create only the subdirectories that are useful. Use `requests/` for raw HTTP
requests, `.http` files, or curl snippets. Use `commands/` for small shell
commands that trigger a local binary, package manager, CLI, or API client. Use
`poc/` only when a real PoC project is needed.

If a PoC project is needed, create the actual project files in `poc/` or a
subdirectory. Do not generate project files by embedding long `cat`,
`echo`, or heredoc blocks inside setup scripts. Triagers should be able to open
the files directly.

## Workflow

1. Load the `triage-verifier` proof packet and the agent-focused PoC artifacts.
   Identify the exact vulnerable primitive, target, required role, environment,
   and evidence the verifier accepted.
2. Strip away verifier-only machinery. Keep self-checks and negative controls
   out of the human flow unless they make the demo clearer.
3. Choose the most direct human trigger:
   raw HTTP request, browser UI action, curl/httpie command, CLI invocation,
   minimized crash input, package install step, or local function call.
4. Split setup from exploitation. Setup may authenticate, create test data,
   install dependencies, or start a local service. The vulnerable step should be
   a separate visible action.
5. Build `steps.md` as a numbered reproduction script. Each step should include:
   action, expected visible result, evidence to capture, and screenshot path.
6. After each evidenced step, take a fullscreen screenshot when tooling is
   available. Store screenshots as `screenshots/01-<slug>.png`,
   `screenshots/02-<slug>.png`, and so on. Keep screenshots uncropped so the
   human can crop later or rely on a screen recording instead.
7. Lightly run through the human flow when authorized and safe. Catch dead
   commands, missing files, stale URLs, and unclear screen states. Do not redo
   the verifier's full positive/negative proof matrix here.
8. Redact secrets, cookies, tokens, private customer data, PII, and destructive
   payloads. Preserve enough structure that the human can substitute their own
   scoped values.

## Human PoC Standards

A good triage-theater package:

- Lets the human see and trigger the vulnerable operation directly.
- Uses the fewest layers possible between the human and the vulnerable endpoint,
  command, parser, or UI workflow.
- Avoids large wrapper scripts unless the target cannot be reached directly.
- Avoids mocked services unless the real dependency is unavailable, unsafe, or
  out of scope. If a mock is necessary, say exactly why in `steps.md`.
- Keeps generated helper code small, readable, and placed in real files.
- Names files for the vulnerable behavior, not for internal research state.
- Prefers direct artifacts: raw requests, minimized inputs, exact commands,
  browser actions, before/after visible states, and clear screenshots.
- Includes cleanup only when the human flow changes target state.

Avoid:

- One giant script that performs setup, exploitation, validation, screenshots,
  and cleanup without exposing the vulnerable action.
- PoC projects that are generated at runtime by shell script file writes.
- Hidden assumptions from the verifier packet.
- Internal IDs, scratch notes, agent reasoning, or tracking metadata in the
  human-facing PoC.
- Artificial demos that look like the agent proved its own mock instead of the
  real target.

## Screenshot Guidance

Capture after the visible evidence appears, not before the step runs. Prefer a
full desktop or full browser viewport screenshot over a cropped window. If only
browser screenshots are available, use the largest practical viewport and name
the limitation in `steps.md`. If no screenshot tool is available, leave the
screenshot paths in `steps.md` and mark them as pending for the human screen
recording pass.

Do not let screenshots replace the reproduction. The human should be able to run
the steps while recording, then decide whether the screenshots are useful as
attachments.

## `steps.md` Shape

Use concise, direct language:

```markdown
# <Vulnerability title without internal ID>

## Environment

- Target: <asset, URL, package, binary, or local app>
- Role/account: <attacker role and victim/owner role if needed>
- Version/build: <version, commit, or date>
- Required files: <paths inside this directory>

## Steps

1. <Setup action>
   - Expected result: <visible state>
   - Evidence: <what should be on screen>
   - Screenshot: screenshots/01-setup.png

2. <Direct vulnerable action>
   - Expected result: <security boundary should block it>
   - Actual result: <visible vulnerable behavior>
   - Evidence: <response, UI state, crash, file output, or data crossed>
   - Screenshot: screenshots/02-vulnerable-action.png

## Cleanup

<Only include if needed.>
```

Keep positive/negative controls in the verifier proof packet. In this phase,
focus on the cleanest human reproduction path.

## Output Format

```text
Triage theater package: <path>
Human flow: <direct request / UI workflow / command / crash input / project>
Primary trigger: <the exact visible action>
Screenshots: <captured count and pending count>
Mocks or wrappers: <none or why they are necessary>
Report handoff: <artifacts report-writer should use>
Remaining gaps: <none or exact human-demo issue>
```

Use `report-writer` after this skill when the user needs a bounty submission,
advisory, internal report, or attachment bundle.
