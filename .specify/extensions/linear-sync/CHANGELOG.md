# Changelog

All notable changes to this project are documented in this file.

## [0.1.1] - 2026-06-11

### Fixed

- Renamed Spec Kit command metadata to the canonical
  `speckit.linear-sync.<command>` format required by Spec Kit 0.10.
- Updated the `after_taskstoissues` hook to reference
  `speckit.linear-sync.sync` directly.

## [0.1.0] - 2026-06-11

### Added

- Added initial Spec Kit extension metadata for `linear-sync`.
- Added Codex skills:
  - `$speckit-linear-init`
  - `$speckit-linear-import`
  - `$speckit-linear-sync`
  - `$speckit-linear-validate`
- Added `linear_sync.py` with dry-run support for parsing Spec Kit `tasks.md`.
- Added `.specify/linear.yml` mapping support for feature/task/Linear issue links.
- Added Linear API issue creation behind explicit `--apply` and `LINEAR_API_KEY`.
- Added Russian plain-language issue titles and descriptions by default.
- Added product-prefixed Linear Project naming:
  `{product} / {feature} {title}`.
- Added `LINEAR_PRODUCT_NAME`, `SPECKIT_PRODUCT_NAME`, and
  `LINEAR_PROJECT_TEMPLATE` support.

### Security

- Kept dry-run as the default behavior.
- Kept `LINEAR_API_KEY` out of tracked configuration.
- Avoided copying raw English task text as the main generated Linear issue copy.
