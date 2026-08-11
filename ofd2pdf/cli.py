"""Command-line interface for ofd2pdf."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .converter import convert_batch, convert_file, list_backends


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ofd2pdf",
        description="Convert OFD (GB/T 33190) documents to PDF.",
    )
    parser.add_argument("input", nargs="?", help="Input OFD file or directory")
    parser.add_argument("-o", "--output", help="Output PDF file or directory")
    parser.add_argument(
        "-b",
        "--backend",
        choices=["easyofd", "taurusxin", "ofdrw"],
        help="Conversion backend (default: first available)",
    )
    parser.add_argument("--batch", action="store_true", help="Batch convert all .ofd files in input directory")
    parser.add_argument("--pattern", default="*.ofd", help="Glob pattern for batch mode (default: *.ofd)")
    parser.add_argument("--list-backends", action="store_true", help="List available backends and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--version", action="version", version=f"ofd2pdf {__version__}")

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    if not args.list_backends:
        if not args.input:
            parser.error("input is required unless --list-backends is used")
        if not args.output:
            parser.error("-o/--output is required")

    if args.list_backends:
        print("Backends:")
        for info in list_backends().values():
            status = "available" if info["available"] else "not available"
            print(f"  - {info['name']:12} [{status}] {info['description']}")
        return 0

    try:
        if args.batch:
            results = convert_batch(args.input, args.output, backend=args.backend, pattern=args.pattern)
            ok = sum(1 for _, dst in results if dst is not None)
            print(f"Batch complete: {ok}/{len(results)} succeeded")
            return 0 if ok == len(results) else 1

        convert_file(args.input, args.output, backend=args.backend)
        print(f"Converted: {Path(args.output).resolve()}")
        return 0
    except Exception as exc:
        logging.error("Conversion failed: %s", exc)
        if args.verbose:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main())
