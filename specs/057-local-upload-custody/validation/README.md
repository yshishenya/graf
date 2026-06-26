# 057 Validation Evidence

Store only metadata-only validation notes for local upload custody here.

Allowed:
- command names, exit codes, timestamps, synthetic fixture ids;
- safe reason codes, enum names, task ids, issue numbers;
- redacted paths such as `<redacted-local-path>`.

Forbidden:
- raw audio, transcript text, private local paths;
- credentials, bearer tokens, cookies, signed URLs, secret values;
- private meeting content or screenshots containing it.

## 2026-06-26 Local Validation

- Focused macOS quickstart:
  `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopUploadQueue|DesktopUploadClient|DesktopLocalPurge|CaptureControl|DesktopCabinet'`
  -> pass, `142 tests`, `0 failures`.
- Focused server quickstart:
  `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_desktop_status_contract.py tests/contract/test_ingest_openapi_contract.py tests/integration/test_ingest_failure_truth.py tests/integration/test_local_purge_coordination.py tests/unit/test_ingest_state_machine.py`
  -> pass, `21 passed`.
- US6 focused lifecycle checks:
  macOS projection/local-purge -> pass, `25 tests`; server purge/processing
  separation -> pass, `8 passed`.
- Full local gate: `infra/scripts/ci-local.sh` -> `ci_local_result=pass`.
- Forbidden-content scan over `specs/057-local-upload-custody/` and
  `validation/` found policy wording that names forbidden categories only; no
  evidence file contains credentials, private proof payloads, local absolute
  paths, meeting content, or media content.
- 057/058 boundary guard:
  `git diff --name-only | rg '^apps/server/src/twobrain_rec_server/cabinet/(web\\.py|templates/|static/|.*\\.css$)'`
  -> no output.
