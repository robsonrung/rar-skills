#!/usr/bin/env python3
"""Execute prompts as the Muse seat through Cline CLI headless mode."""

import sys
from pathlib import Path

CLINE_RUNNER_DIR = Path(__file__).resolve().parents[2] / "cline-runner" / "scripts"
sys.path.insert(0, str(CLINE_RUNNER_DIR))

import run_cline

DEFAULT_MODEL = "meta/muse-spark-1.1"


if __name__ == "__main__":
    run_cline.main(
        default_model=DEFAULT_MODEL,
        runner_name="muse",
        description="Execute prompts as the Muse seat through Cline CLI headless mode.",
    )
