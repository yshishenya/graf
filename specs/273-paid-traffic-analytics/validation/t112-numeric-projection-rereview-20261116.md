# T112 — повторное независимое ревью числовой проекции после N1

16.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Копия `/private/tmp/graf-f273-result-visibility-20261116`.
Точный проверенный HEAD: `78744cd6bf8a066201271ee3a1ec36b84be6c559`.
Исходное рабочее дерево чистое. Основа13fde из текстового request историческая;
новый запрос основного исполнителя явно назначает нынешний78744cd6b.
Полоса: независимое implementation rereview существующей high-risk-product
F273/T112, только числовые raw-byte/raw-shape фазы.

## Решение

**SCOPED PASS для точного числового компонента: P1=0, P2=0; N1 устранён.**
Прежний HOLD `8deb1db8…` остаётся без изменений и относится к первоначальным
module15bdeda/test45d6358. Нынешнее заключение принимает module3017498c и
test7b36f0c с новым завершённым профилем34, не переносит прежний31 PASS.

Это завершение отдельного числового компонента. Полная граница Session,
RR/interception/bypass/control permissions/SQL128/2s/locks/freshness/cleanup,
HTTP, T113, рабочий сбор, T0 и выпуск данным PASS не принимаются. T112/T113
и #7698 остаются открытыми; компонент пока не вызывается продуктом.

## Исправление N1

Полностью самостоятельно прочитаны нынешний модуль167 строк, тестовый файл
368 строк, фрагмент F273 и новый основной validation report. Сверены exact
SHA-256; старый независимый HOLD сохранён с прежней контрольной суммой.

В `_field_bytes`, Numeric-ветка теперь вычисляет
`octet_length(pg_catalog.numeric_send(column))` вместо константы из
`precision/scale`. Измеряется настоящее значение выбранной expression в
двоичном PostgreSQL numeric формате, включая его заголовок и группы цифр.
Наследуемые метаданные SQLAlchemy и отсутствие p/s больше не подменяют
фактический размер. Квалификация `pg_catalog` фиксирует используемую функцию.
SQL NULL по прежнему CASE даёт0; Float остаётся в отдельном фиксированном
scalar envelope. Число/его текст/двоичное тело не возвращаются в Python:
возвращаются только count/sum/max агрегаты размера.

Numeric send соответствует измеряемому двоичному значению PostgreSQL,
которое декодирует используемый asyncpg. Дополнительно прочитан установленный
SQLAlchemy2.0.51 `dialects/postgresql/asyncpg.py:319–346`: native decimal
результат не переводится dialect в иной строковый транспорт; его connection
codec setup явно настраивает JSON/JSONB и не заменяет numeric строковым
codec. Это подтверждение выбранной границы transport size, не гарантия
размера Python Decimal/heap или времени его декодирования.

Общие `_size_query` и резервирование расхода не изменены: фактическая длина
Numeric входит в каждое выбранное поле/повтор, max field/max row и cumulative
raw_bytes до выполнения исходного reader. Поэтому прежнее занижение N1
устранено и для выражений, и для aliases. Исключения SQLAlchemy по прежнему
дают общий отказ; состояние заранее закрывается при неизвестном исходе.

## Новое причинное доказательство

Прочитаны начало RED, оба конкретных failure traceback и окончательная
сводка. Большой блок вывода миграций не выдаётся за самостоятельное повторное
ревью всех миграций. GREEN34 прочитан полностью. Новых запусков reviewer нет.

| Профиль | Проверенный результат | Что доказывает |
| --- | --- | --- |
| two-red | 2 FAIL,32 deselected,1 прежний warning,4.07s; runner8s; cleanup removed | Оба настоящих контрпримера дошли до `pytest.raises` и получили DID NOT RAISE на старом расчёте |
| complete34 | 34 PASS,0 skips,1 прежний warning,11.68s; runner16s; result pass; cleanup removed | Исправленный целый нынешний тестовый файл, включая три новых случая и прежний raw JSON профиль |

Первый контрпример использует обычный `coalesce`: metadata Numeric(1,0),
но фактическое число имеет50000 цифр;22 выбранных повтора превышают512KiB.
Второй использует семь квадратов1000-значного числа через последовательные
CTE: metadata остаётся Numeric(1000,0),9 повторов128000-значного результата
превышают тот же row cap. До guard оба теста получают только числовую длину
`numeric_send`, подтверждают `wire_bytes * repeats > 512 * 1024` и проверяют
унаследованные p/s. Поэтому RED не объясняется неверным fixture type или
компиляцией и действительно воспроизводит N1.

На старой реализации оба отказа отсутствовали. Новый GREEN подтверждает
отказ через `ProjectionBudgetExceeded`, закрытое состояние и отсутствие ORM
identity-map objects. `_check` превращает SQLAlchemy compile/DB ошибку,
оставшуюся как exception context, в отдельный AssertionError; такая ошибка
не может незаметно дать ложный положительный `pytest.raises`.

Новый положительный тест отдельно проверяет точное совпадение raw_bytes с
двоичной длиной SQL NULL, нуля, дроби и большого scale. Неограниченный
Numeric здесь корректно измеряется, а не отвергается из-за отсутствия p/s.
Операция не загружает сам числовой результат для вычисления размера.

Тесты используют прежние изолированные `_run/_prepare` и transactional Probe
Table. Результаты первых неудачных numeric-wire fixture итераций в main
report явно отделены от two-red; они не использованы как причинный RED N1.
Основной исполнитель сообщил terminal session52181 EXIT0 для complete34.
Reviewer читал завершённый журнал, не опрашивал эту terminal session и не
запускал runner. В журналах нет собственного source-hash manifest: их привязка
к конечным файлам основана на подтверждении исполнителя и нынешней точной
сверке. Это не новый exact-SHA GitHub CI или доказательство remote readback.

## Повторно проверенная область остального компонента

Полный нынешний код сохраняет уже разобранные numeric phases: исходный
SQL JSON UTF-8 до JSONB-нормализации, JSONB version byte, String/Text/bytea,
фиксированные известные scalars, cap+1 фактического Select с его binds,
подсчёт каждого поля/alias и отдельный raw duplicate-preserving JSON обход.
Depth/nodes ограничены32/65536 с отказом через cap+1. Расход rows/bytes/nodes
суммарный, неизвестность навсегда закрывает экземпляр. Raw SQL, TypeCoerce,
literal columns, неподдержанные функции/типы, mapped relationships и явное
streaming закрываются; исходный ORM запрос не выполняется/не переписывается.
Новых обязательных дефектов в этой согласованной области не найдено.

GREEN34 заново включает Unicode, SQL NULL/JSON null, duplicate keys,
shadowed early depth/nodes, whitespace, bytes/depth/nodes cap±1, cap+1 rows,
cumulative rows/bytes, повторные aliases/JSONB, empty Q, generic refusal,
50 свежих компиляций CTE и normalization control. Test-only listener перед
настоящим общим `get_cabinet_meeting_review` сохраняет равный `model_dump()`.
Это проверка Python ответа на fixture, не HTTP byte equality и не полный
владелец Session. В исходном Q не добавляются отдельные аналитические
readers, сокращение результата или отключение календарных/previous ветвей.

Пределы остались4096 rows/Q,16384 cumulative,8MiB raw logical bytes,
512KiB row,256KiB field,depth32,nodes65536. Кандидаты ещё не измерены на полном
обычном30–60мин пути и максимальном допустимом envelope. Raw wire bytes не
выдаются за оценку decoded heap: проверка общего2s с materialization/JSON/
Numeric decode/canonical/digest остаётся обязательной будущей приёмкой.

## Требования и границы сохранности

Повторно сверены все18 прежних requirements/review inputs: SAME. Собственное
чтение применимых оригиналов сохранено в этом же диалоге и предыдущем
независимом отчёте; после него новой смены области/сжатия не было. Проект
295ce2c, result-visibility §§2/3/5/7, activation-milestones, Session16.11,
FR-021/025/SC-006, T112/T113 plan/tasks/quickstart, research/data-model,
constitution/privacy/deletion/delivery, PRD14/23/25/31 и product-gates
сохраняют прежние требования. Исправление N1 не меняет цели, получателей,
схему, права, хранение или разрешения рабочего измерения.

Reviewer-owned отметки неизменны: requirements16/0,security27/0,
privacy-measurement52/0,infra29/0; всего **124 checked/0 unchecked**.
Это проверка неизменности списков, не новая полная приёмка F273.

RR до первого tenant SQL, перехват всех actual reads и прямых обходов,
control permissions, подсчёт всех preflight/control/original SQL в128,
один абсолютный срок2s,lock≤250ms,statement≤500ms, cancellation/cleanup,
fresh auth/legal/source/deletion и participating writer fences не выполнены
этим отдельным модулем и данным PASS не принимаются. RR не решает phantom
insertion/freshness. Следующий допустимый шаг — отдельная реализация и
причинная приёмка ранее принятого Session owner, сохраняя исходные caps.

Создан только настоящий новый отчёт. Старый HOLD, code/tests/fragment,
spec/plan/tasks/checklists, Git/GitHub, БД/runtime/данные, сайт, Postal,
соседние службы, nginx/DNS/Compose, сбор/T0, публикации и выпуск reviewer
не менял. Тесты/сборки/пробы/новые агенты не запускались.

## Контрольные суммы

| Проверенный файл | SHA-256 |
| --- | --- |
| `cabinet/result_projection_budget.py` | `3017498c3ae23d897671ae7cc67432b36ffcfbedc9b96a0ab442610b4ef2d18b` |
| `tests/contract/test_result_projection_budget.py` | `7b36f0c99cee98af4b867f05bd01ab2117ed589b0dbb8b8cc35531986ce9828a` |
| `changes/unreleased/F273.yaml` | `65dfa292d94f0f2ea73dd7e7f225f122405acd71b8175aca0e646e4d6766260e` |
| Старый независимый HOLD | `8deb1db80100f28a22981b821eafb293edad2ef18cd76f6e49cf0cbd72e2946f` |
| Новый основной validation report | `d687e892d4ef3f9eabe959cb2e6dcf04493dedd47f4c2a905764a59325ae417b` |
| `/private/tmp/graf-t112-numeric-wire-two-red-20261116.log` | `a4671adbfed4b940f02a0e95bd527a2050634bf7514a432732bc5354c48486e1` |
| `/private/tmp/graf-t112-numeric-wire-complete-20261116.log` | `e11c59afae9029025e472080037f5528358a814cf5671ce87ab8908061bda262` |
