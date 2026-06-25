#!/usr/bin/env python3
"""Execute prompts as the GLM seat through DeepAgents CLI (dcode) headless mode.

The GLM identity is a seat *label* in the envelope; the model dcode actually
calls is whichever one the user has configured in dcode (`/model`, `/auth`,
`~/.deepagents/config.toml`, or a project `.env`). To make the GLM seat truly
GLM, point dcode at a GLM provider in its own configuration — this wrapper
deliberately never forwards `--model` to dcode.
"""

import sys
from pathlib import Path


DCODE_RUNNER_DIR = Path(__file__).resolve().parents[2] / "dcode-runner" / "scripts"
sys.path.insert(0, str(DCODE_RUNNER_DIR))

import run_dcode  # noqa: E402


DEFAULT_MODEL = "z-ai/glm-5.2"


if __name__ == "__main__":
    run_dcode.main(
        default_model=DEFAULT_MODEL,
        runner_name="glm",
        description="Execute prompts as the GLM seat through DeepAgents CLI (dcode) headless mode.",
    )
