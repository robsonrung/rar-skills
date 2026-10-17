---
name: muse-runner
description: Run Muse Wonder Full through its native CLI for an explicit request or an approved optional implementation route. The Pi Muse Spark seat stays separate.
---

# Muse Runner

Run `scripts/run_muse.py` for one bounded turn. Use `--help` for the command
surface. The exact seat is `models.muse-wonder-full` in `shared/model-routing.json`.
It is an optional implementation worker. On 16 October 2026, the user confirmed
ZDR coverage for the current Muse Code subscription. This is account scoped user
evidence, not independent vendor verification or coverage for other users. A
different account needs its own coverage confirmation. Contributor mode is off
for every call. This setting alone does not prove zero retention.
Use live calls only within the user's approved scope for sharing source content.

First run `--preflight --json`. This checks the tested CLI version, startup
configuration, and local model profile without inference. It does not prove
account access. An unsupported version or profile blocks execution. There is no
fallback. The installer discovers this skill in the normal flat installation.
Use the installed `muse` command; `MUSE_CLI_PATH` can select an explicit binary.

Analysis uses a native read only profile, read tools, and no shell. Roles do not
implicitly grant write permission. Use `--allow-write` for authorized file edits.
Add `--allow-shell` only for authorized implementation and test commands. Shell
commands use Muse's sandbox with network access restricted. Per run settings
select a bounded profile; explicit launch flags disable approval prompts and the
approval judge. A sandbox failure blocks the command. Never remove the sandbox
to recover a failed call.

Delegation, observers, web tools, artifact tools, session messaging, and parallel
tool calls are disabled. Startup hooks, configured plugins, and MCP servers block
the adapter because they can execute outside its tool list. Shell permission can
start external programs, so it does not enforce a ban on nested workers. Keep the
single worker constraint in the task prompt when using shell commands.

Use a positive `--timeout` and `--max-steps`. The timeout kills the process group.
Native step exhaustion is a failed result. Sessions are not retained; there is no
persistent resume interface. `--background` uses shared `runner_jobs.py` status,
result, wait, and cancel operations. Cancellation terminates the native process
group. The implementation launcher enables `--allow-write --allow-shell` and
`--require-model-receipt`. It preserves the selected profile reviewer. Use the
existing role override `--role implementer=muse-wonder-full:high` when resolving
a profile. A resume request blocks before launch. A new context requires an
explicit recorded recovery reason and the full approved task context. The parent
runs verification after file-only edits.

Read `agent_message` from the JSON envelope. A completed turn does not establish
that tests passed. A provider completion record can verify the serving model
when it belongs to a linked, completed root model task in the same run. The
envelope retains the provider request and response IDs in `provider_model_receipts`.
Every completed root model task must have a valid receipt for overall verification.
`model_receipt_coverage` lists completed tasks and tasks with missing evidence.
Requested and configured labels are never serving proof. Without that evidence,
`effective_model` stays null and `model_receipt.status` stays `unverified`.
A different serving model or multiple primary model IDs fail the result.
Every live Meta call requires a matching verified receipt. Workflow dispatch
also binds the approved subscription evidence. Serving evidence does not
establish account privacy.

For a deterministic transport check, use `--provider echo`. It makes no model
request. Its provider is `echo`, its configured model is null, and authentication
remains untested. It cannot prove live tool use, entitlement, privacy, or quality.

The CLI contract was checked against Muse 1.4.7 (1.4.7-R6101.1). See
[headless operation](https://dev.meta.ai/docs/muse-code/extending),
[permission profiles](https://dev.meta.ai/docs/muse-code/permissions), and the
[Muse Wonder model ID](https://dev.meta.ai/models/muse-wonder).
