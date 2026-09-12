# Validation
1. Запустить `node apps/server/tests/browser/timezone-settings.test.cjs` с существующим Playwright через NODE_PATH; проверить mouse/keyboard поиск город/IANA/UTC, Enter/Escape/Tab, Cancel, network/422 retry и no-JS.
2. Запустить `node apps/server/tests/browser/settings-combobox.test.cjs`: все зарегистрированные settings selects, фильтр приложений, скрытые приложения при bulk, async disabled/catalog/value, reset, no-match, IME, 600 опций ≤100 мс, narrow/light/dark.
3. Focused pytest contract settings и source tests, Swift tests для MeetingDetection/EmbeddedCabinetRecordingSettingsBridge/notifications. Не запускать отдельный app.
4. Проверить diff и независимый review; записать команды/результаты без приватных данных в validation/receipt.md.
5. После разрешения коммита: harness status → build → promote → status → smoke, проверка выбора в /Applications/GRAF Dev.app. До этого installed acceptance pending.
6. PR governance-fast строго на SHA; release-full только для будущего frozen release, deploy отдельно.

7. Резервное окно: начальный размер в пределах экрана, переключение Запись → Уведомления → Запись без уменьшения; поля уведомлений доступны, длинные имена приложений переносятся, строки компактны.

8. Dev prerequisite FR-010: `uv run --project apps/server --extra dev pytest tests/governance/test_graf_local_adapter.py tests/governance/test_dev_harness.py -q`; build сохраняет локальные датированные образы MinIO, отсутствие образа+ошибка registry прерывает сборку. Promote изменённого harness выполняется с чистым previous-checkout активного SHA, сохраняя runtime-definition gate.

9. Визуальная итерация FR-011: до сохранения кандидата выполнить native geometry/interaction checks и Chromium/WebKit combobox suite; после установки снять открытые меню приложений/всех трёх правил/напоминаний в светлой и тёмной темах. Последняя строка полностью видна, подпись не обрезана, menu без указателя, ширина каталога ≤380 pt и ограничена экраном. Проверить меню у края экрана, перенос длинного имени, закрытие при переключении вкладки/resize/прокрутке, Escape/Tab/outside без сохранения и Enter/click с сохранением. Сохранить исходные пользовательские значения после временного теста.

10. Геометрия общего списка: 0/1/3/8/>8 вариантов, разные высоты, actual rect последней строки и viewport с учётом border/intercell/insets; фильтрация уже прокрученного списка возвращает видимые результаты. Галочка/selected отражают сохранённое значение, active — навигацию; app filter не показывает фиктивную галочку.
