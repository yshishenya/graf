# T112 — повторное независимое ревью владельца Session после R1–R3

16.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Копия `/private/tmp/graf-f273-result-visibility-20261116`.
Основа `f59c1f70ff97d7ac94fd32c330599aa4eed8b889` плюс owned diff.
Полоса: независимое implementation rereview standalone read-only owner
существующей high-risk-product F273/T112. Старые отчёты не изменены.

## Решение и состояние замечаний

**R1, R2, R3 устранены в проверенном коде. Итоговый scoped HOLD:
P1=0, P2=1 — новое замечание R4 о сохранении отказа исходного чтения.**
Это замечание относится к нынешнему read-only owner, не к отсутствующим
admission/HTTP/T113, максимальному envelope или общей Python-песочнице.
Проверенный профиль **75 PASS**, описанный ниже, не содержит случая R4.

## R1 — закрыто

Проверен фиксированный `_ProjectionSession(Session)`: публичный get_bind
сверяет фактическую привязку с исходным sync Engine до её использования.
Публичный connection отдельно проверяет явный bind до вызова super, поэтому
чужая уже начатая nested Connection не успевает выполнить SAVEPOINT.
Фабрики с binds/custom sync_session_class закрываются; свой фиксированный
sync класс задаётся при создании обычного AsyncSession. Явный ORM bind
закрывается до preflight. Динамические bind_mapper/bind_table не обходят
проверку get_bind. After_begin дополнительно проверяет exact Connection.
`_permit` требует ровно один фактический учтённый cursor execution.

Новые тесты проверяют factory/execute/connection/mapper/table routing и
заимствованную nested Connection. Счётчики чужого SQL, состояние владельца
и identity map проверяются вне контекста, который превращает исключения
в общий отказ. Чужая Connection сохраняет nested transaction и затем
выполняет SELECT1. Это устраняет R1 без необходимости поддерживать несколько
привязок и без изменения исходного ORM statement.

## R2 — закрыто

Общий visitor `_bounded_projection` теперь отвергает `node.is_dml` во всём
дереве. Независимые и referenced INSERT/UPDATE/DELETE CTE закрываются до
первого numeric/original SQL. Шесть тестовых случаев после выхода из owner
проверяют ровно2 допустимых SET, пустую identity map, persistent failed и
сохранность исходной строки отдельной сессией. AssertionError счётчика не
может быть скрыт sanitizer owner. Прежний ложный PASS двух INSERT случаев
честно исключён из окончательного причинного доказательства.

## R3 — закрыто

Visitor теперь отвергает `ForUpdateArg.skip_locked` на любом уровне дерева.
Оба теста outer/nested удерживают настоящую блокировку большой строки и
планируют освободить её после numeric preflight. На исправленном коде отказ
происходит до SQL: остаются2 SET, callback освобождения не вызван, большая
модель не загружена, состояние failed сохраняется. Три положительных случая
обычных FOR UPDATE/SHARE/NOWAIT проходят с прежним результатом.

## R4 — P2: перехваченное исключение исходного Q не закрывает владельца

Место: `result_projection_session.py:145–168`, в особенности164–167;
`_permit:82–94`. После успешной `self.budget.check(...)` numeric helper
устанавливает `budget.failed=False`. Затем `state.invoke_statement()`
выполняет исходное Q и driver/ORM decoding. Если здесь возникает исключение,
контроль пропускает checkpoint167. `_permit` в finally лишь очищает
`_expected/_cursor_pending` и не ставит owner/budget.failed.

Внешний `result_projection_session` помечает failed только если исключение
выходит из всего caller context. Reader может его перехватить внутри yield,
как уже предполагают отрицательные тесты failed-state. Тогда при отсутствии
изменений ORM и истечения срока следующий `owner.checkpoint()` и завершение
контекста проходят с обоими failed=False, несмотря на неизвестный исход
исходного чтения. В том же owner допускаются последующие запросы.

Это не требует обхода Session или доступа к частным полям. Пример обычной
ошибки после одобренных агрегатов — исключение JSON codec/result processor:
raw JSON bytes/depth/nodes корректны для SQL JSON, но Python json.loads
отвергает длинное целочисленное значение при стандартном ограничении числа
цифр. Числовые запросы возвращают только count/sum/max и этот JSON не
декодируют; ошибку получает именно original Q. Прочитан установленный
SQLAlchemy2.0.51 asyncpg.py:1184–1206: JSON binary decoder напрямую вызывает
json.loads либо настроенный deserializer. Конкретная текущая настройка
Python integer limit в runtime reviewer не измерялась; само отсутствие
poison при любой ошибке invoke_statement непосредственно видно в коде.

Положение проекта295ce2c требует прекращать фазу при неизвестном исходе,
без refund/retry. Сохранение failed после перехвата reader уже относится
к принятой standalone области. Требуется ставить persistent failed при
неуспехе исходного исполнения/декодирования до передачи исключения reader,
сохранив безопасное поведение отмены. Нужна узкая причинная проверка:
numeric проходит; original действительно даёт ошибку; reader её ловит;
затем checkpoint, новый read и выход owner не могут объявить успех.
Проверки состояния должны находиться за пределами sanitizing context,
как в исправленных R1–R3. Пределы или сам исходный Q менять не требуется.

Это статическое замечание, не результат новой PostgreSQL пробы reviewer.
Текущие75 тестов не содержат перехваченной reader ошибки original после
успешных numeric фаз. Они проверяют persistent numeric refusal и
неперехваченный40001, что не исполняет найденную ветвь.

## Прочитанные источники и доказательства

Полностью прочитаны актуальные Session247 строк, budget170 строк, Session
test554 строки, основной r1-r3 validation135 строк и текущий фрагмент F273.
Неизменный numeric test имеет прежний7b36f0c; собственное полное чтение его
34 случаев сохранено в том же диалоге. Точные хеши сверены независимо.

Финальный журнал прочитан по всем немиграционным строкам: **75 PASS,
0 skips,1 прежний PytestAssertRewriteWarning,27.09s**, runner31s,
`postgres_test_result=pass`, `isolated_container_removed`. Это41 Session
и34 numeric cases. Основной исполнитель сообщил terminal session64450 EXIT0;
reviewer не опрашивал эту terminal session и не запускал тесты. В журнале
нет собственного source-hash manifest; связь с точными файлами — подтверждение
исполнителя плюс нынешние суммы, не новый exact-SHA GitHub CI.

| Обычный полный путь | SQL | Rows | Raw bytes | JSON nodes |
| --- | ---: | ---: | ---: | ---: |
| Общий review | 56 | 1212 | 1214494 | 1263 |
| Fresh bindings | 67 | 1216 | 1221872 | 1870 |

Сохранены600+600 сегментов, настоящие default pinned итогиv2/transcriptv3,
JSON, календарь/roster и previous meeting. Полный ответ равен исходному reader.
Разница67 против прежних71 SQL объясняется динамическими учтёнными SET
остатка времени; статического контракта «ровно71» нет. SQL128 и прочие
caps не повышены. Время pytest case включает fixture/control read, оно
не выдаётся за отдельное измерение всего POST или максимального envelope.

Прочитаны конкретные failure/summaries окончательного causal RED14 и
borrowed-savepoint RED1. RED14 на исходных blobs f59 показывает14FAIL,
27deselected,8.24s. Он **не имеет наблюдённого terminal runner EXIT** после
прерывания родителя и не принимается за штатное EXIT1/cleanup. При этом
конкретные pytest failures остаются доказательством отрицательных случаев;
исправленный окончательный код заново прошёл отдельный завершённый GREEN75.
Предыдущие11FAIL/2PASS и GREEN71 не подменяют окончательные результаты.

Recovery metadata прочитаны полностью: missing unified handle, runner_exit
not_observed, точный собственный tmpfs container, отсутствие mounts,
отдельная очистка exact ID и восстановленные source/budget hashes. Эти
действия являются сообщением основного исполнителя и его receipt; reviewer
не проверял Docker runtime заново. Borrowed nested RED отдельно содержит
SAVEPOINT/ROLLBACK TO SAVEPOINT до after_begin и1FAIL,40deselected,
4.37s/runner9s/cleanup removed. Исправление перенесено до super.connection.

## Требования и оставшиеся границы

18 requirement/review inputs снова SAME. Reviewer-owned totals неизменны:
requirements16/0,security27/0,privacy-measurement52/0,infra29/0 —
**124 checked/0 unchecked**. Собственное чтение применимых оригиналов
того же диалога сохранено; вновь прочитано целое положение проекта295ce2c
о прекращении фазы/перехвате/unknown. Analyze0252da92 не менялся. R4 не
требует нового продукта, цели сбора, права, срока хранения или поднятия caps.

Прежний HOLD e1911713 сохранён. Source query не переписывается, общего
упрощённого reader нет. Admission с двумя INSERT/commit, readiness/fresh
legal/identity/session/source/deletion/writer fences, HTTP/proof/renewal,
максимальный envelope, остальные cleanup неисправности и вся T113 открыты.
Они не включены в число замечаний этого rereview. Прямой произвольный
asyncpg/DBAPI Python доступ не объявлен поддержанной песочницей.

Записан только настоящий новый отчёт. Код/tests/spec/plan/tasks/checklists,
Git/GitHub, runtime/БД/данные, сайт, Postal/соседние службы, сбор/IP/T0,
публикации и выпуск не менялись. Тесты/сборки/пробы, новые агенты и
межчатовые сообщения не запускались. Чужие изменения сохранены.

## Контрольные суммы

| Артефакт | SHA-256 |
| --- | --- |
| Session source | `91ed6b69a853449f15b5d887a82ca014e88067571564c8ed22ac7b13beaa0648` |
| Numeric budget source | `f4de665d1329085a320de268445ace87c886ed08febc387cfd4df65e7c0ea718` |
| Session test | `f2ac14ccf330335c46780d5bf68351e20ff43fc10470b4c8a1bef0889024c6c2` |
| Numeric test | `7b36f0c99cee98af4b867f05bd01ab2117ed589b0dbb8b8cc35531986ce9828a` |
| F273 fragment | `ff0d470097faf0bdcf51c2d090db211aa1949962f4a53960755ead8662db4c47` |
| Основной r1-r3 validation report | `9be100aee651c48b83f96f89ecc9d62f85eaa17a132e750f7ac91279f5a7fe99` |
| Старый независимый HOLD | `e191171386080b31f2db39cb6f02b23d3897845bbe5165216736b45e6f4a75c6` |
| Final GREEN75 log | `0ad0248794140cdcbbc5832d59123c61a91b713f8bde75ec1a489cd31c178749` |
| Interrupted causal RED14 log | `190531d1dfcd3c024a2f2eef88435bed457156ea5364de4293cbde8847d9979b` |
| Borrowed-savepoint RED1 log | `7c1780f24452775c570e60c4287a7009b535b960c826571a67cee41dfed5a913` |
| Interruption recovery metadata | `b81259ddc4abd048456a178b6a4f47bb0b02b79964fb5bb1428a8bb9e4f3984a` |

## Привязка к коммиту при завершении ревью

При завершающей read-only сверке родитель уже сохранил R1–R3 в коммит
`45c068813ed7bdadbe5e90ab82b48cab0f28b1c9`. Source/budget и оба test blobs
этого коммита соответствуют приведённым выше проверенным SHA-256.
В рабочем Session test одновременно появился чужой незакоммиченный тест
для R4 (SHA-256 файла `a39d6f250f03c6475dd281e04a794aedab0fca7173ab8410db699fbd75a696bc`).
Он не входит в завершённое GREEN75 и не принят настоящим ревью как
доказательство исправления R4. Изменение сохранено без вмешательства.
Настоящий HOLD остаётся привязан к проверенным R1–R3 blobs; удалённые
проверки GitHub, CI и выпуск этой сверкой не подтверждаются.
