#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path

HUNK_RE = re.compile(r"^@@\s+\-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")

def parse_diff(text: str):
    files = []
    current = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            if current:
                files.append(current)
            current = {"path": None, "hunks": [], "change_type": "modified"}
        elif current is not None and line.startswith("new file mode"):
            current["change_type"] = "added"
        elif current is not None and line.startswith("deleted file mode"):
            current["change_type"] = "deleted"
        elif current is not None and line.startswith("rename from "):
            current["change_type"] = "renamed"
            current["renamed_from"] = line[len("rename from "):]
        elif current is not None and line.startswith("rename to "):
            current["path"] = line[len("rename to "):]
        elif current is not None and "Binary files" in line and "differ" in line:
            current["change_type"] = "binary"
            current["binary"] = True
        elif current is not None and line.startswith("+++ "):
            parts = line.split()
            if len(parts) >= 2 and parts[1].startswith("b/"):
                current["path"] = parts[1][2:]
        elif current is not None:
            m = HUNK_RE.match(line)
            if m:
                old_start = int(m.group(1))
                old_len = int(m.group(2) or "1")
                new_start = int(m.group(3))
                new_len = int(m.group(4) or "1")
                h = {
                    "header": line,
                    "old_start": old_start,
                    "old_lines": old_len,
                    "new_start": new_start,
                    "new_lines": new_len,
                    "new_range": None,
                    "old_range": None,
                }
                if new_len > 0:
                    h["new_range"] = [new_start, new_start + new_len - 1]
                if old_len > 0:
                    h["old_range"] = [old_start, old_start + old_len - 1]
                current["hunks"].append(h)
    if current:
        files.append(current)

    files = [f for f in files if f.get("path")]
    return {"files": files}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("diff", help="Path to unified diff patch file")
    ap.add_argument("--out", help="Output json file, default stdout")
    args = ap.parse_args()

    p = Path(args.diff)
    text = p.read_text(encoding="utf-8", errors="replace")
    data = parse_diff(text)

    if args.out:
        Path(args.out).write_text(json.dumps(data, indent=2), encoding="utf-8")
    else:
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
