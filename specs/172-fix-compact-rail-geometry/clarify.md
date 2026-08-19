# Clarifications: Цельная геометрия compact rail

### Session 2026-08-19

- Критических неоднозначностей нет: supplied screenshot, computed CSS cascade
  и история `99479bcc` / `9a93a5cc` подтверждают один и тот же дефект и одну
  минимальную модель исправления.
- Текущие product widths `64px / 176px` сохраняются; полный откат старого rail
  `52px / 184px` не требуется и вернул бы уже устранённые регрессии.
- Compact toggle, navigation item, active state и profile action используют
  один квадрат `40×40px`, общий центр rail и существующий radius.
- Финальный JS-ready collapsed state становится единственным владельцем полной
  compact-геометрии на всех ширинах; JS state semantics и Jinja markup не
  меняются.
- Старые embedded media-блоки можно сократить только там, где они дублируют или
  конфликтуют с финальным collapsed contract. Responsive breakpoint, expanded
  layout и profile menu остаются вне scope.
