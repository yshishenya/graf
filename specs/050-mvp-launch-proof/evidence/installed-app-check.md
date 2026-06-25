# Installed App Check

Metadata-only checklist for `/Applications/2brain Rec.app`.

Do not paste account identifiers, meeting titles, transcript text, audio paths,
tokens, cookies, signed URLs, or local private paths into this file.

## Read-Only Commands

```sh
test -d "/Applications/2brain Rec.app"
defaults read "/Applications/2brain Rec.app/Contents/Info.plist" CFBundleIdentifier
defaults read "/Applications/2brain Rec.app/Contents/Info.plist" CFBundleShortVersionString
codesign -dv "/Applications/2brain Rec.app" 2>&1 | sed -n '1,8p'
```

## Runtime Checks

| Check | Status | Evidence |
|-------|--------|----------|
| Installed bundle exists | pass | Bundle id `pro.2brain.rec`, version `2026.06.25.2`, executable `2brain Rec`. |
| App launches without crash | pass | Fresh soft quit/open produced a running process and app-log `app_launch_finished`. |
| Native Record/Stop visible | unproven | Automation AX/window capture could not inspect the window; focused Swift shell/control tests remain supporting evidence. |
| Cabinet does not show false green | pass | App-log recorded `state=expiredSession` / `routeKind=authLogin`, not ready/green. |
| Embedded review route can load or shows truthful auth/server state | pass | Fresh launch reached the configured production cabinet and returned auth-required truth. |

## Notes

- Full-window screenshots are not required for 050.
- If visual evidence is needed, keep it cropped and metadata-safe.
- Codex `screencapture` returned a black frame and Computer Use returned
  `cgWindowNotFound` in this automation context; do not treat that as a product
  screenshot proof.
