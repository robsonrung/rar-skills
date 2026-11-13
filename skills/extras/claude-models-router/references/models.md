# Claude models: facts snapshot

Model guidance and benchmark figures: [Which Claude model should you build with?](https://claude.dev/blog/which-claude-model-should-you-build-with/), published 2026-11-09. The figures are Anthropic's own runs, and several differences are within run-to-run noise. Plan rules: Anthropic's [usage limits](https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work) and [Claude Code plan](https://support.claude.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan) articles, its [pricing page](https://claude.com/pricing), and the Claude Code [cost](https://code.claude.com/docs/en/costs) documentation, read 2026-11-10.

## Side by side

|  | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 | Fable 5.2 |
| --- | --- | --- | --- | --- |
| Built for | High-volume, simple tasks | Fast help with well-scoped tasks | Daily complex coding and knowledge work | The most ambitious, open-ended technical work |
| Latency | Fastest | Fast | Moderate | Moderate |
| Thinking | Adaptive, can be turned off | Adaptive, on by default | Adaptive, always on | Adaptive, always on |
| Effort in Claude Code | Not stated | `medium` | `medium` | `medium` |
| On a subscription | Every paid plan | Every paid plan | Every paid plan | Own weekly limit on Max and Ultra; usage credits on Pro |

Every model has a 1M-token context window and a 128K-token maximum output. `/effort status` shows the effort a session uses. Fable 5.2 generates output up to 30% faster than Fable 5.1, and Sonnet 5.5 runs 30% faster than Sonnet 5.

## Quality evidence

How much a result changes with effort, on Opus 5.5 and SWE-bench Pro, relative to `high`. The source reports cost, which on a single model tracks token usage:

| Effort | Score | Usage |
| --- | --- | --- |
| `low` | About 8 points lower | About one third |
| `medium` | About 2.5 points lower | About 70% |
| `xhigh` | About 1.4 points higher | About 2.5 times |

- On the same subset, `low` with failures rerun at `high` passed about 97% of tasks. Running every task at `high` passed 95.3% and used more.
- A smaller model at the right effort can match a bigger one at its ceiling. On Terminal-Bench 3.0, Opus 5.5 at `high` scored 58.9% with half the tokens of Fable 5.1 at `max`, which scored 58.0%.
- The reverse also holds at the top. On FrontierCode 2.0, Fable 5.2 at `high` scored 45.3% against 45.5% for Opus 5.5 at `max`, at roughly half the API cost per task.
- The hardest tasks dominate. On one 20-problem search benchmark, two problems accounted for 43% of the total.
- Small models do well on high-volume work with checkable outputs and are less suited to long agentic loops.

## Subscription limits

- Two limits apply: a session limit that resets every five hours and weekly limits. Verified Ultra accounts have no five-hour limit.
- The Claude apps, Claude Code, and Claude Desktop share them, and a subagent's requests draw on them too.
- Usage depends on the model, the effort level, and the length of the conversation. Higher effort uses more tokens, and long conversations that trigger context management use more.
- Anthropic publishes no usage ratio between models. As a rough proxy only, API list prices run about 1 to 20 to 40 to 80 from Haiku 5.5 through Sonnet 5.5 and Opus 5.5 to Fable 5.2. Sonnet to Opus is a two-fold step, so a failed Sonnet attempt retried on Opus costs more than Opus alone.
- Agent teams use about seven times the tokens of a standard session when teammates run in plan mode.
- A rate limit never switches the model. At the limit the choices are to wait for the reset or to turn on usage credits, which bill at API rates.
- `/usage` shows the plan's usage bars and a breakdown by skill, subagent, plugin, and MCP server, over 24 hours or 7 days.

## Compare two models on your own work

1. Take one real task with a check that decides success: a passing test, a correct row count, a review against the acceptance criteria.
2. Run it on the lighter candidate and on the next tier, each in a fresh session, switching with `/model`.
3. Compare the results first. Keep the lighter model only when the difference is one the user would not notice.
4. Then compare what `/usage` reports, to learn what the heavier model would cost in the window.
