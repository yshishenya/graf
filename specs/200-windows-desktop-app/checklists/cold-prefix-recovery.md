# Construction B: качество требований cold-prefix recovery

Создан: 2026-10-16. Feature: [spec.md](../spec.md).
Назначение: независимый нормативный gate перед реализацией узкого B в T116.
Сформирован через speckit-checklist; проверяется качество требований, не код.
Review ownership: markers принадлежат независимому reviewer.
`[x]` означает достаточность формулировки и согласованность оснований, а не
выполнение runtime cut, готовность реализации или завершение T116.

## Scope и полномочия

- [x] CHK001 Определён ли положительный результат B как cold capturing/finalizing → фактически проверенный playable sealedDegraded только при unused outputs, с явным исключением started/orphan continuation и Native integration? [Completeness, plan B introduction/§5–7; quickstart B]
- [x] CHK002 Задано ли existing-only получение writable ownership под непрерывным root/package/role lease без CREATE_NEW identities, повышения readonly A до writable или release/reopen? [Security, plan B §1, §6; research B]
- [x] CHK003 Однозначно ли unused role определяется одновременно union refs BOTH slots и точным inventory id.bin, а missing/collision/partial/singleton/bad peer/started content требуют сохранённого отказа? [Clarity, plan B §1–3; data-model B; quickstart B]
- [x] CHK004 Отделены ли первая публикация content в существующей unused role от ремонта metadata birth, выбора orphan и сброса generation/base? [Consistency, plan B §2–3; local custody §4]

## Префикс, история и конечные артефакты

- [x] CHK005 Требуют ли правила readonly canonical Tree, проверки BOTH closure и exact complete480 prefix без checkpoint/truncate/padding/re-AEC, при сохранении всех исходных logical bytes включая хвост? [Integrity, plan B §3, §5; local custody §4; packed custody retained roots]
- [x] CHK006 Связана ли принимаемая история manifest с действующим bound ref и selected actual metadata generation, с отказом для newer-unbound и peer-only истории? [Authority, plan B §3–4; research B]
- [x] CHK007 Определены ли phase-aware closed parsing без ослабления sealed normal validator, проверка session/privacy связанных snapshots и точное сохранение OPEN/CLOSE, IDs, неизвестных границ и optional times без синтеза? [Privacy, plan B §4; data-model B; quickstart B]
- [x] CHK008 Задан ли measurable конечный результат через существующие WAV/AAC loops, recovery record, manifest rollover, sealedDegraded ACK и полную semantic inspection с exact duration и ненулевым decoded AAC? [Measurability, plan B §5–6; quickstart B; local custody §4]

## Отказы, ресурсы и границы приёмки

- [x] CHK009 Различены ли pre-effect refusal и possible-publication failure с сохранением artifacts, отсутствием ложного playable claim и запретом factory retry поверх started outputs? [Failure coverage, plan B §6/end; quickstart B]
- [x] CHK010 Указаны ли освобождение временных readers при сохранении native leases, worker-only terminality и проверки cancel/job/pin/memory без новых pools или повышения действующих limits? [Resource consistency, plan B §5–7/end; local custody §5; construction A]
- [x] CHK011 Исключены ли изменения queue/original owner, account inference, normal/upload/deletion/public authority и повторные append/privacy/finalize после recover? [Scope consistency, plan B §7; data-model B; tasks T116]
- [x] CHK012 Заданы ли реальные RED/GREEN cold fixtures для обеих фаз, exact disk/hash/history/queue checks, negative cases и отдельный учёт publish/rollover/final-ACK cuts без переноса старого PASS или закрытия T116? [Validation quality, plan B acceptance/end; quickstart B; tasks T116–T118]

## Evidence и границы

Reviewer: независимое чтение четырёх B-разделов, scoped analyze и сверка
неизменённых contracts/spec/tasks/constitution; подробности в
[отчёте Round446](../review-2026-10-16-round446-cold-prefix-recovery-requirements.md).
Все будущие runtime cuts остаются непроверенными этим checklist.

## Native startup B — требования Round448

Отдельный этап после standalone B; исключение Native integration в CHK001
описывает границу прежнего этапа, а не запрет следующего. Новые пункты также
оценивают только качество текущих требований, не реализацию или runtime.

- [x] CHK013 Ограничен ли native результат capturing/finalizing → sealedDegraded без normal proof, queue promotion/ticket, HTTP и нового доступа quarantine playback? [Scope, plan Round448; data-model native handoff; quickstart Round448]
- [x] CHK014 Требуется ли fresh exact reservation до acquisition: local/directory/session/path, original owner pair, status/reason/updatedAt, server/deletion fences, без назначения current account и без запрета из-за unrelated generation? [Authority, plan Round448 п.1; spec Start-owner; start-owner CHK005]
- [x] CHK015 Разделены ли private existing-only acquisition единственным storage owner и полный prefix/history/hash/WAV/AAC/decode на существующем executor без передачи StoreOwner, новых pools или повышения resource limits? [Threading/resources, plan Round448 п.2; custody §5; CHK010]
- [x] CHK016 Заданы ли освобождение пробного readonly pair до независимой writable acquisition и однократная передача prepared writer под mutex без превращения readonly proof в effect authority? [Lifetime, plan Round448 п.2–3; construction B §1–3]
- [x] CHK017 Требуется ли фактическое освобождение package/writer/inspection executor до recoveryDone на успехе, отказе и cancellation, без UI/native proof и ложного drain от одного callback? [Failure completeness, plan Round448 п.3/5; quickstart; custody §7]
- [x] CHK018 Сохранены ли Record/Stop/EOS во время старого encoding и реальные owner/reconciliation fences до retirement, включая ambiguous/lost-poll outcome, без stale dispatch или owner reopen при удерживаемом package? [Concurrency, plan Round448 п.5; custody §5/7/Start-owner; start-owner CHK009/010]
- [x] CHK019 Требуют ли deletion/изменение исходной reservation/shutdown отмены B, а физический purge — ожидания actual retirement, не одного cancellation flag или timeout? [Deletion truth, plan Round448 п.1/5; custody §7; constitution IV]
- [x] CHK020 Сохранены ли BOTH union/unused/history/privacy/optional times/canonical invariants standalone B и отказ без записи для started/orphan/already-degraded при отсутствии автоматического factory retry? [Integrity, plan Round448 п.4–5; construction B; CHK003–009]
- [x] CHK021 Измеримы ли cold native positives обеих фаз при original A/current B через actual startup ACK, полную cold degraded/AAC inspection, unchanged canonical/queue и ноль mutation ticket/HTTP? [Measurability, quickstart Round448; plan acceptance]
- [x] CHK022 Названы ли реальные held-read Start/Stop и drain/refusal проверки, прежние normal/degraded/playback/revalidation/V5 regressions и отдельные пределы synthetic/installed/hardware/release/T116 acceptance? [Validation boundaries, plan/quickstart Round448; constitution VI]

Независимая оценка Round448: CHK013–022 — 10 checked / 0 unchecked;
всего в этом checklist 22 / 0. Основания — текущие четыре append448 и
неизменённые spec/contracts/tasks/constitution; scoped analyze C0/H0.
Риски cancellation/ambiguous/drain и будущие runtime доказательства описаны в
[отчёте448](../review-2026-10-16-round448-native-cold-recovery-requirements.md).
Отметки не принимают будущий split, native runtime или T116 целиком.

## Owned-degraded local playback — требования Round451

Этот этап отдельно расширяет пользовательский доступ после B; CHK013 сохраняет
историческую границу Round448. Пункты ниже оценивают требования, не выполнение.

- [x] CHK023 Ограничено ли новое исключение exact original-owned quarantined/capture_prepared с localId=directoryId=sessionId, текущим подтверждённым user/workspace и отказом при aliases/server/deletion/active-session, без общего допуска quarantine, unowned или unknown? [Scope/security, plan451 п.1/3; custody §Owned-degraded local playback; start-owner CHK004–006]
- [x] CHK024 Отделён ли display-only playableDegraded от native authority: full sealedDegraded/AAC inspection, fresh package context/generation adoption и snapshot/epoch binding, без разрешения по одной duration или передачи proof/path в UI? [Clarity/authority, plan451 п.2; data-model §display-only degraded playback; security CHK009–010]
- [x] CHK025 Требуется ли для actual open и дальнейших команд fresh owner/queue/exact reservation including status/reason/updatedAt, shared aliases/deletion policy, actual sealedDegraded/full retained proof и прежняя revalidation, при сохранении normal branch и worker/executor boundary? [Consistency, plan451 п.3; custody §§6–7 и owned-degraded append]
- [x] CHK026 Согласованы ли current auth/document/command-serial fences, cancellation и actual engine/readers/pins retirement перед purge при изменении строки, удалении и shutdown, без ложного drain от scalar/timeout? [Lifecycle coverage, plan451 п.3–4; custody §7 и owned-degraded append; constitution IV]
- [x] CHK027 Сохранены ли неизменные queue/status/reason/original owner/generation и local-only semantics: Send=false/HTTP0/no normal/Saved/uploadComplete, без нового player/pool/schema/claim/repair или ослабления Record/Stop? [Scope consistency, plan451 п.1–4/Constitution check; data-model append; start-owner CHK010]
- [x] CHK028 Заданы ли measurable genuine cold B→A owner-specific display/play/pause/seek, сохранность bytes/queue, отрицательные no-scalar/foreign/unowned/stale/active/deletion/unfinished/corrupt/nonplayable cases, auth/delete invalidation и прежние playback/revalidation/deletion/V5 regressions с отдельной runtime acceptance? [Validation quality, plan451 acceptance; quickstart §owned-degraded local playback; constitution VI]

Независимая оценка Round451: новые CHK023–028 —6 checked/0 unchecked,
всего28/0. Ссылки и текущие normative SHA — в
[review451](../review-2026-10-16-round451-owned-degraded-playback-requirements.md).
Поддержано качество требований, не display bool/native implementation,
не runtime PASS, UI acceptance или завершение T116.

## Готовый WAV до AAC — требования Round461

Исторические CHK001/003/020 сохраняют границу unused construction B. Новое
исключение оценивается отдельно, без принятия произвольных started outputs.

- [x] CHK029 Определены ли exact WAV-ready структура, BOTH-valid/selected-finalizing, bound history и unused playback/recovery без принятия одного flush как завершённого ACK? [Completeness, plan461 admission/п.1–3; spec FR-012/013]
- [x] CHK030 Однозначны ли fresh mixed права ролей, непрерывные leases и запрет readonly upgrade/переноса отказавшего proof при сохранении прежних unused/completed guards? [Clarity/security, plan461 п.1; constitution IV]
- [x] CHK031 Заданы ли независимо same-Guard exact physical EOF и полное побайтовое равенство WAV canonical-конверсии с cancellation/EOF/sticky-fault до любого нового эффекта? [Integrity/measurability, plan461 п.2–3; quickstart461]
- [x] CHK032 Согласованы ли неизменные canonical/WAV/IDs/queue/owner, новый AAC только в unused role, degraded-only final ACK/inspection и отсутствие normal/upload/repair authority? [Consistency, plan461 п.4–5; spec FR-012/013/014/022]
- [x] CHK033 Достаточно ли описаны сохранённые отказы для unknown tail, valid wrong PCM, invalid/partial peer, начатых outputs и cancellation, включая snapshot equality и запрет повторного эффекта? [Failure coverage, plan461 acceptance/п.4; quickstart461]
- [x] CHK034 Разделены ли tests-first actual physical RED/GREEN и полная регрессия от device/installed/hardware/release acceptance без новых executors или повышения resource/deadline limits? [Validation quality, plan461 п.5/acceptance; quickstart461; spec SC-005/006]

### Независимая оценка Round461 — 2026-10-19

**GO только качеству проекта WAV-ready; scoped analyze CRITICAL=0/HIGH=0.**
CHK029–034: 6 checked / 0 unchecked; перечитанный checklist целиком: 34 / 0.
Основания и точные хеши — в
[собственном отчёте Round460, дополнение461](../review-2026-10-19-round460-diagnostic-gate.md#append461--requirements-и-scoped-analyze-wav-ready).
Проверены актуальность всех 12 тематических checklist и сохранение старых
unused/completed, Start-owner, security, privacy и actual-retirement требований
в этой области. Их отметки не являются новой общей или runtime приёмкой.

Прежний feasibility NO-GO в отчёте сохранён: он относился к отсутствовавшим
тогда mixed acquisition, strict media extent и полному сравнению PCM.
Теперь эти обязательства явно заданы plan461/research461/quickstart461;
их будущая реализация ещё не доказана. Допуск не переносится на произвольные
started outputs, readonly upgrade, изменение canonical/WAV/owner, normal/upload,
T116 целиком или выпуск. Следующий этап — предусмотренный actual physical RED
на старом исходнике; затем отдельные actual-diff и runtime gates.

### Уточнение WAV29 op5/op6 — независимый повторный gate

Проверены обновлённые финальные plan461/research461/quickstart461: shape proof
не изменён; op5 после полного HEAD transfer и op6 после flush должны пройти
одинаковые строгие positive assertions. Full matrix24/continued4, filtered
op6 executed1/continued1 и семь refusals; process crash не доказывает старый
flush/checkpoint ACK или power-loss durability. Другие started outputs,
readonly upgrade, repair/retry и ослабление ресурсов/сроков не разрешены.
CHK029–034 повторно supported:6 checked/0 unchecked; весь перечитанный файл
34 checked/0 unchecked, markers не изменены. Scoped analyze C0/H0/M0/L0;
GO требованиям перед test-only edits, не будущему actual source/runtime.
WAV29 RED и прежние ограничения сохранены. Exact hashes и основания:
[собственный отчёт Round460](../review-2026-10-19-round460-diagnostic-gate.md).

## Начатый AAC — требования раунда462

Новые пункты оценивают требования до test-only/production edits. Исторические
CHK003/020/032/033 сохраняют границы прежних branches; отдельное исключение не
разрешает общий repair, изменение sealed data или original owner.

- [x] CHK035 Однозначно ли заданы допустимые unsealed playback/package/history/inventory и отказные incomplete birth/HEAD/metadata shapes без подмены полного P2/T116 более узкой целью? [Completeness, plan462 admission/границы; spec FR-012/013]
- [x] CHK036 Описаны ли fresh mixed rights/непрерывные leases, private playback-only prepared writeExisting, same-HANDLE IDs и запрет readonly upgrade/новых IDs? [Security/clarity, plan462 п.1–2; packed contract «Начатый playback»]
- [x] CHK037 Требуется ли полный BOTH/retained/canonical/history и strict bytewise WAV proof до первого эффекта с различием reachable corruption и сохраняемого orphan playback tail? [Integrity/consistency, plan462 п.2–3; spec FR-012]
- [x] CHK038 Однозначны ли logical reset/monotonic generation/append-after-actual-EOF и неизменность старого physical extent/canonical/WAV/IDs/queue/owner, включая готовый unsealed AAC? [Clarity/measurability, plan462 п.3/5; data-model462; contract]
- [x] CHK039 Полно ли описаны повторный crash, sticky cancel/native/crypto/quota failures, physical cap с orphan records и прежние limits/actual drain без same-owner retry? [Failure/resource coverage, plan462 п.4/acceptance; spec SC-005/006]
- [x] CHK040 Согласованы ли degraded-only ACK/full inspection и отсутствие normal/upload/claim/нового формата с неизменными unused/completed/WAV guards и границами T117/118? [Scope/consistency, plan462 п.5/Constitution check; spec FR-012/013/014/022]
- [x] CHK041 Измеримы ли actual RED/GREEN, real MF partial>256KiB, exact outcomes повторных cuts, сохранность старых bytes/refusal snapshots при отдельной native/installed/hardware/release приёмке? [Validation quality, plan462 acceptance; quickstart462; spec SC-005/006]

### Независимая оценка Round462 — 2026-10-19

**NO-GO перед test-only edits: scoped analyze C0/H1/M1/L0.**
Новые CHK035–041: 4 checked / 3 unchecked; весь файл: 38 / 3.
CHK035/036/037/040 поддержаны только как качество требований указанной ветви,
с сохранением прежнего unfinished history predicate; это не source/runtime GO.
Ни один старый marker не снят; остальные 11 тематических checklist не изменены.

- CHK038 оставлен открытым: plan462 п.3, data-model462 и packed append462
  обещают следующее поколение reset без исключения для уже пустого playback.
  Действующий packed contract §4 требует same-length committed no-op того же
  proof/generation; Writer::resize также не публикует HEAD для 0→0. Нужна
  согласованная техническая поправка: nonempty→0 увеличивает поколение;
  empty→0 сохраняет его, первая запись возникает позднее при encode. В empty
  fixture нельзя ожидать несуществующий reset-HEAD cut или сброс birth/base.
- CHK039/041 оставлены открытыми в части exact repeated-crash outcomes:
  требование перечислить их есть, но соответствие physical metadata shapes
  единственному ожидаемому исходу ещё не задано. Нужна конечная таблица для
  reset/append/HEAD, manifest retire/write/bind, recovery birth/commit и final
  seal. В частности, newer-unbound manifest не разрешает fallback; bound
  terminal manifest при unused recovery не проходит прежний unfinishedHistory,
  а complete recovery относится к отдельной completed continuation. Выбор
  старой history или повторное кодирование sealed refs не разрешены.

Конфликт с immutable sealed artifacts или разрешение authority по orphan tail
не выявлены при сохранении admission: только live canonical/bound manifest refs,
readonly canonical/WAV, full BOTH closures и старый physical extent. Утверждение
о готовности произвольного повторного crash не поддержано. Исправления выше —
технические; нового продуктового ответа не требуется. Полный T116/P2, T117/118,
остальные interrupted shapes и installed/hardware/release gates открыты.
Точные SHA, применимость всех 12 checklist и source evidence — в
[собственном отчёте Round460, дополнение462](../review-2026-10-19-round460-diagnostic-gate.md#round462--независимый-requirements-gate-начатого-aac).

### Повторный gate Round462 — I1/U1 исправлены

**GO качеству требований перед test-only short RED; scoped analyze C0/H0/M0/L0.**
Предыдущий NO-GO выше сохранён как оценка прежних SHA, а не текущий результат.
Новые CHK035–041: 7 checked / 0 unchecked; перечитанный файл: 41 / 0.
CHK038/039/041 отмечены после проверки фактических исправлений пяти нормативов;
ранее поддержанные CHK035/036/037/040 остаются применимыми без ослабления.

I1: nonempty→0 даёт ровно+1; empty→0 — тот же proof/generation, без HEAD write
и без reset-HEAD cut. Это согласовано с прежним same-length contract и Writer.
U1: конечная таблица plan462:2775–2808 содержит15 физических shapes с заранее
единственным R/C/D/S. Retire со старой unfinished history — R; metadata orphan,
newer-unbound, terminal-bound при unused recovery и singleton recovery — D;
готовые terminal members/finalizing — прежняя completed C; selected sealed —
отказ recover и отдельная readonly inspection S; torn final state — D.
Остальные preflight/content/history predicates и отсутствие cancel/pressure
обязательны: строка не становится допуском только по номеру cut/flush.

Не разрешены rollback history, reset sealed artifacts, принятие orphan как
authority, readonly upgrade или retry failed owner. Canonical/WAV/старые
playback bytes/IDs/queue/original owner и пределы ресурсов/сроков сохранены.
Это requirements GO, не actual test-diff/source/runtime GO. Будущий короткий
RED не заменяет real MF partial>256KiB, повторные crash/fault/regression проверки,
полный P2/T116 или installed/hardware/release acceptance. Продуктовых вопросов0.
Точные текущие SHA и основания:
[дополнение отчёта](../review-2026-10-19-round460-diagnostic-gate.md#round462--повторный-gate-после-исправления-i1u1).

## Terminal manifest и unused recovery — требования468-U2

Прежний462-U1 D для этого shape — историческое основание до468-U2. Новые пункты
оценивают только качество требований, не код, runtime или закрытие T116.
Markers остаются reviewer-owned; новые пункты сформированы без отметок.

- [x] CHK042 Однозначны ли exact terminal-bound/selected-finalizing admission, BOTH union/inventory и recovery ровно id.bin без orphan/partial/ref в peer, при сохранении отказов других shapes? [Completeness, plan468-U2 п.1; packed contract468-U2]
- [x] CHK043 Заданы ли fresh mixed existing-only права четырёх readonly members и writable recovery/package-state, непрерывные leases, исходные IDs и отсутствие readonly upgrade/переноса отказавшего proof? [Security/clarity, plan468-U2 п.1; data-model468-U2]
- [x] CHK044 Требуется ли до первого эффекта полная canonical/hash/strict WAV PCM/EOF/AAC/history/session/privacy/optional-times проверка без ослабления unfinished parser и создания fake proof? [Integrity/consistency, plan468-U2 п.2–3; research468-U2]
- [x] CHK045 Отделены ли value-only recovery proposal, actual g1 BOTH readback, final sealed ACK и fresh inspection, с неизменными четырьмя members/queue/owner и без normal/upload/claim authority? [Authority/measurability, plan468-U2 п.3–5; packed contract468-U2]
- [x] CHK046 Полны ли pre-effect byte-preserving refusals и sticky post-effect faults/cancel без same-owner retry/cleanup, с прежними ресурсными пределами и actual retirement? [Failure/resource coverage, plan468-U2 п.5/acceptance; constitution IV/VI]
- [x] CHK047 Согласованы ли tests-first meaningful physical RED/GREEN, exact U/D/C/S матрицы и сохранённые старые TIMEOUT с независимыми source/runtime/installed/hardware/release gates? [Validation quality, plan468-U2 acceptance; quickstart468-U2; spec SC-005/006]

### Независимый requirements/scoped analyze gate468-U2 — 2026-10-21

**GO только требованиям перед test-only edits; C0/H0/M0/L0 в этом scope.**
Перечитаны все47 критериев: CHK042–047 supported6/6; итог47 checked/0 unchecked.
Прежние41 сохраняют основания в границах своих этапов: ограничения unused B
не являются запретом отдельно описанных WAV/playback/terminal-unused layouts.
Предыдущие NO-GO и исторический D для terminal-unused не изменены.

Selected terminal bound и valid старый unfinished peer не требуют двух terminal
копий. Exact physical EOF не запрещает сохранённые внутренние orphan records;
новый неизвестный хвост/metadata orphan/partial recovery остаются отказами.
Value proposal не proof: genuine recovery g1 BOTH/readback, затем final seal и
fresh inspection обязательны. Sticky boundary задана до commitMetadata, включая
ошибки после успешного recovery commit; обязательный publication ACK не обрывается.
Один shape U охватывает repeated19 cut13 и old24 cut18; прочие18/23 исхода
сохранены, новые шесть cuts заранее D/D/D/C/C/S. 49 returned-fault sticky
ожиданий не разрешено заменять успешным recover на том же отказавшем owner.

Применимость остальных11 тематических checklist проверена; их markers не
менялись, это не новая общая приёмка. Точные normative SHA и трассировка —
[собственный отчёт, дополнение468-U2](../review-2026-10-19-round460-diagnostic-gate.md#round468-u2--requirements-only-gate-перед-test-edits).
Продуктовых вопросов0. Source/runtime GO не выдан; AAC47/AAC56 RED, полный
T116 и installed/hardware/accessibility/release gates остаются открытыми.

### Уточнение469 — повторный scoped gate после dispatch H1

**GO требованиям/конструкции469; C0/H0.** Перечитаны пять append469 и affected
CHK042–047: 6/6 supported; весь файл47 checked/0 unchecked, markers неизменны.
Новый критерий не нужен: dispatch уточняет admission/rights/preflight существующих
CHK042–044 и negative/regression coverage CHK047. Ранее отозванный construction
GO не восстановлен задним числом; STOP/H1 сохранён в отчёте как прежнее evidence.

До первого openUnfinished — bounded readonly metadata classification; package
и metadata slots независимы, каждый bound ref проверяется по identity/generation/
length/hash, selected binding — selected metadata. none требует явной normal
проверки, а не parse failure; terminal не переходит в R. No-manifest допустим
только при обоих unfinished/live canonical slots с согласованными IDs/container,
без иных refs и с проверкой cancel. Normal не получает новых privacy/times
equality или semantic требований к unbound metadata peer; terminal проверяет
оба metadata slots строго. Все metadata leases освобождаются до fresh acquisition;
worker ReasonCode не proof, full executor verification и прежние limits остаются.
Это допуск подготовки production diff, не actual source/runtime GO. Точные SHA
и construction obligations — в дополнении469 собственного round460 report.
