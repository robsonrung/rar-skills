#!/usr/bin/env python3
"""Execute prompts as the GLM seat through Cline CLI headless mode.

Unlike the previous dcode-backed shim, the GLM identity here is a *real*
forwarded model: `--model zai/glm-5.2` is passed straight through to `cline`,
which resolves it against Z.AI via whichever Cline provider the user has
authenticated (verified live against the `cline-pass` gateway). The envelope
reports `runner=glm`, `effective_runner=cline`.
"""

import sys
from pathlib import Path


CLINE_RUNNER_DIR = Path(__file__).resolve().parents[2] / "cline-runner" / "scripts"
sys.path.insert(0, str(CLINE_RUNNER_DIR))

import run_cline  # noqa: E402


DEFAULT_MODEL = "zai/glm-5.2"


if __name__ == "__main__":
    run_cline.main(
        default_model=DEFAULT_MODEL,
        runner_name="glm",
        description="Execute prompts as the GLM seat through Cline CLI headless mode.",
    )
