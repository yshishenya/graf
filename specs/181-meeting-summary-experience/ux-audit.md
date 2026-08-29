# Combined UX/UI/IA/CX audit: итоги встреч

Дата наблюдения: 2026-08-21. Поверхность: установленный `/Applications/GRAF.app` и установленный локальный Krisp как clean-room category reference. Screenshots сохранены только в локальном audit-каталоге вне git; они содержат приватный текст и не входят в committed evidence.

## Audit scope

Проверен путь: открыть завершённую встречу → увидеть текущие итоги → открыть быстрый выбор формата → открыть полный каталог → выбрать другой формат → получить состояние недоступности. Для Krisp проверены meeting list, AI Notes/template picker и template library surface. Полная WCAG-проверка требует отдельного keyboard/VoiceOver/browser runtime pass.

## User goal and accessibility target

За две-три минуты понять результат встречи, найти решение и следующий шаг, при необходимости проверить источник, затем безопасно получить другой формат без потери принятого результата. Основной путь должен работать с клавиатуры, VoiceOver и при 200% zoom.

## Step health

1. **Открытие встречи — плохо.** Вкладка «Итоги» обнаружима, player остаётся доступным, но первый экран показывает длинные фрагменты разговора как готовые «Кратко» и «Действия». Визуальная уверенность интерфейса не соответствует качеству данных.
2. **Просмотр результата — плохо.** Есть полезная иерархия «Кратко → Действия → Решения» и ссылки на время, но нет outcome-first блока. Повтор реплик затрудняет сканирование.
3. **Быстрый picker — удовлетворительно.** Он компактный, однако показывает только названия. Пользователь не понимает разницу между вариантами и воспринимает выбор как переключение представления, хотя он сразу запускает новую генерацию.
4. **Полный каталог — удовлетворительно.** Девять форматов видны с короткими описаниями и сохраняют GRAF brand distance. Недостаёт явного current marker, ожидаемых разделов и объяснения, что выбор создаёт новый вариант.
5. **Смена формата — плохо.** Наблюдаемый ответ «новый вариант недоступен» появляется после действия, которое выглядело доступным. Реальная доступность AI не была понятна до клика.
6. **Сравнение — плохо.** Preview расположен перед accepted result; пользователь сравнивает по памяти. «Оставить текущие» фактически отклоняет и удаляет candidate, хотя звучит как безопасное закрытие сравнения.
7. **Recovery — удовлетворительно.** Copy сообщает, что текущие итоги сохранены. Но одинаковый retry без изменения причины создаёт цикл; failure восстановления истории кандидатов может остаться полностью невидимым.
8. **Krisp comparison — reference only.** Krisp делает template selector заметным рядом с AI Notes и сохраняет player. Его destructive regeneration теряет старые notes/manual edits; безопасная GRAF candidate-before-replace модель лучше и должна быть сохранена.

## Strengths

- Итоги и расшифровка находятся на одном meeting-detail surface с постоянным player.
- Источники уже привязаны к временным отметкам.
- Полный каталог использует спокойную GRAF-композицию и не копирует Krisp layout/palette.
- Candidate model защищает принятый результат от молчаливой замены.
- Ошибка уже сообщает о сохранности текущих итогов.

## UX risks

1. **P0 trust mismatch**: mock-like extractive content выглядит как окончательный AI-результат.
2. **P0 dead control**: доступные кнопки форматов приводят к заранее известному `summary_generation_unavailable` при disabled AI.
3. **P1 hidden generation**: выбор формата маскирует side effect и не объясняет ожидаемый результат.
4. **P1 destructive wording**: «Оставить текущие» равно reject; закрытие review не отделено от отклонения candidate.
5. **P1 lifecycle ambiguity**: смешаны current format, pending format и candidate format.
6. **P1 recovery gap**: candidate-history failure без cache не показывает status/retry.
7. **P1 accessibility parity**: macOS WebView ограничивает page zoom 140%, тогда как target — 200%.
8. **P2 all-empty noise**: полностью пустой результат может рендерить восемь повторяющихся пустых категорий вместо одного честного meeting-level состояния.
9. **P2 state semantics**: slow generation визуально маркируется как failure.

## Accessibility risks

- Action buttons помещаются внутрь `role=status aria-live=polite aria-atomic=true`; VoiceOver может повторно объявлять весь интерактивный блок.
- Candidate preview — обычный `div`, а не именованный review region; status не связывает пользователя с новым контентом.
- Disabled/busy state должен сообщать причину не только визуально.
- Dialog, listbox, tabs, source seek и focus return требуют runtime-проверки.
- Screenshot не доказывает contrast, 200% zoom, reduced motion или VoiceOver announcements.

## Target interaction model

```text
Принятые итоги — стабильный документ
├── текущий формат + назначение
├── главное / решения / действия / дополнительные разделы
└── [Создать новую версию]

Review новой версии
├── формат + статус + source revision
├── текущая / новая версия
├── [Использовать новую версию]
├── [Закрыть сравнение]
└── More → [Отклонить новую версию…]
```

## Recommendations

1. Убрать deterministic content из ready/accepted path новой встречи.
2. Автоматически показать первый AI result как готовый candidate, но принимать только после явного действия пользователя.
3. Сохранить preview-before-replace для refresh и format switch; закрытие review не должно быть reject.
4. Сделать девять форматов семантически различимыми в prompt contracts и picker copy.
5. Разделить passive live status и action region; превратить preview в именованный region.
6. Добавить честные first-generation, slow, history-unavailable, preview-unavailable и all-empty состояния.
7. Проверить all-controls matrix в browser и embedded app, включая keyboard, focus, VoiceOver и 200% zoom.
8. Не копировать Krisp visual expression или destructive regeneration; использовать его только как category reference.

## Evidence limits

Скриншоты подтверждают визуальную иерархию и наблюдаемый failure path, но не доказывают полную accessibility. Независимый код-аудит использовал synthetic evidence и не открывал реальные встречи. Fresh runtime нужны для first generation, all-empty, slow, history failure, stale, complete candidate review и installed-app zoom/focus.
