# Debate Protocol and Stance Rotation

Use only after the user approves a `debate` preview. The preview fixes the selected seats, their efforts, the moderator, and a ceiling of one to three rounds. Do not add a round or a seat after approval.

## Protocol

1. Send the neutral question and assigned stance to each opening seat. Do not show peer outputs.
2. The approved moderator produces an anonymized digest: agreements, disagreements, options, evidence gaps, and follow-up questions.
3. For each later approved round, send the digest and a new stance. Each seat must rebut, concede, refine, or integrate.
4. Classify the result as `full_agreement`, `converging`, `material_disagreement`, or `blocked_on_context`.
5. Return the recommended direction with the dissent and evidence gap. A ceiling hit remains a reported disagreement; it never grants another round.

Use `schemas/round1-response.schema.json` for the opening and `schemas/later-round-response.schema.json` later. Keep every digest anonymized. The moderator does not replace a failed seat.

## Stance rotation

| Seat | Round 1 | Round 2 | Round 3 |
| --- | --- | --- | --- |
| `astra` | `balanced_synthesis` | `critical_with_responsibility` | `pragmatic_engineering` |
| `fable` | `critical_with_responsibility` | `balanced_synthesis` | `pragmatic_engineering` |
| `grok` | `pragmatic_engineering` | `devils_advocate` | `balanced_synthesis` |
| `qwen` | `pragmatic_engineering` | `balanced_synthesis` | `critical_with_responsibility` |
| `opus` | `critical_with_responsibility` | `balanced_synthesis` | `pragmatic_engineering` |
| `gemini` | `balanced_synthesis` | `pragmatic_engineering` | `critical_with_responsibility` |
| `sonnet` | `supportive_with_integrity` | `critical_with_responsibility` | `balanced_synthesis` |
| `kimi` | `pragmatic_engineering` | `balanced_synthesis` | `critical_with_responsibility` |
| `glm` | `outsider_fresh_eyes` | `balanced_synthesis` | `critical_with_responsibility` |
| `gemma` | `supportive_with_integrity` | `critical_with_responsibility` | `balanced_synthesis` |
| `muse` | `pragmatic_engineering` | `devils_advocate` | `balanced_synthesis` |

For a panel smaller than six, the preview assigns each selected seat one distinct opening stance. Prefer `outsider_fresh_eyes` for a seat that receives no repository context. Do not create a duplicate seat to fill a missing stance.

## Read-only runner roles

| Stance | Runner role |
| --- | --- |
| `supportive_with_integrity` | `planner` |
| `critical_with_responsibility` | `codereviewer` |
| `balanced_synthesis` | `synthesizer` |
| `devils_advocate` | `adversarial` |
| `pragmatic_engineering` | `challenger` |
| `outsider_fresh_eyes` | `researcher` |

All roles remain read-only. Do not use an implementation role in a council.
