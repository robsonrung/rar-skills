# Auto interview mode

Read only when the invocation includes `--auto`. Two roles advance the design tree from the supplied scope and repository evidence: an interviewer asks, a respondent answers. It is not a council, and a role's answer is not an independent opinion.

## Plan

1. Pick the route: `interview-product` for an ambiguous user or product problem, `interview-technical` for an explicit technical problem; when unclear, use `interview-product` and record that assumption. Run `python3 shared/scripts/model_routing.py resolve <route>`.
2. Show both roles with model, effort, and host route, and the ceilings below. Ask: **"Approve this plan, or specify changes."** `--auto` is the mandate for automatic answers inside the supplied scope; a changed model, role, or ceiling needs the user.

## Roles

Give each role one persistent context for the whole run; every later round goes to that same context. The roles see only the decision record, the question and answer packets, and cited evidence, never each other's transcript. Leave secrets and unrelated personal data out of packets; after the first, send only changed decisions and open questions.

Route each role by host: T3 Code `delegate_task` (continue with `t3_thread_send`); Claude Code or Codex a native subagent with the role's model (continue by messaging it); otherwise the matching `*-runner` skill (continue by resuming its session). Both roles are read-only. An unavailable role pauses the run for the user; never swap in another model.

| Role | Job | Returns |
| --- | --- | --- |
| Interviewer | Recompute the frontier from the record and the last answers | Up to five independent questions, each with repository basis, materiality, and dependencies |
| Respondent | Answer from evidence and the supplied scope | Per question: an answer with evidence, source category, and assumptions, or `awaiting-human` with the reason |

The respondent tags each answer with one source category: `user-supplied`, `repository-evidence` (path, locator, or command result), `automated-inference` (explain why scope and evidence permit it without a preference), `nonmaterial-default`, `out-of-scope`, or `awaiting-human`. It never claims a preference, approval, or authority that was not supplied. Product preference, risk or policy acceptance, data ownership, a security commitment, or any material choice that evidence does not decide is `awaiting-human`.

## Rounds

One interviewer call and one respondent call make a round. Keep going without pausing for ordinary answers. When only material unknowns remain, bring them to the user as one round of at most five questions.

Ceilings: 5 rounds, 5 questions per round, 20 calls in total. A malformed reply or transient failure gets one repair prompt to the same context; a second failure ends the run `failed`. Reaching a ceiling ends it `ceiling_hit`. Do not extend a ceiling or start a fresh run without the user.

Keep the run under `.ai-workflow/work/<feature-slug>/interview-auto/<run-id>/`: the round packets and a run state per `shared/references/run-state-contract.md`. Record the run ID and state path under `## Auto interview run` in the decision record, and resume from there with the same role contexts.

## Ready-for-PRD gate

Set `ready-for-prd` only when every frontier branch has a non-`awaiting-human` result, each automatic answer keeps its decision ID, source category, indexed evidence, and assumptions in the record, and every `automated-inference` states why the scope permits it. Otherwise keep `draft` and present the remaining material questions.
