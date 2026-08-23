# UX evidence: Feature 200 Windows

Статус: partial, не release evidence.

Проверено на portable contract surface текущего macOS-хоста:

- `AccessibilityStateProvider` сохраняет keyboard focus и screen-reader labels,
  нормализует DPI в диапазоне 100–400%.
- `RecordingIndicator` остаётся visible и сохраняет one-action Stop для
  `recording`/`paused`/`degraded` независимо от WebView projection.
- Automatic prompt содержит доступные русские действия «Записать сейчас»,
  «Пропустить» и «Всегда писать это приложение».
- `WebViewCabinetParityTests` проверяет server-owned routes без native meeting UI.

Не подтверждено без Windows host: настоящий WinUI 3 visual review, tray/window
focus, screen reader, High Contrast, 200% DPI, narrow-window layout, reduced
motion, signed MSIX и clean-room visual review. Эти пункты остаются открытыми в
`checklists/ux.md` и не позволяют заявлять Windows distribution readiness.
