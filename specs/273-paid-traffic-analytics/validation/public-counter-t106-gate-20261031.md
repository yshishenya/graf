# F273/T106: предварительный гейт публичной Метрики и relay — 31.10.2026

Проверяющий: `/root/public_counter_readiness_review`.
Точная основа: `82b6c4023705299553a3974fbd2ae97b09294e7e`.
Ветка: `codex/release-rls-tests-20261031`.
Режим: чтение требований и реализации; меняется только этот отчёт.
Этот срез не входит в PR #7846 или текущий выпуск.

## Решение

**HOLD для восстановления публичного внешнего счётчика одной сменой env или добавлением проверки только при открытии HTML.** Требования достаточны и остаются действующими; недостаточен механизм их исполнения в уже открытой вкладке. Нужен отдельный принятый инженерный план в существующей T106 и затем профильная приёмка. Новая фича, инфраструктура, поставщик, хранилище событий или ослабление согласия не требуются.

**Допустимый первый узкий срез T106** — единое актуальное решение для public context и `/analytics/public-event`, проверка непосредственно перед relay/provider side effect, fail-closed при неизвестном основании и прекращение управляемых браузером отправок после отзыва. Это можно реализовать в существующих модулях, сохраняя внешний скрипт выключенным до доказанной приёмки его собственного прекращения. Такой промежуточный PASS не означает восстановления Метрики или завершения T106 целиком.

## Что уже установлено непосредственно

### Public context и Яндекс

`public/analytics.py:build_public_analytics_context` вычисляет enabled по флагу public, окружению/validation mode, counter ID, совпадению редакции и известной публичной surface. Withdrawal register он не читает. `public/templates.py:public_analytics_page_context` использует именно этот builder при формировании страницы. Следовательно, корректная revision сама по себе может открыть старую public ветвь без актуального решения об отзыве основания.

В `public/static/public/analytics.js` publicConfig читается один раз из HTML. `canUseAnalytics` проверяет локально сохранённые переменные categories/state, а не текущее серверное решение. `ensurePublicYandexProvider` вставляет внешний tag.js, вызывает init и hit; `dispatchEvent` вызывает reachGoal по прежнему контексту. В init стоит `accurateTrackBounce: true`; replay/maps могут включаться отдельным разрешением и runtime flags. Уже запущенный внешний код не обязательно ограничен явными вызовами GRAF.

`handleConsent` прекращает управляемые отправки при callback отказа/отзыва в той же вкладке. `disableOptionalProviders` ставит disableYaCounter и блокирующие флаги; подтверждённого остановленного сетевого пути настоящего SDK или очистки его отложенных задач здесь нет. Обработчиков storage, pageshow, visibilitychange/focus и обновления серверного разрешения нет. Изменение localStorage в другой вкладке и отзыв глобального основания после загрузки страницы не обновляют эти локальные переменные автоматически.

Внешний public скрипт допустим только на `/` и `/download`; остальные публичные страницы получают только first-party relay. Расширять external/replay scope для решения T106 не нужно. Опубликованный более широкий охват measurement не разрешает расширять third-party scope.

### Relay и существующая серверная защита

`public/web.py:public_analytics_event` уже проверяет public flag, точную текущую revision настройки и payload, same-origin, размер и закрытый каталог полей/событий. Затем вызывает `deliver_public_analytics_event` в отдельном потоке. Сам route не вычисляет свежее withdrawal-aware решение перед допуском, поэтому при подменённом transport или будущем другом delivery пути самостоятельной гарантии нет.

`deliver_public_analytics_event` использует `PostHogClientWrapper`. Его `capture_event` уже вызывает `resolve_provider_delivery_gate` перед transport; helper читает текущий withdrawal register и блокирует отозванный provider_analytics, ошибки файла, отключённый provider, непригодную readiness и одобрения. Это пригодная повторная серверная граница, её не следует заменять одной проверкой route или HTML. Полезно различать accepted relay input, реальную отправку и подтверждённое чтение получателя: HTTP202 здесь не доказывает внешний визит.

Индивидуальный consent relay проверяет по данным самого запроса. В просмотренном public пути нет endpoint, который принимает и сохраняет отдельный отзыв посетителя на сервере. Тест «grant, затем payload revoked» доказывает отказ конкретному revoked payload, но не доказывает, что повтор старого accepted payload отвергается после серверного принятия отзыва. Нельзя объявлять эти два доказательства одинаковыми. Требование FR-003 сохраняется; новый постоянный идентификатор/реестр посетителей для его исполнения в этом ревью не предлагается. Если план претендует на серверное принятие индивидуального отзыва, он должен назвать существующую доверенную границу и точную судьбу старой заявки, а не только положиться на transport поле.

## Что переиспользовать, а что не подходит целиком

| Существующий элемент | Применимость |
| --- | --- |
| `read_basis_withdrawal_register`, `BasisWithdrawalRegister`, `measurement_level_basis_states`, `level_processing_allowed` | Чтение и интерпретация фактического основания уровня, без новых файлов/форматов. |
| `resolve_provider_delivery_gate(settings, provider=...)` | Актуальная серверная проверка прежних продуктовых provider путей; PostHog сохраняет её перед transport. |
| `build_public_analytics_context`, `public_analytics_page_context` | Единое место для сужения public контекста новым текущим решением, без нового набора поверхностей. |
| `/analytics/public-event`, normalizer и `PostHogClientWrapper` | Существующий маршрут приёма, closed allowlist и последняя серверная граница доставки. |
| `handleConsent`, `disableOptionalProviders`, `startGrantedProviders` | Переиспользуемые локальные точки прекращения/старта; требуется актуальное состояние и проверка асинхронных гонок. |
| `/api/v1/product-analytics/catalog` | Читает текущую готовность, но возвращает широкий продуктовый каталог; не является узким public permission endpoint и не даёт callback старой вкладке. |
| `/telemetry-gate/disclosure` и `/telemetry-gate/access` | Раскрытие/ограничение продуктовой телеметрии; access вычислен по переданному state. Не являются текущим серверным разрешением public counter. |
| `legal_basis_write_gate` | Сейчас разрешает только локальные уровни1/2 и имеет legacy missing-register semantics; напрямую применять к уровню3 нельзя. |

Полный продуктовый gate требует product flags, provider readiness, доступ операторов и launch approvals. Нельзя механически назначить `provider=yandex_all_pages` для старого public counter: получится зависимость от другого переключателя/инвентаря и чужой области. Нельзя и убрать эти существующие проверки у PostHog ради public relay. Минимальная реализация должна отдельно назвать: публичный разрешённый scope и его настройки; свежий отзыв provider_analytics; индивидуальные категории; а каждый прежний provider путь продолжает свой собственный gate.

Особенность reader: отсутствие и OSError/UnicodeError сейчас одинаково возвращают available=false без file_errors. Существующие legacy тесты допускают отсутствие withdrawal-файла как «отзыв не записан». Поэтому нельзя объявить текущий reader доказательством отказа при нечитаемом реестре; в public срезе неизвестное решение обязано оставаться запретом, а общую совместимость других callers менять молча нельзя. Требуется узко проверить этот случай и согласовать конкретный способ отличить нормальное исходное состояние от неизвестного.

## Минимальный достаточный инженерный объём

1. Сформировать одно вычисляемое в текущий момент решение для старого public scope: public flag/окружение/revision/surface, действующее основание provider_analytics и отсутствие ошибки/неопределённости. Решение не должно быть сохранённым положительным результатом прежнего HTML или config snapshot. Категории конкретного посетителя остаются дополнительной обязательной границей. Ответ/журнал только с безопасным кодом причины; без state path, raw register, visitor identifiers, IP и секретов.
2. Применить решение в public context и самостоятельно в relay. Вызов из worker thread/provider wrapper обязан повторно видеть актуальное основание непосредственно перед своим side effect. Изменение реестра между render, приёмом и transport должно закрывать следующую передачу. Не создавать второй транспорт или новый брокер.
3. Для открытой вкладки использовать узкий запрос к тому же приложению, возвращающий только актуальное public разрешение/редакцию, либо равноценную существующую доверенную границу. Готового подходящего endpoint при просмотре не найдено. Если добавляется маленький route, это изменение существующего сервера, без нового сервиса; ответ не должен кэшироваться как постоянное разрешение или создавать аналитику сам на себя. Все начальные/отложенные public действия до результата закрыты. Ошибка/timeout/неизвестное/старая редакция запрещают измерение, сохраняя работу страницы.
4. Обработать изменения выбора в этой/другой вкладке, возврат из background/BFCache и асинхронный ответ: старый положительный ответ, callback tag.onload, очередь ym или запланированный click/observer не должны повторно включать отменённую цель. Новый grant после отказа может восстановить только заново подтверждённые категории; скрытого повтора накопленных событий не допускается.
5. До включения tag.js дать отдельное доказательство остановки настоящего SDK: после принятого отзыва нет новых init/hit/reachGoal и его собственных автоматических передач. Только disableYaCounter, удаление DOM script, reload на следующий визит или опрос раз в N секунд не доказывают FR-003/048/049 для уже исполняющегося внешнего кода. Между опросами остаётся окно; отмена Promise не отменяет уже переданный запрос. Не следует выдумывать разрешённое окно задержки вместо принятой границы «перед следующей записью или передачей».

Пункты3–5 — инженерное исполнение уже принятых требований. Если конкретный механизм не способен гарантировать границу external SDK, его путь сохраняется закрытым; серверный relay можно принимать отдельно. Это не требует согласования нового продуктового решения с пользователем и не даёт оснований отменять текущий выпуск.

## Какими существующими задачами покрыто

- **T106** — текущее withdrawal-aware решение перед каждым writer/relay/Yandex/PostHog side effect; основная задача этого среза, остаётся partial.
- **T105 и T111** — фактическая текущая опубликованная revision и соответствие текстов/режима хранения; не заменяются корректным строковым значением настройки.
- **T107 / FR-049** — прослеживаемое исполнение отзыва рекламной передачи. Public gate не доказывает remote erasure или весь T107.
- **T099 / FR-012** — числитель согласившихся визитов должен исходить из фактически принятых событий; «запрос отправлен» или202 без delivered не является доказанной доставкой.
- **T112/T113** — настоящие продуктовые вехи/устойчивость; public контекст не открывает writer активации и не подтверждает начало T0.

Контракты: FR-001–006/008, FR-027/028, FR-048/049; F273 `contracts/operations.md` прямо оставляет уже загруженный внешний скрипт в границе T106; `contracts/activation-milestones.md` требует свежий gate перед provider side effect; прежний F093 public contract сохраняет отдельные категории, узкий SDK/replay scope, отказ и доступный продукт при сбое.

## Что можно принять по текущим доказательствам

На уровне чтения исходников подтверждены строгая revision, закрытый payload, запрет typed credential values, две внешние public surfaces, отдельная категория replay и наличие повторного серверного PostHog gate. Существующие тесты покрывают отказ/старую редакцию payload и callback revoke в одной вкладке. Эти свойства пригодны для регрессии; в этой проверке тесты не запускались, поэтому новый PASS исполнения для них не заявляется.

Не подтверждены: public context с текущим отзывом; самостоятельный relay gate; отказ при неопределённом withdrawal source; обновление уже открытой вкладки; cross-tab/BFCache; прекращение автономного настоящего SDK; сквозное внешнее чтение визита; полнота трафика или продаж. Модальные/VM тесты не заменяют наблюдение сетевого поведения SDK.

## Точный минимальный профиль проверки после реализации

1. **Решение/контекст:** public enabled+текущая revision+разрешённая surface; отключённый флаг/старая revision/private route; действующий provider_analytics withdrawal; withdrawal только другого уровня не прекращает независимый уровень3; malformed/нечитаемое/неизвестное состояние. Выполнять повтор в том же процессе после изменения файла: положительное решение не кэшируется. Никаких секретных путей в контексте.
2. **Relay/transport:** валидный consented запрос проходит только при актуальном разрешении; отзыв между HTML и POST, между route и worker transport блокирует реальные provider calls. Повтор старого положительного запроса после принятого отзыва не создаёт передачи. Disabled/dry-run/старая revision/слишком большой payload/cross-origin/запрещённые поля сохраняют прежний отказ. Provider outage не ломает страницу, регистрацию и уровень1.
3. **Управляемый браузер:** загрузка старой страницы до revoke; grant затем revoke; смена localStorage во второй вкладке; BFCache/background resume; ошибка/timeout/status!=success/malformed ответа permission; запоздалый положительный ответ после revoke; tag load callback и запланированные observers/clicks. Считать сетевые вызовы и init/hit/goals, а не только локальные флаги. Без выбора и analytics-only не включают replay; auth/legal/guide routes не загружают external tag.
4. **Настоящий браузер/SDK на изолированной цели:** минимально `/` и `/download` с управляемым tag/network capture, grant→принятый отзыв и последующая активность/ожидание автономных SDK задач. Ровно0 новых внешних передач после границы; ошибка отключения сохраняет HOLD. Не использовать production visitor data и не отправлять реальные тестовые цели в рабочий счётчик без отдельного допуска.
5. **Регрессия:** `tests/unit/test_public_analytics.py`, `tests/unit/test_product_analytics_legal_basis_gate.py`, `tests/unit/test_product_analytics_legal_basis_lifecycle.py`, `tests/unit/test_product_analytics_provider_delivery_gate.py`; `tests/contract/test_public_analytics_contract.py`, `tests/contract/test_public_analytics_consent_enforcement.py`, `tests/contract/test_product_analytics_posthog_autocapture_contract.py`, `tests/contract/test_product_analytics_page_inventory_096.py`; node harness `tests/browser/public-analytics-consent.test.cjs` и реальный modal harness. Добавить случаи выше в существующие тестовые файлы; проверить также непосредственный PostHog capture, а не только подменённую функцию delivery. Пропущенный real-browser сценарий остаётся непройденным gate.
6. После локального focused PASS: независимое code review, converge/analyze и штатные проверки нового точного SHA/выпуска. Перед runtime включением — проверка фактических текстов/flags/readiness и разрешённая контрольная передача с readback. Этот отчёт не разрешает такую передачу и не требует повторять полный выпускный цикл до готового проверяемого изменения.

## Reviewer-owned checklists

Каждый действующий вопрос четырёх списков перечитан, включая добавленные security26–27 и infra26–29. Отметки не менялись: требования определяют точную границу, а обнаружены пробелы реализации/инженерного способа её исполнения. Текущая неготовность external path не переименовывается в недостаток правовой конструкции или требование нового сервера.

| Список | Отмечены | Открыты |
| --- | ---: | ---: |
| security |27|0|
| infra |29|0|
| privacy-measurement |45|0|
| requirements |16|0|
| Всего |117|0|

PASS качества ранее принятых требований не является PASS нового конкретного плана/кода/production. Для before-code допуска внешнего счётчика остаётся HOLD до конкретизации пунктов3–5 и независимого review; для узкого server relay с закрытым external path препятствия требований не найдены. T106 целиком остаётся открытой.

## Источники и контрольные суммы

Для неизменных базовых документов использовано ранее разрешённое пользователем исключение F273 с проверкой четырёх SHA-256. Это не заявление о новом полном чтении после сжатия. Непосредственно прочитаны указанные выше целые затронутые разделы spec/plan/tasks/quickstart/contracts и функции реализации; endpoints/consumers проверены поиском. Готовые тестовые файлы прочитаны в затронутых сценариях; наличие теста не выдано за текущий результат его исполнения.

- `.specify/memory/constitution.md`: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- `docs/prd-voice-layer-final.md`: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- `docs/current-product-status.md`: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- `docs/agent-guidance/product-gates.md`: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- `specs/273-paid-traffic-analytics/spec.md`: `0058816587634dc8235c0d2fa44a02218a5978488e37d001a0c909342401155d`.
- `specs/273-paid-traffic-analytics/plan.md`: `ec8c56970d71c8dc76d864c4218d653c1ba4e7efaef98a2d99c27b10d25bfb6f`.
- `specs/273-paid-traffic-analytics/tasks.md`: `08080dd6034d0e1c3cb4bfb6d9e414e697a9bb1350e32bdad9fa250ffc0cf61e`.
- `specs/273-paid-traffic-analytics/quickstart.md`: `d2359d0bf604bd62410c73f5be7a695eb414bcc9a174dcd50677ce3df49a15df`.
- `specs/273-paid-traffic-analytics/contracts/operations.md`: `5b24fae4b8cfae1335890f2f18cbabc26c0174d1da8e97012b10baf627a526d6`.
- `specs/273-paid-traffic-analytics/contracts/activation-milestones.md`: `8f7e7d0ca401c14ff443846c3c0a86e28f081998994ad7489cc89ef3e9fa41e1`.
- `specs/093-public-landing-analytics/contracts/public-analytics-contract.md`: `23b050ab9ddfc21631f0b26eabfb921aa5e9e6e8c961f2026bfff0b4d1df27b8`.
- `apps/server/src/twobrain_rec_server/public/analytics.py`: `862c8163bf06545536ff8493f817c7feb7be2e286e63dea708b1d87494a7e480`.
- `apps/server/src/twobrain_rec_server/public/web.py`: `33f7a2b294f60c5e2f77079295880a1e1511c5a183f7373fb328d437f64844e2`.
- `apps/server/src/twobrain_rec_server/public/templates.py`: `1ff0ed7e5aff07964ed340f10e3d0c89071b925dc84c8d262433a57da56fcff7`.
- `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`: `cd777e2ab12a7de9860ef76c89972d8bf6a0dbd4e3742bccf23e7d50b065b2d0`.
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_gate.py`: `adb849aca8b9c71a763e567fa507c6be797a84cefcb4460e24b55b3814dd85d1`.
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_lifecycle.py`: `ac4eb465afb0c647b0d3501bdbeaca2a8a4b1d9c6cad59d4c9a9953cae5f81f9`.
- `apps/server/src/twobrain_rec_server/product_analytics/provider_delivery_gate.py`: `fbb2616e62802ee0050b0dd2bf220583bd6f4c9772c2a1d88a261c0bcdc04f9e`.
- `apps/server/src/twobrain_rec_server/product_analytics/posthog_client.py`: `12b49bb9d0eda5731091faf50dcc8ef770d6e1c90bc1a542353d0e7174ca4e5f`.
- `apps/server/src/twobrain_rec_server/product_analytics/browser_context.py`: `4b0eb22b21019fe6dbbf977eea15cb8542466a80bcbbf04b6e39d3dbc3834b8e`.
- `apps/server/src/twobrain_rec_server/api/product_analytics.py`: `93e5212a6499568e77a51feed18af69987e7861a08e98d4959701f6b13572898`.
- `specs/273-paid-traffic-analytics/checklists/security.md`: `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8`.
- `specs/273-paid-traffic-analytics/checklists/infra.md`: `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94`.
- `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md`: `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f`.
- `specs/273-paid-traffic-analytics/checklists/requirements.md`: `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2`.
