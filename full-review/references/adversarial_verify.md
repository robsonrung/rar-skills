# Adversarial Verify Sub-Pass

Phase 4 already runs **execution-based verification** for runtime/security/perf findings that one or more seats raised. The adversarial-verify sub-pass adds a second check, aimed at a different failure mode: a finding that *looks* plausible, sits in a hot category, but was raised by **only one model** and cannot be cheaply reproduced by a probe.

It is a refute-by-default skeptic vote. It is cheap because it uses small fast seats (Kimi/GLM/Gemma), not the panel's reasoning seats.

## When It Runs

Trigger when **all** of the following hold:

1. The finding's `category` is one of: `security`, `correctness`, `reliability`, or `performance`.
2. The finding's severity after Phase 4 verification is `CRITICAL` or `HIGH`.
3. `corroborated_models == 1` (raised by exactly one model, in-house or external).
4. Phase 4 could not reproduce it (`verified` is absent or `false`, and no concrete refutation either).
5. The active triangulation preset is `light` or `quality` (skip in `off`).

Skip when:

- The finding is structural maintainability (those are evidence-checked, not refutable).
- The finding has `verified: true` from Phase 4.
- The finding has `verified: false` from Phase 4 — it is already dropped before this pass.

## Skeptic Pool

Pull two or three skeptics from the **cheap pool** (in priority order): `kimi`, `glm`, `gemma`, `qwen`, `minimax`. Skip any seat that originated the finding under test — a model cannot refute itself credibly.

Minimum: 2 skeptics. Preferred: 3 (odd number, no tie).

If the cheap pool cannot supply at least 2 distinct seats (skipping the originator), fall back in this order:
1. Use `sonnet` as a tiebreaker.
2. If still under 2 skeptics, mark the finding `adversarial_verify.verdict = "inconclusive"` and continue.

## Skeptic Prompt

Use the **Adversarial-Verify Skeptic Prompt** in `references/external_prompt_template.md`. Each skeptic gets:

- The finding under test as JSON.
- The diff slice the finding points at.
- ~30 lines of surrounding context around the cited location.

The same diff slice, surrounding context, tool profile, and budget go to every skeptic — identical conditions, like the Phase 3 seats. Each skeptic returns JSON with `refuted`, `rationale`, and `counter_evidence`.

## Verdict

Tally `refuted == true` votes across skeptics. Set `adversarial_verify` on the finding:

| Refuted count | Pool size | Verdict | Effect |
|---|---|---|---|
| ≥ majority | 2–3 | `refuted` | Drop the finding before Phase 5 confidence filter. Do not include in the output. |
| Below majority, ≥ 1 | 2–3 | `survived` | Keep the finding. Subtract `0.05` from confidence (one credible challenge raises uncertainty). |
| 0 | 2–3 | `survived` | Keep the finding. Add `+0.05` to confidence (skeptics could not break it). |
| Pool size < 2 | 0–1 | `inconclusive` | Keep the finding at original confidence. Note inconclusive verification in the report. |

Record on each surviving finding:

```json
"adversarial_verify": {
  "skeptics": ["kimi", "glm", "gemma"],
  "refuted_count": 1,
  "verdict": "survived",
  "rationale": "Two of three skeptics could not break the claim; one cited an upstream guard that does not in fact cover this path."
}
```

Refuted findings are dropped silently from the output — do not surface them. The synthesizer report still references the count in its "Adversarial-verify activity" section.

## Cost Posture

- Skeptics run in parallel for one finding.
- Findings are processed in parallel up to the host concurrency cap.
- Hard ceiling: at most **10 findings** enter adversarial verify per review. Beyond that, prioritize by severity then confidence, and note suppressed findings in the report.
- Token budget per skeptic: cheap (≈ default for the seat's runner). Do not raise budget for skeptics — the point is broad and fast.

## Failure Modes To Avoid

1. **Skeptic-as-author.** Never let the seat that originated the finding act as one of its own skeptics.
2. **Stacking the deck.** Never feed the skeptic the orchestrator's own analysis or the originating seat's rationale. They get the finding JSON + diff slice + surrounding context, period.
3. **Loop expansion.** One round only. Do not re-run skeptics on findings that survived.
4. **Silent drop.** Always record the verdict on surviving findings and count refuted findings in the report.
