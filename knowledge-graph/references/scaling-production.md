# Scaling and Production Operation

## Extraction cost

Two levers, both free of quality tradeoffs:

- **Prompt caching** — the system prompt and schema are identical across
  every extraction call; cache them and pay full price only for the
  document text.
- **Batch API** — 50% off for jobs that tolerate up to 24 hours of
  latency. Corpus ingestion is exactly that job.

Set an **extraction cap** (max documents or tokens per run). Without one, a
corpus-ingestion error — a crawler loop, a duplicated feed — becomes an
unbounded bill before anyone notices.

## Resolution at scale: blocking

Feeding ten thousand PERSON entities to one resolution prompt does not
work. Block first: group candidates by cheap signals — same last name,
overlapping tokens — with a simple inverted index, no model call. The model
then only arbitrates within blocks of 50–100 candidates. Blocking recall is
the ceiling on resolution recall: two mentions that never share a block can
never merge, so keep blocking signals loose and let the model do the
precise work inside each block.

## Incremental updates

The graph accumulates; it never rebuilds.

1. Extract the new document.
2. Resolve its entities against the existing canonical set (per-type, with
   blocking) — not against the whole raw history.
3. Add only the new edges, tagged with their source document.
4. Re-summarize an entity only when its source-document set changes
   materially (new documents mentioning it, not just new edges).
5. Record processed documents in a state file so overnight runs are
   idempotent and resumable.

## Storage

NetworkX in memory works to a few hundred thousand edges. Beyond that, the
schema maps directly onto three Postgres tables:

```sql
entities(id, name, type, summary)
relations(source_id, target_id, predicate, source_doc)
aliases(entity_id, alias)
```

Only the persistence layer changes — the extraction and resolution prompts,
and the schema they share, are untouched by the migration.

## Production readiness checklist

Each element earns its place by the failure that appears without it:

| Element | Failure if missing |
|---|---|
| Gold set | No feedback loop; prompt changes are blind |
| Alias-map coverage | Scoring artifacts: recall looks worse than it is |
| Schema version | Incompatible entities from different prompt versions |
| Extraction cap | Unbounded cost from corpus ingestion errors |
| Resolution fallback | Silent entity loss: nodes disappear |
| Provenance tracking | Ungrounded answers; the evaluator cannot fact-check |
| Connectivity monitor | Fragmented graph: missed cross-document links |
| Human sample | Comprehension rot: the graph outgrows understanding |

The pipeline is not done when it runs. It is done when you can tell, on any
given morning, whether what it produced overnight was actually right — the
gold set, the provenance tracking, and the human sample are what make that
possible.
