# Codex Prompt Engineering Reference

Codex (GPT-5.x) performs best with XML-tagged prompt blocks that create explicit contracts
for what the model should do, verify, and output. This reference provides task-type-specific
recipes for composing effective Codex prompts.

Read this file when crafting prompts for Codex, especially for multi-step or high-stakes tasks.

## Core Principle

Prompt Codex like an operator, not a collaborator. Be explicit about what "done" looks like
and include verification steps so the model self-checks before returning.

## XML Block Reference

| Block | Purpose | When to use |
|-------|---------|-------------|
| `<task>` | Primary instruction | Always |
| `<completeness_contract>` | Definition of "done" | Coding, implementation |
| `<verification_loop>` | Self-check steps before finishing | Coding, implementation |
| `<grounding_rules>` | Evidence requirements | Review, analysis |
| `<structured_output_contract>` | Output format specification | Review, structured data |
| `<missing_context_gating>` | What to do when stuck | Coding, debugging |
| `<research_mode>` | Investigation methodology | Research tasks |
| `<citation_rules>` | Source attribution requirements | Research tasks |
| `<action_safety>` | Boundaries for write operations | Tasks that modify state |
| `<prior_context>` | Previous conversation/debate context | Continuation tasks |
| `<execution_metadata>` | Structured metadata for parsing | Workflow orchestration |

## Recipes by Task Type

### Coding / Implementation

```xml
<task>
[What to build or change, with acceptance criteria]
</task>

<completeness_contract>
Your implementation is incomplete unless:
- All files compile/pass type checks
- New code follows existing patterns in the codebase
- Edge cases from the requirements are handled
- No placeholder or TODO code remains
</completeness_contract>

<verification_loop>
After making changes:
1. Re-read modified files for typos and logic errors
2. Run existing tests if available
3. Verify new public API matches the spec
</verification_loop>

<missing_context_gating>
If you lack information to proceed (unclear requirement, missing file, ambiguous API):
STOP and state exactly what you need. Do not guess.
</missing_context_gating>
```

### Debugging / Diagnosis

```xml
<task>
Diagnose the root cause of: [symptom description]
Do not fix it yet — just identify the cause and explain the mechanism.
</task>

<research_mode>
1. Reproduce the symptom by tracing the code path
2. Identify the specific line(s) where behavior diverges from expectation
3. Check for recent changes (git log) that may have introduced the bug
4. Verify your hypothesis by checking edge cases
</research_mode>

<completeness_contract>
Your diagnosis is incomplete unless:
- You identify the exact file and line(s) causing the issue
- You explain the mechanism (why does this code produce the wrong result)
- You distinguish root cause from symptoms
- You note whether other callers are also affected
</completeness_contract>
```

### Code Review

```xml
<task>
Review the following code changes for correctness, regressions, and security.
</task>

<grounding_rules>
- Every finding must cite a specific file path and line range
- Never speculate — if you cannot find evidence, do not flag it
- Distinguish blocking issues (P1-P2) from suggestions (P3-P4)
- If the code is correct, say so — do not manufacture issues
</grounding_rules>

<structured_output_contract>
Return findings as: severity (P1-P4), file, line range, description, suggested fix.
</structured_output_contract>

<dig_deeper_nudge>
After your initial pass, re-read the diff one more time looking specifically for:
- Off-by-one errors in loops and slices
- Nil/null pointer dereferences in error paths
- Missing authorization checks on new endpoints
- Race conditions in concurrent code
</dig_deeper_nudge>
```

### Root-Cause Review (Adversarial)

```xml
<task>
Perform an adversarial review of the changes. Focus on finding real problems
that would survive a rebuttal from the author.
</task>

<attack_surface>
- Auth/authz bypass
- Data loss or corruption in write paths
- Race conditions and concurrency bugs
- Rollback safety
- Input validation at system boundaries
- Secret/credential exposure
</attack_surface>

<finding_bar>
Only report findings where:
- You can point to specific code demonstrating the issue
- The issue has a plausible real-world trigger
- Impact is meaningful (data loss, security breach, outage)
</finding_bar>
```

### Research / Investigation

```xml
<task>
Investigate: [question or area to research]
</task>

<research_mode>
1. Clarify what needs to be answered
2. Search broadly, then narrow
3. Cross-reference multiple sources
4. Distinguish facts (verified) from inferences (supported) from speculation (flagged)
</research_mode>

<citation_rules>
- Cite file paths, line numbers, URLs, or command output for every factual claim
- Prefix unverifiable claims with "Unverified:"
- Never present inference as fact
</citation_rules>
```

### Write Tasks (Migrations, Config Changes, etc.)

```xml
<task>
[What to create or modify]
</task>

<action_safety>
Before writing any file:
- Verify the target path is correct
- Check for existing files that would be overwritten
- Ensure the change is reversible (especially for migrations)
For database migrations: verify idempotency (IF NOT EXISTS, etc.)
</action_safety>

<verification_loop>
After writing:
1. Re-read the file to verify correctness
2. Check that the file integrates with existing code (imports, references)
3. Run any applicable validation (lint, compile, migrate --dry-run)
</verification_loop>
```

## Anti-Patterns to Avoid

1. **Vague tasks**: "Fix the bug" — instead, describe the symptom and where it occurs
2. **No completion criteria**: Without `<completeness_contract>`, Codex may stop early
3. **Over-constraining**: Long lists of MUSTs and NEVERs create brittle prompts — explain the *why* instead
4. **Missing context gating**: Without it, Codex will guess when stuck instead of asking
5. **Raising effort instead of tightening the prompt**: `--effort xhigh` is expensive; a tighter prompt at `--effort medium` often produces better results

## Effort Level Guidelines

Note: this skill's `run_codex.py` wrapper exposes no `--effort` flag. Reasoning effort is
configured through the Codex CLI itself — set `model_reasoning_effort` in `~/.codex/config.toml`,
or pass it per-run via the Codex CLI config override (`codex -c model_reasoning_effort=<level>`)
outside this wrapper.

| Level | Use case | Cost |
|-------|----------|------|
| `none` / `minimal` | Simple lookups, quick answers | Lowest |
| `low` | Straightforward single-file edits | Low |
| `medium` | Multi-file changes, standard reviews | Default |
| `high` | Complex refactors, thorough analysis | High |
| `xhigh` | Architecture decisions, security audits | Highest |

Prefer tighter prompts over higher effort. If `medium` with a good `<completeness_contract>`
isn't working, improve the prompt before bumping to `high`.
