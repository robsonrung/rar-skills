#!/usr/bin/env python3
"""Execute prompts as the Gemma seat through the Pi CLI on OpenRouter.

Previously this wrapper delegated to the shared `cline-runner`, which resolved
the model through Cline's mutable provider state. It now delegates to the
shared `pi-runner` implementation, which pins `--provider openrouter --model
google/gemma-4-31b-it` per invocation — the Gemma seat served via OpenRouter
with credentials from `OPENROUTER_API_KEY`. The envelope reports
`runner=gemma`, `effective_runner=pi`, `effective_provider=google`.
"""

import sys
from pathlib import Path

PI_RUNNER_DIR = Path(__file__).resolve().parents[2] / "pi-runner" / "scripts"
sys.path.insert(0, str(PI_RUNNER_DIR))

import run_pi  # pyright: ignore[reportMissingImports] - sys.path is set at runtime above

DEFAULT_MODEL = "google/gemma-4-31b-it"


if __name__ == "__main__":
    run_pi.main(
        default_model=DEFAULT_MODEL,
        runner_name="gemma",
        description="Execute prompts as the Gemma seat through the Pi CLI on OpenRouter.",
    )
