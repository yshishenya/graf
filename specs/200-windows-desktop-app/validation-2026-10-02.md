# Feature 200 — validation 2026-10-02

## Раунд141 — IO совместного protected MF-пути / T114 Phase0

High-risk, только disposable generated-data research. Canonical worktree:
`codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Product code, установленный клиент,
устройства, записи пользователя, профиль/ключи/UAC/глобальные ACL и сервер
не менялись. Commit/push/PR/merge/release/issue не выполнялись.

Main полностью прочитал `checklists/review-2026-10-02-phase0-exit.md`.
Независимый audit всех буквальных компонентов T114 установил один пробел:
process IO измерялся для raw stream, но не для существующего protected MF
encode/finalize/reopen/decode/seek случая. Остальные механизмы имеют sufficient
bounded Phase0 evidence; full installed/profile-loss/power-loss/100cycles/
migration/physical SC-003 acceptance не перенесены в предварительное исследование.

Изменён только внешний ResourceProof.cpp в прежней исследовательской папке:
IO window начинается после создания собственного media directory, перед
ProtectedStream constructor. Включает encode30s generated zero PCM, native
Finalize/reset writer и ByteStream/tail Commit, validated reopen, полное decode
до EOS и два SourceReader seek10s/1s, освобождение reader. IO/elapsed фиксируются
до отдельного verifyCipherFiles. Последний проверочный обход ciphertext,
fileBytes/memory query и large-index envelope находятся вне MF IO window.
Положительные read/write deltas обязательны; это reached measurement guard,
не новый product performance threshold. Raw3 cases/indexEnvelope не изменены.

Fresh MSVC x64 `/std:c++17 /EHsc /MT /O2 /W4 /WX /utf-8` build0.
Build receipt `resource-build-result-7f016020-c389-4312-926e-4d0cc88b9a44.json`,
SHA-256 `44f13b62190a91fd2d63f95832e016bbb52a2a93ea5823515fc2d0d6265f3893`.
Wrapper сверяет6 inputs до/после и немедленно сохраняет native build exit.
Main полностью прочитал run receipt
`resource-result-a10ed438-b190-4e4c-9824-f29c2a4be2fb.json`, SHA-256
`67e1f1e593ae45d7814bdd54f962fb7eed6cf738acf62c6ba73474f1115284c5`.
Command: `prlctl exec 'Windows 11' --current-user powershell.exe -NoLogo
-NoProfile -NonInteractive -ExecutionPolicy Bypass -File …\resource-run.ps1`.
Terminal/Context/child0, stderr0, accepted=true; actual medium8192/nonadmin.
Runner сверяет9 inputs/2 fixed EXE до/после, требует по одному MF/INDEX/PROOF
и3 STREAM markers. Own Job60s/outer70s guard — прежние resource limits,
не product5s drain. Metadata length bound применяется после чтения.

| Артефакт | SHA-256 |
| --- | --- |
| ResourceProof.cpp | `106e03275206c156780177774ee4f12144dc5f387da22f4a64d114752ed6a10d` |
| ResourceProof.exe | `39325f1b509e3fe792873166343ebb51024ec0822436639127fa1305660bb81e` |
| ContextProof.exe | `52455eb60f76ad3e0f65f176c9fd761012b51380b60bdcd5f0d502c209101b91` |
| resource-build-run.ps1 | `eb4077e4be241f5de94930668fa90ab59f3321392eaab00e0e936abc9d528bd4` |
| resource-run.ps1 | `d7bd0229baa9dbfaf5566668af03da60c5bd8e290b1c1c713e9b200ac682acd2` |

MF-case: logical AAC366529B, decoded PCM2881536B, checkpoints4/rewrites2;
process read2086190B/write729376B; encode/finalize/reopen/decode/seek561718us,
Finalize+reset+Commit246767us;6 ciphertext files/728676B; process lifetime peak
commit31985664B/resident43474944B. Относительно logical AAC bytes это примерно
5.69×read/1.99×write, включая проверку индексов/references в reopen и чтение MF,
не физическая дисковая амплификация, скорость устройства или all-app SC-003.
Native DPAPI/MF internal allocations не доказаны layer-owned quota этими peaks.

Все прежние raw whole-identity/tail/disk guards прошли для1MiB+123,16MiB+123,
64MiB−123. Latest largest reopen9583851us снова подтверждает обязательный
background scan, а не разрешает foreground/readiness delay. Final tail26689us,
max Write189358us, index publication21019us — один новый run, не оптимизация
относительно round137. Большой native envelope также PASS, не semantic index;
semantic max-dimension evidence остаётся отдельными round138/140 receipts.

Определения счётчиков сверены по первичным Microsoft
[GetProcessIoCounters](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getprocessiocounters)
и [IO_COUNTERS](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-io_counters):
учёт операций процесса и переданных байтов, не прямое измерение физических
секторов диска. IO других процессов/DPAPI service не объявлен измеренным.

Свежий независимый review инструментирования/receipts и aggregate T114 exit
запрошен в append к `checklists/review-2026-10-02-phase0-exit.md`. До его
результата T114 остаётся открытым, T115 не начат. Historical round137 source/
EXE/receipt не переписаны и не считаются текущим proof; helpers hashes текущего
run записаны полностью в receipt. Fixtures retained; нет plaintext content
files, нового профиля или ослабления SC-003/5s/normal-success критериев.

### Окончательное решение round141

Независимый reviewer завершил повторную проверку source/receipts и совокупного
объёма: `checklists/review-2026-10-02-phase0-exit.md`, append от2026-10-02,
**APPROVED для буквального T114**. Основной агент лично прочитал дополнение.
Единственный measurement gap CLOSED; дополнительных bounded опытов до T115
не требуется. T114 отмечен `[X]`; T115–T118 остаются `[ ]`. Это чтение
сохранённых доказательств рецензентом, не независимый повтор запуска VM.
Общая Phase0/готовность F200, audio clock и установленная приёмка не закрыты.
Переход разрешён только к документации T115, не к продуктовому внедрению.

## Раунд142 — кандидат защищённого протокола T115

Lane: active high-risk Spec Kit storage/privacy/deletion slice, **design-only**.
Сохранено текущее clarify2026-09-30; использован speckit-plan для существующего
plan без повторного setup-plan/перезаписи истории. Review — code-reviewer,
независимый Locke. Source HEAD остаётся
`99b00a579c24b50e320465b69d9a296038bc544d`, ветка `codex/200-windows-followup`.
Физический каталог0309/detached не используется. `.specify/feature.json`
по-прежнему указывает F200/source_sha выше; никаких commit/push/PR/merge/release.

Создан кандидат `contracts/windows-protected-local-custody.md`, согласованы
data-model/quickstart §12 и plan. Отдельно заданы LE block/index envelopes,
нативная защита/контекст, bounds, DATA/ZERO, media vs authority-metadata failure,
durable ack/ambiguous error, shared cache/budget/GC/pins, async queue boundary,
MF stream/no plaintext playback, account/delete/shutdown fences, migration и
legacy reader retirement. Candidate не принят, T115 остаётся открытым.
Ни protected product classes, ни runtime migration не добавлены.

Основной агент трассировал существующие AtomicFileStore, Sha256,
V5LocalRecordingWriter/LocalRecordingPackage, queue load/persist/local deletion/
short-discard, HTTP packageTracks/uploadFile, AppMain LocalMetadataScan/open и
recovery lease/drain. Найденные whole-file hashing/plaintext paths остаются
в списке замены T116, не объявлены исправленными документацией. UI ledger
persist требует async adaptation; новый contract не объявляет существующий
synchronous API безопасным. Sentinel/authority transitions проходят review,
не «проверены» только описанием. Очищать legacy original по одной миграции
нельзя: требуется подтверждение либо действующий delete/purge intent FR-012.

Frozen first-review candidate SHA-256 (не runtime binary):

| Документ | SHA-256 |
| --- | --- |
| contract | `27a0ac77a49bed71a3183a83bfaca73d3bf23aa4169788b8d055205785554b76` |
| data-model.md | `7fb236e24be17a8f1734925394d83013c831e26ffb1dd36eef6efbf1204b540a` |
| quickstart.md | `89f39e1aa6ae9ede8899dd504c2928128a7b2bd1a0134b95b8c1745fe84a1089` |
| plan.md | `25957aafcd47eb3955d964bbbb873a94553841510cd322e4a1db0ab63ad90b10` |
| tasks.md | `0d10022ffc500dc8000d90e37cb65655c0ec2d5bf83ebe4da922a80ac04e2f19` |

Проверки документации: governance OK, bootstrap doctor/frozen OK, YAML parse
PASS, diff --check PASS. Отдельный assert только арифметики header104/index112B,
64GiB/262144positions/4198400B plain-index bound PASS; не parser/native/runtime.
Tasks118: закрыто92, открыто26; новый закрытый task только T114. Reviewer-owned
checkboxes не изменялись. После plan ещё нет общего допуска: clock unresolved,
optional agent-context hook отложен, disabled commit hooks не выполнялись.

Свежий independent design/checklist report запрошен в
`checklists/review-2026-10-02-protected-custody-design.md`; до его результата
нет T115 completion/analyze approval/taskstoissues/implementation. Старые
checklist marks не принимают расширенный encryption contract автоматически.
Mac/server/root CHANGELOG и apps/windows code не менялись в этом раунде;
пакет/установленный EXE/профиль/ключи/микрофон не затрагивались. Общий Windows
паритет не закрыт; remaining audio/UI/installed/physical gates сохраняются.

## Раунд143 — текущий master и подтверждённый navigation gap

Read-only source investigation + disposable portable diagnostic, без изменения
продукта/merge. Предыдущий goal turn был progress: T114 закрыт и подготовлен
T115 candidate, а не только ожидание. Reviewer T115 проверяется тем же live
agent handle; observation timeout не считается terminal и не перезапускает его.

`git fetch origin` завершён exit0. Текущий origin/master:
`91b59ac8ee89aad47104ab0f0ff3747a0f70cafa`, release prep2026.10.02.1.
HEAD неизменен `99b00a579c24b50e320465b69d9a296038bc544d`.
Merge base `f5cca687a06dc57ad6ccbef840a0be897eaa6336`; HEAD...master69/34 commits.
34 новых master commits не означают34 новых задач. Нет master delta в
apps/windows/constitution/agent guidance/project skills. Важные baseline updates:
F277 `e39c5f4554174451f790c1240cb07270072b69d1` (#7351),
F279 `04768db6d3bac13ea3121b1171f605aa32062c14` (#7363),
F280 `8b8c653b5159275bfd72af337cd465d6d24813fb` (#7380).
Изменения Mac/server/CSS/templates не вливались поверх dirty feature worktree.

### R143-A — четыре точных billing routes отсутствуют в Windows

Mac master DesktopCabinetRoutePolicy.isBillingRoute разрешает:
`/billing/storage/preview`, `/billing/storage/cancel-selection`,
`/billing/subscription/early-preview`, `/billing/purchases/confirm`.
Текущий Windows WebViewRoutePolicy.billingRoute этих четырёх paths не имеет.
Свежая standalone диагностика вызывает **настоящую** текущую evaluate policy,
не копию алгоритма. Все четыре same-origin запроса дали deny; обычный
`/billing/storage` allow, evil-origin и preview-extra не allow/deny соответственно.
Это подтверждение дефекта, **не PASS продукта/платёжной операции**.

Fixture вне git: `/tmp/graf-f200-master-route-audit.8xl5CX/check.cpp`;
clang++ C++17/Wall/Wextra/Wpedantic/Werror/ASan/UBSan build0/run0,
output4×MISSING_MAC_ROUTE + AUDIT_CONFIRMED mismatches4/product_acceptance=false.

| Артефакт | SHA-256 |
| --- | --- |
| check.cpp | `e713102094ccc01528f6707bc59dc14acc7e968af3034ee13b02405cf682eb1f` |
| diagnostic EXE | `6d45d4503c17ff4c37f15aed8620bb8bbfe8ff5ebb937819e47979653ab5d663` |
| current WebViewRoutePolicy.cpp | `0ef91adfc500a1fbe63a4da33727d336ce13c2146f254941c502e6ccc638442e` |

Existing T102 включает payment-navigation паритет и остаётся открытым;
новая дублирующая задача/issue не создаётся. Дальнейшее исправление должно
добавить точные пути в общий native classifier с regression/no-prefix/no-origin
расширениями; не расширять всё `/billing/*`, не повторять POST и не давать
внешним страницам bridge/cookie authority. Installed payment return остаётся
отдельной live gate; реальных списаний/учётных данных в опыте нет.

### R143-B — native Join требует актуальной F279 сверки

Лично прочитан полный master `specs/279-calendar-join-series/contracts/calendar.md`,
Mac CalendarMeetingOpener:1–195, новый EmbeddedCabinetCalendarJoinBridge и session
generation изменения. F279 задаёт свежий GET join-target по UUID, native/provider
dispatch, explicit browser recovery с повторным resolver и cancellation fences.
Windows AppMain:3635–3679 уже перепроверяет account/epoch/session и свежую
upcoming projection, затем открывает event.meetingUrl через ShellExecuteW.
Это **не** тот dedicated resolver/native opener/retry state, но сам old upcoming
API сохраняет совместимость. Не заявляем, что все calendar действия сломаны
или сервер нарушил старый контракт. Требуется отдельная сопоставительная
проверка scoped calendar/notification coverage перед окончательной приёмкой.
Mac bundle IDs не копировать в Windows; OS capabilities должны оставаться
разделёнными. В этой диагностике UI/сервер/native app поведение не запускалось.

Candidate T115 frozen bytes не менялись в round143; его review не принимает
новые master parity gaps автоматически. Полная цель Windows сохраняется,
а не сужается до protected-storage subset. Merge/commit/release не выполнены.

## Раунд 144 — исправления первого независимого T115 design review

Дата2026-10-02. Canonical branch `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Только кандидат документации;
product source, VM/devices, установленный пакет и GitHub не изменены.
Первый review `checklists/review-2026-10-02-protected-custody-design.md` —
REQUEST CHANGES; его исходные findings/история сохранены, main не менял
reviewer-owned checkbox state. T114 остаётся завершённой, T115 открыта.

Изменён contract и согласованы data-model/quickstart/plan:

- F1: нет singleton exception по generation1. Birth metadata требует g1 в
  обоих independently protected slots до ACK; lost newer slot после g2/delete
  intent приводит к recovery-required, не старому ledger. Partial birth также
  blocked без автодостройки. Media degraded fallback остаётся отдельным.
- F2: old queue .quarantine durable до rename старого имени. Cipher intent
  barrier распознаётся actual old load как запрет empty ledger в rename→sentinel
  окне; new recovery проверяет pinned context/transaction. Original exact bytes
  сохраняются; bootstrap сам по себе не считается понятным старому reader.
- F3: typed pending/committed/not_committed/ambiguous ticket с base/target
  generation и epoch. Prepare/drain/finalizer/deletion/purge continuations
  определены; results/busy/lease не освобождаются до ACK/adoption. Physical
  committed truth принимается даже при stale UI, без stale network effect.
- F4: strict bounded UTF-8 JSON для bootstrap/package-state/migration-intent,
  exact schemas/fields/types/enums/null/refs/stamp/conflict checks, в отличие
  от LE block/index wire. Logical v5/v3/v2 codecs не заменены.
- PRD free reserve min(10GB,10%capacity) явно связан с physical peak/admission;
  закрыт реестр canonical/WAV/AAC temp, manifest/recovery/queue, atomic temp,
  quarantine/sentinel и сохраняемых pre-existing legacy originals. Их наличие
  исключает full-encryption claim, не даёт auto-cleanup rights.

Frozen candidate SHA-256, переданный повторному независимому reviewer:

| Файл в `specs/200-windows-desktop-app/` | SHA-256 |
| --- | --- |
| contracts/windows-protected-local-custody.md | `ad62f9046c2e9017955559d504ab7cdd51d75e2dc668200913a6b4b0837204f3` |
| data-model.md | `486f031e819531e9168ec24a9e56d1933efda29ced85c60d81de0a877e9d9405` |
| quickstart.md | `009af8e065cd9b30838dac74ef7f64049ce8be5b57a43f42a3f7b788288e6f93` |
| plan.md | `f943598d8065e58dff7452348e4b4c0848d7d38eb5579911fafd1de749f65278` |
| tasks.md (не менялся в этом раунде) | `0d10022ffc500dc8000d90e37cb65655c0ec2d5bf83ebe4da922a80ac04e2f19` |

Документные проверки terminal exit0: `check_spec_kit_governance.py`,
`speckit-bootstrap . --doctor --frozen`, Ruby YAML parse F200,
`git diff --check`. Это **не** parser/DPAPI/product runtime PASS.
Повторное independent design/checklist review запрошено; analyze и issue sync
ещё впереди. Нет commit/push/PR/merge/release либо product-ready утверждения.

## Раунд 145 — источник нового calendar Join несовпадения с master

Read-only source audit, без browser/VM/network/device/payment запуска.
Master остаётся `91b59ac8ee89aad47104ab0f0ff3747a0f70cafa`; feature HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Candidate T115 frozen bytes
round144 не меняются, независимое review продолжается.

Лично прочитан полный master calendar-series.js Join handler:1–64 и полный
EmbeddedCabinetCalendarJoinBridge.swift:1–89, Windows injected bridge script,
WebViewBridge allowlist:179–192, NewWindowRequested:1466–1484 и reminder path.

Установленная исходниками причинная цепочка:

1. Общий F279 `[data-calendar-join]` browser handler резервирует
   `window.open('about:blank','_blank')`, затем свежий GET+CSRF POST resolver и
   переводит popup в HTTPS. Для GRAFDesktop UA отказывается от browser path,
   ожидая native capture listener.
2. Mac isolated listener перехватывает trusted click в capture phase и отправляет
   UUID/requestId в grafCalendarJoin; terminal reply снимает pending.
3. Windows injected script не обрабатывает data-calendar-join; allowlist не имеет
   Join intent. В текущем Windows source нет GRAFDesktop UserAgent marker.
4. Windows NewWindowRequested вне payment adapter всегда Handled=true и не
   создаёт generic child. Разрешённый URI навигирует main core, approved external
   открывается ShellExecute, остальные отказываются. Browser-reserved blank popup
   F279 не имеет такого child/method/session lifetime, как ожидает общий handler.

Это конкретный отсутствующий native calendar Join сценарий/несовместимость
popup handoff **по source**, не подтверждённый live симптом всех календарных
действий. Старый reminder отдельно получает fresh upcoming projection с epoch/
session checks и ShellExecute, но это не F279 dedicated resolver/native/browser
retry. Не расширять generic popup/произвольные URL/custom schemes для обхода.
Будущий scoped implementation должен выбирать fresh UUID resolver, trusted
document/session/cancellation/one-flight guards, безопасный provider dispatch и
explicit browser retry с повторным resolver, без передачи URL в page reply.

SHA-256: master calendar-series.js
`3935a6c932d956d18a0ffae5068d95c526cb6b8b2829101a2ad3af540646f8e0`;
feature WebView2Host.cpp
`39a250d6283c61773786b7f095b0d6afd3c023173310136163841c2144c0e0b3`;
feature WebViewBridge.cpp
`a76231407d58734f6f2bcdfc73757988b5fcd43e7ed427cd0bd873ebcbdbc637`.

Перед исправлением требуется покрыть новый Join gap в актуальном Spec Kit
convergence/requirements/contract/tasks/review; T102 не переименовывается в
calendar задачу (это payment), T112 не notification (это update). Не выдавать
T097 визуальную проверку за implementation task. Новая задача/issue пока не
добавлена; master не вливался, product code не менялся, готовность не объявлена.

Focused diagnostic с actual WebViewRoutePolicy.cpp + WebViewBridge.cpp,
не копией их алгоритмов: `/tmp/graf-f200-calendar-policy.ZYjPku/check.cpp`.
Native macOS clang++ C++17 Wall/Wextra/Wpedantic/Werror + ASan/UBSan,
terminal build/run exit0. Assert: about:blank denied; current Windows bridge
rejects Mac action name joinCalendarEvent даже при correct protocol/origin/nonce/
JSON; denied command не продвигает message ID. Control approved desktop route,
native_settings allowlist и request_app_update envelope проходят. Это не
предложенный Windows Join command, не WebView2 runtime/installed/UI PASS и не
доказательство browser window.open return value. Binary выводит product_acceptance=false.
Source SHA256 `c699af9d3fd4ea86d4b3b19b28497712873ba7be26f148cf88af13846fc445d9`;
EXE SHA256 `041e136eb43076e14a0afb6af5aaf9d22be5d7cde99732a258c4d0956a114490`.

## Раунд 146 — T115: первый transition и historical barrier после restart

Предыдущий goal turn — progress: authoritative candidate исправлен по F1–F4,
fresh actual policy diagnostic подтвердил calendar gap. В этом turn актуальная
ветка/HEAD повторно проверены; default detached worktree не менялся. Второй
independent review принял F1–F4 для design scope, но оставил F5/F6. Полное
дополнение reviewer-owned report прочитано; прежние notes/checkboxes сохранены.
Reviewer завершился terminal REQUEST CHANGES, не признан terminal по timeout.

F5 revised candidate: prepared intent предшествует closing bootstrap;
reserved destination/queue ID не означает empty logical queue. Prepared closing
fence валиден без готовых queue indices, но **не разрешает** обычные effects.
Fixed subject/directory routing и interruption table назначают pre-fence,
destination birth, authority-switch-before-receipt и retained singleton outcomes.
Protected mutable queue после switch берётся по current authority, не навсегда
по историческому migration copy hash/generation. v3 ranges/intents не сбрасываются.

F6 revised candidate: historical immutable birth block имеет direct validated
ref с generation1/actual version>0 и строгим native/header/schema/transaction/
source stamp match; он не открывается как current mutable index. Verified
ciphertext tombstone — явно допустимый standalone retained source. Persistent
transitive refs **обоих** metadata slots восстанавливаются до первого GC;
terminal release memory pin не удаляет old-reader tombstone. Третий индекс,
новая служба или бесконечная история generations не вводятся.

Candidate/doc companions frozen и переданы новому независимому rereview:

| Файл в `specs/200-windows-desktop-app/` | SHA-256 |
| --- | --- |
| contracts/windows-protected-local-custody.md | `48704f413e132f2b643206649a6422f6e6f6ea118cc63c86d5b675e9d4be9d54` |
| data-model.md | `c35201de8245e081bd1e0464cf2e6a1e6762a5d8362126892b17d139e34a58bf` |
| quickstart.md | `ddd1c7fbb01546a50f184872555cc2b1562deca337a5d3114b6c614005388208` |
| plan.md | `2fae246c22801ef49bff29f57873ee5e1d894b7fba1899c6b20a5b7333d74bea` |
| tasks.md (без новых отметок) | `0d10022ffc500dc8000d90e37cb65655c0ec2d5bf83ebe4da922a80ac04e2f19` |

Документные проверки снова terminal exit0: governance, frozen bootstrap doctor,
Ruby F200 YAML parse, diff check. Только docs/research, не product implementation.
T115 остаётся открытой до нового independent review/analyze; T116–T118 не начаты.
Нет нового commit/push/PR/merge/release. Windows VM `prlctl status` running;
исправленная read-only process-count команда дала0 для GRAF/PacketProbe.
Первый PowerShell Command вариант потерял quoted label в prlctl и exit1;
он не запускал probe/аудио, последующая count-only команда завершилась exit0.
Новых device capture/private recording/read/upload/cleanup в этом turn нет.

## Раунд 147 — завершённый read-only analyze и свежая переносимая полоса

Canonical branch `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Product source не менялся.
Независимый T115 review завершился APPROVED для frozen bytes round146:
`checklists/review-2026-10-02-protected-custody-design.md:431`;
25 затронутых criteria достаточны,0 неподтверждённых в design scope.
Это не product acceptance, не повторное закрытие T114 и не вся Phase0.

Текущий read-only analyze завершён и выдан пользователю:22FR+10SC связаны
с118 уникальными tasks,92 checked/26 open,32/32 requirements имеют task,
ссылок на отсутствующие task IDs нет. Coverage100% — только наличие работ,
не completion. High findings: незавершённый causal clock contract T094–T096;
новый F279 Join action без Windows requirement/contract/task coverage;
4 новых billing routes покрыты существующей T102, но actual policy их rejects.
Constitution conflicts/zero-coverage core FR не найдены; default analyze gate
нулевых unresolved HIGH не пройден. T115 отметка и T116–T118 не менялись.
`--require-spec` из generated analyze skill actual prerequisite script не
поддерживает; наличие spec проверено отдельно, supported
`--json --require-tasks --include-tasks` успешно вернул current feature.
Generated skills/governance не редактировались, analyze commit hooks disabled.

Fresh portable build из canonical `apps/windows` в
`/tmp/graf-f200-current-portable.42T77W`: CMake configure/build и CTest exit0,
32/32 PASS за18.74s; AppleClang21.0.0.21000101, Release, strict warnings.
LastTest.log SHA256
`d4802252c66137a42ef1b5c83faaff25f2e7d1ce7cbf76be6926535083736daa`.
CMakeLists SHA256
`483f1c384583fcdfa59f110f67f3aa7ae30c71acd39abb26825e1a0179402605`.
Actual tests undefine NDEBUG directly/shared test header; representative
ContractFixtures binary imports assert runtime. All32 symbols were NOT audited:
an exploratory parser produced no aggregate, no full-symbol proof claimed.
AppMain excluded from this CMake surface; WASAPI/MF/WinUI/native AEC/MSIX,
installed parity and SC-003 not accepted by these macOS tests.

## Раунд 148 — pinned native EOS support experiment, не product adapter

Phase0 T094/T095 high-risk research. Disposable outside Git:
`Documents/graf-windows-followup-200/f200-eos-support.VD8MBZ`.
MSVC x64 /O2 /W4 /WX compile/link exit0; direct EXE runtime exit0,
`EOS_SUPPORT_PASS cases=176 live_capture=false production_acceptance=false`.
No devices, real PCM, generated PCM files, network or installed changes.

Actual pin verified again through native git/Get-FileHash:
`846fe90a289f58b7c9303a635142aa2c7caa93e5`;
libcommon_audio.a
`0ccc326fec7456c1c7cb1b13f2580a35fcc959686af8ed4dbf06baad170d04fe`;
sinc_resampler.cc
`3fe2d90e190b893962084e158cd725e1d88c93bae774621c706838b181494f9c`;
header `c954888557538a56511b9cb59a34c447ac8d7783891ff6224782ffedb1b01063`.
Pinned source read directly in VM; primary source also inspected:
https://github.com/okarlsen/webrtc-audio-processing/blob/846fe90a289f58b7c9303a635142aa2c7caa93e5/webrtc/common_audio/resampler/sinc_resampler.cc

Experiment compares two finite fillers17/−73 after N real generated inputs
against generated continuation. Only exact kernel-supported centers compare
bitwise; next16 unsupported outputs are an intentionally unsafe negative,
not published audio. N17/32/33/49/63/64/65/100/128/129/1024 × request64/512 ×
ratio0.918658125/1/1.0001/0.9999 × fixed/switching gives176 cases.
Cursor mirrors per-output double add and actual first/subsequent region wraps.
At ratio1 fixed, trusted count=N−31 for N≥32, otherwise0;
N100 gives69 centers, N128 gives97. This recovers the previously unavailable
supported tail mechanically, not startup/final edge or full product EOS.
SetRatio switches every37 output samples in the switching variants.

SHA256 EosSupport.cpp
`af92fb66932be59ab26689e5e0101a98ec63ae943aa939792b7d4f7253999a66`;
build.cmd `9809371e3dbcfe69533f744b36895372a1c9ac3942e564a5fdfdaf851a6a1109`;
EosSupport.exe `e46eeb6edc5977d17bed5b089c0ff219f46b058c882d44dae17aac9697221254`.
Reproduce build.cmd then EosSupport.exe in that fixed directory.
Independent static review requested; contract/product policy not changed.

## Раунд 149 — causal constant-clock counterexample, actual ClockMapper

Own disposable `/tmp/graf-f200-causal-clock.kJ3GDf/CausalClock.cpp` compiled
with actual canonical ClockMapper.cpp, strict C++17, ASan/UBSan; build/run exit0,
`CAUSAL_FIT_COUNTEREXAMPLE_PASS cases=10 estimator_approved=false live_capture=false`.
44.1/48k × constant−100/0/+100/250ppm and one changing+100/−100/+100ppm case.
Constant cases generate nominal3600s, changing nominal60s; execution is accelerated, not
one hour of real capture. Count continuous, timestamps monotonic, no flags;
jitter400µs amplitude, anchored difference≤800µs;1ms+one-frame fit tolerance.

Fit uses only already received relative timestamps and sample counts,
intersects constant slope bounds; oracle rate is generator input only, not
estimator input. Six healthy hour cases accepted by fit and actual mapper;
two250ppm negatives rejected (fit step420, mapper ordinal421);
two variable-rate cases reject constant fit at step2755/nominal27.55s while current
mapper accepts all6001 observations. This falsifies a single constant affine
model for changing clocks; not a chosen clock estimator or VM diagnosis.
Switches are at input steps2000/4000 (nominal20/40s); trueQ integrates actual
rate so these are not exactly20/40 physical seconds. No discontinuous phase.

SHA256 source `cdd58eabe62639f169c497560860f156faa6b43d810c70c165512bada7cb9db0`;
executable `fe41e9e6f493999056736ad53ac8bee4f8002b6af642e52d7dc3216b7b925e1d`;
actual ClockMapper.cpp
`3a2e325a72542070e670c0446ad42694f0951a0f0915aec0b39af20a4d555827`.
No production clock/reset/threshold/resampler changes. T094–T096 and SC-003
remain open. No new implementation commit/push/PR/merge/release.

### Раунд 148: независимая проверка frozen mechanical source

Reviewer terminal APPROVED NARROW, read-only, собственных VM/runtime запусков
не делал. Frozen source/build/EXE SHA round148 подтверждены. Проверены actual
pinned scalar/SSE/AVX2 support32, inclusive right boundary и counts69/97;
mirror add/wrap/SetRatio согласован для положительных ratios/Resample(1).
check() не зависит от NDEBUG. Никакие файлы/checkboxes reviewer не менял.

Runtime176cases подтверждён Main, не самим reviewer. Runtime не тестирует
все scalar/SSE/AVX2 ветки раздельно или их cross-branch bit identity.
Vendor Meson -DNDEBUG: это не DCHECK-enabled internal-invariant acceptance;
R64/512 удовлетворяют constructorR>48. unsafeDiff требует хотя бы одно
различие за support, не все unsupported centers. NaN/Inf, arbitrary ratios,
Reset/Flush, threads, большие output partitions, causal uncertainty,
timeline/AEC/writer и complete EOS остаются вне этого narrow proof.
Internal finite filler явно есть; принимается только independence selected
fully observed support outputs, не «padding0» или recording-success claim.
Code review skill использован для проверки математики/границ/custody claim;
производственный §5 не менялся и T094/T095 не закрыты.

### Раунд 149: независимое завершение проверки constant fit

Reviewer terminal APPROVED NARROW: рассмотренный global constant-slope fit
с фиксированной погрешностью/первым anchor можно честно отвергнуть.
Генератор интегрирует непрерывное время, fit не видит trueppm/future samples;
текущий ClockMapper без reset принимает все6001 changing observations.
Timing20/40/27.55s — nominal/input-step. Fitstep420 и actualordinal421
обозначают одно наблюдение, не отличие времени отказа. Никаких файлов/запусков
reviewer не делал. Вывод не относится ко всем affine estimators; другой
estimator не принят, current clock contract/threshold не менялся.

## Раунд 150 — actual pinned EOS block partitions и Stop admission boundary

High-risk Phase0 research, canonical HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`, branch
`codex/200-windows-followup`; source Windows/Mac/server не изменён.
Disposable `Documents/graf-windows-followup-200/f200-eos-partitions.K0UAu2`.
Reuse frozen EosSupport.cpp af92… callback/cursor/check, renamed old main
не вызывается; native same pin/library round148, не копия resampler algorithm.
MSVC x64 /O2 /W4 /WX build exit0; runtime exit0:
`EOS_PARTITION_SUPPORT_PASS cases=384 estimator_acceptance=false production_acceptance=false live_capture=false`.

12N17/32/33/49/63/64/65/100/128/129/1024/65536 × request64/512 ×
ratio0.918658125/1/1.0001/0.9999 × fixed/switching × fixed/variable chunks.
Fixed chunk480; variable1/479/31/997/480/7/1024/211; changing ratio cuts at37
outputs. Trial cursor checks EVERY prospective support before Resample(chunk),
warm startup excluded from trusted, first unsupported center stops publication.
All selected output compares bitwise against separate native Resample(1),
finite fillers17/−73 and generated continuation; finite values required.
After closure a negative only explicitly bypasses guard for16outputs, never
increments trusted, requires some difference. At ratio1 fixed N100 gives69,
N128 gives97 for both requests/partition schedules. No devices/audio files.

Frozen SHA256:

| Артефакт | SHA-256 |
| --- | --- |
| PartitionSupport.cpp | `35a8b45ab33ca9ad41390211bb698a0417f3af40a729bcb6f5e62a46c7dd6cac` |
| build.cmd | `5be739a742bbd2a9c8bf8a7c0c858b9e998370fb7ed15af3bfdeac1c9c076e70` |
| PartitionSupport.exe | `e6f1bab9ac32410b3559f028d889f2ef823c9cb1292766e7ca016b283864f921` |
| included EosSupport.cpp | `af92fb66932be59ab26689e5e0101a98ec63ae943aa939792b7d4f7253999a66` |

Reproduce external build.cmd and PartitionSupport.exe. Independent static
review APPROVED NARROW, exact four hashes/pinned source mechanics verified,
no own runtime/devices/writes. Preflight/sample phases/negative control/chunk
bounded≤1024 accepted for tested ratios. All SIMD branches, DCHECK config,
production adapter, causal phase model, waveform integration, AEC/writer and
SC-003 remain unaccepted. No new task marks or product acceptance claim.

Actual integration source inspection (also confirmed by reviewer):
WasapiCaptureWorker.cpp378 normalizes before callback;
WindowsCaptureSessionController.cpp298 returns true on deliberately ignored
closed admission; Stop133 closes admission before putting typed EOS.
Thus callback=true is not raw-input admission receipt. A future resampler tail
must be tied to already admitted input, not delivered as post-Stop new data.
This is a future integration constraint, NOT established present Stop defect.
Read current normalizer/header/controller dispatch and FIFO before this finding.

Native worker279 GetPosition(position,nullptr) intentionally has no paired
current QPC in its ClockObservation. Disposable PacketProbe has paired QPC,
but PacketStats schema6 errors compare spans from first point, not absolute
packet/current-clock latency; primary Microsoft docs confirm distinct position
units and QPC100ns. No incorrect unit-conversion fix inferred. Additional
bounded metadata design is required before choosing an estimator/clock source;
no new device experiment in this round.

No install, settings/microphone/recordings/migration, commit/push/PR/merge/release.
after_plan context hook still deferred because full clock model/Phase0 is open;
root AGENTS unchanged. T094–T096/T115–T118 and whole F200 not closed here.

## Раунд151 — текущая связь WASAPI pairs, schema7

Source HEAD `99b00a579c24b50e320465b69d9a296038bc544d`, canonical
codex/200-windows-followup. High-risk active Spec Kit research slice T094;
production mapper/thresholds/normalizer and package unchanged. Disposable files
outside Git: Documents/graf-windows-followup-200/f200-clock-pair.LXFJPO.
Full old probe read, then mechanically cloned via apply_patch; exact source
diff changes stats type, JSON/schema and window title only. Old probe untouched.

Preparation proof: Windows native MSVCx64 C++17/O2/W4/WX build exit0;
PairStatsTests2000 generated arithmetic cases PASS, huge uint64 origins,
invalid=null, first-anchor negative and existing guard cases checked.
Same2000cases Clang ASan/UBSan PASS. SummaryTests PASS worst_bytes929.
No devices in either test. Independent read-only review APPROVED NARROW for
one bounded metadata experiment: source math, units, privacy,65/64packet cap,
5point cap, unchanged flags/exactS_OK/release/Stop, visible indicator/Stop,
5sUI+12sparent watchdog accepted. Reviewer did not build/run devices.

Frozen SHA256:

| Артефакт | SHA-256 |
| --- | --- |
| PairProbe.cpp | `9552ea6431a5cf72c7f4a34310fe22f3bfe5780cdf9dd551e8c0ad5a5cda8878` |
| PairStats.h | `c1eaae908376f58bdb44c526f77d32894b47ae2536af10c76ab2ceb808745711` |
| PairStatsTests.cpp | `dd315c80aaf21035c3fb2f1a95e376598f32651f61790c50bd244c3a6cba380e` |
| SummaryTests.cpp | `f7a9d44847adc8c0695ec25a7ac2a74e9cfb3b280393ecff743bbf82bcde6c54` |
| Run-One.ps1 | `66063a5193aac0b9f0dac8898c09e34e95b9595ef1f6dca2c16bb5a7e67cd511` |
| build.cmd | `228bea295d83352af9d4eef50cb5c88f8621d06ca717a7592f557a7984c411bf` |
| x64/PairProbe.exe | `1d6be686af31e4c6f664f152230c5aa1dc5300e66127117c6432cacc7f8113f2` |
| included PacketStats.h | `898fc1f00e385a7759fade2d0c956eca907fa68446af5ef673f48baf1637ab3a` |
| linked exact ClockMapper.cpp | `3a2e325a72542070e670c0446ad42694f0951a0f0915aec0b39af20a4d555827` |

Live proof: Parallels Windows11 running, before process count0 (PacketProbe,
PairProbe,GrafWindowsApp); Windows and Mac EXE hashes match. Exactly ONE
Run-One.ps1 invocation -Architecture x64 -ExpectedHash above; no -Mmcss,
candidate44100, settings changes or repeated trials. GUI visible before worker;
parent/own probe exit0, summary770bytes including CRLF, duration441ms after
cleanup. All41acquired packets released, failure0, Stop0, post process count0.
Opaque PCM pointer was never dereferenced/copied; no audio or recording saved.

Safe bounded JSON (absolute positions/QPC and device identity omitted):

```json
{"schema":7,"audio_read":false,"continuity_acceptance":false,"cases":[{"case":"control_mix48000_extensible","end":"metadata_guard","stage":"metadata_guard","native_hr":"0x00000000","stop_hr":"0x00000000","stream_flags":"0x00040000","sample_rate":48000,"clock_frequency":384000,"packets":41,"released_packets":41,"release_failures":0,"zero_packets":0,"discontinuity_packets":2,"timestamp_error_packets":0,"startup_discarded_frames":480,"clock_fault":"discontinuity","elapsed_through_cleanup_ms":441,"start_called":true,"first_fault_packet":41,"guard":"discontinuity","buffer_frames":4800,"mmcss":[0,0,0],"timing_us":[17797,162,false],"stats":{"packets":39,"gaps":[0,0,0],"current_pairs_100ns":[[1,100000,146458,46458],[8,100000,37205,-62795],[32,100000,420,-99580]]}}]}
```

Interpretation:39measured metadata observations have gaps0; packet41reported
post-startup DATA_DISCONTINUITY, rejected before adding a new pair point. The
three position differences are10ms; QPC differences14.6458/3.7205/0.042ms;
residuals+4.6458/−6.2795/−9.958ms. These are simultaneous pair differences,
not elapsed span errors, ppm, lost-frame counts or absolute packet PTS.
Common stream-origin assumption remains explicit. This one run did NOT
reproduce clock_drift; no fault-frame pair accepted. No root cause assigned
to VM/driver/scheduler and no current-clock replacement/causal estimator
validated. Count continuity before a flag cannot excuse the reported fault.
Start_called alone means attempted Start; actual41packets/native0/cleanup0
provide stronger limited capture-call evidence here, never audio acceptance.

No product code/install/recording/settings/migration/commit/push/PR/merge/release.
No task marks changed; T094–T096 and SC003 remain open. Full Phase0/model
selection remains open, optional after_plan context hook deferred.

Independent post-run interpretation review APPROVED NARROW: arithmetic/counts
and limits above confirmed without own devices/writes.41=1startup+39metadata+
1terminal; checkpoint count maps to acquired packets2/9/33. Residual changes
14.6038ms between first/last exported points, so a constant correction between
the two paths is not validated. Residual is NOT delivery latency, negative
physical latency, ppm or the specific cumulative error tested by mapper.
Root cause cannot be separated into API/driver/VM/buffering/query scheduling
from these three points. Main executed build/tests/live; reviewer only read.

Post-round checks: git diff --check PASS; check_spec_kit_governance.py PASS;
speckit-bootstrap --doctor --frozen PASS; F200 YAML parse PASS. Actual HEAD
unchanged; no diff in Windows/macOS/server source, AGENTS, constitution or root
CHANGELOG. Changed this round only owned research and validation appendices.

## Раунд152 — причинный диапазон времени, не готовая шкала публикации

HEAD `99b00a579c24b50e320465b69d9a296038bc544d`, ветка
codex/200-windows-followup, high-risk active Spec Kit research T094.
Существующий план/контракты/численные правила не меняются. Новая программа
вне Git: Documents/graf-windows-followup-200/f200-reachable-phase.bBWqvE,
ReachablePhase.cpp и build.cmd; создана через apply_patch.

Гипотеза: exact first anchor, instantaneous frequency±100ppm, последующие
anchor-relative observation errors≤1ms+1sourceframe. Это не действующий
cumulative guard и не подтверждённый контракт native API. По мере поступления
n/q observer распространяет диапазон времени и пересекает его с измерением;
не получает истинную rate/время/будущие метки. O(1), sticky rejection. Core
не проверяет native flags/count continuity/ReleaseBuffer, поэтому не может
сам принимать capture packets.

Проверки Main:

- Clang C++17/O2/Wall/Wextra/Werror, ASan/UBSan: build/run exit0.
- Windows MSVCx64 C++17/O2/W4/WX: build/run exit0.
- 48instantiations:2rates×6patterns×2partitions×2types; обе среды выводят
  REACHABLE_PHASE_PASS, observations18494460, midpoint_rate_max_ppm4970.21,
  nonmonotonic_midpoints0, estimator_acceptance=false,
  published_pts=false, live_capture=false.
- 40healthy instantiations проходят весь prefix, containment истинного
  времени и ширину диапазона. Восемь sustained250ppm instantiations получают
  отказ; после него дальнейшие вызовы остаются отказами. При fixed10ms первая
  отказная observation ordinal421 совпала с actual mapper на обеих rates.
- double и long double имеют53mantissa bits; не заявляются разные precision
  regimes. UINT64 origins близки к максимуму, вычитаются до преобразования.
  Отдельные проверки: invalid rate, repeated QPC, reversed n, span>2⁵²,
  delta>4800, выброс; обычные throw-проверки, не отключаемый assert.
- Истинная шкала генератора и noise остаются за границей observer. Noise
  sinusoidal±400µs. Smooth dt/dframe99ppm соответствует примерно
  −98.9902…+99.0098ppm frequency, period20source nominal seconds.
- Source positions ограничены3600nominal seconds; при variable partitions
  последняя полная first-frame position может быть раньше горизонта, а
  объявленный packet count выходить за него. Это не exact-hour/EOS proof.

Начальный неуспешный запуск стенда: проверка containment ошибочно применялась
также к заведомо out-of-prior250ppm truth до отказа observer. Исправлена только
область этой проверки; все healthy containment и negative rejection/sticky
условия сохранены. Отрицательный случай не выдаётся за допустимый source.

Frozen SHA256:

| Артефакт | SHA-256 |
| --- | --- |
| ReachablePhase.cpp | `833c16210d8d24e7e8e6060c162c15829638c4a4749467b543df30a8e690b8ce` |
| build.cmd | `205857f7a0cc5fdbd3c495567e6d991889f668bd478444850c727da85603d2f8` |
| Windows ReachablePhase.exe | `d753e2f682d441aaa846d78deef533c2727c28d812fdd3df55b846b5c6c6e73f` |
| Mac ReachablePhase-mac | `3e9fc761c079962da135521d8865999a56d649bbae97a90e0eafff6451daa004` |
| linked actual ClockMapper.cpp | `3a2e325a72542070e670c0446ad42694f0951a0f0915aec0b39af20a4d555827` |

Воспроизведение: build.cmd в Windows собирает и запускает стенд без устройств.
На Mac: c++ -std=c++17 -O2 -Wall -Wextra -Werror -fsanitize=address,undefined,
include apps/windows/RecApp/Audio, ReachablePhase.cpp вместе с actual
ClockMapper.cpp, затем запуск полученного бинарного файла. No fast-math.

Независимый read-only review APPROVED NARROW проверил свежие source hashes,
рекурсию/единицы/outward rounding, границы integer products, отсутствие oracle
в observer, exact first anchor в этом генераторе и honest scope. Устройств,
build/run и файлов reviewer не менял; runtime результаты получены Main.

Содержательный вывод: кандидат проходит меняющуюся частоту, на которой
constant affine fit round149 отвергался. Однако выбор midpoint каждого
диапазона даёт implied frequency4970.21ppm на healthy данных — он не является
готовым rate-constrained publisher. Это не доказывает невозможность иной
согласованной траектории. Полный estimator, native source assumptions,
first-anchor uncertainty, ratio/waveform, integration/start/EOS, AEC/writer
и SC003 не приняты. Текущий mapper/его fault states не изменены.

Микрофон/устройства/VM-настройки в этом раунде не использовались. Нет новых
product code/install/recordings/migration/commit/push/PR/merge/release; задачи
не закрывались. Phase0 и цель остаются открытыми; after_plan context hook
не вызывается для незавершённого плана, root AGENTS остаётся стабильным.

Завершающие проверки: git diff --check PASS, check_spec_kit_governance.py PASS,
F200 YAML parse PASS, speckit-bootstrap --doctor --frozen PASS. HEAD прежний;
нет diff apps/windows, apps/macos, apps/server, AGENTS, constitution, CHANGELOG.
В репозитории этот раунд добавляет только owned research/validation evidence.

## Раунд153 — причинный resampler: девять коротких случаев и искусственный час

HEAD `99b00a579c24b50e320465b69d9a296038bc544d`, active high-risk Phase0
research T094. Main собрал и запустил отдельный стенд без устройств в
Documents/graf-windows-followup-200/f200-causal-waveform.ggtFRM. Pinned native
source `846fe90a289f58b7c9303a635142aa2c7caa93e5` проверен на Windows.
Mirror actual ClockMapper, RecordingAudioTimeline, AudioTypes совпали с
canonical; исходники приложения не менялись.

Frozen SHA256 после завершения обоих запусков:

| Артефакт | SHA-256 |
| --- | --- |
| CausalWaveform.cpp | `22a73297156168354f4d92ee38edf7f0fa6414b786186c6eb6b34b94b7348f72` |
| build.cmd | `0ea5ece99e494a81f71c802b4d3d9d06ae9042f189dc3470bd866876b94053ca` |
| CausalWaveform.exe | `b027dda027cb31c24624e3a57060035459e050e2ab181944efdaeacc12a30b7d` |
| included ReachablePhase.cpp | `833c16210d8d24e7e8e6060c162c15829638c4a4749467b543df30a8e690b8ce` |
| actual RecordingAudioTimeline.cpp | `0f36e9fb38018f49d4dcf42ac552b72104a4036f3e11734f21668fc4e14d2781` |
| actual ClockMapper.cpp | `3a2e325a72542070e670c0446ad42694f0951a0f0915aec0b39af20a4d555827` |
| linked libcommon_audio.a | `0ccc326fec7456c1c7cb1b13f2580a35fcc959686af8ed4dbf06baad170d04fe` |

Build MSVCx64 C++17/O2/W4/WX exit0. Fresh source run без аргументов exit0,
CAUSAL_WAVEFORM_PASS cases9. Отдельный `CausalWaveform.exe --hour` process
exit0, CAUSAL_HOUR_PASS. Тихий живой process не перезапускался: проверялся
тот же terminal handle до завершения. Старые pilot/intermediate source
results не используются для guarded admission proof.

| Случай | canonical frames | phase max ms | duration error ms | fault |
| --- | ---: | ---: | ---: | --- |
| baseline | 2879520 | 0.0210957 | 9.625 | none |
| opposite fixed | 2879520 | 0.1110575 | 9.6159288 | none |
| opposite variable | 2879520 | 0.1119069 | 9.6159288 | none |
| reverse rates | 2879520 | 0.1119069 | 9.6159288 | none |
| changing rates | 2879520 | 0.1118015 | 9.6045687 | none |
| request512 | 2879520 | 0.1202522 | 9.6045687 | none |
| nominal-only negative | 2879520 | 5.9999667 | 9.6159288 | none; expected phase failure |
| fault clock | 201600 | 0.2889438 | 2.0743877 | original clockDrift |
| fault discontinuity | 15360 | 0.0206395 | 6.7905329 | original discontinuity |
| generated hour | 172799520 | 0.111917947834 | 9.62500000014 | none |

Hour additional output: system_rms_db−0.0000762229652545,
waveform_max_error0.164020359516, joint_max_error0.27000015974,
command_ppm_max500, observed172817280/158744124,
internal_eos_filler64/4, trusted_poison_equal=true,
actual_mapper=true, actual_timeline=true, real_aec=false.

Assertion boundaries: exact complete canonical prefix count, contiguous PTS,
no drift trim; bitwise equality17/−73 trusted values and finite samples;
no pre-EOS read-ahead/full callback beyond admitted prefix; guarded support
[center−16,center+15]; startup unavailable history never published; mapper
before admission, fault seals both old prefixes, wrong fault fails. Cursor
integer center is base+floor(index), not floor of rounded large sum. Ratio
controller receives only current accepted n/q, nominal rate and own state.
ReachablePhase interval is NOT controller input. Generator truth schedules
fixture arrivals and provides samples/metrics only.

Independent reviewer reread fresh full source/build after cursor fix and
returned APPROVED NARROW. Reviewed source/control/support/fault/origin
boundaries and matched canonical/mirror. No reviewer builds/devices/writes;
EXE/library/runtime evidence obtained by Main. Hour is a separate Main run,
not a nine-case result or an independently executed reviewer experiment.

Limits: identity AEC; no writer/native packet API/real hardware; single-thread
fixture; exact common q0=100s and one400µs noise law. 1s feedback horizon,
command±500ppm, phase≤1.025ms, RMS≤1dB and duration≤100ms are research
parameters, not new capture validity allowances. RMS bound system-only;
waveform/joint metrics have no bounds, so no waveform-fidelity/alignment
acceptance. All reported cases have positive EOS filler; code does not
require that for every possible case. True rate not passed to controller.
Actual production mapper still rejects observed bad VM timestamps; this
run neither fixes nor accepts live clock_drift/discontinuity. SC003,
T094–T096, native AEC, saving/upload/recovery and full parity remain open.

No mic/devices/settings/install/recordings/migration/commit/push/PR/merge/
release. No task marks, product contract or frozen custody design changed.
Phase0 remains open; optional after_plan context hook deferred, AGENTS stable.

Round153 post-checks: git diff --check PASS; check_spec_kit_governance.py PASS;
speckit-bootstrap doctor frozen PASS; F200 YAML parse PASS. HEAD unchanged.

## Раунд154 — real native AEC: отрицательное качество, не готовность приложения

HEAD `99b00a579c24b50e320465b69d9a296038bc544d`, high-risk active Phase0
T094/T096 research. Generated-only files вне Git в
Documents/graf-windows-followup-200/f200-causal-aec.0VM1Bz. Actual adapter
CPP/header совпали с canonical. Pinned libraries/source прежние; устройства,
installed app, реальные записи и production source не затрагивались.

| Артефакт | SHA-256 |
| --- | --- |
| CausalAec.cpp | `5d7996e475ce775e200c898e70b48f9bedf7abed2dd9505d0ca399131570b82e` |
| build.cmd | `0be5cbcf23bb83905e6188bacf6cb82de55b536c5b1b39458fc25fefd6e2f874` |
| CausalAec.exe | `5f7c14787d0beb02611e6587ecfd91162f4cca36a95befe06accba2b63e3df82` |
| BroadbandAec.cpp | `5a77b3e3df4986232bc74cabc2d951acb8e313aede5405ead8754587bf4571d8` |
| build-broadband.cmd | `16629599dfe554992082a35bedfc23e8ecb0d15c250ab21298a1d32e4cddcaab` |
| BroadbandAec.exe | `08434b48a8241f5e1c63312fa93afdc1bb0728496c546b5bf54f6352b81d4f0f` |
| DirectAec.cpp | `f8784119ccc1df98fe3843ec77d0f5b51d35b4a8dd74e5981388dba1ceda61f0` |
| build-direct.cmd | `b22e31eb78b4ccfacd8333af71e2df9ba907448b0ee6f6712de49b7af5228f9d` |
| DirectAec.exe | `8d5c2cbc53ef3b6f90a88ddaa4b1c9c65007779f6aae2357b8e9e229f8a55682` |
| actual GrafAEC3WebRtcAdapter.cpp | `d80afbb905f5c0ae32e599b95c377e8aa2cf5fc6745bb034edb5a40d2c12bb4f` |
| actual GrafAEC3WebRtcAdapter.h | `4a3c06cc955fc23a4d20310dbbaff0623f7c1aea3de31eecfd9882e12f0db483` |
| linked libwebrtc-audio-processing-2.a | `b96da332c4d8e5fcc7ddc4490d2a8039f22954437e1ace9b62cb1de76b959df1` |

Actual ClockMapper/timeline/Sinc lib/ReachablePhase hashes unchanged round153.
Native source pin846fe90a289f58b7c9303a635142aa2c7caa93e5. No downloaded new
dependency. Build all three fresh MSVCx64 C++17/O2/W4/WX exit0. First CausalAec
build failed vendor C4100 under WX; corrected only vendor external:I/W0,
own W4/WX unchanged, no vendor/source edits. First Direct composition failed
nested main macro; replaced only disposable file composition with frozen
Broadband core + separate driver. Failed builds are not runtime evidence.

CausalAec and BroadbandAec use guarded round153 flow, changing only generated
waveform and real native adapter instrumentation. Mic=0.65·render(t−4ms)+
2111/1777Hz near tones. Reverse-before-near, in-place output; wrapper saves
raw block before actual process, checks finite cleaned samples. Quadrature
energies997/2111Hz over full1s windows after4s warm-up; compare sum of squared
window amplitudes, not total RMS or broadband ERLE. Proposed research bounds
echo≤−10dB/near-band±1dB unchanged. Native factory ready self-check runs too.

Both runtime exit1 at first baseline; no final *_AEC_PASS banner:

| Fixture | calls/windows | echo band delta dB | near band delta dB | result |
| --- | --- | ---: | ---: | --- |
| tone/chirp through actual timeline | 5999/55 | -0.11221325018 | -0.12439826411 | failed proposed bound |
| broadband through actual timeline | 5999/55 | -2.32823687118 | -2.27094051183 | failed proposed bounds |

Baseline count2879520frames, phase max0.0210956971187ms, duration error9.625ms,
no fault/no trim, trusted17/−73 equality. System RMS tone−0.000015915dB,
broadband−0.001245369dB. Cleaned/source joint difference does not test timing
because signals now intentionally differ. Opposite/changing/identity cases
declared later in main were NOT reached. No negative AEC control PASS claimed.

Direct48k bypasses Source, mapper, resampler and timeline; frozen measuring
wrapper calls same actual native adapter. Each case6000×480samples; mic delay
4ms. Echo-only, near from start, near only after20s. At24s only metrics reset,
NOT native state;36full measured windows. First prlctl launch returned255
PrlJob_GetResult invalid argument with no output; later process check found
no DirectAec. A subsequent cmd launch completed exit0 with these results:

| Direct fixture | echo band delta dB | near band delta dB | near present |
| --- | ---: | ---: | --- |
| echo only | -0.19588369318 | -0.129653772754 | no |
| near from start | -35.6561511998 | -18.2774122179 | yes |
| near after training | -3.58946541086 | -3.43845758539 | yes |

DIRECT_AEC_DIAGNOSTIC_DONE suppression_acceptance=false live_capture=false.
Direct exit0 only confirms calls/36windows/finite values. No joint suppression+
near preservation acceptance; 2111Hz in echo-only is noise, not near voice.
It does not accept SC003/hardware, isolate root cause or prove installed app
defective. Later training case is a diagnostic, not mitigation in product.

Main read pinned render_signal_analyzer.cc: narrow-band regions mask adaptation
gains. This supports testing broadband excitation but does NOT establish
cause here. Tone near-end is not speech; broadband includes2111Hz energy,
so this metric is not pure voice gain. No real audio quality/MOS/ERLE matrix.
Original failed fixtures retained; no threshold change or raw-mic fallback.
Independent narrow review requested; result recorded separately on completion.

No task/checklist marks, contract/production changes, install/settings/mic,
recording/upload/migration or commit/push/PR/merge/release. Phase0/goal open.

Independent read-only reviewer завершил APPROVED NARROW для интерпретации
Direct diagnostic и границ этих опытов, НЕ для готовности AEC. Echo-only
не проходит echo bound и не измеряет voice preservation. Near-from-start
проходит997Hz reduction, но не2111Hz preservation; trained case не проходит
обе исследовательские границы. Наличие resampler не необходимо для negative
band results в этом семействе fixtures, но Direct также меняет timeline и
output buffer: direct output отдельный, integrated in-place. Поэтому Direct
не локализует root cause исходного integrated failure и не доказывает
механизм адаптации/double-talk. Reviewer не запускал устройства/бинарники и
не менял файлы; Main runtime evidence отдельно от review. All builds/runs
terminal, no generated experiment process pending. Fresh git diff --check,
governance checker, F200 YAML PASS; bootstrap doctor frozen PASS round153.

## Раунд155 — controlled alias/delay diagnostic и Mac reference

HEAD `99b00a579c24b50e320465b69d9a296038bc544d`, high-risk active Phase0
T094/T096. Main продолжает speckit-plan research, не переинициализирует plan.
Hooks YAML parsed: before_plan commit disabled; after_plan optional context
deferred для незавершённого плана; commit disabled. No root AGENTS changes.
Предыдущий goal turn — progress: completed hour/native negative runs изменили
следующее действие; это не unchanged wait. В этом раунде device audio нет.

Disposable Documents/graf-windows-followup-200/f200-aec-alias-delay.KwwU4L:

| Артефакт | SHA-256 |
| --- | --- |
| AliasDelay.cpp | `d2592058c4d7c67b11b2755e6eb141a64842a2d93630a178046edf188bd6adc8` |
| build.cmd | `f38a6bce1f3fc8138a8d48c8add57031fca629165452274e544fa217d8e3b310` |
| AliasDelay.exe | `e6a8696f3aac78d1441c76b4c65a6aa58972c2a2a58e6d71d70c661bace41645` |

Pinned dependencies/hashes прежние round153–154; native adapter mirror CPP
свежо cmp matched canonical. Build MSVCx64 C++17/O2/W4/WX exit0, runtime0,
AEC_ALIAS_DELAY_DONE alias_cases6 suppression_acceptance=false
live_capture=false. Один process/handle до terminal, не повторялся после
quiet output. В Main вызывается paired driver, скопированные Source/timeline
функции здесь не вызываются и не дают нового capture/count/EOS proof.

Два independent adapter получают bitwise identical raw mic/render; один
output separate, другой in-place. Wrapper raw copy before processing сохраняет
метрики для обоих. Каждый case6000calls и36full1s measurement windows24–60s;
metrics-only reset24s не сбрасывает native state. Всё2880000samples каждой
пары сравнивается bitwise, не только measurement window.

| Synthetic acoustic delay ms | near mode | 997Hz band delta dB | 2111Hz band delta dB |
| ---: | --- | ---: | ---: |
| 4 | absent | -0.19588369318 | -0.129653772754 |
| 4 | from start | -35.6561511998 | -18.2774122179 |
| 4 | after20s | -3.58946541086 | -3.43845758539 |
| 40 | absent | -37.9044520234 | -10.3481336979 |
| 40 | from start | -35.5193033087 | -21.1206431171 |
| 40 | after20s | -39.4821003769 | -15.0597067947 |

Все12output rows имеют unequal_samples0/max_output_difference0;6paired
alias checks PASS, но suppression acceptance=false. В absent cases2111Hz
band — noise, не near voice. Broadband/tones/metric limits round154 сохраняются.
Alias не объясняет эти negative fixtures; не universal alias/thread/lifecycle
proof. Изменение echo-path delay улучшает одну полосу, не подтверждает
сохранение near voice и не разрешает40ms buffer preset. Устройства/реальная
VM задержка/акустическая комната не измерены.

Primary source reads pinned API float range/alias/10ms и delay semantics;
AudioProcessingImpl only calls SetAudioBufferDelay when was_stream_delay_set.
AEC3 config use_external_delay_estimator=false; render delay reset uses default
if no external estimate. Main полностью прочитал bounded source sections,
после truncated search повторно прочитал Reset body. Это source inspection,
не runtime cause proof. Также официальный текущий API:
https://webrtc.googlesource.com/src/+/refs/heads/main/api/audio/audio_processing.h
не заменяет pinned header authority. Первая попытка open AEC3 README не
вернула source; не используется как supporting evidence.

Actual Mac references fully read: Native/GrafAEC3/Sources/GrafAEC3.cpp,
Native/GrafAEC3/upstream.lock, RecApp/Sources/Capture/RecordingEchoProcessor.swift,
Shared/Tests/RecordingAEC3QualityTests.swift. Same native pin. Mac bridge calls
set_stream_delay_ms each frame; Swift supplies0, Windows omits. Shared generation
quality uses speech-like/room fixtures and distinct near-only/double-talk bounds.
Следующий повтор переиспользует эти existing references; порт не создан,
tests не выполнены, ни source test existence, ни signal comparison не
объявлены подтверждённым Windows/Mac quality PASS.

Independent narrow review requested; completion записывается отдельно.
No production/task/checklist/contract edits, no install/mic/settings/recordings,
commit/push/PR/merge/release. Phase0/high-risk gates и goal остаются open.

Independent reviewer APPROVED NARROW проверил exact source/build SHA выше,
две independent instances, real in-place pointers, сохранение raw для метрик,
неизменность render input, finite outputs/full-run bitwise check и metrics-only
reset. Допустимый вывод только для этих6fixtures: output alias не объясняет
negative band results. 2111Hz metric относится к суммарной полосе, не isolated
near voice; агрегат36окон не принимает каждое окно/широкополосное качество.
Reviewer не запускал build/runtime и не менял файлы/устройства; numerical
runtime evidence obtained Main, Mac reference/будущий порт вне verdict.
После terminal process check сообщил0 AliasDelay/DirectAec/BroadbandAec/
CausalAec processes (missing-process query exit1, не failed native run).

Round155 checks: git diff --check PASS, check_spec_kit_governance.py PASS,
speckit-bootstrap doctor frozen PASS, F200 YAML PASS. HEAD unchanged; no
diff Windows/macOS/server source, AGENTS, constitution or root CHANGELOG.

## Раунд 156 — Mac quality reference и причинная проверка mix gain

Canonical HEAD `99b00a579c24b50e320465b69d9a296038bc544d` не изменён.
Продолжение Phase0 в high-risk-feature по `$speckit-plan`; existing plan не
перезаписан. before_plan/after_plan commit hooks disabled; optional context
hook не выполнен, поскольку полный plan ещё не завершён. Только generated
arrays: устройства, microphone, настройки, пользовательские записи, сеть,
установленный пакет, Mac/server source и production Windows не менялись.

Disposable folder: `f200-mac-aec-reference.8FiqPD` в Windows mirror. MacBridge
и GrafAEC3.h — точные копии canonical Mac native source/header, `cmp` PASS.
Actual Windows adapter/timeline подключены из проверенного mirror; исходный
timeline `cmp` canonical PASS. WebRTC pin
`846fe90a289f58b7c9303a635142aa2c7caa93e5`; libraries как round155.

| Исследовательский файл | SHA-256 |
| --- | --- |
| MacReference.cpp | 0e5ae674b9c772a00299278e37ac3b574294ef991464921e0b22cece302faa39 |
| MacReference.exe | 84ea103270eb58286b48f5d481e733e619a1139a62747f75fc3fffd9572395d0 |
| MacBridge.cpp | 43f4003d5a1b4a711ecfb123e2511230de1a85e8435b59deb85755e2e569b1c1 |
| GrafAEC3.h | 0bddd1f3644f696829c3bb392bb199e20fc282dc66fec98949050ac3d3326eb0 |
| build.cmd | 353552aed3c400995835a6da2fd294017186f6a4c24a8bd53eca8e3c1471aa24 |
| CandidateTimeline.cpp | db6b3c547b427e5b63d9fc173a301a3b4d99beaa784736ab600472a158846ef3 |
| build-candidate.cmd | 63c694e64b2e96bd07e1a50e535180627ca5afe3adb9b75939c7ec67c5c04c1c |
| CandidateReference.exe | 67bf09fb92a0dbf01dfa6bc78dc1ddd44f3307f674c47ff594d89c8b6a2ee8fa |

Fresh original frozen build83739 exit0; runtime59466 exit1. Первоначальный
build81026 superseded после добавления exact output-count guard; не evidence
актуального source. Fresh candidate build11708 exit0, единственный runtime50188
exit0; каждый handle доведён до terminal, по quiet output повтор не запускался.
MSVC x64 C++17/O2/W4/WX; vendor headers external W0, те же native libraries.

MacReference — bounded C++ port существующих Mac quality formulas. smoothed
LCG speech-like signal, voiced harmonics, одинаковые C++ arrays для двух
движков; НЕ доказаны byte identity Swift generators или MacOS runtime.
Windows actual adapter сохраняет priming; Mac actual C ABI calls delay0,
separate destination как Swift. Finite outputs и размер checked; plumbing
failure exit2, quality failures накапливаются, не скрывают остальные cases.

На каждый engine:12far-only rooms delay20/80/150/300ms×RT60.2/.5/.8,
RMS reduction≥20dB after5s; near-only after1s lag≤480,level±1dB,corr≥.98;
double-talk near introduced5s echo projection≥10dB, near projection±3dB,
no silence run>960samples; acoustic delay80→85ms reduction≥10dB after7s.
Near lag434samples — измерительная alignment, не удаление кадров из записи.
Projection floor algebra допустима для проверенных ненулевых references,
не тождество для произвольного near-zero input.

Все30core gates PASS в original и candidate, numbers неизменны. Windows
far range22.3303001829–68.9494390449dB; Mac bridge on Windows range
22.3359522746–68.9375166462dB. Near Windows:lag434,gain−.50402217525dB,
corr.999759184752; Mac bridge:lag434,gain−.504022164331,corr.999759184649.
Double-talk Windows:echo28.2501323276dB,near−1.37948028106dB,silent0;
Mac bridge:echo53.5108313335dB,near−1.48815870107dB,silent0. Drift Windows
21.1041990388dB, Mac bridge21.0536397991dB. Это выполнение gates, не
побитовая идентичность engines; прежние отрицательные tone fixtures сохранены.

Mix gate — generated8s/384000samples, real Windows timeline with native AEC,
same initial PTS0/route1/domain1, exact close/count; не resampler/clock/writer.
Reference `.5*(frame.system+frame.microphone)` использует те же очищенные
components; residual subtracts `.5*generatedFar`, threshold20dB и maxdiff≤1e−7
не менялись. Original:delta6.02059991328dB,maxdiff.324655056,clipped0,
residual−5.72882613074dB FAIL; DONE31checks/1failure. Candidate:delta0,
maxdiff0,clipped0,residual22.9561882573dB PASS; DONE31checks/0failures.
Both mac_os_runtime=false/live_capture=false/full_capture_acceptance=false.

Main traced actual Mac timeline689–691, Windows timeline191, AppMain973–1025
и весь V5LocalRecordingWriter: нет последующего уменьшения gain в writer.
Candidate `diff -u` показывает ровно один replacement: sum → .5×sum перед
сохранённым clamp. Admission/count/PTS/queue/EOS/error/native AEC прежние;
build-candidate включает candidate CPP, не canonical timeline CPP. Причинный
вывод только для bounded inputs, где clamp не срабатывает; полная эквивалентность
Mac без clamp при arbitrary over-range/nonfinite output не объявляется.

Independent source review APPROVED NARROW: reviewer лично проверил frozen
CPP/build hashes, port/metrics/engine boundaries и единственную candidate line.
Fresh EXE hash/runtime numbers получены Main и переданы reviewer, reviewer
сам runtime не запускал. Ни narrow verdict, ни31checks не разрешают product
implementation, обновление старых sum-test expectations или закрытие T094–T096,
SC003/installed/hardware gates. No commit/push/PR/merge/release/task/checklist
changes. Следующая граница — согласованный production contract и совмещение
causal resampler с этим native reference без weakening clock/quality gates.

## Раунд 157 — combined causal resampler/native AEC и контроль длины fixture

High-risk Phase0 продолжение; HEAD прежний. Только disposable generated data
в `f200-causal-mac-quality.jpePTG`, no devices/network/user content. Production
source, задачи/checklist state, plan/contracts, Mac/server, installed package
не менялись. Native pin/libraries как round156. Main прочитал весь frozen
CausalAec и ReachablePhase до создания derivative; Source admission/drain/
controller не менялся. Only generator replaces tones with borrowed Mac formulas;
новый collector сохраняет raw до in-place native process и finite cleaned output.

| Файл | SHA-256 |
| --- | --- |
| CausalMacQuality.cpp | 6eaef7e0307c23e35c3bc546e025cabdc0f79674a1e8177bac17590468d555ae |
| build.cmd | c7976bd4566bd5080b8353685c605a27a98230de3aed570f4d3124328d07fd8b |
| CausalMacQuality.exe | 901a5d77923e303ada3602d4bd7cbc27b2a35b9032c47545b3978d61a02a807d |
| DirectMacLong.cpp | c43553d7bf77a7da5233f303bbea7a04029dd5403c341db5d5fc2eb791491b28 |
| build-direct.cmd | 0b9c3f71c162c4576a86e29aafb0a1d0acf1c1a7e5a9f5812490f22377540dd4 |
| DirectMacLong.exe | 5c9eb7c53996c59a6a93c61cce88909fa74dcb5f82f4c82516fdabc8c3441ca2 |
| CausalMacWindow.cpp | 86d8584e7eef059d8b6720bb47fef0708ae3a028dd7082646a1099b7c12ffd56 |
| build-window.cmd | fa42382b40e89869ef3215a8c5a879270af06da93e9fa551d2e8ff3969ddce08 |
| CausalMacWindow.exe | c748c02e77ba6686ba58d6ba28525010273618a262f651b95a75fc17e11f5406 |

Frozen reused CausalAec.cpp5d7996e475ce775e200c898e70b48f9bedf7abed2dd9505d0ca399131570b82e,
ReachablePhase.cpp833c16210d8d24e7e8e6060c162c15829638c4a4749467b543df30a8e690b8ce;
MacReference/CandidateTimeline hashes как round156. Current actual adapter and
ClockMapper source `cmp` PASS canonical/mirror/probe. Prefix includes borrowed
MacReference helpers, но frozen old drivers не вызываются; MacBridge linked
для symbols. Only combined driver вызывает Source/timeline/candidate mix/native
adapter. Direct control не вызывает timeline, хотя build links его unused CPP.

First combined build64715 exit2, unresolved Mac C ABI symbols from included
helpers. Исправлен только build link: exact frozen MacBridge.cpp, без source/
vendor/threshold changes. Fresh build73950 exit0, captured runtime62339 exit1;
DONE13checks/4failures, остальные cases выполнены, не остановлены первым FAIL.
Direct build45473 exit0, captured runtime32928 exit1, DONE4checks/2failures.
Window build46474 exit0. First launch receipt terminal255:
`PrlJob_GetResult: Invalid argument`, no app output — НЕ native PASS/FAIL.
VM running; separate GetProcessCausalMacWindow5198 exit1/noobjects показывает
отсутствие overlap в момент проверки, но не доказывает, что первый launch
никогда не выполнялся. One captured recovery direct-EXE runtime43335 exit1,
DONE17checks/4failures; нельзя называть его первым/единственным actual исполнением.
Все полученные process handles terminal; quiet yield не вызывал повтор запуска.

Generated60s speech/room80msRT60.5 и voiced arrays; native callbacks sample
linear-interpolated wave at physical input clock time. Controller видит только
observed n/q/cursor; generator true time не передаётся ratio estimator. First
anchor exact, noise400us sine, общий epoch100s и nominal±100ppm bounds как
прежний research — не новая модель, принявшая observed VM drift. Callback poison
17/−73, complete support/contiguous PTS/count/no drift trim/finite checks прежние.
Ratio correction1s/±500ppm остаётся исследовательским, не product default.

Baseline48/44.1k nominal fixed; opposite±100ppm variable; reverse44.1/48k;
changing patterns3/4 variable. Каждый имеет far-only, near-only и double-talk
near introduced20s; DT после25s использует lag своего отдельного near-only
run. Near input/output корреляция не доказывает истинность resampler waveform;
DT projection reference — ideal generated wave по canonical PTS, не isolation
actual resampled near component. Same numeric thresholds20dB/±1dB/.98/480
и10dB/±3dB/no silence>960. Long5–60s window — дополнительная исследовательская
граница; существующий Mac test проверяет5–12s, не нормативное20dB весь60s.

| Combined case | far5–12s dB (added gate) | far5–60s dB (original research gate) | DT echo dB | DT near dB |
| --- | ---: | ---: | ---: | ---: |
| baseline | 22.280765503 PASS | 16.529752718 FAIL | 58.1946252786 | -1.57661566007 |
| opposite | 22.2842844976 PASS | 16.5222835049 FAIL | 35.9030636609 | -1.66786364782 |
| reverse | 22.2979610026 PASS | 16.5100929412 FAIL | 36.8343414999 | -1.63818197662 |
| changing | 22.2520615525 PASS | 16.4456342409 FAIL | 27.7989767253 | -1.51481530062 |

Все four near-only PASS:gain−.504050689089…−.504051389875dB,
corr.999759690624… .999759702888,lag434. Все DT PASS, no long dropout.
Все complete prefixes2879520frames, phase max.0210956971187/.111906895958/
.111906895958/.111801498452ms; duration error9.625/9.61592879809/
9.61592879809/9.6045687498ms; mix maxdiff0/no trim. Identity far negative0dB
quality FAIL ожидаемо, control gate PASS. Not full waveform/joint/hardware proof.

Direct no-resampler control uses exact same60s arrays and native engines.
Windows prefix5–12s22.4771799236 PASS, long5–60s16.6349314182 FAIL;
Mac bridge on Windows prefix22.4795298762 PASS,long16.6346209693 FAIL.
Первые12s — prefix одной continuous native60s обработки, не fresh state reset.
Это опровергает утверждение, что resampler необходим для long-result failure;
не устанавливает причину качества native engine, C ABI delay либо VM проблему.
Замена окна требует явного measurement scope, не ослабления исходного gate.

Main `diff -u` проверил derivative: только four new prefix measurements/gates,
output field/DONE label; original13 gates сохранены. Поэтому17/4 не называется
17PASS. Old tone/long negatives сохранены, MacOS runtime/Swift byte identity,
live capture/ReleaseBuffer/dispatcher/writer/finalizer/SC003 не приняты.
Independent final consolidated source review requested; completion отдельно.

Independent consolidated review завершён: APPROVED NARROW, не acceptance
реализации. Reviewer лично прочитал six frozen source/build files, сверил hashes,
unchanged Source prefix, actual adapter/mapper/MacBridge и однострочный timeline
candidate; pinned Resample/SetRatio/UpdateRegions подтверждают cursor mirror.
Build/runtime/EXE results получены Main, reviewer не запускал их. Проверены
admission-before-controller, полный support/poison equality, raw-before-in-place
AEC, collector lengths, отдельный near alignment и unchanged original13 gates.

Уточнения reviewer сохранены: prefix combined отсчитан от первого canonical
sample, сопоставим по длине, но не строго identical physical-time direct window.
Near/DT — более длинные fixtures и другие окна; DT ideal reference не изолирует
реально ресемплированную near component. Дополнительный эффект resampler не
исключён, причина временной динамики residual не установлена. Aggregate energy
ratio не показывает каждый локальный interval; prefix field0 в near/DT rows
означает not measured, не measured0dB. Прежний system-waveform RMS±1dB gate
в combined stand отсутствует: полный уровень исходных каналов не принят.
Review не выполнял VM/device/tests/writes/checkbox edits; source review approved
при сохранении всех трёх отрицательных overall experiment verdicts.

Round156–157 local checks: git diff --check PASS, governance PASS, F200 YAML
PASS; frozen bootstrap doctor PASS на текущем HEAD. tasks/contract hashes прежние,
HEAD source unchanged и no diff Windows/Mac/server/AGENTS/constitution/CHANGELOG.
No commit/push/PR/merge/release. Goal и product/high-risk gates остаются active/open.

Post-run process query вывел count0 для пяти новых research executable names;
exit1 вследствие Get-Process missing names, не native failed run. Первая попытка
array-form query завершилась PowerShell ParserError из-за quotes transport;
никакого process count/evidence она не дала, повтор исправил только read-only
query syntax. Ни один process/worker не завершался принудительно.

## Round158 — разные начала источников и дробная фаза

Source HEAD99b00a579c24b50e320465b69d9a296038bc544d; disposable stand
`/Users/yshishenya/Documents/graf-windows-followup-200/f200-origin-alignment.gDXpMs`.
Никаких product edits, device/audio чтения, записей, сети или установки.

Frozen SHA256:

| Файл | SHA256 |
|---|---|
| OriginAlignment.cpp | 6ccfa41a78018403c8bd6e02db134b4dc8bff356aeb3a6b2e1b087ce3bf8063b |
| build.cmd | dfb34f4b99ea993d51942bf14ce27ab5c0dd9dddd98300a7b6ff3414492ee04c |
| OriginAlignment.exe | 7cfa5061a34530727dc400e7f92c9c4221b7c834c4c235c75c44286710256dfd |

Build70005 terminal0: MSVCx64/O2/W4/WX, same pinned WebRTC/libs and isolated
0.5 mix timeline from round156. Run11371 terminal1, DONE16checks/4failures;
original long gates preserved, live_capture=false/full_capture_acceptance=false.

| Config | Frames | First PTS | Grid origins | Max phase ms | Duration error ms | Far5–12 dB | Far5–60 dB | System RMS dB | DT echo dB | DT near dB |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| fractional_staggered | 2879520 | 4800196 | 4800007,4800178 | 0.021096805690 | 6.054166667 | 22.2887500282 | 16.5212478018 | -0.171738965849 | 55.422678229 | -1.53629760557 |
| opposite_staggered | 2879040 | 4800835 | 4800007,4800817 | 0.111901793082 | 2.741666667 | 22.3057035916 | 16.5499892604 | -0.126296143817 | 23.4982643801 | -1.43757120024 |
| reverse_staggered | 2879040 | 4800835 | 4800817,4800007 | 0.111901793082 | 2.741666667 | 22.3110806650 | 16.5347304180 | -0.128521596822 | 24.6391634660 | -1.51351411557 |
| changing_large_device_origin | 2879520 | 4800195 | 4800178,4800007 | 0.111792739833 | 6.075000000 | 22.2541705584 | 16.4541717139 | -0.126171618813 | 22.9090211626 | -1.49536732359 |

Четыре коротких far, четыре near, четыре DT PASS; четыре long far FAIL.
20dB в5–60 — дополнительное исследовательское условие, не новый FR/SC.
Near gain−0.504048104591/−0.504048663789/−0.504049723809/−0.504048056509dB;
correlation0.999759694074/0.999759693056/0.999759703047/0.999759693786;
lag434 во всех. DT silent run0, mix maxdiff0, drift trim0, poison-independent.
Начальное исключение непересекающегося интервала не считается drift trim.

Отдельный reset_origin_negative rejected=1, exception
`original research phase or Mac mix gate failed`: expected negative assertion
PASS, не quality gate и не раздельная диагностика phase/mix. Прежний Identity
AEC negative этим запуском не повторялся и не заменён.

Reviewer APPROVED NARROW: personally read frozen source/build/pinned Sinc,
integer rounding/residue, initial unpublishable step/ratio restore/cursor,
admission/support/poison/common prefix/EOS and16/4 counter. Native runtime и
EXE hash — evidence Main, не независимый запуск reviewer. No reviewer writes.
Первая QPC в генераторе точна; near-UINT64_MAX только device origin; локальное
окно не буквально Mac physical window; DT reference не isolated native near;
full arrays не доказывают production resources/SIMD/macOS/live acceptance.

## Round159 — отдельная неопределённость первого anchor

Тот же disposable folder, portable Mac clang++C++17/O2/Wall/Wextra/Werror:

| Файл | SHA256 |
|---|---|
| AnchorModel.cpp | f529f3d0de178ee19d672ed8230e41e82825c746ad3ca3ebbc712a03f96f9318 |
| AnchorModel | 27ea964220f13343d61566b448358ada9376a6f7763f6d2cd33d793a1ba67bfd |

Build/run36261 terminal0, ANCHOR_MODEL_PASS observations12000,
independent_device_origins=true, absolute_anchor_accuracy=false,
each_absolute_1ms_equivalent=false, live_capture=false. Exact copied actual
ClockMapper matches canonical source; no native Windows API/device calls.
Два стабильных источника48k/480frames и QPC start100s/100.0008s,6000points
каждый: наблюдения не различают реальное разнесение0.8ms и постоянный bias.
Другой контрпример e0+1ms/e1−1ms: observed8ms, residual96frames>49.0384,
actual sticky clockDrift, следующая корректная метка не снимает отказ.

Independent read-only review выводит относительный guard, не bound e0.
Общая epoch и мгновенный±100ppm в прежних generated моделях — предположения,
не следствия cumulative guard. Нужны независимая sample/QPC correlation или
явные измеренные anchor/inter-source bounds с переносом неопределённости
через resampler/48k rounding. Никакие новые thresholds/checkboxes не введены.
Официальные API различают packet first-frame и current clock position;
GetFrequency номинальна. Ссылки и решение — research round159.

Source review и generated PASS не исправляют installed VM clock_drift,
не принимают живые ReleaseBuffer/dispatcher/writer/finalizer/SC003 и не закрывают
T094–T096. Goal active; product implementation high-risk gates остаются открыты.

## Round160 — schema6 не измеряет абсолютную пару часов

Main прочитал actual ClockMapper, native worker GetPosition call и полный
disposable PacketStats. Paired QPC в product worker не запрашивается (nullptr);
PacketStats checkpoints — relative spans. Никакого нового native capture нет.

Portable PairModel в том же `f200-origin-alignment.gDXpMs`, clang++C++17/O2/
Wall/Wextra/Werror, build665146 exit0, runtime eaccdc exit0:
PAIR_MODEL_PASS observations192/schema6_invariant=true/
common_bias_unobservable=true/native_clock_authority=false/live_capture=false.
Cmp product mirror ClockMapper.cpp/canonical и probe/mirror ClockMapper.h PASS.

| Файл | SHA256 |
|---|---|
| PairModel.cpp | 7695ef2604996aac2ccb719ed1191c2e86e9ed19b776c58cea6afd75c453d993 |
| PairModel | 2b727db7197c5cc9ed8866d562121fe0171234195a6e85aabd1bdfbcc01b5732 |
| PacketStats.h | 898fc1f00e385a7759fade2d0c956eca907fa68446af5ef673f48baf1637ab3a |

Три64-point ряда reference/packet bias+8000ticks/common bias+8000ticks получают
одинаковые checkpoints и accepted mapper verdicts. Только в fixture с явно
общим stream origin и точными rates projected first-frame residual0/−8000/0.
Нет доказательства absolute native anchor, bounded actual device noise,
live sample/QPC correlation либо замены packet authority. Прежние≈−10ms
clock_points не интерпретируются как измеренная абсолютная задержка.

Локальные проверки после rounds158–159: diff check PASS, governance PASS,
YAML F200/extensions PASS; frozen bootstrap doctor PASS. Frozen tasks SHA
0d10022ffc500dc8000d90e37cb65655c0ec2d5bf83ebe4da922a80ac04e2f19 и custody
contract48704f413e132f2b643206649a6422f6e6f6ea118cc63c86d5b675e9d4be9d54
не изменились. Worktree registered at canonical path/branch/HEAD99b00; ignored
pointer matches HEAD. Prereq reports correct feature paths, BRANCH field remains
environment alias200-windows-desktop-app, not actual Gitcodex/200-windows-followup.
No product/Mac/server/root AGENTS/constitution/CHANGELOG diff; no commit/push/PR/
merge/install/release. Последний docs append требует повторных focused checks.

Повтор после round160 append (91acfc): diff check/governance/YAML PASS,
tasks/custody hashes и HEAD прежние, product/root source diff пуст.

## Round161 — свежий installed inventory, текущий Mac и один clock candidate

Canonical HEAD99b00a579c24b50e320465b69d9a296038bc544d/branchcodex/200-windows-followup
сохранены. Worktree существует и зарегистрирован; detached0309 не используется.
Parallels Windows11 running, Mac разблокирован. Это повторная проверка ранее
установленного пакета, не новая сборка/установка.

Read-only Appx inventory: com.graf.desktop0.1.0.12,
com.graf.desktop_0.1.0.12_x64__jqvfym1syd7bp, Status0(Ok). Installed EXE SHA256
7C4193727F2653832DA23E10641C3ABE2686293D802AD5DD0EDDDAC9FFFF9994.
Сохранённый round128-v12 MSIX SHA256
aaa7e812605d470e6400c73f9708e25ea8c411161bbe41a5525434534c5669a1;
это не проверка public trusted signature/нового release artifact.
Перед запуском GRAF/PacketProbe процессов не было. Запуск через AppsFolder
identity дал PID7328, Respondingtrue, MainWindowTitleGRAF.

CUA наблюдала сначала loading cabinet, затем загруженный authenticated кабинет
с общими страницами и idle native capture pane. WebView2-unavailable fallback
не наблюдался. Частные названия/даты/содержание встреч и screenshots не сохранены
в репозиторий. Нет контролируемого замера времени запуска: SC-001 не принят.
Guest clicks/focus/Tab не дали подтверждённого действия; это ограничение
управления Parallels, не доказанный отказ кнопок продукта. T097 остаётся открыт:
submenu «Вид», narrow1080×620, settings и все Windows actions ещё не приняты.
Новый захват/микрофон/PacketProbe не запускались. GRAF остался idle.

Fresh /Applications/GRAF Dev.app GRAFSourceSHA:
6c47c387e92c95f87b1acb0b7a172b403ed18b2b (F283 calendar series UX), не прежний
owner-selected F277 snapshot. В новом Mac source есть разделы ближайших дат,
истории и данных календаря. Нельзя сравнить разные версии shared web и назвать
Windows идентичным. Это наблюдение не меняет нормативные артефакты F200 молча
и не разрешает merge чужой ветки/deploy.

Read-only remote master и scoped fetch подтвердили origin/master
721b5125d799ea798a4af0b3625e18d3c1109039. Fetch обновил remote-tracking ref,
не HEAD/рабочие файлы. Master включает новые F281/F280/F279/F277; текущий
dirty followup не смешивался с ними. F279 native Join source gap остаётся:
новый общий handler ожидает native interception, которого Windows ещё не имеет;
generic blank popup не является решением. Живой Join не вызывался.

Independent requirements review Bernoulli: абсолютная аппаратная калибровка
первой QPC до design не является буквальным FR-009/018, SC-003 или §5 gate.
API trust и late hardware acceptance разделены; ограничения моделей159–160
не превращаются в бесконечную предварительную проверку. §5 не изменён.
Добавлен один `contracts/windows-clock-candidate.md`, plan/research round161;
вердикта о принятии implementation пока нет. Main повторно сверил официальные
GetBuffer/GetPosition и семантику packet-first/current-clock; full plan/Phase1
и optional after_plan context hook не завершены. Auto-commit hooks disabled.

## Round162 — candidate не должен скрыть действующий timestamp-gap отказ

Generated-only disposable `f200-clock-envelope.SeaTcR/EnvelopeModel.cpp`:
clang++ C++17/O2/Wall/Wextra/Werror. Ни устройств, ни сети, ни private audio.
Actual mirror ClockMapper/AudioNormalizer/RecordingAudioTimeline cmp canonical
PASS. Timeline получает paired zeros и Identity AEC: не native AEC acceptance.

8 rates8000/16000/24000/32000/44100/48000/96000/192000 ×6000packets10ms:
48000 mapper observations PASS. Метки сначала плавно уходят на−100ppm до−4ms,
затем на50s переходят к+4ms. Обе стороны находятся внутри cumulative §5 budget,
device/count непрерывен, QPC монотонен, flags0, supplementary clock точен.
Actual old Normalizer даёт gap384frames; actual Timeline во всех8 случаях
отказывает clockDiscontinuity на packet5000 (zero-based). Ideal counter-level
candidate controller на том же шаге имеет phase error8000us/command500ppm.
Ровная новая output PTS сама по себе скрыла бы этот existing timestamp gap.

Это исполняемое отрицательное доказательство для candidate, не PASS решения
записи. Counter model не исполняет SincResampler/callback/full-support EOS,
не доказывает весь8–192kHz/variable packet envelope и аппаратную фазу.
Дополнительная проверка R_i=round(ΔQPC×48000−inputStart×48000/rate)
подтвердила совпадение R_i−R_prev с actual old Normalizer PTS gap во всех48000
наблюдениях. Перенос existing48-frame guard в candidate ещё требует независимого
review; sampled equivalence не разрешает молча заменить его другой проверкой.

| Файл | SHA256 |
|---|---|
| EnvelopeModel.cpp | a8fc9294cde001eda17c40e24ff9aecf488d16f612514c745a73ee253e7f36a5 |
| EnvelopeModel | 54984a896661e2a6d3cfd74cf032b1212210936e4a5c2a2972550ae468fdbcdc |
| ClockMapper.cpp | 3a2e325a72542070e670c0446ad42694f0951a0f0915aec0b39af20a4d555827 |
| AudioNormalizer.cpp | 09c72b620da0c54ad6aee2e429db9f9ac36cde7fe680b6f8ad9c94fcdfea94c8 |
| RecordingAudioTimeline.cpp | 0f36e9fb38018f49d4dcf42ac552b72104a4036f3e11734f21668fc4e14d2781 |

Fresh runtime33723 terminal0: ENVELOPE_MODEL_PASS observations48000,
counterexample=true/live_capture=false/sinc_verified=false. Product code,
task checkboxes, custody contract, installed bytes и numerical §5 не менялись.
Новый candidate не принят; VM clock_drift остаётся нерешённым. Нет commit/push/
PR/merge/install/release; физический x64/SC-003/auth-upload/UI acceptance открыты.

## Round163 — independent candidate review и два actual-core counterexamples

Bernoulli вернул Request Changes в узкой области, не full-plan approval:
P1 ровные output PTS скрывают действующий gap>48 отказ;
P2 R_prev на каждом raw packet не учитывает пустой normalized output;
P2 после full trim state.endPts не продвигается, adjacent R delta даёт ложный отказ.
Reviewer прочитал предыдущий EnvelopeModel source/hash, runtime не повторял;
его review не распространяется на добавленные ниже два теста автоматически.
Никаких checklist edits/approval task closure. Reviewer закрыт после результата.

В том же disposable EnvelopeModel добавлены два generated actual-core проверки:
1.192kHz,300×1920frames затем1/1; all302 mapper PASS, raw residual deltas30/30,
первый маленький выход пуст, actual emitted gap60/Timeline clockDiscontinuity.
2.48kHz,packet sizes1000/1/1, residual0/−48/+1; all3 mapper PASS,
actual Timeline принимает все, trimmedFrames1, последний actual gap2 при raw
adjacent delta49. Нет source/device/network/user audio, native Sinc/AEC нет.

Fresh clang++ C++17/O2/Wall/Wextra/Werror build/run55799 terminal0:
EMPTY_OUTPUT_COUNTEREXAMPLE_PASS mapper302/raw_delta_max30/emitted_gap60;
FULL_TRIM_COUNTEREXAMPLE_PASS mapper3/timeline_true/raw_delta49/actual_gap2/trimmed1.
Все8×6000 прежних случаев повторены,48000 PASS admission observations и
8 expected timeline refusals/candidate8000us. Всего48305 actual mapper наблюдений;
summary marker observations48000 относится только к исходной восьмерке cases.

Текущий source SHA2569efe762a8261b8c95dd24614e469771b475ff77a3686f12ecd0011d935ca2754,
EXE a078cbbc718b115c6f680cc5603a6d63235a0d0750b1b30da473c3aa997d8469.
Эта итерация заменила disposable source/EXE предыдущего round162;
исторические hashes того запуска не выдаются за hashes текущих файлов.
Main записал findings в candidate/plan/research; не выбрал второй legacy
normalizer, новую проверку аппаратной истины или implementation code.
План остаётся pending, §5/численные raw thresholds/custody/tasks не изменены.

## Round164 — направление без legacy shadow и native source-staging proof

Previous goal turn классифицирован как progress: round162/163 executable
counterexamples изменили следующий design шаг. Fresh canonical HEAD99b00/
branchcodex/200-windows-followup и docs-only dirty state подтверждены.
T097: CUA rewriteDocumentation и getApp(Parallels Desktop) получили authoritative
Mac-locked error; автоматическая разблокировка не сработала. Guest UI actions
не выполнялись. Parallels CLI: Windows11 running. User recordings/microphone,
установленный клиент, device formats/UAC/profile/keys не менялись.

Independent read-only Sartre review: exact legacy linear output boundaries
не требуются §5; conditional441/441 example не закрепляет алгоритм. Направление
one Sinc→real witnessPTS/pre-correction ranges→existing timeline допустимо,
но Request Changes для candidate: virtual check не заменяет actual trim,
центр семпла не callback read end, anchor switches нельзя скрыть sink merge,
normalizedFrameOffset должен оставаться pre-correction. Это requirements/design
review, не принятие numeric formula, конкретного layout, Phase1 или реализации.
Reviewer ничего не редактировал/не запускал и закрыт после результата.

Main изменил только candidate/plan/research: packet-containing-center anchor,
range boundary при anchor switch, origin-residue relative rounding, один
существующий timeline с actual interpolation/trim/end. Отдельный legacy
normalizer/virtual monitor не создаётся. Старые counterexamples сохранены;
historical wording о ровной входной PTS помечено как отвергнутый draft.

Disposable `f200-staging-proof.52JVk9`: Source из frozen OriginAlignment,
одна research замена variable parts997→4800 и отдельный ресурсный driver;
quality driver не вызывается, оба generator указателя возвращают artificial0.
Native pinned Sinc и actual callback/cursor проверяются двумя resamplers с
EOS poisons17/−73; IdentityStage AEC, isolated CandidateTimeline coefficient0.5,
actual frozen ClockMapper SHA3a2e325a… совпал с canonical. Native AEC quality,
Mac OS runtime, actual ReleaseBuffer/controller/UI/network не проверяются.

MSVC x64 /std:c++17/EHsc/MD/O2/W4/WX build38723 terminal0. First run39399:
STAGING_PROOF_PASS, но prlctl -Command потерял строковые кавычки marker;
PowerShell Write-Output завершился ошибкой. Этот wrapper не принят как clean run.
Повтор через сохранённый run.ps1 с проверкой source/EXE hashes:
run32246 terminal0, STAGING_PROOF_PASS cases11/peak4863/blocks2189 и NATIVE_EXIT0.
Старый native процесс был terminal до повторного запуска; probe не перезапущен
по одному timeout. Native microphone/device calls в driver отсутствуют.

Для11rates8000/8001/16000/44100/44101/47999/48000/48001/96000/191999/192000,
2s/variable packet count1…4800, paired zero sources: каждый case199 canonical
blocks; largest unread4863, drained remainder<64, no trims, actual callback
counts match NativeCursor; full-support output bitwise independent of filler.
Это input-count capacity evidence, не fixed FIFO allocation/quota proof.
Fixed Source generator не хранит физический owned FIFO, old ReachablePhase
research-only assumptions остаются в fixture. Proposed metadata tags ещё
не реализованы. Длительность и quality acceptance этим драйвером не закрываются.

| Артефакт | SHA256 |
|---|---|
| StagingProbe.cpp | c7961933dee2928cbdf4999daa4d5ced3a396649d48e022ea42aa7ce18c2ddcd |
| StagingProbe.exe | 74054255ee6d7ade0ebb418de21fdf33aa3e1e3bd56dd175ee8bcabb872b4cfa |
| build.cmd | e7ebf9c9d40088d5d465ca97d636be84e53459546e39d86e3d2e50f87c0cc3b4 |
| run.ps1 | 7d3381d89907630dd021c6af4f29c3469097fc2c9f2d70ce82d29e639ac9e808 |

Portable WitnessRounding clang++C++17/O2/Wall/Wextra/Werror build/run12964 exit0.
625 first-QPC residues/two epochs(0,UINT64MAX−1e9)/11rates/output indices128…1023/
three anchor partitions and double/long double:73920000 assertions PASS;
naive absolute floating negative control35620594 несовпадений. Macro inspection
подтвердила DBL/LDBL mantissa53 для обоих host types: не extended precision proof.
Source SHA03434f06f5c69795657902bcaa0a9086810b6cf736d6f6011e8d492fda3f20e9;
EXE6c635c7bc86505ff87b88dce6960b797e56ea0568b7c310ac2208d0f0ae9024d.
Это candidate formula на nominal source centers; native accumulated phase,
waveform partition invariance, dynamic ratio/anchor tag bounds/new witness
pipeline на actual Timeline не приняты. Текущий VM raw clock_drift не исправлен.

Нет product/Mac/server/constitution/root AGENTS/CHANGELOG edit, commit/push/PR/
merge/install/release, task checkbox changes. Полный Spec Kit plan не завершён,
after_plan optional context hook не выполняется; auto-commit disabled.

## Rounds165–166 — integrated witness, terminal fix и ненулевое качество

Canonical worktree/branch/HEAD повторно проверены:
`200-windows-followup/crisp`, `codex/200-windows-followup`,
`99b00a579c24b50e320465b69d9a296038bc544d`.
High-risk active Spec Kit Phase0; disposable generated-data probes не открывают
устройства, не читают записи пользователя и не изменяют установленный пакет.
Plan stage не завершён. Root AGENTS/constitution/CHANGELOG/product code не меняются.

### Round165: полная admission/witness/timeline цепочка

Disposable folder: `f200-witness-chain.kgDXSB` в Windows mirror.
`WitnessProbe.cpp` повторно использует frozen staging Source, но raw admission
теперь только actual ClockMapper: дополнительный ReachablePhase.observe не
вызывается. Metadata ring160 хранит accepted packet start/end/q; anchors
выбираются по floor(source center), выход разделяется при смене опоры.
Relative witnessPTS учитывает first-QPC integer residue. Pre-correction offset
продолжается даже при full trim; actual RecordingAudioTimeline исправляет
данные и отвергает oversized gap. Native Sinc двух poison17/−73 сравнивается
побитно только на full-support trusted выходе; zero waveform/IdentityStage
не являются AEC quality proof. Isolated timeline coefficient0.5, product сумма
не исправлена; actual frozen ClockMapper совпадает с canonical source.

Первый native build97762/run82995 terminal0:13healthy/6expected-fault.
Independent Linnaeus review нашёл P2: flush failure мог оставить реальный Sinc
продвинутым при старом mirrored cursor, а повторный Source call это не запрещал.
Исправлено terminal guard до admission и drain mutation; rewind не выполняется.
Оба Source сначала наблюдают failed timeline; затем два late admit/drain rounds
сохраняют accepted/supplied/outputs/offset/cursor/anchor state и не выдают frames.
Это запрет после замеченного terminal state, не немедленная cross-thread fence.
Reviewer повторно узко принял исправление по source reading, не VM/full plan.

Повторный MSVC x64 /std:c++17/EHsc/MD/O2/W4/WX build31290 terminal0;
hash-guarded run11705 terminal0, NATIVE_EXIT0:

- 11rates8000/8001/16000/44100/44101/47999/48000/48001/96000/191999/192000,
  variable parts1/479/31/4800/480/7/1024/211,2s:199 canonical blocks каждый.
  Measured tag peak3; paired-source trims118/118…455/455.
- All-one input stress8k и192k:199blocks, tags81/84, trims457/457 и462/462.
  Ring160 не исчерпан в этих cases, универсальный production bound не доказан.
- Six rates8k/16k/44.1k/48k/96k/192k: cumulative raw mapper остаётся healthy
  при jitter ramp−4ms→+4ms после50s, actual timeline clockDiscontinuity.
  Trusted blocks5007/4999/5003/5006/5001/4999; packet-start boundary не является
  доказательством точной физической остановки ровно в50s.
  Во всех случаях late_calls_fenced=true.

Итого WITNESS_CHAIN_PASS healthy13 negative6, live_capture=false,
quality_acceptance=false. Не waveform/partition invariance, не controller Stop,
ReleaseBuffer, sink/finalizer либо аппаратная матрица.

### Round166: качество, контроль шума меток и отключение controller

`QualityProbe.cpp` включает frozen current Witness Source через
WITNESS_LIBRARY_ONLY и реально вызывает native GrafAEC3WebRtcAdapter.
Generated speech seed0x12345678, room delay80ms/RT60.5, voice fixture;
nominal physical rates48000/44100, own fractional QPC1375/37123 ticks и
device origins12345/987654. Duration12s, variable input1…4800, callback64.
Двойная речь включена с5s; near-only и far-only отдельны. Metrics используют
существующие Mac helpers и прежние20dB far,10dB DT,1dB/corr.98/lag480 near,
3dB DT voice и отсутствие>20ms silence. Весь полученный common full-block
выход собран; far/DT measurement после5s, near moments после1s.
1199blocks не доказывают полный математический common-prefix count.

First Quality build28119 terminal2: nested main macro C4005/C2084; runnable
EXE тогда отсутствовал. Изолированный guard исправил include, build13149
terminal0. First launch observation terminal255/PrlJob_GetResult invalid argument
не принят как native result. Перед повтором process query11029 terminal0
подтвердил QUALITY_PROCESS_MISSING/WITNESS_PROCESS_MISSING; запуск не дублирован
по timeout. Hash-guarded rerun5562 terminal1, NATIVE_EXIT1, quality2/3FAIL.

Control derivative `WitnessControl.cpp` добавляет только generated metadata
noise toggle; waveform, origins, raw mapper, timeline и AEC не заменяются.
Build48162 terminal0/run94440 terminal1. Два triplets различаются только
sinusoidal metadata noise0 versus0.4ms. Ratio controller включён в обоих.
Wrapper control-run не имел runtime hash guard: source/EXE hashes проверены
до и после; файлы во время run не менялись. Это слабее guarded receipt, не CI.

Attribution derivative меняет только controller flag и labels. Build77475
terminal0; hash-guarded attribution run58758 terminal1, NATIVE_EXIT1.
Последовательные native runs, shared object files не собирались параллельно.

| Метки / controller | Far reduction | Near gain / corr / lag | DT echo / voice | Trim render/mic | Качество |
|---|---|---|---|---|---|
| точные / on |22.4148187457dB|−.504040754033dB / .999759713537 /434|28.4250562505dB /−1.3933609926dB|0/0|3/3PASS|
| шум0.4ms / on |.945745038378dB|−.504024207134dB / .999706311029 /434|9.82036050688dB /−2.72890366716dB|1876/1731|1/3PASS|
| точные / off |22.4141035667dB|−.504040770098dB / .999759713442 /434|27.7070931415dB /−1.40883637769dB|0/0|3/3PASS|
| шум0.4ms / off |.946010963496dB|−.504024364991dB / .999706741083 /434|9.74786014593dB /−2.74535886815dB|1802/1675|1/3PASS|

Каждый case1199blocks, firstPTS4800196, dropout=false; attribution noise/on
повторил frozen baseline численно. Admission не ослаблен, actual mapper PASS.
Физический generated звук nominal; меняются только служебные метки.
Следовательно, SetRatio feedback не необходим для регрессии; direct QPC
batch boundaries + existing timeline corrector достаточны для её получения.
Отдельно trim/interpolation/phase не изолированы. Это не доказательство
неисправности native AEC3 или причины живого VM clock_drift.

Concrete round164 publication algorithm отвергнут, не готов к внедрению.
Safety zero PASS не заменяет качество. Unchanged thresholds, прежние четыре
long-far FAIL, raw VM отказ и hardware/installed gates сохранены.

### Frozen fingerprints

| Артефакт | SHA256 |
|---|---|
| WitnessProbe.cpp |5bee360de03e167b5e41857771f7d31fc67175224b8b63cb740775a97c86099e|
| WitnessProbe.exe |40ac385a2c596ded430040799c7f34f4b18195c3e797eb1ffa4909b1154b7652|
| run.ps1 |22a2dc5b62b0aad93b6fceaac7e34ff08f33959d508c064dc937f749113985c3|
| QualityProbe.cpp |1588889a3fff603b1fab4072e6f4725b3d8141e9425c52cde3c7df5a60ce5517|
| QualityProbe.exe |42ad3c3624561eff498f8b377a4286b3541acabd46c1052f49ba268ec1375d40|
| quality-run.ps1 |35231ca37dea49abeebd16f13a450dcfa624d146d40c06a0e0f10eabad503725|
| WitnessControl.cpp |00c4bd419ca2605c1cd74d474143f003044d25503f78dc1a167a7f973385c189|
| QualityControl.cpp |493753a2edb82d3d767bc138dfddabbd633df5f1581a8c85164b03c41b64cb84|
| QualityControl.exe |67b7a3954d1cadfaf7d9ba118f6eb876df7023f732e5aaaa20f7e991a4dfd0c8|
| control-build.cmd |59398e9865b5e4213852799e41dcf2e4480efa2a780fb32250056df2f3607dcf|
| control-run.ps1 |6e10c978b6656ebe075b4265c60716555d65ef7f3fde90fe9d37fff40172e0cb|
| QualityAttribution.cpp |050409d481da5670ba3a0937499da70d43ccb7f20336c4d48108650ea1905726|
| QualityAttribution.exe |b8fbd36be642c771b11426ff4419cf9bfc08d0b9991d26c5db5167087caf2fd7|
| attribution-build.cmd |edefbf7d924beefc2419422bb657b13c1b081814a4247d260ddc4057935f7a65|
| attribution-run.ps1 |63394c99135b802bcc0faacbfead83f8c6f579343dac73a4e880cde815354237|

Tasks SHA0d10022f… и protected-custody SHA48704f41… сохранились; tasks/checkboxes
не изменены этим раундом. Нет commit/push/PR/merge/install/release или изменений
Mac/server/product/constitution/root AGENTS/CHANGELOG. Independent Darwin
quality interpretation review узко Approved по source reading и переданным
результатам: нет обнаруженного generator/collector дефекта, опровергающего
far-end вывод. Reviewer не запускал Windows и не принимает product/plan.
Отмечены обязательные ограничения:

- controlRatio=false отключает динамическую обратную связь, не все вызовы
  SetRatio: initial phase/nominal ratio остаются;
- far RMS использует actual pre/post-AEC microphone, не идеальный echoReference;
- DT projection использует идеальные physical-time references, поэтому её FAIL
  относится ко всей цепочке и не является чистым измерением остаточного эха AEC;
- near PASS сравнивает данные уже после временных исправлений, не доказывает
  сохранение исходного голоса до trim/interpolation.

Этот review не приписывается раннему узкому terminal-guard review; оба агента
закрыты после получения результатов. Следующее исследование должно сохранить
данные ограничения и не объявить estimator выбранным по этой атрибуции.

## Round167 — фазовая модель, input bound и unchanged native quality gates

Canonical branch/HEAD остаются `codex/200-windows-followup` /
`99b00a579c24b50e320465b69d9a296038bc544d`. Lane: high-risk active Spec Kit
Phase0 research. Source-only variants ниже disposable, generated-only:
не читают пользовательские записи, не открывают устройства и не заменяют
производственный ClockMapper либо установленный MSIX.

### Отличие новой модели от отвергнутого round164

`PhaseSource.cpp` происходит из frozen WitnessControl, но публикация теперь
gridOrigin+generatedOutputIndex после actual Sinc, не packet-center witnessPTS.
Own first QPC/residue остаются. Packet metadata проверяет actual raw mapper,
затем innovation=(observedOffset−consumedOffset)*48000/rate, где observedOffset
получен из received QPC и accepted input start; consumedOffset — actual mirrored
Sinc cursor−initialPhase−nominalRatio*outputs. Nonfinite или abs>48 — отдельный
terminal Source отказ. Otherwise candidate horizon1s/±500ppm меняет actual
Sinc ratio. Real timeline получает непрерывные samples без jitter-driven trim.
Это не тот же алгоритм round164 и НЕ согласованная замена нормативного §5.
Raw budget/flags/device continuity/frequency/clock remain unchanged.

Проверены первичные Microsoft GetBuffer и pinned WebRTC CoreAudioInput;
последний использует QPC для periodic latency, payload — FineAudioBuffer.
Warning-only flags/restart либо callback-time timestamps OBS не перенесены.
Источники с точными ревизиями/различиями — research round167, стороннего
копирования кода или новой зависимости нет.

Первый phase build tool вернул255/PrlJob_GetResult Invalid argument, без
результата компиляции. Он не принят как build failure/success и не повторён
сразу. Status query сначала увидел cl5528; уточняющий запрос35910 terminal0
подтвердил доступную command line, OWNED_PHASE_COMPILER=False и
PHASE_BUILD_SHELLS0. Другой compiler не остановлен; PhaseQuality EXE отсутствовал.
Fresh explicit file-wrapper build76241 terminal0/BUILD_EXIT0.

Hash-guarded quality run84063 terminal0/NATIVE_EXIT0: nominal rates,
48000/44100, jitter0.4ms,12s, variable input, own fractional origins:
far21.8608957803dB PASS20, near−.504046690163dB/corr.999759732931/lag434 PASS,
DT28.908079522dB/voice−1.39746633339dB/no dropout PASS;1199blocks, trim0/0,
max innovation23.23218522/26.6598988237.

Separate PhaseNegative build58298 terminal0/BUILD_EXIT0; run13461 terminal0,
13 zero healthy cases/6 expected8ms faults PASS. Это первая, ещё unbounded
Source версия; её результаты не скрывают замечание следующего review.

### Независимый P1/P2 review и bounded derivative

Hubble read-only review Source253e27c0…: Request Changes.
P1:94admit без drain допускают83161 input/94anchors; последняя команда
−386.8ppm может примениться к10.4s очереди. Arithmetic native-cursor replay
даёт−4.02165ms на последнем trusted center без нового innovation check.
Reviewer не запускал VM/Sinc: это source arithmetic counterexample.
P2: сохранённый old witnessCase ждёт TimelineFault, а phaseRejected не меняет
timeline health; frozen старый driver тогда ушёл бы в bounded-loop failure.
Новый PhaseNegative распознаёт phaseRejected явно; old driver не выполнялся.

`PhaseBoundSource.cpp`: before metadata/mapper/tag mutation admission требует
обоим callbacks supplied<=accepted и accepted−supplied<64. Otherwise
stagingRejected/witnessRejected становятся terminal, count sealed ataccepted.
Packet<=4800 даёт observed unread<=4863 после одного следующего приёма.
Это enforced input-count/order bound, не real owned FIFO allocator quota.
Последняя команда больше не применяется к произвольной многопакетной очереди.
242 строки obsolete CollectedFrames/combined/quality/staging/witness drivers
удалены из этого derivative; original frozen files сохранены для evidence.

Reviewer узко Approved повторно по Sourcef2ad6792…: P1 bound иP2 old driver
исправлены. Full contract, hardware, native quality execution независимо
reviewer не принимал. Final negative runtime ниже выполнен основным агентом
после этого source review; он не приписывается reviewer как независимый запуск.

### Повторные native проверки bounded версии

MSVC x64 /std:c++17/EHsc/MD/O2/W4/WX, same pinned WebRTC/native adapter,
actual frozen ClockMapper, isolated CandidateTimeline coefficient0.5.
Build62559 quality terminal0/BUILD_EXIT0; quality39136 terminal0/NATIVE_EXIT0.
Build60362 negative terminal0/BUILD_EXIT0; negative74904 terminal0/NATIVE_EXIT0.
Builds последовательны, одна native quality run совпала по времени с negative
compilation; CPU/wall/performance acceptance из них не выводится.

Quality source12s/paired48k+44.1k/variable1…4800/callback64, first QPC fractional
1375/37123 ticks, device12345/987654; generated physical waveform/effects
те же round166. В каждом из12cases1199blocks, firstPTS4800196, no trim/dropout.

| Physical clock pattern render/mic | Far reduction dB | Near gain dB / corr / lag | DT projection dB / voice dB | Max innovation frames |
|---|---|---|---|---|
| nominal/nominal |21.8608957803|−.504046690163 / .999759732931 /434|28.908079522 /−1.39746633339|23.23218522/26.6598988237|
|−100/+100ppm |21.8185482909|−.504043062622 / .999759730912 /434|27.8978212307 /−1.56283684179|26.9524998409/30.3568660857|
|+100/−100ppm |21.8372797983|−.504049270784 / .999759735234 /434|32.4709803682 /−1.50823110843|26.9461419097/30.352852868|
| sinusoidal instantaneous99ppm/99ppm |21.8583561352|−.504046805543 / .99975974115 /434|40.4195884758 /−1.43399017334|26.3149772319/29.8350472658|

WITNESS_QUALITY_DONE checks12 failures0, existing_thresholds=true,
full_hardware_matrix=false, live_capture=false. Строковый marker унаследован
от helper и не означает выполнение отвергнутого witness reconstruction.
DT — метрика всей цепочки с ideal physical references, near — actual pre/post
AEC, не независимое подтверждение сохранности waveform до resampling.

Negative:11rates8000/8001/16000/44100/44101/47999/48000/48001/96000/191999/192000
с variable input и two one-frame stress8k/192k. Healthy199blocks/2s/no trim.
Six admitted8ms jumps при8k/16k/44.1k/48k/96k/192k прекращены отдельным
phaseRejected при innovation≈383.999…384.001; raw mapperhealthy=true.
Trusted blocks5007/4999/5003/5006/5001/4999; lateSource calls не продвигаются.
Driver прекращает все дальнейшие публикации после замеченного source failure;
production cross-thread/global fence не проверен.

94admit queued regression PASS: третий вызов terminal при accepted480,
supplied0,anchors2; остальные вызовы/late drain не продвигают Source и не
публикуют canonical frames. PHASE_CASE_PASS healthy13 negative6,
PHASE_BACKLOG_PASS; contract_approved=false.

### Frozen native sources/executables

| Артефакт | SHA256 |
|---|---|
| PhaseSource.cpp |253e27c01b7685f39a2c7f8d509d5f32e3cabcbbcffb156a93d775259b2b02e4|
| PhaseQuality.cpp |b76d4dc49a9a2e0e04ad5e265c700b4768b4d93cbe53c41808d4b3b7e0bc739c|
| PhaseQuality.exe |5212d3c9be52ff43484a58455472cfc78706f94e90e632beb8c495bf81efdcc5|
| PhaseNegative.cpp |dace06d7487dd9b94ce753559eeaa6be2c942f943d2cf7f861cbc4e3fd8685ce|
| PhaseNegative.exe |d970d83386b8945be045131c35b522ef1a0d305d95f4e067b1d2816af7a004f1|
| PhaseBoundSource.cpp |f2ad6792aa8cef942bef75b000b21aa5dcdcbb7ac403ca4c2c2ede86c93988f1|
| PhaseBoundQuality.cpp |9ca316f2818321d3ff4c4df1d8949bb704feb99e77c5d4071186c19c0be8dc0b|
| PhaseBoundQuality.exe |5c3796b513486d4956c3db98772faf3de12c67a2a8269275ebb44051efdfa397|
| PhaseBoundNegative.cpp |5b404b16b217b148d2d278277b50fe9b307b41982a2e516812184e784dd80aec|
| PhaseBoundNegative.exe |309a06d3707bddde125d7b0059982418699d027bfb143582f5319f529e092666|
| phase-bound-quality-build.cmd |eb1a91ee0a2ce6244f0d0dddd44d7ac6a3db11d9ced1dc81270a7e96379fd9df|
| phase-bound-negative-build.cmd |86d15639743c21b72678cadbb42b3f0ea01e7cc977cf222a79350fab04892921|
| phase-bound-build-run.ps1 |bb52417a9db6f729d25529387ae8eabb8a5520d0e91d15f2c849a0f4e9f14b16|
| phase-bound-quality-run.ps1 |55d43ba56c41619c4cfa95964fc975fc6e1202a3b1e4ed1f12b98429bc5ce32e|
| phase-bound-negative-run.ps1 |7aaa641993c7c98569d99f7908ae04fbda9e92a80d3c3846b27630188904cc0e|

**Остаточный gap:** innovation magnitude48 не равно adjacent phase jump48.
Reviewer пример+47.52→−47.52 может иметь≈95frame difference при допустимых
отдельных значениях. Его native replay/guard согласование ещё не выполнены.
Поэтому новый design не принят, §5 не изменён; ровная output PTS не объявлена
доказательством сохранения прежнего jump refusal. Raw VM clock_drift этим
downstream исследованием тоже не исправлен.

SC-00360min/reference-x64, wave partition invariance/integer edge cases,
owned memory layout, startup-discard custody, release/Stop/finalizer/writer,
реальный hardware/AEC matrix, protected storage, current master/shared
Mac UI/features, installed end-to-end/accessibility/clean-image остаются
отдельными задачами. Tasks/checklist checkboxes не менялись. Нет commit/push/
PR/merge/install/release/product/Mac/server/constitution/root AGENTS/CHANGELOG
изменений. Optional after_plan hook не выполняется до завершения всего plan.

## Round168 — native adjacent gap replay и исправление в prototype

Предыдущий открытый counterexample не оставлен непроверенным.
`PhaseAdjacentSource.cpp` отличается от bounded Sourcef2ad… только
generated flag: after2s alternates packet QPC residual±40canonicalframes
(±8333rounded100ns ticks). PhysicalTime/audio/count/arrival не изменены.
paired48000Hz, fixed480,3s, actual raw mapper/native Sinc/real timeline/
IdentityStage, no devices/files/user audio/network. Companion источник без
noise; свои origins/cursors/full-support проверки сохранены.

Build6185 terminal0/BUILD_EXIT0; hash-guarded run11900 terminal0/NATIVE_EXIT0:
ADJACENT_GAP_CONFIRMED adjacent_frames79.9968, maxinnovation41.5589<48,
299blocks, mapperhealthy/candidateaccepted=true/normativepreservation=false.
Exit0 означает подтверждение design gap, не принятие старого кандидата.
±40frame case конкретнее reviewer±47.52 conjecture; именно этот native case
воспроизведён. Никакой claim измеренного аппаратного скачка не сделан.

`PhaseStepSource.cpp` adds previousObservedOffset/maxPhaseStepFrames/
phaseStepRejected. phaseStep вычисляется до новойcontrollercommand из разности
двух соседних raw observedOffset, не consumedOffset. First packet step0.
Nonfinite либо abs>48 прекращают Source вместе с прежним innovation guard;
previousObservedOffset обновляется только после принятия обоих checks.
Terminal witnessRejected предотвращает все последующие изменения/callbacks.
Mapper и ring текущего пакета уже могли обновиться до step rejection:
неизменность текущей metadata mutation не обещается. Staging bound сохранён.

Independent Hubble review source025eccaf… узко Approved: formula эквивалентна
Δinput×48000/rate−ΔQPC×48000/1e7, Sinc correction не скрывает этот step.
Порядок/необратимость отказа и counterfixture выделены корректно. Reviewer
не запускал VM и не принимает §5/whole candidate/native runtime;
итоговый negative ниже выполнен основным агентом после source review.

### Fresh native reruns

Same MSVC x64 /std:c++17/EHsc/MD/O2/W4/WX and pinned native dependencies.
Quality build90640 terminal0/BUILD_EXIT0; hash-guarded quality2928 terminal0/
NATIVE_EXIT0: **12/12 metrics PASS**, все численно совпали с таблицей round167,
1199blocks каждого/trim0/no dropout. Никакого weakening existing20dB/10dB/
near-gain/corr/lag thresholds. Сохраняются все ограничения метрик изround166–167.

Negative build69733 terminal0/BUILD_EXIT0; hash-guarded negative76749 terminal0/
NATIVE_EXIT0:

- 11 ordinary variable-input rates8000…192000 иtwo one-frame stress8k/192k:
  13healthy/199blocks каждый/no trim, largest ordinary raw phase-step36.7592;
- 6admitted8ms jumps: phaseStep383.998…384.002 иinnovation≈384 прекращают Source,
  raw mapperhealthy. Trusted blocks5007/4999/5003/5006/5001/4999,latecallsfenced;
- Новый adjacent counter: step79.9968Rejected=true, innovation40.2224<48,
  mapperhealthy=true.200blocks до отказа, после него counters/cursor не двигаются
  и новых canonical frames нет. Это выделяет действие именно нового guard;
- backlog94admit снова terminal3rd/accepted480/supplied0; дальнейшей выдачи нет.

Marker PHASE_CASE_PASS healthy13 negative6 не учитывает extra adjacent/backlog
в числах13/6; их отдельные строки и assertions проверены, не silently skipped.
No live capture, hardware quality, 60min, allocator/performance или installed
acceptance. Whole-session fence/Stop/EOS/writer/network здесь не реализованы.

### Fingerprints

| Артефакт | SHA256 |
|---|---|
| PhaseAdjacentSource.cpp |3a9db5a4ed90e8789ca29bcd901fc96dafd241207c5247800771fe8bdc6aefe9|
| PhaseAdjacent.cpp |3f0895c26747173d4d8f45817140093d6fd5361d5536d673cc1829f04ceaab9f|
| PhaseAdjacent.exe |3d2afdf1a382ce31b2b7963beaca5db2d5fad97712ce319873ddc4fa5b60a8f0|
| phase-adjacent-build.cmd |59c527ad0d9cd8d60fd8463a78b760f6ab7a52a54b9a06627898b076a5df108d|
| phase-adjacent-build-run.ps1 |042e36c644eb5044c9796527bbefa4780e9ad6d6b60c740606f0239cd65b8f88|
| phase-adjacent-run.ps1 |ef054eb2057f4eb9766dad07ca43d731b10a5360ddcf75ecaab64743d7dbcf96|
| PhaseStepSource.cpp |025eccaffdcbd849f74b4cdf3a9b0fd3fcd881e5b52baf65f40a1649ec754f11|
| PhaseStepQuality.cpp |d319e7cfaf7da6b34d1647c8ffced568c99f9c084b3dcf177b4054b0350b1cfc|
| PhaseStepQuality.exe |563ccda99b081b14990c9d1f459db918fb00394688dd15d93b16ebd8a1b64d33|
| PhaseStepNegative.cpp |20e3b7d5ef4669bbcc41b0d487681eb6b4125d5fe022c7de3879fdfd1b1d21d2|
| PhaseStepNegative.exe |a74163d3c4f1f68e36989275247bde1c3c5814e2a4e61e764519be94070c810b|
| phase-step-quality-build.cmd |14cabd34b70bc7703c98fe5e3a0037fa90ad023a5fde084c83fe24a16a564256|
| phase-step-negative-build.cmd |80b60d4e6e0221f5ec613aac46d71142c502f0054b08551b3ce28dcf9b243b87|
| phase-step-build-run.ps1 |22cf487c02110f837265830b51be65583417df2a697d9a4341179c63a31020c8|
| phase-step-quality-run.ps1 |78047f6cf9a05856dc8b53657b50a4eaf9060f77108ca83bc4e8a6e01fa0815a|
| phase-step-negative-run.ps1 |abd5ed167e728401197746d6a859b802d5b9d6253d595971d32def569329e497|

Guard закрывает конкретный соседний counterexample, не доказывает exact
legacy output decision-set для empty output/full trim/любой packetization.
Normative §5/design/checklists/analyze/issues ещё не приняты; Source-step48
не назван автоматически старым timeline rule. Raw VM clock_drift всё ещё
не исправлен. Actual ClockMapper source cmp с frozen native research copy PASS.

Tasks118/92checked/26open; их SHA0d10022f… и protected-custody SHA48704f41…
сохранены. No product/Mac/server/constitution/root AGENTS/CHANGELOG changes,
commit/push/PR/merge/install/release или reviewer checkbox edits. Результаты
меняют следующий шаг: согласование guard/численных краёв/partition/resource/
full prefix и переход к принятому design, а не повтор тех же quality cases.

## Round169 — waveform partition FAIL, command-only исправление и full support

Продолжение в зарегистрированном worktree200-windows-followup,
branchcodex/200-windows-followup, HEAD99b00a579c24b50e320465b69d9a296038bc544d.
Risk lane high-risk; текущая работа — bounded Phase0 speckit-plan, не product
implementation. Goal остаётся full Windows/macOS parity, не выполнение probes.
Mac/server/app sources, installed package и GitHub state не изменены.

### Исходный тест и сохранённый отрицательный результат

`PartitionSource.cpp` отличается от Source025eccaf… только необязательным
наблюдателем до timeline.push: сохраняет все реальные full-support float values,
проверяет непрерывный PTS, включает неполный финальный хвост. Actual mapper/
phase/step/staging/Sinc алгоритм прежний. Генератор700+1900Hz задан абсолютным
supplied/physicalTime, не размером пакета либо callback. Два источника одной
частоты, разные device origins12345/987654, одинаковое начало1375ticks,
номинальные physical clocks, rounded packet QPC/no metadata noise,0.5s.
IdentityStage; clockRecoveryFrames0 запрещает скрытый trim/interpolation.
Входы fixedrate/100, variable1/479/31/4800/480/7/1024/211, one-frame;
drain соответственно480/479/1. Контроллер выключен/включён.
11rates8000/8001/16000/44100/44101/47999/48000/48001/96000/191999/192000.
44сравнения,66полных прогонов; начало/длина/generated count сравниваются
отдельно от максимальной ошибки значений на общей длине.
Existing tolerance abs(sample difference)<0.00001 из AudioNormalizerTests
не увеличен. Это сравнение комбинаций packet/drain, не изоляция каждого фактора.

Предыдущая попытка compile64342 terminal2/C4459: local failures скрывал global
из frozen MacReference. Исправлено только имя partitionFailures, /W4/WX оставлен.
Fresh build36746 terminal0/BUILD_EXIT0. Hash-guarded run58584 terminal1/
NATIVE_EXIT1, PARTITION_DONE cases44 failures7. Все22controller-off exact0;
controller-on15PASS/7FAIL. Начало, full tap count и generated count совпали во
всех44; расхождения только в значениях, а не потерянном хвосте между вариантами.

| Частота | Разбиение FAIL | max_error |
|---|---|---|
|8001|variable|0.0000390559434891|
|8001|one-frame|0.0000411868095398|
|44101|variable|0.0000356584787369|
|47999|variable|0.0000273287296295|
|47999|one-frame|0.0000265836715698|
|96000|one-frame|0.0000149263069034|
|191999|variable|0.0000275397142104|

Independent Hubble source review принял measurement method узко, не runtime
PASS. Его замечание: equality-only не исключает одинаковую потерю всех вариантов;
для полноты нужны независимые ожидаемые границы и block count. Native FAIL
не удалён после исправления; первоначальные Source/driver/EXE сохранены отдельно.

### Исправление команды и повтор качества/отказов

`QuantizedPhaseSource.cpp` добавляет только command deadband:
feedback=observedOffset−consumedOffset;
при выключенном controller или abs(feedback)<=sourceRate/1e7 выбирается
command0/nominalratio, иначе прежний clamp±500ppm. История/позиция Sinc сохраняются.
Raw mapper и ранние innovation48/adjacent48/staging refusal не меняются.
SetRatio в pinned source сравнивает с double epsilon, не1e-6, и пересчитывает
ядро. Generated source продвигает тот же actual cursor; количество callback
запросов проверено против NativeCursor, две версии EOS filler сверяются побитно.

One-tick обоснование относится к **двум идеальным меткам, округлённым до
ближайшего100ns тика**, а не точности аппаратного/виртуального WASAPI.
Сам integer format не даёт такого bound. Feedback включает также остаток Sinc
и арифметику double; глобальный численный предел для любых длительностей этим
опытом не доказан. Frozen комментарий про два endpoints читается только с этой
оговоркой; для product code её нужно записать прямо. Independent Hubble review
условно Approved именно этот эксперимент/порядок guards, не весь contract§5.
Reviewer не запускал native tests. Дальнейшие результаты получены основным агентом.

Build39604 terminal0/BUILD_EXIT0; hash-guarded run22173 terminal0/NATIVE_EXIT0:
44/44comparisonsPASS, all max_error0, same start/full length/generated counts.
Это показывает устранение найденной зависимости данным command-only изменением,
не универсальную физическую причину hardware timing errors.

Quality build65596 terminal0/BUILD_EXIT0, hash-guarded run30645 terminal0/
NATIVE_EXIT0:12/12existing metricsPASS,1199blocks/case,firstPTS4800196,trim0.
Far reduction21.8185482909…21.8608819457dB при неизменном20dB пороге;
near gain−0.504049270784…−0.504043062622dB,correlation≥0.999759730912,lag434
при прежних1dB/.98/480;
DT reduction27.8978212307…40.4195921013dB,voicegain−1.56283684179…−1.39746615407dB,
dropoutfalse при прежних10dB/3dB. Numbers не объявлены побитно прежними.
Near — actual pre/postAEC, DT — метрика общей цепочки по ideal physical
references; это не отдельный proof input waveform fidelity или pureAEC quality.

Negative build40082 terminal0/BUILD_EXIT0, hash-guarded run22183 terminal0/
NATIVE_EXIT0:13healthy/199blocks каждый,6admitted8ms jumps rejected,
trusted5007/4999/5003/5006/5001/4999blocks; adjacent79.9968 отказал при
innovation40.2224<48/raw mapperhealthy/prefix200blocks;94admit backlog снова
terminal3rd/accepted480/supplied0. Поздние вызовы не продолжают Source/output.
Marker13/6 не включает extra adjacent/backlog, их assertions и отдельные строки
также выполнены. Source-local fencing не назван product cross-thread fence.
No devices, private audio, files of recordings, microphone capture или network.

### Независимые полные nominal границы

`FullPrefixPartitionProbe.cpp` сохраняет тот же corrected Source/test и добавляет
ожидаемые nominal границы: center s(j)=(rate/48000)×(j+0.4), j≥1;
полная опора ядра требует s≥16 и s<count−15. Для этого1375tick origin/.5s:

```text
count = floor(rate/2)
jfirst = ceil(768000/rate - 0.4)
jend = ceil((count - 15)*48000/rate - 0.4)
trusted range = [jfirst,jend)
first PTS = 4800007 + jfirst
blocks = floor((jend-jfirst)/480)
```

Проверяются nonempty tap, оба input counts/generated counts, полный tap length,
первый PTS и число480-frame блоков, включая проверку хвоста через tap.
Неполный хвост не дополняется неподтверждённой тишиной ради полного блока.
Независимый Hubble review узко Approved новые формулы и assertions; для всех
11rates границы дополнительно проверены точной рациональной арифметикой.
Это закрывает замечание об одинаковом укорочении внутри этой fixture, не для
dynamic ratio/любых origins/длительностей. Reviewer не запускал VM.

Build54319 terminal0/BUILD_EXIT0; hash-guarded run87184 terminal0/NATIVE_EXIT0:
44comparisons/66runsPASS с new full_support_bounds=true, max_error0.
Например8k:[96,23910)/23814samples,48k:[16,23985)/23969samples,
192k:[4,23996)/23992samples. Baseline и alternate равны всему ожидаемому
пригодному диапазону, не только удобному качественному окну/480-frame prefix.

### Frozen source/executable fingerprints

Все research files вне git в task mirror f200-witness-chain.kgDXSB;
actual raw ClockMapper compare с canonical source PASS. Windows MSVC x64,
/std:c++17 /EHsc /MD /O2 /W4 /WX, pinned native dependencies прежние.
Сборки с общей obj папкой выполнялись последовательно. Quality runtime и
negative build пересекались; CPU/скорость исполнения по этим runs не измеряются.
Build/hash/runtime evidence не заявляет hermetic reproducible build.

| Артефакт | SHA256 |
|---|---|
|PartitionSource.cpp|e7c6986fb1a0b06a2912bd9ab43548af5f1fd53739776aad1a74bcde73dcd505|
|PartitionProbe.cpp|3a9a2e5a511b966b4b41478a2a2402420f02c2b0df0e5c9544fcb674496596dd|
|PartitionProbe.exe|e81db936cbcf503d14d877da8762cacde043a7f0569e98c3a181c641b01503f8|
|QuantizedPhaseSource.cpp|f545ed2fc0331388f2ca0e5aa5859c4edff571344f7fcb1f6ecb78f3f688de14|
|QuantizedPartitionProbe.cpp|ea6fe3875d2030e82cc1c5f2fffe0979525d8ca1000d51370ed4ea23232d4a8a|
|QuantizedPartitionProbe.exe|f05fe7c02858052318af73819f958f26429ce1b8c83d085d958ebd933c34a3d9|
|QuantizedPhaseQuality.cpp|97aa7ea0c8347f31c4ff4298ceec6f9d160a1241b0f614f8f20b36ea0e9ac32c|
|QuantizedPhaseQuality.exe|d95f714d50d0d5a979d13b99cf852e8532e0a99ee63badd13c1e4d60f0760174|
|QuantizedPhaseNegative.cpp|72e1cd1b7aa80e0f7400050324f232fd3521c1987da0a99512c73a9cdd976720|
|QuantizedPhaseNegative.exe|cb409995236930c2abeebc0d1df14d30c071524ce7c381d6492b7dae35a30f50|
|FullPrefixPartitionProbe.cpp|4e8f1e8acc25b12676ee24a29f5b0195f444a0f0e86c2f5f7d91b06e0bd7c975|
|FullPrefixPartitionProbe.exe|ed3220b3ef6ddeb90563799b8bbbb8384ece06eae5bb9a1c5462ec6fb53976d2|

Номинальный partition gap устранён в prototype на выбранных случаях.
Нормативный§5/full design/численные края/saturated controller/owned resources
и live raw VM clock_drift остаются открытыми. Ни этот тест, ни12quality PASS
не закрывают SC00360min/hardware/installedUI/auth-upload/deletion/accessibility/
clean-image/protected storage. Tasks118/92checked/26open не меняются;
task SHA0d10022f… и custody SHA48704f41… сохранены. Нет commit/push/PR/merge/
install/release/product/Mac/server/constitution/rootAGENTS/CHANGELOG изменений
или reviewer checkbox edits. Optional after_plan отложен: полный план не готов.

После обновления артефактов PASS: check_spec_kit_governance.py,
speckit-bootstrap --doctor --frozen, Ruby YAML parse F200, git diff --check,
UTF-8/newline/trailing-whitespace checks untracked validation/candidate.
Unique tasks118/92checked/26open; оба полных task/custody SHA совпали с frozen.
git diff --exit-code для apps/windows/apps/macos/apps/server/constitution/
AGENTS/CHANGELOG terminal0. HEAD99b00a579c24b50e320465b69d9a296038bc544d
сохранён; открытых build/native процессов этого раунда не осталось.

## Round170 — large first origins и actual native kernel support

Предыдущий round169 — progress: native FAIL исправлен и новые проверки меняют
следующий шаг, не verified wait/no-progress. Текущий canonical worktree/branch
проверены вновь, HEAD99b00a579c24b50e320465b69d9a296038bc544d.
High-risk speckit-plan Phase0 продолжается; setup-plan не перезаписывал active
план. before_plan commit hook disabled, полный plan/after_plan ещё не завершены.

### Матрица и первоначальный ideal FAIL

`OriginPhaseSource.cpp` — derivative corrected sourcef545…: вместо fixedq0
задаётся generatedqpcOrigin, fixture sum проверен до переполнения. Controller/
raw mapper/phase/step/staging/Sinc алгоритм прежний. One-tick комментарий
уточнён: только ideal nearest-tick endpoints, не physical/VM measurement bound.
Generator-only maxPhaseMs измеряется в относительных координатах, не разностью
двух огромных абсолютных double времён. Ни этот observer, ни generator origin
не становятся production clock oracle или дополнительными стартовыми воротами.

Длительность0.05s,physicalnominal,metadataNoisefalse,signal700+1900Hz.
11rates8000/8001/16000/44100/44101/47999/48000/48001/96000/191999/192000;
origins0/1000000000/2^53−625/2^53+625/2^63+1375/UINT64_MAX−2000000;
startoffsets0/1/104/105/624/1375ticks;fixedrate/100,variable1…4800,oneframe;
drain480/479/1. Controller on, timeline recovery0. Pair own device origins
UINT64_MAX−floor(rate/20) и12345, одинаковая actualQPC опора. LargeabsoluteQPC
не смешивается с large elapsed span: каждый Source здесь всего0.05s.

Independent ideal reference использует integer identity q×3/625, не largeq
floating-point multiplication. Counts/grid/residue и rational ceil support
вычислены отдельно от Source. Build35307 terminal0/BUILD_EXIT0; hash-guarded
origin-run terminal2/NATIVE_EXIT2 сразу на первом8k/origin0/start0/fixed case.
Остальная planned ideal матрица этим запуском **не выполнена**.
Trace derivative build78020 terminal0, hash-guarded run47590 terminal2:

```text
count400/400,generated2311/2311,expected_end2310
samples2214,expected_samples2214,firstPTS97,expectedPTS96,blocks4
final mirrored cursor385.1666666666647
```

Независимый review reproduced double cursor arithmetic:
j96 position15.999999999999977 → cell15; j97 position16.16666… → cell16;
j2310 position384.99999999999807 → cell384; j2311position385.16666… → cell385.
Это совпало с trace, но ещё было лишь mirror/kernel-source evidence.
Reviewer уточнил: ideal range[96,2310) не прошёл; это не доказывает Source
отбрасывает пригодный **фактический** выход. Пин использует floor(local double)
для реального input_ptr, не ideal rational position. Нет epsilon-расширения
support, forced phase nudge, reinterpretation native samples или patch библиотеки.

### Непосредственная проверка actual convolution window

`NativeSupportOriginProbe.cpp` использует existing upstream FRIEND_TEST seam
SincResamplerTest_Convolve_Test. Только отдельный reference Sinc instance
перехватывает convolve_proc_: записывает actual input_ptr−r1_, callbackbase0
после первого64request либо supplied−80 после следующих, затем ровно один раз
вызывает прежнюю CPU функцию с неизменными аргументами. Ни vendor исходник,
статическая библиотека, её arithmetic/kernel, ни Source экземпляры не патчатся.
Каждый Resample1 имеет ровно один recorded convolution. Читаемый window32
содержит[center−16,center+15], его отрицательная левая граница выводится signed.
Полнота относится ко всем32 входным отсчётам независимо от нулей коэффициентов.

Reference заранее получил весь generated input и sealed filler; это допустимо
для наблюдения геометрии/значений, не доказательство live scheduling. Первая
phase command и возврат кnominalratio воспроизводятся; Source commandppm0
проверен в каждом случае. Reference actual full range/value collector сравнивается
с Source tap, generated counter, firstPTS, length и число480-frame blocks.
Укорочение/удлинение всего диапазона нельзя скрыть совпавшим common prefix.
Value tolerance прежний<0.00001; full range endpoints/counts требуют equality.

Первый build87347 terminal2/C2653 — один unqualified namespace в probe,
исправлен без выключения /W4/WX. Fresh build98707 terminal0/BUILD_EXIT0;
hash-guarded run45408 terminal0/NATIVE_EXIT0 подтвердил четыре точки:

| j | Actual cell | Полный native read window | Внутри реального[0,400) |
|---|---:|---|---|
|96|15|[-1,30]|нет|
|97|16|[0,31]|да|
|2310|384|[368,399]|да|
|2311|385|[369,400]|нет|

Для8k нативный диапазон[97,2311),2214values,reference_error0. Source не выдал
startup−1 и не включил input400, сохранил весь наблюдавшийся actual full range.
По всем36origin/startgroups×11rates×3partitions прошли1188 Source executions
и1188reference comparisons;792partition comparisons имеют max_error0.
Reference сравнения во всех случаях пройдены при<1e-5; error0 напечатан только
для subsetorigin0/start0. **Bitwise/zero error всей native reference matrix не
заявлен.** Ideal FAIL сохраняется отдельно, не превращён в PASS по новым bounds.
Номинальная матрица не проверяет variable physical rate либо saturated command.

Independent Hubble source review узко Approved observer2eeb…/Source d747…;
конкретных code defects в этом последовательном конечном исследовании нет.
Reviewer получил результаты от main, сам VM/native runs не запускал.
Static hook ownership/no exception reuse и отсутствие explicit reference
finite check ограничивают область: parallel/nonfinite/повтор после exception
не разрешены этим review. Они не названы принятой product архитектурой.

### First-origin integer proof, отдельно от dynamic cursor

Для любогоuint64q `q*48000/1e7=q*3/625`. Quotient/remainder compute не требует
largeq multiplication. Максимальные точные integer значения:

```text
qmax18446744073709551615
wholeproduct88544371553760000
remainderproduct479999952000
roundedGmax88544371553805848 < INT64_MAX
abs(signed residue)<=4992000
```

Rounding pattern имеет period625 ticks/3frames; fractional residue denominator625
нечётен, exact first-origin half-frame tie невозможен. Initial-phase numerator
absresidue×rate<=958464000000 и denominator480000000000 точно представимы
binary64 перед division. Initial magnitude<=nominal×0.4992, first step
nominal+initial>=nominal×0.5008>0, margin доrate/96000 значителен относительно
binary64 rounding. Publication G+j требует отдельного checkedj/add, как в Source;
прочие огромные counters/elapsed/feedback этим first-anchor proof не закрыты.

Main BigInt executable cross-check двух quotient/remainder формул на3491q
(all625residues в выбранных блоках эпох, последний блок обрезанuint64max)
PASS/maxabsresidue4992000. Это аналитические integer bounds и периодический
cross-check, не испытание всех2^64q на Windows или hardware calibration.

### Source identity и fingerprints

Native Sinc file hashes сначала отличались от Mac copy. Не объявлены совпавшими
по предположению: fresh Windows script89623 terminal0 проверил UTF-8 source после
CRLF→LF normalization для sinc_resampler.cc/.h и gtest_prod_util.h, все3MATCH.
Normalized hashes f46fa666…/f731519a…/bf6d5483… совпали с прочитанным pinned source.
Это source-content identity с явной нормализацией, не byte-identical checkout
и не attestation, что эти bytes воспроизводимо создали linked static library.
MSVC x64/O2/W4/WX, предыдущие pinned libraries, последовательные builds.
Research files внеgit в f200-witness-chain.kgDXSB, никаких useraudio/devices/network.

| Артефакт | SHA256 |
|---|---|
|OriginPhaseSource.cpp|d74741b2f68692ef330a4ea54404ab75fe8ad0498e87be9495ea4cc65c37f500|
|OriginPartitionProbe.cpp|7d5571731bfc6600d873a3a341d485c34ae1ec940db7c5786dc153c5f4b96d15|
|OriginPartitionProbe.exe|eb97ea8ff2ecd33e34605b3c505fa96abc025736182acf6b8e2339c62665bafb|
|OriginTraceProbe.cpp|47acfc3aca36ad6c38c3d4fcbfdf52a4394aaaf6681d3749652c9d6a7394ab7e|
|OriginTraceProbe.exe|390f06dd0f190d3c026f67a1f19e6ac7bbbb9bf5ed6c69b856559a067120290d|
|NativeSupportOriginProbe.cpp|2eeb1c51b77bae392e1995a2b6ec28a1041a4ab0ce7a27acd136998d4ead4cec|
|NativeSupportOriginProbe.exe|8d05da6950e2d1b9f0ea53698f060d13b83e306fd4179309b4c8dcd5dd9a177f|
|origin-run.ps1|16033a6fbf7fbb557e80c49eb91bd51836354a85971808575a2b84a4f1d369f8|
|origin-trace-run.ps1|f1882697bceb9b48ec98397379c971273058c5a81066d285357c6f32e1f6cc6d|
|native-support-origin-run.ps1|6e0d33612f84a9c2cb4e1ed89bee5807c586f63728c4abda684d70290a060f71|

Новый результат закрывает narrow actual/ideal support вопрос на исследованной
матрице и first-origin arithmetic uncertainty, не full clock design/§5.
Следующие gaps: большой elapsed/input/output и динамическое phase accounting/
saturation/actualkernel, Source-owned memory/whole-session fence; rawVM clock_drift
и остальные release/parity/storage/UI gates по-прежнему открыты.
Tasks118/92checked/26open, taskSHA0d10022f…/custodySHA48704f41… сохранены.
No product/Mac/server/constitution/AGENTS/CHANGELOG, commit/push/PR/merge/
install/release или reviewer checklist checkbox изменения. Полный план не готов;
optional after_plan не исполняется. Все handles раунда терминальны.

После обновления PASS: governance12104, frozen doctor2540, Ruby YAML parse
F200/extensions, git diff --check, untracked Markdown UTF-8/newline/whitespace.
Unique tasks118/92checked/26open; оба полных task/custody SHA прежние.
Product/Mac/server/constitution/AGENTS/CHANGELOG diff empty, HEAD неизменный.

## Round171 — числовые состояния и исправление research residual/cell

**Lane:** high-risk F200, продолжающийся speckit-plan Phase0; code-reviewer.
Канонический worktree найден и зарегистрирован:200-windows-followup/crisp,
branchcodex/200-windows-followup,HEAD99b00a579c24b50e320465b69d9a296038bc544d.
Исходные грязные изменения сохранены. Ambient0309/detached не используется.
Не создавал новую рабочую копию, не выполнял prune/reset/checkout.

### Область проверки и retained counterexample

Standalone NumericResidualProbe не открывает устройств, не читает/сохраняет
пользовательский звук. Он вводит matched numeric states, где ожидаемый feedback0
рассчитан независимо через целые дроби с общим denominator30000000.
11rates8–192k ×8counts ×3drift directions ×64shifts =16896states.
Counts соответствуют60s/1h/24h/30days либо2^32/2^40/2^48/2^52−4800;
drift≈−50/0/+50ppm. Это не фактическое прохождение всех отсчётов Sinc и не
свидетельство достижимости этих internal states или hardware continuity.

Первый counterexample старой формулы:

```text
rate=8000 accepted=281474976710657 dt=351826128702276850
output=1688765417770928 base=281474976710640 index=16.853333333333332
old feedback=-0.09375 stable=0
base=281474976710640 index=16.98: old center281474976710657,
local center281474976710656
```

Всего oldfalsecommands2003,center mismatches949; first-hour maxoldfeedback
1.1920928955078125e−7. Новый общий helper имеет maxfeedback error
7.1054273576010019e−15 относительно matched0. На этой матрице separate split
floating residuals также дали0falsecommands — их нарушение не доказано.
Сбой raw VM clock_drift эти extremely large states не объясняют.

### Минимальный research successor

OriginPhaseSource.cpp d747… оставлен неизменным; NumericPhaseSource производен
от него. Shared PhaseRemainder вычисляет `count*rate/denominator` через quotient
и remainder, проверяет signed representability до операций, объединяет integer
observed/consumed residuals до double и добавляет local index/fractions/phase.
Соседний step использует accepted−previousAccepted и q−previousQ. Input admission
не выходит за существующий продуктовый2^52 bound. Drain сохраняет прежний
integer center из prepare, вместо повторного floor(double(base)+index).
Настоящий native Sinc/history/ratio update/read window не изменяются.
Raw mapper/budget/flags,innovation48,step48,command cap500ppm и one-tick зона
не увеличены. Arithmetic failure terminal researchwitnessRejected; product typed
reason/controller/finalizer semantics этим не реализованы и не приняты.

### Fresh native проверки

MSVCx64/O2/W4/WX, та же ARM64 Parallels VM, pinned libraries. Все builds и
runs последовательны. Никаких устройств, private content, network или installs.

| Проверка | Build / runtime result |
|---|---|
| Numeric standalone first f8a5… | handle80319:build0/native0,16896states |
| Shared-helper derivative85a12… | handle50232:build0/native0,same matrix |
| Final numeric572b… | handle90070:build0/native0,16896states/10guards PASS |
| Actual-kernel support | handle6053:support build0/native0,792/792comparisons,1188Source runs |
| Quality | samehandle:quality build0/native0,12/12metrics PASS |
| Negative | samehandle:negative build0/native0,13healthy/6jumps+adjacent/backlog PASS |

10 guard checks включают output scale overflow,input>2^52,nonfiniteindex/phase,
packetdelta4801,invaliddenominator,nominalstep,exact−48-frame step,initialphase
once и pre-first-output accounting. Арифметические границы не аппаратный runtime.
Support: прежний independent actual32-sample observer,11rates/6qorigins/6starts/
3partition variants,792partitioncomparisons maxerror0. Referencevalues проходят
existing1e−5; referror0 выводится только origin0/start0subset, не всейmatrix.
8k first actual range[97,2311),startup j96unobserved,lastj2311outsideinput;
старый ideal range[96,2310)FAIL не превращён в PASS.

Quality:4clock-pattern pairs×3modes,12s generatedsignal,1199blocks each,
firstPTS4800196,trim0/0. Far21.813369667–21.8608818751dB≥20;
near gain≈−.50405dB/corr≥.9997597/lag434 в прежних1dB/.98/480;
doubletalk27.89782 из старого раунда не переиспользуется: fresh28.427841439–
40.4193765576dB≥10,voicegain−1.569994…−1.397466dB within3,no dropout.
Near сравнение pre/postAEC, DTwholechainidealref, не inputSRC fidelity.

Negative: healthy199blocks, jump trustedprefix5007/4999/5003/5006/5001/4999;
adjacent step79.9968 отдельно отвергнут приinnovation40.2224<48/rawhealthy,
200blocks retained.94backlogcalls terminalat3rd/accepted480/supplied0.
Поздние вызовы не возобновляют Source output; не whole product Stop proof.

### Fingerprints и ограничения

Research artifacts внеGit в f200-witness-chain.kgDXSB. Все приведённые terminal
exit наблюдались; no pending build/run handle. Main выполнял runtime, independent
source review отдельно; full§5/checklist approval из narrow tests не следует.

| Артефакт | SHA256 |
|---|---|
|PhaseRemainder.h|de73c76412f9af6802587201817f8a23975bd296ec54ccb7eb60ebe79c7fc7d9|
|NumericPhaseSource.cpp|00705e3d6afd8f20065c126bebb2937d5b8e6d76517dc36721624e87f25951b2|
|NumericResidualProbe.cpp|572b44519503859c56ef259bc482ffff4b4a6e58f385767f22a4d8a6308d261d|
|NumericResidualProbe.exe|010acf0e3c568c2254246e440deabe811224d1dd06ab3af475333ec9fe153ee9|
|NumericSupportProbe.cpp|70066afa719f8317e407505fb0247fe96924d2846b702c8bbe8ccc70c187c09b|
|NumericSupportProbe.exe|9b170fe88f94f107b424a1a7c4187c1f19f4d5511266da5a3d247636b37a2d23|
|NumericPhaseQuality.cpp|9eed44faa952db1c6369ef0856b428824c988ba219398454c6f1e506b18220a7|
|NumericPhaseQuality.exe|e694a1c3454168df3136390b8312cd1caca0a0e5c1d2975a26402879b53c509f|
|NumericPhaseNegative.cpp|ea14e14bfc3270cc76477cdcba8ab2e2a96e498df7869819c7c9109908eb4b9f|
|NumericPhaseNegative.exe|05115cdb8d5f96a2b8820d7960ce408a7fdc19d61214dffcdd252dd77526d5a5|
|numeric-native-build-run.ps1|536f1f1e9ce7710fe736da646c30507e8b54752e1bc255634d39462881d669d8|
|NumericSupportProbe-round171.log|008a2f5f1786a686292f44fc2bd8c06d0a0bad612a1bdf585c6fbed484bf4102|
|NumericPhaseQuality-round171.log|b86cc1dc660b77039690e5ce24e5a5be8c60bbe4157369e50de1bdd202fd87a9|
|NumericPhaseNegative-round171.log|8273ea0283c6e9d9962b1ad131dcfeb3ef7e5016a22782f59116dfb3cfae4e76|

Wrapper6053 проверяет пять fixedinputs before/after каждого build/run, печатает
EXEhash до запуска и сохраняет metadatastdout. Это local agreement, не hermetic
compiler/reproducible-build attestation всех linked dependencies. Numeric wrapper
печатает finaldriver/EXEhash; commonhelper совпал до/после native testchain.

Source-owned FIFO/whole-session fence, dynamic saturation/longreachedcursor,
§5 design/checklist/analyze/issues, protectedstorage/UI/auth/upload/hardware/
install/release ещё открыты. Tasks не менялись, новых reviewer checkboxes нет.
Product/Mac/server/constitution/AGENTS/rootCHANGELOG не изменялись; commit/push/
PR/merge/install/release не выполнялись. Optional after_plan не исполняется,
поскольку полный план ещё не принят. Цель полной работоспособности Windows активна.

Independent Hubble source review узко **Approved** для Source00705… и общего
helperde73…: корректны scale/domain/signed difference, previous-packet step,
input admissioncap и сохранение native cell; concrete blocking findings нет.
Source/helper hashes reviewer перепроверил после чтения. Mapper/anchor могли уже
измениться до arithmetic refusal — запрет дальнейшей выдачи не означает полного
отката metadata. Ограничения index/firstphase обеспечены реальным Source/Sinc,
helper не универсальный валидатор произвольной записи internal полей.
Полный§5/design и побитовое равенство всех старых граничных решений не приняты.
Reviewer не исполнял native runs и не утверждал final numericdriver572b…/10guards,
которые менялись во время review: их PASS относится только к main execution.

После обновления PASS: governance26357, frozen doctor40692, RubyYAML
F200/extensions, git diff --check и UTF-8/newline/whitespace для untracked
clockcontract/validation. TasksSHA0d10022ffc500dc8000d90e37cb65655c0ec2d5bf83ebe4da922a80ac04e2f19
и custodySHA48704f413e132f2b643206649a6422f6e6f6ea118cc63c86d5b675e9d4be9d54
сохранились. Product/Mac/server/constitution/AGENTS/CHANGELOG diff пустой;
HEAD прежний. Все процессы/агент раунда завершены.

## Раунд 172 — требования календарного подключения Windows

Canonical worktree вновь проверен в Git: `200-windows-followup/crisp`, branch
`codex/200-windows-followup`, HEAD `99b00a579c24b50e320465b69d9a296038bc544d`.
Копия существует, изменения сохранены; причина прежнего исчезновения не доказана.
Remote master read-only `ls-remote`: `721b5125d799ea798a4af0b3625e18d3c1109039`.
Fetch/merge/reset не выполнялись. Прежний раунд дал independent T115 requirements
PASS; его область не расширяется до полного приложения и нового T119.

Existing-feature specify/clarify/plan уточнили T119, без новой ветки/номера:
US2, FR-002/006, clarification2026-10-02, bridge§10, data-model§8, plan,
research, quickstart§13 и parity-matrix ownership. Текущий Windows принимает
шесть intents и открывает snapshot URL карточки; Mac F279 использует fresh
join-target и current operation. Седьмой calendar_join описан как целевой,
не реализованный: UUID-only, trusted main route/nonce, one busy, fresh resolver,
bounded terminal states, stale cancellation, native/browser recovery и отдельный
native Join-and-record. Общий HTML, server/provider integration не копируются.

T119 append прошлого раунда сохранён; tasks SHA
`45641d615923b4c049482397e90e6ce765255b8ba7467f2d867cd4c8c7e27d50`:
119 unique tasks,92checked/27open. Прежний548-line prefix SHA совпал с
`0d10022ffc500dc8000d90e37cb65655c0ec2d5bf83ebe4da922a80ac04e2f19`.
T119 не закрыт, GitHub issue sync не выполнен; новый дизайн направлен Hubble
на независимую проверку all112 affected requirements. На момент записи report
не завершён; observation timeout не означает остановку reviewer.

Primary sources: F279 calendar contract, Mac bridge/opener/DesktopUploadClient,
server `api/calendar.py`/`api/schemas.py` на указанном master. Host fixture:
141case,66allowed/75denied; это подсчёт expected cases, не Windows validation.
Microsoft Launcher/IgnoreAppUriHandlers/QueryUriSupport docs внесены в research.
Windows11 VM read-only WinRT object check exit0: BROWSER_ONLY_OPTION=True;
URL/apps/audio не запускались. Первая PowerShell попытка exit1: отсутствовала
WinRT type metadata/argv quoting; encoded вызов исправил только диагностику.
Этот результат не C++ compilation/launcher/native client или installed parity.

PASS: governance, frozen doctor, F200/extensions YAML, git diff --check.
Optional agent-context hooks не выбраны: active pointer/rootAGENTS уже корректны,
общий план/clock gates ещё не завершены. Auto-commit hooks выключены.
Product/Mac/server/constitution/AGENTS/rootCHANGELOG diff пустой; implementation
commit/push/PR/merge/install/release не выполнялись. T119 native association
acceptance, clock design, protected implementation, billing policy и полная
Windows приёмка остаются открыты. Общая цель не уменьшена до проекта Join.

## Раунд 173 — календарные требования приняты, технические пробелы сохранены

Рабочая копия существует и зарегистрирована: `200-windows-followup/crisp`,
ветка `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Причина прежнего исчезновения неизвестна;
чужие копии и сохранённые изменения не перемещались и не удалялись.

Исправлен C1: источник календаря `provider_family` не выбирает приложение встречи.
Выбор определяется допустимым HTTPS host/path; calendar/unknown + Zoom URL и
zoom + example.org включены в будущие проверки с подставным resolver. Reviewer
сам актуализировал security CHK008/009 для семи запросов и calendar_join_reply.
Независимый Hubble перечитал все112 критериев, итог112/0 для воздействия T119;
заключительная сверка строки411 сохранила этот результат. Это проверка качества
требований C1/C2/L1, не приёмка технического способа запуска или реализации.
Окончательный bridge SHA-256:
`127356a14df140364ce619554bcc42cab03286262065afa40c1fcdb73ac51ff4`.
Отчёт review-2026-10-02-calendar-join-design.md SHA-256:
`076b7ab014396095bfcf22e51e9977ba9a795dfc2d11ba1f702df452f93b5bfd`.
Основной агент прочитал отчёт и сверил оба хеша; историю отказа не переписали.

Текущий read-only analyze:22FR+10SC,119 уникальных tasks,92checked/27open,
32/32 требований имеют задачи; отсутствующих task references нет. Покрытие
означает наличие работ, не готовность. CRITICAL0/HIGH2/MEDIUM0/LOW1:
U1 — не выбран подтверждённый способ запуска Windows Телемоста при HTTPS
handler браузера; U2 — не принят causal clock/mapper→resampler→timeline проект
и не устранён VM clock_drift. LOW — исторический двухкомандный Goal Phase4
перекрыт явными уточнениями Phase15–19/FR006/bridge. Новых конфликтов конституции
не найдено. Открытая реализация billing T102 и protected T116–118 сама по себе
не считается дефектом покрытия требований. Общий analyze gate ещё не пройден;
код и issue sync в этом раунде не начинались. Analyze hooks выключены.

Три последовательные read-only проверки реестра VM завершились exit0,
audio_read=false/url_launch=false. В HKCU Classes есть protocol telemost с
URL Protocol и URI placeholder; его command target — существующий
YandexTelemost.exe, версия2.42.4.9707, product Yandex Telemost,
GetAuthenticodeSignature=Valid, publisher YANDEX LLC. Одновременно
RegisteredApplications содержит отдельную запись Yandex Telemost (Mac)
с Parallels ProgID для protocol telemost. Это разные записи; выбранный ОС
получатель, формат native URI и реальное открытие Windows-клиента не доказаны.
Полные пути/command templates/пользовательские ссылки в evidence не выводились.
Реестр, defaults и процессы не менялись; встреча/микрофон не запускались.

Возможная следующая нативная проверка, НЕ принятое решение:
[SHELLEXECUTEINFOW](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/ns-shellapi-shellexecuteinfow)
допускает явную association class/key; проверить пригодность передачи неизменной
проверенной HTTPS ссылки известному обработчику без угадывания custom URI,
ручной сборки process command или смены defaults. Документация API не доказывает
поддержку этой ссылки Телемостом. Дизайн Launcher в frozen review не подменён.

PASS: governance, frozen doctor, F200/extensions YAML, git diff --check.
Первый подсчёт FR/SC дал0 из-за неверного regex для Markdown, исправленный
подсчёт подтвердил22/10; отсутствующих требований не было. Tasks SHA сохранён:
`45641d615923b4c049482397e90e6ce765255b8ba7467f2d867cd4c8c7e27d50`.
Product/Mac/server/constitution/AGENTS/rootCHANGELOG diff пустой. Commit/push/
PR/merge/build/install/release не выполнялись; установленный пакет не обновлён,
T119/T097 и полная функциональная/визуальная приёмка Windows остаются открытыми.

## Раунд 174 — передача HTTPS собственному Windows обработчику

Рабочая копия существует и зарегистрирована, branch codex/200-windows-followup,
HEAD `99b00a579c24b50e320465b69d9a296038bc544d`; active pointer/prerequisites
верны. BRANCH alias в prerequisites не подменяет текущую Git branch. Причина
прежнего исчезновения неизвестна. Чужие копии/изменения не удаляли и не переносили.
Линия: high-risk existing Spec Kit slice, speckit-plan Phase0 research, не код
продукта. CUA сообщает Mac locked; реальный Телемост/URL/микрофон не запускались.

Read-only VM queries: AssocQueryStringW(IS_PROTOCOL отдельно FIXED_PROGID,
EXECUTABLE) вернул S_OK с существующим Parallels `.ico` объектом. Это lookup,
не actual dispatch. AssocQueryStringByKeyW от read-only HKCU telemost key дал
S_OK, YandexTelemost.exe, product Yandex Telemost, Authenticode Valid. HKCU/HKCR
command metadata: quoted native target, %1; native App Paths HKCU/HKLM absent.
Первый ByKey PInvoke неправильно передавал SafeRegistryHandle в IntPtr (exit1);
исправлена только диагностика. Пути/command templates/частные ссылки не выводили.

Одноразовый стенд вне Git: собственные GUID class/EXE/receipt, ShellExecuteExW
с class key, свой console sink. Лишь synthetic example.invalid HTTPS. Скрипт
создан основным агентом; процесс PowerShell использует ExecutionPolicy Bypass,
постоянную политику не меняли. Первый -File без override был отклонён политикой;
длинные encoded команды дважды дали guest-session exit255, короткие/-File
выполнялись. Не перезапускали VM, не меняли UAC/registry defaults.

Reviewer нашёл два P2, затем принял исправленные exact sources: cleanup deny
до Open/allow лишь process_complete, receipt wait Stopwatch. Unknown/exception
сохраняют keys, следующие cases не запускаются. Сам ShellExecuteEx не ограничен
process/receipt waits; whole-call timeout/cancellation не заявлены. Receipt
атомарный, хранит лишь argc/UTF-8 length/hash. Точные hashes:

| Источник | SHA-256 |
|---|---|
| NativeAssociation.cs | cd0865adf19c6fb70df7ace252bc493e01500170cebb6a66d53fab8500fecca7 |
| UriSink.cs | 8f4d58d143899eddd58463816a2ad6b90ab5b53b441b282dff62226f4c417c36 |
| Probe.ps1 после двух правок | c695f6822398c1c0439c0e5c9c5ab19e52fbfaa9a1bb5a86c3f17afd975d59fc |

Свежий последовательный NoAppPaths run exit0, fixture
`94357511696642fdba62a0e9bcc7e2a9`:4/4 sent=true/error0/process_complete=true,
args2/exact_utf8=true; owned_registry_clean=true, app_paths_use_url=false,
audio_read=false, telemost_launch=false. Root, escaped quote/query/fragment,
percent-encoded UTF-8, double-encoded value. `unicode` — ASCII URI с encoded UTF-8,
не буквальная кириллица. Старый run не подменяет текущий exact-source результат.

Отдельная read-only проверка точного fixture дала exit0: class_present=false,
app_path_present=false, sink_processes=0. Удалены лишь две свои временные
регистрации; исходники, synthetic receipts и sink оставлены вне Git. Настройки
Telemost/Parallels и данные пользователя не удалялись. Exception cleanup проверен
по source review, не отдельным fault-injection run; unknown не считается PASS.

Доказан лишь механизм передачи собственного обработчика. Не доказаны native
Telemost/HTTPS acceptance, browser recovery, установленный MSIX, auth/upload,
Record/Stop/clock. T119/T097/U1/U2 и аппаратные критерии остаются открытыми.
Research дополнен наблюдениями, bridge/plan/quickstart/checklist state не меняли.
Commit/push/PR/merge/build/install/release не выполнялись; Windows/Mac/server/
constitution/AGENTS/rootCHANGELOG code diff пустой. Проверки документов после
записи выполняются отдельно, а не предполагаются успешными заранее.

После записи PASS: check_spec_kit_governance.py, speckit-bootstrap doctor frozen,
F200/extensions YAML parse, git diff --check. Tasks SHA-256 неизменён:
`45641d615923b4c049482397e90e6ce765255b8ba7467f2d867cd4c8c7e27d50`.
Проверки относятся к текущим незакоммиченным документам, не к новой сборке/PR SHA.

## Раунд 175 — предельная фазовая коррекция, не приёмка устройства

Previous goal turn — progress: Round174 исправил проверочный cleanup и дал новый
exact-source native mechanism proof; не wait/закрытие цели. Текущая рабочая
копия/branch/HEAD99b00a579c24b50e320465b69d9a296038bc544d сохранены. Mac всё ещё
locked по актуальному CUA getApp: Telemost/UI/T097 не проверялись. No product
build/install/recording. Линия — continuing high-risk speckit-plan Phase0.
Before_plan commit hook disabled; setup-plan сохранил существующий план.
План в целом не завершён, optional agent-context hook не исполнялся.

Основной агент прочитал текущий ClockMapper и schema6 PacketStats: отказ
clock_drift возникает до normalizer. Supplementary current IAudioClock не
подменяет packet-QPC и не выключает raw checks; нормализатор сам по себе не
исправляет VM metadata refusal. Microsoft GetBuffer/GetPosition семантика
перепроверена; численной гарантии1ms от отсутствия TIMESTAMP_ERROR не заявлено.
Отдельный read-only reviewer проверяет unresolved clock design (не runtime
missing proof = автоматически spec ambiguity); его handle не перезапускали
из-за observation timeout. Итог review на момент записи отсутствует.

Новый отдельный generated-only стенд SaturationSource/SaturationProbe outsideGit.
Source — derivative прежнего NumericPhaseSource; механическая копия+3 узких
изменения: include прежнего PhaseRemainder, поле noiseTicks8000, его применение
в существующем sinusoidal noise. Прежний source00705e… не изменён. Device/API/
пользовательский звук/сеть не открываются; fixture signal zero, IdentityStage
вместо фактического AEC3. Сборка MSVC17.14.39 x64/O2/W4/WX/native Sinc libraries;
build.cmd повторяет прежнюю linkage, не новый продуктовый dependency.

Sequential VM handle24721 terminal exit0: SATURATION_BUILD_EXIT=0,
SATURATION_RUN_EXIT=0.11rates8000/8001/16000/44100/44101/47999/48000/48001/96000/
191999/192000 ×2QPCorigins =22cases. Second origin UINT64_MAX−100000000,
actual first received QPC ещё включает1375ticks. Источники physical−100/+100ppm,
fixed sourceRate/100 packets,4s each, sinusoidal metadata jitter0.8ms.

Все22cases: commands обоих Source достигли обоих знаков±500ppm,399 непрерывных
480-frame canonical blocks, zero timeline trim, close/EOS healthy, peak anchors2
у обоих. Max generated phase error0.210120289403ms. Проверка phase<=1ms —
assert исследовательского driver, не новый hardware SLA или смена raw budget.
Существующий Source сравнивает trusted outputs двух разных fillers bitwise.
Full native convolution support независимо не наблюдался в этом новом опыте;
здесь действует прежняя mirror cursor/support проверка, не новый exact-kernel
oracle. Variable packet/long/Stop/fence/owned FIFO/AEС quality этим не закрыты.

| Артефакт | SHA-256 |
|---|---|
| SaturationSource.cpp | 07c09898f006624806cf8f6ad277a5102f15a7a2986787c51743970f9b9cdb9a |
| SaturationProbe.cpp | 45c00e75004f3dfbb676878df0370cc482641d2bb9bc139cd5553fb8ca5337a1 |
| build.cmd | 53714225bd5c538fea00afbacca8b97b07317f32369b04dfce67b11fa428b995 |
| run.ps1 | ef95981fc51984f9eac3c862365463cf13d198ec2855df000b586f555da47c6f |
| result.log | 54dcac82e84732434c1c91dc8a00916b7253bf09235df0acf2d8524f1727e5cf |
| EXE reported at runtime | 317540155aad6d1f464c4f835dcaac2ca3233f9cb3dcc6f6986ce568339924b6 |

Wrapper проверяет two sources/helper before build/after build/after run; hashes
самого compiler, transitive sources/libraries/build.cmd/EXE afterrun не закреплены
этим wrapper. Не attestation воспроизводимой/герметичной сборки. Full источник
driver/Source/wrappers прочитан main; narrow independent source review queued
после gap inventory, не объявлен завершённым из намерения/timeout.

Candidate/research дополнены исследовательским покрытием; действующий §5,
thresholds, plan/data-model/tasks/checklist state не менялись. Clock design/rawVM,
T119/T097/SC003, protected implementation и полный Windows goal не приняты.
Commit/push/PR/merge/build product/install/release не выполнялись. После записи
документы проверяются отдельно; успешность проверок не предполагается заранее.

После записи PASS: governance, frozen bootstrap doctor, F200/extensions YAML,
git diff --check; tasksSHA45641d615923b4c049482397e90e6ce765255b8ba7467f2d867cd4c8c7e27d50
сохранён. Windows/Mac/server/constitution/AGENTS/rootCHANGELOG diff пустой.
Reviewer wait вернул observation timeout, не terminal: тот же handle сохранён,
новый агент/повторный стенд из-за timeout не запускались.

## Раунд 176 — native Telemost root и изолированный фазовый отказ

Рабочая копия `200-windows-followup/crisp`, branch `codex/200-windows-followup`,
HEAD `99b00a579c24b50e320465b69d9a296038bc544d` подтверждены. Предыдущий раунд
дал новый saturation proof; текущий также содержит новый эксперимент, не wait.
Mac сейчас разблокирован, прежняя причина недоступности UI более не актуальна.
Способ запуска использует прочитанные вне-Git RootAssociation.cs/LaunchRoot.ps1;
нет частных URI/участников/аудио в evidence. Исследования generated-only не
используют доступ к микрофону. Implementation/release gates сохранены.

### Открытие настоящего Windows-клиента без встречи

STA PowerShell: read-only HKCU Classes telemost + AssocQueryStringByKeyW,
проверка product/signature, ShellExecuteEx CLASSKEY/FLAG_NO_UI с фиксированным
публичным `https://telemost.yandex.ru/`. lookup_hr0, signature_validtrue,
processes_before0, senttrue, native_error0. Сам результат Shell API не является
подтверждением получения ссылки приложением. CUA затем показал домашнее окно
`Yandex Telemost`, без экрана встречи. Отдельный VerifyRoot exit0 подтвердил
process_count1/window_count1/title_matchtrue/paths_matchtrue/Valid signature.
Версия клиента2.42.4.9707. Частная ссылка, вход во встречу, камера, микрофон,
создание встречи и GRAF Record не запускались. Системные defaults/registry/UAC
не изменены. Root launcher не утверждает ограничение whole Shell call15s.

GRAF установлен0.1.0.12, package StatusOk, Respondingtrue; фактический running EXE
SHA-256 `7c4193727f2653832da23e10641c3abe2686293d802ad5dd0edddac9ffff9994`.
Это свежий fingerprint существующего приложения, не новый package build и не
сверка с архивом MSIX. T097 не закрыт: попытки переключить GRAF/открыть меню
через CUA не показали нужного состояния. Пользователю предложено вывести GRAF
на передний план; скриншоты с частными сведениями в Git не сохранялись.

| Вне-Git источник | SHA-256 |
|---|---|
| RootAssociation.cs | 4d17e614539e6254e14862c909f6f037c103446e8c9c0da1f21026d81d74ff62 |
| LaunchRoot.ps1 | 754bbc72680968e2cb8e04f270a5662ae0b304b85b1e28f727eaeb309e438b96 |
| VerifyRoot.ps1 | 1517bfc6553039db1cceba13228de1aadad91b740cc2dca9dd8d13329ae4103a |

### Не переносить короткий saturation PASS на полную quality матрицу

Первый quality variant: build0, native run2/wrapper1. Три режима pair1,1 прошли;
pair0,2 mode0 остановлен guard до quality метрики. Повтор с metadata diagnostic
дал ту же остановку: mic packet471/accepted207711/outputs226017,
innovation48.1112550067frames, step14.1744frames, stagingfalse, raw valid.
Для render maxinnovation47.6612031077frames, отказа нет. Это локализация
metadata/controller ошибки, а не доказательство зависимости от звуковых значений.
Длительность/номинальные частоты отличаются от4s/zero round175. Остальные девять
исходных quality cases не объявлены прошедшими. First failure source/log сохранены.

Скалярная модель: physicalt=t/1.0001, jitter0.0008*sin(37*t),
e=t−physicalt−jitter−c; проверка abs(e*48000)>48 ПЕРЕД c+=0.01*clamp(e,±bound).
На12s clamp500ppm: первое пересечение packet471, max49.100370534frames;
clamp1000ppm: пересечения нет, max43.371743217frames. Это приближение fixed10ms,
не native acceptance. Оно обосновало один отдельный native derivative.

Command1000Source меняет только clamp±0.0005→±0.001 и пояснение. Horizon1s,
raw guards, innovation48/step48, nominal representation floor, sample/cursor/
support/PTS/EOS не изменены. Driver использует actual CollectedAec(false),
generated speech/echo/nearvoice, четыре пары physical patterns ×три режима,
48000/44100Hz/12s/fixed packets/jitter0.8ms. Добавлены asserts generated phase<=1ms
и command<=1000ppm; прежние far20dB/near gain1dB,corr.98,lag480/DT10dB,gain3dB,
no-dropout критерии не ослаблены. Sequential session3421 terminal exit0,
BUILD_EXIT0/RUN_EXIT0,12checks/0failures. Каждая case1199 непрерывных480frames,
trim0/0; far min21.9653184635dB, near gain около−0.504dB/corr≥.999759715267,
lag434frames; DT min26.2414723108dB/abs gain≤1.462947dB/no-dropout.
Maxinnovation43.4240781482frames, maxgenerated phase0.122485933618ms,
peakcommand904.668294754ppm: saturation нового1000ppm НЕ достигнут.

| Вне-Git исследовательский артефакт | SHA-256 |
|---|---|
| Original first-failure source | 755c24dcd6ba5e09d0b0908e2a93cdfa6a6077c9e8ca4fe6c1df86fef8fae6f5 |
| Original first-failure log | 8cac5fc9a22cc90a0aa02ca2d282079d729c76821bdf97c398e45213c3f05623 |
| SaturationQuality diagnostic source | ca15f5090bd7c0007ba01322f9e742a2b711490b85a88ddcbe7067bcef0e6379 |
| Diagnostic log | f5adea59aa8b62c36999dd8115c047fc5ef0ddf17ba5a04e09a94ace53a25d79 |
| Diagnostic EXE reported | 4b0f515f0c0e127a91842bd7a79abe1a8233446b981252d5c73cbd4973f90ea9 |
| Command1000Source.cpp | 53a8d96cff032d404b9f488a76d95bbe430af6a8fb85410c49f8cb581a64f4f8 |
| Command1000Quality.cpp | c079fa5a1e17434c3749987ebe447059abbdaba924c5638d3fe27228f44c4804 |
| command1000-build.cmd | 4cf070435f9c2d97cd5da4b4c99fb04f89ca85d2b4c6b9344e08e820ca913ed5 |
| command1000-run.ps1 | c53ccf38ce57e030826e0c21efe86e00c8040ab86c4c2e353adce7090b201ad3 |
| command1000-result.log | a2fa3c088db8d253e010d1470971c26d40d83426463b3ca3754c0e2a7643f0dd |
| Command1000Quality EXE reported | b3ee8021f83f56df0ee0dd39d255d816d488d8e5a1723cb488322763f90e275a |

Source/helper hashes checked before/after build/run; transitive sources/libraries/
compiler and after-run EXE не полностью закреплены wrapper. Не hermetic build
attestation. Source review22-case round175 узко Approved и четыре design gap
возвращены тем же reviewer: PTS/guard semantics, dynamic partition independence,
owned FIFO, разрешённый хвост принятого входа перед EOS/Stop. Новый derivative
не разрешён в production одним quality PASS; отдельные отказные проверки и review
ещё ожидаются на момент записи. RawVM clock_drift, §5, SC003, T119/T097 и общий
Windows goal не закрыты. tasks state не менялось; build/install/commit/push/PR/
merge/release продукта не выполнялись.

### Последующий source review и повторные отказные проверки

Тот же независимый reviewer прочитал source/helper/wrappers и готовый quality
log, повторно подтвердил hashes: узко Approved, без обязательных P1/P2 правок.
Подтверждены порядок guards до команды/admission, положительность шага и
сохранённый terminal state. Reviewer не выполнял VM/EXE. Комментарий
`noiseTicks` в новом derivative ещё описывает исходный±500ppm saturation опыт;
он не является утверждением достижения±1000ppm. Frozen source не менялся
после проверки, чтобы не подменить fingerprints новым комментарием.

Sequential session29391 terminal0: negative BUILD_EXIT0/RUN_EXIT0. Driver
переиспользует NumericPhaseNegative с новым Source и явно сохраняет прежнюю
amplitude4000ticks для variable-packet fixtures. Это НЕ variable-packet0.8ms
приёмка.13 healthy cases (11rates плюс1-frame8000/192000) дали199blocks каждый,
healthy close и trim0/0. Шесть generated8ms jump cases сохранённо отказали при
здоровом raw mapper; adjacent79.9968frames отказал по step при innovation40.3717
<48. Два повторных вызова после отказа не принимают/не публикуют данные и не
меняют проверяемые счётчики/cursor. Backlog94admit сохранил accepted480/supplied0,
нулевой выход и terminal staging refusal. Всего13 healthy+6jump+1adjacent+1backlog;
не production FIFO, не реальный capture Stop/dispatcher fence.

| Вне-Git отказная проверка | SHA-256 |
|---|---|
| Command1000Negative.cpp | 080fcbd6bdce0e5648d841423a4063cc139075bec29d527c99976a4d1af55512 |
| command1000-negative-build.cmd | 241cffd3dcdd9e935d87408cc4d9b801290317332a9c2b906d41cea5d70806ee |
| command1000-negative-run.ps1 | 020446b1713142574beb1accd2aa5525dad55ed66c01eda0ebe0dbbeca61049f |
| command1000-negative-result.log | 6ea4d4a5d2026042f9a036066fb74576f08ff97b137e5f3a1d6a673ba65233c6 |
| EXE reported before run | 8ccd93737c25e127617dc488740e419c98febb8525c3c0df60b95522caa679fb |

Source-review и новый отказный run дополняют, не отменяют четыре design gap и
отдельный upstream rawVM clock_drift. Новый actuator command ещё не принят в
нормативном §5. Governance passed после первых записей; заключительные проверки
после этого дополнения выполняются отдельно.

## Раунд 177 — один час generated native Sinc/AEC3, не SC-003

Source Command1000 из round176 не менялся. Новый streaming driver генерирует
синусы на запрос callback, не читает устройства/файлы и не сохраняет звук.
3600s,48000/44100Hz,physical−100/+100ppm,jitter0.8ms,fixed≈10ms packets;
разные начальные QPC/device origins, timeline maxBufferedFrames4800. Actual
native AEC3 вызывается на каждую480-пару; его выход проверяется finite, не
сохраняется. Два EOS filler и native cursor/full-support проверки наследуются
из Source. Это не фактический owned FIFO в product controller.

Первый build завершился2 до запуска: Windows `near/far` macros повредили
импортируемый MacReference при раннем включении windows.h. Исправлен только
порядок include в driver: frozen source прежде Windows headers. Это ошибка
исследовательской сборки, не продукта; source/helper не менялись.

Sequential session83392 завершилась0, BUILD_EXIT0/RUN_EXIT0. LONG_PASS:
359999blocks,3599.99s, непрерывные PTS, AEC calls==processedFrames==blocks,
trim0/0, duration difference9.99999999976ms; render RMS difference
0.0000337739347921dB относительно аналитического0.2/sqrt(2), не Mac baseline.
maxphase0.121478866276/0.122555449707ms; maxinnovation43.3810220661/
43.4359796116frames; peakcommand903.771293044/904.916241908ppm — новый1000ppm
предел не достигнут. peak unread512/504, anchors2/2; sampled peak working set
14905344bytes/private11210752bytes, wall339.346573417s. Snapshots начальный,
каждые60000blocks и финальный; это не непрерывный peak monitor/CPU measurement.

| Вне-Git артефакт (`f200-phase-saturation.XSjeTP`) | SHA-256 |
|---|---|
| Command1000Source.cpp | 53a8d96cff032d404b9f488a76d95bbe430af6a8fb85410c49f8cb581a64f4f8 |
| Command1000Long.cpp | 6edaa06ea1a7093a0e662a90c76ea74139ede5faf0afc0bb6897e7002d76709d |
| command1000-long-build.cmd | 0d71b3f4892995e3402865cea11beefebb31d1664af6b078bdc174f2e52e74d3 |
| command1000-long-run.ps1 | bbc64b964c0d3916a98fcfccc754370a0d25bff3e1f08a48853e60204bb60ea9 |
| command1000-long-result.log | b8a0498d22d64d03ea1d1d7a620a83a5f3c42dc32943123671f8f3a87b592985 |
| EXE reported before run | 77bd58765010abd267d00acc193c6aaf2d92e6d5caa7e0da13202260a2451713 |

Wrapper проверяет source/driver/PhaseRemainder fingerprints перед/после build/run,
но не все transitive sources/libs/compiler и не after-run EXE: не hermetic
attestation. Один generated run не закрывает SC-003, hardware matrix, реальные
WASAPI clock_drift, supported format/route cases, Stop5s/dispatcher fence,
WAV/M4A, storage или T097. Независимое review нового driver ожидается. Никаких
product build/install/commit/push/PR/merge/release в этом раунде не выполнялось.

Последующий независимый read-only review полностью прочитал Long/source/
wrappers/log и связанные Sinc/timeline/AEC paths: узко Approved, новых
mandatory P1/P2 нет; reviewer VM/EXE не запускал. Подтверждены admission refusal
до LONG_PASS, actual native AEC/call accounting, отсутствие hour-long массива
или сохранения звука. Важно: отдельного независимого эталона точного полного
dynamic хвоста здесь нет; duration<=100ms assertion могла бы пропустить потерю
пригодного блока. Фактической потери review не обнаружил. Длинный driver не
меряет far/near/double-talk качество; результаты round176 остаются отдельными.

## Раунд 178 — packet-partition failure при continuous physical drift

Driver переиспользует FullPrefixPartitionProbe flow с неизменным Command1000.
Сигнал0.25*sin(700Hz)+0.1*sin(1900Hz),0.5s,44100/48000Hz, physical patterns0/1/2
(−100/nominal/+100ppm), metadataNoise=false. Два одинаковых источника с разными
device origins; first QPC общий. Baseline fixed≈10ms против variable input
{1,479,31,4800,480,7,1024,211} и one-frame input; full-support taps сравниваются
до timeline correction. IdentityStage вместо AEC, timeline recovery0.
Контроль sampleStart/count/generated/tap equality и common block accounting;
frozen Source содержит actual native cursor/dual-filler checks. Удалена только
номинальная rational range assertion, неприменимая к dynamic ratio: независимой
проверки полноты dynamic диапазона этот driver не обещает.

Sequential session53425: build0, native1/wrapper1;24cases/8FAIL. Все12comparisons
controller=false и4 nominal controller=true PASS/maxerror0. Controller=true
physical−100/+100ppm FAIL8: одинаковые starts/count/generated в каждой паре,
но maxerror0.000355431810021…0.00257591158152 > прежнего0.00001.
Исходный driver менял также drain limits480/479/1, поэтому одного этого прогона
недостаточно для изоляции input partition. Отдельный frozen derivative заменил
только drain на480 для всех вариантов и добавил соответствующий output label.
Sequential session95087: build0/native1/wrapper1; те же24cases/8FAIL и точные
печатные ошибки. В этой fixture output caller limit не необходим для отказа;
sampling/admission cadence metadata и per-packet controller остаются причиной
различий в исследованном пути. Это не live WASAPI/VM causal diagnosis.

| Вне-Git артефакт (`f200-phase-saturation.XSjeTP`) | SHA-256 |
|---|---|
| Command1000Partition.cpp | b0ec44fc05b7ceddde705106cbef44cc72f04552a62d3c9bfcacfb900dd28232 |
| command1000-partition-build.cmd | c61ea3c0c23416aa48e0b52fca805fac2c2039563c9a12ece5f1ac5eea8eca6a |
| command1000-partition-run.ps1 | a35bfad2eb49741854dd1ab87088d77747d4497358cd3768116e5b32b2994230 |
| command1000-partition-result.log | e3ba4508a5d98516728d422bfed9415bf90f01064983c0d42d4c2f3119b9b555 |
| Partition EXE reported | 414e05eb88d43cff7d585d878197066fe5c73a3234d7df97cf433f2831344efb |
| Command1000PartitionFixedDrain.cpp | 9f4b859233906588775112b610655fd972c46791558cd6d559bc10f6437cfd92 |
| command1000-partition-fixed-build.cmd | c1645a6b21eafac23008872b3201de354d7428a79c076d60acebc61ac314e40e |
| command1000-partition-fixed-run.ps1 | 99bd17a409f1ecd5588389b05c8a035b59a3ab609710eb66004c687f321b5d06 |
| command1000-partition-fixed-result.log | 91215e6399112657046c6ac2044869504f8cdc21d90b254d6581497b9c82cf1a |
| Fixed-drain EXE reported | a6adf8dff2df741b2f89da51f9829a9e59caef68892bfc74866142fce8385db7 |

Source/helper fingerprints сохранены runner до/после build/run; ограничения
transitive inputs/toolchain/after-run EXE те же, что round177. Новые source/log
вне Git, звук не читается/не сохраняется. Порог/норма §5 не изменены. Нужен
новый cadence/metadata/EOS design и независимое review, не повтор прежнего
quality/long PASS. Память/форматы/Stop5s/live/hardware/SC-003 не закрыты.
CUA свежая попытка чтения Windows вернула locked Mac: T097 не проверен.
Tasks/checklist state не менялись; product source diff по-прежнему отсутствует.

Независимое read-only FIFO/Stop design review прочитало actual controller/
worker/AudioNormalizer/timeline/candidate. Предложено worker-owned размещение
и закрытие нового input до drain принятого input, затем producer completion
обоих sources до двухEOS. Candidate contract сохраняет конкретный layout и
reservations как НЕ принятые: численный maximum output/tail proof ещё нужен.
Preparation/recorded split и tail после fault новой метки отдельно открыты.
Это проектный результат, не проверка production order или новый §5.

Последующий независимый read-only source review двух partition drivers/logs:
узко Approved, новых mandatory P1/P2 нет, hashes подтверждены. Одинаковые
signal/count/physicalTime/firstQPC модели подтверждены; меняются только точки
наблюдения metadata и частота команды. FixedDrain сохраняет восемь FAIL и
ошибки. Роль QPC rounding отдельно от update/hold cadence не изолирована:
no-jitter не значит отсутствие округления до100ns. Reviewer уточнил прежнюю
output-capacity оценку: связь числителя/запаса с actual pinned cursor пока
не доказана; гарантированная достаточность семи reserved slots не заявляется.
Review не выполнял VM/EXE и не менял файлы. Общий design/analyze остаётся открыт.

## Раунд 179 — numeric grid и offline native варианты не завершили исправление

GridMetadata строит реальные rounded n/QPC наблюдения той же generated модели,
проверяет каждое existing ClockMapper и интерполирует соседние опоры после
integer subtraction origin. Не добавляет EOS endpoint.11rates8–192k,
patterns−100/0/+100ppm,0.5s, дваorigins (обычный/nearUINT64_MAX), fixed/variable/
one-frame input. Общий интервал заканчивается последней доступной опорой всех
вариантов; это не full-tail acceptance. Sequential4286 terminal0/build0/run0:
66cases/2676grid points, maxtruth0.5tick/maxpartition0.954142782837tick;
assert.500001/1.000001 учитывает arithmetic representation, не capture allowance.
Нет waveform, nonlinear clock/jitter, device/Stop/FIFO/performance proof.

GridPartition переносит команду на480generated-output cells. Parent Source
admit controlled=false подавляет только новую packet-command; raw/innovation/
adjacent/staging guards остаются, прежний ratio восстанавливается. Grid guard48,
clamp1000 и one-tick floor сохранены. Metadata PRELOADED, правый anchor может
быть ещё не принят parent; весь ряд отдельно проходит raw mapper, но это не
причинная live доступность. Known end удерживает command на последних4800input
frames; Source tail drain сохраняется. Это не live Stop/full-range proof.
Первый compile2 до запуска: nested main macro в frozen Source погасил внешний
main rename. Helper извлечён из GridMetadata без driver/main, старый checker
не менялся. Узкое read-only review helper/wrapper/driver Approved, новых P1/P2
нет; reviewer подтвердил guards и не запускал VM/EXE/не принимал §5.

Sequential76062 build0/native1/wrapper1:24cases/1FAIL —48000/+100ppm/variable,
maxerror0.0000239759683609>старого0.00001. Остальные23comparisons PASS/error0;
start/count/generated совпали. GridFractional отдельно сохранил fractional
interpolated QPC: floor целой части в helper feedback, затем вычел
fraction*rate/1e7; без второго llround. Sequential62560 build0/native1/wrapper1:
24cases/4FAIL, variable physical±100 на обеих частотах, maxerror0.0000364556908607.
One-frame сравнения и nominal/uncontrolled имеютerror0. Этот successor не
считается исправлением, несмотря на обоснованное сохранение дробной точности.

| Вне-Git артефакт (`f200-phase-saturation.XSjeTP`) | SHA-256 |
|---|---|
| GridMetadata.cpp | 2fd2e0ac05de513fdf7314c3d1c6cfa151b0bd6f58fbe9a57ddf13eb6c02eaf0 |
| grid-metadata-build.cmd | 064931b718c5662b982700c54164c73f400d5c4edb6e772fac93d554c8d15446 |
| grid-metadata-run.ps1 | 9a4b86b81f1b8fe7ff5cade03de23a832660478597132410c81fc3be5a4820df |
| grid-metadata-result.log | c135c597af7eb6089b8ab7cf4f26faffb509e8fe856dc6662734ad77ba901b44 |
| Metadata EXE reported | a6740011b6284ed630ef91c93eb0ba3473385de10d37c5b8600e6a231f1130cf |
| GridMetadataFunctions.h | b5da9eef6e3ac90e8ffb66cfebb604815fd0caeca00285ee05f6124d98036dcd |
| GridPartition.cpp | fc098a18908d9280e01a6cebf3e8e1837f832ef5dfbec54e489f15b88f702499 |
| grid-partition-build.cmd | aba4ee20ef44d7004d035ec931bf402ab08894c4d20c314e5510bef4fa2b9bd8 |
| grid-partition-run.ps1 | e44dc60ff728fc6e8c76aadc1d5cf249d2ffa7f759ab5c84e6e61b2628a6d729 |
| grid-partition-result.log | 83ccebcc40c7330043aadfe32bd82412754d0048dd06539a609f1c0c0656e77d |
| Grid EXE reported | f6c7d789964b2f40db80c8afc7380e1f2000e9f2dda649e94f8cf9678a4d80e1 |
| GridFractional.cpp | de82e0b58b84f5ab057bd9086cb014d12e3e4a5e628a41f55a7807b2282c3c1e |
| grid-fractional-build.cmd | 62eebcc4523d3af1f8793265c6b0d1bf3f647fc9ddd141812543fd0a9104242f |
| grid-fractional-run.ps1 | a248093ef2dd9b9906923261a391d2c49fdca8f5a5e8f9cbfadc1083a5897e06 |
| grid-fractional-result.log | d781e6ada117ffcc672a8c3eb1c506fb0f93cfba643aecb7e82abd327859b4c5 |
| Fractional EXE reported | 27d7844f45f974dd49324db7f324b7f140787c7e423a04e0167d1e70648ed385 |

## Раунд 180 — точные integer QPC устраняют неоднозначность quantization

Независимое чтение нормативного §5 не нашло nominal-only исключения. Mac-path
использует CMSampleBuffer PTS, не callback time; его drift и partition tests
проверяют эти свойства раздельно, готового fixed-grid metadata helper нет.
Чтобы не считать округлённые метки буквально точными, создан только fixture
profile42: declared48001Hz/physical48000Hz, около−20.833ppm, QPC=n*625/3.
Fixed packets480, variable{3,477,30,4800,480,6,1023,210}, small3frames делают
все packet starts кратными3. Source/helper asserts подтверждают noise0 и
time==integerQPC для каждой опоры. Ни runtime clock guard, ни tolerance не
изменены. ExactGridSource отличается от Source53a8 только generator-profile,
разрешёнными кратными3 partitions/assert; signal/count одинаковы в сравнениях.

Sequential94810 exactpacket:build0/native1/wrapper1;4comparisons/2FAIL с
controller=true: variableerror0.000456225126982/smallerror0.0000797919929028.
Uncontrolled2comparisons PASS/error0. Sequential45734 exactgridfractional:
build0/run0/terminal0,4comparisons PASS/error0. В каждой паре start4800023,
samples23969/generated23985. Поэтому quantization не необходима для old
packet-command waveform дефекта; fixedgrid устраняет его в этой точной fixture.
Это НЕ исправление rounded cases round179, не general waveform/quality proof,
не live admission/Stop/SC-003 и не изменение установленного Windows клиента.

| Вне-Git артефакт | SHA-256 |
|---|---|
| ExactGridSource.cpp | b6f4f768bee63a919a7eb61c36010893c44d8b6fa6fe74742dabb7c7a06467ea |
| ExactGridMetadata.h | 24ebdcaf414fc7561254d4c024569ec36ad9498042582fce9db83ac3bde1ea26 |
| ExactPacketPartition.cpp | 5a15eb8f31e217d6845f6efcdbb5f8f0977f08ee46e364fdac4d99b147819bf6 |
| ExactGridPartition.cpp | f05a973368df4f9066cec60958ddaf5eefdf1e1ff9f73b4f62065c66ec301794 |
| exact-packet-build.cmd | a4211e27f3df5add66aaddb1a27d40ee5cd722aabe02202558dd9680908421e2 |
| exact-packet-run.ps1 | 3f5cc170d84036ce9e85622d085687e9273da62dddee1dc3a09c7acd8275999c |
| exact-packet-result.log | 06c106e764f465283f154ebe7a593cae331ef2e55a25d3c8ea1951e77ed4e6da |
| Packet EXE reported | 94f6f89629b21f9a9ed087bbf3769ccb73a026310dbebc98afaa1d85fc53227c |
| exact-grid-build.cmd | 12ae2741b04bccdf80360ee1f30ce058cc4d55e58a191df8cad2ef5707653c8b |
| exact-grid-run.ps1 | 7cee2efa180e5851a8c459116692b510ea8bc0bb050e880e3816ae9370eab2be |
| exact-grid-result.log | 897fe330f937039628955e6d432c8c3eab4743ac291512d227b3dfe4a12a6bab |
| Grid EXE reported | d016fe06b5634f31bc3d0224a2e7fb91a5f0589754b8a1d1e3b683a270a2dd73 |

Source/header/driver/helper hashes checked before/after build/run, transitive
toolchain/libs/after-run EXE не полностью закреплены. Imported ClockMapper.cpp
сверен cmp с текущим product: SHA3a2e325a72542070e670c0446ad42694f0951a0f0915aec0b39af20a4d555827.
IdentityStage, не AEC quality. Звук пользователя не читается/не сохраняется;
старые source/failure logs сохранены. Reviewer точной fixture ожидается.
§5/checklist/task state не изменены; product source/build/install/commit/push/
PR/merge/release не менялись. Следующий gate — causal/bounded grid design и
неопределённость rounded metadata, не повтор уже доказанного старого отказа.

Последующий независимый source review Approved в узкой диагностической области,
новых mandatory P1/P2 нет. Подтверждены точный profile42, count24000/кратные3
packet starts, неизменные guards/Sinc и корректные знак/масштаб fractional
feedback. Для grid точек j=480k<48000 virtual n=j тоже кратен3: идеальная
интерполированная QPC целая. Поэтому PASS exactgrid НЕ является стресс-тестом
ненулевой fraction. Reviewer VM/EXE/log не проверял и whole-model acceptance
не давал; terminal results получены основным агентом отдельно. Tasks/checklist
сохраняют прежнее состояние, исходный VM clock_drift остаётся незакрытым.

## Раунд 181 — причинная сетка, фактически скопированный ограниченный вход

2026-10-02, high-risk Phase0, HEAD99b00a579c24b50e320465b69d9a296038bc544d.
Рабочая копия200-windows-followup существует и зарегистрирована Git; пользователь
не обязан её переносить. Ambient0309 не использован для записи. Продуктовый
код, нормативный §5, spec/tasks/checklist marks и установленный пакет не меняются.

Внешний CausalSource повторяет ExactGridSource и сохраняет actual ClockMapper,
raw/adjacent/innovation guards, native Sinc/cursor и два разных EOS заполнителя.
Единственные изменения механизма: input копируется при admission в fixed
16384-float ring каждого Sinc, Run читает уже owned samples; pre-admission
capacity refusal запрещает overwrite unread. Source anchor ring тоже16384.
Это новый исследовательский capacity, **не** утверждение прежнего4864 bound.
CausalGrid хранит только фактически принятые packet-start n/QPC в отдельном
16384-point ring. В открытом потоке output cell480 ждёт latest received n>=
virtual n+4800; после фактического EOS держит последнюю команду на конечном
4800-input span. Контроллер не preload-ит metadata и не читает producer count
до EOS. Правая опора — полученная, не прогноз или endpoint из generator.
Это fixture EOS после последней admission, **не** живой UI Stop/fence protocol.

Первый build0/run−1073741571 (`0xc00000fd`) переполнил Windows stack из-за
крупных фиксированных Source/Grid objects в execute. Driver сохранён как
CausalGridStack.cpp; heap placement через существующий std::make_unique
устранил stack overflow без увеличения stack limit, input capacity или clocks
tolerance. Initial EXE reported4fa81544b7cbbfce4d753b2cd3f200e0d533566e594501b7d30a81f91884aa72;
этот отрицательный запуск не принимается как аудиопроверка. Повтор58396:
build0/native0/wrapper0,4/4 exact-profile comparisons PASS/error0 при прежнем
0.00001. Start4800023/samples23969/generated23985 одинаковы во всех partitions.
Owned peak9875/metadata peak1761 при cap16384; это measured maxima fixture,
не доказанный worst-case production bound или delay/readiness budget.

Независимый read-only reviewer Approved source в узкой диагностической области:
received-only projection, кольца не перезаписывают непрочитанное, EOS tail
не берётся из будущего, heap delta не меняет алгоритм. Reviewer не запускал
VM/EXE и независимо не проверял результаты native-прогонов; terminal evidence
основного агента отдельно. Статический разбор EXE для причины stackoverflow
не является независимым выполнением звукового теста.
Dual EOS equality/full-kernel checks сохраняются, но независимая полнота
динамического выходного диапазона ими не доказана. IdentityStage, не AEC3
quality; нет пользовательского звука, writers, recording/upload/install.

## Раунд 182 — причинный вариант на округлённых метках: 11 отказов сохранены

Последовательный native run26896 расширяет только driver matrix:
11rates8000/8001/16000/44100/44101/47999/48000/48001/96000/191999/192000Hz,
physical−100/0/+100ppm,0.5s, fixed/variable/one-frame packets,
controlled=false/true. Source и алгоритм181 неизменны, jitter выключен;
QPC округляется до100ns. Build0/native1/wrapper1, DONE132comparisons/11FAIL
по прежнему waveform tolerance0.00001;121comparisons PASS. Все11FAIL —
controller=true/variable partitions, maxerror0.0000436156988144 при44101/+100ppm.
Ошибок raw mapper/staging/innovation/kernel/paired timeline в выполненном
проходе нет; это не отменяет11 waveform FAIL. Peaksowned9880/metadata6721,
ни один не достиг cap16384. На8000/8001Hz0.5s<4800frames, поэтому только EOS
hold-tail, активное grid управление этими low-rate cases не упражняется.
Начальный UTF16LE BOM удалён только при чтении/подсчёте журналов:132 строки,
11FAIL; journal bytes не переписаны. Source/delta review Approved diagnostic
scope, не live/global algorithm acceptance.

Scoped требования уточнены чтением §5, FR-009/018, SC-003, T094/096 и audio
checklist: точная непрерывная неноминальная шкала входит в partition invariant;
отдельного универсального equality0.00001 для любых различающихся noisy
наблюдений §5 не устанавливает. Это **не** выводит округление из покрытия:
существующий nominal44100 partition test с llround сохраняется; rounded±100ppm,
jitter, качество AEC и SC-003 обязательны. Исторические179/182FAIL не становятся
PASS, raw100ppm+1ms+frame не является quality proof, research innovation48 не
заменяет действующее timeline±48 правило. Reviewer conditional Approved для
такого разделения; продуктового вопроса не обнаружено, numerical uncertainty
model остаётся задачей плана. Нормативный контракт и checkbox state не правились.

## Раунд 183 — точные пакетные метки, дробная проекция на трёх секундах

Run15080: CausalFraction меняет только duration0.5→3s и добавляет счётчик
ненулевой qFraction/assert на его упражнение. Profile42/physical48000Hz/
declared48001Hz, exact integer packet-start QPC и все прежние guards сохранены.
После1s virtual n на output480grid не всегда кратен3; интерполированная метка
уже дробная, хотя пакетные QPC точные. Build0/native0/wrapper0,4/4comparisons
PASS/error0 при0.00001. Controlled cases:190 fractional cells/источник,
start4800023/samples143968/generated143984; uncontrolled samples143966/generated
143982. Пары сравниваются только внутри одинакового control mode; разные
длительности modes не объявлены равными. Owned peak10045/metadata1762,cap16384.
Это упражняет ненулевую дробь и bounded causal dataflow, не general precision,
unknown user Stop, independent completeness, AEC quality или 60min SC-003.
Отдельное source delta review ожидается; результаты VM получены основным агентом.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalSource.cpp | 1609a588808369308e90e5a5abc66130a3d80ca02e70a4bb6397c71c257a3070 |
| CausalGridStack.cpp (initial failure) | e33dcbab1be085c6926e659a8b637ee2b4e29f53ab06e0e6fd9a6f3531f9c059 |
| CausalGrid.cpp | ad380540ac198f6cd6c855e05cd8540760395c709235442a9e6b9a9979792fe0 |
| causal-grid-build.cmd | 86ee4d43ea4ad1e9d1f0955b00b7c6edf719b73a690cb149a6883fe60af44820 |
| causal-grid-run.ps1 | 2dc6639656db43d0044c7e616a5799015d8515dd2e73cbb800933898cbeeb6f3 |
| causal-grid-result.log | a01097ad4fd0b60b2bebfc36ed171861340dd4402a52614e3d0a646e50cb37ee |
| CausalGrid.exe | 230bc8ad6e2efdf2ccba7100996932cd1a8af67d64b0b9df654ad15146f2653f |
| CausalRange.cpp | c759b02f534b055044db2fcd864334192e3d97eecdffd72e1f8edb88df969482 |
| causal-range-build.cmd | 9ed3aa043238d09f009cc23ae92b01e17cb2090e3231df6f88bf372dd908f63f |
| causal-range-run.ps1 | f2e38b78137e258c9543c27c52dbb21ca3e9c3915513afdea29be156a4f6477e |
| causal-range-result.log | e11b20338fdc080e34bfaa830191a723bd129dd0e75570aa24989fc7d099bba6 |
| CausalRange.exe | 2ad9caf05d2a3b5c69ca4a9b27ccd362477db6105fab4cd8c646660e452b3d9c |
| CausalFraction.cpp | 0eb1ce29bae856913ef2b3b9a25b5dd3afd8bf45b3e12346705e403a6b53cf59 |
| causal-fraction-build.cmd | fefb520381cc07c8349b05ef4e8bb2e49de15a0532796e3ce60202174094177b |
| causal-fraction-run.ps1 | 4c54596d84e550a97142ce43ff1e20a316205d1f67b222ed9b76c60dbf33a4a6 |
| causal-fraction-result.log | a12038b871abec93b835d5849010082a5cd269f247ba3812ac8f68485308a792 |
| CausalFraction.exe | 5a329f916d05b25310d276a8b8475f7b209c419bbbaeb189be31f7ee69ce747a |

Wrappers сверяют source/driver/PhaseRemainder inputs before/after build/run;
EXE SHA reported before run/current local bytes совпадает. Все transitive
imports/compiler/libs и after-run EXE не закреплены hermetic attestation.
Новых recording permissions/devices/UI действий нет. T094–T097/Phase0 остаются
открытыми; apps source/build/install/commit/push/PR/merge/release не меняются.

Последующий независимый read-only delta review183 Approved diagnostic scope,
mandatory P1/P2 нет. При j48000 virtualn48001, его относительная QPC10000208⅓
ticks; новая ячейка ещё вне EOS hold-tail. Reviewer подтвердил использование
fraction в feedback, корректность парных counters/assert и неизменность source/
tolerance. QPC_quantization=false означает точные **пакетные** метки, не отсутствие
дробей/арифметической погрешности внутри расчёта. Counter190 доказывает покрытие
ветви, не самостоятельную численную правильность и не чувствительность проверки
к удалению fraction. VM/EXE/log reviewer не запускал; исходный Stop/clock/quality
gate этим source review не закрыт.

## Раунд 184 — открытый ключ ассоциации не закрепляет прежнего получателя

Внешний стенд KeyMutation меняет только собственный уникальный HKCU class.
Первый AssocQueryStringByKeyW разрешает собственный процесс A. Пока исходный
read-only handle остаётся открытым, команда этого же ключа заменяется на B.
ShellExecuteExW с SEE_MASK_CLASSKEY получает удерживаемый handle и синтетический
example.invalid URI, не реальную встречу. Run98116 terminal0/KEY_MUTATION_EXIT=0:
initial_lookup_a=true, held_key_lookup_b=true, sent=true/native_error=0,
process_complete=true, receiver_b=true, receipt_a_absent=true, exact_utf8=true.
Квитанция проверяет два аргумента, byte count и SHA-256 URI; receiver различается
по суффиксу имени собственного процесса, не по доверенной подписи приложения.

Это контрпример достаточности предварительного lookup + handle lifetime как
закрепления получателя. Он не измеряет конкурентную гонку и не доказывает атаку
на пользователя. Собственный registry key удалён только после завершения
процесса; отдельный read-only run44969 terminal0 подтвердил owned_key_absent=true
и owned_process_count=0. Временные файлы сохранены. Пользовательские defaults,
Telemost, реальные URI/встречи, микрофон, записи и настройки не изменялись.
Fixture сама не делает network calls; это не отдельная трассировка всей ОС.
Пять секунд ограничивают ожидание процесса и квитанции, не ShellExecuteExW.

Независимый source review Approved в узкой области опыта, P1/P2 нет. Reviewer
не запускал VM/EXE; native evidence получено основным агентом. Предыдущие174/176
PASS остаются прежними узкими доказательствами передачи URI/открытия home,
не actual meeting Join или pinning. T119/U1 не закрыты, договор моста не изменён.

| Вне-Git артефакт | SHA-256 |
|---|---|
| KeyMutation.ps1 | e46bc96da5dfdd19b79556359b469e466abe4767f07d21515787a4ce40a0ba40 |
| ReceiverSink.cs | 6d8dc552d7d8ea9514a9c23f7e2edacac0870a66d24d2ff33d62a9fd5aeb07e0 |
| NativeAssociation.cs | cd0865adf19c6fb70df7ace252bc493e01500170cebb6a66d53fab8500fecca7 |
| key-mutation-run.ps1 | 2b941626270baf9b13956ad95e6165b2ec8e7c54bcf0c78f259590d357ecc6b2 |
| key-mutation-result.log | db46a0bb5782de03bb7b66f4ac0d2d69046838eeb3ccae5ad4cf890809225bb1 |
| verify-key-mutation.ps1 | 76a178ada3d148bc9ce11cb09a69cb8ad5156d28ed41c1f297f693f3b909b605 |

Wrapper проверяет три исходных файла до/после; generated EXE/compiler и полный
dependency graph не закреплены. Опыт не является приёмкой product launcher.

## Раунд 185 — причинная сетка с настоящим AEC3, фиксированные пакеты

Run94785 terminal0/build0/native0/wrapper0. CausalQuality повторно использует
Command1000Quality fixtures/formulas/thresholds, но Source/Grid лежат на heap,
admission использует admitWithHeldCommand, output — drainOnGrid. CausalGridLibrary
отличается от frozen CausalGrid только условием компиляции main; прежний source
не переписан. Данные генерируются и реально копируются в owned rings; received
grid без предзагрузки меток. CollectedAec(false) вызывает настоящий pinned AEC3.

12/12 проверок PASS: четыре прежние пары physical patterns, render48000Hz/
mic44100Hz,12s/case, rounded metadata с0.8ms noise, fixed packets, три режима
echo-only/near-only/double-talk. Echo-only reduction21.980963–22.007848dB
(норма>=20), double-talk27.014941–30.986039dB (>=10), near correlation>=0.9997597,
gain около−0.50405dB, lag434samples (нормы>=.98/<=1dB/<=480). Double-talk near
gain−1.469224…−1.346061dB (<=3), dropout=false. Генераторная phase по зеркальному
NativeCursor<=0.142306ms (прежняя<=1ms), command<=903.773ppm (<=1000), innovation<=43.382
frames research guard; это не замена нормативного timeline допуска.1199 blocks/
case, firstPTS4800196, trims0/0, owned peak5324/metadata13/cap16384.

Это первый quality proof именно causal grid, не повтор старого packet controller.
Пока fixed packets only: waveform comparisons11/132FAIL и historical179 остаются
FAIL; quality не переводит их в PASS и не доказывает uncertainty model. Нет
живого захвата, independent dynamic completeness, production FIFO/Stop/writer,
SC-003/installed acceptance. Source review этого delta запрошен отдельно.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalQuality.cpp | d3b78e9b754d09a86e1847bd1d5da69d728dfea0e6bd5651290dd2cfe877ea84 |
| CausalGridLibrary.cpp | 7b7d45f23aed768365bd8524a4342f0db5a08010c6819d42009721bfafe8ceff |
| causal-quality-build.cmd | f1c95873b0723720b8d392c2754a77becc58e31bc1c9947cb98260f984fe2f4e |
| causal-quality-run.ps1 | 4c21e6581b5bcecb4edb3d1b801c1cb50974a75979f02460ea98004759f114c3 |
| causal-quality-result.log | 3160a291c670f1af46435aeee2f4e999de59b5edca1be96315248cdb096fd3ff |
| CausalQuality.exe | 773b42ed9b12699de01cb4064aee7c65fda50c4fbd0cfda234892c6df3414f04 |

Wrapper проверяет пять inputs before/after, EXE hash выведен перед run/current
bytes совпадают; full transitive/compiler/library attestation не заявляется.
Приложение и task checkboxes не менялись, Phase0 продолжается.

Независимый read-only source delta review Approved только для quality driver,
P1/P2 нет; reviewer VM/EXE не запускал. Near-only raw/clean уже после Sinc:
общая ошибка до AEC может не выявиться. Physical generator time не передаётся
контроллеру, но NativeCursor — зеркало, не независимое измерение реальной
дробной позиции Sinc. Trims0/0 здесь наблюдение, не assert: default timeline
clockRecoveryFrames=48 сохранён. Нельзя назвать этот PASS запретом любой
коррекции timeline либо independent physical oracle proof.

## Раунд 186 — переменные пакеты: отказ noise и отдельный clean quality PASS

Run4786 build0/native2/wrapper1 завершился на первом mode0/patterns1,1,
до quality verdict. Source render accepted5798/output1440/packet6 healthy;
mic accepted5311/output0/packet4 отказал phase/adjacent guards. Mic
step53.1089959184frames превышает research48, maxinnovation37.1442721088;
staging=false/raw mapper не отказал. Пакеты1/479/31/4800/480/7/1024/211 при
прежней sinusoidal0.8ms metadata noise дают adjacent difference>1ms.
Защитный отказ сохранён как FAIL, пороги/Source/Grid не менялись. Это не
12 quality FAIL и не 12 PASS: quality corpus был прерван до первой проверки.

Отдельный CausalQualityVariableClean выключает только metadataNoise; метки
по-прежнему rounded100ns, variable packets и четыре physical patterns прежние.
Run83830 terminal0/build0/native0/wrapper0,12/12 actualAEC quality PASS.
Echo-only22.408881–22.426611dB, double-talk26.450877–29.483956dB, near
correlation>=.9997597/gain около−.50405dB/lag434, double-talk gain−1.563144…
−1.408836dB/no dropout. Mirrored NativeCursor phase<=.100103ms; это не
независимая позиция реального Sinc.1199blocks/case,firstPTS4800196,trims0/0
наблюдаются, но не asserted. Command<=100.059ppm, input peak10086/metadata10,
cap16384. Не представлять metadataNoise=false как jitter coverage.

Два результата локализуют отказ jitter/adjacent boundary, не исправляют его
и не устанавливают нового допуска. Исторические rounded partition FAIL11/132
и требования AEC/SC-003/FIFO/Stop остаются. Near-only raw/clean после Sinc и
mirrored phase имеют границы round185. Independent source review round185
не охватывает эти два новых driver delta. Installed GRAF не изменён.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalQualityVariable.cpp | 99761fa77635fd1eec992447f0d0547bbc97947914c4c3cd15f95bd6e7d8e0c5 |
| causal-quality-variable-build.cmd | bacc1eb8ed2c3b7ca9a83923a406e0ec1c3cf8799a77b59478bdc8738bdcf05a |
| causal-quality-variable-run.ps1 | aedffb4cf12c88822b6a9629495e4d9d8c76229e5f81bd12cd5c2f468b534a3a |
| causal-quality-variable-result.log | 22c470f8d915195260a170cbfd8abf654448bd5f589eb96c1620a98ceea10aa6 |
| CausalQualityVariable.exe | dc23c7ea6c7290dab0b3a4d77ae84bb8fe70d8af14e5af233f02d632e623bfbe |
| CausalQualityVariableClean.cpp | b2f8e74fb9783107849ea6caa309af86aeae648beb79f3df4b4c103bb4fcce20 |
| causal-quality-variable-clean-build.cmd | f3fdea5cf001d153fd28c1af6a2935fdb5f9751d48d081b7b607a83a08270b5a |
| causal-quality-variable-clean-run.ps1 | 9616b3a0e6e15a9ca9e7f18a6b7e230f552dbf2c660586758843c09d036f0781 |
| causal-quality-variable-clean-result.log | 20ae495b18e493b6b2c39673be0d5d0bf445f29a9b897178e9aa7ffbdc5af589 |
| CausalQualityVariableClean.exe | 59d5f4bc6ffaf25bb5cfce3dfb20a837567a2cc4d702ec6ba0989aeb09a387dd |

Wrappers pin пять inputs до/после; не full transitive/toolchain attestation.
Current EXE hashes совпадают с before-run; no live capture/user audio/server.

## Раунд 187 — независимое наблюдение позиции Sinc и физического эталона

CausalQualityTruth переиспользует causal grid/native AEC и прежние quality
формулы; новая минимальная матрица9runs:48000Hz/−100ppm render и44101Hz/+100ppm
mic,12s, fixed packets, origins1375/37123, q=round(T), q=round(T±8000sin(37n/rate)),
три режима echo/near/double-talk. Физическая истина/intervals не подаются
контроллеру. Hook existing upstream FRIEND_TEST наблюдает фактический
virtual_source_idx и указатель ядра в sa; исходная CPU convolution вызывается
ровно один раз. Input callback supplied64-base formula проверяет реальную
ячейку, fractional coordinate берётся из настоящего Sinc, не NativeCursor.
Hook снимается в normal/exception пути; output count совпадает с source.outputs.
Второй sb не instrumented: его результат по-прежнему проходит byte-equality
двух EOS fillers в Source. Это не independent dynamic completeness proof.

Run42268 terminal0/build0/native0/wrapper0:9/9runs/18quality gates PASS плюс
asserts фактического времени/received intervals/counts. Actual native phase
max0.121870ms против прежней границы<=1ms без подгонки задержки. Reference
near voice строится на общей PTS48k сетке и не обнуляется до5s: near clean
gain−0.504693…−0.504663dB/correlation0.998522–0.999417/lag437–438. Прежние
raw→clean near gates также PASS. Render energy на заранее выбранном1..11s
интервале сравнивается с physical far reference без lag shift: gain около
−0.127109dB (<=1). Echo-only>=21.939369dB, double-talk>=26.704107dB/
near gain в пределах3dB/no dropout.1199blocks/case,firstPTS4800196,trims0/0
наблюдаются, не asserted; command<=903.773ppm,inputpeak5312/metadatapeak13.

Независимый interval observer выбран именно для constant-rate fixture:
received q_i с известными E=.5 либо8000.5ticks сужают slope interval в пределах
±100ppm; bounds округляются наружу. Known exact fixture q0+start вычитается,
не первая неопределённая observation, поэтому2E здесь не теряется. Assert
содержания физического T(n_i) и measured max width<=240.000003ticks выполнены;
rounding-only maxwidth<1tick. Это simulation premise, не точность WASAPI,
не interval controller design и не acceptance переменных/дрейфующих clocks.
Ширина интервала не считается доказательством качества — quality/time проверены
отдельно. Новый observer не использует PhaseRemainder/Grid time/NativeCursor.

Historical11/132FAIL сохраняются; этот proof не заменяет §5 waveform invariant,
nominal rounded44100 regression, variable-noise отказ186 либо SC-003. Установленное
приложение/реальный микрофон/сервер/задачи не менялись. Source review запрошен.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalQualityTruth.cpp | eca28dd51bd53aa827a32fd3ff9bd84212f2647766f91b73693d913606f207ff |
| causal-quality-truth-build.cmd | 2b070822258393a0db36f3a65a45e70e6893c8127a246eb06cfbabcba300c339 |
| causal-quality-truth-run.ps1 | 6c459636d772e4523ad2561e14fd3798f2f3035d24eaad28d5a5e06e95c6dbcf |
| causal-quality-truth-result.log | e3c1ec278e293ec6d0c31349899385908ee0985ecda985e60a615ccb4fad21bc |
| CausalQualityTruth.exe | 72ca6435016e82e2fe1de991180d4a9240916800dd551cd12b47287fc78b97d6 |

Пять input fingerprints сверены до/после, current EXE соответствует before-run;
full dependency/compiler/library attestation не заявляется.

## Раунд 188 — исправление двух замечаний к тесту и контрольные отказы

Read-only reviewer сначала Request Changes по двум P2 именно в truth driver:
при несовпадении observer counter после detach catch повторно detach-ил nullptr;
поле passed не учитывало дополнительные physical gates. Это не опровергает
измеренные187 числа, но старый source не принимается для дальнейшего теста.
Старые bytes/лог сохранены, новый CausalQualityTruthReviewed исправляет только
эти пути: catch только вокруг drain, detach один раз до отдельного countercheck;
aggregate passed=existing_quality_passed && physical_passed, оба статуса видны.
Пороги/oracle/число18gates не менялись. Follow-up source review Approved,
оба P2 закрыты; это source review теста, не разрешение внедрения CausalGrid.

Reviewed run15507 terminal0/build0/native0/wrapper0 повторил9/9runs/18gates PASS.
Все числа времени/quality/interval187 воспроизведены; каждая строка имеет
aggregate passed=1/existing_quality_passed=1/physical_passed=1. Source review
не включает самостоятельный запуск VM, native evidence основного агента.

Два отдельные negative controls:

- Shift run43174 build0/native2/wrapper1: обе source.gridOrigin сдвинуты на96
  frames после первой admission, без изменения звука/guards. Terminal причина
  точно `actual Sinc physical timing exceeds one millisecond`, не generic fail
  или crash. Это чувствительность actual-time проверки к общему+2ms PTS shift.
- Counter run30485 build0/native2/wrapper1: reviewed driver ожидает source.outputs+1
  вместо actual equality после detach. Terminal причина точно `native output
  observer missed samples`, без повторного detach/access violation. Это
  regression исходного P2 error path, не аппаратный continuity failure.

Negative stdout quality-result logs не созданы: driver печатает exception в
stderr до первой строки результата. Причина подтверждена terminal output,
не ссылкой на отсутствующий/пустой journal. Source/build/runner/EXE hashes ниже;
не считать ненулевой exit сам по себе доказательством нужной причины отказа.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalQualityTruthReviewed.cpp | c4f38d3cecfa7ee5037435d22e1ece519d8ca1f7b7c2d3560d1805571f822da7 |
| causal-quality-truth-reviewed-build.cmd | d648209b415094306d9a0d1ded078fae3047b8fa5fb665d80dc2b48b4bce3766 |
| causal-quality-truth-reviewed-run.ps1 | 20a9db11f999265223d2c4e1872fe0dd979cb104f0da6f8c708eb3d77e6309e4 |
| causal-quality-truth-reviewed-result.log | a4dd5651137476c9606fa8733424e7af1e8ad2c93aa7b513a17806441834b2c3 |
| CausalQualityTruthReviewed.exe | 603e764845523112bd44458caa989c23763174ca2b750bef5156214ebb1611d7 |
| CausalQualityTruthShift.cpp | e5723bf96a99ac7a3229e028992cf7eef10a9a83422ae2209b2af8e54b53a759 |
| causal-quality-truth-shift-build.cmd | 2e28233afad0cd60da55a7053d9423a590149adaba46a9ded9003b0aa1077103 |
| causal-quality-truth-shift-run.ps1 | 65a18ba4bd9e4c366a85b929509dd8767b2d3325420e97b8ab2a67d293799dda |
| CausalQualityTruthShift.exe | 174d4eca26f053adcb0910400ee865c73487a46d14f1d6242fdcbbe8ae0eb80d |
| CausalQualityTruthCounter.cpp | 4ea0dd16c61f98af3d97bf75eabd3346f0a425a39ec15b8f3bc2af6252af59dc |
| causal-quality-truth-counter-build.cmd | 3c23d314b12d37d26b4223371753696bed8fd8808bc341834dfc78dd1468ed69 |
| causal-quality-truth-counter-run.ps1 | 7ac4bd7a0d272beb39bdd9ba8a79c2bac49bf5d953965c5f934c3979642e8ffa |
| CausalQualityTruthCounter.exe | 827c872614d2f71cb76aeac3540820f60bd9abd2395ac09ef180ab57e20e81a4 |

Historical11/132FAIL/variable-noise refusal не исправлены этой проверкой;
independent full-support completeness, bounded production FIFO/Stop/custody и
live VM/hardware/install acceptance остаются. Spec Kit lane high-risk Phase0
research, reviewer checklist/task state/normative §5 не изменены; commit99b00a5
сохранён, новой сборки/установки приложения/commit/push/PR/merge/release нет.

## Раунд 189 — фактическая полная поддержка Sinc и ранний конец входа

Read-only source review CausalSupport/runner: Approved только драйвер опыта,
без самостоятельного запуска reviewer и без принятия runtime. Main run3994:
terminal0/build0/native0/wrapper0,47/47 PASS. Матрица11rates8000…192000,
номинальные/constant±100ppm и exactprofile42; fixed/variable/3-frame partitions,
driver EOS после целого реально принятого пакета при разных порогах. Порог65
может дать accepted480: не заявляется точная отсечка по65-му образцу. Один
принятый кадр/пустой trusted ряд покрыты; EOS до первой admission и отдельные
31/32-frame переходы не покрыты. Metadata rounded100ns,noise=false.

Observer существующим FRIEND_TEST смотрит actual convolution input_ptr−r1,
не NativeCursor: при request64/kernel32 фактическое окно[cell−16,cell+15]
отбирается по current observed accepted end. Native CPU convolution вызывается
ровно один раз. Все её supported values совпадают с tap/offset/first PTS.
После объявленного конца выполняется один дополнительный настоящий Resample:
следующий kernel должен выходить правой границей за неподвижный accepted end,
не добавлять trusted sample. При положительном native шаге следующая полная
поддержка уже невозможна. Это независимая проверка полноты фактически выполненной
последовательности, не проверка правильности команд либо physical clock.

IdentityStage/clockRecoveryFrames=0: каждый system/mic образец канонического
блока численно совпадает с actual convolution по собственному PTS; сравнение
float== не отдельный byte-identity proof для±0. Независимо проверены пересечение
двух trusted intervals, первый/последний PTS, непрерывность и floor(common/480)
блоков. Общий неполный хвост не дополняется тишиной. Source отказал поздней
admission без изменения accepted/packet/generated. Это research sealAccepted,
не product Stop mutex/producer completion/two EOS/finalizer/writer.

В том же EXE --drop-tail: native2,точная причина `SUPPORT_FAIL: candidate ended
before actual full-support tail`; wrapper требует exit2 и ровно одно такое
сообщение, CAUSAL_SUPPORT_NEGATIVE_REASON=True. Native crash/иная причина не
засчитываются. Positive peak input10008/grid metadata1761 — измерения этой
матрицы, не worst-case capacity proof. AEC quality/live audio не выполнялись.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalSupport.cpp | 5a21799fbe522563f9f3080a8845d9d1dbfb02e1703aad844d23fe38ea52712e |
| causal-support-build.cmd | c5e0baf0c3577ac8cc8dbed1bae98eef73f348532b672017c424eeb5934aa76d |
| causal-support-run.ps1 | 4570908912bad2a269e99beedfc1bd0805181868d54eb3d118d9c420de4da30f |
| causal-support-result.log | 4b4c98c2ac8b672417fcc0a8b93f6173c4d96525b619b14e49bf73e7ebc76f7d |
| causal-support-negative-result.log | 5c91fe903e4659e62925b2c6ca7d55cf549d793d031aac4a78b21de860f3bbc0 |
| CausalSupport.exe | 4269f166d5cb61ab13aa3ec1eff7ceeec3af4509154d49a9aa6d34bd6a0cd99b |

Five pinned inputs before/after и current EXE сверены, не full transitive/
compiler/library attestation. Historical11/132FAIL,variable-noise отказ,
upstream VMclock_drift, SC-003, полный production Stop/custody остаются открыты.

## Раунд 190 — предел входного буфера: условный анализ и достижимые случаи

Read-only capacity analysis отделён от измерений и продуктовой приёмки.
Для одного источника L=4800input-lookahead,P<=4800packet,A=accepted,
S=supplied,C=actual native position,n=nominal grid position. Только при полном
drain после каждой admission и здоровых guards: lastPacketStart<n+L,
A<=n+L+P−1; перед следующим drain Anew<=n+L+2P−1. При геометрии request64
и положительном шаге S>=C даёт Unew=Anew−S<=L+2P−1+(n−C).
Innovation48 ограничивает cursor относительно received QPC, не n: raw envelope
содержит накопленный100ppm член. Предварительная консервативная оценка:
E(r,T)=ceil(.0001*r*T+.00201*r+r/96000+3),Unew<=L+2P−1+E.
Её предпосылки, геометрия и арифметический резерв требуют отдельной проверки;
это НЕ новый timestamp allowance или утверждённая allocation.

Frozen grid q<1e9ticks сам ограничивает вычисляемую команду менее100s: его нельзя
назвать часовым controller. При условном T100/r192000 оценка16710>16384:
достаточность кольца не доказана, но превышение верхней оценки НЕ доказательство
достигнутого переполнения. Условные metadata bounds grid<=11520/source<=11917
также требуют обслуживания после admission; измеренные peaks не заменяют их.
При физической частоте>=.9999*r и незадержанном обслуживании запас L/r=600ms
на8000Hz либо25ms на192000Hz; packet-ready bound<(L+2P)/(.9999*r) даёт
1800.181ms/75.008ms. Это ожидание одной grid-ячейки при данных предпосылках,
не UI/готовая пара/Stop SLA; без scheduling/delivery bound общего времени нет.

Native run95026 CausalBounds: terminal0/build0/native0/wrapper0,2/2 PASS.
Использованы неизменные Source/Grid; никаких подставленных cursor/anchors:

- Старт8000Hz,3s input:4795 реальных одно-кадровых пакетов и очередной4800 из
  существующего variable nextCount. При accepted9595 последний anchor4795<4800,
  после полноценного drain outputs0/supplied0,кольцо реально держит9595>4864.
  Следующий реальный480 даёт10075 unread до первого продвижения. Затем native
  Sinc выпускает28800outputs/59полных blocks до EOS при healthy timeline.
  Это воспроизводимый контрпример4864, не теоретический worst14399 и не гарантия
 16384. Низкочастотный open controller действительно упражнён, не только EOS-tail.
- Задержанный потребитель48000Hz:34 реальных fixed480 admissions без drain
  дают16320 unread. Следующий480 отказан staging guard ДО копирования и новых
  metadata. Проверены неизменность обоих owned arrays/accepted/packet/anchors/
  grid; rejected terminal segment не продвигает native reader и позднюю admission.
  Смена count/sealed при terminal refusal ожидаема, не normal completion claim.

Frozen Source SHA1609a588/GridLibrary7b7d45f2 unchanged. Generated wave только в
RAM, микрофон/установленный GRAF/сервер не затронуты. CausalBounds source review
запрошен отдельно; runtime PASS сам по себе не считается source approval.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalBounds.cpp | 703c0abc7c3ae370510c6d51d94b7125e4b55449d611bfa1b40451a6bab0c983 |
| causal-bounds-build.cmd | 5cb46f731bad4676e9226c5de2c9da7de25bfa6906b9bd71c2abb875cfad1f64 |
| causal-bounds-run.ps1 | f2ad2e4177a1b5aa58beae9510fbef8c1fcf0162536acf3b650398583764477b |
| causal-bounds-result.log | aa13bc26981be3b7e8e3e3a2fb63f3fa353fdd23516bc562bf71aa08a9f41329 |
| CausalBounds.exe | ab2a344ee9cfb518dcc3074ee659f736ac90cd36af97fc62a00956ea9f195e21 |

Five input pins проверены до/после; EXE SHA снят до run и совпадает с current
bytes, не hermetic/full dependency attestation. Timeline960000/source,
dispatcher256/twoEOS и5s drain — отдельные границы, их не складываем как ring.
Следующий узкий технический вопрос: численная/достижимая верхняя граница high-rate
кольца и lifetime<100s самого frozen grid; не повторять quality matrix вместо
этого. Не переносить cap/innovation/latency в product contract до принятия.

Current repo/branch/feature verified,HEAD99b00a579c24b50e320465b69d9a296038bc544d.
Mac CUA снова сообщает locked/auto-unlock failed; UI/Telemost/T097 приёмка не
заявляется. Skill speckit-plan оставляет high-risk Phase0 незавершённой: after_plan
не выполняется, задачи/checklist/normative§5 не закрываются, приложения нет в
новой установленной сборке. Commit/push/PR/merge/release в этом раунде нет.

После дополнений189–190: check_spec_kit_governance.py PASS,
speckit-bootstrap doctor --frozen PASS,YAML F200 parse PASS,git diff --check PASS.
Tasks hash45641d615923b4c049482397e90e6ce765255b8ba7467f2d867cd4c8c7e27d50,
normative desktop contract8aaedaa990154a801e6b6c73ba35e304df26bc8b383a0dae35c5929617812135
не изменились. Product apps/windows/server/macOS/AGENTS/constitution/root
CHANGELOG diff пустой. Git worktree registration повторно подтверждает тот же
path/branch/HEAD; перенос/очистка чужих рабочих копий не выполнялись.

Source review CausalBounds сначала Request Changes/P2: в запросе Main ошибочно
было написано «потом полный drain до EOS». Код действительно заканчивает первый
случай после первого open продвижения, печатает EOS=false и не close-ит timeline.
Этого EOS evidence нет; существующие цифры/описание190 выше относятся только к
startup-before-EOS и terminal capacity refusal, не к полноценной записи. Ошибку
формулировки признали, source/runtime не меняли, отдельный EOS proof189 им не
подменяется. Review также подтвердил достижимые10075, ранний refusal16320 и
сохранение accepted input/packet metadata. Запрошен уточнённый узкий verdict
для фактически выполненного опыта, без ослабления продуктовых требований.

Уточнённый verdict: Approved только startup-before-EOS/terminal capacity refusal
на тех же SHA703c0abc/f2ad2e41. Нового source read/VM run reviewer не выполнял,
validation190 независимо не проверял. Historical Request Changes для неверно
заявленного EOS-охвата сохраняется; normal EOS/close этим approval не заявлены.

## Раунд 191 — предел100s и достигнутый overflow при здоровых clocks

Read-only arithmetic review условно допускает только расширение research q
до36010000000ticks: rate<=192000,n/base<=691392000,outputs<=172848000,
монотонные anchors/конечный local cursor. PhaseRemainder scale делит целые
счётчики до умножения; q/o whole и residual безопасны/exactly representable в
этом диапазоне. RelativeTime вычитает абсолютные QPC целочисленно. Binary64
ULP около upper q=0.00000762939453125tick; оценка interpolation arithmetic
<0.00002tick — не WASAPI accuracy, не waveform/cumulative native/threshold proof.
Это не снятие raw100ppm+1ms/innovation48/command1000ppm/owned16384/§5 guards.

Run18011 terminal0 wrapper подтвердил ДВА ожидаемых отказа; это не PASS записи.
CausalLifetime192000Hz/physical−100ppm/variable packets/no noise/generatedZero,
два actual native Source,IdentityStage/recovery0. После каждой admission оба
drain до отсутствия разрешённого продвижения; нет искусственно задержанного
потребителя и нет preload будущих anchors. Source/PhaseRemainder неизменны.

- Frozen101s:build0/native2,точный `fixture relative QPC conversion outside bound`.
  outputs4799520/accepted19205881/supplied19196224/peakUnread11871,
  raw/staging/phase flags0,sealed0. Это именно old q<1e9 restriction, не clock
  refusal, crash или завершённая101s запись.
- Long600s: изменена только одна строка external grid q finite/<3601s.
  build0/native2,точный `owned_input_capacity`: после15963840outputs/33257blocks
  accepted63864951/supplied63849024/unread15927,следующий480 даёт16407>16384.
  Реальный Source::admit выставил staging/witness,но raw/phase refusal0,
  accepted/packet/owned arrays/metadata counts сохранены. Это достижимый случай
  примерно332.64s, не превышение одной теоретической верхней оценки190.

Source review Approved узкие drivers/runner. Preliminary pending check выбирает
момент snapshot,но verdict требует фактический refusal настоящего Source;
runner требует native2 И ровно одну точную причину каждой версии. Meta contents
не snapshot-ятся полностью,early guard order дополнительно проверен по Source.
Zero PCM не проверяет quality произвольного сигнала. Source mirrored base/index
так и подписаны; unread основан на реальном callback supplied. Чистые входные
clocks не означают healthy product при capacity failure; normal claim отсутствует.

Причина роста — nominal n+4800 gate: при physical−100ppm consumed input отстаёт
от nominal n примерно19.2frames/s на192000Hz; это расхождение накапливается в
owned FIFO даже при полном drain после admission. Простой больший cap не выбран.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalLifetime.cpp | 630235e968d42da7a658754e2dfc6f9069de0a62e167f740196d8a6723625aa7 |
| CausalGridLongWindow.cpp | bff1c78157edc7ba698233a23fa76c98f3feb5fa0b618bb3a3dc0b185eb9719f |
| causal-lifetime-run.ps1 | daee5d8efd19b0aa3868059c30b7df68500454baa40d3b28c6df13c8b73c8b7a |
| causal-lifetime-frozen-build.cmd | 94a7b6be995212b27f57562e520d07127abee854c9365c2ac9eff7e773f267d6 |
| causal-lifetime-long-build.cmd | 5073314b8c9a693b4b2bd9cf4936841d8873c043ab50832b8b91d68dfea87056 |
| causal-lifetime-frozen-result.log | e244873ab91fbcb83f53c5f0b42a967c49f1e703c5cbe74ca5631509310c30bf |
| causal-lifetime-long-result.log | 0b22eca3dd2846e5074a29325d2b28cdc182c98b424f2930dfb4e3d966dcf4f1 |
| CausalLifetime.exe | adbe436ff597153aa1197cc17e6ba5602eb8ba5343c9a577b6f25e88a931f979 |
| CausalLifetimeLong.exe | c6e587569830a64f0f9661d12c550b756c04aeefe9d9624ae035619b09c358fa |

Seven pins before/after/current EXE сверены; не full compiler/libs attestation.
Run terminal0 означает корректное обнаружение отказов,не 600s success.

## Раунд 192 — полученное QPC вместо nominal readiness: Ready600s

Внешний вариант ждёт received relative QPC>=fixed output grid time+4800/rate
lookahead,не nominal n+4800. По соседним принятым QPC обратная интерполяция
получает fractional input position; left.n−cursor.base вычитается целочисленно,
остаток учитывается без округления до целого source frame. InitialPhase/seed/
команда±1000ppm/innovation48/Source guards сохранены; tail hold привязан к
consumed position,не nominal. Это новый research controller,не эквивалент §5.

Первый Qpc run89758 build0/native2/wrapper1: `grid origin differs from received
source`,B ещё accepted0/control.size0. Старые bytes/лог сохранены как FAIL.
Ready derivative допускает ожидание пустой metadata только при accepted0 И
outputs0; для уже принятого источника её отсутствие по-прежнему failure.
Неempty origin equality сохраняется. Runtime negative missing-metadata mutation
не выполнялась; refusal ветка только source reviewed.

Ready run17028 build0/native0/wrapper0:600s192000Hz/−100ppm/variable packets
generatedZero,131028packets/115188480accepted per source,28799992outputs,
28799988trusted offset,59999full blocks. Оба sealed/finished,healthy timeline
close,raw/staging/phase flags0. PeakUnread10043,не растёт как191; Source EOS
supplied115188544/filler64,64filler не публикуются. Это controlled=true/Ready
native success,не Pruned evidence,не AEC/живая запись/час/production Stop.
Narrow Ready source/runner review Approved; waveform и аппаратные gates открыты.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalGridQpcWindow.cpp (FAIL) | 33826efc5b3872e03a110613b19c165db9f1379eb77742d9d2af88858f8ee4ed |
| CausalLifetimeQpc.cpp (FAIL) | ea77c21e6563644a0c83dd9b0cd62a461ce4c207331927f7813af13827d3ad9d |
| causal-lifetime-qpc-build.cmd | 383fbe42d9edfa43e6235f57cb48703f08af3cad18a4c878de5350a4051f9942 |
| causal-lifetime-qpc-run.ps1 | 2b2accb3efbf8e03087199e3e05da4eae1186c3cfa012317f39cc7ea10de134e |
| causal-lifetime-qpc-result.log | c2cbc21ac91c573fa579c8639ceb24ee187a929ea7d4510a8eb2f0fd7bf33c81 |
| CausalLifetimeQpc.exe | f6d399786937643c9fdcc4ab494b8078cb177438c3e34a64127ae7d1f59cfe73 |
| CausalGridQpcReady.cpp | 0fa9961cfd7b14f69d1ba3fd584fc5fcc40371124fb9c9f8e3844d30c4e7993b |
| CausalLifetimeQpcReady.cpp | 9f6d55e0e87379e20216b4d1cd2586918633959f956be466ef31f5d5ea0fe07c |
| causal-lifetime-qpc-ready-build.cmd | 7a72049311628417c2c4dc03ba0794e9d60b6d29fbf664f64ed77937f0df390a |
| causal-lifetime-qpc-ready-run.ps1 | 0a4d4a963f68d8e5384176469eebf69d26f84b47320cc3a80f4aa482f36e0ccd |
| causal-lifetime-qpc-ready-result.log | 729fb9cc6f9205abfa37967732a2513ff2bbd27b081ae11ae2caae2289708b2e |
| CausalLifetimeQpcReady.exe | f267f8257666d95aa2e4e1619d8453a456805a4d48bd3a111d2d1eb1140dbbf2 |

FAIL reason подтверждена terminal stderr,stdout log хранит metadata rows;
не приписываем ему отсутствующую строку причины. Five pinned inputs и before-run
EXE/current bytes совпадают; не full transitive attestation.

## Раунд 193 — Pruned:47support PASS,но20/132waveform FAIL

Review выявил Ready grid cleanup только внутри controlled feedback: uncontrolled
накапливал бы все anchors. Pruned переносит тот же while cleanup перед if,
после readiness. Он сохраняет origin/минимум одну точку/соседнюю пару при feedback,
не затрагивает независимые Source anchors. Это root fix общей ветви,не увеличение
metadata cap. Full Pruned source review Approved research only; q domain guard
по-прежнему внутри feedback после cleanup,универсального no-metadata-mutation
при domain failure не заявляем. Ready600s автоматически на Pruned НЕ переносится.

Run59390 build0/native0/wrapper0: Pruned+CausalSupportQpc,47/47 actual native
kernel/common PCM/PTS/EOS checks и --drop-tail native2/точная причина
`candidate ended before actual full-support tail` PASS.
Тестовый oracle189 не изменён,только импорт grid. PeakUnread10008/gridPeak1762;
EOS до первого пакета/31–32 boundaries/AEC/live/production Stop не покрыты.

Run58764 build0/native1/wrapper1: Pruned+CausalRangeQpc,132comparisons/112PASS/
20FAIL,прежний tolerance0.00001. При controlled=false66/66PASS/error0; nominal
pattern1 все44comparisonsPASS/error0. FAIL только controlled±100ppm с округлёнными
QPC; max4.36268746853e−5 на44101/+100ppm/variable. Это хуже historical11/132FAIL,
не «всё исправлено» и не waiver. Initial simple parser увидел131rows из-за BOM
UTF16LE; после явного удаления BOM пересчитаны132,20FAIL,counts совпали сnative.

Первое Ready600s доказало прекращение роста FIFO в одном generated clean
случае; Pruned47 доказали поддержку,но новая132матрица запрещает adoption
controller как готового продукта. Нужны uncertainty/waveform/quality gates,
worst-case FIFO/latency/длительная Pruned/actual Stop/custody/live acceptance.
Старые11/132FAIL/variable-noise/upstream VMclock_drift сохраняются; thresholds
не менялись. Узкий source review производных oracle/runners запрошен.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalGridQpcPruned.cpp | efea42490415a9d3b839234de8802bddcdfb4f5658ead3f47a577bc94ad7e5f0 |
| CausalSupportQpc.cpp | 84f4d8b538190de76324ae4c0203aabfec7f433f847da594b727fff36107e293 |
| causal-support-qpc-build.cmd | 27e2669bdc14aa89e5287852c04a31e0ef4656796aa30181b48b2254f703500b |
| causal-support-qpc-run.ps1 | 96b40efd2159597d26c758cf8a72222ae08f769ee4d91e541d940ff151913bc3 |
| causal-support-qpc-result.log | afbe8bf0e8b50cdde699cc97b6958de49086867f8acd30d83ec68e5d9c7069f6 |
| causal-support-qpc-negative-result.log | 5c91fe903e4659e62925b2c6ca7d55cf549d793d031aac4a78b21de860f3bbc0 |
| CausalSupportQpc.exe | bccc79d99476d6479244f64fadcfbf0ba1c6180b79a7f070982e7995786881b5 |
| CausalRangeQpc.cpp | 0053b2e6fd973f40054619b93135fc3f1c1ecfe9be66c669d2fce001d01b17a8 |
| causal-range-qpc-build.cmd | 709fc3aa2ed197c9590d2fd13922a9961fa3167f6f4c2133fa2759ff27e86509 |
| causal-range-qpc-run.ps1 | 114490a877c7c1c9bae6a034dbde09e9a1a9cf8bbd17266b31d3b7f545065574 |
| causal-range-qpc-result.log | be6aed383d61783a01a5339f26a3ef897d29cdf204d1e5f11e994b0722222c24 |
| CausalRangeQpc.exe | 7a8a517721fb089257e51e5862486d7747c8e5cd431c347c4a1672dac56fa781 |

Pins/current EXEs/Source1609/PhaseRemainderde73 неизменны; не full libs/compiler
proof. High-risk speckit-plan Phase0 не завершена; after_plan/implementation
не запускаются. Tasks/normative§5/checklist state/product code/rootCHANGELOG
не изменены,HEAD99b00a579c24b50e320465b69d9a296038bc544d. App install/commit/
push/PR/merge/release в193 нет; независимые live и physical x64 gates остаются.

Узкий source compare review Approved: Support отличается только import Pruned,
Range main/execute побайтно прежние,47/132counts/.00001/size/start/generated
проверки не ослаблены. Runner fingerprints указывают именно текущий Pruned,
не скрытый old grid; dependency/compiler closure не полный. Support negative
runner использует inherited regex -match текста причины,не equality whole-line;
нужные native2/одна matching строка сохраняются. Reviewer не читал runtime
logs/EXEs и не запускал их: terminal evidence отдельно получено Main выше.

Closeout191–193: governance PASS,frozen bootstrap doctor PASS,F200 YAML parse
PASS,diff --check PASS. Tasks119/92closed/27open и hashes45641d61/8aaedaa9
не менялись; product diff apps/windows/macOS/server/AGENTS/constitution/root
CHANGELOG пустой. Все native run handles18011/89758/17028/59390/58764 terminal;
нет потерянного running процесса или restart по одному observation timeout.

## Раунды 194–196 — локальный fit и отдельный скачок native Sinc

High-risk speckit-plan Phase0; HEAD99b00a579c24b50e320465b69d9a296038bc544d.
Только generated-data исследования вне Git. Продукт/нормативный§5/tasks/
reviewer checklist state не изменены; actual VM clock_drift не исправлен.

194: CausalGridQpcFit интегрирует полученную кусочно-линейную n(q) по времени
в окне q±4800*1e7/rate. Local input integer origin вычитается до float,
u нормирован на окно. Линейный fit вместо соседней двухточечной projection;
prune до max(0,q−window), retaining left bracket. Readiness/48-frame
innovation/±1000ppm actuator/16384 cap/480-output cadence сохранены. Окно
не экстраполируется и не использует fixture physical clock; только принятые
метки. Увеличено удержание старой metadata, достаточность cap НЕ доказана.

Первый preflight91777 завершился exit1 до сборки: опечатка в ожидаемом SHA
CausalRangeQpcFit.cpp (лишний C). Guard обнаружил ошибку; hash исправлен
по фактическому файлу, код опыта не менялся. Run85709 terminal build0/native1/
wrapper1:132comparisons,119PASS/13FAIL, tolerance.00001 прежний. Max
4.36119735241e−5 на44101/+100ppm/variable. Все66uncontrolled и44nominal
сравнения PASS/error0; улучшение20→13 не является waveform acceptance.
Main/execute одинаковы с прежним oracle, кроме include новой grid derivative.
Лог UTF16LE/BOM пересчитан:132rows/13FAIL совпадают сnative summary.

195: read-only friend Convolve observer фиксирует реальную cell/fraction/ratio,
вызывает исходную CPU convolution ровно один раз, её value/count сверены сtap;
detach выполняется на обычном и exception пути. Run78846 terminal0,build0/
native0/wrapper0 — diagnostic success,НЕ waveform PASS. 44101/+100ppm/fixed
vsvariable23967samples:worst index13555,cell12471/12470,fraction
.00016943946318015435/.99991758671437481,maxerror4.3611973524093628e−5.
Max actual position delta.00044581188983983111 input frames,changed integer
cells6. Малые позиции по разные стороны integer boundary требуют отдельной
проверки ядра,а не автоматического ослабления clock/waveform допуска.

CausalKernelBoundary сравнил fraction1 старого окна иfraction0 следующего при
ОДНОМ ratio,33generated samples покрывают два32tap окна. Callback запрещён
exception. Run98087 terminal0,build0/native0/wrapper0 обнаружил limiting gap
4.3008476495742798e−5; два точных исходных trace values воспроизведены.
Это воспроизводимый native kernel counterexample одного случая без WASAPI,
изменения ratio или записи пользователя; не объяснение всех13FAIL и не
исправление upstream raw clock refusal.

196: отдельный SincContinuousResearch.cpp компилируется явным объектом вместо
constructor/kernel объекта архива,не меняя установленные libraries/app.
Лицензионный header сохранён; единственное изменение окна:делитель32→31
и точный0 приx<=0||x>=1. Исходный VMcc SHA
3fe2d90e190b893962084e158cd725e1d88c93bae774621c706838b181494f9c;
локальный LFcc f46fa66676ddcdacec13f6cccf185d314c07e0d7f73a03c6fde8cc9174df53f5
после нормализации CRLF побайтно равен прочитанному VMcc. Это source check,
не полная библиотечная/compiler attestation. Upstream main содержит тот же
неисправленный window denominator: [WebRTC source](https://webrtc.googlesource.com/src/+/refs/heads/main/common_audio/resampler/sinc_resampler.cc);
он не подставляется вместо pinned library.

Run41525 terminal1,build0/native1/wrapper1:132comparisons127PASS/**5FAIL**,
max2.28676944971e−5 на44101/+100ppm/variable. Все66uncontrolled/44nominal
PASS/error0. Остались variable(не allOne) сравнительные FAIL44100/−100,
48000/−100,44101/+100,48000/+100,96000/+100. Допуск.00001 не изменён.
Новая сборка не является готовым фильтром:изменились частотная характеристика
и положение центра window15.5+fraction относительно sinc16+fraction; нужны
обоснование симметрии/quality/aliasing и полноценная повторная приёмка.

Run97354 terminal0,build0/native0/wrapper0:тот же actual trace observer в этой
сборке показывает новый worst index23737 nearEOS,cell21826/21826,fraction
.20857803272661002/.20813629220860363,maxerror2.2867694497108459e−5;
max position delta прежний.00044581188983983111. Значит оставшаяся ошибка
в этом случае НЕ переход integer boundary:временные траектории различаются.
Это локализация следующего вопроса rounding/clock fit/held EOS command,
не доказательство единственной причины всех5FAIL.

Независимый read-only reviewer Approved только четырём research sources:
интегралы корректны и exact affine projection математически partition invariant,
но rounded observations этого не гарантируют; causal window/metadata guard,
actual trace и endpoint counterexample корректны по источникам. Buffer16384
достаточность/SIMD/actual libs/runners/logs/VM replay/quality не reviewer proof.
Результаты VM получены Main,а не независимым повторным запуском. Phase0/
after_plan/implementation/задачи остаются открытыми; старые FAIL сохраняются.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalGridQpcFit.cpp | fa4e0ed08d1775d315241d9390ab40ddffadea762405254f1a32ab28e5dc2de0 |
| CausalRangeQpcFit.cpp | a08df566327ca9ac727bc74a3b5b3d4eb2ebbd4047dfc5d671f6acb5d1aadc5b |
| causal-range-qpc-fit-build.cmd | 7f303c75ab301bcee9050f594a479b537da803fa794cf29fa406dfed18f6297a |
| causal-range-qpc-fit-run.ps1 | 2404da47e9a18113ecb87fc06afcf087679d1c0a324423c8713e11fd008b3261 |
| CausalRangeQpcFit.exe | 94644b264b7b69d6f77d8286b68be8b44be7e3ca3dad779070e55d5937098b55 |
| causal-range-qpc-fit-result.log | 46b27e7cfb205e5d10f271d173216029a8fa5a89e1643b0b61a208160d3aa109 |
| CausalFitTrace.cpp | 32dee0e16dd0df6a08dc7308dda300e465823c8a0ea98abd6ac22cedd619242e |
| causal-fit-trace-build.cmd | 57f2e6d5bb16bccc003211d13617861847302d80e989fe59dd9a7dfa19190b75 |
| causal-fit-trace-run.ps1 | a1db6665000dc60dfa7c3374685b7a13382bf47685cbeeb697360b75019cb60a |
| CausalFitTrace.exe | 6d2727dc1ed68024f49872ad6fb38244353e0c28e1375f840af38b11bcd2751e |
| causal-fit-trace-result.log | 91e0f6a64e5de7b6f6cd97be36824d36782268a0cfa430a49e77386891902ab6 |
| CausalKernelBoundary.cpp | af95991a368e5cec82ded7ec1ed2aac253272ad3346d61745aac816c08150d70 |
| causal-kernel-boundary-build.cmd | d6aff2dda656024523f3abbaf285f0edb675fae5df005a3e271328c821bca316 |
| causal-kernel-boundary-run.ps1 | d177b2bf4b17b8dcb2f8dd9cef0ffea415625a59f66ba6d14c078df3aedf8e48 |
| CausalKernelBoundary.exe | 0e8b26dc3c8b78d8b3e93a38eecfbe874746d8213084f5f01556f463ab179fe2 |
| causal-kernel-boundary-result.log | 482797f2c5fa73219b257c997d62ce1f4d867bce6cd53f70112f705f2db1f0a4 |
| SincContinuousResearch.cpp | b4cf500db6919ae7f307ae934caf1c83b2c030f7e5bee2f26886c5ac2160ed98 |
| causal-fit-continuous-build.cmd | d5cd4d6d10b32f7da5341eccae8fed66f96162e70c8c66b9887ce78cdc5e10ab |
| causal-fit-continuous-run.ps1 | 9d6a57bc13c01bb7ea08df1526e0dd79173f9d3bbd8a1f096e83126039e83e77 |
| CausalRangeQpcFitContinuous.exe | 74a3008b6e15dc1b22d36755e0fe4c2bc9f75663274bfe379548ec0fe34d7d0e |
| causal-fit-continuous-result.log | c423fe9788eff33ee76130a376a0017fb2a9ce479ccb09ba8721d21127e18657 |
| causal-fit-trace-continuous-build.cmd | a150cbab4ae0023e10fb7697dae439b6ab2c79cae5568841c6c3dcdd3493150b |
| causal-fit-trace-continuous-run.ps1 | 1ebaeee7d3903eecc37ffa4d18f11c4e88e316dd421573718315ecd2b14a7789 |
| CausalFitTraceContinuous.exe | 04bff07c19d4c657cc7ef383d8c16a80ece438b513a9aac874c6096b0e68d538 |
| causal-fit-trace-continuous-result.log | 662ffc2f2e2beb3c2f1bc97193bc8de3c1e0d947fac4f1484bdb60c7cb4011d3 |

Сохранены Source1609a588/PhaseRemainderde73c764,прежний Pruned и его failures.
Гейты actual support/длительность/AEC/FIFO bounds/production Stop/custody/
SC-003/live auth-upload/UI/accessibility/physicalx64 новым source не пройдены.
Приложение не установлено заново,новых commit/push/PR/merge/release нет.
Native handles91777/85709/78846/98087/41525/97354 terminal.

Closeout194–196: governance PASS,frozen bootstrap doctor PASS,YAML parse PASS,
diff --check PASS. Отдельная проверка25fingerprints в новой таблице совпала
сфактическими files. Первый Ruby parser отказал на недоступном filter_map
до проверкиpins; после замены наmap/compact25/25,не fakePASS. Hash tasks
45641d615923b4c049482397e90e6ce765255b8ba7467f2d867cd4c8c7e27d50,
нормативного windows-desktop-contract.md
8aaedaa990154a801e6b6c73ba35e304df26bc8b383a0dae35c5929617812135 неизменны.
Worktree зарегистрирован Git на99b00a579c24b50e320465b69d9a296038bc544d;
в ambient detached0309 не работали. Reviewer закрыт после read-only verdict;
продуктового diff/внедрения/перезапускаinstalled GRAF в этом раунде нет.

## Раунды197–199 — ошибка до EOS и условная интервальная модель

High-risk speckit-plan Phase0, HEAD99b00a579c24b50e320465b69d9a296038bc544d.
Исследования generated-data вне Git; installed app/норматив§5/tasks неизменны.

197: Logged добавляет только диагностические поля кFit,не меняет вычисление
команды/готовность/очистку/guards. Actual native position берётся до drain через
callback supplied иprivate virtual_source_idx,включая lazy wrap. Received fit
intercept и эта позиция сравниваются с физическим временем генератора.
Контроллер этой истиной не пользуется. CELL показывает state ДОdrain,но
command_ppm ПОСЛЕвозможного обновления; только успешные grid-cell продвижения.
При fitted=false числоfit_error_ticks=0 означает отсутствие оценки,не error0.

Run11444 terminal0,build0/native0/wrapper0:100CELLrows,прежний TRACE23967samples/
worst23737/max2.2867694497108459e−5 в точности воспроизведён. Наout9600 оба
источника ещё open:fit_error fixed−.004671/variable−.231831 tick,
actual position delta−.0411528tick. Наout16800 open delta−.0719096tick;
наout18240 open−.0779421tick. Следовательно различие возникло доEOS,не только
из-заholdTail. Наout18720 обаsealed,ноheld0:последние команды32.42999157 и
32.41064081ppm;out19200обаheld1/positiondelta−.0817944tick,на23520−.0992083tick.
Удержание разных команд сохраняет и увеличивает прежний остаток. Источник
estimate bias в этом generated constant-rate случае — разные полученные
округлённые опорные точки/кусковая интерполяция;это не доказательство всех5FAIL.

Независимый source review Approved только diagnostic layer:actual position/
fit units/exception detach/tap value-count checks корректны. Runtime review
не выполнялся. Max_position_delta всего потока не равен автоматически delta
в worst PCM точке; CELL context не подменяет этого различия.

198: отдельный AffineResearch хранит два накопленных period bounds вместо
локального fit. Для каждого принятогоn>0 пересекаются
[(qRelative−.5)/n,(qRelative+.5)/n],projection использует midpoint периода.
Ниphysical pattern/истиннаяfrequency,нибудущие anchors не передаются controller.
Readiness/480cadence/48innovation/±1000ppm/representation deadband/holdTail/raw
mapper сохраняются. Pruneдоq,неq−window;старые ограничения остаются вbounds.
Это ПРОБА ТОЛЬКОconstant period + exact first anchor + nearest100ns endpoint
rounding. Полтиковая ошибка — свойство текущего генератора,НЕ accuracy WASAPI.
Непустая модель не делает неизвестное начало точным,не разрешает продолжение
после rawclock fault и не поддерживает changingfrequency/noisy observations.

Run63008 terminal1,build0/native1/wrapper1:132comparisons131PASS/**1FAIL**.
Единственный44101/+100ppm/variable,max1.14161521196e−5 при прежнем<.00001.
Все66uncontrolled/44nominal PASS/error0. Header явно сообщает assumptions;
старый132oracle counts/start/size/generated/.00001 не менялся. Parser132/1
совпадает сnative summary. Не считать почтиPASS приёмкой и не менять gain/
deadband/tolerance ради последнего случая. Low-rate случаи целиком вholdTail
могут проходить без применения новой модели:131PASS не означает131model proofs.

Source review Conditional Approved только под указанными premises. Средняя
точка разных feasible intervals различается;условная математика НЕ обещает
partition waveform invariance. Первоначально reviewer читалdrivera6ffb45d;
до сборки толькоliteral\\n вheader заменён на newline,current53cacf55.
Ordinary quotient division не являлось outward interval certificate.

199: Outward требуетn0при первомanchor,domain n<=2^52/qRelative<2^52 до записи
массива;внешние границы quotient округляются nextafter наружу. Для точных
целых/полтиков в этом диапазоне иcorrectly-rounded IEEE division подnearest
rounding это включает exactquotient. Runtime precondition is_iec559/FE_TONEAREST
и3guardcases проверяют badfirst без измененияsize,half-tick boundary200.5
до/послеconsistentconstraint иempty intersection послеinconsistentconstraint.
Это не полный численный диапазон и не hardware/error measurement certificate.
Непустое внешнее пересечение не доказывает непустоту точного пересечения.

Initial18213 terminalbuild2: C2181 illegal else without matching if.
Новыйdomain check был вставлен междуif/else;native НЕ запускался,EXE/log не
существовали. Ошибочный source13caade9 иrunner78368cac сохранены отдельно как
Failed artifacts. Fixed source9a110cd3 перемещает проверкумонотонности обратно
в непрерывныйif/else,domain guard остаётся доarraywrite. Runnerpin обновлён.
Historical runner ссылается на прежние bytes по прежнемуимени,не current
runnable replay;это сохранённая исходная запись отказа,не новый PASS.

Run84430 terminal1,build0/native1/wrapper1:guardcases3/3PASS,та же132matrix
131PASS/**1FAIL**,тот же44101/+100variable1.14161521196e−5. Outward rounding
исправляет premise численного inclusion,не waveform residual. Fixed flow source
review Conditional Approved:монотонность доunsigned subtraction,отказы до
arraywrite;division assumptions сохранены,ниmatrixPASS,ниfullnumeric proof
reviewer не заявляет. Runtime результаты получены Main,не независимым replay.

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalGridQpcFitLogged.cpp | 829a87eee34c5506d4aefeb9c6c2f89042bd5adc30bb940f8c6e35ee53472e5d |
| CausalFitCellTrace.cpp | 69f24b25b22615cfd9045b88d3890905314246270294b898ce9fdbe5c1b6c1b0 |
| causal-fit-cell-trace-build.cmd | 3b7a96d2bb72a9453fe9a3ffb3c771d90f9dbb9780da0ee0d5a6038efd21a1dd |
| causal-fit-cell-trace-run.ps1 | ccbe8bc10f2c208f5ec0b9e1ec6b4536bc6155522ace6c7dd1ba14b5e531b8cf |
| CausalFitCellTrace.exe | cc63140682c5b6e7a48ca6cefe2f725f270465544b9aa3fc97da197aac1ce1d9 |
| causal-fit-cell-trace-result.log | 3d8885d4e86610c63cfc894cb21f8174a3c93a4fdc17574e1de124c5d4ea5727 |
| CausalGridQpcAffineResearch.cpp | b71f8912fb7a5e065e4e8170b3e1de0b5802310547792d7aae7062c509663817 |
| CausalRangeAffineResearch.cpp | 53cacf55040d3fed99665f55ff6872088edeb1b7e5bc660db55bd8e7f0856295 |
| causal-affine-research-build.cmd | b710250d15ecc0720c9bc3691f8190c3f00e4609ffe4691cc8c79164e5d4a47d |
| causal-affine-research-run.ps1 | 35359938db3f13e4bd365f4181cdaea9924c8dfc6e7d0adf52082119ed349a12 |
| CausalRangeAffineResearch.exe | 70ec0232441953413d8442ec071266150ea4ed64f47643afae9a1e99448f1348 |
| causal-affine-research-result.log | 9b69bd7319439b5017bcc82ef2179ece47015726083dc43058928dd3bf27b217 |
| CausalGridQpcAffineOutwardFailed.cpp | 13caade9938cb930ee6655378710a069819fcab79a6730a73dd2fb516413beaa |
| causal-affine-outward-failed-run.ps1 | 78368cac930889541ad33992bd8ff9d4e6394e8d1b3de2e28c1d5908dc86367f |
| CausalGridQpcAffineOutward.cpp | 9a110cd33ebb19fe8047730f300ea723530d9181fd1718a1cec07f06e3ea9ec2 |
| CausalRangeAffineOutward.cpp | d1ab248f3047997879b61dd35ad3d802ed029ac43c24ce5f4dca49a063b61861 |
| causal-affine-outward-build.cmd | c1807961673925ba70d532709b7570b63b97d7cd0a9136362ab8f430d9946396 |
| causal-affine-outward-run.ps1 | 4920dfd3526b03dcf08375cf7d2acc58ea4a47780eff0b5ec0e32f40311548af |
| CausalRangeAffineOutward.exe | 5bef5f72d58a4224e7648d24b2120677a3f243a4acd334bab5f4fa2731e85646 |
| causal-affine-outward-result.log | 4773064349b03823fc6efa8054db702ca5a3641dc604d31501287cce617bf3ac |

Source1609a588/SincContinuousb4cf500d/PhaseRemainderde73c764 неизменны.
Native handles11444/63008/18213/84430 terminal. Physical/live/installed/custody/
AEC/fullsupport/lifetime/Stop/fullFIFO/currentrawVM gates этими моделями не
закрыты. Следующий исследовательский вопрос — границы clock uncertainty/
неизвестный first-anchor/меняющаясячастота с сохранением настоящих требований,
а не внедрение идеальнойconstant модели. Phase0/after_plan/implementation
не закрыты;новыхcommit/push/PR/merge/release нет.

Заключительный delta-review Approved: currentdriver53cacf55 отличается от
revieweda6ff толькоheader newline(обратнаязамена воспроизводитполныйSHA).
Outwarddriver сохраняет все132oracle/start/size/generated/.00001 predicates;
current4920runner pinsfixed9a110,archival783pinsfailed13caade,не смешаны.
Не проверенные reviewer logs/VM не становятся независимымruntime acceptance.

Closeout197–199: governance PASS,frozen bootstrap doctor PASS,YAML parse PASS,
diff --check PASS;20/20 новыхfingerprints совпали сфактическимиартефактами.
Tasks45641d615923b4c049482397e90e6ce765255b8ba7467f2d867cd4c8c7e27d50 и
нормативныйcontract8aaedaa990154a801e6b6c73ba35e304df26bc8b383a0dae35c5929617812135
не менялись. Новыйproduct diff пуст,reviewerзакрыт,всезапускиterminal.

## Раунды 200–202 — симметричный фильтр и ограничения идеальной модели часов

Путь: `codex/200-windows-followup`; исходный HEAD:
`99b00a579c24b50e320465b69d9a296038bc544d`.
Режим: high-risk, продолжающаяся Phase0 `speckit-plan`, без переноса в продукт.
Все исследования ниже — отдельные x64 EXE в Parallels Windows ARM64, созданные
в `Documents/graf-windows-followup-200/f200-phase-saturation.XSjeTP`.
Они не открывают устройства, не читают пользовательские записи и не обновляют MSIX.

### 200. Симметрия окна и прежний строгий звуковой порог

В отдельной копии закреплённого native Sinc изменена только формула окна:
`x=(float(i)-fraction-1)/(32-2)`, нули вне открытого интервала (0,1).
Центр окна теперь 16+fraction, как у sinc; поддержка [1,31].
Преобразование unsigned i выполнено до вычитания. Другие коэффициенты,
память, native convolution и SetRatio не изменены. Производственное WebRTC
не изменялось; объект заменён только в исследовательском EXE.

Первый build закончился C4459/C2220: локальное имя checks затеняло существующий
счётчик MacReference. Exit=2, native НЕ запускался. Исходник сохранён как
CausalRangeSymmetricFailed.cpp. Исправлено только имя kernelChecks и его pin;
следующий build=0, native=1, wrapper=1.

5445 проверок таблицы коэффициентов и 33 базисных импульсов при пяти ratio:
максимальная разница зеркальных пар дробных смещений 2.98023223877e-8,
предельная разница native output между соседними ячейками 0.
Соответствие K_f[i] ↔ K_(1−f)[33−i] не является доказательством симметрии
каждого отдельного интерполированного ядра. Выведенные частотные амплитуды
только измерения offset=0, spectral_acceptance=false, не полная проверка спектра.

Неизменный Fit fa4e0ed0, 132 прежних сравнения и .00001:
127 PASS, **5 FAIL**, максимум 2.296641469e-5 на 44101Hz/+100ppm/variable.
Остальные отказы: 44100/−100, 48000/−100, 48000/+100, 96000/+100, variable.
Все 66 uncontrolled и 44 nominal сравнения дали нулевую ошибку.
Это не улучшение полного вердикта относительно Continuous: скачок фильтра
устранён отдельно, но зависимость оценки времени от округлённых опор остаётся.

### 201. Идеальная постоянная модель не является общим решением

CausalAffinePremises.cpp использует actual ClockMapper и неизменный
AffineOutward; только метаданные, без запуска Source/drain/PCM.
Положительный контроль плюс четыре воспроизведения ограничений, build=0,
native=0, wrapper=0; все 837 raw observations приняты actual mapper.

| Случай | Raw packets | Первое пустое пересечение period bounds |
|---|---:|---:|
| Точная начальная опора, nominal | 201 | Нет |
| Неизвестная начальная дробь .49 tick, далее округление | 33 | input n=6 |
| Ошибка первой опоры .8ms, далее чистые метки | 201 | n=960 |
| Физическая частота +100 → −100ppm после 1s | 201 | n=48480 |
| Колебание измеренных меток ±.4ms | 201 | n=960 |

В случае начальной дроби истинный период 625/3 уже исключается из ограничений.
Эти воспроизведения показывают недостаточность exact-first/constant-period/.5
premises, а не неисправность устройства и не новый повод запрещать запись.
Return0 означает успешное воспроизведение отрицательных случаев и контроля,
не принятие алгоритма. Нельзя добавить fallback с ослаблением raw guard,
выдавать midpoint за точную опору или превращать эти входы в общую runtime
политику отказа только ради прежнего результата 131/132.

### 202. Отдельная проверка настоящего AEC и физического эталона

CausalQualitySymmetric.cpp отличается от прежнего Reviewed только include:
CausalGridLibrary → CausalGridQpcFit; сборка явно использует Symmetric Sinc.
Те же девять 12s случаев: render48000/−100ppm, microphone44101/+100ppm,
fixed input packets, noise0/+.8ms/−.8ms, far/near/double-talk.
Сохранены реальные native position observer, физические эталоны, полнота
общих блоков, прежние 18 quality/physical predicates и actual AEC.

Build=0, native=0, wrapper=0: **18/18 PASS**.
Far suppression минимум22.392560dB, double-talk минимум26.079284dB,
physical near correlation минимум.99880535, actual phase максимум.104145ms;
render gain около−.12729dB, trim обоих источников0, 1199 блоков на случай.
Это проверка именно новых байтов на конкретной generated fixture, не перенос
старых PASS и не доказательство переменных пакетов, неизвестного first anchor,
меняющейся физической частоты, частотного спектра, EOS/FIFO/Stop или hardware.
Пять отказов раунда200 ею не отменены.

### Исходники и результаты

| Вне-Git артефакт | SHA-256 |
|---|---|
| CausalRangeSymmetricFailed.cpp | 0f91d67a95de11501c252f2adca2637f1baef75b614930b8b414c74a685e784c |
| SincSymmetricResearch.cpp | ef6e7a9460686fcc8f2d3e9b6848ba8194bb4bea1c00f42e20fafed325709f15 |
| CausalRangeSymmetric.cpp | a861e4d85daa6923c458724ab4d10ed690d01ec33e8d65727e57590069e3d0f0 |
| causal-symmetric-build.cmd | 8fce0ac3236ea8c4b600eb983cd4a7b116fddbece0eff384bd5f0a5409a3da78 |
| causal-symmetric-run.ps1 | 4371ec64f939fc4da05e9864898846e4779a9e79b250a4e4f1bcc80f8946211a |
| CausalRangeSymmetric.exe | 506cdae32b8c431d10fb9839a9275f545c48df853fbb63912b0f32476e1d5f13 |
| causal-symmetric-result.log | e1c2442036fb36e36c72bcccda1203d867857bca59af237a7bfa9e6e780e7c22 |
| CausalAffinePremises.cpp | 997911f5b195144c7e7ef640ae7465428960966ba7e0b4c7bc147dc7c3816034 |
| causal-affine-premises-build.cmd | fdeefbc174b64a7d1456b1c79c0dd54180f924cbe74fc1a5a16e15b3d95f916e |
| causal-affine-premises-run.ps1 | 29f2e8c8faa1624925ac2cfdde4a14cbeab439f631ca65b27522fc90ef260acb |
| CausalAffinePremises.exe | 89405f35af3c2a33a36768a461317e954a230c88701b537bbf49621c16e4e4ca |
| causal-affine-premises-result.log | 2c6c63f4c6f3f075907581e60cf007ff52698961cc485044614c1e9b48a4f8bf |
| CausalQualitySymmetric.cpp | b89ca34d2d4c65c7c99dc9ff0958efae97584170b2279fd900984197c309fa06 |
| causal-quality-symmetric-build.cmd | c35ec1e109dff74953b45dedf33d207ec04211f62de6fc6927e0d56b76ef91b7 |
| causal-quality-symmetric-run.ps1 | d06029d3f7ec7ee0556377c1f0bf5bb0185a25d4dbf74e11fcb50c2be9ad80e2 |
| CausalQualitySymmetric.exe | 1c95d80dae53c02e65cb97df482d5d53330c036f82f20765f1adce0cfda233d5 |
| causal-quality-symmetric-result.log | 87f3d571d323b4a45ff5c077b2ca639c96bd69cce2d5a22a631f25aa8296db0c |

Runner checks перечисленные входы до build, после build и после run.
Это не полное закрепление SDK/архивов/всех транзитивных заголовков.
Read-only reviewer одобрил текущий Symmetric source/driver и ограниченную
алгебру; VM/логи независимо не запускал. Остальные результаты получены Main.

Свежий CUA inventory сообщил: Mac locked, automatic unlock failed.
UI T097 сейчас не выполнена; прежний unlocked статус не перенесён.
Установленный пакет не обновлялся; ошибка живой записи ещё не исправлена.
Следующий шаг Phase0 — общий расчёт с неопределённостью первой и последующих
меток и меняющейся частотой, проверенный без ослабления исходных guard/порогов.
Native spectral/interpolation, full-support, capacity/lifetime, production Stop,
protected custody и полный пользовательский путь остаются обязательными.
after_plan не запускался: планирование не завершено. Commit/push/PR/merge/release
в этом раунде не выполнялись.

Closeout200–202: governance PASS, frozen bootstrap doctor PASS, YAML parse PASS,
git diff --check PASS;17/17 fingerprints совпали с фактическими артефактами.
HEAD99b00a579c24b50e320465b69d9a296038bc544d,119 tasks/92 closed/27 open.
tasks SHA45641d615923b4c049482397e90e6ce765255b8ba7467f2d867cd4c8c7e27d50 и
норматив§5 SHA8aaedaa990154a801e6b6c73ba35e304df26bc8b383a0dae35c5929617812135
не менялись. Product diff apps/windows/macOS/server/CHANGELOG пуст.
Все native handles23779/34891/69176/34620 завершены, validation32418/37932 PASS.
Независимый quality delta-review Approved: ровно одна замена include, прежние
18 gates, physical observer и снятие перехвата сохранены; current b89ca34d
и d06029d3 pins проверены. Reviewer не читал VM/logs, отсутствие trim — измерение,
а не новый обязательный predicate. Принятие алгоритма этим не разрешено.

Premises source/build/runner review Conditional Approved на997911f5/fdeefbc1/
29f2e8c8: actual raw admission предшествует interval model, PCM не вызывается,
продолжение после пустого интервала не fallback. Отрицательные случаи и контроль
соответствуют описанию. Driver не проверяет FE_TONEAREST/is_iec559 самостоятельно;
числовое outward обоснование остаётся условным, полной hardware гарантии нет.

## Раунд203 — независимый срез хранения, 2026-10-02

Владелец явно разрешил отдельную реализацию T115–T118, не ожидая clock
T094–T096 и календарного T119. Решение записано в spec Clarifications и
нормативном завершающем разделе plan. High-risk-product, защита данных,
независимый review и все общие условия выпуска сохранены.

В процессе чтения рабочая копия исчезла. Найден Git snapshot
9f67407123afd5f7b5b9ae3383f0ec5e46e7d1e2 (`startup-cleanup`) с родителем
99b00a579c24b50e320465b69d9a296038bc544d и прежними незакоммиченными файлами.
Восстановлена по исходному пути; branch HEAD не изменён, сохранённые bytes
сверены. Git worktree lock установлен на активную копию. Это не доказательство
исправления причины очистки Codex. Из snapshot не восстанавливаются ignored
build artifacts; локальный feature.json восстановлен с прежней feature/branch.

Scoped read-only analyze storage design: CRITICAL=0/HIGH=0, FR-012/013/014/022
и SC-003/005/006/008 сопоставлены T114–T118, неопределённой зависимости от
clock/T119 нет. Это проверка согласованности требований, не encrypted runtime
acceptance. Общие clock/calendar HIGH и product implementation gaps остаются.

Issue-sync выполнен только для отдельного среза: T115 #7443, T116 #7444,
T117 #7445, T118 #7446. Повторная проверка всех четырёх: OPEN; дубли не созданы.
Обязательный before-hook canon ensure PASS/no-op; after-hook
`EXECUTE_COMMAND: speckit.github-issue-canon.validate` PASS — 300 issues.
Это не полная сверка владельцев остальных задач F200 и не закрытие issues.

Frozen bootstrap doctor PASS; git diff --check PASS. До допуска независимого
review product code не изменялся, запись/миграция/установка не запускались.

Independent requirements review: `checklists/review-2026-10-02-storage-independent.md`
PASS112/112, затем отдельный status-only freshness PASS: contract §§1–9
неизменны (SHAfc831b083699fb7e96f17cb642ad9a50b79d68bb2130fff69d4e2500b3151c6b).
Main повторно сверил storage analyze после отметки T115: CRITICAL=0/HIGH=0,
требования и mapping не изменены. T115 `[X]` означает design acceptance,
issue #7443 остаётся OPEN до применимых tracker/merge checks. Всего119 задач,
93 closed/26 open. Текущий HEAD прежний; code не commit evidence.

Начат ограниченный шаг T116 в существующем Storage/Sha256: fixed64KiB read
buffer, native CNG на Windows и прежний portable compressor с фиксированным
64B state для host tests. Whole-file string/vector copies удалены. Stream/file
read/hash error возвращает отсутствие digest, memory identity hash при crypto
отказе бросает безопасную техническую ошибку вместо пустого ключа. Exact-handle
signed executable digest оставлен: путь не переоткрывается вместо validated
handle; исправлен только устаревший комментарий о whole-file sha256File.

Tests-first: новая regression Sha256Tests на non-file directory с прежним
кодом дала assertion failure (CTest exit8). После исправления PASS: SHA empty/
abc/million-a,55/56/63/64/65B padding,64KiB/tail, normal и exception-enabled EOF,
binary/cursor, initial fail и injected mid-read failures. Generated64MiB+5
поток запрашивался≤64KiB,1025 reads, exact independently calculated digest.
Это не измерение полного process budget/SC-003 и не protected IO acceptance.

Host fresh baseline: build PASS,32/32 CTest PASS. После изменения: build PASS,
33/33 CTest PASS. Native VS core project Release/x64 build и run exit0.
Windows whole CMake/VisualStudio build ещё проверяется: первая попытка exit1,
warning flood MSB8064/8065 на shared path скрыла причину; итог не объявлен PASS.
Независимый code review ещё выполняется. Полный T116/T117/T118 не закрыт.

## Раунд204 — реальные отказы CNG и запрет отправки без хеша, 2026-10-02

Продолжение high-risk T116 на HEAD99b00a579c24b50e320465b69d9a296038bc544d.
Исходники незакоммичены; единственная рабочая копия и ветка не менялись.
Проверочная копия на диске Windows не является новой Git authority.

Первый code review обнаружил BH01/BH02: native-provider exception через
memory identity hash мог выйти из reminder destructor или нарушить завершение
удаления. Исправлена общая причина: существующий portable compressor остаётся
маршрутом memory sha256() на всех ОС, с фиксированным состоянием и прежними
digest bytes. Описание memory native exception в раунде203 относится только
к первому варианту. Stream/file на Windows остаются строго CNG; native/read
failure даёт отсутствие digest без portable fallback или успешного prefix.
Same-handle проверка подписанного executable не изменена. /WX C4244 устранён
typed-zero в двух std::fill, требования к предупреждениям не ослаблены.

BH03 исправлен до network boundary: manifest digest проверяется existing
isSha256 до допуска tracks; no-hash означает invalidPackage до любого
UploadSend. Expected track digest проверяется до сравнения: empty==empty
не даёт допуска. Auth, ownership и upload identity не менялись.

Windows-only NativeHashFailureTests включает настоящий Sha256.cpp с четырьмя
TU-local BCrypt wrappers. Normal calls делегируют настоящему provider;
проверены отказы Open/Create/первого и второго HashData/Finish. Memory identity
правильна без native calls до и после отказа. V5 writer создаёт generated
fixture; настоящий transport при отказе третьего Open (только manifest,
media/playback valid) обязан вернуть invalidPackage и Send=0. Baseline с
valid synthetic owner/session доходит до одного подменённого wire call.
Production knobs, DLL hooks и dependencies не добавлены. Обычные CTest
targets получают отдельный SHA object; fault target исключает его,
предотвращая duplicate SHA symbols. Fault executable не входит в приложение.

Независимый обзор исходников Approved:
checklists/review-2026-10-02-native-hash-faults.md. BH01–BH03 устранены,
новых blocking findings нет; Ponytail: Lean already. Это bounded-hash review,
не принятие полного T116, migration/playback, runtime acceptance или release.

Fresh host rebuild/CTest33/33 PASS,26.81s. Native build на shared Mac path
получил LNK1181 и MSB8064/8065; отдельная проверка:
EXACT_OBJECT=True/LOWER_OBJECT=False, EXACT_STAMP=True/LOWER_STAMP=False.
Shared build не принят за PASS. Создана отдельная копия на локальном диске
Windows без out/obj/bin/vendor. Fresh MSVC19.44/CMake Release x64 build PASS;
CTest34/34 PASS,51.79s, включая NativeHashFailureTests. Это x64 код в ARM64
Parallels, не физическая x64 матрица.

Причинная regression проверена на отдельной native копии: временно возвращён
только прежний manifest admission. Fault test упал ровно на invalidPackage
assertion: CTest exit8/0xc0000409. Canonical source не менялся, реальных
wire calls не было. После возврата правильных bytes incremental rebuild
оставил старый object из-за более раннего timestamp копируемого source;
повторный suite33/34 не принят за GREEN. Назначена чистая пересборка.

Native copy SHA-256 всех девяти изменённых/новых Windows files совпали с
canonical/mirror. SHA-256 tracked diff apps/windows:
3f835e25a755d668e8df0953c18d8ca08740675b2cba619b4c8e15e9749348c4.
Untracked tests в diff не входят:
NativeHashFailureTests=a6b54f701ca1927f941a8af914bb88395e8813e4d10d3bf512e47bf4e4db08e4;
Sha256Tests=70bf9177f14bf328299ca44ce1d0de2c2853124b228e9f6515744ca2813cebba.
Current source pins совпали с независимым review.

AEC3 verified cache прошёл native VerifyBuildArtifacts с source identity
846fe90a289f58b7c9303a635142aa2c7caa93e5. Полная solution на shared path
не дала подтверждённого terminal result: prlctl exit255, не BUILD_PASS.
Для solution на Windows-local source restore exit0, build ещё идёт.
Установленный GRAF0.1.0.11 и user state не обновлялись. Микрофон, реальная
запись, migration, playback и реальный сервер не использовались.

Governance, frozen bootstrap doctor, YAML parse и git diff --check PASS.
T116 owner #7444 OPEN;119 tasks/93 closed/26 open, markers не менялись.
Commit/push/PR/merge/release не выполнялись. Protected logical IO и все
producer/reader flows, T117/T118, clock/calendar и installed UI gates остаются.

Round204 runtime follow-up: timestamp причина stale RED object подтверждена
отдельно: правильный DesktopHttpTransport.cpp19:42:42Z, прежний object20:09:10Z.
Source hash при этом уже был34bfb5d5; source pin сам по себе не доказывал
свежесть executable. После cmake --build --clean-first выполнена полная
native пересборка и последовательный CTest:34/34 PASS,52.42s,
CLEAN_GREEN_CTEST_EXIT=0. NativeHashFailureTests PASS0.19s. Это завершает
RED→clean GREEN для bounded-hash на exact reviewed bytes, не весь T116.

Round204 solution follow-up: полная GrafWindows.sln Release/x64 на том же
Windows-local source завершилась SOLUTION_BUILD_EXIT=0. VerifyBuildArtifacts
внутри native app project повторно подтвердил тот же AEC3 source identity;
стандартная проверенная библиотека действительно участвовала в app build.
GrafWindowsCoreTests.exe отдельно исполнен:CORE_RUN_EXIT=0. Остались обычные
D9025 /W1→/W4 и C4100 в сторонних AEC3 headers; новый код компилируется со
сохранёнными проверками. Это не утверждение warning-free всего проекта.

SHA-256 новых собственных executable:
- GrafWindowsApp.exe:2b5c4f31c6c42e0e2621389c06910b3bcd4bcb6353f025a28993cf1f4868cc3e.
- GrafWindowsCoreTests.exe:3d9009f07dd612390a3414c461d31552500ebdd5236c27bccd2c3faf6c3bbecc.
- NativeHashFailureTests.exe:05682833f9063ecd217daa690108695772a8370ac88d7657488ff7b7ce1b55c9.

App build не является MSIX/installed acceptance. Новый пакет не подписывался,
не устанавливался и не запускался как UI. Package-only --verify-audio-backend
не запускался на unpackaged executable; непакетный exit2 не был бы backend
acceptance. Source-only Approved и clean native regressions вместе принимают
этот ограниченный hash шаг; T116/T117/T118 и весь Windows goal остаются открыты.

## Round205 — защищённый wire codec v1, ограниченная часть T116

Срез начат 2026-10-02; проверки закончились 2026-10-02 UTC
(уже 2026-10-03 в часовом поясе Europe/Istanbul). Canonical root/branch/HEAD:
`200-windows-followup/crisp`, `codex/200-windows-followup`,
`99b00a579c24b50e320465b69d9a296038bc544d`. High-risk-product, продолжение
принятого отдельного storage-среза, не новый общий допуск F200.
Независимый requirements refresh:
`checklists/review-2026-10-02-custody-codec-gate.md` PASS112/112;
нормативные spec/plan/tasks/contract bytes совпали, T116 owner #7444 OPEN.
Custom markers и tasks не менялись. Автоматические implementation commit
hooks выключены; commit/push/PR/merge/release не выполнялись.

Добавлен `Storage/ProtectedCustodyCodec.*`: in-memory кодирование/чтение
принятого v1, явный little-endian, headers16/104/112B, роли1–9 и entropy
`graf.custody.v1` с store/object/role/kind/selector/version. Реальные Windows
user-scope DPAPI с UI_FORBIDDEN, без LOCAL_MACHINE, описания данных и файла
ключа. Native output очищается перед LocalFree, временный plaintext кодека
очищается и при отказе. Это не обещание очистки pagefile/crash dump или всех
временных копий остальных пока не переведённых компонентов.

Outer exact kind/schema/size bound проверяется до native вызова; decoded
identity/schema/header/reserved/tail/position/version/length проверяется
отдельно. Checksum и payload digest используют существующий потоковый CNG
SHA-256 Windows; отказ провайдера возвращает typed hashFailed, не portable
fallback/empty checksum. Unknown role/flags/schema, DWORD/count/length overflow,
повреждение, неверная entropy или oversized native output не возвращают bytes
как успешное чтение. DATA/ZERO сочетания и точный tail bound проверяются;
invalid/missing DATA не подменяется ZERO. Index generation/slot проверяется,
но выбор authority и подтверждение двух birth slots ещё относятся к store.

Кодек не выполняет filesystem IO, не публикует index, не даёт durable ACK,
не создаёт новую пустую очередь и не назначает normal package. Его наличие
в app solution не означает подключение writer/upload/playback. Non-Windows
native operation явно unsupportedPlatform; host tests не являются DPAPI PASS.
Без новой сторонней зависимости; подключена штатная Windows crypt32 library.

Сначала добавлен executable regression; без реализации target ожидаемо не
линковался. После реализации host build PASS и CTest34/34 PASS19.20s.
Windows-local MSVC19.44/CMake Release/x64 build PASS, CTest35/35 PASS28.01s:
ProtectedCustodyCodecTests PASS2.22s, NativeHashFailureTests PASS0.12s.
Регрессии на generated bytes: block1/4096/65536/262144B, все девять role caps,
maximum262144-entry index, wrong store/object/role/position/version/slot,
outer/inner tampering, reserved/flags/count/schema, exact tail/length, checksum
failure, valid native encryption of malformed plaintext, rechecksummed invalid
index. Existing TU-local CNG fault test переиспользован для seal/open block/index
при Open/Create/HashData/Finish failures и отказе второго hash chunk.
Production injection knobs, устройства и key export не добавлены.

Полная GrafWindows.sln Release/x64 завершилась SOLUTION_BUILD_EXIT=0,
verified AEC3 source846fe90a289f58b7c9303a635142aa2c7caa93e5.
Новый ProtectedCustodyCodec.cpp действительно перекомпилирован app project.
Обычный D9025 /W1→/W4 остался, не подавлялся. Это не warning-free claim.
Установленный GRAF0.1.0.11 не обновлялся; нет нового MSIX/подписи/installed UI
или audio acceptance. VM остаётся ARM64 Parallels с emulated x64, не физический
x64. Реальных записей, микрофона, миграции, playback и wire upload не было.

SHA-256 текущих локальных исходников (не новый commit):

| Файл | SHA-256 |
| --- | --- |
| Storage/ProtectedCustodyCodec.cpp | 0680f09b8f58f3c074a97e8881657a6c1bcd6712b2eea1b7ababb9be4d9ff107 |
| Storage/ProtectedCustodyCodec.h | 41f14876953475997fac960bc6a466c10887646ade952890affc3af15fe35633 |
| Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp | da8cc416ecf33526249c458e279caf63fc456d738ed5cbda6613334ed217a491 |
| Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp | 813bc9c32a14a1189a67c61593545ca6094c1c02e477fa69dc3c5fff7f46efb0 |
| CMakeLists.txt | 5d9e84c3c4a81751f07c9441c3e9b83d8a379ec8a2c289c5099fcc9c44c15c40 |
| RecApp/GrafWindowsApp.vcxproj | 2f99db451738cd961df7abcaea51ab231bf26ae9c297f5ff76d7fe2537837c64 |

Независимый source review идёт отдельно; runtime PASS не подменяет его.
Следующая обязательная часть: durable confined file IO/две index slots,
commit acknowledgment и recovery authority, далее IStream/MF adapters и
перевод всех producers/readers. T116/T117/T118 и вся Windows приёмка открыты.

Round205 source/identity follow-up: независимый обзор
`checklists/review-2026-10-02-custody-codec-source.md` Approved source only,
0 blocking findings; Ponytail Lean already. Шесть canonical/mirror/native
source hashes совпали. Full solution core executable отдельно выполнен:
CORE_RUN_EXIT=0. GrafWindowsApp.exe SHA-256
be48dfec0cb5c5f9d36987097b0970854069fa04fdaf4e9072582b7e422c7400;
это новый непакетный build, не установленная версия. Reviewed source pins
не изменились после обзора; reviewer не выполнял main runtime checks.

В отдельной disposable source-копии временно удалён только payload checksum
rejection. Windows ProtectedCustodyCodecTests действительно упал на line134:
успешно расшифрованный, но изменённый block ошибочно принимался.
NEGATIVE_CONTROL_CTEST_EXIT=8/0xc0000409. Это ожидаемый контроль причинности,
не исправленный product дефект: canonical source всё время содержал guard.
Правильный source восстановлен и его hash проверен до --clean-first rebuild;
результат повторной чистой проверки фиксируется отдельно после завершения.

Round205 clean GREEN: после возврата reviewed codec выполнены чистая native
пересборка всех CMake targets и последовательный CTest35/35 PASS27.49s,
CLEAN_GREEN_CTEST_EXIT=0. Codec PASS1.82s, hash-fault PASS0.12s. Это завершает
контроль повреждения RED→clean GREEN; в канонической рабочей копии checksum
guard не удалялся. Governance, frozen bootstrap doctor, F200 YAML parse и
git diff --check PASS. Root/server/macOS product code и root CHANGELOG не
менялись. T116 marker не закрыт: primitive source/runtime PASS не принимает
весь protected-storage pipeline или установленный Windows.

## Раунд 206 — ограниченный файловый слой защищённого хранения

Дата среза: 2026-10-02 UTC; локально уже 3 октября, Europe/Istanbul.
Рабочая копия: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`,
ветка `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Проверены рабочие байты, включая
новые файлы, а не утверждается наличие реализации в HEAD. Lane:
**high-risk-product**, частичный T116; commit/push/PR/merge не выполнялись.

Добавлен `ProtectedCustodyFiles.h/.cpp`: только ограниченное физическое чтение
и сохранение уже зашифрованных блоков/индексов. Он использует принятый codec,
проверяет владельца и точный размер до записи и после повторного открытия,
выполняет полную запись и `FlushFileBuffers`. Блоки неизменяемы, создаются через
CREATE_NEW; существующий блок нельзя затереть. Ошибка записи блокирует следующие
записи этого экземпляра. После попытки публикации неопределённый результат
остаётся ambiguous; артефакты сохраняются для последующего восстановления.
Физический published **не означает logical commit ACK**: выбор поколения,
проверка обоих slots, metadata birth g1 pair, общий резерв памяти, snapshots,
pins, migration, GC и подключение производителей/читателей ещё не реализованы.
Действия только на worker; резервирование памяти — обязанность вызывающего слоя.

Существующая проверка `DesktopUploadQueueService::validIdentity` сделана публичной
для повторного использования без копии её логики. Новые исходники зарегистрированы
в CMake и product vcxproj; новых зависимостей или production fault knobs нет.
На non-Windows файловая операция явно unsupportedPlatform, без plaintext fallback.

Независимый допуск требований: `review-2026-10-02-custody-durable-io-gate.md`
PASS112/112, SHA-256
`d118ca80b707ab20846db29e34cd4a05c49e76ff9fc9692ca113d5efbc808cb0`.
Независимый просмотр окончательных исходников:
`review-2026-10-02-custody-files-source.md`, Approved source only,
0 blocking findings, Ponytail LeanAlready/net0. Reviewer не запускал VM или
сборку; результаты ниже получены основным агентом. Markers reviewer-owned
checklists и задачи не изменялись ради реализации.

При проверке найден реальный дефект: доступ только к атрибутам каталога не
участвовал в запрете совместного открытия для удаления/записи. Добавлен
`FILE_LIST_DIRECTORY`; вся проверенная цепочка предков остаётся открытой без
share-write/delete до уничтожения объекта. Прямые DELETE/GENERIC_WRITE открытия
теперь обязаны завершаться ERROR_SHARING_VIOLATION. Защищённый DACL с единственным
full-access ACE текущего пользователя задаётся при создании, до первого write.
Проверяются фактический handle/path, локальный fixed volume с ACL, отсутствие
reparse points и единственная hard link. Идентификаторы не создаются заново
вместо отсутствующего/повреждённого store.id; чужой object.id не принимается.

Отдельные native опыты только с искусственными каталогами выявили, что Win32
rename wrapper не подходит при сохранении строгих parent locks: RootDirectory
давал 87, абсолютное имя — 32, а простое имя с NULL root зависело от process CWD.
Такие варианты не оставлены в реализации. Использован штатный
`NtSetInformationFile` из уже загруженного ntdll с FileRenameInformation (10),
простым фиксированным именем `index.0/1` и NULL root: native same-directory rename.
Synchronous handle принадлежит этому слою; проверяются NT return и IOSB.Status,
после rename — фактический целевой handle, flush и validated reopen. Locks не
отпускаются, DLL не загружается через поиск, резервного небезопасного пути нет.

Все шесть окончательных исходников совпали по SHA-256 в canonical root,
Windows-зеркале и отдельной Windows-local копии:

| Файл относительно `apps/windows` | SHA-256 |
| --- | --- |
| `RecApp/Storage/ProtectedCustodyFiles.h` | `1a8ba5ad54618b66ccf651b74489b6f03c220f28470e35a14a7d6aaa9cd02aac` |
| `RecApp/Storage/ProtectedCustodyFiles.cpp` | `a04e33b1261dd9a429ee7612e41713c7eeea5e2c37e9530ffdebd42ff547988a` |
| `Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp` | `5df8f9a15df74710ee474f74916cf6c61b639323c79d08c453d6a37d691a934f` |
| `RecApp/Upload/DesktopUploadQueueService.h` | `e975df4077df25c8c021487b88ee8e60c3e51947b319062c2fce2a4600775418` |
| `CMakeLists.txt` | `62d81ae52e0269b81f32b6e2aa78f0093e726256dd96d4354090a799bbab561f` |
| `RecApp/GrafWindowsApp.vcxproj` | `4773b9c1b76fd53ad97a83687574153c32f3b7d81d3730450d6df435499c7dca` |

На точном окончательном коде host build PASS; CTest35/35 PASS19.81s в
`/tmp/graf-f200-storage-GWS3Ja`. На Windows 11 ARM64 VM / x64 emulation,
MSVC19.44, Windows-local CMake build PASS; CTest36/36 PASS32.11s,
FINAL_TEST_EXIT=0. Files tests PASS1.27s; codec PASS1.79s; native hash faults
PASS0.11s. Для новых физических IO исходников действует `/W4 /WX`.
Предварительно все targets пересобраны clean-first на предыдущем freeze:
36/36 PASS29.06s; после последней role-bound правки выполнены сборка и полный
повтор на окончательных hashes. Предыдущие hashes не являются final evidence.

На окончательном executable отдельно запущен test-only отрицательный контроль
`--attribute-only-negative-control`: wrapper удаляет FILE_LIST_DIRECTORY только
при открытии test ancestors. Он ожидаемо упал на прямой share-exclusion проверке,
FINAL_RED_EXIT=0xC0000409, assertion line187. Затем обычный запуск полного CTest
без флага прошёл 36/36. Production source не менялся для отрицательного контроля.

Регрессии: wrong IDs, single writer, existing role reset rejection, dot/ADS/UNC,
private ACL до write, junction/hardlink/unprotected-DACL rejection, corrupt/missing
DATA, сохранение неизвестных файлов, partial/zero/failed writes, pre/post flush,
rename, IOSB failure при NT return0, reopen failure и sticky writer. Проверены
max256KiB DATA и 64GiB explicit-ZERO logical index с 262144 entries, без 64GiB
выделения; физический индекс читается/пишется частями не более 256KiB.
Oversized index отвергается до чтения/выделения; manifest payload4097B даёт
invalidInput/0reads до открытия. Повторное открытие проверяет точный envelope,
codec integrity и все referenced block constraints текущей физической операции;
логическая полнота snapshot не утверждается. Test process CWD — другой собственный
искусственный каталог; опубликованный индекс там не появляется.

Финальная GrafWindows.sln Release/x64: FINAL_SOLUTION_BUILD_EXIT=0;
GrafWindowsCoreTests.exe: FINAL_CORE_RUN_EXIT=0. ProtectedCustodyFiles.cpp
перекомпилирован product project. Verified AEC3 source
`846fe90a289f58b7c9303a635142aa2c7caa93e5`.
Существующее D9025 /W1→/W4 осталось; zero-warning solution не заявляется.
SHA-256 собранного, **не установленного** GrafWindowsApp.exe:
`e0192b2b11aae051843cfb2e9aaae655e80b56acb8d5afe6e63700794328faf6`.

Все runtime опыты только на новых искусственных данных текущего Windows-user.
Реальные записи, микрофон, миграция inventory, профиль/ACL пользователя, сервер,
macOS product code, root CHANGELOG и установленный GRAF0.1.0.11 не затрагивались.
MSIX/sign/install/launch не выполнялись. Это не power-loss proof и не physical-x64
приёмка. T116–T118, clock T094–T096, calendar T119, hardware/60min/AEC,
auth/upload/delete E2E, доступность и install/update/rollback остаются открытыми.

## Раунд 207 — проверка защищённого снимка перед выбором поколения

Дата проверки: 2026-10-02 UTC; локальное время Mac — 2026-10-03.
Авторитетная рабочая копия: `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d` плюс незакоммиченные изменения.
Риск: high-risk-product; частичный T116, не закрытие задачи или выпуска.
Spec/plan/tasks/contract, нормативные требования и reviewer-owned markers
в этом срезе не изменялись. Проверки выполнялись на искусственных данных.

Добавлен `ProtectedCustodyFiles::readValidatedSnapshot()`: до выбора поколения
проверяет оба индекса и все referenced DATA, различает отсутствующий index и
отсутствующий DATA. Metadata singleton/invalid блокируется; g1-пара сравнивается
по расшифрованному содержимому, не случайно различающемуся ciphertext.
Для canonical/media допускается только явно обозначенный trustedPrefix с
исходной причиной ошибки и запретом дальнейшей записи. Playback не получает
этого fallback. Verified byte snapshot не означает logical ACK, sealed normal
package или право на upload/delete. Caller reservation/pins/lifetime остаются
обязательными условиями ещё не подключённого логического слоя.

Ошибки CNG/DPAPI, allocation и неизвестные IO отказы передаются отдельно от
подтверждённого повреждения и не превращаются в degraded success. Исправлено
смешение codec hash/native failure с invalidContent во всех Files callers.
Регрессии используют настоящие Files/codec/SHA/CNG и локальные тестовые seams;
production fault knobs, новая зависимость и plaintext fallback не добавлены.

Независимый допуск требований: PASS112/112, все существующие checklist markers
сохранены. Независимая проверка окончательных исходников: Approved source only,
0 blockers; отдельный Ponytail — LeanAlready, net0. Reviewer не запускал VM;
runtime ниже — отдельная проверка владельца, не перенос Round206.

SHA-256 четырёх окончательных исходников:

```text
ProtectedCustodyFiles.h ea531e71be71093abfa31f8c023304098a554f1df442946a1c2fef9b0776990c
ProtectedCustodyFiles.cpp 60770764df0f3e625b9040c6744e07a7891cfa98d9c8a37ccfb37e3d0792d44e
ProtectedCustodyFilesTests.cpp 3353b599c626fe7892b449b6141f82f23cc97a4087364aba036e742eae3ad384
CMakeLists.txt 400b57f98d791a6739aa5be0a7140ce9d63f8d114f14cff305a39d8792eb141d
review-2026-10-02-custody-snapshot-gate.md 2c50e60558ccbdc15ef5c8abc25b6864e994f85010fcd9197bc34e3dd439e5b4
review-2026-10-02-custody-snapshot-source.md 67a25e4b77880b0b02a447a0b230dc7e73ccf0190f3dc4b5ed3a4fa34d156081
```

Перед реализацией тестовый target давал C2039/missing method/exit1.
На окончательных исходниках host build и CTest35/35 PASS19.51s;
Windows native CMake all-build exit0, CTest36/36 PASS31.80s.
GrafWindows.sln Release/x64 exit0 и GrafWindowsCoreTests.exe exit0.
Host не доказывает работу DPAPI; Windows — ARM64 Parallels с x64 emulation,
не физическая x64 приёмка.

Отдельный отрицательный контроль только в зеркале и native synthetic build
намеренно заменил hashFailed на invalidContent. Variant SHA-256:
`2b5c464cb69994754e7e7fe6f8c161be15e2701cc338f61642da6e4a92a810f1`.
Сборка focused FilesTests exit0, тест обнаружил подмену:
`!result.ok() && result.error == expected`, line239, exit `0xC0000409`.
Авторитетные исходники не менялись этим опытом; mirror восстановлен и сверён,
native CPP восстановлен с финальным hash60770764… перед clean-first all-build.
После восстановления **все 36 тестов снова PASS31.93s**, clean-test exit0.
Таким образом, результат относится к восстановленному коду, не fault variant.

После восстановления повторно проверено равенство всех четырёх source pins
в зеркале и native build tree. Product solution повторно компилировала
ProtectedCustodyFiles.cpp; SNAPSHOT_RESTORED_SOLUTION_EXIT=0,
SNAPSHOT_RESTORED_CORE_EXIT=0. SHA-256 повторно собранного, **не установленного**
GrafWindowsApp.exe:
`2837edf0e8c2387d8ac8ab09f279a6482a1844d0f4778050c932222ce1ed03ea`.
Существующее предупреждение D9025 сохранено, zero-warning claim не делается.

После записи отчётов: check_spec_kit_governance.py PASS,
speckit-bootstrap --doctor --frozen PASS, F200 YAML parse PASS,
git diff --check PASS. T116/T117/T118 и reviewer-owned markers не закрывались.

GitHub T116 issue #7444 проверен read-only и остаётся open. Whole T116,
logical read/write/seek/commit и metadata birth ACK, общий бюджет/pins/cache,
асинхронные результаты и вся запись/очередь/воспроизведение ещё не подключены.
T117 migration/GC и T118 full-storage/installed acceptance не закрыты.
Реальные записи, микрофон, пользовательские ACL, сервер, macOS product code,
root CHANGELOG и установленный GRAF0.1.0.11 не затрагивались.
Commit/push/PR/merge, MSIX/sign/install/launch не выполнялись; готовность
приложения, power-loss guarantees и выпуск не заявляются.

## Раунд 208 — общий бюджет реальных custody allocations

Risk lane: high-risk-product, частичный T116. Canonical root/branch/HEAD
остаются как в Round207; source SHA — `99b00a579c24b50e320465b69d9a296038bc544d`
плюс незакоммиченные изменения. Новых нормативных требований, изменений
spec/plan/tasks/contract, checklist markers, GitHub или commit нет.
Независимый requirements gate PASS112/112 допускает этот ограниченный этап.

`CustodyBytes` и `CustodyIndex::entries` теперь используют один process-wide
64MiB allocator. Он резервирует requested capacity до std allocation, включая
одновременно живые old/new buffers при росте; overflow отвергается до умножения.
Copy получает отдельный charge, move/swap/optional result сохраняют его до
actual deallocation; clear не освобождает живую capacity. Underlying allocation
exception откатывает reservation. Все четыре codec API передают bad_alloc как
typed allocationFailed; Files не превращает её в corruption/missing/fallback.
Существующие wipe, post-publish ambiguity и retained-artifact guards сохранены.

Это **не доказанная квота всего приложения**: неохваченные JSON/string/CNG/hash/
upload/CopyTo/job buffers, cache2MiB, dirty≤4blocks/1MiB и pins/clones≤32 на
процесс ещё требуют реальной интеграции. Requested buffer capacity не означает
resident heap/allocator overhead либо MF/DPAPI internal allocation measurement.
Счётчик не является GC/pin registry, не выдаёт logical ACK и не освобождает
права аккаунта/удаления. Нового самостоятельного manager или зависимости нет.

Сначала добавлены регрессии: новый host build отвергал отсутствующие
CustodyOwnedMemory/CustodyAllocator (exit2). После реализации host focused PASS.
Первый native focused build exit0: Files PASS, Codec test упал на assert81,
exit0xC0000409; CTest exit8. Причина — test-size portability, не production quota:
MSVC14.44.35207/std allocator для4096B увеличивает operator-new request ради
alignment, поэтому fault по точному4096 не включался. Первичные Microsoft STL
исходники и фактический installed xmemory подтверждены read-only:
threshold4096, release overhead sizeof(void*)+alignment−1.
Исправлен только test request/fault на1024, ниже threshold; assertions и лимит
не ослаблены. Добавлен прямой include type_traits. Source reviewer закрыл
замечание на final freeze: Approved source only,0 blockers; Ponytail LeanAlready.

Финальные source SHA-256:

```text
ProtectedCustodyMemory.h 8a0fe8e357935c745f860cc35d30220943410b65300d1c2f9bbb98a4bb5383aa
ProtectedCustodyCodec.h 6ac5de213ce896730d87a497d512070dd55a5b496b322c38fdb2c57fa2ed53e6
ProtectedCustodyCodec.cpp 148899142a1568f9bc01c47ab63de07f3b5f8854a05faec8ed3b2e2775963fea
ProtectedCustodyFiles.cpp a39ee45d37a7e89837aafb159c3508809e06b2528a66e1cce10bf978815d1625
ProtectedCustodyCodecTests.cpp 6209b8735fb4fa4d31871d52451832732ec60cfbee7e3041d886f650c710e948
ProtectedCustodyFilesTests.cpp 4919f3a68586779a70ceaebfc1e6b3b07e5ce0e571e87833d7e31c3ea091709d
resources-gate.md 172904d20b14785f8572456a203cc560ab1c38b0583e3954ee62d99aaa4ee2d9
resources-source.md d19390c4a30cb0a943d5ed4e2bd5f8e32a36f282c105cd61841477742941ff59
```

На final freeze: host all-build exit0, CTest35/35 PASS14.90s;
Windows all-build FINAL_RESOURCE_BUILD_EXIT=0, CTest36/36 PASS29.54s,
FINAL_RESOURCE_TEST_EXIT=0. Проверены capacity разных типов, copy/move/results,
clear/swap/deallocation,40+48MiB peak refusal/сохранение старых bytes,
exact64MiB/overflow, real std-allocator failure rollback и12-thread admission.
Real codec/Files cross-TU отказ при заполненном бюджете возвращает allocationFailed;
disk-read/write callbacks0, snapshot failure sticky даже после release бюджета.
Это не новые проверки real capture/whole100cycles, не hardware acceptance.

Все шесть final pins зеркала/native source повторно совпали. Полная
GrafWindows.sln Release/x64 перекомпилировала codec/Files, весь product LTCG:
RESOURCE_SOLUTION_EXIT=0; GrafWindowsCoreTests.exe RESOURCE_CORE_EXIT=0.
AEC3 identity verified `846fe90a289f58b7c9303a635142aa2c7caa93e5`.
D9025/W1→W4 сохранился, zero-warning claim нет. SHA-256 собранного,
**не установленного** GrafWindowsApp.exe:
`ed006e8fa9f4e5308fd5b4325ac63d044b9a62bade6bf217960c90f6e72d759b`.

T116 целиком, T117/T118, logical IO/ACK/cache/pins/async/native consumers,
hardware/clock/calendar/installed/UI/accessibility/release остаются открытыми.
Windows испытания только на новых искусственных данных текущего пользователя
в Parallels ARM64/x64 emulation; физическая Windows x64 не заменена.
Микрофон, реальные записи, миграция, установленный GRAF0.1.0.11, macOS product
code, сервер, root CHANGELOG, MSIX/sign/install/launch не затрагивались.

После записи отчётов: check_spec_kit_governance.py PASS,
speckit-bootstrap --doctor --frozen PASS, F200 YAML parse PASS,
git diff --check PASS. Before/after implement hooks остаются disabled;
implementation commit не выполнялся, задачи и issue markers не закрывались.

## Раунд209 — защищённый read-only IStream, 2026-10-03

Risk lane: high-risk-product, последовательная ограниченная часть T116.
Canonical root/branch прежние; HEAD `99b00a579c24b50e320465b69d9a296038bc544d`.
Spec/plan/tasks/contract SHA совпали с Round208; изменения норм, task markers,
GitHub sync/closeout, commit/push/PR/merge не выполнялись. Before/after implement
commit hooks disabled. Независимый requirements gate:112 checked/0 unchecked,
анализ/владение accepted storage-среза применимы к неизменным нормативным bytes.

Реальная трассировка до кода: V5LocalRecordingWriter всё ещё пишет canonical/WAV
и использует MFCreateSinkWriterFromURL; LocalRecordingPackage проверяет AAC через
SourceReaderFromURL; transport/hash читают обычные пути. Новый reader — необходимый
общий logical IO слой, но пока не замена этих consumers или защищённое приложение.

Добавлены native-only ProtectedCustodyReader.h/.cpp и регистрация product TU
в vcxproj; CMake использует существующий common GLOB. Factory самостоятельно
открывает confined Files/readExisting и validated snapshot. Shared State владеет
Files/context/index/cancellation; каждый живой stream/Clone удерживает реальный
snapshot до actual release. CAS ограничивает process32 holders, включая Clones.
Общий process cache — один charged/wiped блок≤256KiB, key State lifetime+position;
Clone не копирует plaintext или индекс. Не GC/persistent pin registry.

Read проверяет точные DATA/tail и authenticated ZERO; EOF короткий=S_FALSE/got exact,
native/semantic/allocation/cancellation failure sticky/shared, got0, без продвижения
cursor, скопированный prefix обнулён. Seek проверяет signed INT64_MIN/overflow;
за EOF ничего не создаётся. Write/SetSize запрещены, unsupported flags/locking/
revert не S_OK; STGC_DEFAULT — read-only status/no-op, не durable commit/ACK.
CopyTo передаёт≤256KiB charged/wiped chunks и удерживает source/target COM ownership
через callback без global IO lock. Фактически принятый target prefix не откатывается.
Worker-only open/read/last release и caller account/epoch/package authority явны.

### Регрессии и независимая проверка

Первый TDD RED: отсутствующий Reader header, native build exit1. Это missing API,
не поведенческое доказательство. Начальные focused/full PASS были промежуточными.
Независимый source review затем обнаружил P2: last target callback отменяет source
либо фиксирует shared fault через Clone, но CopyTo возвращает S_OK/S_FALSE.
Добавлен настоящий test-only COM CallbackSink без content retention: native
compile0, assertion:268 на старом reader,0xC0000409/CTest8 за3.03s — meaningful RED.
Исправление: post-callback shared status до successful continuation/return;
фактические read/written и target error/status сохранены. После повторного review:
Approved source only/0 blockers, Ponytail LeanAlready/net0. Runtime reviewer не
запускал; отдельные подтверждения ниже получены main.

На искусственных защищённых snapshots проверены full/tail/ZERO/cross-block/EOF,
negative/overflow Seek, independent cursor/cache shared charge, pinned generation
при изменении current index, lifetime после release исходного stream, process32
across objects/roles и40 concurrent Clone holders с barrier,40 failed-open admission
rollbacks. Partial native Read fault/got0/shared sticky Clone, cancellation0IO,
Read/CopyTo actual allocation refusal и возврат charge к baseline. Callback cases:
last exact4/EOF4of8 cancellation, reentrant Clone fault, short2/4, target error2/4,
target S_FALSE4/4 и фактические bounded full CopyTo chunks. Настоящий
MFCreateMFByteStreamOnStream/IMFByteStream подтвердил read-only capabilities,
length/seek/exact tail Read; adapter released before MFShutdown. Не AAC decoder
или MediaEngine playback/installed acceptance.

### Окончательный срез и runtime

| Файл | SHA-256 |
| --- | --- |
| ProtectedCustodyReader.cpp | `af45e6f5bc2c8450c539c9790adc33ec792493b58df79eaf51292b2f43e545f9` |
| ProtectedCustodyReader.h | `d1dc47e71865bd09a67cde2fe281e9be24a92fae690a9a8b2ea90f6f8b6a91b4` |
| ProtectedCustodyFilesTests.cpp | `07f2b47d51cbb5ef4a2b1ca9f0c02791b56eb896f9ccca60003e3cd0210d8a47` |
| GrafWindowsApp.vcxproj | `89d4fb98b1af8ec0ed19ccd4000f45dd55ceca7cdf0dc95459cf378c893a0c55` |

Все четыре source SHA canonical/mirror/native совпали после окончательной сборки.
Прежние Files/codec/allocator/CMake dependencies не изменены.
Во время guest command execution возникали Parallels SDK Invalid argument/session
ошибки; одна копия теста осталась старой. Hash gate это отверг: промежуточные30.00s
PASS не использованы как final proof. Повторная явная copy/readback дала exact SHA,
затем новый build и полный последовательный CTest на окончательных bytes.

- Host `/tmp/graf-f200-resources.81h6xy`: build0,35/35 CTest PASS за19.60s.
  Windows-specific reader assertions на host не исполняются; это portable lane.
- Windows11 ARM64 Parallels/x64 emulation, current-user: final CMake build0,
  CTest36/36 PASS за32.52s; Files/reader test2.73s, FINAL_READER_TEST_EXIT=0.
- Final GrafWindows.sln Release/x64 build0, reader TU перекомпилирован;
  GrafWindowsCoreTests.exe exit0. AEC3 identity846fe90a289f58b7c9303a635142aa2c7caa93e5
  verified. Existing D9025/W1→W4 остаётся: не zero-warning claim.
- SHA-256 собранного, **не установленного**, GrafWindowsApp.exe:
  `1044836bc1bb3b0b3c87b713c0ef0fba9b3f32f093d6bc84d21fd8165217c0b9`.

Requirements report SHA `ef0f98093ad744030f93f5681c8e8741ba7362ef6b54834fac32a61d45ce7b1b`;
source report с append-only закрытием P2 за2026-10-03:
`6d45bdf31dc183bb4496612aa4c332c54df4a60bbd2fca7471615be2a73b2fc8`.

Открыты T116 целиком: writable logical stream/commit/ledger/package-state,
async tickets/adoption, все producers/readers/hash/upload/native playback,
полная process quota/dirty/result limits и account/delete/shutdown интеграция.
T117 migration/GC, T118 installed acceptance, hardware/60min/clock/calendar/UI/
accessibility/signing/release не закрыты. Следующий последовательный шаг —
protected logical writer/commit authority до подключения существующих consumers.
Микрофон/реальные записи/миграция/MSIX/sign/install/launch/macOS product/server/
root CHANGELOG не затронуты. После записи отчётов повторно прошли
check_spec_kit_governance.py, speckit-bootstrap --doctor --frozen,
F200 YAML parse и git diff --check; источник и reviewer markers неизменны.

## Раунд210 — полное защищённое сохранение метаданных, 2026-10-03

Risk lane: high-risk-product; последовательная часть T116, не уменьшение
конечной цели Windows. Canonical root/branch прежние, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`; проверены prerequisites и открытый
owner T116/#7444. Нормативные spec/plan/tasks/contract/data-model/quickstart/
constitution bytes совпали с Round209. Requirements reviewer gate:112/112,
новых пробелов требований0; checklist markers main не менял. Accepted analyze
и ownership применяются к неизменным нормам, новый полный analyze не заявлен.
Before/after implement commit hooks disabled. Commit/push/PR/merge отсутствуют.

### Реализация и границы

ProtectedCustodyMetadata.h/.cpp реализуют worker-only full-value persistence
для manifest/recovery/package-state/queue/bootstrap/migration-intent.
Caller по-прежнему отвечает за semantic JSON, account/epoch и admission.
base0 — exclusive NEW object, не автоматическое исправление отсутствующего
или повреждённого authority. Update принимает только verified exact base.
Каждый DATA блок immutable: потоковая проверка имён учитывает orphan versions,
отказ enumeration/overflow не превращается в пустой inventory; version не
повторяется и неизвестные артефакты не удаляются. Используются существующие
DPAPI codec, Files, DACL/confinement, flush/rename/reopen, без нового IO слоя.

До content writes проверяется physical peak с запасом места по фактической
ёмкости тома и округлением файлов, а не CallerTotal/quota. Это не резервирование
места против внешних writers и не замена inventory/device/account limits.
Один staging mutex ограничивает dirty chunk≤256KiB/process; существующий charged
allocator удерживает64MiB до actual release. Общий CustodyPin объединяет reader,
Clone и metadata result/waiting admission в32 holders/process. Private pin
уничтожается после snapshot/Files: return/future completion не освобождают
реальные handles и право удержания преждевременно.

Birth предварительно seal обе копии g1 и независимо reopen обе; update публикует
один следующий slot. Cancel до публикации запрещает commit; после её начала
worker завершает g1 pair/reopen, не выдавая UI cancellation за rollback.
Final acceptance требует exact generation/length/entries, не только valid bytes.
Результат committed/notCommitted/ambiguous сохраняет первоначальный native error.
Это НЕ async ticket/adoption, package sealing или разрешение upload/delete/GC.

### Независимый P1 и настоящий RED→GREEN

Первый missing-header RED и предварительные PASS не поведенческая приёмка.
Source reviewer нашёл P1: после slot0 success второй publish мог отказать на
hash/RNG до create, а retained Files оставался writable при ambiguous result.
Реальная регрессия: afterRename первого slot инжектирует hashOpen ordinal2,
снимает fault и проверяет отказ новых записей. До исправления native build0,
assert:258,0xC0000409/CTest8 (session35480) — meaningful RED.

Исправление в общей точке: terminal reject при retained lease вызывает
Files::blockWrites noexcept, устанавливающий существующий failed state.
Это охватывает также exact-target mismatch и notCommitted с реальным lease,
не меняет исходный error/state и не закрывает handles/pin/artifacts.
Тест проверяет writerFailed для version/write/publish, отсутствие новых native
writes, readable slot0, exclusion второго writer, сохранение block.0.1 и
отклонение singleton при fresh restart. GREEN session11602: build0,
FilesTests1/1 PASS4.39s, total4.45s, STICKY_GREEN_TEST_EXIT0.
Независимый повторный source review Approved/0 blockers; P1/RequestChanges
сохранены append-only. Ponytail: LeanAlready/net0. Reviewer не выполнял тесты.

На искусственных данных дополнительно проверены g1/g2/shrink и старый reader,
caps всех шести ролей, queue4MiB/16 блоков, cancel/cuts/reopen, immutable orphan,
enumeration/overflow, disk reserve и32-holder/64MiB admission. Дополнительные
staging-wait cancellation и valid-but-wrong final snapshot runtime cases не
заявлены покрытыми; соответствующие source paths идут через общий reject.

### Окончательные источники и terminal evidence

SHA-256 от canonical root; это dirty source freeze, не новый Git commit:

| Файл | SHA-256 |
| --- | --- |
| ProtectedCustodyMetadata.h | `3afe6f936d70c6e94c104c4dad7772dc2a420a7f13f572ff359a13f68d362302` |
| ProtectedCustodyMetadata.cpp | `7e9c23aed46905cbcc61e473ecc0941a6d006b0ce9addcae35db648cb10cc6b9` |
| ProtectedCustodyFiles.h | `3b7e8fb45bce2ac3ff084af1e482a88c8f1ce277fe35b0149cf7a7383b614e0f` |
| ProtectedCustodyFiles.cpp | `eb712a38f76eb5374f6ee4e3d964d15fb5ef92db2e212d20c77a166fd69bf142` |
| ProtectedCustodyMemory.h | `13d3cff525a76976d1462f21848c088b154d01fa169553c48f0867bd9a81d64b` |
| ProtectedCustodyReader.cpp | `5f39f669cccb80e8be73582fc806ff6810e44003b5cb6ba28147c951571978c2` |
| ProtectedCustodyFilesTests.cpp | `3d2c6dda5f1d7c8a01b455a214ea340d21dccfc92a6621d70b72534d1167fc34` |
| GrafWindowsApp.vcxproj | `abcd92596cc2f763ecdced8cbd9f7ac277964be968a24d755eb3345fda7aba54` |

- Native CMake build0, CTest36/36 PASS32.19s, Files3.86s,
  FINAL_NATIVE_CTEST_EXIT0 (session58977).
- Host CMake build0, CTest35/35 PASS19.85s (session44286).
- VS GrafWindows.sln Release/x64 build0, coreexe0 (session57358).
  AEC3 identity `846fe90a289f58b7c9303a635142aa2c7caa93e5` verified.
  Existing D9025/W1→W4 warning остаётся, не zero-warning claim.
- После сборок восемь source/test hashes в mirror/native совпали
  (session85704 FINAL_SOURCE_MATCH=True); canonical/mirror apps/windows
  checksum сравнение также не нашло различий содержимого.
- SHA-256 собранного, **НЕ установленного**, GrafWindowsApp.exe:
  `c4920d176ae56f3a3aa30b38b55de6aae40ae1ffc06ec125f33d4cfdff4dbcb3`.

Две длинные combined prlctl команды завершились255 до guest session,
не запускали сборку/тесты; раздельные команды дали terminal0. Ранний временный
GLOB/link failure и неверное тестовое ожидание Clone HRESULT исправлены до
окончательной проверки; не выдаются за продуктовый отказ или final PASS.

Requirements report SHA `a8d3c46fdfa4c8afbd01c90a586261a6d38aac357d4152f5d2bfc6d37159185c`;
source report с append-only P1 re-review SHA
`87a89433a92b3d13d1ae8195e13769c7e952aacfc222c3654eae80046f336967`.

T116 целиком открыт: writable logical stream, semantic authority/adoption,
async workers и подключение всех producers/hash/upload/playback/recovery.
T117 migration/GC, T118 installed acceptance, clock/calendar/UI/accessibility,
hardware x64/60min/AEC, auth/upload/delete E2E, clean-image install/update/
rollback и доверенная подпись внешнего выпуска не закрыты. Parallels ARM64/x64
emulation не заменяет физическую Windows x64. Следующий шаг — writable logical
IO и authority по принятому плану, не новые задачи вместо полной цели.
Микрофон, реальные записи/миграция, установленный GRAF, MSIX/sign/install/launch,
macOS product/server/root CHANGELOG не затрагивались. После записи отчётов
повторно прошли governance, frozen doctor, YAML parse и diff check; canonical/
mirror отчёты и fragment побайтно совпали. Задачи/GitHub issues не закрываются
на основании одного worker primitive.

## Раунд 211 — writable media core, полное восстановление рабочей копии

Дата: 2026-10-03, Europe/Istanbul. Risk lane: high-risk-product,
продолжение T116/#7444; полная Windows цель и требования не сокращены.
Ветка `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`; это dirty source freeze,
не новый implementation commit.

### Восстановление и актуальный источник

После прерывания отсутствовали исходная рабочая папка и handles команд.
В Git найден полный снимок `e6ac0105029682daef08116f8defb36167f93f2e`,
созданный `startup-cleanup` 2026-10-03 05:00:20 +0300, с родителем HEAD выше.
Он содержит новые исходники, актуальные нормы и оба завершённых отчёта обзора.
Восстановлена отдельная долговременная рабочая копия:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Существующая регистрация Git исправлена через worktree repair; ветка, HEAD,
индекс и пользовательские изменения не сбрасывались. Объекты 239 файлов
apps/windows, specs/200-windows-desktop-app, F200 и constitution побайтно
совпали со снимком до следующего изменения тестов. Новый feature.json
указывает feature200/ветку/текущий HEAD; он остаётся ignored локальным состоянием.

Mirror `/Users/yshishenya/Documents/graf-windows-followup-200` содержит свежий
Windows код, но устаревшую часть нормативных документов. Он НЕ использован
как полный источник восстановления: spec/plan/tasks/constitution взяты из
подтверждённого полного Git snapshot. Codex attach_worktree сообщил, что новая
папка не является managed worktree; UI attachment не заявляется. Это обычный
зарегистрированный Git worktree вне удаляемого каталога `.codex/worktrees`.

### Реализованная область и независимая проверка

ProtectedCustodyWriter — один worker-only владелец для canonical/media/playback:
seekable writeAt/readAt/SetSize, exact DATA и explicit ZERO, перепись header,
shrink/extension без возврата обрезанных bytes; общий DirtySlot4 и Pin32,
charged owned64MiB. Canonical публикует каждый полный256KiB block,
explicit checkpoint сохраняет tail. ACK только после independent full
validated reopen и exact target; ошибка poison реальный retained Files,
сохраняет artifacts/lease и запрещает следующую mutation. Отмена до publication
не ACK; после его начала finish/reopen даёт committed либо ambiguous.
Это НЕ COM/MF adapter, async adoption actor или подключение всего приложения.

Requirements report `review-2026-10-03-custody-media-writer-gate.md`:
PASS112/112, CRITICAL0/HIGH0. Source report
`review-2026-10-03-custody-media-writer-source.md`: Approved текущий code freeze,
Ponytail net0; reviewer не исполнял runtime. Его P2 замечания к точным fault,
reopen/base и bounds/cancellation тестам остаются отдельной проверкой,
не выдаются за закрытые этим решением. Checklist/task markers не менялись.

### Источники и наблюдённые проверки

| Файл | SHA-256 |
| --- | --- |
| ProtectedCustodyWriter.h | `4458449d2b9443178c879ccd15ed1a0949bc071e11f6bf2036d085ad67e9f381` |
| ProtectedCustodyWriter.cpp | `b97a8a3cee2cfe3bd5cb6992b41b34d6394d7b2fef8ddc5be6fa840165b80e2f` |
| ProtectedCustodyFiles.h | `4b92692a1d4f67287574b3e912029fb350955861513ec668c82582c9c43f5367` |
| ProtectedCustodyMemory.h | `3a9e8e8637a21bb4be42a9167d5b7df9f5ebe5f80cd01a29761053b077b005c9` |
| ProtectedCustodyMetadata.h | `de7ba1eba3e7f26a28cb1b73461a42f4402f1f0c49adbe7e9ad1040e46af5cf0` |
| ProtectedCustodyMetadata.cpp | `d35f8e5d142bcc45a648baa70b7c8155a216949b84ae04a3fe1f2213c14397d3` |
| ProtectedCustodyFilesTests.cpp | `bc2ddd63f3737a30d29138473bbed07e0c431b6af6a9279d30d665dce57bac22` |
| GrafWindowsApp.vcxproj | `3e6c9182d440acb7f599b7e587084b8734f52b9419ffcd8fc4fab239c55bf1ff` |

Expanded native focused receipt до прерывания: session97083 build0,
FilesTests1/1 PASS27.69s; subsequent include/ownership-comment-only changes
проверены окончательными hashes, не подменяют initial missing-header/link RED
доказательством дефекта product поведения. Завершённые full CTest receipts
восстановлены read-only из LastTest.log, окончание 2026-10-03 04:59 +0300:
host35/35 PASS, native36/36 PASS, failed0. Windows source/test hashes совпали
с таблицей. Handles первоначальных commands после прерывания недоступны;
сами тесты без причины не перезапускались и terminal code старых handles
не выдуман. Свежие scoped тесты следующего шага будут иметь отдельный receipt.

После восстановления: Visual Studio solution Release/x64 build0,
coreexe0 (session59988); AEC3 identity846fe90a289f58b7c9303a635142aa2c7caa93e5
verified; существующий D9025/W1→W4 warning не означает zero-warning build.
SHA-256 собранного, НЕ установленного GrafWindowsApp.exe:
`34e5cf31bbdc3c07a07d01ed9a7c72613b61a9ddc048ba466acf5eb9b9e37828`.
Frozen doctor, governance, F200 YAML и diff check после восстановления PASS.
GitHub #7444 свежо прочитан и OPEN; closable issues0.

### Незакрытые ограничения

Полная проверка всех DATA refs при каждом full-block checkpoint даёт
кумулятивную O(n²) стоимость для растущего canonical. Короткие тесты НЕ
доказывают realtime/60min/SC-003. Следующий ограниченный probe измеряет только
детерминированные искусственные bytes; нормы и full validated ACK не ослаблены.
T116 целиком, T117/T118, clock/calendar, установленный UI, accessibility,
auth/upload/delete E2E, hardware x64/60min/AEC, clean-image install/update/
rollback и внешняя доверенная подпись остаются открытыми. Микрофон/реальные
записи/миграция/MSIX/install/launch, macOS/server/root CHANGELOG не затронуты;
commit/push/PR/merge/release не выполнялись. Следующий шаг — закрытие точных
writer test gaps и измерение скорости перед дальнейшей COM/MF/V5 интеграцией.

## Раунд 212 — регрессии writer и измеренный предел скорости (2026-10-03)

Рабочая копия: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Это проверка изменённых файлов,
не проверка установленного приложения и не свидетельство нового commit.
Продуктовые исходники writer сохраняют hashes раунда 211.

### Синтетические регрессии

Расширен только `ProtectedCustodyFilesTests.cpp`: проверены точные результаты
неуспешного/неопределённого сохранения, запрет дальнейших операций после отказа,
сохранение артефактов, освобождение квот, отмена до публикации, отклонение
недопустимых размеров до IO, переход g1→g2 и конфликт устаревшего основания.
Добавлены отдельные, не входящие в обычный CTest, конечные пробы 16/64 МиБ.
Они используют детерминированные искусственные bytes и временную Fixture;
не читают микрофон, не открывают пользовательские записи и не принимают
неограниченный размер входа. Параллельного запуска native custody тестов нет.

Окончательный SHA-256 test TU в рабочей копии, зеркале и native source:
`7dc2b317729df8dc5410ee9c3e37dfebf543385980dd7c984c2a63626abd270c`.
Независимые требования и source review раунда 211 сохранены; дополнительный
source review проверил test-only изменения, не распространяя одобрение на
COM/MF/V5 интеграцию или всю T116.

Свежая macOS portable сборка в `/tmp/graf-f200-recovered.yQYDxv` завершилась
с кодом 0; CTest 35/35 PASS, 30,06 с (session37485). Новый каталог нужен,
поскольку прежний CMake cache ссылается на исчезнувший source path;
cache и чужие рабочие копии не удалялись.
Свежий native Windows CTest Release, `-j1`, завершился с кодом 0:
36/36 PASS, 73,48 с (session36857). Полная VS сборка и отдельный core test
раунда 211 относятся к тем же продуктовым исходникам, но предшествуют
последнему расширению test TU; они не выдаются за повторную VS проверку теста.

### Проба 64 МиБ — блокер realtime, а не PASS производительности

Native build0 и `--writer-throughput-probe-64mib` exit0 (session86151).
Проба выполнила 256 подтверждённых checkpoint, без notCommitted/ambiguous;
после release ownedBytes0, все счётчики типизированных отказов0.
Последний вызов WriteAt включает автоматический checkpoint и весь validated ACK.

| Размер, МиБ | Общая длительность, мс | Последний WriteAt, мс | Read calls | Hash-open calls |
|---|---:|---:|---:|---:|
| 1 | 195,313 | 47,575 | 51 | 47 |
| 2 | 441,961 | 67,455 | 167 | 127 |
| 4 | 1608,526 | 108,210 | 591 | 383 |
| 8 | 4292,204 | 183,019 | 2207 | 1279 |
| 16 | 13459,108 | 390,154 | 8511 | 4607 |
| 32 | 48930,092 | 892,097 | 33407 | 17407 |
| 64 | 183810,168 | 3423,817 | 132351 | 67583 |

Это количество вызовов, не IO bytes. ownedBytes270336 на последнем checkpoint
не является peak memory/DPAPI allocation. CPU и чужая нагрузка не измерялись.
В формате canonical mono Float32 48000 Hz блок 256 КиБ поступает каждые
1365,333 мс: последнее сохранение уже дольше этого интервала в текущей VM.
Полный повторный обход всех DATA refs даёт кумулятивную O(n²) стоимость.
Требуется устранить её до подключения writer к длительной записи;
увеличение очереди или ослабление validated ACK не является исправлением.
Это локально воспроизведённый блокер, не физическая x64/60min/SC-003 приёмка.

### Текущий master и границы следующего исправления

Read-only fetch: `origin/master=f3ec4dd95c3aa68fc7246338bd7c58908d24aee2`,
merge-base `f5cca687a06dc57ad6ccbef840a0be897eaa6336`. Master не вливался
в dirty worktree. Независимое сравнение нашло четыре нативных расхождения:
четыре exact billing routes (T102/T103), отсутствующий authenticated calendar
join-target (T119), преждевременное скрытие напоминания при отказе перехода
(T104/T119), лишний Tab stop контейнера инспектора (T081/T097/T063).
Общий кабинет получает F280/F283 через hosted web, без дублирования логики
на Windows; это не доказывает текущую live серверную версию. F284 в данном
master не найден и не объявлен принятой merged базой.

T116/T117/T118, T102/T103/T119 и все аппаратные, сквозные, установочные,
доступности и живые UI критерии остаются открытыми. Commit/push/PR/merge,
release, install, запуск записи, macOS/server/root CHANGELOG не выполнялись.

## Раунд 213 — четыре платёжных перехода Mac в Windows (2026-10-03)

Existing F200 / T102, high-risk-product, FR-002/003/005/006, SC-002.
HEAD и каноническая рабочая копия неизменны относительно раунда 212.
Независимый допуск `checklists/review-2026-10-03-billing-route-gate.md`:
112 checked/0 unchecked, scoped CRITICAL0/HIGH0. Свежие connector reads
#7279/T102 и #7280/T103: OPEN, assignees=null; исполнение среза принадлежит
основному агенту, GitHub assignee не выдуман. Norm hashes не изменились.

В существующий exact allowlist добавлены только:
`/billing/storage/preview`, `/billing/storage/cancel-selection`,
`/billing/subscription/early-preview`, `/billing/purchases/confirm`.
Это те же четыре действия Mac на master
`f3ec4dd95c3aa68fc7246338bd7c58908d24aee2`. Без новых `/desktop/billing`
aliases, wildcard, business/payment/server logic, сроков, command capabilities
или автоматического повторения POST. Production diff +2 строки.

Новая регрессия +33 строки проверяет все четыре разрешённых действия,
query/fragment, первый точный provider и ложный provider, соседние/кодированные/
traversal пути, внешний origin без native bridge, GET/POST recovery refusal
и возврат expiredSession на `/login?next=%2Fbilling`, не на действие оплаты.
Независимый source review
`checklists/review-2026-10-03-billing-route-source.md`: APPROVED bounded source,
CRITICAL0/HIGH0; Ponytail Lean already, безопасных сокращений0.
Тесты reviewer не запускал; их наблюдения основного агента записаны отдельно.

### Свежие проверки точных исходников

| Файл | SHA-256 |
|---|---|
| WebViewRoutePolicy.cpp | 57c66b187311d606727d7d0b776b462ca20fbc1a717a6d219ed61e19e5c5c169 |
| WebViewRoutePolicyTests.cpp | df79e84897bf3828ea9e2b2f0359e8e460228c42192e8f2143416d4b213c6bd9 |
| billing-route-gate.md | 3e2a9dbced8e807be7df73470ab022f4e5dd03f19d9ede9076a6c2a8905d3847 |
| billing-route-source.md | 16c8f52af0a6834ffe588ba2bbd7267ad9969a6735c3b149cfea78f39b23786c |

Test-first RED: host focused build0, CTest exit8, assertion99
`allow + billing` до product edit (session53698). GREEN: focused build0,
CTest1/1 PASS, exit0, 0,44 с (session16037). После этого полный portable
build0 и CTest35/35 PASS, exit0, 28,59 с (session24309).
Canonical/mirror pins совпали через cmp; native source скопирован из зеркала.
Windows native all-build0 и CTest36/36 PASS, exit0, 55,24 с, `-j1`
(session22147). Это исполнение Windows тестов, не установленного WebView2 UI.

### Уточнение ограничения производительности T116

Независимый read-only разбор подтвердил: full-block checkpoint вызывает полный
двухслотовый resolver, который заново проверяет каждый DATA ref. Для append
checkpoint N проверяет 2N−1 refs; к 64 МиБ выполнено 65536 проверок блоков,
то есть 16 ГиБ payload validation без envelopes/write-path checks.
Сокращение повторной инициализации SHA-провайдера, лишнего decode/copy или
проверки одного и того же ref внутри одного resolver может улучшить константу,
но не убрать растущий полный обход. Persistent кэш без удержания нативного
доказательства неизменности старых bytes не принят; неограниченное число
открытых файлов также не принято. Изменение proof/ACK модели требует явного
нормативного решения и нового independent gate до реализации, не скрытого
ослабления существующего контракта. Продуктовый storage код в раунде не менялся.

T102/T103 не закрыты: отсутствует новая живая приёмка точного установленного
пакета и всей платёжной цепочки. T116/T117/T118, clocks/calendar, hardware,
UI/accessibility, auth/upload/deletion и release условия остаются открытыми.
Реальные платежи/микрофон/записи, установка, сервер и macOS не затронуты.

Полная Visual Studio Release/x64 сборка после route edit: первоначальный
вызов без явного verified AEC3 cache завершился build1
(`GrafAEC3 must link the standard library covered by build provenance`,
session91667). Причина — выбранный default path не содержит backend;
проверка защиты сохранена, product project не менялся ради обхода.
Read-only проверка существующих cache нашла единственный проверенный комплект:
`C:\Users\yshishenya\graf-aec3-verified-build`, источник
`C:\Users\yshishenya\graf-aec3-source`. Явные GrafAEC3Root/GrafAEC3BuildRoot
переданы следующему вызову. Script снова проверил source/license/artifact
identity `846fe90a289f58b7c9303a635142aa2c7caa93e5`.
Session4716: `BILLING_VERIFIED_VS_BUILD_EXIT=0`,
`BILLING_VERIFIED_VS_CORE_EXIT=0`. Существующий D9025/W1→W4 warning остаётся;
это не zero-warning claim. Native source pins повторно совпали с таблицей.
SHA-256 собранного, **не установленного** GrafWindowsApp.exe:
`f1de5b6c50dc2ac08afbb929347899580bfb11892cefccc1de3884faccf9347f`.
Package/MSIX/signature/install/runtime acceptance не выполнялись.

Следующий ограниченный performance candidate, пока **не реализован**:
официальный Windows CNG `BCRYPT_SHA256_ALG_HANDLE` вместо открытия/закрытия
алгоритмического провайдера при каждом digest. Microsoft рекомендует
predefined algorithm handles для Windows10+; SHA256 присутствует в таблице,
общий algorithm handle нельзя менять через BCryptSetProperty. Наш NativeHash
такого изменения свойства не делает. Это возможное удаление повторной
инициализации без собственного global/thread cache; каждый hash object и
проверки native create/update/finish должны остаться отдельными и fail-closed.
До product edit необходимы scoped independent gate, проверка TU-local fault
регрессий всех реально используемых native операций и свежий bounded probe.
Старый искусственный отказ неиспользуемого OpenAlgorithmProvider нельзя
выдавать за проверку нового пути. Это не доказательство выигрыша скорости
и не решение O(n²) полного resolver.
Первичные источники прочитаны 2026-10-03:
`https://learn.microsoft.com/en-us/windows/win32/api/bcrypt/nf-bcrypt-bcryptopenalgorithmprovider`,
`https://learn.microsoft.com/en-us/windows/win32/seccng/cng-algorithm-pseudo-handles`.

## Раунд 214 — 2026-10-03: минимальный CNG SHA шаг и повторная проверка скорости

Канонический worktree остаётся
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, ветка
`codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`; проверяются dirty bytes,
не старый установленный пакет. Lane: high-risk-product, ограниченный T116.
Сервер, macOS, реальные записи, микрофон, приложение и установка не менялись.
Commit/push/PR/merge/release в этом раунде не выполнялись.

### Требования, тест до изменения и ограниченная реализация

Независимый `review-2026-10-03-cng-pseudo-handle-gate.md` разрешил только
SHA-подшаг: 112/0 requirement-quality checks, scoped CRITICAL=0/HIGH=0;
существующий issue #7444 OPEN, task T116 остаётся открытым. SHA-256 отчёта:
`eefa1e86efa7295dab227d9442e3914174efafc585496d78990dd4c11a4b8b7d`.
Полный текст отчёта и ограничения прочитаны до правки теста/продукта.
Spec/plan/tasks/protected-custody contract не менялись.

Test-first RED: `NativeHashFailureTests` теперь требует точный
`BCRYPT_SHA256_ALG_HANDLE`, новый hash object для каждого digest и нулевые
Open/Close/SetProperty вызовы в SHA translation unit. Native focused build0,
test exit8/0xc0000409, assertion `algorithm == BCRYPT_SHA256_ALG_HANDLE`
на строке26, 4,70 с (session8374). Это ожидаемое падение старого provider
пути; product edit выполнен только после него.

В NativeHash заменён конструктор на BCryptCreateHash с системным SHA-256
pseudo-handle; убраны app-owned algorithm member и его Open/Close.
Каждый hash создаётся и уничтожается отдельно, flags=0, без reusable hash,
собственного cache, portable fallback, смены digest или политики доверия.
Stream buffer 64 KiB, проверка Create/Update/Finish и отсутствие hash при
ошибке сохранены. Новые native проверки покрывают empty/binary/chunk input,
перекрывающиеся lifetime двух потоков, Create/Update/Finish failures и cleanup.
Manifest-only Create fault ordinal3 оставляет HTTP sends0; portable identity
не вызывает CNG и сохраняет прежний digest. Старая Open fault удалена, а не
выдаётся за тест неиспользуемого API.

В `ProtectedCustodyFilesTests` failure hook перенесён на действующий
BCryptCreateHash вместе с ordinal allocation/std::bad_alloc. Сохранены
notCommitted/ambiguous/hashFailed/allocationFailed, retained artifacts и
sticky writer failure регрессии. File `opens` по-прежнему означает
CreateFileW; hash counter и probe label теперь явно называются hashCreates.
Reader/writer/codec/file/index/ACK/encryption/quotas не менялись.

### Свежие проверки точных исходников

| Файл | SHA-256 |
|---|---|
| Sha256.cpp | af51b5cef94a0855773c1310b05bc7ef1d13a65939d2f8bc4b960ff403f0a4d2 |
| NativeHashFailureTests.cpp | d0d33db879531c2ad5debc7facad20f13b13d3e625d510415d2d37f58fc42414 |
| ProtectedCustodyFilesTests.cpp | a8e3aa8d60410143624e0b81d53c70056e227f8d5879f5600e669bab6005ce72 |

Canonical/mirror files совпали через cmp; native source скопирован из
этого зеркала. Windows targeted build0/CTest2/2 PASS, 13,65 с
(session8513), полный Windows build0/CTest36/36 PASS, 71,40 с, `-j1`
(session22066). Общий portable build0/CTest35/35 PASS, 33,03 с
(session95673); это не исполнение CNG на macOS.

Полная Visual Studio Release/x64 сборка с явным verified AEC3 source/build
завершилась build0 (session95469); guard identity
`846fe90a289f58b7c9303a635142aa2c7caa93e5` сохранён. Прежний D9025/W1→W4
warning остаётся, zero-warning claim отсутствует. Core executable exit0
получен отдельно перед probe (session80586). SHA-256 собранного,
**не установленного** GrafWindowsApp.exe:
`e99c6b2b5506b21a717bebda64aaf4a060bb6493e1dadc3deddb5d7995b7b9c5`.

### Последовательный synthetic probe — сохранность PASS, скорость не принята

Session80586: `--writer-throughput-probe-64mib`, exit0, только generated
bytes, role canonical, 256 KiB block. Сборки/CTest завершены до probe;
Core exit0 также получен до него. Нельзя утверждать отсутствие посторонней
нагрузки ОС/хоста либо превращать один прогон в устойчивый benchmark.

| МиБ | Полное накопленное время, мс | Последний WriteAt с checkpoint, мс | Native reads | Native hash creates |
|---|---:|---:|---:|---:|
| 1 | 350,739 | 88,149 | 51 | 47 |
| 2 | 715,436 | 81,963 | 167 | 127 |
| 4 | 1692,783 | 155,304 | 591 | 383 |
| 8 | 4259,756 | 186,111 | 2207 | 1279 |
| 16 | 13805,939 | 560,754 | 8511 | 4607 |
| 32 | 47213,290 | 596,243 | 33407 | 17407 |
| 64 | 217694,997 | 1435,316 | 132351 | 67583 |

Подтверждены generation256/committed256, notCommitted0/ambiguous0,
13 напечатанных failure counters0 (14 enum entries включают `none`),
owned memory перед пробой0, в конце writer lifetime
270336 bytes и после освобождения0. Счётчик Create не означает Open:
67583 digest creations при 0 provider Open/Close в SHA route подтверждены
разными тестами, а не подменой метки старой метрики.

Предыдущая проба Round212 имела те же native reads132351/digest count67583,
last checkpoint3423,817 мс и total183810,168 мс. Теперь last1435,316 мс,
но total217694,997 мс: одиночные прогоны не доказывают надёжного ускорения.
При 48000 Hz mono Float32 256 KiB поступают за 1365,333 мс, что меньше
наблюдаемого последнего checkpoint. Это по-прежнему блокер масштабирования
и sustained-capture acceptance, не доказательство пригодности установленной
записи/SC-003. Рост числа full resolver reads не устранён.

Независимый `review-2026-10-03-cng-pseudo-handle-source.md` завершён:
APPROVED только exact three-file delta, CRITICAL=0/HIGH=0/blockers0,
ponytail-review: Lean already, production net−3 строки. Main прочитал весь
отчёт, его source pins совпали с таблицей и native повторной сверкой
(session89255). SHA-256 отчёта:
`b3baa96917f61b2fdae21976793aa071c03bd4cb6dccbfc1efe0033b2873e94e`.
Reviewer не запускал tests/probe; это source verdict, не независимое
воспроизведение runtime и не приёмка скорости.

Governance check, bootstrap doctor/frozen, F200 YAML parse и diff check
прошли (session3020; YAML/diff повторены после дополнения журнала).
T116/T117/T118 и полная функциональная/визуальная/аппаратная приёмка
Windows открыты. Реальные данные/приложение/установка не затронуты.

### Следующий алгоритмический шаг не принят как скрытая оптимизация

Прочитан весь ненормативный `research-2026-10-03-scalable-custody-proof.md`:
единый удерживаемый file HANDLE, packed records, bounded трёхуровневое дерево,
небольшие head cells и полный cold verification после разрыва владения.
Его live incremental proof **не равен** прежнему full DATA resolver перед
каждым ACK: скрытая порча старого DATA может обнаружиться при чтении, а не
на ближайшем сохранении. Старые нормы автоматически не переименованы и
T115 checkbox не переоткрыт/закрыт от факта исследования. Требуются явное
решение по detection-time tradeoff и новые согласованные normative gates.

Предложенные AES-GCM/DPAPI key capsules, собственные key epoch/nonce/rotation
не приняты только ради packed tree: основной агент запросил более простой
вариант с сохранением существующего per-record DPAPI primitive для bounded
DATA/node/head. Read-only исследователь завершил append-only §11: blocker
для прежнего DPAPI primitive не выявлен; packed tree не требует собственного
AES/key/nonce lifecycle. Main прочитал дополнение целиком. SHA-256 полного
исследования после дополнения:
`d53306ff8554166603c98c97ecb209166a9986d6b56d9c8ff5e14c2d0d626b6d`.

Это рекомендуемое минимальное предложение, не принятый новый wire/proof
contract и не runtime/crypto claim. DPAPI success проверяется дополнительными
exact context/length/reserved/payload/node/head/ciphertext checks; native
success сам по себе не объявляется доказательством целостности. Следующий
материальный выбор владельца — detection-time tradeoff для old DATA при
live incremental ACK. До его явного решения и последующих normative gates
новый packed proof не реализуется. Старые требования к ACK не ослаблены
молча. Нет нового разрешения на plaintext fallback, сдвиг clock tolerance,
неограниченный кэш, нарушение IO ownership или преждевременный normal ACK.

## Раунд 215 — согласованная поправка хранения, 2026-10-03

Worktree `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Dirty предыдущая работа сохранена;
нет commit/push/PR/merge/install/deploy. Lane high-risk-product, стадия
clarify/design, не product implementation. Последнее «разрешаю» владельца
принимает предложенный round214 detection-time tradeoff.

### Согласованные изменения

Spec FR-012/Session2026-10-03 явно разрешают live inheritance только при
непрерывном проверенном native owner: новые DATA и публикация проверяются
до ACK, скрытая старая порча может обнаружиться при read/full verification.
После любого ownership gap обязателен fresh full closure до normal use.
Observed fault sticky; v1 authority metadata full/no-rollback сохранены.

Добавлен отдельный `contracts/windows-protected-packed-custody.md`:
per-record user DPAPI+SHA, canonical/media/playback-only, один held HANDLE,
radix64/depth3, exact prefix/header/ref/descriptor и две fixed protected cells.
Собственные AES/DEK/nonce/capsules/key cache не введены. Есть versioned
package.v2 refs10/migration.v2 sources11 fields при physical v1 metadata.
Новый schema не означает выполненную consumer/migration integration.
Plan/data-model/research/quickstart§14 согласованы; исходный v1 contract
сохранён с явно различённой областью. Старое v1 принятие не переносится на v2.

T115 переоткрыт для поправки, task IDs не добавлены:92checked/27open/119unique
на этом checkpoint. GitHub read подтвердил #7443/#7444 OPEN; bodies исходные,
comments0. GitHub не изменялся, отдельный внешний sync не объявляется выполненным.
T116/T117/T118 и все clock/installed/physical/release gates остаются открыты.

### Независимая проверка и исправления

Первый `review-2026-10-03-packed-custody-amendment.md`: REQUEST CHANGES,
C0/H2/M1,110checked/2unchecked; security CHK012/CHK015 открыты reviewer.
Main прочитал весь176-line отчёт и не менял его markers:

- H1: checked candidate generation=highest proven selected base+1;
  overflow/jump/stale base до append, другая cell exact selected base,
  adjacent/slot checks перед ACK; empty equal-g1 tie selects slot0.
- H2: expected Ref envelope length/SHA для всех non-inline DATA и NODE,
  включая root, до unprotect/использования refs; внутренний checksum отдельно.
- M1: no per-record reclamation while live отделено от whole-object delete;
  own heads/identity receipts не вечные keep-edges; external ambiguity,
  historical barriers и actual owner completion/absence gates сохранены.

Исправления внесены в normative contract и quickstart, отправлены тому же
независимому reviewer на повторную проверку. Первый verdict не заменён
молчаливым PASS. До актуального повторного gate product v2 code не изменён.

### Native ownership premise — только synthetic fixtures

В running Windows11 Parallels VM выполнены .NET FileStream/MemoryMappedFile
пробы native sharing, без GRAF/meeting/audio/mic/private inventory. Это
предварительная проверка premise, не product GuardOwner tests или standard-user
ACL/physical-x64 acceptance. Полномочия user/token probe не проверяли.

| Проба | Результат |
| --- | --- |
| RW mapping retained после закрытия исходного FileStream; новая RW+FileShare.Read acquisition | denied=true, HRESULT0x80070020; старое mapping оставалось writable; session28712 exit0 |
| Уже открытый обычный RW handle → попытка guard | denied=true |
| Новый обычный writer при held guard | denied=true |
| Writer после actual guard release | allowed=true; session45420 exit0 |

4KiB искусственные files, views и handles освобождены в finally; обе fixtures
реально удалены, `SYNTHETIC_FIXTURE_REMOVED=True`. Нет retained test content.
Первая mapping попытка с PowerShell null→empty name завершилась ArgumentException
и cleanup, это не evidence. Более длинная ordinary-writer invocation вернула
Parallels Invalid argument255 до доказанного guest результата; короткая
повторная команда дала приведённый exit0. CLIXML progress не считается error.

### Остальные проверки и границы

Design arithmetic PASS:128B prefix/header,64B Ref,128B descriptor, append32896,
NODE plaintext4224, radix64^3×262144=64GiB, append max290816B. Это arithmetic,
не кодек/regression/runtime proof. Governance, bootstrap doctor/frozen,
extensions YAML/F200 YAML и `git diff --check` прошли на этой стадии.
Старая speckit-analyze команда с `--require-spec` не поддерживается установленным
script; help проверен, успешный prerequisites вызов использует только
`--json --require-tasks --include-tasks` и отдельную проверку spec exists.
Не объявляется новый build/CTest или performance PASS: product source этого
раунда не менялся. Установленное приложение и рабочие записи не менялись.

Отдельный bounded research T119 завершён:
`checklists/research-2026-10-03-telemost-windows-handoff.md`. Найдена registration
подписанного Win32 Телемоста и explicit-class ShellExecuteExW candidate.
HTTPS Available не client identity; actual target handoff не запускали.
SYSTEM/HKU metadata не выданы за effective GRAF-user association. T119 открыт,
browser launch не объявлен native parity. Корневой AGENTS/constitution,
server/macOS/CHANGELOG и внешние сервисы не изменены.

### Продолжение раунда 215: повторная независимая проверка

После исправлений reviewer Jason повторно проверил только H1/H2/M1 и записал
APPROVED requirements quality, C0/H0/M0. Security CHK012/CHK015 восстановлены
самим reviewer; пять checklists — 112 checked/0 unchecked. Предыдущий отказ
сохранён в первых176 строках отчёта, а не заменён успешным результатом.
Это разрешение на следующий scoped analyze, не принятие реализации T116,
metadata/migration adoption, скорости либо установленного приложения.
T115/T116/T117/T118 остаются открыты, 119 уникальных IDs,92/27.

Packed contract SHA-256:
`7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed`.
Review report SHA-256:
`d410c98077afa8637f03632a5e2c390e93910a457f96798f97493321bb628d72`.
HEAD остаётся `99b00a579c24b50e320465b69d9a296038bc544d`;
свидетельства относятся к перечисленным dirty file hashes, не к новому коммиту.

### T115: решение main по проекту и текущий scoped analyze

Main принял уточнённый проект T115 после human clarification и независимого
design/checklist checkpoint. Это design-only marker: T116/T117/T118 открыты;
schema §6.1 как проект не принимает consumer/migration runtime adoption.
Последующий узкий analyze main перечитал spec FR-012/013/014/022, plan порядок
T116, data-model §13, packed contract целиком, quickstart §14, задачи и
constitution. После изменения только marker T115 проверка повторена на текущем
tasks: 119 уникальных IDs,93 checked/26 unchecked, требования/зависимости
не изменились. C0/H0 для первого wire среза; broader runtime gaps сохранены.

| Требование | Покрытие / ограничение |
| --- | --- |
| FR-012 | T115 exact wire/owner/live+cold proof; T116 codec/IO/tests; T118 faults |
| FR-013/014 | §6.1 сохраняет ledger/ranges; consumer adoption T116, migration T117 |
| FR-022 | base delete authority и §6 whole-object retirement; T116/T117/T118 |
| SC-003/005/006/008 | cadence/resource/security/restart/install проверяются T116–T118, не design PASS |

Недублированные scoped executable owners #7443/#7444/#7445/#7446 снова открыты
2026-10-03. Mandatory canon ensure выполнен после read-only preflight: изменений
файлов/меток не требовалось и не зарегистрировано; validate — 300 issues PASS.
Это scoped storage ownership, не whole-feature issue sync: title-only scan не
доказал некоторые прежние grouped owners и T119; их нельзя объявлять закрытыми
или создавать дубли без проверки. T119 не входит в эту реализацию.

Дополнительный independent analyze worker был остановлен до отчёта после
завершения полезной design review: его отсутствующий результат не evidence.
Текущий analyze выполнен main; независимость относится к завершённому checklist
review, а не этому analyze. Первый implementation шаг ограничен pure prefix/Ref
wire validation без DPAPI authority, owner/tree/adoption/private inventory.

## Раунд 216 — 2026-10-03: первый тест-first wire срез T116

Канонический root `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
HEAD `99b00a579c24b50e320465b69d9a296038bc544d`, ветка
`codex/200-windows-followup`. High-risk active Spec Kit storage slice.
T115 design-only accepted; текущий tasks SHA после marker и main analyze:
`ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98`.
119 IDs,93 checked/26 open; T116/T117/T118 остаются открыты.

### Код и тест-first свидетельство

`ProtectedPackedCustodyFormat.{h,cpp}`: точные prefix128B/Ref64B, LE без native
struct serialization, role allowlist, IDs/framing/constants/reserved, inline
EMPTY/ZERO canonical bytes, stored-kind/version/payload/caps/alignment,
checked offset+length и child-end≤parent≤committed extent. Fixed-size arrays
без heap по анализу кода. Это structural parsing: ни DPAPI/SHA/proof authority,
ни logical EOF/explicit ZERO/selector validation не заявляются выполненными.
Изменённый digest намеренно проходит parsing и должен проверяться codec/owner
до decode/use. Разбор не подключён к consumer/capture/storage IO.

Сначала добавлены tests/CMake registration. Первый build после reconfigure
отказал missing header, это только compile RED. Затем stub build и настоящий
behavioral RED: `encoded && *encoded == golden`, CTest exit8 (session теста
зафиксирован в turn, stage до реализации). После реализации focused GREEN.
Начальная C++20 span/default-equality попытка не собиралась в portable lane;
исправлено на C++17 pointer+count/manual equality без изменения стандарта.
Native MSVC нашёл C4244 в test `std::fill(int→uint8_t)`; explicit byte values
исправлены, `/W4 /WX` не ослаблены. В итоговом source нет stub bodies.

| Текущий файл | SHA-256 |
| --- | --- |
| ProtectedPackedCustodyFormat.h | a210c3331b36d8ae83ddcf3bd6af7e49c0e74fc2c2e4d1ef8bb573f6680fcc82 |
| ProtectedPackedCustodyFormat.cpp | 073ddff71abf2e092b35426befb5648351022a424fa7d1e42cc7508754ce9fd6 |
| ProtectedPackedCustodyFormatTests.cpp | d3b31dc9ab0825e5d846cf5f06286c8ba901f3942049dc1815ae91d8f29d8612 |

### Windows receipts

Canonical→mirror→native explicit files only, no deletion/sync of user inventory.
Первый native CMake build отказал только C4244 test fills (session60790),
после исправления build0/CTest37/37 PASS (session81440). Independent source
review James обнаружил C0/H0/M2: high-u64 literal fixture и raw decoder
negative cases. Оба дополнены тестами; h/cpp не менялись. На новом test hash
native targeted rebuild0 и весь последовательный CTest37/37 PASS,35,46s
(session37294); текущий guest test hash совпал с canonical.

Полный `GrafWindows.sln` Release/x64 build0 и CoreTests.exe exit0
(session54365); guard verified AEC3 source identity
`846fe90a289f58b7c9303a635142aa2c7caa93e5`. Прежний warning D9025 W1→W4
сохранён; zero-warning claim отсутствует. Built, **не установленный** exe SHA:
`752ef36d65dcb56317df794766d99f44e142c02371322c3874ff82ccb6eaf7c8`.
Новые test-only изменения не меняли source solution build; новый wire cpp
не подключает representation к рабочей записи. MSIX/sign/install не выполнялись.

### Граница среза

Ponytail-review нового wire source: Lean already, безопасного сокращения нет.
Это review сложности, не security/runtime/release acceptance. Независимый
correctness report — `checklists/review-2026-10-03-packed-wire-source.md`;
его исходный M2 verdict сохранён, follow-up фиксируется отдельно.
Нативные DPAPI typed DATA/NODE/HEAD, continuous GuardOwner, durable heads,
tree/live+cold proof, schema adoption, migration, performance и full T118
ещё не реализованы этим срезом. Существующие v1 protections не изменены.
Real capture, clock tolerance, private recordings, установленный GRAF0.1.0.11,
macOS, server и root CHANGELOG не менялись; physical x64 не заменена VM.
Коммит/push/PR/merge/release в этом раунде отсутствуют.

### Финальная test-only дельта и повторная приёмка wire среза

James закрыл M1, затем нашёл не изолированный DATA-cap отказ: слишком маленький
parent мог отвергать этот Ref и без проверки cap. Test bounds увеличены до
offset+8192; alignment negative также изолирован от end boundary. Product h/cpp
не менялись. Финальный test SHA:
`119f67d748d2f9794960cd376e7cfbf92f273f15f47203ba6d27ea005aa35b6c`.
Independent final append: C0/H0/M0, оба M закрыты, без новых source findings.
Предыдущие review snapshots сохранены; reviewer сам tests не запускал.

На этом точном снимке main получил native rebuild0/CTest37/37 PASS,31,03s
(session11353), guest/canonical hash matched; portable rebuild0/CTest36/36
PASS,11,25s (session37013). После main fixes до final test-only delta также
был portable36PASS11,12s (session17621), но он не заменяет финальный receipt.
Все native tests последовательны. После source review product bytes остались
на исходных h/cpp hashes; solution/core receipts этого раунда актуальны для них.
Файл implementation test не включён в VS app project и менялся отдельно.

Остаток этого принятого плана всё ещё имеет владельцев: typed DPAPI/SHA и
native owner/heads/tree/integration — T116; restart-safe старый inventory —
T117; полная generated/installed матрица — T118. Не добавлены дубли задач;
whole-feature convergence не объявлена. Новый формат пока не исправляет
измеренную квадратичную цену действующего v1 пути в приложении: устранение
её зависит от следующей реализации tree/delta и повторного benchmark.

## Раунд 217 — 2026-10-03: typed packed codec и нативные отказы T116

Каноническая копия `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Изменения этого раунда не закоммичены.
Tasks SHA `ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98`:
119 уникальных IDs,93 checked/26 open; T116/T117/T118 остаются открыты.

### Границы реализации и предварительная проверка

Независимый gate `checklists/review-2026-10-03-packed-codec-gate.md`:
C0/H0,112 нормативных проверок отмечены/0 неотмеченных. Main повторно прочитал
актуальный контракт, требования и план; scoped analyze codec-only C0/H0.
Issue #7444 открыт и владеет полной T116, не отдельным примитивом. Disabled
Spec Kit commit hooks не исполнялись. Задачи и нормативные маркеры main не менял.

Добавлены `ProtectedPackedCustodyCodec` и общие `ProtectedCustodyPrimitives`.
DATA/три NODE/HEAD имеют точные typed заголовки, контекст защиты, ограничения
размеров и контрольные суммы. Для Ref точный размер и SHA защищённых bytes
проверяются до DPAPI; HEAD дополнительно проверяет слот, поколение и padding.
Неверный размер нативного результата отвергается до выделения owned copy;
временная plaintext и возвращённая нативная память очищаются на отказах.
Общий SHA/DPAPI helper используется и прежним v1 codec: его entropy/wire
и ограничения сохранены. Собственных ключей/шифра/открытого fallback нет.

Это только in-memory codec. Декодированный body не даёт разрешения на чтение,
публикацию, отправку или удаление. Descriptor semantics, дерево, child-before-parent,
непрерывный GuardOwner, birth/flush/readback двух HEAD, подтверждение сохранения,
metadata adoption и перенос старых файлов не реализованы этим срезом.

### Тесты и независимая проверка кода

Начальный build с добавленным тестом отказал из-за отсутствующего header
(compile RED, exit2); это не behavioral RED всех сценариев. Затем реализован
codec и расширены тесты: независимые literal96B заголовки и области SHA,
подмена контекста/Ref/framing/plaintext, DATA cap, NODE/HEAD, отказ выделения
памяти и injected DPAPI/SHA отказы. Тесты используют искусственные bytes.

Source review `checklists/review-2026-10-03-packed-codec-source.md` в финале:
C0/H0/M0. Выявленное M1 касалось доказательства size-before-copy в тесте:
один итоговый счётчик не исключал временную копию. Теперь весь owned budget
занят перед malformed-size вызовом: лишняя копия дала бы bad_alloc вместо
требуемого invalidPlaintext. Нативные wipe/free assertions сохранены.
История review сохранена; рецензент не запускал тесты и сборку.

| Финальный файл | SHA-256 |
| --- | --- |
| ProtectedCustodyPrimitives.cpp | a27b07ac3b04627c5286d6290b3ca6ba3a15710fa170f238be893c3e13c133b3 |
| ProtectedPackedCustodyCodec.cpp | 18d6ca5a0ab0e4a454c81512c18a174dc7009d2baabee0b6bb82a80acecd153f |
| ProtectedCustodyCodec.cpp | 5372538eb3055c2b9a89786ef15089eb090e574025a3c0c030f87730873506c9 |
| ProtectedPackedCustodyCodecTests.cpp | 95a7cd88e709cba04ce5de9dae893fe4fb68f39f50938974c951dce53eef553a |
| NativeCustodyProtectionFailureTests.cpp | 4defade304b5c95eec58d685a5a084e24cc675dfff2ab8af2b061ca6197ded18 |
| NativeHashFailureTests.cpp | b13c2eeb1972afe6e927044072241044e0b39e9e8e6233b598537e3e90d948fe |
| Source review report | ad3e84ab60b44159bbe55a586ec81479c1ba130d2a76ae4ed3f6cacb60886ddb |

### Финальные результаты main

- Portable rebuild0 и CTest37/37 PASS,11,27s (session24631).
- Windows native rebuild0 (session2337), CTest39/39 PASS,30,85s
  (session42555), последовательный запуск. Финальные codec/source/test hashes
  повторно совпали canonical→guest (session98093).
- Полная VS solution Release/x64 build0 (session41895), AEC3 identity guard
  подтвердил `846fe90a289f58b7c9303a635142aa2c7caa93e5`. Прежний D9025
  `/W1`→`/W4` warning остаётся; сборка без предупреждений не заявляется.
- `GrafWindowsCoreTests.exe` exit0 (session32770). Built, не установленный
  GrafWindowsApp.exe SHA
  `fcd9cfe3384f44658bd8ff70e8d2edc713aee25149febac791b5c03329711a9a`.
- Governance, frozen bootstrap и diff hygiene прошли до документирования;
  после записи результатов выполнена отдельная повторная проверка.

Ponytail-review ограниченного source: Lean already; повторная нативная логика
вынесена в действительно общий helper без нового криптографического слоя.
Новый формат ещё не подключён к записи и не устраняет измеренное v1 O(N²)
до реализации tree/delta и повторных измерений. Installed GRAF0.1.0.11,
реальный захват, частоты/clock tolerance, частные файлы, macOS и сервер не
менялись; MSIX/sign/install/runtime acceptance не выполнялись. ARM64 VM
с x64 emulation не заменяет аппаратную x64 приёмку. T116/issue/F200 не закрыты;
commit/push/PR/merge/release отсутствуют. Следующий срез — удержание файла,
позиционные чтения/записи и проверяемая публикация HEAD, затем tree/proof и
полная интеграция по действующим T116/T117/T118.

## Раунд218 — continuous packed owner и ограниченный physical IO (2026-10-03)

### Область и требования

Рабочая копия `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD/source_sha
`99b00a579c24b50e320465b69d9a296038bc544d`. Dirty/untracked bytes не объявляются
содержимым этого commit; отдельные hashes ниже. T115 остаётся закрытой design
задачей, T116/T117/T118/T119 открыты. tasks.md не менялся:
119 уникальных задач,93 checked/26 unchecked, SHA-256
`ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98`.

Main выполнил scoped analyze по FR-012/013/014/022 и SC-003/005/006/008,
plan step2, packed contract и quickstart§14. Новый prerequisite соответствует
согласованному design; полного feature analyze/convergence PASS не заявляется.
Независимый requirements-quality gate: C0/H0,112 checked/0 unchecked
(requirements22, audio24, advanced14, security27, ux25), markers не менялись.
Основание — `checklists/review-2026-10-03-packed-owner-gate.md`, SHA-256
`51623b6046d422d14f730a8ced5f2111d796cafa18fda299000dfa556e4046ba`.

### Реализованный prerequisite

Добавлен `ProtectedPackedCustodyOwner.h`; implementation находится в прежнем
`ProtectedCustodyFiles.cpp`, чтобы переиспользовать единственный confinement
backend, а не создавать второй слой путей/ACL. Files.h содержит private friend;
Directory/trustedRoot bookkeeping удерживает пути для повторных проверок.

Owner удерживает один synchronous RW/shareRead native HANDLE content, прежние
ancestor/store/object guards, native FileID, context и монотонный epoch.
Strict store-ID acquisition сопровождается повторным чтением ID после upgrade.
Rechecks включают native path/ACL/reparse/hardlink/handle-inherit/ADS проверки;
неизвестное окончание enumeration не принимается за отсутствие streams.
Admission до работы: owner/result pins≤32/process, native jobs≤4/process;
копирование/присваивание job token запрещено. Owned allocator учитывает actual
ciphertext capacities/results и новый State/Owner/control block. Унаследованные
path/security bookkeeping allocations НЕ принимаются за полную pipelineOwned
budget/account acceptance: она остаётся частью consumer integration.

Позиционные synchronous ReadFile/WriteFile используют fresh explicit offsets,
общий mutex и chunks≤262144B; valid DATA envelope≤266240B разбивается на chunks.
Read bounds известного запроса проверяются до metadata IO/allocation. Short,
zero и failed IO не повторяются как успех. Read result удерживает ciphertext,
pin и тот же shared owner: освобождение writer не закрывает живой result guard.
Revoke запрещает новые writes, но не healthy reads; observed fault sticky.

Append допускается только после actual EOF с checked alignment, sealed typed
context/ref validation и disk reserve, без truncate/reuse orphan tail. Отдельная
physical HEAD operation проверяет полный fixed cell, выполняет write/flush/
same-HANDLE independent readback. С первой попытки HEAD write ошибка ambiguous;
partial/actual artifacts сохраняются. Physical published не является logical
commit ACK, не принимает paired authority и не разрешает normal upload/GC.
CREATE_NEW подготавливает prefix и две independently protected empty g1 cells,
length0/root EMPTY/extent32896, с flush и independent prefix/HEAD readback.
Writer copies освобождаются до readback. Existing-open проверяет native context,
prefix/minimum physical size, но НЕ делает cold closure/tree proof.

### Ошибки, найденные независимым source review, и исправления main

Initial review `checklists/review-2026-10-03-packed-owner-source.md`:
REQUEST CHANGES, C0/H1/M3. История findings и промежуточных hashes сохранена.

- H1: function-try-block освобождал mutex/native job до фиксации bad_alloc;
  competing operation могла продолжить IO и изменить общий HEAD outcome.
  Все пять physical methods теперь имеют inner catch внутри удерживаемого
  mutex/owner/job scope. Fault и ambiguous фиксируются до unlock/admission release.
- M1: appendPosition/flush теперь возвращают typed allocation failure без
  escaping exception; read/append также сохраняют exact first error/nativeError,
  а не заменяют allocationFailed на recoveryRequired при следующем вызове.
  Наблюдённый невозможный actual size для appendPosition теперь sticky invalidContent.
- M2: implicit copy assignment CustodyNativeJob удалён; static assertions
  подтверждают non-copy-/non-move-assignable token.
- M3: count0, count>266240 и signed-offset overflow отвергаются в public read
  до metadata queries/admission/result allocation; defensive State check сохранён.

### Проверки main на искусственных данных

Начальная отсутствующая Owner header дала compile failure2 (session43398),
это не behavioural RED. Первый воспроизведённый behavioural RED на old product:
session81597, CTest8/0xc0000409, assertion line185 — повторный отказ менял
allocationFailed на recoveryRequired. После fixes focused native1/1 PASS0,84s
(session62744). Отдельный native run финальных nested catches/test bytes:
1/1 PASS0,61s (session56562), /W4/WX. H1 interleaving не выдаётся за отдельный
deterministic old-source RED: source counterexample и final scoped tests отделены.

Синтетические native assertions покрывают birth/prefix/HEAD codec check;
guard lifetime через retained result; new epoch после actual final close;
external writer denial; retained writable mapping/view denial даже после close
исходного file/mapping HANDLE; hardlink и actual named ADS rejection;
двухчастный max DATA append/read и refusal old-offset overwrite;7 HEAD cuts;
3 second-DATA-chunk cuts с orphan preservation; unknown stream-enumeration end;
pin32/job4/owned64MiB exhaustion; exact sticky allocation errors и static bounds;
metadata bad_alloc в четырёх methods, в post-flush/post-HEAD final recheck;
simulated invalid actual size. Exception-object destructor отдельно подтверждает,
что native job ещё занят при exception cleanup. Competing-writer rendezvous
подтверждает ambiguous HEAD и отказ subsequent flush без дополнительного IO;
ready signal означает готовность перед вызовом, не доказанную очередь на mutex.
Native faults — TU-local wrappers вокруг REAL Files.cpp, не product knobs.

Финальные результаты на приведённых ниже product/test bytes:

- Portable rebuild0 и CTest38/38 PASS23,83s (session62872), source root
  `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows`,
  build `/tmp/graf-f200-recovered.yQYDxv`.
- Native full CMake build0 и CTest40/40 PASS34,93s (session14900), serial `-j1`,
  Windows11 ARM64 VM/x64 emulation. Owner suite0,91s. Это также повтор v1 регрессий.
- VS solution Release/x64 build0 и GrafWindowsCoreTests.exe exit0 (session34357).
  AEC3 source/license identity `846fe90a289f58b7c9303a635142aa2c7caa93e5`
  подтверждена прежним guard. D9025 `/W1`→`/W4` warning остаётся; warning-free
  build не заявляется. SHA-256 built, НЕ installed, GrafWindowsApp.exe:
  `cb7fcb0796ae21967de4fed53120afcb01a4e3f4a50a0c56d197f85ec319a869`.
- Canonical→mirror→guest шесть product/build/test hashes совпали (session34357).
  Ранее случайно выбранный portable cache42T77W содержал удалённый old source root:
  rebuild отказал,3 old-fixture tests упали; session83782 исключён из acceptance,
  cache не восстановлен фиктивным old path. Текущая полоса выше собрана заново.
- Governance и frozen bootstrap прошли перед документированием (session75125);
  после сохранения результатов требуется отдельный повтор guards/YAML/diff check.

| Финальный файл (относительно apps/windows) | SHA-256 |
| --- | --- |
| RecApp/Storage/ProtectedPackedCustodyOwner.h | d13e7aeb8263c7ba055c1394343d65abfec6ca9f93f875f360b53ccdc66c2d56 |
| RecApp/Storage/ProtectedCustodyFiles.cpp | fe81d4d3bc6cb7a2a076f9f9bddfdbd533ef418a8753e45739b3f52252a83476 |
| RecApp/Storage/ProtectedCustodyFiles.h | 108f2e989b081812a38a2464a3eda9930fe35c1173a86df0f288851e6aefeced |
| RecApp/Storage/ProtectedCustodyMemory.h | a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad |
| Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp | 476f86fd6d154a0e74fac0f0b58426b1b7b24e5ef68d6be9d2a49a4fc3c0391e |
| CMakeLists.txt | 8d00272d945d5f0880cd3bc1b91753931bf05d2abb84450c7d6511de07764e52 |

Scoped ponytail-review main: Lean already; сохранён один confinement backend,
native codec/allocator переиспользованы, generic writeAt/fault/config framework
не добавлены. Independent current-source recheck после fixes ещё ожидается;
старый source approval не переносится на новые bytes.

T116/issue/F200 остаются открытыми. Следующий срез — typed descriptor/node
structure, guarded cold closure/tree proof и bounded delta writer/paired ACK,
затем consumers/migration/generated full pipeline/100cycles и measurements
по T116/T117/T118. Packed format ещё не подключён к записи и не принимается
за устранение v1 O(N²) до измерения новой полной цепочки. Установленный GRAF0.1.0.11,
частные файлы/звук, microphone/clock tolerance, macOS и сервер не менялись.
MSIX/install/live UI/auth/upload/physical x64/60min audio/accessibility/trusted
external signing/release не выполнялись. Commit/push/PR/merge/release отсутствуют.

### Раунд218 — финальная независимая проверка и завершение scoped среза

Independent current-source recheck2 завершён: scoped source APPROVED,
C0/H0/M0; H1/M1/M2/M3 CLOSED только для frozen bytes таблицы выше.
Main прочитал ordering/lifetime/error/admission выводы и повторно сверил hashes.
Финальный report `checklists/review-2026-10-03-packed-owner-source.md`, SHA-256
`7a17351fcd67bc14a37e6ba9572f8f52303b31541f162b89cdb1cf64b6cef731`.
Reviewer не запускал runtime/compiler/VM и не принимает execution gates;
последняя VS строка report атрибутирована main, terminal34357 exit0.
Рецензент закрыт после передачи результата, competing source edits отсутствуют.

После основного документирования YAML parse/diff check прошли; governance и
frozen bootstrap повторно PASS (session15144). Удалён только один оставшийся
synthetic fixture аварийного RED: перед удалением проверены exact путь/3 файла,
отсутствие reparse и искусственные store/object IDs; session26988 exit0,
SYNTHETIC_RED_FIXTURE_REMOVED=True. Это воспроизводимые искусственные данные,
не пользовательский пакет или audio; private inventory не перечислялся.
Финальное дополнение сопровождается отдельным повтором YAML/guards/diff check.
Этот source prerequisite принят, но tasks/T116/issue/feature не закрываются.

## Раунд219 — current-pair cold verifier и ограниченное чтение дерева (2026-10-03)

Работа продолжается только в
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Изменения dirty/untracked;
HEAD сам по себе не идентифицирует новые исходники. Commit/push/PR/merge/release
не выполнялись. Установленный пакет, пользовательские записи, macOS runtime и
сервер не изменялись; микрофон/audio/private inventory не читались.

`speckit-analyze` и `speckit-implement` использованы последовательно;
disabled hooks не запускались. Prerequisites/governance/frozen bootstrap были
проверены; повтор после окончательной записи evidence обязателен. Независимый
requirements gate `checklists/review-2026-10-03-packed-tree-gate.md` подтверждает
scoped C/H=0 и нормативный readback112 checked/0 unchecked. Reviewers отвечают
за собственные отчёты; main не меняет их markers. T116 остаётся открытой:
этот срез не принимает весь protected-storage поток или приложение.

### Реализация и границы доказательства

`ProtectedPackedCustodyFormat` разбирает descriptor128, adjacent HEAD pair и
все64 Ref64 каждого NODE по принятому contract: exact count/length/version,
actual EOF/extent, уровни/base/slot, canonical EMPTY/ZERO и exact tail DATA.
Parsed descriptor — не proof. Дополнительное требование создания child version
относительно parent не вводилось; provenance будущего live delta остаётся
самостоятельной работой.

Новый `ProtectedPackedCustodyTree::verify()` удерживает private stack Guard:
один admitted NativeJob, strong Owner и тот же State mutex, который используют
raw append/publish. Внутри Guard независимо читаются обе текущие HEAD, затем
полные обе closures с SHA-before-DPAPI и контекстом из проверенного parent.
Проверка потоковая, глубина3, без плоского N-sized индекса/bitmap/cache. Полученный
immutable same-owner root даёт только bounded `readBlock()`; старый proof читает
свои bytes после raw g3/g4 публикаций. Он не даёт authority историческому root,
metadata/package, live commit/ACK, upload, migration, GC или deletion.

Proof/read-result pins допускаются до owned allocation; NativeJob и mutex
сохраняются через классификацию отказа. Plain result удерживает proof/Owner,
ZERO синтезируется только из проверенного explicit ZERO, не вместо missing DATA.
EOF здесь block primitive `invalidInput`, не готовый IStream adapter.
Ограничения64MiB/32pins/4jobs не ослаблены. Inline ZERO fixture на64GiB проверяет
wire/range и retained allocations, не peak memory, sequential cadence или N-scale.

### Test-first, независимая проверка и воспроизведённые отказы

Первый descriptor test действительно RED: session51702 build0/CTest8,
не реализованный decode birth отвергнут assertion187. После реализации
focused Format PASS (sessions69253/2121). Новый Tree suite использует только
генерируемые TempGUID fixtures с искусственными IDs и native user-scope DPAPI.
Покрыты повреждения обеих HEAD/closures, shape/extent/slot/base/SHA/tail,
сохранение первого отказа, закрытие Owner, pinned old root и quota admission.

Независимый source reviewer выявил validation M1/M2: charged/exception/pin
случаи и живое удержание old root/конкурентную операцию. Добавлены реальные
charged ZERO/DATA/verify refusals, pin31/pin30, final-metadata exception и
whole-case cleanup baseline. Конкурентный тест теперь требует наблюдения
допущенного publisher job под held Guard: verifier1+publisher1+probes2=cap4,
третья probe отвергнута. Один `writerReady` более не считается доказательством
входа. Это TU-local test wrappers над реальным Files.cpp, не product fault knobs.

В Debug выявлена дополнительная настоящая граница: charged iterator proxy
в noexcept default/move vector construction мог завершить процесс вместо
`allocationFailed`. Первый отказ Owner в старом Debug прогоне не скрыт:
session23561 завершился неуспехом; точный synthetic PID4528 остановлен после
подтверждения CRT abort dialog. Диагностические промежуточные неуспехи
52036/59663/1528/29426 не принимаются как PASS. Test-only CRT вывод настроен
в stderr, чтобы assertion/abort не ждал человека; iterator checks не отключены.

Перенос создания результата внутрь held-lock try и explicit count constructor
устранил default-construction границу, но reviewer затем нашёл H1 в move return.
Его отдельный Debug exact-fit ZERO test измеряет реальную proxy charge:
native session72885 build0, `--exact-fit-zero` EXIT3 до исправления.
После исправления native session97565 build0,
`--exact-fit-zero` EXIT0 и `--exact-fit-physical` EXIT0. Это точечный RED→GREEN,
не финальная полная проверка последующих compatibility/test изменений.

`CustodyBytes` сохраняет стандартный vector/тот же charged allocator, но default
и move строят potentially throwing empty-count storage до переноса через swap.
У `PackedPlainRead` убран outer noexcept move. Byte temporaries обнуляются при
разрушении, в том числе при failed optional/result transfer. У прежних reader/
writer исправлены noexcept cleanup с allocating empty temporary и buffer
construction до try в CopyTo. Wiping precedes release; retained capacity при
отказе shrink остаётся charged. Native DPAPI/CNG не заменены своей криптографией.

### Точные снимки и проверки

До H1/последнего исправления session52807 подтвердил native Release41/41
PASS39,29s, VS build0/Core0; built exe SHA-256
`08ccafbbe68db83c6b3c26c80c5b7a2dafd5b7f2220ed8282cf98a845ee28b22`.
Предыдущий portable session88956 дал39/39 PASS24,28s, focused Debug10751
дал2/2 PASS11,94s. Эти результаты исторические и НЕ перенесены на новые bytes.

На приведённом ниже текущем снимке portable rebuild/CTest session76810:
39/39 PASS71,06s. Native-ветки portable tests не выполняют. Canonical→mirror→
guest source/build/test14 hashes совпали (session92984). Два чрезмерно длинных
EncodedCommand batch97281 и повтор отказали в создании Parallels session до
получения build receipt; они исключены из acceptance. Короткие commands
`cmd /c ver` и hash/copy succeeded; guest не перезапускался. Точная причина/
числовой предел длины команды не объявлены доказанными.

| Текущий файл относительно apps/windows | SHA-256 |
| --- | --- |
| RecApp/Storage/ProtectedPackedCustodyFormat.h | 0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88 |
| RecApp/Storage/ProtectedPackedCustodyFormat.cpp | bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f |
| RecApp/Storage/ProtectedPackedCustodyOwner.h | 11f4253afe0726781f8319315ba2c707571ac574f23c55aa9b2cf5ce2e0faae6 |
| RecApp/Storage/ProtectedCustodyFiles.cpp | 01ea3672a46cda99e7dffabc30641468de133c77edd30af23b9fa26b534c8bff |
| RecApp/Storage/ProtectedPackedCustodyTree.h | 5e6bc4fa096c13d3e247be5e6bc581fcc6bfb8cb0f697815d584db416943be85 |
| RecApp/Storage/ProtectedPackedCustodyTree.cpp | 11e54696cff69e2421ca312a9e351476cc4979a03f60a5e9bee1e17427b0559f |
| RecApp/Storage/ProtectedCustodyCodec.h | 43c62045f7f31a14127e74310ba09cbead0dffb6272343fc968178401cd4e68b |
| RecApp/Storage/ProtectedCustodyReader.cpp | f8e54ccb3d39ab42803a05be36716b982b1b4e49798f1550df569d978205a676 |
| RecApp/Storage/ProtectedCustodyWriter.cpp | a9a78170945687c4ef8ce58f31960ec2f673190bdfa6bc251a5b5742689cbaa0 |
| Tests/GrafWindowsCoreTests/ProtectedPackedCustodyFormatTests.cpp | d18d3a21c5453964d5381fb4507dce9c26cc871689a8ae6e2ac507fa888fd48e |
| Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp | 9201c6c995c21a7f7bc72300b4dc7d7d50d2363fb9494f6a35fee73ec59f1bd7 |
| Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp | 60c2e2d6db44b0aea6b3d13acce5afee3e3e13ec336f90eca4218630d26d8b3e |
| CMakeLists.txt | b659c852c0c66e455238230b1b05d52292fadf09925ef294e6f322c3a5247b6d |
| RecApp/GrafWindowsApp.vcxproj | 2949fea918a96cad9b4de63d485ab6a0b0c1c35bb66af5e75f43689f0eba7b72 |

Финальные native Debug/full Release/VS receipts и повторный source review ещё
не приняты этим разделом; будут записаны отдельным дополнением после получения.
Задач119/closed93/open26; tasks SHA
`ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98`
и packed contract SHA
`7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed`
не изменились в этом раунде. T116/117/118/119 и полная приёмка остаются открыты.
Далее — live bounded tree update/commit и pinned IO adapter, затем strict
metadata/integration, migration и полный application/hardware acceptance.

### Раунд219 — исправления отказов, чистая пересборка и новая идентичность

После первого среза независимая проверка нашла H2/M3. Они исправлены:

- H2: первый вызов process-wide cache выполняется внутри factory try после
  успешного pin admission, до native open и создания ReaderState. Закрытие
  последнего stream больше не является точкой первого выделения cache proxy.
- M3: в PackedPlainRead/PackedCipherRead потенциально бросающий перенос bytes
  происходит до передачи pin/proof/owner. При отказе исходный результат
  сохраняет данные, фактического владельца файла и admission. Тело деструктора
  PackedPlainRead по-прежнему стирает plaintext до освобождения proof/pin.
- При расширенной проверке metadata staging обнаружен ещё один default-vector
  allocation внутри noexcept MSVC constructor. Candidate entries теперь
  создаются explicit count=0 внутри существующего worker try; exact-type
  prvalue прямо инициализирует aggregate field без промежуточного move.
  Memory/pin/job limits и iterator checks не изменены.

До исправлений Debug сборка тестов проходила: isolated H2 (`92400`) завершился
EXIT3 при измеренном proxy16B; isolated M3 plain/cipher (`81073`) оба EXIT3 на
assertions потерянного владения. После исправлений (`44460`) все три isolated
cases EXIT0; H2 cleanup=16B соответствует единственному process-cache proxy.
Это не было полным suite PASS: FilesTests в том же запуске завершился отказом.

Причины полного Debug отказа разделены, а не скрыты заменой лимитов:

1. Metadata pressure setup считал свободные bytes до выделения собственного
   Debug proxy и падал до worker call (`41566`). Теперь test сначала создаёт
   pressure buffer, затем резервирует реально оставшуюся capacity. После этой
   поправки отказ worker был воспроизведён (`52392`) и исчез после explicit
   candidate construction (`99722`, metadata phase completed).
2. В writer cleanup трассировка `82252` показала вызов CustodyBytes constructor
   из clearDirty, хотя guest source SHA уже соответствовал clear/shrink варианту.
   После clean-first пересборки `42537`, действительно перекомпилировавшей Writer,
   закрытие owner прошло. Причина рассогласования времени/инкрементальной сборки
   отдельно не доказана; факт source hash не приравнивается к свежему object code.
3. Следующий assertion касался test baseline: pressure proxy16B ещё был жив.
   Pressure теперь освобождается целиком выходом из области видимости. Аналогично
   snapshot pressure cleanup не выделяет empty replacement на полном бюджете.
   Временные phase markers, terminate stack handler и DbgHelp include удалены.

Предыдущие incremental/pre-fix receipts выше не переносятся на окончательный
срез. Новый нативный исходный cohort содержит16 файлов; canonical→mirror
и mirror→guest совпадают (session95206: SOURCE_MATCH=16/16). Canonical→mirror
дополнительно сверены все183 tracked/non-ignored Windows source files без
различий. Guest comparison compiled RecApp/Native/Tests выполняется отдельно;
это не сравнение установленного пакета или application acceptance.

SHA-256 относительно `apps/windows`:

| Файл | SHA-256 окончательного среза |
| --- | --- |
| RecApp/Storage/ProtectedPackedCustodyFormat.h | 0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88 |
| RecApp/Storage/ProtectedPackedCustodyFormat.cpp | bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f |
| RecApp/Storage/ProtectedPackedCustodyOwner.h | ac096cb8521e1c818b70c0a8147f4b93661b434fa117068149286ea4c7412b75 |
| RecApp/Storage/ProtectedCustodyFiles.cpp | b29146e86800531c0ef3447fb32bd7846fc17214c418abe5bf5d2e83a7af1825 |
| RecApp/Storage/ProtectedPackedCustodyTree.h | 7209dbfb5a8ba40e0f3afe9032a6bc8d15c2a70b71e54868b518a6fe5edcd586 |
| RecApp/Storage/ProtectedPackedCustodyTree.cpp | 11e54696cff69e2421ca312a9e351476cc4979a03f60a5e9bee1e17427b0559f |
| RecApp/Storage/ProtectedCustodyCodec.h | 43c62045f7f31a14127e74310ba09cbead0dffb6272343fc968178401cd4e68b |
| RecApp/Storage/ProtectedCustodyReader.cpp | 59a72176bff303c5abb34a352015a755481766126f8ff7c5c84c04607f7ab7d9 |
| RecApp/Storage/ProtectedCustodyWriter.cpp | a9a78170945687c4ef8ce58f31960ec2f673190bdfa6bc251a5b5742689cbaa0 |
| RecApp/Storage/ProtectedCustodyMetadata.cpp | 8ae8b8a35fd4f2fa90bc000725fefe711dbba0de56a20d00345fcc5691edad49 |
| Tests/GrafWindowsCoreTests/ProtectedPackedCustodyFormatTests.cpp | d18d3a21c5453964d5381fb4507dce9c26cc871689a8ae6e2ac507fa888fd48e |
| Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp | 9201c6c995c21a7f7bc72300b4dc7d7d50d2363fb9494f6a35fee73ec59f1bd7 |
| Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp | 59e976433e56856c18ffb88090387204c472a2991ab92c901d29450258d00c3e |
| Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | 5fed021b71a3cddfdddcafa77a029ad32924c3712fc0bedf5f1aa8bfd32b06be |
| CMakeLists.txt | b659c852c0c66e455238230b1b05d52292fadf09925ef294e6f322c3a5247b6d |
| RecApp/GrafWindowsApp.vcxproj | 2949fea918a96cad9b4de63d485ab6a0b0c1c35bb66af5e75f43689f0eba7b72 |

Свежие terminal результаты:

- Debug: clean-first target build `42537` EXIT0, затем final test rebuild/CTest
  `91706` EXIT0, **3/3 PASS 12.26s** (Owner1.15s, Tree2.99s, full Files7.99s).
  Нормальный Tree/Files main включает новые move/cold-close regressions.
- Native Release: clean-first full build `10918` EXIT0, CTest EXIT0,
  **41/41 PASS 40.18s**. Release proxy0 не выдаётся за Debug fault injection.
- Portable: clean-first full build/CTest `8829` EXIT0,
  **39/39 PASS 25.34s**. Unsupported native cases остаются unsupported.

Visual Studio Rebuild/CoreTests/app SHA и финальный independent source readback
ещё ожидаются и будут зафиксированы отдельным дополнением. Commit/push/PR/merge
не выполнялись. Feature/contract/tasks не изменены:119/93/26, T116 открыта.
Current-pair root/read prerequisite не равен live writer, v1 admission,
protected pipeline integration, migration или готовому Windows-приложению.

### Дополнение к раунду 219: H3, charged entries и безопасная передача метаданных

Срез ниже заменяет предыдущий 16-file cut только для новой H3 allocation/move
проверки. Старые результаты остаются историческими, не evidence новых bytes.
Канонический checkout `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d` без нового commit. Код dirty/untracked;
одного HEAD недостаточно для идентификации реализации.

Подтверждённый pre-fix native Debug RED `71625`: clean/current writer-open
pressure regression завершалась EXIT3, а не typed allocation failure.
Исправление распространяет уже требуемую безопасную charged byte policy на
`CustodyIndex.entries`: единый `CustodyVector<T>` создаёт empty storage через
potentially throwing count0 ctor и только затем меняет storage местами.
Default/move не обещают `noexcept`; равный stateless allocator обеспечивает
nonallocating move assignment с self-move guard. Proxy allocations, iterator
checks и общий 64MiB budget не исключены. Byte destructor/move assignment
сохраняют wipe живых bytes. Нет новых registry, app keys или общей authority.

`CustodyMetadataCommit` сохраняет исходный порядок полей и обратного destruction:
snapshot освобождается прежде lease, lease прежде admission pin. Throwing
snapshot move готовится до передачи source pin/lease; успешная передача этих
двух owners выполняется в теле конструктора без allocation. При failure source
продолжает удерживать тот же файл и admission. Pin остаётся nonassignable;
новый move assignment не добавлялся. Error return сбрасывает snapshot перед
переносом результата, сохраняет lease/pin и sticky ambiguous после начала
публикации; normal success/commit не объявляется.

Новая native Debug сборка `1232` обнаружила настоящий compile failure /WX C4244:
range ctor выбирался для `CustodyBytes(16,0)` с Iterator=int. Добавлено обычное
`!is_integral_v` ограничение range overload; warnings не подавлялись. Исправленная
clean-first product/target build `6623` EXIT0. Это не старый binary receipt.

Isolated Debug `37585` EXIT0 во всех трёх новых regressions:

- `--entries-move-budget`: measured entries/index/snapshot proxy16B каждый,
  throwing default/move traits, failed index/entries/snapshot moves сохраняют
  точное source storage/value; assignment/self-move не выделяют новую память;
  полный cleanup возвращает charge к baseline.
- `--writer-open-budget`: typed allocationFailed до native IO, без terminate.
- `--metadata-move-budget`: отказ прямого move и optional emplace сохраняет
  snapshot, real lease и один из32 pins; raw second write получает sharing denial.
  После head publication allocation failure возвращает ambiguous с lease/pin,
  без snapshot и без повторной allocating move при error return.

Нормальный Debug sequence `6060` нашёл отдельный test defect: старый
`memoryBudgetTests` сравнивал только capacity bytes и игнорировал charged Debug
proxy (assert line240). Три другие группы прошли. Исправлен именно test accounting:
actual proxy измеряется, move/empty cleanup учитываются; parallel12-buffer test
подготавливает все proxies до worker reservations и по-прежнему требует ровно
четыре принятых capacity reservations и заполнение точного лимита64MiB.
Production limits и assertions не отключались. `96843` —4/4 PASS22.02s.

Добавлена отдельная partial-headroom проверка в metadata regression: доступно
ровно measured p16B, candidate proxy помещается, reserve первой entry отказывает
до native open; возвращается notCommitted/allocationFailed без lease/snapshot,
native counters не меняются, charge восстановлен, все32 admission pins доступны.
Окончательный focused Debug `49243`:4/4 PASS21.02s
(Codec3.71s, Owner1.31s, Tree3.31s, Files12.62s). Product clean build —6623;
последующие rebuild меняли только два test TU, не использовали stale product IO.

Новый stable cohort состоит из18 файлов:13 неизменённых из предыдущей таблицы
и следующие пять актуальных файлов (два добавлены в identity cohort):

| Файл относительно apps/windows | SHA-256 |
| --- | --- |
| RecApp/Storage/ProtectedCustodyCodec.h | a5152a136c102b285e5e34cc926a9c6da7f6c3c43a5acca5707069a757e3dcde |
| RecApp/Storage/ProtectedCustodyMetadata.h | 7d05cf97fc255c30e7171cd4159fb53fe239efacc402944ec629b85f983bb2cd |
| RecApp/Storage/ProtectedCustodyMetadata.cpp | 739b40a5670227530554a9fc3c92a41a86c2b2577a1d9ac92c3ee118581dab74 |
| Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | 388c78d27ab21cb9f203547feb209277ecf8048a156276f6fd20fa8ce139143a |
| Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp | ff3661b517680938096ef9c3fc4756bf5a2f0e1f46b6344a93e8202af013d38a |

Native mirror→guest comparison `32169`: COMPILE_SOURCE_MATCH155/155 для
RecApp/Native/Tests `.cpp/.h/.hpp/.c/.rc/.vcxproj` после последних test edits.
Final portable clean-first `51271`, native Release clean-first `94121` и
Visual Studio/final independent review будут записаны только по terminal receipts.
Pre-H3 portable/Release/VS approval не переносится на этот type policy.

Feature/tasks/accepted packed contract hashes не изменились;119/93/26 задач,
T116–T119 открыты. Эти source fixes не подключают encrypted-at-rest ко всему
приложению, не закрывают migration, installed UI/audio/hardware/accessibility
acceptance и не разрешают release. Установленный GRAF, Telemost, private inventory,
микрофон, macOS/server runtime не менялись; commit/push/PR/merge не выполнялись.

### Раунд 219, final H3 test applicability и текущие terminal receipts

Native clean-first Release `94121` BUILD_EXIT0, но CTest40/41 EXIT8: новый
writer-open-budget ожидал charged proxy allocation failure и в Release, где
measured proxy0 и State может быть создан без charged vector allocation.
Это test applicability defect, не отказ текущего production writer. Тест теперь
измеряет CustodyIndex proxy и явно сообщает `SKIP-no-proxy-allocation-fault`
при proxy0; Debug proxy16 case и его typed-failure/no-IO assertions остаются.
Ни iterator checks, ни budget, ни production failure classification не отключены.

Единственная следующая source delta — FilesTests SHA-256
`e00d64cf3c4682eb21dce1dbaa5c99d78970c60e3b2aa9e03633ae827b26ffe5`.
Остальные17 файлов предыдущего H3 cohort не изменились, включая
CodecTests `ff3661…`, Codec.h `a5152a…`, Metadata.h `7d05cf…`, Metadata.cpp
`739b40…`. `388c78…` и его receipts выше сохранены как предыдущий test cut,
не объявляются byte identity окончательного FilesTests.

После пересборки только изменённого test TU, при неизменных свежих clean-built
product objects, терминальные результаты текущего18-file cohort:

- Windows Release `16265`:41/41 PASS49.33s, EXIT0; product clean build94121.
- Windows Debug `96206`:focused4/4 PASS25.36s, EXIT0
  (Codec4.90s, Owner1.52s, Tree4.31s, Files14.54s); product clean build6623.
  Это четыре указанные группы, не full41 Debug claim. H3 partial-headroom и
  move/owner regressions включены в обычный main и не удалены ради Release.
- Portable `97843`:39/39 PASS14.05s, EXIT0 после изменённого FilesTests rebuild;
  full clean product build51271. Native unsupported branches не выданы за PASS.
- Canonical→mirror все183 tracked/non-ignored Windows source files — совпали.
- Native mirror→guest `27786`:COMPILE_SOURCE_MATCH155/155 для фактических
  compiled source extensions RecApp/Native/Tests, после окончательной test delta.

Новый Visual Studio Rebuild `61697` ещё выполняется; результат и hash сборки
будут записаны отдельно после завершения. Никакие старые exe/MSIX receipts
не доказывают новый H3 type policy. Installed runtime/дизайн/сценарии не проверялись
и не обновлялись этим прогоном; full T116/T117/T118 acceptance остаётся открытой.

### Раунд 219: terminal Visual Studio и binary identity H3

Новый `61697` завершён: `VS_REBUILD_EXIT=0`, GrafWindows.sln Release/x64,
`/t:Rebuild`, current18-file source cut с FilesTests `e00d64cf…`.
CoreTests и приложение перекомпилированы; для app выполнена полная генерация
19174 функций, без пригодного предыдущего IPDB/IOBJ. Source/license identity
AEC3 проверена штатным build target: `846fe90a289f58b7c9303a635142aa2c7caa93e5`.
Известные warnings D9025 (/W1→/W4) и сторонние WebRTC C4100 остались;
warning-free build не заявляется. Исправленный native CMake код собирался с /W4 /WX.

`58899`: `GrafWindowsCoreTests.exe` CORE_EXIT0. Новый **built, NOT installed**
`C:\Temp\graf-f200-native-f4d8739a6fe345f78ceabaebed7d71f9\out\x64\Release\GrafWindowsApp.exe`
имеет SHA-256
`3ea4a30911a7bfe3b49444b315dca56cbb4ea6100f7731f698c8352496b47424`.
Этот receipt заменяет старый `0109…` только как идентичность текущей сборки;
MSIX, development/public signature, installed app или runtime acceptance из
него не следуют. App EXE не запускался, микрофон/записи не открывались.

После всех прогонов ещё раз совпали пять актуальных source hashes
`a5152a…/7d05cf…/739b40…/e00d64cf…/ff3661…`, HEAD прежний99b00a…;
source dirty/untracked и не приравнен к commit SHA. Final canonical/mirror183/183,
guest compiled inputs27786 —155/155. Некоторые Parallels exec запросы вернули255
Invalid argument, а короткие/повторные read/copy команды работали. Точная причина
этого transport failure не доказана; VM/Tools не перезапускались и не обновлялись.

Проверка сложности `ponytail-review` в узком H3 scope: `Lean already. Ship.` —
нет безопасного удаления общей bytes/entries policy или исключительных ownership
границ. Это оценка сложности, не approval выпуска. Временные DbgHelp/StackWalk/
set_terminate/phase hooks отсутствуют в двух проверенных test TU.

Усиленный путь Spec Kit `high-risk-product` сохранён, before/after implementation
auto-commit hooks disabled. Governance/frozen bootstrap/YAML/diff checks прошли;
последний source cut ещё получает отдельный reviewer readback. T116/T117/T118/T119
и полный Windows parity не закрыты; будущий live tree update, подключение ко всей
цепочке и миграция остаются обязательными. Установленное приложение, private
inventory, macOS/server runtime не менялись. Commit/push/PR/merge/release отсутствуют;
implementation commit требует явного разрешения пользователя после validation.

Финальный independent reviewer readback в
`checklists/review-2026-10-03-packed-tree-source.md`: SOURCE ACCEPTED,
H3 CLOSED в этом bounded scope, C/H/M0/0/0; текущий список17 checked/1 unchecked.
Reviewer лично повторно сверил18 local source SHA; execution/guest/binary results
атрибутированы main, не выдаются за собственные запуски reviewer. Единственный
unchecked — fault execution точной engaged-snapshot worker error-return ветки:
source exception/ownership correctness проверена, исполнение этой конкретной
ветки не доказано. Это сохранённая nonblocking coverage boundary, не full-T116
acceptance и не новый product HIGH. Historical16 marks не суммируются с текущими.
