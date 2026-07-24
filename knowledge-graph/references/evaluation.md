# Evaluating Extraction Quality

The harness loop is what turns a demo into a production system: change the
prompt, rerun the scorer, watch F1 move. Without it, every prompt edit is a
blind guess. The same loop has the shape of a self-improving agentic loop —
act, observe, learn, repeat — which is why the harness is worth building
before the corpus grows.

## Building the gold set

- Pick a small, representative document sample (5–20 docs; enough to cover
  the entity types and relation shapes the domain produces).
- For each document, hand-label the entities and relations a competent
  reader would consider central. This is the definition of "correct" the
  extraction prompt is tuned against — disagreements about what belongs in
  the gold set are requirements discussions, resolve them there.
- Version the gold set alongside the schema. When the schema changes (a new
  entity type, a renamed predicate convention), the gold set must be
  re-labeled for the delta or scores stop meaning anything.

## Alias-map-aware scoring

Score after resolution, through the alias map — otherwise recall looks
worse than it is. If the gold set says "Buzz Aldrin" and extraction
produced "Edwin Aldrin", that is a hit if and only if resolution clustered
them; scoring raw surface forms counts it as both a false negative and a
false positive.

```python
def score(predicted, gold, alias_map):
    canon = lambda name: alias_map.get(name, name)
    pred = {canon(e) for e in predicted}
    goldset = {canon(e) for e in gold}
    tp = len(pred & goldset)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(goldset) if goldset else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall else 0.0)
    return precision, recall, f1
```

Score relations the same way: a predicted triple matches a gold triple when
both endpoints canonicalize to the same nodes and the predicates are
equivalent (keep a small predicate-synonym list rather than demanding exact
strings).

## Precision over recall

Expect precision near 1.0 and recall in the 0.4–0.6 range with a
central-entities-only extraction prompt. That asymmetry is usually the
right tradeoff, not a defect:

- A **false negative** (missing entity) is a visible gap — a question the
  graph cannot answer, which grounded querying reports explicitly.
- A **false positive** (wrong entity) spawns wrong relations, and those
  edges propagate through every multi-hop chain that touches them. The
  error is invisible at the node and compounding at query time.

Loosen the centrality guideline only when measured recall is costing
answers you need, and re-measure precision after every loosening.

## Per-stage monitoring

Extraction F1 is not the only number. Watch per-stage:

- **Resolution — silent loss**: union of all cluster aliases must equal the
  input name set. Anything left over vanished from the graph without an
  error. Fail loudly; fall back to singleton clusters.
- **Resolution — over-merging**: sample clusters whose aliases have low
  string similarity (those are the model's judgment calls) and hand-check
  a few per run. "Gemini 12" folded into "Project Gemini" is the canonical
  miss.
- **Connectivity**: track connected-component count as the corpus grows. A
  rising count means cross-document links are being missed — usually a
  resolution regression, not an extraction one.
- **Human sample**: read a fixed-size random sample of new edges each run.
  Metrics catch drift in what you measured; the sample catches drift in
  what you didn't.
