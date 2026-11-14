# Round262 — REQUIREMENTS: исторический migration.v1 birth block

Дата: 2026-10-06. Независимый REQUIREMENTS / scoped analyze; не SOURCE review.
Назначение: решение до RED и реализации самостоятельной исторической проверки
по уже принятому §8.1. Владелец реализации — main; reviewer пишет только этот
новый отчёт. Все предыдущие отчёты, отметки checklist, код и задачи неизменяемы.

## Решение

**SCOPED REQUIREMENTS GO для окончательного предложения Round262.** Можно
начинать RED и реализацию `openMigrationBirthBlock`,
`readMigrationBirthEnvelope`, `readCustodyMigrationBirth` в существующих Codec,
Files и Metadata. Неразрешённых CRITICAL/HIGH требований в этой ограниченной
области: **0/0**; новых продуктовых решений или изменений schema не требуется.
Условия ниже — обязательная граница этого GO, а не уже проверенная реализация.

**Нет GO для MigrationPair, восстановления, GC, bootstrap/queue admission,
эффектов или приложения в целом.** T116/T117, legacy RED257 и B1 остаются
открытыми. Возвращаемое значение — результат проверки содержимого и отношений,
не доказательство текущего владельца, происхождения файла или полномочий.
Нативный RED/GREEN/SOURCE Round262 в этом отчёте не заявляется.

## Основание и свежесть

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Грязное дерево сохранено.
Повторно проверены feature prerequisites с `--json --require-tasks
--include-tasks`: активна Feature 200. Переданный cwd0309 не используется.

Использованы полностью прочитанные в текущем продолжении `speckit-analyze`,
`speckit-checklist`, AGENTS и guidance index; полное ранее прочитанное содержимое
constitution/guidance и активных требований сохранено в контексте, свежесть
проверена хешами. Повторно прочитаны относящиеся к решению §8/8.1, историческая
часть §8.1:516–546, packed §6.1, реальные Codec/Files/Metadata границы и
FR-012/013/022, SC-003/006. Принятые metadata-pair, bootstrap-codec и
migration-codec отчёты используются только в своих прежних узких областях;
не подменяют историческое нативное доказательство. Полный архив validation
не перечитывался и не объявлялся текущим нормативным checklist.

Risk lane: **high-risk-product**, существующий T116. Требуемый порядок:
requirements/checklist → scoped analyze → RED → реализация → независимый SOURCE
и фактические проверки. Hooks before/after analyze/checklist/implement:
для каждого этапа 0 enabled; commit и другие hooks не исполнялись.

Основные нормативные SHA-256:

| Файл | SHA-256 |
|---|---|
| AGENTS.md | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e` |
| windows-protected-local-custody.md | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |

## Качество требований и согласованность

Ниже — проверенные вопросы качества требований, не отметки выполненных тестов.
Отчёт не добавляет новую нормативную обязанность вместо согласованного §8.1
и не меняет reviewer-owned checkbox markers.

| Критерий | Вывод и обязательная граница |
|---|---|
| Определён ли исторический источник без g1 index? | Да: §8.1 прямо разрешает exact immutable block либо verified caller tombstone; отдельная функция не требует исторического индекса. |
| Отделена ли версия блока от JSON generation? | Да: direct ref generation=1, position=0, role=migrationIntent; block version exact из ref и >0, в том числе 17. Не использовать current generation или «наибольший файл». |
| Не ослабляется ли обычный decoder? | Да по предложению: общий внутренний разбор сохраняет все normal `openBlock` проверки expected payload length, exact total length, header/context/position/version/reserved/hash. Только новый role-specific вход допускает bounded inference. |
| Определена ли безопасная inference? | Да: DPAPI plaintext output ограничен header+65536 до native-to-owned copy; authenticated payload length положителен, ≤65536 и exact относительно plaintext размера до выделения возвращаемого payload. Cipher size не является plaintext length. |
| Полон ли cipher/native контроль? | Да: ref exact envelope size/hash, bound >16 и ≤69632; native entropy/user scope, outer/header kind/schema/IDs/role/position/version и payload SHA. Ошибки не превращаются в success. |
| Разделены ли current shape и его достоверность? | Да: текущий `CustodyMigrationValue` повторно проверяется существующей structural shape с независимыми own/tx/subject/directory; non-null valid barrier обязателен для вызова. Plain struct не аутентифицирует сам себя; действительная current-pair проверка — обязанность будущего владельца. |
| Полон ли birth semantic контроль? | Да: строгая migration.v1 schema, independently expected context/tuple, generation=1, prepared, null barrier/auth и все destination triples null. V2, aliases, malformed/duplicate/unknown fields не принимаются. |
| Полно ли сравнение receipt? | Да: весь anchor, source count и множество kind/length/SHA/destination object IDs совпадают независимо от порядка массива. Исторические null destination triples не сравниваются с поздними copied triples как будто это одинаковая стадия. |
| Не подменяет ли anchor fresh authority? | Да: anchor исторический; поздняя очередь может иметь новую generation. Это не разрешение rollback, upload, cleanup либо switch без fresh stamp/owner проверки. |
| Ясен ли confined reader? | Да: existing State::read и удерживаемые directory/identity handles, exact block.0.version; invalid role/version/size отвергаются до IO. Нет arbitrary path, indices/latest guessing, create/write/repair. |
| Определены ли ресурсные границы? | Да: существующие charged bytes/shared limits; plaintext≤64KiB, envelope≤69632. Выполнение worker-only под существующим native-job admission≤4; synchronous native завершение предшествует release владельцев. Нативная временная память отдельно ограничивается и проверяется, не выдаётся за charged memory. |
| Определены ли отмена и lifetime? | Да: будущий составной владелец удерживает job, Files lease и заимствованные inputs до выхода всех IO/native операций; cancel проверяется до/после bounded этапов. Отсутствие cancel у низкоуровневого Codec не делает его admission/owner API; нельзя force-free незавершённый DPAPI по timeout. |
| Сохранены ли privacy/failure требования? | Да: typed native/hash/allocation/io/context/unsafe ошибки, очистка временного plaintext, сохранение artifacts; без plaintext fallback, новых IDs, логирования JSON/контента и эффектов. |
| Ясна ли полнота будущего восстановления? | Да: обоих current slots, fixed old-name copy conflict и tombstone-only IO нет в этом GO; все явно остаются следующей owner-зависимостью. |

Scoped analyze: изменение реализует уже существующее §8.1 требование FR-012/013
и сохраняет запрет недоказанных deletion claims FR-022. Оно не удовлетворяет
целиком FR-012/013/014/022, SC-003/006 либо аппаратную/пользовательскую приёмку.
SC-003 не заменяется коротким metadata тестом; отсутствие устройства у теста
не является подтверждением всей производительности приложения.

## Разрешённые вопросы и границы

**REQ262-1 — длина birth payload, разрешено.** Текущий
`ProtectedCustodyCodec.cpp:144–164` требует exact expected длину. Barrier её не
содержит, а оба g1 indices законно заменены g3/g4. Новый
`openMigrationBirthBlock` ограниченно выводит длину из проверяемого нативного
блока. Не нужны новая schema, текущая длина intent либо ослабление обычного
`openBlock`.

**REQ262-2 — Pair и происхождение, разрешено исключением из scope.** Нет
`MigrationPair` API. Проверка предоставленного envelope допускает равный
содержательный результат для immutable block и caller-verified tombstone,
но не устанавливает местонахождение/отсутствие второй копии. §8.1 требует
отказать восстановлению при malformed/conflicting copy, даже когда другая
копия хорошая. Эта проверка обязательно остаётся в последующем owner scope.

**REQ262-3 — borrowed current value, ясно, не новый blocker.** Helper не
превращает passed struct в authenticated-current proof. Повторная shape
проверка необходима, но недостаточна для effect authority. Настоящая обеих
слотов/currentness/lease цепочка должна предшествовать будущему admission.
Возвращать plain value/typed validation result допустимо; normal/upload/delete/
GC/recovery permission и private proof constructor здесь не разрешены.

Нативные calls в низкоуровневых Codec/Files не должны создавать вторую систему
jobs/таймаутов. Их составной worker использует существующие admission/lease
правила; соответствие фактической реализации, очистка и отсутствие скрытых
допущений проверяются на SOURCE этапе. Это не повод разрешить UI IO или
назвать отдельный helper полным владельцем миграции.

## Что main должен доказать после RED

Это будущие испытания реализации, не результаты reviewer:

1. Реальная DPAPI fixture с независимо заданным own/tuple и generation1 birth
   block version17; текущие g3/g4 BOTH indices/ref/payloads действительно
   проверены существующим API, g1 index отсутствует. Под existing exclusive
   identity lease confined read + helper принимают точный birth.
2. Независимые wrong store/object/role/tx/subject/directory/ref generation/
   block version; exact cipher size/hash, повреждённый envelope/native отказ;
   semantic tamper заново защищён DPAPI, а не только сломанный cipher.
3. Birth non-prepared/generation≠1/non-null barrier/auth/destination triple;
   anchor mismatch во всех полях; source missing/extra/duplicate/kind/size/SHA/
   destination-ID mismatch. Перестановка валидного source массива успешна;
   current copied triples не требуют birth non-null triples.
4. Inferred payload bounds и overflow/truncation/header mismatch, v2/alias/
   malformed JSON; shared exact `openBlock` отрицательные проверки не
   ослаблены. Unsupported role/version0/envelope bound отвергаются до IO.
5. Confined missing/reparse/unsafe/hardlink/size failure, allocation/hash/native
   refusal с typed error и без repair/fallback; charged budget exhaustion и
   retry, временный plaintext/owners release на всех исходах. Worker admission
   и cancel/lifetime проверяются в реальном составном fixture, не dummy flag.
6. Helper даёт одинаковую содержательную проверку переданных exact bytes, но
   тест не объявляет это tombstone path/conflict proof. Нет записи, rename,
   удаления, root reconstruction либо permission при успехе.

Нужны фактические последовательные focused native Release/Debug, сохранённые
RED/source maps/receipts/raw logs и свежая SDK/portable проверка затронутого
источника по выбранному lane. Reviewer не запускает VM. Тесты не подтверждают
GC, tombstone-only IO, full migration, installed app или 50/50 native suite.

## Инвентарь и порог допуска

До этого нового файла: **118 .md** = 10 активных нормативных checklist и
108 исторических/контекстных отчётов. Активные итоги: **154 checked / 0 open**:
advanced-routing14, audio-capture24, calendar-launcher5, calendar-operation8,
calendar-wire5, packed-writer12, privacy-pause12, requirements22, security27,
ux25. Их свежие SHA совпали с полностью прочитанным нормативным состоянием.
Исторические отметки отдельно: **256 checked / 10 unchecked**; они не
переклассифицированы как новые обязательства. Этот отчёт содержит 0 checkbox
markers. После добавления: 119 .md, нормативные итоги остаются 154/0.

Хеш исходного инвентаря (sorted basename + space + file SHA + LF):
`ae8ee2f175d633faab712dbb407cf863cf9b06592eb8ce492f0151661a03930d`.
Задачи: **120 / 93 closed / 27 open**, неизменный tasks SHA выше. T116 CRITICAL
— владелец этого шага; T117/T118 HIGH и T120 CRITICAL остаются открытыми.
#7444 OPEN/current canonical ownership сообщён main; reviewer GitHub не
запрашивал и не менял, поэтому отдельный live tracker audit не заявляется.
Порог допуска: relevant reviewer requirements satisfied, scoped C0/H0,
нет неразрешённого продуктового выбора; это не закрытие task/issue.

Исходные source SHA-256 до RED, не SHA новой реализации:

| Файл | SHA-256 |
|---|---|
| ProtectedCustodyCodec.h | `a5152a136c102b285e5e34cc926a9c6da7f6c3c43a5acca5707069a757e3dcde` |
| ProtectedCustodyCodec.cpp | `5737c34d50bf8a765173a9284054fac90fe0c8ca6ef6d20cdfc3eb2ea9b4b2d3` |
| ProtectedCustodyFiles.h | `7b5587e240b66492f39410c87ea55ce62664f3308843556b96173410528f6ccf` |
| ProtectedCustodyFiles.cpp | `ae784b46f417c503e592410edd7dc71ab8131592f5cfeb04c235e0a96a817b82` |
| ProtectedCustodyMetadata.h | `910b8d5d20a1b5ecac18a563058c483c7aeefbbc65bead08ccd58251ea032004` |
| ProtectedCustodyMetadata.cpp | `1b261f470885988c1ef77ac64bd77d90897f55afbb91bfea3e942864db4fff74` |

Финальный вывод: **требования узкой самостоятельной исторической проверки
достаточно определены; RED разрешён.** Общий owner/recovery/GC/application gate
не открыт и не маскируется этим промежуточным результатом.
