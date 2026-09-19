#!/usr/bin/env python3
"""Bind a bounded role brief to its decision sources without embedding their contents."""

import argparse
import json
from pathlib import Path

from review_evidence import contract_hash, file_hash, load_record, require, write_record

DEFAULT_MAX_BYTES = 24000


def prepare(brief, sources, output, max_bytes=DEFAULT_MAX_BYTES):
    brief = Path(brief).resolve()
    require(type(max_bytes) is int and max_bytes > 0, "positive packet byte limit required")
    require(brief.stat().st_size <= max_bytes, "brief exceeds packet limit; link source sections instead of copying them")
    require(isinstance(sources, list) and sources, "packet requires source authority entries")
    entries = []
    seen = set()
    for source in sources:
        require(isinstance(source, dict) and set(source) == {"path", "authority", "locator"}, "source needs path, authority, locator")
        require(source["authority"] in {"decision", "evidence", "superseded"}, "invalid source authority")
        path = str(Path(source["path"]).resolve())
        require(path not in seen and isinstance(source["locator"], str) and source["locator"].strip(), "duplicate source or missing locator")
        seen.add(path)
        entries.append({**source, "path": path, "sha256": contract_hash(path) if source["authority"] == "decision" else file_hash(path)})
    require(any(e["authority"] == "decision" for e in entries), "name at least one current decision source")
    return write_record(output, {"brief": {"path": str(brief), "sha256": file_hash(brief)}, "sources": entries, "max_bytes": max_bytes})


def verify(path, brief=None):
    packet = load_record(path)
    entry = packet["brief"]
    require(brief is None or Path(brief).resolve() == Path(entry["path"]), "packet belongs to another brief")
    require(file_hash(entry["path"]) == entry["sha256"], "derived brief changed; rebuild packet")
    require(Path(entry["path"]).stat().st_size <= packet["max_bytes"], "brief exceeds packet limit")
    for entry in packet["sources"]:
        actual = contract_hash(entry["path"]) if entry["authority"] == "decision" else file_hash(entry["path"])
        require(actual == entry["sha256"], f"{entry['authority']} source changed; revise derived brief: {entry['path']}")
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    make = sub.add_parser("prepare")
    for name in ("brief", "sources", "output"):
        make.add_argument("--" + name, required=True)
    make.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    check = sub.add_parser("verify")
    check.add_argument("--packet", required=True)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            result = {"packet": str(prepare(args.brief, json.loads(Path(args.sources).read_text()), args.output, args.max_bytes))}
        else:
            verify(args.packet)
            result = {"status": "current"}
        print(json.dumps(result))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
