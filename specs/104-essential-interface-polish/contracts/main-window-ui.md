# UI Contract: GRAF Main Window

## Purpose

Define the visible, interactive contract for the main macOS window without changing server/native ownership or copying the supplied reference.

## Layout

At the default `1280×760` content size:

```text
server navigation  |  flexible meeting workspace  | native capture rail
168–176 CSS px     |  minmax(0, 1fr), max 1040    | 52 pt
```

When the native inspector is intentionally expanded, its target width is 304–312 pt. The meeting workspace absorbs the change without hiding Stop, changing server navigation state, or introducing horizontal scrolling. Recording start itself does not expand the inspector.

The supported minimum window is `1040×680`. Above the responsive threshold, the full server sidebar remains visible. At the minimum window it becomes an approximately 64 px icon rail with accessible names/tooltips; filter, sort, and upload labels may also collapse while their controls keep exact names. The title, duration, status, date, upload action, and 48–52 pt native capture rail remain visible without horizontal scrolling or a blank reserved column.

## Visual Tokens

Reuse the current GRAF family as the source of truth:

| Token | Contract |
|---|---|
| App background | Existing near-black `#191a1c` family. |
| Navigation/rail | Existing `#202224` family, separated by one subtle divider. |
| Content surface | Existing `#242629` family only where grouping is needed. |
| Primary text | Existing light label color; normal text contrast at least 4.5:1. |
| Secondary text | Must remain legible at the final size; not used for critical state alone. |
| Accent | Existing GRAF violet `#8c73ff`, reserved for current selection and primary non-destructive action. |
| Destructive | System/established red, paired with text/icon and confirmation. |
| Focus | 2 px visible outline with at least 3:1 change against adjacent colors. |
| Radius | 8 px for controls/cards; pill only for a true compact status/count. |
| Spacing | 8 / 12 / 16 / 24 rhythm. |

Do not add a Krisp-like trial gradient, purple `New` badge, proprietary right-side voice controls, or copied iconography.

If the wordmark image cannot load, the sidebar retains an accessible text label `GRAF` without changing navigation order or reserving an empty oversized card.

## Typography And Density

| Role | Target |
|---|---|
| Page title | 18–20 px/pt semibold. |
| Row title / primary control | 13–14 px/pt medium or semibold. |
| Supporting metadata | At least 12 px/pt. |
| Control height | 32–36 px/pt. |
| Meeting row | 44–48 px minimum. |
| Icon-only hit target | At least 28×28 pt native and 32×32 CSS px in the embedded surface. |

Text truncation is allowed only for noncritical row titles after the date, duration, state, and actions retain meaning through accessible labels/tooltips. Critical actions and errors wrap instead of becoming ambiguous.

## Default Reading Order

1. Sidebar brand and enabled destinations.
2. `Мои встречи` heading.
3. Search.
4. Filter, sort, and upload actions.
5. Meeting list.
6. Compact native capture rail.

The visual order and keyboard/VoiceOver order must agree within each owner surface. The WebView and native rail remain separate accessibility regions with meaningful labels.

## Visible Elements By Default

- Compact GRAF wordmark.
- `Мои встречи` and `Настройки` navigation.
- `Выйти` at low emphasis.
- One search field.
- Filter disclosure, sort disclosure, and `Загрузить`.
- Meeting rows.
- Native capture rail with direct Start/Stop, attention count only when required, and disclosure.

The default screen must not contain disabled roadmap navigation, disabled invitation, hard-coded plan/trial state, an empty calendar/upcoming block, saved-filter placeholder, inactive bulk actions, duplicate filter/sort decoration, telemetry, report-copy actions, diagnostics disclosure, idle meters, or a duplicate brand label.

## Interaction Contract

- Search updates the existing list route after the current short debounce and preserves other query values.
- Filter/sort disclosures are keyboard reachable, named, expose expanded state, and close through normal semantic behavior. `Escape` or focus movement must not trap the user.
- Active filters are visible without reopening the disclosure; reset is one action.
- Upload retains the existing modal and validation behavior.
- Selection mode begins only with explicit row/select-all intent and ends when the last selection is cleared or the list replacement contains no selected row.
- Delete remains confirmed and does not promise erasure outside GRAF-controlled boundaries.
- Inspector disclosure preserves the current animation duration class and never obscures its own focused control.
- With macOS Reduce Motion enabled, nonessential width/fade transitions become immediate or substantially reduced; meaning, focus, and actions do not depend on animation.

## Screen States

| State | Required main content |
|---|---|
| Ordinary list | Search/tools and readable meeting rows; no unsupported plan/calendar region. |
| Filtered/search | Active refinement visible, result count/list, one-action reset; no duplicate title. |
| Empty result | `Ничего не найдено` plus reset/refine guidance, not a first-run install card. |
| First run / no meetings | Concise explanation that reuses the persistent toolbar upload and native recording actions; no duplicate CTA, app-download/install step, calendar onboarding, or roadmap placeholder inside the installed macOS app. |
| Selection | Contextual toolbar and visible selection controls; meeting reading remains possible. |
| Active recording | Stable meeting layout; native titlebar HUD and rail expose Stop. |
| Actionable local problem | Native panel may open with one recovery action; server list remains usable. |
| Cabinet unavailable | Native capture remains usable and truthful; server area shows a human retry/sign-in state. |

## Accessibility

- Use native HTML/SwiftUI controls before custom widgets.
- Every icon-only button has a concise Russian accessible name and help/tooltip.
- Focus remains visible, un-obscured, and follows reading order.
- State is communicated by copy or a conventional state icon in addition to color; the compact readiness indicator uses a check/ready symbol with the exact `Готово к записи` name rather than an unexplained color dot.
- Destructive confirmation receives initial logical focus and returns focus to the initiating control/row when closed.
- Selection and delete affordances are absent visually and from the accessibility tree in ordinary reading mode; they appear together on row hover, keyboard focus, or explicit selection mode with their exact accessible names.
- Increased contrast must preserve boundaries, focus, selected rows, and active recording.

## Privacy And Evidence

No screenshot committed for this contract may contain real meeting titles, transcript text, email, local path, token, signed URL, or other private content. Visual QA uses synthetic/redacted fixtures or ephemeral local evidence outside git.
