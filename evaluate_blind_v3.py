#!/usr/bin/env python3
"""Score scalar blind-v3 outputs against the separately stored answer key."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def normalize(value: Any) -> str:
    return re.sub(r"[.。]+$", "", re.sub(r"\\s+", " ", str(value or "").lower().strip()).strip('«»"\''))


def record_key(item: dict[str, Any]) -> tuple[str, str, int]:
    return (str(item["benchmark"]), str(item["task"]), int(item["id"]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("results", type=Path, nargs="+")
    args = parser.parse_args()

    key_doc = json.loads(args.key.read_text())
    expected = {record_key(item): item["expected"] for item in key_doc["records"]}
    summary: dict[str, Any] = {}

    for result_path in args.results:
        result_doc = json.loads(result_path.read_text())
        groups: dict[str, dict[str, int]] = {}
        for item in result_doc["records"]:
            gold = expected[record_key(item)]
            group = groups.setdefault(item["benchmark"], {"total": 0, "scored": 0, "exact": 0, "structured": 0})
            group["total"] += 1
            if not isinstance(gold, str):
                group["structured"] += 1
                continue
            group["scored"] += 1
            group["exact"] += int(normalize(item.get("answer")) == normalize(gold))
        summary[result_path.name] = groups

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
