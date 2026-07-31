#!/usr/bin/env python3
"""Kanban board over the pipeline's durable run state.

Serves a static board (index.html) plus /api/runs, which scans the target
repo's .ai-workflow/ tree for run-state.json files (the run-state contract,
_shared/references/run-state-contract.md) and returns them as JSON. Read-only:
never writes to the target repo.

Usage:
    python3 pipeline-board/serve.py [target-repo] [--port 8642]
"""

import argparse
import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BOARD_DIR = Path(__file__).resolve().parent

# State files that follow the contract shape but keep legacy names/locations.
STATE_GLOBS = [
    ".ai-workflow/*/*/run-state.json",
    ".ai-workflow/consensus/*.json",
    ".ai-workflow/*/*/launch-manifest.json",
]


def collect_runs(target: Path) -> list[dict]:
    runs = []
    for pattern in STATE_GLOBS:
        for path in sorted(target.glob(pattern)):
            try:
                data = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                runs.append({"file": str(path.relative_to(target)), "parse_error": True})
                continue
            if not isinstance(data, dict):
                continue
            data["file"] = str(path.relative_to(target))
            data.setdefault("skill", path.parts[path.parts.index(".ai-workflow") + 1]
                            if ".ai-workflow" in path.parts else "unknown")
            runs.append(data)
    return runs


def make_handler(target: Path):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(BOARD_DIR), **kwargs)

        def do_GET(self):
            if self.path.startswith("/api/runs"):
                body = json.dumps(
                    {"target": str(target), "runs": collect_runs(target)}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

        def log_message(self, fmt, *args):
            pass

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", default=".",
                        help="repo whose .ai-workflow/ to watch (default: cwd)")
    parser.add_argument("--port", type=int, default=8642)
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"error: {target} is not a directory", file=sys.stderr)
        return 2
    if not (target / ".ai-workflow").is_dir():
        print(f"note: {target}/.ai-workflow does not exist yet — board will be empty "
              "until a pipeline run writes state", file=sys.stderr)

    server = HTTPServer(("127.0.0.1", args.port), make_handler(target))
    print(f"pipeline board: http://localhost:{args.port}  (watching {target})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
