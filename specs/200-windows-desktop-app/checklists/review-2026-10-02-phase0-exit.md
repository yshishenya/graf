# T114 Phase0: ограниченный exit audit — 2026-10-02

**Вердикт: NOT READY по одному конкретному literal gap — количественное IO совместного protected MF seek/rewrite пути.** Остальные перечисленные ниже механизмы имеют достаточное ограниченное Phase0 evidence; это не полная продуктовая приёмка и не закрытие T114. Audit не требует реализации T115–T118 до T115.

Основание: [буквальный T114](/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp/specs/200-windows-desktop-app/tasks.md:544), [границы Phase0→design→implementation→acceptance и ограничения reopen](/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp/specs/200-windows-desktop-app/plan.md:842), RQ30-H1/research:961–1046 и 1270–1587. Применён лично прочитанный code-reviewer. Это read-only анализ и Docs-only отчёт: без запусков, сборок, VM, product edits, GitHub или изменения task/checkbox state. Сообщения Main — сообщения основного агента, не доказательство человеческого разрешения. Ограничения прежних narrow approvals не перенесены автоматически в blockers Phase0.

## Матрица буквального объёма

`sufficient` означает достаточное исследование именно указанного механизма на bounded generated-data стенде; не принятие готового протокола, SLA или installed продукта. `partial` означает конкретный недостающий факт. Отдельных полностью `missing` механизмов в этом перечне не найдено. Последовательные сценарии одной исследовательской обвязки принимаются как совокупное evidence; нового требования исполнить всё одним процессом одновременно нет.

| Literal компонент T114 | Конкретное evidence round133–140 | Статус | Минимальное действие ДО T115 |
|---|---|---|---|
| Native user-scope DPAPI + 256KiB immutable blocks + два protected indexes | R134: medium8192/noadmin, полный canonical3840123B и все own envelopes; R136: append/rewrite, старые block/temp bytes неизменны при retry; R140: native DPAPI и проверка context/digest до authority. | sufficient | Не повторять benchmark; сохранить отдельные block/index bounds в выводе research. |
| Совместный seek/rewrite IStream→IMFByteStream | R134: protected file-backed AAC366529B, 4 checkpoints/2 rewrites, decode/EOS, seek10s/1s, отдельный child reopen0; R137 повторяет MF-путь. Это не просто memory-only adapter. | sufficient | Generic Clone/CopyTo/все размеры — contract/implementation, не дополнительный Phase0 stand. |
| AAC finalization | R137: успешные Finalize→reset writer/byte stream→tail Commit, вместе226499us; R139: asynchronous protected finalizer job. | sufficient | В T115 не смешивать время этих действий с полным Stop или отдельным Finalize. |
| Native playback/seek | R135 positive: MediaEngine CANPLAY/progress/pause, 3 seek, два resume, ENDED, Shutdown16ms и post-Shutdown rejection; fault: ERROR0x8003001e + sticky read/got0. | sufficient | Непрерывное прослушивание/installed UI/physical quality здесь не требовать. |
| **Измерить combined IO** | R137 raw256KiB/index cases имеют process IO: largest read268491346/write67793792B. **MF-case не имеет IO window/counters**; R134 rewrites=2 и R139 job time не заменяют измерение transfer/amplification совместного MF-пути. | **partial** | Одно дополнительное измерение уже существующего 30s generated MF encode/finalize/reopen/decode/seek случая; подробность ниже. |
| Память и диск | R137: stream/MF process lifetime peaks и file sizes; после MF commit32280576/resident43868160B, media6files/728676B. R140: max-dimension mixed index, 6files/9438756B, peaks32649216/44769280B. | sufficient для Phase0 | Peaks не layer quota, file sizes не NTFS allocated sectors. Точные budgets/резервирование — T115; app SC-003 — поздняя приёмка. |
| Короткий tail | R134 whole canonical включая123B tail; R137 64MiB−123 whole identity/all258objects, final-tail Commit24035us; R140 short last block262021B и EOF clipping. | sufficient | Не добавлять новый full64GiB media case. |
| Stop/fence | R139 **реальный** controller/dispatcher: FIFO255, reserved2EOS/mask3, late enqueue fence, pending Finalizer/lease, sink false/exact throw, held sink5100ms→failed; fresh Stop4–357us/job27791–122478us. P2 закрыт. | sufficient для исследуемого fence | Не принимать worker cleanup/v5/AAC-from-raw: acquisition bypass и independent generated AAC явны. Полные account/delete/shutdown ownership — T115+, не новый Phase0 lifecycle. |
| Partial block/index publish | R136: 28 cases, exception/ExitProcess77, six cuts half/full block, half/full temp index, postMove, postpublishedFlush; точный reached hook, 12 sticky failed writers и16 retries без orphan collision. | sufficient | Actual power-loss/full failure matrix относятся к T118; process cuts ими не называть. |
| Key/integrity failure | R135 corruption native ERROR/sticky Read; R140 **два actual CryptUnprotectData FALSE/error13** wrong entropy, no authority/cipher preservation; authenticated g3 semantic rejection=1 подтверждён обязательным direct open/parser guard. | sufficient для native refusal механизма | Не именовать wrong entropy actual profile/master-key loss. Отдельная destructive/profile identity матрица до design не нужна по literal T114. |
| Последний validated checkpoint | R134 full fallback3670016B/both-bad reject; R136 при cuts1–4 старые bytes,5–6 целая новая версия, retry latest+prior-reader identity; R140 latest2→tail-corrupt fallback1→invalidg3 fallback2→both invalid/reset/preserve6files. | sufficient | В T115 определить ambiguous commit/package authority/GC; fallback не разрешает normal claim усечённой записи или empty ledger. |

## Единственный оставшийся опыт, без расширения scope

Недостаток измерения установлен непосредственно по [ResourceProof.cpp:15](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/ResourceProof.cpp:15): IO before/after собирается внутри streamCase и заканчивается до MF. [MF-case:58–63](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/ResourceProof.cpp:58) печатает elapsed/finalization/disk/memory, но io() не вызывает. Source SHA `062560d273dc37c7458c14bcdd952361cc4f160d0eda68152cf46e9c04135abc` совпал с resource review; receipt38d913ac содержит IO только в трёх STREAM строках. Следовательно, неизвестна количественная IO-стоимость MF-driven переписывания/публикаций; наличие native успеха и конечных728676B её не определяет.

Минимальный полезный опыт: добавить **только в disposable proof**, не продукт, process IO before/after вокруг существующего MF encode→Finalize/reset/Commit→reopen→decode/EOS/seek; вынести verifyCipherFiles за окно либо явно пометить его стоимость включённой. Сохранить прежние проверочные условия и связать результат fresh source/EXE/runner receipt. Достаточны read/write transfer deltas вместе с уже имеющимися logical/disk bytes, timing и memory; это счётчики процесса, не physical disk benchmark. Новые media размеры, полноценный v5 pipeline, playback+capture одновременно, 60min/100cycles или дополнительные профили не требуются. Неподтверждённый путь должен остаться отказом/открытым исследованием, а не PASS без измерения. Этот audit рекомендует опыт, **не разрешает и не выполняет его**.

Reopen9.44s/Write430ms/index publication388ms уже измерены; неизвестность не надо заново доказывать. Plan877 запрещает такой scan в foreground/UI/readiness и выбирает existing background open-validation. Финальный asynchronous ownership/cache/IO contract — T115. **SC-003 и dispatcher drain5s неизменны:** долгий IO нельзя выполнять в callback или компенсировать расширением drain; R139 timeout остаётся failed, pending lease не превращается в normal success.

## Что не является дополнительным blocker Phase0

T114 требует проверить key/integrity failure выбранного native механизма, но не содержит требования удалить DPAPI профиль. Wrong entropy даёт реальный отказ native unprotect уже валидных собственных объектов и проверяет fail-closed authority/preservation. Это достаточный ограниченный ответ про key-context mismatch; не recovery proof при исчезновении master keys. Политика «сохранить артефакты, запретить unsafe writes/GC/plaintext fallback/empty ledger» проектируется в T115; **actual key/profile loss**, power-loss/disk-full boundaries и full installed standard-user/offline/поддерживаемые редакции (включая Home) проверяются в T118. Предложенная ранее anonymous identity — возможный способ исследования, не обязательный дополнительный gate после реального native refusal.

T115 определяет wire/schema/authority, pinned readers/lifetime, numeric limits и migration intent; T116 реализует весь защищённый v5/media/metadata/hash/range pipeline; T117 — migration/retirement; T118 — полный restart/playback/upload/delete, disk snapshots,100cycles SC-005, key-loss/power-loss/installed/update/rollback и memory/IO/Stop acceptance. Full64GiB nonzero media, app CPU/resident/physical60min SC-003, native workers и вся файловая матрица не перенесены в T114. Mixed3refs не принимаются за generic full-layout implementation, но закрывают bounded semantic/query вопрос размерности. Clock T094–T096 остаётся отдельным вопросом, не новым условием literal T114.

## Привязка evidence и окончательный вывод

Использованы narrow reports protected-stream-proof/native-playback/publish-faults/resources/large-index/protected-stop/mixed-index в этой папке; каждый сохраняет свои ревизии, source и receipt hashes. R134 дополнительно прочитан из полного context-result-9759c81a… (SHA `1cb2a8e9a9fe2af7ef00ed785c59ae93b3b8203fe47f59c4d7e412d1b0544eef`), а не из неподтверждённого round133 сообщения. Метаданные R13522abdb51/9ea4a118, R13642555b77, R13738d913ac, R138fda8c038, R13944343e83 и fresh R140852974e5 пересчитаны: receipt hashes совпали с соответствующими reports, exit0/stderr0. Fresh R140 build d9bda888/source/EXEs/runner подтверждены предыдущим narrow rereview; first round140 до P2 fix не заменяет fresh evidence. Это чтение сохранённых доказательств, не независимое воспроизведение Windows runs и не hermetic аттестация всей сборки.

**До T115 остаётся один ограниченный вопрос: измерить IO уже доказанного совместного MF seek/rewrite пути и записать его границы. На имеющемся evidence T114 NOT READY именно по этому literal measurement gap, не из-за отложенной полной T118 приёмки.** После такого дополнения нужен review результата, а не автоматическая отметка выполнения. Задачи/checkboxes не закрыты, implementation не разрешена. Кроме нового отчёта, выполнена только отдельно запрошенная замена атрибуции одной фразы в mixed-index report; findings/hashes там сохранены.

## Дополнение 2026-10-02: fresh combined MF IO и совокупный exit verdict

**Текущий вердикт: APPROVED для исследовательского exit буквального T114. Единственный measurement gap предыдущей матрицы CLOSED; конкретных неподтверждённых механизмов из literal T114 на рассмотренном evidence больше не найдено.** Прежний NOT READY и матрица выше сохранены как история до этого дополнительного измерения. Это вывод о достаточности Phase0 исследования RQ30-H1, не готовность product storage, не закрытие task/checkbox и не начало или утверждение T115. Общий Phase0 F200, включая независимые clock вопросы, данным выводом не закрывается.

Reviewer лично заново прочитал code-reviewer SKILL, текущие ResourceProof.cpp, resource-run.ps1, resource-build-run.ps1 и обе fresh квитанции целиком; также оба текущих общих helpers CommitProof.cpp/BlockProof.cpp полностью и реально вызываемые ProtectedStream reopen/encode/decode условия. ProtectedMfProof SHA совпал с ранее полностью рассмотренным source. Повторно сопоставлен literal tasks.md:544. VM/build/run/tests не выполнялись; единственная запись этой повторной проверки — настоящее append-only дополнение.

### Измерительное окно и ошибка/оракул

[ResourceProof.cpp:59](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/ResourceProof.cpp:59) снимает mediaIoBefore до создания ProtectedStream, затем запускает таймер. Внутри окна: создание stream, encode3000×10ms, успешный Finalize/reset/Commit, копирование writer metrics, validated reopen обоих indexes/их references, decode до EOS, два bounded SourceReader seek и освобождение reader. mediaElapsed и mediaIoAfter фиксируются до verifyCipherFiles. Поэтому отдельный verification scan и последующее fileBytes действительно исключены из IO/elapsed; обязательная validation самого reopen и decode/seek остаются внутри. Elapsed заканчивается непосредственно перед конечной IO-выборкой, не включает стоимость её получения.

GetProcessIoCounters вызывается для текущего Resource process: это все его учтённые операции за интервал, не только media-каталог/поток, не launcher/Job или физические sectors/flush latency. ReadTransferCount/WriteTransferCount — байты, не число операций. [Определение API](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getprocessiocounters), [поля IO_COUNTERS](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-io_counters). Возможная внутренняя MF/runtime IO остаётся в этом combined process window; её отдельно не приписываем media blocks. Полное native/physical IO tracing для literal T114 не требуется.

require `mf-io-measured` проверяет увеличение обоих transfer counters до вычитания. Ошибка API, zero delta, ошибочный HRESULT encode/Finalize/Commit/reopen/decode/seek или нарушение EOS/count ведут к FAIL/exit1; один marker не заменяет эти обязательные проверки. Positive deltas — sincerity guard измерения, **не новый продуктовый threshold/SLA** и не самостоятельное доказательство правильного media. Media checkpoints/rewrites сняты после завершающего Commit, до reset. Lifetime memory peaks снимаются после verification scan и относятся ко всей жизни процесса, не только новому IO-окну. Новых blocking findings в этом изменении/обвязке не обнаружено.

### Fresh receipts и точная привязка

Полностью прочитаны [resource-build-result-7f016020-c389-4312-926e-4d0cc88b9a44.json](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/resource-build-result-7f016020-c389-4312-926e-4d0cc88b9a44.json) и [resource-result-a10ed438-b190-4e4c-9824-f29c2a4be2fb.json](/Users/yshishenya/Documents/graf-windows-followup-200/f200-protected-mf-proof.jADm92/resource-result-a10ed438-b190-4e4c-9824-f29c2a4be2fb.json). Независимо вычисленные hashes:

| Артефакт | SHA-256 текущих локальных bytes |
|---|---|
| ResourceProof.cpp | `106e03275206c156780177774ee4f12144dc5f387da22f4a64d114752ed6a10d` |
| ResourceProof.exe | `39325f1b509e3fe792873166343ebb51024ec0822436639127fa1305660bb81e` |
| ContextProof.exe | `52455eb60f76ad3e0f65f176c9fd761012b51380b60bdcd5f0d502c209101b91` |
| resource-build-run.ps1 | `eb4077e4be241f5de94930668fa90ab59f3321392eaab00e0e936abc9d528bd4` |
| resource-run.ps1 | `d7bd0229baa9dbfaf5566668af03da60c5bd8e290b1c1c713e9b200ac682acd2` |
| Build receipt7f016020 | `44f13b62190a91fd2d63f95832e016bbb52a2a93ea5823515fc2d0d6265f3893` |
| Run receipta10ed438 | `67e1f1e593ae45d7814bdd54f962fb7eed6cf738acf62c6ba73474f1115284c5` |

Все шесть build inputs и девять run inputs независимо пересчитаны и совпали с соответствующими manifests; общие шесть совпали между build/run. Resource EXE hash совпал между build receipt, run receipt, fixed runner и локальным EXE. Context source/EXE unchanged относительно fresh mixed review и совпали с run manifest/fixed runner/локальными bytes. Build receipt содержит build_exit0; это Resource build, не новая Context build receipt. Полные helper hashes сохранены в обоих manifests: Commit `f42b7820bfb04187c32d773fbb49d269e7cce831d6a8a3ab1c6aacf9e9f79ef1`, Block `462b4658dc7c2577119fbcc89c40d075c85e6e758a4372d45790590ee5c73daa`; их default limits и ошибочные пути не ослаблены.

Build wrapper проверяет inputs before/after и сохраняет LASTEXITCODE немедленно; run runner проверяет девять inputs и оба fixed EXE before/after. Receipts хранят начальные manifests, не две отдельные копии: достижение accepted соответствует отсутствию mismatch по прочитанному runner. Это согласованность metadata/current bytes, не независимое воспроизведение сборки, hermetic compiler attestation или подписанная квитанция.

Run: exit_code0, stderr_bytes0, accepted=true; marker counts3/1/1/1 независимо подтверждены. Три STREAM строки относятся ровно к1048699/16777339/67108741B, все whole_identity=true. MF/INDEX/PROOF присутствуют по одному, FAIL отсутствует, CHILD_RESULT exit0/medium_nonadmin_verified=true, medium_integrity8192/restricted_admin=false. Fixed Context запускает sibling ResourceProof --medium в own Job до ResumeThread: child guard60s, runner70s; это исследовательские watchdogs, **не замена dispatcher5s**. Output2813 символов ниже4096; bound применяется после чтения и не доказывает потоковую memory quota.

### Количественный результат и обновление матрицы

| MF30s метрика | Fresh result |
|---|---:|
| Logical AAC / decoded PCM | 366529 / 2881536B |
| Process read / write за combined окно | 2086190 / 729376B |
| Writer checkpoints / rewrites | 4 / 2 |
| Encode→finalize→reopen→decode/seek elapsed | 561718us |
| Finalize/reset/Commit вместе | 246767us |
| Own ciphertext inventory / file sizes | 6files / 728676B |
| Lifetime peak commit / resident после verification | 31985664 / 43474944B |

mf_io_measured=true и verification_scan_excluded=true согласованы с source, не только с output literal. Три raw stream cases и memory-only index envelope повторно прошли: largest all258objects/whole identity, tail26689us, reopen9583851us; native envelope4198400B whole identity с явным existing1MiB-helper rejection. Reopen≈9.58s **не** снимает прежний запрет foreground/UI/readiness validation. MF IO не является physical disk throughput или принятой app CPU/resident/Stop производительностью.

В единственной прежней `partial` строке «Измерить combined IO» статус теперь **sufficient для bounded Phase0**: actual protected MF seek/rewrite путь получил требуемое количественное окно с явными границами. Остальные десять строк сохраняют sufficient по уже привязанным round134–140 доказательствам; новый Resource run не подменяет playback/Stop/fault/mixed receipts другими EXE. Наличие protected MF rewrites + measured IO дополняет, а не заменяет исследования checkpoint authority и error truth.

### Совокупное заключение literal T114

**APPROVED / evidence sufficient для исследовательского exit T114 RQ30-H1.** Совокупность round134–140 и fresh resource receipt проверяет перечисленные native DPAPI/block/two-index механизмы совместно с IStream/MF/AAC/playback, измеряет IO/memory/disk/tail, проверяет реальный Stop/fence, partial publication, native key-context/integrity refusal и последний validated checkpoint. После закрытия единственного количественного пробела оснований требовать ещё один bounded опыт механизма до T115 в literal T114 не найдено. Сохранённые ограничения не превращены в новые предпосылки Phase0; отрицательный результат синхронного reopen учтён как ограничение выбранного дизайна.

**T115 ещё не начат/не принят, окончательный protocol не утверждён, implementation не разрешена этим review.** SC-003 и5s drain не ослаблены. Actual profile/master-key loss, power-loss/disk-full/fullmatrix, installed standard-user/offline/Home,100cycles, migration/retirement и full protected product chain остаются соответствующими design/implementation/acceptance gates T115–T118; wrong entropy по-прежнему не называется profile loss. Общая готовность F200/clock Phase0 не заявлена. Tasks/checklists checkbox state не менялся; reviewer только дописал этот отчёт, без других writes/VM/build/run/tests/GitHub.
