# UX Checklist: Стабильные статусы обработки

**Purpose**: Проверить требования к shared browser/WebView status UX
**Created**: 2026-08-25

- [x] Один видимый статус на строку сформулирован явно [Truth]
- [x] Stable DOM/height для active processing задан до первого fetch [Layout]
- [x] Failed rows защищены от промежуточного copy [Failure state]
- [x] Focus, selection и filter/sort refresh покрыты [Interaction]
- [x] Aria-live объявляет только реальное изменение, не каждый tick [Accessibility]
- [x] Browser и embedded cabinet используют общий код [Parity]
- [x] Narrow viewport входит в rendered QA [Responsive]
- [x] Приватное meeting content запрещено в evidence [Privacy]
