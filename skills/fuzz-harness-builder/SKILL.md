---
name: fuzz-harness-builder
description: Selectively design, implement, run, and triage authorized fuzz harnesses for parsers, codecs, protocols, APIs, CLIs, libraries, native boundaries, kernels, and structured inputs when fuzzing is likely to justify its long-running cost. Use when Codex needs to build libFuzzer/AFL++/Honggfuzz/Centipede/cargo-fuzz/Go fuzz/Jazzer/Atheris/syzkaller-style harnesses, corpora, dictionaries, sanitizers, coverage runs, crash minimization, CI fuzzing, or fuzzing reports, especially after source review, binary reversing, or debugging has identified a fuzzable boundary worth sustained testing.
---

# Fuzz Harness Builder

Use this skill after `engagement-scope` has established the authorized target,
scope evidence, environment, impact tolerance, execution limits, and desired
deliverable. Fuzz only local, lab, CI, or explicitly authorized targets.

Fuzzing is expensive and noisy. Prefer `binary-reversing`, `binary-debugging`,
and `code-vulnerability-review` first when a question can be answered by static
analysis, one crash reproduction, source tracing, patch review, or targeted
debugging. Use this skill only when there is a concrete reason to believe a
fuzzing campaign will pay for its long-running cost.

## Fuzzing Gate

Proceed only when most of these are true:

- A clear boundary exists: parser, decoder, deserializer, protocol handler,
  archive extractor, image/media/document codec, API, CLI option parser,
  kernel syscall/ioctl, native extension, or stateful library API.
- The boundary accepts attacker-controlled or low-trust input in a realistic
  product path.
- A harness can call the boundary cheaply and deterministically without full
  product startup, real credentials, production services, or network dependence.
- There is an oracle: sanitizer, assertion, differential check, invariant,
  timeout, memory limit, semantic validation, or crash signal.
- Seeds, examples, grammar, dictionary tokens, or a format sketch are available
  or can be recovered through reversing/debugging.
- Coverage can be measured and improved; the target is not already heavily and
  effectively fuzzed unless a specific coverage gap or new entry point exists.
- The user has time/compute budget for at least a smoke run and, ideally,
  longer CI or batch fuzzing.

Do not fuzz yet when:

- The target format, entry point, or build path is unknown; reverse or debug
  first.
- A single known crash only needs root-cause triage or patch validation.
- The harness would mostly test mocks, UI, live services, auth, or deployment
  glue rather than the risky boundary.
- Inputs cause irreversible side effects, external traffic, account changes, or
  production load.
- There is no oracle beyond "maybe something interesting happens."
- The code is too slow, nondeterministic, flaky, or stateful to produce useful
  coverage without refactoring.

If the gate is not met, explain the blocker and hand off to the better skill.

## 2026 Practice Bias

Recent successful fuzzing practice emphasizes:

- Harness quality over raw CPU time. Poor harnesses plateau quickly; good
  harnesses isolate deep parser/API logic, avoid irrelevant setup, and expose
  sanitizer-visible faults.
- Coverage feedback with introspection. Use coverage reports and
  Fuzz-Introspector-style data to find blockers, low-coverage high-complexity
  functions, and harness degradation.
- LLM-assisted harness generation is useful when paired with build repair,
  runtime validation, coverage measurement, and human review. Do not trust a
  generated harness until it compiles, runs seeds, reaches target code, and has a
  useful oracle.
- Structure-aware inputs win when raw bytes stall: dictionaries, seed corpora,
  custom mutators, grammar generation, `FuzzedDataProvider`, `arbitrary`,
  Jazzer providers, or syzkaller descriptions.
- Directed and hybrid fuzzing are worth considering only after a target location
  or patch diff identifies where execution should go.
- Continuous fuzzing is where value compounds: CI smoke fuzzing catches
  regressions, while scheduled batch fuzzing grows corpora and finds deeper bugs.

## Modes

Choose one primary mode:

- Harness feasibility: decide whether fuzzing is worth doing and what boundary
  should be targeted.
- Harness implementation: write or modify a harness, build rules, options,
  corpus, dictionary, and sanitizer configuration.
- Corpus and dictionary work: derive seeds from tests, samples, captures,
  minimized crashes, protocol notes, or reversing output.
- Coverage improvement: measure coverage, identify blockers, split targets,
  add seeds/dictionaries, or refactor setup.
- Crash triage: reproduce, minimize, deduplicate, symbolize, classify, and hand
  off to debugging/source review.
- CI or OSS-Fuzz integration: add short PR fuzzing, longer batch fuzzing,
  regression tests, and artifact retention.
- Report prep: summarize harness value, coverage, crashes, root cause leads, and
  next actions.

## Helper Script

Use `scripts/harness_scaffold.py` to create starter harness files for common
ecosystems. The generated code is intentionally minimal and must be adapted to
the real API and build system.

```bash
python3 <skill-dir>/scripts/harness_scaffold.py c-cpp --name parse_config --output fuzz/parse_config_fuzzer.cc
python3 <skill-dir>/scripts/harness_scaffold.py go --name FuzzParseConfig --output parser_fuzz_test.go
python3 <skill-dir>/scripts/harness_scaffold.py rust --name parse_config --output fuzz/fuzz_targets/parse_config.rs
python3 <skill-dir>/scripts/harness_scaffold.py python --name fuzz_parse_config --output fuzz_parse_config.py
python3 <skill-dir>/scripts/harness_scaffold.py java --name ParseConfigFuzzer --output src/test/java/ParseConfigFuzzer.java
```

Do not treat scaffold output as finished. Replace placeholders, add real seeds,
run a smoke test, and verify coverage reaches the intended code.

## Workflow

1. Restate the brief: target boundary, source/binary availability, build system,
   allowed execution, time/CPU limits, sanitizer needs, and deliverable.
2. Apply the fuzzing gate. If fuzzing is not justified, recommend reversing,
   debugging, source review, or a targeted regression test instead.
3. Select the smallest valuable target. Prefer one parser/API mode per harness;
   split formats, protocols, and state machines when one harness hides coverage
   or creates slow setup.
4. Choose engine and instrumentation:
   - C/C++: libFuzzer for in-process harnesses; AFL++/Honggfuzz/Centipede when
     fork/server mode, binary-only, or ensemble fuzzing is useful.
   - Rust: `cargo-fuzz`/libFuzzer, `arbitrary`, or AFL/LibAFL when appropriate.
   - Go: native `go test -fuzz`, with seed corpus under `testdata/fuzz`.
   - JVM: Jazzer/JUnit fuzz tests for Java, Kotlin, Scala, and other JVM code.
   - Python: Atheris for Python/C-extension boundaries.
   - Kernel: syzkaller only when syscall/ioctl descriptions, VM isolation, and
     crash triage workflow are in scope.
5. Build with sanitizers and coverage. Use ASan/UBSan/MSan/TSan/LSan where they
   match the bug class and runtime. Avoid mixing sanitizers that make the target
   too slow or flaky.
6. Add seeds and dictionaries. Start from valid examples, unit fixtures, captures,
   minimized crashes, public corpora, recovered grammar tokens, magic values,
   option names, and protocol constants.
7. Smoke test before long runs. Run seeds and a short fuzz session. Confirm no
   instant crash, OOM, hang, external traffic, nondeterminism, or coverage
   plateau at setup code.
8. Measure coverage and improve. Add targeted seeds/dictionaries, split harnesses,
   remove irrelevant setup, expose deeper APIs, or add structure-aware mutation.
9. Triage crashes. Reproduce, minimize, deduplicate, symbolize, confirm with a
   fixed build if available, and hand off for root cause.
10. Capture the result: harness files, build/run commands, sanitizer settings,
   corpus/dictionary, coverage summary, crashes, limitations, and next run plan.

## Harness Quality Rules

A good harness:

- Is deterministic, fast, isolated, and in-process when possible.
- Accepts arbitrary byte input, including empty, huge, malformed, duplicate, and
  partially valid inputs.
- Avoids `exit`, network calls, real credentials, persistent external state,
  sleeps, excessive logging, and global state that leaks across iterations.
- Resets parser/library state between iterations.
- Checks meaningful invariants and lets sanitizers catch memory/lifetime bugs.
- Parses one meaningful boundary rather than booting the whole application.
- Builds with the project tests or CI so it does not rot.

A bad harness mostly fuzzes constructors, mocks, CLI wrappers, auth setup,
network glue, logging, or validation that rejects nearly every input before
reaching the risky code.

## Corpus, Dictionary, And Structure

Use the lightest structure that improves reach:

- Seed corpus: minimal files/messages that cover major modes and edge cases.
- Dictionary: magic bytes, tags, keywords, delimiters, option names, MIME types,
  protocol verbs, enum strings, and common header fields.
- Fuzzed data provider: split raw bytes into typed fields, sizes, flags, and
  repeated records without hardcoding one shape.
- Grammar or custom mutator: use only when the target rejects raw mutations too
  early or valid nesting/checksums are required.
- Differential oracle: compare two implementations, old/new versions, encode/
  decode round trips, parser/serializer symmetry, or strict/lenient modes.

Keep corpus small and coverage-rich. Minimize crashes and promote useful
regression inputs back into tests.

## Coverage And Stopping Criteria

Track:

- Lines/functions/edges reached in the intended boundary.
- New coverage over time and whether execution is stuck in setup or validation.
- Execs/sec, timeout rate, OOM rate, flaky crash rate, and memory growth.
- Uncovered high-complexity functions or patch-diff targets.
- Crashes by stack signature and sanitizer class.

Stop or redirect when:

- The harness never reaches the intended code after seeds and dictionary work.
- Coverage plateaus in uninteresting code and the next improvement requires
  reversing/debugging or refactoring.
- Crashes are all duplicates, expected aborts, or harness bugs.
- The campaign exceeds the agreed compute/time budget.

## Crash Triage

For each crash:

1. Reproduce with the same binary, sanitizer, options, and input.
2. Minimize input and command line.
3. Deduplicate by stack, sanitizer type, faulting function, and root cause.
4. Decide whether it is harness bug, expected rejection, benign assertion,
   resource exhaustion, DoS, memory safety, logic flaw, or security lead.
5. Hand off to `binary-debugging` or `code-vulnerability-review` for root cause
   and fix when needed.

Do not report raw fuzzer crashes as vulnerabilities without reachability,
control, impact, and root-cause evidence.

## Evidence Standard

Treat a fuzzing result as useful only when it can explain:

- Why fuzzing was justified and why simpler analysis was insufficient.
- Target boundary, attacker model, harness entry point, and code reached.
- Engine, sanitizer, build flags, corpus, dictionary, timeout, memory limit, and
  run duration.
- Coverage before/after and whether coverage includes the intended boundary.
- Crash reproduction, minimization, deduplication, stack, sanitizer output, and
  suspected root cause.
- Constraints: flakiness, nondeterminism, environment, missing symbols, harness
  limitations, or unvalidated runtime assumptions.
- Next action: continue batch fuzzing, improve harness, fix bug, add regression,
  hand off, or stop.

## Output Format

For harness deliverables:

```text
Decision: <fuzz / do not fuzz yet>
Rationale: <why fuzzing is worth it or what must happen first>
Target boundary: <parser/API/protocol/CLI/kernel/etc.>
Harness files: <paths>
Engine and sanitizers: <tooling and flags>
Seeds/dictionary: <sources and paths>
Smoke result: <build/run/coverage/crash status>
Coverage: <what was reached and blockers>
Crashes: <none or summarized with repro/minimized inputs>
Limitations: <flakiness, missing grammar, slow setup, unknowns>
Next action: <long run / CI / debug crash / improve harness / stop>
```

For crash findings, use the `binary-debugging` or `code-vulnerability-review`
finding format after root-cause validation.

## Handoff

Use `binary-reversing` when the input format, protocol, function map, or target
boundary is unclear. Use `binary-debugging` when reproducing, symbolizing, or
root-causing a crash requires runtime state. Use `code-vulnerability-review`
when source-level reachability, patching, or tests are needed. Use
`cve-research` for public advisories and affected-version analysis. Use
`exploit-chain-analysis` only for authorized lab-only chaining after individual
issues are validated.

## Research Basis

This workflow reflects OSS-Fuzz ideal integration guidance, Fuzz Introspector
coverage-gap practice, libFuzzer, AFL++, Go fuzzing, Rust cargo-fuzz, Jazzer,
Atheris, syzkaller, ClusterFuzzLite, FuzzBench, and 2026 research on
LLM-assisted harness generation, coverage-guided refinement, directed fuzzing,
hybrid fuzzing, option-aware fuzzing, and structure-aware fuzzing. Treat these
as prioritization signals; the engagement scope and observed target behavior
remain authoritative.
