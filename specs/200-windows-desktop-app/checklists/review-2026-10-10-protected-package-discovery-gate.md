# T116 — независимое дополнение: обнаружение защищённого пакета после перезапуска

**SCOPED REQUIREMENTS GO — C0/H0.** Принята только описанная ниже конструкция
worker-only `ProtectedCustodyStoreOwner::readPackage(directory, cancel)`.
Это уточнение существующей T116, не изменение норм/schema/задач и не SOURCE,
runtime, installed или release PASS. T116/T117/T118/T120 остаются открытыми.

## Проверенный снимок и основания

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка: `codex/200-windows-followup`; HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Рабочая копия содержит чужие незакоммиченные изменения; HEAD не описывает их bytes.
Все пути ниже относительно canonical; SHA-256 проверены перед сохранением.

| Нормативный файл / основание | SHA-256 |
| --- | --- |
| `specs/200-windows-desktop-app/spec.md` | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| `specs/200-windows-desktop-app/plan.md` | `0ee95002da5b839a83a3074eadaeea4cc64b6e6b31ae92d3b081b981762320e7` |
| `specs/200-windows-desktop-app/tasks.md` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| `specs/200-windows-desktop-app/quickstart.md` | `b0c083c31bfdf6d90f749a925bc8cdddbe7afd79bce18a276af47b3fc5921b78` |
| `specs/200-windows-desktop-app/data-model.md` | `753fa7fec06e3e8b6cf2a084f769def7f7f73012524e6b4a102b73e0984dcc2b` |
| `specs/200-windows-desktop-app/research.md` | `9898f2ded9ef6e85447c08eba7c99347333062bad8049ba6010cd71a4543edcb` |
| `specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md` | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| `specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md` | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| `.specify/memory/constitution.md` | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| `specs/200-windows-desktop-app/checklists/review-2026-10-07-protected-v5-vertical-gate.md` | `c19b90ad52bab0f127b13c1ce0702a65283805a3839218e07156195359625955` |

Принятый vertical review:69–77,93–96,110–122; plan:1875–1888,1903–1924,
1983–1993; quickstart:884–896 требуют release → cold restart и сохраняют no READY.
Local contract:44–79,156–184,186–205 задаёт native identities, BOTH/no rollback,
границы ресурсов/потоков; packed contract:209–219 требует cold full closure.
Metadata-pair gate 2026-10-06:24–39,85–98 уже требует независимо ожидаемый context.
Новых продуктовых решений или отдельной Spec Kit задачи для этого уточнения нет.

## Подтверждённый пробел и принятые инварианты

В `apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h`:18–27 нет readPackage;
Pair:273–275 требует caller context; Files.cpp:380–386 не допускает packageState.
`NativeCaptureStorageIntegrationTests.cpp`:497,618–639 сохраняет context из живой
записи и передаёт его холодному reader: обнаружение ID после restart не доказано.
Это ссылки на `apps/windows/Tests/GrafWindowsContractTests/` для последнего файла.

1. Только private Files helper: genuine shared const root, native directory
   length1..300 с прежним ASCII allowlist, cancellation. Не JSON path/root/context.
   rootLease удерживает исходные root/ancestor handles/storeId без reopen store.id;
   State.initializeSecurity и прежние проверки actual path/ACL/reparse/hardlink.
   lockDirectory package → .custody-v1 → openRole(writeExisting, discover=true).
   StoreId фиксирован от root независимо; ID из удержанного exact16B id.bin —
   nonzero и отличен от store/queue/bootstrap IDs. Никаких create/repair/RNG/ACL edits.
2. Helper устанавливает writable=false, удерживает exclusive identity и root.
   Не вызывать blockWrites до чтения: Files.cpp:780 ставит failed=true,
   readValidatedSnapshotImpl:966 отвергает failed. Existing discover:433 уже
   использует writable=false. Ни public generic discover extension, ни writer API.
3. StoreOwner проверяет текущий store/bootstrap/queue и failed/cancel состояние;
   существующие migration/history exclusions сохраняются (Metadata.cpp:1282–1337).
   Тот же shared Files передаётся Pair::readImpl с observed native context;
   no close/reopen. Reuse BOTH physical/semantic validator и strict codecs;
   каждый payload сверяется со своим index generation и ожидаемым directory.
   Metadata.cpp:923–987 уже удерживает retainedLease; нет второго parser/publisher.
4. Внешний job охватывает owner validation И discovery до native IO и до выхода.
   Проверено: ProtectedCustodyMemory.h:16–30 сейчас считает каждый успешный job
   отдельно; thread-local/coalescing nesting отсутствует. Pair::readImpl:937–940
   приобретает свой job/pin. Вложенность сохраняет эти существующие semantics,
   включая typed quota refusal; новый nesting механизм/повышение квот не разрешены.
   Owned64MiB/pins32/jobs4, charged allocations, wipe, actual-completion lifetime
   и release lease до pin сохраняются; отмена/ошибка не возвращает partial proof.
5. Результат — const metadata pair provenance, не normal/member integrity,
   account/upload/playback/delete/GC authority. Readiness остаётся false.
   После ownership gap BOTH member roots/logical hashes/manifest проверяются
   существующим inspectProtected/Reader путём отдельно; pair не заменяет closure.
   Missing/invalid slots/refs — отказ с сохранением bytes, не rollback/empty queue.

## Обязательные RED / приёмка реализации, ещё не выполнены

1. Освободить прежние capture/owners/proofs/context; worker открывает свежий store,
   readPackage только по directory → существующий inspectProtected. Проверить
   normal/degraded, exact session/hash/duration, BOTH artifacts и queue generation;
   readiness/consumer admission false. Reuse actual ≥3000-frame vertical, не helper-only.
2. Invalid name/ID size/zero/alias/context/directory, missing ID, ACL/reparse/hardlink,
   competing writer/relocation: typed отказ, inventory byte-identical. Pair переживает
   исходный owner reference, сохраняет root/identity exclusion до last worker release.
3. Потерять/повредить любой slot или referenced block, включая g1 после later state:
   no rollback/repair/new IDs/legacy fallback/normal claim; артефакты сохранены.
4. Cancel до IO/после identity lock/между slots/перед return, owner validation fault,
   allocation/pin/job refusal, включая nested pair exhaustion: no partial proof,
   нет записи/утечки handles/admission; existing counters/bounds не изменены.

## Границы независимого отчёта

Lane: read-only investigation существующего high-risk-product T116 + сохранение отчёта.
Согласованная форма получает requirements GO; будущий source review обязателен.
Reviewer не перечитывал skill instructions для main, не запускал tests/build/Windows
jobs/VM/network/GitHub и не вмешивался в native301. Единственная разрешённая запись —
этот новый reviewer-owned report через apply_patch; прежние markers/code/spec/plan/
tasks/constitution не меняются. Старые PASS и checklist counts не переутверждаются.
