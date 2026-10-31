# T048 / #4903: итоговый подтверждённый отказ — 01.11.2026

Полоса: active Spec Kit slice; финансовые уведомления. Legacy Impact untouched.
Основа: a20ce7fc008de6df21967361317ed668ce29238b. Выпуск/Dev/Full/CD не входят.

## Уточнение и анализ до кода

Существующие FR-070/SC-011 и F278 FR-009/012/014/041 определяют итоговое
уведомление без нового решения владельца. Проверены общие вызовы cutoff,
record_renewal_decline из charge/webhook/worker, шаблон PAYMENT_FAILED,
безопасное форматирование даты, planner PostgreSQL и unit doubles.
Все6групп требований связаны с исходной T048/#4903 и её scoped checklist;
несвязанных добавлений0, новых финансовых решений0. Итоговый ограниченный анализ
CRITICAL0/HIGH0. Независимый допуск требований6/0 PASS подтверждён до кода.
Группы: входы/граница, связи/статусы, согласие, транзакция/повтор, текст/данные,
проверки/границы — все6 покрыты исходной T048, без новых task/issue-дублей.

Предыдущая база UNKNOWN проверена отдельным PR7858. Здесь не повторяется
её приёмка и не принимаются остальные события/настоящая доставка T048/T068.
Ретроспективная массовая рассылка старых отказов не планируется.


## Реализация и проверка

Общий узкий помощник сохраняет уведомление через прежнюю транзакционную очередь
после cutoff и позднего record_renewal_decline. Проверены вызывающие charge,
webhook и polling пути. Финансовый guard версии согласия, _project_free,
settlement, деньги и grants не изменены. UNKNOWN допускает отсутствующий
provider_id; PAYMENT_FAILED требует canceled/canceled и известный provider_id.
Проверяются оба снимка, связи счёта и текущий активный Owner личного пространства.
После срока не создаются одновременно attempt_failed и final_failed.
Текст описывает исторический переход с датой МСК и направляет в кабинет.

| Прогон | Результат | Назначение |
| --- | --- | --- |
| red | 7 ожидаемых FAIL, 31 deselected | Отсутствует итоговое уведомление на прежнем коде |
| green | 19 PASS, 19 deselected, 6.96 s | Первые положительные сценарии и сохранение UNKNOWN |
| profile | 472 PASS / 1 FAIL, 171.94 s | Ошибка наблюдения в новом тесте late rollback |
| rollback-fixed | 1 PASS, 59 deselected, 3.08 s | Предметная проверка исправленного теста |
| profile-fixed | **473 PASS / 0 FAIL / 0 ERROR / 0 SKIP, 176.82 s** | Полный выбранный профиль на окончательных файлах |

Исходная ошибка профиля не скрыта: autoflush инвалидировал server-managed
onupdate-поле subscription; полный снимок без явного await db.refresh вызывал
MissingGreenlet. Исправлено только наблюдение теста. После rollback сравнивается
весь прежний набор уведомлений, включая PAYMENT_SUCCEEDED исходной покупки
и UNKNOWN, а не ошибочное ожидание только UNKNOWN. Продуктовый код при этом
не менялся. Повтор473 включает предметный тест; результаты не суммируются.

Полный набор: PostgreSQL renewal planner; unit renewal_charge/notifications;
integration notification_flow, renewal_lifecycle, billing_review_regressions,
billing_return; unit renewal_workflow; contract renewal_resolution.
Digest коллекции: 9c929757791f53bc8dd4f34af7a79faf977ae4b9feb3cbb68d02c87d51625e41.
Сценарии: три синтетических provider POST declines→cutoff; восемь поздних
комбинаций; UNKNOWN с известным/неизвестным provider reference; отрицательные
связи; rollback/новый сеанс/повтор/конкуренция; неотправленный canceled без
provider_id. Каждый одноразовый PostgreSQL контейнер удалён штатным runner.
Журналы/XML хранятся в /Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure.
Реальные письма, платежи, данные, GRAF Dev и production не затрагивались.

Ruff пяти изменённых Python-файлов, git diff --check,
check-development-process.py и check_spec_kit_governance.py — PASS.
Все87 исходных описаний tasks сохранены; T048 остаётся `[ ]`.

## Ограниченная сверка требований и реализации

Проверены6групп требований с одним владельцем T048/#4903: входы/граница;
связи/статусы; согласие; транзакция/повтор; текст/данные; проверки/границы.
Покрытие6/6, неподкреплённых добавлений0, CRITICAL/HIGH0.
Остаток полной T048 уже отслеживается исходной задачей, дубли не созданы.
Это сходимость только итогового отказа, а не всей F140: reminder, проверка
достаточности late-success/manual-resume, полная событийная матрица T068/#4922,
настоящая доставка #7524 и внешние условия запуска остаются открытыми.

Spec Kit prerequisites подтверждают F140; установленный скрипт не принимает
`--require-spec`, поэтому использован поддерживаемый `--require-tasks --include-tasks`
и отдельно проверено наличие spec.md. Hooks before/after analyze выключены;
before/after converge не настроены. Навыки/правила проекта не менялись.
Независимая окончательная приёмка и три точные PR SHA/base gate ещё требуются.

## Контрольные суммы окончательного кода и тестов

- `apps/server/src/twobrain_rec_server/billing/renewal_charge.py`: `ef9f2af007465c1556b8a3f0a86b99f6309ff630ec8e24f738d171dcd9f479d1`.

- `apps/server/src/twobrain_rec_server/billing/notifications.py`: `a993612940adf84a4623342c36b2464306440c6797a9dc947f0917935d7d7c40`.

- `apps/server/tests/integration/test_billing_renewal_planner_postgres.py`: `526c5b7cfbee516c348bf0e7d3fd73e109abb413acab45337c50acab992bce4d`.

- `apps/server/tests/unit/test_renewal_charge.py`: `a243312f2d9ff62d0ac6348a3c73d2ef353fb6eba50d4009be1cbdcc6ae82e33`.

- `apps/server/tests/unit/test_billing_notifications.py`: `b3c60395614dfa0036e56b7166d07fb9df143e6db9caa692ebfdacae9b588230`.
