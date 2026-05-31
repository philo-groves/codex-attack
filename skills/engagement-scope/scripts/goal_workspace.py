#!/usr/bin/env python3
"""Create a per-goal workspace tree for Codex ATTACK goal runs."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


GOAL_SUBDIRS = ("recon", "modeling", "proofing", "reports")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def validate_goal_id(value: str) -> str:
    goal_id = value.strip().lower()
    if not SLUG_RE.fullmatch(goal_id):
        raise argparse.ArgumentTypeError(
            "goal ID must be a lower-case slug like pragma-elevation"
        )
    return goal_id


def bullet(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def brief_text(args: argparse.Namespace, root: Path) -> str:
    return f"""# Goal: {args.goal_id}

Created: {now()}
Artifact root: {root.as_posix()}

## Objective

{args.objective}

## Target Boundary

{args.target}

## Completion Condition

{args.completion}

## Non-Goals

{bullet(args.non_goal or [])}

## Notes

{args.notes or "none"}
"""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Create goal/<goal-id>/{recon,modeling,proofing,reports}."
    )
    parser.add_argument("--goal-id", required=True, type=validate_goal_id)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--completion", required=True)
    parser.add_argument("--non-goal", action="append")
    parser.add_argument("--notes", default="")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--force", action="store_true", help="overwrite brief.md")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser()
    root = workspace / "goal" / args.goal_id
    root.mkdir(parents=True, exist_ok=True)
    for name in GOAL_SUBDIRS:
        (root / name).mkdir(exist_ok=True)

    brief_path = root / "brief.md"
    if brief_path.exists() and not args.force:
        print(f"error: refusing to overwrite {brief_path}; pass --force", file=sys.stderr)
        return 2
    brief_path.write_text(brief_text(args, root), encoding="utf-8")

    print(root.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
