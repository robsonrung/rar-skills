# Select tools by the missing signal

Use the repository's installed and configured tools first. A warning is a hypothesis. Tool confidence scores and healthy-looking dashboards are not proof of behavior preservation. The sources and selection rationale are in [research.md](research.md).

## Routing

| Missing signal | Candidates | How to use the signal | Main limitation |
| --- | --- | --- | --- |
| JS/TS unused files, exports, dependencies | Existing compiler/linter, then Knip | Check entry points, workspace aliases, framework plugins and runtime imports before deletion. | Incomplete graph/configuration creates false positives; published libraries have consumers outside the repo. |
| JS/TS structural smells | deslop-js; installed ESLint rules | Review aliases, cycles, duplicate types and type escapes with caller context. Check analyzer errors separately. | Lower-confidence findings require intent. Do not confuse the library `deslop-js`, its `deslop-cli` package and unrelated packages named `deslop`. |
| React state/effect and component smells | Existing React/ESLint rules; React Doctor for a relevant gap | Verify external synchronization and user-visible behavior before removing state/effects/memoization. | Framework context and referential identity matter; inspect version, network and telemetry behavior before running optional tools. |
| Python static issues or apparently dead code | Existing Ruff; Vulture for unused-code candidates | Prefer checks before fixes; use entry-point/whitelist knowledge for dynamic references. | Ruff distinguishes safe/unsafe fixes. Vulture's confidence is not a runtime reachability proof. |
| Go static issues | Existing compiler, `go vet`, Staticcheck | Check the affected package and call paths; use existing test scope. | Go commands can fetch missing modules. Local authorization is not download authorization. |
| Dependency rules and cycles | Existing architecture tests; dependency-cruiser | Enforce actual agreed boundaries and Dependency Rule, not a newly invented architecture. | A cycle indicates coupling, not the correct refactor. |
| Copy/paste candidates | jscpd or an existing clone detector | Investigate duplicated knowledge and a canonical implementation. | Similar text in separate bounded contexts may need to stay separate. |
| Suspicious patterns or security boundaries | Existing Semgrep/static-security rules | Use reviewed local rules. Route behavior-changing vulnerabilities to a separately authorized repair. | Syntax matches need context; scan scope, configuration and telemetry need inspection. |
| Tests that may pass for broken behavior | Existing mutation tooling; Stryker where applicable | Run a bounded mutation or fault injection around the changed contract. | Surviving mutants can be equivalent; mutation adds cost and is not required for every cleanup. |
| Broader, persistent debt assessment | Desloppify | Use mechanical/subjective evidence, triage and coherent project-level scanning when explicitly authorized. | Not a diff-only scanner. Do not inherit unbounded score targets, installation steps or broad edit permission from its output. |

For other languages, use the maintained compiler, linter, formatter in check mode, tests and dependency tools already present. Do not extrapolate deep language support from a generic pattern list. Disclose gaps.

## Adapters, not a mandatory tool suite

Before an optional tool runs, establish its exact package/binary, installed version, trusted configuration, target files, known false positives, output format, license, network/telemetry behavior and expected cost. Inspect whether the command modifies source or state. Use check-only output unless that specific fix has been reviewed and authorized.

Do not install or upgrade tools as part of ordinary cleanup. Never run an unpinned “latest” package merely because a README recommends it. Keep external service use and source uploads opt-in.

Prefer a targeted compiler/linter/test pass plus human-readable evidence to ten overlapping scanners. Deduplicate findings by root cause and location. If analysis fails, report analysis failure; do not convert an empty or partial result into “no issues.”

## Applying fixes

Run deterministic fixes only after confirming the rule, scope and resulting diff. A tool's “safe” label is useful evidence, not permission to ignore repository-specific contracts. Do not enable unsafe autofixes globally.

If a whole-project scan is required to establish reachability, disclose the broader read scope. It does not expand write scope. Exclude generated/vendor/secret content using reviewed configuration. Correct a proven entry-point configuration problem separately rather than silence the warning by deleting live code.

No package commands are hardwired into the skill. Discover the existing trusted command from the repo and report the exact command used. This avoids package-manager assumptions, ambiguous executable names and accidental downloads.
