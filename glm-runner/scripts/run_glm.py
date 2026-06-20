#!/usr/bin/env python3
"""Execute prompts against GLM models through Qwen CLI headless mode."""

import sys
from pathlib import Path


QWEN_RUNNER_DIR = Path(__file__).resolve().parents[2] / "qwen-runner" / "scripts"
sys.path.insert(0, str(QWEN_RUNNER_DIR))

import run_qwen  # noqa: E402


DEFAULT_MODEL = "z-ai/glm-5.2"


if __name__ == "__main__":
    run_qwen.main(
        default_model=DEFAULT_MODEL,
        runner_name="glm",
        description="Execute prompts using Qwen CLI against GLM models in headless mode.",
    )
