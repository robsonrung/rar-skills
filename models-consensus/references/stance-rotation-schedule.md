# Stance Rotation Schedule

Rotate stances across iterations to reduce model-position bias. The moderator applies this schedule per seat based on the round number.

## Round 1: Natural Stances

Each model starts in its natural role:

| Seat | Round 1 Stance | Runner Role |
|------|----------------|-------------|
| Claude Opus 4.8 | `critical_with_responsibility` | `codereviewer` or `adversarial` |
| Claude Sonnet 5 | `supportive_with_integrity` | `planner` or `implementer` |
| Codex | `devils_advocate` | `challenger` |
| Gemini | `balanced_synthesis` | `synthesizer` |
| Kimi | `pragmatic_engineering` | `implementer` |
| GLM | `pragmatic_engineering` | `implementer` |

The Runner Role column above is the canonical stance-to-runner-role mapping (`supportive_with_integrity` -> `planner` or `implementer`, `critical_with_responsibility` -> `codereviewer` or `adversarial`, `balanced_synthesis` -> `synthesizer`, `devils_advocate` -> `challenger`, `pragmatic_engineering` -> `implementer`, `outsider_fresh_eyes` -> `reviewer` with no repo context). For `blocked_on_context` investigation rounds, use the `researcher` runner role.

When 5 or more seats are available, reassign **GLM** to the `outsider_fresh_eyes` stance for Round 1 (give it the brief with repo glossary/ADR context stripped) so the panel always carries one curse-of-knowledge check — GLM is the deterministic pick because it otherwise duplicates Kimi's `pragmatic_engineering` coverage. If GLM is absent from the panel, reassign Kimi instead; if both are absent, reassign the lowest seat in the table that still leaves every other stance covered. With 4 or fewer seats, keep the natural-stance table above and reserve `outsider_fresh_eyes` for a later round only if no seat has surfaced a clarity/assumption objection.

## Round 2: Cross-Stance Pressure

Each seat adopts a stance that challenges its Round 1 position:

| Seat | Round 2 Stance | Purpose |
|------|----------------|---------|
| Claude Opus 4.8 | `balanced_synthesis` | Step back and weigh alternatives fairly |
| Claude Sonnet 5 | `critical_with_responsibility` | Stress-test the supportive position |
| Codex | `critical_with_responsibility` | Ground devil's advocacy in constructive critique |
| Gemini | `pragmatic_engineering` | Move from synthesis to actionable evaluation |
| Kimi | `balanced_synthesis` | Evaluate tradeoffs beyond implementation details |
| GLM | `balanced_synthesis` | Evaluate own pragmatism against alternatives |

## Round 3: Convergence / Integration

Final round focuses on integration or decisive critique:

| Seat | Round 3 Stance | Purpose |
|------|----------------|---------|
| Claude Opus 4.8 | `pragmatic_engineering` | Recommend specific implementation path |
| Claude Sonnet 5 | `balanced_synthesis` | Reconcile findings and recommend direction |
| Codex | `balanced_synthesis` | Synthesize objections into final assessment |
| Gemini | `critical_with_responsibility` | Final sanity check on consensus direction |
| Kimi | `critical_with_responsibility` | Identify last-mile risks in the leading option |
| GLM | `critical_with_responsibility` | Flag overlooked practical blockers |

## Fallback Rules

- If fewer than 3 seats are available, skip Round 3 and run only 2 rounds.
- If a seat's output in Round 1 already matches the Round 3 stance for that seat, keep the Round 2 assignment for Round 2 but shift Round 3 to `balanced_synthesis` to ensure the seat contributes to convergence.
- If the user explicitly pauses the council to provide direction, resume from the next round using the scheduled stance for that round number — do not restart the rotation.
