# T113: независимый проектный разбор UTC-слота и attempt v2

31.10.2026, проверяющий `/root/f273_release_boundary`, F273/T113/#7804,
`high-risk-product`. Основа `ad363160d049b9bed1346955ba0af5cc806c9470`,
ветка `codex/f273-local-period-20261029`. Предмет — незакоммиченный точный
раздел [UTC-расписание и attempt v2](t113-full-operator-design-20261030.md#utc-расписание-и-attempt-v2--уточнение-31102026)
и его зависимости initial/ready/обычного backup. Это проверка до кода.
Изменён только настоящий отчёт; код, планы, требования, чек-листы, Git/GitHub,
сервер, задания и Dev reviewer не менял. Чужая работа сохранена.

## Решение

**SCOPED DESIGN/ANALYZE PASS только UTC/attempt-v2**: открытых P1:0, P2:0,
CRITICAL:0, HIGH:0 в этом срезе. Принятый полный документ имеет SHA-256
`ecf733993e32be274ba5e9bb3f4b6e901631cbcf4a3deccffb7d961664297869`.
Окончательные изменённые разделы и связанные ссылки перечитаны независимо.

**Полный J1 остаётся HOLD**: весь host scheduler, indirect executable/config/
hooks closure и полнота установки этим отчётом не принимаются. Это не
разрешение реализации всего верхнего цикла до полного J1/analyze, не кодовый
PASS, не установка cron, provisioning, T0 или рабочий запуск. Тестов лично
запущено0; SSH/Docker/БД/production операций0.

## Найденные пробелы и принятые минимальные исправления

| Находка первого прохода | Почему требовалось уточнение | Окончательное исправление |
| --- | --- | --- |
| S1: канал времени bootstrap→child не определён; FD не переносит дату | Child запускается после подготовки и не может сам повторить проверку «до подготовки». Владение lock не доказывает происхождение timestamp | Доверенный root bootstrap передаёт вычисленные due_started_at и абсолютный monotonic deadline фиксированными внутренними argv тому же pinned child; inherited FD доказывает только lock. Root/source/FD/type/finite/date/day/остаток проверяются. Ручная преднамеренная root-подмена явно за прежней границей |
| S2: completion обеих initial-копий относительно T0/ready/resume был неоднозначен | Completed-only ordinary verifier до завершения второй attempt образовал бы цикл; разные UUID копий нельзя заменить одним terminal record | Две physical immutable копии проверены до T0. Первая attempt completed до второй; вторая остаётся exact in_progress под EX до ready/safe resume, затем terminal commit. Trusted owner использует внутреннее физическое чтение manifest, ordinary consumers остаются completed-only |
| S3: completed→failed после поздней ошибки требует нового сложного rollback служебной записи | Неуспешная downgrade-запись могла оставить видимый прежний completed; прежний fallback охватывает in_progress→completed, а не произвольный обратный переход | Обратный переход исключён. Completed — последняя durable мутация всего запуска после обязательных proof/ready writes/safe resume. До неё исход in_progress→failed; ошибка terminal fsync использует прежний fallback на in_progress той же attempt/claim |

S1–S3 закрыты проектно. Первоначальный вариант с обеими initial attempt
completed до resume и последующим completed→failed не является принятым.
Дополнительный token/pipe/pass-file/IPC для аутентификации parent не нужен.
Принята именно доверенная root/source граница, а не фиктивная защита от root.

## Проверенная окончательная модель

Внешний bootstrap не принимает даты, deadline, слот или timezone. Фиксированный
scheduled режим первым stdlib UTC чтением выбирает день/минуту03:10, до
installation/lock/temp/uv/БД. Вне окна возвращается not_due без записи и без
backup PASS. Due сохраняет один600с monotonic deadline, общий для подготовки,
ожидания lock и всей операции; вложенные стадии получают остаток.

В существующем Linux процессе и его дочернем процессе абсолютный monotonic
deadline применим в одной системной шкале. Child проверяет его конечность,
положительный остаток≤600, root/pinned source, тот же canonical inherited lock
FD/dev/ino, UTC due minute/день/небудущее timestamp. Позднее окончание uv не
требует снова попасть в минуту03:10. Обход обычного внешнего bootstrap
преднамеренным root-вызовом child явно вне гарантии. Дата в argv сама по себе
не объявлена ни proof родителя, ни выполненным backup. Исходящие argv создаёт
проверенный bootstrap в очищенном окружении; нового механизма доверия нет.

Attempt v2 добавляет только nullable scheduled_claim с тремя строгими полями
utc_day/run_id/claimed_at. Применяются точные ключи/типы/настоящая UTC дата,
согласованность дня и claimed_at, отсутствие будущего/неполного/duplicate
состояния. Claim на момент создания ссылается на текущий run; в следующих
ручных попытках сохранённый scheduled run закономерно иной. Это не ошибка и
не основание обнулить claim. Claim не задаёт T0, source binding или успех.

Read-only проверка terminal attempt до revoke использует тот же строгий
чистый parser и защищённое чтение. Существующее требование revoked у
`_previous_backup_attempt` не ослабляется. Равный день даёт already_claimed
без мутации/остановки; future/clock rollback/missing/unresolved дают HOLD.
Под EX проверка повторяется; новый claim записывается атомарно вместе с
единственной in_progress attempt после revoke и до stop. Неудачный fsync
запрещает stop. Failed/cancelled/crash расходуют день. Manual/restore не
сбрасывают claim; следующий день не лечит unknown actual restore.

Один верхний owner создаёт UUID/destination и владеет attempt до terminal
исхода. Copy core получает эту exact attempt, создаёт и проверяет bytes/
manifest/cleanup, не создаёт другой run и не меняет claim. Внутри attempt
UUID/destination/binding/started_at/claim неизменны. Приняты только переходы
in_progress(running,null finish/digest)→completed(verified,exact manifest)
или →failed(backup_failed/cancelled,current UTC,null digest). Новая attempt
начинается только после terminal; ошибка записи остаётся unresolved/HOLD.

Для initial первая физическая копия завершается под тем же owner/EX, затем
начинается вторая distinct UUID attempt. До T0 trusted owner сам читает оба
полных immutable комплекта штатным `_read_coherent_backup`, сверяя собственную
exact in_progress вторую attempt и binding. Две копии действительно закончены
физически; terminal попытки не заменяет такого доказательства. T0/initial
создаются по прежнему однократному marker-порядку после этого proof. Ready
записывается под EX; runtime admission его ещё не видит. Только после safe
resume и всех обязательных проверок вторая attempt получает completed, затем
идёт обычный strict read_ready и отпускание EX. Публичного allow_in_progress
нет. Initial8/9 и раздел проверки перед ready приведены к этому порядку.

Scheduled/manual backup используют тот же final commit point. Поздний drift
обычного admission/verify может дать HOLD/revoke, но не меняет уже завершённое
копирование задним числом и не объявляется PASS готовности. Ошибка resume до
commit оставляет in_progress/failed и revoked; старая хорошая копия её не
скрывает. Ошибка fsync terminal сохраняет fallback in_progress именно этой
attempt и claim; повторная отмена не освобождает locks/children до cleanup.

Создание отсутствующей записи допустимо только initial с проверенным
never_started и отсутствием initial.json. После initial потеря записи — HOLD.
V1 не становится null-claim автоматически: scheduling выключен, provisioning
подтверждает отсутствие прежних расписаний/claims полным J1, проверяет terminal
v1 и сохраняет закрытый digest прежних bytes; добавляет null, сохраняя остальные
значения, initial и T0. Неизвестное отсутствие claims — HOLD. Нового state-файла
или TTL нет; immutable manifest остаётся v1 и не переписывается.

Verify03:15 использует общий lock и собственный конечный600с deadline,
не вызывает stop/второй backup. Долгая копия до03:20 допускает конечное ожидание
или HOLD. Пропущенный tick не порождает дневной catch-up; not_due/already_claimed
и сам claim не заменяют свежий manifest/receipt. Часы сервера и чужие задания
не перенастраиваются. Полный installed-jobs proof остаётся обязательным.

## Scoped analyze и контрольные списки

Применён ранее прочитанный speckit-analyze в ограниченном срезе. Prerequisites
`--json --require-tasks --include-tasks` подтвердили именно F273; spec проверен
отдельно. Установленная версия не имеет --require-spec. Before/after analyze
hooks перечитаны: enabled=false, они не выполнялись. Эти read-only проверки
метаданных не являются тестами реализации.

| Требования | Существующие задачи | Что проверено проектно |
| --- | --- | --- |
| FR-033/034/051 | T110/T113, существующая T117 | Ежедневный due, последний исход, failure и freshness без подмены старой копией |
| FR-035 | T113, существующая T118 | Два distinct комплекта и физическое доказательство до T0 не заменяют restore proof |
| FR-038 | T100/T113 | Pinned root/source/argv/FD и общая строгая version2 модель consumers |
| FR-050, зависимость | T109/T113 | Ordinary verify03:15, конечное ожидание, отсутствие ложного receipt/ready |

Шесть FR в срезе,6/6 покрыты существующими задачами; новых непокрытых/дублирующих
задач0. Противоречий конституции и новых продуктовых решений нет. Это карта
требований и дизайна, не степень готовности F273.

Все117 действующих вопросов перечитаны и независимо переоценены:
requirements16 checked/0 unchecked, privacy45/0, security27/0, infra29/0.
Итого **117 checked /0 unchecked**, отметки не менялись. Для этого среза
непосредственно применимы infra CHK003–009/025, privacy CHK033–037 и security
CHK010–015/022; их исходные требования остаются ясными и проверяемыми.
Остальные не получают новых данных/получателей/согласий/продуктовых сценариев.
Отметки относятся к качеству требований, не к установленному расписанию,
actual attempts или достигнутым показателям. Неизменные большие baseline
сверены по хешам в рамках разрешённого владельцем исключения F273;
затронутые разделы/зависимости прочитаны непосредственно.

## Следующие необходимые проверки и сохраняющиеся HOLD

До кода остаётся полный J1/analyze. Затем обязательны причинные проверки
UTC/Europe-Amsterdam/DST, не-due без uv/temp/state/БД, неверные root/source/FD/
NaN/infinity/future/deadline, переход минуты во время подготовки без нового
600с, parallel ticks/manual backup/clock rollback, claim fsync/crash/TERM,
exact run ownership, два initial комплекта/единственный T0, failure до terminal
и при safe resume, terminal fsync fallback, потеря/v1 provisioning, contention
verify03:15, no catch-up и физическое чтение latest manifest. Независимое code
review и реальный разрешённый запуск полного argv/attempt/receipt отдельно.

Оба общих HOLD `full_preflight_not_implemented` и
`activation_recovery_unverified`, J1, весь верхний цикл, ресурсы/пауза/retry,
права/операторы/MFA, T112/T113, AC01–AC06, T0 и exact-SHA CI/Full/выпуск
сохраняются. Никаких выводов о рабочей аналитике, трафике или продажах.

## Проверенные хеши

| Источник | SHA-256 |
| --- | --- |
| full-operator-design | `ecf733993e32be274ba5e9bb3f4b6e901631cbcf4a3deccffb7d961664297869` |
| host-schedule-options-review | `09fce5d224efcba0c52211d5811416f4e6893128de70f900732aeecd7b827bc9` |
| bootstrap activation-operator.py | `e11efddb4001602014977be3dff5e86550978cf81bfe67f23d7ae60a0bdfbfb5` |
| activation_operator.py package | `b086459d5f3a2a16571041cc96c7120543a6ebfed3dd1ae4887a0a7405ea4ced` |
| operations | `8340e07793a6c27668f9850652f00b05fdc147fb895375bd9c9815a80d68a1d5` |
| data-model | `aba2d03bcdd21541b06b5874a9dd29b0395712f28cb26efcae635c46115e1c45` |
| plan | `ac3abed8277feed03e58c9978d25dc89ac701511e14a1215f1fffa24babeff3e` |
| tasks | `eb31f04c410ec6b4aa92c3823f40c7d8e0c31c4f266911b982af7f2be90d25a2` |
| quickstart | `9812f3683f74f72dcfdda0cc33ba3a2820bee73004ef832b7d1444bec338afbd` |
| spec | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current-product-status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| checklist requirements16/0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| checklist privacy45/0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| checklist security27/0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| checklist infra29/0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

После записи отчёт перечитан; counts и финальный design hash проверены ещё раз.
Изменение алгоритма или доверенной границы требует повторного scoped review.
