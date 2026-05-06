---
name: engagement-scope
description: Establish authorized engagement context, look up public bounty scope evidence, and route ATTACK cyber tasks before using specialized skills. Use for any request to model security boundaries, review code vulnerabilities, inspect web or mobile apps, research CVEs, build fuzzers, reverse or debug binaries, or analyze exploit chains, especially when target authorization, bounty program scope, impact tolerance, or the desired deliverable is unclear.
---

# Engagement Scope

Use this skill as the first stop for ATTACK workflows. Define what is authorized, what is in scope, what level of impact is acceptable, and which specialized skill should carry the work forward.

## Scope Workflow

1. Identify the requested security activity.
2. Determine whether the target, authorization context, and boundaries are already clear from the conversation, local workspace, or provided materials.
3. If the user names a public bounty or vulnerability disclosure program, collect current scope evidence from official sources before assuming coverage.
4. Ask only for missing information that changes whether work can proceed safely or changes the technical approach.
5. Produce a short engagement brief before handing off to a specialized skill.
6. Re-check scope before any step that would materially increase impact, touch live external systems, attempt exploitation, collect sensitive data, or alter target state.

## Authorization Check

Proceed when there is a clear authorized context, such as:

- The target is source code, binaries, logs, configs, or infrastructure artifacts supplied by the user in the workspace.
- The user states they own or administer the target.
- The user provides a bug bounty, pentest, audit, lab, CTF, or internal security-testing context with scope boundaries.
- The task is non-destructive analysis, reproduction in a local lab, hardening, or report preparation for an authorized finding.

Pause and ask a concise scope question when:

- The target is a live third-party system and authorization is not stated.
- The request could affect availability, integrity, confidentiality, accounts, data, or logs outside a local lab.

## Public Scope Lookup

When a user mentions a public bounty platform, program handle, or official VRP, verify scope from official sources before treating the target as authorized. Prefer current, specific program rules over general company ownership.

Source priority:

1. User-provided private invitation, contract, rules of engagement, or current program brief.
2. Official platform program page or official platform API for the named program.
3. Official company security, bounty, or vulnerability disclosure page.
4. Official `security.txt` as a lead when no program page is known.
5. Third-party directories, public writeups, or search snippets as discovery leads only.

For HackerOne public programs, use `scripts/hackerone_program_lookup.py` when a handle is known. Resolve the script path relative to this skill directory:

```bash
python scripts/hackerone_program_lookup.py <handle> --format markdown --eligible-for-submission yes --limit 50
python scripts/hackerone_program_lookup.py <handle> --format markdown --search <asset-or-domain> --limit 20
python scripts/hackerone_program_lookup.py <handle> --format json --all
python scripts/hackerone_program_lookup.py <handle> --refresh --format markdown --eligible-for-submission yes
```

Use `--eligible-for-submission yes` to focus on testable assets, `--eligible-for-bounty yes` to focus on bounty-eligible assets, and `--search` for a specific domain, repository, app, or package. Treat the script as a best-effort public lookup through HackerOne's current GraphQL surface; verify important decisions against the official program page at `https://hackerone.com/<handle>?type=team`.

The HackerOne script uses a persistent cache by default to avoid repeated scope pulls across conversations. Default cache location is `$CODEX_HOME/cache/codex-attack/engagement-scope` when `CODEX_HOME` is set, otherwise `~/.codex/cache/codex-attack/engagement-scope`. Default TTL is 6 hours. Use `--refresh` before active testing, when the user asks for current scope, or when cache metadata is older than the engagement requires. Use `--no-cache` for one-off uncached reads, `--cache-dir` to isolate a cache, or `ATTACK_SCOPE_CACHE_DIR` / `ATTACK_SCOPE_CACHE_TTL` to change defaults.

For Bugcrowd, Intigriti, YesWeHack, and major direct programs, read `references/bounty-scope-sources.md` only when needed. Use it to find official scope pages and to decide what evidence to capture.

## Engagement Brief

Before routing, summarize the working frame in compact form:

```text
Authorized context: <what establishes permission or what remains unknown>
Scope evidence: <official program URL, API/script result, cache hit/refresh, date checked, policy version/change date>
Target assets: <repos, apps, hosts, binaries, versions, files, accounts>
In scope: <allowed systems, code paths, vulnerability classes, techniques>
Out of scope: <systems, data, techniques, timing, impact limits>
Objective: <review, reproduce, fuzz, reverse, debug, research, report>
Impact tolerance: <read-only, local-only, low-rate live testing, invasive lab testing>
Deliverable: <findings, patch, PoC-in-lab, harness, threat model, report>
Next skill: <specialized ATTACK skill>
```

Use `unknown` sparingly. If an unknown affects safety or execution, ask before proceeding.

When scope comes from a public bounty program, include exact asset identifiers or rule text summaries. Do not collapse a precise target list into a broad phrase like "company assets" unless the official program explicitly defines an open scope.

## Routing

Route to one primary skill. Mention secondary skills only when they are likely to be needed later.

- Use `code-vulnerability-review` for source-code audits, insecure patterns, dependency risk, data-flow review, patch review, and remediation planning.
- Use `web-app-security-inspection` for browser-visible behavior, HTTP flows, authentication, authorization, API testing, session handling, and live or local web apps.
- Use `cve-research` for vulnerability intelligence, affected-version checks, exploitability analysis from public sources, and advisory triage.
- Use `fuzz-harness-builder` for parser, protocol, API, CLI, library, or file-format fuzzing and deterministic test harnesses.
- Use `binary-debugging` for runtime inspection, crash triage, debugger workflows, memory state, symbols, and dynamic behavior.
- Use `binary-reversing` for static analysis, disassembly, decompilation, binary structure, protocols, and undocumented behavior.
- Use `exploit-chain-analysis` for authorized lab-only proof of exploitability, chaining multiple validated findings, risk demonstration, and report evidence.

## Question Style

Ask the smallest useful question set. Prefer one question when possible.

Useful questions include:

- "What target assets are in scope for this engagement?"
- "What authorization context applies to this target?"
- "Should this stay read-only/local, or is controlled live testing allowed?"
- "What deliverable do you want: findings, a patch, a lab reproduction, a harness, or a report?"
- "Is there a bounty program handle, official scope URL, or private invitation I should use as the authority?"

If enough information is already available, do not ask a ritual preflight. State the inferred scope and proceed.

## Handoff

When another ATTACK skill is used after this one, pass along the engagement brief and the immediate task. Keep the brief visible enough that later work does not drift from authorization, boundaries, and deliverable expectations.
