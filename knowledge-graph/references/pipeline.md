# The Four Prompts: Schemas, Prompt Text, Code

Everything here shares one interface: `client.messages.parse()` with a
Pydantic model as `output_format`. The response validates against the schema
and comes back as a typed object with attribute access — no free-form text
to parse, coerce, or retry. Ten thousand documents produce ten thousand
valid objects with zero parse errors. That contract is what makes the schema
the only training data.

```python
from anthropic import Anthropic
from pydantic import BaseModel
from typing import Literal

client = Anthropic()
EXTRACTION_MODEL = "claude-haiku-4-5"   # cheap/fast tier
JUDGMENT_MODEL = "claude-sonnet-5"      # judgment tier
```

## Prompt 1 — Extraction

Replaces the trained NER and the trained relation classifier in a single
call per document.

```python
EntityType = Literal["PERSON", "ORGANIZATION",
                     "LOCATION", "EVENT", "ARTIFACT"]

class Entity(BaseModel):
    name: str
    type: EntityType
    description: str    # one line, for disambiguation

class Relation(BaseModel):
    source: str
    predicate: str      # short verb phrase
    target: str

class ExtractedGraph(BaseModel):
    entities: list[Entity]
    relations: list[Relation]
```

Prompt text — each guideline annotated with the failure mode it fixes:

```python
EXTRACTION_PROMPT = """Extract a knowledge graph from the document below.

Guidelines:
1. Extract only entities central to this document, not every name
   mentioned in passing.               # recall control
2. For each entity, write a one-sentence description grounded in what
   THIS document says about it.        # disambiguation signal for resolution
3. Use short verb phrases as predicates (e.g. "commanded", "launched
   from", "developed by").             # constrained predicate vocabulary
4. Every relation must connect two entities from your extracted entity
   list.                               # no orphaned edges

Document:
{text}"""

def extract(text: str) -> ExtractedGraph:
    response = client.messages.parse(
        model=EXTRACTION_MODEL,
        max_tokens=2048,
        messages=[{"role": "user",
                   "content": EXTRACTION_PROMPT.format(text=text)}],
        output_format=ExtractedGraph,
    )
    return response.parsed_output
```

Why the cheap tier: extraction is high-volume and schema-constrained — the
schema defines the entity types, enforces the structure, and eliminates
parsing errors, so the model has little judgment left to exercise. 10,000
documents at ~2,000 tokens each cost single-digit dollars at Haiku rates,
before prompt caching and batching (see
[scaling-production.md](scaling-production.md)).

## Prompt 2 — Entity resolution

Raw extraction yields overlapping mentions ("Neil Armstrong" / "Neil Alden
Armstrong"). Building the graph directly from them fractures one concept
across disconnected nodes. String similarity (edit distance, token Jaccard)
handles typos but fails outright on "Edwin Aldrin" vs. "Buzz Aldrin" — zero
character overlap, same person.

```python
class Cluster(BaseModel):
    canonical: str        # most complete form
    aliases: list[str]    # all surface forms

class ResolvedClusters(BaseModel):
    clusters: list[Cluster]
```

```python
RESOLUTION_PROMPT = """Below are {entity_type} entities extracted from a
document corpus, each with a one-line description from its source document.

Cluster the names that refer to the same real-world {entity_type}.
- Use the descriptions, not just the names: identical names with
  incompatible descriptions are DIFFERENT entities; different names
  with matching descriptions may be the SAME entity.
- Pick the most complete form as the canonical name.
- Every input name must appear in exactly one cluster (a cluster may
  contain a single name).

Entities:
{entities_with_descriptions}"""
```

Run it one entity type at a time — the focused input keeps clustering
tractable. The disambiguation power comes entirely from the one-line
descriptions written at extraction: "Armstrong, first person to walk on the
Moon" and "Armstrong, jazz trumpeter" share a name and must not merge. The
description replaces what a trained resolver would have learned from
domain-specific labels.

Failure modes to check after every run:

- **Silent loss** — an input name appearing in no cluster simply vanishes
  from the graph. Assert that the union of all cluster aliases equals the
  input set; route leftovers to a fallback (their own singleton cluster).
- **Over-merging** — a specific entity folded into a broader one ("Gemini
  12" into "Project Gemini") because descriptions overlap. Sample-review
  clusters whose aliases have low string similarity.

## Prompt 3 — Entity summarization

Each node initially carries only the one-line description from whichever
document mentioned it first. For hub nodes (degree ≥ 3), pool every mention
across documents plus the node's graph neighborhood and synthesize a proper
profile. Below degree 3, skip it — the single-document description is
usually sufficient and this is the expensive stage (one judgment-tier call
per entity, with multi-document input).

```python
class TimeRange(BaseModel):
    start: str    # YYYY or "unknown"
    end: str      # YYYY or "ongoing"

class EntityProfile(BaseModel):
    summary: str            # 2-3 paragraphs
    key_facts: list[str]    # 3-5 atomic facts
    time_range: TimeRange
```

```python
SUMMARIZATION_PROMPT = """Write a profile of {canonical_name} from the
evidence below. Use only the evidence provided — do not add outside
knowledge. Every key fact must be traceable to a mention or an edge.

Mentions across documents:
{pooled_mentions}

Graph neighborhood (direct relations):
{neighborhood_triples}"""
```

The result turns a graph of labels into a graph of knowledge: profiles that
no single source document contains, suitable for search results or as
context for downstream agents.

## Prompt 4 — Graph-grounded querying

Serialize the k-hop neighborhood of a seed entity as triples and let the
model reason over them.

```python
def serialize_subgraph(G, center, hops=2):
    nodes = {center}; frontier = {center}
    for _ in range(hops):
        nxt = set()
        for n in frontier:
            nxt |= set(G.successors(n))
            nxt |= set(G.predecessors(n))
        frontier = nxt - nodes; nodes |= frontier
    sub = G.subgraph(nodes)
    return "\n".join(sorted(set(
        f"({s}) --[{d['predicate']}]--> ({t})"
        for s, t, d in sub.edges(data=True)
    )))
```

```python
QUERY_PROMPT = """Answer the question using ONLY the knowledge-graph
edges below. Cite the specific edges you use, in the form
(subject) --[predicate]--> (object). If the graph does not contain the
information needed, say exactly what is missing — do not fill gaps from
general knowledge.

Graph edges:
{serialized_subgraph}

Question: {question}"""
```

Choosing k:

| k | Behavior |
|---|---|
| 1 | Fast and focused; misses indirect connections |
| 2 | The sweet spot — captures the multi-hop chains that justify the graph |
| 3 | May exceed the context window; needs filtering before serialization |

Grounded vs. ungrounded: without graph context the model answers from
pretraining — comprehensive, unverifiable, and useless on a private corpus.
With graph context the answer is constrained to extracted edges, traceable
edge by edge, and explicit about what the corpus does not say.
