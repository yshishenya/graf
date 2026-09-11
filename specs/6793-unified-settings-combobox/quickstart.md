# Validation
1. Запустить `node apps/server/tests/browser/timezone-settings.test.cjs` с существующим Playwright через NODE_PATH; проверить mouse/keyboard поиск город/IANA/UTC, Enter/Escape/Tab, Cancel, network/422 retry и no-JS.
2. Запустить `node apps/server/tests/browser/settings-combobox.test.cjs`: все зарегистрированные settings selects, фильтр приложений, скрытые приложения при bulk, async disabled/catalog/value, reset, no-match, IME, 600 опций ≤100 мс, narrow/light/dark.
3. Focused pytest contract settings и source tests, Swift tests для MeetingDetection/EmbeddedCabinetRecordingSettingsBridge/notifications. Не запускать отдельный app.
4. Проверить diff и независимый review; записать команды/результаты без приватных данных в validation/receipt.md.
5. После разрешения коммита: harness status → build → promote → status → smoke, проверка выбора в /Applications/GRAF Dev.app. До этого installed acceptance pending.
6. PR governance-fast строго на SHA; release-full только для будущего frozen release, deploy отдельно.

7. Резервное окно: начальный размер в пределах экрана, переключение Запись → Уведомления → Запись без уменьшения; поля уведомлений доступны, длинные имена приложений переносятся, строки компактны.
