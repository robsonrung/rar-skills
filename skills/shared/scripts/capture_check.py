#!/usr/bin/env python3
"""Capture a check's real output bound to the inputs it ran on, and tell when that evidence is stale.

  capture_check.py run --out <evidence/name.json> [--cwd DIR] [--base REV] [--contract FILE] -- <command> [args...]
  capture_check.py stale [--target DIR] [--base REV] [--contract FILE] [--command "CMD"] <evidence.json> [...]

`run` exits with the command's exit code. It records the inputs: the tree hash of the checkout the command ran in,
the resolved base commit (with --base), the contract file's hash (with --contract), and the exact command.

`stale` exits 1 when any record no longer matches. It compares against the target checkout (--target, default: the
current directory), never against the checkout named inside the record, so evidence captured in a worker checkout is
stale once the target differs. A record is current only when every recorded input matches:
  - the target's tree hash equals the recorded one;
  - the recorded base ref (or --base) resolves in the target to the recorded commit;
  - the recorded contract file (or --contract) has the recorded hash;
  - --command, when given, is the recorded command.
A record that lacks an input the caller asks for, or an old record without recorded inputs, is stale: rerun it.

The tree hash covers every tracked and untracked file except .ai-workflow/, so a commit alone does not make evidence
stale; the contract under .ai-workflow/ is covered by --contract instead. It never writes to the repository.
"""
import argparse, hashlib, json, os, shlex, subprocess, sys, time
from pathlib import Path

FORMAT = 2


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


def resolve_commit(cwd, ref):
    """Commit a ref names in the checkout at `cwd`, or None when it does not resolve."""
    out = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"],
                         capture_output=True, text=True).stdout.strip()
    return out or None


def file_hash(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def contract_input(path, root):
    """Record a contract file by its hash, with its path relative to the checkout root when inside it."""
    path = Path(path).resolve()
    digest = file_hash(path)
    if digest is None:
        raise SystemExit(f"error: contract file not found: {path}")
    try:
        shown = str(path.relative_to(root))
    except ValueError:
        shown = str(path)
    return {"path": shown, "sha256": digest}


def run(out, cwd, command, base=None, contract=None):
    cwd = Path(cwd).resolve()
    state = tree(cwd)
    inputs = {"tree": state["tree"], "command": command, "base": None, "contract": None}
    if base is not None:
        commit = resolve_commit(cwd, base)
        if commit is None:
            raise SystemExit(f"error: base does not resolve: {base}")
        inputs["base"] = {"ref": base, "commit": commit}
    if contract is not None:
        inputs["contract"] = contract_input(contract, Path(state["root"]))
    started = time.time()
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, errors="replace")
    record = {"format": FORMAT, "command": command, "cwd": str(cwd), **state, "inputs": inputs,
              "exit_code": proc.returncode, "duration_s": round(time.time() - started, 3),
              "stdout": proc.stdout, "stderr": proc.stderr}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "x") as stream:  # never overwrite earlier evidence
        json.dump(record, stream, indent=2)
    print(json.dumps({"evidence": str(out), "exit_code": proc.returncode, "tree": state["tree"]}))
    return proc.returncode


def stale_reasons(record, target, base=None, contract=None, command=None):
    """Why a record is stale for the target checkout; an empty list means it is current."""
    inputs = record.get("inputs")
    if record.get("format") != FORMAT or not isinstance(inputs, dict) or not inputs.get("tree") or not inputs.get("command"):
        return ["record has no recorded inputs (old format); rerun"]
    try:
        now = tree(target)
    except subprocess.CalledProcessError:
        return [f"target is not a git checkout: {target}"]
    reasons = []
    if now["tree"] != inputs["tree"]:
        reasons.append("target tree differs from the recorded tree")
    recorded_base = inputs.get("base")
    if base is not None and not recorded_base:
        reasons.append("record has no base")
    elif recorded_base:
        ref = base if base is not None else recorded_base.get("ref")
        if not ref or resolve_commit(target, ref) != recorded_base.get("commit"):
            reasons.append(f"base {ref} does not resolve to the recorded commit")
    recorded_contract = inputs.get("contract")
    if contract is not None and not recorded_contract:
        reasons.append("record has no contract")
    elif recorded_contract:
        path = Path(contract if contract is not None else recorded_contract.get("path", ""))
        if contract is None and not path.is_absolute():
            path = Path(now["root"], path)
        if file_hash(path) != recorded_contract.get("sha256"):
            reasons.append(f"contract {path} differs from the recorded hash")
    if command is not None and shlex.split(command) != inputs["command"]:
        reasons.append("command differs from the recorded command")
    return reasons


def stale(paths, target=".", base=None, contract=None, command=None):
    target = Path(target).resolve()
    results = []
    for path in paths:
        record = json.loads(Path(path).read_text())
        reasons = stale_reasons(record, target, base, contract, command)
        results.append({"evidence": path, "current": not reasons, "exit_code": record.get("exit_code"), "reasons": reasons})
    print(json.dumps(results, indent=2))
    return 0 if all(r["current"] for r in results) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)
    capture = sub.add_parser("run")
    capture.add_argument("--out", required=True)
    capture.add_argument("--cwd", default=".")
    capture.add_argument("--base", help="base ref; its resolved commit is recorded")
    capture.add_argument("--contract", help="acceptance contract file; its hash is recorded")
    capture.add_argument("command", nargs=argparse.REMAINDER)
    check = sub.add_parser("stale")
    check.add_argument("--target", default=".", help="checkout to compare against (default: current directory)")
    check.add_argument("--base", help="base ref the evidence must have been captured against")
    check.add_argument("--contract", help="contract file the evidence must have been captured against")
    check.add_argument("--command", help="exact command the evidence must have run (shell-quoted string)")
    check.add_argument("paths", nargs="+")
    args = parser.parse_args()
    if args.action == "stale":
        return stale(args.paths, args.target, args.base, args.contract, args.command)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("name the command after --")
    return run(args.out, args.cwd, command, args.base, args.contract)


if __name__ == "__main__":
    sys.exit(main())
