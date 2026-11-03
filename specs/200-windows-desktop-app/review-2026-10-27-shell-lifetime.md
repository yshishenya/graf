# Независимое source review T108/T110/T111: shell lifetime, 2026-10-27

Авторитетный checkout: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Lane: scoped read-only source review внутри существующего F200 high-risk-product.
Объём: только shell lifetime T108, фоновые поверхности T110 и tray actions T111;
исходники, вызывающие участки и относящиеся к ним тесты. Полный аудит, новый
Spec Kit analyze, task/issue inventory не выполнялись.

**Итог: C0 / H0 / MEDIUM 1.** Найден один source-контрпример ошибки запуска.
Он не основан на отсутствии hardware/UI evidence. Нативное воспроизведение
самим рецензентом не выполнялось; ниже задан детерминированный сценарий для
проверки с управляемой ошибкой. Обычные рабочие пути не получили C/H/M findings.

## M1 [P2]: у Quit после частично неудачного запуска нет повторного drain

Место: AppMain.cpp:601–603, до создания stateTimer_ в строках 613–618.
Связанные участки: создание capture_/storage worker 525–526; catch 556–559;
showStartupError 2642–2658; beginExit/requestExit 2518–2535;
NativeCapture.h shutdown 554–559 и shutdownWorkDrained 1411–1418.

Точная последовательность:

1. NativeCapture создан и startStorageValidation запустил собственный worker.
2. Один из последующих шагов startup до shellReady=true бросает исключение
   (например, управляемая ошибка выделения при создании reminders_ после старта
   worker). Catch показывает экран ошибки; capture_ остаётся существующим.
3. !shellReady возвращает из OnLaunched до создания/запуска stateTimer_.
4. Пользователь один раз выбирает «Закрыть GRAF» на экране ошибки. requestExit
   вызывает beginExit, который запрашивает shutdown, и один раз проверяет
   exitWorkDrained. Если worker ещё не terminal/завершён, результат false.
5. Когда worker впоследствии заканчивает, никто больше не вызывает
   refreshNativeState/exitWorkDrained и window_.Close. Окно остаётся открытым
   после команды выхода. Повторное нажатие может закрыть его, если drain уже
   завершился; автоматического продолжения первоначального Quit нет.

Для детерминированного воспроизведения в отдельном тестовом derivative:
удержать synthetic storage worker до выхода из первого requestExit, вызвать
управляемую startup-ошибку после строки 526, выбрать существующую кнопку Quit,
освободить worker и прокачать UI dispatcher без второго пользовательского
действия. Ожидание: окно само закрывается после drain; текущий source-путь не
планирует такой опрос. Это source proof по последовательности вызовов, а не
заявление, что такая ошибка уже наблюдалась в установленном приложении.

Минимальное направление исправления: сохранить существующий polling/drain для
startup-error окна либо запланировать его при beginExit, когда штатный timer
ещё не создан. Без второго пути финализации, синхронного ожидания на UI thread
и принудительного завершения процесса. Добавить регрессию именно первого Quit
после partial startup failure с удержанным worker, затем его освобождением.

Почему имеющиеся проверки не исключают M1: testCloseSourceWiring проверяет
порядок beginExit/exitWorkDrained и наличие requestExit в showStartupError,
но не выполнение ветви !shellReady при незавершённом drain. Portable session
тесты не создают GrafApp/WinUI stateTimer. Native storage tests демонстрируют,
что после shutdown требуется ждать/опросить завершение (например,
blockedRecordingDrains и shutdownRecoveryAdmission), но не этот startup caller.

## Прочитанные рабочие пути без дополнительных findings

- Крестик главного окна: ShellClosePolicy разрешает hide только при доступном
  tray и, для активного состояния, доступном indicator/Stop. Closing отменяет
  уничтожение окна и скрывает его; не вызывает stop/requestExit и не отменяет
  automaticPolicy. Действующая запись/lease не заменяются новой сессией.
- Явный Quit из tray, web handler, fallback/button: общий requestExit/beginExit;
  закрывается admission, отменяются предложения/фоновая работа, запрашивается
  interruption Stop, затем нормальный timer продолжает Health/ACK/deletion drain.
  Closed выполняется после exitWorkDrained и освобождает ресурсы. Исключение M1
  относится к пути без созданного timer, а не к обычному capture drain.
- Отсутствие/потеря Explorer tray: available повторно проверяет NIM_MODIFY/ADD/
  SETVERSION; TaskbarCreated восстанавливает регистрацию. Fallback сохраняет
  главное окно, раскрывает inspector/Stop и возвращает его через Show(false)/
  SW_SHOWNOACTIVATE, не останавливая запись.
- Фоновые Ask/cards: прежнего automaticPromptWindow_ нет; общий presenter
  использует SW_SHOWNOACTIVATE и SWP_NOACTIVATE; WM_MOUSEACTIVATE возвращает
  MA_NOACTIVATE. Индикатор предварительно создаётся без показа, затем Show(false),
  доступность проверяется до manual/automatic capture. Ошибка его показа
  сохраняет/возвращает главное окно с Stop.
- Активация через F6, выбранный tray пункт focus/open, ручные Settings и закрытие
  индикатора — явные действия пользователя. Их Activate/SetForegroundWindow
  не классифицировались как фоновый захват фокуса.
- T111 Start/Settings используют существующие recordCapture/openAccountSettings.
  MenuAvailability учитывает capture state/readiness/exit/privacy; recordCapture
  повторно проверяет readiness/current session/admission после menu snapshot.
  Settings открывает общую account страницу; новой UI/capture logic не добавляет.

Прочитаны связанные tests RecordingIndicatorTests: policy matrix, same-session
lease и automatic end-of-meeting tracking после hide, source wiring close/drain,
tray failure/recovery, background surface wiring, tray menu projection/callers,
а также native menu fixture/lifetime проверки. Прочитаны относящиеся presenter
проверки presentation/interaction failure и NativeCapture shutdown/drain участки
и соответствующие storage tests. Это не новый аудит storage/format/сервера.

## Сохранённые portable evidence, прочитанные отдельно

Stage: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/settings-chain-li1qcg1c`.
Прочитаны финальная shell-review-build.json и сохранённый build/test log.
configure_exit=0, build_exit=0, test_exit=0; RecordingIndicatorTests 1/1 PASS,
полное ctest время 0.58 s. Receipt executable SHA256:
`4f682e1a9ac0a10b581ce30681a99a9c5e0c9354a8e8dbddc562b5d73be5f7af`.
Receipt native_window_acceptance=false, platform=macOS portable policy only.

Рецензент самостоятельно пересчитал current Windows 220 inputs против
source.json: 220/220 совпадают, ошибок 0. Manifest SHA256
`487cba19270355e9074285e882f9d32cd281b598b656b3bddf031272342d2131`.
Финальная receipt temporary_build_removed=true; указанный ею каталог на Mac
при чтении отсутствует. Прежнее сообщение об удалении до исправления guard
не используется как доказательство. Удаление рецензент не выполнял.

Portable PASS не опровергает M1 и не является Win32/WinUI foreground/menu/
Explorer restart/installed MSIX acceptance. Отсутствие такой acceptance не
добавлено в findings как дефект. Рецензент не запускал сборки, тесты, VM, UI,
запись/микрофон и не взаимодействовал с Windows Security Warning/trust.
T108/T110/T111 не отмечены выполненными; нормативные файлы, checklists и GH
не менялись. Единственная запись этого прохода — данный новый отчёт.

## SHA256 прочитанных исходников и сохранённых evidence

- `apps/windows/RecApp/AppMain.cpp`: `a7927bb8e84b05f0c747fdca7756edbd8b0509ce8f49a0083187ff9680f0ff38`
- `apps/windows/RecApp/Shell/ShellClosePolicy.h`: `2cccd3b954ea140fc60bc320457bca2f0d6905955071d69dcce06750169a5ac4`
- `apps/windows/RecApp/Shell/WindowsTray.h`: `88c4ebc7abb234feb8a548d32d3aac117dcb4cd35bdd1eca8529ad809b93b636`
- `apps/windows/RecApp/Shell/WindowsTray.cpp`: `928c9c77a37a67dd992f0d9cf9a5406281f04611461162b389ef50c90d0a2bd2`
- `apps/windows/RecApp/Shell/RecordingIndicator.h`: `c1f309c705842c20aaf306112808b399d10be025c26ab6bb2ccef442ac5fe052`
- `apps/windows/RecApp/Shell/RecordingIndicator.cpp`: `1ffd69adac8a62fb33c02ea9024db50a8efcb844c4e042ac71e4b8669b542ccb`
- `apps/windows/RecApp/Shell/RecordingNoticePresenter.cpp`: `40cb56dcf74913089609c4724f291b860289a18390547720ae695e4fc25985a7`
- `apps/windows/RecApp/Recording/NativeCapture.h`: `95b0c03cc98cfa2e4dd138de5f4b96a99bdaa23654e87ef5c19e92c849d70e37`
- `apps/windows/Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp`: `91c17499fa74b345937ca67c32c08efc0d92c838e7c4351dac1c882d1569b6b4`
- `apps/windows/Tests/GrafWindowsPackageTests/RecordingNoticePresenterTests.h`: `7ed56b2fbb75611812fdb3d04b9eed8efd33adfd68c1b17876da65afc3bec3de`
- `apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp`: `54ffe2c826366d7b4775fc2bcec92fc517d271064c0f5595d2edd431746c12b9`
- `shell-review-build.json`: `bc289a1addef9e79c699d4177bcc6715c762bd9e97eae6efac59b8e019a8aace`
- `shell-review-build.log`: `ae5ad63ee75938fd3af6dddb450fb6f1b229ca04723f849cd12618271c660fe0`


## Дополнение 2026-10-27: исправление startup M1, узкий source re-review

**Текущий итог C0/H0/M0. Исторический M1 CLOSED на уровне исходников.**
Первоначальное описание контрпримера и ограничения evidence выше сохраняются.

Проверены только текущая дельта AppMain.cpp, семь добавленных строк
RecordingIndicatorTests.cpp и неизменённые вызываемые exit-drain участки.
Точное обратное применение timer move/guard в памяти восстанавливает прежний
AppMain SHA256 a7927bb8e84b05f0c747fdca7756edbd8b0509ce8f49a0083187ff9680f0ff38;
удаление только семи новых строк теста восстанавливает прежний tests SHA256
91c17499fa74b345937ca67c32c08efc0d92c838e7c4351dac1c882d1569b6b4.
Другой дельты в этих двух файлах относительно предыдущего review нет.

Existing timer создаётся и запускается до !shellReady return. Tick захватывает
shellReady по значению; normal partial-shell refresh запрещён до explicit Quit.
Для shellReady=false/exitRequested=false Tick ничего не делает; после Quit
вызывает существующий refreshNativeState, который до обычных shell controls
входит в exit branch и продолжает health/shutdown/uploads/deletion completion.
Для shellReady=true поведение обычного refresh/exit сохраняется. При capture_
отсутствующем requestExit может закрыть окно сразу; новый Tick не разыменовывает
несуществующий capture. Единый beginExit/exitWorkDrained не заменён вторым
finalization путём; blocking wait/новый worker не добавлены.

Регрессия проверяет stateTimer_.Start до раннего return и guard
shellReady || exitRequested_ внутри Tick перед refreshNativeState.
Рецензент независимо проверил именно source-order predicate на восстановленном
старом тексте (false) и текущем (true). Это не исполнение C++ test executable;
сообщённый главным полноценный RED-on-old test run отдельно не повторялся.
Held synthetic worker/actual first Quit UI acceptance не заявлены и не закрыты.
Ранее прочитанный portable PASS относится к старому source до этой правки и
не переносится на текущие байты как новый build/test PASS.

### Existing T108 requirements/checklist gate

Прочитаны существующая T108 и применимые FR-002/004/015, а также относящиеся
к текущему срезу ux CHK005/006/021/022/024 в reviewer requirements mapping
checklists/review-2026-10-01-ui-parity.md. Они требуют независимого native Stop,
close/quit/finalization и сохранения custody/состояния. Существующая задача
T108 прямо владеет разделением close/explicit Quit и единым bounded drain.
Исправление M1 остаётся в этой области: новых требований, форматов, storage
политики, сервера, task или API не требует. Независимое scoped source review
этим дополнением выполнено; полномасштабный analyze/issue audit не повторялся.
T108 остаётся [ ]; checklist markers и нормативные spec/plan/tasks не менялись.
Source closure M1 не означает installed MSIX/native held-worker acceptance.

### Отделение от ожидающего HTTPS runtime

Сохранённый source10 AppMain derivative по-прежнему имеет SHA256
827ceb5bd0ef3b2d17d4c1c7d5ce6f305d1723ae9de8bf6434d8ed19531f19d9.
Независимо побайтово сопоставлены все 11 production sections текущего AppMain
с сохранённым source10 и appmain-test-bindings.json: 11/11 совпадают.
Текущая M1 дельта находится внутри заменяемого OnLaunched; прежний HTTPS PE
не получает доказательства нового shell startup поведения. Рецензент не
менял стенд/manifest, не строил ничего в guest directory, не запускал VM/UI,
не взаимодействовал с ожидающим Windows Security Warning.

### Текущие source hashes

- AppMain.cpp:
  a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0
- RecordingIndicatorTests.cpp:
  d37c09c7c416924bc2bbf7ed3a9b362beadc218cbcb3d0a8c8ae4acf69ed73a4

Единственное изменение рецензента — append к этому reviewer-owned отчёту.


## Дополнение 2026-10-27: финальные portable и production SDK compile-only receipts M1

**Source-вердикт C0/H0/M0 сохраняется; M1 CLOSED по исходникам.**
Узко прочитаны только перечисленные главным финальные stage-файлы SDK compile
и portable regression. Широкий аудит, gates/issue inventory не повторялись.

### Проверка связи байтов

Независимо пересчитаны все 220 файлов startup-quit-production против
startup-quit-production-source.json и все соответствующие 220 current files:
обе проверки 220/220, missing/mismatch 0. Snapshot AppMain побайтово равен
текущему production original, SHA256
`a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0`.
Это не settings derivative/test OnLaunched.

Compile-Startup.cmd вызывает VsDevCmd x64 и cl.exe с сохранённым response file.
В rsp есть /c, нет /FI и /link; source — отдельная копия production AppMain,
/Fo и /Fd направлены в отдельный exclusive временный каталог. Используются
существующие SDK/generated include paths, без изменения ожидающего HTTPS PE.
Compile-Startup.ps1 проверяет manifest до/после компиляции, код возврата,
сохраняет object hash перед удалением временного output. Рецензент скрипты
не запускал; сведения об их исполнении получены из сохранённой квитанции.

### Production SDK compile-only

startup-quit-native-compile.json: terminal=true, compile_only=true,
compile_exit=0, input_files=220, launched=false, installed=false,
temporary_output_removed=true. Нет failure.
Объект SHA256 по квитанции:
`05d0f4c595a2998454236075a5c1a28f79878d878709bc648b3c8fb06d717a98`.
stdout содержит AppMain.cpp; stderr содержит только command-line warning
D9025 о замене /W1 на /W4. Он не скрыт и не объявлен compile error.

Принято как согласованное сохранённое свидетельство компиляции текущего
production AppMain с SDK, без тестового forced include, linking/запуска/
установки. Object/PDB удалены после GetHash; повторно хешировать сам guest
object рецензент не может. Доказательство object hash ограничено сохранённой
квитанцией и прочитанным скриптом, не независимым чтением удалённого binary.
Это не clean SDK rebuild всего проекта и не новый исполняемый продукт.

### Portable regression текущего исправления

shell-quit-fix-build.json: terminal=true, configure_exit=0, build_exit=0,
test_exit=0, input_files=220, inputs_unchanged=true,
temporary_build_removed=true, native_startup_error_quit_accepted=false.
Сохранённый log подтверждает RecordingIndicatorTests 1/1 PASS, 0.58 s.
Mach-O executable SHA256 по квитанции:
`6e40b183cfee2c1f14bd0390d8c901a86b55b30f872a6c2733e7961350e82974`.
Указанный temporary build directory на Mac при чтении отсутствует; его
удаление рецензент не выполнял. Сам Mach-O после удаления не перехеширован.

Принято как сохранённое portable policy/source-wiring regression evidence
текущих исправленных исходников. Native held-worker/actual first Quit WinUI
acceptance не заявлена. T108 и прочие задачи/checklist markers не закрывались.
Рецензент не строил/не запускал код, не изменял normative spec/plan/tasks,
код, GH, guest directory или ожидающий HTTPS runtime/Windows Security Warning.
Единственная запись — append к этому reviewer-owned отчёту.

### SHA256 финальных прочитанных свидетельств

- `startup-quit-native-compile.json`: `aff7a7c3e06f83e8c424399d2425e696fbe17af6855b64cdd5eb8126cf5879e9`
- `startup-quit-native-compile.log`: `be41d158f5d5ad57e58ac5ff59279702349c4c9a9fde33d12bea309cb99c761e`
- `startup-quit-native-compile.err`: `7ff61890b3ae3e960e5ec37dfc0f07317fd10da5ce8d50557a8f0b6d44156941`
- `startup-quit-production.rsp`: `fb071315895f09429ad089fc0de0e1c8725d604c619251a5f15ba1f29e1775fd`
- `Compile-Startup.ps1`: `767e1d81c2a1cb7b8fefebd4a07c9acb97a30316a8572ae40b6f545fb02843f5`
- `Compile-Startup.cmd`: `9b9225b4523d93675c037843d0a85382d15d2b867936c1894c763e20cceac687`
- `startup-quit-production-source.json`: `ff9a8e158a8a417a65a5c9292b8be05d707b7145a073e4a565740edd761a72ce`
- `shell-quit-fix-build.json`: `58225a5c8b71cab8cae3cf886c8de72787d23dc55832d2ae01b495012a5c7e1a`
- `shell-quit-fix-build.log`: `a1ee99142a2e6f99fdfb52cc2b20cfe6d4086415eae6e6c873aab897dd852b67`
