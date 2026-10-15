# T116 — независимая проверка требований конкурентной cold inspection

SCOPED REQUIREMENTS / TEST-CONSTRUCTION GO. Scoped analyze: C0/H0/M0/L0.
Принята только уточнённая конструкция plan.md:2012–2036,2110–2149,
quickstart.md:936–962 и research.md:3013–3029. Это не SOURCE GO будущего
исправления, не runtime PASS и не закрытие T116 или полной Windows parity.

## Снимок и метод

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; проверены dirty bytes.
Feature pointer и однократно выполненный read-only prerequisites
`--json --require-tasks --include-tasks` указывают на Feature200.
Lane: существующий high-risk-product slice, не новая задача или прямая
низкорисковая правка. Прочитаны AGENTS/router, применимые spec-kit-flow,
product-gates, release-and-validation, tracker-policy, конституция,
активные требования/задачи и относящиеся к конструкции model/contracts.

Применён speckit-analyze: анализ без изменения исходных артефактов; отдельный
новый reviewer report сохранён по прямому разрешению пользователя.
before_analyze/after_analyze содержат только disabled commit hooks;
enabled hooks 0, ничего не исполнялось. Optional agent-context не нужен:
active feature/stack/router прежние. Commit не разрешён.

| Нормативный файл | Лично проверенный SHA-256 |
| --- | --- |
| spec.md | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| plan.md | 40443131fdafc41aa13ef98058e2fa95608dfdc1f60ae03d2ea6ab3acadb4868 |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| research.md | 901de067501da665dc3d28710c7691665a3d584f7bdcdb8f4f3c1a1ebbf8a774 |
| data-model.md | c24b9d10bf5b935bcf51bb12034a0bb9ccef4a0b3719a138b48a26cbaa0d3bc7 |
| quickstart.md | 6a070377de42113eea427d376f6b39beac5e222ca1dab31a69a85587b68f6dc3 |
| contracts/windows-protected-local-custody.md | 598223854ea7e614694167c4019ef199e30c82b3ac1c44b33fcefa94fbe27fee |
| contracts/windows-protected-packed-custody.md | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| .specify/memory/constitution.md, от корня | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |

Три заявленных новых SHA совпали. Остальные шесть совпадают с таблицей
прежнего scoped gate review-2026-10-10-protected-http-integration-gate.md,
SHA 51af545d0cc8a4dc31c5ea0d65595f08dcb6be2c8a4e2194ee3c3d8da90174e0.
Его утверждение «Proof готовится … storage worker» в строке37 относится к
прежней конструкции; только это распределение работы заменено текущим
уточнением. Старый отчёт и его hash table не переписаны. H1 prepare/full ACK,
H2 body/lifetime/quota и остальные ограничения продолжают действовать.

## Все текущие checklist items

Просканированы все187 Markdown-файлов папки checklists. Все420 checkbox items
в29 файлах лично перечитаны и проверены на применимость к трём уточнённым
артефактам. Десять постоянных checklist файлов содержат154 отметки;
19 датированных review файлов —266. Остальные158 файлов не имеют checkbox.
Для них выполнен поиск противоречащего распределения inspection/proof между
storage/network; найденная прежняя формулировка51af описана выше как история.
Большие исторические validation narratives заново целиком не аудировались.

Каждый пункт ниже сохраняет свой исходный смысл: качество требований либо
исторический source/runtime cut. Отметки не превращены в приёмку нынешней
реализации или новой конкурентности. Неподтверждённые будущие проверки не
отмечались; новых checkbox нет, существующие не изменены.

| Файл | Checked / unchecked | Результат проверки применимости |
| --- | --- | --- |
| advanced-routing.md | 14 / 0 | Граница native/shared loopback не изменена |
| audio-capture.md | 24 / 0 | Callback/worker, Stop, SC-003 и аппаратные gates сохранены |
| calendar-launcher.md | 5 / 0 | T119 не затронута, новой приёмки нет |
| calendar-operation.md | 8 / 0 | T119 не затронута, actual completion не заменён cancel |
| calendar-wire.md | 5 / 0 | Bridge/schema не изменены |
| packed-writer.md | 12 / 0 | Единственный mutator и admission/release не ослаблены |
| privacy-pause.md | 12 / 0 | T120 и durable OPEN/CLOSE не закрыты |
| requirements.md | 22 / 0 | FR/SC, native ownership и полный parity goal сохранены |
| review-2026-10-03-packed-tree-source.md | 38 / 0 | Source/runtime утверждения привязаны к прежним cut; не повторно приняты |
| review-2026-10-04-calendar-join-gate.md | 12 / 0 | T119 requirements вне изменения |
| review-2026-10-04-calendar-resolver-gate.md | 12 / 0 | Auth/resolver authority не переносится в pair/proof |
| review-2026-10-04-calendar-url-gate.md | 12 / 0 | URL policy не затронута |
| review-2026-10-04-manifest-cap-source.md | 9 / 0 | Исторический codec/source/runtime scope; cap не изменён |
| review-2026-10-04-packed-cadence-gate.md | 12 / 0 | Storage-only timing не подменяет product Stop/SC-003 |
| review-2026-10-04-packed-cadence-source.md | 18 / 0 | Исторические измерения, не concurrency acceptance |
| review-2026-10-04-packed-live-writer-gate.md | 14 / 0 | Guard/paired ACK/immutable roots остаются обязательными |
| review-2026-10-04-packed-live-writer-source.md | 9 / 0 | Историческая source/runtime приёмка не расширена |
| review-2026-10-04-packed-package-gate.md | 12 / 0 | Pair/parsed value не дают account/upload authority |
| review-2026-10-04-packed-reader-gate.md | 20 / 0 | Full verification, cancellation, pins и failure precedence сохранены |
| review-2026-10-04-packed-reader-source.md | 9 / 0 | Исторический источник и runtime, не новый SOURCE GO |
| review-2026-10-04-packed-resize-gate.md | 14 / 0 | Resize/old-reader/ownership-gap правила не изменены |
| review-2026-10-04-packed-resize-source.md | 9 / 0 | Исторический source/runtime scope сохранён |
| review-2026-10-04-packed-rewrite-gate.md | 16 / 0 | Structural diff/publication/limits не изменены |
| review-2026-10-04-packed-rewrite-source.md | 9 / 0 | Исторический source/runtime scope сохранён |
| review-2026-10-04-packed-tail-gate.md | 14 / 0 | Tail ACK не объявлен EOS/finalizer acceptance |
| review-2026-10-04-packed-tail-source.md | 9 / 0 | Исторический source/runtime scope сохранён |
| review-2026-10-04-packed-writer-source.md | 18 / 0 | Старые findings/receipts остаются историческими |
| security.md | 27 / 0 | Auth/deletion/diagnostics/least privilege без ослабления |
| ux.md | 25 / 0 | Native visible Stop и truthful states обязательны |
| Итого | 420 / 0 | Никаких новых implementation/runtime отметок |

Hash исходного набора187 файлов: SHA-256 UTF-8 JSON массива sorted
[имя файла, SHA-256 bytes], без whitespace:
d19bc253d9fe5a9f0777ea12e7ed634a0ca50a475e6b0a184e233db61841561d.
После нового отчёта файлов188; прежние187 и счётчик420/0 должны остаться
байт-в-байт прежними, отчёт содержит0 checkbox.

## Scoped analyze и покрытие

| Обязательство | Проверенные основания | Решение |
| --- | --- | --- |
| Свободный исполнитель prepare/finalize | FR-004/015; constitution I/II; plan:2012–2016,2110–2149; quickstart:936–962 | Полный media inspection/hash/AAC переносится в existing executor, не в UI/новый поток; это проверяемая конструкция, не обещание bounded native IO |
| Единственная authority и pair | FR-012/013; local custody §5–7; plan:2028–2036,2121–2131; model:597–617 | Mutable StoreOwner и current row/delete/account проверки остаются storage-worker-only; переносится тот же genuine pair, без второго readPackage/reopen или обычного DTO-адаптера |
| Полная проверка содержимого | FR-011/012/014; packed §2/§6; plan:2124–2125; research:3013–3029 | Existing inspectProtected и uploadProtected сохраняются; заголовок/decrypt/тип поля не заменяют полный hash/AAC/proof |
| Учёт и release | Local custody §5; packed §6; plan:2126–2131 | Один pair/inspection одновременно;32 — flight selection, не inventory/proof count. Owned64MiB/cache2MiB/pins32/jobs4 не увеличены; pair/proof/slot cleanup на worker до resultReady, включая cancel/exception/launch failure |
| Актуальность и result ACK | FR-013/014/022; local custody §5–7; plan:2032–2059,2129–2131 | Cancel/grant перед wire и fresh current-row/result commit/adoption сохранены; no effects без ACK/current; pending/lost poll удерживают ownership, ambiguous не становится успехом |
| Классификация отказов | FR-012/014; plan:2130–2131; quickstart:954–956 | Quota/key/IO/cancel не доказанная invalidPackage; отказ не включает plaintext fallback, пустой ledger или unsafe retry |
| Квалифицированный test-first cut | Plan:2133–2142; quickstart:942–953 | Настоящий nonempty packed read выбранного старого пакета, offset≥appendOffset, сохранённые bytes/LastError; actual reached-prepared, не queued. Отдельно обслуживание finalize, затем release cut до полного EOS/finalization/commit/adoption |
| Пределы доказательств | SC-003/006; plan:2144–2149; quickstart:958–962; research:3016–3029 | Packed IO marker не объявляется hash/AAC caller; factory/build/случайный timeout не named RED; dispatcher5s не full AAC bound; generated tests не hardware/installed/release proof |

Все8 scoped обязательств покрыты конструкцией/проверочным планом существующей
T116; непокрытых scoped обязательств0. Найденных scoped конфликтов,
блокирующих неоднозначностей, дублирующих алгоритмов/задач и нарушений
конституции0: C0/H0/M0/L0. Это не глобальный нулевой analyze всей Feature200.
Общий inventory:22 FR,10 SC; tasks120, checked93/open27. T116 строка568
остаётся open и прямо владеет Storage/Recording/Upload интеграцией, UI/callback
no IO и test-first регрессиями. T117/T118/T120 не заменены этим срезом.

Локальная связь T116→#7444 подтверждена tasks.md:550–568. Live OPEN и
канонические labels сообщены main в текущем запросе; reviewer не выполнял
собственный GitHub/network запрос и не выдаёт это за fresh remote audit.
Новая issue/schema/user-policy не нужна для данной внутренней механики.

## Что ещё обязательно и не принято

Текущий source manifest365:
f2ca944325fc48917d5a55326006edb4642bb15974ada8eeaf0cb34fcf71bd94.
Лично сверены209 canonical/frozen inputs —0 расхождений. Эти байты ещё
содержат прежнее размещение inspection; runtime365 в этом отчёте не принят.
Даже возможный последующий selected22 GREEN не примет новую concurrency
границу, отсутствующую в этом source и тестах.

Следующий допуск — написать минимальный test-first case в существующем
NativeCaptureStorageIntegrationTests и независимо проверить actual diff/harness.
Qualified RED требует подтверждённого packed cut и именованной проверки
actual preparation/service, а не произвольного timeout. Затем отдельно
исправление, source review и exact-source Debug/Release RED→GREEN, cancel/
logout/shutdown, wire0, pending/lost poll, result ACK, owned/pin/native drain.
Нельзя ждать полного finalizer под удерживаемым Guard/cache cut: это способно
само заблокировать обе реализации. Полный EOS и restart проверяются после
освобождения барьера. Кооперативная отмена не доказывает срок ReadSample.

Новых source freeze/native jobs до terminal365 и его postflight/idle нет.
Global storageWritable/localQueueComplete остаются false до всех consumers.
SC-003/60min,100cycles, retained display/playback/retry/delete/claim, T117/T118/
T120, installed/hardware/macOS parity/signing/release остаются отдельными
незавершёнными воротами. Полная Windows parity — цель, не суженная этим GO.

Единственная запись reviewer — этот новый report. Source/tests/spec/plan/
research/quickstart/tasks/markers/старые checklist reports/AGENTS не менялись;
VM/build/test/job/GitHub/hook/commit/release не запускались.

Финальный readback после записи:188 Markdown,29 с checkbox,420 checked /
0 unchecked; прежние187 SHA без изменений, девять норм без изменений за время
review,209 canonical/frozen inputs без расхождений. Новый report перечитан.
