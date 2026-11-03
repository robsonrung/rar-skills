# Model Calibration

Use this reference when judging instruction wording, migrating a skill to a newer model, or diagnosing a behavior a skill causes. Its observations come from vendor guidance checked on 2026-09-26 (sources below); re-check them when a routed model changes.

## Direction of change

Current frontier models, such as GPT-6 Astra, Claude Fable 5.x, and Claude Opus 5.x, follow instructions more literally and do more unasked than the models many skills were written for. A rule that compensated for an older model's weakness now over-steers. Remove or narrow it before adding a new rule.

| Older instruction | Effect on current models | Replace with |
| --- | --- | --- |
| "Be thorough", "if in doubt, use X" | Too many tool calls and too much exploration | When X helps: "Use X for schema questions." |
| "Verify", "double-check", "use a subagent to verify" | Cost without quality | The named contract check or repository gate |
| "Think carefully", "think step by step" | Redundant with effort, slower replies | Nothing; routing sets effort |
| "Explain your reasoning in the response" | Claude models can refuse it | A rationale field, if a consumer needs one |
| "Before every edit, read A, B, and C" | Loads context the task doesn't need | "Use A for service boundaries, B for schema changes." |
| "Only report high-severity issues" in a review | The model reports less, literally | Report all findings, then filter in a separate step |
| Anti-formatting rules, or "hold findings for the end" | Fable 5.1 already narrates less, so users see silence | Say when formatting or updates are wanted |
| All-caps NEVER or MUST with no reason | Applied rigidly, misapplied at the edges | The rule plus its reason |
| Approval gates on reversible local actions | Astra stops where the user expected progress | Grant it: "Run local tests without asking." |
| Remaining-context countdowns | Fable trims its work or proposes a new session | Omit them |

Keep a rule that protects authority, state, an output contract, or a safety boundary, even when it looks like a row above.

## What current models need stated

- **Completion.** Opus 5 tends to widen scope, Fable 5.1 adds unrequested extras, and Astra can stop early; a stated end condition reins in all three.
- **Scope boundary.** Unrequested fixes, extra tests, and new files go in the report as follow-ups, not into the change. A user describing a problem wants an assessment.
- **Precedence.** The user's explicit request beats a skill default, except for safety and authority boundaries. Current models follow a conflicting rule rather than ignore it, so resolve conflicts between layers where they live.
- **Delegation.** Delegate independent, sizeable, parallel work; never verification of your own work or a handful of tool calls. Opus 5 delegates readily, Astra less so, and Fable 5.1 does better when the lead keeps working while subagents run.
- **Length.** Opus 5 writes long documents by default; match the deliverable to the task.

## Where model-specific cues live

Skill bodies stay model-neutral, because several seats run them. A cue only one family needs (a bias-to-action line for Astra, continuation handling for unattended Opus 5.5 runs, progress updates from Fable 5.1) belongs in that model's runner or route, with its evidence, and only while evidence shows it helps. Effort lives in `shared/model-routing.json`.

## Diagnose a behavior

Rerun the case on the seat that showed it, in a fresh context with the same skill loaded, and ask:

```text
Name the file and quote the instruction that led you to <pause | ask | add X | skip Y>. If no instruction did, say so.
```

If it quotes an instruction, fix that owner: remove it, reword it with its reason, or resolve the conflict. If it cites none, the behavior is a model default: add one brief instruction with its reason at the owning layer, or a runner cue if only one family needs it. The answer is a lead, not proof; confirm the fix with a rerun.

## Sources

Index pages only, because exact model IDs belong in `shared/model-routing.json`.

- OpenAI, the developer blog post "Rethinking skills and prompts" for the Astra model (2026-09-05), and [Model guidance](https://developers.openai.com/api/docs/guides/latest-model).
- Anthropic, [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) and the model pages it links for Opus 5.5, Opus 5, Fable 5.1, and Fable 5.
