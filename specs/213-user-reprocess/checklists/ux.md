# UX and Accessibility Checklist: Повторная обработка записи

## Information architecture

- [x] The action is in the ordinary meeting `Ещё` menu
- [x] It appears before deletion and only for eligible owner recordings
- [x] Admin pages, operator roles and reason forms are absent
- [x] Shared recipients continue to see the published result without recovery controls

## Confirmation

- [x] Copy names transcript, speakers and outcomes
- [x] Copy promises continuity and unchanged source audio
- [x] Cancel, Escape, initial focus and focus restoration are specified
- [x] Busy state prevents repeated activation

## Status and recovery

- [x] Active replacement leaves transcript, player, export and outcomes usable
- [x] Reliable retry time shows time, countdown and `Повторить сейчас`
- [x] Unknown retry time shows no fabricated countdown
- [x] Manual retry resets only after a server-accepted newer generation
- [x] Terminal failure preserves the current version and offers a fresh launch
- [x] Old outcomes carry `По предыдущей версии расшифровки`

## Accessibility and responsive behavior

- [x] Keyboard and visible-focus behavior reuse existing components
- [x] Status transitions are announced once
- [x] Per-second countdown is outside the live region
- [x] Color is not the only status signal
- [x] Browser and embedded macOS use the same responsive page
