# Code Inventory

**Date**: 2026-06-30
**Scope**: tracked code, scripts, and config-like runtime files under `apps/server`, `apps/macos`, `infra`, `scripts`, and `.specify/scripts`.

## Count Summary

Generated build output under `apps/macos/.build/` is excluded.

```text
Dockerfile 1
c 1
cpp 12
h 1
hpp 7
js 2
py 411
sh 46
swift 214
yml 3
```

Approximate audited lines across the counted files: `129005`.

MacOS tracked source/script files under `Shared`, `RecApp`, `AudioDriver`, `Scripts`, and `Installer`: `265`.

## Largest Server Files

```text
2125 apps/server/src/twobrain_rec_server/cabinet/web.py
2025 apps/server/src/twobrain_rec_server/readiness/matrix.py
1928 apps/server/src/twobrain_rec_server/cabinet/view_models.py
1542 apps/server/tests/integration/test_calendar_settings_flow.py
1192 apps/server/src/twobrain_rec_server/cabinet/rendering.py
1158 apps/server/tests/unit/test_cabinet_web_shell.py
1070 apps/server/src/twobrain_rec_server/cabinet/egress.py
1037 apps/server/src/twobrain_rec_server/api/auth.py
996 apps/server/tests/contract/test_auth_contracts.py
943 apps/server/src/twobrain_rec_server/api/schemas.py
```

## Largest macOS Files

```text
2479 apps/macos/Shared/Tests/DesktopUploadQueueTests.swift
2370 apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift
2295 apps/macos/Shared/Sources/Models/AudioModels.swift
2065 apps/macos/RecApp/App/TwoBrainRecApp.swift
1657 apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift
1604 apps/macos/Shared/Tools/ContractValidation/main.swift
1562 apps/macos/Scripts/validate-system-audio-capture-pivot.sh
1550 apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift
1450 apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift
1162 apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift
```

## Initial Risk Notes

- File size is not deletion evidence.
- `apps/server/src/twobrain_rec_server/cabinet/web.py`, `cabinet/view_models.py`, and `cabinet/rendering.py` are presentation-layer split candidates, but only for a dedicated cabinet batch.
- `apps/server/src/twobrain_rec_server/readiness/matrix.py` and deployment/readiness tests are release-evidence logic; treat as high-risk retained until a focused readiness audit proves otherwise.
- macOS capture, upload queue, and diagnostic files are high-risk because they protect local capture truth, metadata-only diagnostics, deletion/purge truth, and upload custody.
- Bundled `htmx-2.0.10.min.js` is a vendored browser asset and must not be treated as hand-authored dead code without asset replacement proof.

## Next Candidate Buckets

- Python dependency candidate: `httpx2` dev extra.
- Python code candidates: use Ruff/Vulture and import/caller checks after dependency docs are complete.
- Cabinet candidates: presentation-only split/shrink, separate from API/service behavior.
- macOS candidates: source-level audit only after target/product evidence; no target removal from `Package.swift` now.
- Infra candidates: generated caches are excluded; tracked deploy/smoke scripts are retained unless a release/deploy task scopes removal.
