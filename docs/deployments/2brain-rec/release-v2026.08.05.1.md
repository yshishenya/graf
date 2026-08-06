# Production closeout: `v2026.08.05.1`

## Immutable release

- Tag: `v2026.08.05.1`
- Deployed SHA: `50fef018add21a3677e4100327b5c506b98f647c`
- Deploy branch: `master`
- Runtime checkout: clean `master` at the same SHA
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.08.05.1
- Feature PR: https://github.com/yshishenya/crisp/pull/4851
- Release tooling PR: https://github.com/yshishenya/crisp/pull/4852
- Contract gate PR: https://github.com/yshishenya/crisp/pull/4853

## Validation gates

| Gate | Result |
| --- | --- |
| Full exact-SHA CI | pass; macOS 646/646; server 2512 passed, 1 skipped; strict RLS 42 passed, 1 skipped |
| CD dry-run and guarded deploy | pass; explicit production approval recorded |
| Backup, restore rehearsal, migration and RLS | pass; migration head `0043_initial_outcome_reconcile` |
| Temporal, processing/media workers and readiness | pass |
| Prompt promotion and rollback | pass; exact outcome `v5`, prepared `v6`, restored `v5` |
| Live outcome smoke | pass for health `200/200`, candidate `ready`, accept `200/accepted` |
| Public-link readback | expected blocked; `403 share_policy_blocked`, public-link gates disabled |

## Public macOS artifacts

- ZIP: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.05.1.zip
- PKG: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.05.1.pkg
- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- Landing package: https://rec.2brain.pro/static/public/downloads/graf-local.pkg
- ZIP SHA-256: `c791da8c301bc62337aaa76187f237dd02c397653bb2c5f3a46d38c9364fd1e7`
- PKG SHA-256: `d567bc43ac47ddb241c519ce73d858d0ea3a1fc657990529b455ec4c66678703`
- Appcast SHA-256: `d88adae3029bf3b4a7546a11da4939b1ba109d0efafc492f3a645b70e1d79033`
- Apple ZIP notarization: accepted, request `55028a61-2a26-434c-bf1d-36d0bcff3cce`.
- Apple PKG notarization: accepted, request `f2de9b0c-c93c-47f7-882d-8b399edd7f04`.
- Stapling and Gatekeeper: pass for app and package.
- Sparkle signing workflow: pass, run `31071458619`; continuity validator passed
  against `v2026.08.04.4`.

## Rollback and limitations

- Previous appcast was backed up as
  `graf-appcast.xml.pre-v2026.08.05.1-20260806T043407Z`.
- Previous landing package was backed up as
  `graf-local.pkg.pre-v2026.08.05.1-20260806T043407Z`.
- Public links remain disabled by the existing security gate; enabling them is a
  separate approved product/security change, not part of this release.
- Evidence contains metadata only; no transcript, audio, prompt text or secrets
  were committed or published.
