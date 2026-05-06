---
name: binary-reversing
description: Reverse engineer authorized binaries and native artifacts through static analysis, disassembly, decompilation, strings, imports, symbols, file formats, firmware contents, protocols, config extraction, patch diffing, obfuscation triage, and security-relevant behavior recovery. Use when Codex needs to inspect ELF/Mach-O/PE files, shared libraries, firmware userspace binaries, native extensions, packed or stripped artifacts, proprietary protocols, license or crypto logic, malware-like samples in a defensive lab, or undocumented behavior without source code.
---

# Binary Reversing

Use this skill after `engagement-scope` has established the authorized target,
scope evidence, artifact handling rules, and desired deliverable. If no brief is
present, infer local/offline scope from files in the workspace and ask only for
missing context that changes whether unpacking, emulation, or dynamic execution
is allowed.

Default to static analysis. Do not execute unknown binaries, detonate suspicious
samples, contact embedded network endpoints, or run unpacked code unless the
engagement explicitly allows isolated lab execution. Use `binary-debugging` when
runtime state, crashes, registers, traces, or process behavior become the
blocker.

## Reversing Modes

Choose one primary mode:

- Artifact triage: identify format, architecture, compiler/runtime, protections,
  packing, entropy, symbols, imports, exports, strings, and embedded resources.
- Behavior recovery: reconstruct high-level purpose, entry points, major
  functions, state machines, file/network/process behavior, and trust boundaries.
- Protocol or file-format analysis: recover message formats, parsers, encodings,
  checksums, compression, serialization, command IDs, and error handling.
- Config and secret extraction: locate embedded config, keys, certificates,
  endpoints, feature flags, license material, and environment assumptions.
- Patch diffing: compare vulnerable and fixed binaries to identify changed
  functions, constants, guards, and likely root cause.
- Firmware or appliance triage: unpack images, identify filesystems, init
  scripts, services, web roots, credentials, update logic, and privileged
  helpers.
- Obfuscation or packing triage: identify packers, protectors, encryption,
  virtualized control flow, anti-analysis checks, and unpacking requirements.
- Report prep: turn static evidence into a clear technical summary, finding,
  advisory background, or handoff for debugging/fuzzing.

## Quick Strings Helper

Use `scripts/string_triage.py` for non-executing string and clue extraction.

```bash
python3 <skill-dir>/scripts/string_triage.py ./path/to/artifact
python3 <skill-dir>/scripts/string_triage.py --json --min-len 6 ./path/to/artifact
```

The helper extracts ASCII and UTF-16LE strings, hashes the file, estimates
entropy, and groups interesting strings such as URLs, IPs, paths, commands,
crypto terms, auth material, API names, and error messages. Treat output as a
lead list, not proof of behavior.

For format/protection context, reuse `binary-debugging/scripts/binary_context.py`
when that skill is available in the same plugin.

## Workflow

1. Restate the brief: artifact paths, platform, architecture, suspected purpose,
   allowed operations, prohibited operations, and deliverable.
2. Preserve artifact identity. Record path, size, hashes, source, container or
   firmware image, extraction steps, and whether the artifact may be sensitive.
3. Triage statically. Identify file type, architecture, endianness, compiler,
   runtime, linking, symbols, imports, exports, sections, resources, entropy,
   strings, embedded files, and obvious packers or obfuscators.
4. Build a map before drilling down. Identify entry points, initialization,
   command dispatch, parser functions, crypto/config paths, network/file/process
   APIs, privilege boundaries, and error paths.
5. Name and annotate as evidence accumulates. Prefer stable names based on
   behavior, references, constants, strings, and call graph position.
6. Recover data structures and formats. Track lengths, tags, magic values,
   checksums, endian conversions, state enums, tables, object layouts, and
   ownership/lifetime conventions.
7. Validate hypotheses through cross-references, caller/callee checks, constants,
   strings, imports, and patch/source comparisons before reporting behavior.
8. Produce the deliverable: triage summary, behavior notes, protocol sketch,
   config extraction, vulnerability lead, patch diff result, or handoff package.

## Tool Selection

Use the artifact's native ecosystem and the lightest tool that answers the next
question:

- General static triage: `file`, `strings`, `readelf`, `objdump`, `nm`,
  `rabin2`, `rizin`, `radare2`, `lief`, `capa`, `yara`, `binwalk`, `xxd`.
- Decompilation and graphing: Ghidra, Binary Ninja, IDA, Hopper, RetDec, angr.
- ELF/Linux: `readelf`, `objdump`, `eu-readelf`, `patchelf`, `ldd` only for
  trusted binaries, libc/libstdc++ symbol knowledge.
- Mach-O/macOS/iOS: `otool`, `jtool2`, `class-dump`, `codesign`, `plutil`,
  Swift/Objective-C metadata tools.
- PE/Windows: PEStudio, CFF Explorer, `dumpbin`, `sigcheck`, `lief`,
  Resource Hacker, .NET ILSpy/dnSpy for managed assemblies.
- Firmware: `binwalk`, `unsquashfs`, `cpio`, `7z`, `ubi_reader`, filesystem
  tools, init/service/web-root inspection.

Avoid relying on one decompiler view. Cross-check important logic against
disassembly, references, constants, and callers.

## Static Triage Checklist

Collect:

- Format, architecture, bitness, endianness, compiler/runtime, build ID, and
  stripped/debug-symbol status.
- Sections/segments, permissions, relocations, TLS callbacks, constructors,
  Objective-C/Swift/.NET metadata, and resources.
- Imports and exports grouped by behavior: file, network, process, registry,
  crypto, compression, parsing, IPC, dynamic loading, privilege, sandbox.
- Strings grouped by behavior: URLs, domains, paths, commands, config keys,
  errors, protocol constants, user-agent strings, SQL, scripts, certificates,
  keys, license text, and debug logs.
- Entropy, packed-looking sections, tiny import tables, suspicious overlays,
  embedded archives, compressed blobs, and encrypted config.
- Security-relevant mitigations and trust boundaries: signature checks, update
  checks, path validation, parser bounds, auth checks, sandbox profile, and
  privilege transitions.

## Function And Data Recovery

Prioritize functions that sit on trust boundaries:

- Input parsers, decoders, archive handlers, image/media/document parsers,
  protocol handlers, IPC handlers, plugin loaders, update installers, license
  checks, command dispatchers, and auth/config readers.
- Sinks for memory safety or command risk: copies, formatters, allocators,
  deserializers, shell/process APIs, dynamic library loading, file writes,
  registry writes, network fetches, and script/template execution.
- Guards: length checks, canonicalization, signature verification, MAC/HMAC,
  auth checks, role checks, sandbox checks, feature flags, and error returns.

Recover:

- Function purpose, arguments, return values, error conventions, ownership rules,
  object layouts, global state, state machines, tables, and callback chains.
- Taint path from untrusted input to parser, decision, allocation, copy, branch,
  file/network/process operation, or privileged action.
- Why a guard is sufficient, missing, bypassable, or unreachable.

## Protocol And File-Format Reversing

Document enough to validate behavior without overfitting one sample:

- Magic bytes, version, endian, length fields, tags, checksums, compression,
  encryption, authentication, optional fields, and nesting.
- Message or record types, command IDs, state transitions, error codes, and
  retry behavior.
- Parser trust assumptions: maximum lengths, integer conversions, recursion,
  allocation strategy, partial reads, duplicate fields, unknown-field handling,
  and downgrade paths.
- Test vectors or packet/file sketches that are safe and minimal.

Use `fuzz-harness-builder` when the recovered format should become a harness or
corpus.

## Patch Diffing

When comparing versions:

1. Normalize artifacts: architecture, build options, stripping, compiler, and
   packaging.
2. Match functions using symbols when present, then imports, strings, constants,
   call graph shape, function size, and control-flow fingerprints.
3. Identify changed guards, constants, parser branches, allocation sizes, bounds
   checks, signature checks, and removed dangerous calls.
4. Tie the change to an affected feature and attacker-controlled input before
   calling it a security fix.
5. Record confidence and any ambiguity caused by optimization, inlining, or
   broad refactors.

## Obfuscation And Packed Artifacts

Do not rush into execution. First identify:

- High entropy sections or resources, unusual section names, overlays, TLS
  callbacks, self-modifying code, import resolution loops, opaque predicates,
  anti-debug checks, VM/protector signatures, and encrypted string/config blobs.
- Whether safe static unpacking is possible through archive extraction,
  resource decoding, known packer tooling, or vendor update format parsing.

If dynamic unpacking is necessary, hand off to `binary-debugging` with a lab plan
that avoids network contact, uses snapshots, captures memory safely, and records
exact tool settings.

## Evidence Standard

Treat a reversed conclusion as reliable only when it can explain:

- Artifact identity: hash, format, architecture, version, build ID, extraction
  path, and symbol status.
- Location: function name or address, file offset, section/resource, string
  offset, import/export, xrefs, and call graph context.
- Behavior: what the code does, which data it reads/writes, and which APIs or
  helpers it calls.
- Control: which input, config, environment, file, packet, or caller influences
  the behavior.
- Boundary: parser, auth, crypto, update, sandbox, privilege, filesystem,
  network, IPC, or plugin trust boundary.
- Confidence: direct evidence, inferred evidence, decompiler uncertainty,
  missing symbols, packing, or unvalidated runtime assumptions.
- Next step: source review, debugging, fuzz harness, CVE research, mitigation,
  or no further action.

Use `Confirmed`, `Likely`, `Possible`, or `Unknown` rather than presenting
decompiler guesses as fact.

## Output Format

For reversing summaries:

```text
Artifact: <path, hash, format, arch, version/build>
Objective: <question being answered>
Summary: <high-level behavior or conclusion>
Key locations: <functions/offsets/strings/imports/resources>
Evidence: <xrefs, constants, call graph, decompiler/disassembly facts>
Inputs and trust boundaries: <what influences the code>
Security relevance: <risk, impact, or why benign>
Confidence: <high/medium/low and why>
Next steps: <debugging/fuzzing/source review/report/none>
```

For vulnerability leads, include the suspected entry point, attacker-controlled
data, sink, missing guard, impact hypothesis, and validation needed.

## Handoff

Use `binary-debugging` when runtime state, crashes, unpacking, traces, memory, or
register evidence is needed. Use `code-vulnerability-review` when source is
available for root-cause validation or remediation. Use `fuzz-harness-builder`
when a parser/protocol/file format should be tested systematically. Use
`cve-research` for public advisories and affected-version analysis. Use
`exploit-chain-analysis` only for authorized lab-only chaining after individual
issues are validated.
