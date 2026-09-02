# Global Search: Questions the Whole Graph Owns

Local search starts from a seed entity and walks k hops. Two kinds of question defeat it structurally, not marginally:

- **No seed exists.** "What themes run through this corpus?" names no entity to start from.
- **The answer is a property of the graph, not of any node.** Recurrence, coverage, which concerns cluster together — no neighborhood contains it, because it is about the shape of the whole.

Global search answers both by summarizing the graph once, in pieces sized to fit a context window, and then reasoning over the summaries instead of over the corpus. Three stages: detect communities, write one report per community, answer by map-reduce over the reports.

The economics are the point: report cost scales with the number of communities, not with the size of the corpus, and reports are built once at ingest. A global question then reads a few dozen summaries — never the documents.

## 1. Detect communities

Louvain over an undirected projection. Direction carries meaning at query time; for clustering it only fragments what belongs together.

```python
from networkx.algorithms.community import louvain_communities, louvain_partitions

def detect_communities(G, resolution=1.0, seed=0):
    return louvain_communities(G.to_undirected(), resolution=resolution, seed=seed)
```

`resolution` is the one knob: below 1 it favors fewer, larger communities; above 1, more and smaller ones. Pass `seed` — Louvain is randomized, and an unseeded run makes every rebuild a different graph to reason about.

For a hierarchy, take the levels instead of the flat partition. `louvain_partitions` yields finest first, coarsest last: report at a coarse level for broad questions, descend a level when the coarse reports come back as generalities.

```python
def community_levels(G, seed=0):
    return list(louvain_partitions(G.to_undirected(), seed=seed))
```

## 2. Write one report per community

One judgment-tier call per community over its entities and the edges _internal_ to it — same `client.messages.parse()` contract as the other four prompts.

```python
class CommunityReport(BaseModel):
    title: str               # 3-6 words, names what connects the members
    summary: str             # 1-2 paragraphs
    key_findings: list[str]  # 3-7 atomic claims, each traceable to an edge
    entity_names: list[str]  # canonical names, for provenance
```

```python
COMMUNITY_REPORT_PROMPT = """Write a report on the cluster of entities below.
Use only the entities and edges provided — do not add outside knowledge.

Title the cluster by what actually connects its members. Every key finding
must be traceable to a specific edge or entity profile below. If the members
share no coherent theme, say that in the summary rather than inventing one.

Entities:
{entity_profiles}

Edges inside the cluster:
{internal_triples}"""
```

"Say so rather than inventing one" is load-bearing: asked to name a theme, a model will always produce one, and a fabricated theme in a report becomes a fabricated finding in every answer that cites it.

## 3. Answer by map-reduce

| Step | Tier | What it does |
| --- | --- | --- |
| Score | Cheap/fast | Rate each report 0–100 for relevance to the question |
| Map | Judgment | Partial answer from each surviving report, citing findings |
| Reduce | Judgment | One answer, naming the communities it drew on |

Scoring is a schema-constrained filter, so it belongs on the cheap tier and runs across every report. Keep the top reports that fit the context budget and drop the rest — then say how many were dropped.

```python
class Relevance(BaseModel):
    score: int      # 0-100
    reason: str

class PartialAnswer(BaseModel):
    contributes: bool          # False when the report says nothing useful
    answer: str
    findings_used: list[str]   # verbatim key_findings, not paraphrases
```

```python
REDUCE_PROMPT = """Answer the question from the partial answers below, each
produced from one community of the knowledge graph.

Attribute each claim to the community it came from. Where partials disagree,
report the disagreement — do not average it away. State the coverage: you saw
{used} of {total} community reports.

Question: {question}

Partial answers:
{partials}"""
```

A global answer that does not state its coverage reads as a statement about the corpus when it is a statement about the reports that fit in the budget.

## 4. Refresh, don't rebuild

Reports follow the same discipline as hub-node profiles: recompute only what moved. Store each report against a hash of its member set; after an incremental update, re-detect communities and rewrite only the reports whose membership hash changed. A corpus that grows 2% does not need 100% of its reports rewritten.

## Failure modes

| Failure | Symptom | Fix |
| --- | --- | --- |
| One giant community | A single report covering everything, in generalities | Raise `resolution`, or take a finer level from `louvain_partitions` |
| Singleton dust | Dozens of one-node communities with nothing to report | Lower `resolution`; fold degree-1 nodes into their neighbor's community before reporting |
| Stale reports | An answer cites entities that resolution has since re-canonicalized | Refresh on membership-hash change; never serve a report older than its community |
| Findings with no edge | Answers sound authoritative and cannot be traced | Require every `key_finding` to name its edge; sample-check per run |
| Unseeded clustering | Communities differ between runs; report cache never hits | Pass `seed` |
