# Contract: Left-Side Update Badge

## Embedded Cabinet

The server-rendered embedded sidebar provides one hidden, inert slot:

- rendered only when `embedded=True`;
- identified by `data-graf-app-update`;
- hidden by default;
- button semantics, keyboard focus, and Russian accessible label;
- no server-owned update state and no network action.

The native WebView bridge may only:

- show or hide the slot from a trusted local availability boolean;
- send a single `checkForUpdates` action back to the native app when activated.

The bridge does not inject URLs, release notes, HTML, versions, credentials, or server responses into the page.

## Local-Only Mode

When no embedded cabinet exists, the native shell shows the same compact badge in the leading portion of the local workspace. It uses the same action and visibility state.

## Presentation

- Visible text: `Доступно обновление`
- Help/accessibility text: `Доступно обновление GRAF. Открыть проверку обновлений.`
- Visual tone: informational accent, not error/red
- Minimum hit target: 40 × 40 points
- Must not obscure recording controls, one-action stop, logout, or sidebar navigation
- Hidden for current, unavailable, checking, failed, withdrawn, or skipped state
