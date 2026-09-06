# UX Checklist: MediaScribe polling recovery

**Purpose**: Проверить, что ожидание, временный сбой и terminal failure не
смешиваются в пользовательском пути.
**Created**: 2026-08-26
**Feature**: [spec.md](../spec.md)

- [X] Pending provider status объяснён простым языком.
- [X] При назначенном повторе показывается countdown до следующей проверки.
- [X] Ручная проверка видима, доступна с клавиатуры и сбрасывает countdown.
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
