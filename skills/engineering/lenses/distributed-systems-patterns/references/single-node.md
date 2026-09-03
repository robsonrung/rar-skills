# Single-node patterns

Read when the family is single-node — two or more containers that must be a **coscheduled pair**.

## Contents

1. [Coscheduled pair test](#coscheduled-pair-test)
2. [Sidecar](#sidecar)
3. [Ambassador](#ambassador)
4. [Adapter](#adapter)
5. [Container API](#container-api)
6. [Reuse rules](#reuse-rules)

## Coscheduled pair test

A single-node pattern assumes:

- the containers are scheduled onto one machine as an atomic group (a pod, or the orchestrator's equivalent)
- they may share a network namespace (localhost), volumes, and optionally the PID namespace
- they fail and restart as a group; you do not independently place them

If the helper talks to the app over the cluster network, name it a service (or "distributed ambassador") and leave this file. That is serving-family work.

## Sidecar

The sidecar **augments** the application container, often without the app's knowledge.

| Use when | Do not use when |
| --- | --- |
| Add HTTPS, config sync, Git-pull deploy, or shared introspection (`topz`-style) to an app you will not (or cannot) change | The helper must be independently placed or scaled |
| You want one reusable utility image injected beside every app | The feature is the app's core business logic |
| Roll the helper without rebuilding the app image | The pair does not share the namespace the helper needs |

Typical pairs: TLS terminator on localhost; config-manager writing a shared file then signaling the app (`SIGHUP` / inotify / last-resort `SIGKILL` so the orchestrator restarts it); Git sync + auto-reloading server.

State it as: _"sidecar — the app stays ignorant; the helper is the **coscheduled pair**."_

## Ambassador

The ambassador **brokers outbound** calls. The app connects to localhost; the ambassador is the world.

| Use when | Do not use when |
| --- | --- |
| An existing client expects one backend, but production is sharded | You own the server and can put the shard router there more cheaply |
| The same app must run against SaaS in one env and a local VM in another (service broker) | The proxy is a cluster-wide service in front of many clients — that is a serving-layer root, not an ambassador |
| You need request splitting / teeing (10% experiment, shadow traffic) without changing the app | The app already has a maintained sharded client you trust |

Trade-off Burns names: shard-router-as-a-service simplifies clients and complicates the storage deploy; client-side ambassador does the reverse. Pick from team lines and whether the storage is off-the-shelf.

State it as: _"ambassador — the app's **container API** is localhost; sharding / brokering / splitting lives next to it."_

## Adapter

The adapter **normalizes inbound** interfaces so heterogeneous apps look the same to the platform.

| Use when | Do not use when |
| --- | --- |
| Metrics, logs, or health must match one platform contract (Prometheus, stdout, a readiness URL) | You own the app and changing it to the contract is cheaper than running a second container |
| The image is vendor/OSS and forking it would mean you now patch and rebase it | The adapter is doing business logic rather than presentation of an existing signal |
| You want CPU/memory isolation so a misbehaving exporter cannot starve the app |  |

Typical pairs: Redis + Prometheus exporter; app that logs to a file + Fluentd redirecting to stdout / a schema; MySQL + a thin HTTP health adapter that runs a real query.

Do not "just modify the image" when you do not own it. A slightly patched vendor image is more expensive than an adapter you can share.

State it as: _"adapter — the platform sees one interface; the app keeps its native one."_

## Container API

Treat every reusable container as a function. The **container API** is:

- inbound parameters (prefer env vars; document defaults with `ENV`)
- ports (`EXPOSE` plus a comment for what listens)
- files and shared volumes
- signals the helper will send or expect
- outbound calls the helper makes (APIs it consumes)

A change is breaking if an old invocation stops working _or_ silently changes load — Burns' `UPDATE_FREQUENCY` going from seconds to milliseconds is a break even though it still parses.

On `create` and `maintain`, name the parameters. On `review`, flag unnamed or renamed ones.

## Reuse rules

1. Parameterize. A sidecar with no knobs is a snowflake.
2. Keep the app image and the helper image independently releasable.
3. Document the image where operators will look (Dockerfile `EXPOSE` / `ENV` / `LABEL`).
4. Share the helper across apps. If only one app can use it, the **container API** is too specific.
5. Prefer off-the-rack helpers (exporters, proxies) over a bespoke image unless performance extremes require it.
