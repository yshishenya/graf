# Round277 — REQUIREMENTS / scoped analyze: настоящая queue recovery

**SCOPED REQUIREMENTS GO — C0/H0 для изложенного ниже среза.**
Это допуск RED/реализации, не SOURCE/исполненные тесты/full T116/product GO.
Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty сохраняется.
Reviewer применил speckit-checklist/analyze read-only; VM/build/tests не запускал.
Единственная разрешённая запись — этот новый отчёт с 0 checkboxes.

## Нормативная база и реальные caller semantics

Plan:1802–1891, особенно1839–1854, custody §4/§5:206–243 и §8:328–360,447–464,
FR-012/013/014/022 и T116:568 покрывают worker ownership, typed commit/adoption,
сохранение logical v3/read-v2, отсутствие plaintext fallback и ложных effects.
Конституция II/IV/VI, current десять normative checklists и guidance сохранены;
исторический SOURCE276 подтверждает только startup, не mutation/fault coverage.
REQ276 SHA `29f499af128e7a6826e55bcf5c4405d32b86dcc4588581a0719cd76116d2d556`;
plan SHA `5d01df02ef0ff32f2a3ccaf7158133726a62a10a7643098610c50b1c69c7fe00`.
Лично прочитаны NativeCapture.h:261–314,615–673, Scheduler.cpp:27–68,
QueueService.cpp:583–593,1301–1387, Candidate storage и retained-owner commit.
Сегодня recover закрыт localQueueComplete; Scheduler.prepare включает IO/flight.
Новый путь должен выделять ТОЛЬКО domain transition, не вызывать prepare/start/drain.

## Принятая точная область; условия реализации

1. Actual `setAuthSessionToken → recover(authRecovered)` посылает классификацию
   на существующий retained startup worker при global storage guard=false.
   Это не подтверждение account/owner, не HTTP, не claim identity и не media effect.
2. Один общий domain loop для legacy/protected: все needsAuth → retry,
   safeReason=auth_recovered; владельцы, identity, accepted ranges, attempts,
   server truth, deletion operations и purge ACK не переписываются.
   Сохраняются существующие row timestamps и stamp документа при реальной mutation;
   no-op без needsAuth не меняет timestamps/bytes/generation и не пишет файл.
3. Общий allocator-generic serializer сохраняет logical v3 writer/read-v2
   и текущие field/order/escaping semantics, без второго parser/writer/backend.
   QueueValue — immutable charged value из трёх коллекций/вложенных strings,
   НЕ native proof/authority. Native Candidate продолжает удерживать genuine input.
4. Owner.readQueueValue на worker revalidates BOTH/bootstrap/context/current gen
   под непрерывными leases; startup projection публикуется лишь через startup ACK.
   Никакого path reopen, передачи Files/commit/last native release на UI.
5. Одна active command/result и один coalesced latest-epoch intent, не backlog
   full candidates; всё scratch/copies/serialization/result/control charged
   до allocation, включая Debug proxies, в прежних64MiB/pin32/nativejob4 limits.
   Decoder/serializer/domain scans bounded-cancel; existing quotas не расширяются.
6. До startup запрос хранится как scalar epoch-intent, без выдуманных context/base.
   При dispatch ticket получает genuine context/base/target; captured epoch
   dispatched ticket неизменен, новая epoch относится к следующему intent.
   Explicit no-change outcome имеет unchanged base/target и не выдаётся за commit.
7. Worker делает один full commit private copy на том же owner; poll принимает
   физически committed generation/value и возвращает ACK. До этого опубликованная
   protected projection старая. Candidate/result/commit живут до ACK; повтор ACK
   не освобождает новый ticket. Следующая mutation только от adopted generation.
8. Stale epoch не откатывает storage adoption и не получает UI/network права.
   Обычный lost poll сохраняет completion до polling ACK; update/shutdown без UI
   после publication доводит readback и terminal physical adoption на worker.
   До publication cancellation=notCommitted/old projection; ambiguous сохраняет
   ownership/recovery-required и запрещает последующие mutations до reconciliation.
   Не менять cancel token обратно false и не переиспользовать failed writer.
9. Global storageWritable, queue_/scheduler effect consumers остаются закрытыми;
   typed recovery не сообщает saved/uploaded/deleted и не открывает Record.
   Нет bool LedgerWriter durable promise, fake READY/test authority или нового task.

## Обязательства проверки; ещё не выполнены

Actual NativeCapture caller + genuine seeded protected queue на отдельном worker:
Публичный recover(authRecovered) с empty token допустим: классификация не требует
verified account; HTTP по-прежнему требует current verified account/epoch и
consumer admission. Тест не производит auth/network или package/owner authority.
все needsAuth, смешанные statuses, owners/ranges/server fields и обе другие
коллекции, startup value ACK, one generation commit, immutable precommit view,
restart, повтор/no-op без записи, request-before-startup и coalescing epochs.
Stale/lost poll, ACK ordering, update/shutdown precommit и postpublish drain,
charged copy/serialize/result refusal/cancel/cleanup проверяются без auth network.
Existing FilesTests имеет native flush/renameCompletion/read/hash faults и
afterRename/afterRead hooks: это реальный reuse, но их доступность из actual-class
target ещё не доказана. Owner-helper fault PASS не подставлять вместо caller PASS.
Непокрытые ambiguous/postpublish callsite/control-transfer probes явно PENDING;
source-only ordering не объявлять runtime test. SOURCE approval оценивает эту
оговорку отдельно и не принимает полную failure/integration matrix молча.
Нужны final actual Release/Debug, shared grammar/serializer regressions и SDK
caller compile с exact map/EXE/readback; нынешний report не выдаёт будущие PASS.

## Analyze, ownership и сохранность

Противоречий требований C/H в этой конкретной области нет; новые product choices
не нужны. Mapping FR-012/013/014/022 → existing T116, broader T117/T118 без закрытия.
Fresh read-only #7444 OPEN: feature:200, priority:P0, area:storage,
gate:pr-blocker, type:hardening; GitHub не изменялся.
До записи162 Markdown:10 normative154 checked/0 open +152 historical отдельно.
Tasks120/93/27 SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Все6 before/after implement/analyze/checklist hooks registered1 disabled,
enabled0/dispatch0; никакие hooks/commits не исполнялись.
Main может начать RED и реализацию ТОЛЬКО принятого queue-recovery среза.
Owner/birth fault gaps из SOURCE276, full typed caller migration/finalizer/V5,
HTTP/playback/delete, H250, legacy AAC RED, installed/hardware/release остаются OPEN.
