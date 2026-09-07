# Grounding validation

Use this after the solution document is written. A flag is evidence to adjudicate, not permission to ignore or rewrite blindly.

## Evidence sources

Verify code behavior against the current working tree. Verify merge state against the forge or tracker when it is available. If remote state cannot be checked, qualify the claim as time-bound and report degraded verification.

## Resolve each validator flag

| Flag | Resolution |
| --- | --- |
| Missing path or link | Correct the citation or remove the claim. |
| Deliberately removed path | Mark the citation as historical. |
| Unreachable or local-only commit identifier | Prefer the reviewed change reference or remove it. |
| Draft placeholder | Replace it with a real value. |
| Behavior claim without defining source | Add the source evidence, attribute it to the session, or remove it. |

After an edit, run the mechanical validator again. Finish only when every remaining flag is explicitly confirmed intentional.

## Independent check

Use one read-only reviewer only when the document makes material claims that current source and validator output cannot settle. Give that reviewer the document and the specific claims to check. Correct contradicted claims and soften unverifiable ones. Do not add a review pass for routine, well-cited documentation.
