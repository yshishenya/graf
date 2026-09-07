# F255: проверка возврата навигации

Решение владельца от 2026-09-07 отменило native sidebar/bridge. Ниже действующая проверка T019; прежняя полная приёмка оформления остаётся открытой.

1. Проверить ветку, чистый diff и отсутствие всех потребителей `EmbeddedCabinetShellBridge`, `grafDesktopShell`, `data-native-navigation`.
2. Server pytest: `test_cabinet_navigation_model.py`, `test_cabinet_web_shell.py`, `test_cabinet_template_sections.py`, `test_cabinet_shell_response_contract.py`, `test_settings_ui_contract.py`. Использовать существующее окружение с pytest.
3. `swift test --package-path apps/macos --parallel --num-workers 1 --filter 'DesktopCabinet|EmbeddedCabinet|DesktopMeetingShellWebViewBoundary|AppControlAccessibility|CaptureControlV5'`.
4. Согласованная чистая ревизия F249/F255 → штатный Dev build, promote dry-run, promote с проверяемым previous-checkout, status, smoke. Не устанавливать старую схему поверх текущей0086. Не создавать другую диагностическую app.
5. В установленном Dev: основные разделы и старый профиль снизу; нажатие открывает прежние команды и подменю, Escape закрывает. Навигация к настройкам и назад; правая запись видима. Автозапись28 pt без заглушек. Не менять пользовательские правила и не начинать запись без необходимости.
6. Остальная матрица остаётся открытой: macOS14.5/26, светлая/тёмная/system, Reduce Transparency/Motion, Increase Contrast, VoiceOver, 200%, минимальное окно, активная запись/Stop, реальные соседние фичи/admin/public/no-JS. Текущий возврат не доказывает Liquid Glass.
7. PR governance-fast на точном SHA. Full CI/notarization/production — отдельный frozen release candidate; этот Dev проход их не заменяет.
