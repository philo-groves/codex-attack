#!/usr/bin/env python3
"""Generate minimal fuzz harness scaffolds for common ecosystems."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def ident(value: str, fallback: str = "target") -> str:
    value = re.sub(r"\W+", "_", value.strip())
    value = re.sub(r"^_+|_+$", "", value)
    if not value:
        value = fallback
    if value[0].isdigit():
        value = "_" + value
    return value


def c_cpp(name: str) -> str:
    return """#include <cstddef>
#include <cstdint>

// TODO: include the header for the API under test.
// #include "parser.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  // TODO: Replace this placeholder with a deterministic call into one parser,
  // decoder, or API boundary. Avoid network, filesystem, sleeps, and exit().
  (void)data;
  (void)size;
  return 0;
}
"""


def go(name: str) -> str:
    func = ident(name, "FuzzTarget")
    if not func.startswith("Fuzz"):
        func = "Fuzz" + func[0].upper() + func[1:]
    return f"""package TODO_PACKAGE

import "testing"

func {func}(f *testing.F) {{
\tf.Add([]byte("seed"))
\tf.Fuzz(func(t *testing.T, data []byte) {{
\t\t// TODO: Replace with a deterministic call into the API under test.
\t\t_ = data
\t}})
}}
"""


def rust(name: str) -> str:
    return """#![no_main]

use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    // TODO: Replace with a deterministic call into the API under test.
    let _ = data;
});
"""


def python(name: str) -> str:
    func = ident(name, "fuzz_target")
    return f"""import atheris
import sys


def {func}(data: bytes) -> None:
    # TODO: Replace with a deterministic call into the API under test.
    _ = data


def main() -> None:
    atheris.Setup(sys.argv, {func})
    atheris.Fuzz()


if __name__ == "__main__":
    main()
"""


def java(name: str) -> str:
    cls = ident(name, "Fuzzer")
    return f"""import com.code_intelligence.jazzer.api.FuzzedDataProvider;

public class {cls} {{
  public static void fuzzerTestOneInput(FuzzedDataProvider data) {{
    // TODO: Replace with a deterministic call into the API under test.
    byte[] bytes = data.consumeRemainingAsBytes();
  }}
}}
"""


TEMPLATES = {
    "c-cpp": c_cpp,
    "cpp": c_cpp,
    "c": c_cpp,
    "go": go,
    "rust": rust,
    "python": python,
    "java": java,
    "jvm": java,
}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate a starter fuzz harness.")
    parser.add_argument("kind", choices=sorted(TEMPLATES), help="harness ecosystem")
    parser.add_argument("--name", default="target", help="harness/function/class name")
    parser.add_argument("--output", help="write scaffold to this path")
    parser.add_argument("--force", action="store_true", help="overwrite output file")
    args = parser.parse_args(argv)

    text = TEMPLATES[args.kind](args.name)
    if args.output:
        path = Path(args.output)
        if path.exists() and not args.force:
            print(f"error: refusing to overwrite {path}; pass --force", file=sys.stderr)
            return 2
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(str(path))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
