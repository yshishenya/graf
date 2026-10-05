# Независимая проверка требований F286 — 2026-10-06

Рецензент: `sharing_critical_review`. Полоса функции: `high-risk-feature` (auth/privacy/backend/UX). Это независимая проверка качества требований и задач до реализации.

## Проверенные источники

`AGENTS.md`, guidance index, spec-kit-flow, product-gates, release-and-validation, применимые разделы product baseline/current-product-status, constitution 7.1.0; активные spec, plan, research, data-model, contracts/sharing, quickstart и security/ux/infra checklists. Указатель `.specify/feature.json` и prerequisite paths сообщают F286, ветка `286-sharing-results`; HEAD `df9c8f4ee4b538cba6c42e1fad6007595e22774a`. Подробная привязка подтверждённых требований записана в каждом checklist.

## Результат

| Контрольный список | [x] | [ ] |
|---|---:|---:|
| security.md | 5 | 0 |
| ux.md | 5 | 0 |
| infra.md | 5 | 0 |

Итог повторной проверки проектирования: **PASS**, 15 подтверждены, 0 открыты. Задачи и analysis перечитаны; требования и декомпозиция проходят независимую проверку перед реализацией. Это не доказательство реализации или разрешение выпуска.

## Первоначальные замечания (устранены повторной проверкой)

1. **HIGH — security CHK001.** contracts/sharing.md:11 обещает сохранить existing behavior для старых full приглашений, хотя research.md:7 описывает опасный вход как адресат из пересланного приглашения. Совместимость должна сохранять старый объём полномочий, а не вход по bearer-токену. Требуется явно применить независимое подтверждение email и запрет bootstrap сеанса также к старым ещё не принятым приглашениям. Уже принятые независимые права не отзываются этим исправлением.
2. **MEDIUM — ux CHK001.** contracts/sharing.md:15 не задаёт «Проверьте отправку» для только неизвестного исхода. Нужны три определённых заголовка: все accepted → «Итоги отправлены»; есть failed → «Отправлено не всем»; нет failed, есть unknown → «Проверьте отправку». Это согласование с проверенным макетом, а не новый сценарий.
3. **HIGH — infra CHK003.** quickstart.md:6 откладывает Downgrade plan, но безопасный порядок пока не указан. Нужны запрет новых публикаций/заданий, прекращение неначатых попыток, учёт зарезервированных отправок, совместимость старого кода со схемой/правами и запрет восстановления удалённого/отозванного доступа. Проверка самого отката остаётся последующей воротой выпуска.

## Что ещё не доказано

В первоначальном проходе tasks отсутствовал; в окончательном проходе перечитаны все T001–T018, зависимости, ответственность, ссылки задач и analysis. Пока не проверены ни новая реализация, ни RLS runtime, ни вход/пересылка, ни сеть/почтовый сервис, ни браузер/GRAF Dev, ни миграция/откат/production, ни exact-SHA CI. Отметки [x] подтверждают только полноту требований проектирования; все эти реализационные доказательства должны появиться в validation и финальном независимом review, а не подразумеваться из этого отчёта.

Рецензент изменил только три reviewer-owned checklist и этот отчёт. Код/spec/plan/tasks/GitHub/коммиты/релиз/продукт не изменены.

## Повторная проверка изменений

Перечитаны актуальные contracts, plan Safe rollback и quickstart. Запрет входа по старому/новому приглашению теперь явен; неизвестный исход имеет согласованный заголовок; безопасный порядок отката определён. Перечитаны три итоговых checklist: каждый 5 [x], 0 [ ]. `tasks.md` пока отсутствует; проверка проектирования PASS, проверка задач ожидается отдельно.

## Окончательная проверка перед реализацией

**PASS — требования/декомпозиция, 15 [x], 0 [ ].** Перечитаны tasks.md, analysis.md, актуальные plan/data-model/contracts/research/quickstart и все три checklist. Основной агент подтвердил синхронизацию 18 задач; reviewer самостоятельно проверил в tasks наличие уникальных ссылок T001–T018 → #7547–7564, но не проверял удалённые labels или состояние чужого #7544. Это отдельное доказательство синхронизации основного агента, не предмет отметок checklist.

Покрытие задач: основа/RLS T002; стабильная проекция, ссылка и её ограничения T003–T006; точная идентичность всех приглашений, неизменяемый пакет, durable sending и неизвестные исходы T007–T010; явная область/Google состав/автоматизация T011–T014; собственный путь/отписка T015; очистка T016; настоящая UI/безопасность/convergence T017; exact-SHA и выпуск T018. Чувствительные проверки поставлены до соответствующей реализации. Конкретные общие файлы закреплены за основным агентом, цепочка миграций согласована.

Последние ограничения прочитаны: auto_epoch исключает восстановление старых заданий после паузы; устойчивый requires_review/cancel требует явного повторного подтверждения; initial occurrence уникален поперёк владельцев/версий/статусов; AUTO ограничен полным Google снимком не старше 15 минут с organizer.self и проверенными участниками пространства. Проверки изменений/конкуренции входят в T011–T013 и T017. Это уточняет защитные границы FR-013–019 и не разрешает отправку внешним/неизвестным участникам.

Все T001–T018 пока открыты. Реализация/браузер/RLS/Postal/production/CI не были выполнены reviewer и не считаются доказанными. После реализации нужен отдельный независимый разбор. Повторных разрешений пользователя эта проверка не требует.

## Независимый разбор реализации — промежуточные замечания

2026-10-06, рабочий код меняется параллельно. Проверены публикация/пакет/доставка/AUTO/API/приглашения, интерфейс, миграции/RLS-предикаты и удаление. Этот раздел фиксирует обнаруженные ошибки, а не окончательный статус после исправлений.

- **HIGH, сохранение прежних прав.** Первоначальная ветка `accept_share_invitation` перезаписывала прежний full grant принятого приглашения тем же адресом. Исправлено в текущем коде сохранением всех активных независимых grants; требуются отдельная проверка оставшихся сроков и точного документа.
- **HIGH, адресный документ и независимый доступ.** API form acceptance и browser continuation выбирают full-meeting redirect до проверки `_shared_publication_override`: получатель с прежними полными правами видит актуальную встречу вместо выбранной сохранённой редакции. Сохранение старого grant также сокращает доступ к новому пакету до срока старого summary grant. `/received` не проверяет отдельный срок чтения пакета (30 дней). Нужна адресная authority на конкретную публикацию, с независимым подтверждённым адресом и собственным сроком; она не должна менять независимые полные права.
- **HIGH, повторное открытие письма.** Browser invitation preview и continuation creation исключают accepted invitation. После первого принятия адрес из письма перестаёт вести к документу даже в пределах срока. Вход по invitation bearer по-прежнему запрещён: безопасное повторное открытие требует самостоятельного входа/совпадения адреса.
- **HIGH, потерянный запрос до commit.** UI сохраняет ключ операции, но при lookup 404 навсегда оставляет только проверку и блокирует нового адресата/отправку. Сохранённый исходный payload и повтор POST с тем же ключом позволяет восстановить попытку без дублирования. Уже добавленный backend lookup устранил отсутствие маршрута, но не этот сценарий.
- **MEDIUM, просроченная ссылка.** UI скрывает grant, create возвращает прежний expired grant с `share_url=null`, и clipboard копирует `/null` с ложным сообщением об успехе. Нужна явная операция восстановления срока/замены и проверка действительного URL до clipboard.
- **MEDIUM, замена legacy ссылки.** Главная кнопка replacement_required вызывает rotate без template_key; legacy grant без сохранённой публикации получает 422. Ссылка должна явно публиковать выбранный формат.
- **MEDIUM, формы без JavaScript.** Прямые Pydantic-конструкторы не обрабатывают ValidationError, поэтому неправильный срок/пустой или слишком большой список дают необработанную ошибку. Основной no-JS путь пока не предоставляет отключение ссылки/отмену пакета. Нужно сохранить эти существенные действия и понятный результат ошибки.
- **MEDIUM, установщик входного nginx.** Synthetic invalid public probe не задаёт обязательный workspace_id и получит 422, хотя установка принимает только 404/429/503. Нужен синтетический UUID запроса. Защита от live drift уже допускает точное повторное совпадение новой конфигурации.

Замечания переданы основному агенту сразу при подтверждении. Старые несоответствия queue/rule schema и отсутствие recipients/operation lookup устранены до выдачи findings. Безусловный open в initDialog не признан ошибкой: сам fragment вставляется только по явному открытию пользователем, исходный host пуст.

Удаление перечитано: порядок recipient → batch → invitations/grants → publication корректен для новых foreign keys; правило series не привязано к удаляемому occurrence и сохраняется. Доставка использует тот же meeting fence до reservation и при фиксации результата. Сеть находится вне DB-транзакции, поэтому уже зарезервированная попытка может завершиться, как и разрешает plan. Новый maintenance recovery переводит stale sending в unknown без повторного транспорта. Положения подтверждены кодом; runtime race/deletion и RLS требуют отдельного доказательства.

Локальная проверка `node apps/server/tests/browser/summary-sharing-state.test.cjs` прошла: success/known failure/unknown/pending/cancellation/suppression. Это проверка функции выбора заголовка, а не полного браузерного взаимодействия. Финальное ревью остаётся **PENDING** до перечитывания исправлений и результатов runtime/browser проверок.

### Повторное чтение первых исправлений

Подтверждены кодом: expired сохраняет grant и использует отдельное явное продление, clipboard требует active и действительный URL; legacy rotate получает template_key; после lookup404 тот же ключ разрешает идемпотентный POST; показанный список блокируется при известном frozen payload; no-JS ловит ValidationError/ValueError и показывает 422, появились revoke/rotate/update/expiry/cancel/retry; synthetic nginx probe содержит вымышленный UUID; browser continuation GET больше не принимает приглашение, а показывает отдельную CSRF-protected форму; accepted email направляет в independently authenticated reader. Projection unit test самостоятельно выполнен: **1 passed**.

**HIGH — остаточный отзыв доступа (исправление ещё не подтверждено).** В новой `/summary-sharing/received` проверяется accepted invitation/resolved user или первоначальный row.user_id, но убрана текущая `decide_meeting_access`. Generic revoke_share_grant изменяет только grant.status; accepted invitation/row не меняются. Поэтому reader игнорирует последующий отзыв grant, а внутренний recipient продолжает читать после потери исходного can_view. Отдельный срок row.read_expires_at устранил бессрочное чтение, но не отзыв/текущую authority. Нужно связать адресную publication authority с доступным отзывом, одновременно сохранив независимые прежние права и срок каждого нового пакета.

**MEDIUM — AUTO представление.** auto_state возвращает сырые pending/completed; интерфейс не знает pending и не отличает completed unknown/failed. Глобальная paused перекрывает completed. Замечание передано владельцу AUTO. **MEDIUM — режим окна** после ASK оставался email для следующего обычного открытия; основным агентом добавлено одноразовое consume/delete, повторно прочитано.

Reviewer-owned checklist перечитаны вновь: security 5 [x]/0 [ ], ux 5 [x]/0 [ ], infra 5 [x]/0 [ ]; эти 15 отметок подтверждают проектирование. Статус реализации пока **PENDING**, с перечисленным HIGH до окончательного re-read. Runtime RLS, браузер, GRAF Dev, live nginx и production reviewer не запускал.

### Следующий разбор адресной authority и доставки

Исправление `/received` повторно прочитано: internal путь снова проверяет текущий can_view; external row связывается с конкретным grant_id при принятии и требует active status, собственный row.read_expires_at проверяется независимо от срока прежнего grant. Это устраняет непосредственный обход отзыва и срок старого пакета, но обнаружен новый **HIGH replay/rebinding**: после отзыва grant A, создания нового active grant B для того же адресата повторный accept старого accepted invitation попадает в раннюю ветку existing grant и переписывает старый delivery.grant_id на B. Так восстанавливается старый отозванный документ. Replay должен проверять и сохранять ранее записанную authority, не перепривязывать её к новому grant; замечание передано немедленно.

Проверка активного распространителя добавлена в owner_meeting и reserve_recipient: действующий UserIdentity, membership и совпадающая organization, с блокировкой до commit reservation. Test deactivated_sender добавлен основным агентом; результат его выполнения reviewer пока не видел. Отдельно сообщён отсутствие повторной проверки внешнего feature gate в worker перед неначатой передачей; требуется сверка конечного кода.

AUTO теперь преобразует aggregate state в presentation из recipient counts и выводит can_cancel по наличию pending. Осталось согласовать приоритеты смешанных unknown/failed и pending/sending с принятыми заголовками ручной доставки; замечание передано владельцу AUTO. No-JS основной результат ещё требует полного набора заголовков и проверки unknown после aggregate completed; маршрут retry уже есть, кнопка в форме ещё не подтверждена.

### Статус последнего чтения кода

No-JS заголовки, unknown check и known-failed retry теперь присутствуют; expired/replacement формы используют соответствующую отдельную операцию. Подтверждены повторным чтением, не браузерным запуском. Сохранённая row authority требует active grant при внешнем чтении, внутреннее чтение использует актуальное can_view; доставка повторно проверяет активного распространителя. Независимые прежние полномочия не перезаписываются.

**Результат промежуточного разбора реализации: CHANGES REQUIRED**, по последнему чтению остаются: HIGH replay может перепривязать отозванный адресный документ к новому active grant (`access.py:2017–2031`); HIGH текущий запрет external invitations не перепроверяется перед неначатой доставкой (`summary_delivery.py:166`); MEDIUM AUTO presentation выбирает unknown раньше pending/sending/known failure (`summary_autosend.py:1114`). Все переданы владельцам. Требуется отдельный финальный re-read исправленных веток и runtime evidence перед разрешением implementation PASS; этот статус не объявляет выпуск готовым.

Самостоятельные проверки reviewer: unit projection 1 passed и node status selection PASS. Миграции/RLS-предикаты/явные workspace filters, FK-порядок очистки и reservation/revoke fence проверены кодом. Runtime RLS, full delivery tests, браузер/GRAF Dev, фактическая отправка, installed nginx, exact-SHA CI и production evidence не были получены reviewer. Три reviewer-owned requirements checklist перечитаны: **15 [x], 0 [ ]**, requirements PASS; отдельные проверенные code findings не следует скрывать этими отметками.

### Дополнительный read-only проход по root UI/error изменениям

Прочитаны problems.py, reader unavailable renderer/template, no-JS form, актуальный summary-sharing.js и существующий HTMX loading/reset. Обработанная ошибка reader 400/403/404/410/422/429/503 возвращает HTML без текста/метаданных встречи; renderer не получает product analytics config, шаблон и cabinet_html_response задают noindex/no-store/no-referrer. Успешный reader и fallback содержат только добровольный переход на свои встречи.

HTMX opener вставляет новый fragment по явному нажатию, основной host изначально пуст; summary-sharing.js потребляет ASK mode один раз, обработчик старого диалога больше не прикрепляется к opener. Поэтому обычное повторное открытие идёт по ссылке и не накапливает слушатели старых диалогов. ASK только показывает добровольную кнопку и никогда не создаёт пакет. SessionStorage содержит только ключ операции, не email/текст/секрет; frozen payload живёт лишь в памяти диалога. При потере памяти и отсутствии пакета разрешён повтор с тем же ключом; если payload отличается от уже принятого, 409 ведёт на проверку существующего пакета. Исторический пакет не повторяется под новым ключом. Expired copy явно подтверждает продление прежнего адреса и проверяет active/URL перед clipboard.

No-JS результат содержит согласованные success/failed/unknown/process/cancelled заголовки, retry только known-failed, check для unknown после completed, cancellation при pending и revoke/expiry/replacement ссылки. ValidationError и ожидаемые ProblemDetail возвращают понятную HTML ошибку и сохраняют ключ/пространство. Эти выводы основаны на коде, не на реальном браузерном взаимодействии.

**MEDIUM — текст временной недоступности.** problems.py отправляет также 429/503 в один шаблон, который объясняет результат только отключением ссылки, истёкшим сроком или удалением встречи и просит отправителя поделиться заново. При ограничении запросов или сбое хранилища ссылка может быть действующей. Нужен нейтральный временный текст/повтор позже для 429/503 и сохранение Retry-After при наличии; замечание передано основному агенту. Других новых HIGH в этом узком root UI/error проходе не обнаружено.

Три прежних findings исправлены и перечитаны: replay published invitation сначала требует исходный delivery.grant_id active, без перепривязки; external flag проверяется до новой invitation reservation; AUTO presentation учитывает pending/sending раньше финальных отказов/unknown. Проверки новых регрессий присутствуют в test_summary_delivery.py. Самостоятельный запуск pure AUTO presentation tests: **9 passed, 21 deselected**.

**MEDIUM — завершение при истёкшем deadline.** Новые recover_finished_dispatches и начальный reconcile при deadline отменяют только DispatchIntent. Неначатые recipient.pending и batch.pending остаются и дают бесконечное «Отправляем…»/poll после 24h outage, хотя workflow уже не запускается. Требуется финализировать неначатые строки/агрегат под тем же meeting fence, сохраняя accepted/unknown/sending. Замечание передано владельцу backend/AUTO и основному агенту. Окончательный статус ожидает стабильного кода и evidence, предыдущий CHANGES REQUIRED остаётся промежуточной историей, а не утверждением о коде после будущих исправлений.

Оба последних MEDIUM исправлены и перечитаны: temporary=429/503 выбирает временный текст «Попробуйте открыть эту страницу немного позже», problem.headers сохраняются; finalize_expired_batches вызывается перед reconciliation, блокирует meeting→batch→pending recipients, отменяет только pending и refreshes aggregate. Accepted/unknown/sending не изменяются; параметризованный deadline test для created/started dispatch присутствует. По последнему source re-read открытых HIGH/MEDIUM из этого отчёта **0**, окончательный implementation verdict ещё ожидает сообщения о стабильном коде и runtime evidence. Это не browser/production validation.

## Дополнительный независимый разбор включения общих ссылок

Read-only source + production metadata, 2026-10-05 22:20 UTC. Работающий rec-api: один экземпляр; PUBLIC_LINKS_ENABLED=false, PUBLIC_LINKS_ABUSE_GATE_APPROVED=false, SHARE_EXTERNAL_INVITATIONS_ENABLED=true. Uvicorn --no-access-log включён. Метаданные установленного nginx: маршрутов public-shares/optout нет, access_log off отсутствует, limit_req присутствует только в отдельном webhook-контуре. Сам nginx/main содержит stream/ssl_preread, но не proxy_protocol или transparent client forwarding. Никакие настройки production не менялись. Один вымышленный недействующий запрос public-shares дал HTTP 404 с private,no-store / no-referrer / noindex,nofollow,noarchive.

Конкретная работа до включения флага:

1. **Вход nginx.** `infra/nginx/rec.2brain.pro.conf:6,25,48` журналирует обычный request URI и проксирует public-shares через общий location без ограничения чтения. Требуются отдельные ограничения для `/api/v1/cabinet/public-shares/` и фактического нового optout prefix; `access_log off` либо явный формат без request/URI/args/referrer, также на HTTP redirect. Учесть nginx error_log: лимитер/upstream ошибки могут включить полный request даже с access_log off. Для узких секретных locations допустимо отключить error_log и оставить обезличенный app-журнал. Edge-ответы 429/502/413/redirect должны получать no-store/no-referrer/noindex через add_header always; app middleware не покрывает ответ, созданный самим nginx.
2. **Самый простой общий лимитер.** В проекте уже есть стандартный `limit_req_zone`/`limit_req` — `infra/nginx/graf-billing-webhook-limit.conf:2` и `rec.2brain.pro.conf:96`. Использовать отдельную общую зону для чтения/optout, ограниченный burst и 429 до API; новый сервис/Redis не нужен. Важная топология: внешний 443 — stream SNI-router → loopback10444 (`docs/runbooks/billing-launch.md:99–113`, подтверждено текущим main). `$binary_remote_addr` здесь является адресом локального hop; не заявлять такой лимитер как per-visitor. Проще честный общий бюджет hostname/server для этих дешёвых summary маршрутов. Не доверять X-Forwarded-For от пользователя и не менять общий SNI-router ради этой функции.
3. **App журнал/ответы.** `observability/logging.py:13–16,65–82` уже маскирует public-shares path и задаёт нужные заголовки после нормального ответа, включая handled 404/422. Новый optout prefix пока не входит в этот regex: добавить после выбора реального маршрута. Ошибки вне middleware normal return (unhandled 500) требуют отдельного покрывающего заголовки ASGI/edge пути. Existing actor/device limiter `cabinet/access.py:208` требует реального пользователя/device и ограничивает операции владельца; он не защищает анонимное чтение.
4. **Флаги Compose.** `infra/env/rec.production.env.example:241–242` задаёт оба public flags=false. В `infra/docker-compose.yml` у rec-api отсутствуют интерполируемые PUBLIC_LINKS_ENABLED/ABUSE_GATE_APPROVED (есть external invitations:49). Поэтому установка только ключей в root .env не передаст их контейнеру. Нужны явные overrides с default false; enabled/approved выставлять лишь после installed nginx validation. `config.py:615–624` проверяет только наличие base URL/approved bool, не доказывает лимитер/редакцию журналов.
5. **Установка edge отдельно.** `cd-remote.sh`/`cd-remote-runtime.sh` не устанавливают nginx. Пример backup→nginx -t→reload→probe→rollback есть в `infra/scripts/install-billing-webhook-edge.sh`, но запускать его для summary не следует: он трогает секрет/проводит billing probes и перезаписывает весь сайт. Нужна узкая установка summary-zone + актуального site с сохранением существующего billing listener, конфигурационная проверка и вымышленная header/rate/log probe до включения PUBLIC flags.

Серверный выпуск и macOS: `scripts/release.sh:21,39,49` имеет `--no-app`; без него macOS сборка/публикация включена по умолчанию. Для этого среза использовать server-only --no-app. `infra/docker-compose.yml:184` монтирует runtime/public-downloads read-only; `cd-remote-runtime.sh:255–310` сохраняет существующий graf.pkg (`unchanged`), а :313–411 проверяет его HTTP/checksum и доступность feed/archive. Appcast сравнивается по структуре/длине архива, не доказывает неизменность feed/ZIP: до и после server deploy записать SHA256 PKG/appcast/current ZIP (только публичные артефакты), не вызывать publish-appcast. Все обычные exact-SHA/train/full/CD ворота остаются обязательны.

Эти наблюдения относятся к предстоящей реализации/включению; requirements checklist остаётся PASS 15/0 и не считается runtime acceptance. Reviewer изменил только этот отчёт, не код/проект/GitHub/production.
