# Minimax Runner — Requirement Backlog

Requirement-tracking notes relocated from `SKILL.md` (they are spec backlog, not agent instructions). Status reflects the current implementation in `qwen-runner/scripts/run_qwen.py`.

- Requirement: qwen/minimax auth smoke test and explicit blocked response. (Not implemented — no pre-run smoke test exists; failures surface via return codes and `auth_ok` in the envelope. If built, it belongs in `run_qwen.py`.)
- Differentiate missing_binary vs auth_failed vs timeout in return semantics. (Covered today by the Return Codes table in the qwen-runner skill's SKILL.md plus `auth_ok` in the envelope.)
- Output must include effective_provider metadata even in non-fallback mode. (Implemented — `effective_provider` is a required envelope key.)
- Document council seat accounting behavior. (Done — documented in `SKILL.md` Behavior item 3.)
