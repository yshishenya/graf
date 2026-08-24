# Quickstart: Проверка навигации кабинета

## Prerequisites

- macOS 14+ and the GRAF desktop app with an authenticated cabinet session.
- Repository checkout at `/Users/yshishenya/.codex/worktrees/e4ef/crisp`.
- The installed app smoke must use the current visible app session; do not add
  credentials, cookies, private meeting text, or screenshots containing secrets
  to the repository.

## Focused automated checks

```sh
swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests
swift build --package-path apps/macos
```

Expected: the focused suite passes, including duplicate-history, back/forward,
fallback, loading, and accessibility assertions.

## Installed-app smoke matrix

For each route below, wait until the page is stable and record only the URL and
the four control states:

1. `/desktop/meetings`
2. `/desktop/settings`
3. `/desktop/settings/recording`
4. `/desktop/settings/summaries`
5. `/desktop/settings/integrations/calendar`
6. `/desktop/settings/workspace`
7. `/desktop/settings/account`
8. `/desktop/settings/notifications`
9. `/billing`

Check:

- The same four controls exist with stable labels and identifiers.
- On a non-home route, «Домой» opens `/desktop/meetings`.
- On a safe document, «Обновить» reloads the same URL and becomes disabled only
  while loading.
- From `/desktop/settings/recording` →
  `/desktop/settings/integrations/calendar`, «Назад» returns to recording.
- After that return, «Вперёд» becomes available and returns to calendars.
- Repeating the scenario with billing or any settings route never leaves the
  user on the same URL because a duplicate history item was selected.
- While any navigation is running, all four controls report loading/disabled.

## Fast lane

```sh
infra/scripts/ci-local.sh --fast
```

Expected: the repository fast lane passes. No deploy, release preparation,
notarization, Sparkle, or appcast check is part of this feature.
