# Round260: требования к чистому bootstrap.v1 codec

Дата: 2026-10-06. Независимый REQUIREMENTS review и ограниченный
`speckit-analyze` перед RED/реализацией. Risk/validation lane:
**high-risk-product**, существующий T116; связь #7444 указана основным агентом,
состояние GitHub в этой проверке не запрашивалось.

## Решение

**GO только к RED и ограниченной реализации предложенного чистого codec
`graf.custody.bootstrap.v1` в существующих `ProtectedCustodyMetadata.h/.cpp`
с тестами в существующем `ProtectedCustodyPackageTests.cpp`.**
В этой области **CRITICAL=0 / HIGH=0 / MEDIUM=0 / LOW=0**; неразрешённых
продуктовых уточнений нет. Новые схема, задача, DOM, зависимость или путь
хранения не нужны. Это допуск требований, **не SOURCE approval, не GREEN,
не допуск bootstrap/очереди/миграции/приложения**.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty worktree сохранён.
`tasks.md`: **120 задач / 93 checked / 27 open**. T116–T118 и T120 этим
решением не закрываются. Legacy RED257, B1 и требования подключения
реальных потребителей сохраняются; предыдущие SOURCE259 и include-order
решения не расширяются и не изменяются.

## Основания и ограниченный анализ

Прочитаны проектные навыки `speckit-analyze` и `speckit-implement`, текущий
AGENTS/индекс guidance, все критерии десяти действующих checklist; для
constitution/guidance использован ранее полностью прочитанный контекст с
текущей сверкой относящихся к этому шагу положений. Свежие источники:

| Источник | Значение для данного шага |
| --- | --- |
| Constitution VI и Development Workflow; `spec-kit-flow.md`, `product-gates.md` | Независимый gate до high-risk code, сначала регрессии, без ложной приёмки приложения/данных/удаления |
| `spec.md` FR-012/013/014/022; SC-003/005/006/008; уточнение 2026-10-02 | Защита всей цепочки, сохранение ledger/ranges/identity, отказ без empty state; самостоятельная последовательная реализация хранения разрешена |
| `plan.md:1501` и `tasks.md:568` | T116 допускает структурные primitives как зависимость; неподключённый codec не считается защищённым приложением |
| `data-model.md:504`, строка ProtectedBootstrap | Fixed location, reserved queue ID не является reader authority, никакого перенаправления через JSON |
| `quickstart.md:408` — New payload codec / First transition | Точные схемы/типы/связи/лимиты; межобъектные cuts и настоящая миграция — последующая отдельная приёмка |
| `windows-protected-local-custody.md:415` (§8.1), §2/§3/§8 | Полный нормативный контракт bootstrap, независимо от package-state v1/v2 и logical v5/v3/v2 |

Ни новая продуктовая политика, ни конфликт с текущей схемой не обнаружены.
Более строгие собственные ограничения на нулевые ID или совпадение разных
ID не выводятся из §8.1 и не вводятся. Общий анализ Feature200 не объявляется
PASS: открытый полный T116 имеет CRITICAL объём, T117/T118 остаются HIGH.

Prerequisite выполнен поддерживаемой командой
`.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`:
правильный FEATURE_DIR, spec/plan/tasks существуют. Флаг `--require-spec`,
указанный в навыке analyze, текущим скриптом не поддерживается; первоначальный
вызов вернул `Unknown option`, после проверки справки выполнен поддерживаемый
вариант, наличие spec проверено отдельно. Файлы tooling не менялись.
В конфигурации нет включённых before/after analyze/implement hooks.

## Точная форма и обязательные условия реализации

Все **девять** JSON-полей обязательны, даже когда значение `null`.
Единственный ключ версии — `schema`, значение только
`graf.custody.bootstrap.v1`; внутреннее `schema=1` не разрешает JSON aliases.

| Поля | Проверка |
| --- | --- |
| `store_id`, `object_id` | После декодирования ровно 32 lowercase hex; совпадают с независимо ожидаемым own context |
| `generation` | Decimal unsigned literal 1..UINT64_MAX; exact совпадение с ожидаемой own/target generation; не float, bool, string, exponent, minus, leading-zero или overflow |
| `mode`, `queue_object_id` | Только `protected`/`migrating`; queue ID canonical и совпадает с отдельным ожидаемым queue ID |
| `transaction_id`, `subject`, `directory_id` | Точные типы/null и сочетания из таблицы ниже; отсутствие поля не заменяется null/default |

| Mode / subject | transaction_id | subject | directory_id |
| --- | --- | --- | --- |
| protected | null | null | null |
| migrating / queue | canonical ID | queue | null |
| migrating / package | canonical ID | package | 1–300 ASCII `[A-Za-z0-9_-]` |

Own context и значение обязаны иметь роль `bootstrap`, совпадающие store/object
IDs и generation. Ожидаемые данные не извлекаются из того же непроверенного
JSON. Для записи ожидается именно target generation, не автоматически base+1:
переполнение/публикация относятся к будущему фактическому commit.
Mode/subject при записи также валидируются, включая недопустимые значения enum,
до обращения к таблицам. Optional directory/массив301 должен однозначно
отличать null от непустой identity; пустая строка не является package identity.
Массив не разрешает чтение вне границ или принятие 301-символьной identity.

Полный input ≤65536 bytes; JSON whitespace/key order не значимы, вывод
детерминирован. Decoded duplicate, unknown/missing key, неверный тип/null,
вложенная форма, BOM, invalid UTF-8/escape/surrogate, комментарий, trailing
comma/bytes, неизвестные schema/enum и любое несовпадение — отказ целиком,
без частичного результата или восстановленного default bootstrap.
Этот плоский закрытый объект имеет depth1 и 9 ключей, то есть не расширяет
нормативные depth≤4/keys≤16. ASCII, в том числе `\u0061`, проверяется **после
декодирования**; raw Unicode или escaped non-ASCII не входит в грамматику
ни одного принятого поля. Общий Unicode parser здесь не требуется.

## Пригодность повторного использования

Лично прочитаны `ProtectedCustodyMetadata.h`, существующий `PackageJson`
(`.cpp:71–183`), package reader/writer (`:186–225`), тесты package и общий
allocator. `PackageJson` уже имеет stack token300, явную ASCII identity,
decode-before-key-mask, hex/number/nullable/object primitives, exact EOF,
без heap DOM, recursive skipping или удерживаемых input views.
**Overload `read(CustodyBootstrapValue&)` подходит**: собственная таблица9
ключей и полный mask; bootstrap shape не вызывает package phase/ref validator.
Структурный результат — фиксированное владеемое значение, не представление
заимствованного буфера и не private proof factory.

Запись может повторно использовать существующий bounded emit/quoted/hex/
`to_chars` pattern: проверенная ASCII-грамматика, admitted charged buffer до
первых plaintext bytes, ограничение всего вывода и штатный wipe/release.
Reader не выделяет динамическую память; writer возвращает типизированный отказ
при shared-memory exhaustion, не использует запасной uncharged буфер.
Существующие package v1/v2 bytes/семантика и их тесты сохраняются. Минимальное
извлечение общих formatting helpers допустимо в том же TU, не новый framework.
`CMakeLists.txt:27` уже содержит нужный тестовый файл; новый target не требуется.

## RED и последующая SOURCE-проверка

Предложенной матрицы достаточно для начала, при следующих точных проверках:

- Три разрешённые формы, разные key order/whitespace/escaped ASCII;
  write→read и детерминированный повторный write, generation UINT64_MAX,
  identity300, допустимые zero/equal IDs при совпадающем expected context.
- Все обязательные поля по отдельности: missing, normalized duplicate,
  unknown/alias/schema, тип/null; все несовместимые mode/subject/directory/
  transaction сочетания. Own role/store/object/generation и отдельный queue ID
  mismatch; invalid enum/input при writer без UB/публикации.
- Generation0/overflow/minus/fraction/exponent/leading-zero; upperhex/не32hex;
  identity0/301/slash/NUL/non-ASCII; BOM, invalid UTF-8/escapes/surrogate,
  nested value, trailing данные/запятая. Полный валидный input с whitespace
  ровно65536 принимается, 65537 отвергается без allocation.
- Reader остаётся успешным для разрешённого input при полностью занятом
  shared budget; writer allocation refusal без утечки/роста/partial output,
  освобождение давления и успешный retry. Существующие package v1/v2 регрессии
  не сокращаются. RED предшествует production; реальные результаты и точный
  SHA будут предметом последующего независимого SOURCE review.

Здесь тесты/сборка/VM не запускались; будущие условия не отмечены как PASS.

## Не входящие в GO полномочия и обязательные зависимости

`CustodyBootstrapValue` — **plain structural value, не authority/proof**.
Успех codec не доказывает DPAPI/ACL/own index provenance, durable matching
intent, fixed queue `id.bin`, BOTH queue slots, copy receipt, account/epoch/
current owner, permission на effect, write/upload/playback/delete/GC.
Expected queue ID должен позднее поступать из независимо проверенного
фиксированного объекта, а не из JSON или произвольного нового ID.

§8.1 требует matching durable intent в migrating, но чистый codec без IO не
может его проверить: он принимает только структурно допустимый tuple; полный
cross-record consumer ОБЯЗАН проверить intent и этапные условия §8 до
admission. Initial queue/prepared допускает reserved queue ID без готовых
indices, не regular queue authority; package migration уже требует protected
queue pair. После switch актуальная queue может законно менять generation/
hash: bootstrap не фиксирует их навсегда. Migrating запрещает обычные effects.

Лично подтверждены текущие непринятые потребители: `AppMain.cpp:600` вызывает
`queue_.load()` в NativeCapture; `DesktopUploadQueueService.cpp:135` читает
обычный ledger JSON, `:1220` сохраняет JSON через existing writer/AtomicFileStore.
Этот gate не меняет их, не разрешает автоматически считать их protected и
не даёт новое разрешение regular plaintext fallback. Подключение bootstrap,
owner/queue/writer, migration intent/restart/adoption и приложение остаются
**NOT GO / не выполнены данным шагом**. Нужны их собственные реальные gates.

## Инвентаризация и точный снимок

До этого отчёта **114 `.md`**: **10 текущих нормативных checklist,
154 checked / 0 open**; отдельно **104 historical/context файла
(100 review + 4 analyze/research), 256 historical checked / 10 historical open**.
Старые открытые маркеры не превращены в новые нормативные обязанности.
Все десять текущих наборов критериев прочитаны; это не повторная приёмка всей
реализации или всех unrelated domains. Никакие старые маркеры не изменены.

| Текущий checklist | checked / open |
| --- | --- |
| requirements / security / ux | 22/0 · 27/0 · 25/0 |
| audio-capture / advanced-routing | 24/0 · 14/0 |
| calendar-launcher / calendar-operation / calendar-wire | 5/0 · 8/0 · 5/0 |
| packed-writer / privacy-pause | 12/0 · 12/0 |

SHA-256 инвентаря исходных114 файлов (sorted basename + space + file SHA + LF):
`c89f65ec014c85aaf53ce4d483c2d9cbb697db1a71ec7475629bc4ed382f356d`.
Новый отчёт в этот исходный инвентарь не входит.

| Файл | SHA-256 до RED |
| --- | --- |
| constitution | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |
| spec.md | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| plan.md | 527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| quickstart.md | fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e |
| data-model.md | 8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19 |
| windows-protected-local-custody.md | ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a |
| windows-protected-packed-custody.md | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| ProtectedCustodyMetadata.h | 3e1f12fda3e18463c6430921e16173afac5c549aaebfa222efcc9dd24b743478 |
| ProtectedCustodyMetadata.cpp | c917b43a94d09547be829694b6cf9c44efde0f91d03dce4c931d8534fa68a1f7 |
| ProtectedCustodyPackageTests.cpp | 6bb176332bceb6fd195d1eacb3c3ea4af827d029a03b819d3c30ab7397e9f3e6 |
| SOURCE259 inspector report, неизменённый | 8502317a4e6b16a0089d35ea45b8a8967f5070e4f7bca91a41c74a55f7f3cadf |
| include-order SOURCE report, неизменённый | 132b71975eaf00ee9d7f8cc7d7838e7fc79efbe5033da1fb829a5a40a7ef2524 |

Записан только этот новый reviewer-owned файл. Старые отчёты, source/tests,
spec/plan/tasks, GitHub, VM, устройства, профиль, commit и release не изменялись
рецензентом. Полная приёмка Windows/macOS и её аппаратные/установочные условия
остаются неизменной конечной целью, не результатом Round260 codec gate.
