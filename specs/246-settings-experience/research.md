# Исследование настроек

## Проверено 2026-09-06
Krisp 3.15.6, установленный app Info.plist: ai.krisp.krispMac. Через Computer Use открыты Account и AI Note Taker: самостоятельная навигация настроек, центрированная читаемая колонка справа от меню; простые секции с разделителями, подпись и пояснение слева, действие справа. Account различает профиль, безопасность, поддержку; AI Note Taker группирует автоматизацию и sharing. Части toggle не отдаются в accessibility tree — эту слабость не воспроизводим. ASAR, бинарники и ресурсы не извлекались.

Decision: центрировать содержимое внутри рабочей области; сохранять левое выравнивание текста. Основание: CSS .settings-page__content ограничен 780px без auto margins, поздний workspace reset сбрасывает прежнее внешнее центрирование. Calendar content использует другую ширину; billing уже имеет 880px. Отклонено: сдвиг окна macOS/изменение глобальной workspace, затрагивающее встречи.

Decision: переиспользовать существующие секции и формы. Подтверждены потерянные query results profile (embedded)/account_close (browser), ошибочная success классификация failed/reauth; исправить в общем rendering и route wiring, сохранив серверные guards.

Decision: native recording сохраняет отдельное локальное окно и state store; размеры NSWindow 720x480 и SwiftUI 760x500 расходятся. Правила и миграции остаются; улучшаются объяснения и геометрия.

## Актуальные внешние источники
- https://www.nngroup.com/articles/ten-usability-heuristics/ — visibility of status, consistency, recognition, error recovery: видимый правдивый результат и общие patterns.
- https://www.w3.org/WAI/tutorials/forms/labels/ — подписи элементов формы.
- https://www.w3.org/WAI/WCAG22/Understanding/reflow.html — 320 CSS px без двухмерной прокрутки.
- https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html — targets 24x24px минимум, исключения не заменяют удобные основные действия.

Источники получены напрямую 2026-09-06; измерения финальной реализации фиксируются в quickstart.md. Не заявляется исследование внутренней логики Krisp: наблюдаемое поведение и публичные метаданные достаточны для самостоятельной реализации.

## Карта проверенного кода

| Участок | Поток и принятое решение |
|---|---|
| Обзор, запись, итоги, пространства, уведомления | settings routes → render_settings_page → pages/components → cabinet.css/cabinet.js; общая колонка и секции, адреса и доступные действия сохранены |
| Аккаунт и безопасность | Все browser/embedded aliases, view models, result markers, формы профиля/preferences/provider/device/session/closure; исправлены forwarding и классификация, мутации и guards сохранены |
| Календари | calendar rendering/fragments, общие control rows и tooltip; общая ширина и заголовок, подключения/синхронизация/выбор календарей защищены существующими integration tests |
| Тариф и оплата | billing routes/templates/contracts; сохранены отдельные 880px, права владельца, платежные действия и существующие таблицы |
| Подключение способов входа | provider-links routes и fragment; общие стили проверены на реальном шаблоне, safe POST+CSRF сохранены |
| macOS | Settings window → MeetingDetectionSettingsView → bindings → MeetingDetectionSettingsStore; единый размер, один ScrollView, системный alert, прежние правила и миграции |
| Общие потребители | theme menu, manual upload, account aliases и desktop workspace; найденные побочные эффекты устранены, область CSS ограничена |

## Подтверждённая очистка

- `.settings-handoff-card`, `.settings-choice-row--toggle`: поиск в production templates/JS не нашёл потребителей; удалены только CSS-правила.
- `.settings-section { grid-template-columns: 1fr; }`: section использует flex, декларация не работала.
- Повторные heading declarations объединены; дубли календарного заголовка заменены общим оформлением.
- Submit listener `initAccountPreferences`: общий `initSettingsFormState` уже выполняет работу;
  второй listener повторно включал кнопку в состоянии saving. Проверена вся цепочка инициаторов,
  включая theme menu без submit-кнопки. Общая обработка reset/dirty/saving сохранена.
- Неиспользуемый import `sections` удалён из summaries template.
- Из render context удалены только `provider_link_result`, `provider_unlink_result`,
  `device_revoke_result`, `session_result`, `account_close_result`: потребители используют
  `account_outcome`; входные аргументы и query contracts сохранены.
- `DesktopCabinetWorkspaceView.embeddedWorkspaceMaxWidth`: нет действующих потребителей;
  удалена константа и проверка её равенства литералу. Рабочая область встреч не изменена.
- Декодирование `autoRecordTargetIds`, миграции, deny старых маршрутов и account aliases
  сохранены: они обслуживают существующие данные и границы безопасности.

## Исправления после независимого review

1. Ошибка native save теперь системный `.alert`: видна независимо от прокрутки,
   прежнее правило сохраняется, сообщение поясняет возможность повторить.
2. Сохранено исходное мобильное позиционирование tooltip для manual upload;
   календарные поправки ограничены `.calendar-settings`.
3. Специфичность Email tooltip исправлена: при hover/focus подсказка остаётся ниже
   подписи на 4px, не перекрывает кнопку. Проверены показанные, а не только скрытые подсказки.

## Уточнение после master sync 6ff8db3ee

История очистки выше относится к исходной базе. В master уже удалены часть мёртвых selectors
и прежний CSS tooltip. F246 сохраняет новый Popover целиком, собственные старые positioning
rules больше не входят в итоговый diff. Поздние ограничения 900px удалены, чтобы общая ширина
настроек имела один источник. В нативном picker добавлены отдельные доступные имена кнопок
и контейнер группы `.accessibilityElement(children: .contain)`; поведение правил не изменено.
