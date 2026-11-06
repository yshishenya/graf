# Round265 — SOURCE: частный queue decoder и позднее принятие candidate

## Решение

**REQUEST_CHANGES / scoped SOURCE NO-GO** на конечных inputs265a2/d2:
CRITICAL=0, HIGH=0, **MEDIUM=1 (SRC265-1, P2)**. Одно обязательное исправление
нарушения принятой классификации malformed content; зелёная существующая
матрица не содержит этот countercase. Requirements gate остаётся принят:
`review-2026-10-06-queue-load-candidate-gate.md`, SHA
`8703c09d254a584a50a706eada5cf9270f3088a5681fd55308736c771007b8fe`.
Он не является approval фактической реализации.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; lane `high-risk-product`, T116/#7444.
Прочитаны текущий diff, весь вынесенный parser/load, persist и guards caller,
новая матрица существующего V2 target и её сохранённые compatibility tests.
Лично прочитаны `code-reviewer` и `ponytail-review` skills; optional preflight
не выполнялся: main владеет исполнением, reviewer не запускает VM/тесты.
Запись только этого нового отчёта, без изменения code/tests/старых отчётов,
checklist markers/tasks/spec/plan/GitHub/commit/runtime/profile.

## SRC265-1 — malformed stamp ошибочно становится execution failure

Место: `Upload/DesktopUploadQueueService.cpp:306–315`; актуальный CPP SHA
`c3370c1afeb0a000b68eb7df07454108e7c03689c62bf6679e0aab46934d93f9`.

Синтетический документ оборван сразу после цифр document stamp:

```json
{"schema_version":"desktop-upload-queue.v3","items":[],"updated_at_ms":0
```

Source-derived цепочка, **не исполненный reviewer тест**:

1. `find_first_not_of` возвращает `std::string_view::npos`.
2. Проверка307 отвергает только `stampEnd == cursor`, не npos.
3. `substr` до конца и `stoull` успешно разбирают `0`.
4. `cursor = stampEnd`, затем `json.compare(cursor, ...)` бросает
   `std::out_of_range` из-за позиции npos.
5. Общий catch load206–210 возвращает false/quarantined без rename.

Old projection не публикуется частично и effects остаются blocked — нет
заявления о потере данных или успешной отправке. Но повреждённый JSON
ошибочно относится к IO/allocation/writer failure: не выполнен согласованный
quarantine backup для malformed content. Старый parser тоже имел этот
непроверенный npos, но новый catch теперь делает его частью неправильной
классификации; прежнее поведение не является нормой, разрешающей этот путь.

Минимальное исправление в существующем decoder:

```cpp
if (stampEnd == cursor || stampEnd == std::string_view::npos) return false;
```

В existing V2Tests добавить обрыв после цифр stamp с прежней непустой
projection: false/quarantined, старые items/operations/ACK сохранены,
source bytes в `.quarantine`, без candidate persist/effects. Нормальные
v2/v3 bytes и grammar не меняются; новый parser/class/schema не требуется.
После исправления нужны свежие frozen maps и применимые проверки нового
исходного кода. Current PASS не закрывает SRC265-1. Это finding данного
source review, **не новый task или дубль legacy AAC**.

## Остальные проверенные свойства текущего кода

| Область | Прочитанный результат |
| --- | --- |
| Частный decoder | H401 private; единственный вызов CPP179 на freshly constructed candidate. Parser не открывает файл, не rename/persist/stamp и не выдаёт публичную protected authority. |
| Совместимость | Existing emitted v3/read-v2 и logical `schema_version` сохранены. Переносит прежние field helpers/duplicate checks/server fields; нет нового строгого protected JSON codec. Root check перенесён наружу, numerical catches уточнены. |
| Bounds/read | CPP150–174: ate/tell length checked≤4MiB до resize, seek/read checked, gcount exact, extra byte/eof/bad guard. Input scope завершён до required rewrite; oversized close перед quarantine. |
| Candidate | CPP176–203: root checks после decode, copying прежних writer/root/clock, uploading recovery и v2 stamps только на candidate, required persist до swaps трёх vectors и document stamp. Swaps standard-allocator vectors не делают следующую allocation. |
| Failure | Live projection не очищается в начале/при failed decode/rewrite. Failure flag сохраняет known ledger, false/throw writer и allocation доходят до non-renaming fence; malformed returns идут к rename, кроме SRC265-1. |
| Known/missing | CPP155–158 и202; persist1266 ставит ledgerKnown только при saved. Даже known empty stamp0 missing — failure; прежняя quarantine/nonempty projection/sentinel не считаются virgin. Valid replacement может снять fence. |
| Числовые exceptions | CPP79–80/95–96 и311–312 ловят только invalid_argument/out_of_range, bad_alloc не превращается в content failure. Parser map/set allocations тоже могут выйти в load catch. |
| Caller | AppMain ctor600 — existing sole production load, bool ignored, дальнейшая пригодность основана на quarantine. Queue nextPending/pendingItems и completeLocalPurgeTask проверяют quarantine до выбора/effect/ACK. Retained getter не становится effect authority. |
| Scope | Startup IO остаётся синхронным, plaintext root/path reader не получает pin/lease/native job/account epoch. Новая private value copy не является protected queue owner или typed durable ticket. |

Изменён ровно существующий трёх-input slice относительно264b172:
QueueService.h/.cpp и DesktopUploadQueueV2Tests.cpp. `validServerOrigin`
public relocation уже присутствовал в предыдущем accepted input; его HEAD
diff не является новым расширением API265. Нет новой зависимости/target.

## Test source и пределы доказательства

Новая матрица V2Tests174–376 прочитана: повторный ACK load без rewrite;
late malformed item/operation/ACK/tail и invalid package root; retained
owner/ranges/retry state, guarded nextPending/markUploaded/purge/recycle;
numeric-helper bad_alloc и load-buffer bad_alloc без source rename;
directory IO failure; removal ACK через valid replacement; false/throw
uploading rewrite и false/success v2 rewrite; missing known/nonempty,
known empty stamp0 и virgin; exact4MiB/+1. Existing tests после нового
блока остаются исполняемыми при GREEN, не удалены ради результата.

Allocation interception следует existing test executable pattern и не
вводит production seam. Numeric1024-digit token достаточно велик для
allocating conversion; установленный диапазон не равен whole read buffer.
Тест подтверждает consumption fault и original-name bytes, не доказывает
отказ каждого возможного allocator/native allocation. Исправление только
numericMarker после C4456 не меняет production logic.

Writer callback проверяет прежние live row/status/operation/ACK до возврата
false/throw. Нет отдельного полного сравнения private document stamp в
callback; его позднее присваивание подтверждено source. Valid replacement
test использует пустой ACK array, не отдельный случай полного omission поля.
Short-read/growth/seek race не инъецировались детерминированно — это SOURCE
guards, не выполненная OS-race матрица. Не заявляется exhaustive OOM в
неизменённых noexcept filesystem helpers, shared64MiB protected budget,
race-free retained IO или полная migration/queue/admission приёмка.

Ponytail, только сложность: **Lean already. Ship.** Безопасных удалений,
новой абстракции или дублирования parser не найдено. Это не correctness
approval и не отменяет REQUEST_CHANGES по SRC265-1.

## Лично прочитанные immutable exports

Root: `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI`.
JSON BOM удалён только в памяти перед parse; файлы не переписаны, SHA
считался по исходным bytes. Canonical map172 и SDK map179 сравнивались
по каждому path/hash, mismatches0; RED/failed-build maps отдельно historical.

| Artifact | SHA-256 / проверенный результат |
| --- | --- |
| source265r-red172 | `7aebc6ca03805813d0707a623feb56134d362162b0c9c81c5e70bfa03439c5a1`; old CPP/H, isolated regression target source |
| receipt265r-red | `b34b9a3ac77eb1d22b80bc1d4870f4a46b9d66ed49991435a43e16b875533da3`; terminal failed, configure0/build0/test8 |
| raw265r-red | `745f228475530ff55ee69d322f80833eb3c6d49ccdfc10e9e933ebcef312580b`;5 PASS/1 FAIL, repeated ACK assertion207 |
| receipt265a failed build | `2f6e028093c7d73a9f88967467b1b0349ccd5b78ef04b5de794dc27fa81448ab`; build1/test null/exe map0; не test evidence |
| source265a2-release172 | `a87bccac22ac4c0c4a0d4ddbeb7e4dd98f9521e805fe9aa989e3b893cca4d264`; canonical172 MATCH |
| receipt265a2-release | `7fd8f369c70c12eb7e416559c46e5be1823c74b5ddb9071cc7f025553cc1ea03`; terminal passed, configure/build/test0, exact172 map,6 EXE hashes |
| raw265a2-release | `98a288665249652004b964d6bc25d6351e185ee8c4b91b78ee5a7b6d1b1a8c8e`; actual Release commands,6/6 PASS |
| receipt265b2-debug | `dc0a571721b77762c2b83d1186db77823bb614bda2c70312395c215237bb74bd`; terminal passed, configure/build/test0, exact172 map,6 EXE hashes |
| raw265b2-debug | `6e2c75da8b0af4f761d8c688f4121ac312400337aecff99171f866acdf179d97`; actual Debug commands,6/6 PASS |
| raw265-portable2 | `1bf5d21a07f929f8a1650973e05f9f7d372174d27591a89288a6dc68d6de078e`; Mac paths46/46 PASS; не native branch/platform acceptance |
| source-sdk265d2-179 | `50f53e2c37a389410203b0401d72a219a90e28adbcaa8e49cd74a888ebbebc04`; canonical179 MATCH |
| receipt-sdk265d2 | `c5c209c01a27778526048e3f30d34587f5c3bffebb04dd918895e3a9c15df206`; terminal passed restore0/build0, exact179 map |
| receipt265e2-all | `020c7d57483cc16aac8f87d9aa1f7bf43f32a1d1e4a01ee0ee27a514ab888ffc`; terminal failed configure0/buildALL0/test8, exact172 map, same6 Release EXE hashes |
| raw265e2-all | `175c01f0b49ba5519dd00b1f27059e4a6b2bf2dedd2e9370c2ca17d0cf0ac85f`;50 unique tests/50 Release commands,49 PASS/1 FAIL |

Full FAIL только #47NativeHashFailureTests, assertion395:
original48128 frames, corrupt EOS complete1/frames0, explicit normal1/
playback1/default normal1, invalid_package0/synthetic_sends1. Это прежний
AAC_MDAT_COUNTEREXAMPLE, не regression queue load и не новый task; не skipped,
не объявлен GREEN. Полное время257.16s — execution summary main; raw failure
блок2.33s лично прочитан. Focused totals14.32/19.03s и portable8.02s — main
execution summary; raw содержит individual passed commands/times.

SDK receipt EXE SHA
`695f2008eb0b7b8a6decc35d73667defa0dae9c18f088fa3e9bebb641c026a03`.
Build не является installed/package/signature/runtime proof. Reviewer не
запускал EXE или Windows. Read265f script лично прочитан: правильные Release/
Debug paths,12 EXE плюс SDK/source comparisons; SHA
`84dff51d0b7ac056a92b469a3dce9b811d6d67ea22f0d2c71a24091dd52d0b9f`.
Завершённый **main execution**, tool chunk86d5b4 exit0, передан после
первой записи этого отчёта: обе172/Release265a2/Debug265b2 дают
`MIRROR_NTFS_SOURCE_AND_EXE_MATCH`, SDK179 даёт
`SDK179_MIRROR_NTFS_SOURCE_AND_EXE_MATCH`, `ROUND265F_READONLY_EXIT=0`.
Соответствующая append-only запись main в validation Round265 лично
прочитана вместе с F200 fragment; это не standalone exported stdout receipt
и не личная reviewer NTFS execution. Это закрывает readback ожидание,
**не** SRC265-1: production inputs не менялись, npos guard отсутствует.

## Неизменяемые anchors и открытые gates

- CPP: `c3370c1afeb0a000b68eb7df07454108e7c03689c62bf6679e0aab46934d93f9`.
- H: `b3de437363e7e85adb19c649221408dd6f6ff0081932c51e69a46c634399fc6f`.
- V2Tests: `b307b5cae3eec6ada20af9f6cfe46bc49fa12bbff30ff608e022a1f2b8e80f5c`.
- Tasks SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`;
 120/93/27 неизменно; T116–T120 не закрываются.
- До этого отчёта125 checklist files:10 current normative154 checked/0 open;
 отдельно115 historical/context256 checked/10 open. После записи проверено:
 все старые125 hashes совпали, added только этот report, итого126. Старые
 markers и tasks не изменены; исторические open не переклассифицированы.
- Registry шесть before/after implement/analyze/checklist, каждой1registered
 git.commit disabled,0enabled,0dispatch. Ни commit, ни GitHub mutation нет.

**Итог: actual matrix PASS подтверждён в её объёме, но узкая SOURCE приёмка
заблокирована только SRC265-1.** Protected owner/BOTH/async/bootstrap/
migration, H250/B1/AAC, installed/hardware и whole app остаются отдельными
открытыми gates; их не требую внедрить ради закрытия этого одного finding.
