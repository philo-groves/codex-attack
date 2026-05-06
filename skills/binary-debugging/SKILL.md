---
name: binary-debugging
description: Debug authorized binaries, native crashes, core dumps, sanitizer reports, process state, runtime behavior, memory corruption, register state, symbols, dynamic loading, and exploitability evidence using debuggers and tracing tools. Use when Codex needs to inspect ELF/Mach-O/PE executables, shared libraries, firmware userspace binaries, native extensions, crash logs, minidumps, core files, GDB/LLDB/WinDbg sessions, ASAN/UBSAN/TSAN output, strace/ltrace/dtruss traces, or runtime behavior that cannot be resolved from source review alone.
---

# Binary Debugging

Use this skill after `engagement-scope` has established the authorized target,
scope evidence, environment, impact tolerance, and desired deliverable. If no
brief is present, infer local/offline scope from files in the workspace and ask
only for missing information that changes whether execution or instrumentation
is allowed.

Prefer local, reproducible, low-impact debugging: static inspection, crash/core
analysis, sanitizer output, recorded traces, and isolated lab execution. Do not
attach to production processes, run unknown binaries, fuzz live services, or
exercise exploit payloads unless the engagement explicitly allows that impact.

## Debugging Modes

Choose one primary mode:

- Binary context: identify file format, architecture, protections, symbols,
  imports, exports, sections, build IDs, and linked libraries.
- Crash triage: inspect signal/exception, fault address, instruction pointer,
  registers, stack, backtrace, threads, loaded modules, and sanitizer evidence.
- Reproduction debugging: run a provided input or command in a lab debugger to
  reproduce a crash, hang, assertion, or behavioral bug.
- Memory-corruption analysis: investigate use-after-free, heap overflow, stack
  overflow, out-of-bounds access, integer overflow, type confusion, double free,
  uninitialized memory, and lifetime bugs.
- Runtime trace: collect syscalls, library calls, file/network access, dynamic
  loader behavior, environment use, and IPC without full reverse engineering.
- Patch and regression validation: confirm a fix changes the failing behavior
  and does not hide the crash without addressing the root cause.
- Report prep: turn debugger evidence into a clear internal, bounty, or advisory
  finding.

## Quick Context Helper

Use `scripts/binary_context.py` to collect non-executing file context when a
binary, library, crash-adjacent executable, or unknown artifact is present.

```bash
python3 <skill-dir>/scripts/binary_context.py ./path/to/binary
python3 <skill-dir>/scripts/binary_context.py --json ./path/to/binary
```

The helper runs whichever local inspection tools are available. It is a starting
point; inspect debugger state and source/assembly context before forming a
finding.

## Workflow

1. Restate the brief: target files, platform, architecture, inputs, crash/core
   artifacts, allowed execution, allowed instrumentation, and deliverable.
2. Inventory artifacts. Identify binaries, libraries, symbols, source, inputs,
   logs, cores/minidumps, ASAN reports, container/VM setup, and exact command
   lines.
3. Collect static context before execution: file type, architecture, bitness,
   endianness, compiler/runtime hints, security protections, imported libraries,
   exported symbols, debug symbols, build IDs, and stripped status.
4. Reproduce safely when allowed. Pin arguments, environment, working directory,
   input files, locale, resource limits, container/VM snapshot, and ASLR/core
   settings so results are repeatable.
5. Capture crash facts: signal/exception, faulting instruction, registers,
   backtrace for all threads, loaded modules, memory maps, faulting address
   classification, tainted input offsets, and sanitizer diagnostics.
6. Minimize the hypothesis. Decide whether the failure is parser state, bounds,
   lifetime, type, integer arithmetic, race, unsafe FFI, dynamic loading,
   environment/path trust, or configuration.
7. Validate root cause. Correlate source, disassembly, runtime values, allocator
   state, and input influence. Prefer a small crashing input or deterministic
   reproduction over a large opaque trace.
8. Produce the deliverable: triage notes, exploitability assessment, root cause,
   patch guidance, regression test, or report text.

## Tool Selection

Use the native debugger and artifact format:

- Linux ELF/core: `gdb`, `coredumpctl`, `eu-stack`, `readelf`, `objdump`,
  `nm`, `addr2line`, `strace`, `ltrace`, `perf`, sanitizers, Valgrind, rr.
- macOS Mach-O/crash: `lldb`, `atos`, `otool`, `dtruss`, crash reports,
  Instruments, sanitizers.
- Windows PE/minidump: WinDbg, Visual Studio debugger, `dumpbin`, ProcMon,
  Process Explorer, Application Verifier, PageHeap, sanitizers when available.
- Cross-platform/native extensions: `lldb` or `gdb`, language runtime crash
  output, FFI boundary logs, symbols for both host runtime and native module.

Prefer the simplest tool that answers the next question. Use dynamic
instrumentation or heavyweight tracing only when static context and ordinary
debugger state are insufficient.

## Reproduction Discipline

Record:

- Binary path, hash, version, build ID, architecture, and symbol status.
- OS/kernel/runtime version, container/VM image, loader path, environment, and
  relevant resource limits.
- Exact command line, input files, stdin, network fixture, config, and current
  working directory.
- Debugger/tool versions and important settings such as ASLR, core pattern,
  allocator options, sanitizer options, and timeout.

Before varying inputs, preserve a baseline crash. Change one variable at a time.
Use checksums for crash inputs and avoid editing original user artifacts in
place.

## Crash Triage Checklist

For each crash, answer:

- What stopped: signal, exception code, sanitizer finding, assertion, timeout, or
  abort?
- Where stopped: module, function, offset, source line, instruction, and
  disassembly context.
- What memory: fault address, mapped/unmapped, null/near-null, heap, stack,
  code, freed, guard page, or controlled-looking data.
- What control: attacker-controlled input reaches length, index, pointer, type,
  state machine, format string, path, environment, or concurrency edge.
- What path: call stack from input parser or API entry point to failing sink.
- What mitigations: ASLR, PIE, NX/DEP, stack canary, RELRO, CFG/CET/PAC,
  sandbox, seccomp, AppContainer, hardened runtime, privilege separation.
- What changed: fixed build, patch, input minimization, or configuration that
  removes the crash.

## Exploitability Triage

Stay evidence-driven. Use `Confirmed`, `Likely`, `Potential`, or `Unknown` for
control and impact when proof is incomplete.

High-risk signals:

- Instruction pointer, return address, function pointer, vtable, jump target, or
  allocator metadata influenced by input.
- Write-what-where, controlled heap overflow, stack overflow, type confusion,
  use-after-free with reclaim control, format string, or out-of-bounds write.
- Crash occurs before authentication or in a privileged parser, service,
  browser/document renderer, kernel/driver, setuid helper, or sandbox broker.
- Input can be delivered remotely, through a file previewer, archive extractor,
  plugin loader, IPC boundary, or automated indexing path.

Lower-confidence signals:

- Read-only null dereference in a low-privilege local tool.
- Abort/assertion after safe bounds checks.
- Crash requires trusted local access, debug flags, artificial limits, or
  unrealistic resource exhaustion.
- Sanitizer-only failure where production allocator behavior is unclear.

Do not provide weaponized exploit steps in general reports. Provide enough
detail for defensive validation: control surface, crash primitive, constraints,
mitigations, and remediation path.

## Memory And State Inspection

Inspect:

- Registers and flags at crash.
- Stack frames, arguments, locals, and inlined frames.
- Heap allocation metadata where safe and supported.
- Memory maps, permissions, and module base addresses.
- Nearby disassembly and source correlation.
- Input buffer locations, decoded structures, lengths, offsets, and ownership.
- Thread states, locks, condition variables, signal handlers, and async callbacks
  for race/hang bugs.

Use watchpoints, catchpoints, conditional breakpoints, reverse debugging, rr, or
sanitizers when the write/free happens before the observed crash.

## Dynamic Loading And Environment Trust

Check loader and environment boundaries:

- RPATH/RUNPATH, `LD_LIBRARY_PATH`, `DYLD_*`, DLL search order, plugin paths,
  config paths, current working directory, and relative file opens.
- Setuid/setgid, elevated helpers, services, scheduled tasks, installers, and
  auto-update paths.
- Signature, quarantine, Mark-of-the-Web, hardened runtime, entitlements,
  AppContainer, and sandbox profiles where relevant.

Confirm whether lower-privileged users can influence a path, library, config,
environment variable, IPC message, or working directory used by privileged code.

## Evidence Standard

Treat a finding as confirmed only when the debugging record can explain:

- Artifact identity: binary, version, hash, architecture, build ID, symbols, and
  environment.
- Entry point: command, file, protocol message, API, IPC, service, previewer, or
  loader path.
- Trigger: exact input, state, timing, and configuration needed.
- Root cause: vulnerable operation and why validation, lifetime, bounds, type,
  synchronization, or trust boundary fails.
- Control: what the attacker influences and how that influence reaches the
  crash or dangerous operation.
- Impact: crash-only DoS, information disclosure, privilege escalation, sandbox
  escape, code execution potential, or unknown.
- Constraints: privileges, user interaction, mitigations, sandboxing,
  architecture, build flags, allocator behavior, and reliability.
- Fix path: specific validation, ownership, bounds, lifetime, synchronization,
  parser, or privilege-separation change and regression test.

## Output Format

For crash or vulnerability findings:

```text
Finding: <short title>
Severity: <critical/high/medium/low/info>
Confidence: <high/medium/low>
Artifact: <binary, version, hash, architecture>
Environment: <OS/runtime/debugger/settings>
Entry point: <command/API/file/protocol/IPC>
Crash: <signal/exception, fault address, instruction, stack summary>
Root cause: <failing operation and missing guard>
Control: <attacker-controlled values and constraints>
Impact: <DoS/info leak/privesc/RCE potential/sandbox escape>
Evidence: <registers, backtrace, disassembly/source, sanitizer trace>
Fix: <specific remediation>
Tests: <regression, sanitizer, minimized input, harness>
```

If no security issue is found, state the artifacts, inputs, debugger/tooling,
paths inspected, assumptions, and remaining unknowns.

## Handoff

Use `binary-reversing` when static structure, protocols, undocumented behavior,
or decompilation is the blocker. Use `code-vulnerability-review` when source
root cause or patch review is needed. Use `fuzz-harness-builder` when a parser,
codec, file format, protocol, or API needs systematic input generation. Use
`cve-research` for public advisories and affected-version analysis. Use
`exploit-chain-analysis` only for authorized lab-only chaining after individual
issues are validated.
