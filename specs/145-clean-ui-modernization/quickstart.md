# Quickstart: Clean UI Modernization

## Validation lane

Active Spec Kit slice / high-risk UX. The implementation is UI-only: no
routes, persistence, capture policy, billing, auth or external font loading
were changed.

## Checks

```sh
infra/scripts/ci-local.sh --fast
swift test --package-path apps/macos
git diff --check
```

## Evidence

- Server fast gate: `1087 passed`, lint and Python compile passed.
- macOS package tests: `671 passed` after updating the token expectations.
- No Google Fonts or remote font imports in the changed cabinet surface.
- Accessibility labels, hit targets and manual capture controls remain covered
  by the existing SwiftUI contract tests.
- The stale source branch was not merged wholesale; only the validated
  eight-file UI-only commit was transplanted onto current `master`.
