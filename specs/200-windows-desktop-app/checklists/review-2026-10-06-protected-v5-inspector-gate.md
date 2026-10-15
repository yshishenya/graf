# Round259: REQUIREMENTS gate полного protected v5 inspector

## Текущий вердикт

**SCOPED REQUIREMENTS / analyze GO** на RED и реализацию конкретного
readonly protected normal/degraded inspector после закрытия REQ259-1.
Прежний NO-GO до уточнения имени marker — промежуточное решение, не текущий verdict.
Это не SOURCE review,
не результат запуска тестов и не запрет продолжать локальное проектирование.
Конкретное предложение main рассмотрено вместе с уточнениями degraded producer,
Mac dates/privacy IDs и reuse Unicode decoder. Полный semantic consumer —
следующая зависимость T116/#7444, не завершённые T116/T117/T118/T120 или приложение.
Lane: существующий high-risk-product; scoped `speckit-analyze` и требования
`speckit-implement`. Менять нормативные артефакты или старые отчёты reviewer не вправе.

## Инвентаризация и границы доказательства

До этого отчёта лично просчитаны SHA256 **111 .md**. Десять действующих
нормативных списков лично перечитаны по всем критериям: **154 checked / 0 open**.
Остальные **101** — исторические списки и отчёты: прежние95 имеют
**256 checked / 10 historical open**, шесть Round256/257/258 отчётов не имеют
checkbox. Исторические open не превращены в новые текущие обязательства;
отмеченные нормативные критерии означают качество требований, не готовый код.

| Нормативный список | Checked / open |
| --- | --- |
| advanced-routing.md | 14 / 0 |
| audio-capture.md | 24 / 0 |
| calendar-launcher.md | 5 / 0 |
| calendar-operation.md | 8 / 0 |
| calendar-wire.md | 5 / 0 |
| packed-writer.md | 12 / 0 |
| privacy-pause.md | 12 / 0 |
| requirements.md | 22 / 0 |
| security.md | 27 / 0 |
| ux.md | 25 / 0 |

Inventory SHA256: сортированные `repo-relative-path + space + SHA256 + LF`:
`764ae61310a267a4de910b60fef05112972e0a8cab409d15bc195e72f3e7c31a`.
Tasks: **120 total / 93 closed / 27 open**, без изменений.

Round258 SOURCE approval принимается только в его объявленной области.
Лично перечитаны итоговый раздел SOURCE258 и текущие input/group/decode участки;
его native Release/Debug доказательства здесь повторно не исполнялись.
Два AAC scalar не доказывают manifest/session/prefix и не дают полномочий.
Legacy Round257 RED и REQ257-B1 для старых path-based full-decode callers не закрыты.

## Scoped analyze: точечное несовпадение и условия

### REQ259-1 — HIGH / закрытая грамматика short marker

Предложение называет optional `shortRecordingDiscarded`, но существующий Windows
writer использует **`short_recording_discarded`**: WindowsDesktopContracts.h:44,
V5LocalRecordingWriter.cpp:233–249. CamelCase принадлежит Mac manifest, который
предложение прямо не собирается навязывать Windows. При unknown-key rejection
это существенная разница, а не орфография: новый parser либо отклонит собственную
известную форму, либо незаметно добавит alias. Минимум перед RED/кодом — указать
единственный точный Windows key и правило false/true; не принимать оба молча.
В sealed normal/degraded true не даёт semantic success. DiscardPending не
принимается этим API; short predicate/queue removal/deletion authority отложены.
Отсутствие готовой short-adoption цепочки не блокирует этот явно ограниченный API.

Других установленных CRITICAL/HIGH противоречий для предложенной readonly
normal/degraded границы нет **при соблюдении обязательных условий ниже**.
Это не утверждение, что соответствующий код/тесты уже существуют.

| Узел | Обязательное условие конкретного предложения |
| --- | --- |
| Input / result | Genuine private-ctor Pair, trusted root, non-null общий cancel, selected sealedNormal/sealedDegraded. Один private-ctor result удерживает Pair и BOTH-slot readers; public structural value, copied scalars или path cache не подменяют proof. Нет account/bootstrap/queue/network/playback/delete rights. |
| Job / lifetime | Worker-only; <=4 общий native jobs, до native ожиданий и до фактического MF shutdown/release, включая отказ/exception/cancel. Retained group/pins/charged bytes живут до actual last result/stream release. Если операции завершаются раньше retained result, dormant owners остаются под pin/owned limits; последующий native IO требует своего admission, не наследует истёкший job. Destruction не делает I/O/flush; timeout не уничтожает действующие объекты. |
| Один group | `openProtectedCustodyReaders` проверяет обе физические slots и все siblings: exact versions/representation/length/logical SHA/retained roots. Любой bad sibling — общий отказ, no rollback. TU-local AAC helper получает stream именно этой группы; wrapper Round258 открывает собственную группу только для собственного вызова. Нет drop/reopen gap или второго open поверх уже удерживаемой exclusive группы. |
| Context / cancellation | Независимый expectedSession не извлекается из manifest/имени каталога. Borrowed view допустим только синхронно при доказанном lifetime; до первого ожидания нужно owned значение, если job/result удерживает его. Null/true cancel до IO; проверки до/после ожиданий и перед успешным возвратом. Позднейшее UI/effect adoption требует current owner/session/store/account epoch и admission; inspector не выдумывает dummy context. |
| Manifest bytes | Selected sealed ref, полный exact logical SHA/length; <=65536B до allocation/read, не substring/truncation. Полный retained payload и parser token/ID storage charged до allocation, включая capacity/retained result. Весь input UTF-8, без BOM/trailing bytes; decoded duplicate/unknown keys, wrong types/null/overflow отвергаются. Logical v5 `schema_version` не переименовывается в package-state `schema`. |
| Closed Windows shape | Известные snake_case schema/profile/source/mode/duration/artifacts; status/reason только вместе либо известная pre-status legacy форма. Optional time triple только целиком, present invalid values — отказ. Валидность display offset и чисел проверяется до casts. Не принуждать старый минимальный Windows manifest стать full camelCase Mac manifest. |
| Legacy session | Отсутствие sessionId и privacySegments у известного Windows legacy нормально, но **не доказывает привязку session из manifest**. Present sessionId должен точно совпасть с независимо ожидаемым. Privacy segments все сверяются с ним даже при отсутствующем top-level sessionId; expectedSession для такого случая не пустой/не догадка. |
| Privacy grammar | Ровно известные11 Mac names: segmentId, sessionId, control, startedAt, endedAt, startMonotonicMs, endMonotonicMs, durationMs, localMicTreatment, initiator, diagnosticSafe. OPEN имеет9 обязательных полей, оба end отсутствуют, не null, duration0; closed оба end present. Unique decoded segmentId, exact session; known enum, bool, nonnegative Int64, end>=start, exact difference без overflow. |
| Privacy dates / IDs | ISO UTC Gregorian `YYYY-MM-DDTHH:MM:SSZ` по предложенному producer subset; syntactic date validity, **не** wall-clock endedAt>=startedAt. Монотонное время управляет длительностью. UTF-8 IDs, весь64KiB bound и charged uniqueness storage; не переносить ASCII/300-char package identity cap, UUID/calendar caps или отдельный count limit на privacy IDs. Неподтверждённые ISO extensions не угадывать. |
| Normal | Selected sealed media/playback/manifest refs; descriptors exact length/SHA соответствуют ref/stream. WAV44 PCM16 LE/16k/mono, RIFF/data exact sizes, positive data/duration, существующее соответствие duration. AAC native LC/48k/mono и полный bounded PCM EOS по Round258, independently positive container/decoded duration в прежних100ms. Pair none, manifest normal/none или известная pre-status форма; short false/absent. Ошибки не превращаются в normal. |
| Degraded without manifest | Разрешён selected sealed canonical+recovery с known non-none Pair reason. У early encoder/storage failure действительно нет manifest: V5 writer retainPrefix/finalize:262–317. Не требовать отсутствующий manifest как prerequisite и не сочинять пустой. Положительная длительность выводится из validated complete480-float frames, не caller duration или наличия recovery filename. |
| Degraded prefix / optional finals | Exact recovery fields capture_status/capture_reason_code/trusted_prefix_frames/canonical_bytes/canonical_sha256. Reason совпадает с Pair; full immutable canonical logical length/SHA совпадают. Positive trusted count N<=floor(validated_length/1920), prefix=N*1920 bytes, duration=N*10ms; все операции checked. По custody §4 floor определяет максимум полного prefix, не право включить ещё не принятый writer frame. Early append может оставить tail, его отсутствие не требуется. Выдаваемый prefix stream/range реально ограничен этим полным prefix, без tail/padding. Manifest при наличии имеет ту же derived duration. Каждый присутствующий ref проверяет batch; упомянутый manifest artifact обязан иметь matching ref и полностью валидный WAV/AAC. Отсутствие optional artifact не успех отсутствующего referenced artifact. Degraded никогда normal/upload. |
| Short / collection | No accepted normal/degraded для discardPending/capturing/finalizing. Bool marker не доказывает exact frame count/normal stop/no fault и не даёт deletion. Collection metadata projection не вызывает full decode всех пакетов и не выдаёт semantic normal/play authority. |
| Memory / errors | Owned64MiB, native working budget2MiB, cache2MiB, pins32, chunks256KiB и job<=4 неизменны. Manifest cap не per-job расширение. Native MF allocation измеряется отдельно. Exact typed allocation/cancel/native/integrity errors; no raw/URL/temp/normalization/fallback. API evidence не performance PASS. |

## Parser reuse и предел области

Уточнение trusted prefix принято в ограниченном семантическом смысле:
`N<=floor(length/1920)` не превращается в равенство всей длины с frame count,
не добавляет missing samples и допускает conservative меньшее N, которое writer
успел принять. Known finite float values проверяются в используемом complete
prefix; AEC/clean provenance принадлежит настоящему producing lifecycle,
не выводится из float values, SHA или произвольного recovery JSON. Полный SHA
проверяет и сохранённый tail, но tail не становится записанным prefix.

PackageJson в ProtectedCustodyMetadata.cpp:71–185 — closed object/bitmask/token
pattern; его ASCII-only string и token300 **не** ready-made privacy parser.
DesktopApiClient.cpp:455–529 лично прочитан: calendarString уже проверяет raw
UTF-8/Unicode/surrogate escapes, но создаёт uncharged std::string и TU-private.
Предложенное выделение **только** allocation-free traversal с byte emitter в
internal JsonString.h допустимо как reuse, без DOM/framework/dependency.
V5 emitter использует заранее charged capacity; emit failure не выдаёт partial
accepted token. Calendar wrapper сохраняет maxRawBytes/allowNul/UTF-8/escape и
exception semantics; календарные регрессии обязательны. Нужны decoded-key
duplicates (например escaped spelling), escaped ID uniqueness, Unicode/overflow
countercases и stable token lifetime, не ссылки на overwritten token buffer.

Экстракция добавляет shared header + DesktopApiClient wrapper к production
scope main; это явно предложенное изменение, но **не** разрешение reviewer
редактировать их и не runtime acceptance календаря. Server manifest acceptance
main описал как role-descriptor wire, не local JSON parser: reviewer эту часть
не исполнял и не подменяет её независимой серверной приёмкой. Wire/backend
менять для этого inspector не разрешается.

## Что требуется для следующего SOURCE gate

RED до кода в existing native FilesTests: настоящий Pair/BOTH slots и retained
result; normal positive, pre-status/no-session legacy, exact privacy OPEN/closed,
Unicode/duplicates/unknown/null/overflow/64KiB boundary, present invalid time,
bad sibling/ref/hash/length/format, damaged AAC; degraded canonical+recovery без
manifest и с finals, mismatched reason/count/hash и partial tail; all failures
release/retry, cancel/admission/charged memory/terminal cleanup. Existing
Round258 wrapper/native baseline и все затронутые calendar tests сохраняются.
Native format/extra stream/flags/late ReadSample cancel и performance cases не
объявлять PASS без действительных fixtures/измерений. Retained result не
доказывает account/bootstrap admission или consumer adoption будущих callers.

Этот финальный GO требований не является SOURCE approval. Whole-app,
writer/queue/bootstrap/current epoch/adoption/migration/T120, SC-003/100cycles,
SDK full build/installed/hardware/signature/release остаются отдельными gates.

## Точный текущий baseline

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserved.
Supported read-only prerequisites подтверждают feature200; analyze/implement
hooks YAML parsed, все четыре соответствующих hooks disabled.

| Artifact | SHA256 |
| --- | --- |
| constitution.md | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |
| spec.md | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| plan.md | 527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| quickstart.md | fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e |
| data-model.md | 8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19 |
| windows-protected-local-custody.md | ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a |
| windows-protected-packed-custody.md | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| LocalRecordingPackage.h | fd4d8721893fea6ba706d978c3d2a28b08ccaed416d97e0213607633fb2ce710 |
| LocalRecordingPackage.cpp | 0ccedb1a67363be192460349cc87d2fa0ddce97184f32fc7027112f47416da6c |
| ProtectedCustodyFilesTests.cpp | dff07b7f5a0bb790564f952d43644346310ab947f70b2bce21ec464d9131391f |
| NativeHashFailureTests.cpp | a2d6d9a8e1dd0ea75832d987502b4cfd6a41cfd0414e6506c60ea933cc8f3f76 |

Only write: этот новый reviewer-owned файл. Ни production/tests/spec/plan/tasks,
old reports, VM/GitHub/app/profile, commit/push/merge не изменялись reviewer.

## Закрытие REQ259-1 и итоговый допуск

Main явно подтвердил единственный существующий Windows key
`kShortRecordingDiscardedField = "short_recording_discarded"`.
CamelCase `shortRecordingDiscarded` не добавляется как alias. Known absence
или explicit false допустимы для normal/degraded; true отвергает оба результата
независимо от reason/duration. DiscardPending вне области API. REQ259-1 закрыт.

**Scoped analyze: CRITICAL 0 / unresolved HIGH 0** для конкретного предложения
с обязательными условиями таблицы. Разрешены RED, затем реализация main:
existing LocalRecordingPackage.h/.cpp + native existing FilesTests; небольшой
internal JsonString.h/existing DesktopApiClient wrapper только для заявленного
переиспользования traversal, с календарными регрессиями. Никакого public
arbitrary-stream proof или generic JSON DOM. Новый private result удерживает
real Pair/BOTH owners/charged manifest; header AAC scalar сам не authority.

Degraded может не иметь manifest; validated recovery/canonical обязательны.
Trusted N положительно и не превышает floor(actual length/1920); exact prefix
N*1920 ограничивает последующее чтение, duration=N*10. Остаток full object
проверен hash, но не включается в prefix. Optional finals не подменяют missing
referenced artifact. Privacy IDs UTF-8 без чужого ASCII/count cap; Mac date
rollback не делает закрытый сегмент invalid при корректной monotonic паре.
Заимствованный expectedSession не должен пережить своего владельца; retained
job/result получает owned value, если сохраняет эту строку.

Остаются NOT GO: SOURCE/runtime новой реализации, полная semantic short-adoption,
account/bootstrap/currentness/effect integration, queue/writer/T120/migration,
SC-003/full native format/performance, SDK/installed/hardware/release и вся цель
Windows parity. REQ257-B1/legacy RED неизменны. Никакая задача не закрыта.
