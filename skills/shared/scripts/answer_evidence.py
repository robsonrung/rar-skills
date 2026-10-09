#!/usr/bin/env python3
"""Capture an actual supplied answer as immutable, portable decision evidence."""

import argparse
import hashlib
import json
from pathlib import Path

from review_evidence import load_record, require, write_record

AUTHORITIES = {"user_instruction", "approved_decision", "repository_fact", "inference"}


def capture(answer, supplied_by, authority, output, native_locator=None, supersedes=None, dry_run=False):
    """Capture supplied text; the caller must establish its origin and decision scope."""
    require(isinstance(answer, str) and bool(answer.strip()), "actual supplied answer text is required")
    require(supplied_by in {"user", "role", "repository"}, "invalid answer origin")
    require(authority in AUTHORITIES, "invalid source authority")
    require(authority not in {"user_instruction", "approved_decision"} or supplied_by == "user",
            "only an actual user answer can carry user decision authority")
    require(native_locator is None or isinstance(native_locator, str) and bool(native_locator.strip()),
            "native locator must be a supplied nonempty reference, or omitted")
    previous = None
    if supersedes is not None:
        prior_path = Path(supersedes).resolve()
        prior = load_record(prior_path)
        require(prior.get("schema_version") == 1 and "source_id" in prior and "actual_answer" in prior,
                "supersedes must identify an answer evidence record")
        require(prior_path != Path(output).resolve(), "a correction needs a new artifact path")
        previous = {"source_id": prior["source_id"], "path": str(prior_path)}
    answer_hash = hashlib.sha256(answer.encode("utf-8")).hexdigest()
    record = {"schema_version": 1, "actual_answer": answer, "answer_sha256": answer_hash,
              "supplied_by": supplied_by, "authority": authority, "native_locator": native_locator,
              "locator_limit": None if native_locator else "Native message locator unavailable; captured supplied text only.",
              "supersedes": previous}
    identity = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    record["source_id"] = "S-" + hashlib.sha256(identity).hexdigest()
    output = Path(output).resolve()
    if output.exists():
        require(load_record(output) == record, "answer evidence already exists with different content")
    if not dry_run:
        write_record(output, record)
    return {"source_id": record["source_id"], "path": str(output), "locator": "payload.actual_answer",
            "authority": authority, "content_revision": record["answer_sha256"],
            "native_locator": native_locator, "locator_limit": record["locator_limit"]}


def packet_source(path, superseded=False):
    """Map captured authority to the existing context packet input shape."""
    path = Path(path).resolve()
    value = load_record(path)
    require(value.get("schema_version") == 1 and value.get("authority") in AUTHORITIES,
            "invalid answer evidence record")
    authority = "superseded" if superseded else "decision" if value["authority"] in {"user_instruction", "approved_decision"} else "evidence"
    return {"path": str(path), "authority": authority, "locator": "payload.actual_answer"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    save = commands.add_parser("capture", help="capture a supplied answer without replacing prior evidence")
    save.add_argument("--answer", type=Path, required=True, help="UTF-8 file with the exact supplied answer")
    save.add_argument("--supplied-by", choices=["user", "role", "repository"], required=True)
    save.add_argument("--authority", choices=sorted(AUTHORITIES), required=True)
    save.add_argument("--output", required=True)
    save.add_argument("--native-locator", help="actual host message reference when exposed")
    save.add_argument("--supersedes", help="previous immutable answer record; preserved unchanged")
    save.add_argument("--dry-run", action="store_true")
    packet = commands.add_parser("packet-source", help="emit one source entry for context_packet.py")
    packet.add_argument("--record", required=True)
    packet.add_argument("--superseded", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "capture":
            with args.answer.open(encoding="utf-8", newline="") as stream:
                result = capture(stream.read(), args.supplied_by, args.authority, args.output,
                                 args.native_locator, args.supersedes, args.dry_run)
        else:
            result = packet_source(args.record, args.superseded)
        print(json.dumps(result))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
