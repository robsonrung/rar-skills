---
name: to-tasks
description: Break an approved plan, spec, or PRD into autonomously executable tasks — tracer-bullet vertical slices that each carry a machine-checkable acceptance contract and design/security gate flags, so an agent can complete them without asking the user anything. Use when the user wants to break a plan into tasks, convert a spec or PRD into a work queue, create implementation tasks for autonomous agents, or when a pipeline planning phase needs the task breakdown. Writes one markdown file per task under .ai-workflow/work/<feature-slug>/tasks/, never to an issue tracker. Use whenever tasks will be executed by agents; for human-executed tickets without contracts, a plain checklist suffices. An opt-in Panel mode drafts the breakdown with a multi-model panel.
---

# To Tasks

Break a plan into independently-grabbable tasks using vertical slices (tracer bullets). Every task carries a Slice Contract — machine-checkable acceptance plus gate flags — so the user approves the breakdown once and is never asked anything afterwards.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (a PRD path such as `.ai-workflow/work/<feature-slug>/prd.md`, a plan file, or a URL), read it in full.

### 2. Explore the codebase

If you have not already explored the codebase, do so. Task titles and descriptions should use the project's domain glossary vocabulary (`CONCEPTS.md`) and respect ADRs in the area being touched. Also identify the repo's real verification commands (test, lint, build, typecheck) — the acceptance contracts below must use commands that actually exist.

While you are in the code, look for **prefactoring** opportunities: a small, behavior-preserving structural change that makes the feature's implementation easy — extract the seam the slices will test through, split the module two slices would otherwise both edit, introduce the type the new behavior hangs on. "Make the change easy, then make the easy change." A prefactor slice's acceptance contract carries characterization tests, or `Test expectation: none — behavior-preserving refactor, covered by the existing suite` when the suite already pins the behavior.

### 3. Draft vertical slices

Break the plan into **tracer bullet** tasks. Each task is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
- Each slice is sized to fit in a single fresh context window: one agent, one session, no mid-slice handoff. If the What-to-build needs more than a screen, split it
- Prefactoring slices come first, before the slice that needs the easier shape
</vertical-slice-rules>

Assign each slice a stable ID (`T1`, `T2`, …) at draft time. **IDs are never renumbered.** Reordering leaves IDs in place (T1, T3, T5 in their new order is correct; renumbering to T1, T2, T3 is not). Splitting keeps the original ID on the original concept and gives the new slice the next unused number. Deleting leaves a gap — gaps are fine. Executors and "Blocked by" references cite slices by T-ID, so the IDs must survive every later reorder, split, or delete of the breakdown.

Classify each slice **HITL** or **AFK**. HITL slices require human interaction — irreversible migrations, externally visible contract sign-off, design approval. AFK slices run unattended. Prefer AFK; schedule HITL slices first so human involvement clusters at the start.

**Wide refactors are the exception to vertical slicing.** A wide refactor is one mechanical change (rename a column, retype a shared symbol, swap a base class) whose blast radius fans across the whole codebase, so a single edit breaks hundreds of call sites at once and no vertical slice can land green. Do not force it into a tracer bullet; sequence it as **expand–contract**:

1. **Expand** — add the new form beside the old so nothing breaks. One slice.
2. **Migrate** — move the call sites over in batches sized by blast radius (per package, per directory), each batch its own slice blocked by the expand slice. CI stays green batch to batch because the old form still exists.
3. **Contract** — delete the old form once no caller remains, in a slice blocked by every migrate batch.

When even the batches cannot stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify slice; green is promised only there, and that slice's acceptance contract is the full suite.

### 4. Attach the Slice Contract

Add two fields to every slice while the user is still present:

1. **`acceptance`** — exact commands that must pass (the repo's real test, lint, build commands plus any app-level check a verification skill can run) and the observable behaviors that prove the slice works. When the source is a `to-prd` PRD, lift the behaviors from its Testing Decisions / named seams; name each at the **highest seam** as external behavior (`test-lens`), never an implementation detail — these become the test-first targets when `implement-and-review` builds the slice. Done must be machine-checkable; never invent commands — verify each one exists in the repo. A slice with no behavioral change (pure config, scaffolding, styling) states the mandatory line `Test expectation: none — [reason]` in place of behaviors; a feature-bearing slice with blank behaviors flags the breakdown incomplete — the none-annotation is never valid there.
2. **`gates`** — which design lenses apply, selected from the routing table in `design-gate` by the surfaces the slice touches, and `security: deep|standard`, set from `security-gate`'s deep-pass trigger list (when the source PRD has a Security Decisions section pre-marking security-sensitive surfaces, lift the flag from there instead of re-deriving). Do not copy those tables here — read them and record only the resulting flags.

### 5. Quiz the user — the approval gate

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: T-ID plus short descriptive name (`T3: …`)
- **Type**: HITL / AFK
- **Blocked by**: which other slices by T-ID (if any) must complete first
- **Acceptance**: the contract commands and observable behaviors
- **Gates**: lens flags and security level, with the matched trigger
- **Parallel-safe**: whether it can run alongside other slices, and which
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked HITL and AFK?
- Are the acceptance contracts complete — would passing these commands genuinely mean done?

Iterate until the user approves. This is the last required human touchpoint before delivery.

### 6. Publish the work queue

Write the approved breakdown as **one markdown file per slice** under `.ai-workflow/work/<feature-slug>/tasks/`, beside the PRD that produced it (`.ai-workflow/work/<feature-slug>/prd.md`; reuse its slug, or pick one if the input was a bare plan). Never publish to an issue tracker — the files are the queue. Name each file `T<N>-<slug>.md` and fill it from the template below. Write them in dependency order (blockers first) so every "Blocked by" names a file that already exists. Blocking edges are text: the T-IDs and file names of the slices that gate this one. One slice per file, never a combined file — an executor reads only its own slice, and parallel status updates never collide on a shared file.

The `Status` line is the queue state: `ready-for-agent` when written, then `in-progress`, `done`, or `blocked`, flipped by the executor. Executors **work the frontier**: any slice whose blockers are all `done` is grabbable, and the HITL slices at the head of the order are taken first. The T-ID stays authoritative across every later edit of the breakdown.

<task-template>
# T<N>: <Title>

**Type:** HITL | AFK **Status:** ready-for-agent | in-progress | done | blocked **Parent:** the PRD path (`.ai-workflow/work/<feature-slug>/prd.md`), the plan file, or "none"

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation. Avoid file paths or code snippets — they go stale. Exception: a prototype snippet that encodes a decision more precisely than prose (state machine, reducer, schema, type shape) — inline the decision-rich parts and note their origin.

## Acceptance contract

- Commands: each exact command that must pass
- Behaviors: each observable behavior that must hold, or `Test expectation: none — [reason]` for a non-feature slice
- Never delete, skip, weaken, narrow, or mock-away tests — or loosen these checks — to make this contract pass. If the contract is wrong, stop and report it.

## Gates

- Lenses: the design-gate lens flags for this slice
- Security: deep | standard (with the matched trigger)

## Rollback note

How to undo this slice if it lands badly: the revert shape (plain revert, feature flag off, down-migration, cache purge), and anything that makes it _not_ a plain revert — data written, external calls made, contracts published. Say "plain revert, no side effects" when that is genuinely true.

## Expected review focus

Where a reviewer should spend their attention on this slice — the one or two things most likely to be wrong here (a boundary, an error path, a permission check, a migration order, a state transition). Not a generic checklist; the specific risk this slice carries.

## Parallelization

Whether this slice is safe to run alongside others, and which. Never parallelize tasks that write the same files, migrations, shared contracts, or security-sensitive paths — unless there is an explicit merge plan stated here. When in doubt, serialize: a stated dependency costs less than a merge conflict in a migration.

## Blocked by

The T-ID and file name of each blocking slice (`T2 — T2-add-schema.md`), or "None - can start immediately". </task-template>

Do NOT edit the parent PRD, and do NOT delete or rewrite a slice file an executor has already moved past `ready-for-agent`.

## Panel mode (optional)

By default this skill drafts the breakdown with a single model. **Panel mode** is opt-in: turn it on when the user asks for a multi-model task plan, or when the architecture and test strategy are consequential enough to be worth independent seats. It replaces **step 3 and step 4** — the drafting of slices and their contracts — with a five-phase multi-seat panel, and nothing else: the output still carries the full Slice Contract, it still ends at the step-5 approval quiz, and it still publishes per step 6. **The panel replaces drafting, never the gate.** Read [references/panel-mode.md](references/panel-mode.md) before running any panel phase; it holds the phases, roles, artifacts, validation command, and honesty rules.

## Gotchas

1. Do not publish a slice whose acceptance commands you have not confirmed exist and run in this repo.
2. Do not inline the design-gate routing table or security-gate trigger list — reference them and record only the flags.
3. Do not let a slice's acceptance be "tests pass" alone when the slice promises observable behavior — name the behavior.
4. Do not mark a slice AFK if completing it requires a decision the contract does not answer.
5. Do not renumber T-IDs when reordering, splitting, or deleting slices — new slices take the next unused number and gaps are fine.
6. Do not slice a wide refactor vertically — sequence it expand → migrate batches → contract, with the contract slice blocked by every batch.
7. Do not publish to an issue tracker or a single combined file — one markdown file per slice under `.ai-workflow/work/<feature-slug>/tasks/`.

---

_Stable-ID and test-expectation contracts adapted from Every's compound-engineering-plugin (`ce-plan`)._
