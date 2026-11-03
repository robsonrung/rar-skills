# Read-only queue controller

`shared/scripts/task_queue.py` reads the queue, task contracts, approved routing plan, ledger, and review evidence, and projects which tasks may start. It writes nothing, starts no worker, and runs no check. Its `--help` documents the `queue.json` shape, merge plans, `approval_record`, and `integration_evidence`; read it rather than a copy here.

```bash
python3 shared/scripts/task_queue.py approval-inputs --queue <queue.json> --root <project-root> \
  [--routing-plan <draft-routing-plan.json>]
python3 shared/scripts/task_queue.py schedule --queue <queue.json> --routing-plan <routing-plan.json> \
  --ledger <run-state.json> --root <project-root>
```

`approval-inputs` reports current and prospective ready-state hashes for drafts, and with `--routing-plan` the prospective scope and route digests for a combined approval. `schedule` returns `ready`, `blocked`, and `required_integration` in stable order. Bad IDs, missing blockers, cycles, malformed bindings, and unsafe ownership fail closed.

The approved routing plan's `scope.inputs` binds the queue, the PRD, every task contract, and any review policy. Changing dependencies, ownership, concurrency, or merge plans needs a new approval. `concurrency.isolation` is `working-tree` (the default, one writer) or `worktree`.

Run `schedule` immediately before each dispatch, and again after any ledger, contract, integration, or source change. It reserves nothing: reserve the call in the ledger before starting it.

With a feature policy, `implemented` lists provisional tasks whose focused evidence permits dependency release, `integrated` lists tasks accepted by the final gate, and `feature_review` reports `blocked`, `review_required`, or `ready`.
