# UX and accessibility checklist: Feature 195

**Статус**: частично закрыт HTML/JS/CSS contract review; browser E2E и
usability research остаются незакрытыми.

## User path

- [ ] User can tell whether the recording is safe, whether action is needed and what happens next.
- [x] Transcript is hidden before diarization and visible after diarization regardless of summary state.
- [x] Summary has its own loading/error/unavailable state and action.
- [x] Temporary failure shows automatic next attempt, countdown when trustworthy and «Проверить обработку».
- [x] Unknown upload outcome says GRAF is checking the original attempt and does not suggest re-upload.
- [x] Terminal failure has no countdown and offers a concrete next path.
- [x] Existing artifacts remain visible when another artifact fails.

## Countdown and manual action

- [x] Countdown uses server `next_attempt_at` and is recalculated after refresh/background tab.
- [x] No polling request is made for every countdown tick.
- [x] Button has idle, submitting, in-flight, success, retryable and terminal states.
- [x] Double click, two tabs and automatic/manual race are fenced to one operation.
- [x] After manual action the old countdown is reset; a new countdown appears only from the new server state.
- [x] If time hint is absent or invalid, UI does not display a false exact date.

## Accessibility and parity

- [ ] Keyboard focus reaches the action and is preserved after fragment refresh.
- [x] Accessible name says what «Проверить обработку» checks/retries.
- [x] Busy/disabled state is exposed to screen readers and prevents duplicate activation.
- [x] Important state transitions use a polite live region; ticking seconds are not announced.
- [x] Reduced-motion and forced-colors styles plus shared web/embedded projection are present.
- [x] Web and embedded desktop use the same status/recovery projection and localized copy.
- [x] Provider ids, HTTP codes and raw errors are absent from normal copy.

## Research/measurement

- [ ] Usability test checks whether a user can answer the four recovery questions without support.
- [x] Track first usable result, retry recovery, manual action success and support handoff by surface.
- [x] Analytics events are metadata-only and use bounded duration/size buckets.

Отметки выше подтверждены статическим accessibility contract, локальными
unit/contract tests и full CI; реальное поведение в браузере, фокус после
HTMX/fragment refresh, узкие окна и usability-ответы ещё нужно проверить
отдельно.
