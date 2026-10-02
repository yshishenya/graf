# Research — F285

## Контейнеры

Decision: заменить @FocusState / .focused на @AccessibilityFocusState / .accessibilityFocused и убрать .focusable только у captureControls и custodyDetailRow.
Rationale: Shift+Tab воспроизводит фотографию в GRAF Dev без остановки записи. Контейнер не выполняет действие Enter/Space; scrollTo остаётся. VoiceOver получает прежний целевой контекст от явного notification navigation request.
Alternatives: глобальное отключение системных рамок лишает кнопки ориентиров; focusEffectDisabled оставляет лишний невидимый Tab stop; полное удаление binding теряет целевой доступный переход.

## Поля

Decision: существующий border перекрасить в --focus-ring и расширить внутрь inset shadow на 1px; убрать внешний outline только у текстовых полей/select/textarea. Код входа использует ту же внутреннюю границу. Forced colors — один outline, border transparent, shadow none.
Rationale: при мыши поле должно показывать активность, а обычная кнопка — только :focus-visible. Соседние элементы не должны смещаться. --focus-ring уже есть в обеих темах.
Alternatives: глобальный outline:none нарушает клавиатурную доступность; border-width:2px меняет геометрию; новый JS input modality дублирует браузерный :focus-visible.

## Область

Обычные notification кнопки сохраняют AppKit focus ring и существующий explicitFocus lifecycle. Selected/error/highlight рамки, modal restoration и range/checkbox/radio/file проверяются, но не отключаются. Baseline GRAF на origin/master 77e6aed8ff79127d6e6b284ad18b58da5793ef51; установленный Dev до изменения 7c4f844a983f2fe10a5f51fa695310acd47abac1. Сравнение этих трёх UI-файлов между SHA не выявило изменений. Наблюдения metadata-only, private screenshot не сохраняется в git.

## Нативное поле выбора

Decision: NativeSettingsComboBox.Control.draw рисует один 2px stroke внутри bounds с DesktopDesignTokens.focusRing вместо NSFocusRingPlacement.only.
Rationale: field.focusRingType=.none не мешает текущему Control вручную рисовать внешний системный контур. Сохраняем field.currentEditor/keyWindow guard, текущий border и repaint lifecycle.
Alternatives: отключение draw лишает редактируемое поле выделения; глобальное focusRingType не выключает custom draw.

Редактор названия .meeting-title-input имеет border:0: его единственный контур — inset shadow 2px, внешний outline удаляется только одновременно с этой заменой. Browser regression явно включает редактор названия и проверяет клавиатуру/contrast.

WebKit native select не рисует inset box-shadow: один 2px outline с offset -2px покрывает собственную границу без изменения appearance/стрелки/размеров. Forced-colors по-прежнему оставляет один Highlight outline. Regression проверяет это отдельно в Chromium и WebKit.

CALayer.borderWidth=1 рисуется поверх backing contents. Проверка выявила сохранённый separatorColor при активном поле; updateColors теперь одновременно перекрашивает существующую границу в focusRing, поэтому она не закрывает наружный пиксель внутренней линии. Blur возвращает separatorColor. Проверяется цвет слоя и bitmap во всех четырёх appearance.
