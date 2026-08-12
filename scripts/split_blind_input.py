#!/usr/bin/env python3
"""Split a blind-input JSON into contiguous batches without changing prompts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.size < 1:
        raise ValueError("--size must be positive")

    source = json.loads(args.input.read_text())
    records = source["records"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(records), args.size):
        part = {
            "version": source.get("version"),
            "batch": start // args.size + 1,
            "records": records[start : start + args.size],
        }
        (args.output_dir / f"batch-{part['batch']:02d}.json").write_text(
            json.dumps(part, ensure_ascii=False, indent=2) + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
