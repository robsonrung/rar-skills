# Microkernel (plug-in) Architecture

**Class:** Monolithic (usually) · Technical *or* Domain partitioning — the only style that
can be either. Adapter/config plug-ins ⇒ technical; feature/extension plug-ins ⇒ domain.

## Topology
Two component types:
- **Core system** — minimal functionality to run; varies from bare (older Eclipse) to
  full-featured (Chrome). Holds the stable logic that rarely changes.
- **Plug-in modules** — standalone, independent components adding features, custom rules,
  or adapters. Should be independent of *each other*; keep inter-plug-in comms minimal.

A **plug-in registry** tells the core what plug-ins exist and how to reach them (name,
contract, protocol). Plug-ins connect as libraries/point-to-point (OSGi, Java modules,
.NET), as a namespace within one codebase (`app.plugin.assessment.iphone12`), or as remote
services (REST/messaging) — the remote form makes it a *distributed* architecture.

## When to consider
- Product-based apps with **planned extensions** released over time, or control over which
  users get which features.
- Multiple configurations per client/environment via adapter plug-ins (e.g. cloud-agnostic
  core with vendor-specific plug-ins).
- Per-jurisdiction / per-customer rule sets over a stable core (insurance claims, tax).
- Tight budget/time — simple and cost-effective like layered.
- Want evolutionary design: ship a minimal core, add plug-ins incrementally.

## When NOT to consider
- High scalability / elasticity / fault tolerance — all requests funnel through the core,
  which is the bottleneck and a single entry point.
- Most of your changes land in the **core** rather than plug-ins — you're not using the
  style's power; pick something else.

## Characteristics
Partitioning Technical or Domain · Cost $ · Agility ★★★ · Simplicity ★★★★ ·
Scalability ★ · Fault tolerance ★ · Performance ★★★ · Extensibility ★★★
