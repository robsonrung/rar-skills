# Self-contained HTML page conventions

Rules shared by every skill whose deliverable is a rendered HTML page — `explain-architecture`, `html-explainer`, and `consensus-summary-html` load this file by path. Each skill keeps its own template, page anatomy, and validator; this file holds what they have in common so a new page skill starts from the same floor.

## Self-containment

- One `.html` file with inline CSS, JavaScript, and SVG. It opens from disk with no server and no build step.
- The only permitted external resource is a Google Fonts stylesheet, and every font face declares a real fallback stack. No remote scripts, tracking pixels, or required network calls.
- Head carries `<title>`, `lang`, charset, and viewport. The title names the subject.

## Three depths

The page must work at three depths, in this order:

- **Glance** — the first screen alone answers the reader's main question: a hero or a clickable big-picture map plus one-paragraph ledes.
- **Scan** — section summaries, cards, tables, small diagrams.
- **Descend** — expandable `<details>` panels holding the bulky evidence.

Nothing essential lives only at descend depth; nothing bulky lives above it. Put the most surprising fact of a section in its lede, not inside a panel.

## Navigation

- Every table-of-contents anchor and every clickable map element targets a real element id. Section ids are stable and named in the skill's page anatomy.
- Expand-all and collapse-all controls exist and are wired.
- Sections follow the reader's path through the subject (edge to inside, outcome to evidence), never discovery order.

## Honesty of the surface

- Status is marked with text as well as color; the page reads in grayscale and on a narrow screen (wide content scrolls inside its own container).
- A bar, ring, or number appears only for a value present in the source. A visual must not imply precision the source did not report.
- Missing data is shown as `Not reported` and named as a gap, never filled in.
- Leftover template tokens (`<!-- SLOT`, `{{...}}`, `TODO`, `Replace with`) are failures.

## Escaping

Escape `&`, `<`, `>` in code and quoted text **before** adding highlight spans. Generics such as `Promise<Foo>` are the classic silent loss; `&amp;lt;` anywhere means a double escape. Keep source labels (`path:line`, `report.md`) literal.

## What must never reach the page

Secrets, credentials, tokens, live hostnames, and content the source deliberately redacts — see `grounded-evidence.md` §6. Refer to the name of a secret and where it is resolved.

## Verification

1. Run the skill's validator until it exits 0.
2. When a browser is available, open the file and confirm the glance layer draws, one navigation click reaches its section, and the expand controls work at desktop and narrow widths.
3. Prefer DOM queries (section and `details` counts, anchor-to-id resolution, an expected generic present in `pre` text) over screenshots for everything below the first screen: `scroll-behavior: smooth` makes programmatic scrolling asynchronous, and a hidden preview pane returns stale screenshots. A headless Chrome full-page capture is the reliable way to see the whole page.
4. Without a browser, report that the mechanical check passed and the visual check did not run.

## Delivery

Lead with the output path, then how to navigate the page, then the sections in one line each. Name any part that could not be visually verified. Never present a page built from a partial or unverified source as final.

## Adding a page skill

Bring a template and a validator of your own, load this file in the assemble step, and keep everything page-specific (section ids, palette, component cheat sheet) in the skill's own `references/`.
