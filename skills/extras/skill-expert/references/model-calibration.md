# Model Calibration

The observations come from vendor guidance checked on 2026-09-26, and on 2026-11-10 for Fable 5.2; re-check them when a routed model changes.

## Direction of change

Current frontier models, such as GPT-6 Astra, Claude Fable 5.x, and Claude Opus 5.x, follow instructions more literally and do more unprompted than the models many skills were written for. A rule that compensated for an older model's weakness now over-steers. Remove or narrow it before adding a new one.

| Older instruction | Effect now | Replace with |
| --- | --- | --- |
| "Be thorough", "if in doubt, use X" | Too much exploration | When X helps: "Use X for schema questions." |
| "Verify", "double-check", "use a subagent to verify" | Cost without quality | The named contract check or repository gate |
| "Think carefully", "think step by step" | Redundant with effort | Nothing; routing sets effort |
| "Explain your reasoning in the response" | Claude models can refuse | A rationale field, if a consumer needs one |
| "Before every edit, read A, B, and C" | Loads unneeded context | "Use A for service boundaries, B for schema changes." |
| "Only report high-severity issues" in a review | Reports less, literally | Report all findings, then filter in a separate step |
| Anti-formatting rules, "hold findings for the end" | Fable 5.2 already writes little during long tool runs; users see silence | Say when formatting or updates are wanted |
| All-caps NEVER or MUST without a reason | Applied rigidly at the edges | The rule and its reason |
| Approval gates on reversible local actions | Astra stops where the user expected progress | "Run local tests without asking." |
| Remaining-context countdowns | Fable trims work or proposes a new session | Omit them |

Keep a rule that protects authority, state, an output contract, or a safety boundary, even when it looks like a row above.

## Model tendencies

A stated end condition steadies all three: Opus 5 widens scope and writes long documents, while Fable 5.2 and Astra can stop before the work is done. Fable 5.2 makes unrequested changes mainly when a prompt hands it ownership of the code. Opus 5 delegates readily, Astra less so, and Fable 5.2 when the prompt invites it. Current models follow a conflicting rule rather than ignore it, so a collision between layers needs a fix, not a hope.

Skill bodies stay model-neutral, because several seats run them. A cue only one family needs, such as a bias-to-action line for Astra or continuation handling for unattended Opus 5.5 runs, belongs in that model's runner or route with its evidence, and only while the evidence holds.

## Diagnose a behavior

Rerun the case on the seat that showed it, in a fresh context with the skill loaded, and ask:

```text
Name the file and quote the instruction that led you to <pause | ask | add X | skip Y>. If no instruction did, say so.
```

If the model quotes an instruction, fix that owner: remove it, reword it with its reason, or resolve the conflict. If it cites none, the behavior is a model default: add one brief instruction with its reason at the owning layer, or a runner cue when one family needs it. The answer is a lead, not proof; confirm the fix with a rerun.

## Sources

- OpenAI, the developer blog post "Rethinking skills and prompts" for Astra (2026-09-05), and [Model guidance](https://developers.openai.com/api/docs/guides/latest-model).
- Anthropic, [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) and the model pages it links for Opus 5.5, Opus 5, Fable 5.2, Fable 5.1, and Fable 5.
