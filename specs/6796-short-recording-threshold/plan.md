# Implementation Plan: Единый порог сохранения

**Branch**: `codex/6796-short-recording-threshold` | **Date**: 2026-09-12 | **Spec**: [spec.md](spec.md)

## Summary

В существующем writer фиксировать решение до публикации завершённого манифеста. Общий обработчик штатного Stop включает правило для ручного/автоматического запуска; аварийные вызовы сохраняют прежнее поведение. Очередь распознаёт решение и безопасно удаляет локальный материал вместо отправки. Отдельное информационное сообщение не становится recordingBlocker.

## Technical Context

- Language/Version: Swift 6 package, Foundation/AppKit/SwiftUI, macOS 14+.
- Primary Dependencies: существующие AVFoundation/ScreenCaptureKit; новых зависимостей нет.
- Storage: локальные manifest.json и upload queue; серверная схема не меняется.
- Testing: существующий XCTest, синтетические аудиокадры и временные хранилища.
- Risk / Validation Lane: high-risk-feature (capture, storage, deletion, UX).
- Release Gate: no deploy; коммит реализации после проверки и разрешения владельца; затем GitHub governance-fast на exact SHA и native acceptance через GRAF Dev; release-full для будущего выпуска.
- Performance Goals: нет задержки старта; нет обработки файлов на аудиопотоке/main actor; штатный Stop короткой записи в прежнем бюджете 2 секунд.
- Scope: macOS, только новые штатные завершения, исторические/импорт/сбои исключены.

## Constitution Check

До Phase 0: PASS — разрешения/видимость/Stop не меняются, правило согласовано владельцем, сетевой границы нет, аудио не попадает в evidence.
После Phase 1: PASS — аварийное аудио сохраняется, локальная очистка проверяет пути и сохраняет маркер до удаления аудио; отказ очистки не разрешает upload. Нет изменения генерации, auth, платформы и распространения. Изменение старого требования о сохранении каждого штатного фрагмента ограничено новой явно согласованной политикой.

## Phase 0: Research

См. research.md. Общий stop вызывается также при ошибке — разрешить только userRequested/meetingEnded. Точное число кадров канонического WAV, не ceil duration очереди. Scanner видит манифест до возврата Stop — устойчивое решение должно появиться атомарно с завершением.

## Phase 1: Design

1. Дополнительное optional поле shortRecordingDiscarded в LocalRecordingManifest, отсутствие = прежнее поведение. Признак выставляется только writer по явной штатной причине, при сохранном v5 результате, без ошибки/egress и точной положительной длительности <30 секунд. Помеченный результат имеет status=blocked, readiness=degraded для совместимости старого клиента.
2. stop/stopAsync принимают optional stopReason (default nil сохраняет исторические вызовы/аварию). Контроль порога вынести в вычисление манифеста с проверкой точных кадров; один источник политики.
3. Scanner пропускает помеченное, убирает только pristine .saving элемент очереди: совпадают sessionId/directoryId/пути, attemptCount=0, serverCreationAttempted=false, нет meeting/upload/revision/server truth IDs и lifecycle/deletion конфликта; отсутствие строки допустимо; неоднозначность запрещает purge и upload; очистка каталога только после успешной проверки. makeItem отклоняет помеченное как страховку прямого enqueue. Очистка: проверить границы root и идентичность, убрать очередь устойчиво, удалить содержимое кроме manifest.json, манифест последним. При сбое маркер остаётся и scanner повторит очистку. Отказ очистки не прерывает обработку прочих записей.
4. Обычный Stop после решения не сообщает saved и не вызывает upload; обновляет список и показывает отдельное неблокирующее native-сообщение. Вызовы failures/app exit не меняются. Уведомление видимо при скрытом основном окне, не активирует приложение и не требует системного разрешения; VoiceOver announcement.
5. Test matrix и changelog; независимый review требований и кода, converge.

## Validation Plan

Focused XCTest для writer/queue/recovery/notification и сборка Swift package. Границы 479999/480000/480001 кадров при 16kHz; ручная и автоматическая остановка; неверная длительность; авария/exit; повторное сканирование, cleanup failure и symlink escape; исторический пакет. Затем quickstart с официальным GRAF Dev после разрешённого коммита. CI только exact PR SHA. Проверки приватных записей не требуются.

## Project Structure

- apps/macos/Shared/Sources/Models/AudioModelCore.swift — локальный признак и точный предикат.
- apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift — атомарное завершение.
- apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift — запрет отправки и очистка.
- apps/macos/RecApp/App/TwoBrainRecApp.swift — общий Stop и сообщение.
- apps/macos/RecApp/Sources/Notifications/DesktopRecordingNoticePresenter.swift — малое native уведомление, если существующего механизма нет.
- apps/macos/Shared/Tests/ — профильные XCTest.
- specs/6796-short-recording-threshold/ — требования, план, проверки и evidence.

## Complexity Tracking

Новых зависимостей, сервисов и серверных таблиц нет. Устойчивый признак необходим для crash safety; манифест сохраняется последним до окончания очистки. Отдельный lifecycle пользовательского удаления не создаётся.

## Дополнение для доступности штатного стенда

Перед T006 выполнить T007: перенести точный scoped patch из e964bba55 для scripts/dev-harness.py, tests/governance/test_graf_local_adapter.py и infra/dev/README.md. Только MinIO pull policy missing; fake tests доказывают остановку до архива/сборки app при недоступном образе. Тег/digest verification/архив/подпись и все остальные guards сохраняются. Независимый infra checklist/review, focused pytest и exact-SHA CI до PR ready.

## T008: разовая диагностика незавершённой приёмки

Lane остаётся high-risk-feature (capture/diagnostics). Constitution check:
локальный журнал содержит только технические метаданные, без raw audio,
личных данных, абсолютных часов, путей и новых сетевых вызовов. Никакого
изменения защит захвата/PTS/порога. Не создаём отдельную систему диагностики.

В ScreenCaptureKitSystemAudioRuntime хранить предыдущие PTS и числа
объявленных/декодированных кадров только в памяти, только на serial outputQueue.
Сброс на start до регистрации callbacks. При первом nil extraction, расхождении
числа кадров или интервала больше 1 ms передать ограниченное событие в существующий AppLog через переданный обработчик.
В RecordingAudioTimeline.process при первом промежутке больше существующего
допуска записать относительные expected/requested frame, источник, формат,
размер batch/converted batch и discontinuity. Срабатывает до существующей
проверки, без изменения samples или результативной ветви ошибки.

Файлы: SystemAudioCaptureService.swift, RecordingAudioTimeline.swift, V5LocalRecordingWriter.swift, App/TwoBrainRecApp.swift и
Shared/Tests/RecordingAudioTimelineTests.swift. Проверить прежний целый
префикс при gap >48 и отсутствие новых ошибок на непрерывном потоке; выполнить
профильные timeline/system extractor/short recording tests, code review, CI,
штатные build/promote и контролируемую реальную запись после handback Dev.
Результат T008 — доказанная классификация сбоя, а не автоматическое снятие T006.

Уточнение по наблюдаемости: NSLog виден в stderr теста, но контрольный
запуск не появился в доступном unified log. Использовать существующий
AppLog/BoundedLogFileWriter через optional diagnosticLogger в конструкторах
writer/timeline и system runtime/service. Путь, лимиты и очистка существующего
журнала не меняются. В тесте timeline передать collector и проверить ровно
одно сообщение с предусмотренными полями. Это заменяет NSLog, не добавляет
второй журнал и не отправляет метаданные.

Обработчик AppLog не выполняет файловых операций на очередях захвата: готовая
ограниченная строка асинхронно передаётся на DispatchQueue.global(qos: .utility),
где вызывается существующий writeRaw. Флаг бюджета выставляется до callback
на исходной serial queue. Callback nonthrowing, optional default nil.
Reviewer подтвердил применимость CHK012–014 при этом уточнении.
