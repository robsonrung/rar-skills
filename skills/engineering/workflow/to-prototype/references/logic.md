# Logic prototype

One self-contained HTML file that lets anyone drive a state model by clicking. Use it when the question is about business logic, state transitions, or data shape: things that read fine on paper and feel wrong once pushed through real cases. Because it needs nothing installed, a designer, PM, or domain expert can open it and feel the model, so it speaks their language. For "what should this look like", use [ui.md](ui.md).

**Write the question at the top of the page**, in a visible intro, so anyone returning later can check the demo answers it.

**Keep the logic a pure module** in one `<script>` block: a reducer `(state, action) => state`, an explicit state machine when "which actions are legal now" is part of the question, pure functions over plain data, or a small class when the logic truly owns ongoing state. Pick the shape that fits the question, not the one easiest to wire. The module never touches the DOM; the page calls into it.

**Build the page** in plain inline HTML, CSS, and JS: no framework, bundler, or server, so it opens by double-click and survives email. Label everything in domain language. Top to bottom:

1. Title and a one-line explanation.
2. Current state as a labelled panel, not raw JSON, re-rendered after every click, with what just changed called out.
3. Free-play buttons, one per action, always available.
4. Guided scenarios in tabs: a short description of the situation and what to watch, then the ordered buttons to press. Starting one resets to a known state. Cover the happy path, a tricky edge case, and an attempt at something that should be illegal.

Keep it restrained: clean type, generous spacing, one accent color, no animation. Use in-memory state unless persistence is the question, add assertions only where they make the observation trustworthy, and never generalize for a later case.

Hand it over. The useful moments are "wait, that shouldn't be possible" and "I assumed X would differ": bugs in the idea. Add actions or scenarios as asked, then capture the answer as the skill describes.
