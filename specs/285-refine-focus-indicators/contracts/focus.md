# UI contract — F285

| Поверхность | Mouse | Keyboard / assistive navigation |
| --- | --- | --- |
| capture/custody container | Нет внешней рамки | Нет лишнего Tab stop; явный переход scroll + VoiceOver target |
| Button/link/summary/checkbox/radio/file | Стандартное :focus-visible поведение | Видимый контур конкретного действия |
| Text/search/code/textarea/select/combobox input | Один контур в границе | Тот же один контур |
| NativeSettingsComboBox editable field | Один 2px stroke внутри bounds | Tab показывает тот же контур; стрелки/Return/Escape сохраняются |
| Range | Существующий индикатор | Видимый индикатор, не замена полем |
| Dialog | Существующий focus trap | Escape/restore/Tab сохраняются |
| Notification action | Существующий первый click | Explicit focus/Tab/Return/Escape без изменений |

Single contour: outline none для border-bearing полей, border focus color, inset 1px shadow. Forced colors: transparent border + один 2px Highlight outline, без shadow. В обеих темах contrast ≥3:1; high contrast не скрывает фокус. Ошибки и семантическое выделение не выключаются; нет активации от focus.

Редактор названия .meeting-title-input имеет border:0: его единственный контур — inset shadow 2px, внешний outline удаляется только одновременно с этой заменой. Browser regression явно включает редактор названия и проверяет клавиатуру/contrast.

Нативное editable поле проверяется мышью и Tab в светлой/тёмной теме и при Increase Contrast; stroke использует существующий focusRing token, не меняет bounds и не открывает popup от одного focus.

WebKit native select не рисует inset box-shadow: один 2px outline с offset -2px покрывает собственную границу без изменения appearance/стрелки/размеров. Forced-colors по-прежнему оставляет один Highlight outline. Regression проверяет это отдельно в Chromium и WebKit.

В forced-colors браузер вправе перекрасить прозрачную нативную границу. Highlight outline2px расположен внутри с offset -2px и покрывает её; дополнительной внешней линии нет.
