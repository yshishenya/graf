# F280 — независимая проверка тестовой границы фокуса

Дата: 2026-10-02, Europe/Istanbul. Проверка только чтением. Ветка `codex/280-native-validation-repair`, рабочая копия `release-f280/crisp`. Область: текущая правка `DesktopNotificationAccessibilityTests.swift` для блокирующего T025 gate. Код, specs, GitHub и состояние выпуска рецензентом не изменялись; записан только этот отчёт.

**PASS для рассмотренной тестовой правки. Замечаний к diff: 0. Подтверждение выполнения новой проверки фокуса остаётся открытым.**

## Основания

Прочитаны `/tmp/graf-f280-native-full-failure-diagnosis.md`, исходный журнал `/tmp/graf-f280-provider-full-corrected-macos.log:5492`, текущий diff, соответствующий метод `DesktopNotificationCardPresenter.focus()` и штатные AppKit helper функции.

Исходный Full отказался на одном сравнении activation policy: финальное `.regular` против раннего `.prohibited`. `focus()` первым guard требует policy != `.prohibited`; в том же тесте `XCTAssertTrue(presenter.focus())` не падал. Следовательно, ранний снимок уже не соответствовал policy на входе в команду. Точный внутренний переход AppKit журналом не установлен и здесь не утверждается.

Новый снимок `policyBeforeFocus` снимается в существующей perform closure после подготовки её event loop, прямо перед `presenter.focus()` на MainActor. Между снимком и вызовом нет await, повторной прокачки событий, setter или другого действия продукта; добавлен настоящий assert, что policy допускает активацию. `awaitAppKitState` вызывает perform один раз: timer-ветвь защищена `performed`, другая ветвь выполняет closure перед ограниченным циклом. После подтверждённого active/key-window состояния equality сравнивает финальную policy с этим же unwrapped снимком.

Сохранены проверки начального inactive состояния, отсутствия активации и key-window после автоматического показа, видимого/не скрытого хоста, видимой панели перед командой, принятия `focus()`, реального active и key-window, начального first responder close и перехода Tab на checkbox. Финальное сравнение policy не удалено и не заменено допуском произвольного значения. Отсутствующий снимок провалится через XCTUnwrap.

В diff нет новых skip, retry, delay, timeout, дополнительных попыток фокуса или новых helper. Существующая 30 ms пауза и timeout 3 остаются без изменения. Продукт и test helper не меняются. Presenter не вызывает setActivationPolicy; его hash, а также hash Compact helper совпадают с документом исходной диагностики. Предусловие не подменяется установкой policy внутри команды.

## Проверка журнала локального запуска и пределы

По текущему `/tmp/graf-f280-native-validation-focused.log` выбранный класс завершился: **19 tests, 5 skipped, 0 failures**. Сам изменённый `testExplicitFocusFromInactiveAppDoesNotDependOnAnotherSuiteActivation` **skipped** на штатной `requireFocusHost` проверке фокуса обычного окна. Следовательно, этот запуск подтверждает сборку и отсутствие ошибок остальных выполненных тестов, но не выполнение новой границы снимка или новой equality. Причина skip существующая, не внесена этой правкой.

Нельзя обозначать локальный результат как 19 реально пройденных проверок или утверждать, что исправленный focus test исполнился. Новый exact-SHA native/full результат в среде с разрешённым фокусом и необходимые GRAF Dev ограничения остаются за основным агентом. Сам рецензент тесты или приложения не запускал. Этот code-review PASS не заменяет CI/Full/release/runtime или пользовательскую приёмку.

## SHA-256 рассмотренных файлов

- `apps/macos/Shared/Tests/DesktopNotificationAccessibilityTests.swift`: `8a6f09be23d174b0b619db6e6ae9d2ea3a9c23ff1cbbe7dc5985be62b53da002`
- `apps/macos/Shared/Tests/DesktopNotificationCompactTests.swift`: `a6184827336d655a1d1b6d95370fa001400e909714343d81a2a8b6c816ea3e73`
- `apps/macos/RecApp/Sources/Notifications/DesktopNotificationCardPresenter.swift`: `fdbe7b422d59b2467a1bdc544b166786ed0d369de30d6a31520f5a0f8f2d57c3`

Изменение hash рассмотренного теста требует повторной сверки diff; необъяснённое изменение двух остальных файлов не покрывается этим заключением.
