"""Example: batch convert all .ofd files in a directory."""

from pathlib import Path

from ofd2pdf.converter import convert_batch

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument("--backend", default=None)
    args = parser.parse_args()

    results = convert_batch(args.input_dir, args.output_dir, backend=args.backend)
    for src, dst in results:
        status = "OK" if dst else "FAILED"
        print(f"{status}: {Path(src).name}")
