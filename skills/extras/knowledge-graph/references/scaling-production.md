# Scaling and Production Operation

## Extraction cost

Two levers, both free of quality tradeoffs:

- **Prompt caching** — the system prompt and schema are identical across every extraction call; cache them and pay full price only for the document text.
- **Batch API** — 50% off for jobs that tolerate up to 24 hours of latency. Corpus ingestion is exactly that job.

Set an **extraction cap** (max documents or tokens per run). Without one, a corpus-ingestion error — a crawler loop, a duplicated feed — becomes an unbounded bill before anyone notices.

## Resolution at scale: blocking

Feeding ten thousand PERSON entities to one resolution prompt does not work. Block first: group candidates by cheap signals — same last name, overlapping tokens — with a simple inverted index, no model call. The model then only arbitrates within blocks of 50–100 candidates. Blocking recall is the ceiling on resolution recall: two mentions that never share a block can never merge, so keep blocking signals loose and let the model do the precise work inside each block.

## Incremental updates

The graph accumulates; it never rebuilds.

1. Extract the new document.
2. Resolve its entities against the existing canonical set (per-type, with blocking) — not against the whole raw history.
3. Classify each extracted fact against what the graph already holds (below), and act on the verdict.
4. Re-summarize an entity only when its source-document set changes materially (new documents mentioning it, not just new edges), and refresh the community reports whose membership changed.
5. Record processed documents in a state file so overnight runs are idempotent and resumable.

## Classifying new facts: flag, never overwrite

Append-only is not the same as accumulating. Real corpora correct themselves, and a document that revises an earlier one arrives looking exactly like a document that agrees with it. Classify every extracted fact against the existing edges between the same two nodes:

| Verdict | Action |
| --- | --- |
| **new** | Add the edge with its evidence span and source document |
| **duplicate** | Add the source document to the existing edge; no new edge |
| **update** | Add the edge; keep the prior one, timestamped, not deleted |
| **contradiction** | Record both edges in the contradiction ledger; flag for review |
| **uncertain** | Route to the human sample; do not guess |

This is not a fifth prompt so much as prompt 2's move applied to facts instead of names: the same judgment tier weighing conflicting evidence, with the same refusal to merge without it.

```python
class FactVerdict(BaseModel):
    kind: Literal["new", "duplicate", "update",
                  "contradiction", "uncertain"]
    conflicting_edge: str | None   # the edge it disagrees with, if any
    reason: str
```

```python
CLASSIFY_PROMPT = """A new fact was extracted from document {source}. Below
are the edges the graph already holds between the same two entities.

Classify the new fact. Compare the evidence spans, not just the predicates —
two phrasings of one fact are a duplicate; two incompatible claims about the
same thing are a contradiction; a later fact that supersedes an earlier one
is an update. When the evidence does not settle it, answer "uncertain"
rather than guessing.

New fact: {fact}
Existing edges: {existing}"""
```

The rule the classifier exists to enforce is **flag, never overwrite**. A pipeline that silently keeps the newest fact makes a correction and a transient error indistinguishable, and it destroys the evidence that would have told them apart. Two edges that disagree, both carrying provenance, are a finding. One edge that quietly replaced another is a data loss nobody will notice.

Ambiguity is worth preserving for a second reason: a graph an evaluator uses as ground truth must be able to say "the corpus disagrees with itself here" rather than assert one side of it.

The contradiction ledger is a work queue, not an archive. Track its depth — a backlog that only grows means the corpus is noisier than the extraction prompt assumes, or that entity resolution is merging nodes that should have stayed apart and manufacturing disagreements between them.

## Storage

NetworkX in memory works to a few hundred thousand edges. Beyond that, the schema maps directly onto a handful of Postgres tables:

```sql
entities(id, name, type, summary)
relations(source_id, target_id, predicate, evidence, source_doc, valid_from)
aliases(entity_id, alias)
community_reports(community_id, level, member_hash, title, summary)
contradictions(relation_a, relation_b, detected_at, resolved_by)
```

Only the persistence layer changes — the extraction and resolution prompts, and the schema they share, are untouched by the migration.

## Production readiness checklist

Each element earns its place by the failure that appears without it:

| Element | Failure if missing |
| --- | --- |
| Gold set | No feedback loop; prompt changes are blind |
| Alias-map coverage | Scoring artifacts: recall looks worse than it is |
| Schema version | Incompatible entities from different prompt versions |
| Extraction cap | Unbounded cost from corpus ingestion errors |
| Resolution fallback | Silent entity loss: nodes disappear |
| Provenance tracking | Ungrounded answers; the evaluator cannot fact-check |
| Connectivity monitor | Fragmented graph: missed cross-document links |
| Contradiction ledger | Corrections silently overwrite, or silently vanish |
| Report freshness check | Global search cites themes the graph no longer has |
| Human sample | Comprehension rot: the graph outgrows understanding |

The pipeline is not done when it runs. It is done when you can tell, on any given morning, whether what it produced overnight was actually right — the gold set, the provenance tracking, and the human sample are what make that possible.
