# Независимый preflight T097: паритет интерфейса F200 — 2026-10-01

## Итоговый gate

**PASS — только requirements-quality gate существующей T097/FR-parity:
read-only UI/code verification и минимальные исправления подтверждённых
расхождений существующего интерфейса.** Невыполненных критериев качества
требований для этого узкого среза не выявлено. Все 112 существующих отметок
сохраняются без редактирования.

Это не одобрение ещё неизвестного code/test diff, не разрешение обходить
последовательность задач, не PASS UI-тестов, не закрытие T097/#7240, не
приёмка установленного приложения и не готовность F200 к выпуску.
Main обязан закончить причинный разбор каждого найденного дефекта, текущий
узкий analyze, проверку принадлежности существующей задаче и последующий
code review/validation. Чеклисты не заменяют эти этапы.

**Phase0/Phase1 новой clock/protected-storage модели остаются NOT READY.**
Никакой waiver, новая модель, порог, storage-format, миграция или
routing-изменение этим PASS не разрешены. Действующий §5 и SC-003 неизменны.

Дата текущего review: 2026-10-01. Только canonical worktree
/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp,
ветка codex/200-windows-followup, HEAD
a9691d4d474d918f54493d55a3aba286c749b513.
Осмотрен текущий dirty снимок; HEAD не является SHA незакоммиченного diff
или свежим package/PR proof. Незакоммиченная работа других участников сохранена.

## Текущие инструкции и источники

Активная F200 определена по .specify/feature.json и текущему
check-prerequisites.sh --json --paths-only. Применены текущие локальные
speckit-implement и speckit-checklist: обязательный независимый reviewer gate
и семантика checklist как проверки полноты/ясности/измеримости/согласованности
требований, не runtime proof. Risk lane продукта high-risk-product сохраняется;
единственное изменение рецензента — docs-only отчёт без запуска продукта.

Заново прочитаны AGENTS.md, guidance README, spec-kit-flow, codex-worktrees,
product-gates, tracker-policy, local-development, применимые review/validation
разделы release-and-validation; конституция 7.1.0, current spec/plan/tasks,
quickstart и все пять активных checklist с примечаниями. Для каждого критерия
сверены текущие desktop/native-web/F277 contracts, data-model, relevant research,
parity-matrix, clarify и ux-evidence. Product baseline/current-product-status
прочитаны в относящихся к native/web, privacy, UI reference и acceptance границах.
Предыдущие checklist/report — исторический контекст, не новое подтверждение.
Текущий review-2026-10-01-release-custody.md перечитан целиком, включая
post-implementation раздел; он не переписывается и не расширяется на другой diff.

Новый round126 перечитан в текущих research/plan/validation: compiled
continuous-ratio waveform oracle на pinned dependency — исследование при известных
часах, не выбранный causal estimator/uncertainty/slew/start/partial-EOS contract
и не audio acceptance. Изменившиеся plan/research проверены заново, а не
автоматически приняты из предыдущего отчёта.

Никакие VM, UI, microphone, capture, app, build, product tests, сеть/GitHub,
Git index, commits или пользовательские данные рецензентом не запускались
и не менялись. UI/mic принадлежат main. Mac locked по текущему сообщению
main: ждём разблокирования владельцем, без обхода. Для последующей Mac-проверки
действует current local-development: только /Applications/GRAF Dev.app и
существующий dev-harness, сохранение bundle/signing/TCC identity, никаких
GRAF Local/Preview/Test.app, swift run или обходов failed harness.

## Разделение T097 и открытой Phase0 без снятия gates

| Область | Решение и текущее основание |
| --- | --- |
| Проверить существующие меню/маршруты/тексты/темы/комбобоксы/фокус/доступность и исправить доказанный дефект размещения или представления | PASS по требованиям узкого T097. S FR-002/003/015 и SC-002/009, T097, P native/web ownership + final parity и M дают уже существующую цель. Layout/DOM presentation и native UI не требуют выбора нового clock estimator или encrypted stream format. |
| Сохранить общий кабинет и обе платформы | Обязательно: P Phase3/4/final parity, B §§1–6/9, Q §11, K VII и PG reference-fidelity. Нет отдельного Windows кабинета; shared-resource fix требует проверок Mac/Windows и Chromium/WebKit. Не изменять пользовательский текст заменой всего DOM или ослаблением trust boundary. |
| Исправить отображение времени существующей строки через действующий presentation API | Допустимо исследовать и подтвердить в T097/FR-parity. Изменение часового пояса отображения не является WASAPI/QPC clock model. Нужны регрессии реального API и фактического перерисованного результата; изменение audio PTS, capture clocks/thresholds или простое ослабление assertion недопустимо. Точный будущий diff пока не принят. |
| Новая согласованная clock модель, resampler integration, estimator/slew/noise/start/EOS, новые thresholds | NOT READY. P «Открытая Phase0…», R round122–126: ключевые quantitative решения не завершены. Waveform oracle, metadata scheduling и custody repair не дают такого допуска. C §5/S FR-009/010/018/SC-003 сохраняются. |
| Новый protected local stream, file format, ownership/authority, playback, migration | NOT READY. S FR-012, PRD encrypted buffers, P/R RQ30-H1 требуют защиты полного потока и design/integration/validation. ACL, EFS, encrypted manifest или UI-фраза не заменяют это. |
| Сделать Record доступным ради UI-проверки или назвать состояние ready/normal без проверки | Запрещено. C §§2–6/8, S FR-004/015/017, T101/T113: readiness, pinned AEC3, обе обязательные sources, окончательный допуск, visible indicator/Stop, Stop/finalizer fences сохраняются. Показать реальную blocked/degraded причину можно; снять её нельзя. |
| Признать завершённой T097 или общий паритет | NOT ACCEPTED. Нужен свежий installed package/EXE/source/server reference, обе платформы, одинаковые состояния и действующие сценарии. Browser/component pass не заменяет Windows native/Mac interactive proof. |

Фраза плана «перед реализацией… Phase1 и общий gate не закрываются»
относится к двум непосредственно названным незавершённым решениям — новой
clock и protected-storage архитектуре. Это не запрет читать существующий UI
или ремонтировать его подтверждённое представление без изменения модели.
Но возможность такого отделения не делает общий архитектурный gate PASS.

T Phase15 отдельно требует «сначала T101»; T104 — после T109; T108–T113 имеют
собственных владельцев. Этот отчёт порядок не отменяет и их работу в T097
не переименовывает. Main должен сохранить его в текущем analyze/планировании.
Read-only наблюдение интерфейса само по себе не внедряет эти задачи и не
утверждает готовность записи/пакета. При исправлении действительного capture,
storage, lifecycle, settings-protocol или auth дефекта нужна применимая
существующая задача, её зависимости и отдельный gate, а не blanket T097 PASS.

### Текущий эталон вместо исторического read-only обхода

S/P и нормативный F277 contract задают выбранный пользователем Mac-срез
51bcff6b1abfdf2a01d59a7d3f00c831674c365c от 28 сентября. M дополнения и
B §9 прямо заменяют старый notification v1/системный канал/ранние окна.

T097 «отсутствие обеих неработающих кнопок» проверяет отсутствие обещаний
несуществующего действия. Это не разрешение скрыть уже реализованное F277
действие, вернуть read-only как окончательный паритет, убрать preview/quiet
или восстановить permission/openSystemSettings и OS toast из старых задач.
Для текущего notification v2 обязательны соответствующие read/set/test,
понятный отказ v1, реальный preview без capture/server effects, scope/nonce/
request/document gates и ошибка save вместо ложного успеха. T104/T105
остаются владельцами функциональности; T097 проверяет её актуальный UI.

## Свежие результаты main и непроверенные acceptance условия

Следующие результаты предоставлены main в текущем сообщении. Рецензент
их не запускал; нет собственного browser/VM runtime proof или проверки
свежего test-source hash/полного output. Они не перенесены на установленный MSIX:

| Набор | Предоставленный результат | Граница утверждения |
| --- | --- | --- |
| Profile menu | 33/33 Chromium + WebKit PASS | Компонентная проверка, не весь T097 или native меню. |
| Platform-copy | 29/29 PASS | Не освобождает от сохранения пользовательских строк и Mac regression. |
| Settings consistency | 224 PASS | Не доказывает installed native settings/миграцию/права или actual audio readiness. |
| Comboboxes | Оба набора PASS | Детальный denominator и exact-source receipt должны остаться в validation main. |
| Notification contract | 37 PASS | Не доказывает фактический показ, звук, фокус, preview, сохранение на установленном клиенте. |
| local-recording-focus.test.cjs:96 | FAIL: actual03:30, expected05:30 | Не снят. Причина и будущая правка ещё проверяются main; нет разрешения считать набор PASS. |
| timezone-settings.test.cjs | PASS, synthetic HTTP autosave422 recovery/setTimezone | Сообщение main; не собственный прогон рецензента и не полный installed UI proof. |
| user-time.test.cjs:19 | FAIL: expected02:30, actual00:30 | По trace main helper deviceZone=undefined пропускает OS Intl timezone Europe/Istanbul. Набор остаётся FAIL до принятой правки и повторного прогона. |

По исследованию main, тест меняет только meta graf-timezone и повторно
подключает user-time.js; meta теперь server-zone fallback, действующий выбор —
explicit graf-time-preferred либо OS device. Main указывает публичный
GRAFTime.setTimezone и реальное использование settings-autosave.js;
normalized row учитывает все отображаемые поля. Это текущая рабочая гипотеза,
не завершённый независимый code review изменения и не доказательство
отсутствия продуктового дефекта.

Для принятия соответствующей регрессии main должен подтвердить актуальный
source trace и проверить смену зоны через действующий API, фактическое
обновление отображаемых дат/времени и сохранение требуемого focus/selection
существующей строки, включая повторное обновление. Нужно различить выбранную,
device и server fallback зоны; одна замена expected time или исключение поля
из сравнения не доказывает контракт. До этого FAIL остаётся открытым, и
возможный test-only patch не одобрен этим requirements review.

Дополнительный read-only trace main уточняет минимальное предложение: helper
run получает явную default deviceZone=Asia/Yekaterinburg; browser page теста
локальной строки создаётся с timezoneId=UTC, затем вызывается существующий
GRAFTime.setTimezone('Asia/Yekaterinburg') вместо изменения fallback meta и
повторного script injection; добавляется проверка сохранения identity/focus.
Все прежние assertions сохраняются, production JS/backend не меняются.
Это согласуется с требованиями детерминированной регрессии существующего UI:
явная зона среды + пользовательский API выбора исключают случайную зависимость
от timezone workstation. Это не новая capture clock/storage model и не waiver.
Requirements preflight разрешает продолжить такое узкое test-only исправление
после source trace/analyze; фактический patch ещё не прочитан/не одобрен,
повторные результаты и code review обязательны. Ошибки тестов не считать
устранёнными только по правдоподобию этого предложения.

| Открытая область | Причина / что этот PASS не закрывает |
| --- | --- |
| T097/#7240 | Свежая UI приёмка двух платформ отсутствует; Mac locked; два timezone regression FAIL имеют trace/proposed test-only repair main, но фактический diff/повторный прогон ещё не принят. |
| T094/T095 и новая clock Phase0 | Estimator/uncertainty/slew/start/partial-EOS contract не принят. Round126 — oracle, не integration gate. |
| RQ30-H1/FR-012 protected storage | Full protected stream/layout/authority/migration/resources/playback gates открыты. Пользовательские записи не мигрировать. |
| T096/#7239 | Предыдущий APPROVED NARROW относится только к двум hash-bound custody repair файлам; остальная fault/EOS/sink/capture матрица и вся задача не закрыты. |
| T063/T071 | SC-003/60-minute/resource/физический x64, полный quickstart, installed accessibility и clean-image/public distribution proof не получены этим review. |
| T083/T087/T088 | Auth/upload/deletion/local preservation/server truth E2E не доказаны чтением требований или UI browser tests. |
| T101 | Требования pinned backend/build/provenance/installed ready-capture обязательны. Записанный main build success не снимает оставшуюся часть и порядок задачи. |
| T102/T103/T106/T107 | Payment/auth/attribution/permanent rejection остаются своими открытыми задачами; нет нового network/API approval. |
| T104/T105/T108/T109/T110/T111/T112/T113 | Reminders/card/focus/tray/OS copy/update/final start реальные проверки и существующее ownership не поглощаются T097. |
| Analyze/code review/exact-SHA CI/commit/release | Этот reviewer preflight их не заменяет; необходимы текущий scoped analyze, focused validation и review будущего diff, applicable required GitHub checks и явные approvals. |

## Пересчёт исходных checklist и задач

Подсчитаны текущие исходные строки checklist «- [x/X/ ] CHK…», а не числа
в старом отчёте. Все 112 критериев ниже рассмотрены по отдельности на current
документах. Маркеры не изменялись; новых checkbox criteria не создавалось.

| Checklist | Всего | Checked | Unchecked |
| --- | ---: | ---: | ---: |
| advanced-routing.md | 14 | 14 | 0 |
| audio-capture.md | 24 | 24 | 0 |
| requirements.md | 22 | 22 | 0 |
| security.md | 27 | 27 | 0 |
| ux.md | 25 | 25 | 0 |
| Итого | 112 | 112 | 0 |

Reviewer-owned custom: 90 checked/0 unchecked. Built-in Specify
requirements.md: 22 checked/0 unchecked; не редактировался.
Неподтверждённых **requirements-quality** пунктов нет, причин для снятия
существующих отметок в этом срезе не выявлено. Runtime FAIL/blocked не
переименовывается в quality PASS и не скрывается: причины приведены выше.

security CHK012 проверяет scope/ACL/atomic/flush, не готовность нового
шифрования. audio CHK005/007/019 проверяют сформулированный действующий
clock/SC контракт, не выбранный estimator. ux CHK014–020 проверяют
измеримые accessibility/reference требования, не завершённую UI приёмку.
Ни один из этих [x] не снимает blocked design или failed runtime evidence.

Текущие tasks.md: 113 задач, 91 checked, 22 unchecked.
Открыты T071, T083, T063, T087, T088, T094, T095, T096, T097, T101,
T102, T103, T104, T105, T106, T107, T108, T109, T110, T111, T112, T113.
Это иной denominator, не 112 Spec Kit requirements-quality пунктов.
Причины соответствующих acceptance/design блокеров перечислены выше;
задачи/issue-map не редактировались. T097→#7240 взято из текущего локального
issue-map; текущий GitHub статус рецензент не запрашивал.

## Поэлементные результаты текущей проверки

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



Ни одна строка выше не является runtime proof. Основания сопоставлены заново с текущими документами; схема таблицы сохранена для сравнения с прошлым review.

## Проверенный снимок и контроль reviewer-write

Перед записью SHA-256 текущих checklist, spec/plan/tasks, источников и инструкций
повторно сопоставлены с началом этого review: изменений в перечисленных файлах
нет. Source hashes worker/fixture совпадают с post-implementation разделом
release-custody review; это не доказательство нового installed package.

| Файл | SHA-256 |
| --- | --- |
| `specs/200-windows-desktop-app/checklists/advanced-routing.md` | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| `specs/200-windows-desktop-app/checklists/analyze-2026-09-27.md` | `eba3e7b7d85e000ab2ba6f38cca3719b57c55dabebd217ae3467dc5c7e7d5105` |
| `specs/200-windows-desktop-app/checklists/analyze-2026-09-28.md` | `59b369289c8c12069050159229597295365b62a816438cf74dbc83f6f3e2844a` |
| `specs/200-windows-desktop-app/checklists/audio-capture.md` | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| `specs/200-windows-desktop-app/checklists/requirements.md` | `ed65406d9f400a5ccb6510f40630462206e7afe86d9c9743e75f0d027b2d826a` |
| `specs/200-windows-desktop-app/checklists/review-2026-09-26.md` | `73959e8e75d4b08bf68b2910c52edcdfc7a8adae58f70f59ec9a316b7bbe88c6` |
| `specs/200-windows-desktop-app/checklists/review-2026-09-27.md` | `1a71d065b80a566098f924cdf193bfa63c65cfc2e3b847fdd6efb7af39e937a9` |
| `specs/200-windows-desktop-app/checklists/review-2026-09-28.md` | `3ec0c88cf72b2e99ef9cdc754dae9ac92f1d03d81dcb874db0d728554f60b0bd` |
| `specs/200-windows-desktop-app/checklists/review-2026-09-30.md` | `19014b7dd4f02808f8cec36a179861f7f2a337f8ebfdf0304d3ef34e656862af` |
| `specs/200-windows-desktop-app/checklists/review-2026-10-01-release-custody.md` | `0ac73667fddb0f4d759d4f0157419396aec468602c9255fa2988988d47253fb1` |
| `specs/200-windows-desktop-app/checklists/security.md` | `e7aeddb5c3469a46063d3897dd6f77969c8e1fd07b3fc43b2d37936b92195612` |
| `specs/200-windows-desktop-app/checklists/ux.md` | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| `specs/200-windows-desktop-app/spec.md` | `9f7e0d9ca96c6be1209af723e5fad0745a9b78cf8314f2b2996d6697de5c20b2` |
| `specs/200-windows-desktop-app/plan.md` | `1f6f8767c643341ff6d6368bc5f5f12dcb2377138babd01379285d71702b0386` |
| `specs/200-windows-desktop-app/tasks.md` | `0debc42565eee06752e6fdaabd3288d07102dae6c4ee50546bcb9347f09c0700` |
| `specs/200-windows-desktop-app/research.md` | `eea11e88d9cd3156998a87512ac45b728d8f28e1f51e14dbac1a90d68e127faf` |
| `specs/200-windows-desktop-app/data-model.md` | `54021e4e2713606c35fcc24a6df69f2706d0bcdbdf75a501bf435b6df3c3a41e` |
| `specs/200-windows-desktop-app/quickstart.md` | `e406992de33841821a63cee727f60b5fbe7df5e7364b9b6180ce3b0d66c9b247` |
| `specs/200-windows-desktop-app/parity-matrix.md` | `53920e7cb15aca2e7087a7c4bf23963c21b08d7530c0876d3576838627787669` |
| `specs/200-windows-desktop-app/contracts/windows-desktop-contract.md` | `8aaedaa990154a801e6b6c73ba35e304df26bc8b383a0dae35c5929617812135` |
| `specs/200-windows-desktop-app/contracts/windows-native-web-bridge.md` | `b8425859dc3a2d034a7be8767880bb6c86ada639431eccd9403d9c1910c55b95` |
| `specs/200-windows-desktop-app/contracts/f277-notifications-parity.md` | `e6e4e3048ad53d078cb80dccd3a34c9fe967a04ac65558141a834dc11fb6b7ca` |
| `specs/200-windows-desktop-app/validation-2026-09-30.md` | `8c31ae86f0648972639923f75442bd06b464dd11102e2720d0f72071853f3aee` |
| `AGENTS.md` | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| `.specify/memory/constitution.md` | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| `docs/agent-guidance/spec-kit-flow.md` | `5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887` |
| `docs/agent-guidance/product-gates.md` | `e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097` |
| `docs/agent-guidance/local-development.md` | `bcfd042e80e61f2ca7bbc51d9f9b94aba911ab33cf6d7936eb86d28f4ce6add7` |
| `apps/windows/RecApp/Audio/WasapiCaptureWorker.cpp` | `80b06e4b04845608cb70379bdb2ac5026f8d81e0a9a3845756b478de5a9f83a6` |
| `apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp` | `9b957d67a9d660623aa5e695489f5915c6862fc29676c99eeba790134270ca0c` |
| `specs/200-windows-desktop-app/validation-2026-10-01.md` | `db827d7041790bd6fd04c7d96adc54f19a94e8ea155fe48e5a308b46f0e54cbf` |

Единственный разрешённый reviewer-write — этот новый
checklists/review-2026-10-01-ui-parity.md. Прежние отчёты, пять checklist,
spec/plan/tasks, product source/tests, Git index и commits не редактировались.
Сохранены все исходные dirty изменения. После записи повторно проверены
112 исходных checked/0 unchecked, 112 строк поэлементного evidence, 0 новых
checkbox criteria; все 31 перечисленный исходный SHA-256 совпали с состоянием
перед записью. Tasks повторно дали 113/91/22, HEAD остался указанным выше.
git diff --check для прежних checklist и отдельный --no-index --check нового
отчёта не сообщили whitespace ошибок. Продуктовые тесты не запускались.
Новый UI report не расширяет прежний allocation code approval и не заменяет
последующий code review фактического UI/test исправления.

## Узкий post-change code review четырёх тестов — 2026-10-01

**APPROVED NARROW — только фактический test-only diff четырёх файлов ниже.**
Блокирующих замечаний и предложений к исправлению не выявлено. Это не review
всей ветки, не одобрение production cabinet.js, удаления/auth/upload protocol,
новой clock/storage модели или закрытие T097/приёмки установленного UI.

Применены code-reviewer, frontend-code-review и ponytail-review. Прочитаны
оба time/focus теста целиком, текущие четыре diff (staged изменений этих файлов
нет), контекст двух однострочных spelling assertions и вызываемый production
flow. React/React Flow/Tailwind правила frontend checklist неприменимы к этому
CJS assert/Playwright diff; новых components/styles/state abstractions нет.
Lane остаётся existing F200 high-risk-product; это узкий test-only follow-up
после requirements gate, не снижение требований всего продукта. Повторного
112-point review не проводилось, исходные markers не редактировались.

### Причины и проверенная корректность

| Файл / строки текущего снимка | Основание и вывод |
| --- | --- |
| user-time.test.cjs:5,12–19 | Раньше deviceZone был undefined: mock DateTimeFormat передавал timeZone:undefined, поэтому вызов без options в production user-time.js:7 брал OS Intl timezone машины. Expected02:30 для21:30Z подразумевает UTC+05:00, а не Europe/Istanbul. Явный default Asia/Yekaterinburg исправляет test fixture, не Intl и не production. |
| user-time.test.cjs:19–47 | Все прежние assertions сохранены, включая02:30, naive ISO→UTC, date-only, отсутствие cookies/reload loop, explicit UTC/Kathmandu, spring/fall New York DST, preferred account zone, invalid zone и format override. Explicit options в mock по-прежнему перекрывают device default; зоны не сведены к единственному happy path. |
| local-recording-focus.test.cjs:9,94–97 | timezoneId:UTC задаёт детерминированную среду до загрузки JS. Старые meta mutation+reinject не задавали пользовательскую зону: user-time.js:6–7 предпочитает graf-time-preferred либо device; graf-timezone в61–92 — server fallback/cookie/reload negotiation. Реальный публичный setTimezone в49–51 меняет closure timezone и GRAFTime.timezone, затем hydrate. Expected05:30 для updatedAt00:30Z и02:30 для startedAt21:30Z сохранены. |
| settings-autosave.js:74–84,164–175 — только read-only context | Настоящий autosave после проверенного saved:true/actor/workspace/values публикует saved и вызывает GRAFTime.setTimezone(values.timezone). Новый тест использует этот же presentation API, не подменяет formatter и не выдаёт fallback meta за saved preference. HTTP autosave здесь не моделируется заново; его соседний test приведён только как предоставленное runtime evidence main. |
| local-recording-focus.test.cjs:82–99 / cabinet.js:259–269,315,394,776–794 | Предшествующий server handoff переносит selected identity local:local-a→server-a и удаляет local ключ. После возврата нового local-only snapshot нельзя предполагать его прежний checked. Явный check в92 — корректная подготовка нового selection через настоящее control/change→updateSelection, не ослабление проверки. Затем после timezone refresh проверяется сохранение true на новом checkbox. |
| local-recording-focus.test.cjs:98 / cabinet.js:155–163,237–252,375–390 | Изменение зоны меняет полный rendered markup даты/заголовка/accessible labels. Существующий render сравнивает row.outerHTML, при изменении делает replaceWith(row), после сортировки restoreLocalFocus выбирает соответствующий доступный control новой строки. Поэтому проверяется activeElement на соответствующем новом Open, а не недопустимое обещание старого DOM node через реальное изменение markup. |
| local-recording-focus.test.cjs:100–102 и59–71 | После изменённого render сохраняется ссылка на уже восстановленный control;20 одинаковых публикаций обязаны оставить именно тот же active DOM node. Исходные20-repeat проверки всех четырёх controls, row identity и0 MutationObserver moves остаются. Это различает необходимую замену при изменении представления и запрещённую повторную замену при одинаковом output. |
| mixed-meeting-list.test.cjs:145 | Единственная замена exact regex «аккаунт не подтверждён»→«аккаунт не подтвержден». В current cabinet.js:497 и HEAD cabinet.js:485 уже «подтвержден». Проверки recoveryRequired=true→текст и false→count0 сохранены, regex не расширен до е/ё и assertion не удалён. |
| recording-deletion-recovery.test.cjs:100 | Единственная замена exact regex «Попробуйте ещё раз»→«Попробуйте еще раз». Current cabinet.js:1605 и HEAD:1593 уже «еще». Полный текст, число1, точка и смысл отказа сохранены. Row count1, dialog remains open, Retry enabled, отсутствие ложного saved/pending/deleted и отсутствие server request offline, explicit reconnect retry и последующие сценарии не изменены. Одобряется совпадение exact UI copy, не correctness всего delete protocol. |

Production user-time.js/settings-autosave.js не имеют diff к HEAD.
cabinet.js содержит предшествующий отдельный dirty diff: он не включён в это
одобрение; два рассматриваемых литерала совпадают с HEAD. В четырёх actual
test diff нет production/backend изменения, изменённого времени ожидания,
удалённого assertion, tolerance regex, нового API/dependency или скрытого
capture/auth/deletion side effect. Проверка expected times не ослаблена.

### Минимальность и результаты main

Actual diff: local-recording-focus8 additions/3 deletions; остальные три
файла каждый1/1. Используются имеющиеся fixture, Playwright timezoneId,
публичный GRAFTime.setTimezone и assert. Новые focus/selection/20-repeat
assertions проверяют именно риски этого перехода; удалять их ради меньшего
diff не следует. Новая библиотека, helper framework или отдельный UI не нужны.

Main сообщил сегодня:
- RED обоих time/focus тестов до patch; затем user-time GREEN при TZ=UTC,
  Europe/Istanbul и America/New_York.
- Финальный local focus GREEN на обычном host и TZ=America/New_York после
  явного check-before-timezone; local handoff PASS.
- timezone-settings PASS на synthetic HTTP с422 recovery/реальным saved
  autosave→setTimezone. Это соседний неизменённый test, не пятый approved diff.
- mixed-meeting-list прежний spelling RED, теперь PASS до конца.
- recording-deletion-recovery прежний spelling RED, теперь exit0,
  S09 и S48 оба PASS.

Эти результаты предоставлены main; рецензент тесты/браузеры/VM не запускал,
полные runtime logs не проверял и собственный runtime PASS не заявляет.
Четыре предоставленных final test SHA-256 независимо совпали с текущими
прочитанными файлами. Поздние GREEN supersede ранние FAIL как сведения main
для этого hash-bound test patch, но не превращают весь T097 в ACCEPTED.
Round127 docs main готовит отдельно. CUA/Mac LOCKED, новой microphone/UI
приёмки нет; пользовательские capture/privacy настройки не менялись.

### Отпечатки одобренного diff и прочитанного production context

| Файл | SHA-256 |
| --- | --- |
| apps/server/tests/browser/user-time.test.cjs | 49fa87eeea71c0c65fa7a8cbeb7f0455b1fb6085a49ca53677339f9b560d81fc |
| apps/server/tests/browser/local-recording-focus.test.cjs | 05a5054fef7330eeb06a63b48a21699cdd59b5b285de1ffc6c20cc21ec0e62f0 |
| apps/server/tests/browser/mixed-meeting-list.test.cjs | 9e55a80752cd91ee72a9818d1b9c7260fafb290abf4d2ad7b238a14897d74165 |
| apps/server/tests/browser/recording-deletion-recovery.test.cjs | c8bd22da7e8870da7ac57410ee73b4b6126b71228adc73a16305fca1cedce8cb |
| apps/server/src/twobrain_rec_server/cabinet/static/cabinet/user-time.js — context only | b8e835129cd11f8b08478a34a53aa8158b8c750e15e301706338e2a143cf004a |
| apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js — context only | 469f3aad79f962a1140f733de4a0dbc09b982ff8c91f6a037ca576d3766d5f49 |
| apps/server/src/twobrain_rec_server/cabinet/static/cabinet/settings-autosave.js — context only | 6175466793e87d2e8335b61f49d3e0af5126af41dd838a5a762bbe396355b17d |

Перед единственным reviewer append эти семь hashes повторно совпали;
git diff --check четырёх tests не сообщил ошибок. Тесты/code/tasks/spec/plan,
checklist markers, old report sections, Git index/GitHub/commits/VM рецензент
не менял. HEAD остаётся a9691d4d474d918f54493d55a3aba286c749b513;
approval относится к dirty test file hashes, а не всем изменениям HEAD/ветки.
§5/SC-003, новые clock/protected-storage Phase0/Phase1, installed UI/hardware,
полная T097, CI/commit/release approvals сохраняют прежние отдельные gates.

Ponytail-review оценивает только форму этого test diff, не разрешение выпуска:
Lean already. Ship.
