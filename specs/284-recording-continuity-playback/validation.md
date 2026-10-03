# Validation — F284

Source baseline: 77e6aed8ff79127d6e6b284ad18b58da5793ef51. Branch284-recording-continuity-playback. High-risk-product. Initial local validation was completed before the implementation commit; no external CI claim is made in that initial evidence. On 2026-10-02 the user explicitly authorized commit, push, PR and release. Subsequent exact-SHA evidence is recorded separately.

## Root localization and repair
- The600s timer formerly aged the last *transition*, while the log supervisor restarted every300s and could fail its3.5s two-hour snapshot. New default observer reads current CoreAudio input metadata every2s; no legacy log child is launched in native mode, including on unavailable metadata. App no longer resets accepted/manual-suppressed detector state on generation/failure. Full current snapshots mark absent sources inactive with15s grace and renew active evidence.600s remains for real observation loss. Child executable is attributed to containing outer app with exact bundleID registry filtering.
- Quota failures already had public storage_capacity_exceeded type but missing cabinet mapping/copy; fixed exact mapping and honest storage message plus existing /billing overview. No quota/payment/storage admission/state changes.
- Existing native player/queue already authorize retained audio. Detail now projects local open and binds native action to routeUUID/rowUUID; send/delete remain list-only. Existing lifecycle synchronization, hash/size/root checks and player revocation remain.

## Requirements gates
Independent reviewer: requirements3/3, safety8/8; analysisCRITICAL0/HIGH0/MEDIUM0; task ownership T001–T006 synced to issues7454–7459, umbrella7447. Issue canon validation passed300issues. Optional commit/context hooks skipped. Initial task list was reviewer draft; finalized after PASS. Supported prerequisite command used (installed script lacks --require-spec).

## Red evidence
- Quota regression failed before fix: expected storage_capacity_exceeded, actual unsupported_media.
- Detail browser regression failed before fix: authorized local copy expected1button, actual0.
- New Swift native/snapshot/timer/route tests required absent APIs and did not compile on old code; this is compile-time red evidence, not a claimed old runtime reproduction. Original runtime cause separately confirmed by prior system/app logs and historical slow-query reproduction. New executable emulation checks behavior after implementation.

## Passing checks
- Swift focused detector/composition/bridge/queue/deletion:213tests,0failures; native observer restart extra1test,0failures. After final composition cleanup,21focused composition/bridge/restart checks passed,0failures. Synthetic45min clock yields one offer, no timer expiry, preserves accepted/manual-suppressed state; full empty snapshot clears all old source state and emits end at15s; stale predicate false599/true600. Unavailable/native-empty stream never launches configured old-log-active children. Repeated observer generation does not replay accepted offer. Existing file missing, invalid M4A/track/path/readability, ownership/deletion tests pass. SHA256 comparison in the unchanged native-open authorization path was confirmed by source inspection; no separate wrong-SHA256 runtime test is claimed.
- Server isolated Postgres focused run:22passed in59.99s. Includes all public terminal reasons, durable list/detail parity, unvalidated candidate denial, deletion precedence, stored playback contracts, bounded transfer/digest unit checks and new quota render/copy checks.
  Exact focused selection: `UV_PROJECT_ENVIRONMENT=<existing local test environment> GRAF_TEST_WORKERS=2 bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/contract/test_playback_status_contract.py tests/contract/test_cabinet_playback_contract.py tests/unit/test_playback_normalization_storage.py`. This22test run is16contract+6normalization storage tests, not billing_domain.
- Separate billing overview non-owner test:1passed (existing owner restrictions preserved); separate `tests/unit/test_billing_domain.py::test_storage_uses_exact_object_stat_and_rejects_overrun`:1passed, accepts exact boundary and rejects overrun; not attributed to22test run. Disposable container removed by runner; production data untouched.
- Browser local-recording-detail, local-recording-handoff, playback-refresh: PASS. Exact matching meeting, no browser/local action before native rows, lost access/removal/account change, server access_denied with stale native row, navigation/fragment refresh, retained keyboard focus, existing playback/comments and title edits covered.
- Ruff touched Python files, Spec Kit governance/bootstrap integrity, changelog fragments, git diff --check: PASS.

## Existing unrelated browser failure
local-recording-focus.test.cjs reaches timezone expectation and fails expecting05:30, actual03:30. Reproduced identically with original HEAD cabinet.js and user-time.js under the same browser runtime. Keyboard/local focus checks before that assertion pass; failure predates this change. No unrelated timezone fix folded in.

## Evidence boundaries
CoreAudio read-only probe: process list status0,40objects; no input active at probe time. The actual new `activeBundleIDs()` helper also returned available=true, active_count=0 in a read-only metadata probe. This proves API availability, not live Telemost capture. No new microphone capture performed; no private audio/transcript/paths/credentials stored here.
Dev harness status: active source7c4f844a983f2fe10a5f51fa695310acd47abac1, app GRAF Dev. It was not replaced: local-development requires an authorized implementation commit and clean exact SHA. Required PR governance-fast/macos-pr/pr-metadata, release-full, real controlled long-call acceptance, installed candidate and production deployment are still pending. Existing old call files remain intact; missing uncaptured seconds cannot be recovered. Quota still limits server audio, and local fallback requires retained authorized audio on this Mac plus updated desktop/cabinet.

## Convergence assessment
FR001–008 and SC001–004 compared against current code/tests/design after implementation. No missing code change found. No new implementation tasks required. Baseline timezone failure is outside these two bugs. Hardware/clean candidate/CI/release evidence remains explicitly pending, so feature is not declared shipped and tracker issues stay open.

Final independent review: PASS local code/regressions, requirements3/0+safety8/0. The access_denied stale-row gap was fixed and retested. Reviewer explicitly limits45min emulation to detector/start offers/timer decisions; no45min audio track was recorded. Full code/hardware/CI/release gates remain distinct.

## PR preflight correction
Implementation PR #7462 was opened on 2026-10-02. Initial governance-fast run37057788338 stopped in Development process preflight because spec.md lacked the required Legacy Impact section. The section now records removal of production log authority and retention of existing parser regression coverage. The local context category was also normalized to the supported high-risk-product value and its ownership/source pointer refreshed. No product behavior changed in this correction. Subsequent required checks must pass on the new head.

## Additional local diagnostic after PR preflight repair
`GRAF_CI_BASE_REF=56e98f101 infra/scripts/ci-local.sh --fast` on df6112370a5a8aa68c3bbb7d1050fcc1e0142d04: Swift build PASS,1197tests with9environment skips and0failures; related cabinet behavior101passed; server pure2264passed, fast179passed and1setup error because GRAF_NODE_MODULES was not supplied. The full diagnostic is therefore FAIL, not authoritative CI. The sole setup failure was resolved without changing product code: `GRAF_NODE_MODULES=<existing pinned Playwright modules> NODE_PATH=<same modules> GRAF_TEST_WORKERS=2 bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/unit/test_meeting_progress_ui.py::test_first_transcript_refresh_keeps_live_audio_and_comment_draft` on rebased333332019a56b0db186e89f9c0025cfb0f2edd6a:1passed,3.24s, isolated database removed. Rebase introduced only the already merged F280 evidence documents; runtime bytes of F284 remained identical.
Apple notary profile preflight succeeded; Developer ID app/package signing dry-run resolved the existing identities. No public mutation was performed by either read-only check. GRAF Dev candidate was built for df6112370a5a8aa68c3bbb7d1050fcc1e0142d04, but not promoted while the shared installed Dev was in use by F285. These older candidate builds do not count as acceptance of the final release SHA.

## Дополнительная сходимость: замечания PR #7462

Первоначальный набор проверок пропустил три подтверждённых дефекта. В настоящем шаблоне проигрыватель расположен рядом с main, тогда как проверка ошибочно вкладывала его внутрь main. Прямая замена проигрывателя удаляла локальную кнопку; технический перезапуск наблюдения закрывал предложение записи при сохранённом accepted в детекторе. Прежний вывод о завершённой сходимости ограничен прежним набором; эти пробелы закрывают T007/#7463 и T008/#7464.

- Browser: local-recording-detail и playback-refresh PASS в Chromium и WebKit; local-recording-handoff PASS. Отказы до исправления: кнопка отсутствует в реальной соседней разметке; после одного исправления поиска исчезает при прямом опросе preparing. Конечная проверка охватывает подготовку→квоту, отказ доступа без смены текста, замену блока, ответ другого маршрута, сохранение аудио/комментария/названия/фокуса и удаление кнопки.
- Swift: `swift test --package-path apps/macos --filter 'MeetingDetectionCountdownTests|MeetingDetectionPolicyTests|MeetingDetectionRecordingLifecycleTests'`: 56 тестов, 0 ошибок, 0 пропусков. Настоящие observer/detector/presenter с синтетической активностью сохраняют исходное окно, token, rememberChoice и deadline через restart; исходная кнопка и таймер выполняют решение один раз. Исполняемый тест не вызывает закрытый ContentView handler; удаление ошибочного dismiss подтверждено исходниками. Сон/пробуждение и аудиозахват на устройстве не выполнены.
- Governance, changelog fragment, node syntax и git diff --check PASS. Все новые задачи синхронизированы; issue canon PASS (300 проверенных задач).
- Проверки GitHub прежнего SHA 0909e6ac6fe74a9156bd6b3c5be0dff9263ecfb0 прошли, но не являются доказательством нового изменения. Нужны независимое ревью и новые обязательные проверки текущего коммита.

Попытка получить интерфейс установленного GRAF Dev после дополнительных исправлений остановлена системной блокировкой Mac. Автоматическое разблокирование недоступно; ручная проверка и продвижение нового приложения этим действием не выполнялись.

## Дополнительный отказ доступа после перехода — 2026-10-03

T009/#7466: общий recoverMeetingDetailFromResponse запоминает исходный meetingId; после чтения ошибки проверяет текущую карточку, её подключение и неизменность ID. Устаревший ответ возвращает true и отбрасывается всеми вызывающими путями. До исправления запоздалый 403 менял адрес новой встречи на /desktop/meetings и при успешном json, и при ошибке чтения; оба отказа воспроизведены в Chromium/WebKit. После исправления четыре сочетания успешное/неуспешное чтение × замена main/смена ID того же main сохраняют страницу, адрес и название. Актуальный 403 продолжает закрывать содержимое. local-recording-detail и playback-refresh PASS в Chromium/WebKit, node syntax и git diff --check PASS.

## Установленный GRAF Dev перед T010

После разблокировки Mac штатные promote и smoke выполнены на точном e62c85c641b6ae61860f69a8e011e0f8a351cb4f, manifest dev-e62c85c641b6. Все13 проверок smoke PASS. Через встроенный кабинет /Applications/GRAF Dev.app локальная кнопка открыла штатный проигрыватель: длительность487s, продвижение45s, затем воспроизведение остановлено и окно закрыто. Переход на другую карточку и обновление сохраняют кнопку. Установленная проверочная встреча имела transcription_service_unavailable; это проверка локального проигрывателя, а не аппаратное воспроизведение отказа квоты. Доказательство также приложено к PR#7462. Новая запись и новые разрешения не запускались.

Это доказательство предыдущего e62; будущий T010 SHA требует отдельного штатного обновления и smoke. Реальная45min непрерывная запись остаётся not_run: рабочий старт всегда захватывает микрофон, разрешение на такой контролируемый захват не получено. Эта аппаратная приёмка и exact-SHA release-full остаются обязательными отдельными воротами. Merge и выпуск не выполнены.

## Подготовка T010

Дополнительное замечание PR подтвердило, что недоступный соседний CoreAudio процесс отменял весь снимок, включая подтверждённую активность звонка. Требования уточнены признаком полноты: только полный снимок доказывает отсутствие, частичный сохраняет положительные подтверждения отдельных целей. Независимый reviewer после исправления противоречий research: requirements3/0, safety8/0, CRITICAL0/HIGH0. T010 связан с issue#7468; umbrella#7447 обновлён; mandatory issue-canon validation PASS (300 задач).

После уточнения браузерные local-recording-detail и playback-refresh повторно прошли Chromium/WebKit. Они проверяют неизменённое воспроизведение; результаты нового кода CoreAudio записываются отдельно после реализации.

## Реализация и проверки T010

До исправления исполняемый testMixedCurrentInputSnapshotRetainsReliableMeetingBesideUnreadableProcess завершился двумя ошибками: оба порядка списка возвращали nil вместо Telemost. После исправления тот же тест PASS. Восемь новых проверок охватывают отдельные отказы/некорректные размеры, недоступные PID/path/bundle, вышедший процесс, общий отказ списка, точный прямой bundleID и внешний Qt bundle, процесс вне .app и неразрешённую цель.

`swift test --package-path apps/macos --filter MeetingDetection`:93 проверки,0 ошибок,0 пропусков. Последовательность collector→observer→detector→используемый приложением600s predicate обработала1351 снимок за45min синтетического времени в обоих порядках процессов: одно принятое предложение, без завершения или истечения текущего подтверждения. Пустые неполные и неизвестные снимки не завершают встречу через15s и не обновляют600s clock; следующий полный пустой снимок сохраняет15s окончание. Проверка не записывает физическую аудиодорожку.

Один промежуточный запуск отказал из-за ошибочного ожидания теста для синтаксически допустимого bundleID Telemost.app. Проверочное значение заменено на действительно некорректное Telemost app; окончательный набор93/0/0 выше прошёл. Промежуточный запуск не объявляется PASS.

После реализации governance, changelog fragment, node syntax и git diff --check PASS. Независимый implementation review и новый exact-SHA CI записываются отдельно; их результаты на этом этапе ещё не получены.

Повторный серверный контракт воспроизведения:10passed на изолированной временной PostgreSQL БД через run_local_postgres_tests.sh --focused; контейнер удалён штатно. Первый прямой pytest дал2passed/8setup errors из-за отсутствующего TWOBRAIN_DATABASE_URL, не является успешным доказательством. Quickstart исправлен на штатный помощник.

Независимый implementation review T010: PASS, CRITICAL0/HIGH0/MEDIUM0. Reviewer сопоставил исходники и журналы red/green, collector/observer/detector/predicate и границы фактической аппаратной приёмки. Чеклисты повторно перечитаны: requirements3/0, safety8/0. Локальная сходимость не выявила нового непостроенного поведения; T010 отмечен выполненным после этих проверок. Новый commit/CI/Dev и реальный45min звук ещё не приняты; Mac вновь заблокирован, графический интерфейс текущим проходом недоступен.

## Контрольный физический звонок 2026-10-03 — FAIL

Пользователь отдельно разрешил45min Telemost с микрофоном и системным звуком в единственном GRAF Dev. Проверялся d496f165af9d131caddaa848aff8de9a7a9bfd67 после штатных build/promote/status/smoke (13/13). Одно предложение и один старт. Через361s запись остановилась: write_failed/source_overflow, hostOverrunCount=1, ptsGapCount=0, processErrorCount=0; сохранены оба очищенных файла с префиксом333.709s. Дискового заполнения нет. Подтверждение Telemost оставалось текущим. Контрольный звонок завершён; Dev UI показывает сохранённую часть и причину отказа.

Общий writer с ограничением20s ожидающих кадров — точка отказа, но исходные данные не различают задержку получения микрофона и недостаточное чтение writer. Отрицательный estimatedDriftPpm отражает расхождение прочитанных PTS, а не доказывает физическое изменение частоты. Для этого добавлена T011: исполняемая регрессия и безопасные относительные счётчики. Нагрузка CPU/замедление метаданных являются условиями, не доказанной причиной.

Эта проверка отменяет готовность к merge/release. Эмуляция45min детектора остаётся успешным отдельным тестом. До нового физического PASS приёмка открыта. Содержимое аудио/расшифровки, идентификаторы звонка, пути и исходные PTS не включены.

Независимое ревью требований T011: requirements5/0, safety12/0, PASS; t011-requirements-review.md. Analyze requirements: CRITICAL0/HIGH0, implementation proof pending. T011 issue#7471 создан после поиска дублей, ensure/validate issue canon прошли.

Релизный внешний отказ: Apple notarytool403 — обязательное соглашение отсутствует или истекло. Владелец команды должен принять его; нотариализация не обходится.

### Реализация T011 и локальная проверка

До исправления настоящий LocalRecordingWriter с непрерывными PTS и ограниченными источниками (microphone30s mono, system10s stereo) дал source_overflow при целых входных очередях:1test/8failed assertions. После чтения по PTS оба25s файла сохранены полностью, проверены оба соотношения размеров пакетов. Ограничения памяти и работы128 порций/проход, stop1024/источник сохранены. Между проходами удерживается не более одной порции на источник; настоящая потеря остаётся отказом.

Финальная команда `swift test --package-path apps/macos --filter 'LocalRecordingWriter|RecordingAudioTimeline|SystemAudioSampleExtractor|PrivacySuppressingSampleSource|MicrophoneCapture'`:72tests/0failures,27.24s. Включены две комбинации размера пакетов, длительность обеих дорожек, реальные overflow/loss, конечная остановка, несовместимые часы, NaN/infinite PTS и pause→drain→resume на реальном writer. Предварительная проверка паузы выявила ошибку проверочного замыкания; её исправили и окончательный набор повторили.

Независимое окончательное ревью T011: PASS, CRITICAL0/HIGH0/MEDIUM0. Консервативное заглушение ожидающего микрофона выполняется после долговечной отметки паузы, PTS/число кадров сохраняются, подавление не считается дважды. Интервалы диагностики монотонные, период30s, обычные относительные снимки отдельно capture.writer_progress; исходные PTS и содержимое не пишутся.

Локальная реализация и ревью не закрывают физическую приёмку T011. Следующие ворота: новый чистый SHA, штатный dev-harness, повторный разрешённый45min звонок, проигрывание/длительность, exact-SHA CI и выпуск.

### Повторная физическая приёмка T011 — PASS, 2026-10-03

Проверен продуктовый SHA6f1b4417518190eef6d1aaa3c007ff118c298389 в единственном GRAF Dev, manifest dev-6f1b44175181; штатные build/promote/status и smoke13/13. Пользователь разрешил микрофон и системный звук. Запись началась02:40:58UTC, штатная автоматическая остановка по meeting_ended03:26:38UTC после выхода из Telemost. Одна папка записи, одно предложение, один старт, ни одного повторного окна или досрочного отказа. Все60 снимков до финализации active; заключительный61-й saved. Максимальный наблюдаемый разрыв подтверждения Telemost3s.

Оба готовых файла сохранены полностью: WAV2740.009313s, M4A2740.053333s; оба полностью декодированы ffmpeg без ошибок и stderr. Manifest saved/failureReason=none, длительность обеих дорожек2740009ms, difference0; hostOverrunCount0, hostUnderrunCount0, ptsGapCount0, processErrorCount0, clipped/nonFinite0. Контрольные суммы вычислены. Наблюдаемые максимумы очереди: microphone512frames/10.667ms, systemAudio960frames/20ms; ожидающие порции0, накопленного отставания нет. Периодические снимки не доказывают отсутствие каждой краткой задержки; итоговая целостность подтверждена независимо.

В карточке видна45min сохранённая запись и «Слушать запись с этого Mac». Действие открыло штатный native player: прогресс00:18, после перехода45:00→45:26, duration45:40. После закрытия, обновления карточки и повторного действия player вновь показывает движущийся прогресс00:13/duration45:40. Оба файла проверены декодированием; слуховая оценка содержимого не заявляется. Расшифровка на Dev недоступна из-за настройки доступа к внешнему сервису — отдельное ограничение стенда, не PASS обработки встречи. Основной GRAF был временно закрыт на контроль и возвращён после.

Системный журнал CoreAudio/GRAF/Telemost за весь контроль проверен по overrun/overflow/overload/drop/error/fail. Единственное overload относится к DeviceIsRunning=0 при штатной остановке03:26:38UTC; overrun/overflow отсутствуют. Сообщения cache_delete/APFS, сетевого ограничения журнала событий и Bluetooth XPC не сопровождались разрывом PTS или отказом writer. Сырые системные строки, аудио, текст, личные пути и идентификаторы встреч в git не включены. Обезличенные метаданные: hardware-acceptance.json.

Общий validate-pr-checks.py подтвердил SHA6f1b441… и базуf3ec4dd95c3aa68fc7246338bd7c58908d24aee2: governance-fast37090084881, macos-pr37090084876, pr-metadata37090742893 PASS. Следующий документационный коммит требует собственных текущих CI; повтор физического звука при неизменном продуктовом коде не требуется. Apple preflight вновь403 missing/expired agreement; публичный выпуск, release-full и установленная production-приёмка остаются отдельными незакрытыми воротами.

Независимая оценка окончательной аппаратной приёмки: PASS,61 снимок перепроверен; обе дорожки росли во всех59 интервалах до финализации, повторное проигрывание подтверждено. T011 может быть закрыта; непостроенных обязательных частей F284 нет. Чеклисты качества требований остаются requirements5/0+safety12/0.

## T012–T013: дополнительные замечания PR

Риск high-risk-product. Требования уточнены после независимого BLOCK по отсутствующей конечной границе nil-diagnostics; revised reviewer-owned pr-followup PASS5/0. Issue-sync #7480/#7481 и canon/governance/changelog PASS. Первоначальный аппаратный PASS45min40s6f1b441 сохраняется историческим доказательством. Новые продуктовые файлы требуют актуальных регрессий, независимого ревью, Dev и exact-SHA CI.

T013 предварительная браузерная регрессия: на прежнем коде stale403 менял URL новой встречи на список; после исходного meetingId до fetch и проверок актуальности passed Chromium/WebKit. Итоговые команды и независимая оценка записываются после завершения исполнителя.

T013 итог: существующий NODE_PATH=/Users/yshishenya/Documents/crisp/apps/server/tests/browser/node_modules (Playwright1.63.0), `node apps/server/tests/browser/local-recording-detail.test.cjs` и `node apps/server/tests/browser/playback-refresh.test.cjs` — exit0 в Chromium и с GRAF_BROWSER=webkit. Задержанные fetch403/404/500/success/network rejection и отдельное text-body сохраняют новый main/ID/URL/title/markup/button/focus; текущий403 отзывает собственный доступ. node syntax/diff PASS. Root независимо прочитал изменённые функции, всех relevant recovery callers и проверки: исходный ID фиксирован до await; recovery дополнительно защищён во время JSON, ни один путь устаревшего notice/replacement не остался. Новых замечаний к T013 не найдено.

T012 red: прежний код исполнил6 новых проверок с533 assertion failures, в том числе подтвердил ненулевые паузные порции и утечку в оба итоговых файла; отказ источника без границы не сохранял открытый checkpoint. Это исполняемое red-доказательство, не только отсутствие API.

T012 green: `swift test --package-path apps/macos --filter 'LocalRecordingWriter|RecordingAudioTimeline|SystemAudioSampleExtractor|PrivacySuppressingSampleSource|MicrophoneCapture'` —80tests,0failures,28.206s. Несколько FIFO-порций, частичная стереопорция, повторная пауза, совместное чтение/resume, nil-diagnostics с непрерывным пополнением, явный отказ resume/open checkpoint/конечный Stop, оба декодированных итоговых файла, сохранение системного звука и новых микрофонных кадров. Точные нулевые значения источника и строгий файловый порог0.0001 сохранены.

Промежуточный nonzero-system fixture дал паузный хвост около0.001 в WAV/M4A. Контроль с буквальными нулевыми микрофонными порциями через тот же system/AEC/codec path воспроизвёл эти же значения; итоговая паузная разница файлов0.0, проверяется с допуском0.000001. Строгая zero-render проверка микрофона отдельно остаётся. Промежуточный отказ не скрыт ослаблением порога; результаты окончательного набора80/0 привязаны к окончательным файлам.

Независимое ревью T012: CRITICAL0/HIGH0/MEDIUM0, без изменения кода и без дублирующего запуска тестов. Сериализация, конечная граница, предварительно прочитанные/частичные порции, двойной учёт, производственные callers и прежние отрицательные ограничения проверены. Runtime/release readiness не заявляется.

2026-10-03 повторная CUA-проверка вернула системную блокировку Mac. Физическая приёмка новых файлов ожидает ручного разблокирования; ранее пройденные45min40s относятся к6f1b441. Read-only Apple preflight вновь HTTP403 required agreement missing/expired. Приёмка, merge и выпуск остаются открытыми; ни сборка без подтверждения Apple, ни прежние runtime/CI доказательства не заменяют обязательные ворота нового SHA.

## T013: согласование существующей контрактной карточки

На6c91a6b4165eafe14a849ab0567b7874d94eacf3 GitHub governance-fast37096256211 завершилась failed/ci_stage_failed; macos-pr37096256155 PASS. Середина удалённого журнала обрезана обоими средствами диагностики; первая внутренняя строка удалённого отказа не заявляется установленной. Локальный fast сначала остановился на устаревшем ignored source_sha; после обновления локального указателя воспроизведён конкретный отказ related behavior tests: test_meeting_detail_runtime_scrubs_private_dom_after_access_loss, private detail remained connected.

Причина локального отказа — FakeElement не задавал dataset.meetingId и FakeDocument не поддерживал main[data-meeting-id]. Настоящая разметка rendering.py содержит этот атрибут. Исправлены только эти два элемента искусственной страницы; все утверждения удаления закрытого DOM/title/history, безопасного адреса, семантики и фокуса сохранены. Изменений продуктового кода нет. Полный static-assets contract:76passed/0failed,2.43s; связанный scoped lane:112passed/0failed,3.03s. Локальный fast на исходном6c91 также прошёл Swift build,1224tests/9skipped/0failures,117.933s и ContractValidation, затем остановился на описанном контракте. Эти локальные проверки не заменяют новый GitHub source proof.

GRAF Dev dev-6c91a6b4165e штатно promoted2026-10-03T04:24:30Z; отдельный live smoke PASS13/13. Mac повторно заблокирован при попытке открыть Telemost. Новая аппаратная приёмка T012 и release Apple403 остаются открытыми.

Независимое read-only ревью исправленной контрактной карточки:CRITICAL0/HIGH0/MEDIUM0. Проверены настоящая разметка, обе строки и сохранение всех утверждений отзыва доступа; других необходимых изменений не найдено.

## T014 — новое замечание производителя

Общий GitHub proof e4b1ebb774d661348098bc89fbff398a8ea0a165 прошёл обе source проверки:governance-fast37097156141,macos-pr37097156195; обновлённое описание также governance-fast37097577754,macos-pr37097577759,pr-metadata37097578185 PASS. Новый review4171728042 локализовал producer race между diagnostics snapshot и сменой состояния; отдельное read-only исследование подтвердило прямой appendCapturedBatch под другой блокировкой. Это новый блокирующий дефект поверх прежнего T012, даже при80/0 и успешных CI. T014 issue7486 и новые FR012/SC008/plan/contracts/checklist зарегистрированы; независимый requirements PASS5/0,C0/H0/M0. Исправление producer атомарности, red/green и новая приёмка выполняются отдельно.

Единственный GRAF Dev dev-e4b1ebb774d6 promoted2026-10-03T04:39:25Z и live smoke13/13PASS. Повторная попытка UI подтверждает заблокированный Mac; аппаратная приёмка остаётся открытой. Apple403 сохраняется.

### T014 — атомарная граница производителя: локальные проверки и независимое ревью PASS

Окончательная реализация передаёт withQueuedFrameCountSnapshot через AppOwnedMicrophoneSampleSource в BufferedLocalRecordingSampleSource. Размер FIFO и переход privacy wrapper выполняются под одной блокировкой очереди, общей с append/read; порядок wrapper→FIFO. Производственный callback меняет только конечный счётчик и состояние. Unsupported/default callback не вызывается; отрицательная граница сохраняет паузу и открытый checkpoint. Новый буфер или ожидание пустой очереди не добавлены.

На прежнем e4b1 коде барьерное воспроизведение: 3 проверки / 6 assertion failures. После исправления targeted 7/0, окончательный focused набор 84/0 за 26.085s. Проверены обе стороны границы, исключение параллельных append/read на производственном источнике, diagnostics-only отказ, negative boundary, repeated pause и bounded Stop/open checkpoint. Итоговые WAV/M4A проверки сохранены; paused_mic_delta=0.0 в обеих дорожках при сравнении с нулевым микрофонным образцом. Независимое read-only ревью стабильных четырёх файлов: C0/H0/M0; проверены production factory, forwarding, порядок блокировок и локальные результаты. Контрольные суммы записаны в followup-review-evidence.json.

Reviewer-owned requirements: прежние 22/0 и producer-boundary 5/0, всего 27/0. Аппаратная приёмка текущей T012/T014 остаётся открытой: Mac заблокирован. Предыдущие 45min40s не перенесены на новый код. Новые exact-SHA CI, штатная установка Dev и выпуск остаются отдельными воротами.

## T015 — завершение при недоступном реестре, 2026-10-04

Свежий PR review обнаружил ранний выход композиции при nil registry до единственного inactive/grace пути detector.advance. FR013/SC009/план/контракт/T015/quickstart согласованы, независимые требования4/0,C0/H0/M0. Analyze C0/H0/M0, canon ensure/validate PASS300, task issue#7504 после поиска дублей.

Исполняемый red: optional registry API с прежним ранним отказом (минимальный адаптер прежнего блокирующего пути, не неизменный исторический SHA),3 проверки/4 assertion failures. Полное отсутствие не давало ended на15s; после восстановления реестра событие приходило поздно. Green: guard реестра перенесён после inactive/grace в единственном advance, композиция всегда передаёт outputs; для новых prompt/auto/candidate реестр обязателен. Ownership event при nil всё равно reconciled. Никаких вторых таймеров, сохранённых старых реестров или новых разрешений. `swift test --package-path apps/macos --filter 'MeetingDetectionPolicyTests|MeetingDetectionRecordingLifecycleTests|MeetingDetectionCountdownTests'` —68tests/0failures,8.864s.14.999/15s/ровно один ended, partial-empty, повторная активность, ручное подавление, отсутствие новых предложений и восстановление реестра покрыты исполняемо; отдельная проверка wiring читает production composition.

Работающий45min Telemost1e78 не обновлён. Подтверждение нового T015 требует независимого ревью, нового SHA/CI и штатного Dev после сохранения контроля; текущий аппаратный прогон не объявляется тестом обновлённой композиции.

Независимое ревью T015 реализации C0/H0/M0, требования перечитаны4/0; checked production outputs/current-start/Stop/deferred/600s и4source hashes. Физическая проверка новой композиции и окончательные exact-SHA CI остаются открытыми.

## Контроль Telemost — 2026-10-04,49min41s

Единственный GRAF Dev1e78bfc1751ebe28ad97dab90b0cc2c17f797e80, штатный harness/smoke13/13.22 исходных Capture файла побайтно совпадают с6dc8d369656d171d1a81488a9ec1b3dd58d0e9aa; T015 изменяет только композицию/детектор и отдельно ожидает Dev. Запись22:02:34–22:52:15Z, один prompt22:02:31Z, один start, одна директория,0 повторных prompt/ошибочных остановок/тайминговых аномалий, текущая активность Telemost с максимальным интервалом3s. Оба pause/resume сегмента завершены,16.515s и6.683s. Системный контрольный сигнал присутствует в WAV (RMS0.002796). Это аппаратная работоспособность паузы; точную приватность FIFO/producer подтверждают прежние детерминированные84/0 и WAV/M4A delta0.0, аппаратный mix не заменяет их.

Оба файла saved/failure none, duration2981308ms. WAV95401914bytes, M4A24124706bytes; полное ffmpeg decode и ffprobe PASS,0 строк ошибок. Физический UI: карточка49min/Сохранено на Mac, кнопка локального аудио открывает штатный плеер, начало продвигается, seek49:35 воспроизводится до49:41/paused; reload карточки сохраняет кнопку. Также серверный player продвигается при blocked_config расшифровки; Dev не содержит MediaScribe настройки и не отправляет запрос поставщику.

Telemost закрыто пользователем только как окно: CUA подтвердил продолжающийся фоновый звонок49min и кнопку Завершить звонок. Штатное нажатие завершило звонок; Telemost01:51:59.450 call running=false/01:51:59.685 stop streams; GRAF22:52:15Z meeting_ended stop,22:52:16Z saved. Автоматический stop16s, saved17s от фактического окончания звука. Предыдущее время намерения root не используется.

Итоговая completed AEC health: processed298362frames, overrun0/underrun0/PTSgap0/processError0/nonFinite0,clipped14808,p95 processing1ms. Нулевые active placeholders не используются. Системный журнал10012events: replayd7960/coreaudiod2052,125 error/fault записей; большая доля связана с aggregate channel-layout/vocal-isolation и camera/ScreenCaptureKit setup/teardown. В01:16:21 отмечен один эпизод HAL client-timeout/overload(5 строк), без разрыва GRAF PTS или host overrun. Причина внутри macOS не установлена и не приписывается CPU. Все обычные logs и audio остаются локальными; git содержит только hardware-acceptance-2026-10-04.json без путей/ID/содержимого.

Короткий предварительный запуск1e78 отказал render_reference_missing: входящий SCK PTS gap16.0416ms, размеры960/48000/mono согласованы,callback max0.362875ms. Реальные потери остаются отказом FR009; защита не ослаблялась. Этот отказ сохранён как ограничение, не засчитан в PASS49min.

Общий exact-head PR proof6dc8/base d8fa: governance-fast37159017529,macos-pr37159017528,metadata37159567661 PASS, проверены общим validate-pr-checks. Более ранний metadata failure относится к устаревшему описанию. Новые изменения T016 и итоговые docs требуют новых SHA/CI; T015/T016 Dev и выпуск открыты.

## T016: восстановление ожидающего предложения

Новый review4175168241 локализован в обоих auth/registry callers общего dismiss. FR014/SC010/T016/контракт/quickstart, independent requirements5/0,analyze C0/H0/M0,issue#7509 и canon PASS. Первый helper подавал retryable лишь из native auth path. Wiring-red2tests/6 source assertions на6dc8; behavioral-red1/1 с минимальным адаптером прежнего dismiss; первыйgreen70/0 не доказывал порядок observers.

Независимое implementation review H001 обнаружило синхронный NotificationPresenter auth invalidation прежде SwiftUI: onInvalidated ставил terminal и очищал prompt раньше helper. Настоящий presenter.invalidate reproducer дал1test/1failure восстановленного offer; источник callback адаптирован явно, не неизменный исторический SHA. Уточнение требований5/0 задаёт два порядка и generic invalidation terminal. Callback сравнивает существующий authEpoch с захваченным при показе; только auth transition даёт retryable текущему prompt. Вторых таймеров, новых state/fields, reset всего detector нет.

Итоговый ordering-green:70tests/0failures,7.674s. Настоящий notification presenter.invalidate вызывается в обоих порядках, обычный dismissAllCards сохраняет terminal; восстановленный offer один,2s/8s и nil registry/accepted/Skip/Stop сохранены. Отдельный wiring охватывает оба callers, authEpoch callback и outcome-before-clear. Первыйgreen/historical review сохранены как история, не итоговая приёмка. Независимое повторное ревью и текущий Dev ещё требуются.

## Converge итоговой реализации — 2026-10-04

Применён speckit-converge после implement T016; штатный prerequisite поддерживает --require-tasks/--include-tasks, upstream --require-spec отсутствует, spec/plan/tasks проверены явно. До/после hooks converge не зарегистрированы.14 FR и10 SC,7 именованных групп проектных решений и применимые8 принципов constitution проверены по существующим source/callers/tests. Buildable gaps missing0/partial0/contradicts0/unrequested0,C0/H0/M0. Текущий CoreAudio/partial coverage,15s/600s/manual suppression, локальная привязка/доступ/удаление/целостность/квота, PTS interleave и атомарная приватность, nil registry lifecycle и authEpoch recovery согласованы.

Новых задач не добавлено: T015/T016 уже содержат актуальную Dev/CI приёмку и остаются открыты до неё. Во время converge tasks.md побайтно не изменялся. Hardware49min41s закрывает T012/T014, не T015/T016. Внешние merge/release-full/CD/Apple/feed/install ворота остаются. Это проверка соответствия реализации, не объявление завершённого выпуска.

Независимое повторное ревью T016 C0/H0/M0, H001 устранён; требования перечитаны5/0, всего reviewer-owned36/0. Три итоговых product hashes в prompt-recovery-review.md. Исторический H1 и первый70/0 сохранены как история. Текущий Dev/CI/release не объявлены пройденными.
