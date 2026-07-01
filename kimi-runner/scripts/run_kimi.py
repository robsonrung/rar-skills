#!/usr/bin/env python3
"""Execute prompts as the Kimi seat through Cline CLI headless mode.

Previously this wrapper called a dedicated `kimi-cli` binary directly. It now
delegates to the shared `cline-runner` implementation with a real forwarded
model: `--model moonshotai/kimi-k2.7-code` — the premium Kimi K2.7 Code seat
(best for MVP implementation, minimal diffs, fast coding, small focused
patches) — is passed straight through to `cline`, which resolves it via
whichever Cline provider the user has authenticated. The envelope reports
`runner=kimi`, `effective_runner=cline`.
"""

import sys
from pathlib import Path


CLINE_RUNNER_DIR = Path(__file__).resolve().parents[2] / "cline-runner" / "scripts"
sys.path.insert(0, str(CLINE_RUNNER_DIR))

import run_cline  # noqa: E402


DEFAULT_MODEL = "moonshotai/kimi-k2.7-code"


if __name__ == "__main__":
    run_cline.main(
        default_model=DEFAULT_MODEL,
        runner_name="kimi",
        description="Execute prompts as the Kimi seat through Cline CLI headless mode.",
    )
