# Command discovery

How to find a repository's own verification commands without assuming a toolchain. The output of this procedure is the `commandSurface` block of the result: the build systems present, the package manager, and one concrete command per rung of install → build → typecheck → lint → test, each tagged with where it came from.

## Precedence

For each rung, take the first source that yields a command:

1. **Named repo scripts** — the repo's own aliases carry its flags and environment.
2. **CI config as read-only oracle** — the commands CI runs are, by definition, what the repo treats as gating.
3. **Task runners** — Makefile / justfile targets.
4. **Reconstructed tool invocations** — only when nothing above names the rung (`npx tsc --noEmit`, `cargo check`, `go vet`); tag these `source: reconstructed` and hold their failures to more scrutiny, since the flags are yours, not the repo's.

## Detection by build system

| Evidence | Build system | Where the commands live |
|---|---|---|
| `package.json` | Node | `scripts` block; `packageManager` field names npm/pnpm/yarn/bun and its version. Lockfile disambiguates when the field is absent (`package-lock.json` → npm, `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn, `bun.lock*` → bun). |
| `pnpm-workspace.yaml`, `workspaces` in package.json, `turbo.json`, `nx.json` | Node monorepo | Same scripts, plus a native scoping mechanism (see below) |
| `Makefile`, `justfile` | Make / just | Targets named `test`, `lint`, `check`, `build`, `typecheck` |
| `Cargo.toml` | Rust | `cargo build` / `cargo check` / `cargo clippy` / `cargo test`; workspace members support `-p <crate>` |
| `go.mod` | Go | `go build ./...` / `go vet ./...` / `go test ./...`; scope by package path |
| `gradlew`, `build.gradle*`, `pom.xml` | JVM | `./gradlew build test` / `mvn verify` |
| `pyproject.toml`, `tox.ini`, `setup.cfg` | Python | Named tool configs (`ruff`, `mypy`, `pytest`, `tox -e`); prefer a `Makefile`/script wrapper when one exists |

A repo can match several rows; run each surface it matches.

## Rung mapping

| Rung | Typical names to look for |
|---|---|
| install | `npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`, `bun install`, `pip install -e .`, `cargo fetch` — always the lockfile-respecting form when one exists |
| build | `build`, `compile`, plus any dependency-build prerequisite the repo's scripts or docs name (some monorepos require building shared packages before anything else typechecks) |
| typecheck | `typecheck`, `tsc`, `check-types`, `mypy`, `cargo check` |
| lint | `lint`, `eslint`, `clippy`, `ruff`, `vet` |
| test | `test`, `vitest`, `jest`, `pytest`, `cargo test`, `go test` |

Some repos fold several rungs into one script (`check`, `verify`, `ci`). Running that one script and recording it once is correct — do not also run its constituent parts.

## Scoping mechanisms

When the diff maps cleanly onto workspace roots, prefer the repo's native affected-scoping:

| Mechanism | Invocation shape |
|---|---|
| npm workspaces | `npm run <script> --workspace=<name>` |
| pnpm | `pnpm --filter <name> <script>` |
| yarn workspaces | `yarn workspace <name> <script>` |
| Turborepo | `turbo run <script> --filter=<name>` |
| Nx | `nx affected --target=<script> --base=<base>` |
| Cargo workspace | `cargo <cmd> -p <crate>` |
| Go | `go test ./path/to/pkg/...` |

Root-level rungs (repo-wide lint, typecheck of a single tsconfig) still run at the root even when tests are scoped.

## What discovery must not do

- Never write to `package.json`, CI config, or any config file to make a command exist.
- Never install a tool globally to reconstruct a missing rung; a rung with no command is `not-applicable`.
- Never guess flags that change semantics (e.g. `--force`, `--no-verify`); reconstructed commands use the tool's plain defaults.
