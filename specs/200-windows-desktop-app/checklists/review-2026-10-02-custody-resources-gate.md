# Независимый requirements gate ресурсов — T116

Дата среза: 2026-10-02 UTC; локальный контекст Europe/Istanbul — 2026-10-03.
Root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Branch: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.

## Решение

**PASS требований, 112/112; новых нормативных blockers: 0.** Разрешён ближайший
ограниченный шаг: общий process64MiB allocator для реальных `CustodyBytes` и
`index.entries`, применённый к codec/Files allocations, copies и results.
Сначала регрессии этого этапа, затем реализация. Это допустимый фазовый подход
по завершающему accepted plan/T116, не новое проектирование или ослабление норм.

Standalone transfer-only RAII primitive тоже допустим как подготовительная
часть, но отдельный manager не обязателен. Последнее предложение main — сразу
подключить allocator к реальным allocations — заменяет идею unused helper.
Главное требование: reserve до allocation и ownership до actual deallocation.

**Не принимаются** код allocator, весь pipeline/process quota, cache/dirty/pin
registry, async integration, logical commit, T116/runtime/installed/release.
Risk lane: **high-risk-product**. `speckit-implement` использован для независимого
checklist/analyze/ownership gate, не выполнения кода/hooks/task marking.

## Свежесть

Git root/branch/HEAD, active feature pointer и read-only prerequisites
`--json --paths-only` подтверждены. Все 6 feature и 10 root/constitution/
guidance/product/pointer SHA ниже совпали с полным
`review-2026-10-02-storage-independent.md`: его ранее полностью прочитанное
поэлементное основание переиспользовано; перечитаны актуальные resources/IO/
lifetime/failure нормы §§3/5–7/9, data-model §12, quickstart §12 и порядок T116.

Все 35 Markdown checklists/report files до записи просканированы, markers
5 checkbox-файлов перечитаны; их полные SHA неизменны. 30 reports без checkbox
не FAIL. После этого отчёта: 36 Markdown, 5 checkbox, 31 без checkbox.

| Checklist | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | --- |
| advanced-routing.md | 14 | 0 | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| audio-capture.md | 24 | 0 | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| requirements.md | 22 | 0 | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| security.md | 27 | 0 | `50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9` |
| ux.md | 25 | 0 | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| **Всего** | **112** | **0** | Custom **90/90**, built-in **22/22** |

Markers изменены: **0**. Это качество требований, не hardware/runtime proof.
Accepted plan сохраняет storage analyze CRITICAL=0/HIGH=0, отсутствие storage
clarification blockers, issue-sync #7443–#7446/canon PASS, T116 owner #7444.
Evidence привязано к неизменным нормативным bytes, не новому analyze/live GitHub.
T116–T118 открыты; clock T094–T096/T119 не зависимости этого development шага.
Round207 source/runtime завершён по сообщению main; snapshot source report
заключает Approved source only/0 blockers. Runtime/installed лично не проверял.

## Обязательства ближайшего real allocator этапа

- Один общий предел **64MiB на процесс**, concurrent reserve до underlying
  allocation. Не per-object/per-container/per-thread/allocator-instance budget.
  Учитывать capacity в bytes, проверять multiplication/addition overflow до
  reservation/allocation; `clear`/меньший size не освобождают живую capacity.
- Одновременно считать все охваченные живые allocations: оба index candidates,
  entries, decoded/serialized index, cipher/plain, copies и returned results.
  При grow old+new capacity остаются charged до actual old deallocation, не
  только delta. Shared одна allocation считается один раз; отдельные copies —
  каждая отдельно. Move/transfer/swap не теряют charge; copy резервирует новый.
- Allocation/`bad_alloc` failure откатывает reservation ровно один раз. Release
  только при actual deallocation; возврат из worker/helper не release результата.
  Учёт и owner должны переживать все живые результаты и jobs, без underflow/
  утечки/oversubscription. Source review подтверждает реальные application sites,
  не только тест standalone counter. Сообщение main об отсутствии прежнего helper
  не проверялось независимым аудитом кода.
- **Явный budget/allocator отказ, fail-closed.** Contract не требует отдельного
  wire enum/нового status для различения этих причин. Существующая локальная
  typed failure категория достаточна, если обе причины не превращаются в
  missing/invalid-content/corruption/fallback success. Раздельный local reason
  допустим; новые значения протокола не нужны. Native/hash/unknown IO отказ
  также не artifact corruption; успешная другая slot не подавляет этот отказ.
- Отказ до принятия изменения не normal save/empty ledger/swap/plaintext обход.
  Logical error sticky/got0, partial buffer не используется. При отказе после
  publish allocator не определяет `not_committed`: worker reconciles до
  committed либо ambiguous; последнее блокирует writes/effects/GC. Physical
  published **не** logical ACK.
- MF/DPAPI internal allocations измеряются отдельно. App-owned копии их выхода,
  metadata/CNG/hash buffers не становятся internal только из-за native origin.
  Неохваченные string/JSON/cache/hash/upload/CopyTo/async allocations остаются
  следующей integration обязанностью, не доказанным общим process PASS.

## Оставшаяся logical IO/cache/pins/lifetime integration

Действующие границы сохраняются одновременно, не как независимые добавочные квоты:

- Owned64MiB включает indices/candidate copies, cipher/plain, metadata
  serialization, hash/upload/CopyTo buffers и cache (§5).
- Shared plain cache **≤2MiB суммарно на процесс/общий для Clone**, внутри64MiB.
  Одна dirty seek/rewrite группа **≤4blocks/≤1MiB**, без накопления следующих,
  тоже внутри64MiB. Крупные Write/CopyTo/hash chunks **≤256KiB**.
- **Clones/pins≤32 на процесс**, не на артефакт. Отдельно: один исполняемый
  candidate на ledger, **≤32 bounded commands/results**, включая retained
  completions. Quota/count token не registry generation/refs/persistent roots.
- Clone: independent cursor/same pinned generation/shared cache. Read только
  verified exact full/tail/ZERO bytes; EOF/S_FALSE/got, signed Seek/overflow,
  read-only rejection, SetSize/shrink/rewrite/extension, bounded CopyTo и
  Commit flags/error semantics остаются §6. Full metadata — один commit, не
  публикация промежуточного JSON из dirty groups.
- Worker держит candidate/pins/lease/result до actual terminal completion **и**
  adoption либо revalidation. Удерживаемые result allocations продолжают charge.
  Stop/cancel/timeout/lost callback/UI close не освобождают занятый owner.
  Store и ресурсный учёт переживают UI/controller; jobs владеют value snapshot,
  cancellation, store/account epoch, package ID/state generation и pin, не raw
  UI/controller/queue pointers. Stale UI не effects; committed storage adoption
  сохраняется. Следующая mutation только от принятой generation.
- MF Shutdown/release engine/byte stream **до release pin**; playback
  Pause/resume/seek/Stop держат один pin. Delete ждёт actual выход owners/flight/
  finalizer, timeout сохраняет pending/lease. Shutdown закрывает admission,
  отменяет jobs, сохраняет ownership до actual exit; no encoding/network destructor.
  Finalization освобождает writer copies перед reopen. UI/readiness/WASAPI не
  выполняют disk/crypto/scans/hash/encode/GC; existing workers сохраняются.
- GC≤64objects/pass, streamed; refs обоих indices/pinned snapshots/dirty
  candidate/package-state сохраняются. После restart transitive roots обоих
  valid metadata slots восстанавливаются до GC; token прошлого процесса не root.
  Invalid/unknown/ambiguous блокируют GC. Allocator не разрешает GC/migration.

## Регрессии и порядок доказательства

1. **Сейчас:** реальные codec/Files containers и results: aggregate capacity
   нескольких objects/threads, exact64MiB/overflow/refusal-before-allocator,
   bad_alloc rollback, old+new reallocation peak, clear/shrink/deallocation,
   copy/move/swap/returned-result lifetime; сохранение wire/bytes/errors.
2. **Следующий logical слой:** реальный Read/Seek/SetSize/CopyTo/Clone, shared
   cache admission/eviction, dirty/pin limits across objects, same-generation
   roots и error fences. Counter тесты не доказывают эти integrations.
3. **Async/native consumers:** delayed/pending/ambiguous commit, lost/stale
   callback, actual worker/result retention/adoption, MF shutdown и delete/
   account/shutdown races с реально удерживаемыми allocations/refs; metadata
   pair/partial birth и ordered durability. Не требуются для закрытия только
   allocator этапа, но обязательны прежде соответствующего integration PASS.
4. **Полная T116/T118:** generated protected canonical→WAV/AAC→manifest/state→
   restart→inspect/hash/playback/upload/reconcile/delete, все temp producers,
   simultaneous owned/native memory peaks, PRD disk reserve/retention,100cycles,
   installed matrix. Primitive/allocator не доказывает pipeline или SC-003
   resident growth≤128MiB/CPU/latency/Stop. Hardware/audio/clock/calendar/release
   остаются отдельными условиями, не новыми blockers этого ограниченного шага.

## Текущие нормативные SHA-256

| Файл | SHA-256 |
| --- | --- |
| spec.md | `d778aa44725911288331beeddc5a2293333bf2fb39ab93e2087a471cdb4f1c0f` |
| plan.md | `34e64befcd775c85ee524a8d0e097d7d08805545cec92966bfdbf98d446f71cc` |
| tasks.md | `76c91845c3ce5da964351cca95b027562190bbc0fcb9f76b7159d0d021261287` |
| quickstart.md | `9946be5c60a192c2fcb92d7c8db1419827ff757fea8c13d40b9023b949ce1d59` |
| data-model.md | `b494c57fa6cff34c0128d674677f5fca09e647aabbf60aea15c2a53603c43848` |
| contracts/windows-protected-local-custody.md | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |
| Contract tail от `## 1.` до EOF | `fc831b083699fb7e96f17cb642ad9a50b79d68bb2130fff69d4e2500b3151c6b` |
| AGENTS.md | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| docs/agent-guidance/README.md | `40e357e422c60915d2c4334c83b9ab74f5ef4c0df6ab8831e3ed16e281ba18a6` |
| docs/agent-guidance/codex-worktrees.md | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` |
| docs/agent-guidance/spec-kit-flow.md | `5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887` |
| docs/agent-guidance/product-gates.md | `e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097` |
| docs/agent-guidance/release-and-validation.md | `e3d24689a330634ec5ef87d829f8bcbf16bb7b81e0196b9d0baae4f49f27278d` |
| docs/prd-voice-layer-final.md | `5c93f6a3a72e639e0cf835518f2ef5e03680b3b500c53734e3478cdd59448212` |
| docs/current-product-status.md | `014243c9fc34ad4a7c77028685c82edcfba8ef8e2a4fcff64ed0479f728d4482` |
| .specify/feature.json | `690b400b9bc43852df04feb265c544d4cde8531fb61d8f921acea757983949c4` |

## Область записи

Изменён только этот новый report; прежние reports/markers/нормы/код сохранены.
Tests/build/VM/audio/GitHub/external writes/commit/migration/install не выполнялись.
Только read-only проверка и `apply_patch` собственного отчёта, с final reread.
