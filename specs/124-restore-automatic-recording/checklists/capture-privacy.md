# Capture And Privacy Requirements Checklist: Восстановление автозаписи встреч

**Purpose**: Проверить, что требования автозаписи сохраняют границы захвата,
видимое согласие и честное поведение при отказе.
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] Описаны все gates, от которых зависит prompt и automatic start: confidence,
  target, permission, readiness, policy, suppression, storage и active session.
- [x] Требования отделяют verified native targets от unknown, browser,
  diagnostic-only и future-platform targets.
- [x] Manual Start, local visible indicator и one-action Stop явно сохранены.
- [x] Описано exact-target поведение для сохранения и отзыва auto-record.
- [x] Описаны duplicate, restart, stale registry и prompt-dismiss edge cases.

## Requirement Clarity

- [x] Время countdown задано точным числом — восемь секунд.
- [x] Указано, что timer expiry не отменяет повторную проверку gates.
- [x] Запрещён arbitrary system audio, media playback, notification, music,
  video и unknown-app start.
- [x] Указано, что auto-record action — это eligibility, а не обход capture
  prerequisite path.
- [x] Отдельно зафиксировано, что отмена/disappearance prompt отменяет timer и
  не может позднее начать запись.
- [x] Для одновременных detector outputs задан лимит в один recording trigger.

## Requirement Consistency And Traceability

- [x] Требования Feature 124 не противоречат конституционному принципу Visible
  Consent And User Control.
- [x] Документы сохраняют историческую правду Feature 121 и одновременно
  маркируют её no-countdown/no-autostart текст как superseded.
- [x] Quickstart содержит blocked-gate сценарии и metadata-only evidence rules.

## Notes

- Все пункты пройдены на уровне качества требований; runtime evidence входит в
  implementation validation, а не в эту checklist.
