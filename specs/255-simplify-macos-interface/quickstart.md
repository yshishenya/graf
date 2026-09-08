# F255: проверка возврата навигации

## Решение владельца от 2026-09-08: проверка macOS 14

Владелец сообщил: «У меня нет макос 14. Давай без него если невозможно так протестировать. Доводи до готовности к мерджу и релизу».
Для F255 отсутствие ручной проверки на macOS 14.5 принимается как явное ограничение выпуска, а не блокирующий пункт и не PASS. Минимальная поддерживаемая версия не повышается; сохраняются deployment target и проверки совместимости API при сборке. Матрица на доступной macOS 26.5, доступность, совместимость и остальные проверки остаются обязательными. Это решение не отменяет Full CI, подписывание, нотариализацию или контроль точного SHA.


Решение владельца от 2026-09-07 отменило native sidebar/bridge. Ниже действующая проверка T019; прежняя полная приёмка оформления остаётся открытой.

1. Проверить ветку, чистый diff и отсутствие всех потребителей `EmbeddedCabinetShellBridge`, `grafDesktopShell`, `data-native-navigation`.
2. Server pytest: `test_cabinet_navigation_model.py`, `test_cabinet_web_shell.py`, `test_cabinet_template_sections.py`, `test_cabinet_shell_response_contract.py`, `test_settings_ui_contract.py`. Использовать существующее окружение с pytest.
3. `swift test --package-path apps/macos --parallel --num-workers 1 --filter 'DesktopCabinet|EmbeddedCabinet|DesktopMeetingShellWebViewBoundary|AppControlAccessibility|CaptureControlV5'`.
4. Согласованная чистая ревизия F249/F255 → штатный Dev build, promote dry-run, promote с проверяемым previous-checkout, status, smoke. Не устанавливать старую схему поверх текущей0086. Не создавать другую диагностическую app.
5. В установленном Dev: основные разделы и старый профиль снизу; нажатие открывает прежние команды и подменю, Escape закрывает. Навигация к настройкам и назад; правая запись видима. Автозапись28 pt без заглушек. Не менять пользовательские правила и не начинать запись без необходимости.
6. Остальная матрица остаётся открытой: macOS14.5/26, светлая/тёмная/system, Reduce Transparency/Motion, Increase Contrast, VoiceOver, 200%, минимальное окно, активная запись/Stop, реальные соседние фичи/admin/public/no-JS. Текущий возврат не доказывает Liquid Glass.
7. PR governance-fast на точном SHA. Full CI/notarization/production — отдельный frozen release candidate; этот Dev проход их не заменяет.

T021: `swift test --package-path apps/macos --parallel --num-workers 1 --filter CabinetSidebarRuntimeTests`; в профиле проверить hover одного подменю, переход внутрь через зазор, смену строки, уход, keyboard/touch/Escape. Проверить светлую/тёмную тему и компактное окно: подпункты видимы внутри меню. Evidence — `validation/profile-hover.md`.

T010, общий валидатор Dev: `pytest -q tests/governance/test_dev_runtime.py tests/governance/test_dev_compose_contract.py`; `python3 scripts/validate-dev-runtime.py`; `python3 scripts/validate-agent-context.py`. Отсутствие/номер локального указателя не влияет на runtime-проверку; нарушения Compose/evidence должны приводить к ошибке.

Ручной VoiceOver не запускать по решению владельца 2026-09-08. Повторить совместные проверки на коде, уже включённом через #6762, не ожидая закрытия исторических исходных PR.

T031: профильные DesktopCalendarReminderTests проверяют реальное NSMenu: Start/starting/Stop/микрофонная пауза/stopping, stale Start/Stop, доступное обновление, отсутствие календарного шума, private/title/time preferences и безопасные ссылки. Установленный официальный GRAF Dev: открыть меню, Escape/внешний клик/клавиатура, начать короткую запись командой меню, снова открыть меню во время записи и Stop; сохранено на Mac. Повторить idle после закрытого/свёрнутого окна, обе темы. macOS14.5/VoiceOver остаются not_run_owner_accepted; недоступные через CUA системные значки не засчитываются как визуальный PASS.

T032 заменяет соответствующие шаги T031: idle меню имеет Start, Open GRAF, общие «Настройки…», «Выйти из GRAF». Проверить внешний click по обычному окну GRAF, окну другого приложения, потерю активности и Escape; внутренний выбор и повторное открытие работают. Проверить общий settings overview и idle Quit через действующий termination pipeline, затем запуск GRAF Dev и smoke. Вектор меняется outline → filled без отдельной отметки; микрофонная пауза оставляет заполненный знак. Native menu width/height не задаются вручную, кроме прежнего минимального width 240 pt.

## T033 — Mute и встроенная индикация

Проверить Start → Mute микрофона → Включить микрофон → Stop и Stop прямо из Mute в штатном Dev. Во время Mute системный звук остаётся активным, меню явно поясняет это; общий статус не говорит о паузе всей записи. Проверить обе темы, статичную точку при Reduce Motion и отсутствие перехвата мыши поверх точки. Автотест: переходы/повтор устаревшей команды, неизменная геометрия template-логотипа, красная точка внутри кольца, ограниченная анимация и её удаление после Stop/Reduce Motion.
