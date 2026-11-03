#!/usr/bin/env python3
"""Capture a check's real output bound to the tree it ran on, and tell when that evidence is stale.

  capture_check.py run --out <evidence/name.json> [--cwd DIR] -- <command> [args...]
  capture_check.py stale <evidence.json> [...]

`run` exits with the command's exit code. `stale` exits 1 when any file no longer matches the tree.
The tree identity hashes every tracked and untracked file (ignoring .ai-workflow/), so a commit alone does not make
evidence stale. It never writes to the repository.
"""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, check=True).stdout


def tree(cwd):
    """Content identity of the working tree (tracked and untracked files), independent of commits. Read-only."""
    top = git(cwd, "rev-parse", "--show-toplevel").decode().strip()
    head = subprocess.run(["git", "-C", top, "rev-parse", "--verify", "-q", "HEAD"], capture_output=True, text=True).stdout.strip()
    names = sorted(set(git(top, "ls-files", "-z", "--cached", "--others", "--exclude-standard").decode().split("\0")) - {""})
    digest = hashlib.sha256()
    for name in names:
        if name == ".ai-workflow" or name.startswith(".ai-workflow/"):
            continue
        path = Path(top, name)
        if path.is_symlink():
            data = b"link:" + os.readlink(path).encode()
        elif path.is_file():
            data = path.read_bytes()
        else:
            continue  # deleted from the working tree
        digest.update(name.encode() + b"\0" + hashlib.sha256(data).digest())
    return {"root": top, "head": head or None, "tree": digest.hexdigest()}


def run(out, cwd, command):
    cwd = Path(cwd).resolve()
    state, started = tree(cwd), time.time()
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, errors="replace")
    record = {"command": command, "cwd": str(cwd), **state, "exit_code": proc.returncode,
              "duration_s": round(time.time() - started, 3), "stdout": proc.stdout, "stderr": proc.stderr}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "x") as stream:  # never overwrite earlier evidence
        json.dump(record, stream, indent=2)
    print(json.dumps({"evidence": str(out), "exit_code": proc.returncode, "tree": state["tree"]}))
    return proc.returncode


def stale(paths):
    results = []
    for path in paths:
        record = json.loads(Path(path).read_text())
        now = tree(record["cwd"])
        current = now["tree"] == record["tree"]
        results.append({"evidence": path, "current": current, "exit_code": record["exit_code"]})
    print(json.dumps(results, indent=2))
    return 0 if all(r["current"] for r in results) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)
    capture = sub.add_parser("run")
    capture.add_argument("--out", required=True)
    capture.add_argument("--cwd", default=".")
    capture.add_argument("command", nargs=argparse.REMAINDER)
    check = sub.add_parser("stale")
    check.add_argument("paths", nargs="+")
    args = parser.parse_args()
    if args.action == "stale":
        return stale(args.paths)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("name the command after --")
    return run(args.out, args.cwd, command)


if __name__ == "__main__":
    sys.exit(main())
