#!/usr/bin/env python3
"""Workspace-local security finding tracker with duplicate checks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATES = {"discovered", "confident", "proofed", "de-escalated"}
ACTIVE_STATES = {"discovered", "confident", "proofed"}
DEFAULT_PATH = Path("data/findings.json")
SCHEMA_VERSION = "finding-tracker.v1"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def tokens(text: str) -> set[str]:
    return {
        tok
        for tok in re.findall(r"[a-z0-9_./:{}-]+", text.lower())
        if len(tok) > 1 and tok not in {"the", "and", "for", "with", "this", "that"}
    }


def norm(text: str | None) -> str:
    return (text or "").strip()


def unique(items: list[str] | None) -> list[str]:
    seen = set()
    out = []
    for item in items or []:
        value = norm(item)
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "updated_at": now(), "findings": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(f"unsupported schema_version in {path}: {data.get('schema_version')}")
    data.setdefault("findings", [])
    return data


def save(path: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def next_id(findings: list[dict[str, Any]]) -> str:
    max_num = 0
    for finding in findings:
        match = re.fullmatch(r"F-(\d{4})", finding.get("id", ""))
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"F-{max_num + 1:04d}"


def finding_text(finding: dict[str, Any]) -> str:
    parts = [
        finding.get("title", ""),
        finding.get("summary", ""),
        finding.get("category", ""),
        finding.get("target", ""),
        " ".join(finding.get("locations", [])),
        " ".join(finding.get("evidence", [])),
        " ".join(finding.get("related_ids", [])),
    ]
    return " ".join(str(part) for part in parts if part)


def score_candidate(query: dict[str, Any], finding: dict[str, Any]) -> float:
    query_text = " ".join(
        str(part)
        for part in [
            query.get("title", ""),
            query.get("summary", ""),
            query.get("category", ""),
            query.get("target", ""),
            " ".join(query.get("locations", [])),
            " ".join(query.get("evidence", [])),
            " ".join(query.get("related_ids", [])),
        ]
        if part
    )
    qt = tokens(query_text)
    ft = tokens(finding_text(finding))
    score = 0.0
    if qt and ft:
        score += 0.55 * (len(qt & ft) / len(qt | ft))
    if norm(query.get("target")).lower() and norm(query.get("target")).lower() == norm(finding.get("target")).lower():
        score += 0.18
    if norm(query.get("category")).lower() and norm(query.get("category")).lower() == norm(finding.get("category")).lower():
        score += 0.12
    qloc = {loc.lower() for loc in query.get("locations", [])}
    floc = {loc.lower() for loc in finding.get("locations", [])}
    if qloc and floc:
        if qloc & floc:
            score += 0.30
        elif any(a in b or b in a for a in qloc for b in floc):
            score += 0.18
    qtitle = tokens(query.get("title", ""))
    ftitle = tokens(finding.get("title", ""))
    if qtitle and ftitle:
        score += 0.20 * (len(qtitle & ftitle) / len(qtitle | ftitle))
    return min(score, 1.0)


def find_by_id(data: dict[str, Any], finding_id: str) -> dict[str, Any]:
    for finding in data["findings"]:
        if finding.get("id") == finding_id:
            return finding
    raise SystemExit(f"finding not found: {finding_id}")


def add_milestone(finding: dict[str, Any], note: str, evidence: list[str] | None = None) -> None:
    finding.setdefault("milestones", []).append(
        {
            "at": now(),
            "state": finding.get("state"),
            "note": note,
            "evidence": evidence or [],
        }
    )
    if evidence:
        finding.setdefault("evidence", [])
        for item in evidence:
            if item not in finding["evidence"]:
                finding["evidence"].append(item)
    finding["updated_at"] = now()


def state_change(
    finding: dict[str, Any],
    new_state: str,
    note: str,
    proof_ref: str | None = None,
    evidence: list[str] | None = None,
) -> None:
    old_state = finding.get("state")
    finding["state"] = new_state
    finding["updated_at"] = now()
    if proof_ref:
        finding["proof_ref"] = proof_ref
    finding.setdefault("state_history", []).append(
        {"at": now(), "from": old_state, "to": new_state, "note": note, "proof_ref": proof_ref}
    )
    add_milestone(finding, note or f"State changed from {old_state} to {new_state}", evidence)


def print_finding(finding: dict[str, Any]) -> None:
    print(f"{finding['id']} [{finding['state']}] {finding['title']}")
    print(f"  target: {finding.get('target') or '-'}")
    print(f"  category: {finding.get('category') or '-'}")
    if finding.get("locations"):
        print(f"  locations: {', '.join(finding['locations'])}")
    if finding.get("related_ids"):
        print(f"  related: {', '.join(finding['related_ids'])}")
    if finding.get("summary"):
        print(f"  summary: {finding['summary']}")
    if finding.get("duplicate_of"):
        print(f"  duplicate_of: {finding['duplicate_of']}")
    if finding.get("proof_ref"):
        print(f"  proof_ref: {finding['proof_ref']}")
    if finding.get("milestones"):
        latest = finding["milestones"][-1]
        print(f"  latest: {latest.get('at')} {latest.get('note')}")


def cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.file)
    data = load(path)
    save(path, data)
    print(f"initialized {path}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    data = load(Path(args.file))
    counts = {state: 0 for state in sorted(STATES)}
    for finding in data["findings"]:
        counts[finding.get("state", "unknown")] = counts.get(finding.get("state", "unknown"), 0) + 1
    print(f"Findings: {len(data['findings'])} total")
    for state in ("discovered", "confident", "proofed", "de-escalated"):
        print(f"- {state}: {counts.get(state, 0)}")
    active = [f for f in data["findings"] if f.get("state") in ACTIVE_STATES]
    if active:
        print("\nActive:")
        for finding in active[-10:]:
            print(f"- {finding['id']} {finding['state']}: {finding['title']}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    data = load(Path(args.file))
    selected = data["findings"]
    if args.state == "active":
        selected = [f for f in selected if f.get("state") in ACTIVE_STATES]
    elif args.state != "all":
        selected = [f for f in selected if f.get("state") == args.state]
    if args.json:
        print(json.dumps(selected, indent=2, sort_keys=True))
    else:
        for finding in selected:
            print_finding(finding)
    return 0


def query_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "title": norm(args.title),
        "summary": norm(args.summary),
        "target": norm(args.target),
        "category": norm(args.category),
        "locations": args.location or [],
        "evidence": args.evidence or [],
        "related_ids": unique(getattr(args, "related", None)),
    }


def duplicate_candidates(data: dict[str, Any], query: dict[str, Any], threshold: float) -> list[tuple[float, dict[str, Any]]]:
    scored = [(score_candidate(query, finding), finding) for finding in data["findings"]]
    return sorted(
        [(score, finding) for score, finding in scored if score >= threshold],
        key=lambda item: item[0],
        reverse=True,
    )


def cmd_search(args: argparse.Namespace) -> int:
    data = load(Path(args.file))
    query = query_from_args(args)
    matches = duplicate_candidates(data, query, args.threshold)
    if args.json:
        print(json.dumps([{"score": score, "finding": finding} for score, finding in matches], indent=2, sort_keys=True))
    else:
        if not matches:
            print("No likely duplicates found.")
        for score, finding in matches:
            print(f"score={score:.2f}")
            print_finding(finding)
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    data = load(Path(args.file))
    query = query_from_args(args)
    matches = duplicate_candidates(data, query, args.threshold)
    if matches and not args.allow_duplicate and not args.duplicate_of:
        print("Likely duplicate finding(s) found; update an existing finding or pass --allow-duplicate/--duplicate-of.", file=sys.stderr)
        for score, finding in matches[:5]:
            print(f"score={score:.2f} {finding['id']} [{finding['state']}] {finding['title']}", file=sys.stderr)
        return 3

    finding_id = next_id(data["findings"])
    ts = now()
    finding = {
        "id": finding_id,
        "state": "discovered",
        "title": query["title"],
        "summary": query["summary"],
        "target": query["target"],
        "category": query["category"],
        "locations": query["locations"],
        "evidence": query["evidence"],
        "related_ids": query["related_ids"],
        "severity": norm(args.severity),
        "confidence": norm(args.confidence),
        "duplicate_of": args.duplicate_of,
        "created_at": ts,
        "updated_at": ts,
        "state_history": [{"at": ts, "from": None, "to": "discovered", "note": args.note or "Finding discovered."}],
        "milestones": [
            {
                "at": ts,
                "state": "discovered",
                "note": args.note or "Finding discovered.",
                "evidence": query["evidence"],
            }
        ],
    }
    data["findings"].append(finding)
    save(Path(args.file), data)
    print_finding(finding)
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    data = load(Path(args.file))
    finding = find_by_id(data, args.id)
    if args.state:
        if args.state not in STATES:
            raise SystemExit(f"invalid state: {args.state}")
        if args.state == "proofed" and not args.proof_ref:
            raise SystemExit("--proof-ref is required when setting state to proofed")
        state_change(
            finding,
            args.state,
            args.note or f"State updated to {args.state}.",
            args.proof_ref,
            args.evidence,
        )
    elif args.note or args.evidence:
        add_milestone(finding, args.note or "Milestone added.", args.evidence)
    if args.title:
        finding["title"] = args.title
    if args.summary:
        finding["summary"] = args.summary
    if args.target:
        finding["target"] = args.target
    if args.category:
        finding["category"] = args.category
    if args.location:
        existing = finding.setdefault("locations", [])
        for loc in args.location:
            if loc not in existing:
                existing.append(loc)
    if args.related:
        existing = finding.setdefault("related_ids", [])
        for related_id in unique(args.related):
            if related_id not in existing:
                existing.append(related_id)
    if args.severity is not None:
        finding["severity"] = args.severity
    if args.confidence is not None:
        finding["confidence"] = args.confidence
    finding["updated_at"] = now()
    save(Path(args.file), data)
    print_finding(finding)
    return 0


def cmd_milestone(args: argparse.Namespace) -> int:
    data = load(Path(args.file))
    finding = find_by_id(data, args.id)
    add_milestone(finding, args.note, args.evidence)
    save(Path(args.file), data)
    print_finding(finding)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    data = load(Path(args.file))
    finding = find_by_id(data, args.id)
    if args.json:
        print(json.dumps(finding, indent=2, sort_keys=True))
    else:
        print_finding(finding)
        if finding.get("milestones"):
            print("  milestones:")
            for item in finding["milestones"]:
                print(f"  - {item.get('at')} [{item.get('state')}] {item.get('note')}")
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--file", default=str(DEFAULT_PATH), help="tracker JSON path")


def add_query_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--title", default="", help="finding title")
    parser.add_argument("--summary", default="", help="finding summary")
    parser.add_argument("--target", default="", help="target asset/component")
    parser.add_argument("--category", default="", help="finding category")
    parser.add_argument("--location", action="append", help="affected location/surface")
    parser.add_argument("--evidence", action="append", help="short evidence reference")
    parser.add_argument("--related", action="append", help="related finding ID")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Track security findings in a workspace-local JSON file.")
    add_common(parser)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="create tracker if missing")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("summary", help="print finding counts and active items")
    p.set_defaults(func=cmd_summary)

    p = sub.add_parser("list", help="list findings")
    p.add_argument("--state", default="active", choices=["all", "active", *sorted(STATES)])
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("search", help="search likely duplicates")
    add_query_args(p)
    p.add_argument("--threshold", type=float, default=0.45)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("add", help="add a discovered finding after duplicate check")
    add_query_args(p)
    p.add_argument("--severity", default="")
    p.add_argument("--confidence", default="")
    p.add_argument("--note", default="")
    p.add_argument("--threshold", type=float, default=0.45)
    p.add_argument("--allow-duplicate", action="store_true")
    p.add_argument("--duplicate-of")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("update", help="update finding metadata or state")
    p.add_argument("id")
    p.add_argument("--state", choices=sorted(STATES))
    p.add_argument("--note", default="")
    p.add_argument("--proof-ref")
    p.add_argument("--title")
    p.add_argument("--summary")
    p.add_argument("--target")
    p.add_argument("--category")
    p.add_argument("--location", action="append")
    p.add_argument("--evidence", action="append")
    p.add_argument("--related", action="append")
    p.add_argument("--severity")
    p.add_argument("--confidence")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("milestone", help="add a milestone note")
    p.add_argument("id")
    p.add_argument("--note", required=True)
    p.add_argument("--evidence", action="append")
    p.set_defaults(func=cmd_milestone)

    p = sub.add_parser("show", help="show one finding")
    p.add_argument("id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_show)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
