---
name: knowledge-graph
description: Build and operate a knowledge graph from documents using four Claude prompts sharing one Pydantic schema — extraction, entity resolution, entity summarization, and graph-grounded querying — in place of four trained NLP systems. Use when the user wants to build a knowledge graph or GraphRAG pipeline, extract entities and relations from documents, resolve or deduplicate entity mentions, answer multi-hop questions across many documents, or give agents shared graph memory / a persistent world model. Includes the decision framework for when a graph is the wrong tool — not for single-document QA or single-hop retrieval (use direct prompting or RAG), and not for capturing session learnings into docs (that is capture-learning).
---

# Knowledge Graph: Four Models to Four Prompts

Building a knowledge graph classically required four trained systems — a
named-entity recognizer, a relation classifier, an entity-resolution engine,
and a summarizer — each with its own labeled dataset, its own training
pipeline, and its own domain-shift failures. Structured outputs collapse all
four into four prompts that share one Pydantic schema:
**the schema is the only training data**. Adapting to a new domain means
editing the schema and the prompt, not labeling and retraining.

Say it while working:

> "No NER model to train — the schema is the only training data; tightening
> the `type` Literal is our retraining step."

## When a graph is the right tool

Route before you build. A knowledge graph pays off only when facts must be
chained across documents, shared across agents, or checked with provenance.

| Scenario | Right tool | Why |
|---|---|---|
| Single-doc QA | Direct prompting or RAG | No chaining needed |
| Multi-doc, single-hop | RAG + reranking | Answer spans docs, no chaining |
| Multi-doc, multi-hop | Knowledge graph | Chaining requires entity linking |
| Multi-agent shared state | Knowledge graph | Workers need a shared world model |
| Evaluator needs ground truth | Knowledge graph | Fact-checking needs provenance |
| Overnight persistent loop | Knowledge graph | Memory must survive context flushes |

Say the routing-out sentence when it applies:

> "This is single-hop retrieval over one collection — RAG, not a graph;
> stopping here."

## The four-prompt pipeline

Two model tiers, chosen per stage: a cheap fast tier where the schema does
the work, a judgment tier where synthesis and conflicting evidence do.

| Prompt | Model tier | Why this tier |
|---|---|---|
| Extraction | Cheap/fast (e.g. Haiku) | High volume, schema-constrained |
| Resolution | Judgment (e.g. Sonnet) | Weighing conflicting evidence |
| Summarization | Judgment (e.g. Sonnet) | Synthesizing across documents |
| Querying | Judgment (e.g. Sonnet) | Multi-hop reasoning over triples |

Full schemas, prompt text, and code: [references/pipeline.md](references/pipeline.md).

### 1. Extraction

One call per document replaces both NER and relation classification: a list
of typed entities plus subject-predicate-object triples. Every prompt
guideline exists to fix a specific failure mode — keep all four:

- extract only entities central to the document → recall control
- one-sentence description grounded in that document → the disambiguation
  signal resolution depends on
- short verb phrases as predicates → constrained predicate vocabulary
- every relation connects two extracted entities → no orphaned edges

### 2. Entity resolution

Cluster surface forms into canonical nodes, one entity type at a time. The
one-line descriptions are the signal: they merge "Edwin Aldrin" with "Buzz
Aldrin" — zero character overlap, where string similarity fails outright —
and keep "Armstrong, first person on the Moon" apart from "Armstrong, jazz
trumpeter". Monitor the two failure modes: silent loss (a name left out of
every cluster) and over-merging (folding "Gemini 12" into "Project Gemini").

### 3. Entity summarization

Pool every mention plus the graph neighborhood into a cross-document profile
— hub nodes only, degree ≥ 3. Below that the single-document description
suffices; this is the expensive stage, so apply it selectively.

### 4. Graph-grounded querying

Serialize the k-hop neighborhood of a seed entity as
`(subject) --[predicate]--> (object)` triples and reason over them. k=2 is
the sweet spot: it captures the chains that make the graph valuable without
flooding the context. A grounded answer cites specific edges and states what
the graph does not contain; an ungrounded one draws on pretraining and cannot
be verified. On a private corpus, only grounded answers work at all.

## Precision over recall

A wrong entity is worse than a missing one: it spawns wrong relations that
propagate through every multi-hop chain that touches it, while a missing
entity is a visible gap. Tune extraction toward precision, and improve with
the harness loop: change the prompt, rerun the scorer against the gold set,
watch F1 move. Score through the alias map, or recall looks worse than it
is. Details: [references/evaluation.md](references/evaluation.md).

## The graph accumulates; it never rebuilds

When a new document arrives: extract its entities, resolve them against the
existing canonical set, and add only the new edges. Re-summarize a node only
when its source-document set changes materially. This discipline is what
turns the graph into agent infrastructure instead of a one-shot artifact:

- **Shared memory for orchestrator-workers** — workers read their relevant
  subgraph and write new entities back; the orchestrator's context stays
  small regardless of worker count.
- **Grounding layer for evaluator-optimizer** — the evaluator checks a
  generator's claimed triple against actual edges with provenance; feedback
  shifts from estimation to fact-checking.
- **Persistent world model for overnight loops** — state survives context
  flushes and session restarts. The agent forgets; the graph does not.

## Scaling and production

Cache the fixed system prompt and schema; push bulk extraction through the
Batch API at half price. Before resolution, block candidates by cheap
signals (shared tokens, same last name — an inverted index, no model call)
so the model only arbitrates within blocks of 50–100. NetworkX holds to a
few hundred thousand edges; beyond that, three Postgres tables (`entities`,
`relations`, `aliases`) — the persistence layer changes, the prompts do not.
The pipeline is done not when it runs, but when you can tell on any given
morning whether what it produced overnight was right: gold set, provenance
tracking, human sample. Full detail and the readiness checklist:
[references/scaling-production.md](references/scaling-production.md).

## Sources

Synthesized from Anthropic's public knowledge-graph construction cookbook
(claude-cookbooks) and "Building Effective Agents" (Anthropic Engineering).
Code patterns adapted from the public cookbook.
