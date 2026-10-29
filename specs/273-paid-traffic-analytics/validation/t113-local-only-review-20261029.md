# F273/T113: независимый докодовый гейт local_only — 29.10.2026

**SCOPED PASS по требованиям узкого подготовительного среза.** Все117 действующих вопросов прочитаны и оценены на согласованность с предложенным срезом; итог117 отмеченных /0 неотмеченных. Отметки не менялись. Докодовых blockers в этом объёме нет; разрешения открыть рабочий admission, снять `activation_recovery_unverified` или закрыть T113 этот вывод не даёт.

## Область и источник

Независимый reviewer `/root/f273_release_boundary`. Объявленная основа `5c1ab517a194b5102a4fbefa732840e071717841`, ветка `codex/f273-local-period-20261029`, F273/T113, high-risk-product. Активная feature.json и prerequisite paths указывают одну F273; ownership содержит объявленные config/ingest/legal gate/API/tests. Физическое имя worktree не использовано как определение фичи. Git/GitHub и рабочая среда не менялись; актуальность issue #7804 взята из задания/проекта, отдельной рабочей проверкой GitHub здесь не подтверждалась.

Проверен весь конечный проект `.dev/growth/t113-local-only-scope-20261029.md`, принятое R3 и его независимый scoped analyze. Сохраняется вариант A/R3 с единственным первым периодом; вариант B не принят. Предыдущие отчёты не заменяли чтение затронутых требований и117 вопросов.

## Проверка непротиворечивости и анализ-гейт

| Проверяемая граница | Основание и вывод |
| --- | --- |
| Режим | Activation-milestones §Режим и договор настроек прямо определяет отдельный local_only. Settings во всех средах требует enabled=true, provider_mode=disabled; PostHog master, оба продуктовых Яндекс-пути, desktop-direct/egress выключены. Проект также выключает replay. Подчинённые неактивные настройки автосбора с прежними defaults сами по себе не являются включением передачи. Прежние режимы сохраняются. |
| Повторная проверка | Несовместимость отклоняется и конфигурацией, и свежим admission. Вызов после ожидания account-lock обязан заново проверить режим/flags до INSERT. Смена режима в течение запроса означает отказ, а не переход к внешним намерениям. Это исполняет существующий контракт, не новый продуктовый gate. |
| Получатели | local_only возвращает providers=() до resolver/exporter/transport. Новые строки имеют not_requested/not_requested. Отдельные provider gates остаются прежними. Общая PostHog readiness не становится разрешающим обходом собственного GRAF recovery; постоянный activation_recovery_unverified остаётся безусловным. |
| Второй HTTP-формат | Контракт T113 требует общего admission для /events и /posthog-desktop-capture. Допуск второго формата в local_only при выключенном egress соответствует ему: это прежняя форма запроса к первичному серверу. Он должен пройти существующие auth/trusted-subject, telemetry, api_key_state, payload/catalog проверки и общий ingest. Он не включает прямой desktop egress, не разрешает прочие события/браузерный autocapture и не меняет прежний provider-путь в остальных режимах. |
| Повтор после смены режима | Unique account+event и неизменяемое первое решение сохраняются. Переход из local_only в иной режим не превращает прежние not_requested в pending и не создаёт скрытой передачи старой строки. Дубликат возвращает прежнее решение; нельзя переписать его payload/время/кампанию/состояния. Прежние решения иных режимов также не изменяются локальным повтором. |
| История и восстановление | План §Первый локальный период, operations §Приёмка и R3 сохраняют полный history proof, backup/restore, единственный started_at, protected filesystem/DB fences и fail-closed unknown. Срез не добавляет trusted verifier и не снимает activation_recovery_unverified; положительный учебный тест с заменённым gate не является рабочим допуском. |
| Основания/удаления | FR-026/034–036/048–050, until_decision, fresh register/disclosure и resource guard сохраняются. Обычный analytics HOLD не блокирует продукт и обязательные account/category DELETE. Нет новых полей, identity, таблиц, получателей или импорта истории. |
| Границы задачи | Существующие T113 и T112 открыты. Это локальная часть T113, без нового выпуска/Full/CD/рабочего включения. T112 и коммерческие AC не закрываются. |

Анализ R3 остаётся применим: его проект имеет тот же SHA256, spec.md и plan.md совпали с входами прежнего анализа. Tasks дополнен фактическими частичными результатами; соответствующие секции перечитаны, T113 осталась открытой. Текущие activation-milestones и quickstart содержат принятый договор mount ID, ранее независимо проверенный; эта поправка не меняет local_only/получателей. Новый узкий scope конкретизирует уже принятый договор настроек и общий HTTP admission, не меняя цель/основание/семантику первого события. При повторном scoped анализе затронутых требований не найдено CRITICAL/HIGH или обязательного нового уточнения. Старый R3 PASS не объявлен PASS будущего кода или всей текущей сборки.

## Все действующие вопросы reviewer-owned чек-листов

Повторно прочитан текст каждого117 действующего вопроса, включая поздние security CHK026–027 и infra CHK026–029. Каждый оценён на ослабление/противоречие данным срезом. Ниже основания сгруппированы только для компактности; соседняя реализация и историческая рабочая приёмка заново не присваивались.

| Список / вопросы | Основание сохранения отметок в данном срезе |
| --- | --- |
| Requirements, все16 | User Story3, FR021/025/026, измеримые SC006/007, отдельный проверяемый договор local_only и негативные сценарии quickstart заданы; нет новой цели, допущения или расширения измерения. Качество требований не означает достигнутый outcome. |
| Privacy CHK001–007 | Правовая конструкция уровней и прежние категории/запрещённые поля не расширены. Локальная веха остаётся уровнем2, псевдоним не объявлен обезличиванием; approvals не заменяются режимом. |
| Privacy CHK008–015 | Согласие/отзыв/unknown/register по-прежнему проверяются свежо; local_only не превращается в согласие и не соединяет уровни1/3. |
| Privacy CHK016–025 | Запрещённые поля, метки и гранулярность/корзины/фильтрация служебных наблюдений, окно90дней и unknown/direct не меняются. |
| Privacy CHK026–030 | Доверенный субъект, уникальность account+event, общий HTTP/server-auth admission, T112 и различие установки/просмотра/активации сохранены. Дубликат не создаёт намерения после смены режима. |
| Privacy CHK031–038 | Сроки/пороговые условия alerts/ресурсов/локальной копии и until_decision не снимаются, recovery остаётся закрыт. |
| Privacy CHK039–045 | FR/SC и отчётность/оговорки/владельцы/зависимости093/094/096 сохраняются; подготовка режима не является платным launch approval. |
| Security CHK001–009 | Ни данные, ни получатели не расширены. providers=() предшествует provider decisions; consent и post-egress deletion остаются отдельными. |
| Security CHK010–015 | Категория activation_milestone_decisions уже зарегистрирована, until_decision и scope/deadline/result/restore-delete сохранены. Режим не разрешает бессрочное хранение неизвестной категории или сброс счёта при удалении встречи. |
| Security CHK016–025 | Строгий режим, unknown, цели, operator access/MFA/config version/правовые approval не ослаблены; local_only не открывает рабочий writer. |
| Security CHK026–027 | Proxy/IP и семипольный IP writer не затронуты; допуск второго HTTP payload не доверяет клиентскому account ID/IP и не включает IP-хранение. |
| Infra CHK001–010 | Действующий контур полной локальной копии/restore/cleanup и границы потери узла сохранены; нет подмены GRAF recovery PostHog receipt. |
| Infra CHK011–020 | Нагрузка/деградация/общий диск/алерты не меняются; отказ измерения не ломает продукт. Свежесть и внешнее наблюдение не объявлены принятыми. |
| Infra CHK021–025 | Владение/рост/пороги/rollback заданы действующими contracts; новый режим не возвращает ready из старого образа и не удаляет историю по возрасту. |
| Infra CHK026–029 | Общий SNI ingress/соседи/ресурсы/T098-временная совместимость не меняются. Изменение API-формата local_only не означает новую сетевую экспозицию или принятие T098. |

| Чек-лист | Отмечено | Не отмечено | SHA256 |
| --- | ---: | ---: | --- |
| `infra.md` | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |
| `privacy-measurement.md` | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| `requirements.md` | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| `security.md` | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |

Итог **117/0**, отметки не менялись. Текст всех действующих вопросов повторно проверен при подсчёте. Это подтверждение качества требований в узком scope.

## Проверки, необходимые после реализации

- Конфигурационные положительные/отрицательные случаи development и production: local_only отдельно, каждый конфликтующий master/provider/egress/replay flag, enabled=false, неподходящий provider_mode; прежние режимы сохраняют ограничения.
- Реальный общий admission через оба HTTP-формата и server-auth на изолированной PostgreSQL: одна account+event, not_requested/not_requested, повтор после смены режима не меняет решения и не создаёт provider intents.
- Resolver/exporter/transport должны быть недостижимы в local_only даже при искусственно разрешающем provider gate в тесте. Это причинная проверка ранней ветви, а не один только результат disabled-провайдера.
- После ожидания строки аккаунта: смена validation_mode/flags и withdrawal отказывают до INSERT. При сохранённом настоящем recovery gate обе HTTP-ветви и server-auth остаются HOLD, без строки и внешней передачи.
- Независимое ревью diff и focused checks после кода обязательны. Полная интеграция filesystem/DB/оператора, actual restore, рабочие входы истории и конечные PR/release gates относятся к остальной T113.

## Прочитанные документы и граница повторного чтения

В рамках разрешённого пользователем исключения повторного чтения F273 заново прочитаны затронутые целые разделы: spec §User Story3, §Functional Requirements и §Пробелы; plan §ПродолжениеT112/T113, §Закрытые файлыGRAF, §Первый локальный период; tasks §Phase13 и все три секции исполнения первого периода28–29.10; data-model §Веха активации и §Устойчивое решение; полный activation-milestones; operations §Lifecycle первой вехи со всеми подразделами; quickstart §Первый локальный период. Конституция, product-gates и spec-kit-flow прочитаны целиком. PRD перечитан в применимых полных разделах25/26, current-product-status — analytics093/094 и непринятый096; полную историю PRD/status заново прочитанной не называю. Проверены собственные текущие хеши этих файлов. Ранее прочитанное и пересказ не выданы за текущую рабочую приёмку.

Дополнительно просмотрены текущие Settings, весь activation_milestone_write_blockers и provider_delivery_gate, общий ingest и второй HTTP handler/его модель запроса. Кода для нового scope на момент ревью ещё нет; это докодовая проверка договоров. Тесты, сборки, контейнеры и рабочие подключения ревьюер не запускал. Изменён только данный отчёт; checklist/code/spec/plan/tasks/Git/GitHub/runtime сохранены.

### SHA256 входов

| Путь | SHA256 |
| --- | --- |
| `.specify/feature.json` | `5360e4f237708cf25d48aaefd4c7a1764e72da71339d9231fd7bb4c32ac9292c` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `specs/273-paid-traffic-analytics/spec.md` | `0058816587634dc8235c0d2fa44a02218a5978488e37d001a0c909342401155d` |
| `specs/273-paid-traffic-analytics/plan.md` | `ec8c56970d71c8dc76d864c4218d653c1ba4e7efaef98a2d99c27b10d25bfb6f` |
| `specs/273-paid-traffic-analytics/tasks.md` | `735b20715d4d58d981c38bffed913bd5b2350db25ad34bd0eb6cca997661d448` |
| `specs/273-paid-traffic-analytics/data-model.md` | `52fb96e3dd9c399c741a9c982916fd755a056580efdd36539bfc7f1a91cc74be` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `dc508089165b26025ffc9fe338aff049f1f7e55e1bda958f9ad187ae2828a297` |
| `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` | `1c186585f56321d49d587875aa900d44496733b8f31467a81615bada0034912e` |
| `specs/273-paid-traffic-analytics/contracts/operations.md` | `5b24fae4b8cfae1335890f2f18cbabc26c0174d1da8e97012b10baf627a526d6` |
| `.dev/growth/t113-local-period-next-design-20261029.md` | `2373296a023254af5644593d311c65c90d67940c25c91024cbfa3eef265a4aa5` |
| `.dev/growth/t113-local-period-next-design-r3-review-20261029.md` | `aa79e67d9dcc00da81e18bd7a3ce7797f064979e0abdabf8333b3d2e76625dca` |
| `.dev/growth/t113-local-only-scope-20261029.md` | `7b31858c4d71794ce24dbc70f26bf8c424381dcd1d966245ccb54bb777f13daf` |
