# T112 — устойчивый отказ после ошибки исходного чтения, R4

16.11.2026. Основа `45c068813ed7bdadbe5e90ab82b48cab0f28b1c9`.
Существующая F273/T112, полоса `high-risk-product`, `$speckit-implement`.
Legacy Impact: untouched. Это изолированный компонент, не выпуск.

## Основание и исправление

Получено и полностью прочитано независимое
[повторное ревью](t112-session-owner-rereview-20261116.md): R1–R3 закрыты,
HOLD P1=0/P2=1, R4. SHA-256 отчёта:
`1429a48947347e85d159e24cbb49de3787633bbc8da5d90564beabd7f592fa95`.
Ранее прочитанная промежуточная сумма59064e заменена окончательной суммой
после завершающей записи reviewer; это не разные результаты ревью.
Предыдущие HOLD и основной отчёт R1–R3 сохранены без изменения.

После успешных числовых фаз original SQL/JSON decoder мог выбросить ошибку.
Если reader ловил её внутри owner, внешний обработчик не видел исключения:
checkpoint, новое чтение и нормальный выход оставались разрешены.
Минимальное исправление в общем `_permit`: при `BaseException` сначала
установить оба `failed`, затем повторно выбросить исходное исключение.
Отмена не превращается в обычную ошибку; finally продолжает очищать разрешение
исполнения. Все четыре callers `_permit` остаются на общей проверке.
Новых настроек, зависимостей, пределов или запросов нет.

## Причинная проверка

Три параметризованных случая используют настоящий стандартный Python limit
длины целого. В изолированной PostgreSQL хранится синтетический JSON integer
с limit+1 цифрами. Raw bytes/depth/nodes проходят; исходный `db.get` вызывает
настоящий `ValueError` JSON decoder. Reader перехватывает его внутри owner.
Затем отдельно проверяются checkpoint, следующее чтение и выход.
Проверки состояния и числового расхода находятся вне sanitizing context.

| Версия | Результат |
| --- | --- |
| Точный исходный source45c068813, новые3 случая | 3FAIL/41deselected,4.87s,runner9s,EXIT1; isolated_container_removed |
| Исправленный source, весь Session-файл | **44PASS/0skips**,21.05s,runner25s,EXIT0; isolated_container_removed |

RED получен из настоящей terminal session19573; повторно не запускался.
GREEN завершился в session95333. В обоих запусках один прежний
PytestAssertRewriteWarning. Перед проверкой доступно124GiB на Mac.
При исправлении Session исходники/34 теста numeric не менялись;
их прежний результат из GREEN75 не объявляется новым запуском78 тестов.

| Обычный полный reader в GREEN44 | SQL | Rows | Raw bytes | JSON nodes |
| --- | ---: | ---: | ---: | ---: |
| review | 56 | 1212 | 1214494 | 1263 |
| fresh bindings | 71 | 1216 | 1221872 | 1870 |

Полный ответ равен исходному reader:600+600 сегментов, JSON, календарь,
предыдущая встреча и настоящий default pinned outcomev2/transcriptv3.
Динамические SET остатка срока учитываются;71 против67 в прежнем запуске
не означает изменения контракта. Предел128 SQL не повышен.

## Ворота и границы

18 входов SAME, scoped analyze0252da92 неизменен, prerequisite PASS;
requirements16/0,security27/0,privacy52/0,infra29/0=124checked/0unchecked.
Reviewer-owned отметки не менялись. Применимые оригинальные положения
unknown/refund/retry и общего срока перечитаны; новых требований нет.
Before/after implement hooks отключены. T112/T113/#7698 открыты.
Ruff и diff PASS. Повторная независимая проверка R4 ещё ожидается.

Полный admission/два INSERT/commit, trusted readiness и свежие identity/
session/legal/source/deletion/writer fences, maximum envelope, HTTP/proof/
renewal и остальные cleanup исходы остаются открытыми. `_result_period_context`
по-прежнему yield None. Нет общей Python-песочницы от прямого DBAPI доступа.
Postal, соседние службы, рабочие настройки, сайт/контент/вёрстка, сбор/IP/T0,
публикации, backup/restore не менялись. Новых подтверждённых визитов,
регистраций или оплат нет. PR/merge/CI/release не запускались.

## Контрольные суммы

| Артефакт | SHA-256 |
| --- | --- |
| Session source | 95108da96f1df0c479ad402cc80a563382049f395d276c5976499a8a67874dc8 |
| Session test | a39d6f250f03c6475dd281e04a794aedab0fca7173ab8410db699fbd75a696bc |
| Numeric source, без изменения | f4de665d1329085a320de268445ace87c886ed08febc387cfd4df65e7c0ea718 |
| Numeric test, без изменения | 7b36f0c99cee98af4b867f05bd01ab2117ed589b0dbb8b8cc35531986ce9828a |
| RED log | 1f375d1494dae02e384a75d351f94516729428c6b54f19fe9640098fb44f1ceb |
| GREEN log | 659f273e5c2eb22adc9f537b0ad967d829ce26f918feb4e8d3aafc24f6756bf1 |

Журналы вне Git: `/private/tmp/graf-t112-session-r4-{red,green}-20261116.log`.

## Полученная независимая приёмка

После сохранения исходного отчёта в `adb0329159ac495a13e129483762bdf08a06bd62`
полностью прочитан [новый независимый отчёт](t112-session-owner-r4-review-20261116.md),
SHA-256 `24cd545cbae2f5fec61856b2252731d8ec943144c0d10f4a5a5574dcb7b38d78`.
Итог **scoped PASS, P1=0/P2=0; R4 закрыт**. Exact source/test/numeric/log
хеши совпали; код и тесты после GREEN44 не менялись. Reviewer проверил
исходный основной отчёт с SHA1e35fbf6 до настоящего дополнения. Отметка об
ожидании выше описывает предыдущий этап, а не текущее состояние.

Отдельно подтверждено ограничение доказательства отмены: существующий тест
отменяет reader после SQL; прохождение BaseException именно внутри нового
обработчика проверено статически. Нового in-flight cancellation опыта нет.
Это не замечание текущего scoped review и не доказательство остальных
cleanup/failure исходов. Полные T112/T113 и ранее перечисленные границы
остаются открытыми. Tests/CI/release повторно не запускались.
