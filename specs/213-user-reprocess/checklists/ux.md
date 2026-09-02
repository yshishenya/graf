# UX and Accessibility Checklist: Повторная обработка записи

## Information architecture

- [x] The action is in the ordinary meeting `Ещё` menu
- [x] It appears before deletion and only for eligible owner recordings
- [x] Admin pages, operator roles and reason forms are absent
- [x] Shared recipients continue to see the published result without recovery controls

## Confirmation

- [x] Copy contains only the approved manual speaker-name reset warning
- [x] Copy states that the reset happens only after successful processing
- [x] Cancel, Escape, initial focus and focus restoration are specified
- [x] Busy state prevents repeated activation

## Status and recovery

- [x] Active replacement hides the owner's transcript, player, speaker UI and outcomes behind one neutral indicator
- [x] Expected waiting, automatic retry and temporary status-fetch failures use the same neutral state
- [x] Replacement UI exposes no countdown, stage, timestamp, manual check or retry-now action
- [x] Terminal failure restores the current version and manual names and offers `Попробовать снова`
- [x] Successful publication updates transcript and player together without carrying old manual names
- [x] Old outcomes carry `По предыдущей версии расшифровки`

## Accessibility and responsive behavior

- [x] Keyboard and visible-focus behavior reuse existing components
- [x] Status transitions are announced once
- [x] Replacement start, success and terminal failure are announced once without per-second updates
- [x] Color is not the only status signal
- [x] Browser and embedded macOS use the same responsive page
