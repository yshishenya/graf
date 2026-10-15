# Round259: SOURCE-проверка порядка Windows/WinUI заголовков

## Вердикт и область

**SCOPED SOURCE APPROVAL — только mechanical compile fix в AppMain.cpp.**
Блокирующих замечаний в этом исправлении не установлено. Свежий SDK259i
receipt подтверждает restore0/build0 на exact179 inputs. Это не whole-app
GREEN, не runtime/UI acceptance и не закрытие T116 или legacy RED257/B1.

Использован `code-reviewer`; продолжение existing high-risk T116, без нового
runtime-контракта/требования или изменения public typed API. Reviewer пишет
только этот новый отчёт. Production/tests/spec/plan/tasks/старые отчёты,
GitHub/VM/profile/commit не менялись. Сборки и binaries reviewer не запускал.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty работа main сохранена.

## Причина и минимальное исправление

Лично прочитаны actual AppMain includes1–100 до/после переноса,
LocalRecordingPackage.h, ProtectedCustodyReader.h и соответствующие metadata/
files dependencies; CabinetWindow.h → WebView2Host.h и его ранние dependencies.
Проверены include/conditional directives всех прямых callers этих заголовков
в RecApp/Tests; это не новое полное ревью каждого caller body.

Старый порядок: AppMain включал LocalRecordingPackage.h:10, который теперь
включает ProtectedCustodyReader.h с objidl.h/wrl/client.h. Затем CabinetWindow.h:12
включал WebView2Host.h с projected Microsoft.UI.Xaml.Controls.h. Существующие
undef GetClassName/GetCurrentTime стояли только после проектных заголовков,
то есть после возможной обработки WinRT projections под Windows aliases.
Поздний undef не исправляет уже обработанные объявления.

Main сообщил SDK diagnostics GetClassName not member в generated Automation.Peers
и GetCurrentTime macro warning. Сохранённый failed receipt не содержит текста
diagnostics; reviewer не объявляет эти строки лично прочитанным raw build log.
Source trace согласуется с сообщённой причиной. Успех сборки после единственного
изменения порядка подтверждает устранение compile blocker в проверенной lane.

Теперь AppMain:3–10 включает windows.h и снимает обе aliases внутри _WIN32,
**до первого проектного header**. Остальные platform includes остаются позже.
Нового Pimpl/helper/macro policy/generated-header patch/dependency нет.
Directory.Build.props уже задаёт WIN32_LEAN_AND_MEAN/NOMINMAX; они не менялись.
В RecApp не найдено GetClassName()/GetCurrentTime() вызовов, которым требовались
бы эти aliases. В прочитанных прямых caller include orders не найден второй
такой же новый COM → WinUI → late-undef порядок. Это не обещание отсутствия
любых будущих macro collisions при изменении других headers.

## Точное сравнение source

| Snapshot | AppMain SHA256 |
| --- | --- |
| failed SDK259h / historical native172 | 2b7fb97f1a64853b78146cb715bfe3f752a11908727ed4fb2d0babade63194dc |
| passed SDK259i / current canonical | 52435fb55a5c8a8f7cab3c5052381d4a9a5373f590e530f139577beda2a99c3e |

Source maps h/i обе содержат179 inputs, exact same path set: added0/removed0.
Изменён **только RecApp\\AppMain.cpp**, остальные178 hashes совпали.
Лично вычислены hashes каждого current canonical `apps/windows/<path>`:
179/179 MATCH с i, missing0. Каждый SDK receipt source_hashes exact совпадает
со своим source map; это hash binding inventory, не SOURCE review всех179 files.

Обратный перенос actual current блока на старое место и восстановление старого
комментария сделаны только в памяти: полученный whole-file SHA exact совпал
с h. Так доказано отсутствие других изменений в AppMain между h/i: bodies,
public API, account/queue/capture/admission правила не переписаны. Изменение
имеет compile-time цель; runtime equivalence/работа установленного приложения
не доказываются одним успешным build.

## Лично прочитанные immutable SDK exports

External root: `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI/`.
Receipts parsed readonly; BOM снят только в памяти. SHA256 вычислены по исходным
bytes с BOM, никакие exports не нормализованы/переписаны.

| Export | SHA256 |
| --- | --- |
| source-sdk-round259h.json | 8177d598ef056994d0bc5bafdc4db267cde89dd43a5c889002261874809aea15 |
| graf-f200-sdk-live-round259h.json | 3077dd5affcb9f707a0260ad484bcc7074894acad0a93ad27b22a477e1c70c53 |
| source-sdk-round259i.json | ab0e2d86968d8328de6c7c63f94434045ee48de4409ee832bb91d3fd6885a32b |
| graf-f200-sdk-live-round259i.json | 585458eb3fcb2891f9a7d7712b3b3ec593770ba568f0e217d442235fd2489344 |

h: mode full-sdk-app-build-only, terminal=true/phase=failed, restore0/build1,
source_count179, exe_sha256=null. Не объявлен successful artifact.
i: тот же mode, terminal=true/phase=passed, restore0/build0, source_count179.
Лично прочитанный EXE hash **из receipt**:
`a28c858972f6939c631ad5817cef5c137eb2305354bf3e0bac783adc952a4910`.
Это не reviewer NTFS reread или исполнение EXE.

Build helper i лично прочитан: MSBuild GrafWindowsApp.vcxproj Restore/Build,
Release/x64, mirror hash preflight, actual copied source post-build hash check,
actual output EXE hash; external receipt export CreateNew. Нет launch/package/
sign/install. Helper не запускается reviewer. SDK Debug/ARM64 и fresh complete
native suite после нового AppMain этим receipt не подтверждены.

## Исторический full native259g: не current GREEN

Отдельно лично parsed/hash-verified `graf-f200-all-round259g.json` и целиком
прочитан raw `graf-f200-all-round259g-test.log` (879 строк, без пропусков).

| Export | SHA256 |
| --- | --- |
| graf-f200-all-round259g.json | 55e0e5bc07927a6ffee4f76ca760105b7ee9be4443f4f6a88222e2dd7d0328a5 |
| graf-f200-all-round259g-test.log | 85ee77a3d1bcf8375530ca716979646857fd3ef583cae4f4467fff6e3e3d9603 |

Receipt: mode full-native-suite, terminal=true/phase=failed,
configure0/build0/test8, source_count172, test_count50, EXE map50 entries.
Его source_hashes exact совпадает с прежним source-v5-round259c-matrix.json.
Из этих172 inputs с current canonical отличается только AppMain. Это честный
исторический запуск **до** include-order fix, не проверка нового AppMain.

Raw journal содержит50 команд Release binaries,49 Test Passed и1 Test Failed.
Единственный отказ — test47 NativeHashFailureTests, assertion395:
`malformed.integrity == PackageIntegrity::malformed && !malformed.playbackAvailable`.
Safe counterexample output:
original_frames48128; corrupt_decode_complete1; corrupt_frames0;
explicit_root_normal1; explicit_root_playback1; default_root_normal1;
invalid_package0; synthetic_sends1. Это прежний header-only plain path RED257,
не новый protected inspector failure и не ошибка include-order fix.
Звук synthetic; sends относится к injected transport, не real network proof.
Этот FAIL не исключён, не переименован в expected GREEN и не закрыт.

Raw test47 time2.48s; остальные49 прошли. Main сообщил CTest total271.80s;
в raw LastTest.log нет отдельного total field, сумма50 округлённых Test time
составляет271.71s. Total271.80s здесь помечен сообщённым main, а не якобы
прочитанным из отсутствующего поля. Receipt EXE hash NativeHashFailureTests:
`3265e6d51178cf3172230babf7d7541a101f9c64536e791b69ced336d4e8fa8d`.
Reviewer не перепроверял NTFS/binaries; main выполняет это отдельно.

## Сохранённые границы

Прежний SOURCE259 inspector report не изменён; лично повторно проверенный SHA:
`8502317a4e6b16a0089d35ea45b8a8967f5070e4f7bca91a41c74a55f7f3cadf`.
Его scoped acceptance не расширена на весь SDK/app flow. Старые reports,
normative checklist state и tasks93/27 не редактировались reviewer.
H250, legacy RED257/REQ257-B1, writer/queue/bootstrap/currentness/adoption,
migration, аппаратная/installed UI/выпускная приёмка остаются открытыми.
Этот отчёт разрешает принять **только** mechanical include-order compile fix
на current AppMain SHA и exact passed SDK179 evidence; не даёт разрешения
на whole-app GREEN, commit/merge/release или обход следующих проверок.
