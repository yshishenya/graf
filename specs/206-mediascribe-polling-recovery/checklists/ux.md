# UX Checklist: MediaScribe polling recovery

**Purpose**: Проверить, что ожидание, временный сбой и terminal failure не
смешиваются в пользовательском пути.
**Created**: 2026-08-26
**Feature**: [spec.md](../spec.md)

- [X] Pending provider status объяснён простым языком.
- [X] При назначенном повторе показывается countdown до следующей проверки.
- [ ] Ручная проверка видима, доступна с клавиатуры и сбрасывает countdown.
- [X] Terminal provider failure имеет отдельный текст и recovery action.
- [X] Watchdog state не утверждает, что провайдер сообщил ошибку.
- [X] Transcript не появляется до готовой diarization.
- [X] Summary state не блокирует готовый transcript.
- [X] Detail и list показывают одну и ту же terminal/pending семантику.
- [X] Скрытое окно не теряет плановую detail-проверку и догоняет terminal state.
- [X] Normalization pending не показывается как provider error.
- [X] Normalization retry имеет countdown и отдельное действие «Повторить подготовку».
- [X] Terminal input-audio state прекращает polling и предлагает загрузить другой файл.
- [X] No-archive flow не показывает transient canonical в плеере.

## Независимая сверка 28.10.2026

Подтверждены 12 из 13 пунктов в пределах автоматических договоров состояния,
текста и серверной проекции. Пункт о ручной проверке оставлен открытым:
серверный сброс таймера и HTML-кнопка подтверждены, но текущей проверки её
видимости и запуска с клавиатуры в настоящих web/embedded путях нет. Это
приёмка T030; проверка строк исходников и Node с подменённым DOM её не заменяет.
Постатейные основания и ограничения: [отчёт](../review-t029-20261028.md).
