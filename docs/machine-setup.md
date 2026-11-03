# Machine setup

Install the base tools, then only what your routes use. Runner usage lives in
the runner skills:
[`cli-runner`](../skills/engineering/seats/cli-runner/SKILL.md),
[`pi-runner`](../skills/engineering/seats/pi-runner/SKILL.md), and
[`muse-runner`](../skills/engineering/seats/muse-runner/SKILL.md). Model IDs
and effort live in [`model-routing.json`](../skills/shared/model-routing.json).

## 1. Base tools

| Tool | Check | Notes |
| --- | --- | --- |
| A skill host | Sign in | Allow workspace, subprocess, and network access. |
| Git | `git --version` | Set your name, email, and remote authentication. |
| Python 3.11+ | `python3 --version` | Runs the wrappers, validators, and checker. PyYAML is optional. |
| Node.js 24.x with npm | `node --version` | Needed for Pi and the npm browser tools. Pi needs Node 22.19.0 or newer. |
| Bash and Unix tools | `bash --version` | macOS, Linux, or WSL. Native Windows is not tested. |
| ripgrep (optional) | `rg --version` | `grep` and `find` work without it. |

Install the skills into a project from this checkout:

```sh
bash scripts/install-skills.sh /absolute/path/to/project [--layout agents|claude|both] [--copy]
```

The default is both layouts, as symlinks, so keep the checkout in place.
`--copy` makes a standalone copy. Entries with matching names are replaced.

## 2. Pi and Muse

**Pi** (`pi`) reaches gateway models such as Kimi and GLM.

```sh
npm install -g @earendil-works/pi-coding-agent@0.85.1
pi --version
```

- Version 0.85.1 or a newer stable release. Prereleases are rejected.
- Credentials: export `OPENROUTER_API_KEY` to the process that starts the host,
  or log in through Pi's `/login`. Missing credentials return `auth_missing`.
- Pi's agent directory (`~/.pi/agent`, or `PI_CODING_AGENT_DIR`) must be
  writable, including its credential lock.
- Zero-retention routing is set per request from `model-routing.json`; there is
  no global `ZDR` variable.

**Muse** (`muse`) serves the optional Muse Wonder Full implementation worker.
Install the Muse CLI and authenticate it with your subscription. Set
`MUSE_CLI_PATH` if `muse` is not on `PATH`. Preflight checks the CLI and the
workspace configuration without a model call; it does not check the login:

```sh
python3 skills/engineering/seats/muse-runner/scripts/run_muse.py --preflight --json
```

## 3. Browser tools

Install one driver for the work, plus a browser binary.

| Driver | Install | Use |
| --- | --- | --- |
| Playwright Test | The project's pinned `@playwright/test`, then `npx playwright install` | Repeatable E2E tests and CI. On Linux you may need `--with-deps`. |
| Playwright CLI | `npm install -g @playwright/cli` | Interactive exploration. Separate sessions with `PLAYWRIGHT_CLI_SESSION` or `-s=<name>`. |
| agent-browser | `npm install -g agent-browser@0.36.0`, then `agent-browser install` | Alternative interactive driver. Separate sessions with `AGENT_BROWSER_SESSION` or `--session <name>`. |
| Host browser tools | Enable them in the host | Logged-in sessions. Pi does not inherit them. |

Give each parallel worker its own session. A version check does not prove a
driver works: before using an external browser route, have the worker navigate,
interact, assert, and save a screenshot.

## 4. Model CLIs and other tools

| Tool | Used for | Authentication and notes |
| --- | --- | --- |
| `claude` | Claude routes in `cli-runner` | Log in with the CLI. |
| `codex` | GPT routes (Astra, Sol, Terra) in `cli-runner` | Log in with the CLI; a desktop app login does not cover it. |
| `agy` | Gemini routes in `cli-runner` | Log in to Antigravity CLI. The runner calls `agy`, not `gemini`. It reads `conversation_id`, `status`, and `response` from the JSON output and resumes with `--conversation <conversation_id>`. `agy` reports no serving model, so its results count as configured, not verified. |
| `grok` | Grok routes in `cli-runner` | `grok login`. |
| `pi`, `muse` | `pi-runner`, `muse-runner` | See section 2. |
| `gh` | Pull requests and PR feedback | `gh auth login`, then `gh auth status`. Git push needs its own authentication. |
| `cmux` | Visible peer sessions | Install the app and CLI, start the app, check `cmux ping`. |
| `jq` | The optional command guard | Without `jq` the guard lets every command through. |

## 5. Environment variables

Set only what your routes need. Keep secrets out of committed files and
`.rar-skills/config.local.yaml`.

| Variable | Meaning |
| --- | --- |
| `PATH` | Must expose `python3`, the CLIs, and the browser driver to the host's child processes. |
| `OPENROUTER_API_KEY` | Gateway key for Pi, unless Pi's login supplies it. |
| `PI_CODING_AGENT_DIR` | Optional custom Pi state directory. |
| `MUSE_CLI_PATH` | Optional path to the `muse` binary. |
| `GH_TOKEN` / `GITHUB_TOKEN`, `GH_HOST` | Optional alternatives to `gh auth login`, and the enterprise host. |
| `PLAYWRIGHT_CLI_SESSION` / `AGENT_BROWSER_SESSION` | One browser session per worker. |
| `CMUX_WORKSPACE_ID` / `CMUX_SURFACE_ID` | Set by cmux inside its sessions. Do not set them globally. |
| `RAR_GUARD_PATTERNS` | Optional pattern file for the command guard. |

Do not set `RAR_PI_RUN_CONFIG` or `RAR_PI_RUN_RECEIPT`; the Pi wrapper sets them
per run. A `.env` file is not loaded automatically, and a GUI host may miss
shell profile changes, so restart it after changing its environment.

Optional model preferences go in the project's `.rar-skills/config.local.yaml`
(keep it out of version control), as
[local-config.md](../skills/shared/references/local-config.md) describes.

## 6. Check

```sh
bash scripts/check-environment.sh
bash scripts/check-environment.sh --project /absolute/path/to/project --json
```

It reports `OK`, `MISSING`, and `WARN` with next steps. Flags: `--native-models` when the host supplies review and planning models,
`--browser agent-browser|playwright-cli|none`, and `--timeout <seconds>`. Exit
code `0` means nothing required is missing, `1` means something required is
missing, and `2` means invalid input. It installs nothing and calls no
provider, so it cannot prove a login or a browser works.

To see which runner CLIs are on `PATH`:

```sh
python3 skills/shared/scripts/discover_runners.py probe
```

A probe confirms a transport, not the serving model. In an installed project,
use `.agents/skills/shared/` for `skills/shared/`.
