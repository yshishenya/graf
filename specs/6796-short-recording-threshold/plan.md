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
