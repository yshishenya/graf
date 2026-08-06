# Implementation Plan: Надёжный email-вход в macOS WebView

## Lane and Scope

- Risk lane: significant/high-risk auth and user-facing workflow.
- Scope: route identity handling in the embedded macOS WebView, regression test,
  changelog and release evidence.
- Tracking: existing [GitHub issue #4734](https://github.com/yshishenya/crisp/issues/4734).
- Exclusions: server auth policy, email delivery, credentials, capture and
  production deploy implementation.

## Root Cause

Production metadata showed `POST /login/email/start` returning 200 followed by
`GET /login/email/start` returning 501, with no email verify POST. The WebView
was promoting a transient form URL to `currentRoute` and
`lastLoadedRequestIdentity`; SwiftUI reconstructed it as a GET on the next
render.

## Design

1. Extend the existing request-identity predicate with the four transient email
   form endpoints.
2. Use it for both `currentRoute` and `lastLoadedRequestIdentity`.
3. Preserve allowlisting, cookie sync, session state and Yandex OAuth behavior.
4. Add a focused unit test for all four endpoints and stable login/meeting routes.

## Validation

- `swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests`
- `swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests`
- `infra/scripts/ci-local.sh`
- Metadata-only manual email and Yandex smoke after release.
