# T112/T113 — первичный вывод ревью реализации admission owner

16.11.2026. Независимый проверяющий `/root/public_counter_readiness_review`.
Копия `/private/tmp/graf-f273-result-visibility-20261116`.
F273/T112/#7698, T113/#7804; `high-risk-product`.
Заявленная основа8a7b43955e6abc1dcdac8d47f8cbfb16ff359ae7 плюс uncommitted
реализация. Git/remote не опрашивались; идентификация SHA-256.

## Историческое решение

**Первичный implementation HOLD: P1=0, P2=1.**
Этот вывод относится к Session source477d2164 до исправления precommit.
Файл сохраняет первоначально сообщённое замечание и причинное воспроизведение;
на момент записи исполнитель уже начал исправление. Текущую исправленную
редакцию следует оценивать отдельным повторным отчётом, а не переносить
этот HOLD на изменённые файлы или затирать исходную находку.

## P2 C1 — precommit recheck позволяет оживить операцию

`apps/server/src/twobrain_rec_server/cabinet/result_projection_session.py`,
`ResultAdmissionSession.commit_pair`, строки322–340 прежней редакции477d2164.
`recheck()` на строке326 находился перед `try/except BaseException/finally`.
После PermissionError от отозванного допуска owner.failed/budget.failed и
_terminal не устанавливались. Обе операции уже завершены, _phase==2;
внутренний caller мог перехватить отказ внутри owned context, прочитать
снова и повторить commit_pair с проходящим callback в том же снимке.

Обычный `_account_transaction` не перехватывает эту ошибку и откатывает
вызов; это не заявленный удалённый обход. Дефект находится в намеренно
строгом контракте нового owner: после отказа нельзя оживить ту же операцию.
Основание: integration design1723f68c §§7/8/D1 и persistent-refusal R4,
result-visibility §§2/3/5/7. Исправление требует поместить recheck и переход
к commit внутрь прежней защищённой области, сохранив failed/terminal для
любой ошибки/отмены и неизменные caps/сроки/учёт фактической попытки commit.

Причинный новый `test_caught_precommit_guard_failure_is_terminal_and_never_retries`
завершился **1FAIL/55deselected/3.93s**, runner7s,cleanup removed.
В нём перехватывается исходный PermissionError внутри owner, затем пробуются
SELECT и повторный commit; `_accept` неожиданно возвращалTrue. Важные
assertions находятся снаружи sanitizing context. Reviewer сам не запускал
тест, прочитал полный немиграционный вывод исполнителя.

Общий предшествующий профиль **486PASS/0skips/1warning/185.86s**, runner191s,
result pass/isolated_container_removed не содержал новой проверки и поэтому
не опровергал найденный дефект. Настоящий источник периода остаётся yieldNone.

## Прочие проверенные границы

Дальнейших P1/P2 при разборе integration области не найдено: exact owned
AsyncConnection INSERT, UUID precharge/conflict0, общий guarded SELECT,
фиксированная account/source последовательность,128SQL и прежние raw/JSON
caps, реальный RR/advisory/shared identity/session/device lock путь,
work/cleanup без нового срока, unknown40001 без retry, in-flight cancellation
и pool handoff согласованы с принятым проектом. Обычная60min600+600 цепочка
проходит без уменьшения fixture:94SQL/1228rows/1224672bytes/1909nodes.
Полная текущая приёмка должна учитывать исправление C1 и его GREEN отдельно.

18 requirement inputs SAME; analyze0252da92 неизменен. Повторный независимый
подсчёт reviewer-owned списков:requirements16/0,security27/0,
privacy-measurement52/0,infra29/0 —124checked/0unchecked; отметки не менялись.
Прежнее собственное чтение оригиналов этого же диалога сохранено.

Т113/runtime/filesystem/receipts/backup/restore/ресурсы, полный HTTP и
maximum envelope, T0/измерение/трафик/продажи, GitHub/выпуск не приняты.
Нового продуктового решения владельца для C1 не нужно. Запись ограничена
этим собственным отчётом; код/spec/plan/tasks/checklists/старые отчёты и
Git/GitHub/runtime не менялись. Тесты/БД/сборки/пробы не запускались.

## SHA-256 исходного замечания и доказательств

| Артефакт | SHA-256 |
| --- | --- |
| Session до исправления | `477d2164b0a44be5498caeea4ff2ac94f6033fc2b8ee6616e2df8e1bd9bfb201` |
| Admission до новой причинной проверки | `dbd174044cf77f1af18eb002fa3463430905bb7673c14078094ff9eb18f3cb09` |
| Admission с причинной проверкой | `71c219be966466c67013b1001b66ef16acedfb2fc803469851f7da9ac3b1877d` |
| `graf-t112-admission-precommit-red-20261116.log` | `3c1a71f090e2d9ed64832c7c124745d9fd24f2c137137fc519b60fc75b0f3997` |
| `graf-t112-admission-owner-accepted-green-20261116.log` | `d4ac1e1bb04a506bdbf77d87278bde914129c8819124dd2328febab1cc74b950` |
