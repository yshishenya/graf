# T048 / #4903: UNKNOWN при окончании периода — 01.11.2026

Полоса: active Spec Kit slice; серверное финансовое уведомление. Legacy Impact:
untouched. Исходная основа проверки `638cf598269a717258e77140d7e28801257b06d0`;
обязательная приёмка PR выполняется отдельно на окончательном SHA и текущей основе.

## Результат

В существующем `project_renewal_cutoffs` после Free/unknown_pending создаётся
`RENEWAL_UNKNOWN` только для sent/processing/unknown, текущего плательщика и
заканчивающегося paid_through. Учитываются прежние personal/active Owner scope
проверки; invoice принадлежит operation/workspace, остаётся pending/unknown,
оба снимка подтверждают payer/period. Согласие на будущие списания, финансовые
состояния, срок и grants не меняются этим дополнением. В одной транзакции
используется прежняя постоянная очередь и `renewal:<invoice UUID>:unknown`.
Текст описывает включение бесплатного тарифа и неизвестный результат
на границе периода в прошлом; актуальный статус предлагается посмотреть в кабинете. Никакой новой таблицы/службы/зависимости/миграции нет.

## Проверки

| Прогон | PASS | FAIL | SKIP | Назначение |
| --- | ---: | ---: | ---: | --- |
| baseline | 114 | 0 | 0 | прежние planner PostgreSQL + renewal unit |
| red | 0 | 6 | 0 | во всех шести сценариях нет записи notification |
| green | 7 | 0 | 0 | три состояния × два согласия и rollback |
| profile | 416 | 20 | 0 | выявлена утечка тестовых подписок между сценариями |
| profile-fixed | 436 | 0 | 0 | весь выбранный профиль после исправления подготовки |
| final-module | 26 | 0 | 0 | окончательные байты целого planner PostgreSQL module |

Первый расширенный прогон не принят. Cutoff обрабатывает все подходящие
пространства, а paid_workspace оставлял оплаченные подписки прежних случаев.
В finally удаляется только подписка своего созданного case.workspace из
одноразовой БД; исходный setup-отказ защищён case=None. Продуктовая область
обработки и строгие assertions не изменены. Все20 новых случаев прошли:
6 положительных, rollback,12 несовместимых/оконченных связей, concurrency.
Повтор, commit/новая AsyncSession, сохранность original purchase/grants/methods,
согласия/версии/paid_through, безопасный payload и текст проверены.

Точный профиль — existing run_local_postgres_tests.sh --focused с файлами:
`integration/test_billing_renewal_planner_postgres.py`, `unit/test_renewal_charge.py`,
`unit/test_billing_notifications.py`, `integration/test_billing_notification_flow.py`,
`unit/test_billing_renewal_workflow.py`, `contract/test_renewal_resolution.py`,
`integration/test_renewal_lifecycle.py`, `integration/test_billing_review_regressions.py`,
`integration/test_billing_return.py`. 436 PASS за171.42s; final module26 за7.90s.
Использованы настоящий migrated PostgreSQL/forced RLS и maintenance role без
superuser/BYPASSRLS/table ownership. В новых сценариях HTTP запрещён fixture;
профильные внешние ответы синтетические. После каждого прогона runner удалил
свой одноразовый контейнер. Два существующих предупреждения не являются skip.
Новые AsyncSession не выдаются за отдельные физические сетевые соединения.

ruff по трём Python-файлам, git diff --check, check-development-process.py
и check_spec_kit_governance.py — PASS. Все87 исходных описаний задач сохранены;
снята лишь ошибочная общая отметка T048. Независимые основания требований6/6
и заключительное ревью находятся в review-renewal-unknown-20261101.md.

Scoped analyze:6 требований→T048, покрытие100%, CRITICAL/HIGH0, новых
продуктовых вопросов0. Scoped converge: producer/copy/атомарность/связи/проверки
предусмотренного UNKNOWN реализованы; несвязанных добавлений0. Остаток исходной
T048 уже отслеживается ею же, дубли задач/issues не созданы.

## Границы

T048/#4903 остаётся открытой: reminder, failure-to-Free, late-success,
manual-resume и вся исходная приёмка ещё не доказаны. #7524/реальная доставка
почты также открыта. Исторические58 открытых пунктов общих списков не приняты.
Настоящие письма/платежи, Dev, выпуск, Full/CD, рабочие настройки и финансовая
приёмка не выполнялись. Проверки GitHub точного SHA/основы обязательны до merge.

## Контрольные суммы продуктового исправления

- `apps/server/src/twobrain_rec_server/billing/renewal_charge.py`: `93363014b3fb62d073ef94acd59b11e7a43e12a91bfb76bf31bc5567fbacf0ef`.
- `apps/server/src/twobrain_rec_server/billing/notifications.py`: `6a8a4d1e3b3701a16dc7b25c4008db68a6f0b689eeff057c1c1809e84a7d560f`.
- `apps/server/tests/integration/test_billing_renewal_planner_postgres.py`: `c5e8d8b2edff01da408c7651def793d2735863373e7a3661f2dc2bed828025b2`.

## Дополнительная проверка задержанной доставки до merge

Независимое ревью обнаружило P2: прежние заголовок/тело ошибочно утверждали
текущие Free и неизвестный исход при возможном позднем успехе до отправки.
До кода уточнены spec/plan и CHK005, requirements6/0 PASS. Исправлен только
существующий шаблон: состояние на границе периода описано в прошлом;
за актуальным статусом платежа и тарифа нужно открыть кабинет.
Новых delivery guards, таблиц, состояний или сетевых действий нет.

Причинный copy-red:6 ожидаемых FAIL именно на старом заголовке,2 PASS,
18 deselected. Copy-green на окончательных байтах:59 PASS/0 FAIL/0 SKIP
за17.30s, весь planner PostgreSQL + notification unit + notification flow.
Этот набор пересекается с прежними436 и не прибавляется к ним.
Оба одноразовых контейнера штатно удалены. Журналы/XML: copy-red/copy-green
во внешнем каталоге graf-f140-renewal-unknown. Ruff, process, governance
и diff --check повторно PASS. Предыдущие исходные RED и временно отвергнутый
PASS сохранены; требуется новое независимое итоговое ревью и новые GitHub gates.
