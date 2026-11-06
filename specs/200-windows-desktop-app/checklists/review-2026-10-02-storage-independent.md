# Независимая проверка требований хранения T115–T118 — 2026-10-02

## Заключение и границы

**PASS — качество требований отдельного high-risk storage-среза.**
Повторно прочитаны и проверены все 112 checkbox-критериев во всех
`checklists/*.md`: 112 checked / 0 unchecked, неподтверждённых критериев 0.
Новых блокирующих пробелов требований T115 не обнаружено. Это независимый
review требований, **не** результат `speckit-analyze`, аудит кода, принятие
T116–T118, runtime PASS, установленная приёмка или общий PASS F200.

Рабочая область строго:
`/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
HEAD до и при фиксации вывода:
`99b00a579c24b50e320465b69d9a296038bc544d`, ветка
`codex/200-windows-followup`. Активная feature подтверждена
`.specify/feature.json` и `check-prerequisites.sh --json --paths-only`;
физическое имя каталога не использовано как источник feature.
Risk/validation lane: `high-risk-product`, полный проектный Spec Kit путь;
в этой проверке выполнен только независимый допуск качества требований.

Изменён только настоящий новый отчёт. Маркеры чеклистов не менялись: все
имеющиеся отметки подтверждены текущими требованиями, а не прежними PASS.
Код/spec/plan/tasks/data-model/quickstart/contracts/root/GitHub/коммиты
не менялись. Параллельные изменения main сохранены. Реальных storage producers
не аудировал: этот отдельный анализ принадлежит main.
VM, устройства, микрофон, сборки, тесты, реальные записи, ключи, миграции,
установка, сеть продукта, публикация и выпуск не использовались.

## Полнота чтения и актуальность T115

Полностью прочитаны: `AGENTS.md`, guidance index,
`.specify/memory/constitution.md`, `codex-worktrees.md`, `spec-kit-flow.md`,
`product-gates.md`, `release-and-validation.md`, product baseline
`docs/prd-voice-layer-final.md`, `docs/current-product-status.md`, текущие
`spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, `data-model.md`, весь
`contracts/windows-protected-local-custody.md`. Дополнительно прочитаны
desktop и native-web contracts, пять полных checklist-файлов; для ссылочных
критериев — исходная и актуальная parity matrix и относящиеся к будущему
routing/идентичности разделы research. Исторический Phase0 exit прочитан
как ограниченное исследовательское основание, не заново выполненный опыт.

Уточнение владельца о независимом хранении сопоставлено по четырём текущим
источникам, не только по прежнему отчёту:

| Источник | Проверенное текущее правило |
| --- | --- |
| spec, Clarifications / Session 2026-10-02 — независимый срез | T115–T118 разрешены отдельно от clock/T119, без отмены общих требований, миграционных и release gates |
| plan, последняя секция «Актуальный порядок» | Прежний общий запрет начала storage заменён; собственные review/analyze/issue gates обязательны; общий F200 PASS запрещён |
| tasks, Phase18 / T115–T118 | Последовательность T114 → T115 → independent checklist review → read-only analyze → taskstoissues → T116 → T117 → T118; clock/T119 не зависимости разработки |
| quickstart §12, последний абзац | Искусственные storage-регрессии без микрофона; полная матрица хранения и отдельная общая приёмка не сокращены |

Последнее уточнение пользователя о первом шаге учтено **по новым байтам plan**:
wire/identity/bounds/integrity и bounded incremental hash в существующем
`Storage/Sha256.*` идут первыми, затем durable IO/adapters и вся цепочка.
Это согласовано с T116 и contract §6; не новое продуктовое требование и не
интеграционный PASS. Предыдущий SHA-256 plan
`9f438f21b692c8f3e09322439eb8e6a268fb0e9cc9a2ea43ae7ed69e3d3f32c1`
не является привязкой настоящего вывода; актуальный hash указан ниже.
Дополнительная проверка первичных ссылок CNG, сообщённая main, не выдаётся
за выполненную этим reviewer проверку API или кода.

T114 отмечена выполненной только в исследовательском объёме; T115 в текущих
tasks всё ещё открыта. «Кандидат/проект» в заголовках contract/data-model и
историческое «T115 ещё не принят» — честный статус до этого review, а не
недостающая wire/authority спецификация. Их status-only обновление после PASS,
отметка T115 и финальное связывание hashes принадлежат main; здесь не выполнены.
Этот отчёт принимает именно качество текущего кандидата. Перед кодом main
должен завершить свой analyze storage-среза (CRITICAL=0/HIGH=0, без открытых
уточнений), актуальную синхронизацию владельцев/задач GitHub и служебную
фиксацию T115. В заключительном перечитывании tasks появились четыре явные
ссылки владельцев: T115 #7443, T116 #7444, T117 #7445, T118 #7446. Проверены
текущие байты этого дополнения и неизменные условия T114–T118; отметка T115
по-прежнему открыта. Main сообщил issue-canon ensure no-op PASS,
post-canon PASS (300 issues) и bootstrap doctor PASS. Это сведения main,
не независимо выполненные этим reviewer GitHub/bootstrap проверки.
Любое последующее смысловое изменение требует повторной проверки; status-only
изменение должно быть отдельно сравнено и привязано к новым hashes.

## Проверка критических требований хранения

Обозначения: C — `windows-protected-local-custody.md`, D — data-model §12,
Q — quickstart §12. В таблице PASS означает достаточную определённость
требований и проверочных условий, не доказанную реализацию.

| Область | Основание PASS / сохранённая граница |
| --- | --- |
| Полный охват | FR-012, T116, C §§1–2/8.2, D/Q замыкают canonical temporary, WAV, AAC, manifest, recovery, очередь, deletion, quarantine и atomic temporary bytes. Защита до write, не только после finalize; никакого plaintext fallback или полного encrypted claim при legacy leftovers |
| Формат и bounds | C §3 задаёт explicit LE, exact outer16B, block104B/index112B headers, 256KiB blocks, DATA/ZERO, reserved/unknown/excess rejection, checksum/digest, overflow до allocation/cast. Media≤64GiB/262144 blocks; index≤4198400B, physical overhead≤65536B, payload overhead≤4096B; роли manifest4096B/queue4MiB/служебные64KiB разделены |
| Integrity и identity | C §§2–3/8.1: непрозрачные16B IDs, fixed confined locations, собственные role/store/object/index identities, exact tail/length и SHA. Повреждённый encrypted object не декодируется как legacy; отсутствующий DATA не ZERO; потерянный store.id не регенерируется из protected traces |
| Commit | C §4: immutable CREATE_NEW blocks → flush → protected alternate index publish → flush/reopen/validation → ACK. До ACK нет durable success; ошибка после publish — ambiguous, закрывает последующие mutations/unsafe GC, сохраняет checkpoint и требует reconcile. Generation/version не оборачиваются и orphan versions не переиспользуются |
| Metadata birth / singleton | C §4, D/Q: initial g1 в двух independently written/validated slots до первого ACK. Equal-generation допустим только для одинаковой birth-пары. Любой singleton после restart, включая g1 после потери g2/delete slot, блокируется; нельзя восстановить stale ledger, создать empty queue или автоматически достроить slot |
| Media и package authority | Media fallback — только validated degraded prefix, не normal upload. Capturing/finalizing/sealed/discard состояния отдельны; manifest last, exact sealed refs/role/hash. Metadata slot/reference failure закрывает authority, а не выбирает удобный старый документ |
| Общая память/IO/GC | C §5: process-owned budget64MiB до allocation, shared plaintext cache2MiB, dirty≤4blocks/1MiB, chunks256KiB, pins/clones≤32, commands/results≤32, GC≤64objects/pass. MF/DPAPI memory измеряется отдельно. Roots обоих slots, candidates/pins/barriers/tombstones восстанавливаются после restart до GC; unknown/ambiguous сохраняется |
| Product quotas | C §5/Q сохраняют PRD7дней/5GB,80%/95% и reserve=min(10GB,10%capacity), accounting peak ciphertext/index/orphan/pin/legacy/temp. Wire64GiB и layer64MiB не новые пользовательские квоты и не app performance proof. Различие24h parser/4h server не выдаётся за расширенную серверную поддержку |
| Async authority | C §5: целый immutable metadata candidate и typed ticket pending/committed/not_committed/ambiguous с base/target generation/context epoch. Network, queue drain, enqueue, reply/handled/delete продолжения ждут ACK; pending не bool-success. Physically committed generation принимается даже при stale UI, но stale action не получает UI/network effect; lost callback сверяется до следующей mutation |
| Lifetime и потоки | C §§5–7: UI/capture callback без disk/crypto/hash/fullscan; worker имеет собственный snapshot/pin/lease/result до terminal adoption и реального завершения. До publish cancel → not_committed, после publish → committed/ambiguous. MF Shutdown/actual worker completion перед release pins; timeout не force-close и не освобождение занятого owner |
| Logical IO / hash / upload | C §6/T116: sticky errors/got0, exact EOF/S_FALSE, explicit ZERO без padding, bounded seek/CopyTo, Clone independent cursor/same pinned generation, точные Commit flags. IStream→IMFByteStream, native audio-only playback без plaintext URL/tmp/ShellExecute. Bounded incremental logical SHA/CNG и exact HTTP ranges/part hashes; v5 bytes/UUID/roles/accepted ranges не меняются |
| Delete и короткая запись | C §7/FR-022: durable intent → close admission/cancel/network/playback Shutdown/quiesce actual owners → confined recycle/purge → actual absence → durable ACK. IFileOperation/RecycleBin не forensic/cryptographic erasure, profile keys не удаляются. Positive short-recording predicate/marker, durable queue removal до cleanup, marker last; restart не воскресит upload |
| Initial migration | C §8/8.1: verified legacy inventory, exclusive lease/quiesce, reserved queue ID без empty logical queue, prepared intent pair → closing bootstrap fence pair → destination pair → single switch/reconcile. Prepared fence не требует ещё не созданную destination queue; package migration требует protected queue. Provisional objects не regular authority |
| Старый reader / cut до sentinel | C §8: durable CREATE_NEW .quarantine с точными protected birth-block bytes до первого rename старого ledger. Старый load после rename отказывает, не создаёт empty v3; неизвестный quarantine не перезаписывается. Originals сохраняются и проверяются; sentinel/actual switch/receipt cuts и source stamps определены отдельно |
| Historical barrier и persistent roots | C §8.1/D/Q: direct g1 birth-block ref проверяется без исчезнувшего g1 mutable index после g3/g4; current mutable intent по-прежнему требует два valid slots. Transitive roots обоих metadata slots восстанавливаются до GC; tombstone переживает release terminal in-memory pin. Третья вечная index-копия не нужна |
| Codec authority payloads | C §8.1: strict UTF-8, exact schemas/fields/null/enums/IDs, no duplicate decoded keys/unknown/missing/BOM/trailing, exact decimal u64 без float, глубина≤4/refs≤6/keys≤16/payload≤64KiB. Fixed locations, own generation/identity, permitted stage/ref combinations; legacy logical codecs не подменяются |
| Migration rights / cleanup / retirement | C §8: whole source/range stamp и streaming exact length/hash до switch, прежние owner/delete/purge/UUID/ranges сохраняются. Migration permission не cleanup permission; нужны отдельное owner-confirmation или уже подтверждённый delete intent и свежие права всех строк. Old-reader exception owner F200/T117, removal до first public storage release, hard expiry2026-11-01UTC; overdue blocked/preserve, без plaintext downgrade |
| Отказы и приёмка | C §9/Q/T118 перечисляют corruption/key/profile/disk-full/power-loss/process cuts,100cycles, full generated pipeline, actual installed SHA/MSIX/EXE, standard-user/offline/Home/Pro/N/Win10/11/update/rollback. Wrong entropy T114 не actual profile loss; arithmetic bounds не runtime proof |

Не выявлено неразрешённого storage уточнения по перечисленным областям.
Это не самостоятельный аудит корректности DPAPI/CNG/MF implementation.
Закрытый список путей §8.2 является требованием для T116; сопоставление его
с реальными producer/reader/caller sites выполняет main отдельно.

## Отделение условий разработки, приёмки и выпуска

1. Собственный review/analyze/issue допуск T115 позволяет начать только
   последовательный storage T116→T117→T118 на разрешённых искусственных данных.
   Clock T094–T096 и календарный T119 не его зависимости разработки.
2. Неподключённый codec/hash primitive не защищённое приложение, не T116/T118
   PASS и не разрешение переноса непрошедшего clock candidate в runtime.
3. T118 дополняет, не заменяет T083/T087/T088/T063/T071/T094–T097, реальный
   authenticated upload/delete, физический x64/60min/AEC, доступность,
   signature/clean-image/install/update/rollback. Реальная миграция и установка
   требуют собственных применимых gates и полномочий.
4. Общие governance-fast exact PR SHA, независимый review/convergence,
   frozen release-full, отдельное approval на commit/production/public release
   сохраняются. Root AGENTS locked и стабилен; общий after_plan hook не запущен.
   Нет заявления об общей готовности F200, публикации или новом установленном EXE.

Исторические задачи/опыты/кандидаты, отдельные portable/native tests,
standalone DPAPI/MF mechanism proofs и старый пакет не использованы как
runtime PASS сегодняшнего protocol. Старое desktop описание logical
WAV/M4A/manifest остаётся logical wire-форматом; D §12 и C §§2/6/8.2 запрещают
открытые physical content files после перехода. Общая формулировка
deletion/tombstone/cryptographic proof не обещает cryptographic erasure:
текущий storage контракт разрешает только доказуемый доступный результат.

## Перечитанные чеклисты: точный пересчёт

Просмотрены все Markdown-файлы каталога на checkbox markers, включая прежние
review-отчёты. Checkbox-критерии находятся только в следующих пяти файлах;
новый отчёт не добавляет checkbox-критериев. CHK IDs локальны файлу, не всему
каталогу. Регистр `[x]`/`[X]` учтён как checked.

| Файл | Перечитано | Checked до | Unchecked до | Checked после | Unchecked после | Изменено markers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| requirements.md | 22 | 22 | 0 | 22 | 0 | 0 |
| security.md | 27 | 27 | 0 | 27 | 0 | 0 |
| audio-capture.md | 24 | 24 | 0 | 24 | 0 | 0 |
| ux.md | 25 | 25 | 0 | 25 | 0 | 0 |
| advanced-routing.md | 14 | 14 | 0 | 14 | 0 | 0 |
| **Всего** | **112** | **112** | **0** | **112** | **0** | **0** |

Ниже отдельная запись для каждого критерия. «Подтверждён» означает качество
требования по указанному текущему источнику, не исполнение соответствующего теста.
W — windows-desktop-contract; B — windows-native-web-bridge; P — plan;
S — spec; M — data-model; Q — quickstart; C — protected custody contract.

### requirements.md — 22/22

| Критерий | Основание подтверждения |
| --- | --- |
| CHK001 | S FR001–022; tasks исходная traceability + Phase14–19 дополнения, отдельно T114–118 для полного FR012/013/014/022 |
| CHK002 | S SC001–010; Q §§3–9/11–13 и tasks T063/T071/T083/T087/T088/T094–119 задают источник/порог/проверку, не скрывают открытые proofs |
| CHK003 | Пять S User Stories с Independent Test/AC; отдельные capture/cabinet/custody/limited audio/automatic условия |
| CHK004 | S FR002–004; W §1 и B §§4–5: native capture/local truth против server cabinet/business truth |
| CHK005 | S Edge Cases; W §§3/6; C §4: normal/degraded/failed/blocked/recovery различаются |
| CHK006 | S FR002/SC002, конечная цель; parity matrix и P/Q итоговая приёмка, Toolkit не критерий идентичности |
| CHK007 | S FR003/005; B §§1/6/9/10: exact origin/route kinds, auth/payment/external границы |
| CHK008 | S FR010–017; W §§5–6; C §4: trusted prefix не normal/полный capture |
| CHK009 | S FR009/018/SC001/003, W §5, B §3, C §§3–5: численные bounds и scopes |
| CHK010 | S FR004/007–010, W §§2–3; storage/readiness, два источника, AEC/indicator/Stop, без legal prerequisites |
| CHK011 | S FR007–010 совпадают с W §§4–6 по source/order/queue/fail-closed; C не меняет audio guards |
| CHK012 | S FR011–014, M §§6–7/12 и C §6: logical v5 roles, schema v3/read v2/historical filename, server ranges/truth |
| CHK013 | S FR004–006, W §1, B §§4–5: display/native_ready не custody/capture authority |
| CHK014 | S US5/FR016, Constitution II, M §9: три режима/explicit Remember/verified identity/countdown/Stop сохранены |
| CHK015 | S Out of Scope; P Source ownership; нет process/driver/service/exclusive/Windows-only cabinet задач |
| CHK016 | S Edge Cases; W §§2/6, B §6, C §4: runtime/network/auth/endpoint/privacy/disk ошибки не смешаны |
| CHK017 | S FR017/Edge Cases; W §§3/5–6: доверенный prefix и запрет normal при разрыве/overflow |
| CHK018 | S Edge Cases/FR020, P/Q prerequisites: Windows N/AAC absence явно блокирует normal playback readiness |
| CHK019 | S Assumptions и конечная цель: общие routes/API/v5/deletion принадлежат shared source, изменение требует отдельного решения |
| CHK020 | S FR012/021, Repository Hygiene, W §9, product-gates: запрет private/content/credential evidence |
| CHK021 | S SC/AC, W/B/C exact thresholds/state transitions: общие слова раскрыты измеримыми/наблюдаемыми условиями |
| CHK022 | S Assumptions/Out of Scope, P/Q итоговая совместная приёмка: shared изменения отдельны, не скрыты в Windows storage |

### security.md — 27/27

| Критерий | Основание подтверждения |
| --- | --- |
| CHK001 | B §1 exact normalized HTTPS scheme/host/port; substring trust запрещён |
| CHK002 | B §§1/5/8–10 approved route kinds/typed capabilities и отказ unknown/native-only |
| CHK003 | B §§1/6/9: schemes/local/download/frame/redirect/external и bounded payment exception |
| CHK004 | S FR020/Edge Cases, B §§2/6: Evergreen failure/recovery вне capture authority |
| CHK005 | B §2: host objects=false, no COM/filesystem generic bridge, bounded capabilities, standard user |
| CHK006 | B §§3–4 и M §8: request envelope, native_ready envelope и отдельные display rows различаются |
| CHK007 | B §§3/6/7/10:64KiB/depth8, source/current nonce/document, replay/stale rejection |
| CHK008 | Текущая редакция критерия уже включает семь exact intents; B §§3–6/8–10, S FR006 и Phase19 сохраняют запреты старых aliases и auth/payment/frame authority; F277 version2 требует отдельной приёмки, T119 пока целевой контракт |
| CHK009 | B §§4/8/10 и M §8 задают native_ready/local_recordings/typed replies/calendar_join_reply, bounded fields и stale/result truth; URL/private contents/Record authority отсутствуют |
| CHK010 | B §§4–5/8, W §7, M §§7–8: no ack aliases; только durable native и server truth, не web reply |
| CHK011 | B §6: document nonce invalidation без изменения native recording state |
| CHK012 | S FR012, C §§2–5: user-only ACL до write, confinement, protected temporary/atomic publication/ACK/error bounds |
| CHK013 | S FR013, C §§4/8: two-slot authority/quarantine/preservation, повреждение/singleton не empty queue/старое deletion состояние |
| CHK014 | S FR014, W §7, C §6: только существующие GRAF APIs, credentials/provider egress не native |
| CHK015 | S FR022, C §7: actual local proof и durable ACK; RecycleBin не remote/forensic/cryptographic erasure |
| CHK016 | S SC008, C §8, Q §§8/12: preservation/update/rollback; old-reader downgrade unsupported не plaintext fallback |
| CHK017 | S FR021, W §9: allowlisted metadata, paths/command lines исключены |
| CHK018 | Repository Hygiene/product-gates/W §9 и Q evidence: raw audio/private IDs/response bodies/secrets не допустимы |
| CHK019 | P Phase0 и AEC gate/исходные pins в S/Q; source/license/build provenance обязателен, наличие backend не принимается по fake tests |
| CHK020 | S FR020/SC008, P Phase6/Q §8: signature/architecture/App SDK/Evergreen/clean-image/rollback до распространения |
| CHK021 | S FR019/Out of Scope, W/B/C boundaries: no elevation/driver/service; user-scope DPAPI offline |
| CHK022 | B §7 и Q §5: hostile origin/nonce/replay/oversize/redirect/close/runtime threat cases заданы |
| CHK023 | W §7 exact spaces→auth/me protocol: same session, HTTP200/no redirects,2MiB/1024, typed UUID/active/duplicates, cancellation/owner and no purge authority |
| CHK024 | Constitution II и S context/FR004/W §2 явно исключают юридические prerequisites без фиктивного consent |
| CHK025 | W §§2–3/7, S FR004/012–014/022: technical readiness, server auth/recording owner/deletion rights разделены |
| CHK026 | S US5 AC7–9, M §9, W §4: targetKey не identityKey, membership/collision/version и сохранение всех трёх режимов |
| CHK027 | M §9/P Phase5/Q постоянные keys/research точная первая identity: V2/default/bulk/error/return правила; не заявлены все версии/архитектуры/настоящая встреча |

### audio-capture.md — 24/24

| Критерий | Основание подтверждения |
| --- | --- |
| CHK001 | S FR007–008/W §4: shared selected/default render и отдельный физический microphone |
| CHK002 | S FR004/008/012/W §2: privacy/endpoint/format/storage prerequisites разделены |
| CHK003 | S FR007/Out of Scope: no process isolation/Stereo Mix/driver/kernel/exclusive claims |
| CHK004 | S FR017/Edge Cases/W §6: endpoint/service/exclusive faults наблюдаемо заканчивают trusted segment |
| CHK005 | S FR018/W §5: packet QPC100ns и monotonic mapping, не callback/wall clock; clock open не меняет качество требования |
| CHK006 | M §4/W §4: source/format/count/PTS/domain/route/flags полностью определены |
| CHK007 | W §5/S FR009/018/SC003:256 slots/2EOS,48frames correction,100ppm+1ms+frame, drift/overflow отказ |
| CHK008 | P Performance/W §4/C §5: callbacks не disk/crypto/WebView/UI/unbounded allocation/block waits |
| CHK009 | W §5/S Edge Cases: partial/jitter/reorder/backward/domain/packet ranges и prefix refusal правила |
| CHK010 | S FR009/W §5:48kHz mono float,480sample/10ms до AEC |
| CHK011 | S FR009–010/W §5/P AEC gate: pinned C ABI, render/reference before microphone |
| CHK012 | S FR010/W §§5–6: creation/process/reference/sample/timestamp/route/overflow fail-closed |
| CHK013 | W §§5–6/C §4: no raw mic; verified cleaned prefix отдельно от normal sealed/upload |
| CHK014 | W §5: cleaned mic смешивается с неизменённым system reference, не crypto/clock замена сигнала |
| CHK015 | S FR011/SC003/W §5/C §6: WAV16kHz PCM/M4A48kHz AAC, exact logical hashes/durations≤100ms |
| CHK016 | S Edge Cases/Q prerequisites: Windows N codec readiness, нет normal без playback |
| CHK017 | S Edge Cases/W §§3/6/C §§4/7: sleep/resume/suspend/termination сохраняют лишь trusted data, Stop не новый finalizer |
| CHK018 | S FR017/W §6: DRM limitation честная, нет bypass/fullcapture claim |
| CHK019 | S SC003/Q §§3–4:60min/±100ppm/no drop/duplicate/duration100ms/system1dB |
| CHK020 | S SC003/P/Q:CPU≤25% одного logical core, resident growth≤128MiB и bounded queues; crash-free недостаточно |
| CHK021 | P Validation/Q §4:Win10 22H2/Win11/built-in/USB/Bluetooth/HDMI/DP/dock/RDP matrix; физический x64 не VM |
| CHK022 | S FR021/W §9: safe counters/reasons/durations/classes/redacted fingerprint, без samples/paths |
| CHK023 | W §3/S FR009: privacy Pause сохраняет reference/timeline, timestamped zero microphone, no raw/wallclock padding |
| CHK024 | W §3/5/C §§4–5: idempotent Stop/start/pause/degraded, exact EOS/finalizer/manifest/queue ACK handoff;5s drain не увеличен |

### ux.md — 25/25

| Критерий | Основание подтверждения |
| --- | --- |
| CHK001 | parity matrix initial/current, S FR002/SC002, P/Q final parity: route/state/action/permission/custody meanings и conventions |
| CHK002 | S FR003/W §1: один server-owned cabinet, native-only capture, не новая Windows meeting UI |
| CHK003 | S context/FR007: global selected render mix, не только Zoom/Teams |
| CHK004 | S AC/Edge Cases, W §3/P shell states и Q: русские state/recovery результаты; storage pending/ambiguous не saved |
| CHK005 | S FR015/W §§2–3/8: indicator/scope/one-action Stop до аудио и вне WebView/focus/network |
| CHK006 | W §§3/8: background/tray state и idempotent Stop без второго finalizer |
| CHK007 | W §8/B §4: DOM/web messages не owner и не способ удалить native indicator |
| CHK008 | W §3/S FR009: Pause privacy copy/reference/time, raw mic fallback запрещён |
| CHK009 | S Edge Cases/W §6/B §6/C §4: разные endpoint/privacy/clock/DRM/disk/runtime reasons и recovery |
| CHK010 | S US5/уточнение/Constitution II:8s visible Ask, Record now/Never for attempt, only explicit checked Remember changes rule |
| CHK011 | S FR016/M §9:Always/Ask/Never одна строка продукта, Ask default, bulk known catalog, Mixed не четвёртое правило |
| CHK012 | S FR016/SC007: unknown/unverified/playback/denied/suppression не autostart; Always обходит лишь вопрос, Ask expiry валиден |
| CHK013 | Критерий прочитан вместе с соседним действующим уточнением Constitution7 в этом файле: old legal-policy words не prerequisites; S context/FR004/016/M §9 сохраняют technical/identity/Stop и independent manual Record |
| CHK014 | S SC009/Q §§7/11: keyboard/focus для capture/permission/tray/prompt обязательно, не принято по screenshot |
| CHK015 | S SC009/W §8: names/descriptions/state announcements, Stop/degraded/custody для screen reader |
| CHK016 | S SC009/P/Q:High Contrast/200%DPI/narrow/reduced motion/theme/focus/target/overflow criteria |
| CHK017 | S SC009/W §8: текст/icon/shape/accessible state, не один цвет |
| CHK018 | S FR002/021/context/P/Q parity: согласованный русский copy, no secrets/process isolation claims |
| CHK019 | S US1–3/W §6/B §6/C §4:offline/auth/runtime/upload pending не normal/remote success |
| CHK020 | S конечная цель/F277, Constitution VII/product-gates/P/Q: faithful Krisp reference разрешён, independent code/accessibility/provenance обязательны; лицензии не доказаны этим checklist |
| CHK021 | S Edge Cases/W §3/C §§5/7/8: close/Quit/relaunch сохраняют actual custody lease/status/Stop, update/deletion не hidden cleanup |
| CHK022 | S FR004/015/W §§1/8: критический Stop/readiness/recovery/custody native, не WebView route prerequisite |
| CHK023 | S/M §9 и Q keys: прежние memory/global rules не migration permission, corrupt→Ask, strict enum/error preserves previous choice |
| CHK024 | S US5 AC4/P Phase5/W §§2/4: hidden preparation, actual independent indicator/Stop до capture; show failure denies |
| CHK025 | S US5 AC5–6/M §9/W §4: accepted starting/current identity,2/15/600 freshness, stale/repeat/lost proof и independent manual flow |

### advanced-routing.md — 14/14

| Критерий | Основание подтверждения |
| --- | --- |
| CHK001 | S context/FR007/W §4:global mix отличен от future process-isolated |
| CHK002 | S Out of Scope явно перечисляет Stereo Mix/hardware/virtual/kernel/exclusive/elevated service |
| CHK003 | S FR007/019/W source boundary: no privacy/DRM/endpoint bypass privileged helper |
| CHK004 | P Source ownership/W §1: один WASAPI/timeline/local truth; storage adapter не второй audio-routing stack |
| CHK005 | S FR017/W §6: protected limitation только truthful limited/degraded, no hidden alternate source |
| CHK006 | Research Rejected alternatives/future routing, S Out of Scope:future separate process feature/OS prerequisites, не F200 AC |
| CHK007 | Research future routing/2026-09-26, Constitution II:identity/children/permissions/DRM/minimization/fallback, техническое не юридическое согласие |
| CHK008 | Constitution advanced-routing gate/P/Q:separate QA/package/resource/rollback/product approval перед future routing |
| CHK009 | Полностью прочитанные tasks не содержат driver/Stereo Mix enablement/system service implementation; T116–118 только local custody |
| CHK010 | S context/FR007 и parity source scope:copy global endpoint, не отдельный процесс |
| CHK011 | S FR019–020/SC003/008/P/Q:resource/ownership/update/rollback не kernel/virtual component prerequisite |
| CHK012 | P Complexity/source boundary, research future scope:future routing failure не незаметная замена/блокировка базового shared loopback |
| CHK013 | S FR008/021/research future routing:explicit owner/choice/Windows controls/metadata-safe limits, no Stereo Mix name heuristic |
| CHK014 | S Out of Scope/Constitution advanced routing: separate approved spec до future work, no implicit F200 task |

## Точные hashes прочитанного состояния

Ниже SHA-256 **текущих локальных байтов**, не SHA коммита и не hashes
установленного приложения. Дерево содержит чужие незакоммиченные изменения;
одного HEAD недостаточно для привязки этих документов. Root восстановлен
владельцем из startup-cleanup snapshot; reviewer проверил его стабильность,
но не подтверждает происхождение snapshot сверх сообщения владельца.
Его Git blob SHA-1 `23d8121689bea6982c319623cdd8f4fb2939b840`
и SHA-256 ниже неизменны в ходе review.

Все feature-relative пути в таблице относятся к `specs/200-windows-desktop-app/`.

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `d778aa44725911288331beeddc5a2293333bf2fb39ab93e2087a471cdb4f1c0f` |
| plan.md — после последнего уточнения bounded hash | `0cda6e6b94e40fca30d1c545255a65bcd27cc10379dcc39c7406a7df2edb766c` |
| tasks.md — после четырёх issue-ссылок | `507d5e59098ad46a878d4fc8be5de07970ef6e37d539de28b6f3340ddff743fd` |
| quickstart.md | `fc536ab5ad7576890bbe839687f29a15d90b6db7b790649df011f5d3e2476b2f` |
| data-model.md | `9883413023579202561dc214e0ce96b817c21a29a2e8af02717042dcb7a5429a` |
| contracts/windows-protected-local-custody.md | `48704f413e132f2b643206649a6422f6e6f6ea118cc63c86d5b675e9d4be9d54` |
| contracts/windows-desktop-contract.md | `8aaedaa990154a801e6b6c73ba35e304df26bc8b383a0dae35c5929617812135` |
| contracts/windows-native-web-bridge.md | `127356a14df140364ce619554bcc42cab03286262065afa40c1fcdb73ac51ff4` |
| parity-matrix.md | `72c9b6556a4d18a3b6549322b44f02ff15959d8c2eb90f00d4a982ed280a24ab` |
| research.md — ссылочные разделы | `435491ed6ea6094178e81a169152ff19d010ae7e28f41924c29a578500544125` |
| checklists/requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| checklists/security.md | `50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9` |
| checklists/audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| checklists/ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| checklists/advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |

| Обязательный общий артефакт, путь от корня | SHA-256 |
| --- | --- |
| AGENTS.md | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| docs/agent-guidance/README.md | `40e357e422c60915d2c4334c83b9ab74f5ef4c0df6ab8831e3ed16e281ba18a6` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| docs/agent-guidance/codex-worktrees.md | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` |
| docs/agent-guidance/spec-kit-flow.md | `5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887` |
| docs/agent-guidance/product-gates.md | `e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097` |
| docs/agent-guidance/release-and-validation.md | `e3d24689a330634ec5ef87d829f8bcbf16bb7b81e0196b9d0baae4f49f27278d` |
| docs/prd-voice-layer-final.md | `5c93f6a3a72e639e0cf835518f2ef5e03680b3b500c53734e3478cdd59448212` |
| docs/current-product-status.md | `014243c9fc34ad4a7c77028685c82edcfba8ef8e2a4fcff64ed0479f728d4482` |
| .specify/feature.json | `690b400b9bc43852df04feb265c544d4cde8531fb61d8f921acea757983949c4` |

| Ключевой артефакт | Git blob SHA-1 текущих байтов (`git hash-object`, без записи object) |
| --- | --- |
| spec.md | `fc0c396ce0c9cf7ea9b0cbc9d15d5df24119677a` |
| plan.md | `30e50c98020aa6355091d948f4110c898cfaf038` |
| tasks.md | `f28c9009d2c3855eaefbb9f2f6588aa46f13f0cd` |
| quickstart.md | `23fbde3587773395fd3e4cf8c5ef8e3301844765` |
| data-model.md | `fc1f76ee2f74b341d5d475ea58aa395ee846cdf7` |
| contracts/windows-protected-local-custody.md | `8814dda38b98816aa13b0b7fd4eff777010dc50d` |

## Передача main

Requirements review PASS предоставлен для указанных текущих байтов.
Все 112 критериев подтверждены, отметки не изменены. Main остаются его
собственный storage analyze/producer audit, привязка сообщённого issue sync и
status-only freshness T115/заголовков перед кодом. Их завершение этим reviewer
не проверено, как и дальнейшие T116–T118 и
общие release gates, настоящим отчётом не объявляется. Область единственной
записи reviewer — этот отчёт; других изменений нет.

## Дополнение: freshness после принятия T115 — 2026-10-02

**PASS — проверено только status-only delta текущих байтов.** Это дополнение
обновляет привязку review; прежний текст и hashes выше сохранены как история.
HEAD остаётся `99b00a579c24b50e320465b69d9a296038bc544d`.

Проверено фактическое различие contract/data-model с ранее принятыми Git blobs.
Для quickstart/plan/tasks прежние blobs недоступны в object store, поэтому
проверка выполнена обратной заменой ровно заявленных status-only фрагментов
**только в памяти**, без записи файлов. SHA-256 целого восстановленного текста
каждого из трёх файлов точно совпал с предыдущей привязкой этого отчёта.
Это проверка всего файла, не предположение по показанным строкам.

| Файл | Единственное проверенное изменение |
| --- | --- |
| protected custody contract | Title/header: T115 design accepted, ссылка на этот review и сведения main об analyze/issue sync; нормативные §§1–9 не менялись |
| data-model | §12 title/status и заключительная фраза о принятии требований; entities/таблица/authority/bounds/fences/условия runtime неизменны |
| quickstart | §12 status: проектирование принято, разрешён следующий T116/T117 шаг; вся проверочная матрица и общий допуск неизменны |
| plan | Только финальная Storage Phase1 принята со ссылкой review/analyze/issues; bounded incremental hash first-step и full-pipeline/release ограничения неизменны |
| tasks | Только T115 `[ ]` → `[X]`; текст T115, T116–T118, issue owners и зависимости не менялись |

Нормативный хвост contract, начиная с `## 1.` до EOF (включая §§8.1/8.2/9),
имеет одинаковый SHA-256 до и после delta:
`fc831b083699fb7e96f17cb642ad9a50b79d68bb2130fff69d4e2500b3151c6b`.
Spec requirements и root AGENTS SHA-256 также неизменны. Пять checklist-файлов
совпали с предыдущими hashes; пересчёт по всем `checklists/*.md` сохранил
112 checked / 0 unchecked. Новых критериев и изменений markers нет;
полное предыдущее перечитывание 112 пунктов остаётся применимым.

| Текущий артефакт, путь от feature | SHA-256 | Git blob SHA-1 |
| --- | --- | --- |
| contracts/windows-protected-local-custody.md | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` | `6a8a3f2cce5c81640c8a5334041ebfec5523362d` |
| data-model.md | `b494c57fa6cff34c0128d674677f5fca09e647aabbf60aea15c2a53603c43848` | `51fefa6fe5a31207719a02c7bd081827218853f0` |
| quickstart.md | `9946be5c60a192c2fcb92d7c8db1419827ff757fea8c13d40b9023b949ce1d59` | `639db6cde0b54f9cae03d7674dac0d20a7d7774d` |
| plan.md | `34e64befcd775c85ee524a8d0e097d7d08805545cec92966bfdbf98d446f71cc` | `9fd9d32b9b6c40dc11e241dc61ae5546b377ae68` |
| tasks.md | `76c91845c3ce5da964351cca95b027562190bbc0fcb9f76b7159d0d021261287` | `892dda0c8de96b1f5956091093c976c88b7ef8e8` |

По сообщению main, scoped analyze повторно прочитан и сохраняет CRITICAL=0/
HIGH=0, canon owners OPEN. Здесь подтверждены отражение этих сведений в статусах
и неизменность требований; самостоятельно analyze/GitHub/bootstrap не запускал.
Закрытая отметка T115 означает принятие проектирования, не реализацию storage.
Открытый canonical owner issue не превращается в выполненный issue этим review.

Независимый допуск требований остаётся PASS на новых байтах; blocker со стороны
этого reviewer для начала bounded-hash regressions нет. Это первый ограниченный
шаг T116 в существующем Storage/Sha256.*, не полный T116/T118 PASS. Clock/T119
не storage defects; общий F200/installed/physical/migration/release допуск не
сокращён. Изменено только append-only дополнение этого отчёта, без кода,
других документов, marker edits, коммитов и внешних операций.
