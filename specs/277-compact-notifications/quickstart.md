# F277 — Проверка

## Предусловия

Ветка277/macOS14+. Читать `docs/agent-guidance/local-development.md` и `infra/dev/README.md`. Никаких альтернативных app/`swift run TwoBrainRecApp`. Только synthetic события/evidence безчастногосодержимого. Production/release не входят.

## Команды из корня

```sh
swift test --package-path apps/macos --filter 'DesktopNotification|DesktopLocalNotification|EmbeddedCabinetNotification|MeetingDetectionCountdownTests|MeetingDetectionPolicyTests|MeetingDetectionRecordingLifecycleTests|CaptureControlTests|CaptureIndicatorTests|ShortRecording|AppControlAccessibility|DesktopCabinetRoutePolicy|DesktopCalendarReminderTests|DesktopUploadQueueTests/testRevokedPromptStart|DesktopUploadQueueTests/testV5CaptureFailure'
swift build --package-path apps/macos --product TwoBrainRecApp
swift build --package-path apps/macos --product ContractValidation
apps/macos/.build/debug/ContractValidation
python3 scripts/check_notification_retirement.py
node apps/server/tests/browser/settings-consistency.test.cjs --notification-contract
apps/server/.venv/bin/python -m pytest -q -o addopts= apps/server/tests/contract/test_desktop_notification_retirement.py
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_settings_ia_flow.py
infra/scripts/ci-local.sh --plan
infra/scripts/ci-local.sh --focused
git diff --check
```

Tests:5variants, measurement44–52/380, optionalfields/largetext, buttons/checkbox, tickpreservesfocus, firstclick, stalecallbacks/doubleactivation, informationalhold vs8s, ownerswitch, boundedneutralhistory, quiet/sound, oldprefsdecode/OScleanup, calendar0/1/5/deadlinewithoutreset. Фильтр дополняется новымиclasses. Node/pytest встроенныхsettings выбираются focusedmap; отсутствующее покрытие дополнить прямой командой, пустой запуск неPASS.

## Единственный GRAF Dev

Дополнение FR-026–028 (до общей матрицы):

```sh
swift test --package-path apps/macos --filter 'RecordingStartAcceptanceTests|DesktopUploadQueueTests|DesktopUploadClientTests|LocalRecordingWriter|CaptureRecovery|CaptureControlTests|CaptureIndicatorTests|MeetingDetectionRecordingLifecycleTests'
```

Новые проверки должны реально писать/читать manifest: первоначальный отказ
не активирует writer; pending остаётся запрещённым после успешного stop,
ошибки финального сохранения, нового recovery service, повторного scan и
retry с нулём transport calls. Проверить отказ принятия, неправильный sessionID,
принятие после stop, положительный accepted/recovery и старый nil/manual.
Протоколировать длительность подтверждения (цель ≤100ms без искусственной
задержки); не заменять runtime проверки анализом исходника интеграции.

Сначала `infra/scripts/dev-harness.sh status --json`. После focusedtests и авторизованного cleancommit — штатные build→promote→status→smoke поREADME, фиксироватьmanifest/SHA. Busy проверять поliveprocess, не обходить harness. Не копироватьbundle/не менятьподпись/TCC.

### Матрица приёмки

1. Все5сценариев light/dark × standard/largefont; nooverlap/truncation, closelefttop/noemptycolumn; short≤52standard. Проверить actualsyntheticscreenshots.
2. НеактивныйGRAF: firstclick исполняетcontrol. Ввод другогоприложения не прерывается появлением.
3. Меню→focus, Tab/ShiftTab, checkboxSpace, actionsReturn, Escape; VOinitialonce, tickfocusstable, no%/ложного«сохранено».
4. Start/skip/close/timeout×remember:одноaction/вернаяsetting. Hoverнеreset8s. Syntheticcapture: indicator/Stop/localoutcome; deniedpermissions/storage/policy не обходятся.
5. Info20s/preview6s holdhover/focus; outcome доступенповторно; problemостаётсяуrecording. History≤50, nopreview/tick/privatecontent, clearcontext.
6. Settings0/1/5, reminder/sound/title/quiet toggles; noOSduplicates/permissionUI. OldprefsJSON/ownOScleanup безновогоscheduling.
7. Concurrentprompt/problem/meeting/preview, callbackсоздаётновуюcard, refresh/changed/deletedlink; nostalestart/latesound. Sleep/lock/wake безhiddenstart.
8. Fullscreen/2displays/отключение/масштаб: surface/hitregion внутриvisibleFrame, ownStopнеперекрыт. Недоступныйscreen→missing evidence, неPASS.

Ожидаемые результаты конкуренции: prompt удерживается перед problem/meeting; после него problem раньше ещё актуальной meeting; равный приоритет другого события не вытесняет; preview при занятости отклоняется; вытесненная уже показанная карточка не возвращается. Для экрана: указатель задаёт только первый выбор, tick/перемещение указателя не перемещают окно; отключение выбранного экрана переносит на main без сброса срока. Проверить узкую область с вертикальными кнопками, прокручиваемый длинный текст и явный отказ при невозможности разместить controls/не перекрыть Stop: ноль невидимых запусков.

## Closeout

Решения владельца от 2026-09-28: VoiceOver уже проверен им и работает;
повторять этот сценарий не требуется. Физическая проверка двух мониторов
и отключения выбранного экрана перенесена в технический долг T020 / #7305
до появления оборудования. Это не PASS и не перенос одноэкранного fullscreen.
Подробные границы, условие возврата и выполненная визуальная сверка 20
тестовых представлений записаны в `validation.md`, раздел «Решения владельца
и визуальная сверка». Остальные непроверенные пункты матрицы сохраняются.

Для T030–T032 дополнительно запускать профильный набор
`DesktopNotificationAccessibilityTests|DesktopNotificationCompactTests|DesktopNotificationPromptLifecycleTests`
отдельно от общего. Проверять реальные Down/PageDown/Tab/Shift-Tab, изменённый
заголовок после tick, прежнюю координату прокрутки и возврат ключевого окна
после Escape. Обычное контрольное окно должно сначала получить фокус средствами
AppKit; отказ среды фиксировать как skip, не как успешную проверку карточки.
Не заменять физическую клавиатуру и VoiceOver этим автоматическим набором.

Reviewerchecklists — качество требований, не результат runtime. Analyze0CRITICAL/0HIGH. Послекода `$speckit-converge`, newtasks appendonly. PR exactSHA/base проверять `scripts/validate-pr-checks.py`. Tasks/issues закрывать поevidence. Historicaldocs неизменны, currentstatus/changelogfragment обновить. Полныйrelease отдельно.

### Воспроизводимая ручная проверка вопроса в Телемосте

- Только разрешённая пустая встреча без приглашений и разговора. Сначала
  остановить тестовую запись штатной кнопкой и закончить предыдущий вызов.
- Для нового предложения детектор должен увидеть прекращение всех источников
  аудио Телемоста и не менее 15 секунд непрерывной неактивности. Выдержать около
  20 секунд после выхода; это запас к порогу, не гарантия, если приложение
  продолжает удерживать аудио. Быстрые выход/вход могут оставаться одним событием.
- Подготовить проверяемое действие до создания встречи. Восемь секунд не
  останавливаются наведением или фокусом. Промежуточное открытие меню и чтение
  больших деревьев доступности может занять весь отсчёт. Для проверки первого
  физического щелчка пользователь нажимает кнопку сам, агент не переключает окна.
- Первый отдельный сценарий: «Не записывать» при выключенном флажке, после
  чего остаться во встрече. Сопоставить сообщение пользователя с техническими
  событиями отказа, отсутствием начала записи после прежнего срока и сохранённым
  правилом «Спрашивать». Не ожидать повторного вопроса внутри того же события.
- Различать `prompt_presented`, `prompt_accepted` с `reason=prompt_timeout`
  и `consumer_outcome` с `reason=user_skipped`. Принятие события детектором
  (`result=accepted`) само по себе не означает согласие пользователя на запись.
  `prompt_presented` подтверждает успешный путь показа, но не заменяет снимок,
  проверку первого щелчка и озвучивания. Сохранять только время/вид/причину
  события, без полного журнала, ссылок, идентификаторов сессий и аудио.
- Если началась тестовая запись, остановить её и выйти из встречи. Не объявлять
  отказ проверенным по одной последующей остановке; не менять срок и правило
  ради удобства испытания. Остальные варианты матрицы остаются отдельными тестами.
