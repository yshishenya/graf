# Research

The local `.app` already owns a separate bundle identifier and injects explicit
loopback origins. Its WebKit cookie store is intentionally separate from the
Codex/browser cookie store, so browser login cannot authenticate the app.

The existing `DesktopCabinetWorkspace.loginRoute` and email-code routes already
provide the correct in-app flow. The smallest safe fix is to make recovery from
the local unauthenticated state use that route. Production recovery remains
unchanged.
