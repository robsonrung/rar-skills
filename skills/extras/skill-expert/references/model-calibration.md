# Model Calibration

Use this reference when judging instruction wording, migrating a skill to a newer model, or diagnosing a behavior a skill causes. Its model observations come from vendor guidance checked on 2026-09-26 (sources below). Re-check them when a routed model changes.

## Direction of change

Current frontier models, such as GPT-6 Astra, Claude Fable 5.x, and Claude Opus 5.x, follow instructions more literally and do more without being asked than the models many skills were written for. A rule that compensated for an older model's weakness now tends to over-steer. Remove or narrow it before adding a new rule.

## Remove or replace

| Older instruction | Effect on current models | Replace with |
| --- | --- | --- |
| "Be thorough", "if in doubt, use X", "default to X" | Too many tool calls and too much exploration | When X helps: "Use X for schema questions." |
| "Verify", "double-check", "use a subagent to verify" | Over-verification that adds cost and not quality | The named contract check or repository gate |
| "Think carefully", "think step by step" | Redundant with effort, and slows replies | Nothing. Effort is set by routing. |
| "Explain your reasoning in the response" | Current Claude models can refuse it (`reasoning_extraction`) | A rationale field, if a consumer needs one |
| "Before every edit, read A, B, and C" | Loads context the task does not need | "Use A for service boundaries, B for schema changes." |
| "Only report high-severity issues" in a review | The model reports less, literally | Report all findings, then filter in a separate step |
| Anti-formatting rules, or "hold all findings for the end" | Fable 5.1 already formats and narrates less, so users see silence | State when formatting or updates are wanted |
| All-caps NEVER or MUST with no reason | Applied rigidly and misapplied at the edges | The rule plus its reason |
| A list naming every variant of an unwanted behavior | Unneeded, because one principle generalizes | One sentence, plus one positive example if format matters |
| Approval gates on reversible local actions | Astra stops where the user expected progress | Grant it: "Run local tests with disposable fixtures without asking." |
| Remaining-context countdowns | Fable trims its work or proposes a new session | Omit them |

Keep a rule that protects authority, state, an output contract, or a real safety boundary, even if it looks like an item above.

## State what current models need

- **Purpose.** One sentence on why the work matters and who uses the result, so the model can make the small judgment calls itself.
- **Completion.** The result, what counts as finished, and what to do when one part is blocked: finish the rest and report the gap. Opus 5 tends to widen scope, Fable 5.1 adds unrequested extras, and Astra can stop early. A stated end condition reins in all three.
- **Scope boundary.** Unrequested fixes, extra committed tests, and new files go into the report as follow-ups rather than into the change. If the user is describing a problem rather than requesting a change, the deliverable is an assessment.
- **Precedence.** When a skill default and the user's explicit request differ, the request wins, except for safety and authority boundaries.
- **Delegation criteria**, for skills that orchestrate. Delegate independent, sizeable, parallel work. Do not delegate verification of your own work, or work that takes a handful of tool calls. Opus 5 delegates readily, Astra less so, and Fable 5.1 does better when the lead agent keeps working while subagents run.
- **Deliverable length.** Match written documents to the task, with no filler sections. Opus 5 writes longer documents by default.
- **Final report.** Lead with the outcome. Base each claim on a tool result from the session and name anything unverified. Write for a reader who did not watch the run.

## Where model-specific cues live

Skills in this collection run on several seats, so keep skill bodies model-neutral. A cue that only one family needs belongs in the runner or route that dispatches that model, together with its evidence. Examples are a bias-to-action line for Astra, continuation handling for unattended Opus 5.5 runs, or a request for progress updates from Fable 5.1. Effort belongs in `shared/model-routing.json`, not in prose. Keep a cue only while evidence shows it still helps.

Removing guidance can leave a smaller seat under-guided. Test a trimmed skill on the weakest seat that routes to it, as [evaluation.md](evaluation.md) describes.

## Diagnose a behavior

Rerun the case on the seat that showed the behavior, in a fresh context with the same skill loaded, and ask:

```text
Name the file and quote the instruction that led you to <pause | ask | add X | skip Y>. If no instruction did, say so.
```

If it quotes an instruction, fix that owner: remove it, reword it with its reason, or resolve the conflict between layers. If it cites none, the behavior is a model default. Add one brief instruction with its reason at the owning layer, or add a runner cue if only one model family needs it. Treat the answer as a lead, not as proof, and confirm the fix with a rerun.

## Sources

Links point to index pages because exact model IDs belong only in `shared/model-routing.json`.

- OpenAI, the developer blog post "Rethinking skills and prompts" for the Astra model (2026-09-05), and [Model guidance](https://developers.openai.com/api/docs/guides/latest-model) for the current model.
- Anthropic, [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) and the model pages it links for Opus 5.5, Opus 5, Fable 5.1, and Fable 5.
