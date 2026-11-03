# Leitwörter

A **leitwort** (plural leitwörter) is a short, distinctive phrase that steers an agent because the agent repeats it while acting: "the **smallest reversible move** is…", "I see **primitive obsession** here". A phrase that appears only in a heading does nothing. Put it where the agent states a diagnosis, names a check, or picks a move.

## When to coin one

Coin a leitwort only for a load-bearing concept the skill owns and no other skill covers. Define it once, in one sentence, and route a real decision through it. Prefer a rare term of art to a generic word: `connascence` pulls toward one analysis, while `coupling` has many loose associations. Name the source when it adds meaning ("Feathers", "Khorikov"). Name only the few concepts that carry the skill; when every line has a named term, none of them stands out.

Before naming a concept, check the `canon` in `leitworter.json`. When the concept is already there, use its word, not a synonym. Synonym drift makes the agent translate between skills. Two pairs stay distinct: the **cold-start test** asks whether a fresh agent can resume from a written handoff, and the **crash-resume test** asks whether a run can resume from its own checkpoint. **idempotent** covers both stored-state writes and agent steps, scoped in the sentence.

## Model the sentence

Each leitwort needs one modelled sentence that shows the agent how to use it: _"This keeps **conceptual integrity** at the cost of **change ownership**."_ Agents echo modelled sentences; they rarely echo definitions.

## The registry and its checker

`leitworter.json` at the repository root has three blocks:

- `guards`: each entry names one file. A `must_contain` phrase must stay in that file. Deleting it is a **deletion** failure. A `must_not_contain` phrase must not return. Its return is a **drift** failure.
- `canon`: the vocabulary shared across skills. Each concept has a leitwort and the `drift_terms` it replaces.
- `filler_verbs`: words such as "carefully" that add no guidance. Replace each with the check it stands for.

`python3 scripts/check_leitworter.py` (`--json` for data) matches case-insensitive substrings. It exits 1 on a deletion or drift failure and 2 on a registry error. It warns, without failing, on a canon drift term in a `SKILL.md` that does not own that leitwort, and on filler verbs in any `SKILL.md`. CI runs it in `.github/workflows/skill-guards.yml`.

When you add a leitwort, add its guard, and add a canon entry if other skills should use the word. When you rename or move one, update its guard in the same change. Never weaken a guard just to make a check pass.
