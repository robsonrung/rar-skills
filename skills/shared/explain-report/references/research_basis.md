# Research basis

Research checked on 17 November 2026. These sources informed the workflow. The renderer and report contract are original implementation, not a claim that any source provides this exact combination.

## Closest existing approaches

1. [Visual Explainer](https://github.com/nicobailon/visual-explainer), visual coding plans, architecture comparisons, plan audits, and HTML explanations. Borrow the idea of a navigable report; keep evidence collection and factual checking integral.
2. [CodeRabbit Change Stack](https://www.coderabbit.ai/blog/introducing-change-stack-the-first-ai-native-code-review-interface), semantic change groups, deliberate reading order, diff anchors, and implementation snapshots. Use a behavior focused reading path while keeping raw diff inspection optional.
3. [Microsoft CodeTour](https://github.com/microsoft/codetour), guided explanations anchored to code and revisions. Use precise evidence locations and preserve context across time without requiring an editor as the main interface.

## Architecture and planning foundations

1. [C4 model](https://c4model.com/), successive architecture abstractions and supporting diagram types. Show only levels useful for the change; keep each figure at one level.
2. [Architecture Decision Records](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions), context, choice, status, consequences, and retained superseded decisions. Preserve rationale and history.
3. [MADR](https://adr.github.io/madr/), problem, drivers, alternatives, outcome, consequences, and confirmation. Include the accepted cost and evidence needed to confirm the choice.
4. [OpenAI harness engineering](https://openai.com/index/harness-engineering/), versioned plans and decision logs, concise entry points, and progressive disclosure. Match documentation depth to task complexity.
5. [Anthropic SDLC playbook](https://claude.com/resources/articles/the-ai-native-sdlc-playbook), plans grounded in files, sequencing, tests, risks, and alternatives, followed by comparison against implementation.
6. [Claude Code best practices](https://code.claude.com/docs/en/best-practices), observable checks, actual command evidence, and review against the specification. Avoid claiming verification from a summary alone.
7. [GitHub Spec Kit plan template](https://github.com/github/spec-kit/blob/main/templates/plan-template.md), explicit technical context, repository structure, and justification of added complexity.
8. [OpenSpec concepts](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md), distinct proposal, behavioral specification, design, and tasks, with retained change history. Adapt existing project artifacts.

## Format rationale

Use HTML for progressive disclosure, linked detail, search, and local feedback. Generate Markdown from the same structured content for portability and version control. Use expanded print output for a static reading copy. PDF does not retain the exploration interface. Markdown presentation varies by viewer. A complex application or external service adds setup that most individual reports do not need.

Use native disclosure controls and readable semantic content. Maintain exact diagrams and text alternatives. AI generated artwork can illustrate concepts but is unsuitable as the authoritative map of real code relationships.

## Limits

These sources document designs and practices, not a controlled comparative trial proving this report workflow is superior. Vendor performance claims are not adopted as established results. A visually polished explanation still needs evidence. Structural validation, source review, and implementation verification remain separate activities.
