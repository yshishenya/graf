# F259 — бэклог проверки и исправления

Статус: подготовлен для уточнения и планирования. Все B-пункты ниже открыты; это направления будущих `tasks.md`, а не отметки реализации.

Родитель: [#6827](https://github.com/yshishenya/graf/issues/6827). Спецификация: [spec.md](spec.md). Полный реестр: [issue-inventory.md](issue-inventory.md).

Снимок GitHub: **279 исходных открытых issues**, получен 2026-09-08T16:13:53+00:00; новый родитель #6827 не включён в собственный реестр. База: `e81b412dff920cc29ed37de60be13dd8fc4d1c43` (`origin/master`, выпуск v2026.09.08.1). Снимок не означает повторную приёмку всех задач.

## Порядок работы

1. B000: уточнить объём выбранного этапа, владельцев, среды и зависимые решения; пройти Spec Kit перед реализацией.
2. Сначала риски данных и обязательные P0: B002/B004/B009; готовность окружения определяет возможность исполнения, но не отменяет приоритет исходного issue.
3. Затем основной пользовательский путь: B001/B003/B005/B006/B007. B001 координируется с активным B027.
4. Биллинг, контакты, качество и эксплуатация: B008/B010–B016; инфраструктурные дефекты процесса: B017–B022.
5. B023–B027 — существующие владельцы реализации и отдельная очередь проверки интеграции. Они не блокируют независимый разбор других направлений.
6. B028: учесть тестовые объекты; B029: финальная повторная сверка, доказательства и исходные issues.

## Общий порядок для каждого исходного issue

Прочитать актуальные body/comments и содержательно сопоставить задачу → воспроизвести/проверить на нужной версии → при провале установить причину и всех потребителей → выполнить минимальное исправление в ветке владельца → повторить исходный сценарий и затронутые регрессии → review и требуемые CI/выпуск → согласовать `tasks.md`, evidence и состояние GitHub.

Критерий направления ниже дополняет все критерии каждого issue в реестре. Ссылки на родительские задачи не создают рекурсивную зависимость. Для результата фиксировать: issue, версия/SHA, среда, сценарий, expected/actual, результат (пройден/не пройден/ожидает условия), безопасное evidence, остаток, PR и решение владельца при необходимости.

COMPLETED требует всей приёмки и штатного `scripts/validate-issue-closeout.py`; obsolete/duplicate — содержательного обоснования NOT_PLANNED, без фиктивного `[X]`. Перед каждой записью перечитать live state/comment, при ограничении GitHub сохранить позицию и не дублировать комментарий.

- [ ] **B000 — подготовить первый исполняемый этап.** Уточнить scope и владельца; пройти `clarify → plan → checklist → tasks → analyze → taskstoissues`. Выбрать конкретные файлы только после чтения действующего потока. Риск реализации high-risk-product; проверки зависят от затронутого домена. Текущая спецификация не разрешает обход обязательных gates. Готово: задачи этапа зависимостно упорядочены, критерии сопоставлены исходным issues и independent review завершён.

## Направления

### B001 — Запуск записи и календарные уведомления

- [ ] **P1; F249; 9 issues.**

**Известно:** На production v2026.09.08.1 нажатия Start в меню открывали окно, но запись не начиналась; Start в главном календарном предложении дал положительный контроль. Причина на этом этапе не установлена. Уведомления production GRAF выключены; доставка баннера не доказана.

**Проверить и при необходимости исправить:** Сначала сверить результат F6788/#6825. Проверить #6780 при скрытом окне, активном предложении, повторном нажатии; #6779 — действие уведомления встречи без ссылки; #6758 — перенос встречи и возврат разрешения. Для #6678/#6686 нужны разрешения и Focus; #6689 — полный аппаратный путь; #6690 — пять пользовательских сценариев и исходный p95; #6691/#6635 — общая приёмка. Запрос о включении production уведомлений остаётся без ответа; состояние системы не менять.

**Готово, когда:** На принятой версии все исходные сценарии F249 подтверждены отдельно. Команды выполняются ровно один раз; индикатор/Stop доступны; действие no-link правдиво; старые напоминания не повторяются. Исправление берётся из F6788, параллельный дубль не создаётся.

**Исходные задачи:** [#6635](https://github.com/yshishenya/graf/issues/6635), [#6678](https://github.com/yshishenya/graf/issues/6678), [#6686](https://github.com/yshishenya/graf/issues/6686), [#6689](https://github.com/yshishenya/graf/issues/6689), [#6690](https://github.com/yshishenya/graf/issues/6690), [#6691](https://github.com/yshishenya/graf/issues/6691), [#6758](https://github.com/yshishenya/graf/issues/6758), [#6779](https://github.com/yshishenya/graf/issues/6779), [#6780](https://github.com/yshishenya/graf/issues/6780).

### B002 — Сохранность локальных записей и отдельные инциденты

- [X] **P1; F114; 3 issues.**

**Результат:** дальнейший поиск трёх записей отменён владельцем после ограниченной локальной проверки. PR #6910 включён в master; все три issues закрыты как NOT_PLANNED. Восстановление либо полная утрата не заявляются; подробности в support-triage.md.

**Известно:** #4460/#4535 сообщают local_artifacts_unavailable; #5268 — retention_expired.local_retained. Давность сообщения не доказывает восстановление.

**Проверить и при необходимости исправить:** Разобрать каждый инцидент отдельно: доступность файлов, серверный статус и возможность восстановления/отправки. Использовать только безопасные метаданные; сначала сохранить доступные артефакты. Решение об удалении или признании утраты требует владельца.

**Готово, когда:** Для каждого из трёх случаев установлены фактическая судьба записи и допустимое действие, восстановление проверено либо зафиксирована честная граница. Ни один инцидент не закрыт общим успешным smoke.

**Исходные задачи:** [#4460](https://github.com/yshishenya/graf/issues/4460), [#4535](https://github.com/yshishenya/graf/issues/4535), [#5268](https://github.com/yshishenya/graf/issues/5268).

### B003 — Сквозной путь запись → отправка → просмотр

- [ ] **P1; F052; 2 issues.**

**Известно:** Недавние 17 секунд доказывают только запись, локальное сохранение и отправку; просмотр и результат той же записи не подтверждены.

**Проверить и при необходимости исправить:** В единственном GRAF Dev пройти #1818 на тестовой записи; связать с metadata probe #1819: specs/052-mvp-live-ui-proof/evidence/production-owner-journey-probe.py. Отдельно сверить production candidate без вывода содержимого встречи.

**Готово, когда:** Один связанный прогон доказывает запись/Stop/upload/review, playback/timeline и ожидаемые результаты. Для #1819 сохранены безопасные счётчики и точная версия.

**Исходные задачи:** [#1818](https://github.com/yshishenya/graf/issues/1818), [#1819](https://github.com/yshishenya/graf/issues/1819).

### B004 — Часовой установленный macOS pipeline

- [ ] **P0; F106; 1 issues.**

**Известно:** #3688 требует реальный 60-минутный прогон; модель дрейфа часов и короткая запись не заменяют аппаратную проверку.

**Проверить и при необходимости исправить:** Прочитать исходную матрицу T063; подготовить устройство, источники звука и тестовый материал. Проверить длительность, целостность канонического WAV/M4A, временную шкалу и единственность задания обработки.

**Готово, когда:** Есть непрерывный аппаратный прогон не менее 60 минут на указанной установленной версии с выполнением всех критериев T063, без возврата удалённых способов маршрутизации.

**Исходные задачи:** [#3688](https://github.com/yshishenya/graf/issues/3688).

### B005 — Восстановление обработки и правдивые состояния

- [ ] **P1; F206; 3 issues.**

**Известно:** Открыты review/replay и полная приёмка web/embedded: pending, retry countdown, terminal, success. Общий release не закрывает эти матрицы.

**Проверить и при необходимости исправить:** Пройти quickstart F206: valid/recoverable corrupt/no-archive/terminal, timeout/no-speech, скрытое окно, worker restart и replay, один provider job/idempotency. Опасные повреждения воспроизводить в изолированной среде; production сценарий определять отдельно, без порчи пользовательских данных.

**Готово, когда:** #5893 получает scoped/replay/current-SHA evidence; #5895 — все четыре состояния в web и embedded; #5896 — отдельную production приёмку и требуемый выпуск.

**Исходные задачи:** [#5893](https://github.com/yshishenya/graf/issues/5893), [#5895](https://github.com/yshishenya/graf/issues/5895), [#5896](https://github.com/yshishenya/graf/issues/5896).

### B006 — Пустой экран после обновления Sparkle

- [ ] **P1; F179; 1 issues.**

**Известно:** #5472 относится к историческому дефекту обновления, а нынешний F179/T001 в master — к инвентарю лендинга. Это ложное совпадение, не доказательство исправления.

**Проверить и при необходимости исправить:** Восстановить содержательную связь issue с исходной реализацией. При доступном официальном обновлении проверить Developer ID → Developer ID relaunch wide/compact, сессию, TCC, отсутствие лишних WebViews/navigation и recovery после auth/network ошибки.

**Готово, когда:** Приложение после реального обновления открывается без Reload; все исходные переходы подтверждены на конкретных версиях. Текущий работающий экран не засчитывается за update/relaunch.

**Исходные задачи:** [#5472](https://github.com/yshishenya/graf/issues/5472).

### B007 — Вход, привязка провайдера и история переходов

- [ ] **P1; F136; 7 issues.**

**Известно:** specs/136-auth-navigation-recovery отсутствует в master. F180 и F241 покрывают только часть требований; семь issues сохраняют самостоятельные критерии.

**Проверить и при необходимости исправить:** Восстановить владельца задач по истории. Проверить login vs linking (#4731), сброс history только после смены session (#4732), порядок session/route (#4733), кнопки после смены session (#4737), сохранение session при linking (#4738), Settings POST/linking (#4739), полную ручную OAuth-матрицу (#4743).

**Готово, когда:** Все семь сценариев имеют отдельный результат на указанной версии, включая отмену и ошибки провайдера; нет потери сессии или ошибочного доступа через старый маршрут.

**Исходные задачи:** [#4731](https://github.com/yshishenya/graf/issues/4731), [#4732](https://github.com/yshishenya/graf/issues/4732), [#4733](https://github.com/yshishenya/graf/issues/4733), [#4737](https://github.com/yshishenya/graf/issues/4737), [#4738](https://github.com/yshishenya/graf/issues/4738), [#4739](https://github.com/yshishenya/graf/issues/4739), [#4743](https://github.com/yshishenya/graf/issues/4743).

### B008 — Незавершённые функции и приёмка биллинга

- [ ] **P1; F140; 16 issues.**

**Известно:** У части исторически выполненных helpers не было подтверждённых действующих потребителей. Остались runtime, продуктовые, финансовые и review требования.

**Проверить и при необходимости исправить:** Сопоставить каждое из 16 issues с реальными вызовами: account handoff, co-termed storage, renewal/failure и billing notifications, referral maturity/cap/reversal, fair-use, test-shop E2E, provider polling/reconciliation, monitoring/runbooks и security/UX review. Для сегмента, цен и upgrade copy получить решения владельца. Сначала sandbox; реальный платёж отдельно.

**Готово, когда:** Каждый критерий исходных 16 issues проверен в действующем пути, а не только в helper-тесте. Финансовые решения записаны; не завершённый платёж/owner gate явно остаётся открытым.

**Исходные задачи:** [#4877](https://github.com/yshishenya/graf/issues/4877), [#4897](https://github.com/yshishenya/graf/issues/4897), [#4903](https://github.com/yshishenya/graf/issues/4903), [#4917](https://github.com/yshishenya/graf/issues/4917), [#4922](https://github.com/yshishenya/graf/issues/4922), [#4926](https://github.com/yshishenya/graf/issues/4926), [#4928](https://github.com/yshishenya/graf/issues/4928), [#4930](https://github.com/yshishenya/graf/issues/4930), [#4932](https://github.com/yshishenya/graf/issues/4932), [#4933](https://github.com/yshishenya/graf/issues/4933), [#4936](https://github.com/yshishenya/graf/issues/4936), [#4937](https://github.com/yshishenya/graf/issues/4937), [#4938](https://github.com/yshishenya/graf/issues/4938), [#5017](https://github.com/yshishenya/graf/issues/5017), [#5018](https://github.com/yshishenya/graf/issues/5018), [#5019](https://github.com/yshishenya/graf/issues/5019).

### B009 — Решения по размещению данных и оплате

- [ ] **P0; F142; 2 issues.**

**Известно:** #5092 требует решения о размещении данных и трансграничном контуре; #5093 — каталога, YooKassa и правил оплаты.

**Проверить и при необходимости исправить:** Подготовить конкретный перечень размещения/передач и платежных правил из действующей системы. Зафиксировать решение владельца и требуемое подтверждение провайдера; не подменять согласование техническим smoke.

**Готово, когда:** Оба решения существуют в явном виде, охватывают фактический контур и связаны с соответствующими исходными критериями. Пока решения нет — зависимость, а не дефект с мнимым исправлением.

**Исходные задачи:** [#5092](https://github.com/yshishenya/graf/issues/5092), [#5093](https://github.com/yshishenya/graf/issues/5093).

### B010 — Биллинг в установленном приложении

- [ ] **P1; F210; 2 issues.**

**Известно:** Browser surface matrix и CSS zoom F255 не доказывают native minimum/standard/fullscreen × inspector collapsed/expanded.

**Проверить и при необходимости исправить:** В GRAF Dev выполнить шесть сочетаний T017/#5961 на одной сборке, проверить читаемость, действия, прокрутку и доступность без финальной оплаты. Затем выполнить T018/#5962: согласование evidence и требуемый CI.

**Готово, когда:** Шесть native состояний приняты на точной версии; зависимая T018 не закрыта раньше T017.

**Исходные задачи:** [#5961](https://github.com/yshishenya/graf/issues/5961), [#5962](https://github.com/yshishenya/graf/issues/5962).

### B011 — Контакты, приглашения и реферальный цикл

- [ ] **P1; F125; 7 issues.**

**Известно:** Семь открытых задач #4448–#4454 сохраняют требования к lifecycle, scopes и защите адресной книги.

**Проверить и при необходимости исправить:** Прочитать критерии каждой задачи; проверить ограниченный picker, отсутствие скрытой полной синхронизации контактов, scopes, referral lifecycle, безопасную аналитику только по метаданным и rollback. Реальную рассылку выполнять только при отдельном разрешении.

**Готово, когда:** Все семь задач сопоставлены с действующим потоком, доступ и отзыв проверены, нет неявного импорта адресной книги или выдачи прав по приглашённому roster.

**Исходные задачи:** [#4448](https://github.com/yshishenya/graf/issues/4448), [#4449](https://github.com/yshishenya/graf/issues/4449), [#4450](https://github.com/yshishenya/graf/issues/4450), [#4451](https://github.com/yshishenya/graf/issues/4451), [#4452](https://github.com/yshishenya/graf/issues/4452), [#4453](https://github.com/yshishenya/graf/issues/4453), [#4454](https://github.com/yshishenya/graf/issues/4454).

### B012 — Поддерживаемые приложения на живых звонках

- [ ] **P2; F119; 1 issues.**

**Известно:** #3992 требует проверки реально включённых сторонних приложений; синтетический capture её не заменяет.

**Проверить и при необходимости исправить:** Составить матрицу по исходному T008, согласовать участников тестового звонка и пройти обнаружение/включение/запись/завершение на поддерживаемых приложениях.

**Готово, когда:** Для каждого требуемого приложения указан результат, версия и ограничения. Непроверенное приложение не помечено принятым.

**Исходные задачи:** [#3992](https://github.com/yshishenya/graf/issues/3992).

### B013 — Удобство экспорта для пользователей

- [ ] **P2; F120; 1 issues.**

**Известно:** #4083 требует проверки с представителями пользователей, а не только правильного файла экспорта.

**Проверить и при необходимости исправить:** Подготовить тестовые встречи и задания по исходному T059; согласовать участников, собрать наблюдения о поиске и использовании экспорта, исправить воспроизводимые препятствия.

**Готово, когда:** Проведена предусмотренная исходной задачей пользовательская проверка; замечания разрешены либо явно согласованы. Успешная загрузка файла не заменяет приёмку удобства.

**Исходные задачи:** [#4083](https://github.com/yshishenya/graf/issues/4083).

### B014 — Качество и задержка девяти форматов итогов

- [ ] **P1; F181; 1 issues.**

**Известно:** #5513 оставляет human usefulness/pairwise и version-bound Temporal/private publication; старые синтетические 18/18 и 9/9 недостаточны.

**Проверить и при необходимости исправить:** На согласованном тестовом наборе закрепить точную версию конфигурации, проверить девять форматов, задержку и полноту, независимую полезность/попарную оценку и приватную публикацию через Temporal. Не выгружать частные встречи в отчёт.

**Готово, когда:** Все девять форматов покрыты требуемой матрицей качества/задержки и человеческой оценкой; повторные/intermittent сбои отражены честно, доказательства принадлежат одной версии.

**Исходные задачи:** [#5513](https://github.com/yshishenya/graf/issues/5513).

### B015 — Эксплуатационная приёмка PostHog

- [ ] **P1; F096; 2 issues.**

**Известно:** Health/backup не закрывают #3857; #3860 зависит от всей эксплуатационной приёмки.

**Проверить и при необходимости исправить:** Проверить RBAC/audit, явное решение MFA, retention/deletion, свежесть dashboards/goals, thresholds/alerts и rollback. Исторический отказ от MFA не объявлять одобрением всех security критериев; настройки не менять без соответствующего решения.

**Готово, когда:** #3857 получает результат по каждому пункту; только затем #3860 — согласованные tracker/review/release/receipt.

**Исходные задачи:** [#3857](https://github.com/yshishenya/graf/issues/3857), [#3860](https://github.com/yshishenya/graf/issues/3860).

### B016 — Эксплуатационные хвосты выпуска

- [ ] **P2; F238; 1 issues.**

**Известно:** #6501 сохраняет решение по production stash, Actions Node20 и отдельным процедурам обслуживания.

**Проверить и при необходимости исправить:** Сначала прочитать stash diff и подготовить решение по backup-retention. Проверить обновление Actions runtime и фактические automatic_retry, backfill_inventory, range_playback, normalization_cleanup. Не применять и не удалять stash по факту этого бэклога.

**Готово, когда:** Каждая из четырёх процедур имеет результат, Actions runtime соответствует требованиям, судьба stash определена отдельным решением. Общий release smoke не заменяет эти пункты.

**Исходные задачи:** [#6501](https://github.com/yshishenya/graf/issues/6501).

### B017 — Общая приёмка среды разработки

- [ ] **P1; F216; 5 issues.**

**Известно:** Пять issues F216 оставляют reviewer-owned checklist, analyze/converge и общее подтверждение harness.

**Проверить и при необходимости исправить:** Сопоставить #6090/#6125/#6128/#6132/#6139 с актуальным harness; получить проверку требований, повторить необходимые проверки на точной версии, согласовать остаток и evidence.

**Готово, когда:** Все обязательные пункты приняты уполномоченным проверяющим, analyze/converge соответствуют реальной реализации; автор реализации не проставляет чужую приёмку.

**Исходные задачи:** [#6090](https://github.com/yshishenya/graf/issues/6090), [#6125](https://github.com/yshishenya/graf/issues/6125), [#6128](https://github.com/yshishenya/graf/issues/6128), [#6132](https://github.com/yshishenya/graf/issues/6132), [#6139](https://github.com/yshishenya/graf/issues/6139).

### B018 — Единая идентичность репозитория в рабочих копиях

- [ ] **P1; F224; 9 issues.**

**Известно:** По аудиту _repo_identity опирается на имя common git directory; девять задач нормализации не доказаны. Отсутствующая здесь исходная спецификация не отменяет issues.

**Проверить и при необходимости исправить:** Восстановить исходный контракт #6180–#6188; проверить canonical remote identity, нормализацию remote, shared state/locks и отклонение state override до побочных действий. Найти всех потребителей общего helper перед исправлением.

**Готово, когда:** Разные worktrees одного репозитория видят согласованную идентичность/блокировки, разные репозитории не смешивают состояние; опасный override отвергается до записи.

**Исходные задачи:** [#6180](https://github.com/yshishenya/graf/issues/6180), [#6181](https://github.com/yshishenya/graf/issues/6181), [#6182](https://github.com/yshishenya/graf/issues/6182), [#6183](https://github.com/yshishenya/graf/issues/6183), [#6184](https://github.com/yshishenya/graf/issues/6184), [#6185](https://github.com/yshishenya/graf/issues/6185), [#6186](https://github.com/yshishenya/graf/issues/6186), [#6187](https://github.com/yshishenya/graf/issues/6187), [#6188](https://github.com/yshishenya/graf/issues/6188).

### B019 — Корректное выделение номера фичи

- [X] **P1; F225; 8 issues.**

**Результат:** PR #6899 включён в master; семь детей и umbrella F225 закрыты после исходной приёмки и live CI/PR проверки. Этап #6837 также закрыт. Подробности: execution-status.md и acceptance.md F225.

**Известно:** По аудиту allocator продолжает учитывать служебные/capture refs; восемь задач исключения таких refs не приняты. Во время создания F259 также выявлено отсутствие автоматического создания новой feature-метки.

**Проверить и при необходимости исправить:** По #6189–#6196 проверить обычные и service/capture refs, локальные/удалённые ветки, reservations и GitHub history, конкурентное выделение и отсутствие метки feature:N. Исправлять единый allocator после анализа всех вызовов; не менять номера других активных фич в рамках этого исправления.

**Готово, когда:** Служебные ссылки не искажают число, реальные reservations не теряются, конкурентные запуски не получают один ID, отсутствие новой метки обработано. Проверки исходного контракта и governance проходят.

**Исходные задачи:** [#6189](https://github.com/yshishenya/graf/issues/6189), [#6190](https://github.com/yshishenya/graf/issues/6190), [#6191](https://github.com/yshishenya/graf/issues/6191), [#6192](https://github.com/yshishenya/graf/issues/6192), [#6193](https://github.com/yshishenya/graf/issues/6193), [#6194](https://github.com/yshishenya/graf/issues/6194), [#6195](https://github.com/yshishenya/graf/issues/6195), [#6196](https://github.com/yshishenya/graf/issues/6196).

### B020 — Настоящая проверка очереди слияния GitHub

- [ ] **P1; F227; 5 issues.**

**Известно:** merge_group остаётся действующим требованием; локальный mapping self-test не заменяет remote rehearsal.

**Проверить и при необходимости исправить:** Для #6274 проверить authoritative GitHub API mapping merge_group → PR; выполнить настоящий PR+merge_group rehearsal #6236, сверить coverage/analyze #6233, converge #6237 и общий #6207. Изменение правил репозитория отдельно согласуется.

**Готово, когда:** Есть фактический удалённый запуск и корректное сопоставление PR с exact SHA, а не только подготовленный workflow. Все зависимые gates завершены.

**Исходные задачи:** [#6207](https://github.com/yshishenya/graf/issues/6207), [#6233](https://github.com/yshishenya/graf/issues/6233), [#6236](https://github.com/yshishenya/graf/issues/6236), [#6237](https://github.com/yshishenya/graf/issues/6237), [#6274](https://github.com/yshishenya/graf/issues/6274).

### B021 — Управляемое выведение legacy

- [ ] **P2; F228; 32 issues.**

**Известно:** Подготовительный план выполнен, но 32 задачи инвентаря, реестра и реализации удаления остались открыты.

**Проверить и при необходимости исправить:** Сначала построить инвентарь и установить владельцев/потребителей, совместимость, критерии сохранения и rollback. Для каждой записи выбрать сохранение, замену или удаление по F228; удаления выполнять только после проверки конкретного набора.

**Готово, когда:** Каждый исходный пункт имеет решение и проверенный результат; удалённое не используется действующими потребителями. Подготовка списка не считается выполненным удалением.

**Исходные задачи:** [#6238](https://github.com/yshishenya/graf/issues/6238), [#6243](https://github.com/yshishenya/graf/issues/6243), [#6244](https://github.com/yshishenya/graf/issues/6244), [#6245](https://github.com/yshishenya/graf/issues/6245), [#6246](https://github.com/yshishenya/graf/issues/6246), [#6247](https://github.com/yshishenya/graf/issues/6247), [#6248](https://github.com/yshishenya/graf/issues/6248), [#6249](https://github.com/yshishenya/graf/issues/6249), [#6250](https://github.com/yshishenya/graf/issues/6250), [#6251](https://github.com/yshishenya/graf/issues/6251), [#6252](https://github.com/yshishenya/graf/issues/6252), [#6253](https://github.com/yshishenya/graf/issues/6253), [#6254](https://github.com/yshishenya/graf/issues/6254), [#6255](https://github.com/yshishenya/graf/issues/6255), [#6256](https://github.com/yshishenya/graf/issues/6256), [#6257](https://github.com/yshishenya/graf/issues/6257), [#6258](https://github.com/yshishenya/graf/issues/6258), [#6259](https://github.com/yshishenya/graf/issues/6259), [#6260](https://github.com/yshishenya/graf/issues/6260), [#6261](https://github.com/yshishenya/graf/issues/6261), [#6262](https://github.com/yshishenya/graf/issues/6262), [#6263](https://github.com/yshishenya/graf/issues/6263), [#6264](https://github.com/yshishenya/graf/issues/6264), [#6265](https://github.com/yshishenya/graf/issues/6265), [#6266](https://github.com/yshishenya/graf/issues/6266), [#6267](https://github.com/yshishenya/graf/issues/6267), [#6268](https://github.com/yshishenya/graf/issues/6268), [#6269](https://github.com/yshishenya/graf/issues/6269), [#6270](https://github.com/yshishenya/graf/issues/6270), [#6271](https://github.com/yshishenya/graf/issues/6271), [#6272](https://github.com/yshishenya/graf/issues/6272), [#6273](https://github.com/yshishenya/graf/issues/6273).

### B022 — Проверка соблюдения процесса разработки

- [ ] **P1; F230; 12 issues.**

**Известно:** Двенадцать issues сохраняют contracts, owner/reviewer приёмку и enforcement; шесть доказанных дублей уже закрыты отдельно.

**Проверить и при необходимости исправить:** Сверить реальные requirements #6314–#6334 из реестра: claim/umbrella/pointer, root-router и отказ без mtime fallback, portable templates, правила владельцев worktrees, observe-only rehearsal/rollback, issue sync/analyze/fast/converge. Не включать required checks автоматически.

**Готово, когда:** Оставшиеся двенадцать требований получили актуальную проверку и operator/reviewer решения; закрытые дубли не создаются заново.

**Исходные задачи:** [#6314](https://github.com/yshishenya/graf/issues/6314), [#6315](https://github.com/yshishenya/graf/issues/6315), [#6316](https://github.com/yshishenya/graf/issues/6316), [#6321](https://github.com/yshishenya/graf/issues/6321), [#6327](https://github.com/yshishenya/graf/issues/6327), [#6328](https://github.com/yshishenya/graf/issues/6328), [#6329](https://github.com/yshishenya/graf/issues/6329), [#6330](https://github.com/yshishenya/graf/issues/6330), [#6331](https://github.com/yshishenya/graf/issues/6331), [#6332](https://github.com/yshishenya/graf/issues/6332), [#6333](https://github.com/yshishenya/graf/issues/6333), [#6334](https://github.com/yshishenya/graf/issues/6334).

### B023 — Зависимость: Windows

- [ ] **P1; F200; 78 issues.**

**Известно:** 78 issues относятся к активной невлитой Windows-разработке. В master есть другие specs с номером 200; автоматическое сопоставление по номеру ошибочно.

**Проверить и при необходимости исправить:** Найти каноническую Windows ветку/план по содержанию issues и владельцу; сохранить реализацию там. После включения в master проверить весь исходный набор Windows критериев, CI и установленную сборку.

**Готово, когда:** Есть содержательная связь каждой задачи с Windows реализацией и её приёмкой. Другие каталоги F200 не используются как доказательство, исходные задачи не отменяются из-за возраста.

**Исходные задачи:** [#5662](https://github.com/yshishenya/graf/issues/5662), [#5663](https://github.com/yshishenya/graf/issues/5663), [#5664](https://github.com/yshishenya/graf/issues/5664), [#5665](https://github.com/yshishenya/graf/issues/5665), [#5666](https://github.com/yshishenya/graf/issues/5666), [#5667](https://github.com/yshishenya/graf/issues/5667), [#5668](https://github.com/yshishenya/graf/issues/5668), [#5669](https://github.com/yshishenya/graf/issues/5669), [#5670](https://github.com/yshishenya/graf/issues/5670), [#5671](https://github.com/yshishenya/graf/issues/5671), [#5672](https://github.com/yshishenya/graf/issues/5672), [#5673](https://github.com/yshishenya/graf/issues/5673), [#5674](https://github.com/yshishenya/graf/issues/5674), [#5675](https://github.com/yshishenya/graf/issues/5675), [#5676](https://github.com/yshishenya/graf/issues/5676), [#5677](https://github.com/yshishenya/graf/issues/5677), [#5678](https://github.com/yshishenya/graf/issues/5678), [#5679](https://github.com/yshishenya/graf/issues/5679), [#5680](https://github.com/yshishenya/graf/issues/5680), [#5681](https://github.com/yshishenya/graf/issues/5681), [#5682](https://github.com/yshishenya/graf/issues/5682), [#5683](https://github.com/yshishenya/graf/issues/5683), [#5684](https://github.com/yshishenya/graf/issues/5684), [#5685](https://github.com/yshishenya/graf/issues/5685), [#5686](https://github.com/yshishenya/graf/issues/5686), [#5687](https://github.com/yshishenya/graf/issues/5687), [#5688](https://github.com/yshishenya/graf/issues/5688), [#5689](https://github.com/yshishenya/graf/issues/5689), [#5690](https://github.com/yshishenya/graf/issues/5690), [#5691](https://github.com/yshishenya/graf/issues/5691), [#5692](https://github.com/yshishenya/graf/issues/5692), [#5693](https://github.com/yshishenya/graf/issues/5693), [#5694](https://github.com/yshishenya/graf/issues/5694), [#5695](https://github.com/yshishenya/graf/issues/5695), [#5696](https://github.com/yshishenya/graf/issues/5696), [#5697](https://github.com/yshishenya/graf/issues/5697), [#5698](https://github.com/yshishenya/graf/issues/5698), [#5699](https://github.com/yshishenya/graf/issues/5699), [#5700](https://github.com/yshishenya/graf/issues/5700), [#5701](https://github.com/yshishenya/graf/issues/5701), [#5702](https://github.com/yshishenya/graf/issues/5702), [#5703](https://github.com/yshishenya/graf/issues/5703), [#5704](https://github.com/yshishenya/graf/issues/5704), [#5705](https://github.com/yshishenya/graf/issues/5705), [#5706](https://github.com/yshishenya/graf/issues/5706), [#5707](https://github.com/yshishenya/graf/issues/5707), [#5708](https://github.com/yshishenya/graf/issues/5708), [#5709](https://github.com/yshishenya/graf/issues/5709), [#5710](https://github.com/yshishenya/graf/issues/5710), [#5711](https://github.com/yshishenya/graf/issues/5711), [#5712](https://github.com/yshishenya/graf/issues/5712), [#5713](https://github.com/yshishenya/graf/issues/5713), [#5714](https://github.com/yshishenya/graf/issues/5714), [#5715](https://github.com/yshishenya/graf/issues/5715), [#5716](https://github.com/yshishenya/graf/issues/5716), [#5717](https://github.com/yshishenya/graf/issues/5717), [#5718](https://github.com/yshishenya/graf/issues/5718), [#5719](https://github.com/yshishenya/graf/issues/5719), [#5720](https://github.com/yshishenya/graf/issues/5720), [#5721](https://github.com/yshishenya/graf/issues/5721), [#5722](https://github.com/yshishenya/graf/issues/5722), [#5723](https://github.com/yshishenya/graf/issues/5723), [#5724](https://github.com/yshishenya/graf/issues/5724), [#5725](https://github.com/yshishenya/graf/issues/5725), [#5777](https://github.com/yshishenya/graf/issues/5777), [#5778](https://github.com/yshishenya/graf/issues/5778), [#5779](https://github.com/yshishenya/graf/issues/5779), [#5780](https://github.com/yshishenya/graf/issues/5780), [#5781](https://github.com/yshishenya/graf/issues/5781), [#5782](https://github.com/yshishenya/graf/issues/5782), [#5783](https://github.com/yshishenya/graf/issues/5783), [#6636](https://github.com/yshishenya/graf/issues/6636), [#6637](https://github.com/yshishenya/graf/issues/6637), [#6638](https://github.com/yshishenya/graf/issues/6638), [#6639](https://github.com/yshishenya/graf/issues/6639), [#6640](https://github.com/yshishenya/graf/issues/6640), [#6641](https://github.com/yshishenya/graf/issues/6641), [#6781](https://github.com/yshishenya/graf/issues/6781).

### B024 — Зависимость: системная админка

- [ ] **P1; F254; 40 issues.**

**Известно:** 40 issues относятся к F254, открытый PR #6788 — ссылка на PR, не номер фичи. Код ещё не входит в проверенную базу master.

**Проверить и при необходимости исправить:** Получить фактический статус PR #6788 и владельца F254, дождаться согласованной интеграции; затем проверить catalog/promotion/subscription, права, migrations/idempotency и остальные критерии каждого issue.

**Готово, когда:** Работа и приёмка сохраняются у F254; локальные focused tests не выдаются за merge/production. Приёмка всех 40 исходных issues подтверждена отдельно.

**Исходные задачи:** [#6708](https://github.com/yshishenya/graf/issues/6708), [#6712](https://github.com/yshishenya/graf/issues/6712), [#6713](https://github.com/yshishenya/graf/issues/6713), [#6714](https://github.com/yshishenya/graf/issues/6714), [#6715](https://github.com/yshishenya/graf/issues/6715), [#6716](https://github.com/yshishenya/graf/issues/6716), [#6717](https://github.com/yshishenya/graf/issues/6717), [#6718](https://github.com/yshishenya/graf/issues/6718), [#6719](https://github.com/yshishenya/graf/issues/6719), [#6720](https://github.com/yshishenya/graf/issues/6720), [#6721](https://github.com/yshishenya/graf/issues/6721), [#6722](https://github.com/yshishenya/graf/issues/6722), [#6723](https://github.com/yshishenya/graf/issues/6723), [#6724](https://github.com/yshishenya/graf/issues/6724), [#6725](https://github.com/yshishenya/graf/issues/6725), [#6726](https://github.com/yshishenya/graf/issues/6726), [#6727](https://github.com/yshishenya/graf/issues/6727), [#6728](https://github.com/yshishenya/graf/issues/6728), [#6729](https://github.com/yshishenya/graf/issues/6729), [#6730](https://github.com/yshishenya/graf/issues/6730), [#6731](https://github.com/yshishenya/graf/issues/6731), [#6732](https://github.com/yshishenya/graf/issues/6732), [#6733](https://github.com/yshishenya/graf/issues/6733), [#6734](https://github.com/yshishenya/graf/issues/6734), [#6735](https://github.com/yshishenya/graf/issues/6735), [#6736](https://github.com/yshishenya/graf/issues/6736), [#6737](https://github.com/yshishenya/graf/issues/6737), [#6738](https://github.com/yshishenya/graf/issues/6738), [#6739](https://github.com/yshishenya/graf/issues/6739), [#6740](https://github.com/yshishenya/graf/issues/6740), [#6741](https://github.com/yshishenya/graf/issues/6741), [#6742](https://github.com/yshishenya/graf/issues/6742), [#6743](https://github.com/yshishenya/graf/issues/6743), [#6744](https://github.com/yshishenya/graf/issues/6744), [#6745](https://github.com/yshishenya/graf/issues/6745), [#6746](https://github.com/yshishenya/graf/issues/6746), [#6747](https://github.com/yshishenya/graf/issues/6747), [#6748](https://github.com/yshishenya/graf/issues/6748), [#6749](https://github.com/yshishenya/graf/issues/6749), [#6750](https://github.com/yshishenya/graf/issues/6750).

### B025 — Зависимость: панель проигрывателя

- [ ] **P1; F256; 13 issues.**

**Известно:** 13 issues новой F256 — действующая продуктовая работа, а не набор доказанных ошибок.

**Проверить и при необходимости исправить:** После завершения владельцем F256 проверить воспроизведение/дорожки, обсуждения, роли и доступ, lifecycle и все web/Dev переходы из исходных задач.

**Готово, когда:** Изменения включены в согласованную версию; критерии 13 исходных issues и их собственный review пройдены. Новый дубль реализации не создаётся.

**Исходные задачи:** [#6793](https://github.com/yshishenya/graf/issues/6793), [#6795](https://github.com/yshishenya/graf/issues/6795), [#6796](https://github.com/yshishenya/graf/issues/6796), [#6799](https://github.com/yshishenya/graf/issues/6799), [#6802](https://github.com/yshishenya/graf/issues/6802), [#6805](https://github.com/yshishenya/graf/issues/6805), [#6807](https://github.com/yshishenya/graf/issues/6807), [#6811](https://github.com/yshishenya/graf/issues/6811), [#6812](https://github.com/yshishenya/graf/issues/6812), [#6813](https://github.com/yshishenya/graf/issues/6813), [#6814](https://github.com/yshishenya/graf/issues/6814), [#6815](https://github.com/yshishenya/graf/issues/6815), [#6816](https://github.com/yshishenya/graf/issues/6816).

### B026 — Зависимость: страница итогов встречи

- [ ] **P1; F257; 11 issues.**

**Известно:** 11 issues F257 находятся в активной разработке.

**Проверить и при необходимости исправить:** После интеграции проверить шапку/документ, выбор формата, copy при смене состояния, экспорт без потери навигации, web и GRAF Dev по исходному плану.

**Готово, когда:** Все исходные сценарии F257 приняты на её точной версии и повторно проверены в общей версии при затронутых пересечениях.

**Исходные задачи:** [#6794](https://github.com/yshishenya/graf/issues/6794), [#6797](https://github.com/yshishenya/graf/issues/6797), [#6798](https://github.com/yshishenya/graf/issues/6798), [#6800](https://github.com/yshishenya/graf/issues/6800), [#6801](https://github.com/yshishenya/graf/issues/6801), [#6803](https://github.com/yshishenya/graf/issues/6803), [#6804](https://github.com/yshishenya/graf/issues/6804), [#6806](https://github.com/yshishenya/graf/issues/6806), [#6808](https://github.com/yshishenya/graf/issues/6808), [#6809](https://github.com/yshishenya/graf/issues/6809), [#6810](https://github.com/yshishenya/graf/issues/6810).

### B027 — Зависимость: объединённые исправления встречи и уведомлений

- [ ] **P1; F258, F6788; 7 issues.**

**Известно:** Актуальный #6825 назначает F6788 владельцем общего пути записи/уведомлений и перенесённых частей F258/PR #6824. Это обновляет раннюю договорённость об отдельной ветке codex/f249-production-calendar-fixes.

**Проверить и при необходимости исправить:** Использовать действующие tasks F6788; сверить интеграцию звука до итогов, актуальной попытки, автообновления, native owner/incident и media grants. Дождаться review и проверки GRAF Dev общей версии. Старые #6780/#6779/#6758 проверять по B001, не закрывать автоматически переносом.

**Готово, когда:** Принята единая версия F6788 с полным перенесённым объёмом F258; соответствие исходных issues явно доказано. Ни старый успешный тест, ни сам перенос diff не являются приёмкой общего SHA.

**Исходные задачи:** [#6818](https://github.com/yshishenya/graf/issues/6818), [#6819](https://github.com/yshishenya/graf/issues/6819), [#6820](https://github.com/yshishenya/graf/issues/6820), [#6821](https://github.com/yshishenya/graf/issues/6821), [#6822](https://github.com/yshishenya/graf/issues/6822), [#6823](https://github.com/yshishenya/graf/issues/6823), [#6825](https://github.com/yshishenya/graf/issues/6825).

## Завершение и безопасное продолжение

- [ ] **B028 — определить судьбу тестовых объектов предыдущей проверки.** В календаре осталась тестовая встреча `GRAF QA 6780 6779` (2026-09-08, 19:23–19:33 UTC+05), а в GRAF — связанная 17-секундная запись. Они не удалены. Установить, нужны ли они для повторного воспроизведения; получить решение о хранении/удалении, выполнить только согласованное действие и проверить результат. Содержимое записи не переносить в git.
- [ ] **B029 — повторно сверить итог со всеми исходными issues.** Обновить актуальное состояние каждой строки реестра, проверить PR/точный SHA/CI/среду и комментарии. Документировать новые находки отдельным дополнением. Обязательные незакрытые критерии остаются открытыми; закрытие новой umbrella-задачи не закрывает их автоматически. Готово: ни одна исходная задача не потеряна, каждый результат доказан или остаётся явным остатком, согласованные передачи имеют владельца.

## Ограничения среды и решений

- Ручная macOS приёмка через единственный `/Applications/GRAF Dev.app` и штатный dev-harness; перед работой прочитать local-development.md и согласовать использование общей среды с активным владельцем. Не собирать отдельную копию приложения.
- Production наблюдения 2026-09-08 уже разрешены пользователем; новые изменения системы/данных и выпуск требуют соответствующего объёма разрешения и release gates. Включение production уведомлений ранее запрошено, ответа нет; не считать его полученным.
- Реальные платежи, рассылки, удаление/восстановление пользовательских данных, stash apply/drop и изменение GitHub required checks не выполняются подготовкой бэклога. Перед этими действиями подготовить конкретный проверяемый результат/сценарий.
- Не хранить credentials, signed URLs, аудио, транскрипты, частное содержимое встреч и необработанные логи в спецификации, evidence или GitHub. Для записи доказательств достаточно безопасных метаданных.
- Непроверенный аппаратный/пользовательский сценарий остаётся открытым. Успешные unit tests, CI, runtime, release и installed-app проверка — отдельные доказательства.

## Основания и степень проверки

1. Аудит трекера 2026-09-08: в первом и повторном проходах подтверждены 569 закрытий; позднее отдельно закрыты шесть дублей F230, F239, F255 и два пункта F249. Эти исторические итоги не переносятся в список будущей реализации.
2. Последний подробный проход перечитал 24 issues: F179, F136, F206, F210, F227, F052, F096, F181, F238. Новых закрытий в этом проходе не было. Остальные строки полного реестра имеют подтверждённое открытое состояние и основания из предыдущего аудита, но не объявлены повторно принятыми.
3. Production GRAF проверен как установленный v2026.09.08.1, подпись/stapling пройдены. SHA не встроен в Info.plist; связь с исходной версией установлена по релизу, а не по полю приложения.
4. При запуске из меню в 14:23:33Z и 14:23:59Z фиксировалось открытие главного окна; recording.started в 14:25:03Z возник после Start в главном предложении, сохранение/Stop — в 14:25:20Z. Это симптом для повторной проверки, не установленная причина.
5. Актуальный #6825 перечитан при подготовке: F6788 объединяет оставшуюся работу F249 и F258. Старую отдельную ветку и чат не копировать и не перезапускать как второго владельца.
6. Исправление нумерации: первоначальный F6789 был ошибкой. Bootstrap продолжил завышенную цепочку F6788 вместо продуктовой последовательности до F258; результат был принят без должной проверки. После замечания владельца F259 проверен по specs всех worktrees, refs, shared claims и точным GitHub markers, затем зарезервирован штатной функцией claim с проверкой коллизий. Ветка, каталог, active pointer и тот же issue #6827 переведены на F259; бэклог сохранён. Общая ошибка allocator остаётся в B019, чужая F6788 не изменена.

Подробные локальные отчёты исходного аудита (не входят в новую ветку; для переноса использовать безопасные выводы выше):

- `/Users/yshishenya/.codex/worktrees/ea3e/crisp/.dev/closeout/2026-09-08-round2/report.md`
- `/Users/yshishenya/.codex/worktrees/ea3e/crisp/.dev/closeout/2026-09-08-followup-audit/report.md`
- `/Users/yshishenya/.codex/worktrees/ea3e/crisp/.dev/closeout/2026-09-08-production-calendar/`

Постоянные исходные требования и уточняющие комментарии доступны по ссылкам на GitHub в реестре. Сырые локальные выгрузки body/comments не скопированы.

## Проверка документов при создании

- PASS: 279 уникальных исходных issues, точное соответствие снимку, одно направление на issue; 27 направлений и 30 B-пунктов.
- PASS: 3 истории, 11 требований, 5 критериев, локальные ссылки, отсутствие выполненных пунктов реализации и ошибок пробелов.
- PASS: `check-prerequisites.sh --json --paths-only` находит новую фичу; branch/active pointer/reservation #6827 согласованы.
- PASS: `git diff --check`; новые неотслеживаемые Markdown дополнительно проверены напрямую.
- BLOCKED: `python3 scripts/check_spec_kit_governance.py` — frozen doctor видит установленный specify v1.0.4/ref cb610277fdea781fcfa83d20522c2db37c94068d, а lock требует v1.0.1/ref 9118ed15a0ba65053469a94c560ea5d233f75884. Это состояние инструмента относительно неизменённой базы. Добавлено в B000: подготовить закреплённую среду и повторить проверку перед реализацией; глобальный инструмент и lock сейчас не изменены.
- Необязательный after_specify hook agent-context.update пропущен: активная фича уже задана per-worktree pointer, root AGENTS.md сохраняется стабильным. Commit hooks отключены конфигурацией.
- Full CI не запускался: текущий объём — спецификация и бэклог, продуктовый код не менялся. Независимая проверка требований остаётся открытой.

## Продолжение B019 — исправление скрипта

По прямому запросу владельца исправлен локальный кандидат в scripts/claim-feature.py и трёх branch adapters. План/задачи первого этапа находятся в plan.md/tasks.md; результаты — validation.md. Следующий номер по реальным данным — 260; 320 governance tests прошли. B019 остаётся открытым до T006 и сопоставления всей исходной приёмки F225. Остальные 279 issues этим изменением не закрыты.

## Дополнение: workflow завершения

По следующему поручению владельца проверен разрыв после implement; локальное исправление и его задачи T007–T010 сохранены в той же F259. Подробности — workflow-audit.md. Исправление не заменяет приёмку исходных 279 issues и не закрывает их по одному лишь [X].
