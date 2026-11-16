# T112 — независимая приёмка корреляции checkin по checkout

16.11.2026. Проверяющий `/root/public_counter_readiness_review`; рабочая копия `/private/tmp/graf-f273-result-visibility-20261116`, HEAD `3b1c23e7a85a77b8861ae18ed174232835587a32`. Существующая F273/T112/#7698,T113/#7804, `high-risk-product`. Точное поручение прочитано из `/private/tmp/graf-t112-ordinary-raw-checkin-review-request-20261116.txt`. Разрешено записать только этот новый отчёт; старые отчёты, код/tests/spec/plan/tasks/checklists и чужие изменения сохранены. Git использован только для чтения; тесты/сборки/службы/production не запускались и не изменялись.

## Решение

**SCOPED IMPLEMENTATION PASS для поправки checkout-корреляции; P2-01 закрыт, P1=0/P2=0 в этой узкой области.** Наблюдение больше не подавляет повторные checkin одной аналитической выдачи. Законченный адресный2PASS подтверждает текущий source, порядок invalidate→checkin(None), DBAPI identity, прежние M1/cleanup/F/B и явный следующий POST.

**Общий implementation HOLD остаётся по неизвестной причине первоначального repeated unavailable.** Его адресный и общий последующие PASS не объясняют. Этот отчёт не закрывает T112/T113/T098/T0 и не разрешает выпуск T112. Отдельная пауза master для уже опубликованного выпуска Метрики снята; старое утверждение об этой паузе не переносится на текущее состояние. Настоящий T112 period остаётся закрытым; это не утверждение, что вся публичная Метрика выключена.

## Точный diff и неизменённые входы

Прочитан полный diff integration между `50c9ecab6586a39650e78039775311278a7d2ba9` и текущим HEAD: **9 добавлений /5 удалений**, только новый native test. SHA-256 точного stdout этого diff `324124909d7ddf083c59c0671801ba0311415e18aaa02dd41b2adbce0adf5ec3`. Budget не менялся. Рабочий diff двух тестовых файлов к HEAD пуст: рассматривается именно сохранённый кандидат.

Изменения ограничены списком несжатых returns, фиксацией checkout ordinal при настоящем аналитическом Engine.commit, записью каждого target-entry checkin с его ordinal, фильтром markers по аналитическому checkout вместо наличия прежнего marker, count==1 до B и безопасным выводом числовых offsets. Имеющиеся M1/SQL/caps/deadlines/native/Session/Pools/fixtures/provider запреты и ожидания следующего POST сохранены.

Все apps/server/src и changes побайтово совпали с исходным checkpoint `237d368b94c61908f853262ec1be545504951dc8`. Прочитаны текущий тест, прежний собственный rereview и авторский `t112-ordinary-return-checkout-validation-20261116.md`, включая последующее уточнение опубликованной Метрики. Старые решения сохранены как история, а не переписаны задним числом.

| Вход | Проверенный SHA-256 |
| --- | --- |
| Текущий integration | `1a3267352ff6b838daa153f5dacc105a98eaed29d57a930f8e244ecf8229daa0` |
| Неизменённый budget | `f12c96159912479d5fc3c59a00bd5df0eccc944486b4900df9b7edebf72f5eb7` |
| Авторский checkout-validation | `f6fe3bbe14b50a4aa7f497908ac9d06a1653260909f1b40931122d2a3e8db6a8` |
| Прежний собственный rereview | `4618fe7668ef0feef4732cda697049827c4ac82d9d5e4d02b448ab41777ab5f7` |
| Прежний implementation review | `d537d25dd8185c792eb5450e0faee531634434b39bc7bc2c85a33efe7cbff924` |
| Принятый design | `04f10392b802ffd769dcd95324de4f1070f125ac29385f121547475611ad9c6f` |

## Почему корреляция устраняет P2-01

1. Public checkout callback уже сохраняет entry/DBAPI/native driver/Context owner и увеличивает список checkouts. В точном аналитическом COMMIT запоминается его текущая длина. Это событие связано с настоящими ResultAdmissionSession/root/lease/task/DBAPI/driver, а не с произвольным commit auth/renewal.
2. После entered каждый checkin **точного target entry** попадает в raw returns независимо от наличия прежнего marker. Пока ordinal равен зафиксированному на COMMIT, каждый такой checkin также попадает в markers. Второе событие до следующего checkout поэтому даст count2 и провалит assertion; прежнего first-marker подавления нет. Это проверка логики collector по исходнику, не заявление о запуске искусственного отрицательного теста.
3. Граница ordinal обоснована устройством именно этого опыта: F непрерывно удерживает другой слот request pool; observer использует отдельный engine; F SELECT/commit не возвращают его в pool. Поэтому до B новые request-engine checkout относятся к свободному T entry. Один глобальный ordinal здесь однозначен; он не предлагается как универсальный коррелятор для произвольного конкурентного пула.
4. Fault в ранней точке проверяет ровно один invalidate, ровно один checkin той же выдачи, порядок и returned_dbapi=None. Перед B count==1 проверяется повторно для normal/fault, в исходном hard budget и до gate.set/teardown. Чужие законные выдачи не превращены в дубли аналитической операции.
5. При B сохранены exact T entry, пустые owner keys/Context, DBAPI/native/PID normal same и fault different. Старое fault поколение/relay/backend уже завершены до этого; owner tasks/registries пусты. Поэтому последующая новая выдача не заменяет доказательство окончания старой cleanup. B/F проверки до и после gate.set и следующий отдельный POST сохранены.

Оставшееся подавление reset после первого checkin относится к ранее принятому normal reset marker; оно не подавляет raw checkin. Все эти callbacks синхронно наблюдают public events, не запускают native методы, не создают await или искусственный отказ приложения.

## Прочитанные законченные результаты

| Опыт | Фактический результат | SHA-256 журнала в `/private/tmp/` |
| --- | --- | --- |
| `graf-t112-native-commit-raw-checkin-20261116.log` |2FAIL/56deselected,9.92s pytest/16s runner,EXIT1; normal count2, fault invalidate1/checkin2; isolated_container_removed | `ef4c38ea9f869ee5ec7c13adb3a8717d3b8d982e3903381c1bc2a2edf689ca80` |
| `graf-t112-native-commit-checkout-window-20261116.log` |2PASS/56deselected,10.30s pytest/15s runner,EXIT0; isolated_container_removed/resultpass | `aae40ec23e0989343af25e53e407cbc9b01ca4fa772001a9dc8695a8255b3bfe` |
| `graf-t112-unknown-post-chain-20261116.log` |87PASS,150.37s pytest/155s runner,EXIT0; прежний64b6abed с временным observer; isolated_container_removed/resultpass | `0b668de206529d98088bea9d1352f4249554ec1f4d62d3653f622cea7930de19` |

EXIT значения получены из актуального поручения исполнителя; в законченных журналах самостоятельно прочитаны итоги/cleanup/result markers и конкретные causal/failure строки. В адресных2PASS normal0.720s/fault1.554s, watchdogFalse, foreign/reuseTrue; M1 faultTrue и старое поколение закрыто только fault. Оба следующих POST и сравнения полных saved rows прошли. Один прежний PytestAssertRewriteWarning, без skipped; deselected56 указан явно.

Raw offsets в обоих успешных случаях `[0,1]`: первый возврат соответствует аналитическому checkout, второй — уже следующему checkout. Это причинно объясняет, почему простое число возвратов slot2 не равно двум checkin одной выдачи. Прежний2FAIL сохранён и не объявлен runtime-дефектом. Настоящий session_renewal_middleware и его регистрация в `_setup` перечитаны: после handler действительно возможна другая DB Session в том же pool, однако **точный caller второго возврата отдельно не установлен**; происхождение именно из renewal не утверждается.

Полный87PASS относится к прежнему64b6abed и не выдаётся за полный прогон нового1a326735.87 и2 не складываются. Для принятия этого узкого изменения collector достаточно исполненных двух изменённых случаев на неизменных runtime/fixtures; оснований повторять завершённые87/312 здесь не найдено.

## Неизвестный repeated отказ остаётся отдельным вопросом

Chain-диагностика записала normal POST1/POST2 accepted; fault POST1 unavailable и POST2 accepted. Её цепочка ProjectionBudgetExceeded (`_result_session_context:382`) → TimeoutError (`timeouts.__aexit__:116`) → CancelledError (`protocol.query:369`) относится **только к намеренно задержанному первому COMMIT**, не к первоначальному repeated unavailable. Причина исторического второго отказа не воспроизведена и не установлена; timeout/нагрузка/lock/TTL/утечка не приписываются ему без доказательства.

Временный observer этой законченной диагностики оборачивал базовый `_refuse` и boundaries только нового native test; это не ранее предложенный новый Python call/exception trace без замены методов. Его копия сохранена вне дерева: `/private/tmp/graf-t112-unknown-post-observer-20261116.py`, проверенный SHA-256 `66f44ab4f1f38261aca3df3342cce0aab8097f0144e190fac7026df7e0387cd5`. Новый trace-опыт не выполнялся. Существующие отчёты/адресный результат не принимают за реализацию этого проекта. Новые диагностические циклы и runtime fix этим ревью не требуются и не выполняются.

## Требования и текущее состояние выпуска

Повторная сверка18 `unchanged_inputs` карты `/private/tmp/graf-t112-root-history-reading-20261116.json` дала **18SAME**. Применимые reviewer-owned checklists перечитаны для подсчёта, не менялись: requirements16/0, security27/0, privacy-measurement52/0, infra29/0 — **124checked/0unchecked**. Analyze `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` остаётся применим к прежним FR-021/025/SC-006; нового поведения сбора/хранения/получателя нет. T112 deadlines2s/work1.5s/cleanup0.5s, SQL128, lock250ms, statement500ms и запрет автоматического retry неизвестного COMMIT сохранены.

По актуальному поручению и последующему разделу validation автора отдельная пауза master снята; опубликован `v2026.11.16.1`/`d03114b6ade9750154186cc6bedffe2235921628`, Full13jobsPASS подтверждены задачей выпуска/чтением автора. Проверяющий этого отчёта заново GitHub/release/runtime/provider не проверял. Deploy/health/ответы Метрики и ограничения Webvisor/T121 относятся к сведениям задачи выпуска, а не к независимым production-проверкам здесь. Их нельзя выдавать за приёмку T112 либо новые внешние визиты/продажи.

Итог: **P2-01 CLOSED, P1=0/P2=0 для checkout-поправки; unknown repeated HOLD OPEN.** Настоящий `_result_period_context` T112 закрыт; состояние всей публичной Метрики этим не определяется. Postal сохраняется. T098/T113/restore/T0, остальная ручная/native T112, коммерческие критерии и общий допуск этого T112-кандидата остаются открытыми. Прежняя история freeze/collection off в старых отчётах не переписана; текущие границы уточнены здесь.
