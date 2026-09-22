# Machine setup checklist

Checked against this repository on 20 September 2026. Install the base tools and
the tools for the routes you select. Optional runners are not required for every
skill. This checklist does not install software or change credentials.

## 1. Base tools

| Item | Required for | Configuration or check |
| --- | --- | --- |
| Compatible skill host | Reading skills, running commands and coordinating work | Sign in. Permit the required workspace, subprocess and network access. Confirm the selected models and tools are available. |
| Git | Worktrees, source evidence, commits and delivery | `git --version`; configure your commit name and email; configure SSH or HTTPS authentication for the remote. |
| Python 3.11 or newer | Workflow controllers, runner wrappers and validators | `python3 --version`. Use 3.11+ for the standard TOML parser used by artifact validation. |
| Node.js 24.x with npm/npx | Pi and npm-distributed browser tools | `node --version`; `npm --version`. The verified Pi package requires Node >=22.19.0; Node 24.x is the setup baseline. |
| Bash and standard Unix tools | Installation, command guards and shell helpers | `bash --version`. Use macOS, Linux or a compatible WSL environment; native Windows execution is not verified here. |
| ripgrep (optional) | Faster repository searches | `rg --version`. Use `grep` and `find` if it is absent. |
| Repository runtime and package manager | Building and testing the target application | Follow the target repository's lockfile and setup instructions. Node, Python, Java, databases or containers depend on that application. |
| Skill collection, including `shared/` | All collection workflows | Install the skill directories and shared scripts together. Keep copied installations updated. |

Most bundled Python helpers use the standard library and modules shipped in the
collection. PyYAML is optional for more complete frontmatter validation. It is
not required for ordinary skill execution. If maintaining skills, install it in
your development virtual environment with `python3 -m pip install PyYAML`.

From a checkout of this collection, install into a target repository:

```sh
bash scripts/install-skills.sh /absolute/path/to/project --layout agents
```

Use `--layout claude` for that host's project layout, or `--layout both` for both
layouts. The default is both. The installer creates individual symlinks; keep the
source checkout at its current path. Add `--copy` for a self-contained copy that
must be updated separately. It replaces existing entries with matching names, so
preserve any local edits before running it.

## 2. Economy model execution

| Item | Required setup |
| --- | --- |
| Pi CLI | Install `@earendil-works/pi-coding-agent` version 0.85.1 or newer. The checker and runner use the same minimum. |
| OpenRouter account | Configure a valid key and sufficient account access or credit for the selected models. |
| Provider credential | Export `OPENROUTER_API_KEY` into the process that starts the host and workers, or authenticate the gateway in Pi through `/login`. |
| Review and planning models | Make the selected central routes available through native host delegation or their authenticated runner. Economy still uses independent review and stronger planning/risk roles. Pi alone does not provide every default role. |
| Credential storage | Pi's agent directory must be writable, including the credential-store lock. An environment key does not remove that lock requirement. |
| Network access | Permit the selected gateway over HTTPS and local browser/server connections when needed. |

```sh
npm install -g @earendil-works/pi-coding-agent@0.85.1
pi --version
```

The minimum Pi version is `0.85.1`. Newer stable releases are accepted.
Prerelease versions are not accepted. The runner still requires the request hook
to confirm readiness before sending task content. Model IDs and effort defaults remain in
[`model-routing.json`](../skills/shared/model-routing.json).

The strict route passes ZDR, denied data collection and required parameter
support in each request. These are routing fields, not environment variables.
There is no collection-wide `ZDR=true` setting. Do not redirect the gateway in a
custom model registry. Strict execution checks both model and resolved credential
destinations. A full session stops before unprotected compaction.

## 3. Browser tools

Install the mechanism selected for the work. A browser binary is also required;
an installed JavaScript package alone is insufficient.

| Mechanism | Install/configure | Use |
| --- | --- | --- |
| Playwright Test | Use the target project's pinned `@playwright/test`, configuration and browser binaries | Repeatable E2E tests and CI. Run the existing suite directly. |
| Playwright CLI | `npm install -g @playwright/cli`; run `playwright-cli --help` and its documented browser setup | Interactive exploration and test authoring through shell access. Install its instructions with `playwright-cli install --skills` when wanted. |
| agent-browser | `npm install -g agent-browser@0.36.0`, then `agent-browser install` | Alternative interactive driver. Version 0.36.0 passed the local collection checks. |
| Playwright MCP | Configure the server in the selected host only when its structured tool interface is needed | Optional. It is not required for CLI operation or the test runner. |
| Native host browser | Enable the host's browser tools and required operating-system permissions | Existing authenticated sessions or capabilities unavailable to an external worker. Pi does not inherit these tools. |

For an existing Playwright project, restore its locked dependencies first, then
install the browsers required by its configuration:

```sh
npx playwright install
npx playwright test
```

On supported Linux systems, browser libraries may require
`npx playwright install --with-deps`. For a new suite, add Playwright Test through
the project's normal dependency process. Do not reinitialize an existing suite.
See the official [Playwright setup](https://playwright.dev/docs/intro).

Use separate sessions for parallel workers. Playwright CLI accepts
`PLAYWRIGHT_CLI_SESSION` or `-s=<name>`;
[its documentation](https://github.com/microsoft/playwright-cli) describes setup
and session controls. agent-browser accepts `AGENT_BROWSER_SESSION` or
`--session <name>`; load its matching instructions with
`agent-browser skills get core`. See the official
[agent-browser setup](https://github.com/vercel-labs/agent-browser).

Before accepting an external browser route, capture navigation, state inspection,
interaction, assertions and screenshot evidence from the worker environment.
The shared preflight helper records and verifies those observations; it does not
perform them. Version output alone is not proof of readiness. Keep the application
server running and supply test accounts, seed data and a writable artifact path.
Application URLs and login settings use the application's own variable names;
there is no universal collection `BASE_URL` or test-password variable.

## 4. Optional tools by workflow

| Tool | When needed | Authentication/configuration |
| --- | --- | --- |
| `codex` | Selected external review, planning or implementation routes that use this runner | Authenticate the CLI and confirm access to the exact selected model. A desktop login is not assumed to authenticate a separate CLI. |
| `claude` | Selected routes using this runner | CLI login, or the supported credential variables below. |
| `agy` | The `gemini-runner` route | Authenticate Antigravity CLI and select the model there. This adapter uses `agy`, not the `gemini` command; its `--model` argument does not change the serving model. |
| `grok` | Explicit Grok routes | Configure the CLI through `grok login`. |
| `gh` | GitHub PR creation, PR feedback and remote review context | `gh auth login`, then `gh auth status`, or a suitable token. Git push authentication is a separate requirement. |
| `cmux` | Visible peer sessions or direct cmux control | Install the app and CLI, start the app, and verify `cmux ping`. It is not required for ordinary native delegation. |
| `jq` | The optional shell command guard | `jq --version`. Without it, the current guard exits without checking commands. Install and test it if enabling that guard. |
| HTML-capable browser | Viewing generated reports | Open the generated local HTML. Diagram renderers or CDN assets may need network access when an artifact uses them. |

Knowledge graph storage, application databases, Docker and other specialist
services depend on the requested project. They are not general prerequisites for
loading this collection. Desktop task/sidebar controls require a host that
exposes those controls; installing a model CLI does not add them.

## 5. Environment and local settings

Set only the variables needed for the selected route. Use a secret manager or the
CLI's credential store. Do not put secrets in committed files, model plans or
`.rar-skills/config.local.yaml`.

| Variable | Required? | Meaning |
| --- | --- | --- |
| `PATH` | Yes | Must expose `python3`, required CLIs and the selected browser driver to the host's child processes. |
| `OPENROUTER_API_KEY` | For gateway calls unless Pi login supplies credentials | Gateway API key. No separate vendor key is needed for GLM through this gateway. |
| `PI_CODING_AGENT_DIR` | Optional | Custom Pi state directory. Leave unset for the normal `~/.pi/agent` location. If set, ensure its configuration, credentials and locks work. |
| `CLAUDE_CODE_OAUTH_TOKEN` | Optional, Claude routes | OAuth token supported by the runner. Normal CLI login is another option. |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` | Conditional, Claude routes | Explicit credentials required by the wrapper's bare mode. They are not required for Pi gateway routes. |
| `GH_TOKEN` / `GITHUB_TOKEN` | Optional alternative to GitHub CLI login | Token for GitHub operations; `GH_TOKEN` takes precedence. |
| `GH_HOST` / `GH_ENTERPRISE_TOKEN` | Conditional | Enterprise hostname and token when using that service. |
| `AGY_CLI_PATH` | Optional | Override the `agy` executable path. |
| `PLAYWRIGHT_CLI_SESSION` / `AGENT_BROWSER_SESSION` | Per browser worker | Separate browser sessions. Prefer explicit per-run names. |
| `CMUX_WORKSPACE_ID` / `CMUX_SURFACE_ID` | Only inside applicable cmux sessions | Runtime context. Do not reuse another session's IDs as global defaults. |
| `RAR_GUARD_PATTERNS` | Optional | Custom pattern file for the command guard. |
| `RUNNER_BASE_PATH` | Optional legacy panel configuration | Alternate runner root for `panel_round.py`; normally leave unset. This is not a model-profile setting. |

`RAR_PI_RUN_CONFIG` and `RAR_PI_RUN_RECEIPT` are private per-run variables created
by the wrapper. Do not configure them in the user's shell.

A `.env` file is not automatically loaded by every runner. Export credentials
through a trusted launcher or use the selected CLI's login. A GUI host may not
inherit terminal shell changes. Confirm variable presence inside the actual host
without printing the value, then restart that host if its launch environment
must change.

Optional model preferences, in the target project:

```yaml
# .rar-skills/config.local.yaml
profile: economy
seats:
  preferred: []
  excluded: []
```

Create the parent directory if needed and keep the file out of version control.
This changes preview preferences only. Explicit user choices win, and approved
run snapshots remain unchanged. See the [local configuration contract](../skills/shared/references/local-config.md).

## 6. Final readiness checks

Run the local environment checker from this collection checkout:

```sh
bash scripts/check-environment.sh
bash scripts/check-environment.sh --project /absolute/path/to/project --json
```

The shell entry point checks for Python 3.11+ before starting the Python
checker. It reports `OK`, `MISSING` and `WARN`, with required and optional checks shown
separately. The text report lists required next steps in order, with install
commands, login instructions and checks. Optional steps apply only to tools your
task needs. The final command repeats the check with your project, browser,
model access and timeout options. Run it from the host environment after setup.
If Python is missing or too old, the shell entry point shows how to install it
and repeat the check. The JSON format retains its existing fields and includes the
setup instructions in each check's `action` field. Checks that require manual
verification have `manual: true` and appear in a separate text section. Repeating
the checker does not verify login or browser behavior. A writable Pi state
directory passes its local permission check without repeated repair steps.
In automatic browser mode, one working driver is enough; instructions use that
driver. Version probe warnings distinguish a timeout from an execution failure.

It checks the Economy prerequisites by default. Use `--native-models`
when the host supplies review and planning models instead of the external CLI.
Use `--browser agent-browser` or `--browser playwright-cli` to require a specific
driver, or `--browser none` for work without browser checks. Set `--timeout 5`
to bound each version command.

Exit codes: `0` means no required prerequisite is known to be missing, `1` means
a required prerequisite is missing or unsupported, and `2` means invalid input
or a configuration inspection error. Warnings can remain with exit code `0`;
check the JSON summary before interpreting the result as readiness. The report
describes the current process environment, including its sandbox permissions.

The script does not install software, launch browsers, read credential values
from files, perform logins or call a provider. It runs version commands, which
may use the tool's own caches. Optional runner checks inspect PATH only. Environment
keys are checked for presence without displaying their values. Authentication,
account access and actual browser behavior require separate checks.

From the collection checkout:

```sh
python3 --version
node --version
npm --version
git --version
rg --version
pi --version
python3 skills/shared/scripts/discover_runners.py probe --seat glm --seat luna --seat sol --seat astra
python3 skills/shared/scripts/model_routing.py resolve routine-implementation --profile default
```

In a flat project installation, replace `skills/shared/` with
`.agents/skills/shared/` or the actual installed shared path. A CLI probe confirms
transport availability, not credentials, model access, browser readiness or an
inference host. Confirm native model access separately when that is the selected
transport. A live model check incurs provider usage and should be part of an
explicitly selected run.

Verify the chosen browser can open the target, inspect current state, interact,
assert a result and save evidence. Verify the application test command and the
required remote authentication. No global installation, environment change or
paid validation call is performed by reading this checklist.
