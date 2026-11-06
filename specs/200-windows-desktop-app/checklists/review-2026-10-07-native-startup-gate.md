# Round275 — NativeCapture: закрытый startup, REQUIREMENTS gate

**SCOPED REQUIREMENTS GO — C0/H0/M0/L0.** High-risk-product, F200/T116 (#7444).
Это допуск требований к указанной реализации, не SOURCE/validation/application GO.
Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`; dirty изменения сохраняются.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

## Принятый объём

1. Механически перенести единственный настоящий NativeCapture в внутренний
   NativeCapture.h с необходимыми inline helpers; AppMain и тест используют
   тот же класс. SharedMutationScope/newSessionId/deviceDisplayName переиспользуются.
   Реальный selectAec остаётся в AppMain; constructor явно принимает root+AecSelection.
2. AppMain разрешает root path без mkdir. Constructor не делает legacy load,
   sweep/recover, registry preference read или endpoint refresh.
   Idle controller/timeline/writer допустимы только без дисковых effects.
3. Единственная custody boundary — существующий readiness_.storageWritable=false.
   Никакого true от пути/bootstrap, root classification, async probe, setReady,
   test flag или публичного path/HANDLE bridge. Все корни остаются закрытыми.
4. Record manual/auto/tray/calendar отказывает ДО pipeline replacement,
   readiness refresh, StartGuardFactory и запуска capture. Stop/shutdown/cancel
   и безопасная idle-индикация сохраняются; cleanup не объявляется completion.
5. Auth/cabinet/general settings не блокируются. pollUploads может сначала
   вызвать существующий auth-only pollAccount, затем storage guard обязательно
   ДО scheduler.drain/startAsync. recover/retry не допускают custody dispatch.
6. Preference initialization ленивое в явном refreshReadiness; metadata/device
   settings и selectMicrophone могут оставаться доступны по прежним ограничениям.
   Fixtures их не вызывают. AAC/MF metadata probe не открывает storage authority.
7. Ledger наружу только const projection. Existing deletion/purge/owner/retry
   mutations идут через guarded forwarding methods; queue codec не меняется.
   acceptedBeforeUpdate не обходит storage; новая owner/framework модель не нужна.
8. AppMain закрывает scan/inspect/playback/ShellExecute, deletion dispatch и purge.
   Confirmation/dispatcher callbacks повторяют guard ДО mutation/reply/ACK.
   При отказе — nonsaved/unverified, не saved/deleted; не отправлять deleted ACK
   из позднего prepared списка. Counters/pending callbacks безопасно завершаются.
9. Finalizer enqueue/discard и прочие поздние публикации не обходят guard.
   localQueueComplete=storageWritable&&!quarantined. Default empty projection
   не доказывает пустой диск/upload/очистку; recoveryRequired/actions правдивы.
10. Readiness/custody copy приоритетно сообщает:
    «Защищённое локальное хранилище недоступно. Записи не изменены.»
    Это не результат чтения корня и не обещание восстановления входом.

## Основания ограниченного analyze

- FR-012/013/014/022 → существующая T116, tasks568–570; plan1510–1527.
- Base custody §7:292–320: callback/shutdown/delete truth; §8:328–360:
  missing/reserved/invalid не дают effects/empty queue; §8.1:447–464:
  closing bootstrap не даёт regular authority. Packed §6.1 не ослабляется.
- Constitution II/IV: manual при выполненных prerequisites, доступный Stop,
  truthful deletion. Storage prerequisite ещё не выполнен: blocked, не ready.
- Исходные causal callers AppMain: root453–465; constructor594–613;
  Record615–643; drain678–695; mutable ledger849; deletion852–881;
  finalizer985–1067; scan1941–1974; playback2170–2197;
  deletion2220+/2449+; purge2310+/2360+.
- Для запрета всех effects НЕ требуется сначала queue birth/protected writer.
  Они обязательны перед будущим открытием, а не блокеры этого закрытого среза.

## Обязательные будущие проверки

- Настоящий RED старого constructor/consumer на disposable generated root;
  compile failure не RED. Механическое выделение класса не дублирует реализацию.
- NativeCaptureStartupTests в существующем CMake Win32 lane: тот же header/class,
  SDK C++/WinRT Package/Analytics+windowsapp, без WinUI test project/framework.
  Nonnull существующий IAec3Processor dummy; никакого READY/device test flag.
- Unknown/missing/arbitrary/malformed ledger/prepared-reserved roots:
  ctor→Record/auto→poll/recover/retry/adopt/delete/purge→Stop/shutdown/restart
  не меняют bytes/names и не создают root/ledger/quarantine/media.
- StartGuard не вызван, storage/recordingReady/localQueueComplete false;
  const ledger проверен типом; forwarding не вызывает recycle/persist/ACK.
- Auth token пуст до poll; synthetic auth epoch очищен до poll: без auth network,
  реального профиля/устройств. Explicit settings APIs fixture не вызывает.
- AppMain caller review проверяет entry+late guards/counters/no false replies.
  Class tests не выдаются за runtime WinUI callbacks или injected late drain.
- Exact-source Release/Debug native и затронутые shared regressions, SDK App build;
  portable только applicable. Результаты/хеши/readback проверяются в SOURCE отдельно.

## Инвентарь и сохранность

`speckit-checklist`/`speckit-analyze` использованы; инструкции прочитаны полностью.
Нормы/guidance повторно использованы с fresh SHA; historical giant logs не переаудированы.
157 прежних Markdown byte-identical: 10 нормативных +147 остальных исторических.
Нормативные totals: 22+27+25+24+14+12+12+5+8+5 = **154 checked / 0 open**.
Этот единственный новый отчёт имеет 0 checkbox; markers не меняются.
Tasks:120/93/27; SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Source274 SHA `6029cba40fa91dd900e1f34e6f0c2717fe55cea6c50e44997673182c2ddb9fb7` неизменён.
Before/after implement/analyze/checklist: 6×1 registered, enabled0/dispatch0.
OPEN #7444 и feasibility сообщил main; reviewer не исполнял VM/tests/GitHub/hooks.
Разрешена только запись этого gate; code/spec/plan/tasks/старые отчёты не изменены.
T116/T117/T118/T119/T120/H250/AAC RED, installed/profile/release остаются OPEN.
**Main может реализовать ровно этот default-closed actual consumer/test scope.**
