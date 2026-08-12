#!/usr/bin/env python3
"""Build the public blind v3 diagnostic slice from local SLAVA and MERA data."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MANIFEST = Path("data/slice-manifest-v3.json")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def render_instruction(row: dict[str, Any]) -> str:
    instruction = str(row["instruction"])
    raw_inputs = row.get("inputs", {})
    inputs = raw_inputs if isinstance(raw_inputs, dict) else {"inputs": raw_inputs}
    values: dict[str, Any] = {}

    def collect(mapping: dict[str, Any]) -> None:
        for key, value in mapping.items():
            values.setdefault(str(key).casefold(), value)
            if isinstance(value, dict):
                collect(value)

    collect(inputs)
    if "{toxic_comment}" in instruction and "inputs" in values:
        values["toxic_comment"] = values["inputs"]

    def replace(match: re.Match[str]) -> str:
        value = values.get(match.group(1).casefold(), match.group(0))
        if isinstance(value, float) and value != value:
            return match.group(0)
        return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)

    return re.sub(r"\{([^{}]+)\}", replace, instruction).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slava", type=Path, required=True)
    parser.add_argument("--mera", type=Path, required=True, help="MERA data directory")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--reference-key",
        type=Path,
        help="optional local answer-key output; never pass this file to a model",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    slava = {int(row["id"]): row for row in read_jsonl(args.slava)}
    records: list[dict[str, Any]] = []
    reference: list[dict[str, Any]] = []
    for item in manifest["records"]:
        if item["benchmark"] == "SLAVA":
            row = slava[int(item["id"])]
        else:
            rows = read_jsonl(args.mera / item["task"] / f'{item["split"]}.jsonl')
            row = rows[int(item["row_index"])]
        record = {key: item[key] for key in ("benchmark", "task", "id")}
        if "split" in item:
            record["split"] = item["split"]
        record["prompt"] = render_instruction(row)
        records.append(record)
        reference.append({key: record[key] for key in record if key != "prompt"} | {"expected": row.get("outputs")})

    unresolved = re.compile(r"\{(?:[A-Za-z_][A-Za-z0-9_]*|Option_\d+)\}")
    if len(records) != 20 or any(unresolved.search(item["prompt"]) for item in records):
        raise ValueError("slice is incomplete or has unresolved placeholders")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"version": manifest["version"], "records": records}, ensure_ascii=False, indent=2) + "\n")
    if args.reference_key:
        args.reference_key.parent.mkdir(parents=True, exist_ok=True)
        args.reference_key.write_text(json.dumps({"version": manifest["version"], "records": reference}, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
