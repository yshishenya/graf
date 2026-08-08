# Tasks: Надёжный email-вход в macOS WebView

- [X] T001 [P] [US1] Добавить regression test для четырёх email endpoints и обычных login/meeting routes в `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`.
- [X] T002 [US1] Не сохранять transient email form-response URL в `currentRoute` и `lastLoadedRequestIdentity` в `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`.
- [X] T003 [US2] Сохранить существующий allowlist и Yandex OAuth lifecycle в `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` и `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`.
- [X] T004 [P] Обновить `CHANGELOG.md` и записать metadata-only evidence.
- [X] T005 Запустить focused macOS suites и canonical local CI; зафиксировать unrelated worktree failures, если они есть.

## Dependencies

`T001` blocks `T002`; `T002` and `T003` block `T005`; `T004` is release closeout.
