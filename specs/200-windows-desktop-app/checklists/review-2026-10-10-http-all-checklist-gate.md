# F200/T116 — текущий ALL-checkbox gate после исторического согласования

**STOP / FAIL: 419 checked, 1 unchecked.** High-risk ALL-checkbox gate из
`.agents/skills/speckit-implement/SKILL.md` §2 применяется ко всем Markdown
в checklists, не только к нормативным требованиям. Исторический статус файла,
scoped C0/H0 и согласие пользователя принять риск не исключают оставшийся пункт.

## Снимок, действия и предел доказательства

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
branch `codex/200-windows-followup`;
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Проверены dirty bytes.
В рамках обязательного независимого ревью Spec Kit, по поручению основного агента,
независимый reviewer изменил ровно9 старых маркеров
в3 reviewer-owned reports и дописал обоснования; этот файл — единственный
новый gate report. Старые findings, failure/pending формулировки, исходные
cut counts и атрибуция main сохранены. Ниже — текущие физические counts,
которые заменяют прежнее исключение historical checkboxes из общего gate.

Перечитаны последующие source/terminal разделы трёх отчётов, соответствующие
validation Round218–219/228/229 и текущие исправленные source/test границы.
Исторические terminal результаты — документальные receipts main, а не
личное выполнение reviewer или новое чтение guest binaries/raw runtime logs.
Старые SHA ниже не объявляются identity нынешних209 inputs. Нормы/tasks/code,
GitHub state, jobs/native/VM/CUA не изменялись; сборки/тесты не запускались.
`code-reviewer` применён для exception/lifetime/test-boundary проверки;
`speckit-implement` — для буквального reviewer-owned gate.

## Девять согласованных старых пунктов

| Исторический пункт | Последующее точное evidence, перечитанное reviewer |
| --- | --- |
| tree VS95823 | Tree report около562: main terminal Rebuild0/Core0 для cut16. Закрыто ожидание terminal результата; EXE0109… остаётся только prefix, не independently verified binary SHA. VS61697/Core58899 — отдельный frozen18, не подмена95823. |
| tree H3 | Frozen18 Codec.h a5152a…/Metadata.h7d05cf…/Metadata.cpp739b40…/FilesTestse00d64cf…; полные SHA в append и финальной таблице tree report. Isolated37585 и partial-headroom49243 отделены; финальные Debug96206 focused4/4 EXIT0, Release16265 full41/41 EXIT0, portable97843 39/39 EXIT0 подтверждены также validation Round218–219. |
| cadence PCD003 | Corrected OwnerTests454febc71de0c1d1ef787f699afe79a8b1d612543dda8be7594c0b6824e66c23: exact nodeL0/L1/L2 исключают HEAD; текущий observer225–230 перечитан. |
| cadence PCD004 | Corrected/current assertions404/406: DATA1/NODE≤3/flush2, append≤290816B, не resize cap. |
| cadence PCD009 | Report final + validation Round229:66321 build0/Release41/41 PASS215.52s;83905 Debug short0;75226 portable39/39 PASS11.30s; два corrected64MiB terminal0;98391 guest6/source и test-binary SHA. Каждый receipt относится к corrected454febc freeze. |
| Writer PWW003 | Guards gap→DATA, flush→shrink, byte ACK, actual root/lease/adoption; corrected cancellation CLI91577 Release/20733 Debug EXIT0, HEAD reads3. |
| Writer PWW005 | Same-owner fault/revocation до RAM/input/no-op/cancel, sticky native cause; admission3causes×4actions91577/20733 EXIT0. Healthy read после revoke сохранён. |
| Writer PWW006 | Charged State/Writer wrapper, прежние limits; resources91577/20733 EXIT0: owned/wrapper/pin/job/dirty refusals, baseline, actual wipe-before-free. НЕ ALL HTTP allocations. |
| Writer PWW009 | Report final + validation Round228: Writer.cppdc1e9cc31ae90186f73d989602895026cff58c2bdb34414b25ffa3f91ad6a4fd, OwnerTests2a30db694c70c0858fb39057c4a33ab443c6ab4723478398aa9988abd2939923;38336 build0/Release41/41 PASS250.90s,91577/20733 CLI+Tree/Files,44507 portable39/39 PASS11.33s. Observer failures86409/18481 остаются отозванными, не product RED. |

Полные pre-reconciliation report SHA и текущие source SHA сохранены в
append каждого изменённого отчёта. Их нынешние контрольные суммы:

| Report | checked/unchecked | SHA-256 после согласования |
| --- | --- | --- |
| review-2026-10-03-packed-tree-source.md | 37/1 | `8810e2dbfdc8099c92d0a43402343a14187c5bed6ab14419f4450c25a4bb961d` |
| review-2026-10-04-packed-cadence-source.md | 18/0 | `ab25a6daef6d992199542ec340edbf8b873b85976daf9bfb5ffc82ba924b2f74` |
| review-2026-10-04-packed-writer-source.md | 18/0 | `5171fa791058d63856283b4cf187a02e7cc7b03b635213ec1642a043d60421fe` |

## Полный подсчёт Markdown

До записи этого файла:171 Markdown,410/10 до согласования →419/1 после.
С этим report: **172 Markdown,420 items,419 checked/1 unchecked**.
Просканированы все файлы;29 имеют checkbox,143 имеют0 items, включая этот
report. Ни один historical marker не исключён. Таблица содержит все29
файлов с markers; остальные143 дают ровно0/0 и не скрывают open items.

| Markdown с checkbox | Total | Checked | Unchecked |
| --- | ---: | ---: | ---: |
| advanced-routing.md | 14 | 14 | 0 |
| audio-capture.md | 24 | 24 | 0 |
| calendar-launcher.md | 5 | 5 | 0 |
| calendar-operation.md | 8 | 8 | 0 |
| calendar-wire.md | 5 | 5 | 0 |
| packed-writer.md | 12 | 12 | 0 |
| privacy-pause.md | 12 | 12 | 0 |
| requirements.md | 22 | 22 | 0 |
| review-2026-10-03-packed-tree-source.md | 38 | 37 | 1 |
| review-2026-10-04-calendar-join-gate.md | 12 | 12 | 0 |
| review-2026-10-04-calendar-resolver-gate.md | 12 | 12 | 0 |
| review-2026-10-04-calendar-url-gate.md | 12 | 12 | 0 |
| review-2026-10-04-manifest-cap-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-cadence-gate.md | 12 | 12 | 0 |
| review-2026-10-04-packed-cadence-source.md | 18 | 18 | 0 |
| review-2026-10-04-packed-live-writer-gate.md | 14 | 14 | 0 |
| review-2026-10-04-packed-live-writer-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-package-gate.md | 12 | 12 | 0 |
| review-2026-10-04-packed-reader-gate.md | 20 | 20 | 0 |
| review-2026-10-04-packed-reader-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-resize-gate.md | 14 | 14 | 0 |
| review-2026-10-04-packed-resize-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-rewrite-gate.md | 16 | 16 | 0 |
| review-2026-10-04-packed-rewrite-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-tail-gate.md | 14 | 14 | 0 |
| review-2026-10-04-packed-tail-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-writer-source.md | 18 | 18 | 0 |
| security.md | 27 | 27 | 0 |
| ux.md | 25 | 25 | 0 |
| Остальные143 Markdown без checkbox | 0 | 0 | 0 |
| **Итого172 Markdown** | **420** | **419** | **1** |

Отдельно, только для классификации:10 standalone normative checklists154/0,
остальные162 Markdown265/1. Это НЕ альтернативный PASS gate.

## Единственный оставшийся checklist blocker и действие для закрытия

`review-2026-10-03-packed-tree-source.md:586`: exact engaged-snapshot
worker error-return fault execution остаётся unchecked. Последующие
metadata-pair/package-assembly/package-authority/package-members reports
прямо сохраняют этот пробел.

Current `ProtectedCustodyFilesTests.cpp:1292–1372` metadataMoveBudget
проверяет pre-IO refusal, direct ctor/emplace moves и second-rename pressure.
Second rename может отказать внутри publishIndex/readback до engaged
snapshot. Ни один из этих сценариев не различает исполнение
`Metadata.cpp:1647–1650` с уже заполненным result.snapshot и очистку
`reject:1556` именно этого snapshot.

Для закрытия требуется отдельно разрешённая точная regression/evidence:
successful reopen и engaged snapshot → отказ allocating final transfer
без зависимости от optional NRVO → ambiguous/allocationFailed, snapshot
absent, фактические lease/pin удержаны, writes blocked, затем resource drain.
Тест должен отличать эту ветку от раннего readback failure; необходим terminal
receipt с exact frozen test/source/command/config identity. Reviewer после
проверки evidence сможет закрыть исходный маркер и пересчитать gate.
**Новый T116 implementation до этого не допущен.** Общий PASS существующего
набора/full320 не заменяет отсутствующий различающий тест. Это coverage/gate
blocker, не утверждение о новом доказанном product defect.

## Текущие source SHA, лично снятые и повторно сверенные

| Файл относительно apps/windows | SHA-256 |
| --- | --- |
| RecApp/Storage/ProtectedCustodyCodec.h | `ef725ea1bc07c6a6905f801dcf63d94f7827b4e630ca301d69ec4f6dabcc906b` |
| RecApp/Storage/ProtectedCustodyMetadata.h | `e6ff8be26942647129a90110e617a72e7be6260904ff5e56b2227700e7b9dce9` |
| RecApp/Storage/ProtectedCustodyMetadata.cpp | `82e7bd60e3bde12acef730013f9de6b4fe26bab82af4078e61fb868ad69e4f13` |
| RecApp/Storage/ProtectedCustodyWriter.h | `855547cc256f6f5a73fbff82c6d3c3d96188f45b53771ae198316a7593b090f9` |
| RecApp/Storage/ProtectedCustodyWriter.cpp | `a0fe79760d101b4aec8e72f311bd3972dd5c88266f217e6cb973b159a2255a0a` |
| RecApp/Storage/ProtectedPackedCustodyTree.cpp | `c308ac7159695a5a1e8edc1c65a1332481c576fff4f53b2ab270c99960d97391` |
| Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | `fb599aafc0ab790edb2db787562031c350ba198e413c8376e446cfbfc014a250` |
| Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp | `ca4e041ca15b978e6573e3473fe8ac003b166ac313bbc46c54a643bfbcef3205` |
| Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp | `a2f571035624f76bede9df4643d7daec3aa778b85d1cac8e64c921fc73664490` |

## Принятые нормативные9 — identity повторно подтверждена

Все9 current SHA совпали с принятым HTTP supplemental gate
`review-2026-10-10-protected-http-integration-gate.md`,
SHA `51af545d0cc8a4dc31c5ea0d65595f08dcb6be2c8a4e2194ee3c3d8da90174e0`.
Его scoped requirements/analyze C0/H0 остаётся привязанным к неизменным
документам, но прежний вывод о допуске не отменяет нынешний ALL-checkbox STOP.
Нового полного feature analyze или SOURCE/ALL-quota GO этот report не выдаёт.

| Артефакт | Current SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `9cdc5200419b6264d8e0c6a8c01aca5956b225661e674bba49acecbc4b90cf21` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| research.md | `4a7a1f9d8f7606a106b68e5b6194a0de8d75243508232c191f945f0fc0faa90e` |
| data-model.md | `c24b9d10bf5b935bcf51bb12034a0bb9ccef4a0b3719a138b48a26cbaa0d3bc7` |
| quickstart.md | `44c93c6558e8564aefe15a2180fd22d117f6368307d865b02253f9e0dffdf0b9` |
| contracts/windows-protected-local-custody.md | `598223854ea7e614694167c4019ef199e30c82b3ac1c44b33fcefa94fbe27fee` |
| contracts/windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

Tasks:120 unique,93 checked/27 open; T116:568 OPEN, T120 OPEN.
Read-only `gh issue view7444 --repo yshishenya/graf` подтвердил
[#7444](https://github.com/yshishenya/graf/issues/7444) OPEN,
title `[200][P0][storage] T116: Защитить всю локальную цепочку записи без открытых временных копий`,
body `Spec tasks:T116` и весь результат строки T116, labels feature:200,
priority:P0, area:storage, gate:pr-blocker, type:hardening.
Это существующий task-backed owner issue; assignees=[] — личный исполнитель
GitHub не назначен. Проверка не объявляет полную синхронизацию всех120 задач.

Full320 handle15840 running по сообщению main; reviewer не проверял live
процессы, не менял harness и не принимал terminal/full PASS. Нет runtime,
installed, release или полного T116 GO. ALL HTTP quota, scheduler/result
continuation и T120 остаются незавершёнными независимо от этого согласования.
