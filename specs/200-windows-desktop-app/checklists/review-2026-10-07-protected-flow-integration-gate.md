# Round276 — REQUIREMENTS: действующий защищённый поток T116

**SCOPED REQUIREMENTS / ANALYZE GO — C0/H0/M0/L0 для проекта подключения.**
Это разрешение начать RED/реализацию согласованного вертикального среза,
НЕ SOURCE/runtime/adoption/installed/release GO и НЕ закрытие T116.
Lane high-risk-product; существующий T116/#7444, без новой задачи или схемы.
Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Dirty сохранён. Reviewer не исполнял VM/tests/GitHub/hooks и не менял исходники.

## Точная принятая база

Лично полностью прочитан НОВЫЙ раздел plan.md:1802–1891
«T116: подключение действующего защищённого потока — 2026-10-07»;
plan SHA `5d01df02ef0ff32f2a3ccaf7158133726a62a10a7643098610c50b1c69c7fe00`.
Вердикт относится к нему вместе с нормативными local custody §2/§4–§8.1,
packed §2/§5/§6/§6.0–6.1, data-model §12–13, quickstart §12/§14–15,
FR-012/013/014/022, SC-003/005/006 и tasks.md:568–570,602.
Конституция/guidance и ранее полностью прочитанные активные артефакты сверены;
все десять текущих нормативных чеклистов прочитаны. Применены
`speckit-analyze` и `speckit-checklist`: requirements quality, не отметка реализации.
Основные shared consumers и актуальный closed NativeCapture прослежены read-only.

## Принятые механизмы; прежние предварительные пробелы сняты

1. **Birth/допуск.** Один worker удерживает native root/ancestor/IDs/ACL ownership.
   Streamed inventory проверяется до birth и повторно после BOTH-slot ACK.
   Случайные exact16B IDs не восстанавливаются поверх partial/unknown/protected
   следов. Virgin empty ledger и bootstrap подтверждаются до admission;
   failed birth сохраняется закрытым, не автоматически достраивается.
   Legacy/prepared/incomplete не становятся пустой или обычной очередью.
2. **Непрерывный writer.** Factory переиспользует Files State/openImpl;
   readonly proof не разблокируется. Worker держит writable lease и независимый
   context/base generation; один существующий commit-body, без второго publisher.
   Release/reopen path gap отсутствует по проекту. Если он фактически появится,
   полный повторный verify под эксклюзивным владением обязателен до mutation.
3. **Typed очередь.** Ограниченная value copy → последовательный full commit →
   value-only ticket → storage generation adoption → ACK обратно worker.
   Lease/candidate/completion остаются worker-owned до adoption; максимум32
   commands/results с shared charge, без future с native lease на UI.
   До publish отмена не меняет projection; после publish доводится readback.
   Ambiguous закрывает effects/следующий commit; stale account не отменяет
   physical committed adoption и не получает UI/network capability.
   Lost callback/shutdown/update сохраняют ownership и polling reconciliation.
4. **Настоящий поток.** NativeCapture принимает storage completions ДО closed
   guard. Capturing state ACK предшествует audio; protected canonical → WAV/AAC
   через logical IStream/MFByteStream → manifest → sealed state → queue ACK/adoption.
   Existing EOS/timeline/finalizer сохраняется; saved не возникает при pending.
   Pipeline proof приватен и подлинен; обычный Record не обходит closed admission.
5. **Все потребители.** Общий storageWritable открывается только после подключения
   HTTP/range/hash/reconcile, playback и delete/purge к тому же ownership.
   Никаких plaintext URL/temp/ShellExecute/content file fallback или durable bool.
   Правила account/epoch, sealed refs, quiescence/absence/ACK и stage §8 обязательны.
   Неподдержанный restart/tombstone/conflicting-copy случай остаётся закрытым;
   direct-only MigrationPair не объявляется общим recovery/GC разрешением.

Предложение Fermat и новый раздел плана закрывают проектные вопросы, отмеченные
до его добавления. Ожидаемое отсутствие кода/исполненных тестов не является H.
Новых продуктовых решений, порогов, framework, reader или dispatcher не требуется.

## Обязательная приёмка реализации — всё ниже ещё PENDING

- Actual NativeCapture/controller, genuine worker birth/current authority;
  CaptureSessionTestPeer заменяет только device audio, не READY/IDs/generation.
  Generated ≥30s frames → EOS → pending → sealed → queue commit/adoption →
  холодный restart → logical playback/seek → partial HTTP/reconcile → deletion ACK.
- Birth/commit cuts, inventory races, BOTH missing/singleton/bad peer, чужие IDs,
  context/stage/base-generation conflict, orphan/key/native/budget refusal:
  без empty queue, overwrite, normal/saved и effects до доказанного ACK.
- Нормальный, fault/degraded trusted complete prefix и short-discard пути;
  exact v5 format/hash/duration ±100ms; short marker и removed ACK порядок.
  Privacy OPEN/CLOSE/full manifest сохраняют нормы T120, без отдельного plaintext
  журнала; этот gate не объявляет T120 исправленным или принятым.
- Pending/not_committed/ambiguous, stale epoch, lost callback, shutdown/update:
  generation принимается ровно по storage truth, следующий commit сериализован;
  late callbacks не запускают network/новую запись и не выдают false deletion ACK.
- Disk snapshots на checkpoint/finalize/metadata/temp/quarantine: нет открытых
  app-written content/key копий. HTTP exact logical ranges/part SHA/server truth;
  MF Shutdown/stream/Clone lifetime и delete actual quiescence/absence доказаны.
- Existing shared budgets: owned64MiB, cache2MiB, dirty≤4blocks, pins≤32, native
  jobs≤4; bounded callback handoff, никакого disk/crypto/UI wait в WASAPI callback.
  Actual Release/Debug faults/allocations/cancellation/retry/last-release и SDK
  caller builds обязательны. Native MF/DPAPI memory измеряется отдельно.
  Source/API evidence не заменяет SC-003/100cycles/installed/hardware T118.

## Сохранность и предел решения

До записи inventory160 Markdown: **10 normative, 154 checked / 0 open**;
150 остальных отчётов/исторических файлов отдельно, не новые обязательства.
159 прежних файлов совпали с prior inventory; accepted correction275 также
совпала с SHA `c483a9a3ce7638bf141bb42f25c874ba39d67b6a9dbbd88029b7f56e67f0182b`.
Tasks **120/93/27**, SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
T116/#7444 принадлежит существующему task; fresh OPEN сообщён main,
reviewer GitHub не опрашивал. Шесть before/after implement/analyze/checklist
hooks имеют по1 registered disabled entry, enabled0; dispatch0.
Единственная запись reviewer — этот новый report с0checkbox; старые markers
и reports неизменны. Main может начать RED и реализацию принятого проекта.
SOURCE/нативная сквозная приёмка впереди; весь T116/T117/T118/T120, H250,
AAC legacy RED, physical/installed/macOS parity и release остаются OPEN.
