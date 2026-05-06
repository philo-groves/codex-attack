#!/usr/bin/env python3
"""Collect static context about local binary artifacts without executing them."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


COMMANDS = {
    "file": ["file", "-b", "{path}"],
    "readelf_header": ["readelf", "-h", "{path}"],
    "readelf_sections": ["readelf", "-S", "{path}"],
    "readelf_dynamic": ["readelf", "-d", "{path}"],
    "readelf_notes": ["readelf", "-n", "{path}"],
    "objdump_file_header": ["objdump", "-f", "{path}"],
    "objdump_private_headers": ["objdump", "-p", "{path}"],
    "nm_dynamic": ["nm", "-D", "{path}"],
    "checksec": ["checksec", "--file={path}"],
    "otool_headers": ["otool", "-hv", "{path}"],
    "otool_load_commands": ["otool", "-l", "{path}"],
    "dumpbin_headers": ["dumpbin", "/headers", "{path}"],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_command(template: list[str], path: Path, max_bytes: int) -> dict[str, Any]:
    cmd = [part.format(path=str(path)) for part in template]
    exe = cmd[0]
    if shutil.which(exe) is None:
        return {"available": False}
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should report tool failures.
        return {"available": True, "error": str(exc), "command": cmd}

    stdout = proc.stdout
    stderr = proc.stderr
    truncated = False
    if len(stdout.encode("utf-8", "replace")) > max_bytes:
        stdout = stdout.encode("utf-8", "replace")[:max_bytes].decode("utf-8", "replace")
        truncated = True
    if len(stderr.encode("utf-8", "replace")) > max_bytes:
        stderr = stderr.encode("utf-8", "replace")[:max_bytes].decode("utf-8", "replace")
        truncated = True
    return {
        "available": True,
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
        "truncated": truncated,
    }


def collect(path: Path, max_bytes: int) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "mode": oct(stat.st_mode & 0o7777),
        "sha256": sha256(path),
        "tools": {
            name: run_command(cmd, path, max_bytes)
            for name, cmd in COMMANDS.items()
        },
    }


def print_markdown(report: dict[str, Any]) -> None:
    print("# Binary Context")
    print()
    print(f"- Path: `{report['path']}`")
    print(f"- Size: {report['size']} bytes")
    print(f"- Mode: `{report['mode']}`")
    print(f"- SHA-256: `{report['sha256']}`")
    print()

    for name, result in report["tools"].items():
        if not result.get("available"):
            continue
        print(f"## {name}")
        print()
        print(f"Command: `{' '.join(result.get('command', []))}`")
        if result.get("returncode") is not None:
            print(f"Return code: {result['returncode']}")
        if result.get("error"):
            print(f"Error: {result['error']}")
        if result.get("stdout"):
            print()
            print("```text")
            print(result["stdout"])
            print("```")
        if result.get("stderr"):
            print()
            print("stderr:")
            print("```text")
            print(result["stderr"])
            print("```")
        if result.get("truncated"):
            print()
            print("_Output truncated._")
        print()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Collect static binary context.")
    parser.add_argument("path", help="binary or library path")
    parser.add_argument("--json", action="store_true", help="print JSON")
    parser.add_argument("--max-bytes", type=int, default=12000, help="max stdout/stderr bytes per tool")
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print(f"error: not found: {path}", file=sys.stderr)
        return 2
    if not path.is_file():
        print(f"error: not a file: {path}", file=sys.stderr)
        return 2

    report = collect(path, args.max_bytes)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_markdown(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
