# Round260: SOURCE — bootstrap.v1 codec

Дата: 2026-10-06. Независимая проверка корректности/безопасности через
`code-reviewer` и отдельная проверка формы решения через `ponytail-review`.
Область — чистый bootstrap codec существующего T116/§8.1, lane
**high-risk-product**. Реализация и исполнения принадлежат основному агенту;
рецензент читает исходники и экспортированные результаты, не запускает VM.

## Решение

**SCOPED SOURCE APPROVED** для текущего добавления в трёх файлах:
`ProtectedCustodyMetadata.h/.cpp` и `ProtectedCustodyPackageTests.cpp`.
**CRITICAL=0 / HIGH=0 / MEDIUM=0 / LOW=0** исправимых findings в этой области.
Принятый REQUIREMENTS gate Round260 не изменён и не расширен.

Это приёмка структурного codec и относящихся к нему доказательств, **не
protected bootstrap/queue admission, миграция, подключение writer/очереди,
весь T116, установленное приложение или выпуск**. Legacy RED257/B1 сохраняются;
свежий отдельный legacy260d ниже подтверждает, что старый consumer не исправлен.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty preserve.

## Лично проверенные исходники

Полностью прочитаны текущие три файла, relevant diff/старый package baseline,
§8.1, REQUIREMENTS260 и используемые `CustodyBytes`/allocator semantics.

| Проверка | Основание в текущем коде / результат |
| --- | --- |
| Форма и независимые ожидания | `.h:10–30`, `.cpp:29–37`: фиксированное владеемое значение без input views; роль bootstrap, точные own store/object/generation и отдельный queue ID; generation0/schema mismatch/unknown enum отвергаются |
| Все три сочетания | protected требует три null; migrating требует transaction+subject; queue — null directory; package — непустая ASCII identity≤300. Нет дополнительного запрета zero/equal IDs |
| Обязательные поля и дубликаты | overload `PackageJson::read` с девятью известными ключами, mask511 и полным EOF. Проверка ключа после escape decoding и до чтения значения; default struct не скрывает missing/null/type error |
| Строки/числа/вложенность | Общие primitives не изменены: token300, ASCII/escape checks, lowercase hex после decoding, exact unsigned `from_chars` без float/overflow/leading-zero; все accepted поля закрытые ASCII. Неизвестные вложенные формы не пропускаются; bootstrap depth1/keys9 ниже общих пределов |
| Directory граница | `std::find` внутри array301; parser копирует≤300 в нулевой initialized array. При writer массив301 без terminator имеет length301 и отвергается, пустая/невалидная identity также; null представлен отдельным optional |
| Отказ целиком | `.cpp:225–230`: empty/>65536/parse/shape failure возвращает no value + invalidPlaintext, не fallback/default/partial result |
| Запись и память | `.cpp:232–250`: shape до allocation, charged reserve65536 до plaintext, каждый emit ограничен remaining cap; `to_chars`20 хватает всему u64; quoted принимает только validated grammar. No growing/unwiped prior buffer; bad_alloc/length_error имеют typed no-value outcomes |
| Жизненный цикл | Результат не удерживает JSON; parser token wipe, штатный CustodyBytes wipe/release при исключении/переносе результата. Нет native IO/job/stream/COM, timeout, path, account или effect factory в новой части |
| Совместимость | При удалении только новых bootstrap блоков **в памяти** восстановлены побайтно три SHA из REQUIREMENTS260 — прежние package parser/writer, metadata pair/commit и все прежние package tests сохранены |

Последняя проверка дала восстановленные SHA:

- H `3e1f12fda3e18463c6430921e16173afac5c549aaebfa222efcc9dd24b743478`.
- CPP `c917b43a94d09547be829694b6cf9c44efde0f91d03dce4c931d8534fa68a1f7`.
- Tests `6bb176332bceb6fd195d1eacb3c3ea4af827d029a03b819d3c30ab7397e9f3e6`.

Это read-only сравнение строк и хешей, не изменение/восстановление файлов.
SDK179 diff относительно SDK259i также содержит ровно эти три входа.

## Матрица теста и ограничения её смысла

Новый `bootstrapTests` проверяет три допустимые формы, roundtrip/determinism,
порядок/whitespace, escaped ASCII keys/IDs/identity, UINT64_MAX, identity300,
zero/equal expected IDs. По отдельности проверяются missing/decoded duplicate
каждого поля, wrong types/null, unknown/schema aliases, 72 сочетания
mode×transaction×subject×directory, own role/store/object/generation/queue
mismatch, invalid writer enum/shape, числовые и строковые границы, BOM,
invalid UTF-8/escape/surrogate, nesting/trailing, exact65536/+1.

Shared-budget test: reader при полностью занятом бюджете, writer allocation
refusal без value/утечки, invalidInput до allocation, release и успешный retry.
Assertions включены в Release (`#undef NDEBUG` до `<cassert>`); в конце
проверяется возврат shared owned count к начальному значению. Старые package
v1/v2 и packed reference assertions исполнены после новой матрицы в GREEN.

`accepted=15 rejected=173` — счётчики вызовов нового `check` helper, **не
количество всех assertions** и не число native security/effect сценариев.
Тест purecodec не доказывает durable own slots/fixed queue/intent/currentness.

## Лично прочитанные экспортированные доказательства

Внешний каталог: `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI`.
JSON с возможным WinPS UTF8 BOM разобран после снятия BOM **только в памяти**;
хеши вычислены по исходным bytes, файлы не нормализованы и не переписаны.
Все raw logs прочитаны целиком, а не только строка PASS.

| Исполнение основного агента | Что независимо прочитано |
| --- | --- |
| RED260a | terminal failed, configure0/build0/test8; source172 receipt map = frozen RED map; один Release PackageTests, assertion `bootstrapDecoded.ok()` line46, raw2.27s. Это RED stub до code, не прохождение старых assertions после точки отказа |
| Release260b | terminal passed, configure0/build0/test0; два targeted tests — PackageTests raw0.06s, FilesTests raw25.43s; новая строка 15/173/refusal1/retry1. Основной агент сообщил CTest total25.50s; LastTest raw содержит per-test времена, не эту итоговую сумму |
| Debug260c | terminal passed, configure0/build0/test0; PackageTests raw0.89s, FilesTests raw36.46s, та же строка15/173. Основной агент сообщил total37.38s; raw per-test времена отделены от этого сообщения |
| SDK260e | terminal passed, restore0/build0, mode full-sdk-app-build-only; receipt179 map = frozen SDK179 map = current canonical. Это сборка, не launch/install/MSIX или acceptance |

FilesTests raw содержит прежние generated AAC 1s/30s, damaged rejection и
45 normal/privacy +14 degraded строки. Release явно SKIP-ит три debug-proxy
fault relevance проверки, Debug показывает charged proxy path; эти различия
не выданы за одинаковую полную матрицу. Новых устройств/реальных записей нет.

Лично вычислены все172 hashes canonical Windows inputs и сравнены с GREEN
map: **172/172 MATCH**, Release receipt map MATCH, Debug map тот же172 и MATCH.
RED→GREEN172 отличается только Metadata.cpp и новым test; header одинаковый.
SDK179 **179/179 MATCH**, его receipt map MATCH, относительно SDK259i ровно3
изменённых inputs. Рецензент не перечитывал NTFS/EXE через VM: ниже EXE SHA
взяты из лично разобранных receipt, не заявлены как его собственный reread.

| Экспорт | SHA-256 исходных bytes |
| --- | --- |
| source-bootstrap-round260a-red.json | 25725d47a52ff9c7256c2b8fa8e1f7bc4b0c08be782dac7c6f98010affd1ff75 |
| graf-f200-bootstrap-round260a-red.json | a35241661bd157494b1317c8d4a45938937711b7a34d39f3404c3ef0da38fd78 |
| graf-f200-bootstrap-round260a-red-test.log | 7833928f9146666190fa3ff177403c9ddf2ec0a8f07b6fbc7d318809bc9be8c3 |
| source-bootstrap-round260b-green.json | 9f8eade9b63abd98eefaf705233a30b4a064a13c0b6980ffe1471cc94fd36559 |
| graf-f200-bootstrap-round260b-green.json | 78896ac0cb1454b21893cb0904539d413bc94b1e4b23f9c034aa31e9ffa9dfa3 |
| graf-f200-bootstrap-round260b-green-test.log | b6b45d0328057d7c94c70da2972ef6243986e8cf5f564b7095c2560a3324b1ab |
| graf-f200-bootstrap-round260c-debug.json | 4dc1e29e79044de2ef82d3a50011c140901349dd0a70e1030dc7e30278e605d0 |
| graf-f200-bootstrap-round260c-debug-test.log | 522c7e20e3d516395fe889abdcb90d60933c0d8f21e1b5c4d782848fb69eb3c4 |
| source-sdk-round260e.json | a0f402f36e6646400882972533b376591ce670e502d099fb21450275319e77b5 |
| graf-f200-sdk-live-round260e.json | 5f457f831c3c9a21c950d2ef8f9c17bca8b2e4f952c85d53dd32774272a4bd7f |

Receipt EXE hashes:

- RED PackageTests `229a2c8a67e1b528c7d54c3bf5085d31c77b563e291d25bfa914771dd725a428`.
- Release PackageTests `16f66084cb721cec8c678570ea9be9361c326ae054ba4167226bbd93890f4633`;
  FilesTests `87183c71135475d0b3a9488cfa2e1e0ba4b20696f07b540c12a90678f557ed46`.
- Debug PackageTests `c37c6ceddc3b04f74f05a03b7dc8434a8701c0b862a50a36a0997d3759f9b461`;
  FilesTests `b9d13cf0dc048c4e85d269b1cda207fee23b4c35506b9023be15ead65c1fc3d6`.
- SDK app `88d076d621b23386bd114017863ecd8c30fd011a475cbea7eb44079e87873418`.

Portable46/46 PASS15.43s сообщён основным агентом; здесь не воспроизводился
и отдельным лично прочитанным portable raw log не подтверждался.

## Актуальный legacy NO-GO не скрыт

Лично разобраны `graf-f200-bootstrap-round260d-legacy.json` и raw `-test.log`:
terminal failed, configure0/build0/test8, тот же frozen172 map MATCH; **один**
NativeHashFailureTests raw2.49s, не full suite. Воспроизведён assert395:
original_frames48128, corrupt_decode_complete1/corrupt_frames0,
explicit_root_normal1/playback1/default_root_normal1,
invalid_package0/synthetic_sends1. Нельзя называть это native decoder HRESULT
error: данный повреждённый fixture достигает EOS с нулём decoded frames,
а прежний path consumer неправомерно выдаёт valid и начинает injected send.
Bootstrap codec этот path не меняет. Legacy RED257/B1/T116 adoption остаются
открыты независимо от корректности данного структурного prerequisite.

Legacy receipt SHA:
`fd376ab0c6458b61be9b0f5c298236940f8ba36067e010b6e8f44c0de420a10a`;
raw SHA `c53e44c32e8e9b6c018437fc0f6ccec168ce6905bc6752bf8528c8f712d82c69`.
Legacy EXE SHA в receipt:
`3fbb430dcf6942a2d65b7a9c57538a2d85cd58c44b1bcd2e4cb66a7e228ccb28`.

## Ponytail и сохранность

`Lean already. Ship.` — только verdict формы этого purecodec, **не разрешение
выпуска**. Существующие parser primitives используются напрямую; fixed shape
и отдельный малый writer не требуют нового DOM/класса/адаптера. Безопасных
сокращений без ослабления closed grammar/ошибок/регрессий не найдено.
Ничего не удалено и не переписано рецензентом.

Точные frozen source SHA:

- H `8cbf848fa864bc50298e2d0bb30d6bf7d2225e1c0258cef184959d981ffd3eec`.
- CPP `09d0d0d66037c1c0231dd92400e97430b4a2d4b71d3ba3ef540c8e5d546f6c6c`.
- Test `833eab30402e0743bf1c90ffed382c62fca400c7eda2814bd0b3e25852d8571d`.
- REQUIREMENTS260 `dffd526cd25d552155c790010c42845724807f29370355aa82ea0eb2380e4a98`.
- tasks `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`;
  120 total /93 checked /27 open, неизменённый.

До этого SOURCE отчёта115 старых `.md` checklist/report файлов. SHA инвентаря
sorted basename + space + file SHA + LF:
`0fb7af28b5db356473fdce78fab463945e528c0c309a787db2868b67cb54ea44`.
Все прежние файлы и markers immutable; текущие10 нормативных checklist
остаются154 checked/0 open, исторические256/10 считаются отдельно.
Рецензент записал только этот новый файл. Code/tests/spec/plan/tasks/oldreports,
GitHub, VM, профиль, commit/release не изменял; никаких production/fullnative/
installed/effect/hardware claims из scoped approval не следует.
