#!/usr/bin/env python3
"""Execute prompts as the Qwen seat through the Pi CLI on OpenRouter.

Previously this wrapper delegated to the shared `cline-runner`, which resolved
the model through Cline's mutable provider state. It now delegates to the
shared `pi-runner` implementation, which pins `--provider openrouter --model
qwen/qwen3.8-2.4t-a95b` per invocation — the Qwen3.8 27B seat (256K-token context)
served via OpenRouter with credentials from `OPENROUTER_API_KEY`. The
envelope reports `runner=qwen`, `effective_runner=pi`,
`effective_provider=qwen`.

Gemma and Minimax remain Cline-backed; they delegate to `cline-runner`
directly with their own model and runner identity.
"""

import sys
from pathlib import Path

PI_RUNNER_DIR = Path(__file__).resolve().parents[2] / "pi-runner" / "scripts"
sys.path.insert(0, str(PI_RUNNER_DIR))

import run_pi  # pyright: ignore[reportMissingImports] - sys.path is set at runtime above

DEFAULT_MODEL = "qwen/qwen3.8-2.4t-a95b"


if __name__ == "__main__":
    run_pi.main(
        default_model=DEFAULT_MODEL,
        runner_name="qwen",
        description="Execute prompts as the Qwen seat through the Pi CLI on OpenRouter.",
    )
