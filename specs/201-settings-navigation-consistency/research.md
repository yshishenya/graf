# Research: Единая информационная архитектура меню GRAF

## Sources inspected

- Attached GRAF screenshot: duplicate settings entry in sidebar and profile menu.
- Installed Krisp via Computer Use: account context, Appearance, Settings,
  Troubleshooting, Resources, support/feedback/community, Sign out and Quit.
- GRAF shared template/CSS/JS: one profile overlay, existing theme picker,
  logout CSRF flow, Escape/click-outside handling, compact rail and wrapping.
- GRAF macOS WebKit surface: existing allowlisted `grafAppUpdate` bridge and
  `NSApp.terminate` lifecycle path; no existing quit bridge.
- Data Analytics lens: measurable UI contract is static rendered counts/order,
  disabled-state coverage and browser-vs-embedded parity; there is no product
  event dataset in scope, so no behavioral metric is invented.

## Decisions

- Keep Settings in the profile menu because the latest user request explicitly
  requires it; sidebar remains the persistent cabinet navigation.
- Use native `<details>` for submenus and existing `theme_picker` markup.
- Persist appearance through the existing account preferences POST with current
  locale/timezone values; apply the existing local theme preview first.
- Render Quit as enabled only for embedded desktop and route it through a
  main-frame, same-origin, allowlisted native message. Browser remains disabled.
- Keep temporary help/support actions semantic disabled buttons without hrefs.

## Out of scope

New support/diagnostic implementations, external documentation links, Telegram
integration, new telemetry, new API contracts, exact Krisp styling/assets/code.
Production rollout and installed-app mutation were out of scope for implementation;
the current user-requested release closeout handles them through the release gate.
