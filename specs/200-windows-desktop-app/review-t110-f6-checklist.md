# F200 / T110 — независимая проверка требований к F6 и фокусу

**Решение: NO-GO для начала продуктового исправления на проверенном снимке.** F6 укладывается в существующий T110 и может быть реализован после выполнения ворот. Текущая дорожка — `high-risk-product`: изменение маршрута клавиатуры к фоновой карточке и нативному Stop затрагивает доступность и управление записью.

Проверено только рабочее дерево `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, ветка `codex/200-windows-followup`, HEAD `3dfeaff5a6774ab12be781547e4a300f9ce2a46c`. Учитывались незакоммиченные и неотслеживаемые материалы. Проверка предварительных условий указала на активный F200. Проверены применимые требования [spec](spec.md), [plan](plan.md), [tasks](tasks.md), [quickstart](quickstart.md), контракты, [конституция](../../.specify/memory/constitution.md), [правила Spec Kit](../../docs/agent-guidance/spec-kit-flow.md) и [локальный навык](../../.agents/skills/speckit-implement/SKILL.md). Hooks реализации не запускались: это ревью.

## Ворота

| Ворота | Результат |
| --- | --- |
| Общий подсчёт, шаг 2 | **PASS по маркерам: 554/554, 0 открыто.** 218 файлов, из них 46 с пунктами, 172 без пунктов. В отслеживаемых файлах 492 пункта, в неотслеживаемых — 62. Это инвентаризация всех файлов и предметное ревью T110; чужие исторические решения и исходные прогоны не переаттестованы. Отдельного файла чек-листа T110/F6 нет. В [истории T117](checklists/t117-legacy-queue-gate-immutability-review.md#L57) общий NO-GO из-за CHK003–006 прямо помечен как прежний; актуальный итог его чек-листа — 6/6. Если снова появится хотя бы один открытый пункт в общем каталоге, шаг 2 требует остановить high-risk реализацию до независимого подтверждения; принятие риска пользователем не заменяет его. |
| Актуальный analyze, шаг 3 | **Не подтверждён.** PASS от [27 сентября](checklists/analyze-2026-09-27.md#L3) относится к прежнему снимку; [28 сентября](checklists/analyze-2026-09-28.md#L3) — к T104/T105/T109/T113. [Сверка T121](issue-map.md#L113) и [source review оболочки](review-2026-10-27-shell-lifetime.md#L3) также не покрывают нынешний T110/F6. Текущие tasks отличаются даже от HEAD, а сценарии прямого F6 и отрицательные проверки добавлены в рабочий Quickstart. Нужен `speckit-analyze` после текущих tasks, с трассировкой уточнённого маршрута, без открытых C/H и блокирующих уточнений. Настоящее ревью не выдаёт общего PASS analyze. |
| Ownership и порядок, шаги 4/8 | **Привязка есть, текущая сверка не подтверждена.** [T110 → #7344](issue-map.md#L102), запись об исходной синхронизации от 27 сентября. Это не подтверждение текущего открытого/согласованного владельца и актуальных доказательств для F6. Карта в одиночку не покрывает текущие 123 задачи (93 отмечены, 30 открыты); более поздние привязки встречаются в других документах. После analyze требуется сверить существующий #7344 и актуальные привязки исполняемых задач по шагу 4, без дубликата. [Phase 16](tasks.md#L478) ставит T110 после T108, запрещая параллельно менять общий AppMain. T108 остаётся [ ] и имеет лишь частичное доказательство; нет записи, что зависимая часть принята и AppMain передан T110. Подтвердить эту последовательность до правки; компонентный результат T108 не закрывает установленную приёмку. |
| Истёкшее исключение T117 | **Отдельный блок слияния/выпуска**, не самостоятельный запрет локального F6. [Контракт §8](contracts/windows-protected-local-custody.md#L442): старый читатель только в worker миграции, владелец T117/#7445, крайний срок 2026-11-01 UTC. [Сохранённый отчёт](validation-2026-11-03-master-preview.md#L234) фиксирует отказ PR metadata именно по сроку. [Правила](../../docs/agent-guidance/development-process.md#L188) требуют завершить снятие исключения до слияния/выпуска; цель `expired_exceptions=0`. Не продлевать срок автоматически, не открывать старый читатель для обычных операций и не удалять оригиналы. 6/6 по требованиям T117 не доказывает миграцию или снятие исключения. |

## Требования T110 и граница фокуса

| Требование | Что установлено |
| --- | --- |
| Фоновый Ask и индикатор не активируют GRAF; ручное управление остаётся доступным (FR-002, FR-015/016, SC-002/004/009) | Согласовано: [spec](spec.md#L57), [plan](plan.md#L650), [T110](tasks.md#L501), [матрица](parity-matrix.md#L463), [F277](contracts/f277-notifications-parity.md#L73). Показ и явное действие — разные события; F6 может переводить фокус, но не запускает, не останавливает запись и не меняет выбор. Однодейственный Stop остаётся видимым и доступным независимо от WebView и карточки. |
| Прямой F6 из нативной оболочки и из активной страницы кабинета; отдельно команда трея | [Quickstart](quickstart.md#L252) задаёт оба положения фокуса и отдельный маршрут трея. Plan/T110 задают общий клавиатурный путь; явная клавиша уточнена в Quickstart. Нет противоречия с F277: пункт трея явно обязателен, контракт не объявляет его единственным способом. В текущем [AppMain](../../apps/windows/RecApp/AppMain.cpp#L583) остался только корневой WinUI KeyDown; [изолированный RED](validation-2026-11-06-t110-notice-foreground.md#L68) показывает, что из WebView2 событие до него не доходит. SHA-256 AppMain совпадает с указанным в отчёте RED. Вызов focus(), выход из WebView2 по Tab и команда трея не засчитываются за прямой F6. |
| Отрицательные случаи и момент выдачи разрешения | Quickstart запрещает нативный перевод при отсутствии доступной поверхности, Shift+F6, удержании, фокусе вне GRAF и при устаревшем отложенном запросе. Действующий корневой обработчик не проверяет Shift/повтор; для карточки `focusBackgroundSurface()` возвращает true даже при отказе `focus()`. Это повод проверить единственный маршрут для обоих исходных положений, без двойного срабатывания и без поглощения клавиши в отрицательных случаях. Последняя редакция Quickstart требует отмены и после деактивации с возвратом в то же окно; одной сверки HWND недостаточно. Привязать отложенное действие к непрерывному периоду активности исходного окна и конкретному поколению карточки либо сеансу записи с доступным Stop. Закрытие, замена, смена окна или сеанса, исчезновение Stop и выход отзывают запрос; новый явный F6 работает для новой цели. |
| Возврат фокуса и различие карточки/индикатора | Есть **неоднозначность формулировки**: Quickstart безусловно обещает «Escape возвращает пользователя в исходное окно», F277 ограничивает возврат возможностями ОС и говорит о явно активированной карточке. Текущий [presenter](../../apps/windows/RecApp/Shell/RecordingNoticePresenter.cpp#L782) пытается вернуть предыдущее окно, только если карточка ещё была активна и исходное окно существует. Уточнить в требованиях: Escape закрывает карточку, возврат — при актуальном источнике и когда ОС допускает, без повторной активации поверх другого приложения; не распространять закрытие по Escape на обязательный индикатор/Stop. Для F6 с индикатором целевой результат — фокус на Stop, без его вызова. |
| Нативная граница | [FR-005/006](spec.md#L432) и действующий bridge не разрешают новый web-to-native intent для F6; [отчёт](validation-2026-11-06-t110-notice-foreground.md#L83) отдельно исключает доверие к сообщению страницы и глобальный перехват. Нативный ограниченный маршрут сам по себе не конфликтует с контрактом. Для варианта с очередью UI явно ограничить действие своим активным главным окном и допустимым контекстом; отдельно описать поведение вне страницы кабинета (auth/payment и нативная модальная панель), чтобы фокус не уходил из отдельного диалога по совпадению потока/корня. Технический стенд не вводит новое продуктовое полномочие. |
| Приёмка | [Стенд очереди](validation-2026-11-06-t110-notice-foreground.md#L135) даёт осуществимость и часть отрицательных контролей, не результат продуктового пути. [Дополнение о смене окна](validation-2026-11-06-t110-notice-foreground.md#L188) фиксирует отмену, даже если исходный HWND снова активен; это проверка стенда, не установленного GRAF. Для T110 всё ещё нужны точный установленный MSIX, реальный WebView2 и нативная кнопка, живые Ask/Always/manual Start, отсутствие смены foreground при показе/повторе и при отказе, физическая клавиатура с удержанием, мышь, экранный диктор, фокус и фактический однодейственный Stop, отдельный путь трея. T097/T063 и общие требования выпуска остаются самостоятельными. |

Чтобы снять NO-GO, закрепить область F6 и условия возврата, завершить текущий analyze и сверку задачи/зависимости T108. Для проверки после изменения сначала нужен причинный RED/GREEN именно маршрута продукта на одинаковом сценарии; затем отдельная приёмка установленного пакета. Доказательство целевого маршрута готовится пользователем отдельно и в этом отчёте не зачтено. Quickstart и отчёт стенда обновились параллельно во время ревью; прочитаны свежие изменения, они сохранены и не меняют NO-GO.

Маркеры сохранены. Код, нормативные документы, GitHub и VM не менялись; внешнее состояние и сырые журналы Windows не проверялись.

Контрольные SHA-256 рабочих входов: tasks `21ec466096d713d8dbbf5023c9a8669329f18ffaaf91026bb83024626c7497f3`, tasks из HEAD `2d32f436ec29dcf5cf792a6c182f963258a2a542db80f78bf7ee5bb3312c570d`, quickstart `27eb094337544d8e468274752ae43585309aaa58b6f7331c4d61d21c74b722d7`, AppMain `5d8b1e7dfcf1dc1ba3e3b59c1b6beb8a85ed066bbe579fb71b28fb1c82410c8d`.

## Инвентаризация всех файлов каталога checklists

Считаются только строки списка с маркерами Spec Kit, включая отступы. Файл без маркеров указан отдельно по статусу «без пунктов»; это не оценка содержания отчёта.

| Файл | Всего | Отмечено | Открыто | Статус |
| --- | ---: | ---: | ---: | --- |
| [advanced-routing.md](checklists/advanced-routing.md) | 14 | 14 | 0 | PASS |
| [analyze-2026-09-27.md](checklists/analyze-2026-09-27.md) | 0 | 0 | 0 | без пунктов |
| [analyze-2026-09-28.md](checklists/analyze-2026-09-28.md) | 0 | 0 | 0 | без пунктов |
| [audio-capture.md](checklists/audio-capture.md) | 24 | 24 | 0 | PASS |
| [calendar-launcher.md](checklists/calendar-launcher.md) | 5 | 5 | 0 | PASS |
| [calendar-operation.md](checklists/calendar-operation.md) | 8 | 8 | 0 | PASS |
| [calendar-wire.md](checklists/calendar-wire.md) | 5 | 5 | 0 | PASS |
| [cold-prefix-recovery.md](checklists/cold-prefix-recovery.md) | 47 | 47 | 0 | PASS |
| [packed-writer.md](checklists/packed-writer.md) | 12 | 12 | 0 | PASS |
| [privacy-pause.md](checklists/privacy-pause.md) | 12 | 12 | 0 | PASS |
| [requirements.md](checklists/requirements.md) | 22 | 22 | 0 | PASS |
| [research-2026-10-03-scalable-custody-proof.md](checklists/research-2026-10-03-scalable-custody-proof.md) | 0 | 0 | 0 | без пунктов |
| [research-2026-10-03-telemost-windows-handoff.md](checklists/research-2026-10-03-telemost-windows-handoff.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-09-26.md](checklists/review-2026-09-26.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-09-27.md](checklists/review-2026-09-27.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-09-28.md](checklists/review-2026-09-28.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-09-30.md](checklists/review-2026-09-30.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-encryption-plan.md](checklists/review-2026-10-01-encryption-plan.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-large-index.md](checklists/review-2026-10-01-large-index.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-medium-launch.md](checklists/review-2026-10-01-medium-launch.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-mixed-index.md](checklists/review-2026-10-01-mixed-index.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-native-playback.md](checklists/review-2026-10-01-native-playback.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-package-followup.md](checklists/review-2026-10-01-package-followup.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-protected-stop.md](checklists/review-2026-10-01-protected-stop.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-protected-stream-proof.md](checklists/review-2026-10-01-protected-stream-proof.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-publish-faults.md](checklists/review-2026-10-01-publish-faults.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-release-custody.md](checklists/review-2026-10-01-release-custody.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-resources.md](checklists/review-2026-10-01-resources.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-01-ui-parity.md](checklists/review-2026-10-01-ui-parity.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-bounded-hash.md](checklists/review-2026-10-02-bounded-hash.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-calendar-join-design.md](checklists/review-2026-10-02-calendar-join-design.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-custody-codec-gate.md](checklists/review-2026-10-02-custody-codec-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-custody-codec-source.md](checklists/review-2026-10-02-custody-codec-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-custody-durable-io-gate.md](checklists/review-2026-10-02-custody-durable-io-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-custody-files-source.md](checklists/review-2026-10-02-custody-files-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-custody-reader-gate.md](checklists/review-2026-10-02-custody-reader-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-custody-reader-source.md](checklists/review-2026-10-02-custody-reader-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-custody-resources-gate.md](checklists/review-2026-10-02-custody-resources-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-custody-resources-source.md](checklists/review-2026-10-02-custody-resources-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-custody-snapshot-gate.md](checklists/review-2026-10-02-custody-snapshot-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-custody-snapshot-source.md](checklists/review-2026-10-02-custody-snapshot-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-native-hash-faults.md](checklists/review-2026-10-02-native-hash-faults.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-phase0-exit.md](checklists/review-2026-10-02-phase0-exit.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-protected-custody-design.md](checklists/review-2026-10-02-protected-custody-design.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-02-storage-independent.md](checklists/review-2026-10-02-storage-independent.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-billing-route-gate.md](checklists/review-2026-10-03-billing-route-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-billing-route-source.md](checklists/review-2026-10-03-billing-route-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-cng-pseudo-handle-gate.md](checklists/review-2026-10-03-cng-pseudo-handle-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-cng-pseudo-handle-source.md](checklists/review-2026-10-03-cng-pseudo-handle-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-custody-media-writer-gate.md](checklists/review-2026-10-03-custody-media-writer-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-custody-media-writer-source.md](checklists/review-2026-10-03-custody-media-writer-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-custody-metadata-source.md](checklists/review-2026-10-03-custody-metadata-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-custody-writer-gate.md](checklists/review-2026-10-03-custody-writer-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-packed-codec-gate.md](checklists/review-2026-10-03-packed-codec-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-packed-codec-source.md](checklists/review-2026-10-03-packed-codec-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-packed-custody-amendment.md](checklists/review-2026-10-03-packed-custody-amendment.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-packed-owner-gate.md](checklists/review-2026-10-03-packed-owner-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-packed-owner-source.md](checklists/review-2026-10-03-packed-owner-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-packed-tree-gate.md](checklists/review-2026-10-03-packed-tree-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-03-packed-tree-source.md](checklists/review-2026-10-03-packed-tree-source.md) | 38 | 38 | 0 | PASS |
| [review-2026-10-03-packed-wire-source.md](checklists/review-2026-10-03-packed-wire-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-04-calendar-join-gate.md](checklists/review-2026-10-04-calendar-join-gate.md) | 12 | 12 | 0 | PASS |
| [review-2026-10-04-calendar-operation-gate.md](checklists/review-2026-10-04-calendar-operation-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-04-calendar-operation-source.md](checklists/review-2026-10-04-calendar-operation-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-04-calendar-resolver-gate.md](checklists/review-2026-10-04-calendar-resolver-gate.md) | 12 | 12 | 0 | PASS |
| [review-2026-10-04-calendar-resolver-source.md](checklists/review-2026-10-04-calendar-resolver-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-04-calendar-response-source.md](checklists/review-2026-10-04-calendar-response-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-04-calendar-url-gate.md](checklists/review-2026-10-04-calendar-url-gate.md) | 12 | 12 | 0 | PASS |
| [review-2026-10-04-calendar-url-source.md](checklists/review-2026-10-04-calendar-url-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-04-manifest-cap-source.md](checklists/review-2026-10-04-manifest-cap-source.md) | 9 | 9 | 0 | PASS |
| [review-2026-10-04-packed-cadence-gate.md](checklists/review-2026-10-04-packed-cadence-gate.md) | 12 | 12 | 0 | PASS |
| [review-2026-10-04-packed-cadence-source.md](checklists/review-2026-10-04-packed-cadence-source.md) | 18 | 18 | 0 | PASS |
| [review-2026-10-04-packed-live-writer-gate.md](checklists/review-2026-10-04-packed-live-writer-gate.md) | 14 | 14 | 0 | PASS |
| [review-2026-10-04-packed-live-writer-source.md](checklists/review-2026-10-04-packed-live-writer-source.md) | 9 | 9 | 0 | PASS |
| [review-2026-10-04-packed-package-gate.md](checklists/review-2026-10-04-packed-package-gate.md) | 12 | 12 | 0 | PASS |
| [review-2026-10-04-packed-reader-gate.md](checklists/review-2026-10-04-packed-reader-gate.md) | 20 | 20 | 0 | PASS |
| [review-2026-10-04-packed-reader-source.md](checklists/review-2026-10-04-packed-reader-source.md) | 9 | 9 | 0 | PASS |
| [review-2026-10-04-packed-resize-gate.md](checklists/review-2026-10-04-packed-resize-gate.md) | 14 | 14 | 0 | PASS |
| [review-2026-10-04-packed-resize-source.md](checklists/review-2026-10-04-packed-resize-source.md) | 9 | 9 | 0 | PASS |
| [review-2026-10-04-packed-rewrite-gate.md](checklists/review-2026-10-04-packed-rewrite-gate.md) | 16 | 16 | 0 | PASS |
| [review-2026-10-04-packed-rewrite-source.md](checklists/review-2026-10-04-packed-rewrite-source.md) | 9 | 9 | 0 | PASS |
| [review-2026-10-04-packed-tail-gate.md](checklists/review-2026-10-04-packed-tail-gate.md) | 14 | 14 | 0 | PASS |
| [review-2026-10-04-packed-tail-source.md](checklists/review-2026-10-04-packed-tail-source.md) | 9 | 9 | 0 | PASS |
| [review-2026-10-04-packed-writer-gate.md](checklists/review-2026-10-04-packed-writer-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-04-packed-writer-source.md](checklists/review-2026-10-04-packed-writer-source.md) | 18 | 18 | 0 | PASS |
| [review-2026-10-04-privacy-pause-design.md](checklists/review-2026-10-04-privacy-pause-design.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-05-calendar-host-source.md](checklists/review-2026-10-05-calendar-host-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-05-calendar-launcher-gate.md](checklists/review-2026-10-05-calendar-launcher-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-05-calendar-launcher-source.md](checklists/review-2026-10-05-calendar-launcher-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-05-calendar-owner-source.md](checklists/review-2026-10-05-calendar-owner-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-05-calendar-shim-source.md](checklists/review-2026-10-05-calendar-shim-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-05-calendar-wire-gate.md](checklists/review-2026-10-05-calendar-wire-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-05-calendar-wire-source.md](checklists/review-2026-10-05-calendar-wire-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-aac-payload-red-source.md](checklists/review-2026-10-06-aac-payload-red-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-bootstrap-codec-gate.md](checklists/review-2026-10-06-bootstrap-codec-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-bootstrap-codec-source.md](checklists/review-2026-10-06-bootstrap-codec-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-bootstrap-discovery-gate.md](checklists/review-2026-10-06-bootstrap-discovery-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-bootstrap-discovery-source.md](checklists/review-2026-10-06-bootstrap-discovery-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-bootstrap-pair-gate.md](checklists/review-2026-10-06-bootstrap-pair-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-bootstrap-pair-source.md](checklists/review-2026-10-06-bootstrap-pair-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-calendar-menu-source.md](checklists/review-2026-10-06-calendar-menu-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-metadata-pair-gate.md](checklists/review-2026-10-06-metadata-pair-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-metadata-pair-source.md](checklists/review-2026-10-06-metadata-pair-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-migration-codec-gate.md](checklists/review-2026-10-06-migration-codec-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-migration-codec-source.md](checklists/review-2026-10-06-migration-codec-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-migration-history-gate.md](checklists/review-2026-10-06-migration-history-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-migration-history-source.md](checklists/review-2026-10-06-migration-history-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-package-assembly-gate.md](checklists/review-2026-10-06-package-assembly-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-package-assembly-source.md](checklists/review-2026-10-06-package-assembly-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-package-authority-gate.md](checklists/review-2026-10-06-package-authority-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-package-format-gate.md](checklists/review-2026-10-06-package-format-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-package-format-source.md](checklists/review-2026-10-06-package-format-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-package-members-gate.md](checklists/review-2026-10-06-package-members-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-package-members-source.md](checklists/review-2026-10-06-package-members-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-protected-aac-consumer-source.md](checklists/review-2026-10-06-protected-aac-consumer-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-protected-inspection-job-gate.md](checklists/review-2026-10-06-protected-inspection-job-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-protected-inspector-gate.md](checklists/review-2026-10-06-protected-inspector-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-protected-package-consumer-gate.md](checklists/review-2026-10-06-protected-package-consumer-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-protected-package-consumer-source.md](checklists/review-2026-10-06-protected-package-consumer-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-protected-queue-input-correction-source.md](checklists/review-2026-10-06-protected-queue-input-correction-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-protected-queue-input-gate.md](checklists/review-2026-10-06-protected-queue-input-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-protected-queue-input-source.md](checklists/review-2026-10-06-protected-queue-input-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-protected-v5-inspector-gate.md](checklists/review-2026-10-06-protected-v5-inspector-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-protected-v5-inspector-source.md](checklists/review-2026-10-06-protected-v5-inspector-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-queue-fields-gate.md](checklists/review-2026-10-06-queue-fields-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-queue-fields-path-correction-source.md](checklists/review-2026-10-06-queue-fields-path-correction-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-queue-fields-source.md](checklists/review-2026-10-06-queue-fields-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-queue-load-candidate-correction-source.md](checklists/review-2026-10-06-queue-load-candidate-correction-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-queue-load-candidate-gate.md](checklists/review-2026-10-06-queue-load-candidate-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-queue-load-candidate-source.md](checklists/review-2026-10-06-queue-load-candidate-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-recovery-wait-gate.md](checklists/review-2026-10-06-recovery-wait-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-recovery-wait-source.md](checklists/review-2026-10-06-recovery-wait-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-retained-root-source.md](checklists/review-2026-10-06-retained-root-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-06-winui-include-order-source.md](checklists/review-2026-10-06-winui-include-order-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-block-name-construction-gate.md](checklists/review-2026-10-07-block-name-construction-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-block-path-composition-gate.md](checklists/review-2026-10-07-block-path-composition-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-bootstrap-intent-link-gate.md](checklists/review-2026-10-07-bootstrap-intent-link-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-bootstrap-intent-link-source.md](checklists/review-2026-10-07-bootstrap-intent-link-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-custody-directory-relocation-correction-gate.md](checklists/review-2026-10-07-custody-directory-relocation-correction-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-custody-directory-relocation-gate.md](checklists/review-2026-10-07-custody-directory-relocation-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-custody-index-name-read-path-gate.md](checklists/review-2026-10-07-custody-index-name-read-path-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-custody-open-path-composition-gate.md](checklists/review-2026-10-07-custody-open-path-composition-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-custody-package-ascii-path-gate.md](checklists/review-2026-10-07-custody-package-ascii-path-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-custody-path-iteration-gate.md](checklists/review-2026-10-07-custody-path-iteration-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-custody-security-string-construction-gate.md](checklists/review-2026-10-07-custody-security-string-construction-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-custody-state-path-initialization-gate.md](checklists/review-2026-10-07-custody-state-path-initialization-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-custody-state-vector-initialization-gate.md](checklists/review-2026-10-07-custody-state-vector-initialization-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-migration-pair-gate.md](checklists/review-2026-10-07-migration-pair-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-migration-pair-shared-validation.md](checklists/review-2026-10-07-migration-pair-shared-validation.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-migration-pair-source.md](checklists/review-2026-10-07-migration-pair-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-migration-v2-codec-gate.md](checklists/review-2026-10-07-migration-v2-codec-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-migration-v2-codec-source.md](checklists/review-2026-10-07-migration-v2-codec-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-native-startup-correction-source.md](checklists/review-2026-10-07-native-startup-correction-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-native-startup-gate.md](checklists/review-2026-10-07-native-startup-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-native-startup-source.md](checklists/review-2026-10-07-native-startup-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-protected-flow-integration-gate.md](checklists/review-2026-10-07-protected-flow-integration-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-protected-flow-integration-source.md](checklists/review-2026-10-07-protected-flow-integration-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-protected-queue-candidate-gate.md](checklists/review-2026-10-07-protected-queue-candidate-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-protected-queue-candidate-source.md](checklists/review-2026-10-07-protected-queue-candidate-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-protected-queue-recovery-gate.md](checklists/review-2026-10-07-protected-queue-recovery-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-protected-queue-recovery-source.md](checklists/review-2026-10-07-protected-queue-recovery-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-protected-v5-vertical-gate.md](checklists/review-2026-10-07-protected-v5-vertical-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-sha256-empty-construction-gate.md](checklists/review-2026-10-07-sha256-empty-construction-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-07-sha256-return-copy-gate.md](checklists/review-2026-10-07-sha256-return-copy-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-custody-pressure-scope-construction.md](checklists/review-2026-10-10-custody-pressure-scope-construction.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-custody-wipe-default-source-runtime.md](checklists/review-2026-10-10-custody-wipe-default-source-runtime.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-custody-wipe-gate.md](checklists/review-2026-10-10-custody-wipe-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-custody-wipe-red-production-gate.md](checklists/review-2026-10-10-custody-wipe-red-production-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-custody-wipe-source-runtime.md](checklists/review-2026-10-10-custody-wipe-source-runtime.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-custody-wipe-source.md](checklists/review-2026-10-10-custody-wipe-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-http-account-quota-source-runtime.md](checklists/review-2026-10-10-http-account-quota-source-runtime.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-http-all-checklist-gate.md](checklists/review-2026-10-10-http-all-checklist-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-http-control-construction.md](checklists/review-2026-10-10-http-control-construction.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-http-owned-data-gate.md](checklists/review-2026-10-10-http-owned-data-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-http-owned-data-source-runtime.md](checklists/review-2026-10-10-http-owned-data-source-runtime.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-http-owned-data-source.md](checklists/review-2026-10-10-http-owned-data-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-http-post-ack-progress-source.md](checklists/review-2026-10-10-http-post-ack-progress-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-http-preowned-terminal-source-runtime.md](checklists/review-2026-10-10-http-preowned-terminal-source-runtime.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-http-response-quota-source-runtime.md](checklists/review-2026-10-10-http-response-quota-source-runtime.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-http-test-and-worker-teardown.md](checklists/review-2026-10-10-http-test-and-worker-teardown.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-metadata-final-transfer-runtime-gate.md](checklists/review-2026-10-10-metadata-final-transfer-runtime-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-protected-http-body-source.md](checklists/review-2026-10-10-protected-http-body-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-protected-http-integration-gate.md](checklists/review-2026-10-10-protected-http-integration-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-protected-http-red-source.md](checklists/review-2026-10-10-protected-http-red-source.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-protected-package-discovery-gate.md](checklists/review-2026-10-10-protected-package-discovery-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-10-winhttp-wide-quota-source-runtime.md](checklists/review-2026-10-10-winhttp-wide-quota-source-runtime.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-11-cold-inspection-concurrency-gate.md](checklists/review-2026-10-11-cold-inspection-concurrency-gate.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-11-protected-playback-drain-foundation.md](checklists/review-2026-10-11-protected-playback-drain-foundation.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-12-live-born-inspection-source-runtime.md](checklists/review-2026-10-12-live-born-inspection-source-runtime.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-12-privacy-pause-requirements-refresh.md](checklists/review-2026-10-12-privacy-pause-requirements-refresh.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-12-protected-media-engine-source-runtime.md](checklists/review-2026-10-12-protected-media-engine-source-runtime.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-12-protected-playback-consumer-source-runtime.md](checklists/review-2026-10-12-protected-playback-consumer-source-runtime.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-12-retained-package-revalidation-source-runtime.md](checklists/review-2026-10-12-retained-package-revalidation-source-runtime.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-15-round410-privacy-history-requirements.md](checklists/review-2026-10-15-round410-privacy-history-requirements.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-10-16-start-owner-requirements.md](checklists/review-2026-10-16-start-owner-requirements.md) | 0 | 0 | 0 | без пунктов |
| [review-2026-11-05-t117-missing-directory.md](checklists/review-2026-11-05-t117-missing-directory.md) | 10 | 10 | 0 | PASS |
| [security.md](checklists/security.md) | 27 | 27 | 0 | PASS |
| [start-owner-recovery.md](checklists/start-owner-recovery.md) | 10 | 10 | 0 | PASS |
| [t088-session-platform.md](checklists/t088-session-platform.md) | 7 | 7 | 0 | PASS |
| [t097-export-dialog-revocation.md](checklists/t097-export-dialog-revocation.md) | 4 | 4 | 0 | PASS |
| [t097-profile-decorative-labels-review.md](checklists/t097-profile-decorative-labels-review.md) | 0 | 0 | 0 | без пунктов |
| [t097-profile-decorative-labels.md](checklists/t097-profile-decorative-labels.md) | 3 | 3 | 0 | PASS |
| [t117-fresh-queue-publication-design-review.md](checklists/t117-fresh-queue-publication-design-review.md) | 0 | 0 | 0 | без пунктов |
| [t117-fresh-queue-publication-design.md](checklists/t117-fresh-queue-publication-design.md) | 6 | 6 | 0 | PASS |
| [t117-legacy-queue-gate-immutability-review.md](checklists/t117-legacy-queue-gate-immutability-review.md) | 0 | 0 | 0 | без пунктов |
| [t117-legacy-queue-gate-immutability.md](checklists/t117-legacy-queue-gate-immutability.md) | 6 | 6 | 0 | PASS |
| [t120-stale-position-review-report.md](checklists/t120-stale-position-review-report.md) | 0 | 0 | 0 | без пунктов |
| [t120-stale-position-review.md](checklists/t120-stale-position-review.md) | 5 | 5 | 0 | PASS |
| [t121-addressed-position.md](checklists/t121-addressed-position.md) | 3 | 3 | 0 | PASS |
| [t121-shared-cookie-position.md](checklists/t121-shared-cookie-position.md) | 3 | 3 | 0 | PASS |
| [t121-shared-meeting.md](checklists/t121-shared-meeting.md) | 8 | 8 | 0 | PASS |
| [t121-windows-auth-continuation.md](checklists/t121-windows-auth-continuation.md) | 4 | 4 | 0 | PASS |
| [t121-windows-inbound-position.md](checklists/t121-windows-inbound-position.md) | 3 | 3 | 0 | PASS |
| [t121-windows-recovery-position.md](checklists/t121-windows-recovery-position.md) | 3 | 3 | 0 | PASS |
| [t123-export-save-review.md](checklists/t123-export-save-review.md) | 0 | 0 | 0 | без пунктов |
| [t123-export-save.md](checklists/t123-export-save.md) | 7 | 7 | 0 | PASS |
| [ux.md](checklists/ux.md) | 25 | 25 | 0 | PASS |
| [windows-pr-verification.md](checklists/windows-pr-verification.md) | 5 | 5 | 0 | PASS |
| **Итого** | **554** | **554** | **0** | **PASS по маркерам** |
