# Settings UX Requirements Checklist: 119 Registry Expansion

**Date**: 2026-07-21
**Purpose**: Validate that expanded coverage is understandable and accessible.

## Information Architecture

- [x] Requirements show every verified native app in one common prompt/auto-record list.
- [x] No engineering-facing “diagnostic” section appears in user settings.
- [x] Every verified native target is prompt-enabled and receives the existing toggle.
- [x] Shared-identity forks appear as aliases in one row without duplicate toggles.
- [x] Empty/unavailable registry copy is specified without blocking manual recording.
- [x] No new status UI is required; post-enable QA remains in the feature evidence.

## Scale And Accessibility

- [x] Complete catalog overflow is addressed through scrolling.
- [x] Keyboard navigation and VoiceOver labels are required.
- [x] Increased text size and narrow-window behavior are required.
- [x] Status meaning is textual and does not depend on color.
- [x] Existing original GRAF/native visual language remains the design boundary.

## Testability

- [x] Each verified row has the existing independently testable toggle predicate.
- [x] “Выбрать все” covering the complete verified target set is explicitly testable.
- [x] Alias rendering is independently testable with Telegram shared-ID products.
- [x] Unavailable-cache behavior has a concrete expected state.

## Outcome

All settings requirement-quality checks pass. No additional clarification is
required before task decomposition.
