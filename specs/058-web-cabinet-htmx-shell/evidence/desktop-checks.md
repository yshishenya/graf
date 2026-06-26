# Desktop Checks Evidence: 058 Web Cabinet HTMX Shell

Date: 2026-06-26

## Result

`desktop_cabinet_result=pass`

## Command

```sh
swift test --package-path apps/macos --filter DesktopCabinet
```

## Observed Output

- `Executed 63 tests, with 0 failures`

## Covered Boundaries

- Desktop cabinet offline/unavailable states stay native and do not expose stale online sidebar recovery.
- Native Record/Stop, active capture, upload truth, permission recovery, and diagnostics stay outside WebView ownership.
- Successful login page loads do not mark the cabinet ready.
- Exact route-kind policy allows meeting list/detail/deletion report and blocks native/local/future governance routes.
- Desktop headers are reattached only to approved embedded meeting routes.

## Evidence Hygiene

This evidence contains no private meeting content, raw audio, transcript text,
credentials, signed URLs, object keys, private local paths, or real account
identifiers.
