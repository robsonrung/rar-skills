# Deny-List Categories

The deny-list is the set of change categories automation must never approve, no matter how clean the diff reads. `scripts/gate_check.py` is the executable source of truth — the patterns below describe intent; when this file and the script disagree, the script wins and this file has rotted.

| Category | Why it is never auto-approved | Matched by (illustrative) |
|---|---|---|
| `auth` | Authn/authz mistakes are silent until exploited | `auth`, `oauth`, `saml`, `sso`, `login`, `session`, `permission`, `rbac`, `acl`, `mfa` as path words |
| `crypto-secrets` | Key and secret handling fails catastrophically, not gradually | `crypto`, `secret`, `vault`, `credential`, `token`, `password`, `jwt`, `signing` path words; `.env*`; `.pem`/`.key`/`.crt`/`.p12`/`.jks`; `id_rsa` |
| `migrations` | Schema changes and backfills are irreversible in production | `migrations/`, `alembic/`, `schema.rb|prisma|sql`, `structure.sql`, `.ddl`, `migration`/`backfill` path words |
| `infra-ci` | CI and infra changes can rewrite the safety rails themselves | `.github/workflows/`, `*.tf`, `terraform/`, `k8s/`, `helm/`, `Dockerfile*`, `docker-compose*`, Jenkins/GitLab/Circle/Buildkite config, `CODEOWNERS` |
| `billing` | Money paths need a human | `billing`, `payment`, `stripe`, `invoice`, `subscription`, `checkout`, `pricing`, `refund`, `payout` path words |
| `public-api` | Published contracts break other people's code | `openapi`, `swagger`, `*.proto`, `public_api`, `api_spec` |
| `dependencies` | Supply-chain surface; lockfile diffs are unreviewable by reading | Manifests (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Gemfile`, `pom.xml`, …) and all lockfiles |

## Design choices

- **Paths, not diff content.** Membership must be checkable without judgment, or the gate stops being deterministic.
- **The deny-list outranks the size exclusions.** `tests/test_login.py` is excluded from the size count and still a deny-list `auth` hit — a test encoding auth behavior is an auth change.
- **Over-matching is the intended failure mode.** `src/theme/tokens.ts` trips `crypto-secrets` on the word `tokens`; the cost is one unnecessary human look, while the missing-match cost is an unreviewed secret. Escalation is cheap; silence is not.
- **Word-delimited matching.** Words match only between `/`, `.`, `_`, `-`, or string edges, so `authors.py` is not `auth` and `certifi/` is not `cert`.

## Extending per repo

Add repo-specific rules at invocation, without editing the script:

```bash
python3 .agents/skills/approval-gate/scripts/gate_check.py --git origin/main HEAD \
  --extra-deny 'feature-flags=(^|/)flags?/' \
  --extra-deny 'analytics-schema=(^|/)posthog/hogql/'
```

Rules only ever add categories. There is deliberately no `--allow` override: narrowing the deny-list is a policy edit a human makes in the script, reviewed like any other change.
