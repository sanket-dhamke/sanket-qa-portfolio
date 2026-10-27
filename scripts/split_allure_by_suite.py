#!/usr/bin/env python3
"""Copy Allure result files into smoke / sanity / regression buckets."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

SUITES = ("smoke", "sanity", "regression")


def suite_of(result: dict) -> str | None:
    labels = result.get("labels") or []
    values = {row.get("value") for row in labels if row.get("name") in {"suite", "feature", "tag"}}
    if "live" in values:
        return None
    for suite in SUITES:
        if suite in values:
            return suite
    return None


def attachment_names(obj: object) -> list[str]:
    names: list[str] = []
    if isinstance(obj, dict):
        source = obj.get("source")
        if isinstance(source, str) and "-attachment" in source:
            names.append(source)
        for value in obj.values():
            names.extend(attachment_names(value))
    elif isinstance(obj, list):
        for value in obj:
            names.extend(attachment_names(value))
    return names


def empty_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def split(src: Path, dest_root: Path) -> dict[str, int]:
    counts = {suite: 0 for suite in SUITES}
    buckets = {suite: dest_root / suite for suite in SUITES}
    for dest in buckets.values():
        empty_dir(dest)
    uuids: dict[str, set[str]] = {suite: set() for suite in SUITES}
    for path in src.glob("*-result.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        suite = suite_of(data)
        if not suite:
            continue
        dest = buckets[suite]
        shutil.copy2(path, dest / path.name)
        counts[suite] += 1
        uuid = data.get("uuid")
        if uuid:
            uuids[suite].add(str(uuid))
        for name in attachment_names(data):
            att = src / name
            if att.exists():
                shutil.copy2(att, dest / name)
    for path in src.glob("*-container.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        children = [str(c) for c in (data.get("children") or [])]
        for suite, kept in uuids.items():
            filtered = [c for c in children if c in kept]
            if not filtered:
                continue
            row = dict(data)
            row["children"] = filtered
            (buckets[suite] / path.name).write_text(json.dumps(row), encoding="utf-8")
    for name in ("environment.properties", "categories.json", "executor.json"):
        src_file = src / name
        if not src_file.exists():
            continue
        for dest in buckets.values():
            shutil.copy2(src_file, dest / name)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("src")
    parser.add_argument("dest")
    args = parser.parse_args()
    counts = split(Path(args.src), Path(args.dest))
    print(f"{args.src} -> {args.dest} {counts}")


if __name__ == "__main__":
    main()
