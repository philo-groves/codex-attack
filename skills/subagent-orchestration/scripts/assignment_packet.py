#!/usr/bin/env python3
"""Create a durable subagent assignment packet."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STAGES = {
    "prepare",
    "scan",
    "validate-debate",
    "dedup",
    "prove",
    "report-patch",
}
ROLES = {"mapper", "auditor", "debater", "deduper", "prover", "patcher", "reporter"}
AGENT_TYPES = {"explorer", "worker", "default"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "assignment"


def validate_slug(value: str) -> str:
    slug = value.strip().lower()
    if not SLUG_RE.fullmatch(slug):
        raise argparse.ArgumentTypeError("expected a lower-case slug")
    return slug


def bullet(items: list[str] | None) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def packet_text(args: argparse.Namespace) -> str:
    return f"""# Subagent Assignment: {args.title}

Created: {now()}
Assignment ID: {args.assignment_id}
Goal ID: {args.goal_id or "none"}
Role: {args.role}
Agent type: {args.agent_type}
Stage: {args.stage}

## Authorized Scope

{args.scope or "Use the current engagement brief and do not expand target scope."}

## Target Slice

{args.target}

## Objective

{args.objective}

## Non-Goals

{bullet(args.non_goal)}

## Write Ownership

{args.write_scope}

## Tracker Discipline

{args.tracker}

## Evidence Standard

{args.evidence or "Cite exact files, symbols, requests, commands, crashes, or artifact paths."}

## Stop Criteria

{args.stop}

## Output Contract

{args.output}
"""


def output_path(args: argparse.Namespace) -> Path:
    if args.output_path:
        return Path(args.output_path).expanduser()
    filename = f"{args.assignment_id}.md"
    workspace = Path(args.workspace).expanduser()
    if args.goal_id:
        return workspace / "goal" / args.goal_id / "modeling" / "subagents" / filename
    return workspace / "data" / "subagents" / filename


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create a subagent assignment packet.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--role", required=True, choices=sorted(ROLES))
    parser.add_argument("--agent-type", required=True, choices=sorted(AGENT_TYPES))
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    parser.add_argument("--target", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--stop", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tracker", default="Search data/findings.json before proposing new findings.")
    parser.add_argument("--write-scope", default="read-only")
    parser.add_argument("--scope")
    parser.add_argument("--evidence")
    parser.add_argument("--non-goal", action="append")
    parser.add_argument("--goal-id", type=validate_slug)
    parser.add_argument("--assignment-id")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--output-path")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    args.assignment_id = validate_slug(args.assignment_id or slugify(args.title))
    path = output_path(args)
    if path.exists() and not args.force:
        print(f"error: refusing to overwrite {path}; pass --force", file=sys.stderr)
        return 2
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(packet_text(args), encoding="utf-8")
    print(path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
