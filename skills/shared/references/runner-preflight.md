# Local runner preflight

`shared/scripts/runner_preflight.py` provides:

```python
check_claude(model, effort, cli_path=None, launch_context=None,
             *, working_dir=None, env=None)
```

Direct calls may omit the model or effort to use runtime defaults. Omitted
controls stay `unknown`; the helper does not select replacements or claim
support. An explicit model still receives its version check when effort is
omitted. Approved routes must retain their explicit controls.

Pass the exact approved model and effort, execution directory, and child
environment. The helper uses that environment's PATH and passes the directory
and environment to both local commands. It runs only `--version` and
`auth status --json`. It does not start inference, install software, or inspect
other skill trees by default. It discards raw authentication output.

The result has `blocked`, `reasons`, `checks`, and `evidence`. Each check has
`status` set to `true`, `false`, or `unknown`. Transport, CLI compatibility,
credential visibility, account entitlement, effort, and tools are separate
checks. A visible login is not proof of live authentication or model access.
Tool access stays unknown because this API takes no requested tool policy.

An unsupported configured effort, known incompatible version, an unknown version
when a minimum is required, unreadable
compatibility policy, missing CLI, or confirmed install drift blocks execution.
A local logout blocks only when the caller supplies
`launch_context={"auth_visibility": "full"}` after confirming credential
visibility in the execution context. Otherwise, logout stays unknown. Unknown
access is not a denial. Unknown compatibility is not a passed version check.
The runner must preserve these limits in its result.

`shared/runner-compatibility.json` holds minimum CLI versions and their evidence,
keyed by central seat names. The helper verifies each seat belongs to the runner
and matches the requested model against the loaded registry. Model IDs remain
in the registry.
The initial minimum comes from the reported CLI rejection, not an independent
provider test. The report records loaded configuration and policy paths,
resolved paths, content digests, CLI version and file metadata, and a context
digest. It never supplies a serving receipt.

## Installation evidence

`install-skills.sh` records `.rar-skills-install.json` at the installed skills
root after copying or linking. It records the source root and digests of routing
data and critical runner files. The manifest stays outside `shared/`, so a
linked installation does not write into the source tree.

Normal preflight calls `install_drift.check_loaded_install()` for the loaded
tree. A changed loaded file or available source file blocks dispatch. An absent
manifest means unknown provenance. An absent source tree means unknown source
status; it does not prove drift. For symlinked entry points, path resolution can
select the source tree. Call with the lexical installed root when the caller
needs to inspect that installation's manifest.

Existing installations can be checked without a manifest:

```python
check_loaded_install(installed_root, source_root=source_root,
                     approved_route=approved_snapshot)
```

The source comparison checks configuration and compatibility policy. An
approved snapshot must have exact `roles` with `seat`, `model`, `runner`, and
`effort`. Its optional `config_digest` must match. A mismatch blocks. This API
never edits or re-resolves the approved snapshot. Without a manifest, source
provenance remains unknown even when an explicit comparison finds matching
configuration. Script integrity needs a manifest.

For a read-only comparison, use:

```sh
python3 skills/shared/scripts/install_drift.py \
  --source-root /path/to/checkout \
  --installed-root /path/to/installed/skills \
  --seat sol --effort high
```

Use `--approved-route /path/to/approved.json` instead of `--seat` to check a saved
route. Exit 0 means the requested comparison passed; exit 1 means a mismatch or
unreadable input. Neither result proves provider access.

## Cache limits

`preflight_cache.py` stores stable capability fields only. It rejects live auth,
entitlement, serving receipts, quota, and request privacy fields. Full preflight
reports must not be cached. Extract stable checks when needed. Auth visibility
must be checked again in the actual execution context.

Recompute the fingerprint before lookup. It includes CLI path, resolved path,
file size, modification time, inode, version, loaded configuration and policy
digests, caller policy digest, and launch context. Pass `working_dir` and `env`
to `compute_fingerprint` when execution uses them. A CLI upgrade changes the
fingerprint. Missing fingerprints, old cache schemas, changed fingerprints,
and expired entries are misses. Cache status reports only age, not current
capability or authentication truth.
