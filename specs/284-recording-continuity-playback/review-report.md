# Независимая проверка требований F284
Дата: 2026-10-02. Исходный SHA: 77e6aed8ff79127d6e6b284ad18b58da5793ef51.
Статус: **PASS по качеству требований** после повторного чтения уточнённых артефактов. Это проверка качества требований до реализации; код, CI, приложение и релиз не приняты.

## Проверенные пункты
| Чеклист | Пункт | Доказательства |
|---|---|---|
| requirements | CHK001 | spec.md:10–27: две независимо проверяемые истории; spec.md:59–63: тарифы, браузер, утраченный звук, релиз и несколько приложений ограничены. |
| requirements | CHK002 | spec.md:38–57; data-model.md:3; contracts:2–3; research.md Source authority; quickstart.md:3: 45 минут, 15–17s, 600s, current-only evidence и отрицательные сценарии определены. |
| requirements | CHK003 | spec.md:30–45,59–63; plan.md:13,20–24: доступ, удаление, согласие, квота и разрешение на выпуск сохранены. |
| safety | CHK001 | spec.md:13–18,38–40,54–55; research.md:3–7; quickstart.md:3: длинный звонок, ошибки журналов/сбросы, количественные результаты. |
| safety | CHK002 | plan.md:5; data-model.md:3; contracts:2–3; research.md Source authority; quickstart.md:3; tasks.md:T002: native — единственный рабочий источник, полный снимок согласует все source states, старый журнал не используется даже при ошибке, unknown не заменён пустым, точная outer bundleID атрибуция и проверки отказов заданы. |
| safety | CHK003 | spec.md:17–18,41,60; plan.md:21; constitution §II и product-gates.md Capture And Platform. |
| safety | CHK004 | spec.md:27,32–33,42,44; data-model.md:4; contracts/recording-and-playback.md:4; существующие localPlaybackURL/canOpenLocalPlayback и handleLocalRecordingAction повторно проверяют lifecycle и файл. |
| safety | CHK005 | spec.md:25,34,43,60–61; research.md:10–13; contracts:6: квота не обходится, нет обещания автоматического восстановления; браузер без файла ограничен. |
| safety | CHK006 | spec.md:26; plan.md:5,21; contracts:5: обычная доступная кнопка и существующий GRAF player, без новых assets. |
| safety | CHK007 | spec.md:45; plan.md:21; quickstart.md:2; просмотренные feature artifacts содержат только служебные сведения, без аудио, текста встречи, учётных данных и приватных путей. |
| safety | CHK008 | plan.md:13,24; quickstart.md:7: эмуляция, GRAF Dev, разрешённый чистый commit, точный SHA PR/CI и release-full разделены. |

## Повторная проверка и анализ
Первоначальный HIGH о конфликте старого журнала с новым CoreAudio снимком устранён в требованиях. Рабочая композиция использует только текущие native snapshots; legacy log child никогда не запускается в native mode и не используется как fallback. Полный снимок согласует все состояния источников, повторный active сохраняет accepted/terminal и manual suppression. Нет противоречия между plan, research, data-model, contract и quickstart.

Исчезнувший/неразрешимый активный PID и ошибка свойства дают unavailable, не пустой set. Child attribution сравнивает exact outer bundleID с действующим verified registry; отрицательные nested-helper/unapproved-target проверки включены. Наличие API на машине не объявляется аппаратной приёмкой звонка.

Требование исполняемых регрессионных проверок уточнено: T002/quickstart используют advancing synthetic clock с реальным shared evidence predicate и detector, не только строки исходников. Native empty + old log active → stop15–17s; native unavailable + cached log active → stop600s; stream не запускает configured old-log-active script. Это требования к будущим проверкам, а не сообщение об их выполнении.

FR001–008 покрыты T002–T005 и T006; обе истории имеют независимые результаты, tests предшествуют fixes. T001/issue sync, формальная генерация tasks/analyze и последующая validation остаются обязанностями основного агента. Critical=0, High=0, unchecked причин нет.

Рекомендация реализации без изменения требований: ссылка управления хранилищем должна сохранять текущую роль billing_owner; для не-владельца показывать доступный путь использования/обращения к владельцу. Повторная lifecycle/access проверка перед native open, а также удаление stale DOM action остаются обязательными отрицательными сценариями.

## Границы проверки
Проверены AGENTS.md, .specify/feature.json, constitution, product baseline/current status, spec-kit-flow/product-gates/release guidance; все feature spec/plan/research/data-model/contracts/quickstart/tasks; исходники детектора, stream/composition, локального bridge/player/queue и отображения terminal reason. Только requirements/safety и этот отчёт изменены. Объединённый safety checklist допустим: guidance задаёт default set, а не обязательные имена.

## Перечитанные итоги
requirements.md: checked=3, unchecked=0. safety.md: checked=8, unchecked=0. Всего checked=11, unchecked=0. Все пункты перечитаны после изменения. Выдан только PASS требований; implementation/hardware/CI/release gates им не заменяются.

## Независимая проверка реализации и журналов
Итог: **PASS локальной проверки исходников и автоматических регрессий** после исправления замечания о серверном отказе доступа. Проверены текущий diff, native snapshot reader, все затронутые callers, bridge/DOM, исходники проверок и соответствие validation.md фактическим журналам. Это не приёмка установленного приложения, реального звонка, внешнего CI или релиза.

| Граница | Исходники и доказательства | Результат |
|---|---|---|
| Единственный текущий источник | MacOSAudioOwnershipLogStream default snapshotProvider=MacOSAudioInputActivitySnapshot.activeBundleIDs; native branch не запускает runSupervisor/историю даже при nil. Provider error даёт snapshotUnavailable. Существующий CoreAudio reader возвращает nil при ошибке свойства/неразрешимом PID, empty только при подтверждённом отсутствии. | PASS чтения кода и injected-provider регрессии. |
| Точное приложение | proc_pidpath → outer .app → Bundle.bundleIdentifier; существующий verified registry/filter принимает точное bundleID. Тест outer Telemost vs nested Qt helper и non-app path проходит. | PASS; фактическая input-active Telemost атрибуция требует аппаратной проверки. |
| Длинный звонок и ручной запрет | reconcileSnapshot сохраняет tracked outcome, согласует отсутствие всех source states; app не reset на reconcile/unexpectedFinish. Повторный active не проигрывает accepted/terminal. | 45min synthetic detector test и restart/manual-suppression тесты PASS. |
| Остановка | Первый empty устанавливает inactiveAt, повторные empty его не сдвигают; detector.advance выдаёт ended после15s. Shared recordingEvidenceExpired false599/true600, composition вызывает predicate только для activeMeetingDetectionBundleID. Неактивность завершается через detector, manual suppression очищается тем же ended. | PASS кода и управляемого времени; реальная stop latency15–17s ещё не измерена. |
| Маршрут/действие | Coordinator: active attached main frame, sourceURL==webView.url, allowed origin/route. allowedAction разрешает detail только open и UUID(route)==UUID(row); неизвестный row/маршрут/send/delete отвергаются. | Executable bridge test и источник PASS. |
| Lifecycle/файл | Существующий native open синхронизирует lifecycle, выполняет localPlaybackURL, затем ещё раз проверяет текущий lifecycle перед player.open. Queue проверяет active owner, удаления, recordingsRoot, читаемость/размер, M4A format и SHA256; player reconciliation закрывает отозванные/удалённые записи. | Guard-код сохранён; missing/invalid media/track/path/readability и ownership/deletion regressions PASS. Сравнение SHA256 проверено по коду; отдельный tampered-SHA local-open тест в предъявленном наборе не найден. |
| DOM/квота | Native rows дают кнопку только для текущей meetingId/canOpen. deleted/deleting и access_denied удаляют кнопку, даже если stale native row ещё canOpen. Повторный publish не заменяет сфокусированную кнопку; HTMX swap согласует её с новым detail. Exact quota mapping/copy, /billing overview без обхода billing_owner; shared workspace не раскрывает billing link. | После замечания guard и scenario добавлены; final-detail PASS. Квота/state/admission код не менялся. |

## Сверенные результаты
- /tmp/graf-swift-green2.log:213 XCTest,0failures; native restart extra /tmp/graf-swift-restart.log:1test,0failures.
- /tmp/graf-final-focused.log:21test,0failures после финальной правки композиции. Часть composition assertions остаётся проверкой исходников; новый detector/evidence predicate исполняется с synthetic clock.
- /tmp/graf-server-tests.log:22passed,1warning,59.99s;16contract+6normalization storage. Не приписывается billing admission.
- /tmp/graf-final-capacity.log: отдельная admission boundary проверка1passed,1warning; точная команда в validation.md. Приём точной границы и отказ при превышении видны в исходном test_storage_uses_exact_object_stat_and_rejects_overrun.
- /tmp/graf-final-detail.log: текущий browser detail test PASS; исходный сценарий дополнен access_denied со stale native row.
- /tmp/graf-baseline-focus.log падает на ожидании05:30 при фактическом03:30. Оба baseline assets cabinet.js/user-time.js байт-в-байт совпадают с git show HEAD соответствующих файлов: это подтверждённая исходная ошибка в той же среде, не введённая F284.
- git diff --check в ходе review PASS. Ruff/governance/bootstrap/changelog сведения сохранены в validation.md; эти результаты не заменяют exact-SHA внешние проверки.

## Итог и ограничения
В текущем срезе новых неустранённых ошибок по рассмотренным границам не найдено. Требования перечитаны: requirements checked3/unchecked0, safety checked8/unchecked0, всего11/0. Checklists остаются воротами качества требований, не общим утверждением аппаратной готовности.

45min эмуляция подтверждает одну offer и отсутствие timer expiry в detector/predicate, а не записанную45min аудиодорожку. CoreAudio probe без активного входа доказывает только доступность API. Требуются отдельные контролируемый реальный звонок, installed candidate через GRAF Dev harness, точный commit/PR SHA с governance-fast/macos-pr/pr-metadata и release-full для выпуска. Продуктовый commit, замена приложения, сервер и публичный релиз этой проверкой не разрешены и не выполнены. Reviewer изменил только этот отчёт; код и остальные artifacts исправлял основной агент.


## Независимое повторное review T007/T008 — 2026-10-02

Проверен рабочий diff поверх 0909e6ac6fe74a9156bd6b3c5be0dff9263ecfb0. Исходные три замечания подтверждены на этом HEAD и устранены в предъявленных изменениях; прежний PASS не охватывал обнаруженные gaps. Текущее решение: PASS исправлений этих трёх замечаний по исходникам и указанным автоматическим проверкам; CRITICAL=0, HIGH=0. Аппаратная приёмка, будущий commit/PR SHA и выпуск не приняты.

1. renderDetailLocalPlayback использует detailPlayback, соответствующий реальному соседнему контейнеру после main. Browser fixture теперь воспроизводит эту структуру; matching meetingId/canOpen, access_denied/deleting/deleted, смена аккаунта и обычный браузер без native rows проверяются.
2. Прямой refreshPlaybackRecovery согласует кнопку и после замены, и при неизменном содержимом с новым reason. Native-only текст исключён из server signature, поэтому неизменный ответ сохраняет кнопку и фокус. Ответ для другого meetingId отвергается; после чтения успешного тела повторно проверяется актуальный main. initCabinet согласует processing fragment. Существующий playback-refresh сохраняет audio node, воспроизведение, draft, focus/selection и восстанавливает локальную кнопку после смены media revision.
3. Технический restartMeetingDetectionObservation больше не закрывает Ask. Detector accepted и оригинальное окно/token/deadline сохраняются; намеренная остановка наблюдения и конец звонка сохраняют отдельные пути закрытия. Новый тест исполняет реальные observer/detector/presenter с синтетическими данными, проверяет тот же NSWindow, исходный deadline, remember choice, кнопку/timeout и единственное решение. Он НЕ вызывает executable handler приложения: его однострочное изменение подтверждено чтением исходников. Этот тест сам по себе не является старым runtime reproduction или сквозной проверкой приложения.

Независимо выполнены local-recording-detail в Chromium и WebKit и playback-refresh в Chromium: PASS. Сверен /tmp/graf-f284-prompt-restart-tests2.log: 56 tests, 0 failures, включая новый тест. Worker сообщает дополнительные playback-refresh WebKit и local-recording-handoff PASS; эти дополнительные запуски здесь отдельно не выполнялись. git diff --check PASS. Чеклисты перечитаны: requirements checked3/unchecked0, safety checked8/unchecked0; всего11/0. Они подтверждают качество требований, не факт аппаратной приёмки; их состояние не менялось.

Дополнительное MEDIUM/P2 наблюдение по существующему пути: recoverMeetingDetailFromResponse читает responseProblemCode асинхронно и после этого вызывает renderMeetingDetailRecovery без повторной проверки актуальности исходного main. Синтетическая браузерная проверка: старый poll получает403, ожидание clone().json приостановлено, затем переход на новую встречу и завершение старого403; адрес новой встречи меняется на /meetings. Успешные ответы новым guard защищены, error recovery этим guard не покрыт. Это не одно из исходных трёх замечаний и не новое поведение diff. Для отдельного исправления требуется привязать recovery к исходному detail и повторно проверить его текущую identity после асинхронного чтения ошибки, перед изменением DOM/адреса. Доступ к чужому аудио в этом сценарии не получен.


## Независимое review T009 — 2026-10-02

Проверен только новый T009 diff поверх abe2623b18d77118b38d73e206e38492b42982bf: shared recoverMeetingDetailFromResponse и дополнительные сценарии local-recording-detail. Дополнительное MEDIUM/P2 замечание из предыдущего раздела устранено; CRITICAL=0, HIGH=0, MEDIUM=0 по рассмотренным T007–T009 границам. Итог PASS исходников и перечисленной автоматической проверки, не аппаратной приёмки или выпуска.

Shared helper запоминает meetingId до чтения responseProblemCode и после await проверяет connected, identity актуального detail и неизменность meetingId. Устаревший ответ возвращает true до special-action веток и renderMeetingDetailRecovery, поэтому вызывающий код завершает обработку, не применяя ответ к новой карточке. Действующий отказ доступа сохраняет очистку своей карточки и приватного URL. Изменение не затрагивает bridge/queue/player authority.

Новый проверочный сценарий вызывает настоящую shared-функцию через тестовый export; задерживает clone().json, заменяет main либо меняет meetingId того же элемента и маршрут другой встречи, затем завершает чтение обычным JSON или ошибкой. Проверяет прежний DOM новой встречи, title/URL и отсутствие дальнейшего применения stale response вызывающим кодом. Отдельно проверяет действующий403: карточка удалена и адрес нейтрализован. Независимый запуск нового сценария до исправления падал на read-error с адресом /desktop/meetings вместо нового meeting route. После исправления local-recording-detail независимо прошёл в Chromium и WebKit. Более широкий набор повторно не запускался.

Чеклисты качества требований не менялись: requirements checked3/unchecked0, safety checked8/unchecked0, всего11/0. Их состояние не используется как evidence исполняемого исправления. Mac locked/GUI недоступен; установленный окончательный кандидат, реальный длительный звонок, будущий commit/PR SHA, обязательные GitHub checks и выпуск этой проверкой не приняты. Отчёт обновлён только в разрешённой reviewer-owned области.
