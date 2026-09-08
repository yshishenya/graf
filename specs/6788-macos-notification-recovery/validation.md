# Проверки объединённой F6788 — рабочий журнал

Дата: 2026-09-08. Ветка codex/6788-macos-notification-recovery, база
 e81b412dff920cc29ed37de60be13dd8fc4d1c43. Это результаты незакоммиченного
объединённого дерева; точный кандидат/CI/Dev добавляются после фиксации.
Lane: high-risk-product. Merge, release и production не выполнялись.

## Выполнено

- Независимые требования: affected-analysis.md, 22 FR/SC и 21 задача,
  38/38 требований UX/capture/security/infra, CRITICAL/HIGH/MEDIUM0.
- Обязательные ensure/validate после объединения: 279 Spec Kit issues PASS;
  #6825 владеет T001–T021; источники F258/#6824 остаются Refs.
- Issue-canon upstream: 21 unittest PASS, GRAF full-ID regression3 PASS.
  Закреплён источник adf2b1b6d7f04ec97099b6716d2f971350262920;
  отдельный PR зависимости spec-kit-ext-github-issue-canon#11, без публикации.
- Frozen governance PASS с изолированным specify1.0.1. Extension установлен
  штатным CLI из immutable archive; lock хранит реальный source/archive/tree,
  а не скрывает drift. Глобальный specify не изменён.
- Нативные focused: 289 PASS (capture, calendar, route, controls, notifications,
  upload/client/queue/custody). Включены реальные async gates для смены owner,
  snapshot/calendar во время permission/submit, отсутствие recap при12 готовых
  встречах, свежие/исторические/чужие incidents, переход к своей записи внутри
  общей группы и повтор команды. ОС этими тестами не вызывается.
- TwoBrainRecApp compile PASS после итогового переноса/targeting.
- Серверный объединённый набор: 197 tests, первоначально191 PASS/1 SKIP/5 FAIL.
  Все5 FAIL — удалённые по решению владельца поля UUID/time native recap в
  старых ожиданиях F258. После адаптации весь изменённый summary-slot набор:
  23 PASS. Таким образом функциональные проверки выбранных197 прошли,
  кроме явно пропущенного bootstrap ниже; исходные F2581734 не засчитываются.
- В серверном наборе выполнены actual restricted media-role/RLS/DML checks,
  processing/sync/audio source fences, selected summary format, Node behaviour,
  contract/static assets/settings. PostgreSQL запускался в одноразовом
  контейнере, удалён штатно. Общий GRAF Dev и его БД не использовались.
- Общий Swift набор820: первоначально818 PASS/1 SKIP/1 FAIL. FAIL был старым
  source-string ожиданием группировки custody; исправлено на адресный выбор.
  Повтор всей соответствующей группы: 17 PASS. Итоговый общий прогон: 820 tests, 819 PASS / 1 SKIP / 0 FAIL (38.28с).
- git diff --check и changelog validator PASS.

## Не засчитано как PASS

- Swift permission preview без GRAF_PERMISSION_PREVIEW_DIR — штатный SKIP.
  DesktopCabinetWorkspaceTests и EmbeddedCabinetJavaScriptConfirmTests исключены
  из CLI: создают отдельные окна вместо единственного установленного GRAF Dev.
- Full runtime-role bootstrap idempotence — SKIP в shared fixture namespace;
  отдельная actual media-role проверка прошла. Не выдавать её за полный bootstrap.
- Установленная приёмка, реальная synthetic запись и настоящий OS banner/actions
  объединённого кандидата — NOT RUN. VoiceOver исключён владельцем.
- На момент проверки общего стенда active F256/257, schema0090. F256 согласована
  короткая повторная приёмка. Наша база0089; штатный harness запрещает
  schema rollback после допуска новых writers. Данные/manifest не подменялись;
  требуется совместимый путь приёмки, иначе этот gate остаётся открытым.
- Exact-SHA GitHub governance-fast — ещё не запускался для продуктового PR.
- Release-full/CD/notarization/appcast/production — не выполнялись: эта задача
  готовит PR, публичный релиз имеет отдельный frozen candidate и разрешение.

## Legacy и объём F258

Убраны DesktopRecordingWidget/его View/placement и четыре private tray events;
общий dispatcher, F214, очередь, decoder и данные сохранены. Не перенесены
native recap, отдельные UUID/time и helper без оставшегося потребителя.
Сохранены звук/progress/обновление/узкие grants, owner/auth epoch/incidents.
Результаты обработки остаются в кабинете. Старые настройки false читаются.
Дедупликация календаря использует stable occurrence ID и синхронизирует прежний
ключ с временем при его обнаружении. Claim означает попытку, не доказанный
показ ОС. Никакой fallback-overlay при Focus или отказе нет.

## Дополнение T022 и финальные проверки до коммита

- Независимый bounded review Reload: code-review.md, подтверждённых замечаний нет.
- На объединённом дереве настоящий WebKit/loopback HTTP воспроизвёл прежний
  отказ: второй GET не пришёл за5с. После guard исправления весь набор:
  29 PASS (18route +10request-policy +1reload),0.338с. Тестовое окно не показывалось.
  Логи reload-red.log/reload-green.log в ignored .dev/imported-postrelease.
- Серверный ruff check: PASS. Issue canon после T022:279 PASS.
- PR зависимости issue-canon#11: все обязательные CI/Security checks PASS
  на adf2b1b6d7f04ec97099b6716d2f971350262920; не merged/released.
- 2026-09-08: F256 освободил Dev после14smoke, активный dev-74ceabab096b
  со schema0090; следующий согласованный слот взял F257. Эти результаты
  не засчитываются F6788. Installed часть T014/T021 и финальный T015 открыты.

- Финальный общий серверный набор всех изменённых test-файлов:173 PASS/1 SKIP,
 101.37с; actual media-role/RLS/DML, summary-slot/format, sync/context, Node,
 шаблоны и настройки. Лог merged-server-final.log. Одноразовый контейнер удалён
 штатно. Это174 теста; ранний197-набор включал дополнительные неизменённые
 проверки, его пройденные результаты остаются историей этого дерева.
- Общий code reviewer после длительного чтения был прерван родителем и
 продолжен в той же read-only session для конечного заключения. Прерванный
 проход сам по себе не засчитывается как review PASS.

## Итоговый review и T023

Независимый общий review:combined-code-review.md. C1–C3 закрыты, P0/P1=0,
один P2 о неверной подписи partial. Отдельных Ponytail findings нет. T023
согласовал серверную строку/метку и реальный JavaScript списка/этапов.
Optional summary_status в MeetingListItem берётся из прежней проверенной
проекции; новых данных/прав/миграций нет.

Регрессии до исправления:2 FAIL (сервер и Node); после:132 PASS/0 SKIP/0 FAIL,
125.57с, включая все summary-slot/Node/static-assets/meeting-list. Логи
partial-red.log/partial-green.log. Ruff, whitespace и changelog PASS.
Независимая повторная проверка T023 выполняется отдельно.

## Сверка перед первым PR

T023 независимо принят:t023-review.md, P1/P2=0; код пяти файлов после
132PASS неизменен. Общий review вместе с повторной проверкой закрывает
C1–C3 и последний P2. Продуктовый объём23 задач/14 FR/8 SC: реализация
T001–T013,T016–T020,T022–T023 завершена. Остались существующие T014/T021
(установленный путь и измерения) и T015 (Dev/CI/готовый PR). Дополнительной
непокрытой работы по коду при повторном converge не выявлено; открытые gates
не продублированы новыми задачами и не названы полным завершением фичи.

Перед коммитом:git diff --check, changelog, frozen governance PASS; bounded
credential-pattern scan88 изменённых/новых файлов — совпадений нет. Разрешение
на проверенный commit/push/PR уже дано владельцем. Ни исходный F258PR, ни
старые задачи не закрываются этим черновиком.

## T024: достоверная проверка конкурирующей установки Dev

F257 передал воспроизведённый в общем CI нестабильный результат прежнего
test_concurrent_promote_is_serialized. Независимый reviewer подтвердил
границы SC006: один изменяемый manifest не моделирует двух конкурирующих
кандидатов. Второй процесс может прочитать уже опубликованный active и
законно получить idempotent PASS. Если оба прочитали исходный manifest,
второй получает identity-changed, а не заявленный старым комментарием
stale-parent. В изолированном последовательном воспроизведении получены
active/active и second_idempotent=true. Старый тест на Mac в данном запуске
прошёл; это не red→green доказательство постоянного отказа.

T024 меняет только tests/governance/test_dev_harness.py: общий активный
родитель, два разных кандидата, один победитель, точный stale-parent отказ
второму и сверка active ID/SHA/parent с победителем. Отдельная проверка
повторного запуска active сохранена. scripts/dev-harness.py, блокировка,
приложение, runtime, данные и manifest настоящего Dev не менялись.

После исправления: весь test_dev_harness.py —17 PASS,0.51с (macOS spawn);
целевой тест с multiprocessing fork —1 PASS,0.08с; весь tests/governance —
299 PASS/1 SKIP,36.82с. Проверки используют временные метаданные без --live.
Успех одного запуска не означает перебор всех вариантов планирования.
Независимая проверка требований T024 принята до изменения; итоговая проверка
diff: t024-review.md, PASS/P1/P2=0, собственный запуск reviewer1 PASS.
Convergence T024 закрыт; дополнительных задач в этом изменении не найдено.
Установленная приёмка T014/T021 и итоговая T015 открыты.
