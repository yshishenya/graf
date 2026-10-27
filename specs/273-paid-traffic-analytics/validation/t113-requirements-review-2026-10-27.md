# Независимое ревью требований F273 T112/T113 — 27.10.2026

**Итог повторного прохода: PASS качества требований; 117 checked / 0 unchecked.**

Проверяющий `/root/activation_requirements_gate`. Ветка `codex/273-activation-ledger`. Lane: независимый reviewer gate требований активного high-risk Spec Kit среза. Это не проверка выполненной реализации, runtime, выпуска или достигнутого роста. Разрешены только четыре reviewer-owned checklist и этот отчёт. Код/spec/plan/tasks/Git/GitHub/приложение/данные не менялись проверяющим.

HEAD основы `c6e49f52a32de8dcb49673509cbfd64bc20e7bfe`. Требования находятся в явно изменённой рабочей копии из8 документов; один SHA основы не идентифицирует эти байты, ниже приведены текущие SHA-256. Первичный read-only HOLD на этой основе сохранён в `.dev/growth/activation-requirements-gate-20261027.md`.

## Метод и прочитанные источники

Первичный полный просмотр spec/plan/tasks/quickstart/research/data-model/legal/contracts/constitution и четырёх чек-листов использован как база. Все изменения8 документов в этом проходе прочитаны полностью по diff, затронутые lifecycle/trust/delivery/restore разделы перечитаны непосредственно; неизменные части сопоставлены с базой. Все117 действующих вопросов перечитаны заново; прежние markers не приняты за текущий PASS. PRD/current-product-status в этом назначении самостоятельно не перечитывались, поэтому полная продуктовая/runtime приёмка не заявляется. Инженерные зависимости исследованы собственным чтением соответствующих аналитических и account-close путей, в пределах указанных ниже разделов.

## Что исправлено основным агентом после первого HOLD

- FR025 и Key Entities теперь различают псевдоним и обезличивание, задают trusted server auth и устойчивое решение+доставку.
- Одна relation `public.product_activation_milestones` с unique(account_id,event_name), не более5 строк на аккаунт, двумя фиксированными получателями и snapshot<=16KiB. Принятие и intents одной транзакцией; payload не заменяется повтором.
- Все ingress, server-auth и browser trigger проходят одну trusted boundary. Body identity не может занять чужую веху; unlinked first_open без trusted install key не создаёт аккаунтный или внешний первый счёт. Новая install identity не вводится.
- `submitted` отделено от `confirmed`; транспортный timeout/5xx/crash после начала вызова — ambiguous без слепого retry. Commit права попытки до сети и attempt owner защищают от конкурирующих работников. PostHog и Яндекс не делят один флаг.
- Ограниченный maintenance:20 строк/проход,1 запрос разом,timeout<=5с,пауза60с, без нового брокера/процесса. Product response не ждёт сети.
- Действующие основание/цели/выключатели проверяются перед admission и каждым side effect; snapshot/body не заменяют свежий gate. Unknown не разрешает передачу; отзыв рекламы не отменяет допустимую локальную веху уровня2 автоматически.
- Категория activation_milestone_decisions зарегистрирована в целевой model/operations как graf_postgres/until_decision. Source_kind теперь внутренняя browser/desktop/server колонка из trusted caller, не client JSON и не внешнее свойство.
- GRAF DB backup явно относится к существующему T110; PostHog-only T118 не расширен молча. Relation включена в inventory/T109, schema/runtime/restore invalidate старые receipts. Writer закрыт до текущих доказательств, размер/пять строк не заменяют реальный рост/запас.
- Category removal назначен legal_basis_lifecycle level2/DISPOSITION_DELETE/local statement; account-case назначен existing finalize_account_close с точным WHERE account_id=request.requested_by_user_id в текущей транзакции. FK CASCADE только последняя защита, existing close сохраняет identity. Это узкое расширение, не новая система удаления аккаунта. Подтверждено собственным чтением finalize_account_close:359–439 и legal_basis_lifecycle:74–129,600–645.

## Исправленные замечания промежуточного прохода

**R7, MEDIUM — исправлено, PASS.** `quickstart.md:98` буквально требует «gate до транспорта даёт pre_send_retry», тогда как контракт отменяет намерение при отзыве. Нужна явная граница: только доказанный технический сбой до входа в транспорт допускает retry; выключатель/нечитаемое основание не разрешают отправку, отзыв отменяет соответствующее намерение. Не следует реализовывать повтор отменённой цели ради зелёного сценария.

**R8, HIGH — исправлено, PASS.** `activation-milestones.md`, финальный абзац restore, правильно карантинирует восстановленные неподтверждённые намерения и помечает пропуск после backup неизвестным. Но после backup могла быть принята и доставлена строка, которой в восстановленной БД вовсе нет. Карантин существующих rows её не защищает. Нужно явно оставить readiness/admission затронутых первых вех закрытыми при непокрытом gap до подтверждённой сверки; unknown сам не является разрешением повторно INSERT/отправить ту же account+event. Новый backfill/сервис/история не требуются. Это уточнение границы возобновления, не требование реализовать восстановление до разработки.

Финальная версия data-model задаёт явный конечный server reason enum; клиент не определяет reason, неизвестный код отклоняется, raw exception/response запрещены. Source_kind ограничен browser/desktop/server и остаётся внутренним. По этим границам PASS. Дальнейший внутренний формат GRAF receipt принадлежит реализации при соблюдении принятых требований: полный ledger+provider states, свежесть/схема/runtime, повторное удаление, карантин, invalidation старого/partial свидетельства.

### Повторная собственная проверка R7/R8 и backup-рецепта

R7 устранён в quickstart: доказанный технический сбой до входа в транспорт отделён от выключателя, неизвестного основания и отзыва. Отзыв отменяет соответствующее намерение; технический retry не разрешает повтор отменённой цели.

R8 устранён одновременно в activation-milestones и quickstart: при непокрытом после backup интервале admission затронутых первых вех остаётся закрытым, включая account+event, отсутствующие в восстановленной копии. Неизвестность не разрешает новый INSERT, отправку или полную историческую сумму. Это закрытая безопасная граница до подтверждённой сверки, без выдуманной истории.

Operations теперь называет уже существующие backup-rec-stack.sh/rehearse-rec-restore.sh и требует узкое расширение restore-проверки схемы/unique/FK, количеств/состояний, удаления/карантина и unknown-gap admission. Receipt связан с backup checksum, schema/source/runtime fingerprint, точкой копии и сверки, результатами удаления/карантина, временем и cleanup временной БД. Общий backup_result=pass старого сценария не разрешает writer.

Оба скрипта прочитаны полностью, не запускались: backup использует custom-format pg_dump, restore создаёт временную БД и сейчас проверяет лишь count(*)>=0. Документ явно признаёт эту проверку недостаточной и назначает узкое исправление. PASS относится к качеству принятого проекта; реальные copy/restore, права0700/0600 и receipts не подтверждены.

Все восемь документов изменённого набора сверены с предыдущим снимком. После HOLD изменились только четыре ожидаемых документа: activation-milestones, quickstart, data-model и operations; spec/plan/research/tasks и прочие записанные зависимости сохранили прежние SHA-256. Все исправленные части перечитаны. Семь открытых quality items проверены заново и отмечены только после устранения причин.

## Полная матрица117 пунктов

Каждый PASS ниже означает качество требования для проверки, без заявления о выполненном коде, SC или production. Новые продуктовые цели/получатели/права не добавлялись.

### requirements.md

| Пункт | Вывод | Проверенные требования / причина |
| --- | --- | --- |
| No implementation details (languages, frameworks, APIs) | PASS | Spec goals/User Stories; plan isolates implementation |
| Focused on user value and business needs | PASS | Spec User Scenarios, SC-006/007; first value |
| Written for non-technical stakeholders | PASS | Русский продуктовый spec, договор/согласие пояснены |
| All mandatory sections completed | PASS | Spec все обязательные разделы, plan/research/data-model/contracts/tasks |
| No [NEEDS CLARIFICATION] markers remain | PASS | Clarify decisions; принятая трёхуровневая модель |
| Requirements are testable and unambiguous | PASS | FR025 + activation admission/states/restore; quickstart технический pre-send и запрет admission при unknown gap |
| Success criteria are measurable | PASS | Spec SC-001–SC-012, численные критерии |
| Success criteria are technology-agnostic (no implementation details) | PASS | Spec SC; технологии только в инженерных артефактах |
| All acceptance scenarios are defined | PASS | quickstart4: technical pre-send != withdrawn gate; crash/ambiguous; absent-row restore gap denied |
| Edge cases are identified | PASS | activation последний абзац: missing account+event после backup не принимается при unknown gap |
| Scope is clearly bounded | PASS | Spec Out of Scope/Legacy; одна relation,2 получателя |
| Dependencies and assumptions identified | PASS | Plan dependency order; T106/T109/T110/T111/T116/T118 разделены |
| All functional requirements have clear acceptance criteria | PASS | FR025 + activation admission/states/restore; quickstart технический pre-send и запрет admission при unknown gap |
| User scenarios cover primary flows | PASS | User Stories + browser/desktop activation contracts |
| Feature meets measurable outcomes defined in Success Criteria | PASS | Spec SC и quickstart; качество outcome definition, не достижение KPI |
| No implementation details leak into specification | PASS | Spec FR-025 не закрепляет новую очередь/сервис; конкретика в model/contracts |

Итог: **16 checked / 0 unchecked**.

### privacy-measurement.md

| Пункт | Вывод | Проверенные требования / причина |
| --- | --- | --- |
| CHK001 Граница между тремя уровнями измерения определена проверяемыми признаками, а не намерением? [Clarity, Spec §Правовая конструкция измерения] | PASS | Spec Правовая конструкция |
| CHK002 Утверждение «определяемого лица не остаётся» подкреплено закрытым перечнем исключаемых идентификаторов? [Clarity, Spec §FR-010] | PASS | FR-010; anonymous-aggregate closed exclusions |
| CHK003 Правовое основание каждого уровня указано со ссылкой на конкретную норму, а не общим упоминанием закона? [Completeness, Spec §Правовая конструкция измерения, legal-basis.md] | PASS | legal-basis нормы/ограничения; без нового legal approval |
| CHK004 Требование о том, что псевдонимизация не является обезличиванием, сформулировано так, что случайное переиспользование модуля псевдонимов исключено? [Clarity, Spec §Правовая конструкция измерения, research.md §1] | PASS | Spec правовая конструкция; anonymous contract |
| CHK005 Область «свои зарегистрированные пользователи» определена достаточно точно, чтобы отнести конкретные данные к договорному основанию? [Ambiguity, Spec §Правовая конструкция измерения] | PASS | activation trusted principal; model account_id |
| CHK006 Перечень того, что запрещено измерять без согласия, исчерпывающий, а не примерный? [Completeness, Spec §Out of Scope] | PASS | Out of Scope/FR-001–003 |
| CHK007 Требование к записи об одобрении конкретно в части того, кто подтвердил, что именно и когда? [Clarity, Spec §FR-047] | PASS | FR-047; approval fields |
| CHK008 «Немедленно» в требовании о прекращении измерения при отказе имеет наблюдаемую границу? [Ambiguity, Spec §FR-003] | PASS | FR-003 next-write/transfer boundary |
| CHK009 «Отказ не сложнее согласия» выражено измеримыми признаками? [Measurability, Spec §FR-004] | PASS | FR-004 comparable actions |
| CHK010 Требования о строгом режиме по умолчанию и запрете режима «включено по умолчанию» не противоречат друг другу? [Consistency, Spec §FR-001] | PASS | FR-001 strict default |
| CHK011 Описано поведение посетителя, который менял решение более одного раза? [Coverage, Edge Case, Spec §FR-003] | PASS | FR-003 changing decision |
| CHK012 Определено поведение, когда запись о решении посетителя недоступна или повреждена? [Coverage, Exception Flow, Gap] | PASS | Edge Cases unknown/invalid gate closed |
| CHK013 Согласованы требования об отказе и основаниях уровней: отказ не останавливает уровень 1, прекращает соответствующую цель уровня 3, а уровень 2 прекращается при утрате собственного основания? [Consistency, Spec §FR-003, §FR-009] | PASS | FR-003/048 distinct levels |
| CHK014 Требование к сообщению о измерении конкретно в части того, что именно в нём должно быть сказано? [Clarity, Spec §FR-005] | PASS | FR-005 published copy |
| CHK015 Указано, что запись о решении посетителя не используется как источник данных измерения? [Consistency, contracts/anonymous-aggregate.md] | PASS | anonymous contract no consent-source reuse |
| CHK016 Перечень запрещённых к хранению значений закрыт и проверяется разбором сохранённых записей, а не чтением кода? [Measurability, Spec §FR-010, SC-002] | PASS | FR-010/SC-002 saved-data check |
| CHK017 Описаны требования к меткам кампании, приходящим из неуправляемого источника? [Coverage, Gap, data-model.md] | PASS | data-model aggregate UTM normalization |
| CHK018 Гранулярность класса устройства и региона ограничена так, чтобы исключить повторную идентификацию? [Ambiguity, Spec §FR-011] | PASS | FR-011 closed device/region |
| CHK019 Задан минимальный размер корзины агрегации, исключающий выделение одного человека? [Gap, Measurability] | PASS | anonymous contract >=3 before sum; requests not people |
| CHK020 Определены признаки, по которым внутренний, служебный и тестовый трафик отличается от внешнего? [Completeness, Spec §FR-013] | PASS | FR-013 external/operator/service classifiers |
| CHK021 Указано, что обезличенный уровень не читает и не пишет состояние согласия? [Consistency, contracts/anonymous-aggregate.md] | PASS | anonymous contract no consent read/write |
| CHK022 «Последний непрямой источник» определён точно, включая случай возврата без меток? [Clarity, Spec §FR-017] | PASS | attribution contract last_non_direct_90d |
| CHK023 Окно 90 дней применяется согласованно в Метрике и продуктовой аналитике? [Consistency, Spec §FR-017, SC-008] | PASS | FR-017/SC-008 independent coverage caveats |
| CHK024 Описаны требования к регистрации, пришедшей без меток кампании? [Coverage, Edge Case, Spec §FR-018] | PASS | FR-018 unknown absence |
| CHK025 Различие между «кампания неизвестна» и «прямой заход» задано с критериями приёмки? [Clarity, Spec §FR-024] | PASS | FR-024 unknown distinct direct |
| CHK026 Требование о защите от двойного счёта при повторной отправке вехи задано и для приложения, и для сервера? [Completeness, Spec §FR-025] | PASS | unique(account,event), immutable snapshot; unknown restore gap запрещает повтор даже отсутствующей строки |
| CHK027 Набор уровней надёжности атрибуции закрыт и определён? [Completeness, contracts/activation-milestones.md] | PASS | activation linked/weak/unknown |
| CHK028 Описаны требования к атрибуции, которая охватывает два устройства? [Coverage, Edge Case, Spec §FR-022] | PASS | attribution handoff reserve path |
| CHK029 «Фактическое скачивание» отличимо от нажатия кнопки измеримым признаком? [Measurability, Spec §FR-019] | PASS | FR-019 full installer response; T114 remains open |
| CHK030 Для каждой вехи каталога указан реальный путь продукта, из которого она отправляется? [Completeness, Spec §FR-021, contracts/activation-milestones.md] | PASS | activation names all real ingress; plan actual paths |
| CHK031 Срок доставки оповещения задан для каждого класса деградации, а не только в целом? [Completeness, Spec §SC-009] | PASS | SC-009 per degradation class; observer |
| CHK032 Условия аналитической и общехостовой области перечислены с проверяемым разделением сигналов и действий, включая общий физический ресурс и совместное срабатывание? [Consistency, Spec §FR-031] | PASS | FR-031; operations shared-FS priorities |
| CHK033 «Названное целевое хранилище» резервных копий определено достаточно конкретно для проверки? [Ambiguity, Spec §FR-033] | PASS | operations local named target/root protection |
| CHK034 Локальное размещение копий, отсутствие обязательной внешней выгрузки и предел защиты при потере узла/диска сформулированы явно и согласованно? [Clarity, Consistency, Spec §FR-052/053, contracts/operations.md] | PASS | FR-052/053 local only loss boundary |
| CHK035 Сроки хранения заданы по каждой категории данных, а не одним общим значением? [Completeness, Spec §FR-036] | PASS | operations category row activation_milestone_decisions until_decision |
| CHK036 Определено последствие отсутствия срока хранения для категории? [Coverage, Exception Flow, Gap] | PASS | FR-050 unknown mode errors |
| CHK037 Условие блокировки готовности из-за устаревшей копии выражено числом? [Measurability, Spec §FR-034, SC-010] | PASS | FR-034/SC-010 freshness0<=age<26h |
| CHK038 Условие нагрузки в критерии о всплеске трафика выражено измеримо? [Measurability, Spec §SC-012] | PASS | SC-012/operations minute baseline/5xR |
| CHK039 Каждый критерий успеха соотнесён хотя бы с одним функциональным требованием? [Traceability] | PASS | Spec FR/SC + model traceability |
| CHK040 Содержание отчётов перечислено до проверяемого набора? [Completeness, Spec §FR-040] | PASS | FR-040 explicit reports |
| CHK041 Требование о владельце и обязательных оговорках отчёта проверяемо? [Measurability, Spec §FR-042] | PASS | FR-042 owner/freshness/caveats |
| CHK042 Допущения о первом платном канале и платформе согласованы с планом? [Assumption, plan.md] | PASS | Plan first channel/platform; no paid launch automatic |
| CHK043 Сохранение контрактов фич 093, 094 и 096 задокументировано как зависимость? [Dependency, Spec §Legacy Impact] | PASS | Legacy F093/094/096 restrictions preserved |
| CHK044 Граница между этой фичей и отдельным выпускным решением о запуске платного трафика явная? [Clarity, Spec §FR-044] | PASS | FR-044 launch approval separate |
| CHK045 Открытые эксплуатационные решения записаны с указанием владельца? [Gap, plan.md] | PASS | Plan declared engineering owners/T110/etc dependencies |

Итог: **45 checked / 0 unchecked**.

### security.md

| Пункт | Вывод | Проверенные требования / причина |
| --- | --- | --- |
| CHK001 Определено, какие категории данных относятся к персональным, а какие нет, с признаком разграничения? [Completeness, Spec §Правовая конструкция измерения] | PASS | Spec levels; pseudonym explicitly personal |
| CHK002 Указано, что запрет на содержимое встреч, аудио, расшифровки, токены и локальные пути сохраняется без ослабления? [Completeness, Spec §FR-008] | PASS | FR-008; activation deny content/secrets/private IDs |
| CHK003 Перечень запрещённых полей остаётся единым источником правды и не дублируется в новых требованиях? [Consistency, Spec §FR-008, §Legacy Impact] | PASS | Existing forbidden-fields source preserved |
| CHK004 Определено, что происходит с данными, если правовое основание уровня отпадает? [Coverage, Exception Flow, Gap] | PASS | activation lifecycle+quickstart: отдельные технический сбой, unknown gate и purpose withdrawal; cancelled не повторяется |
| CHK005 Перечислены все внешние получатели данных измерения с указанием, какие данные каждый получает? [Completeness, Spec §FR-028, plan.md] | PASS | FR-028; exactly existing PostHog/Yandex |
| CHK006 Указано, что данные посетителей не попадают во внешний канал оповещений? [Clarity, contracts/operations.md] | PASS | operations metadata-only alert |
| CHK007 Условие передачи данных в рекламную платформу выражено проверяемым признаком, а не формулировкой «при наличии основания»? [Measurability, Spec §FR-028] | PASS | FR-028 current advertising gate side effect |
| CHK008 Требование о предварительном согласии абонента для рекламы по сетям связи отделено от требования о согласии на измерение? [Consistency, Spec §FR-029] | PASS | FR-029 contact advertising separate |
| CHK009 Определено, что происходит при отзыве согласия после того, как данные уже переданы внешнему получателю? [Coverage, Gap] | PASS | FR-049 recipient requests not remote deletion proof |
| CHK010 Явный режим хранения задан отдельно для каждой категории, включая IP; окно атрибуции отделено от удаления истории? [Completeness, Spec §FR-036, data-model.md] | PASS | model+operations explicit new until_decision category |
| CHK011 Указано, где именно применяется режим хранения для каждой категории, включая IP? [Clarity, contracts/operations.md] | PASS | model public.product_activation_milestones graf_postgres |
| CHK012 Явный режим без удаления по возрасту отличим от отсутствующего или неизвестного режима, и определено последствие ошибки? [Coverage, Exception Flow, Gap] | PASS | FR-050 missing mode error |
| CHK013 Отдельное решение или обязательное требование на удаление имеет собственный срок исполнения, наблюдаемо и журналируется? [Measurability, Spec §FR-036] | PASS | FR-036/048 separate owner/deadline/result |
| CHK014 Формулировки об удалении остаются в пределах контролируемого хранилища? [Consistency, Constitution §IV] | PASS | Constitution IV bounded control deletion |
| CHK015 Новые категории данных зарегистрированы в правилах хранения, а не описаны только в спецификации? [Completeness, Constitution §IV] | PASS | model/operations registration + planned retention/lifecycle implementation |
| CHK016 Строгий режим «только по разрешению» сохранён и прямо защищён от возврата к режиму по умолчанию? [Consistency, Spec §FR-001] | PASS | FR-001 no default mode |
| CHK017 Отсутствие решения посетителя трактуется как запрет для всех необязательных целей? [Clarity, data-model.md] | PASS | consent model unknown denied |
| CHK018 Разделение согласия по целям задано так, что одна цель не тянет за собой другую? [Consistency, Spec §FR-002] | PASS | FR-002 distinct purposes |
| CHK019 Отзыв согласия соблюдается в последующих визитах, а не только в текущем? [Coverage, Spec §FR-003] | PASS | FR-003 later visit/current register |
| CHK020 Определено, что запись о решении посетителя не используется как источник данных измерения? [Consistency, contracts/anonymous-aggregate.md] | PASS | anonymous contract no consent reuse |
| CHK021 Требование о числе операторов и втором факторе выражено проверяемо? [Measurability, Spec §FR-037] | PASS | FR-037 operators2/MFA |
| CHK022 Указано, что конфигурация измерения версионируется, и что именно подлежит проверке соответствия? [Clarity, Spec §FR-038] | PASS | FR-038 configuration versioning |
| CHK023 Определено, кто отвечает за реагирование на оповещение о деградации? [Completeness, contracts/operations.md] | PASS | operations named infra_operator |
| CHK024 Определено, что происходит с доступом при увольнении или смене оператора? [Coverage, Gap] | PASS | FR-055 access removal |
| CHK025 Требование о записи об одобрении покрывает правовое подтверждение отдельно от остальных? [Completeness, Spec §FR-047] | PASS | FR-047 separate legal record |
| CHK026 Разделены происхождение адреса и доверие к передающему сокету; описаны недоверенные локальные/Docker участники, поддельные заголовки, UNKNOWN и обход SNI/Host? [Completeness, Spec §FR-062; Quickstart §Сценарий 8] | PASS | FR-062 ingress trusted sockets distinct IP |
| CHK027 Требования запрещают непредусмотренное сохранение visitor IP в журналах и новых получателях при изменении прокси; прежние границы семипольного хранилища и включения writer сохранены? [Consistency, Spec §FR-061; Plan §Полный вход T098] | PASS | FR-061 same7-field separate IP storage; no new proxy logging |

Итог: **27 checked / 0 unchecked**.

### infra.md

| Пункт | Вывод | Проверенные требования / причина |
| --- | --- | --- |
| CHK001 Целевое хранилище копий названо конкретно, а не описано общими словами? [Ambiguity, Spec §FR-033] | PASS | operations backup named local target |
| CHK002 Явно определены размещение копий и граница защиты при отсутствии внешней копии? [Clarity, Consistency, Spec §FR-034/052/053, Session 2026-10-22] | PASS | FR-052/053 all copies may be lost |
| CHK003 Расписание копирования задано с частотой, а не только словом «автоматически»? [Measurability, Spec §FR-033] | PASS | FR-033 daily schedule; readiness26h |
| CHK004 Определено, что происходит при неудачном копировании? [Coverage, Exception Flow, Gap] | PASS | operations failed/unknown blocks |
| CHK005 Определено, сколько копий хранится и как старые копии удаляются? [Coverage, Gap] | PASS | operations last7/min2 complete sets |
| CHK006 Условие блокировки готовности из-за отсутствия или устаревания копии выражено числом? [Measurability, Spec §FR-034, SC-010] | PASS | FR-034 numeric age criterion |
| CHK007 Частота проверки восстановления задана числом? [Measurability, Spec §FR-035, SC-010] | PASS | FR-035/SC-010 <=30days |
| CHK008 Определено, что считается доказательством успешного восстановления? [Clarity, Spec §FR-035] | PASS | operations T110: checksum/schema/source/runtime, точка/сверка, states/unique/FK, quarantine/deletion/cleanup receipt; partial/old deny |
| CHK009 Описан порядок действий при неудачной проверке восстановления? [Coverage, Exception Flow, Gap] | PASS | operations failed restore/re-enable manually |
| CHK010 Указано, восстанавливается ли измерение полностью или частично при потере узла? [Coverage, Gap] | PASS | FR-053 point gap and whole host loss |
| CHK011 Условие нагрузки в критерии о всплеске трафика выражено измеримо? [Measurability, Spec §SC-012] | PASS | SC-012 5xR20min measured |
| CHK012 Указано, какой именно показатель считается обычной нагрузкой? [Ambiguity, Spec §SC-012] | PASS | SC-012 p95 complete10080-minute baseline |
| CHK013 Определено, что публичная страница не зависит от доступности стека аналитики? [Clarity, Spec §FR-032, research.md §2] | PASS | FR-032 public product analytics fail-open |
| CHK014 Требование о порядке отключения при деградации однозначно: первой отключается аналитика? [Consistency, Spec §FR-032] | PASS | FR-032 shared-FS analytics first |
| CHK015 Заданы требования к поведению измерения при недоступности внешнего счётчика? [Coverage, Edge Case] | PASS | activation per-provider states no blind retry |
| CHK016 Условия аналитической и общехостовой области перечислены с проверяемым разделением сигналов и действий, включая общий физический ресурс и совместное срабатывание? [Consistency, Spec §FR-031] | PASS | operations shared-FS/analytics/host priorities |
| CHK017 Указано, что общехостовые пороги не отключают измерение автоматически? [Clarity, Spec §FR-031] | PASS | FR-031 with explicit shared-FS protection exception |
| CHK018 Срок доставки оповещения задан для каждого класса деградации? [Completeness, Spec §SC-009] | PASS | SC-009 classes and<=15min |
| CHK019 Определено, что оповещение доставляется по пути, независимому от измеряемого сервера? [Clarity, Spec §FR-030] | PASS | operations astraglobal independent direct route |
| CHK020 Определено поведение при недоступности самого канала оповещения? [Coverage, Exception Flow, Gap] | PASS | FR-056 separate failure route/error not PASS |
| CHK021 Указан владелец каждого правила оповещения? [Completeness, contracts/operations.md] | PASS | operations named owners |
| CHK022 Заданы требования к наблюдаемости роста объёма хранилища? [Completeness, Spec §FR-039] | PASS | operations inventory classification includes relation |
| CHK023 Указано, какой абсолютный объём и какая скорость роста считаются приемлемыми? [Measurability, Spec §FR-039] | PASS | operations128GiB/0.5GiBday/90days accepted criteria not measurements |
| CHK024 Определено, что происходит при приближении хранилища к заполнению? [Coverage, Edge Case, Spec §Edge Cases] | PASS | shared-FS<20% stop optional writing no deletion |
| CHK025 Заданы требования к поведению при обновлении или откате версии платформы аналитики? [Coverage, Edge Case, Spec §Edge Cases] | PASS | operations rollback/version fingerprints |
| CHK026 Полный путь общего SNI-входа и границы владения соседними маршрутами определены без подмены рабочего доказательства изолированным прототипом? [Completeness, Plan §Полный вход T098; Quickstart §Сценарий 8] | PASS | T098 full SNI ownership/public binds |
| CHK027 Требования к сохранению ресурсов, таймаутов, настоящего special-протокола и соседних vhost измеримы и охватывают оба семейства адресов? [Measurability, Quickstart §Сценарий 8] | PASS | T098 IPv4/v6/resources/special measured checks |
| CHK028 Стадии перехода и возврата учитывают позднее соединение прежнего worker, дренирование и запрет прерывания чужих сессий? [Coverage, Plan §Полный вход T098] | PASS | T098 oldworkers/drain/lateClientHello |
| CHK029 Временная совместимость ограничена владельцем, конечным сроком, условием снятия и задачей; приёмка измерения запрещена до удаления прежнего обхода? [Consistency, Spec §Legacy Impact; Plan §Полный вход T098] | PASS | Legacy expiry/owner/removal task; readiness blocks bypass |

Итог: **29 checked / 0 unchecked**.

Итого: **117 checked / 0 unchecked, PASS качества требований перед реализацией**. Исторические T098 и промежуточный HOLD сохранены как история; текущий PASS основан на новом просмотре исправленного снимка. Остальные analyze/issue-sync/validation/runtime/release gates сохраняются.

## SHA-256 прочитанных входов

- `.specify/memory/constitution.md` — `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`
- `docs/agent-guidance/README.md` — `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb`
- `docs/agent-guidance/product-gates.md` — `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`
- `docs/agent-guidance/document-reading.md` — `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411`
- `docs/agent-guidance/spec-kit-flow.md` — `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`
- `docs/agent-guidance/development-process.md` — `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864`
- `specs/273-paid-traffic-analytics/spec.md` — `0058816587634dc8235c0d2fa44a02218a5978488e37d001a0c909342401155d`
- `specs/273-paid-traffic-analytics/plan.md` — `86991b85ebeed9a9c3d7d2d50a980b4eb827796734fa0b4bd6df7f92c08e79ec`
- `specs/273-paid-traffic-analytics/tasks.md` — `f5fe73b9847ac10d05029af9ed93ef939e119cf46e4b1cdd8c1cbdcf6fe48787`
- `specs/273-paid-traffic-analytics/quickstart.md` — `c8fdc2c68ffc8e3aa86ed32b250603022e643df4e4f3ede3091a073fe1b05479`
- `specs/273-paid-traffic-analytics/research.md` — `a9b5331c68424cd86f47119b8994db442da4250cc536683695d9488fe9b6f46b`
- `specs/273-paid-traffic-analytics/data-model.md` — `52fb96e3dd9c399c741a9c982916fd755a056580efdd36539bfc7f1a91cc74be`
- `specs/273-paid-traffic-analytics/legal-basis.md` — `f5c8b5ea1bb2a145f438069dc64b0e3816fb46496de86aecd17d02d47db3d423`
- `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` — `2bba8a3fa0a7040591664343158e4d0b3b1045cfe356a96e3e30e2f93fa4adc5`
- `specs/273-paid-traffic-analytics/contracts/operations.md` — `f696f7b87024783dad0a28ab84af0c7b3dc2329a595eb470c256232a3797c0fb`
- `specs/273-paid-traffic-analytics/contracts/attribution-handoff.md` — `8d5808a1bd4a1bbc6fbdbbc8cf1d301e246dd8822c25e841bef7ceaca723fd82`
- `specs/273-paid-traffic-analytics/contracts/anonymous-aggregate.md` — `7e10a25d64c9d94951bec8440c1c84d205e5bfc0e87f31364f0739c5357ca47f`
- `apps/server/src/twobrain_rec_server/product_analytics/milestones.py` — `ace3d2ead15dbef408f26278ba7c338da63abc8c0f2173f5f958dcf2f0ccc2d8`
- `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` — `f62a2713da17a38898be1149a5b2d7dee9ccb504fa0cd70cef76426856f92c5f`
- `apps/server/src/twobrain_rec_server/product_analytics/router.py` — `864b3da9bf0ff45b1d67839e37054598b8684deb4e870110ede37c552bc8d588`
- `apps/server/src/twobrain_rec_server/product_analytics/event_catalog.py` — `0d8740eb6a3c30e428447d9e9cadc735273d670207efb0907cb5dc4499767c2d`
- `apps/server/src/twobrain_rec_server/api/product_analytics.py` — `122824470fcbe5a4c46e5c425adf4855501ca622bb7c840f1424cf404bfe2a8a`
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_lifecycle.py` — `94c5b3d5dd5337eebb686d90ad049d4db5d2dc0cb722e54690a5e5aa5c62e2f4`
- `apps/server/src/twobrain_rec_server/product_analytics/retention.py` — `fd1ce8c278fccdce608ba99c916853e34706e68ecdb08a810ba645488b0b84b6`
- `apps/server/src/twobrain_rec_server/auth/account_closure.py` — `774053658513600e4b5cc702bd4e341de7467d6a724c40daf561318a05e83ec0`
- `apps/server/src/twobrain_rec_server/deletion/service.py` — `4534012daa4f54dfe5fd58cc8bba5674c4771e9c108697c34820b4a3c5b3aa00`
- `apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py` — `e53d4573d0d6094962afebc8862232b6958ab7dd3e76c5fbdc069144aa2928a4`

Кодовые зависимости исследованы в пределах аналитического ingress/delivery, level disposition, account closure, meeting-close fanout и maintenance orchestration; полное чтение больших соседних модулей не заявляется.

## Контроль результата

`git diff --check` выполнен до записи: PASS. После записи перечитаны все действующие checkbox строки и статистика; исходные8 документов/прочитанные зависимости повторно сверены по SHA-256. Никаких code/runtime tests, GitHub, commit, release, deploy или сетевых side effects проверяющий не выполнял. Изменены только4 reviewer checklists и этот отчёт. Неизвестность продакшен-оснований/доставки/хранения остаётся отдельным блокером рабочего включения, а не препятствием принятой изолированной разработки после требований PASS/analyze/issue-sync.

- Итоговый `specs/273-paid-traffic-analytics/checklists/requirements.md` — `b10a19943d788e9b8f5b3c9e322f6a614eb60f1cb8ea6cb207404bf82c3f3c30`; 16 checked/0 unchecked.

- Итоговый `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` — `42f018d295b3c7fe50873612eeff9ec94c71a8d8b810060edb78a59ed7800b38`; 45 checked/0 unchecked.

- Итоговый `specs/273-paid-traffic-analytics/checklists/security.md` — `d9c8078134a53d3a89c1171826a24b3271488fc2ff48687ad6a8bbf95eaf6678`; 27 checked/0 unchecked.

- Итоговый `specs/273-paid-traffic-analytics/checklists/infra.md` — `ea43c13bb2ed6acba078bb6b511bcd6b981ac5db03d652548948b346ecfda87e`; 29 checked/0 unchecked.

- Дополнительно полностью прочитан `infra/scripts/backup-rec-stack.sh` — `64c20e804b6dec0e73dd3c28778c81a9d076b3ddea5190ad4fb41961a40c20fc`.

- Дополнительно полностью прочитан `infra/scripts/rehearse-rec-restore.sh` — `fd442e9e76030bcc73244a706b36cc8ddf996e122f8f1d330431416dd62850ac`.

Итоговый digest восьми требований (SHA-256 JSON mapping, sort_keys=True,separators=comma/colon): `95663c306cd000b6e2c32f66e8588847f1e2c329c33d658c38300df0e5fe7fdf`.
