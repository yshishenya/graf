# Независимая проверка требований F200: освобождение WASAPI-пакета — 2026-10-01

## Итоговый gate

**PASS — только requirements-quality gate для узкого восстановления существующей
custody-гарантии в T096: ровно одна попытка ReleaseBuffer для полученного пакета
при исключении выделения samples, проверка результата освобождения и остановка
без normalizer/callback/append.** Невыполненных требований качества к этому
ограниченному предложению не выявлено.

Это разрешение продолжить существующую T096 в высокорисковом Spec Kit срезе,
а не приёмка шестистрочного прототипа, готового рабочего diff, всей T096,
SC-003, архитектуры F200 или выпуска. Общий Phase 0/Phase 1 gate для новой
clock/protected-storage модели **NOT READY**; никаких исключений из него нет.
Остальные analyze, implementation, validation, exact-SHA review и approval
gates сохраняются. Main выполняет узкий analyze отдельно; этот отчёт его не заменяет.

Дата запуска review: **2026-10-01**, местная дата по уточнению пользователя.
Новый отчёт создан отдельно; review-2026-09-30.md и другие прежние отчёты не
переписываются. T096/#7239 — существующий владелец работы, не новая задача.
Статус #7239 OPEN предоставлен main; GitHub в этом review не читался и не менялся.

## Область, независимость и источники

- Единственный рабочий каталог:
  /Users/yshishenya/.codex/worktrees/200-windows-followup/crisp.
- Ветка codex/200-windows-followup; HEAD
  a9691d4d474d918f54493d55a3aba286c749b513. Проверен dirty рабочий снимок,
  а не только содержимое HEAD и не опубликованный PR SHA.
- Активная F200 установлена по .specify/feature.json и локальному
  check-prerequisites.sh --json --paths-only, не по имени физического worktree.
  Полоса high-risk-product; scoped docs-only характер этого reviewer-изменения
  не понижает полосу будущего исправления capture.
- Прочитаны AGENTS.md, guidance index, активные spec.md, plan.md, tasks.md,
  quickstart.md, конституция, spec-kit-flow.md, codex-worktrees.md,
  product-gates.md, tracker-policy.md и относящиеся к review/доказательствам
  разделы release-and-validation.md; сверены capture/encrypted-buffer положения
  product baseline и current-product-status.
- Для конкретных критериев сверены data-model.md, research.md, parity-matrix.md,
  clarify.md, Windows desktop/native-web contracts, перенос F277 и ux-evidence.md.
  Критерии и примечания всех пяти активных checklist прочитаны. Все шесть
  исторических файлов checklists/analyze-* и checklists/review-* рассмотрены
  как контекст, не как сегодняшнее подтверждение реализации.
- Исторический validation-контекст рассмотрен во всех семи файлах
  validation-2026-09-06/17/26/27/28/29/30.md и quickstart-run-2026-09-19.md:
  основания, итоги, ограничения, относящиеся к текущему capture/custody и
  сегодняшнему gate сведения. Исторические package/test/UI результаты не
  перенесены на текущий dirty снимок и не объявлены новыми прогонами.
- Применены speckit-implement и speckit-checklist: reviewer-owned отметки
  оценивают полноту, ясность, измеримость и согласованность требований,
  а не runtime proof. Встроенный requirements.md оценён, но не редактировался.
- Изменение рецензента — только этот новый отчёт. Старые checklist/report,
  spec/plan/tasks/constitution, source/tests, устройства, сеть, GitHub, Git index,
  commits и пользовательские данные не изменялись. Сборки и тесты не запускались.
  Предшествующие незакоммиченные изменения принадлежат другим участникам и сохранены.

## Почему открытая Phase 0 не блокирует именно существующий custody repair

| Работа | Действующий gate | Основание и решение |
| --- | --- | --- |
| Устранить исключение до ReleaseBuffer в текущем consumePacket | PASS по качеству требований узкого предложения; implementation proof ещё нужен | P: последнее уточнение T096 прямо выделяет этот regression/fix отдельно от clock bounds; R: «T094/T096: reuse преобразователя и исключение до ReleaseBuffer»; T096 уже покрывает worker/sink/failure ordering; S FR-009/010/018 и SC-003 сохраняют прежний fail-closed путь. Не создаётся новая модель. |
| Ввести новый clock estimator, коррекцию resampler ratio или новые thresholds | NOT READY; запрет реализации сохраняется | P «Открытая Phase 0…», R round122–124: coherent estimator/slew/uncertainty, startup/partial EOS и двухисточниковые waveform проверки не выбраны/не приняты. API candidate SetRatio и короткий metadata опыт — не утверждённый clock contract. |
| Ввести ProtectedLogicalFile, защищённый полный stream, формат/authority/migration/playback | NOT READY; запрет реализации сохраняется | S FR-012 и PRD требуют encrypted local buffers; P/R описывают DPAPI/layout candidates, но Phase 0 остаётся открытой, Phase 1 data-model/contract/tasks, миграция, combined IO/memory/Stop/power-loss и playback fences ещё не завершены. ACL/EFS/защита одного manifest не закрывают требование. |
| Ослабить §5, расширить routing, добавить synthetic coverage или признать SC-003 | Не разрешено | Текущий C §5, S FR-007/009/010/018 и SC-003 остаются нормативными. Исправление освобождения не объясняет наблюдаемый clock_drift и не доказывает здоровый захват. |

Плановая фраза «перед реализацией… Phase 1 и общий gate не закрываются» относится
к двум незавершённым техническим решениям, перечисленным непосредственно перед
ней. Последнее уточнение P отдельно требует reviewer/implementation gate для
исправления уже существующей custody-гарантии без расширения clock bounds.
Эти положения совместимы: узкое сохранение ресурса не является скрытым запуском
заблокированной архитектуры. Общий gate остаётся NOT READY и после этого PASS.

## Фактическое основание: что доказано и чего не доказано

Прочитан round124 check.cpp:
`/tmp/graf-f200-release-allocation.ZT2GOG/check.cpp`.
Проверены SHA-256 исходника
`205d0494ba01a56ea1bbe2138ff6346cc5a28758fa18452b8f7ce380501e3fd4`
и существующего executable
`8702f73577a90c237b0ddb61cf77b000d8eda17e0e9e36cfe5b7d3fc93f0c52b`.
Файлы только читались, executable не запускался.

Стенд вызывает настоящий shared consumePacket через существующий TestPeer.
Одноразовый отказ operator new ограничен 480 float allocation; release function
построена до включения fault injection. Проверки намеренно ожидают bad_alloc,
ReleaseCalls=0 и отсутствие release trace. Это **контрпример** прежнего поведения,
не положительный custody proof. validation-2026-09-30.md фиксирует build0/run0
с actual worker/mapper/normalizer и
ALLOCATION_FAULT_REPRODUCED=1 RELEASE_CALLS=0 CUSTODY_ACCEPTED=0.
Сегодня подтверждены текст, связь с actual source и хеши, но не новый запуск.

По текущему worker source:
GetBuffer → GetPosition → consumePacket → mapper.observe → batch.samples.resize
→ copy/zero → проверенный release → normalize → callback.
resize может выбросить исключение до release; внешний thread catch ставит
initializationFailed, но сам пакет не освобождает. COM interface RAII не
подменяет ReleaseBuffer(count). recordTrace noexcept, mapper.observe в текущем
исходнике выполняет только арифметику/проверки и не выделяет память. Обычные
ранние отказы consumePacket уже используют один shared release helper, который
ставит releaseFailed после отказа ReleaseBuffer.

По сообщению main от 2026-10-01, disposable шестистрочный try/catch только вокруг
resize проходит actual consumePacket one-shot для Release success/failure:
одна попытка, приоритет releaseFailed, noNormalizerAdvance. Путь/хеш изменённого
прототипа и его полный output в этот review не предоставлены; это
**предоставленное свидетельство**, а не независимо выполненная или полностью
проверенная рецензентом регрессия. Оно не закрывает T096 и не одобряет будущий diff.

## Требования к минимальному предложению и последующей приёмке

| Обязательство | Конкретное основание / ожидаемое доказательство |
| --- | --- |
| Ровно одна попытка release для каждого полученного пакета на failure path | Existing release helper и P/R T096 allocation counterexample. Успешный release не обещается при HRESULT failure; нельзя повторять попытку в outer catch или destructor после уже выполненной release. GetBuffer failure не освобождает неполученный packet. |
| Исключение до release не оставляет acquired packet без cleanup | Общая native consumePacket catch/cleanup либо ownership RAII. Для текущего resize fault catch должен вызвать прежний checked release и вернуть отказ; не продолжать normal capture и не перебросить исключение в outer catch с потерей reason. |
| Не потерять custody до входа в consumePacket | Native call site строит временный std::function из capture-lambda после GetBuffer. One-shot 480-float стенд строит function заранее и эту границу не проверяет. Перед широкой формулировкой «ни одно исключение acquired packet» доказать отсутствие fallible callback construction в этой области либо построить существующий callable до acquisition/защитить acquisition RAII. Это обязательство implementation review, не новая публичная API/библиотека и не waiver. Шесть строк вокруг resize сами по себе не доказывают эту более широкую гарантию. |
| releaseFailed имеет приоритет | На allocation fault сначала выставить существующий подходящий bounded failure, затем вызвать release helper, который может заменить его на releaseFailed; после этого не перезаписывать reason. При successful release остаётся allocation-path failure; в обоих случаях false, ready не становится true. Не требуется новая public error enum/API. |
| Не двигать normalizer и downstream | При allocation failure normalize, callback, dispatcher append/timeline/AEC/writer не вызываются; нет partial batch или silent fallback. Mapper уже выполнен до resize — noNormalizerAdvance не означает rollback/noMapperAdvance; нельзя ради этого менять clock модель или запускать новый origin. |
| Сохранить штатный путь и ранние отказы | Не изменить GetBuffer/GetPosition checks, zero packet, startup-only discard, unknown/mixed flags, frame/channels bounds, continuity/clock rules, SILENT handling, sink failure, Stop/EOS/finalizer ordering и §5. |
| Native-first минимальность | Использовать нынешний checked release helper в shared consumePacket либо маленький acquisition owner. Без нового публичного API, зависимости, сервиса, storage schema, route, estimator, threshold, fallback или второй custody-цепочки. |
| Регрессия продукта обязательна после допущенного изменения | Actual shared worker one-shot allocation fault с Release success и failure; проверять count/однократность/HRESULT/reason/false/no normalize/no callback/no append. Сохранить положительные/отрицательные existing guards и соответствующую native validation для текущего снимка. Disposable pass не заменяет product test и exact-SHA review. |
| Полнота T096 и approval не закрываются узким PASS | Широкая T096 остаётся открытой, как и аппаратная/60-minute SC-003 приёмка. Main analyze и последующий implementation review/validation отдельны; commit требует явного одобрения пользователя после validation. |

Невыполненных требований **качества** к перечисленному предложению нет. В таблице
выше названы обязательства реализации/доказательства, которые должны быть
выполнены перед приёмкой кода: PASS не превращает их в уже пройденные проверки.
Если фактический diff ограничен resize catch, его нельзя описывать как доказанное
закрытие всех возможных исключений между acquisition и release без дополнительной
проверки указанной call-site границы.

## Повторный подсчёт исходных отметок

Подсчитаны именно строки checklist вида «- [X/x/ ] CHK…», с учётом регистра,
не таблицы прежних отчётов, численные утверждения в prose или task statuses.

| Checklist | Всего | Подтверждено | Не подтверждено |
| --- | ---: | ---: | ---: |
| advanced-routing.md | 14 | 14 | 0 |
| audio-capture.md | 24 | 24 | 0 |
| requirements.md | 22 | 22 | 0 |
| security.md | 27 | 27 | 0 |
| ux.md | 25 | 25 | 0 |
| Итого | 112 | 112 | 0 |

Reviewer-owned custom: 90/90; встроенный Specify requirements.md: 22/22.
Все существующие 112 отметок сохраняются. Ни один новый checkbox criterion
не создан; таблицы этого отчёта не увеличивают denominator. Неподтверждённых
checklist-пунктов 0, поэтому причин для [ ] в исходных checklist нет.

Это не означает полноту нового архитектурного плана. В частности,
security/CHK012 буквально проверяет user scope/ACL/atomic write/flush:
его [X] нельзя использовать вместо encrypted local stream requirement FR-012.
Уточнённое требование encryption наблюдаемо, но незавершённые design/validation
в P/R по-прежнему блокируют protected-storage implementation. Аналогично
audio/CHK005/007/019 подтверждают существующий clock contract, не новый estimator.

Ниже для каждого существующего критерия зафиксировано конкретное основание
требований в текущих документах. Историческая структура таблиц сохранена для
сопоставления с review-2026-09-30; подтверждение дано заново для ограниченного
нынешнего среза. Никакая строка не является runtime proof.

## Поэлементные результаты

Обозначения: **S** — `spec.md`; **P** — `plan.md`; **T** — `tasks.md`; **K** —
`.specify/memory/constitution.md`; **C** — `contracts/windows-desktop-contract.md`;
**B** — `contracts/windows-native-web-bridge.md`; **F277** —
`contracts/f277-notifications-parity.md`; **D** — `data-model.md`; **R** —
`research.md`; **M** — `parity-matrix.md`; **Q** — `quickstart.md`; **PG** —
`docs/agent-guidance/product-gates.md`.

### `advanced-routing.md` — 14/14 `[x]`

| Пункт | Итог и evidence требований |
| --- | --- |
| CHK001 | `[x]` — S «Контекст и цель»/FR-007 и M фиксируют общий WASAPI render loopback отдельно от process-isolated capture. |
| CHK002 | `[x]` — S «Out of Scope»; R «Rejected alternatives» перечисляют Stereo Mix, virtual driver, kernel, exclusive mode и service. |
| CHK003 | `[x]` — S FR-007/019; C §§2, 4, 6 запрещают обход DRM/privacy/ownership и привилегированный аудиопуть. |
| CHK004 | `[x]` — P «Source ownership»/«Audio pipeline» и M распределяют capture, custody и cabinet без второго владельца. |
| CHK005 | `[x]` — S FR-017 и C §6 задают ограниченный/degraded результат для protected audio без скрытого fallback. |
| CHK006 | `[x]` — S «Out of Scope»; R «Пересмотр гипотезы часов и границы будущего routing» отделяет process loopback в будущую фичу. |
| CHK007 | `[x]` — R, раздел о будущей routing-границе, перечисляет выбор/identity, дочерние процессы, технические разрешения, protected audio и fallback; K Principle II не превращает юридическое согласие в gate. |
| CHK008 | `[x]` — PG «Capture And Platform» требует для advanced routing отдельный approved Spec Kit slice и product gate; K «Product And Platform Constraints» сохраняет отдельное одобрение. |
| CHK009 | `[x]` — S «Out of Scope»; T §Phase 1 и T059/T070 описывают baseline package без driver/service/elevation. |
| CHK010 | `[x]` — S «Контекст и цель»/FR-007 и R «Render/system source» прямо называют глобальный микс, не звук одного приложения. |
| CHK011 | `[x]` — S FR-019/020 и SC-008; P §Architecture и M «Packaging/update» не зависят от routing-драйвера. |
| CHK012 | `[x]` — P «Complexity Tracking» и дополнение о полном паритете удерживают будущий routing вне базового среза. |
| CHK013 | `[x]` — R, раздел о process loopback, требует identity, явного технического выбора, границ данных и честного отказа; S FR-008/021 и K II согласованы. |
| CHK014 | `[x]` — S «Out of Scope» и PG «Capture And Platform» требуют отдельной одобренной спецификации до такой работы. |

### `audio-capture.md` — 24/24 `[x]`

| Пункт | Итог и evidence требований |
| --- | --- |
| CHK001 | `[x]` — S FR-007/008; C §4 определяет общий render endpoint и отдельный физический microphone endpoint. |
| CHK002 | `[x]` — S FR-004/008 и C §2 перечисляют privacy, endpoints, форматирование, AEC3/AAC, storage, indicator/Stop как readiness gates. |
| CHK003 | `[x]` — S «Out of Scope»; R «Rejected alternatives» исключает process capture, Stereo Mix, driver и exclusive mode. |
| CHK004 | `[x]` — S FR-017/Edge Cases; R «permissions, power and endpoint recovery» определяет endpoint/service/sleep recovery через состояние и поколение маршрута. |
| CHK005 | `[x]` — S FR-018; D §§4–5 и C §5/T085 задают QPC/WASAPI mapping, запрет wall-clock alignment и packet/timeline clock checks. |
| CHK006 | `[x]` — D §4 перечисляет source, format, frames, PTS, clock domain, route generation и discontinuity для batch. |
| CHK007 | `[x]` — D §5 и C §5 задают 960,000 buffered frames, 48-frame recovery bound, 100 ppm + 1 ms + frame, отказ >48 и исключение неиспользуемого reorder window. |
| CHK008 | `[x]` — R «Решение 3» и C §4 отделяют короткий callback от bounded queue, worker, normalizer, timeline и AEC3. |
| CHK009 | `[x]` — C §5/T085 задаёт входные/выходные диапазоны, малые пакеты, ±48/49, повтор/пропуск и отказ при discontinuity; Q §3 перечисляет synthetic cases. |
| CHK010 | `[x]` — S FR-009; C §5 и D §§3–5 устанавливают 48 kHz mono float и 480-sample/10 ms framing до AEC3. |
| CHK011 | `[x]` — S FR-009/010; R «Решение 1» указывает pin AEC3, а C §5 фиксирует render/reference перед microphone/near-end. |
| CHK012 | `[x]` — S FR-010/017; C §6 задаёт один fail-closed/degraded путь для AEC, reference, samples, timestamps, route и overflow. |
| CHK013 | `[x]` — S FR-010–017 и C §6 запрещают raw-mic fallback и различают доверенный префикс от normal package. |
| CHK014 | `[x]` — C §5: после AEC3 cleaned mic объединяется с неизменённым system component до writer. |
| CHK015 | `[x]` — S FR-011/SC-003; C §5 определяет роли, форматы, integrity и расхождение длительности ≤100 ms. |
| CHK016 | `[x]` — S Edge Cases/Assumptions и C §2 требуют AAC readiness и запрещают normal playback package при отсутствии encoder. |
| CHK017 | `[x]` — S Edge Cases/FR-017; C §§3, 6 описывают Pause, Stop, route/sleep/failure и сохранение только проверенного результата. |
| CHK018 | `[x]` — S FR-017; C §§4, 6 раскрывают protected/DRM limitation и запрещают выдавать её за полный capture. |
| CHK019 | `[x]` — S SC-003 задаёт 60 минут, ±100 ppm, frame/duration/RMS и resource thresholds; Q §3 разделяет synthetic и hardware run. |
| CHK020 | `[x]` — K capture gates, P «Performance Goals» и Q §3 дают измеримые CPU/memory/queue критерии. |
| CHK021 | `[x]` — P «Validation Plan»; Q §§1, 4 задают Windows 10 22H2/поддерживаемый Windows 11 x64, устройства и RDP limitation. |
| CHK022 | `[x]` — S FR-021; C §9 перечисляет разрешённые metadata и запрещённые audio, transcript, credentials, paths и meeting data. |
| CHK023 | `[x]` — C §3 описывает privacy pause с живой reference/timeline и timestamped zero contribution без wall-clock padding/raw path. |
| CHK024 | `[x]` — C §3 задаёт idempotent Stop и упорядочивает worker/EOS/timeline/writer/finalization/queue handoff. |

### `requirements.md` — 22/22 `[x]` (встроенный Specify checklist, неизменён)

| Пункт | Итог и evidence требований |
| --- | --- |
| CHK001 | `[x]` — S FR-001–022 и T «Requirements traceability»/phases дают наблюдаемые требования и задачи для каждого FR. |
| CHK002 | `[x]` — S SC-001–010; Q §§2–9 задаёт источник доказательства, порог и отдельную задачу/полосу проверки. |
| CHK003 | `[x]` — S User Stories 1–5 содержит independent test и acceptance scenarios; T «Dependencies & Execution Order» раскрывает зависимости. |
| CHK004 | `[x]` — S FR-002–004 и C §1–2 разводят native host и server-owned cabinet. |
| CHK005 | `[x]` — S «Edge Cases» и C §6 описывают нормальный, ограниченный, отказной и восстановительный исход. |
| CHK006 | `[x]` — S FR-002/SC-002 и M определяют паритет по смыслу, маршрутам, состояниям и доступности, не одинаковый toolkit. |
| CHK007 | `[x]` — S FR-003/005 и B §§1, 6 задают точный origin/route и redirect/auth/external-navigation policy. |
| CHK008 | `[x]` — S FR-010–017, C §6 и v5 manifest contract определяют normal, trusted prefix, degraded и protected-audio result. |
| CHK009 | `[x]` — S FR-009/018, SC-001/003; D §§4–5 и B §3 содержат frame/gap/clock и bridge limits (64 KiB/depth 8). |
| CHK010 | `[x]` — S FR-004/007–010 и C §2 прямо устанавливают prerequisites и состояния отказа для Record. |
| CHK011 | `[x]` — S FR-007–010 согласованы с C §§2, 4–6 и D §§3–5 по источникам, AEC3, framing, bounded queues и отказам. |
| CHK012 | `[x]` — S FR-011–014, D §§6–7 и C §7 используют v5 roles/server truth и совместимый v3 ledger с v2 reader/историческим именем файла. |
| CHK013 | `[x]` — S FR-004–006, B §§3–5 и C §§1–3, 7 оставляют bridge типизированным, capture native и не считают сообщения proof. |
| CHK014 | `[x]` — S FR-016, User Story 5; D §9 и K II сохраняют verified identity, opt-in policy, prompt/countdown, indicator и Stop. |
| CHK015 | `[x]` — S «Out of Scope», FR-007/019, R «Rejected alternatives» и P §Architecture исключают driver, process loopback и отдельный Windows cabinet. |
| CHK016 | `[x]` — S «Edge Cases» и C §§2, 6–7 задают разные безопасные исходы и recovery для WebView, сети, auth, endpoints и storage. |
| CHK017 | `[x]` — S FR-017; C §§3, 5–6 определяют trusted-prefix и запрет normal package при sleep/route/clock/overflow failures. |
| CHK018 | `[x]` — S Edge Cases/Assumptions, C §2 и Q §1 устанавливают Windows N/AAC readiness и границы поддержки. |
| CHK019 | `[x]` — S «Assumptions»/«Legacy Impact» назначает существующие cabinet/API/v5/deletion contracts источниками истины и ограничивает пересмотр. |
| CHK020 | `[x]` — S FR-012/021, C §9 и Q §1 задают запреты на private/content-bearing evidence. |
| CHK021 | `[x]` — S FR/SC, C, D, B и F277 дают измеримые условия и наблюдаемые результаты для слов normal/parity/recovery/security; непроверенная реализация не подменяет их. |
| CHK022 | `[x]` — S «Assumptions» и P/ T Phases 15–16 отделяют общие F277/shared-resource изменения от Windows-only native slice и задают последовательность интеграции. |

### `security.md` — 27/27 `[x]`

| Пункт | Итог и evidence требований |
| --- | --- |
| CHK001 | `[x]` — B §1 задаёт нормализованные HTTPS origin/route; S FR-005 запрещает substring allowlisting и произвольную навигацию. |
| CHK002 | `[x]` — B §§1, 5 и S FR-005/006 перечисляют допустимые route kinds и отдельные native-only/unknown outcomes. |
| CHK003 | `[x]` — B §§1, 6 покрывает redirects, frames, local/file schemes, loopback и внешний handoff. |
| CHK004 | `[x]` — S FR-020/Edge Cases и C §2 отделяют WebView runtime failure от audio readiness и local custody. |
| CHK005 | `[x]` — B §2 задаёт `AreHostObjectsAllowed=false`, no COM host objects, bounded capabilities и standard user. |
| CHK006 | `[x]` — S FR-006/Key Entities, B §§3–4 и D §8 явно разделяют web request envelope, `native_ready` и display-only `local_recordings`. |
| CHK007 | `[x]` — B §§3, 6 задаёт origin/source, nonce/document boundary, message id, payload size/depth и rejection conditions. |
| CHK008 | `[x]` — S FR-006, B §§3–6, F277 «Мост и настройки», C §§3/7 и T Phases 15–16 задают ровно шесть запросов, точные payload/route/state gates и retired aliases. |
| CHK009 | `[x]` — B §§4, 8–9, D §8 и F277 §1 ограничивают replies/display rows и отказывают stale/replay/version mismatch без полномочий. |
| CHK010 | `[x]` — B §§4–5/8, D §§7–8, C §7 и S Key Entities прямо исключают ack как proof; local purge и server deletion truth разведены. |
| CHK011 | `[x]` — B §6 инвалидирует nonce/bridge на navigation/auth/recreate и оставляет native session независимой. |
| CHK012 | `[x]` — S FR-012, C §7 и Q §6 определяют user-scoped directory, ACL, atomic write, flush и error bounds. |
| CHK013 | `[x]` — S FR-013, D §7 и C §7 задают ledger atomicity, quarantine и recoverable backup вместо пустой очереди. |
| CHK014 | `[x]` — S FR-014, C §7 и PG «Server, Storage, And AI Boundaries» ограничивают egress существующими GRAF API и исключают provider credentials/direct upload. |
| CHK015 | `[x]` — S FR-022, C §7, B §8 и PG «Deletion Truth» требуют доказанного локального purge и не выводят server erasure из local state. |
| CHK016 | `[x]` — S SC-008/FR-020, P Phase 6 и Q §8 перечисляют preservation/update/rollback/uninstall evidence и запрет неявной очистки. |
| CHK017 | `[x]` — S FR-021, C §9 и product-gates §Audio, Artifacts, And Diagnostics перечисляют safe fields и запреты, включая paths/process command lines. |
| CHK018 | `[x]` — S Repository Hygiene/FR-021, C §9 и Q §1 исключают audio, transcripts, tokens, cookies, URLs и private paths/content. |
| CHK019 | `[x]` — R «Решение 1», P Phase 0 и source/build notes определяют pinned AEC3 revision, C ABI, identity, notices и build evidence. |
| CHK020 | `[x]` — S FR-020/SC-008, P Phase 6 и Q §8 перечисляют signature, architecture, dependencies, runtime and rollback gates. |
| CHK021 | `[x]` — S FR-019, C §§2/4 и P Technical Context запрещают elevation, driver, service и privileged audio component. |
| CHK022 | `[x]` — B §7 enumerates hostile origin, stale nonce, malformed/deep/oversized payload, redirects, close/recreate and missing runtime cases. |
| CHK023 | `[x]` — C §7 defines spaces→`/auth/me` schema, UUID/type/duplicate/size limits, same session, cancellation/generation and no deletion authority. |
| CHK024 | `[x]` — S FR-004/Context, K Principle II and C §2 consistently exclude participant notice/legal consent from app readiness without synthetic permission. |
| CHK025 | `[x]` — S FR-004/Context; C §§2–3/6–7 preserve technical prerequisites, ownership/auth and deletion proof separately from legal-policy gates. |
| CHK026 | `[x]` — S User Story 5/AC7–9, P Phase 5 and D §9 separate stable `target_key` preference from exact verified identity and preserve approved-version behavior. |
| CHK027 | `[x]` — S User Story 5/AC8–9, D §9, R «Постоянные настройки…» and Q «Постоянные ключи…» specify V2 defaults, no V1/global migration, write failure and return behavior. |

### `ux.md` — 25/25 `[x]`

| Пункт | Итог и evidence требований |
| --- | --- |
| CHK001 | `[x]` — M route/state matrix and S FR-002/SC-002 compare capture, permission, custody and cabinet meaning with allowed Windows conventions. |
| CHK002 | `[x]` — S FR-003, P WebView ownership and M keep cabinet business UI shared and native capture controls separate. |
| CHK003 | `[x]` — S «Контекст и цель»/FR-007 and C §4 disclose global shared render mix, not app-isolated capture. |
| CHK004 | `[x]` — C §§3, 6 and S Edge Cases give states, user-facing reason and recovery/action transitions. |
| CHK005 | `[x]` — S FR-015, C §8 and M require persistent native status/scope/Stop independent of WebView/focus/minimize/network. |
| CHK006 | `[x]` — C §§3, 8, S FR-015 and M specify tray/background status, one Stop and idempotent finish. |
| CHK007 | `[x]` — C §8 derives indicator only from native session and protects it from DOM/navigation failure. |
| CHK008 | `[x]` — C §3 defines pause timeline/reference and forbids raw-mic fallback or wall-clock padding. |
| CHK009 | `[x]` — S Edge Cases/FR-017/020, C §6 and D §10 provide distinct bounded reasons and recovery paths. |
| CHK010 | `[x]` — S User Story 5/AC and FR-016, D §9, R §8, K II define eight-second visible prompt, explicit choices, remember behavior and timeout. |
| CHK011 | `[x]` — S FR-016, D §9 and R §8 specify verified apps, exactly three reversible modes, Ask defaults and shared product key. |
| CHK012 | `[x]` — S FR-016/SC-007, D §9, R §8 and K II enumerate disallowed start cases and distinguish timeout from a blocked start. |
| CHK013 | `[x]` — S clarification/FR-016, R §8 and K II establish client-owned preferences, no legal/server gate and preserve authorized manual Record. |
| CHK014 | `[x]` — S SC-009 and Q §7 require keyboard focus/flows on shell, prompt, tray and recovery controls. |
| CHK015 | `[x]` — C §8 and S SC-009 specify accessible names/descriptions and state announcements for indicator and custody outcomes. |
| CHK016 | `[x]` — S SC-009, F277 «Вид, доступность и экран», and Q §§7/11 define contrast, DPI, narrow layout, reduced motion and overflow outcomes. |
| CHK017 | `[x]` — S SC-009 and C §8 require text/shape/accessibility distinction, not color alone. |
| CHK018 | `[x]` — S FR-002/021, M and PG «UX Reference Fidelity» constrain language, truthful capture scope and secret disclosure. |
| CHK019 | `[x]` — S User Stories 1–3/Edge Cases, C §2 and B §§1, 6 define offline/auth/runtime/upload states with contextual recovery. |
| CHK020 | `[x]` — S final goal/Clarifications, P final parity section, K Principle VII, PG «UX Reference Fidelity», M and F277 give a current Mac reference, scoped OS deviations, accessibility/provenance gates and no brand-distance requirement. |
| CHK021 | `[x]` — S Edge Cases and C §3 specify close/quit/finalization/preserved local package and Stop/custody status. |
| CHK022 | `[x]` — S FR-004/015, C §§1, 3, 8 and M keep Stop, permission recovery and custody native. |
| CHK023 | `[x]` — S compatibility clarification, D §9 and Constitution II explicitly bound legacy auto-record fields and fallback defaults. |
| CHK024 | `[x]` — S US5/AC4–6 and P Phase 5 require foreground-independent readiness, indicator preparation/show-before-capture and fail-closed visibility. |
| CHK025 | `[x]` — S US5/AC5–6, P Phase 5, C §4, D §9 and Q §2 define accepted `starting`, exact identity, 2/15/600-second thresholds and stale/repeated-snapshot behavior. |



## Открытые требования реализации и причины

Независимый подсчёт tasks.md: **113 задач, 91 отмечена, 22 открыты**.
Число 112 из checklist относится к требованиям качества, не к задачам.
Точный перечень открытых задач: T071, T083, T063, T087, T088, T094, T095, T096, T097, T101, T102, T103, T104, T105, T106, T107, T108, T109, T110, T111, T112, T113.

| Открытая область | Причина, почему этот review её не закрывает |
| --- | --- |
| T094/T095 | Clock/frame/model и downstream поведение требуют согласованного design и реальной приёмки; Phase 0 открыта. |
| T096 | Product fix ещё не принят; обязательны regression и review текущего worker, а также остальная fault/EOS/sink матрица задачи. |
| RQ30-H1 / FR-012 protected storage | Унаследованное шифрование не выполнено одним ACL; полный защищённый поток, формат/authority/migration/resources/playback остаются заблокированным design. Не создаётся дублирующая задача в этом review. |
| T063/T071 | Полный quickstart/SC-003 и физическая Windows x64 hardware evidence отсутствуют; VM/portable pass их не заменяет. |
| T083/T087/T088 | Auth/upload/deletion/preservation и фактические custody/server proofs не доказаны этой проверкой требований. |
| T097/T101 | Полная интерактивная приёмка и installed real pinned AEC3/signed-package readiness не проверяются чтением checklist или disposable allocation probe. |
| T102–T113 | Payment/auth/reminders/UX/tray/update/F277-final-start parity остаются отдельной текущей product/native/shared задачей; allocation repair не служит evidence этих сценариев. |
| Release / commits / main analyze | Нет нового exact-SHA CI/PR/approval/release proof. Ни публикации, ни коммита, ни снятия этих gates этим отчётом не разрешено. |

Отдельно готовящийся main disposable MMCSS metadata candidate находится вне
этого gate. Он не изменяет clock model и не является audio/SC-003 acceptance;
этот review не подтверждает его запуск, результат или причинность clock_drift.

## Отпечатки проверенного снимка и контроль сохранности

SHA-256 перед созданием нового отчёта. Все ранее существовавшие checklist/report
и перечисленные core/source файлы должны оставаться побайтно такими же после
единственного reviewer-write; параллельные чужие изменения не откатываются.

| Файл | SHA-256 |
| --- | --- |
| `checklists/advanced-routing.md` | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| `checklists/analyze-2026-09-27.md` | `eba3e7b7d85e000ab2ba6f38cca3719b57c55dabebd217ae3467dc5c7e7d5105` |
| `checklists/analyze-2026-09-28.md` | `59b369289c8c12069050159229597295365b62a816438cf74dbc83f6f3e2844a` |
| `checklists/audio-capture.md` | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| `checklists/requirements.md` | `ed65406d9f400a5ccb6510f40630462206e7afe86d9c9743e75f0d027b2d826a` |
| `checklists/review-2026-09-26.md` | `73959e8e75d4b08bf68b2910c52edcdfc7a8adae58f70f59ec9a316b7bbe88c6` |
| `checklists/review-2026-09-27.md` | `1a71d065b80a566098f924cdf193bfa63c65cfc2e3b847fdd6efb7af39e937a9` |
| `checklists/review-2026-09-28.md` | `3ec0c88cf72b2e99ef9cdc754dae9ac92f1d03d81dcb874db0d728554f60b0bd` |
| `checklists/review-2026-09-30.md` | `19014b7dd4f02808f8cec36a179861f7f2a337f8ebfdf0304d3ef34e656862af` |
| `checklists/security.md` | `e7aeddb5c3469a46063d3897dd6f77969c8e1fd07b3fc43b2d37936b92195612` |
| `checklists/ux.md` | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| `spec.md` | `9f7e0d9ca96c6be1209af723e5fad0745a9b78cf8314f2b2996d6697de5c20b2` |
| `plan.md` | `a3ce12af9b86649e23907c60dd7dbd3e46f55b9c839baf6703f7dd7eeb6070a1` |
| `tasks.md` | `0debc42565eee06752e6fdaabd3288d07102dae6c4ee50546bcb9347f09c0700` |
| `research.md` | `fc02f754960fcf652fbb9e1a113031d1dde394443dff7ed32ce36067a0c3798c` |
| `data-model.md` | `54021e4e2713606c35fcc24a6df69f2706d0bcdbdf75a501bf435b6df3c3a41e` |
| `quickstart.md` | `e406992de33841821a63cee727f60b5fbe7df5e7364b9b6180ce3b0d66c9b247` |
| `parity-matrix.md` | `53920e7cb15aca2e7087a7c4bf23963c21b08d7530c0876d3576838627787669` |
| `contracts/windows-desktop-contract.md` | `8aaedaa990154a801e6b6c73ba35e304df26bc8b383a0dae35c5929617812135` |
| `contracts/windows-native-web-bridge.md` | `b8425859dc3a2d034a7be8767880bb6c86ada639431eccd9403d9c1910c55b95` |
| `contracts/f277-notifications-parity.md` | `e6e4e3048ad53d078cb80dccd3a34c9fe967a04ac65558141a834dc11fb6b7ca` |
| `apps/windows/RecApp/Audio/WasapiCaptureWorker.cpp` | `09572c0a60c7234ad9dfb224b85565da06dff1390f18c7a0bee032d543e48c7e` |

Контроль после записи выполнен: исходные marker counts повторно прочитаны —
112 checked, 0 unchecked; в отчёте 112 поэлементных строк evidence и 0 новых
checkbox markers. Все 22 перечисленных прежних файла совпали с исходными
SHA-256, включая пять checklist, шесть исторических checklist/report и worker.
HEAD остался a9691d4d474d918f54493d55a3aba286c749b513; git diff --check для
checklists не сообщил ошибок. Git index рецензент не менял. Новый отчёт —
единственный reviewer-write; повторной проверки готовности приложения нет.

## Узкий post-implementation code review — 2026-10-01

**APPROVED NARROW — T096 allocation-before-ReleaseBuffer repair.**
Блокирующих замечаний к фактическому resize catch, перемещению release callable
и четырём новым allocation-fault случаям не выявлено. Это отдельный code review,
не повторная проверка 112 требований и не закрытие всей T096/#7239.

Применён code-reviewer: прочитаны текущий WasapiCaptureWorker.cpp целиком,
новый блок CaptureFaultStateTests.cpp и его allocator/TestPeer/lifecycle
окружение; сопоставлены AudioTypes, ClockMapper, AudioNormalizer и CMake flags.
Обзор ограничен данным repair. Предшествующие изменения Stop, автозаписи и
другие dirty изменения не включены в это одобрение как новый общий diff.
Продуктовый код, тесты, tasks и checklist markers рецензент не менял.

### Проверенные свойства кода

| Область | Фактическое основание и вывод |
| --- | --- |
| Освобождение при resize failure | WasapiCaptureWorker.cpp:356–362: catch устанавливает normalizationFailed, вызывает существующий checked release ровно один раз и возвращает false. Копирование данных, normalize и callback недостижимы из этой ветки. Нет повторного release в destructor/outer catch. |
| Приоритет release/Stop | Worker:316–323: отрицательный результат release устанавливает releaseFailed после allocation reason. catch не перебрасывает исключение и не затирает причину. Native loop выходит через break к completeNativeStop; существующий compare_exchange none→stopFailed не заменяет более ранний normalizationFailed/releaseFailed. |
| До consumePacket нет нового allocating callable | Worker:218–222: std::function releasePacket построена до Start и любого GetBuffer. Она живёт до выхода из capture loop; capture ComPtr живёт дольше, захват по ссылке корректен. Worker:282–285 передаёт const reference, не копию std::function; создание ClockObservation — числовой aggregate. Возможный bad_alloc при создании callable теперь происходит без acquired packet. |
| Acquired-packet call-site boundary | Worker:253–285: между успешным GetBuffer и consumePacket остаются числовые переменные/ветви, HRESULT GetPosition, bounded noexcept recordTrace и передача уже построенной function. Zero-packet путь сохраняет собственный checked release. Нет нового std::function construction, string/vector copy или растущей контейнерной операции на этом участке. Это снимает call-site reservation предыдущего requirements review для рассматриваемого repair. |
| Внутри consumePacket до resize | ClockMapper::observe в прочитанном исходнике выполняет числовые проверки/арифметику, не выделяет память. AudioBatch использует scalars и default vector<float>; нужное 480-float выделение выполняется resize под catch. Обычные ранние failure/startup paths не изменены. |
| Минимальность | У allocation repair только catch вокруг существующего resize и предварительное создание прежнего native release callable вместо временного в call expression. Повторно используется нынешний release helper; нет нового API, enum, зависимости, clock/storage модели, fallback, owner framework или общей RAII-надстройки. |

### Четыре real-worker regression случая и allocator/MSVC границы

- CaptureFaultStateTests.cpp:686–723 перебирает render/microphone × release
  success/failure. Существующий device body test seam заменяет только acquisition;
  настоящий worker thread, consumePacket, error и completion fence сохранены.
- Scalar operator new/delete в test executable (строки 23–33) заменены согласованной
  malloc/free парой; для size 0 выделяется хотя бы один byte, при неудаче выдаётся
  bad_alloc. Есть unsized и sized scalar delete; это допустимая C++17 replacement
  граница для рассматриваемого обычного vector<float>, не allocator продукта.
  Флаг thread_local: другие потоки не получают injection, heap не истощается.
- Target — ровно 480*sizeof(float), один раз. Флаг сброшен **до** throw.
  Release std::function и mapper созданы до включения флага; до resize в
  рассматриваемом shared path нет другой 1920-byte allocation. Проверка
  !failSampleAllocation исключает ложный pass без потребления injection.
- reinterpret_cast<const void*>(1) — намеренно непригодный адрес, не данные
  настоящего аудио. Catch должен сработать до доступа к нему. Он не служит
  тестом перехвата access violation/SEH; /EHsc не обещает такой перехват.
- Assert проверяет count=480, release до Stop, ровно одну попытку, точный HRESULT
  и released flag, только release trace до Stop, false/no callback/no ready,
  sticky normalizationFailed либо releaseFailed после Stop. Повторный normalize
  с тем же QPC и offset=0 после worker.finished() подтверждает, что normalizer
  не был инициализирован/продвинут. finished release/acquire fence делает чтение
  worker-thread counters/normalizer из проверяющего потока упорядоченным.
- MSVC /W4 /WX /EHsc и C++17 видны в CMake. Замена scalar new и обеих scalar
  delete не требует новой production зависимости. Array, aligned и nothrow
  allocation families этим test hook не объявлены покрытыми; для обычного float
  sample buffer они не являются целевым сценарием. Возможные debug-iterator
  auxiliary allocations и поведение конкретной STL/toolchain не подменяются
  Mac результатом: Windows compile/link/run остаётся обязательной отдельной
  проверкой. One-shot 480-float test — не доказательство устойчивости при
  произвольном global OOM/SEH или при исключении произвольного injected release
  callback. Native release callable использует HRESULT API, не пользовательский
  throwing callback. В узком diff подтверждённой MSVC-ошибки не найдено.

### Доказательства и незакрытые gates

Сообщение main: исходный CTest RED exit8 на assert releases==1, после resize catch
GREEN 1/1, финальный Mac CTest 32/32 PASS после перемещения callable. Это
предоставленные результаты, рецензент их не запускал и не объявляет собственной
независимой runtime валидацией. Новые записи/hashes main добавляет в validation.
**Windows build на момент review выполняется; Windows PASS не заявляется.**
git diff --check двух обозреваемых файлов не сообщил ошибок.

Отпечатки фактически прочитанного post-implementation снимка:

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Audio/WasapiCaptureWorker.cpp | 80b06e4b04845608cb70379bdb2ac5026f8d81e0a9a3845756b478de5a9f83a6 |
| apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp | 9b957d67a9d660623aa5e695489f5915c6862fc29676c99eeba790134270ca0c |

Прежние хеши выше относятся к pre-implementation requirements review, не к
этому более позднему worker. Одобрение привязано к новым двум отпечаткам.
§5/routing/clock/storage не ослаблены; Phase 0/Phase 1 новой модели, SC-003,
остальная T096, аппаратная/product acceptance, Windows validation, exact-SHA
CI и commit/release approvals остаются открытыми. Marker totals не пересматривались.
