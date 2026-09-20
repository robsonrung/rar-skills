"""Persist structured process events and partial receipts without claiming completion."""

import contextlib
import json
import os
import selectors
import signal
import subprocess
import time
import threading
from pathlib import Path

from execution_metrics import FIELDS, normalize_metrics
from run_state import atomic_write


def progress(events):
    session = None
    messages = {}
    terminal = None
    for event in events:
        if not isinstance(event, dict):
            continue
        session = event.get("session_id") or session
        if event.get("type") == "result":
            terminal = event
        message = event.get("message")
        if event.get("type") == "assistant" and isinstance(message, dict) and message.get("id") and isinstance(message.get("usage"), dict):
            messages[message["id"]] = normalize_metrics(message)
    metrics = normalize_metrics(terminal) if terminal else {
        key: sum(row[key] for row in messages.values()) if messages and all(row[key] is not None for row in messages.values()) else None
        for key in FIELDS
    }
    return {"session_id": session, "metrics": metrics, "metrics_complete": terminal is not None,
            "events": len(events), "terminal_observed": terminal is not None}


def parse_events(text):
    events = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
            events.extend(event if isinstance(event, list) else [event])
        except json.JSONDecodeError:
            continue
    return events


@contextlib.contextmanager
def cancellation_signals():
    """Let cleanup terminate the owned child group when the wrapper is cancelled."""
    previous = {}
    def stop(signum, _frame):
        raise SystemExit(128 + signum)
    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous[signum] = signal.signal(signum, stop)
    try:
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def capture(command, cwd, env, timeout, event_log):
    """Drain both pipes, flush each event, and terminate the owned process group on timeout."""
    target = Path(event_log).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = target.with_suffix(".checkpoint.json")
    events, chunks = [], {"stdout": [], "stderr": []}
    pending = b""
    with target.open("xb") as log, cancellation_signals():
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        deadline = time.monotonic() + timeout
        timed_out = False
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            try:
                while selector.get_map():
                    if time.monotonic() >= deadline:
                        timed_out = True
                        break
                    for key, _ in selector.select(min(0.2, max(0, deadline - time.monotonic()))):
                        block = os.read(key.fileobj.fileno(), 65536)
                        if not block:
                            selector.unregister(key.fileobj)
                            continue
                        chunks[key.data].append(block)
                        if key.data == "stdout":
                            log.write(block)
                            log.flush()
                            pending += block
                            while b"\n" in pending:
                                line, pending = pending.split(b"\n", 1)
                                events.extend(parse_events(line.decode("utf-8", errors="replace")))
                            atomic_write(checkpoint, {**progress(events), "status": "running", "event_log": str(target)})
                if not timed_out:
                    try:
                        process.wait(timeout=max(0, deadline - time.monotonic()))
                    except subprocess.TimeoutExpired:
                        timed_out = True
            except BaseException:
                atomic_write(checkpoint, {**progress(events), "status": "interrupted", "event_log": str(target)})
                raise
            finally:
                if process.poll() is None or timed_out:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.wait()
                process.stdout.close()
                process.stderr.close()
        stdout = b"".join(chunks["stdout"]).decode("utf-8", errors="replace")
        stderr = b"".join(chunks["stderr"]).decode("utf-8", errors="replace")
        # Include a final JSON event without a newline, but never treat truncation as a result.
        receipt = {**progress(parse_events(stdout)), "status": "interrupted" if timed_out else "exited",
                   "event_log": str(target), "return_code": process.returncode}
        atomic_write(checkpoint, receipt)
        if timed_out:
            raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr)
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
