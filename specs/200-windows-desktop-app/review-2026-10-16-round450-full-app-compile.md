# Round450 — independent bounded compile qualification

2026-10-16. **GO для compile/link основного GrafWindowsApp.vcxproj Release/x64.
CRITICAL0/HIGH0/P1 findings0.** Это не runtime/installed/MSIX/release GO и не
закрытие T116/#7444. Lane: read-only independent review of high-risk-product
diagnostic evidence. Reviewed current scripts, сохранённые terminal receipts,
UTF-16LE logs и только новые Round450 main documentation sections.

## Identity и immutable evidence

Authoritative repo /Users/yshishenya/Documents/crisp-worktrees/200-windows-followup,
branch codex/200-windows-followup, HEAD
b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1. Source — dirty tree, не один HEAD:
current216/216 совпали с manifest449green6
99b6941e0ec32c556de10b71f3e0437eaeaacfa64b5778a761a90f2992e91443.
Source-origin ссылка на сохранённый full patch проверена: файл существует,
SHA9a8c6db851c3bcbbad93e90d3b490f3a02d12a8cb18478e3e95cbcc843748d3e совпал.
Повторная reconstruction здесь не выполнялась: это source linkage/hash check.

Evidence root /Users/yshishenya/Documents/graf-f200-build450.rXty3N.
SHA256SUMS SHA72f95563906d7b7ddc7be0b6c9b7bafcdc347cba0d1b027426e12464155a1bd1
совпал; все12 перечисленных files прошли независимый shasum check.

## Compile / output qualification

- Original result.json terminaltrue, AECverify0/Restore0/Build0, pre/post216,
  saved owned_processes0, pipeline elapsed238917ms. Failure EXE_ABSENT сохранён:
  исходный harness искал output под RecApp вместо Directory.Build.props out.
  Это не первоначальный успешный harness run.
- Separate app-qualification.json terminaltrue/no failure/source216/saved
  owned_processes0. Его ссылка по SHA на original result.json совпала:
  eabb7fca910e11fbfd0de445b938f9c5b088d88278b3856f0080a2350daa778b.
  Scripts fail closed на unexpected prior failure, missing/stale output,
  wrong PE header/machine и source drift. Нормальный Git index не использован.
- UTF-16LE build log прочитан после декодирования: MSBuild17.14.51,
  AppMain/WebView2/Storage/LocalPackage/V5 actual compilation, linker output
  apps/windows/out/x64/Release/GrafWindowsApp.exe; no usable IPDB/IOBJ и полная
  code generation28630 functions. Это не no-op; не hermetic clean rebuild
  всего dependency chain и не Build всей solution.
- Saved actual guest output: SHA
  9b90dc08d0776df015e421a41cc1397135f8896ee047129324d8595805bdcd73,
  bytes3264512, PE machine0x8664, LastWrite2026-10-16T10:06:35.7411061Z.
  Log path, fresh timestamp, MZ/PE/x64 и file hash проверял guest script;
  reviewer не читал live guest PE и не выполнял live CIM.
- Штатный -VerifyBuildArtifacts проверяет config/architecture/pinned source,
  source/header digest и полный artifact inventory, вызывается отдельно и
  внутри vcxproj BeforeTargets PrepareForBuild. Bypass не найден.
  Source846fe90a289f58b7c9303a635142aa2c7caa93e5, Release/x64 inventory27 artifacts;
  saved provenance SHAebe9b371f9ef9ab8e78f45c607ab7a661235ad9396d4001e2079395b08aae0fe.
- Имеются D9025 (/W1→/W4) и upstream C4100 warnings. Нельзя называть результат
  warning-free или отдельным Werror acceptance. 238917ms — весь timed pipeline,
  включая AEC verify/restore, а не только compiler wall time.

## Main documentation review

Прочитаны validation-2026-10-02.md:25892–25955 и
changes/unreleased/F200.yaml:3217–3225. Они корректно разделяют application
compile vs CMake tests/whole solution, original harness failure vs separate
output qualification, source manifest vs base HEAD, app HTTP vs NuGet feed.
Scope limitations и quarantine UI/changed-row continuation сохранены;
неподтверждённого installed/release/T116 completion claim не найдено.

Governance/doctor/YAML/diffcheck PASS, normal-index/server-hash preservation —
сообщение main; отдельные receipts этих запусков в12files bundle не представлены
и reviewer не выдаёт их за собственный повторный запуск. Это не блокирует
bounded compile verdict. Настоящий report — единственная запись этой финальной
проверки; main validation/fragment/source/tasks/checklists не редактировались.
VM, tests, build, install, launch, migration, GitHub/commit/cleanup не выполнялись.

Новых source/dependency copies в bundle нет, source-copy cleanup здесь не нужен.
Quarantine playback admission требует будущего scoped plan/source/runtime review;
этот GO не переносится на следующий срез или общую T116 acceptance.
