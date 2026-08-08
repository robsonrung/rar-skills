# Page Anatomy & Mechanics

Read this before replacing the template's slots. It defines what each region of the page is for, the SVG diagram rules, and the code-snippet formatting contract.

## Contents

1. [Region-by-region anatomy](#region-by-region-anatomy)
2. [SVG diagram mechanics](#svg-diagram-mechanics)
3. [Code snippet contract](#code-snippet-contract)
4. [Component cheat sheet](#component-cheat-sheet)
5. [Verification notes](#verification-notes)

## Region-by-region anatomy

The template is ordered glance → scan → descend. Keep that order.

| Region | Depth | Content |
|---|---|---|
| Header | glance | Title + pulsing dot; a 3–5 line subtitle saying what the system is, what the page covers, and how to navigate ("click a box / expand ▸ panels"). Name the service root path. |
| TOC chips + controls | glance | One chip per section (`#sec-…` anchors) plus the Expand-all / Collapse-all buttons (already wired to `setAll()`). |
| Big-picture map | glance | One SVG showing the whole request/data path plus external dependencies. Every major box is clickable via `jump('sec-…')`. A caption line names what the page deliberately leaves out. |
| Tech-stack grid | scan | One `.stack-item` per technology: name + version, one line of purpose, and the file path where it lives. Close with a drill panel of 3–4 cross-cutting concepts the reader will meet repeatedly. |
| Numbered sections (6–9) | scan + descend | Each: `h2` with colored `sec-num` badge, a lede paragraph (the section's whole story in 3–4 sentences), optional section diagram or flow steps, then 2–5 `details.drill` panels holding the code. |
| Footer | — | Generation date, service root, companion docs. |

Section ordering follows the data flow: infrastructure/edge first, then the request path inward, then data stores, then cross-cutting concerns (observability, quality) last.

**Lede discipline:** the lede must answer "what happens here and why does it matter" without opening any panel. Put the single most surprising fact of the section in the lede, not inside a panel.

## SVG diagram mechanics

Diagrams are inline SVG inside `.diagram` wrappers (`viewBox` around `1100 × 400–600`, `min-width: 720px` gives horizontal scroll on narrow screens).

**Z-order: arrows first.** SVG paints in document order. Draw all connection lines/arrows immediately after the background, then boxes. To fully mask arrows passing under a translucent box, draw an opaque rect first, then the styled rect on top:

```svg
<rect x="X" y="Y" width="W" height="H" rx="6" fill="#0f172a"/>
<rect x="X" y="Y" width="W" height="H" rx="6" fill="rgba(6,78,59,0.4)" stroke="#34d399" stroke-width="1.5"/>
```

**Clickable boxes.** Wrap each box in a group tied to a real section id; the CSS hover brightening is already defined:

```svg
<g class="clickable" onclick="jump('sec-auth')"> … </g>
```

**Spacing:** ≥ 40px vertical gap between stacked boxes; small connectors (buses, labels) live inside the gap, never overlapping a box. Legends/caption text go below everything, outside any dashed boundary; extend the viewBox rather than squeezing.

**Boundaries:** dashed rects for trust/VPC/cluster boundaries (`stroke-dasharray="8,4"`, amber) and for security elements (`stroke-dasharray="4,4"`, rose).

**Semantic palette** (fill rgba / stroke):

| Component | Fill | Stroke |
|---|---|---|
| Frontend / client | `rgba(8,51,68,0.4)` | `#22d3ee` |
| Backend / service | `rgba(6,78,59,0.4)` | `#34d399` |
| Database / storage | `rgba(76,29,149,0.4)` | `#a78bfa` |
| Cloud / infra | `rgba(120,53,15,0.3)` | `#fbbf24` |
| Security / auth | `rgba(136,19,55,0.4)` | `#fb7185` |
| Bus / async | `rgba(251,146,60,0.3)` | `#fb923c` |
| External / neutral | `rgba(30,41,59,0.5)` | `#94a3b8` |

Line meanings: solid slate = request/data flow; dashed rose = auth/identity; dashed other-color = whatever the caption says — always add one caption line decoding the line styles.

Font sizes inside SVG: 11–13px box titles, 8.5–9px sublabels, 8px annotations.

**Graph/flow diagrams** (state machines, pipelines): give loops a distinct color from the happy path, label conditional edges with the condition text, and mark human-pause points visually (⏸ plus dashed border).

## Code snippet contract

Every snippet lives in this structure (all classes exist in the template CSS):

```html
<div class="code"><div class="code-src">backend/svc/src/file.ts:123-141</div><pre>…</pre></div>
```

- The `.code-src` bar carries the repo-relative path and real line range. Append `(abridged)` or `(excerpt)` when lines were cut; cut whole lines only.
- Escape `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;` in snippet text **before** adding highlight spans. Generics (`Promise<Foo>`, `Record<string, T>`) are the classic silent loss.
- Optional manual highlighting with four spans only: `.c` comment, `.k` keyword, `.s` string, `.f` function/identifier. Highlight sparsely — comments and strings matter most; skip highlighting entirely for YAML/config.
- 5–20 lines per snippet. Longer means you're pasting, not explaining — cut to the load-bearing lines.
- Inline references in prose: `<code class="inline">symbol</code>` for identifiers, `<code class="path">dir/file.ts</code>` for paths.

## Component cheat sheet

All defined in the template CSS; copy usage from the template's example section.

| Component | Use for |
|---|---|
| `details.drill > summary + .drill-body` | Every descend-depth block. Summary = short claim + `<span class="hint">` file/topic hint. Panels nest one level max. |
| `.flow > .flow-step` | Numbered end-to-end sequences (auto-numbered circles). One step = one h4 + short p, optionally one snippet. |
| `.compare` | Two-column A/B (e.g., two data paths, two auth models). |
| `.chips` / `.chip` (+ `ev`, `write`, `cond` variants) | Event names, tool names, flags — anything enumerable. |
| `.callout` (`info`, `warn`, `danger`) | Caveats, trust boundaries, known limitations. War stories found in code comments belong here. |
| `table` in `.tbl-scroll` | Endpoint lists, tool inventories, config matrices. |
| `.stack-grid > .stack-item` | The tech-stack region only. |
| `.sec-num` + `acc-*` color classes | Section number badges; pick one accent per section and reuse it for that section's diagram boxes. |

## Verification notes

- The template CSS sets `scroll-behavior: smooth`, so programmatic `scrollTo`/`scrollIntoView` is **async** — reads of `scrollY` right after are stale. For automated checks prefer DOM queries over scroll-and-screenshot.
- Useful DOM assertions after assembly: every TOC `href="#…"` has a matching id; `svg` count ≥ 1; `details.drill` count ≥ 5; each `.code` contains a `.code-src`; searching all `pre` textContent finds an expected generic (proves escaping survived); no `&amp;lt;` anywhere (proves no double-escape).
- A hidden/backgrounded browser preview pane can return stale screenshots; if screenshots disagree with DOM queries, trust the DOM.
