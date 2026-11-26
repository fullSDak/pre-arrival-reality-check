"""Command-line entry point: python3 -m realitycheck INPUT [--output NEWFILE]."""

from __future__ import annotations

import argparse
import sys
import unicodedata

from .core import InputError, load_input, render_report


def _safe_error(text: str) -> str:
    result = []
    for ch in text:
        category = unicodedata.category(ch)
        if category in ("Cc", "Cf", "Cs", "Zl", "Zp"):
            code = ord(ch)
            result.append(f"\\u{code:04X}" if code <= 0xFFFF else f"\\U{code:08X}")
        else:
            result.append(ch)
    return "".join(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m realitycheck",
        description="Summarize synthetic, manually annotated evidence without verification or network access.",
    )
    parser.add_argument("input", help="UTF-8 JSON input file (synthetic data only)")
    parser.add_argument("--output", metavar="NEWFILE.md", help="Create a new Markdown file; never overwrite")
    args = parser.parse_args(argv)
    try:
        report = render_report(load_input(args.input))
        if args.output is None:
            sys.stdout.write(report)
        else:
            # Exclusive creation rejects existing regular files, the input file,
            # symlinks (including dangling symlinks), and hard links without a
            # check-then-open race.
            with open(args.output, "x", encoding="utf-8", newline="\n") as stream:
                stream.write(report)
    except FileExistsError:
        print("error: output already exists; refusing to overwrite", file=sys.stderr)
        return 2
    except (InputError, OSError, UnicodeError) as exc:
        print("error: " + _safe_error(str(exc)), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
