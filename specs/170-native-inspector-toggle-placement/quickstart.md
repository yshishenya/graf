# Quickstart: Нижний toggle native панели

## Focused checks

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp
swift test --package-path apps/macos -Xswiftc -enable-testing
git diff --check
```

If the package exposes a narrower test scheme, run the repository's existing
macOS test command and select `DesktopMeetingShellWebViewBoundaryTests` and
`AppControlAccessibilityTests`.

## Visual matrix

Use Computer Use with installed `GRAF Dev` and `GRAF`: collapsed inspector,
expanded inspector, pointer hover, keyboard focus and two consecutive toggles.
Record only state/geometry/labels; do not save meeting content or credentials.

## Evidence

Status: implementation and macOS build/visual review passed. `GRAF Dev` showed
the expanded «Скрыть панель управления» control in the bottom-right footer;
collapsed and expanded states used the same trailing control, and the second
click returned the panel to its prior state without moving the pointer.
Accessibility labels/hints and 44 px target checks passed. Focused XCTest runs
passed: 21 accessibility tests and 15 shell boundary tests. Evidence is
metadata-only.
