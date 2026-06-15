# Web Meeting Review Exceptions

## Purpose

Preserve trust when a meeting is partial, degraded, failed, deleted, only on
one device, or access denied.

## Shared Layout

- State title.
- What exists.
- What is missing or failed.
- Why, if known.
- What the user can do now.
- Source/deletion/access truth.

## Variants

### Partial Ready

- Transcript available, notes failed.
- Primary: `Повторить итоги`.
- Secondary: `Открыть транскрипт`.

### Processing Failed

- Upload or processing cannot continue automatically.
- Primary: `Повторить обработку` when allowed.
- Secondary: `Связаться с поддержкой` or `Скачать доступное`.

### Local Only

- Meeting exists on desktop but server does not have final truth.
- Primary: `Открыть статус на Mac`.
- Secondary: `Повторить загрузку`.

### Deleted

- Server-controlled objects deleted or deletion in progress.
- Primary: `Отчёт об удалении`.
- Copy must state that external systems, backups, local buffers, or offline
  devices may have separate expiry or purge behavior.

### Access Denied

- Do not leak title, transcript, participants, or source content beyond safe
  metadata.
- Primary: `Запросить доступ` or `Войти`.

### Degraded

- Some outputs are usable, some are blocked or low confidence.
- Primary: `Открыть доступное`.
- Warning must say exactly which output is degraded.

## Forbidden

- No universal deletion promise.
- No meeting-content leak in access-denied state.
- No "ready" label when transcript or notes are missing.

## Acceptance Evidence

Covered by Figma `V8 06 - Загрузка и обработка в списке`,
`V8 11 - Веб-детали встречи и транскрипт`, `V8 12 - Поделиться, экспорт, удаление`,
`V8 14 - Правила интерфейса и QA`, and `design/validation-evidence.md`.
