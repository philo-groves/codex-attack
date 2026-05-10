#!/usr/bin/env python3
"""Render a small HTML session viewer for security research state."""

from __future__ import annotations

import argparse
import http.server
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


SCHEMA_VERSION = "session-viewer.v1"
DEFAULT_STATE_PATH = Path("data/session-viewer.json")
DEFAULT_HTML_PATH = Path("data/session-viewer.html")
STATES = ["discovered", "confident", "proofed", "de-escalated"]
ACTIVE_STATES = {"discovered", "confident", "proofed"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def unique(items: list[str] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items or []:
        value = (item or "").strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def split_values(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return unique(result)


def empty_state(title: str = "Security research session", target: str = "") -> dict[str, Any]:
    timestamp = now()
    return {
        "schema_version": SCHEMA_VERSION,
        "title": title,
        "target": target,
        "created_at": timestamp,
        "updated_at": timestamp,
        "refresh_seconds": 5,
        "cards": {},
        "events": [],
    }


def load_state(path: Path, title: str | None = None, target: str | None = None) -> dict[str, Any]:
    if not path.exists():
        return empty_state(title or "Security research session", target or "")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(f"unsupported schema_version in {path}: {data.get('schema_version')}")
    data.setdefault("cards", {})
    data.setdefault("events", [])
    data.setdefault("refresh_seconds", 5)
    if title:
        data["title"] = title
    if target:
        data["target"] = target
    return data


def save_state(path: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def classify_transition(old_state: str | None, new_state: str | None) -> str:
    if new_state == "de-escalated":
        return "de-escalation"
    if old_state in {"discovered", "confident"} and new_state in {"confident", "proofed"}:
        return "escalation"
    if new_state == "proofed":
        return "proof"
    if old_state and new_state and old_state != new_state:
        return "transition"
    return "milestone"


def latest_note(finding: dict[str, Any]) -> str:
    history = finding.get("state_history") or []
    if history:
        note = history[-1].get("note")
        if note:
            return str(note)
    milestones = finding.get("milestones") or []
    if milestones:
        note = milestones[-1].get("note")
        if note:
            return str(note)
    return str(finding.get("summary") or "")


def card_from_finding(finding: dict[str, Any]) -> dict[str, Any]:
    finding_id = str(finding.get("id") or "").strip()
    return {
        "id": finding_id,
        "title": str(finding.get("title") or finding_id or "Untitled finding"),
        "target": str(finding.get("target") or ""),
        "category": str(finding.get("category") or ""),
        "state": str(finding.get("state") or "discovered"),
        "summary": str(finding.get("summary") or ""),
        "locations": unique([str(item) for item in finding.get("locations", [])]),
        "evidence": unique([str(item) for item in finding.get("evidence", [])]),
        "related_ids": unique([str(item) for item in finding.get("related_ids", [])]),
        "proof_ref": str(finding.get("proof_ref") or ""),
        "updated_at": str(finding.get("updated_at") or now()),
        "next_action": str(finding.get("next_action") or ""),
    }


def add_event(
    data: dict[str, Any],
    *,
    kind: str,
    title: str,
    subject: str = "",
    summary: str = "",
    from_state: str = "",
    to_state: str = "",
    evidence: list[str] | None = None,
    next_action: str = "",
) -> None:
    data["events"].append(
        {
            "at": now(),
            "kind": kind,
            "subject": subject,
            "title": title,
            "summary": summary,
            "from_state": from_state,
            "to_state": to_state,
            "evidence": unique(evidence),
            "next_action": next_action,
        }
    )


def load_findings(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"findings file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    findings = data.get("findings")
    if not isinstance(findings, list):
        raise SystemExit(f"findings file has no findings list: {path}")
    return findings


def summarize_counts(cards: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {state: 0 for state in STATES}
    counts["other"] = 0
    for card in cards.values():
        state = card.get("state")
        if state in counts:
            counts[state] += 1
        else:
            counts["other"] += 1
    counts["active"] = sum(counts[state] for state in ACTIVE_STATES)
    counts["total"] = len(cards)
    return counts


def js_safe_json(data: dict[str, Any]) -> str:
    return (
        json.dumps(data, indent=2, sort_keys=True)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def browser_relative_url(target_path: Path, from_file: Path) -> str:
    relative_path = Path(os.path.relpath(target_path.resolve(), from_file.resolve().parent))
    return "/".join(quote(part) for part in relative_path.parts)


def render_html(data: dict[str, Any], html_path: Path, state_path: Path | None = None) -> None:
    payload = js_safe_json(data)
    config = js_safe_json({"stateUrl": browser_relative_url(state_path, html_path) if state_path else ""})
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Session Viewer</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f7f4;
      --panel: #ffffff;
      --ink: #1f2933;
      --muted: #667085;
      --line: #d8ddd7;
      --accent: #b91c1c;
      --blue: #2563eb;
      --green: #16803c;
      --amber: #b45309;
      --gray: #64748b;
      --shadow: 0 14px 35px rgba(31, 41, 51, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .wrap {{ max-width: 1320px; margin: 0 auto; padding: 22px; }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: end;
      padding: 10px 0 20px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0; font-size: 26px; line-height: 1.15; letter-spacing: 0; }}
    .target {{ color: var(--muted); margin-top: 6px; }}
    .updated {{ color: var(--muted); text-align: right; font-size: 12px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 10px;
      margin: 18px 0;
    }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      box-shadow: var(--shadow);
    }}
    .metric b {{ display: block; font-size: 24px; line-height: 1; margin-bottom: 5px; }}
    .metric span {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
    .toolbar {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }}
    button {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 7px;
      padding: 7px 10px;
      cursor: pointer;
      font: inherit;
    }}
    button.active {{ background: var(--ink); color: #fff; border-color: var(--ink); }}
    main {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 18px;
      align-items: start;
    }}
    .board {{
      display: grid;
      grid-template-columns: repeat(4, minmax(190px, 1fr));
      gap: 12px;
    }}
    .lane {{
      background: rgba(255, 255, 255, 0.58);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-height: 180px;
      padding: 10px;
    }}
    .lane h2 {{
      margin: 0 0 10px;
      font-size: 13px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      letter-spacing: 0;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-left: 4px solid var(--gray);
      border-radius: 8px;
      padding: 10px;
      margin-bottom: 9px;
      box-shadow: 0 8px 18px rgba(31, 41, 51, 0.06);
    }}
    .card.confident {{ border-left-color: var(--blue); }}
    .card.proofed {{ border-left-color: var(--green); }}
    .card.de-escalated {{ border-left-color: var(--gray); opacity: 0.82; }}
    .card h3 {{ margin: 0 0 6px; font-size: 14px; line-height: 1.25; letter-spacing: 0; }}
    .meta {{ color: var(--muted); font-size: 12px; margin-bottom: 7px; overflow-wrap: anywhere; }}
    .summary {{ margin: 0 0 8px; overflow-wrap: anywhere; }}
    .chips {{ display: flex; gap: 5px; flex-wrap: wrap; }}
    .chip {{
      display: inline-flex;
      max-width: 100%;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 7px;
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    aside {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 12px;
      max-height: calc(100vh - 42px);
      overflow: auto;
      position: sticky;
      top: 22px;
    }}
    aside h2 {{ margin: 0 0 12px; font-size: 16px; letter-spacing: 0; }}
    .event {{
      border-left: 3px solid var(--gray);
      padding: 0 0 14px 11px;
      margin-left: 4px;
    }}
    .event.escalation {{ border-left-color: var(--blue); }}
    .event.proof {{ border-left-color: var(--green); }}
    .event.de-escalation {{ border-left-color: var(--amber); }}
    .event h3 {{ margin: 0 0 4px; font-size: 13px; letter-spacing: 0; }}
    .event p {{ margin: 0 0 5px; color: var(--muted); overflow-wrap: anywhere; }}
    .empty {{ color: var(--muted); padding: 14px; text-align: center; }}
    @media (max-width: 1050px) {{
      main {{ grid-template-columns: 1fr; }}
      aside {{ position: static; max-height: none; }}
      .board {{ grid-template-columns: repeat(2, minmax(190px, 1fr)); }}
      .metrics {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
    }}
    @media (max-width: 620px) {{
      .wrap {{ padding: 14px; }}
      header {{ grid-template-columns: 1fr; }}
      .updated {{ text-align: left; }}
      .board {{ grid-template-columns: 1fr; }}
      .metrics {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div>
        <h1 id="title"></h1>
        <div class="target" id="target"></div>
      </div>
      <div class="updated" id="updated"></div>
    </header>
    <section class="metrics" id="metrics"></section>
    <div class="toolbar" id="filters"></div>
    <main>
      <section class="board" id="board"></section>
      <aside>
        <h2>Transitions</h2>
        <div id="timeline"></div>
      </aside>
    </main>
  </div>
  <script id="session-data" type="application/json">{payload}</script>
  <script id="viewer-config" type="application/json">{config}</script>
  <script>
    let data = JSON.parse(document.getElementById('session-data').textContent);
    const config = JSON.parse(document.getElementById('viewer-config').textContent);
    const states = ['discovered', 'confident', 'proofed', 'de-escalated'];
    const labels = {{
      discovered: 'Discovered',
      confident: 'Confident',
      proofed: 'Proofed',
      'de-escalated': 'De-escalated'
    }};
    let filter = localStorage.getItem('session-viewer-filter') || 'all';
    let lastFingerprint = fingerprint(data);

    function text(value) {{
      return value == null || value === '' ? '-' : String(value);
    }}

    function escapeHTML(value) {{
      const chars = {{'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}};
      return text(value).replace(/[&<>"']/g, (char) => chars[char]);
    }}

    function countByState(cards) {{
      const counts = Object.fromEntries(states.map((state) => [state, 0]));
      cards.forEach((card) => {{
        if (counts[card.state] == null) counts[card.state] = 0;
        counts[card.state] += 1;
      }});
      return counts;
    }}

    function fingerprint(nextData) {{
      return JSON.stringify([
        nextData.title,
        nextData.target,
        nextData.updated_at,
        nextData.cards || {{}},
        nextData.events || []
      ]);
    }}

    function renderMetrics(cards) {{
      const counts = countByState(cards);
      const active = cards.filter((card) => card.state !== 'de-escalated').length;
      const metrics = [
        ['Active', active],
        ['Confident', counts.confident || 0],
        ['Proofed', counts.proofed || 0],
        ['De-escalated', counts['de-escalated'] || 0],
        ['Total', cards.length],
      ];
      document.getElementById('metrics').innerHTML = metrics.map(([label, value]) =>
        `<div class="metric"><b>${{value}}</b><span>${{label}}</span></div>`
      ).join('');
    }}

    function renderFilters() {{
      const filters = ['all', 'active', ...states];
      document.getElementById('filters').innerHTML = filters.map((item) =>
        `<button data-filter="${{item}}" class="${{filter === item ? 'active' : ''}}">${{item === 'all' ? 'All' : item === 'active' ? 'Active' : labels[item]}}</button>`
      ).join('');
      document.querySelectorAll('[data-filter]').forEach((button) => {{
        button.addEventListener('click', () => {{
          filter = button.dataset.filter;
          localStorage.setItem('session-viewer-filter', filter);
          render();
        }});
      }});
    }}

    function visibleCards(cards) {{
      if (filter === 'all') return cards;
      if (filter === 'active') return cards.filter((card) => card.state !== 'de-escalated');
      return cards.filter((card) => card.state === filter);
    }}

    function renderCard(card) {{
      const stateClass = states.includes(card.state) ? card.state : 'discovered';
      const bits = [card.id, card.category, card.target].filter(Boolean).join(' | ');
      const evidence = (card.evidence || []).slice(-2).map((item) => `<span class="chip">${{escapeHTML(item)}}</span>`).join('');
      const nextAction = card.next_action ? `<p class="summary"><strong>Next:</strong> ${{escapeHTML(card.next_action)}}</p>` : '';
      return `<article class="card ${{stateClass}}">
        <h3>${{escapeHTML(card.title || card.id)}}</h3>
        <div class="meta">${{escapeHTML(bits || labels[card.state] || card.state)}}</div>
        <p class="summary">${{escapeHTML(card.summary || 'No summary recorded.')}}</p>
        ${{nextAction}}
        <div class="chips">${{evidence}}</div>
      </article>`;
    }}

    function renderBoard(cards) {{
      const selected = visibleCards(cards);
      const board = document.getElementById('board');
      board.innerHTML = states.map((state) => {{
        const laneCards = selected.filter((card) => card.state === state);
        return `<section class="lane">
          <h2><span>${{labels[state]}}</span><span>${{laneCards.length}}</span></h2>
          ${{laneCards.length ? laneCards.map(renderCard).join('') : '<div class="empty">No cards</div>'}}
        </section>`;
      }}).join('');
    }}

    function renderTimeline(events) {{
      const timeline = document.getElementById('timeline');
      const selected = events.filter((event) => {{
        if (filter === 'all') return true;
        if (filter === 'active') return event.to_state !== 'de-escalated';
        return event.to_state === filter || event.kind === filter;
      }});
      timeline.innerHTML = selected.length ? selected.slice().reverse().map((event) => {{
        const eventClass = ['escalation', 'proof', 'de-escalation', 'blocked', 'milestone', 'transition', 'added'].includes(event.kind) ? event.kind : 'milestone';
        const transition = event.from_state || event.to_state ? `${{event.from_state || '?'}} -> ${{event.to_state || '?'}}` : event.kind;
        const when = new Date(event.at).toLocaleString();
        const evidence = (event.evidence || []).slice(-2).map((item) => `<span class="chip">${{escapeHTML(item)}}</span>`).join('');
        return `<section class="event ${{eventClass}}">
          <h3>${{escapeHTML(event.title)}}</h3>
          <p>${{escapeHTML(when + ' | ' + transition)}}</p>
          <p>${{escapeHTML(event.summary || '')}}</p>
          <div class="chips">${{evidence}}</div>
        </section>`;
      }}).join('') : '<div class="empty">No transitions</div>';
    }}

    function render() {{
      const cards = Object.values(data.cards || {{}}).sort((a, b) => String(a.id).localeCompare(String(b.id)));
      document.getElementById('title').textContent = data.title || 'Security research session';
      document.getElementById('target').textContent = data.target || 'No target label';
      document.getElementById('updated').textContent = `Updated ${{new Date(data.updated_at).toLocaleString()}}`;
      renderMetrics(cards);
      renderFilters();
      renderBoard(cards);
      renderTimeline(data.events || []);
    }}

    async function pollState() {{
      if (!config.stateUrl) return;
      try {{
        const separator = config.stateUrl.includes('?') ? '&' : '?';
        const response = await fetch(`${{config.stateUrl}}${{separator}}t=${{Date.now()}}`, {{ cache: 'no-store' }});
        if (!response.ok) return;
        const nextData = await response.json();
        if (nextData.schema_version !== data.schema_version) return;
        const nextFingerprint = fingerprint(nextData);
        if (nextFingerprint === lastFingerprint) return;
        data = nextData;
        lastFingerprint = nextFingerprint;
        render();
      }} catch (_error) {{
      }}
    }}

    render();
    const refreshSeconds = Number(data.refresh_seconds || 5);
    if (refreshSeconds > 0) {{
      setInterval(pollState, refreshSeconds * 1000);
    }}
  </script>
</body>
</html>
"""
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")


def viewer_url(host: str, port: int, html_path: Path, directory: Path) -> str:
    try:
        relative_path = html_path.resolve().relative_to(directory.resolve())
    except ValueError as exc:
        raise SystemExit(f"html file must be inside served directory: {html_path} not under {directory}") from exc
    encoded = "/".join(quote(part) for part in relative_path.parts)
    return f"http://{host}:{port}/{encoded}"


def serve_viewer(args: argparse.Namespace, html_path: Path) -> None:
    directory = Path(args.directory or html_path.parent).resolve()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *handler_args: Any, **handler_kwargs: Any) -> None:
            super().__init__(*handler_args, directory=str(directory), **handler_kwargs)

        def log_message(self, format: str, *message_args: Any) -> None:
            if not args.quiet:
                super().log_message(format, *message_args)

    server = http.server.ThreadingHTTPServer((args.host, args.port), Handler)
    port = int(server.server_address[1])
    url = viewer_url(args.host, port, html_path, directory)
    print(f"session viewer url: {url}", flush=True)
    print("open this URL in the in-agent browser; keep this command running while monitoring", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def cmd_init(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    html_path = Path(args.html_file)
    data = load_state(state_path, args.title, args.target)
    save_state(state_path, data)
    render_html(data, html_path, state_path)
    print(f"session viewer: {html_path}")
    return 0


def cmd_sync_findings(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    html_path = Path(args.html_file)
    data = load_state(state_path, args.title, args.target)
    findings = load_findings(Path(args.findings))
    changed = 0
    added = 0
    for finding in findings:
        card = card_from_finding(finding)
        if not card["id"]:
            continue
        previous = data["cards"].get(card["id"])
        data["cards"][card["id"]] = card
        if previous is None:
            added += 1
            if args.record_new:
                add_event(
                    data,
                    kind="added",
                    title=f"{card['id']}: {card['title']}",
                    subject=card["id"],
                    summary=card["summary"],
                    to_state=card["state"],
                    evidence=card["evidence"],
                    next_action=card.get("next_action", ""),
                )
            continue
        old_state = previous.get("state")
        new_state = card.get("state")
        if old_state != new_state:
            changed += 1
            add_event(
                data,
                kind=classify_transition(old_state, new_state),
                title=f"{card['id']}: {card['title']}",
                subject=card["id"],
                summary=latest_note(finding),
                from_state=str(old_state or ""),
                to_state=str(new_state or ""),
                evidence=card["evidence"],
                next_action=card.get("next_action", ""),
            )
    save_state(state_path, data)
    render_html(data, html_path, state_path)
    print(f"session viewer: {html_path}")
    print(f"synced {len(findings)} findings ({added} new, {changed} state changes)")
    return 0


def cmd_event(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    html_path = Path(args.html_file)
    data = load_state(state_path, args.viewer_title, args.viewer_target)
    subject = (args.subject or "").strip()
    evidence = split_values(args.evidence)
    if subject:
        existing = data["cards"].get(subject, {})
        state = args.to_state or args.card_state or existing.get("state") or "discovered"
        data["cards"][subject] = {
            "id": subject,
            "title": args.title_text or existing.get("title") or subject,
            "target": args.card_target or existing.get("target", ""),
            "category": args.category or existing.get("category", ""),
            "state": state,
            "summary": args.summary or existing.get("summary", ""),
            "locations": unique(existing.get("locations", []) + split_values(args.location)),
            "evidence": unique(existing.get("evidence", []) + evidence),
            "related_ids": unique(existing.get("related_ids", []) + split_values(args.related)),
            "proof_ref": args.proof_ref or existing.get("proof_ref", ""),
            "updated_at": now(),
            "next_action": args.next_action or existing.get("next_action", ""),
        }
    add_event(
        data,
        kind=args.kind,
        title=args.title_text or subject or args.kind,
        subject=subject,
        summary=args.summary,
        from_state=args.from_state,
        to_state=args.to_state or args.card_state,
        evidence=evidence,
        next_action=args.next_action,
    )
    save_state(state_path, data)
    render_html(data, html_path, state_path)
    print(f"session viewer: {html_path}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    data = load_state(state_path, args.title, args.target)
    render_html(data, Path(args.html_file), state_path)
    print(f"session viewer: {args.html_file}")
    return 0


def cmd_launch(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    html_path = Path(args.html_file)
    data = load_state(state_path, args.title, args.target)
    save_state(state_path, data)
    render_html(data, html_path, state_path)
    serve_viewer(args, html_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain a standalone HTML session viewer.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_file_args(target_parser: argparse.ArgumentParser) -> None:
        target_parser.add_argument("--state-file", default=str(DEFAULT_STATE_PATH), help="Path to session viewer JSON state")
        target_parser.add_argument("--html-file", default=str(DEFAULT_HTML_PATH), help="Path to rendered HTML viewer")

    def add_view_args(target_parser: argparse.ArgumentParser) -> None:
        add_file_args(target_parser)
        target_parser.add_argument("--title", help="Viewer title")
        target_parser.add_argument("--target", help="Target label")

    init_parser = subparsers.add_parser("init", help="Initialize or re-render an empty viewer")
    add_view_args(init_parser)
    init_parser.set_defaults(func=cmd_init)

    sync_parser = subparsers.add_parser("sync-findings", help="Sync cards and transitions from finding-tracker JSON")
    add_view_args(sync_parser)
    sync_parser.add_argument("--findings", default="data/findings.json", help="Path to finding-tracker JSON")
    sync_parser.add_argument("--record-new", action="store_true", help="Add timeline events for first-seen findings")
    sync_parser.set_defaults(func=cmd_sync_findings)

    event_parser = subparsers.add_parser("event", help="Record a manual event and optionally update one card")
    add_file_args(event_parser)
    event_parser.add_argument("--kind", choices=["escalation", "de-escalation", "proof", "blocked", "milestone", "transition", "added"], required=True)
    event_parser.add_argument("--subject", help="Finding, chain, proof, or lead ID")
    event_parser.add_argument("--title", dest="title_text", help="Event or card title")
    event_parser.add_argument("--viewer-title", default="", help="Optional viewer title update")
    event_parser.add_argument("--viewer-target", default="", help="Optional viewer target update")
    event_parser.add_argument("--summary", default="", help="Short event summary")
    event_parser.add_argument("--from-state", default="", help="Previous state")
    event_parser.add_argument("--to-state", default="", help="New state")
    event_parser.add_argument("--card-state", default="", help="Card state when no transition state applies")
    event_parser.add_argument("--card-target", default="", help="Card target label")
    event_parser.add_argument("--category", default="", help="Card category")
    event_parser.add_argument("--location", action="append", default=[], help="Location or comma-separated locations")
    event_parser.add_argument("--evidence", action="append", default=[], help="Evidence reference or comma-separated references")
    event_parser.add_argument("--related", action="append", default=[], help="Related ID or comma-separated IDs")
    event_parser.add_argument("--proof-ref", default="", help="Proof packet or verifier reference")
    event_parser.add_argument("--next-action", default="", help="Next action shown on the card")
    event_parser.set_defaults(func=cmd_event)

    render_parser = subparsers.add_parser("render", help="Render HTML from existing viewer state")
    add_view_args(render_parser)
    render_parser.set_defaults(func=cmd_render)

    launch_parser = subparsers.add_parser("launch", help="Render and serve the viewer for the in-agent browser")
    add_view_args(launch_parser)
    launch_parser.add_argument("--host", default="127.0.0.1", help="Local bind host")
    launch_parser.add_argument("--port", type=int, default=0, help="Local bind port; 0 chooses an available port")
    launch_parser.add_argument("--directory", default="", help="Directory to serve; defaults to the HTML file directory")
    launch_parser.add_argument("--quiet", action="store_true", help="Suppress request logs")
    launch_parser.set_defaults(func=cmd_launch)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
