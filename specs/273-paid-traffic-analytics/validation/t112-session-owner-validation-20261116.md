# T112 — отдельный владелец сессии проверки результата

16.11.2026. Основа: `3fd1de03b342d85537784db98b213dfc1553edbd`.
Полоса: существующий `high-risk-product`, `$speckit-implement`, F273/T112.
Legacy Impact: untouched. Это локальный кандидат отдельного владельца
**только для чтения**, не приёмка полного admission/HTTP/T113.
T112/T113 и #7698 остаются открытыми; GitHub подтвердил #7698 OPEN.

## Реализовано

`cabinet/result_projection_session.py` создаёт собственную AsyncSession из
штатного async_sessionmaker, привязанного к AsyncEngine. Чужая Session или
фабрика с начатым AsyncConnection не принимается. Autoflush выключен;
исходная identity map, транзакция и tenant context должны отсутствовать.
REPEATABLE READ выбирается до первого tenant/readiness SQL.

Session-local `do_orm_execute` вызывает уже принятый ProjectionReadBudget
до неизменного исходного statement. Проверяются execute/scalar/scalars/get;
кэш get содержит лишь ранее проверенный объект этой свежей сессии.
Числовые фазы получают фактический Select и параметры; aliases и форма
исходного результата не переписываются. Перехватчики Connection
before_execute/before_cursor_execute допускают только конкретное выполняемое
выражение и отклоняют прямые SQLAlchemy Connection.execute/exec_driver_sql.
Это не изоляция от произвольного Python-кода, напрямую использующего asyncpg;
таких вызовов в проверенном штатном reader нет.

Общий счётчик ограничен128 фактическими cursor executions: управляющие SET,
tenant SELECT, обе числовые фазы и исходные чтения. Это не128 логических
ORM-чтений и не счёт всех низкоуровневых сообщений протокола PostgreSQL.
Разрешён только конкретный tenant SELECT общего apply_tenant_context,
структурно сверенный с ожидаемыми настройками двух используемых контекстов.
Произвольного разрешения raw SQL/set_config нет. Записи, commit, streaming,
неподдержанные формы и попытки продолжить завершённый снимок закрываются.

Один абсолютный срок2s включает резерв0.5s для очистки. Перед выполнениями
и после них проверяется остаток; statement timeout≤500ms и уменьшается
по остатку, lock timeout250ms. Все новые SET входят в128. Checkpoint после
синхронной материализации/canonical/digest обязателен для будущего caller.
Неизвестный исход числовой фазы закрывает владельца даже после перехвата
исключения самим reader. Пределы размера/строк/JSON не повышались.

Listeners снимаются в finally до возврата соединения в пул. close ожидается
непосредственно, без shielded фоновой задачи. При timeout завершается только
ещё принадлежащее владельцу точное соединение, затем invalidate. Закрытое,
invalidated или уже переданное другому владельцу соединение не завершается
по сохранённой ссылке. Это отдельно проверено на одном физическом driver.

## Проверки

Штатный focused PostgreSQL runner, только синтетические записи. Перед
запуском на Mac было129GiB свободно. Свой временный контейнер удалён.

| Профиль | Завершённый результат |
| --- | --- |
| Первый новый профиль | 5 FAIL/10 PASS; найден неперенесённый failed state числового компонента |
| После исправления failed state | 14 PASS/1 FAIL; ошибка тестового пути previous_recurring_meeting, не отказ runtime |
| Расширенный профиль | 18 PASS/1 FAIL с тем же неверным путём тестовой проверки |
| После исправления пути и полной source-ветви | 20 PASS/0 skips,12.58s,runner17s |
| Streaming/same-pool/stuck-close | 23 PASS/0 skips,14.45s,runner19s |
| Проверка смены владельца | 24 PASS/0 skips,15.36s,runner20s,EXIT0 |
| Окончательный файл с настоящим default pinned slot | **24 PASS/0 skips,17.52s,runner22s,EXIT0** |

Во всех профилях один прежний PytestAssertRewriteWarning. Initial/complete/
expanded не выдаются за причинный RED отсутствовавшей реализации.
Финальный журнал:
`/private/tmp/graf-t112-projection-session-pinned-final-20261116.log`.
Session77922 терминально завершена; не опрашивать и не перезапускать.

Отдельный причинный RED failed state: из текущего кода временно убрана
только проверка budget.failed в checkpoint. Текущие пять выбранных случаев
дали **5 FAIL с DID NOT RAISE**,18 deselected,4.91s,runner9s,EXIT1.
Журнал `graf-t112-projection-session-closed-state-red-20261116.log`.
Исходник восстановлен в finally к module20bc8a9, принятому локальным GREEN23.
Следующее изменение только очистки дало нынешний module0a7cd26; пять
отрицательных тестовых случаев не менялись.
Это контрпример конкретного найденного дефекта нового владельца, а не
доказательство RED на всём историческом пути без владельца.

Второй причинный RED: временно убрана только проверка действующего владения
соединением перед terminate. Настоящий single-connection pool передал его
другой Session; старый код завершил чужое соединение, проверка получила
InterfaceError underlying connection is closed:1FAIL,23deselected,4.74s,
runner9s,EXIT1. Журнал released-close-red; контейнер удалён, module0a7cd26
восстановлен в finally. Финальный GREEN24 проверяет живую replacement Session.
Отрицательная проверка после этого не менялась; затем только усилен
положительный60мин fixture настоящим закреплённым default slot.

Положительные проверки не ограничены одним transcript reader:

| Полный штатный путь | SQL | Строки | Исходные байты | JSON nodes |
| --- | ---: | ---: | ---: | ---: |
| get_cabinet_meeting_review | 56 | 1212 | 1214494 | 1263 |
| load_fresh_result_view_bindings, включая Meeting fence и source | 71 | 1216 | 1221872 | 1870 |

Fixture:60мин,600 transcript/600 diarization segments, JSON provenance,
четыре участника календаря, настоящая предыдущая30мин встреча с результатом,
текущая расшифровка v3 и принятые итоги v2 через настоящий default
MeetingSummarySlot. Оба точных result_id и outcome_set_id проверены явно. Профили сравнивают полный
ответ/набор binding с тем же исходным reader без защиты. Calendar/previous/
grants/roster ветви не выключены, отдельный упрощённый reader не добавлен.
Поле previous находится в calendar_context_detail; раннее ошибочное обращение
к корню модели было исправлением теста, без изменения продукта ради PASS.

Настоящие PostgreSQL проверки: FOR UPDATE внутри числового preflight ждёт
не более lock timeout и не загружает ORM; concurrent UPDATE после RR snapshot
даёт ровно один40001 без retry. Проверены128 executions, параметры и duplicate
labels, empty/scalar/scalars/get/cache, raw/control/write/commit/stream refusal,
отмена, отсутствие surviving tasks и сессий в проверенных сценариях,
очистка listeners и повторное использование того же физического соединения.
Синхронная задержка после чтения обнаруживается checkpoint до принятия.

## Независимое ревью и открытые работы

Перед кодом существующий reviewer заново подтвердил применимость проекта
295ce2c и требований:18 входных хешей SAME, requirements16/0,security27/0,
privacy52/0,infra29/0=124/0. Analyze0252da92 неизменен. Применимые оригиналы
восстановлены по document-reading в том же диалоге; карта чтения находится
в `/private/tmp/graf-t112-root-history-reading-20261116.json`.

**Независимая проверка точного нового кода ещё не получена.** Читаемый запрос
подготовлен в `/private/tmp/graf-t112-session-owner-review-request-20261116.txt`;
его доставка/новый FINAL не подтверждаются одним наличием файла.
Файлы требований и reviewer-owned отметки не менялись. Старые отчёты numeric
HOLD/PASS сохранены. Ошибочные wait без живого cell ID не были ожиданием
ревью или проверкой среды и не использованы как доказательства.

Полный admission owner с filesystem/DB readiness fences, общей транзакцией
двух INSERT/commit, fresh legal/session/source/deletion/writer fences,
HTTP/auth/renewal/proof, максимальным допустимым envelope и всей T113 остаётся
открытым. Изолированный60мин fixture не доказывает максимальную нагрузку
или каждую сетевую/checkout/TLS/commit/cleanup неисправность.
Этот read-only владелец не подключён к продукту и ничего не сохраняет.
`_result_period_context` по-прежнему yield None.

Контент/вёрстка, Postal и соседние службы, nginx/DNS/Compose, рабочие БД,
очереди/письма/backups, настройки сбора/IP, T0 и внешние публикации не менялись.
PR/merge/выпуска нет. Новых подтверждённых визитов/регистраций/оплат нет.

## Контрольные суммы

| Файл | SHA-256 |
| --- | --- |
| result_projection_session.py | 0a7cd26ea864df12b498bf044015f34b328bf96c7c46ade1ee79b0c44b9b3c3e |
| test_result_projection_session.py | c071b26d044c377dd960e7ad706f66eb3d3864b4b3788877c954f384ecaa3bcd |
| F273.yaml | b027bcbf7ee98a5fb889eb4e69cc28535eaf2f6c994c2eb1e6479a215842667c |
| final GREEN24 log | f2f34fc9521b03825ef5e4eed57ba83f9bb2efdecb436d2f73253cf71dbf0fcc |
| failed-state RED5 log | 55980bf6b67096a607b50c9db12fd72b40a629408deb8bee0f4f6bee40e07b2f |
| released-connection RED1 log | b34ae851486bebcf52aa0b2d90bbb6d4f84657322518e6bc09a375ff03a21244 |
