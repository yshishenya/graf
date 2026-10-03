# Implementation Plan: Непрерывная запись и доступ к аудио
**Branch**: `284-recording-continuity-playback` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

## Summary
CoreAudio подтверждает текущую входную активность приложения независимо от скорости unified log. В рабочем пути текущие снимки CoreAudio являются единственным источником активности: старые log edges/snapshots не могут переопределять их. Журнальный наблюдатель сохраняется только как явно выбираемый прежний режим для существующих проверок, приложение его не выбирает. Успешные полные снимки согласуют ВСЕ источники детектора без сброса подтверждённых/вручную подавленных звонков. Существующий bridge и LocalRecordingPlayer открывают локальную копию из карточки только для UUID маршрута. Квота получает правильный текст и переход к существующему хранилищу.

## Technical Context
**Language/Version**: Swift 6, Python 3.12+, JavaScript.
**Primary Dependencies**: CoreAudio/AppKit, existing WKWebView, FastAPI/Jinja; no new dependencies.
**Storage**: Existing local queue/manifests; unchanged Postgres/MinIO/quota.
**Testing**: Existing XCTest, pytest, Playwright tests.
**Risk / Validation Lane**: high-risk-product (capture, storage access, UX).
**Release Gate**: user explicitly authorized commit/push/PR/release on 2026-10-02; clean-SHA GRAF Dev, exact-SHA PR checks, frozen-candidate release-full and public notarization/Sparkle gates remain mandatory.
**Target Platform**: macOS 14.5+ and server cabinet.
**Project Type**: desktop-app/web-service.
**Performance Goals**: Current metadata snapshot every two seconds; no audio reads for detection or repeated hashes for UI projection.
**Constraints**: Unknown snapshot != empty; observer gaps never justify indefinite recording; 600s fail-closed retained. No changes to quota or production data.
**Scale/Scope**: Two bugs; one existing native player and bridge; no database migration.

## Constitution Check
PASS before research and after design: native system-audio-first capture unchanged; explicit per-target local choice, visible recording and one-action Stop unchanged. Metadata observation uses existing platform APIs without starting capture, requesting new TCC or uploading. Existing access/deletion/owner fences and hash check remain. Credentials remain server-side. No private content in artifacts. Root AGENTS, tariff and release governance unchanged.

## Validation Plan
Tests precede fixes. CoreAudio identity/failed snapshots, observer lifecycle and simulated 45-minute call; stop15s/unknown600s and no replay. Detail bridge tests for matching UUID/open only, file/access fences; browser DOM refresh/no stale buttons; server quota mapping/render contract. Existing focused detector, queue/deletion/playback suites. Repository governance/changelog checks. Required GitHub governance-fast, macos-pr, pr-metadata on future committed PR SHA and release-full on frozen candidate; no claim these ran for an uncommitted diff. Hardware validation only using GRAF Dev through dev-harness after authorized clean commit.

## Project Structure
- apps/macos/RecApp/Sources/MeetingDetection/ — native metadata snapshot, stream, detector.
- apps/macos/RecApp/App/TwoBrainRecApp.swift — composition and evidence renewal.
- apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift — route-bound open.
- apps/server/src/twobrain_rec_server/cabinet/{view_models.py,templates,static/cabinet/cabinet.js} — quota and local playback action.
- apps/macos/Shared/Tests; apps/server/tests/{unit,contract,browser} — existing checks.
- changes/unreleased/F284.yaml — owned change note.
**Structure Decision**: Extend existing paths; no new service or playback implementation.

Quota navigation uses the existing /billing overview (shared access); capacity-management actions remain guarded by billing_owner. Copy asks to contact the workspace owner when appropriate. No new authority or purchase action is introduced.

## Сходимость T010

Сбор метаданных различает отказ списка процессов и недоступность отдельного процесса. Пакет снимка содержит текущие активные точные bundleID и полноту покрытия. Полный снимок сохраняет прежнюю15s семантику отсутствия; неполный передаёт достоверные положительные события без ложного окончания отсутствующего источника. Таймер600s обновляется только текущим подтверждением записываемого приложения. Исполняемые проверки чтения отдельных процессов, внешнего bundle для Qt helper, смешанного снимка и общего detector/recording predicate должны доказать непрерывность45min с недоступным соседним процессом; неполный пустой снимок не должен превращаться в завершение через15s. Нового журнального запасного пути нет.

## T011: аппаратный source_overflow

Разобрать распределение чтения пакетов microphone/systemAudio. Текущий writer читает сначала все пакеты одного источника; одинаковый предел количества пакетов не означает одинаковую длительность. Исполняемый тест должен показать искусственное накопление при непрерывных входах и сохранить прежние отрицательные проверки. При доказательстве исправить порядок обработки по PTS, сохранив ограничение работы очереди, остановки, памяти и отказ при реальной потере. Добавить безопасные относительные счётчики в событие переполнения для следующей аппаратной проверки. Новые зависимости и изменения формата хранения не требуются. Проверки: writer/timeline/extractor и detector, независимое ревью, exact-SHA CI, dev-harness и повторный разрешённый45min Telemost. Нотариализация отдельно блокируется Apple403 missing agreement.

Constitution Check T011: PASS в проектировании. Захват и доступ остаются по уже выданному согласию; пределы памяти/потерь и видимая остановка сохраняются. Ни фиктивных аудиосэмплов, ни новой передачи приватных данных.

Кандидат доказуемого исправления: выбирать меньший PTS из не более одной ожидающей порции каждого источника, переносить эти порции между ограниченными live-проходами. Общий текущий предел работы128 порций сохраняется; stop имеет конечный отдельный предел. Для локализации следующего аппаратного отказа метаданные источника должны различать принятую и обработанную границу, число ожидающих кадров и размер/частоту последней порции. Допустим необязательный снимок протокола (по умолчанию nil у сторонних источников), передаваемый через существующие обёртки; в журнал попадают только относительные значения, не исходные PTS. Буферы и файловый контракт неизменны.

Сходимость предварительного ревью: периодический снимок не чаще30s, интервалы измеряются монотонным временем. При успешной паузе ожидающая порция микрофона консервативно заглушается без удаления кадров/PTS; требуется отдельная исполняемая проверка pause→drain→resume. Нечисловой PTS и несовместимые часы должны давать прежний отказ и не скрываться сортировкой за непрерывным вторым источником. Обычные снимки writer журналируются отдельным capture.writer_progress, ошибки остаются capture.timing_anomaly.
