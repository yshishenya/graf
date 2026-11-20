# Round450 — read-only quarantine playback gap

2026-10-16. Authoritative Feature200 / T116, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Анализ следующего среза, не
source/runtime acceptance и не закрытие T116. Reviewer не запускал VM/build/
tests/GitHub и не менял source/norms/tasks/checklists. Единственная запись —
этот reviewer-owned report. Full-app compile diagnostic ещё не квалифицирован.

## Текущий разрыв

Plan:2397–2413 намеренно отделяет B sealing от доступа к quarantine через UI.
Recovery оставляет owned-A row quarantined/capture_prepared и не создаёт queue
ticket/normal proof/HTTP. Смена current account B не даёт доступа к A.
Общий план:585 и Start-owner:2204–2233 сохраняют проверенный local playback,
immutable original owner и отдельность normal upload/unknown/no-login.

WebView2Host.cpp:1198–1228 уже показывает owned row, но :1286–1296 запрещает
canOpen для любой quarantine. NativeCapture.h:1483–1505 независимо запрещает
её при открытии и последующей проверке. Одного изменения кнопки недостаточно.
Это сохранённая граница предыдущего scope, не новая ошибка B encode.

Нижний playback path уже существует: owner fresh queue/readPackage допускает
sealedNormal или sealedDegraded (:2090–2105); executor inspectProtected
(:1510–1548) проверяет actual package/BOTH/session/content; package inspector
проверяет recovery prefix, media и AAC, сохраняет degraded integrity
(LocalRecordingPackage.cpp:648–704). ProtectedLocalRecordingPlayback::open
проверяет genuine proof/token/pair и media evidence. Decode/seek validation,
cancel/drain/delete path нужно переиспользовать, не создавать новый player.

## Минимальный следующий production slice — рекомендация, не implement GO

1. Только original-owned capture_prepared row, current verified account ровно
   того же user/workspace; exact local/session/directory/path, no alias/server/
   deletion/active-session conflict. Не разрешать всю quarantine. No-login,
   capture_owner_unknown, старые unknown и чужой owner не назначаются.
2. Existing display inspection может дать только scalar verified-playable-
   degraded значение, привязанное к adopted queue snapshot/auth epoch и
   фактическому package context/generation. Наличие duration само по себе не
   доказывает playback: prefix может быть degraded без playable outputs.
   Если UI должен заранее показывать доступность, минимально дополнить
   существующий timing/display result, не вводить отдельный registry/cache,
   publisher или новую capability. UI scalar не является native proof.
3. В current native requestProof/validation допустить только этот отдельный
   degraded-local случай. Для него owner заново читает queue/exact row и
   actual pair, требует sealedDegraded; executor делает прежнюю full semantic/
   AAC inspection и открывает тот же protected IStream player. Сохранить
   original normal branch. Нельзя просто убрать общий quarantine check из
   playbackRowCurrent: eligibility строки и actual sealed proof — разные gates.
4. На play/resume/seek остаются existing current account/document/nonce/Source,
   epoch, fresh row/deletion и retained-package validation. Changed row/delete/
   shutdown отменяют playback; actual retirement предшествует purge. Никакого
   disk reopen по UI path, plaintext export, ShellExecute, нового pool или
   передачи proof в WebView.
5. Queue/status/reason/owner/generation не меняются от local open. Send остаётся
   false, normal/Saved/uploadComplete не объявляются; local delete продолжает
   прежний intent→ACK→drain→purge путь. Duration — подтверждённый prefix; «X из Y»
   допустимо только при доказанном исходном Y, не выдуманном времени сессии.

Текущий B append явно исключает quarantine UI и ослабление playbackRowCurrent.
Перед source edit нужен короткий scoped plan/admission/cuts review этого пути;
это не новый user decision, схема, task или разрешение upload. Настоящий отчёт
не переносит прежний B GO на будущие изменения доступа.

## Минимальная будущая runtime evidence

- Genuine cold B→sealedDegraded, current B не видит/не открывает A; после
  настоящего account resolution A display подтверждён, actual muted play
  продвигает позицию, pause/seek работает. Queue/canonical/package bytes и
  original owner unchanged, HTTP0 и Send false.
- Capturing/finalizing, started/orphan/partial/bad BOTH и degraded без playable
  media не получают audio-ready; no-login/unknown/foreign остаются закрытыми.
- Реальный deletion intent или auth/document invalidation между display и
  open/seek не обходится старым scalar; actual player drain до physical purge.
- Сохранить нормальный playback regression, budgets/pins/jobs/exact idle memory;
  затем exact-source/PE/receipt evidence, отдельно от full-app compile.

## Compile evidence semantics

User сообщает штатный AEC verification PASS/Restore0 и ещё running Build.
Это не независимый terminal PASS. Если initial script выдаст EXE_ABSENT из-за
ошибочного output path, исходный receipt сохраняется как неуспешный. Отдельный
reconciliation receipt может связать actual Directory.Build.props output
apps/windows/out/x64/Release с build log/configuration/source и PE hash, но
не переписывает прежний outcome. Флаг real_network=false означает отсутствие
app HTTP, а не отсутствие NuGet/feed network. Install/launch/migration не нужны.

## Append-only — terminal compile qualification

Свежая независимая read-only проверка сохранённых scripts/receipts и полностью
декодированных UTF-16LE logs: **bounded compile GO, P1 findings0**.

- result.json terminaltrue, AEC verify0/Restore0/Build0, pre/post216, saved
  owned_processes0, elapsed238917ms (pipeline timer включает verify/restore,
  не выдаётся за чистое время compiler). Original failure EXE_ABSENT сохранён.
- app-qualification.json terminaltrue, без failure, source_count216/saved
  owned_processes0. Ссылка на original receipt по SHA
  eabb7fca910e11fbfd0de445b938f9c5b088d88278b3856f0080a2350daa778b проверена
  локально. Оба receipt используют manifest
  99b6941e0ec32c556de10b71f3e0437eaeaacfa64b5778a761a90f2992e91443;
  manifest SHA и actual current216 проверены reviewer:216/216, mismatches0.
  Dirty source связывается именно этим manifest, не одним base HEAD.
- MSBuild17.14.51, Release/x64 actual AppMain.cpp, ProtectedCustodyMetadata,
  LocalRecordingPackage, V5 и WebView2Host compile; linker/LTCG сообщает
  no usable IPDB/IOBJ и все28630 functions compiled. Это не no-op build, но
  не утверждение о hermetic clean build всей цепочки зависимостей.
- Лог завершён правильным output apps/windows/out/x64/Release/GrafWindowsApp.exe,
  совпадающим с Directory.Build.props. Отдельный script проверяет log output,
  timestamp относительно creation build.log, MZ/PE и machine8664, source216
  и SHA PE. Saved PE:9b90dc08d0776df015e421a41cc1397135f8896ee047129324d8595805bdcd73,
  bytes3264512, written2026-10-16T10:06:35.7411061Z. Guest PE/headers/time/CIM
  наблюдал script, не live VM reviewer. Host PE copy не предоставлялась.
- AEC verify — штатный -VerifyBuildArtifacts, не только печать revision:
  проверяет identity/config/architecture/source-tree и полный artifact map.
  Та же проверка есть BeforeTargets PrepareForBuild. Saved provenance SHA
  ebe9b371f9ef9ab8e78f45c607ab7a661235ad9396d4001e2079395b08aae0fe;
  inventory identity Release/x64, source846fe90a289f58b7c9303a635142aa2c7caa93e5,
  artifacts27. Проверка не bypassed.
- Журнал содержит предупреждения D9025 (/W1→/W4) и upstream C4100; claim
  warning-free/Werror cleanliness не разрешён этим receipt.

Сохранённый build.log SHA
fed87e83f398a05bba7b052cb951625b23fcbf5295733c4ad1c1711851c642b8;
app-qualification.json SHA
1b45f333f775847e23429f7a607daff48294601fc033d113a18707418141c25c.
real_networkfalse первоначального receipt трактуется только как no app HTTP;
separate qualification прямо помечает NuGet network not measured. Scripts
не выполняют install/launch/migration/audio и не являются runtime validation.
Это GO compile/link application project, не всей solution/MSIX/installer,
не new native test matrix, не installed/hardware/release/T116 closure.
code-reviewer skill применён к evidence scripts без выполнения preflight.
