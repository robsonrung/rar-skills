# UI Prototype

Use this branch to answer one visual decision. If the question concerns logic or state, use [logic.md](logic.md).

## Choose the smallest form

1. Start with one fixture or static screen that uses safe data.
2. When comparing two concrete options can change the decision, use two screens. An explicit user request for a different bounded set controls.
3. Use an existing host page only when its real layout, navigation, density, or data context changes what the reviewer can observe.
4. Add a switcher only when the host page and a direct comparison are both necessary. Keep it inside the prototype work.

State the question and the observation that will answer it at the prototype location. Use the project's visual conventions only as far as they help the question.

## Build and review

Keep the fixture or screen in a scratch location or local worktree. Use fixtures, stubs, or memory backed data. Do not connect visual prototypes to real mutations.

Open the result in a browser and review the stated observation. Record the screen or option reviewed, viewport when it matters, observation, and limit. A model or DOM check does not verify visual usability. If browser review is unavailable, leave the visual decision open.

## Capture and dispose

Record the selected direction and why beside the caller's decision record or task plan. Keep the artifact only when it is useful evidence. **Prototype code never graduates**. A production task rebuilds the selected behavior under its acceptance contract.

Remove only routes, switchers, and fixtures created for this prototype. A commit or tracker update requires authorization.
