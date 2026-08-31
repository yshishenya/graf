# Development Process Harness

This directory is the extraction boundary for the reusable public harness. It
must contain only generic rules, schemas, validators, templates, self-tests and
adapter interfaces. GRAF product-specific capture, privacy, deletion, signing,
provider and production gates remain in this repository's adapter.

## Non-negotiable boundaries

- Never commit secrets, API keys, credentials, signed URLs, raw audio,
  transcript text, private meeting content or machine-specific absolute paths.
- Pin every harness version by immutable commit/tag and document migration and
  rollback.
- Keep root project instructions short; load active feature context explicitly
  from per-worktree state.
- Use one active Dev manifest and one installed app when a consumer has the same
  single-application requirement; do not create a hidden parallel runtime.

## Planned portable contents

- Feature claim and bounded-context schemas/validators.
- Changelog fragment and Legacy Impact templates.
- SHA-bound CI evidence and release-candidate contracts.
- Dev manifest adapter interface with lock/atomic-promotion semantics.
- Self-test, secret/path/provenance scan and clean sample-project quickstart.

## Portable package

`src/dev_harness` and `bin/harness-check` are dependency-free and contain no
product runtime or private product rules. From this directory, install in
another repository with `python -m pip install .` or run the CLI directly. The
sample project under `sample/` is the publish smoke fixture. The following
commands are the source-tree self-check and must work from a clean checkout:

```sh
(./bin/harness-check --self-test)
(cd sample && ../bin/harness-check --spec specs/001-example/spec.md)
(./bin/harness-check --package-root .)
```

The package scan is intentionally run before building or installing the
package: generated `build/`, `*.egg-info/` and bytecode files are not
publishable. A consumer may run the same checks from its CI after extracting
this directory as the repository root.

Project adapters may add real build, health, signing and deployment probes, but
must preserve the exact-SHA, loopback-only, one-active-target and fail-closed
contracts. Each published version is immutable SemVer and requires a checksum,
migration notes, secret/path scan and a rollback ref.

The current public release is pinned at
`https://github.com/yshishenya/graf-development-harness/releases/tag/v0.1.4`;
`v0.1.3` remains the rollback ref. A consumer must pin the immutable release
and update its migration notes and rollback ref together.
