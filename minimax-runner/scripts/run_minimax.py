#!/usr/bin/env python3
"""Execute prompts against Minimax models through Cline CLI headless mode."""

import sys
from pathlib import Path

QWEN_RUNNER_DIR = Path(__file__).resolve().parents[2] / "qwen-runner" / "scripts"
sys.path.insert(0, str(QWEN_RUNNER_DIR))

import run_qwen

DEFAULT_MODEL = "minimax/minimax-m2.7"


if __name__ == "__main__":
    run_qwen.main(
        default_model=DEFAULT_MODEL,
        runner_name="minimax",
        description="Execute prompts using Cline CLI against Minimax models in headless mode.",
    )
