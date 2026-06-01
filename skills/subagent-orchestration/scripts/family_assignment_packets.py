#!/usr/bin/env python3
"""Create one subagent assignment packet per vulnerability family."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DEFAULT_BATCH_SIZE = 6

FAMILIES: dict[str, dict[str, object]] = {
    "access-control": {
        "title": "Access Control",
        "focus": "authorization, IDOR, tenant/object ownership, role checks, confused deputy paths",
        "seeds": [
            "authz",
            "permission",
            "policy",
            "owner",
            "tenant",
            "role",
            "admin",
            "organization",
            "account_id",
        ],
    },
    "auth-session": {
        "title": "Authentication And Session",
        "focus": "authentication, session lifecycle, OAuth/OIDC, CSRF, token handling, account recovery",
        "seeds": [
            "login",
            "session",
            "cookie",
            "csrf",
            "oauth",
            "oidc",
            "token",
            "jwt",
            "password",
            "recovery",
        ],
    },
    "injection": {
        "title": "Injection",
        "focus": "SQL/NoSQL/LDAP/template injection, command execution, dynamic evaluation, unsafe query construction",
        "seeds": [
            "query",
            "sql",
            "exec",
            "spawn",
            "eval",
            "template",
            "where",
            "filter",
            "shell",
            "deserialize",
        ],
    },
    "ssrf-egress": {
        "title": "SSRF And Egress",
        "focus": "URL fetchers, webhooks, previewers, importers, redirects, internal egress, metadata access",
        "seeds": [
            "url",
            "fetch",
            "webhook",
            "callback",
            "import",
            "preview",
            "metadata",
            "redirect",
            "proxy",
            "http client",
        ],
    },
    "file-path-archive": {
        "title": "File Path And Archive",
        "focus": "uploads, downloads, path traversal, symlinks, archive extraction, MIME/content-type trust, storage ACLs",
        "seeds": [
            "upload",
            "download",
            "path",
            "filename",
            "archive",
            "zip",
            "tar",
            "symlink",
            "mime",
            "storage",
        ],
    },
    "deserialization-parser": {
        "title": "Deserialization And Parser",
        "focus": "unsafe deserialization, parser differentials, XML/entity behavior, codec and structured input bugs",
        "seeds": [
            "parse",
            "decode",
            "deserialize",
            "pickle",
            "yaml",
            "xml",
            "protobuf",
            "json",
            "codec",
            "schema",
        ],
    },
    "crypto-secrets": {
        "title": "Crypto And Secrets",
        "focus": "cryptographic misuse, signatures, nonce/IV handling, webhook validation, secrets exposure, key lifecycle",
        "seeds": [
            "crypto",
            "sign",
            "hmac",
            "nonce",
            "iv",
            "secret",
            "key",
            "token",
            "certificate",
            "webhook signature",
        ],
    },
    "business-logic": {
        "title": "Business Logic",
        "focus": "workflow abuse, payment or quota bypass, state-machine flaws, raceable business transitions",
        "seeds": [
            "state",
            "workflow",
            "limit",
            "quota",
            "payment",
            "billing",
            "approval",
            "invite",
            "race",
            "retry",
        ],
    },
    "supply-chain": {
        "title": "Supply Chain",
        "focus": "dependency risk, package scripts, build/release automation, CI/CD trust, generated artifacts",
        "seeds": [
            "package",
            "dependency",
            "lockfile",
            "build",
            "release",
            "ci",
            "workflow",
            "artifact",
            "script",
            "registry",
        ],
    },
    "memory-concurrency": {
        "title": "Memory And Concurrency",
        "focus": "memory safety, lifetime, bounds, lock/race, async/concurrency, unsafe native boundaries",
        "seeds": [
            "unsafe",
            "malloc",
            "free",
            "buffer",
            "copy",
            "lock",
            "race",
            "thread",
            "async",
            "refcount",
        ],
    },
    "ai-tool-boundary": {
        "title": "AI Tool Boundary",
        "focus": "prompt/tool boundaries, MCP or connector permissions, retrieval isolation, generated-code execution, cross-tenant agent state",
        "seeds": [
            "prompt",
            "tool",
            "mcp",
            "connector",
            "retrieval",
            "agent",
            "sandbox",
            "plugin",
            "system prompt",
            "generated code",
        ],
    },
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_slug(value: str) -> str:
    slug = value.strip().lower()
    if not SLUG_RE.fullmatch(slug):
        raise argparse.ArgumentTypeError("expected a lower-case slug")
    return slug


def normalize_family(value: str) -> str:
    family = value.strip().lower()
    if family not in FAMILIES:
        choices = ", ".join(sorted(FAMILIES))
        raise argparse.ArgumentTypeError(f"unknown family {value!r}; choose one of: {choices}")
    return family


def selected_families(args: argparse.Namespace) -> list[str]:
    if args.all:
        selected = list(FAMILIES)
    else:
        selected = args.family or []
    excluded = set(args.exclude or [])
    selected = [family for family in selected if family not in excluded]
    if not selected:
        raise SystemExit("select at least one family with --family or --all")
    seen: set[str] = set()
    unique = []
    for family in selected:
        if family not in seen:
            seen.add(family)
            unique.append(family)
    return unique


def output_root(args: argparse.Namespace) -> Path:
    workspace = Path(args.workspace).expanduser()
    if args.output_dir:
        return Path(args.output_dir).expanduser()
    if args.goal_id:
        return workspace / "goal" / args.goal_id / "modeling" / "subagents"
    return workspace / "data" / "subagents"


def packet_text(args: argparse.Namespace, family_id: str) -> str:
    family = FAMILIES[family_id]
    title = str(family["title"])
    focus = str(family["focus"])
    seeds = ", ".join(str(seed) for seed in family["seeds"])
    return f"""# Subagent Assignment: {title} Family Audit

Created: {now()}
Assignment ID: family-{family_id}
Goal ID: {args.goal_id or "none"}
Role: auditor
Agent type: explorer
Stage: scan
Vulnerability family: {family_id}

## Authorized Scope

{args.scope or "Use the current engagement brief and do not expand target scope."}

## Target Slice

{args.target}

## Objective

Audit the target for the `{family_id}` vulnerability family: {focus}.

## Search Seeds

{seeds}

## Non-Goals

- Do not broaden into unrelated vulnerability families unless a concrete cross-family chain emerges.
- Do not add tracker findings without duplicate search evidence.
- Do not perform proofing or patching unless the parent assigns that follow-up.

## Write Ownership

read-only

## Tracker Discipline

Search `data/findings.json` before proposing a new finding. Return likely duplicate IDs, related IDs, and any de-escalated leads that matter.

## Evidence Standard

Cite exact files, symbols, routes, requests, commands, tests, crashes, or artifact paths. For each candidate, name entry point, attacker control, missing guard, impact, constraints, confidence, and proof gap.

## Stop Criteria

Return after mapping the relevant attack surface and producing at most {args.max_candidates} candidate findings for this family.

## Output Contract

Return:
- family ID and target slice;
- reviewed files/routes/components;
- candidate findings ordered by confidence and impact;
- likely duplicates or related tracked findings;
- refuted leads worth preserving;
- exact proof gaps and recommended next stage.
"""


def write_packet(root: Path, family_id: str, args: argparse.Namespace) -> Path:
    path = root / f"family-{family_id}.md"
    if path.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {path}; pass --force")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(packet_text(args, family_id), encoding="utf-8")
    return path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Create one subagent assignment packet per vulnerability family."
    )
    parser.add_argument("--list-families", action="store_true")
    parser.add_argument("--all", action="store_true", help="create packets for all families")
    parser.add_argument("--family", action="append", type=normalize_family)
    parser.add_argument("--exclude", action="append", type=normalize_family)
    parser.add_argument("--target", help="target boundary for every family packet")
    parser.add_argument("--scope", help="authorized scope text for every family packet")
    parser.add_argument("--goal-id", type=validate_slug)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--output-dir")
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.list_families:
        for family_id, family in FAMILIES.items():
            print(f"{family_id}: {family['focus']}")
        return 0

    if not args.target:
        parser.error("--target is required unless --list-families is used")
    if args.max_candidates < 1:
        parser.error("--max-candidates must be at least 1")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    families = selected_families(args)
    root = output_root(args)
    paths = [write_packet(root, family_id, args) for family_id in families]
    for path in paths:
        print(path.as_posix())
    if len(paths) > args.batch_size:
        print(
            f"note: created {len(paths)} family packets; run subagents in batches of "
            f"{args.batch_size} or less.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
