# Task implementation

1. Read the task, acceptance contract, relevant code and tests, and active project conventions. Reuse settled design, security, interface, and acceptance decisions. Reopen only changed or unresolved boundaries.
2. Confirm approved inputs still match the routing plan. An inherited plan supplies the route. For a new selection, use the common preview rules, including independent review, session strategy, host capabilities, provider controls, tools, receipt limits, budget, and exact fallback triggers. Approval for unchanged defaults remains valid within source sharing authority and receipt limits.
3. Start with one sequential working-tree track. Add independent tracks only when their scopes and contracts permit it. Worktree isolation is reversible; commit-based integration retains its separate authority.
4. Read [methodology.md](methodology.md) through `Select by Trigger` and [evidence-strategy.md](evidence-strategy.md). Discover required commands and stable check IDs before dispatch. Put relevant method constraints, inherited lens findings, requirements, capture commands, intended base, artifact location, and required failing regression evidence in the brief.

For a bound feature policy, read `Policy and authority`, `One check plan`, and `Provisional dependency release` in `shared/references/feature-review.md`, plus the bound policy. Derive this task's focused requirements with `feature_review.py requirements --policy PATH --root ROOT --task TASK`. The launcher validates the binding before it can omit a deferred task reviewer. Record broad simplification candidates for the combined pass; clean locally when correctness, a critical boundary, or the task contract needs it. Focused regression and dependency checks remain required.

For task mode, include `coding-review-simplify` when a behavior-preserving simplification can help after the task turns green. Complete that cleanup before the final snapshot, including candidates discovered during implementation. Resolve its readable skill path for the implementer; include the method constraints if it cannot read the path. Use existing report fields for cleanup outcomes.

## Dispatch

Prefer native delegation when the host exposes the exact model, effort, isolation, and tools. Use an external runner for a foreign model, an unsupported native capability, or an explicit transport request. An external process does not inherit host browser tools.

```bash
SKILL_DIR="<absolute path of this skill directory>";
python3 "$SKILL_DIR/scripts/launch.py" launch \
  --session-id <session-id> --task-id <task-id> \
  --routing-plan <routing-plan.json> \
  --track <track-name> <implementation-brief.md>
```

Use `--isolation worktree` and one `--track` pair per approved independent track. `task-id` is the stable task namespace. A dry run previews a complete draft without writes, worktrees, or dispatch. Read `Launch implementation` in [runner-invocations.md](runner-invocations.md#launch-implementation) only for draft promotion, explicit working-directory, or additional launch options.

Read the common router's selected receipt section. Record actual native execution with `record-native`; a native handoff is not execution. Every initial call, repair, review, and resume retains the selected request controls and tools. Validate their request policy digest and receipt evidence.

After the final edit, the implementer captures required checks and returns the snapshot and original result paths. Continue through [deferred-task.md](deferred-task.md) for a deferred feature task, or [task-review.md](task-review.md) for critical and task-mode review. Worker success alone cannot release a dependency.
