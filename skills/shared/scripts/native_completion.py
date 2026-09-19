#!/usr/bin/env python3
"""Capture an exact final message from a saved task wait response. Never dispatch."""
import argparse
import json
from pathlib import Path

from execution_metrics import normalize_metrics
from review_evidence import file_hash, load_record, require, write_record


def capture(raw_path, dispatch_path, context_id, host_id, turn_id, completed_turn, output):
    raw = json.loads(Path(raw_path).read_text())
    dispatch = json.loads(Path(dispatch_path).read_text())
    require(type(completed_turn) is int and completed_turn > 0, "positive completed turn required")
    require(isinstance(raw, dict) and raw.get("isError") is not True, "host response failed")
    if "content" in raw:
        payloads = [json.loads(block["text"]) for block in raw["content"] if block.get("type") == "text"]
        require(len(payloads) == 1, "expected one saved wait payload")
        raw = payloads[0]
    require(isinstance(raw, dict), "wait payload must be an object")
    polls = [p for p in raw.get("polls", []) if p.get("thread", {}).get("id") == context_id
             and p.get("thread", {}).get("hostId") == host_id]
    require(len(polls) == 1, "matching task completion is missing or ambiguous")
    poll = polls[0]
    turn = poll.get("latestTurn") or {}
    message = poll.get("latestAssistantMessage") or {}
    require(turn.get("id") == turn_id and turn.get("status") == "completed" and not turn.get("error"),
            "expected turn did not complete successfully")
    require(message.get("turnId") == turn_id and message.get("phase") == "final_answer"
            and isinstance(message.get("text"), str) and message["text"].strip(), "exact final message is missing")
    require(dispatch.get("context_id") in (None, context_id), "dispatch context differs")
    keys = ("host", "transport", "role", "task_id", "configured_model", "configured_effort", "tool_policy", "call_id", "input_revision")
    require(all(key in dispatch for key in keys), "dispatch binding is incomplete")
    execution = {key: dispatch[key] for key in keys}
    execution.update(context_id=context_id, completed_turn=completed_turn, turn_id=turn_id, host_id=host_id)
    receipt = {"success": True, "agent_message": message["text"], "native_execution": execution,
               "metrics": normalize_metrics({"duration_ms": turn.get("durationMs")}),
               "model_verification": "unverified", "verification_reason": "Wait response does not attest serving model.",
               "evidence": {name: {"path": str(Path(path).resolve()), "sha256": file_hash(path)}
                            for name, path in (("raw", raw_path), ("dispatch", dispatch_path))}}
    return write_record(output, receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("raw", "dispatch", "context-id", "host-id", "turn-id", "output"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--completed-turn", type=int, required=True)
    args = parser.parse_args()
    try:
        path = capture(args.raw, args.dispatch, args.context_id, args.host_id, args.turn_id, args.completed_turn, args.output)
        print(json.dumps({"receipt": str(path)}))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
