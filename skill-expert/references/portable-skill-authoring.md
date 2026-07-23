# Portable Skill Authoring Across Models and Harnesses

Read this when creating or materially revising a skill that must work across models and agent harnesses, when reviewing skill prose for cross-model behavior or over-prompting, or when a skill names a model anywhere in its content.

Governing idea:

> Start with the outcome and intent. Add only the smallest protocol needed to protect that outcome across runtimes.

You always author from inside one model and one harness. Treat that runtime as one data point, not as the definition of how agents behave. This guide is not a template: a small skill may need only an outcome, a completion condition, and one boundary.

## Contents

1. [The model-tier abstraction](#the-model-tier-abstraction)
2. [Author in this order](#author-in-this-order)
3. [The portability problem](#the-portability-problem)
4. [Your model is not a neutral author](#your-model-is-not-a-neutral-author)
5. [Build around an outcome spine](#build-around-an-outcome-spine)
6. [Separate protocol from judgment](#separate-protocol-from-judgment)
7. [Preserve literal scope locally; define completion, not effort](#preserve-literal-scope-locally-define-completion-not-effort)
8. [Describe capabilities before tools](#describe-capabilities-before-tools)
9. [Make activation portable](#make-activation-portable)
10. [Make authority proportional to risk](#make-authority-proportional-to-risk)
11. [Load instructions when they can change behavior](#load-instructions-when-they-can-change-behavior)
12. [Evaluate proportionally](#evaluate-proportionally)
13. [Compact review prompt](#compact-review-prompt)

## The model-tier abstraction

Concrete model ids are the single largest source of repo-wide churn in skill collections: this repo's multi-model skills hardcode names like specific Opus, Sonnet, GPT, Kimi, and GLM versions across SKILL.md bodies, runner tables, and reference files, and every model generation forces a synchronized edit across all of them. A portable skill never hardcodes a model id into its workflow prose. Instead it declares **semantic cost tiers once** — in a single small block near the top of the skill or in one designated config/reference file — and every other line refers to tiers by name.

The three canonical tiers:

| Tier | Meaning | Typical work |
|---|---|---|
| **extraction** | The cheapest model capable of the mechanical step | Reading files, extracting fields, formatting, classification against a rubric, glob/grep triage |
| **generation** | A mid-tier model with solid drafting and bounded reasoning | Drafting sections, single-lens review, summarization with judgment, test writing |
| **ceiling** | The orchestrator's own model, **inherited by omission** | Synthesis, final decisions, cross-cutting review, anything ambiguous |

Rules:

- **Declare once, refer by name.** The tier block is the only place a concrete model id may appear, and even there prefer platform aliases (`haiku`/`sonnet`/`opus`-style capability names, a runner's default) over dated version strings. Workflow steps say "dispatch an extraction-tier subagent", never "dispatch claude-x-y-z".
- **Ceiling is expressed by omission.** Do not name a model for ceiling-tier work at all — omit the model parameter and the work inherits the orchestrator's own model, which is by definition the best one the user chose to run. Naming a "best" model pins yesterday's best.
- **A model generation change touches one block**, not every step, table, and reference in the skill — and ideally zero files, when tiers map to platform aliases.
- **Fallback rule:** when a platform cannot select models per agent or subagent, everything runs on the inherited model. The tier declaration then stops controlling spend, and cost control falls back to **read budgets** (cap which files and how many lines each step may read) and **output caps** (cap the length and shape of each step's output). Write those budgets into the step regardless, so the skill degrades to acceptable cost instead of silently running every mechanical step at ceiling price with unbounded context.

When auditing an existing skill, treat every inline model id outside a tier declaration as a defect of the same class as a hardcoded absolute path.

## Author in this order

| Layer | What belongs there | When to include it |
|---|---|---|
| Outcome spine | Result or decision, next consumer, done condition, non-obvious intent | Always first; a small skill may express it in one sentence |
| Hard protocol | Falsifiable scope, gates, state, evidence, coverage, authority, failure behavior | Only when omission can produce a wrong path or unsafe action |
| Load-bearing workflow | Sequence whose order materially changes correctness | Only for invariant ordering |
| Useful context | Domain facts, schemas, examples, specialist payloads, late routes | Conditionally, when it can change judgment |
| Adapters and techniques | Harness capability detection, verified tool adapters, path mechanics, optional methods | As defaults or heuristics, never as the portable core |

Prefer small units of weaker-model insurance: one threshold, enum, count, quantifier, or gate beside the action it protects — not a paragraph of defensive workflow. If a capable model's output gets worse after adding prose, remove judgment guidance and non-load-bearing steps first; do not respond to lost reasoning quality by stacking more protocol.

Every instruction must earn its cost. Keep a line when it adds falsifiable protocol, counters a demonstrated model or harness tendency, or supplies domain knowledge that can change a decision. Prefer an observable rule over a qualitative exhortation:

| Instead of | State what the instruction must change |
|---|---|
| "Be thorough." | "Check every changed execution path and report any path you could not verify." |
| "Produce high-quality work." | "The handoff must name the decision, evidence, unresolved risk, and next owner." |
| "Be concise." | "Lead with the outcome; omit details that would not change the reader's next decision." |

This is an admission principle, not a mandate to delete unfamiliar detail: a line that feels redundant may be targeted insurance for a more literal model. Test that possibility before removing it.

## The portability problem

A portable skill operates across two execution axes under one authority overlay:

1. **Model behavior** — how literally the model follows scope, how much structure it invents, how it handles ambiguity, effort, and delegation.
2. **Harness mechanics** — which tools, paths, permissions, delegation primitives, and loading behavior exist.
3. **Authority context** — system, harness, user, and project instructions constraining both axes.

Author against all three. Do not mistake behavior supplied by the current model or harness for behavior guaranteed by the skill.

## Your model is not a neutral author

Before changing a skill, state which model tier and harness you are using, then ask what that runtime may mask or exaggerate:

| Authoring reaction | Possible bias | Portability check |
|---|---|---|
| "This rule is redundant." | Your model supplies the behavior unprompted. | Does a more literal model still preserve the contract? |
| "This needs more steps." | Your runtime needs scaffolding another does not. | Is the step protocol, or compensation for this runtime? |
| "It worked in my test." | The harness supplied a tool, path, or permission. | What happens when that capability is absent? |
| "This mechanic is broken." | You recognized a familiar failure pattern. | Can you reproduce it, or is it already handled? |
| "This skill is missing X." | Review prompts bias toward additive findings. | What observable failure does X address? |

Decentering procedure: state the runtime; name likely masking effects; inspect the executed artifact (scripts, launchers, harness behavior); separate confirmed failures from verification tasks and plausible enhancements; test the smallest realistic behavioral floor before adding prose.

Classify guidance by strength — **invariant** (deviate only when it does not apply), **default** (override only with a concrete local fact, named consequence, substitute safeguard, and verification), **heuristic** (apply when useful). Local evidence may override general guidance; preference and convenience may not. If the same justified exception recurs, update the guide instead of multiplying local carve-outs.

## Build around an outcome spine

State before any workflow:

- **Result** — the artifact or decision the skill must produce.
- **Next consumer** — the user, agent, skill, or system that uses it next.
- **Done** — the observable completion condition.
- **Intent** — only the non-obvious reason that could change the approach.

Add other protocol fields only when they materially constrain the skill: authority when sources may conflict; boundaries when scope or mutation is risky; decision state when work persists or branches; act/ask rules when ambiguity can change scope; evidence rules when claims need provenance; coverage floors when missing a category silently makes the result incomplete; failure branches when a missing capability could cause a silent skip.

Split into multiple skills only when outcomes, triggers, authority domains, audiences, or lifecycles are independently meaningful. Do not reduce visible line count by creating a hidden cross-skill state machine.

## Separate protocol from judgment

For each prescriptive block ask: *if this instruction disappears, can the workflow produce a wrong path, state, count, gate, field, boundary, coverage floor, or handoff?* If yes it is **protocol** — keep it explicit and falsifiable. If removal mainly gives a capable model more freedom to reason, it is **judgment** — first try deleting it; if observed behavior shows it is needed, compress it to the smallest principle or contrast pair.

| Usually protocol | Usually judgment |
|---|---|
| Output paths and stable file shapes | Long menus of possible reasoning approaches |
| Stable fields, headings, enums | Several examples proving the same distinction |
| Ordering, state transitions, gates | Multi-paragraph rationale after a clear rule |
| Counts, thresholds, scope quantifiers | Generic quality exhortations |
| Permission and mutation boundaries | Step-by-step reasoning the model can choose itself |
| Required coverage categories | Creative menus that supply inspiration only |
| Failure and completion branches | Repetition without a demonstrated drift point |

A menu is not automatically judgment: if omitting one item silently drops required coverage, the menu is protocol. Decompose mixed blocks before classifying — preserve the invariant skeleton, fields, enums, and coverage; compress examples and rationale separately.

## Preserve literal scope locally; define completion, not effort

More literal models lose distant qualifiers. Keep scope beside the action it governs — "for each candidate separately", "return exactly three", "do not change files outside…", "stop after the first confirmed blocker" — rather than a general reminder elsewhere.

Avoid open-ended instructions ("continue until good"). Define observable completion: required artifact exists; mandatory fields populated; evidence recorded; each route ends in a result, routed action, required question, or blocker. Do not request hidden chain-of-thought; ask for decisions, evidence, assumptions, material rejected alternatives, and next actions.

## Describe capabilities before tools

A named tool should not become the portable contract unless its exact semantics are load-bearing. Write in this order:

1. State the required capability.
2. State the observable success contract.
3. State the acceptable degradation path.
4. Name verified tools only as adapters, short-circuits, or non-exhaustive examples.

Preserve the semantic floor: if every iteration requires fresh agent judgment, a shell loop that only repeats the outer command is not an equivalent fallback. Do not infer that a capability is unavailable from one missing binary, env var, or MCP server — check the harness's available interfaces and degrade explicitly. A user affordance such as a slash command is not necessarily agent-callable; do not instruct the model to use one unless the harness exposes it as callable.

For bundled-file paths and executed shell commands, follow the three-tier resolution rules in `references/authoring-contract.md`.

## Make activation portable

The name and description are an activation contract; a correct body is useless if it never runs.

- Describe the user-visible job and the situations that should route to the skill.
- Name the closest adjacent requests that belong elsewhere.
- Preserve deliberate invocation as a fallback when automatic routing is unavailable.
- Use capability language instead of one harness's command syntax; do not stuff workflow into frontmatter.

Evaluate activation separately from execution with a few positive triggers, adjacent negatives, and explicit invocations. A routing failure is not an execution failure.

Keep agent-to-agent routing capability-first: format formal skill names as inline code and invoke through the active harness's callable skill mechanism. Exact command spelling belongs only where the skill prints a user-runnable invocation; at that output seam default to `/skill-name`, render only the invocation as inline code, and output exactly one form.

## Make authority proportional to risk

Most read-only, single-shot, non-delegating skills need no authorization apparatus — skip it. For consequential workflows, distinguish the directly requested action, in-envelope actions necessary to complete it, actions outside the envelope, and higher-priority prohibitions invocation cannot erase. When invocation supplies authority, write the positive rule:

```text
Invoking this workflow authorizes the following in-envelope actions without
per-action confirmation: [...]. It does not authorize: [...].
```

For chained mutation workflows, carry authority as bounded data (target, permitted action classes, exclusions, user-direct vs inherited). Downstream skills may narrow inherited authority, never broaden it. A live user instruction can narrow or revoke the envelope at any time.

## Load instructions when they can change behavior

Always-loaded prose stays in context throughout the workflow. Keep the outcome spine, protocol kernel, and load-bearing route inline; move large schemas, specialist prompts, examples, and route-specific instructions to references. Keep the instruction to load the reference inline at the point of use, and do not inline a summary complete enough to suppress loading the authoritative reference. Pass large context to subagents by file path plus a short gist.

When delegating, each task needs a distinct scope, output contract, and synthesis owner. Use parallel work for genuinely independent questions, not as a reflex. Stable cross-skill fields, enums, and return statuses are protocols — version or parity-test them when independently evolving skills depend on exact agreement.

## Evaluate proportionally

Mechanical checks (frontmatter and schema validation, broken references and paths, duplicated-contract parity, stable fields and enums, script and fixture tests) belong in deterministic validation. Behavioral reasoning evals are best-effort local evidence, not a mandatory exhaustive matrix — use a small fixture pack targeted at the largest portability risks of the change.

Prioritize: (1) weakest realistic layer — does the minimum supported model or harness preserve the protocol; (2) strong-model regression — did added prose reduce reasoning quality or restraint; (3) restraint — does the agent avoid inventing defects, additions, or unrelated work; (4) fresh downstream consumer — can the next agent use the output without clarification; (5) activation — do positive and adjacent-negative prompts route correctly.

Use fresh context for behavioral evaluation — some harnesses cache skill content at session start, so invoking the edited skill in the authoring session may test stale content. For side-effecting skills, evaluate in layers: graded intent, fake boundaries or dry-run contracts, ephemeral external systems, and a live canary only when remaining risk justifies it. Read a tie honestly: if old and new prose both succeed on a strong model, the test shows no regression, not improvement. Measure the outcome the skill exists to improve, not proxy volume such as tool-call count.

## Compact review prompt

```text
Review or author this skill for portability across models and agent harnesses.

Start with the outcome spine: result, next consumer, done condition, and
non-obvious intent when it changes the approach. Add only the protocol needed
to protect that outcome.

1. State the current model tier and harness; name likely masking effects.
2. Diagnose before prescribing: a correctness fix needs a reproduced failure or
   necessary failing path; an addition needs an observable consequence, unmet
   consumer contract, or material risk. Otherwise return Verify or Consider.
3. Separate model behavior, harness mechanics, and authority context.
4. Treat the name and description as an activation contract.
5. Keep protocol explicit; delete judgment guidance when the outcome is enough.
6. Preserve local quantifiers, gates, stable fields, coverage floors, and
   completion branches.
7. Describe capabilities before named tools; define degradation.
8. Refer to models only through declared semantic tiers (extraction /
   generation / ceiling-by-omission); flag every inline model id.
9. Add authority machinery only when the skill mutates or delegates
   consequential work.
10. Choose the smallest supported change and record material deviations.

Return the outcome spine, proposed skill or findings, Change/Verify/Consider
findings, targeted tests, and unresolved contract-changing decisions.
```

---

*Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
