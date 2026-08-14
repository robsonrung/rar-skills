#!/usr/bin/env python3
"""Execute prompts as the GLM seat through Cline CLI headless mode.

Unlike the previous dcode-backed shim, the GLM identity here is a *real*
forwarded model: a genuine Z.AI GLM id is passed straight through to `cline`
as `--model`. Cline providers do not share one model-id namespace for Z.AI —
the OpenRouter catalog lists GLM under the hyphenated org slug
(`z-ai/glm-5.2`), while the cline/cline-pass gateway uses `zai/glm-5.2` — so
the shim picks the id that matches the provider that will actually serve the
run: an explicit `--provider` flag first, else cline's persisted
`lastUsedProvider`. The envelope reports `runner=glm`, `effective_runner=cline`.
"""

import sys
from pathlib import Path

CLINE_RUNNER_DIR = Path(__file__).resolve().parents[2] / "cline-runner" / "scripts"
sys.path.insert(0, str(CLINE_RUNNER_DIR))

import run_cline

DEFAULT_MODEL = "zai/glm-5.2"
DEFAULT_MODEL_BY_PROVIDER = {
    "openrouter": "z-ai/glm-5.2",
    "cline": "zai/glm-5.2",
    "cline-pass": "zai/glm-5.2",
    "*": "zai/glm-5.2",
}


if __name__ == "__main__":
    run_cline.main(
        default_model=DEFAULT_MODEL,
        runner_name="glm",
        description="Execute prompts as the GLM seat through Cline CLI headless mode.",
        default_model_by_provider=DEFAULT_MODEL_BY_PROVIDER,
    )
