# Review rules packs

A **review rules pack** is a skill that holds one repository's review rules and design decisions. A skill that checks a design or a change against repository rules finds the pack this way.

## Find the pack

1. First, a pack that the agent's instructions name for this repository.
2. Otherwise, any installed skill whose description says it is the review rules pack of this repository, by name. The description must name the repository, so another repository's pack never matches.

Load it through the host's skill mechanism. Read only the rules that match the paths or surfaces in scope.

## Report

Report the packs you read, or "no rules pack found". A named pack that cannot be read is a coverage gap: report it, and do not claim its rules were checked.

## What a pack returns to a calling skill

When another skill loads it, a pack returns the matching rule paths, their precedence, and any missing rule sources. It does not fix code or edit its own rule files; that happens only when the user invokes the pack directly.
