# Round261 — REQUIREMENTS: migration.v1 codec

Дата: 2026-10-06. Независимая проверка требований и ограниченный
`speckit-analyze` до RED/production code. Существующий T116, lane
**high-risk-product**. #7444 OPEN/canonical labels сообщены основным агентом;
рецензент GitHub не запрашивал и не менял.

## Решение

**GO к RED и ограниченной реализации чистого структурного
`graf.custody.migration.v1` reader/writer** в существующих
`ProtectedCustodyMetadata.h/.cpp`, с расширением существующего
`ProtectedCustodyPackageTests.cpp`. Новые задача, схема, target, parser/DOM,
контроллер, зависимость и полномочия не нужны.

Финальный scoped analyze: **CRITICAL=0 / HIGH=0 / MEDIUM=0 / LOW=0**,
неразрешённых уточнений нет. Первоначальная неточность количества полей source
исправлена владельцем до кода; решение относится к уточнённому предложению и
его дополнительным согласованным связям queue/source/anchor и package anchor.

Это REQUIREMENTS approval, **не SOURCE/GREEN/полная миграция/защищённая очередь/
приложение/выпуск**. T116–T118, RED257/B1 и полное подключение потребителей
остаются открыты. Round260 bootstrap SOURCE approval не расширяется.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty preserve.

## Нормативные основания и ограниченный анализ

Навык `speckit-analyze` прочитан полностью. Использован ранее полностью
прочитанный AGENTS/constitution/required guidance и все критерии десяти
действующих checklist; их текущие SHA лично сверены и совпадают. Свежие
релевантные положения constitution VI/quality gates, plan/spec/tasks/models/
quickstart и полный контракт migration §8/§8.1 прочитаны отдельно.
Исторические большие validation/reports не подменяют текущие нормы.

| Требования | Покрытие существующими задачами / смысл данного шага |
| --- | --- |
| FR-012 — полная защита и сохранение original | T116/T117/T118; строгий intent codec — зависимость, не защита дискового пути |
| FR-013 — identity/ranges/deletion/purge, no empty ledger | T116/T117/T118; structural anchor/source stamps, не проверенный ledger |
| FR-014/FR-022 — серверные и deletion rights | T116/T117/T118; JSON receipt не выдаёт upload/cleanup right |
| SC-003/005/006/008 | T116/T117/T118; неизменные ресурсы/100cycles/diagnostics/install gates, не результаты purecodec |
| Constitution VI, `plan.md:1501`, `tasks.md:568` | Независимый high-risk gate, сначала регрессии, существующая последовательная зависимость внутри T116 |
| `data-model.md:504`, `quickstart.md:409`, base §8/§8.1 | Exact schema, fixed roles, strict fields/stages, отдельные IO/cuts/owner/authority проверки |
| Packed contract migration.v2 | Отдельный точный schema2 и ещё4 source поля; не разрешает добавить их в schema1 или fallback после ошибки packed |

Нет новой задачи без покрытия, конституционного конфликта или нового
продуктового выбора в этом codec. Общий Feature200 analyze не объявляется
PASS: незавершённая реализация T116 CRITICAL и T117/T118 HIGH остаётся такой.

Prerequisite command с поддерживаемыми флагами:
`.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`
дал правильный FEATURE_DIR; spec/plan/tasks существуют. Неподдерживаемый в
текущем скрипте `--require-spec` из инструкции навыка не использован повторно;
spec проверен отдельно. `.specify/extensions.yml` разобран: before/after
analyze и implement имеют0 enabled hooks. Tooling не менялся.

## Выявленная неточность — закрыта до кода

| ID | Severity | Наблюдение и решение |
| --- | --- | --- |
| REQ261-1 | MEDIUM, CLOSED | В первоначальном описании test masks source указан8; §8.1 перечисляет ровно7 полей. Владелец подтвердил точные7. Матрица теперь12/4/7/5/6, никакого восьмого поля/alias не добавляется |

Это исправление описания предложения, не изменение §8.1/spec/plan/tasks.
Остальные параметры ниже выводятся из существующего контракта, не задают
новую политику. Дополнительных CRITICAL/HIGH ambiguities не обнаружено.

## Точная структурная форма

API принимает независимо ожидаемые own context с ролью `migrationIntent`,
target/own generation≥1, transaction ID, `CustodyMigrationSubject` и directory
(`string_view`: queue ожидает empty и JSON null; package — explicit identity).
Reader/writer сверяют один и тот же tuple. Schema только
`graf.custody.migration.v1`, внутреннее schema1. Никаких input-derived expected
данных, retained input views, path/controller/proof factory или IO.

| Объект | Все обязательные точные поля / число |
| --- | --- |
| root | schema, store_id, object_id, generation, transaction_id, subject, directory_id, stage, ledger_anchor, sources, barrier, cleanup_authorization —12 |
| ledger_anchor | object_id, generation, length, sha256 —4 |
| sources item | source, source_length, source_sha256, destination_object_id, destination_generation, destination_length, destination_sha256 —7 |
| barrier, когда non-null | object_id, generation, block_version, envelope_bytes, sha256 —5 |
| cleanup_authorization, когда non-null | kind, operation_id, actor_user_id, workspace_id, queue_object_id, queue_generation —6 |

Null допустим только в названных §8.1 nullable полях и цельных сочетаниях;
отсутствие обязательного ключа не является null. IDs — decoded32 lowercase
hex, SHA — decoded64 lowercase hex, u64 — exact decimal unsigned literal
без sign/fraction/exponent/leading-zero/overflow. Identity —1–300 ASCII
`[A-Za-z0-9_-]`; массив301 имеет bounded terminator, optional null отличим
от пустой строки. Нет дополнительного zero-ID/ID collision запрета.

Ledger anchor object ID/generation: весь null pair либо оба present с gen≥1;
length≤4MiB и SHA32. **Package требует present protected anchor pair**:
§8/§8.1 требует protected queue уже перед prepared package migration.
Это structural declaration, не проверка настоящей current queue pair.
Queue допускает оба вида anchor; её единственный ledger source описывает
тот же snapshot, поэтому source length/hash **равны** anchor length/hash.
Actual entire snapshot/hash, owner/ranges/deletion/purge и virgin-root proof
при empty ledger устанавливает будущий IO consumer, не codec.

Sources1–6, уникальные closed enums
`ledger|manifest|canonical|media|playback|recovery`. Queue — ровно1 ledger;
package — без ledger, следовательно максимум5 известных уникальных kinds.
Source length ограничен соответствующим role cap: ledger4MiB,
manifest/recovery64KiB, canonical/media/playback64GiB. Destination object ID
present уже в prepared; triple generation/length/hash обрабатывается целиком
по stage. Никакие names/paths/orphan suffix из JSON не принимаются.

Barrier, если present: тот же own object ID, historical generation=1,
block_version>0, envelope_bytes>16 и ≤
`blockEnvelopeLimit(logicalLimit(migrationIntent))` = **69632**.
Это согласовано с существующим common entry bound; не заявление, что любой
размер17..69632 является валидным native envelope. SHA здесь cipher envelope
hash, не content SHA. Block version не приравнивается к generation.

Authorization, если present: точный kind `owner_confirmation|delete_purge`,
operation/actor/workspace — identity, queue ID canonical и queue generation≥1.
Для owner_confirmation operation ID — именно32 lowercase hex ожидаемого
transaction ID. Delete_purge operation остаётся existing identity, не обязан
быть transaction hex. Current queue, actual operation/owner и fresh rights
не выводятся из этих полей и требуют отдельной проверки перед cleanup.

## Stage/generation: достаточные, но не effect-authorizing правила

| Условие | Destination triple каждого source | Barrier | Authorization |
| --- | --- | --- | --- |
| Birth own generation1 | stage только prepared, все triple null | null | null |
| prepared, generation>1 | весь null | null либо валидный ref | null либо валидный объект |
| copied_verified | весь non-null, destination gen≥1, length/hash точно равны source | null либо валидный ref | null либо валидный объект |
| switched | как copied_verified | обязательно non-null | null либо валидный объект |
| cleanup_pending / complete | как copied_verified | обязательно non-null | обязательно non-null |

Частичный triple/pair, generation0, неизвестный stage/enum или mismatch — отказ.
Для **copied_verified с null barrier** отдельного запрета чистого codec в §8.1
нет; прямо запрещён switched без barrier. Не вводится новая структурная
политика по догадке. §8 при этом сохраняет actual g1→g2 barrier/fence/rename
ordering; принятие структуры copied_verified/null **не** означает принятие
reachable migration state, разрешённый rename/switch или отсутствие IO gates.

Не-null authorization до cleanup_pending допустим структурно (кроме g1 birth):
§8.1 не запрещает такую сохранённую форму. Она не разрешает раннюю очистку.
Complete по-прежнему требует actual absence proof; switched требует
reconciliation/bootstrap/state agreement; чистый codec ничего из этого не
проверяет и не выдаёт permission bool. Actual исторический validator сверяет
birth schema/payload/transaction/anchor/sources с retained immutable block,
а не читает g1 как current metadata; этот validator не реализуется здесь.

## Reuse и обязательная матрица RED/SOURCE

Текущий `PackageJson` и allocator/formatting полностью прочитаны в предыдущем
SOURCE260; свежий hash тот же и bootstrap overload сверён. Object/hex/number/
nullable/string и fixed masks подходят; добавляется закрытый overload и
известные nested shapes, не второй decoder/DOM/recursive unknown-key skipper.
Root mask4095, anchor15, source127, barrier31, authorization63. Максимальная
известная вложенность root→sources array→source object ниже depth≤4;12 root
keys ниже16. Число source перед записью/индексированием≤6, enum перед shift/
table access проверен. Результат владеет fixed arrays, reader без heap allocation.

Full input≤65536, strict EOF, JSON whitespace/key order не значимы; BOM,
invalid UTF-8/escape/surrogate, decoded duplicates, unknown/missing fields,
неверные типы/null/nesting/comments/trailing и inconsistent tuple/stages —
typed whole failure, не partial/default. Все accepted strings ASCII; общей
Unicode DOM/traversal зависимости не нужно. Writer deterministic, shared
charged reserve до plaintext, no unwiped growth, typed allocation refusal.
Существующие bootstrap/package writer bytes и tests не меняются по смыслу.

Перед code — минимальный valid g1/prepared queue RED. Затем в том же existing
test target: пять stages × два subjects с допустимой generation, birth negative
cases; every12/4/7/5/6-key missing/decodedduplicate/type/null, 0/7 source counts,
duplicate/unknown/source scope, complete/partial destination triples, mismatch
length/hash/queue anchor equality, package legacy-null anchor rejection,
barrier null/ID/gen/version/envelope boundaries, authorization kind/identity/
transaction equality и early optional/later mandatory cases. Independently
expected own role/IDs/gen/transaction/subject/directory mismatches в reader и
writer; bad enum/count до UB/index/allocation. Exact u64/role caps/identity300/
301/ASCII/hex/escaped keys, full65536/+1, full shared-budget allocation-free
reader, writer refusal/no leak/release/retry; прежние tests сохраняются.

Это условия будущей SOURCE проверки, не выполненные тесты. Нет native jobs,
MF waits, filesystem publication, bootstrap fence или ledger change в этом
чистом шаге. Реальные IO/ownership/migration cuts должны прийти после него,
не fake controller/currentness или ещё один публичный plaintext fallback.

## Инвентаризация и исходный снимок

До нового отчёта116 `.md`: **10 текущих normative checklist =154 checked/0 open**;
отдельно106 historical/context =102 review+4 analyze/research,
**256 historical checked/10 historical open**. Полностью прочитанный контекст
всех критериев сохранён; свежие10 SHA совпадают. Исторические open не
переклассифицированы в новые нормативные обязанности и не переотмечены.
Tasks **120 total/93 checked/27 open**, без изменения.

SHA-256 исходного inventory116 (sorted basename + space + file SHA + LF):
`7053bc9dd36ca3d0ebd3c3224267508091b345a7a0cb74f6b394afed01f8370b`.

| Источник | SHA-256 до RED261 |
| --- | --- |
| constitution | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |
| spec | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| plan | 527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c |
| tasks | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| quickstart | fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e |
| data-model | 8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19 |
| base custody contract | ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a |
| packed custody contract | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| Metadata.h | 8cbf848fa864bc50298e2d0bb30d6bf7d2225e1c0258cef184959d981ffd3eec |
| Metadata.cpp | 09d0d0d66037c1c0231dd92400e97430b4a2d4b71d3ba3ef540c8e5d546f6c6c |
| PackageTests.cpp | 833eab30402e0743bf1c90ffed382c62fca400c7eda2814bd0b3e25852d8571d |

Записан только этот новый reviewer-owned gate после read-only analyze по
явному write scope владельца. Никакие old reports/checklist markers/code/
tests/spec/plan/tasks/constitution/GitHub/VM/commit/profile/release не менялись
рецензентом; новых тестовых/SDK/installed результатов этот отчёт не заявляет.
