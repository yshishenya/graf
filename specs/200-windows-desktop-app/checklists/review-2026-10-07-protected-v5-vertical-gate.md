# Round278 — REQUIREMENTS / scoped analyze: настоящий protected V5 vertical T116

**SCOPED REQUIREMENTS GO — C0/H0 для согласованной ниже конструкции.**
Это разрешение RED/реализации целого vertical, не SOURCE/runtime PASS и не T116 close.
Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty сохраняется.
Lane high-risk-product; speckit-checklist/analyze применены read-only.
Reviewer не запускал VM/tests/build/GitHub, не менял code/spec/plan/tasks/markers.

## Нормы и сохранённая идентичность

Plan1802–1993, включая новый append1893–1993 и caller correction; research2967–2987,
data-model582–595 и quickstart877–900 прочитаны полностью.
Custody §2/§4–7/§8.1, packed §5/§6/§6.0/§6.1,
spec FR-004/009–014/017/018/022, SC-003/004/005/006/008 → existing T116/#7444.
Constitution I/II/IV/VI: native lifecycle/Stop, truthful persistence/deletion,
bounded resources и независимые gates; новых product choices/schema/tasks нет.
spec SHA `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658`;
plan SHA `0ee95002da5b839a83a3074eadaeea4cc64b6e6b31ae92d3b081b981762320e7`;
research SHA `9898f2ded9ef6e85447c08eba7c99347333062bad8049ba6010cd71a4543edcb`;
data-model SHA `753fa7fec06e3e8b6cf2a084f769def7f7f73012524e6b4a102b73e0984dcc2b`;
quickstart SHA `b0c083c31bfdf6d90f749a925bc8cdddbe7afd79bce18a276af47b3fc5921b78`;
custody SHA `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a`;
packed SHA `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5`;
constitution SHA `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`.
Tasks120/93/27 SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
SOURCE277 остаётся историческим SHA `7dd5b49ed717d0c3127c00f3037d4c2b52d75d93b88e0f8f8d9c04ca494f45c5`.

## Принятая конструкция и обязательные границы

1. Existing Metadata createPackage принимает genuine shared StoreOwner,
   native session directory ID и cancellation, не caller contexts/READY/root.
   Private Files helper переиспользует State/security/retained root handles;
   exclusive CREATE_NEW private package ACL предшествует content bytes.
   BCrypt генерирует собственные package-state/canonical/object/container IDs.
   Shared private root part отделена от mutable queue authority; MF/capture
   дочерний owner не получает queue access. Borrowed-Files PackedOwner path
   проверяет actual borrowed store handle/ancestors, не пропуская guard checks.
2. Reserved native role IDs → schema2 capturing/canonical-live ref → прежний
   commitImpl borrowed state lease → BOTH semantic readback/capturing ACK →
   prepared canonical Files в SAME PackedOwner openImpl → empty packed BOTH
   heads → Tree::verify → Writer. Нет path reopen/createNew role второго раза.
   Canonical bytes лишь после capturing ACK И успешного настоящего writer open.
   Частичный birth сохраняет артефакты/ownership; sticky failure, no auto-repair,
   no replacement IDs/retry поверх существующего неполного inventory.
3. Реальный V5 получает private package ownership вместо path-only authority.
   Canonical append идёт через существующий packed ProtectedCustodyWriter;
   нет открытых canonical/WAV/AAC/manifest/recovery/temp копий или URL fallback.
   Общие dirty≤4blocks/1MiB, owned64MiB, cache2MiB, pins32/nativejobs4,
   chunks≤256KiB, cadence full256KiB и Flush/Pause/Stop tail сохраняются.
   Physical disk peak/reserve/5GB/80%/95% из custody §5 не обходятся фабрикой.
4. Dispatcher — единственный active mutator до EOS; handoff finalizer только
   после actual dispatcher completion и timeline close. Не raw UI/controller
   ownership, не новое семейство dispatcher/queue/publisher/backend.
5. Writable IStream — один charged retained state с сериализацией всей операции
   Read/Write/Seek/SetSize/Commit и cursor; direct writer access при adapter запрещён.
   MF internal workers используют ту же serialization; UI/WASAPI IO запрещён.
   ONE-worker здесь сохраняет единственное логическое владение/active mutator,
   не вводит недоказанную гарантию fixed OS thread ID для вызовов MF.
   COM mutex не держится вокруг MF вызова, способного вызвать IStream обратно;
   иначе Finalize/read/write может сам себя заблокировать.
6. Finalize → закрыть adapter access под mutex/дождаться active calls → release
   sink/byteStream/COM на native finalizer → checkpoint/readback/release worker.
   Поздний COM call видит closed без native access. Worker сохраняет state
   независимо от COM refs; concurrent call/Clone/release/cancel/error не создаёт
   несериализованного writer и не освобождает native ownership на UI.
   Typed HRESULT/fault/overflow/short-read и partial-write semantics явные;
   readonly Reader не объявляется writable. Destructor не выполняет flush/IO.
7. Canonical → WAV PCM16/16k/mono и native AAC-LC48k/mono → logical incremental
   SHA/length → exact logical v5 manifest≤64KiB последним → sealed schema2 state.
   Exact packed stamps/ref IDs/roots/extents обоих metadata slots проверяются
   независимо, не выводятся из наличия файлов или успешного encoder. Нужны
   actual committed snapshot и retained inspection: прежнее semantic body
   переиспользуется на retained leases, не через release/reopen/raw-proof API.
   Normal требует настоящей semantic/integrity проверки и duration≤100ms;
   codec EOS/header-only недостаточны. После ownership gap — full cold closure
   обоих retained snapshots/refs перед normal use, не RAM stamp или path cache.
8. Degraded использует только actual complete cleaned480-frame prefix;
   trailing partial bytes/padding/raw fallback не принимаются. Recovery/hash/
   prefix refs согласованы; row quarantined, не normal/saved/uploadable.
   Short — прежний exact frame/normal-stop/no-fault predicate, durable discard
   intent/state; до actual purge+removed ACK нет removed/раннего short-notice.
9. Existing StorageWork расширяется bounded command-kind recovery/insertion.
   Worker удерживает recordingWork, package/native result и существующий
   async finalizer handle. UI получает значения; финализация pending до sealed
   result, одного protected QueueValue insertion commit и adoption ACK.
   queue_.enqueue/bool durable fallback отсутствует в этом пути.
10. Cancel до publish сохраняет old projection/trusted artifacts; после publish
    доводит readback. Ambiguous закрывает next mutation. Stale epoch принимает
    физическое storage truth, не новую account capability/normal UI reply.
    Shutdown/update/lost poll сначала drain recording/result/adoption, потом
    worker last release; immediate stoploop/drop ownership не допускаются.
11. Internal continuation проверяет genuine held owner/capturing ACK, session,
    cancellation/current stage; он не generic bypass public Record. Global
    storageWritable=false до всех content consumers; HTTP/playback/delete не
    включаются этим gate. Generated hardware prerequisites не storage authority.
12. Caller census входит в scope, без произвольного file-count ceiling:
    удалить production V5 path constructors/PlaybackEncoder и destructor
    plaintext recovery, не оставить их dormant под false guard. Адаптируются
    NativeCapture, offline/V5/short-threshold/controller faults/ProtectedFiles,
    upload/recovery/hash и связанные custody fixtures с сохранением assertions.
    Legacy-read/migration plaintext inputs — только изолированные test-only
    generated fixtures; minimal native stream encoder/fixture reuse, не копия
    прежнего writer в новый backend. Actual vertical использует настоящий MF,
    не fake encoder. Corrupt-mdat/native-hash regression не исключается:
    genuine protected output и необходимые legacy compatibility inputs,
    semantic rejection assertions сохранены. Перенос fixture сам по себе не
    закрывает исходный legacy false-accept RED или T117/B1.

## Generated actual-class acceptance, ещё НЕ исполненная

Reuse только CaptureSessionTestPeer devices/deviceRunForTesting: НЕ begin,
session_.markReady/startRecording/acceptingBatches setter, allReady/storage injection.
Peer вызывает тот же private continuation после actual factory ACK; далее
controller.record → actual worker-ready → pollHealth → dispatcher → EOS.
≥30s определяется настоящими accepted frames; timeline/AEC/clock invariants,
bounded producer/dispatcher и 5s drain не ослабляются ради быстрого fixture.
Actual NativeCapture: birth → append → EOS/finalizer pending → sealed → queue
commit/ACK → release → cold restart. Нет helper-only замены этого RED/acceptance.
Normal, degraded/short, partial birth, limit/refusal/DPAPI/IO/HEAD failure,
MF error/seek/header rewrite, cancellation/stale epoch/update/shutdown/lost ACK,
notCommitted/ambiguous и отсутствие plaintext проверяются на generated roots.
Фиксируются MF callback/last-release thread IDs и сериализация; один успешный
Finalize не доказывает thread safety. MF/DPAPI native allocations измеряются
отдельно от owned64MiB. Release/Debug/portable/shared consumers/SDK exact maps,
actual EXE readback и SOURCE review требуются после реализации, не обещаны сейчас.
Официальные API лично сверены: [MFCreateMFByteStreamOnStream](https://learn.microsoft.com/en-us/windows/win32/api/mfidl/nf-mfidl-mfcreatemfbytestreamonstream)
оборачивает IStream; [MFCreateSinkWriterFromURL](https://learn.microsoft.com/en-us/windows/win32/api/mfreadwrite/nf-mfreadwrite-mfcreatesinkwriterfromurl)
поддерживает URL=null/writable stream с обязательным container attribute.
Это доказательство формы API, не безопасности потоков или runtime PASS.

## Scoped analyze и preservation

C0/H0 в конкретной конструкции после трёх уточнений; coverage existing T116,
новая задача не нужна. Generated hardware readiness не конфликтует с no READY:
controller сам проходит transitions, storage proof не производится test peer.
До отчёта164 Markdown; все сохраняются byte-identical. Current10 normative
checklists154 checked/0 open; historical154 отдельно, новый report0 checkboxes.
Все6 before/after implement/analyze/checklist hooks registered1 disabled,
enabled0/dispatch0. Current #7444 OPEN подтверждён main, reviewer его не менял.
Main может начать RED/реализацию только полного согласованного V5 vertical.
Это не full T116/T117/T118/T120, working-profile/H250, installed/UI-visible Record,
hardware/60min/A11y/full-suite или release GO; legacy AAC RED остаётся OPEN.
