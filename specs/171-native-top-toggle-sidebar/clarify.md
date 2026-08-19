# Clarifications: Единый верхний toggle и аккуратный rail

### Session 2026-08-19

- Критических неоднозначностей нет: native control должен быть одним верхним
  trailing-slot в обоих состояниях; web rail сохраняет ручное состояние до
  toggle или Escape.
- Для embedded default используется `min-width: 981px`, потому что текущий
  `1121px` порог подтверждённо оставляет normal large `GRAF Dev` compact после
  Reload.
- Cross-session persistence и unrelated product redesign остаются вне scope.
