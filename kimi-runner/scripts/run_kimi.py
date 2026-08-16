#!/usr/bin/env python3
"""Execute prompts as the Kimi seat through the Pi CLI on OpenRouter.

Previously this wrapper delegated to the shared `cline-runner`, which resolved
the model through Cline's mutable provider state (and once routed it to a
local LM Studio server as a result). It now delegates to the shared
`pi-runner` implementation, which pins `--provider openrouter --model
moonshotai/kimi-k3` per invocation — Moonshot's flagship Kimi K3 seat
(long-horizon coding, large-codebase understanding, 1M-token context,
always-on thinking) served via OpenRouter with credentials from
`OPENROUTER_API_KEY`. The envelope reports `runner=kimi`,
`effective_runner=pi`, `effective_provider=moonshotai`.
"""

import sys
from pathlib import Path

PI_RUNNER_DIR = Path(__file__).resolve().parents[2] / "pi-runner" / "scripts"
sys.path.insert(0, str(PI_RUNNER_DIR))

import run_pi  # pyright: ignore[reportMissingImports] - sys.path is set at runtime above

DEFAULT_MODEL = "moonshotai/kimi-k3"


if __name__ == "__main__":
    run_pi.main(
        default_model=DEFAULT_MODEL,
        runner_name="kimi",
        description="Execute prompts as the Kimi seat through the Pi CLI on OpenRouter.",
    )
