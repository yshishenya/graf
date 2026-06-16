# Quickstart: MVP Loop Readiness

Date: 2026-06-16

This guide validates feature `034-mvp-loop-readiness`. It is metadata-only:
do not add raw audio, private transcript text, credentials, tokens, signed
URLs, private emails, live local paths, or private Krisp screenshots to
committed evidence.

## 1. Local Repository Gate

```sh
./infra/scripts/ci-local.sh
```

Expected:

- `ci_local_result=pass`
- server tests pass;
- server lint passes;
- Python compile passes;
- production compose config renders;
- deployment evidence scan passes.

## 2. Focused Readiness Contract Tests

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/contract/test_mvp_loop_readiness_contract.py \
  tests/integration/test_mvp_loop_readiness_report.py \
  tests/unit/test_mvp_loop_readiness_matrix.py
```

Expected:

- Readiness JSON matches `contracts/readiness-evidence-schema.md`.
- Markdown report contains all sections from
  `contracts/mvp-loop-readiness-contract.md`.
- P0/P1 launch gaps block `mvp_loop_ready`.
- Synthetic-only stages cannot claim live/pilot readiness.

## 3. Desktop Shell Regression

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet|AppControlAccessibility|CaptureControl|DesktopUploadQueue|DesktopLocalPurge'
```

Expected:

- Native capture controls remain outside embedded web content.
- Desktop cabinet routes stay bounded.
- Upload-to-review continuity still requires server meeting identity.
- Local purge acknowledgement remains metadata-only.

## 4. Web Cabinet And Lifecycle Regression

```sh
cd apps/server
uv run --extra dev pytest -q \
  tests/contract/test_cabinet_contract.py \
  tests/contract/test_access_sharing_downloads_contract.py \
  tests/contract/test_retention_deletion_contract.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/unit/test_deletion_report_view_models.py
```

Expected:

- Meeting list/detail routes remain accessible for authorized users.
- Governance actions are truthful by policy state.
- Deletion report copy does not overpromise universal erasure.
- Web shell keeps layout safe for desktop/embedded use.

## 5. Production Readiness Boundary

For a full deploy/smoke after implementation:

```sh
infra/scripts/cd-remote.sh --dry-run --branch master
infra/scripts/cd-remote.sh --execute --branch master
```

For a read-only current public health check:

```sh
curl -fsS https://rec.2brain.pro/api/v1/health/live
curl -fsS https://rec.2brain.pro/api/v1/health/ready
```

Expected:

- CD execute, when run, emits `deploy_result=pass` and
  `readiness_verdict=infra_smoke_ready`.
- Public health endpoints return ok/ready.
- The readiness report still states that `infra_smoke_ready` is not user
  rollout readiness.

## 6. Screenshot Evidence

Capture or generate metadata-safe screenshots for:

- desktop app first product surface or explicit unavailable/auth blocker;
- desktop embedded ready detail or explicit blocker;
- web meeting list/detail;
- deletion/retention truth where visible.

Store safe committed screenshots under:

```text
docs/evidence/034-mvp-loop-readiness/screenshots/
```

Expected:

- Screenshots contain no private account strings, private emails, transcript
  text, raw audio filenames, signed URL material, live local paths, or Krisp
  private content.
- Screenshot evidence says whether it is live, local runtime, synthetic, or
  blocked.

## 7. Forbidden Content Scan

Run text scan:

```sh
rg -n -i "(/Users/|bearer|secret|password|token|signed_url|presigned|object_key|storage_object_key|transcript text|raw audio|credential|api[_-]?key|private email|private account|mediascribe_job|external_job_id)" \
  specs/034-mvp-loop-readiness \
  docs/evidence/034-mvp-loop-readiness \
  --glob '!**/*.png'
```

Run screenshot payload scan:

```sh
find docs/evidence/034-mvp-loop-readiness/screenshots -type f -name '*.png' -print0 \
  | xargs -0 strings \
  | rg -n -i "(/Users/|bearer|secret|password|token|signed_url|presigned|object_key|storage_object_key|transcript text|raw audio|credential|api[_-]?key|private email|private account|mediascribe_job|external_job_id|krisp)"
```

Expected:

- No unsafe evidence matches.
- Policy/disclaimer text matches, if any, are documented as non-secret
  references.

## 8. Product Status Review

Inspect:

```sh
sed -n '1,340p' docs/current-product-status.md
```

Expected:

- 018 is listed as accepted/implemented/deployed when evidence exists.
- 018 is not listed as the next product slice.
- The next product slice recommendation follows the 034 launch gap register.

## Acceptance Summary

034 is accepted only when:

- all generated tasks are marked complete;
- focused tests pass;
- readiness report and launch gap register exist;
- forbidden-content scans pass;
- product status no longer drifts;
- final claim is bounded to the strongest evidence actually proven.
