# UI Contract: Meeting Actions Menu

## Purpose

Define the shared browser and embedded-cabinet contract for `Ещё` without
changing Feature 120 export, audio download or deletion APIs.

## Authority Map

| Concern | Authority | UI obligation |
|---|---|---|
| Export availability | Existing content export capability | Render action only when at least one supported scope is ready |
| Audio download availability | Existing cabinet egress policy/state | Render link only when server says available |
| Delete availability | Existing governance/delete policy | Render action only for allowed state and actor |
| Export bytes/revision/audit | Existing Feature 120 endpoints | Open existing dialog; do not format or authorize in the menu |
| Audio bytes/audit | Existing download endpoint | Follow existing server-mediated link |
| Deletion truth/lifecycle | Existing delete confirmation/service | Open existing confirmation; preserve report and bounded copy |
| Details content | Existing meeting review projection | Re-present existing fields; create no new source |

## Render Contract

`Поделиться` remains outside the menu. `Ещё` controls a compact menu. Available
items appear in this stable order:

1. `Экспортировать…` — `Расшифровка или итоги`;
2. `Скачать аудио…` — `Исходная запись`;
3. `Сведения о встрече`;
4. divider, then `Удалить встречу…`.

Unavailable actions are absent. Empty helpers, groups and dividers are absent.
When no action exists, `Ещё` is unavailable and no empty surface is exposed.

## Interaction Contract

- `Ещё` exposes its relationship, menu state and expanded state.
- Enter/Space opens and focuses the first item.
- Down opens/focuses first; Up opens/focuses last.
- Up/Down wrap through available items; Home/End move to first/last.
- Enter/Space activates the focused item.
- Escape or outside click closes and restores focus to `Ещё`.
- Selecting an item closes the menu before or as its destination opens.
- Export opens the existing export dialog.
- Audio follows the existing download link.
- Details opens a separate named modal dialog.
- Delete opens the existing named confirmation dialog.

## Details Dialog Contract

The dialog contains only existing available information, ordered for ordinary
review first and diagnostics last:

1. files and their current download/export truth;
2. meeting revision and calendar context;
3. speakers;
4. recent activity;
5. deletion/lifecycle truth and the existing report link.

It has an explicit close control, traps Tab/Shift+Tab, closes on Escape or
backdrop click and restores focus to visible `Ещё`.

## Accessibility Contract

- Every item has a Russian accessible name and text label.
- Decorative icons are hidden from assistive technology.
- Delete is identified by text/icon/position as well as color.
- Targets are at least 40 CSS px high.
- Focus is visible and not clipped.
- Menu and dialogs remain usable at 200% zoom and 320 CSS px viewport.
- Reduced motion, increased contrast, forced colors and light/dark appearance
  reuse existing cabinet behavior.
- Browser and embedded cabinet expose the same order and semantics.

## Security And Lifecycle Contract

- Menu visibility is not authorization.
- Direct export/download/delete requests retain their existing final server
  authorization, policy, audit, race and deletion checks.
- No raw content, token, signed URL, credential or policy debug detail is added
  to markup, telemetry or committed evidence.
- No endpoint, persistence, artifact class or lifecycle registration is added.

## Enhancement Boundary

Script owns transient menu presentation and focus behavior. It does not
manufacture capabilities, replace server checks or change the existing export,
download and deletion behavior when scripting is unavailable.
