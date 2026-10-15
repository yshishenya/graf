# Round275 — исправление раннего отказа Record: SOURCE

**SCOPED CORRECTION SOURCE GO — C0/H0/M0/L0. SRC275-PRE-1 закрыт на corrected source.**
Принят default-closed actual consumer Round275, НЕ protected authority/usable release.
High-risk-product, F200/T116 (#7444); reviewer не исполнял VM/tests/EXE/GitHub/hooks.
Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Dirty изменения сохранены; никакие code/spec/plan/tasks/markers не исправлялись reviewer.

## Коррекция и независимая проверка

- Исходный NO_GO report сохранён byte-identical, SHA
  `97376602d7e333538c73d83af08e1ecaee889461adb843ef5a9c76810c712bbc`.
  Его прежний snapshot и результаты не объявляются corrected evidence.
- Лично прочитан incremental diff относительно accepted275: ровно 4 production
  строки AppMain и 5 строк существующего RecordingIndicatorTests, без иных delta206.
- AppMain.cpp:2662–2665 теперь проверяет `!capture_->localQueueComplete()`,
  устанавливает `localActionNotice_=capture_->custodySummary()` и возвращается
  ДО `refreshReadiness()`. В закрытой ветке нет `refreshNativeState()`.
  Null/shutdown/update/current guards перед ней сохранены; settings/metadata не запрещены.
- Это устраняет конкретное нарушение пункта 4 REQUIREMENTS275. Ранний return
  закрывает refresh и дальнейший Record из общего manual/tray/calendar caller.
  NativeCapture::record и automatic storage prerequisites не изменены.
- RecordingIndicatorTests.cpp:571–575 проверяет guard перед refresh, правдивый
  custody-текст, return и отсутствие refreshNativeState в выделенной ветке.
  Предыдущие assertions/обязательная индикация/порядок refresh→canStart→record сохранены.
  Новая регрессия — source-order proof, не runtime WinUI Record invocation.
- Лично прочитан portable RED до исправления: compiled0, CTest8, expectBefore386,
  «if (!capture_->localQueueComplete()) before capture_->refreshReadiness()», 0.48s.
  `record-caller275-red.log` SHA
  `309916cdb822f63bb2444dc7c82f50e55bac54d7397b43246587a4fbae65782b`.
- `code-reviewer` и `ponytail-review` прочитаны полностью и применены;
  нет нового helper/framework/state/test flag. **net: -0 lines possible**.
  Первичный аудит sole NativeCapture/closed effects/late callback guards сохраняется;
  текущая карта подтверждает, что header и StartupTests byte-identical accepted275.

## Exact corrected source

Stand `/Users/yshishenya/Documents/graf-f200-native-startup-corrected275.fD1syk`.
`source-corrected275.json`: 206 inputs, SHA
`ffb6a856baf18c7c201b2ccad1b130050523dcafd85f167c775e93a816dc1d98`.
Лично пересчитаны все 206 canonical и frozen файлов: **0 mismatches**;
полные карты corrected Release/Debug/App receipts равны этой карте.
AppMain SHA `d4306d9c946fceb861024e7e38fc058a726f8dc5eb5aec67ef901d602d362fc6`.
RecordingIndicatorTests SHA `6a56dcbf3f9732a0bda7215c84a59514127c2c83a83ab90a277c0267cadbe438`.
Внешние BOM receipts разобраны только в памяти, не нормализованы/перезаписаны.

## Native и portable evidence

Обе terminal receipts и полные raw logs прочитаны лично. Actual execution — main.
8 targets: QueueV2, DeletionLedger, CaptureFault, AppUpdate, NativeCaptureWebFailure,
Recovery, RecordingIndicator, NativeCaptureStartup. Это selected8, НЕ full51.

- Release: build0/test0, **8/8 PASS**, команды/EXE пути Release;
  main сообщил общий CTest26.74s, raw Indicator2.14s/Startup0.09s.
  `native275b-release.json` SHA
  `cb4bdf8cfc36434f293d2803f00d35a190022d4e9e2d8798ac08db2ae64389fb`;
  raw `c4264585239fcd2bca330779fcec3ec1e9aa50caf91b1e793d0fd4ea507ac7bb`.
- Debug: build0/test0, **8/8 PASS**, команды/EXE пути Debug;
  main сообщил общий CTest29.36s, raw Indicator2.25s/Startup0.13s.
  `native275b-debug.json` SHA
  `6de436a6fd40a5797beecd4c2023c3d5497cf4db7ec677a24776fcaa26dcacbe`;
  raw `225e719ebd6fe46114da85ed68becf22e5f2f9932a9a3bf684ba7a34a157843a`.
- `readback-accepted275.json` SHA
  `f7a39f8f71b43366764c62dc9b3bf89ece054c8722e44c81b9a7f62e65655e9b`:
  source_count206/source_match/receipt_match true; все16 executable entries
  лично сопоставлены с corrected receipts, каждый machine0x8664.
  Readback script прочитан: actual native/source/export/EXE checks, CreateNew export.
- Portable applicable **46/46 PASS**, main сообщил11.85s; лично проверен raw
  `portable275-corrected.log`, 46 Test Passed/0 failed, SHA
  `d659f7f311ec2b3f79564b06ee6c68e2a2978f92ec3fbfc40c735761d150458e`.
  Portable не запускает Win32 Startup target; native popup tests не доказывают App Record.

## SDK App и экспортированный readback

Лично parsed/hash `app-corrected275.json`: terminal/build0, Release/x64,
mode build-only-no-install, source206; receipt SHA
`0263cb33574b27e480f816e90178d9081ca2c77609e65464b88ffbffae51f74f`.
EXE `7a80c629536a14b32c8592eaa396b1df6bf52f76c726a42e1e65f6be430a4697`, PE0x8664.
AEC provenance `14bff774615f3dfa12188d53dea8fcad1a19fbcf7800f66faa46ce76c549556e`.
Лично parsed/hash `app-readback-corrected275.json`, SHA
`5df7a08ff3e3ed4f8cfa5dbaba598b3b67176a03115208ba725343a4c2b4042a`:
terminaltrue, source_count206/source_match/receipt_match true, owned_jobs0;
EXE/PE совпадают с App receipt, receipt_sha256 совпадает с её actual bytes.
App build/readback scripts прочитаны полностью; native/export byte audit выполнил main.
Нет заявления reviewer VM исполнения; D9025/C4100 предупреждения main не скрыты.
Это не vulnerability audit, WinUI runtime, установка, MSIX, hardware или рабочий профиль.

## Сохранность и границы GO

До записи: **159 прежних Markdown byte-identical** относительно reviewer inventory,
включая original NO_GO; 10 normative **154 checked / 0 open**, historical149 отдельно.
REQUIREMENTS275 SHA `5fbb2dec2ff9cf7d63829e9ab75a0d1ddc416c8b7d2fe7ad8e31852f16722472` сохранён.
Tasks120/93/27, SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Этот единственный новый report имеет0checkbox; старые markers/reports/code не меняются.
**Default-closed SOURCE275 принят с исправлением SRC275-PRE-1.**
Storage остаётся закрытым для ВСЕХ roots: GO не разрешает поставить storageWritable=true.
Настоящие authority/root birth/migration/writer/queue commit/adoption/HTTP/playback/delete
требуют следующего согласованного vertical integration gate до реализации.
T116/T117/T118/T119/T120, H250, AAC legacy RED, full native51, installed/hardware/macOS parity
и release остаются OPEN. REQUIREMENTS276 этим отчётом не утверждён.
