# Clarification: Контекстная ссылка на приложение на экране входа

**Date**: 2026-08-18  
**Feature**: [spec.md](spec.md)

## Result

Критических неоднозначностей не обнаружено. Пользователь явно разделил web и
embedded macOS-сценарии, а текущий код уже передаёт embedded-назначение через
безопасный `next=/desktop/...`. Изменение ограничено presentation layer и не
меняет auth, redirect validation или download route.

## Coverage

| Категория | Статус | Основание |
|---|---|---|
| Functional scope | Clear | Web CTA и embedded отсутствие CTA заданы отдельно. |
| Interaction and UX | Clear | Позиция, focus, responsive boundary и non-overlap заданы. |
| Security and privacy | Clear | Existing safe `next` normalization и auth flow сохраняются. |
| Integration | Clear | Используется существующий `/download`; новый API не нужен. |
| Edge cases | Clear | Ошибки auth, desktop settings, invalid next и узкая ширина перечислены. |
| Completion signals | Clear | Focused render и visual matrix имеют измеримые критерии. |

## Questions

Вопросы пользователю не задавались: разумный default уже зафиксирован в
спецификации и подтверждён аудитом текущего маршрута.
