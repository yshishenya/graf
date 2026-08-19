# UI Contract: Нижний toggle native панели

- `compactInspector` and `inspector` each expose exactly one
  `desktop-meeting-shell-inspector-toggle` control.
- Expanded `inspector` contains a scrollable content region followed by a fixed
  footer; the disclosure button is not inside the ScrollView content header.
- Expanded footer aligns the button to `.trailing` and preserves the 44px hit
  target.
- `InspectorDisclosureButton` keeps the existing Russian labels, help text,
  accessibility hint, hover state and reduced-motion behavior.
- Existing inspector width, capture controls, settings action and attention
  semantics remain unchanged.
