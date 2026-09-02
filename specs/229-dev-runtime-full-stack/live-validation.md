# Live validation: presentation lifecycle

Metadata-only operator evidence for T039. No production command, deploy,
migration, data read or release publication is part of this rehearsal.

## Rehearsal baseline

- captured at: `2026-09-02T12:29:38Z`
- known-good Dev SHA: `1d5cef3b9eef3ce517f6a5739b12a8c1774c712c`
- installed process path: `/Applications/GRAF Dev.app/Contents/MacOS/GRAF`
- macOS displayed process name: `GRAF Dev`
- macOS window title: `GRAF Dev`
- live smoke: 13/13 PASS, including `app_identity`, `app_presentation` and
  `exact_source_sha`
- production app CDHash: `bde38a180c557dcb8624de32ad1841163a61439c`
- production `Info.plist` SHA-256:
  `caadd72e8966ec6dd006cbbd799fa95f36a6b2aa30415aa42ed290c58c115840`
- production data file count: `21`
- production data metadata SHA-256:
  `ba56daf0d7d49ec521b50914d3923e0ac4cf819feb58471a4eb621035279df28`

The final section is appended only after the injected failure, compensation,
explicit rollback and post-rehearsal fingerprint comparison complete.
