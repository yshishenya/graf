# 119 Quickstart: Expanded Meeting App Registry

## Preconditions

- Branch: `119-expand-meeting-app-registry`.
- Real meeting content is not used in automated validation; live calls are
  post-enable QA.
- Synthetic observations contain bundle IDs and safe display labels only.

## 1. Catalog And Registry Contract

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest \
  tests/unit/test_meeting_detection_registry.py \
  tests/contract/test_meeting_detection_api_contract.py
```

Expected: all released targets remain accounted for; registry has 87
case-insensitively unique native IDs and 79 prompt-enabled native targets;
duplicate case variants fail.

## 2. Migration Upgrade And Rollback

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest \
  tests/integration/test_meeting_detection_migrations.py
```

Expected: migration 0030 publishes one newer global registry, leaves workspace
registries untouched, and downgrade restores the previous global baseline.

## 3. macOS Resolution And Fail-Closed Policy

```sh
swift test --package-path apps/macos --filter \
'MeetingTargetRegistryTests|MeetingDetectionPolicyTests|BrowserTargetEvidenceTests'
```

Expected:

- mixed-case observed bundle IDs resolve to their one target;
- Telegram Desktop, TDX, Forkgram, and 64Gram resolve through one shared identity;
- Telegram for macOS, Telegram A, AyuGram, and Kotatogram remain distinct;
- every verified native target resolves as prompt-enabled;
- generic browser activity remains manual-only.

## 4. Settings UX And Accessibility

```sh
swift test --package-path apps/macos --filter \
'AppControlAccessibilityTests|CaptureControlV5Tests'
```

Expected: settings uses one common scrollable applications list beside Zoom and
Telemost, every verified native target has the existing checkbox, “Выбрать все”
selects all 79 targets, and manual control/Stop contracts remain intact.

## 5. Repository Gate

```sh
infra/scripts/ci-local.sh
```

Expected: local CI passes before rollout.

## Validation Evidence

- Server registry unit tests: `10 passed`.
- Focused Postgres contract/integration/migration tests: `15 passed`.
- Focused macOS registry/policy/settings tests: `51 passed`.
- Full macOS suite through local CI after rebase: `592 passed`.
- Full server collection after rebase: `1997` tests. Parallel phase: `1961 passed, 1
  skipped`; strict-RLS phase: `34 passed, 1 skipped`; server lint and compile
  passed.
- Full `infra/scripts/ci-local.sh`: `ci_local_result=pass`.
- The first full server run exposed leaked anonymous PostgreSQL test volumes and
  stopped with `DiskFullError`. The disposable runner now keeps database data in
  tmpfs and removes volumes attached to its own container. A before/after focused
  run kept the Docker volume count unchanged (`316 -> 316`), and the full rerun
  passed without deleting pre-existing user volumes.
- Registry-derived count check: `85` total targets, `79` prompt-enabled native
  targets, `87` case-insensitively unique bundle IDs, `2` blocked missing-ID
  targets, and `4` browser/manual targets.
- Ruff, Python compileall, `git diff --check`, JSON parsing, and bounded
  metadata secret scan: pass.
