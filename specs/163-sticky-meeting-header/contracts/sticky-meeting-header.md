# UI Contract: Закреплённый верхний блок встречи

- `meeting_detail_content.html` has one `data-meeting-detail-header` wrapper
  containing `.topline`, `#meeting-share-host` and `.meeting-detail-tabs`.
- `.meeting-detail-header` is `position: sticky` with the existing main-container
  top padding compensated in its `top`, margin and padding rules, an opaque
  `var(--bg)` background and a single stacking/shadow treatment.
- `.meeting-detail-tabs` remains a tablist but is not an independent sticky
  element.
- Detail transcript/outcome targets use the responsive header scroll margin.
- Repeated partial render does not duplicate wrapper, tablist or controls.
