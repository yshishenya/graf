# Implementation Plan: F297 — Непрерывная запись, честное хранение и правдивые обещания запуска

**Branch**: `297-launch-capture-retention` | **Date**: 2026-11-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/297-launch-capture-retention/spec.md`

## Summary

Закрыть четыре launch-блокера без расширения продукта: (1) сохранять одну запись при смене output device и коротком разрыве системного звука, (2) исполнять заявленные сроки retention/backup, (3) привести оферту к фактическому автопродлению и лимиту 4 часа, (4) убрать 500 на referral-ссылках. Автозапись и её список приложений не меняются; платёжные sign-off, Роскомнадзор и трансграничная передача остаются отдельными задачами.

## Technical Context

**Language/Version**: Swift 6.0.3 / macOS 14.5+; Python 3.12 / FastAPI; shell для host prune; существующий SwiftPM и pytest.

**Primary Dependencies**: ScreenCaptureKit, CoreAudio, WebRTC AEC3 (`GrafAEC3`), существующий `RecordingAudioTimeline`, `V5LocalRecordingWriter`, `DesktopUploadQueueService`; FastAPI/Jinja/StrictUndefined; существующий `run_retention_scan`; Docker/Compose; systemd timer для backup prune.

**Storage**: локальные WAV/M4A/manifest и очередь без изменения схемы; PostgreSQL retention snapshots/audit без новых таблиц; одна аддитивная RLS-функция `rec_maintenance_allowed()` для `retention_scan`; backup-каталоги на host filesystem.

**Testing**: `swift test --package-path apps/macos` focused filters; `apps/macos/Scripts/run-swift-tests.sh`; `swift run --package-path apps/macos ContractValidation`; focused pytest; shell `--dry-run` для prune; HTTP checks для referral; `infra/scripts/ci-local.sh --fast` как диагностика (не замена GitHub gates).

**Target Platform**: macOS 14.5+ (Apple Silicon/Intel), Linux server, существующий production host `2brain.dev`.

**Project Type**: desktop app + web/server + host scripts.

**Performance Goals**: не увеличивать задержку записи; короткий gap bridge — не более **500 мс** (`maximumBridgedGapSeconds`), типичный 5–50 мс; разрыв 500 мс–15 с не маскируется тишиной; route rebase без потери кадров; retention/backup prune — bounded, off-main/off-request.

**Constraints**: сохранить один канонический WAV/M4A, AEC3, видимый индикатор, одну кнопку Stop, существующую очередь и форматы; не менять автозапись; не логировать аудио/текст/пути.

**Scale/Scope**: один Mac на запись; серверный retention на все активные workspace; backup prune на собственные каталоги GRAF; публичные тексты и referral.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Capture-first MVP integrity**: PASS — изменение усиливает сохранность записи, не меняет manual Record/Stop и не возвращает legacy routing.
- **II. Visible consent and user control**: PASS — видимый индикатор и Stop сохраняются; route/gap уведомление не скрывает запись; автозапись не меняется.
- **III. Plaintext observability**: PASS — новых content-bearing логов нет; retention audit metadata-only.
- **IV. Deletion truth and lifecycle accounting**: PASS — retention использует существующий deletion path и snapshot/audit; backup prune явно ограничен.
- **V. Public macOS distribution**: PASS — bundle ID, Developer ID, Sparkle, notarization не меняются.
- **VI. Spec-driven delivery**: PASS — F297 high-risk, clarify/checklist/analyze/tasks обязательны.
- **VII. Reference fidelity**: PASS — UI-копирайт и оферта правдивы; сторонние assets не добавляются.

**Post-design re-check**: PASS — no new violation; backup prune остаётся operator-owned и не расширяет публичные обещания.

## Project Structure

### Documentation (this feature)

```text
specs/297-launch-capture-retention/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── capture-continuity.md
│   ├── retention-backup.md
│   └── public-copy-referral.md
├── checklists/
│   ├── requirements.md
│   ├── audio-capture.md
│   ├── security.md
│   ├── infra.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/RecApp/Sources/Capture/
├── RecordingAudioTimeline.swift
├── V5LocalRecordingWriter.swift
├── SystemAudioCaptureService.swift
└── LocalRecordingManifestService.swift
apps/macos/Shared/Sources/Models/
├── AudioModelCore.swift
└── SystemAudioCaptureCoreModels.swift
apps/macos/Shared/Tests/
├── RecordingAudioTimelineTests.swift
├── LocalRecordingWriterSystemAudioTests.swift
└── CaptureControlV5Tests.swift
apps/server/src/twobrain_rec_server/
├── workflows/maintenance_worker.py
├── db/tenant_context.py
├── db/migrations/versions/0116_retention_scan_maintenance.py (new RLS function replacement)
├── public/templates/public/offer.html
├── public/templates/public/landing.html
├── public/templates/public/privacy.html
├── cabinet/templates/cabinet/auth/analytics.html
└── cabinet/web_routes/referrals.py
apps/server/tests/
├── unit/test_retention*.py
└── integration/test_meeting_sharing_parity.py (если нужно)
infra/
├── scripts/backup-rec-stack.sh
├── scripts/prune-rec-backups.sh (new)
└── systemd/graf-rec-backup-prune.{service,timer} (new)
docs/
├── agent-guidance/release-and-validation.md (только ссылка на prune)
└── runbooks/backup-retention.md (new)
```

## Phase 0: Research

См. [research.md](research.md). Ключевые решения:

1. **Gap bridge**: короткий forward gap системного звука (<= 500 мс) закрывается ограниченной тишиной; разрыв 500 мс–15 с не маскируется и даёт partial/stop; реальная потеря сверх `maximumKnownGapSeconds` остаётся fail-closed. Это соответствует стандартной практике audio capture: silence insertion только для короткого reference-разрыва и сохранение timestamp continuity.
2. **Route change**: новый SCK stream ре-базируется на текущий output frame; AEC3 продолжает работу без нового процессора; при невозможности — partial upload с явным статусом. Альтернатива «останавливать запись» отклонена как потеря встречи.
3. **Retention**: использовать существующий `run_retention_scan`, добавить ежедневный maintenance-loop; не создавать новый deletion algorithm. Планировщик по умолчанию выключен; после включения первые прогоны остаются dry-run, пока оператор не снимет второй ключ.
4. **Backup prune**: отдельный host script с dry-run по умолчанию, `TWOBRAIN_BACKUP_ROOT` (корень, не полный путь копии), строгим именем каталога, запретом symlink/чужих путей и exit codes 0/2/3; systemd timer — операторский, отключается остановкой timer.
5. **Offer**: автопродление остаётся checked; правдивый текст важнее «красивой» формулировки. Лимит 4 часа берётся из `max_recording_duration_seconds`.
6. **Referral 500**: причина — отсутствующий `public_analytics` при StrictUndefined; чинится явной передачей контекста и безопасным default в шаблоне.

## Phase 1: Design & Contracts

- [data-model.md](data-model.md) — manifest continuity fields, retention snapshot, backup directory, referral states.
- [contracts/capture-continuity.md](contracts/capture-continuity.md) — timeline/gap/route/partial contract.
- [contracts/retention-backup.md](contracts/retention-backup.md) — daily scan and prune contract.
- [contracts/public-copy-referral.md](contracts/public-copy-referral.md) — offer/checkout/referral contract.
- [quickstart.md](quickstart.md) — runnable validation.

## Complexity Tracking

No constitution violations. The capture change is the only high-complexity part; it is bounded to `RecordingAudioTimeline` and `V5LocalRecordingWriter`, with focused tests and no new audio path.

## Implementation Strategy

1. Capture gap bridge (<= 500 ms) + route rebase + partial fallback; update tests and accessibility status.
2. Retention maintenance loop + tenant context + `TWOBRAIN_RETENTION_SCHEDULER_ENABLED` (default `false`) + `TWOBRAIN_RETENTION_SCHEDULER_DRY_RUN_ONLY` (default `true`), operator enables after dry-run and verified backup; focused tests.
3. Backup prune script (`TWOBRAIN_BACKUP_ROOT`, exit codes 0/2/3) + systemd timer + install/disable/rollback runbook.
4. Offer/landing copy and referral fix; preserve checkout CSRF/auth/routes; focused HTTP/render tests.
5. Run focused validation and hardware QA matrix; then exact-SHA PR checks and full release gates.

## Risks

- AEC3 quality after route change: mitigate with a short rebase and a non-blocking accessible warning; hardware test required.
- Retention automation is destructive: mitigate with existing snapshot/fences, bounded limit, dry-run and tests, `TWOBRAIN_RETENTION_SCHEDULER_ENABLED=false` by default, and restore from backup; production enablement is a deployment action after a per-workspace dry-run and verified fresh backup.
- Backup prune can delete data: dry-run default, strict path/name checks, no symlinks, no wildcard outside `TWOBRAIN_BACKUP_ROOT`, exit codes 0/2/3, timer stop as disable.
- Copy changes can drift from checkout: one source of truth in templates and a contract test that also covers CSRF/auth/routes.
