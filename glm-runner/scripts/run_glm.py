#!/usr/bin/env python3
"""Execute prompts as the GLM seat through the Pi CLI on OpenRouter.

Previously this wrapper delegated to the shared `cline-runner` and carried a
per-provider model-id map because Cline providers did not share one Z.AI
namespace (`z-ai/glm-5.2` on OpenRouter vs `zai/glm-5.2` on the cline
gateway). It now delegates to the shared `pi-runner` implementation, which
pins `--provider openrouter --model z-ai/glm-5.2` per invocation, so the
single OpenRouter id is the only one left. Credentials come from
`OPENROUTER_API_KEY`. The envelope reports `runner=glm`,
`effective_runner=pi`, `effective_provider=z-ai`.
"""

import sys
from pathlib import Path

PI_RUNNER_DIR = Path(__file__).resolve().parents[2] / "pi-runner" / "scripts"
sys.path.insert(0, str(PI_RUNNER_DIR))

import run_pi

DEFAULT_MODEL = "z-ai/glm-5.2"


if __name__ == "__main__":
    run_pi.main(
        default_model=DEFAULT_MODEL,
        runner_name="glm",
        description="Execute prompts as the GLM seat through the Pi CLI on OpenRouter.",
    )
