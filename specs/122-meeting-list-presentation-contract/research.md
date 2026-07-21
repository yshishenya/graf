# Research: Meeting List Presentation Contract

## Evidence Boundary

The research used the current GRAF list implementation, its browser/embedded accessibility surface, the user's supplied GRAF and Krisp screenshots, feature 104's clean-room baseline, and current official design/accessibility guidance. Real meeting screenshots remain local because they contain private meeting and account metadata.

Krisp is evidence only for calm density, hierarchy, and contextual disclosure. It is not a source for GRAF copy, assets, icons, colors, composition, folders, tags, favorites, save-later, unread, sharing, billing, or upcoming-meeting behavior.

Current external guidance consulted:

- Apple [Lists and tables](https://developer.apple.com/design/human-interface-guidelines/lists-and-tables): text rows should be easy to scan and selection feedback must match whether a row navigates or toggles state.
- Apple [Focus and selection](https://developer.apple.com/design/human-interface-guidelines/focus-and-selection/): macOS list focus should be visibly highlighted and focus must not cause an unexpected navigation context shift.
- Apple [Search fields](https://developer.apple.com/design/human-interface-guidelines/search-fields) and [Searching](https://developer.apple.com/design/human-interface-guidelines/searching): keep one clearly identified search surface close to the collection it filters and account for window resizing.
- W3C [Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html): progress, results, and errors that do not move focus need programmatic announcement without interruption.
- W3C [Focus Order](https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html), [Focus Appearance](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html), and [Name, Role, Value](https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html): focus order must preserve meaning, actionable elements need real roles/names/states, and the focus indicator must be discernible.
- W3C [Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) and [Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html): targets need at least 24×24 CSS px or sufficient spacing, while meaningful control/focus cues need 3:1 contrast. GRAF keeps the stronger 32×32 project target for contextual row controls.

## Decision 1: Derive one compact presentation value object

**Decision**: Add one immutable meeting-list presentation projection in the existing cabinet view-model boundary. It derives the display title, duration, time label, one compact status, optional measured progress, optional explicit action, and a complete accessible description from the existing `MeetingListItem` plus the selected sort.

**Rationale**: Today `rendering.py` concatenates overall processing, playback, and calendar labels independently. Scattered template guards would make precedence incomplete and hard to test. A small pure projection makes the total state order reviewable without changing the public list schema or source records.

**Alternatives considered**:

- Add fields to the public `MeetingListItem` API — rejected because the requirement is web-presentation-only and existing API consumers must remain compatible.
- Compute each token independently in Jinja/Python rendering — rejected because it recreates the current collision problem.
- Introduce a frontend state store/component framework — rejected because server rendering already owns the truth and no new dependency is needed.

## Decision 2: Ready is silent; the first true exception wins

**Decision**: Use this total compact priority: deleting → failed result → ambiguous calendar choice → local-only custody → active upload → processing → playback preparing → playback unavailable limitation → other partial limitation → ready with no status. Normal playback availability and ordinary calendar provenance never become list status.

**Rationale**: A compact list should answer whether the result is available, waiting, limited, or actionable. Repeating `Готово`, `Аудио готово`, and `Без календарного контекста` makes normal rows look like monitoring output and makes real exceptions less salient.

**Alternatives considered**:

- Keep three independent status families — rejected because the user must resolve contradictions and priority themselves.
- Show a generic `Нужна помощь` for all problems — rejected because `Без аудио` and `Не удалось обработать` communicate different current impact.
- Remove underlying calendar/playback truth — rejected because detail and recovery surfaces still need it; only compact projection changes.

## Decision 3: Native HTML actions separate opening from selection

**Decision**: Make the meeting link the single primary row action and the real checkbox the selection control. The readable row area activates the link; `Enter` opens. A focused checkbox/selection intent uses native `Space` behavior. Delete remains a separate button. Avoid a focusable non-action `article` with nested hidden controls and avoid a custom `grid` because the list does not need spreadsheet navigation.

**Rationale**: The current focusable row toggles selection on blank click while the title link opens, which makes the row's action ambiguous and creates nested focus semantics. Standard links, checkboxes, and buttons expose names/roles/states through the browser and reduce custom keyboard code.

**Alternatives considered**:

- Make the whole row a custom button — rejected because it would contain separate checkbox/delete actions and produce invalid or confusing nested interaction.
- Use `listbox` — rejected because WAI-ARIA listbox options do not support nested interactive descendants well.
- Use `grid` with roving focus — rejected as unnecessary complexity for a short content list with a normal link and two contextual actions.

## Decision 4: Contextual controls reserve geometry and remain reachable

**Decision**: Keep fixed intent and delete target columns. Pointer hover, keyboard focus-within, or selected state reveals controls without changing column geometry. The controls remain in logical DOM order and become focusable when the row has interaction intent; non-hover/coarse-pointer media keeps them persistently available. Each contextual target is at least 32×32 CSS px.

**Rationale**: Progressive disclosure reduces ordinary noise only if keyboard, VoiceOver, magnification, and non-hover users retain the same functions. Fixed columns prevent title/date movement that would harm scanning.

**Alternatives considered**:

- Permanently display every checkbox and delete button — valid but unnecessarily administrative for normal reading.
- Hide controls only with CSS opacity and `aria-hidden`/`tabindex=-1` forever — rejected because keyboard users would lack an equivalent path.
- Add an overflow menu — rejected because delete is the only row-specific secondary command.

## Decision 5: Default sort follows meeting time, not backend activity

**Decision**: Change browser and embedded defaults to `started_desc`, keep SQL `nullslast(desc(started_at))`, and display `Сначала новые`. When users explicitly choose `updated_desc`, the trailing label becomes `Обновлено <date, time>`; otherwise it describes the meeting's trusted start time. Rows without trusted start time show `Без даты` and remain after dated rows in the default sort.

**Rationale**: People scan meetings by when they happened. `updated_at` may change because of backend work and is misleading when rendered like the meeting date.

**Alternatives considered**:

- Keep `updated_desc` but rename only the toolbar — rejected because ordering and visible time would still conflict.
- Remove recently updated sorting — rejected because it remains a supported useful explicit choice.
- Persist a user preference — rejected as new data and unnecessary for this slice.

## Decision 6: Refined counts and asynchronous feedback are contextual live status

**Decision**: Remove the duplicate `Записи встреч` heading and persistent sort subtitle. Show `Найдено: N` only when search or filters are active. Place deletion feedback above the list and keep it in a polite live region. Announce refinement, progress, deletion, and error results without moving focus; after a focused row disappears, restore focus to the next row, previous row, or list heading.

**Rationale**: W3C treats result/progress/error copy added without a context change as status messages. The current feedback after a potentially long list can be visually missed, while focus theft would interrupt the task.

**Alternatives considered**:

- Put feedback in a modal — rejected because accepted deletion is nonblocking status, while confirmation already uses a dialog.
- Auto-focus each message — rejected because it disrupts keyboard and screen-reader position.
- Always display total count — rejected because it adds noise when the unrefined collection is already visible.

## Decision 7: Empty and failure states are distinct and metadata-safe

**Decision**: Keep separate first-empty, no-results, loading, offline, service-unavailable, session-expired, and revoked-access copy from [visual-target.md](./visual-target.md). Reuse persistent upload/native record actions for first-empty; provide only the applicable reset/retry/sign-in/back action elsewhere. Never repeat cached meeting metadata in session/access failure surfaces.

**Rationale**: Each state has a different next step and privacy boundary. One generic empty/error block either duplicates actions or exposes information after access is gone.

**Alternatives considered**:

- One generic `Ничего нет` state — rejected because it obscures whether the user should create, reset, retry, or authenticate.
- Add installation/calendar onboarding — rejected because the installed app already exposes supported recording/upload actions and this slice adds no calendar onboarding.

## Decision 8: Evidence is synthetic, matched, and clean-room

**Decision**: Validate the same synthetic state fixtures before and after at `1280×760`; repeat layout-sensitive states at `1040×680`. Record keyboard/accessibility-tree and contrast/Reduce Motion evidence. Keep real user screenshots and local runtime paths out of git.

**Rationale**: Matched evidence makes regressions reviewable while preserving meeting privacy and brand-distance boundaries.

**Alternatives considered**:

- Commit the supplied real screenshots — rejected by privacy requirements.
- Treat one happy-path screenshot as completion — rejected because interaction, failure, minimum-width, and assistive-technology states are part of the contract.

## Resolved Technical Unknowns

- **Public API/schema change**: none.
- **Database migration**: none.
- **Native macOS code change**: none expected; native capture is a regression boundary.
- **New dependency or client framework**: none.
- **Default sort implementation**: existing `started_desc` sorter already uses `nullslast`.
- **Status-filter transport**: retain existing allowlisted values (`ready`, `processing`, `partial`, `failed`) and grouped server behavior; change only user-facing labels.
- **Deletion behavior**: retain current dialog, CSRF, authorization, bounded copy, request, and failure flow.
- **External design gate**: none; repository `visual-target.md` is the approved pre-build target.
