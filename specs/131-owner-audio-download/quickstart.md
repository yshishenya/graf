# Quickstart: Скачивание аудио владельцем по умолчанию

## Preconditions

- Run from the repository root on the feature branch.
- Use the existing synthetic cabinet fixtures and a valid retained playback
  M4A; never use a real meeting or record audio in evidence.
- Do not print response bodies, object keys, signed URLs, credentials, private
  paths, transcript text, or audio bytes.

## Focused checks

```sh
(cd apps/server && uv run --extra dev pytest -q \
  tests/integration/test_artifact_egress_policy.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/contract/test_recording_governance_ui_contract.py \
  tests/contract/test_access_sharing_downloads_contract.py)
```

## Acceptance scenarios

1. **Owner without separate permission**: synthetic owner meeting with a valid
   playback M4A and no policy row shows `Скачать аудио…` in web and embedded
   detail; direct server-mediated request returns 200 and the existing audit
   event sequence.
2. **Current production-shaped default**: a `workspace_default` row with
   `audio_download=disabled` still permits the owner and does not permit a
   permitted non-owner.
3. **Explicit privacy decision**: a `meeting_override` row with
   `audio_download=disabled` rejects the owner with bounded 409 and no bytes.
4. **Unavailable/lifecycle safety**: missing artifact, deletion, stale object,
   storage failure, and invalid access retain the existing bounded failures and
   metadata-only audit behavior.
5. **Scope guard**: transcript, summary, package, playback, and storage URL
   contracts remain unchanged.

## Repository gate

After focused checks:

```sh
infra/scripts/ci-local.sh
```

The gate is required because this changes shared egress, authorization, UX,
and audit behavior. A production CD dry-run/execute is not part of this
implementation validation and needs a separately approved release turn.

## Evidence

Record only command status, test counts, HTTP status codes, bounded policy
reasons, audit event types, and presence/absence of the relative route. Do not
record meeting IDs, titles, transcript/audio content, storage identifiers,
signed URLs, credentials, or private paths.

## Validation receipt (2026-07-26)

- PASS — Feature 131 focused PostgreSQL suite: `57 passed`; only warnings were
  dependency/test-runner warnings.
- PASS — isolated SC-017 timing check after the full-load failure: `1 passed,
  34 deselected`.
- PASS — deployment evidence scan after the pre-existing wording false
  positive was corrected: `14` metadata-only files scanned.
- PARTIAL — `infra/scripts/ci-local.sh` completed macOS validation with `642`
  Swift tests passed. The server phase reported `2446 passed, 1 skipped, 1
  failed`; the only failure was the unrelated
  `test_sc017_one_hundred_warmed_atomic_consumptions_are_within_50ms_p95`
  performance assertion (`136.764875 ms` p95 under the full parallel load,
  `50 ms` limit). The same test passes in isolation as recorded above.
- EXPECTED LIMITATION — the local RLS production-enforcement probe remains
  blocked because no production database was provided; no live production
  probe was attempted.
- RELEASE BOUNDARY — no production deploy or release was run in this slice.
