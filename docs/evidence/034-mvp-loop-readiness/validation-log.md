# Validation Log: 034 MVP Loop Readiness

Date: 2026-06-16

This log records the Phase 8 validation evidence for feature
`034-mvp-loop-readiness`. Results are metadata-only; long command output that
contains local absolute paths or rendered secret-file locations is intentionally
not copied here.

## T052 Focused Readiness Tests

Command:

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/contract/test_mvp_loop_readiness_contract.py \
  tests/integration/test_mvp_loop_readiness_report.py \
  tests/unit/test_mvp_loop_readiness_matrix.py
```

Result:

- `22 passed in 0.04s`
- Re-run after lint/readiness-report updates: `22 passed in 0.04s`

## T053 Web Cabinet And Lifecycle Regression

Command:

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/contract/test_access_sharing_downloads_contract.py \
  tests/contract/test_retention_deletion_contract.py \
  tests/unit/test_deletion_report_view_models.py \
  tests/integration/test_local_purge_coordination.py
```

Result:

- Initial Phase 8 run: `29 passed in 8.44s`
- Re-run after lint/readiness-report updates: `29 passed in 7.59s`

## T054 macOS Desktop Shell Regression

Command:

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'DesktopCabinet|AppControlAccessibility|CaptureControl|DesktopUploadQueue|DesktopLocalPurge'
```

Result:

- `47 tests, 0 failures`

Note:

- An initial wrapper command failed because it used `status`, a read-only zsh
  variable. The Swift test itself was re-run with a safe shell variable and
  passed.

## T055 Forbidden Content And Screenshot Payload Scans

Commands:

```sh
rg -n -i '<real private-value regex for private Krisp captures, private emails, concrete local user paths, fixture private IDs, and private audio filenames>' \
  specs/034-mvp-loop-readiness \
  docs/evidence/034-mvp-loop-readiness \
  docs/current-product-status.md \
  CHANGELOG.md
```

```sh
rg -n -i '<payload-id-value regex for storage object keys, external job ids, signed URL fields, and presigned URL fields>' \
  docs/evidence/034-mvp-loop-readiness
```

```sh
find docs/evidence/034-mvp-loop-readiness/screenshots -type f \
  \( -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' -o -name '*.webp' \) -print
```

Results:

- `forbidden_real_private_values_scan_extended=pass`
- `forbidden_evidence_payload_value_scan=pass`
- `screenshot_payload_scan=pass_no_raster_files`

Notes:

- A broader exploratory scan matched the literal forbidden-pattern examples in
  `quickstart.md` and GitHub repository URLs in `issues.md`. Those were reviewed
  as false positives and replaced with the real-value scans above.
- `readiness-report.json` now records `forbidden_content_scan.status=pass`.

## T056 Local Repository CI

Command:

```sh
./infra/scripts/ci-local.sh
```

Result:

- First run: server tests passed, then lint failed on readiness import sorting
  and a nested `if`.
- Fix applied: import sorting through Ruff and one `SIM102` simplification.
- Final run after report/log updates:
  - server tests: `440 passed, 4 skipped`
  - server lint: `All checks passed`
  - python compile: pass
  - RLS validation boundary: expected blocked truth in local postgres-test mode
  - production compose config: rendered
  - deployment evidence scan: pass
  - `ci_local_result=pass`

## T057 Production Health Boundary

Command:

```sh
curl -fsS https://rec.2brain.pro/api/v1/health/live
curl -fsS https://rec.2brain.pro/api/v1/health/ready
```

Result:

- live: `{"status":"ok"}`
- ready: `{"status":"ready"}`

Strongest valid production claim:

- `infra_smoke_ready`

Explicit exclusions:

- This does not prove `internal_pilot_candidate`, `mvp_loop_ready`,
  `user_rollout_ready`, or `production_ready`.

## T058 Checklist Review

Checklist status:

- `infra.md`: total=14 completed=14 incomplete=0
- `launch-readiness.md`: total=15 completed=15 incomplete=0
- `requirements.md`: total=16 completed=16 incomplete=0
- `security.md`: total=14 completed=14 incomplete=0
- `ux.md`: total=14 completed=14 incomplete=0

Result:

- All requirement-quality checklists remain complete.

## T059 GitHub Issue Traceability

Command:

```sh
python3 - <<'PY'
from pathlib import Path
mapping = Path('specs/034-mvp-loop-readiness/issues.md').read_text()
tasks = Path('specs/034-mvp-loop-readiness/tasks.md').read_text()
missing = [f'T{i:03d}' for i in range(1, 60) if f'T{i:03d}' not in mapping]
open_tasks = [line for line in tasks.splitlines() if line.startswith('- [ ] T')]
print('missing_issue_mappings=', missing)
print('open_tasks=', len(open_tasks))
PY
```

Result before marking Phase 8 complete:

- `missing_issue_mappings= []`
- `open_tasks= 8`

Result after marking Phase 8 complete:

- `missing_issue_mappings= []`
- `open_tasks= 0`
