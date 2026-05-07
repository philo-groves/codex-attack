#!/usr/bin/env python3
"""Create a concise vulnerability report scaffold."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip())
    value = re.sub(r"-+", "-", value).strip("-")
    return value.lower() or "report"


def bullet(items: list[str] | None, default: str = "none") -> str:
    return "\n".join(f"- {item}" for item in (items or [default]))


def block(value: str | None, default: str = "TODO") -> str:
    return value.strip() if value and value.strip() else default


def validate(args: argparse.Namespace) -> list[str]:
    errors = []
    for field in ("title", "target", "summary", "impact"):
        if not getattr(args, field):
            errors.append(f"--{field.replace('_', '-')} is required")
    return errors


def report_text(args: argparse.Namespace) -> str:
    finding = args.finding_id or "pending"
    return f"""# {args.title}

Generated: {now()}
Finding ID: {finding}
Recipient format: {args.platform}
Submission readiness: {args.readiness}

## Summary

{block(args.summary)}

## Scope And Target

- Target: {args.target}
- Scope evidence: {block(args.scope, "TODO: cite program brief, asset, commit, build, or authorization evidence")}
- Affected version/build/package/endpoint: {block(args.affected, "TODO")}
- Attacker role/preconditions: {block(args.preconditions, "TODO")}

## Classification

- Weakness: {block(args.weakness, "TODO: CWE/VRT/category")}
- Severity: {block(args.severity, "TODO")}
- CVSS: {block(args.cvss, "not provided")}
- CVSS vector: {block(args.vector, "not provided")}
- CVE/GHSA/advisory ID: {block(args.advisory_id, "not assigned or not applicable")}

## Steps To Reproduce

{block(args.reproduction, "TODO: numbered deterministic steps, commands, requests, or UI actions")}

## Expected Behavior

{block(args.expected, "TODO")}

## Actual Behavior

{block(args.actual, "TODO")}

## Impact

{block(args.impact)}

## Evidence

- Proof reference: {block(args.proof_ref, "TODO")}
- Attachments:
{bullet(args.attachment)}
- Diagrams:
{bullet(args.diagram)}

## Severity Rationale

{block(args.severity_rationale, "TODO: connect program taxonomy/CVSS/VRT/context to proven impact")}

## Remediation

{block(args.remediation, "TODO: fix direction and regression tests")}

## Disclosure And Redaction Notes

{block(args.disclosure, "TODO: platform/channel/disclosure constraints and redactions")}

## Final Checklist

- [ ] Program scope and policy checked.
- [ ] Reproduction is deterministic and scoped.
- [ ] Impact is proven and not overstated.
- [ ] Expected and actual behavior are clear.
- [ ] Severity rationale names the taxonomy or score source.
- [ ] Secrets, cookies, tokens, PII, and customer data are redacted.
- [ ] Attachments are direct files or approved platform attachments.
- [ ] Mermaid diagrams render and match the proof.
- [ ] Remediation or regression-test guidance is included.
"""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create a vulnerability report Markdown scaffold.")
    parser.add_argument("--finding-id", default="")
    parser.add_argument("--title", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--platform", default="internal", choices=["hackerone", "bugcrowd", "github-advisory", "coordinated-disclosure", "internal"])
    parser.add_argument("--summary", required=True)
    parser.add_argument("--impact", required=True)
    parser.add_argument("--scope", default="")
    parser.add_argument("--affected", default="")
    parser.add_argument("--preconditions", default="")
    parser.add_argument("--weakness", default="")
    parser.add_argument("--severity", default="")
    parser.add_argument("--cvss", default="")
    parser.add_argument("--vector", default="")
    parser.add_argument("--advisory-id", default="")
    parser.add_argument("--reproduction", default="")
    parser.add_argument("--expected", default="")
    parser.add_argument("--actual", default="")
    parser.add_argument("--proof-ref", default="")
    parser.add_argument("--attachment", action="append")
    parser.add_argument("--diagram", action="append")
    parser.add_argument("--severity-rationale", default="")
    parser.add_argument("--remediation", default="")
    parser.add_argument("--disclosure", default="")
    parser.add_argument("--readiness", default="draft", choices=["draft", "ready", "needs-proof", "needs-redaction", "needs-program-fields"])
    parser.add_argument("--output-dir", default="data/reports")
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
        stem = slug(args.finding_id or args.title)
        output = Path(args.output_dir) / f"{stem}-report.md"
    if output.exists() and not args.force:
        print(f"error: refusing to overwrite {output}; pass --force", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report_text(args), encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
