# Bounded context packets

Use a short role brief with the goal, acceptance contract, settled decisions,
open questions, scope, and source locators. Keep complete evidence in files.
Choose which sections matter; do not compress a whole archive into the prompt.

Prepare a source list with absolute paths, authority (`decision`, `evidence`, or
`superseded`), and a section or line locator. At least one current decision source
is required. A superseded document is history, not an instruction.

```json
[
  {"path": "/project/prd.md", "authority": "decision", "locator": "Access and acceptance"},
  {"path": "/project/research.md", "authority": "evidence", "locator": "Current authorization path"}
]
```

```bash
python3 <shared-dir>/scripts/context_packet.py prepare \
  --brief <brief.md> --sources <sources.json> --output <brief.md.packet.json>
python3 <shared-dir>/scripts/context_packet.py verify --packet <brief.md.packet.json>
```

The default limit is 24,000 bytes for the derived brief. Use a larger explicit
`--max-bytes` only with a recorded reason. The approved task contract is separate;
the launcher still includes it in full. The packet hashes the brief and source
revisions. Only an exact task status line can change without changing a decision
hash. If decisions change, revise the affected brief and create a new packet path;
never replace old evidence to conceal drift.

The launcher checks a packet named `<brief-file>.packet.json` before dispatch.
New workflow runs use this binding. Legacy briefs remain readable. Direct interview,
design, and handoff callers run `verify` themselves before dispatch. A hash detects
drift, not a semantic contradiction already present in the brief; resolve that
contradiction against the current user decisions before sending the packet.
