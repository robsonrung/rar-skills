#!/usr/bin/env python3
"""Execute prompts against Minimax models through Cline CLI headless mode."""

import sys
from pathlib import Path

CLINE_RUNNER_DIR = Path(__file__).resolve().parents[2] / "cline-runner" / "scripts"
sys.path.insert(0, str(CLINE_RUNNER_DIR))

import run_cline  # pyright: ignore[reportMissingImports] - sys.path is set at runtime above

DEFAULT_MODEL = "minimax/minimax-m2.7"


if __name__ == "__main__":
    run_cline.main(
        default_model=DEFAULT_MODEL,
        runner_name="minimax",
        description="Execute prompts using Cline CLI against Minimax models in headless mode.",
    )
