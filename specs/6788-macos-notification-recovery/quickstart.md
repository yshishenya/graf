# Проверки F6788

Lane: **high-risk-product**. Выполнять по текущей ветке/SHA, сохранять только
метаданные. VoiceOver исключён владельцем. Production не изменять.

## Автоматические проверки

```sh
swift test --package-path apps/macos --filter 'CaptureControlTests|DesktopNotificationControlTests|DesktopCalendarReminderTests|DesktopCabinetRoutePolicyTests|AppControlAccessibilityTests'
swift build --package-path apps/macos --product TwoBrainRecApp
git diff --check
# GRAF_NODE_MODULES указывает на уже установленный Playwright.
node apps/server/tests/browser/playback-refresh.test.cjs
GRAF_BROWSER=webkit node apps/server/tests/browser/playback-refresh.test.cjs
```

Для затронутого серверного шаблона выбрать существующий pytest contract/
integration набор настроек/уведомлений после поиска фактических имён. Негативные
проверки маршрутов: другой origin/порт, обычный браузер, query/fragment, подмена
пути; существующие внешние callback не расширять.

В регрессиях покрыть общий dispatch/неготовый handler/повтор перехода;
default/join/settings/dismiss/unknown; старого owner/occurrence/URL;
disable/enable/перенос/отмена; запись/тихие серверные результаты.
Обязателен раздел «Проверяемые границы» contracts/experience.md: p95 ответа
≤200мс, Stop→освобождение ≤5с без прерывания сохранения, dropout <0.5% и отсутствие
новых discontinuity/alignment ошибок, отказ неготового handler без deferred Start,
due-time cutoff/add failure, showTitles cleanup без повторов.
Чистая компиляция и source-string assertions не заменяют сценарии Dev.

## Приёмка единственного GRAF Dev

Прочитать `docs/agent-guidance/local-development.md` и `infra/dev/README.md`.
Сначала `infra/scripts/dev-harness.sh status --json`: проверить source/schema
и совместимость. Не понижать схему0090, не заменять работающий чужой кандидат
и не создавать второе приложение. Build/promote только штатным harness из
проверенного чистого SHA; обновление сохраняет bundle ID/подпись/разрешения.

1. Скрытый кабинет, календарная карточка и повторное открытие: Start из меню,
   короткая синтетическая запись, Mute/Unmute, Stop. Проверить один start/stop,
   длительность, сохранённый файл и закрытие ресурсов. Постоянных окон — ноль.
2. F214: Ask8сек/явные Record и Не записывать/remember/Always/Never. Ни
   календарный баннер, ни Join не запускают захват самостоятельно.
3. Оба меню → уведомления → настройки Mac; повторить при открытой другой
   вкладке, несохранённом черновике и недоступном сервере. Темы, клавиатура,
   фокус, узкий кабинет, полный экран/штатное раскрытие строки меню.
4. Одно разрешённое тестовое OS-уведомление: отдельно фиксировать передачу
   ОС, фактический баннер и действие. Настоящий reminder со ссылкой/без неё:
   default открывает GRAF, Join актуальную встречу, настройки нужную вкладку.
   Отказ OS/Focus не обходить, разрешения не сбрасывать.
5. Будущее событие: выключить/включить напоминания; перенос/отмена/рестарт/
   пробуждение/смена аккаунта; уже показанное не повторяется. Исходные
   F249 T026/#6758 и T034/#6779 остаются открыты до фактического доказательства.
6. Потеря сети → Ожидает отправки у записи; полезная локальная ошибка →
   конкретная запись. Серверные ready тихие, terminal в Важном, read != resolved,
   повтор не создаёт новую точку. blocked_config не предлагает бессмысленный retry.

## Завершение

Внести результаты/ограничения в `validation.md`, выполнить независимые review
и convergence. PR: актуальный changelog fragment, задачи/issue-связи,
`governance-fast` exact SHA и `validate-pr-metadata.py --expected-sha`.
Release-full/публикация относятся к отдельному замороженному релизу.

## Объединённая приёмка F258

- Повторить integration summary-slot/recording-sync/media-role и Node
  test_meeting_progress_ui.py; пригодное audio при empty/pending/failed summary,
  selected-format/partial/source/media/deletion fences.
- Native decoder/queue: независимые transcript/review/summary, auth epoch,
  foreign-first и несколько incidents; ноль recap баннеров.
- После освобождения Dev: первый embedded вход без reload; synthetic
  запись → звук/расшифровка → итоги; появление <=15с, без прерывания audio
  и потери name draft/focus. Проверить сеть/сон/ожидание >5мин.
- При недоступном Dev эти строки остаются NOT RUN; исходные F258 PASS не
  замещают результаты объединённого SHA.
