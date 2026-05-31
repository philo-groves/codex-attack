#!/usr/bin/env python3
"""Context-continuity hooks for the Codex ATTACK plugin.

These hooks intentionally do not block prompts, deny tools, or force extra turns.
They only surface compact shared context and write lightweight checkpoint files.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_ACTIVE_FINDINGS = 8
MAX_RECENT_GOAL_FILES = 6
MAX_MESSAGE_CHARS = 5000


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def truncate(value: Any, max_chars: int = MAX_MESSAGE_CHARS) -> Any:
    if isinstance(value, str) and len(value) > max_chars:
        return value[:max_chars] + "..."
    return value


def read_event() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"_parse_error": "hook stdin was not valid JSON"}
    return payload if isinstance(payload, dict) else {}


def workspace_from(event: dict[str, Any]) -> Path:
    raw = event.get("cwd") or os.getcwd()
    return Path(str(raw)).expanduser()


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None
    return None


def short_path(path: Path, workspace: Path) -> str:
    try:
        return path.relative_to(workspace).as_posix()
    except ValueError:
        return path.as_posix()


def finding_sort_key(finding: dict[str, Any]) -> str:
    return str(finding.get("updated_at") or finding.get("created_at") or "")


def summarize_findings(workspace: Path) -> dict[str, Any]:
    path = workspace / "data" / "findings.json"
    data = load_json(path)
    if not data:
        return {
            "path": short_path(path, workspace),
            "exists": False,
            "counts": {},
            "active": [],
        }

    findings = data.get("findings") or []
    if not isinstance(findings, list):
        findings = []
    counts: dict[str, int] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        state = str(finding.get("state") or "unknown")
        counts[state] = counts.get(state, 0) + 1

    active_states = {"discovered", "confident", "proofed"}
    active_findings = [
        finding
        for finding in findings
        if isinstance(finding, dict) and finding.get("state") in active_states
    ]
    active_findings.sort(key=finding_sort_key, reverse=True)

    active = []
    for finding in active_findings[:MAX_ACTIVE_FINDINGS]:
        active.append(
            {
                "id": finding.get("id"),
                "state": finding.get("state"),
                "title": finding.get("title"),
                "target": finding.get("target"),
            }
        )

    return {
        "path": short_path(path, workspace),
        "exists": True,
        "updated_at": data.get("updated_at"),
        "counts": counts,
        "active": active,
    }


def summarize_scope(workspace: Path) -> dict[str, Any]:
    candidates = [
        workspace / "data" / "program.yaml",
        workspace / "data" / "program.yml",
        workspace / "data" / "program.json",
        workspace / "data" / "scope.yaml",
        workspace / "data" / "scope.yml",
        workspace / "data" / "scope.json",
    ]
    present = [path for path in candidates if path.is_file()]
    if not present:
        return {"exists": False, "paths": []}
    return {
        "exists": True,
        "paths": [short_path(path, workspace) for path in present[:4]],
    }


def summarize_goal_files(workspace: Path) -> dict[str, Any]:
    goal_dir = workspace / "goal"
    if not goal_dir.is_dir():
        return {"exists": False, "goals": [], "legacy_files": []}

    suffixes = {".md", ".txt", ".json", ".yaml", ".yml"}
    goal_roots = [
        path
        for path in goal_dir.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    ]
    goal_summaries = []
    for root in goal_roots:
        files = [
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in suffixes
        ]
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        latest = files[0].stat().st_mtime if files else root.stat().st_mtime
        goal_summaries.append(
            {
                "id": root.name,
                "path": short_path(root, workspace),
                "latest_mtime": latest,
                "recent_files": [
                    short_path(path, workspace)
                    for path in files[:MAX_RECENT_GOAL_FILES]
                ],
            }
        )

    legacy_files = [
        path
        for path in goal_dir.iterdir()
        if path.is_file() and path.suffix.lower() in suffixes
    ]
    legacy_files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    goal_summaries.sort(key=lambda item: item["latest_mtime"], reverse=True)

    return {
        "exists": True,
        "goals": goal_summaries[:4],
        "legacy_files": [
            short_path(path, workspace)
            for path in legacy_files[:MAX_RECENT_GOAL_FILES]
        ],
    }


def build_summary(workspace: Path) -> dict[str, Any]:
    findings = summarize_findings(workspace)
    scope = summarize_scope(workspace)
    goal = summarize_goal_files(workspace)
    return {
        "generated_at": utc_now(),
        "workspace": workspace.as_posix(),
        "scope": scope,
        "findings": findings,
        "goal": goal,
    }


def has_useful_context(summary: dict[str, Any]) -> bool:
    return bool(
        summary["findings"].get("exists")
        or summary["scope"].get("exists")
        or summary["goal"].get("exists")
    )


def summary_lines(summary: dict[str, Any], *, for_subagent: bool = False) -> list[str]:
    lines = ["Codex ATTACK shared context:"]
    findings = summary["findings"]
    scope = summary["scope"]
    goal = summary["goal"]

    if scope.get("exists"):
        lines.append(f"- Scope/program records: {', '.join(scope.get('paths', []))}")
    else:
        lines.append("- Scope/program records: none found in data/")

    if findings.get("exists"):
        counts = findings.get("counts", {})
        state_text = ", ".join(
            f"{state}={counts.get(state, 0)}"
            for state in ("discovered", "confident", "proofed", "de-escalated")
            if counts.get(state, 0)
        ) or "no findings"
        lines.append(f"- Finding tracker: {findings.get('path')} ({state_text})")
        active = findings.get("active") or []
        if active:
            lines.append("- Active findings:")
            for finding in active:
                lines.append(
                    "  - "
                    f"{finding.get('id')} {finding.get('state')}: "
                    f"{finding.get('title')}"
                )
    else:
        lines.append(f"- Finding tracker: not initialized ({findings.get('path')})")

    if goal.get("exists"):
        goals = goal.get("goals") or []
        if goals:
            lines.append("- Goal artifacts:")
            for item in goals:
                recent = item.get("recent_files") or []
                if recent:
                    lines.append(
                        f"  - {item.get('id')}: {', '.join(recent)}"
                    )
                else:
                    lines.append(f"  - {item.get('id')}: {item.get('path')}")
        else:
            lines.append(
                "- Goal directory exists but no per-goal subdirectories were found"
            )
        legacy_files = goal.get("legacy_files") or []
        if legacy_files:
            lines.append(
                "- Goal root files not under a goal ID: "
                f"{', '.join(legacy_files)}"
            )

    if for_subagent:
        lines.extend(
            [
                "- Before adding new security findings, search the tracker for duplicates.",
                "- Record meaningful evidence changes as milestones for handoff.",
                "- Keep proof references tied to triage-verifier output.",
            ]
        )

    return lines


def context_output(event_name: str, context: str) -> None:
    print(
        json.dumps(
            {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": event_name,
                    "additionalContext": context,
                },
            },
            separators=(",", ":"),
        )
    )


def data_dir(workspace: Path) -> Path:
    return workspace / "data" / ".codex-attack" / "hooks"


def compact_event(event: dict[str, Any]) -> dict[str, Any]:
    compact = dict(event)
    for key in ("prompt", "tool_input", "tool_response"):
        if key in compact:
            compact[key] = "<omitted>"
    compact["last_assistant_message"] = truncate(compact.get("last_assistant_message"))
    return compact


def write_checkpoint(
    action: str,
    event: dict[str, Any],
    workspace: Path,
    summary: dict[str, Any],
) -> None:
    if not has_useful_context(summary):
        return

    output_dir = data_dir(workspace)
    output_dir.mkdir(parents=True, exist_ok=True)
    turn = str(event.get("turn_id") or "session")
    timestamp = timestamp_slug()
    path = output_dir / f"{timestamp}-{action}-{turn}.json"
    record = {
        "action": action,
        "recorded_at": utc_now(),
        "hook_event": event.get("hook_event_name"),
        "event": compact_event(event),
        "summary": summary,
    }
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    latest = output_dir / "latest-summary.md"
    latest.write_text("\n".join(summary_lines(summary)) + "\n", encoding="utf-8")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def handle_session_start(event: dict[str, Any], workspace: Path) -> int:
    summary = build_summary(workspace)
    if not has_useful_context(summary):
        return 0
    context = "\n".join(summary_lines(summary))
    context_output("SessionStart", context)
    return 0


def handle_compact(action: str, event: dict[str, Any], workspace: Path) -> int:
    summary = build_summary(workspace)
    write_checkpoint(action, event, workspace, summary)
    return 0


def handle_subagent_start(event: dict[str, Any], workspace: Path) -> int:
    summary = build_summary(workspace)
    if not has_useful_context(summary):
        return 0
    lines = summary_lines(summary, for_subagent=True)
    agent_type = event.get("agent_type")
    if agent_type:
        lines.insert(1, f"- Subagent type: {agent_type}")
    context_output("SubagentStart", "\n".join(lines))
    return 0


def handle_subagent_stop(event: dict[str, Any], workspace: Path) -> int:
    summary = build_summary(workspace)
    if has_useful_context(summary):
        write_checkpoint("subagent-stop", event, workspace, summary)
        append_jsonl(
            data_dir(workspace) / "subagent-handoffs.jsonl",
            {
                "recorded_at": utc_now(),
                "agent_id": event.get("agent_id"),
                "agent_type": event.get("agent_type"),
                "turn_id": event.get("turn_id"),
                "agent_transcript_path": event.get("agent_transcript_path"),
                "last_assistant_message": truncate(event.get("last_assistant_message")),
            },
        )
    print(json.dumps({"continue": True}, separators=(",", ":")))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: codex_attack_context.py <hook-action>", file=sys.stderr)
        return 2

    action = argv[0]
    event = read_event()
    workspace = workspace_from(event)

    try:
        if action == "session-start":
            return handle_session_start(event, workspace)
        if action == "pre-compact":
            return handle_compact("pre-compact", event, workspace)
        if action == "post-compact":
            return handle_compact("post-compact", event, workspace)
        if action == "subagent-start":
            return handle_subagent_start(event, workspace)
        if action == "subagent-stop":
            return handle_subagent_stop(event, workspace)
    except Exception as exc:
        print(f"codex-attack hook warning: {exc}", file=sys.stderr)
        return 0

    print(f"unknown hook action: {action}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
