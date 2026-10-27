# Specification Quality Checklist: Надёжное ожидание результата MediaScribe

**Purpose**: Проверить полноту требований перед планированием.
**Created**: 2026-08-26
**Feature**: [spec.md](../spec.md)

- [x] Описана пользовательская ценность и поведение.
- [x] Сценарии понятны пользователю и тестировщику.
- [x] Обязательные разделы заполнены.
- [x] Не осталось маркеров NEEDS CLARIFICATION.
- [x] Покрыты pending, ready, terminal, retryable и watchdog состояния.
- [x] Описаны same-job reconciliation и Temporal replay.
- [x] Границы задачи и зависимости указаны.
- [x] Для каждой пользовательской истории есть независимая проверка.
- [x] Canonical M4A ограничена ручной загрузкой; first-party `single_wav_v1`
  продолжает отправлять canonical WAV, historical dual-track остаётся read-only
  compatibility.
- [x] Описаны archive/no-archive custody, quota и purge semantics.
- [x] Описаны corrupt, terminal, deletion, supersession и crash boundaries.
- [x] Указаны измеримые pass-count, exact-byte и one-provider-job критерии;
  ambiguous POST может иметь несколько exact same-key HTTP attempts.

## Независимая сверка 28.10.2026

Подтверждены 12 из 12 пунктов качества требований. Перечитаны актуальные
`spec.md`, `plan.md`, `tasks.md`, `quickstart.md` и договор обработки. Устаревшая
инструкция о пропуске Full CI исправлена; добавлена классификация Legacy Impact
для документальной сверки. Это не приёмка реализации, T030 или T031.
Постатейные основания и ограничения: [отчёт](../review-t029-20261028.md).
