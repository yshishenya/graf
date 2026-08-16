# UX Requirements Checklist: Паритет нативных кнопок с веб-частью

- [x] Требование к базовой высоте 32 px, радиусу 7 px и padding 12 px однозначно
      зафиксировано и ограничено текстовыми кнопками.
- [x] Источник цветов и light/dark tokens явно указан в spec и research; action
      accent — фиолетовый `#8c73ff`, а синий status token не используется для
      основных native action-кнопок.
- [x] Disabled, pressed, destructive и повышенный контраст входят в acceptance
      criteria, а не остаются неявными визуальными пожеланиями.
- [x] Сохранение accessibility labels, identifiers, shortcuts и hit-area
      выделено отдельным функциональным требованием.
- [x] Scope перечисляет capture, shell recovery, support, permission и settings
      call sites; web CSS и поведение действий исключены.
- [x] План содержит focused tests, build и manual dark/light validation.
- [x] Spec не ослабляет видимый Record/Stop, one-action Stop или существующие
      capture gates.

## Notes

- Отдельные пункты о фактическом результате ручной проверки будут закрыты в
  quickstart и финальном отчёте после реализации.
