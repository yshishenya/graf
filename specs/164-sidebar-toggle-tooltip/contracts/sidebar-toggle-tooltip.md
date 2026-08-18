# Contract: Sidebar toggle tooltip

- `data-cabinet-rail-toggle` identifies the only toggle in a full shell.
- `aria-controls="cabinet-sidebar"` identifies the controlled region.
- `aria-expanded="false"` + `data-tooltip="Показать боковую панель"` describe
  the collapsed state; `true` + `Скрыть боковую панель` describe expanded state.
- `title` remains a fallback; CSS hover/focus content is non-interactive.
- Pointer, Enter and Space use the existing button activation semantics.
- Repeated initialization must preserve one `data-cabinet-rail-toggle` and one
  guarded listener.

