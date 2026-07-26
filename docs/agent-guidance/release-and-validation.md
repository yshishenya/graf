# Release And Validation

## Local Validation

Use the feature `quickstart.md` first when working inside a Spec Kit slice. For
repository-wide local validation, use:

```sh
infra/scripts/ci-local.sh
```

This is the canonical local gate for Crisp. Prefer it over ad hoc validation
when closing a feature or preparing a deploy.

Use targeted tests during development, but do not replace the feature
quickstart or canonical local gate with a narrow command when the change touches
shared behavior, privacy, auth, storage, infrastructure, user-facing flows,
UX/QA expectations, operations, release readiness, or shared code paths.

## Validation Lanes

Every change must record one risk/validation lane in the final response or PR.

- **Read-only investigation**: no tests required; report inspected sources and
  limits.
- **Docs-only / mechanical**: review the rendered wording or template diff; run
  a focused markdown/template check when one exists.
- **Tiny low-risk code**: run the focused test or lint command for the touched
  path. Add one small runnable check when the change adds non-trivial logic.
- **Active Spec Kit slice**: use `quickstart.md` and focused tests during
  development. Run `infra/scripts/ci-local.sh` once at closeout when behavior,
  shared surfaces, UX/QA expectations, operations, release readiness, or code
  paths changed.
- **Significant or high-risk feature**: run the feature quickstart and
  `infra/scripts/ci-local.sh` before closeout/PR.
- **Release / deploy**: run the CD dry-run and execute only after the release
  gate is met and approved.

Do not rerun full local CI after every small edit inside a slice. Accumulate
focused checks while developing, then run the repository gate at the closeout
boundary required by the lane.

## Public macOS Signing And Migration

The active public macOS path is Developer ID-only. A releasable app uses
`Developer ID Application`, a published package uses `Developer ID Installer`,
and both artifacts require Apple notarization, stapling and Gatekeeper
acceptance. Set `GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1` for the public candidate;
the builder and validator must fail closed before public files or the appcast
change when an identity is local, self-signed, ad-hoc, owner-only or missing.

The current published reference is `v2026.07.26.8`: it passed Apple
notarization, stapling, Gatekeeper assessment and a real Developer ID →
Developer ID Sparkle update from `2026.07.26.7`. Use the [release note](../releases/v2026.07.26.8.md)
and [production receipt](../deployments/2brain-rec/release-v2026.07.26.8.md)
as the evidence template for the next release.

The published `v2026.07.26.6` is a one-time migration bootstrap from the
historical local/self-signed predecessor. Validate that transition with
`apps/macos/Installer/Scripts/validate-developer-id-bootstrap.sh` and install
the notarized `.pkg` manually. The migration validator forbids an update ZIP
and appcast; keep the live appcast unchanged for this step. After that manual
installation, use the ordinary `validate-app-updates.sh` path only with a
Developer ID predecessor and candidate, preserving bundle ID, team identity,
designated requirement, feed URL and Sparkle trust generation.

`build-trust-bootstrap.sh` and `validate-manual-update-bootstrap.sh` concern
Sparkle Ed25519 trust-generation custody/rotation. They are not Apple
code-signing migration tools. Local/self-signed/ad-hoc commands may remain in
historical receipts or disposable fixtures for negative tests, but are never a
public release fallback.

## Dependency Updates

Use the latest stable dependency versions by default. Before adding or updating
dependencies, refresh the package index with the project package manager instead
of relying on memory or old lockfile state.

For the server app:

- update `apps/server/pyproject.toml`, `apps/server/uv.lock`, and
  `apps/server/constraints.txt` together when runtime dependencies change;
- regenerate `apps/server/constraints.txt` from the lockfile so the production
  Docker image installs the same validated runtime package set without dev
  tools;
- run `uv lock --upgrade` and `uv tree --outdated` to prove whether direct
  dependencies are current;
- avoid prerelease versions unless the user explicitly accepts that risk;
- keep an older pin only with an adjacent reason, owner, and recheck trigger.

Runtime dependency upgrades are significant maintenance when they affect backend
frameworks, auth, storage, database, infra, or shared behavior. Use the relevant
Spec Kit lane and finish with `infra/scripts/ci-local.sh` before closeout.

## Production Deployment And Smoke

Deployment is remote-first and gate-driven:

```sh
infra/scripts/cd-remote.sh --dry-run
infra/scripts/cd-remote.sh --execute
```

Only run `--execute` when the release gate is met. Production deploy/smoke work
must preserve:

- clean or intentionally accounted working tree;
- branch/ref sync with the intended remote;
- pinned commit SHA;
- backup and restore rehearsal evidence where required;
- secret scans;
- health checks and smoke evidence;
- metadata-only evidence.

`--skip-local-ci` bypasses local CI only; it does not bypass production gates.

## Changelog

Maintain `CHANGELOG.md` in the repository root.

Every implemented feature slice that changes behavior, architecture, UX, QA
expectations, operations, or release readiness must update `[Unreleased]` before
merge.

Keep entries grouped by:

- `Added`
- `Changed`
- `Fixed`
- `Security`
- `Docs`
- `Ops`

Include feature, issue, or task references when available.

## Versioning

Every release must have a version tag, a GitHub Release, and a human-written
Russian changelog entry. Do not ship a release from a floating branch name or
from a tag that has no release notes.

Use this versioning policy:

- Product apps, deployed services, and release-train bundles use Calendar
  Versioning: `vYYYY.MM.DD.N`, where `N` starts at `1` and increments for
  multiple releases on the same day. Example: `v2026.06.18.1`.
- Libraries, CLI tools, reusable Spec Kit extensions, bootstrap wrappers, and
  anything consumed as a dependency use Semantic Versioning:
  `vMAJOR.MINOR.PATCH`.
- Use SemVer `MAJOR` for breaking API/CLI/workflow compatibility changes,
  `MINOR` for backward-compatible features or new capabilities, and `PATCH` for
  fixes, docs, reliability, or operational quality improvements.
- Do not put a descriptive slug in the stable tag. A tag such as
  `v2026.06.18.1-release-rules` is harder to sort and may be interpreted like a
  prerelease by tooling. Put the readable postfix in the GitHub Release title
  instead, for example `v2026.06.18.1 - release-rules`.
- Use prerelease suffixes only for real prereleases: `-alpha.N`, `-beta.N`, or
  `-rc.N`.
- If a repository already has a published versioning scheme, do not switch it
  silently. Document the migration in `CHANGELOG.md`, explain why the old scheme
  no longer fits, and make the next release notes explicit.

Product release command:

```sh
./scripts/prepare-release.sh YYYY.MM.DD.N
```

For example:

```sh
./scripts/prepare-release.sh 2026.06.18.1
```

Use `patch`, `minor`, or `major` only in repositories that are intentionally
still using SemVer. In a CalVer product release train, pass the full version
explicitly so the date and same-day release counter are deliberate.

Then review `CHANGELOG.md`, commit release prep, create the matching tag, and
push the branch and tags only when the user approves the release action.

## Release Notes

Каждый GitHub Release должен быть написан простым русским языком:

- не смешивай русский текст с английским инженерным жаргоном, кроме буквальных
  названий продуктов, команд, тегов, файлов, протоколов и внешних сервисов;
- пиши для пользователя, а не для внутренней команды разработки;
- избегай внутренних терминов вроде payload, fixture, dependency,
  status/reason, review surface, metadata-safe или benchmark.

В каждом GitHub Release должны быть:

- что изменилось, простыми словами;
- влияние на совместимость или миграции;
- чем проверяли релиз;
- ссылки на запросы на слияние и задачи, если они есть;
- заметки про выкатку, откат или эксплуатацию, если это важно;
- явные ограничения и следующая работа.

## Git Safety

- Never reset or discard user changes.
- Do not auto-commit implementation code, generated build outputs, secrets, or
  unrelated changes.
- Implementation commits require explicit user approval after validation.
- Spec Kit documentation auto-commits may run only through user-approved Spec
  Kit hooks.

## Evidence Safety

Evidence must be metadata-only unless a spec explicitly allows more. Do not
commit raw audio, transcript text, credentials, tokens, signed URLs, passwords,
live local paths, private screenshots, private meeting content, or real account
identifiers.
