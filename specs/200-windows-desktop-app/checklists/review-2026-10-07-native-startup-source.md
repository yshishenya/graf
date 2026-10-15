# Round275 — настоящий NativeCapture, закрытый startup: SOURCE

**SCOPED SOURCE NO_GO / REQUEST_CHANGES — C0/H0/M1/L0.**
Validation свидетельства приняты отдельно; они не закрывают SRC275-PRE-1.
High-risk-product, F200/T116 (#7444); это не общий application/release вердикт.
Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch `codex/200-windows-followup`; HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Dirty изменения сохранены; reviewer не исполнял VM/tests/EXE/GitHub/hooks.

## Единственное открытое замечание

**SRC275-PRE-1, M — AppMain.cpp:2659–2665: Record обновляет устройства до отказа storage.**
`recordCapture()` проверяет shutdown/update/current/capture-state, но не
`localQueueComplete()`, затем вызывает `capture_->refreshReadiness()`.
Тот читает preference, проверяет MF/AAC, перечисляет endpoints и может вызвать
`controller_->setEndpoints` (NativeCapture.h:678–701). Проверка recordingReady
идёт позже; её ветка отказа вызывает `refreshNativeState()`, также обновляющий readiness.
Это нарушает пункт 4 принятого REQUIREMENTS gate: manual/auto/tray/calendar Record
должен отказать ДО readiness refresh. Общие settings/metadata APIs остаются разрешены.
Callers: tray AppMain:641, main Record:963, compact Record:1144.
Запуск записи или обход custody mutation не доказан: нижний `NativeCapture::record`
отказывает правильно. Поэтому M, не C/H; исходная цель отказа записи сохранена.
Минимальная коррекция: early storage/localQueueComplete guard в `recordCapture`
до refresh с правдивым custody-текстом; в этой ветке не вызывать refreshNativeState.
Новый owner/framework/probe/state machine не нужен.
Class tests не вызывают AppMain::recordCapture; 7/7 и SDK compile не закрывают замечание.
Перед SOURCE acceptance нужен exact-source повторный review исправленного caller
и проверка порядка guard→refresh; старые frozen receipts нельзя объявлять новыми.

## Проверка исходников и границ

- Лично прочитаны настоящий shared header/class, AppMain callers/callbacks,
  CMake, StartupTests и механическая адаптация RecordingIndicatorTests.
  Сравнение — с accepted274, не с устаревшим HEAD-diff всех раундов.
- Единственная реализация NativeCapture; constructor root+AecSelection внутренний.
  AppMain разрешает путь без mkdir. Idle pipeline constructor не открывает ledger;
  load/sweep/recover/registry/device refresh из constructor убраны.
- storageWritable остаётся false; нет setReady/публичного setter/READY test flag.
  record класса отказывает до pipeline/StartGuard; localQueueComplete не выводит
  пустой диск из пустых vectors. Readiness/custody text сообщает недоступность storage.
- pollAccount остаётся auth-only; storage guard до scheduler.drain/startAsync.
  recover/retry/adopt/owner mutations, удаления и acceptedBeforeUpdate закрыты.
  Ledger наружу const; guarded forwarding сохраняет старую QueueService реализацию.
- AppMain scan/open/playback/delete/purge entry/late callbacks закрыты.
  Guard после recycle перед ACK dispatch присутствует; финальные reply counts
  публикуются лишь при complete&&!shutdown. Отказ не выдаётся за saved/deleted/ACK.
- Audio/finalizer callbacks проверяют storage перед append/диском/queue publication.
  Это source ordering proof закрытого режима, не runtime proof активного закрытия,
  account handoff, injected flight/drain или WinUI callback после reentrancy.
- StartupTests: тот же header/class, assert активен и в Release, const API проверен
  типом; 8 generated root scenarios × 2 restart, update guard, shutdown, без
  изменения snapshot bytes/names. Reserved/prepared traces явно НЕ genuine envelopes.
  Auth synthetic token очищен до poll; явные preference/device APIs не вызываются.
- RecordingIndicatorTests меняет только источник двух выделенных class sections;
  проверки first/last/assert/order сохранены. CMake добавляет Win32 target в имеющийся lane,
  без дублированного класса, WinUI test project, dependency или нового framework.
- `code-reviewer` и `ponytail-review` прочитаны полностью и применены.
  По сложности безопасных сокращений не найдено: **net: -0 lines possible**.
  Это не снимает замечание корректности выше и не означает Ship.

## Exact source и лично проверенные выгрузки

Stand: `/Users/yshishenya/Documents/graf-f200-native-startup-accepted275.WTdKQx`.
`source-accepted275.json`: 206 inputs,
SHA `2b38ea18f0008f2f1c49c48ed88d708fe4835ca442280149235cc55ec5d16746`.
Лично повторно пересчитаны все canonical/frozen inputs: 0 mismatches.
Release, Debug и App receipts содержат ровно эту полную source map.
Внешние UTF8 BOM receipts разобраны только в памяти; bytes не переписывались.

Пять reviewed paths SHA256:

- CMakeLists.txt: `63e68fcbeb421898f12e319266e6833438265d8996200aba0368accd21f59520`.
- RecApp/AppMain.cpp: `5021851a8c96b0fcb589aafc10ca587701777114dd9dcf81bd20c6f53ccd305e`.
- RecApp/Recording/NativeCapture.h: `1108770c3a8ad2a53a75bbf82973c926e6d10cb2d7cb4855d666e0641f2e9a16`.
- NativeCaptureStartupTests.cpp: `c13ac18d23880dbe1b8b976aca96adde3840fa83e98f27d94359cd71ae8dda5a`.
- RecordingIndicatorTests.cpp: `436f354f62a00074e9324650d5df52a93fea3b6c7e150f1f063e2a5aff6e9341`.

**Native focused validation PASS, не full suite:**

- `native275-release.json`: terminal/build0/test0; raw лично прочитан, **7/7**,
  команды Release; StartupTests 0.12s.
  Receipt `10792c628f68ab4249f0ddd998a9d966e3739827b4699777dc854ed05e07f2e9`;
  raw `476c40ce3b7e04afa2495f555be6193eb5e51a79a66acce5b237eb959411a692`.
- `native275-debug.json`: terminal/build0/test0; raw лично прочитан, **7/7**,
  команды Debug; StartupTests 0.22s.
  Receipt `543f07143e0c070353d76811cfe73c6642f0afb60a633543e07b9788dc9e8dba`;
  raw `24b1032ef0a0dbf954e3748b165ad0142c6aaf52a099188b6db92abf17025d5c`.
- `readback-accepted275.json`: лично parsed/hash; source_match/receipt_match true,
  14 executable entries совпадают с обеими receipts, каждый PE machine 0x8664.
  SHA `5c4f1a0dda0ea1965f57046290439adf0970a7f367cf4811f418080ef9a81636`.
  Actual native readback исполнил main, не reviewer.
- Portable applicable: raw before-wiring 45/46, ошибка moved source section375;
  после механической адаптации 46/46, main сообщил 12.10s.
  After raw SHA `0cd0799cf2580a7b761a3ed9468b8e7874211792d94aade5661f99e82e69c491`.
  Portable не исполняет Win32 NativeCaptureStartup target.
- Genuine runtime RED старого constructor: build0/test8, `!storageWritable`46,
  2.42s; сохранён в отдельном stand `graf-f200-native-startup275.o3vMj5`.
  Patch/shell quoting failures до dispatch не объявляются RED/PASS.

**SDK App build-only PASS:** лично parsed/hash `app-accepted275.json`,
terminal/build0, Release/x64, source206; receipt
`57848aea28f015d3195de465a436b4ad4cd37be1343ced516a96a98989235e68`.
EXE `9ed5c814b04985c9750eeed1a68476affcd365a4c80dfdac0b0094b86a0077d8`, PE0x8664;
AEC provenance `14bff774615f3dfa12188d53dea8fcad1a19fbcf7800f66faa46ce76c549556e`.
Readback-app script лично прочитан; actual main terminal0 сообщил source206/EXE/PE
MATCH и owned-build-test-count0. Отдельной stdout-export receipt этой проверки нет:
сообщение main не выдаётся за собственное reviewer VM исполнение.
D9025/C4100 warnings остаются; это не vulnerability audit, install/launch/MSIX proof.

## Сохранность и решение

До записи этого единственного 0-checkbox report: **158 прежних Markdown byte-identical**
относительно сохранённого reviewer inventory. 10 normative: **154 checked / 0 open**;
148 остальных historical, не новые нормативные обязательства. Markers не менялись.
Tasks120/93/27, SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
REQUIREMENTS gate SHA `5fbb2dec2ff9cf7d63829e9ab75a0d1ddc416c8b7d2fe7ad8e31852f16722472` сохранён.
Ранее прочитанные guidance/constitution/contracts не заменялись build результатами.
Hooks before/after implement/analyze/checklist: 6×1 registered, enabled0/dispatch0.
Reviewer изменяет только этот новый report; code/spec/plan/tasks/GitHub/VM не изменены.
**Round275 SOURCE не принят из-за SRC275-PRE-1; новое REQUIREMENTS/product решение не требуется.**
T116/T117/T118/T119/T120, protected authority/writer/adoption, H250, AAC legacy RED,
full native suite, hardware/installed/profile/macOS parity/release остаются OPEN.
