# Production receipt: v2026.08.12.3

Date: 2026-08-13
Target: `2brain.dev` / `https://rec.2brain.pro`
Deployed ref: `master`
Deployed SHA: `a6d4745508e3381338c61c07dc77b1d77eb47a36`

## Result

- `infra/scripts/cd-remote.sh --execute --branch master` — pass.
- Full local gate — pass: 657 Swift tests, 2893 parallel server tests,
  42 strict tests, lint, compile and evidence scan.
- Remote backup and restore rehearsal — pass.
- Migration head — `0071_fair_use_capability_prefix`.
- Production smoke — `infra_smoke_ready`; API, processing worker, media worker,
  Temporal and automatic dispatch readiness — pass.
- Metadata-only smoke cleanup — pass; no residue remained.

## Public download receipt

Checked 2026-08-13 against the public deployment:

- `GET /download` — HTTP 200.
- The page exposes one installer link:
  `/static/public/downloads/graf.pkg?v=6c6cb57affeb`.
- `GET /static/public/downloads/graf.pkg` — HTTP 200,
  `content-length: 6136432`.
- SHA-256:
  `6c6cb57affebd65430c8b49a4636506638950e6ecb9fc4c88b638b6067342c5c`.

The public file matches the notarized `v2026.08.12.3` release asset. No raw
audio, transcript, credentials, signed URLs or private meeting content are
included in this receipt.

## Compatibility boundary

The release provides one universal app-only installer for macOS 14.5+ with
`arm64` and `x86_64` slices. A separate physical Intel Mac smoke remains a
manual follow-up; it does not reopen the public installer or live-download gate.
