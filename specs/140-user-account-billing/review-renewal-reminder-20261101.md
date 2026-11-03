# F140/T048 — независимая проверка требований напоминания, 01.11.2026

**SCOPED REQUIREMENTS PASS — 6 отмечены / 0 открыты.** Ограниченный анализ:
покрытие 6/6, неподкреплённых добавлений 0, CRITICAL 0 / HIGH 0;
блокирующих вопросов не найдено. Это допуск к реализации после остальных
ворот, не подтверждение ещё отсутствующего кода/проверок/доставки.

Полоса: active Spec Kit, серверные финансовые события. Ветка
`codex/140-renewal-reminder`, HEAD `838aa9e93310d341885b1a7a1d0b4011f3ed45ec`;
feature.json подтверждает F140/T048. Старый HEAD в файле назначения не принят
за текущую основу. Изменения назначения ограничены этим отчётом и новым
checklists/renewal-reminder.md; parent final-failure review не менялся.

Непосредственно прочитаны весь новый diff spec/plan/tasks/quickstart и
шесть пунктов reminder checklist, FR070–073, notifications-support,
security-privacy-compliance, F278 FR014/041. Прежние прочитанные конституция,
AGENTS и применимые guidance сохранены; их текущие суммы совпали.

| Пункт | Основание достаточности и планируемая проверка |
| --- | --- |
| CHK001 | Spec задаёт текущего personal active Owner, прежние price/consent/method/pending/window ограничения и первое окно [−72,−48). Пропущенное первое окно/backfill не принимаются за reminder. Plan/quickstart требуют отрицательные финансовые границы. |
| CHK002 | Spec/plan задают событие на payer/workspace/paid_through без номера операции/попытки, в одной транзакции с operation/invoice. Повтор, local retry, новое согласие в том же периоде и следующие окна не создают второго reminder; PostgreSQL commit/new session/rollback/concurrency предусмотрены. |
| CHK003 | Spec явно отделяет событие от согласия, денег, успеха и разрешения dispatch. Plan сохраняет всё финансовое планирование/отправку. Письмо не блокирует попытку; F278 FR014/041 и прежние неизвестные исходы/отзыв/paid-through не меняются. |
| CHK004 | Принятые personal/month-year/amount minor/RUB, первое окно/конец периода МСК, last4 и /billing/subscription заданы. При отсутствии маски безопасная общая фраза; полный номер, email и provider reference исключены. Plan/quickstart требуют allowlist и форматирование. |
| CHK005 | Spec/quickstart требуют исторический текст расписания, правдивый после dispatch/success/decline/revocation, без обещания будущего списания или текущего согласия/тарифа. Текущий статус и изменения доступны в кабинете. |
| CHK006 | Plan/quickstart задают настоящий PostgreSQL planner и прежнюю очередь, RED до минимального producer, сохранение/rollback/повтор/конкуренцию/следующие окна/негативы. Нет нового scheduler/schema/service; настоящая почта/деньги, полные T048/T068/#7524/выпуск остаются вне приёмки. |

Проверен настоящий flow: plan_due_renewals в renewal_charge.py выбирает
personal активного Owner, блокирует workspace/subscription, проверяет
согласие, незавершённые покупки, принятый составной каталог/сумму, saved method,
receipt contact и последовательные окна. При создании operation он сохраняет
payer/paid_through/cycle/amount/currency snapshot и счёт. Новый вид reminder
и его producer пока отсутствуют — подтверждённый предмет будущей реализации.
Физического renewal_planner.py сейчас нет; действующий вход находится в
renewal_charge.py, а не в новом модуле.

run_billing_renewal_reconciler сначала коммитит planner, затем в отдельном
сеансе выбирает charge candidates. Существующий events/outbox только flush,
commit принадлежит вызывающему. Следовательно, требуется одна запись
существующей очереди при первой операции, а не новый scheduler или ожидание
доставки до списания. Конкуренция опирается на тот же workspace lock и
существующую уникальность event/recipient/channel; новый event_id должен
включать плательщика/пространство/оплаченный период, а не UUID попытки.

Важные границы реализации из уже принятых требований: актуальность personal
active Owner проверяется при создании события после lock, а не считается
вечной из первоначального query. Маска разбирается только до допустимого
last4: нынешний snapshot может содержать masked_label, его нельзя выводить
произвольной строкой. Amount берётся из принятого составного снимка в целых
minor units, не из публичной цены или float. Платёжные guards не ослабляются;
новый вид должен быть обязательным и иметь ограниченный безопасный payload.

Общие списки пересчитаны: 162 отмечены / 58 открыты, отметки не менялись.
Это продуктовый срез, прежние test-only T074/файловая T075 не дают исключения
из полномочий, изоляции, согласия и сохранности. Не требуются дубли писем
только из-за существования enum: manual resume/success оцениваются отдельно
по поведению AUTORENEWAL_ENABLED/PAYMENT_SUCCEEDED. Parent final-failure
и его 473 PASS не принимают ещё отсутствующий reminder.

Checklist после записи полностью перечитан: **6 отмечены / 0 открыты**.
Тесты/БД/HTTP/почта/приложение/Git/GitHub проверяющий не запускал и не менял.
`git diff --check` PASS. Дальше нужны реализация, предметные сохраняемые
доказательства, независимое review/converge и три PR gate точного SHA/основы.
T048/#4903, T068/#4922, #7524 и запуск этим результатом не закрываются.

## Контрольные суммы текущих источников

- `AGENTS.md`: `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958`.
- `.specify/memory/constitution.md`: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- `docs/agent-guidance/spec-kit-flow.md`: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`.
- `docs/agent-guidance/product-gates.md`: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- `docs/agent-guidance/release-and-validation.md`: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`.
- `docs/agent-guidance/tracker-policy.md`: `9793de5e158283c2d37bdd2b47f0daf4d312a44fd6ffa37cc22ac47f7a0c3472`.
- `specs/140-user-account-billing/spec.md`: `44f3d1d2ffdd110a87a85c39e7ebc8cbdf97c4bd18b3e988e2cbf8c1dc5797e0`.
- `specs/140-user-account-billing/plan.md`: `30ca2a01a60ed8e7a7ee7e4221b062e80bd43d11511652470ca291faf964b961`.
- `specs/140-user-account-billing/tasks.md`: `6036a52a1de3fdd667dde4fad6af2c8e5236f94f7f0059510fa0b096b0003518`.
- `specs/140-user-account-billing/quickstart.md`: `a8a40e99036f91b128f9129494e7e1e7b57a334dc73d35c97aea6a38d5ee19fc`.
- `specs/140-user-account-billing/contracts/notifications-support.md`: `3b5d29fc37d63087a70d05151da42f7bbe873276c98234a77e9826bba0fdac97`.
- `specs/140-user-account-billing/contracts/security-privacy-compliance.md`: `38934189b91e33a070b49e61673020d41530eec3d06a4fad5bd00f3317071cfc`.
- `specs/278-production-billing/spec.md`: `db906afb6bb2ae5f3034e64b77db2eb4ff1ea5c144f5d69e2a5aee0cf6cb7d83`.
- `apps/server/src/twobrain_rec_server/billing/renewal_charge.py`: `ef9f2af007465c1556b8a3f0a86b99f6309ff630ec8e24f738d171dcd9f479d1`.
- `apps/server/src/twobrain_rec_server/billing/notifications.py`: `a993612940adf84a4623342c36b2464306440c6797a9dc947f0917935d7d7c40`.
- `apps/server/src/twobrain_rec_server/billing/events.py`: `c4d8b6cdc72c31aa19d0d3a58ce72e6dae28551f8b2784974facc638c75512cf`.
- `apps/server/src/twobrain_rec_server/billing/payment_methods.py`: `51c0d747daa8ddb5f1b9362ece0123575af8522be72cfc3981af3e933a75e4ef`.
- `apps/server/src/twobrain_rec_server/workflows/worker.py`: `376820913dfd73477d25cb07945ebbc9547772126758fa1ab1e59a70881d2ba7`.
