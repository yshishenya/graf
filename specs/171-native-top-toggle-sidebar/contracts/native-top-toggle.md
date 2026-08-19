# Native top-toggle contract

## View contract

- `DesktopMeetingShellChrome.inspectorToggleHitSize >= 44`.
- `inspectorToggleTopInset` and `inspectorToggleTrailingInset` are shared by
  both modes.
- The source has one `inspectorDisclosureHeader(isExpanded:)` call in
  `compactInspector` and one in `inspector`.
- The expanded `ScrollView` contains content only and reserves the top-slot
  height; it does not own a second disclosure control.

## Accessibility contract

- Expanded label: `Скрыть панель управления`.
- Collapsed label: `Показать панель управления`.
- Hints describe the next action in Russian.
- Identifier: `desktop-meeting-shell-inspector-toggle`.
- Existing settings, capture and attention identifiers remain unchanged.

## Visual contract

Computer Use evidence must show:

1. collapsed native panel: one top-right control;
2. expanded native panel: same top-right coordinate;
3. no overlap with `Запись`, settings, capture card or attention disclosure;
4. two consecutive clicks work without pointer movement.
