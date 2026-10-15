# Round272 — REQUIREMENTS / scoped analyze: migration.v2 codec + Birth

Дата: 2026-10-07. Независимый reviewer. Lane: **high-risk-product**,
существующая T116; до RED и реализации. Canonical:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, ветка
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Dirty preserve.

## Решение и окончательная область

**SCOPED REQUIREMENTS GO — вариант B; C0 / H0 / M0 / L0.**
Разрешены RED и ограниченная реализация принятых `migration.v2` read/write
и дополнительных сравнений `readCustodyMigrationBirth` в существующих
`ProtectedCustodyMetadata.h/.cpp`, с регрессиями в существующих тестах.
Действующие v1 reader/writer и physical metadata protection сохраняются.

Вариант A — `ProtectedCustodyMigrationPair` — **не входит** в этот допуск.
Существующий migration reader принимает только v1; создать сейчас v1-only
pair и представить его как закрытие matching durable intent для packed media
означало бы пропустить явную зависимость §6.1. Сначала B, затем отдельный
конкретный gate pair/consumer. Агрегатный допуск очереди ещё шире и не является
меньшим решением этого отсутствующего codec.

Нет новых продуктовых решений, task, parser/DOM, target, зависимостей,
backend или контроллера. Это не SOURCE approval и не выполненные тесты.
Нет app adoption, bootstrap/queue/account/path authority, миграции inventory,
network, persist, rename, purge, GC, installed/release acceptance.
T116–T118/T119/T120, H250, legacy AAC RED257/B1 и physical x64 остаются открыты.

## Основания, чтение и scoped analyze

Использованы `speckit-checklist` для качества требований и `speckit-analyze`
для непротиворечивости артефактов. Полные инструкции навыков прочитаны;
ранее полностью прочитанные AGENTS/required guidance/feature context
переиспользованы с текущей сверкой SHA. Лично перечитаны все десять текущих
нормативных checklist, constitution, relevant spec/plan/tasks/models/quickstart,
base §8/§8.1 и packed §6.1; существующие shape/parser/writer/Birth и Format
проверены по исходникам. Большие исторические validation не перечитывались
и не используются вместо норм.

| Норма | Согласование и покрытие B |
| --- | --- |
| Конституция VI, spec FR-012/013/014/022 | Независимый high-risk gate; строгие защищённые metadata, no empty/plaintext fallback; codec не выдаёт прав отправки/удаления |
| Base custody §8.1:415–559 | Прежние tuple, exact shapes, caps, stages, birth/barrier/authorization остаются без ослабления |
| Packed custody §6.1:297–347 | Явная migration.v2, 11 source fields, representation/stamp и неизменная schema transaction; physical protection v1 |
| Plan:1501–1534,1565–1597 | B — необходимая версия metadata внутри T116 до consumer/T117; неподключённый codec не завершает приложение |
| Tasks:567–570 | T115 design принят; T116 CRITICAL остаётся owner; T117/T118 отдельные незавершённые зависимости, новой task нет |
| Data model:535–578 | Logical v5/v3/v2 не меняются; migration.v2 refs explicit; RAM proof не выводится из строки |
| Quickstart:509–532 | Exact schema/null/stamps, budgets и regressions; full roots/GC/generated/installed acceptance отдельно |

Не найдено нового противоречия конституции, uncovered task, неоднозначной
формы или блокирующего C/H в B. Недостроенная общая T116 не переименована в
общий analyze PASS. Чтение текущей модели, где таблица §12 описывает v1,
не отменяет явную поправку §13 и её нормативную ссылку на packed §6.1.

Prerequisite ранее в этой проверке дал правильный FEATURE_DIR с поддерживаемыми
`--json --require-tasks --include-tasks`; spec/plan/tasks существуют. Установленный
скрипт не поддерживает `--require-spec` из навыка; это проверено по help, spec
проверен отдельно, tooling не менялся. Hooks before/after analyze, checklist,
implement: **по одному зарегистрированному git.commit, enabled=false** на каждом
из шести этапов; 0 enabled/0 dispatched. Коммитов и hooks execution не было.
#7444 OPEN/canonical ownership — свежая проверка main, сообщённая в запросе;
reviewer сам GitHub не запрашивал, live tracker audit не заявляется.

## Точная закрытая форма и совместимость

| Объект | Форма |
| --- | --- |
| root | Те же 12: schema, store_id, object_id, generation, transaction_id, subject, directory_id, stage, ledger_anchor, sources, barrier, cleanup_authorization; mask4095 |
| anchor | object_id, generation, length, sha256 —4; mask15 |
| schema1 source | source, source_length, source_sha256, destination_object_id, destination_generation, destination_length, destination_sha256 —ровно7; mask127 |
| schema2 source | Предыдущие7 + destination_representation, destination_container_id, destination_committed_extent, destination_root_ref —ровно11; mask2047 |
| barrier / authorization | Прежние точные5/mask31 и6/mask63; null только где разрешён базовой нормой |

`schema` — единственное поле версии: `graf.custody.migration.v1` или
`graf.custody.migration.v2`; неизвестная версия/alias/отсутствие — отказ.
Schema1 не emit новые поля и отвергает их даже со значением null; typed schema1
отвергает packed=true и любые новые non-null stamp fields. Schema2 всегда
пишет/читает все11 полей, включая explicit flat_v1 и его три null stamp fields.
Изменение только wire schema v1→v2 при прежних7 source fields остаётся отказом.
Старый typed negative schema=2 становится schema=3, без удаления wire negative.

Добавление `packed=false` и optional container/extent/ref в тот же fixed
MigrationSource достаточно. Один PackageJson и один deterministic writer;
можно переиспользовать существующие package.v2 shape/hex/representation/Format
правила. Не нужен отдельный JSON parser или новые persistent proof flags.
Порядок JSON ключей незначим: источники могут идти до schema; проверять exact
маску source по окончательно разобранной версии, не вводить schema-first policy.

Все старые constraints остаются: ≤65536 полных input bytes, strict EOF/no BOM,
unknown/missing/decoded duplicate/type/null/depth/nesting отказ; depth≤4,
keys≤16, sources1–6 и уникальные kinds; все identity/hex/u64/role caps и tuple
ожидания независимо от JSON. Текущий token≤300 достаточен для 128 lowercase
hex root Ref64B. Нового Unicode/framework/cap расширения не требуется.
Queue требует single ledger с length/SHA равными anchor, directory null;
package — без ledger и с present protected anchor pair. Никакого new zero-ID
или cross-role ID collision запрета поверх принятого §8.1.

## Representation, stage и stamp

- Packed разрешён только schema2, subject package, source canonical/media/playback.
  Queue/ledger и package manifest/recovery — только flat_v1.
- Flat требует null container/extent/root на всех stages. Schema2 flat — не
  packed fallback: проверка actual обоих v1 indices принадлежит consumer, не JSON.
- Packed container ID independently reserved и non-null уже prepared.
  Prepared destination generation/length/SHA **все null**, extent/root null.
  Положительная original source length не запрещена в prepared.
- Copied_verified и далее: destination triple весь non-null, generation≥1,
  exact destination length/SHA равны original. Packed extent/root оба non-null.
  Partial triples/stamps, unknown representation, foreign kinds — отказ.
- Структуру root проверять тем же `ProtectedPackedCustodyFormat::decodeReference`:
  ровно64 decoded bytes/128 lowercase hex, kind EMPTY при length0, NODE_L2 иначе,
  root payload0, generation/committedExtent bounds, reserved0, version/offset/
  envelope/overflow ограничения. ZERO/DATA/другой NODE как root отвергаются.
  Destination g1 допускает только empty length0 и extent=appendOffset32896;
  g>1 empty остаётся допустимым по существующей package/Format норме.
- Stage правила unchanged: own generation1 только prepared/null barrier/auth;
  prepared g>1 и copied_verified могут структурно иметь null barrier;
  switched/later требуют barrier, cleanup_pending/complete требуют auth.
  Ранний валидный auth не запрещён, кроме g1; codec не разрешает ранний cleanup.

Это проверка **структуры stamp**, не проверка реального container, full tree,
root ciphertext/closure/logical hash, reachable migration cut или absence.
Нельзя возвращать semantic/effect authority из одного принятого Ref string.
Persistent roots обоих metadata slots/barriers и verified tombstone конфликт/
restoration перед GC остаются обязательными будущему owner/consumer, не B.

## Historical Birth: точное дополнение, не новый physical protocol

Сохранить existing cipher size/SHA, native header/context/role/position0,
exact ref blockVersion>0 и generation1 unprotect/strict decode. Metadata entropy
и opener v1 подходят schema2 payload; не приравнивать version к generation
и не искать newest block/g1 mutable index.

К прежним expected tuple, whole anchor и order-independent source kind/length/
SHA/destination object ID добавить **равную schema birth/current**, а для каждого
соответствующего source — равные packed representation и reserved container ID.
Birth generation1/prepared требует null barrier/auth/destination triple/extent/root;
не требовать равенства null birth extent/root с sealed current stamp.
Schema/container/representation нельзя менять внутри начатой transaction.
Переданный current struct сам себя не аутентифицирует; результат остаётся
borrowed structural value, не genuine pair, источник полномочий или roots proof.

## Обязательная будущая матрица RED / SOURCE (не выполненные результаты)

1. Реальный RED valid schema2 до codec implementation; сохранить schema1 byte
   roundtrip, старые bootstrap/package/migration cases и wire-version-only negative.
2. Обе схемы × допустимые subjects/stages, mixed flat+packed package kinds,
   root/source key permutations; каждый key 12/4/7-or-11/5/6: missing, decoded
   duplicate, unknown, wrong type/null, nesting, aliases, BOM/trailing.
3. Все flat-only kinds/subjects; schema1 typed extras; schema2 unknown
   representation; prepared reserved container и forbidden stamps, every partial
   copied triple/stamp, wrong length/hash/gen0, u64/role caps/count/identity bounds.
4. Positive EMPTY/g1 и nonempty NODE_L2/g>1; generation1 nonempty/wrong extent,
   malformed128hex/ref reserved/kind/payload/version/offset/overflow/extent отказ.
   Не нужен гигантский media fixture или чтение actual tree в чистом codec.
5. Реальная native DPAPI birth fixture v1 и v2, blockVersion17, current g3/g4
   BOTH проверены существующим API без historical g1 index. Schema mismatch,
   representation/container/anchor/source tamper заново защищены DPAPI с новым
   корректным cipher SHA; это semantic negative, не только сломанный cipher.
   Source reorder positive; текущие sealed stamps не сравнивать с null birth.
6. Reader без heap allocation при полном shared quota; writer/native Birth
   реальные allocation refusal/cuts, cleanup/retry и baseline budget restoration,
   exact native/hash errors без plaintext/default. Не считать нулевые allocation
   cuts pure parser доказательством native allocation matrix; Debug proxy count
   не исключать и не ослаблять asserts/лимиты.
7. Fresh exact-source portable + focused Windows Release/Debug, RED/source maps,
   receipts/raw logs; SDK/caller compilation по затронутому scope. Reviewer VM не
   запускает. Испытания generated-only, без устройств/профиля/приложения.

## Инвентарь, hashes и неизменность

До этого файла **137 .md**: 10 текущих нормативных checklist, **154 checked /0 open**;
127 исторических/контекстных отчётов, **256 checked /10 historical open**.
Нормативные количества: routing14/audio24/calendar launcher5/operation8/wire5/
packed writer12/privacy12/requirements22/security27/ux25. Все текущие критерии
прочитаны; прежние отметки не получили нового SOURCE/runtime смысла.
Исторические открытые отметки не переклассифицированы в новые обязанности B.
Исходный SHA инвентаря (sorted basename + TAB + SHA256 + LF):
`5435dbc211ea8699c0793419c5a7f3517f441db8198bbf9e125c048c28857ae1`.
Этот отчёт содержит0 checkbox markers; после него138 .md, нормативные154/0.
Tasks **120/93/27**, SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.

| Текущий исходный файл, до RED B | SHA-256 |
| --- | --- |
| constitution | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |
| spec | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| plan | 527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c |
| data-model | 8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19 |
| quickstart | fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e |
| base contract | ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a |
| packed contract | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| Metadata.h | 524a040b07a3264369406d7bdbcd9e9bcb90417b471f4f3455ced9109f02b615 |
| Metadata.cpp | 6b9566e55edb24e6880d971777cb0d2b852e04cafb28831530395c161dcefba1 |
| Format.h | 0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88 |
| Format.cpp | bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f |
| PackageTests | bd437f417c9ea07d03d182a471e53fef4885a620c9aa137bf61f250eb6c58269 |
| FilesTests | 1b58a9448461983b76b4608392ba7bbeac2163e0117a64618814f59f4ddce9d0 |

Существующие137 checklist/report hashes зафиксированы reviewer до записи;
после записи лично проверено: changed0, единственный added — этот отчёт.
Код/tests/spec/plan/tasks/старые reports/markers/GitHub/
VM/working profile не изменялись. В этой проверке нет исполнения тестов,
компиляции, установки, network или подтверждения полномочий миграции.

Итог: **B достаточно определён принятой нормой; можно начать RED.**
Будущая SOURCE проверка должна оценить actual implementation/evidence отдельно;
это решение не закрывает MigrationPair, matching intent или конечную цель Windows.
