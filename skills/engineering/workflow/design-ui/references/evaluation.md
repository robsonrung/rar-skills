# Evaluation and iteration

## Separate evidence

Distinguish visual preference, reference fidelity, functional verification, and usability validation. Agent criticism can help with the first three. It cannot substitute for observations of representative people. A model score is not a probability of quality, a compliance certificate, or a measured business outcome.

## Define the acceptance contract

Before implementation, identify primary tasks, critical actions, success and failure outcomes, relevant states, target viewports, and meaningful constraints.

Use separate gates for task completion, blocking accessibility problems, responsive behavior, technical integrity, and fidelity when required. Record pass, fail, unverified, or not_applicable with reasons and evidence.

A concept may pass visual selection while behavioral gates remain unverified. Never present this as a verified application.

## Compare candidates

Hold brief, content, state, and viewport constant. Label alternatives neutrally without exposing author, model, favored candidate, previous scores, or desired scores. Show the relevant images together.

Ask for A, B, or no clear winner, specific evidence, tradeoffs, and uncertainty. For a close choice, swap presentation order or request a second fresh comparison. Keep approved references as stable anchors.

Assess hierarchy, type, spacing, density, composition, semantic color, imagery, and product fit. Do not reward novelty that makes common work harder.

If numerical scoring is requested, define criterion anchors first. Keep critical failures separate. Do not reveal a desired score as an approval cue or prompt the reviewer to increase its grade.

## Inspect actual renders

Capture desktop and mobile, plus tablet where its layout differs materially. Use screenshots from the checked version. Record route, viewport, state, and version or content fingerprint. Prefer existing project tools.

Compare reference and result under equivalent conditions. Wait for content and fonts. Stabilize variable dates, fixtures, and animation timing where practical. Do not mask genuine defects to pass comparisons.

Inspect composition, hierarchy, density, line breaks, alignment, spacing, contrast, data formatting, images, cropping, icons, overflow, scrolling, sticky controls, and obstructing overlays. Include relevant loading, empty, error, selected, focus, and success states.

Use pixel diffs for regressions against an accepted render in consistent conditions. Do not make a raster concept an exact pixel regression baseline. Low pixel difference does not prove quality.

## Exercise UX

Drive a realistic primary journey and verify its observable outcome and recovery path.

1. Pricing workspace, locate a listing, select dates, preview an override, save, verify the changed state, and recover from invalid values.
2. Operations table, filter records, inspect details, perform an allowed action, and return without losing useful context.
3. Onboarding, encounter validation, correct it, go backward without data loss, and finish.
4. Checkout prototype, change quantity, understand totals, correct input, and reach a clearly simulated confirmation.

Check keyboard access, visible focus, focus movement, names and labels, associated field errors, reading order, and appropriate status feedback. Use semantic HTML and existing accessible primitives. Measure contrast when relevant. Refer to the applicable current standard instead of inventing universal thresholds.

Check supported reflow, zoom, touch, reduced motion, and content extremes. Automated checks cover only part of accessibility. State what was tested without claiming complete conformance from a scan.

Use focused behavior tests and existing repository checks for changed functionality. Do not add implementation coupled assertions or broad test suites for trivial visual changes.

## Independent review

Give reviewers the task, acceptance criteria, approved direction, existing system, actual artifacts, checked version, reproduction information, and real constraints.

Withhold the builder's self praise, preferred verdict, target numeric score, and previous reviewer scores. Preserve genuine user preferences.

Require category, severity, location, observable evidence, user impact, proposed correction, and recheck. Vague praise or "make it premium" is insufficient.

For complex work, split visual craft from UX and accessibility review. Parallelize observation while one integrator reconciles findings and makes edits. Avoid concurrent agents overwriting the same files.

## Stop and preserve evidence

Fix the largest issues first and keep each pass small enough to assess. Recapture changed states and rerun relevant checks. Preserve the best verified version.

Stop successfully when required gates pass and no significant finding remains in scope. Stop optional aesthetic refinement at the available budget or after consecutive passes without material improvement. Continue feasible necessary fixes to required behavior. If a real access, capability, or task budget constraint leaves a gate unresolved, report incomplete status and the concrete blocker rather than inventing a passing score.

Tie evidence to the version checked.
