# Quickstart: email login WebView regression

```sh
swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests
swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests
infra/scripts/ci-local.sh
```

Manual smoke uses a test account and metadata-only evidence: submit email, enter
the code, confirm meetings open without a repeated email-start GET, then confirm
Yandex login still completes. Do not record email, code, cookies, tokens, audio
or meeting content.
