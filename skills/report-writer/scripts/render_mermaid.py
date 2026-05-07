#!/usr/bin/env python3
"""Render Mermaid diagrams to SVG/PNG/PDF using Mermaid CLI."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def is_windows_tool(path: str | None) -> bool:
    if not path:
        return False
    lowered = path.lower()
    return lowered.startswith("/mnt/c/") or lowered.endswith((".exe", ".cmd", ".bat"))


def wsl_to_windows(path: Path) -> str:
    return subprocess.check_output(["wslpath", "-w", str(path.resolve())], text=True).strip()


def build_command(args: argparse.Namespace) -> list[str]:
    mmdc = shutil.which("mmdc")
    args.run_cwd = None
    use_windows_paths = False
    if mmdc:
        cmd = [mmdc]
    else:
        npx = shutil.which("npx")
        if not (args.allow_npx and npx):
            raise SystemExit(
                "mmdc was not found. Install @mermaid-js/mermaid-cli or rerun with --allow-npx "
                "to use npx -y @mermaid-js/mermaid-cli."
            )
        cmd = [npx, "-y", "@mermaid-js/mermaid-cli"]
        use_windows_paths = is_windows_tool(npx) and shutil.which("wslpath") is not None
        if use_windows_paths and Path("/mnt/c/Windows/Temp").is_dir():
            args.run_cwd = "/mnt/c/Windows/Temp"

    def p(path: Path) -> str:
        return wsl_to_windows(path) if use_windows_paths else str(path)

    cmd.extend(["-i", p(args.input), "-o", p(args.output)])
    if args.theme:
        cmd.extend(["-t", args.theme])
    if args.background:
        cmd.extend(["-b", args.background])
    if args.width:
        cmd.extend(["--width", str(args.width)])
    if args.height:
        cmd.extend(["--height", str(args.height)])
    if args.scale:
        cmd.extend(["--scale", str(args.scale)])
    if args.config:
        cmd.extend(["--configFile", p(args.config)])
    if args.css:
        cmd.extend(["--cssFile", p(args.css)])
    if args.puppeteer_config:
        cmd.extend(["--puppeteerConfigFile", p(args.puppeteer_config)])
    return cmd


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render a Mermaid diagram with Mermaid CLI.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--theme", default="default", choices=["default", "forest", "dark", "neutral"])
    parser.add_argument("--background", default="")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--scale", type=float)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--css", type=Path)
    parser.add_argument("--puppeteer-config", type=Path)
    parser.add_argument("--allow-npx", action="store_true")
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_command(args)
    subprocess.run(cmd, check=True, cwd=getattr(args, "run_cwd", None))
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
