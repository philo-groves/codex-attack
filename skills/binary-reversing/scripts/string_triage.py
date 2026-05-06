#!/usr/bin/env python3
"""Extract and group strings from local artifacts without executing them."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PRINTABLE = set(range(0x20, 0x7F)) | {0x09}
CATEGORIES: dict[str, re.Pattern[str]] = {
    "urls": re.compile(r"https?://|wss?://|ftp://", re.I),
    "ips": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "domains": re.compile(r"\b[a-z0-9][a-z0-9.-]{2,}\.[a-z]{2,}\b", re.I),
    "windows_paths": re.compile(r"[a-z]:\\|\\\\[a-z0-9_.-]+\\", re.I),
    "unix_paths": re.compile(r"(^|[\s'\"])/(?:[A-Za-z0-9_.+-]+/?)"),
    "commands": re.compile(r"\b(cmd\.exe|powershell|pwsh|/bin/sh|/bin/bash|curl|wget|chmod|chown|system\(|execve|CreateProcess)\b", re.I),
    "crypto": re.compile(r"\b(aes|rsa|ecdsa|ed25519|sha-?256|sha-?1|md5|hmac|pbkdf|bcrypt|scrypt|nonce|cipher|x509|certificate|private key)\b", re.I),
    "auth_secrets": re.compile(r"\b(api[_-]?key|secret|token|bearer|password|passwd|credential|authorization|cookie|jwt)\b", re.I),
    "network_apis": re.compile(r"\b(socket|connect|listen|accept|send|recv|http|grpc|websocket|dns|tls|ssl)\b", re.I),
    "file_registry": re.compile(r"\b(fopen|openat|CreateFile|RegOpenKey|RegSetValue|HKLM|HKCU|sqlite|\.db|\.conf|\.json|\.yaml|\.xml)\b", re.I),
    "errors_debug": re.compile(r"\b(error|failed|exception|assert|debug|trace|panic|fatal|usage:|invalid)\b", re.I),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def extract_ascii(data: bytes, min_len: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    start = None
    buf = bytearray()
    for i, b in enumerate(data):
        if b in PRINTABLE:
            if start is None:
                start = i
            buf.append(b)
        else:
            if start is not None and len(buf) >= min_len:
                out.append({"offset": start, "encoding": "ascii", "value": buf.decode("ascii", "replace")})
            start = None
            buf = bytearray()
    if start is not None and len(buf) >= min_len:
        out.append({"offset": start, "encoding": "ascii", "value": buf.decode("ascii", "replace")})
    return out


def extract_utf16le(data: bytes, min_len: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    i = 0
    while i + 1 < len(data):
        start = i
        chars = []
        while i + 1 < len(data) and data[i + 1] == 0 and data[i] in PRINTABLE:
            chars.append(data[i])
            i += 2
        if len(chars) >= min_len:
            out.append({"offset": start, "encoding": "utf-16le", "value": bytes(chars).decode("ascii", "replace")})
        if i == start:
            i += 1
    return out


def dedupe(strings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for item in strings:
        key = (item["encoding"], item["value"])
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def categorize(strings: list[dict[str, Any]], limit: int) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in strings:
        value = item["value"]
        for name, pattern in CATEGORIES.items():
            if pattern.search(value) and len(groups[name]) < limit:
                groups[name].append(item)
    return dict(groups)


def interesting(strings: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    scored = []
    for item in strings:
        value = item["value"]
        score = 0
        score += min(len(value) // 20, 5)
        score += sum(3 for pattern in CATEGORIES.values() if pattern.search(value))
        score += 2 if any(c in value for c in "{}[]=:/\\") else 0
        score += 2 if re.search(r"[A-Za-z0-9+/]{32,}={0,2}", value) else 0
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["offset"]))
    return [item for _, item in scored[:limit]]


def collect(path: Path, min_len: int, limit: int) -> dict[str, Any]:
    data = path.read_bytes()
    strings = dedupe(extract_ascii(data, min_len) + extract_utf16le(data, min_len))
    strings.sort(key=lambda item: item["offset"])
    return {
        "path": str(path),
        "size": len(data),
        "sha256": sha256(path),
        "entropy": round(entropy(data), 4),
        "string_count": len(strings),
        "categories": categorize(strings, limit),
        "interesting": interesting(strings, limit),
    }


def fmt_item(item: dict[str, Any]) -> str:
    value = item["value"].replace("\n", "\\n").replace("\r", "\\r")
    if len(value) > 220:
        value = value[:217] + "..."
    return f"0x{item['offset']:x} {item['encoding']}: {value}"


def print_markdown(report: dict[str, Any]) -> None:
    print("# String Triage")
    print()
    print(f"- Path: `{report['path']}`")
    print(f"- Size: {report['size']} bytes")
    print(f"- SHA-256: `{report['sha256']}`")
    print(f"- Entropy: {report['entropy']} bits/byte")
    print(f"- Unique strings: {report['string_count']}")
    print()

    for name, items in report["categories"].items():
        if not items:
            continue
        print(f"## {name}")
        print()
        for item in items:
            print(f"- `{fmt_item(item)}`")
        print()

    if report["interesting"]:
        print("## interesting")
        print()
        for item in report["interesting"]:
            print(f"- `{fmt_item(item)}`")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Extract and group strings from a local artifact.")
    parser.add_argument("path", help="artifact path")
    parser.add_argument("--min-len", type=int, default=5, help="minimum string length")
    parser.add_argument("--limit", type=int, default=25, help="max items per category")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print(f"error: not found: {path}", file=sys.stderr)
        return 2
    if not path.is_file():
        print(f"error: not a file: {path}", file=sys.stderr)
        return 2

    report = collect(path, args.min_len, args.limit)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_markdown(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
