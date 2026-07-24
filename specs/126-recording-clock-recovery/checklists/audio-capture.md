# Audio Capture Requirements Checklist: Восстановление устойчивой синхронизации

**Purpose**: Проверить качество требований capture/timing до реализации
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## Clock and synchronization contract

- [x] PTS явно отделён от времени доставки callback-а
- [x] Описана единая сравнимая шкала для system audio и app-owned microphone
- [x] Зафиксировано, что callback jitter не является сам по себе clock failure
- [x] Указан bounded policy для reorder, gap, overlap и late batch
- [x] Drift описан измеримо и не маскируется автоматическим «улучшением» звука

## Native capture lifecycle

- [x] Указаны ScreenCaptureKit и AVFoundation как текущие native boundaries
- [x] Описаны serial callback queues, bounded work и Stop barrier/drain
- [x] Описано поведение startup order и missing required source
- [x] Описаны route generation, dropped batch и overflow как integrity cases
- [x] Не предложено возвращать virtual driver, routing daemon или AEC

## Storage and upload safety

- [x] Успешный package имеет ровно существующий набор v5 artifacts
- [x] Неполный package явно блокирует upload до server meeting creation
- [x] Finalization failure не оставляет partial audio, выглядящее готовым
- [x] Повторный Stop/relaunch/queue refresh имеет idempotency expectation
- [x] Сохранены границы существующего server/MediaScribe contract

## Privacy and validation

- [x] Диагностика ограничена bounded metadata и reason codes
- [x] В acceptance не требуется коммитить raw audio, transcript или private content
- [x] Synthetic test evidence отделена от hardware acceptance
- [x] Заданы focused tests, full local CI и ручной 60-minute gate
- [x] Каждое требование можно проверить без неявного изменения product scope

## Result

Все 20 capture/lifecycle/privacy checks закрыты до tasks. Чеклист проверяет
качество требований, а не подменяет XCTest и hardware evidence.
