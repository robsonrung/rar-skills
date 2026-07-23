---
name: to-tasks
description: Break an approved plan, spec, or PRD into autonomously executable tasks — tracer-bullet vertical slices that each carry a machine-checkable acceptance contract and design/security gate flags, so an agent can complete them without asking the user anything. Use when the user wants to break a plan into tasks, convert a spec or PRD into a work queue, create implementation tasks for autonomous agents, or when a pipeline planning phase needs the task breakdown. Preferred over to-issues whenever tasks will be executed autonomously; use plain to-issues only for human-executed tickets without contracts.
---

# To Tasks

Break a plan into independently-grabbable tasks using vertical slices (tracer bullets). Every task carries a Slice Contract — machine-checkable acceptance plus gate flags — so the user approves the breakdown once and is never asked anything afterwards.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (issue number, URL, or path to a PRD/spec), fetch and read its full body and comments.

### 2. Explore the codebase

If you have not already explored the codebase, do so. Task titles and descriptions should use the project's domain glossary vocabulary (`CONTEXT.md`) and respect ADRs in the area being touched. Also identify the repo's real verification commands (test, lint, build, typecheck) — the acceptance contracts below must use commands that actually exist.

### 3. Draft vertical slices

Break the plan into **tracer bullet** tasks. Each task is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
</vertical-slice-rules>

Assign each slice a stable ID (`T1`, `T2`, …) at draft time. **IDs are never renumbered.** Reordering leaves IDs in place (T1, T3, T5 in their new order is correct; renumbering to T1, T2, T3 is not). Splitting keeps the original ID on the original concept and gives the new slice the next unused number. Deleting leaves a gap — gaps are fine. Executors and "Blocked by" references cite slices by T-ID, so the IDs must survive every later reorder, split, or delete of the breakdown.

Classify each slice **HITL** or **AFK**. HITL slices require human interaction — irreversible migrations, externally visible contract sign-off, design approval. AFK slices run unattended. Prefer AFK; schedule HITL slices first so human involvement clusters at the start.

### 4. Attach the Slice Contract

Add two fields to every slice while the user is still present:

1. **`acceptance`** — exact commands that must pass (the repo's real test, lint, build commands plus any app-level check a verification skill can run) and the observable behaviors that prove the slice works. When the source is a `to-spec` PRD, lift the behaviors from its Testing Decisions / named seams; name each at the **highest seam** as external behavior (`test-lens`), never an implementation detail — these become the test-first targets when `implement-and-review` builds the slice. Done must be machine-checkable; never invent commands — verify each one exists in the repo. A slice with no behavioral change (pure config, scaffolding, styling) states the mandatory line `Test expectation: none — [reason]` in place of behaviors; a feature-bearing slice with blank behaviors flags the breakdown incomplete — the none-annotation is never valid there.
2. **`gates`** — which design lenses apply, selected from the routing table in `design-gate` by the surfaces the slice touches, and `security: deep|standard`, set from the trigger list in `security-gate` Part 2 (when the source PRD has a Security Decisions section pre-marking security-sensitive surfaces, lift the flag from there instead of re-deriving). Do not copy those tables here — read them and record only the resulting flags.

### 5. Quiz the user — the approval gate

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: T-ID plus short descriptive name (`T3: …`)
- **Type**: HITL / AFK
- **Blocked by**: which other slices by T-ID (if any) must complete first
- **Acceptance**: the contract commands and observable behaviors
- **Gates**: lens flags and security level, with the matched trigger
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked HITL and AFK?
- Are the acceptance contracts complete — would passing these commands genuinely mean done?

Iterate until the user approves. This is the last required human touchpoint before delivery.

### 6. Publish the work queue

If an issue tracker is configured, publish each approved slice as an issue using the template below, titled with its T-ID prefix (`T3: <title>`), with the `ready-for-agent` triage label, in dependency order (blockers first) so real identifiers can be referenced in "Blocked by". If no tracker is configured, write the approved breakdown to a `TASKS.md` at the repo root using the same template, one section per task headed `## T<N>. <Title>`, with a status line (`todo | in-progress | done | blocked`). The T-ID stays authoritative across plan edits even after tracker identifiers exist.

<task-template>
## Parent

A reference to the parent issue or PRD (omit if none).

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation. Avoid file paths or code snippets — they go stale. Exception: a prototype snippet that encodes a decision more precisely than prose (state machine, reducer, schema, type shape) — inline the decision-rich parts and note their origin.

## Acceptance contract

- Commands: each exact command that must pass
- Behaviors: each observable behavior that must hold, or `Test expectation: none — [reason]` for a non-feature slice

## Gates

- Lenses: the design-gate lens flags for this slice
- Security: deep | standard (with the matched trigger)

## Blocked by

A reference to each blocking task by T-ID (plus tracker identifier when published), or "None - can start immediately".
</task-template>

Do NOT close or modify any parent issue.

## Gotchas

1. Do not publish a slice whose acceptance commands you have not confirmed exist and run in this repo.
2. Do not inline the design-gate routing table or security-gate trigger list — reference them and record only the flags.
3. Do not let a slice's acceptance be "tests pass" alone when the slice promises observable behavior — name the behavior.
4. Do not mark a slice AFK if completing it requires a decision the contract does not answer.
5. Do not renumber T-IDs when reordering, splitting, or deleting slices — new slices take the next unused number and gaps are fine.

---
*Stable-ID and test-expectation contracts adapted from Every's compound-engineering-plugin (`ce-plan`).*
