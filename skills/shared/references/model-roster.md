# Model roster

[`model-routing.json`](../model-routing.json) is the single maintained source
for model IDs, aliases, adapter defaults, effort capabilities, task routes,
interview roles, and council selections. Edit that file to change a default.
Do not copy its tables into skills, templates, or runner scripts.

## Read and resolve

Resolve `SHARED_DIR` from the loaded shared skill, as
[the shared library](../SKILL.md) describes. These commands only read configuration:

```bash
SHARED_DIR="<absolute shared skill directory>"
python3 "$SHARED_DIR/scripts/model_routing.py" show
python3 "$SHARED_DIR/scripts/model_routing.py" resolve isolated-implementation --family gpt
python3 "$SHARED_DIR/scripts/model_routing.py" validate
```

Use `routes.<task>.families` to select roles. `models` resolves seats to exact
IDs and adapters. `effort_profiles` describes adapter capabilities; `runners`
defines direct-call defaults and accepted flags. `discovery` supplies probe
metadata. None of these fields proves account access or serving identity.
The native host can expose controls that differ from its external adapter;
verify the exact route with [host-model-execution.md](host-model-execution.md).

## Policy and evidence

Task defaults are policy, not a benchmark ranking verified by this repository.
The configuration records its evidence limit. Use captured acceptance results
to compare candidate routes; static validation does not establish equal quality,
fewer tokens, lower cost, or faster completion.

A CLI probe confirms a transport only. An envelope separates `requested_model`,
`configured_model`, and observed `effective_model`. Only a verified
`model_receipt` from a native or provider event identifies the serving model.
A configured label, wrapper echo, or self-description is not serving evidence.
A route with `model_verification: required` blocks without a matching receipt.
An `allow_unverified` route needs the authority specified by its caller.

## Availability and compatibility

A missing model or unsupported effort cannot cause a silent substitution.
Unlisted models need an explicit route and capability evidence; add maintained
defaults to the configuration before using them as library policy.
`conditional_models` records unavailable specialist candidates. Never substitute
an ordinary model for an unverified specialist identity.

Approved run plans and receipts are historical snapshots. Do not regenerate
an approved route from the latest defaults during retry or resume. The launcher
validates the recorded selection and preserves the caller's approval boundary.
