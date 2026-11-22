# T120: независимое обновление проверки требований приватной паузы

Дата: 2026-10-12. Lane: high-risk-product, только требования и конструкция
проверки. Объём — ровно CHK001–CHK012 действующего `privacy-pause.md`.

**Итог требований: PASS, 12 проверены / 0 неподтверждённых;
CRITICAL0 / HIGH0 / MEDIUM0 в указанном объёме.**
**Реализация T120: NO-GO до явной авторизации и canon/issue sync.**
Отсутствующий issue — отдельный процессный prerequisite, не неоднозначность
требований и не основание ослаблять их.

## Привязка, способ проверки и ограничения

Каноническая рабочая копия Feature200, ветка `codex/200-windows-followup`,
лично прочитанный HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
`.specify/feature.json`: feature200, owner `codex`, lane `high-risk-product`.
Незакоммиченные требования привязаны к SHA-256 ниже, не только к HEAD.

Использован `speckit-analyze`: прочитан полностью SKILL.md, выполнена
ограниченная cross-artifact проверка, без изменения нормативных артефактов.
Этот отдельный reviewer report записан по прямому разрешению пользователя;
результат анализа не меняет spec/plan/tasks или checklist.
Установленный prerequisites script не поддерживает upstream `--require-spec`;
путь подтверждён поддерживаемым `--json --require-tasks --include-tasks`,
spec/plan прочитаны непосредственно. Эта проверка пути выполнена в предыдущей
части текущего review. YAML extensions разобран через safe_load:
enabled before_analyze/after_analyze hooks — 0/0; commit hooks не выполнялись.

Прочитаны актуальные CHK001–012, исторический requirements report2026-10-04,
spec FR-002/009/010, SC-002/004 и Session2026-10-04; plan раздел T120;
quickstart §15; desktop contract §3; data-model §1; research T120;
local-custody §3–5 и T116/T120 в tasks. Конституция перечитана;
AGENTS/router и применимые guidance о риске, capture/privacy, issue sync,
валидации и гигиене прочитаны. В PRD/status прочитаны относящиеся к предмету
части, не вся историческая документация продукта. Packed contract здесь
проверен по SHA как неизменённая зависимость, не заново принят как реализация.

Mac-образец сверялся через локальный `git show` точного commit
`c8d67ccefe7848f731798b23d72d37757ad812f5`: privacy contract FR012,
полный PrivacySuppressingSampleSource, ProductPrivacySegment/enums,
manifest encoder/decoder и writer pause/resume/checkpoint portions.
Это собственный согласованный эталон, не сторонний исходный код.
Полного повторного аудита всех задач/отчётов или нового runtime не заявляю.

## Доказательство каждого из12 пунктов

| Пункт | Лично проверенное актуальное основание | Решение |
| --- | --- | --- |
| CHK001 | spec Session2026-10-04 фиксирует полный Mac SHA и связь FR-002/009. Desktop §3 и plan T120 отличают необратимое подавление накоплений от bool при drain. FR-002 сохраняет семантику Mac, FR-009 — один bounded timeline. Pinned Mac contract и wrapper подтверждают выбранную FIFO семантику. | PASS требований |
| CHK002 | Desktop §3 п.1/4, spec и quickstart раздельно задают обязательный protected OPEN до accepted Pause и best-effort CLOSE после успешной границы Resume. Mac pausePrivacyOnQueue сначала persist, при ошибке снимает новый active segment и бросает ошибку; resumePrivacyOnQueue требует boundary, затем finalize и try? checkpoint. Failed CLOSE не превращает принятый Resume в отказ и не стирает прежний durable OPEN. | PASS требований |
| CHK003 | Desktop §3 п.2, plan шаг1 и quickstart явно охватывают producer queue, extracted/in-flight, prefetched, timeline и частичный prefix. Уже записанный pre-Pause prefix не переписывается. Resume не восстанавливает старые samples изменением текущего bool. Mac suppressPrefetchedBatch сохраняет формат/PTS/route и не учитывает уже подавленное дважды. | PASS требований |
| CHK004 | Desktop §3 п.3 и plan требуют точную границу под владением append/read FIFO, replacement вместо сложения, отсутствие двойного учёта prefetched и ожидания пустой очереди. Mac update/read используют один wrapper lock, withQueuedFrameCountSnapshot меняет state под FIFO boundary; queuedFramesToSuppress заменяется. Quickstart задаёт concurrent producer, partial batch и повторные controls. | PASS требований |
| CHK005 | Desktop §3 п.3, spec и quickstart Boundary unavailable требуют отказ Resume при отсутствующей/отрицательной/некорректной границе: paused, durable OPEN, system и Stop сохраняются. Mac boundary отказ возвращает false, writer выбрасывает resumeBoundaryUnavailable до finalizePrivacySegment. Диагностический счётчик сам по себе не разрешает Resume. | PASS требований |
| CHK006 | FR-009/010, desktop §3 п.5 и quickstart Неверные данные сохраняют system reference, PTS, count/channels/format/route, exact480-frame AEC и Stop/EOS. NaN/Inf, invalid timestamps/count/route/overflow должны отклоняться даже у подавляемого mic; raw validation выполняется до потери исходных значений при zeroing. Fault sticky; raw fallback/wall-clock padding запрещены. Это требование, не утверждение о пройденных новых негативных тестах. | PASS требований |
| CHK007 | Spec, desktop §3 п.6, plan шаг3 и tasks T116/T120 связывают durable privacy metadata с защищённым T116. Ни текущий открытый writer, ни отдельный plaintext journal не обходят эту зависимость. Timeline/dispatcher prerequisite допускается как ограниченный этап без UI/durable принятия Pause. | PASS требований |
| CHK008 | Data-model §1 задаёт все11 полей ProductPrivacySegment, control/treatment/initiator, optional endedAt/endMonotonicMs, OPEN duration0, closed end>=start без overflow. Pinned Mac struct совпадает по именам и optional полям; Codable не задаёт custom CodingKeys. ManifestService использует .iso8601 для encoder/decoder. Known legacy отсутствие privacySegments сохраняется, whitespace/key order не authority. Exact bytes fixtures и строгий Windows validator остаются обязательной отдельной consumer проверкой, не выдуманным приблизительным JSON. | PASS требований |
| CHK009 | Local-custody §3, plan и quickstart задают весь serialized manifest<=65536B, 65537B отказ до publication/OPEN. Один прежний256KiB block; owned64MiB, job2MiB, cache/pins/jobs/root/queue/audio bounds не увеличиваются. Codec cases1/4096/4097/65536 означают вместимость/roundtrip, а не валидность произвольного payload как v5. Hash/format/identity checks не ослабляются. | PASS требований |
| CHK010 | Desktop §3 п.1/6 и quickstart Mandatory OPEN/История пауз запрещают accepted Pause при failed OPEN/cap exhaustion, обрезание прошлого и произвольный segment-count cap. Plan требует согласовать decoder/reader/writer/legacy; unknown/duplicate/malformed формы не допускаются substring-проверкой. Legacy compatibility не означает принятия повреждённого encrypted object как plaintext. | PASS требований |
| CHK011 | Desktop §3 п.7, plan шаг5, data-model и quickstart Stop/late completion требуют единственного owner/dispatcher/writer, current session/generation ordering, async UI/Stop без storage I/O на WASAPI/UI. Late OPEN/CLOSE после Stop/Quit/newsession не возвращает recording/delivery. Queue254+EOS2 и прежние бюджеты сохраняются; timeout не подменяет реальное завершение/last release. Конституция II сохраняет видимый capture и one-action Stop. | PASS требований |
| CHK012 | Plan steps1–5, tasks и quickstart разделяют T116 codec/storage prerequisite и T120 capture control; RED обязателен, synthetic/native/installed и hardware/release самостоятельны. Приёмка timeline не доказывает FIFO/in-flight, durable privacy, весь T116/T120, physical x64/AEC/60min, installed MSIX или выпуск. Исторические source/runtime результаты не переотмечаются. | PASS требований |

Критерии не изменились. Все12 существующих отметок сохранены байт-в-байт;
новые checkbox items не добавлялись. Свежая сверка завершает ранее pending
refresh; исторический report2026-10-04 остаётся отдельным историческим фактом.

## Scoped analyze и покрытие

Область анализа — требования этих12 пунктов, не полный Feature200 analyze.
CRITICAL0 / HIGH0 / MEDIUM0; блокирующих clarification gaps и конфликтов
в этом объёме не обнаружено. Все12 имеют явные нормативные основания.

FR-002/009, SC-002/004 прямо покрыты T120; FR-010 сохраняет invalid-input,
AEC ordering и no-raw границы. Protected metadata/consumer dependency покрыта
T116, без новой задачи-дубля. Предписанные FIFO, durable и installed сценарии
остаются обязательными, хотя не входят в ближайший delayed-render RED.
Слово CRITICAL в текущей строке T120 описывает незавершённый дефект/приоритет
реализации, а не обнаруженное здесь противоречие требований.

Constitution I/II: native capture integrity, явный отказ и доступный Stop
не ослаблены. III: нового egress/credentials/серверной authority нет.
IV: privacySegments принадлежат прежнему пакету/удалению, не новому журналу.
VI: mandatory clarify/checklist/analyze/issue gates сохранены.
VII: reference fidelity не отменяет privacy/accessibility/source/runtime gates.
V/public signing и полный release вне этого requirements PASS.

## Узкая конструкция RED и границы внешнего diagnostic

Требования допускают первым prerequisite test в существующем Timeline flow:
проверенный общий480-frame prefix → Pause → mic без render → Resume → render.
Старые pending mic samples должны остаться нулевыми; system, PTS, counts,
новые post-Resume samples, AEC и trusted prefix сохраняются. Нужны также
invalid raw samples/metadata проверки до zeroing, а не их маскировка нулём.
Этот этап не принимает producer FIFO snapshot или durable OPEN/CLOSE.

Лично прочитан внешний `graf-f200-pause-red.0Lg1Z3/pause-red.cpp`, SHA-256
`cef802db66907ee5274ac50d3993dbfcf8c597f9813f670e2ac5f6d7d6363940`.
Он через переименование main включает действующие RecordingAudioTimelineTests,
вызывает их baseline, затем проверяет pendingBeforePause0/1/240/480,
system/PTS/new Resume mic/AEC calls/prefix/close; при утечке возвращает42.
Тестовые значения синтетические. Reviewer ничего не компилировал/запускал.
Compile0/runtime42 и4/4 утечки — сообщение main, не лично перечитанная
runtime receipt: в прочитанном каталоге были wrapper и executable, отдельного
журнала/receipt не было. Конструкция не покрывает raw-negative tests,
FIFO/in-flight/continuous producer, durable writer или Windows native.
Внешний diagnostic не заменяет issue sync и не разрешает repository edits.

## Отдельный implementation stop

T120 остаётся открытой строкой tasks. Main сообщил fresh search/list, где issue
T120 не найден; исторический report также явно оставлял authorization pending.
Reviewer GitHub не опрашивал и не изменял. `.specify/feature.json` owner codex
не заменяет синхронизированный task-backed issue.

До capture/test implementation необходимы явная авторизация на canon/sync,
проверка дублей по feature/task/labels и канонический issue с привязкой T120.
Title/body/labels — по действующему github-issue-canon; enabled mandatory
before/after_taskstoissues hooks нельзя обходить. Ни issue, ни T120 completion
этим report не созданы. Этот процессный NO-GO не включён искусственно в C/H
счётчик неоднозначностей требований.

## SHA-256 актуального нормативного снимка

Пути ниже относительны канонической рабочей копии; live local paths не включены.
SHA полного файла не означает полного перечитывания несвязанных разделов.

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| plan.md | 40443131fdafc41aa13ef98058e2fa95608dfdc1f60ae03d2ea6ab3acadb4868 |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| research.md | 901de067501da665dc3d28710c7691665a3d584f7bdcdb8f4f3c1a1ebbf8a774 |
| data-model.md | c24b9d10bf5b935bcf51bb12034a0bb9ccef4a0b3719a138b48a26cbaa0d3bc7 |
| quickstart.md | 6a070377de42113eea427d376f6b39beac5e222ca1dab31a69a85587b68f6dc3 |
| contracts/windows-desktop-contract.md | 79a5b1870748f50f857e082d6ec5b2f99ba6a9149d846718865ef1de71cf5d2d |
| contracts/windows-protected-local-custody.md | 598223854ea7e614694167c4019ef199e30c82b3ac1c44b33fcefa94fbe27fee |
| contracts/windows-protected-packed-custody.md, hash-only dependency | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| .specify/memory/constitution.md | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |
| checklists/privacy-pause.md, unchanged | 5e1c0a89ebb33f47876fafd345972e3e627e6597504d6b6a5dc4c8ac1ab10eec |
| checklists/review-2026-10-04-privacy-pause-design.md, historical unchanged | 9098ed5afd52a956b24020db32b827d579ebbc9b8bf0ff1f8412c95598a6a75e |

## Guidance и reference binding

| Артефакт | SHA-256 |
| --- | --- |
| AGENTS.md | 384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b |
| .specify/feature.json | d4be889d623986959cc6b11beeb6227a4a33d0a1d9b2052e782db105439ba882 |
| .specify/extensions.yml | ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c |
| docs/agent-guidance/README.md | 40e357e422c60915d2c4334c83b9ab74f5ef4c0df6ab8831e3ed16e281ba18a6 |
| docs/agent-guidance/codex-worktrees.md | d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d |
| docs/agent-guidance/spec-kit-flow.md | 5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887 |
| docs/agent-guidance/product-gates.md | e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097 |
| docs/agent-guidance/tracker-policy.md | 06450200cabdef48000af51241564e9ee9e8d36b50c71e06a88f8c50b7365466 |
| docs/agent-guidance/github-issue-canon.md | 7cd5c1cde2bb51e3842cae9e3717b094fea9f6fbb33fb1a408e6d243f9d68bf3 |
| docs/agent-guidance/release-and-validation.md | e3d24689a330634ec5ef87d829f8bcbf16bb7b81e0196b9d0baae4f49f27278d |

Следующие SHA — полных Mac файлов из pinned c8d67c…; прочитанный объём указан
выше, это не новое runtime/installed принятие Mac.

| Mac reference | SHA-256 |
| --- | --- |
| PrivacySuppressingSampleSource.swift | ca8d3b86defb99d1945d18cc81795c0f528cfdbcc9add3ddea591caea920cd32 |
| MeetingMuteTruthModels.swift | a01b4f1799379c4abea9715354f2327fafc3dd706cad4fe93c30f3f296415767 |
| LocalRecordingManifestService.swift | 36fec91280c57d6d8e30b3ae07969d7994520edb3de38c488d6c83ca2259558a |
| V5LocalRecordingWriter.swift | 044061b32fea07979229474337c934f7c4620ab42ffe5da910b5b944294a5b23 |
| F284 contracts/recording-and-playback.md | b1b234fac88839b40bb359b6c2155b2d7722f73607e42bae957be8fee41f1d50 |

## Контроль изменений и итог

До записи:193 checklist/report files,29 с checkbox items,
420 checked /0 unchecked. После добавления только этого отчёта:194 files,
29 с items,420 checked /0 unchecked. Privacy checklist12/0 до/после.
Tasks120 =93 checked /27 open; T120 и T116 не отмечаются выполненными.

Digest прежних193 файлов: SHA-256 отсортированного UTF-8 списка
`filename + space + sha256(bytes) + LF` равен
`0797488920c71addc72efb5bd3a0a1d15acea158c639c68e8665103be73b85c0`.
Повторный readback исключает только этот новый report и должен сохранить
этот digest. Нормативные hashes и checklist marks должны совпасть с таблицей.

Разрешённое изменение — только новый reviewer-owned report. Никаких
code/test/spec/plan/tasks/constitution/GitHub/VM/commit изменений reviewer
не выполнял. Итог — завершённый свежий PASS качества12 требований;
не source/runtime acceptance, не готовая Privacy Pause и не снятие issue stop.
