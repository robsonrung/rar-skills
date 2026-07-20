# Leitwörter — Leading Words for Skill Authors

A *leitwort* (plural *leitwörter*) comes from literary theory: a word or phrase
repeated through a text to anchor its meaning. In a skill, a leitwort is a word
or phrase the agent **repeats back to itself while acting**, and which thereby
steers its behavior. "Zone of proximal development", "tracer bullet", "deep
module", "connascence", "behavior-preserving" — each is a compact token that
both reinforces a behavior and tickles the model's parameters for the
discipline it comes from.

This doc is the convention for writing skills in this repo so they exploit
leitwörter by default.

## The one rule that matters

**A leitwort only works when the agent says it back while acting.** A concept
named once in a heading and then dropped is inert. A concept the agent utters as
it reasons ("I see **primitive obsession** here", "the **smallest reversible
move** is…") is self-reinforcing. So:

- Put the leitwort where the agent narrates its decisions, not only in a section
  title.
- Give the agent a reason to repeat it — a diagnosis to state, a check to name, a
  move to choose by name.
- Prefer one sharp, narratable phrase over a prose list of adjectives.

## How to deploy a leitwort

1. **Name it once, define it once.** One clear sentence. Attribute it to its
   source when that adds activation ("Brooks", "Farley", "Khorikov", "Feathers").
2. **Make it load-bearing.** Route real decisions through it. The agent should
   have to invoke the word to make the call.
3. **Model the sentence.** Show the agent the kind of sentence it should produce:
   *"This keeps **conceptual integrity** but at the cost of **change
   ownership**."* Modelled sentences get echoed.
4. **Prefer rare, precise words.** `connascence` beats `coupling` because it has
   almost no false-friend activations — it pulls straight to the intended
   analysis. Uncommon terms of art are higher-leverage than generic ones.
5. **Don't bury it in a checklist.** A 15-item prose sentence is read once and
   forgotten. Group and name the items so each is a token the agent can cite.

## Anti-patterns

- **Heading-only leitwörter** — the word is a title but never recurs in the
  body. Inert.
- **Filler verbs as guidance** — "carefully", "thoroughly", "make sure",
  "review for clarity". These activate nothing. Replace with a named anchor.
- **Synonym drift** — the same concept under a different word in each skill,
  forcing the agent to re-translate when it switches skills. Use the canon below.
- **Over-naming** — every line a Capitalized Term. Reserve leitwörter for the
  load-bearing concepts; noise dilutes them.

## Canonical vocabulary (use these words, not synonyms)

When a skill touches one of these concepts, use the canonical leitwort so the
agent sees one consistent token across the whole library:

| Concept | Canonical leitwort | Avoid (synonym drift) |
|---|---|---|
| Not changing what the code does | **behavior-preserving** | behavior unchanged, invariant-safe, correctness-preserving |
| Coupling as the unit of analysis | **connascence** (strength × locality × degree) | tight/loose coupling, distant, high degree |
| Keeping scope minimal | **smallest coherent shape** | minimal, don't boil the ocean, just enough |
| The cheapest reversible learning step | **smallest reversible move** | small step, quick win, MVP move |
| Test value | **four pillars** (regression protection, resistance to refactoring, fast feedback, maintainability) | meaningful, valuable, worth keeping |
| Testing *what*, not *how* | **observable behavior** | black-box, outcome-based, end result |
| One coherent design idea | **conceptual integrity** | coherent, unified, single model |
| Where a change wants to live | **change ownership** | boundary ownership, responsibility |
| Failures must be loud | **observable failure** | fail loudly, make failure visible |
| End-to-end thin path | **vertical slice** / **tracer bullet** | thin slice, e2e path |
| Domain words in code | **ubiquitous language** | domain language, business terms |
| Resumable handoff | **cold-start test** | fresh-agent, continuity |
| Pinning legacy behavior before change | **characterization test** (the **net**) | approval test (acceptable synonym), golden test |
| A seat's output is only ever that seat's | **seat fidelity** | never substitute, block the seat, treat seat as absent |
| A task is done only when its criteria pass | **acceptance contract** | definition of done, completion criteria, completeness contract |
| A comment that carries what the code can't | **earned comment** | good comments, useful comments, helpful comments |
| Escalate review spend only where risk is | **cheap-first** | cost-aware review |
| Risk-scaled review depth | **blast radius** | impact radius |
| Humans in a thread outrank automation | **human-participation gate** | defer to humans, human override |
| Graduated autonomy for ambiguous findings | **autonomy ladder** | judgment call, discretion |
| Categories automation must never approve | **deny-list** | blocklist, forbidden paths |
| Hunt only reasons a merge must not happen | **showstopper-only** | blockers-only, critical-only |
| A loop is only finished in a named end state | **terminal state** | done condition, exit condition |

A skill may introduce a new leitwort when it genuinely owns a concept no other
skill covers. Add it to this table when you do.

## Checklist before shipping a skill

- [ ] The load-bearing concept has a named leitwort, defined once.
- [ ] The agent has a reason to **repeat** the leitwort while executing, not just
      read it.
- [ ] At least one **modelled sentence** shows the agent how to say it.
- [ ] Filler verbs ("carefully", "thoroughly") are replaced by named anchors.
- [ ] Concepts already in the canon use the **canon word**, not a synonym.
- [ ] Rare, precise terms are preferred where one exists.
- [ ] Leitwörter are reserved for load-bearing ideas — not every line.
