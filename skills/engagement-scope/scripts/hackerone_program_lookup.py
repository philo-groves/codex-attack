#!/usr/bin/env python3
"""Look up a public HackerOne program through HackerOne's public GraphQL endpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import textwrap
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


GRAPHQL_URL = "https://hackerone.com/graphql"
CACHE_SCHEMA_VERSION = 1
DEFAULT_CACHE_TTL_SECONDS = 6 * 60 * 60

QUERY = """
query PublicProgramScope(
  $handle: String!
  $from: Int
  $size: Int
  $searchString: String
  $eligibleForSubmission: Boolean
  $eligibleForBounty: Boolean
) {
  team(handle: $handle) {
    id
    handle
    name
    state
    url
    offers_bounties
    offers_thanks
    submission_state
    external_url
    scope_description
    policy_setting {
      id
      policy
      last_policy_change_at
    }
    external_program {
      id
      policy_url
      policy
      disclosure_url
      offers_rewards
      thanks_url
    }
    declarative_policy {
      id
      has_open_scope
      protected_by_gold_standard_safe_harbor
      protected_by_ai_safe_harbor
      scope_exclusions {
        id
        category
        details
      }
    }
    structured_scopes_search(
      from: $from
      size: $size
      search_string: $searchString
      eligible_for_submission: $eligibleForSubmission
      eligible_for_bounty: $eligibleForBounty
    ) {
      total_count
      nodes {
        ... on StructuredScopeDocument {
          id
          identifier
          display_name
          instruction
          eligible_for_bounty
          eligible_for_submission
          cvss_score
          asset_type
          created_at
          updated_at
        }
      }
    }
  }
}
""".strip()


def normalize_handle(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise ValueError("program handle is empty")

    if "://" in raw:
        parsed = urllib.parse.urlparse(raw)
        host = parsed.netloc.lower()
        if not (host == "hackerone.com" or host.endswith(".hackerone.com")):
            raise ValueError(f"not a HackerOne URL: {value}")
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            raise ValueError(f"could not find a program handle in URL: {value}")
        raw = parts[0]

    raw = raw.strip().strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", raw):
        raise ValueError(
            "HackerOne handles should contain only letters, digits, underscores, or hyphens"
        )
    return raw


def default_cache_dir() -> Path:
    override = os.environ.get("SCOPE_CACHE_DIR")
    if override:
        return Path(override).expanduser()

    return Path.cwd() / "data" / ".cache" / "hackerone"


def parse_cache_ttl(value: str | None) -> int:
    if value is None or value == "":
        return DEFAULT_CACHE_TTL_SECONDS
    try:
        ttl = int(value)
    except ValueError as exc:
        raise ValueError("cache TTL must be an integer number of seconds") from exc
    if ttl < 0:
        raise ValueError("cache TTL must be zero or greater")
    return ttl


def iso_utc(timestamp: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))


def make_cache_key(params: dict[str, Any]) -> str:
    encoded = json.dumps(params, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:24]


def cache_path_for(cache_dir: Path, params: dict[str, Any]) -> Path:
    handle = params["handle"]
    return cache_dir / f"{handle}-{make_cache_key(params)}.json"


def load_cached_program(
    cache_path: Path, cache_ttl: int
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if cache_ttl <= 0:
        return None
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            record = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    if record.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None
    fetched_at = float(record.get("fetched_at") or 0)
    age_seconds = max(0, int(time.time() - fetched_at))
    if age_seconds > cache_ttl:
        return None

    program = record.get("program")
    if not isinstance(program, dict):
        return None

    return program, {
        "status": "hit",
        "path": str(cache_path),
        "fetched_at": iso_utc(fetched_at),
        "age_seconds": age_seconds,
        "ttl_seconds": cache_ttl,
    }


def write_cached_program(cache_path: Path, program: dict[str, Any]) -> dict[str, Any]:
    fetched_at = time.time()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    record = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "fetched_at": fetched_at,
        "program": program,
    }
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp_path, cache_path)
    return {
        "status": "refresh",
        "path": str(cache_path),
        "fetched_at": iso_utc(fetched_at),
        "age_seconds": 0,
        "ttl_seconds": None,
    }


def annotate_cache(program: dict[str, Any], cache_status: dict[str, Any] | None) -> dict[str, Any]:
    if not cache_status:
        return program
    annotated = dict(program)
    source = dict(annotated.get("source") or {})
    source["cache"] = cache_status
    annotated["source"] = source
    return annotated


def graphql_request(
    handle: str,
    offset: int,
    size: int,
    timeout: int,
    search: str | None,
    eligible_for_submission: bool | None,
    eligible_for_bounty: bool | None,
) -> dict[str, Any]:
    payload = {
        "operationName": "PublicProgramScope",
        "variables": {
            "handle": handle,
            "from": offset,
            "size": size,
            "searchString": search,
            "eligibleForSubmission": eligible_for_submission,
            "eligibleForBounty": eligible_for_bounty,
        },
        "query": QUERY,
    }
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "scope-lookup/0.1",
            "X-Requested-With": "XMLHttpRequest",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HackerOne returned HTTP {exc.code}: {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"could not reach HackerOne: {exc}") from exc


def fetch_program_live(
    handle: str,
    *,
    limit: int,
    page_size: int,
    fetch_all: bool,
    timeout: int,
    search: str | None,
    eligible_for_submission: bool | None,
    eligible_for_bounty: bool | None,
) -> dict[str, Any]:
    first_size = page_size if fetch_all else limit
    data = graphql_request(
        handle,
        0,
        first_size,
        timeout,
        search,
        eligible_for_submission,
        eligible_for_bounty,
    )
    if data.get("errors"):
        messages = "; ".join(error.get("message", str(error)) for error in data["errors"])
        raise RuntimeError(f"HackerOne GraphQL error: {messages}")

    team = (data.get("data") or {}).get("team")
    if team is None:
        raise RuntimeError(f"no public HackerOne program found for handle: {handle}")

    scope_search = team.get("structured_scopes_search") or {}
    nodes = list(scope_search.get("nodes") or [])
    total = int(scope_search.get("total_count") or len(nodes))

    if fetch_all and len(nodes) < total:
        offset = len(nodes)
        while offset < total:
            page = graphql_request(
                handle,
                offset,
                page_size,
                timeout,
                search,
                eligible_for_submission,
                eligible_for_bounty,
            )
            if page.get("errors"):
                messages = "; ".join(
                    error.get("message", str(error)) for error in page["errors"]
                )
                raise RuntimeError(f"HackerOne GraphQL error: {messages}")
            page_team = (page.get("data") or {}).get("team") or {}
            page_search = page_team.get("structured_scopes_search") or {}
            page_nodes = list(page_search.get("nodes") or [])
            if not page_nodes:
                break
            nodes.extend(page_nodes)
            offset += len(page_nodes)

    team["structured_scopes"] = nodes
    team["structured_scope_total_count"] = total
    team.pop("structured_scopes_search", None)
    team["source"] = {
        "graphql_url": GRAPHQL_URL,
        "program_url": f"https://hackerone.com/{handle}?type=team",
        "filters": {
            "search": search,
            "eligible_for_submission": eligible_for_submission,
            "eligible_for_bounty": eligible_for_bounty,
        },
        "note": "Best-effort public lookup. Verify current scope on the official program page before testing.",
    }
    return team


def lookup_program(
    handle: str,
    *,
    limit: int,
    page_size: int,
    fetch_all: bool,
    timeout: int,
    search: str | None,
    eligible_for_submission: bool | None,
    eligible_for_bounty: bool | None,
    cache_dir: Path,
    cache_ttl: int,
    refresh: bool,
    no_cache: bool,
) -> dict[str, Any]:
    cache_params = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "source": "hackerone-graphql",
        "handle": handle,
        "limit": None if fetch_all else limit,
        "fetch_all": fetch_all,
        "search": search,
        "eligible_for_submission": eligible_for_submission,
        "eligible_for_bounty": eligible_for_bounty,
    }
    cache_path = cache_path_for(cache_dir, cache_params)

    if not no_cache and not refresh:
        cached = load_cached_program(cache_path, cache_ttl)
        if cached is not None:
            program, cache_status = cached
            return annotate_cache(program, cache_status)

    program = fetch_program_live(
        handle,
        limit=limit,
        page_size=page_size,
        fetch_all=fetch_all,
        timeout=timeout,
        search=search,
        eligible_for_submission=eligible_for_submission,
        eligible_for_bounty=eligible_for_bounty,
    )

    if no_cache:
        cache_status = {"status": "disabled"}
    else:
        cache_status = write_cached_program(cache_path, program)
        cache_status["ttl_seconds"] = cache_ttl

    return annotate_cache(program, cache_status)


def parse_optional_bool(value: str) -> bool | None:
    lowered = value.lower()
    if lowered in {"any", "unknown", "null"}:
        return None
    if lowered in {"yes", "true", "1"}:
        return True
    if lowered in {"no", "false", "0"}:
        return False
    raise argparse.ArgumentTypeError("expected one of: yes, no, any")


def bool_text(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def truncate(value: str | None, max_chars: int) -> str:
    if not value:
        return ""
    collapsed = re.sub(r"\s+", " ", value).strip()
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max_chars - 3].rstrip() + "..."


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(program: dict[str, Any], policy_chars: int) -> str:
    policy = (program.get("policy_setting") or {}).get("policy")
    external_policy = (program.get("external_program") or {}).get("policy")
    declarative = program.get("declarative_policy") or {}
    scopes = program.get("structured_scopes") or []

    lines = [
        f"# HackerOne Program Scope: {program.get('name') or program.get('handle')}",
        "",
        f"- Handle: `{program.get('handle')}`",
        f"- Source: {program.get('source', {}).get('program_url')}",
        f"- State: `{program.get('state')}`",
        f"- Submission state: `{program.get('submission_state')}`",
        f"- Offers bounties: {bool_text(program.get('offers_bounties'))}",
        f"- Offers thanks: {bool_text(program.get('offers_thanks'))}",
        f"- Open scope: {bool_text(declarative.get('has_open_scope'))}",
        "- Gold safe harbor: "
        f"{bool_text(declarative.get('protected_by_gold_standard_safe_harbor'))}",
        "- AI safe harbor: "
        f"{bool_text(declarative.get('protected_by_ai_safe_harbor'))}",
        f"- Structured scopes shown: {len(scopes)} of "
        f"{program.get('structured_scope_total_count', len(scopes))}",
    ]
    cache = (program.get("source") or {}).get("cache")
    if cache:
        lines.append(
            "- Cache: "
            f"{cache.get('status')}"
            + (f" from `{cache.get('path')}`" if cache.get("path") else "")
            + (f", fetched {cache.get('fetched_at')}" if cache.get("fetched_at") else "")
        )

    exclusions = declarative.get("scope_exclusions") or []
    if exclusions:
        lines.extend(["", "## Scope Exclusions", ""])
        for item in exclusions:
            category = item.get("category") or "uncategorized"
            details = truncate(item.get("details"), 240)
            lines.append(f"- `{category}`: {details}")

    if scopes:
        lines.extend(
            [
                "",
                "## Structured Scopes",
                "",
                "| Submission | Bounty | Type | Identifier | Severity | Notes |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for scope in scopes:
            identifier = scope.get("identifier") or scope.get("display_name")
            notes = truncate(scope.get("instruction"), 160)
            lines.append(
                "| "
                f"{bool_text(scope.get('eligible_for_submission'))} | "
                f"{bool_text(scope.get('eligible_for_bounty'))} | "
                f"{markdown_escape(scope.get('asset_type'))} | "
                f"`{markdown_escape(identifier)}` | "
                f"{markdown_escape(scope.get('cvss_score'))} | "
                f"{markdown_escape(notes)} |"
            )

    if policy_chars > 0 and (policy or external_policy):
        lines.extend(["", "## Policy Excerpt", ""])
        lines.append(truncate(policy or external_policy, policy_chars))

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Look up public HackerOne program scope via HackerOne GraphQL."
    )
    parser.add_argument("program", help="HackerOne handle or https://hackerone.com/<handle> URL")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="output format",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="number of structured scopes to fetch unless --all is set",
    )
    parser.add_argument("--all", action="store_true", help="fetch all structured scopes")
    parser.add_argument("--page-size", type=int, default=100, help="page size for --all")
    parser.add_argument("--timeout", type=int, default=20, help="request timeout in seconds")
    parser.add_argument(
        "--cache-dir",
        default=str(default_cache_dir()),
        help="directory for persistent cache files; defaults to workspace data/.cache/hackerone",
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=parse_cache_ttl(os.environ.get("SCOPE_CACHE_TTL")),
        help="cache freshness window in seconds; 0 disables cache reads",
    )
    parser.add_argument("--refresh", action="store_true", help="ignore cache and fetch fresh data")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="disable cache reads and writes for this lookup",
    )
    parser.add_argument("--search", help="filter structured scopes by search text")
    parser.add_argument(
        "--eligible-for-submission",
        type=parse_optional_bool,
        default=None,
        metavar="{yes,no,any}",
        help="filter assets by submission eligibility",
    )
    parser.add_argument(
        "--eligible-for-bounty",
        type=parse_optional_bool,
        default=None,
        metavar="{yes,no,any}",
        help="filter assets by bounty eligibility",
    )
    parser.add_argument(
        "--policy-chars",
        type=int,
        default=2000,
        help="policy excerpt length for markdown output",
    )
    args = parser.parse_args(argv)

    try:
        handle = normalize_handle(args.program)
        if args.limit < 1:
            raise ValueError("--limit must be at least 1")
        if args.page_size < 1:
            raise ValueError("--page-size must be at least 1")
        if args.cache_ttl < 0:
            raise ValueError("--cache-ttl must be zero or greater")
        program = lookup_program(
            handle,
            limit=args.limit,
            page_size=args.page_size,
            fetch_all=args.all,
            timeout=args.timeout,
            search=args.search,
            eligible_for_submission=args.eligible_for_submission,
            eligible_for_bounty=args.eligible_for_bounty,
            cache_dir=Path(args.cache_dir).expanduser(),
            cache_ttl=args.cache_ttl,
            refresh=args.refresh,
            no_cache=args.no_cache,
        )
        if args.format == "markdown":
            sys.stdout.write(render_markdown(program, args.policy_chars))
        else:
            json.dump(program, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
    except Exception as exc:
        wrapped = textwrap.fill(str(exc), width=88)
        sys.stderr.write(f"error: {wrapped}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
