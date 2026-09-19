"""Record loaded resources and runtime facts without reading local credentials."""

import hashlib
import platform
from pathlib import Path


def capture(paths):
    resources = []
    for path in sorted({str(Path(p).resolve()) for p in paths}):
        resources.append({"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()})
    return {"resources": resources, "runtime": {"python": platform.python_version(), "system": platform.system()}}
