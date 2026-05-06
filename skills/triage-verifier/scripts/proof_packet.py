#!/usr/bin/env python3
"""Create a concise triage proof packet for a confident finding."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED = [
    "finding_id",
    "title",
    "target",
    "claim",
    "reproduction",
    "expected",
    "actual",
    "impact",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "finding"


def validate(args: argparse.Namespace) -> list[str]:
    errors = []
    for field in REQUIRED:
        if not getattr(args, field):
            errors.append(f"--{field.replace('_', '-')} is required")
    if not args.evidence:
        errors.append("--evidence is required at least once")
    if not args.negative_control:
        errors.append("--negative-control is required at least once; use 'not feasible: <reason>' if truly unavailable")
    if not args.constraints:
        errors.append("--constraints is required")
    if args.outcome == "proofed" and not args.poc:
        errors.append("--poc is required for proofed packets unless the proof is non-executable and undeniable; provide a reference or explanation")
    return errors


def bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def packet_text(args: argparse.Namespace) -> str:
    poc = bullet(args.poc or ["not provided"])
    evidence = bullet(args.evidence)
    negative = bullet(args.negative_control)
    constraints = bullet(args.constraints)
    cleanup = bullet(args.cleanup or ["not applicable or not provided"])
    return f"""# Triage Proof Packet: {args.finding_id}

Generated: {now()}
Outcome: {args.outcome}

## Finding

- ID: {args.finding_id}
- Title: {args.title}
- Target: {args.target}

## Claim

{args.claim}

## Reproduction

{args.reproduction}

## Expected

{args.expected}

## Actual

{args.actual}

## Impact

{args.impact}

## Evidence

{evidence}

## Negative Controls

{negative}

## Preconditions And Constraints

{constraints}

## PoC References

{poc}

## Cleanup

{cleanup}

## Notes

{args.notes or "none"}
"""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create a triage proof packet.")
    parser.add_argument("--finding-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--claim", required=True)
    parser.add_argument("--reproduction", required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--actual", required=True)
    parser.add_argument("--impact", required=True)
    parser.add_argument("--evidence", action="append", required=True)
    parser.add_argument("--negative-control", action="append", required=True)
    parser.add_argument("--constraints", action="append", required=True)
    parser.add_argument("--poc", action="append")
    parser.add_argument("--cleanup", action="append")
    parser.add_argument("--notes", default="")
    parser.add_argument("--outcome", choices=["proofed", "needs-more-work", "de-escalated", "split-or-duplicate"], default="proofed")
    parser.add_argument("--output-dir", default="data/triage-verifier")
    parser.add_argument("--output")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    errors = validate(args)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2

    if args.output:
        output = Path(args.output)
    else:
        output = Path(args.output_dir) / f"{slug(args.finding_id)}-proof.md"
    if output.exists() and not args.force:
        print(f"error: refusing to overwrite {output}; pass --force", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(packet_text(args), encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
