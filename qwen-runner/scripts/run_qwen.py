#!/usr/bin/env python3
"""Execute prompts as the Qwen seat through Cline CLI headless mode.

The wrapper delegates to the shared ``cline-runner`` implementation and
forwards ``qwen/qwen3.8-max`` on every default run. The envelope reports
``runner=qwen`` and ``effective_runner=cline``.

Gemma and Minimax keep importing this module with their own model and runner
identity, so all three seats share the same Cline transport contract.
"""

import sys
from pathlib import Path


CLINE_RUNNER_DIR = Path(__file__).resolve().parents[2] / "cline-runner" / "scripts"
sys.path.insert(0, str(CLINE_RUNNER_DIR))

import run_cline  # noqa: E402


DEFAULT_MODEL = "qwen/qwen3.8-max"


def main(
    default_model: str = DEFAULT_MODEL,
    runner_name: str = "qwen",
    description: str | None = None,
) -> None:
    """Expose the shared entry point for the Gemma and Minimax shims."""
    run_cline.main(
        default_model=default_model,
        runner_name=runner_name,
        description=description
        or f"Execute prompts as the {runner_name} seat through Cline CLI headless mode.",
    )


if __name__ == "__main__":
    main()
