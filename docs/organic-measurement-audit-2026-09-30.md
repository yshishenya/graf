# Проверка измерений и технического SEO rec.2brain.pro

Дата: 30 сентября 2026. Режим: read-only investigation. Изолированная ветка
`audit/organic-measurement-20260930`, база `50e05f05b026835367bb1a88c3e8d9cdbcf5b2b6`.
Production, главная, её метаданные, download, CTA и оформление не изменены.
Новые провайдеры, ключи, платежи и тестовые события не создавались.

## Решение и ближайший исполнимый шаг

Данные пока непригодны для вывода об органической активации или выручке.
Можно продолжать техническую подготовку и отдельные проверяемые материалы.
Нельзя выдавать просмотры или клики скачивания за пользователей продукта.

Минимальный пакет сейчас: этот отчёт, повторяемая read-only SQL-сверка
`docs/organic-measurement-audit-2026-09-30.sql` и описанные ниже критерии запуска.
Первое действие владельца — предоставить существующий read-only доступ либо
агрегированные выгрузки PostHog и Яндекс Вебмастера; подтвердить владельцев
юридического основания и readiness. Метрика и Search Console уже доступны;
из них нужен одинаковый период для сравнения, новые права там не требуются.
Новый OAuth и расширенный постоянный доступ требуют отдельного решения.

Пустая таблица атрибуции сама по себе не доказывает ошибку кода: записи создаются
для переходов с campaign labels. Отсутствие свежих регистраций также не позволяет
проверить перенос источника в реальную регистрацию. Исправление причин требует
сначала согласованного безопасного теста в отдельной среде.

## Проверенные production факты

| Проверка | Результат | Ограничение вывода |
|---|---|---|
| Домен и код | DNS 162.120.16.66 = 2brain.dev; `/opt/projects/2brain-rec` SHA совпадает с базой | production remote сохранил старое имя `crisp`; GitHub default — `graf/master` |
| Release-full 36750255124 | completed, success, SHA 50e05f05… | зелёный CI не гарантирует доступность сайта |
| Доступность | первая HEAD `/` = 502; затем GET `/`, `/download`, `/privacy`, `/login`, `/sign-up`, robots и sitemap = 200 | краткий сбой подтверждён, постоянный простой не доказан |
| API контейнер | healthy; между проверками пересоздавался: Up → Created → Up | временная корреляция с внешней выкладкой; причина и частота 5xx не установлены |
| Nginx журналы | недоступны yan; `sudo -n` требует пароль | не повышались права, не выполнялись restart/deploy |
| Публичная Метрика | enabled=true; replay=true; существующий counter задан | optional сбор требует отдельного согласия |
| Продуктовая аналитика | enabled=false, validation/provider mode=disabled, PostHog=false, Yandex all-pages/offline=false | продуктовую воронку провайдеры сейчас не измеряют |
| Метрика, реальный кабинет | «Источники, сводка»: 30 августа–29 сентября, 16 визитов, 10 посетителей; 8 direct, 4 internal navigation, 4 referral с 2brain.pro | цель не выбрана, сегмент не выбран; видимых поисковых строк нет; малая база |
| Цели Метрики | существующие 9 JS goals: landing, section, CTA, download, installer click, login intent, product tab, pricing cycle, FAQ | достижения целей не проверены; активным Zen одновременно пользовался владелец |

Search Console открыт в отдельной скрытой IAB вкладке с существующей сессией,
property `sc-domain:rec.2brain.pro`. Индексация обновлена 21 сентября: 1 indexed,
3 excluded; 2 crawled-not-indexed — `/terms` (crawl 27 августа) и `/offer`
(26 августа), ещё одна redirect. URL inspection главной: «URL есть в индексе
Google», crawl 11 сентября 18:42:50, Googlebot smartphone, fetch успешно,
crawl/index разрешены, declared canonical и selected canonical — главная HTTPS.
Вебмастер открыл welcome/Add site, существующая property не показана; PostHog
открыл `/login` без сессии. Ни аккаунты, ни права, ни ключи не создавались.
Пустой `site:` не является доказательством отсутствия индексации.

Search Console performance: выбран период «3 месяца», веб-поиск; обновлено
10 часов назад. 0 clicks, 1 impression, CTR 0%, average position 7; график
показывает доступные данные с 19 августа по 27 сентября. Query table «Нет данных».
Одного показа недостаточно для вывода о позициях/запросах или эффективности SEO.

URL inspection `/download`: URL нет в индексе, «URL неизвестен Google»,
ссылающиеся sitemap/страница не найдены, последнего сканирования нет.
Это конкретный пробел обнаружения. Live download проверен 200/canonical/indexable;
отправленный sitemap включает его. Индексация после отправки не гарантируется.

В Search Console не было отправленных sitemap. Перед разрешённой отправкой
проверены все 7 live URL: HTTP 200, exact HTTPS canonical и нет noindex;
XML корректен. Существующий `https://rec.2brain.pro/sitemap.xml` отправлен:
Google показал «Файл Sitemap отправлен», дата 30 сентября; сразу после отправки
в таблице статус «Не получено», тип «Неизвестно», выявлено 0 URL. Это подтверждает
отправку, но не успешную обработку. Не выполнять повторные submit или принуждение
индексации юридических страниц; позже проверить receipt/fetch status.

## Реальные данные БД и расхождения

Все запросы выполнялись внутри `BEGIN READ ONLY`; выводились только агрегаты,
даты и схема таблиц. Аудио, текст встреч, email, имена и идентификаторы не читались.

| Источник | Факт | Что нельзя заключать |
|---|---|---|
| anonymous_page_aggregate_buckets | 148 бакетов, 331 request visits, даты 22–30 сентября | это не 331 человек и не 331 сессия |
| Главная | 115 external, 21 automated посещение | external не гарантирует исключения сотрудников |
| Download | 10 external, 22 automated | просмотр страницы не означает скачивание |
| Installer delivery | 25 automated; external значение ниже порога раскрытия 5 не публикуется | нельзя выдать автоматические доставки за установки |
| public_visit_attributions | 0 строк | недостаточно данных для реального campaign handoff, не доказательство дефекта |
| client_acquisition_attributes | 1 строка, bridge_present=0, 28 сентября | нет проверенного organic → desktop cohort |
| user_identities | 48; последняя создана 29 августа | исторические аккаунты не свежая конверсия сентябрьского трафика |
| processing_results | 185 | результат обработки не обязательно первая активация уникального клиента |
| processing_workflows | processed=183, blocked=11, failed_terminal=10, waiting_retry=5; canceled ниже порога раскрытия | workflow и result различаются по смыслу; причины расхождения не исследованы |
| Billing | 8 operations / 8 уникальных idempotency keys; 4 webhooks / 4 уникальных provider event ids | отсутствия дублей по ключам мало для сверки платежей; succeeded не доказанная live выручка |

Повторный запуск приложенной SQL-сверки дал 150 бакетов / 344 requests;
счётчик обновляется, поэтому снимки не являются фиксированной месячной базой.
Для общего окна 30 августа–29 сентября: landing external=106, automated=20;
download external=8, automated=21; installer delivery automated=24.
Наши GET-проверки выполнялись curl/python-urllib, которые классификатор относит
к automated; они могут увеличить технический агрегат, optional JS события не
исполнялись. Это не тестовые регистрации, оплаты или события активации.

331 DB requests и 16 Метрики нельзя делить друг на друга как consent rate:
разные периоды, поверхности, бот-фильтры и единицы (request/pageview против
session). Нужно одинаковое окно времени, определение визита, scope и фильтры.
В runtime internal hosts пусты. Операторский обычный браузер может попадать в
external; код распознаёт автоматические user agents, но это не полная защита.
Cross-domain referral с 2brain.pro виден; связность user/session между доменами
и подавление self-referrals не проверены. Direct нельзя переименовывать в AI.

## Согласие, приватность и readiness

Live HTML и код ограничивают внешний counter и replay двумя страницами: `/`
и `/download`. `/privacy`, `/login`, `/sign-up` имеют replay=false и
external_counter=false. Формы не отправляются в Метрику; form_analytics=false,
sendTitle=false, trackLinks=false, trackHash=false. На остальных public pages
используется first-party relay в PostHog; текущий выключенный provider означает,
что этот путь не даёт подтверждённой доставки. Его наличие в HTML не доказывает
достижение событий. Кабинет продукта имеет noindex в базовом шаблоне; share token
маршруты имеют X-Robots-Tag noindex/nofollow/noarchive и no-store.

Локальные consent проверки подтвердили: нет события без решения, отказ сохраняется,
повреждённое решение означает отказ, отзыв прекращает отправку, consent только
на analytics не включает replay, signup не несёт введённых form values.
Это проверка логики и rendered scope, а не аудит фактических записей Webvisor
или всех payload в кабинете провайдера. Последнее остаётся обязательным до вывода
«PII никогда не уходит».

Production metadata-only `resolve_provider_delivery_gate` для всех трёх providers
возвращает allowed=false. Реальные блокировки: product_analytics_disabled,
validation_mode_disabled, legal_not_approved, dashboard_not_ready,
provider_smoke_not_approved, live_provider_delivery_not_approved,
provider_analytics_basis_not_confirmed; approval_state_file_unavailable,
access_governance_state_unavailable, backup_state_unavailable,
restore_verification_missing, retention_state_unavailable.
Отдельные approved=true в env не заменяют реестры подтверждений.

Минимальный достаточный путь:

1. Согласовать legal basis и disclosure для pseudonymous milestone events,
   владельца доступа, срок retention и существующий провайдер. Сбор содержимого
   встреч, названий, email и участников запрещён.
2. В отдельной среде проверить только explicit события: download click,
   installer delivery, desktop_first_opened, account connected,
   first_recording_completed, first_result_viewed, first_value_session_completed.
   Replay, autocapture, direct desktop egress, Yandex all-pages/offline не нужны
   для минимальной продуктовой воронки. Предложение: оставить их выключенными;
   это предложение не применено к production.
3. Проверить exact attribution handoff, окна/истечение, отсутствие PII в UTM,
   unknown отдельно от direct, внутренний/тестовый трафик, отказ и отзыв.
4. Проверить durable дедупликацию и повтор после рестарта/с нескольких устройств.
   MilestoneEmissionGuard по умолчанию процессный, приложение хранит durable copy;
   серверная process guard сама по себе не доказывает один milestone на аккаунт
   через рестарт и все устройства. До rollout нужен отдельный evidence тест.
5. Собрать readiness registry/access/backup/restore/retention evidence, сделать
   provider smoke в тестовой среде и только затем согласовать точный runtime diff.
   Не просто менять enabled/live_safe и approved flags.

## Воронка и правила отчёта

Organic sessions → download CTA → доставленный installer → first launch →
подтверждённый аккаунт → первая успешная обработка → просмотр полезного результата
→ повторная полезная сессия в дни 1–7. Account/signup и email verification
разделять; существующий auth audit требует дополнительной сверки семантики.
Основной показатель до готовности оплаты — уникальные первые полезные результаты
на органическую когорту, а не pageviews. Публиковать coverage связки и долю unknown.
Если данные о first launch отсутствуют, показывать «не измерено», а не ноль.
Retention считать на созревших когортах; сегодняшний клиент ещё не D7 cohort.

После проверки платежей: paid conversion и net revenue из live server payment
ledger, с provider reconciliation, возвратами, отменами и test/live разделением.
Никаких сумм выручки из восьми найденных операций без этой сверки.

## Техническое SEO и приоритеты

P0: выяснить причину и частоту кратких 502 через разрешённую агрегированную
выгрузку nginx или владельца сервера; проверить существующий мониторинг и его
покрытие. Никаких инфраструктурных изменений по одному замеру.

P1: подтвердить Search Console/Яндекс Вебмастер property, sitemap receipt,
URL inspection главной/download, canonical selected, crawl errors и search
clicks/impressions. robots и sitemap живые 200; sitemap содержит 7 публичных URL;
canonical public HTML правильные HTTPS. HTML серверный, schema уже существует.
Дубли SoftwareApplication/FAQPage не добавлять. Auth/cabinet не включать в sitemap.

Доступ к Search Console подтверждён, главная/download и эффективность проверены.
Осталась обработка отправленного sitemap и дальнейшее обнаружение download; Вебмастер
требует существующую property/session либо экспорт. Построение новых grants
не входит в этот пакет. Для PostHog достаточно существующего project read-only
доступа либо агрегированного экспорта events/delivery/дублей по дням и event_name,
без distinct_id, payload и содержимого replay. Для Вебмастера — индексация,
диагностика crawl, обработка sitemap и показы/клики для HTTPS rec.2brain.pro.

Обязательные решения readiness и владельцы: repo назначает роль product analytics
operator с infrastructure operator backup, а Yandex offline — growth analytics
operator. Конкретные люди на эти роли не подтверждены; не назначать их по имени
вошедшего пользователя. Владелец продукта должен подтвердить ответственных:
legal/privacy — основание и допустимые данные; product analytics operator —
definitions/dashboard/smoke; infrastructure operator — backup/restore/retention,
доступ и rollback. Нужны проверяемые реестры, а не только env=true.

## Короткий план стендовой explicit воронки

Использовать существующие тестовые fixtures и отдельный disposable PostgreSQL,
синтетические campaign labels `organic_test` и псевдонимный аккаунт. Продуктовые
провайдеры заменить test doubles; счётчик production и реальные ключи не задавать.
Первый прогон уже сделан существующими 85 unit тестами и 8 DB consent tests.
Это проверки отдельных звеньев, не доказательство реальной end-to-end установки.

Оставшийся сквозной сценарий: вход с synthetic UTM → download CTA → получение
installer (отдельные counters) → first launch тестового клиента → account connect
→ safe sample processing → ready result → first result viewed → повторная
полезная сессия. Для D7 использовать фиксированные часы теста, не ожидание недели.
Протоколировать только event_name, synthetic linkage presence, status и counts.
Повторить: без consent; analytics без advertising/replay; отзыв; истёкший bridge;
unknown/direct; повтор click/result; рестарт сервера и второй тестовый клиент.
Критерии: отсутствие optional egress без согласия, запрещённых полей и дублей
first milestone; один источник на связанный synthetic cohort; processed/ready
сверяется с серверным состоянием. Только после этого делать provider smoke
на согласованном тестовом ресурсе и предоставлять точный rollout diff владельцу.

Команда уже проверенного DB smoke:
`bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_public_analytics_consent_enforcement.py -q`.
Unit smoke: `pytest` для `test_public_visit_attribution.py`,
`test_product_analytics_attribution_bridge.py`, `test_product_analytics_milestone_dedupe.py`,
`test_product_analytics_forbidden_fields.py`, `test_product_analytics_provider_delivery_gate.py`.

P2: og:image отсутствует; это возможность улучшить preview, не причина объявлять
индексацию сломанной. FAQ JSON-LD и видимый текст о Windows/Linux расходятся;
download обещает «скоро». По новому указанию пользователя тексты и метаданные
главной/download сохранены, изменения только предложены отдельно.
Мобильные 360/390/768 ещё не проверены. Не считать CSS брейкпоинты доказательством.

Контент после реальной проверки сценариев: 2–4 отдельных материала о записи на
Mac без бота, Телемост/Google Meet на Mac, запись → протокол. Не обещать уникальность,
не создавать массовые страницы и не публиковать приватные примеры. Расширение
решать по органическим активациям созревших когорт.

## Проверки и состояние поставки

- 21 Python unit/contract test passed: public analytics и landing contract.
- 9 consent JS harness сценариев passed.
- 3 headless Chromium consent modal сценария passed на localhost.
- 85 unit tests attribution bridge, public visit, milestone dedupe,
  forbidden fields и provider delivery gate passed на синтетических данных.
- DB-dependent consent enforcement: после подготовки disposable local PostgreSQL
  8 passed, 1 skipped; контейнер автоматически удалён. Предыдущие 6 setup errors
  отсутствующего TWOBRAIN_DATABASE_URL устранены. Production БД для тестов не
  использовалась. Пропущенный тест не считается подтверждённым.
- Начатые собственные template изменения точечно отменены. git diff runtime пуст.
- Код production не исправлялся: подтверждённого узкого runtime дефекта, который
  допустимо безопасно исправить без readiness процесса, не установлено.
- Документы/SQL подготовлены; merge/deploy не выполнялись. Draft PR публикуется
  отдельно, без runtime diff. Единственная внешняя запись — разрешённая отправка
  существующего sitemap в Search Console; не rollout сайта или аналитики.
