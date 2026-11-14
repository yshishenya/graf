# Финальное независимое ревью чеклистов: 295-capture-storage-gate

- **Дата**: 2026-11-14
- **Reviewer**: независимый read-only reviewer-агент (OpenCode subagent; модель DeepSeek V4.1 Flash 1017)
- **Фича**: `295-capture-storage-gate`
- **Тип проверки**: повторное независимое ревью reviewer-owned чеклистов после обновления `plan.md` и analysis-документа.
- **Разрешённые записи**: только `checklists/requirements.md`, `checklists/ux.md` и этот отчёт. Код, `spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, `validation.md`, analysis-документ, git и GitHub не изменялись.
- **Итог**: **PASS** — 27/27 пунктов подтверждены.

## 1. Контекст и границы проверки

Это ревью требований и проектных артефактов, а не приёмка реализованного поведения. На момент проверки:

- в `tasks.md` все T001–T017 остаются `[ ]`;
- `validation.md` содержит `pending` для локальных и release-проверок;
- новых файлов `LocalRecordingFootprint.swift` и `LocalRecordingFootprintProvider.swift` ещё нет.

Пункты отмечались только там, где `spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, analysis-документ и текущий код дают конкретное проверяемое основание. Будущая реализация сама по себе основанием не считалась.

Прочитаны:

- `specs/295-capture-storage-gate/spec.md`;
- `specs/295-capture-storage-gate/plan.md`;
- `specs/295-capture-storage-gate/tasks.md`;
- `specs/295-capture-storage-gate/quickstart.md`;
- `specs/295-capture-storage-gate/validation.md`;
- `specs/295-capture-storage-gate/analysis-server-library-local-cache.md`;
- `specs/295-capture-storage-gate/checklists/requirements.md`;
- `specs/295-capture-storage-gate/checklists/ux.md`;
- `specs/295-capture-storage-gate/checklists/review-2026-11-14.md`.

Дополнительно только для чтения проверен текущий код:

- `apps/macos/RecApp/Sources/Capture/RecordingPrerequisiteGate.swift`;
- `apps/macos/RecApp/Sources/Buffering/LocalBufferService.swift`;
- `apps/macos/RecApp/Sources/Capture/LocalRecordingStore.swift`;
- `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`;
- `apps/macos/Shared/Sources/Models/AudioModelCore.swift`;
- `apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift`;
- `apps/macos/Shared/Sources/Models/SystemAudioCaptureCoreModels.swift`;
- `apps/macos/RecApp/Sources/AppShell/ContentView.swift`;
- `apps/macos/RecApp/Sources/Calendar/CalendarTray.swift`;
- `apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift`;
- релевантные тесты `RecordingPrerequisiteGateTests.swift`, `MeetingDetectionPolicyTests.swift`, `DesktopCalendarReminderTests.swift`, `CaptureIndicatorTests.swift`, `AppControlAccessibilityTests.swift`.

## 2. Итоговые totals

| Чеклист | Всего | Checked | Unchecked | Открытые пункты |
|---|---:|---:|---:|---|
| `requirements.md` | 15 | 15 | 0 | нет |
| `ux.md` | 12 | 12 | 0 | нет |
| **Итого** | **27** | **27** | **0** | **нет** |

## 3. Закрытие ранее открытых пунктов

### CHK012 — измерение вне MainActor, single-flight, TTL, fail-closed

**Закрыт.** Обновлённый `plan.md` больше не допускает «Actor or `@MainActor` coordinator»:

- `plan.md:66` — dedicated actor `LocalRecordingFootprintProvider` с явной пометкой «never MainActor»;
- `plan.md:68-73` — single-flight, кэш и `measuredAt`, TTL 60 секунд, timeout 2 секунды, generation/root fence, fail-closed при отсутствии снимка или устаревании;
- `plan.md:80-83` — старт ждёт свежее измерение с timeout 2 секунды; timeout или ошибка блокируют старт с `storageUnsafe`;
- `plan.md:152` — тест `LocalRecordingFootprintProviderTests` прямо требует «proof that measurement runs off the main thread»;
- `spec.md:64` (FR-013) требует ровно это поведение.

Остаётся только реализационное уточнение: тест должен действительно проверить non-MainActor executor, а не только отсутствие enumeration в render path. Plan теперь формулирует это как отдельное требование, поэтому пункт закрыт на уровне проектного артефакта.

### CHK015 — F295 не удаляет файлы, не меняет очередь и не трогает F284/local-only/deletion

**Закрыт.** Analysis-документ больше не требует для F295 relief action или удаления WAV:

- `analysis-server-library-local-cache.md:1` — документ помечен как superseded 2026-11-14; authoritative F295 scope — `spec.md`/`plan.md`, F295 deletes no files;
- `analysis-server-library-local-cache.md:255-263` — «Revised F295 scope (final)»: actual footprint, warning non-blocking, `.failed` light/reason, «No file deletion, no queue schema change, no local playback removal»; relief/file cleanup явно отнесён к F296b;
- `analysis-server-library-local-cache.md:331-335` — «Revised F295 safety»: «No file deletion in F295», идея «Освободить место»/WAV cleanup отложена в F296b;
- `spec.md:66` (FR-015), `spec.md:70-75` (Out Of Scope), `plan.md:9`, `plan.md:138-147`, `plan.md:211-217`, `tasks.md:42-47` и `validation.md:36` последовательно запрещают удаление файлов, изменение схемы очереди и изменение F284/local-only/deletion.

### UX CHK008, CHK011, CHK012 — VoiceOver для warning и failed reason

**Закрыты.** Обновлённый план задаёт явные accessibility-требования:

- `plan.md:108-110` — warning-карточка получает accessibility identifier `systemAudio.storage.warning` и полный accessibility label: «Мало места на Mac. Запись разрешена. Освободите место, чтобы следующая запись не остановилась.»;
- `plan.md:123-124` — причина в меню-баре обрезается визуально, полный текст остаётся в tooltip, а accessibility label строки причины равен полному безопасному тексту;
- `plan.md:27` — Constitution Check VII явно упоминает VoiceOver-копию для warning и failed reason;
- `plan.md:156` — тесты `DesktopCalendarReminderTests` включают `.failed` с завершающимся writer, `.degraded`/`.stopping` и active stop+timer.

Для active stop: пункт меню остаётся нативным `NSMenuItem` с title «Остановить запись» (`SystemAudioCaptureCoreModels.swift:804`); нативный title является доступным именем пункта, а существующий тест `DesktopCalendarReminderTests.swift:988-989` проверяет его title и действие. F295 это поведение не меняет. Явный AX-label override для active stop не требуется, потому что нативный menu item уже озвучивается по title.

## 4. Requirements checklist: evidence

| Пункт | Evidence |
|---|---|
| CHK001 | `spec.md:52` (FR-001) требует фактический размер локальной папки. `plan.md:51` задаёт источник — `desktopUploadQueueService.recordingsRootURL`, тот же root, что у очереди. В коде свойство существует: `DesktopUploadQueueService.swift:128,159`; root задаётся через `LocalRecordingStore` (`LocalRecordingStore.swift:8-15`). |
| CHK002 | `spec.md:53` (FR-002) исключает `terminal_deleted` метаданные и требует учитывать только реально существующие файлы. `plan.md:51-58` измеряет фактическую папку, пропускает каталоги и symlink-обход; удалённые каталоги в неё не попадают. |
| CHK003 | `spec.md:54` (FR-003) требует учитывать `uploaded` записи, каталоги которых существуют. Фактическое измерение папки (`plan.md:51-58`) включает такие файлы; это же следует из User Story 1 и Acceptance Scenario 1 (`spec.md:21`). |
| CHK004 | `spec.md:55` (FR-004), `spec.md:62` (FR-011), `spec.md:65` (FR-014) и `spec.md:80` (SC-002) требуют разрешать warning для ручного и автоматического старта. `plan.md:87-100` разрешает `.warning` в gate, snapshot и meeting detection. |
| CHK005 | `spec.md:55` (FR-004) и `spec.md:24` (Scenario 4) требуют блокировки на critical, полном лимите и нарушении резерва. `plan.md:87-91` блокирует `.critical` и `.mustDegradeOrStop`; `LocalBufferService.swift:96-116` возвращает `.mustDegradeOrStop` для полного лимита и резерва, `.critical` — для critical-порога. |
| CHK006 | `spec.md:59` (FR-008) требует fail-closed при ошибке измерения. `plan.md:55-58` задаёт fail-closed для permission/enumerator error, `plan.md:73` — fail-closed при отсутствии/устаревании снимка, `plan.md:80-83` — блокировку старта при timeout/error. Текущий `LocalRecordingStorageProbe` уже возвращает `.mustDegradeOrStop` при ошибке (`LocalBufferService.swift:198-208`). |
| CHK007 | `spec.md:57` (FR-006) задаёт скрытие красного индикатора в `.failed` и сохранение видимости `.degraded`/`.stopping`. `plan.md:118-125` добавляет `.failed` к скрытым состояниям, сохраняет `.recording`, `.paused`, `.degraded`, `.stopping` видимыми и требует тест. Текущий `GrafRecordingLightView` скрывает `.idle`/`.starting` (`CalendarTray.swift:574-588`). |
| CHK008 | `spec.md:58` (FR-007) требует причину рядом с «Повторить запись». `plan.md:121-136` добавляет `failureDetail` в `CalendarTrayModel`, `CalendarTrayController`, `AppLifecycleDelegate` и `ContentView`, показывает вторую информационную строку под «Повторить запись» и задаёт fallback. |
| CHK009 | `spec.md:60` (FR-009) запрещает ослаблять гейты разрешений, источника, индикатора и политики. `plan.md:91` меняет только storage-ветку `RecordingPrerequisiteGate`; permission/source/indicator/policy-ветки сохраняются. T005 и T011 требуют boundary/regression-тестов. |
| CHK010 | `spec.md:79-84` (SC-001–SC-006) измеримы. `plan.md:151-159` задаёт поведенческие тесты, включая автоматический SC-001 fixture: 1,5+ ГБ исторических метаданных при ~1,1 ГБ фактического root; `quickstart.md:30-56` содержит ручные сценарии. SC-006 — release evidence, а не unit-тест, но проверяется через `release-full`, нотаризацию, Gatekeeper, Sparkle и health. |
| CHK011 | `spec.md:62` (FR-011) и `spec.md:65` (FR-014) прямо запрещают warning устанавливать `blockedReason`, `recordingBlocker`, `hasActionableProblem`, подавлять idle и блокировать automatic start. `plan.md:87-112` повторяет это; T006–T008 добавляют тесты. |
| CHK012 | `spec.md:64` (FR-013). `plan.md:66-83` задаёт dedicated actor «never MainActor», single-flight, TTL 60 секунд, timeout 2 секунды, generation/root fence, fail-closed и свежее измерение перед стартом. `plan.md:152` требует отдельное доказательство, что измерение идёт вне main thread. |
| CHK013 | `spec.md:57` (FR-006) и `spec.md:81` (SC-003). `plan.md:118-125` задаёт скрытие светящейся точки для `.failed` и сохранение видимости `.degraded`/`.stopping`; T009 и `DesktopCalendarReminderTests` покрывают состояния. |
| CHK014 | `spec.md:63` (FR-012) требует безопасную пользовательскую копию без сырых ошибок, путей, содержания встречи, токенов и credentials. `plan.md:132-136` требует curated copy, fallback «Запись не началась. Повторите попытку.» и запрещает raw errors/paths; T010 проверяет safe copy. Текущий `recordingBlockerPresentation` для storage уже отдаёт русскую пользовательскую копию (`ContentView.swift:3123-3126`). |
| CHK015 | `spec.md:66` (FR-015), `spec.md:70-75` (Out Of Scope), `plan.md:9,138-147,211-217`, `tasks.md:42-47` и `validation.md:36` запрещают удаление файлов, изменение схемы очереди и изменение F284/local-only/deletion. Analysis-документ помечен superseded и больше не требует F295 relief/WAV deletion (`analysis-server-library-local-cache.md:1,255-263,331-335`). |

## 5. UX checklist: evidence

| Пункт | Evidence |
|---|---|
| CHK001 | `spec.md:56` (FR-005) и `plan.md:102-112` требуют отдельное неблокирующее уведомление, а не `RecordingBlockerPresentation`: карточка `StatusNoteView` с amber-иконкой. Это информационный паттерн, а не error card. |
| CHK002 | `plan.md:109-111` прямо говорит: warning не устанавливает `blockedReason`, `recordingBlocker`, `hasActionableProblem` и не подавляет idle. `spec.md:62` (FR-011) подтверждает. Текущий `hasActionableProblem` возвращает true только для actionable blocker (`CaptureControlViewCore.swift:329-331`). |
| CHK003 | `plan.md:112` задаёт точную copy: «Мало места на Mac. Запись начнётся, но старые локальные записи скоро нужно будет удалить.» Текст на простом русском, объясняет, что запись начнётся и что старые локальные записи потребуют удаления; F295 сам файлы не удаляет. |
| CHK004 | `spec.md:24` (Scenario 4) требует понятное объяснение при critical/full/reserve. `plan.md:87-91` блокирует `.critical`/`.mustDegradeOrStop`; текущая storage-копия говорит: «Запись не началась: недостаточно безопасного места для локальной копии. Освободите место на Mac.» (`ContentView.swift:3123-3126`). |
| CHK005 | `spec.md:58` (FR-007) и `plan.md:121-136`: в `.failed` показываются «Повторить запись» и безопасная причина второй строкой; fallback задан. T010 покрывает reason row, truncation, safe copy и очистку устаревшей причины. Текущее меню уже показывает retry (`CalendarTray.swift:299`). |
| CHK006 | `spec.md:57` (FR-006) и `plan.md:118-125`: `.failed` скрывает красный индикатор, `.degraded`/`.stopping` остаются видимыми. T009 и `DesktopCalendarReminderTests` проверяют это. Текущий `GrafRecordingLightView` уже скрывает `.idle`/`.starting`, а `.degraded`/`.stopping` считает capturing (`CalendarTray.swift:574-588`). |
| CHK007 | `spec.md:22` и `spec.md:35` требуют Stop и таймер при активной записи. `plan.md:118-125` запрещает менять `GrafTrayRecordingState.resolve` и `statusIcon`; текущее меню показывает Stop и elapsed для `.recording`/`.paused`/`.degraded` (`CalendarTray.swift:303-320`). `plan.md:156` требует active stop+timer тест. |
| CHK008 | `plan.md:110` задаёт полный VoiceOver label для warning; `plan.md:124` — полный безопасный текст для failed reason. Active stop остаётся нативным `NSMenuItem` с title «Остановить запись» (`SystemAudioCaptureCoreModels.swift:804`), который является доступным именем пункта; существующий тест проверяет title и действие (`DesktopCalendarReminderTests.swift:988-989`). F295 это поведение не меняет. |
| CHK011 | `plan.md:110` задаёт полный accessibility label warning-карточки, а не только видимую copy. `plan.md:108` добавляет стабильный identifier `systemAudio.storage.warning`. |
| CHK012 | `plan.md:123-124` требует визуальное обрезание, полный текст в tooltip и accessibility label с полным безопасным текстом. T010 добавляет тест на truncation и safe copy. |
| CHK009 | `plan.md:123` требует truncate visible title и full text в tooltip. Текущий `CalendarTrayController.truncatedMenuTitle` уже обрезает по ширине (`CalendarTray.swift:379-391`), а event-строки используют `toolTip` (`CalendarTray.swift:327-330`). T010 добавляет тест на truncation. |
| CHK010 | `spec.md:73` (Out Of Scope) запрещает отмену F284 fallback, удаление кнопки «Слушать запись с этого Mac», изменение `LocalRecordingPlayer`, `localPlaybackURL`, bridge `openAction`, local-only списка и progress helpers. `plan.md:9` повторяет это; T011 требует regression assertions; `quickstart.md:55-56` требует unchanged F284/local-only/deletion. |

## 6. Остаточные наблюдения (не блокируют PASS)

1. **`.failed` + завершающийся local writer.** `plan.md:125` требует тест `.failed` с ещё завершающимся writer, но не фиксирует ожидаемое значение светящейся точки в этом конкретном пересечении. Тест должен явно зафиксировать выбранное поведение, чтобы не получилось скрытие индикатора при фактически идущей финализации. Базовое правило `.failed` скрывает индикатор, поэтому пункты CHK007/CHK013/UX CHK006 подтверждены; это уточнение для реализации.
2. **SC-006 — release evidence.** SC-006 проверяется `release-full`, нотаризацией, Gatekeeper, Sparkle и production health, а не unit-тестом. Это допустимый release-критерий, но он не заменяет поведенческие SC-001–SC-005.
3. **Active stop VoiceOver.** Для active stop используется нативный title `NSMenuItem`, а не явный AX-label override. Это корректно для AppKit и покрыто существующим тестом, но при реализации стоит сохранить этот контракт и не заменять нативный пункт кастомным view без accessibility label.

## 7. Проверка границ

- Изменены только `checklists/requirements.md` и `checklists/ux.md`; создан только этот отчёт.
- `spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, `validation.md`, analysis-документ, код, git, GitHub и release-артефакты не изменялись.
- Реализация F295 не начиналась: T001–T017 остаются `[ ]`, `validation.md` содержит `pending`.

## 8. Итог

- `requirements.md`: **15/15 checked**, открытых пунктов нет.
- `ux.md`: **12/12 checked**, открытых пунктов нет.
- Всего: **27/27 checked**, **0 unchecked**.

**Final verdict: PASS.** Reviewer gate пройден на уровне требований и проектных артефактов. Реализация может начинаться; поведенческие тесты, release-full, нотаризация, Gatekeeper, Sparkle и production health остаются обязательными на следующих этапах.
