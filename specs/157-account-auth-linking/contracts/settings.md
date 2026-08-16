# Contract: account security settings

The account security page must expose a section `Способы входа` on web and in
GRAF Local.

Each row shows only:

- safe provider label (`Email`, `Яндекс`, `VK`, etc.);
- verified/confirmation state;
- approximate connection date when available;
- `Подключить` or `Удалить` action when policy permits.

Actions:

- `Подключить` starts the existing provider-link flow and never silently
  switches the current account.
- `Удалить` requires re-authentication and is disabled for the last usable
  verified method.
- A provider conflict links to the explicit recovery/merge flow rather than
  showing a generic meetings-unavailable page.

The HTML contract keeps CSRF hidden inputs, keyboard focus, `aria-live` result
messages and the existing active-auth-only WebView navigation boundary.
