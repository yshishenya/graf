# Production closeout: `v2026.08.07.2`

## Immutable release

- Tag: `v2026.08.07.2`
- Source commit: `9f72ea86ab446a0ed4b3a5ca4a3a935f32a0b1d2`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.08.07.2
- Sparkle workflow: https://github.com/yshishenya/crisp/actions/runs/31173368610

## Apple notarization

- ZIP request: `ea6a0f0e-a43f-4109-b37e-2bb2daad3afe` — Accepted.
- PKG request: `6e6ab7a9-3b7d-40b8-8d60-3cbc2802589b` — Accepted.
- Stapling and Gatekeeper for app and PKG — pass.

## Public macOS artifacts

- ZIP: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.07.2.zip
- PKG: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.07.2.pkg
- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- ZIP SHA-256: `00cfd6e8728ff7e35c4a60022e03c827f9ea52bc1c449158ea9da65d470bb12a`
- PKG SHA-256: `197c3c3a8208fe51dcbb6ec770b2bf0c8e2b4e59b46535429d6bce8ceb313b43`
- Appcast SHA-256: `bc8cbee4efd240da7464239291d48276a9f48db0363f93b05fd12fafcdebd35`
- ZIP length in appcast: `3837689` bytes.

## Verification and rollout

- `validate-app-updates.sh` against `v2026.08.05.1` — pass.
- Public ZIP integrity, XML, ZIP/PKG checksums and PKG signature — pass.
- Public appcast reports `2026.08.07.2` and points to the versioned ZIP.
- `/Applications/GRAF.app` реально обновлён через Sparkle с `2026.08.05.1`
  до `2026.08.07.2`; installed app stapler and Gatekeeper checks — pass.
- Previous appcast and landing package were backed up before publication with
  timestamp `20260807T111808Z`.

Evidence contains metadata only; no credentials, private meeting material,
unprocessed audio or content-bearing transcript data were committed or
published.
