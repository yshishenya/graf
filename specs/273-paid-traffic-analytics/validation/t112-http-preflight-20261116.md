# T112 — независимый вход перед HTTP, выдачей и обновлением proof

Дата: 16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Основа: `9f37adc897217ea2416cf3ebeccb4373efbe1c70`; при входе рабочая копия чистая.
Полоса: существующая `high-risk-product` F273/T112. Следующего HTTP кода ещё нет.
Разрешённые изменения проверяющего: только настоящий новый отчёт; код,
требования, задачи, Git/GitHub, runtime и списки не менялись. Тесты не запускались.

## Решение

**PASS качества требований: 124 отмечено / 0 не отмечено. PASS уточнённого
проекта первого, внешнего ASGI шага; P1=0, P2=0 в его узкой области.**
Последнее решение основного агента зафиксировано в
`t112-http-boundary-design-20261116.md`: существующий внешний ingress guard,
сохранённое штатное auth renewal, ограниченная буферизация ответа и один
абсолютный срок. Оно заменяет промежуточное предложение с подавлением renewal
в двух APIRoute. Ниже сохранена история находки H1 и добавлены актуальные
условия отмены/DB cleanup. Полный HTTP/issuance/renewal ещё не принят; сначала
допустимо реализовать и проверить только внешнюю границу без заявления
о доказанной очистке реальной БД при всех отказах.
Независимое implementation review будет отдельным шагом. Настоящий T113
по-прежнему закрыт; этот отчёт не разрешает рабочий сбор или публикацию.

| Действующий основной список | Отмечено | Не отмечено |
| --- | ---: | ---: |
| requirements | 16 | 0 |
| security | 27 | 0 |
| privacy-measurement | 52 | 0 |
| infra | 29 | 0 |
| Всего | **124** | **0** |

Все действующие вопросы перечитаны и оценены применительно к этому шагу.
Отметки относятся к достаточности требований, а не наличию HTTP реализации.
Четыре вспомогательных public-* списка также просмотрены: 21/0, прежние T106
public/consent/SDK boundaries. Они не становятся частью T112 implementation
приёмки; этот проект не меняет их scope, egress, индивидуальный отзыв или SDK.
Нет оснований менять reviewer-owned отметки.

## H1 — post-response renewal: найдено и уточнено до кода

**Первоначальная проектная находка P2, устранена уточнением ниже:** wrapper нового APIRoute может охватить FastAPI
зависимости, чтение тела и route/service, но не всё существующее окружение.
`auth/session_renewal.py:session_renewal_middleware` выполняет работу
**после** `await call_next(request)`: открывает ещё одну DB-сессию, вызывает
`record_session_activity` и commit. `auth/dependencies.py` успешно разобранной
session оставляет `request.state.auth_session_renewal`, а новые ответы
accepted/renewed/unavailable с HTTP 200 проходят условие renewal. Поэтому
две секунды APIRoute могут закончиться, после чего middleware ещё ждёт pool,
locks и commit. У него собственного общего дедлайна нет.

Кроме того, сам `_principal_from_session_token` открывает сессию и делает
штатные auth commits до входа в новый service. Обёртка лишь тела handler не
охватывает даже эту часть. Нельзя считать нынешние внутренние 2s service
или 1.5s account owner общим временем запроса и нельзя каждому слою дать
свои новые независимые две секунды.

Принятое уточнение основного агента: только два новых APIRoute охватывают
штатный handler со всеми зависимостями и их завершением бюджетом 1.5s,
оставляя резерв до общего 2s. В безусловном `finally` этих маршрутов
`request.state.auth_session_renewal=None` убирает подготовленную попытку
post-response activity writer. В существующем middleware после `call_next`
это приводит к немедленному возврату без новой DB-сессии и commit. Другие
маршруты не затронуты; обычные product GET/POST сохраняют прежнее renewal.
Это явная узкая семантика новых аналитических POST, а не общий обход auth.
Текущая session всё равно обязана пройти штатные dependencies и свежие locks.

Условия этого проекта: `finally` выполняется также при auth/CSRF exception,
timeout и cancellation, не только на успешном return. В wrapper нет фоновой
задачи, которую cleanup продолжает после выхода. Нужно проверить реальный
FastAPI dependency exit stack установленной версии: его закрытие не должно
оказаться вне wrapper. Повторное middleware чтение renewal после wrapper
обязательно видит None. Остальные middleware в прочитанном main окружении
делают logging/context reset, дополнительного DB writer не обнаружено;
изменение их поведения/порядка потребует пересмотра этого вывода.

Альтернатива остаётся допустимой: один scoped внешний ASGI guard с общим
дедлайном, включая post-response middleware, если узкое подавление renewal
не используется. Нельзя принять исходный APIRoute-only timer с сохраняющимся
post-response SQL writer. Сам резерв 0.5s не доказывает завершение shielded
cleanup; это обязательная причинная приёмка следующего кода.
Внутренним слоям передаётся оставшееся время с резервом на отмену и закрытие
DB; ограничения lock<=250ms и statement<=500ms также не должны превышать
остаток. Неопределённый commit не повторяется, accepted не отправляется
раньше разрешения общей транзакции. При отмене нельзя оставлять фоновый
request/DB-task или отдавать соединение в pool с продолжающейся транзакцией.
Один `asyncio.timeout(2)` не доказывает ограниченную shielded cleanup;
нужны причинные проверки ниже. Ошибка cleanup остаётся закрытым результатом,
а не основанием ослабить учёт времени.

## Допустимая минимальная структура

1. Один новый `cabinet/web_routes/result_views.py` регистрирует оба POST alias
   с одним handler и штатными Principal/WebTenant/WebCSRF. Роутер подключается
   в существующем `cabinet/web.py`; нет альтернативного auth, service writer
   или отдельной ledger транзакции. UUID пути и поверхность определяет сервер.
2. До выполнения зависимостей, способных читать body, узкая обёртка отклоняет
   non-JSON. Это нужно до `require_web_csrf`, который для URL-encoded формы
   без header вызывает `request.form()`. Нельзя ставить проверку только
   внутри handler либо добавлять Form/Pydantic body, прочитанный до лимита.
   Ранний форматный отказ не является освобождением принятого JSON от CSRF.
3. Принимать только ограниченный stream собственного тела, суммируя реальные
   bytes до JSON parsing: <=2048, независимо от Content-Length. Рано отвергать
   заведомо большой Content-Length; ложная/отсутствующая длина и chunked не
   обходят реальный лимит. Slow receive прерывается тем же внешним дедлайном.
4. JSON — ровно объект с единственным `proof`; строка ASCII <=1536 bytes,
   без неизвестных полей, client identity/surface/source и приватных refs.
   Отвергать неправильный тип, пустой/повреждённый JSON и неоднозначные
   duplicate keys, без эха входа и exception text. Общая функция проверки
   подписи остаётся единственной криптографической проверкой.
5. Выдача, renewal и пара проходят общий service owner и те же fresh
   account/session/membership/device/Meeting/source/gate fences. Частные
   helpers не коммитят. Для GET/renewal нет вызова milestone primitive,
   INSERT ledger, provider transport или новой очереди. Commit read-only
   транзакции общего owner сам по себе не является ledger записью.
6. Proof или accepted/renewed возвращаются только после успешного выхода
   из общего owner и его последнего guard/commit. Отложенная ошибка не должна
   оставлять уже сформированный proof в render context. Closed/missing T113
   возвращает отсутствие proof/unavailable при неизменной работе просмотра.

## GET — сравнение с тем, что действительно будет показано

Подключаются только owner detail callers browser/desktop, обе полная HTML
страница и HTMX fragment. Shared/public и restricted grant не получают proof.
Существующий review для render остаётся основой отображения; свежий повтор
под Meeting fence не должен молча заменить его новой версией.

Внутри общего owner вычисляются bindings именно переданного render review
и свежего locked review; proof выдаётся только при точном совпадении
соответствующего блока, его источника/result/outcome/version/digest/deletion
и session binding. Совпадения meeting ID либо одного текста недостаточно.
Выбор должен совпадать с GET: browser использует summary_format и
source_result_id, desktop — только свой текущий summary_format. Повторные
query keys, последнее пустое значение и невалидный UUID обрабатываются
одинаково со штатным GET; новый helper не придумывает альтернативный default.

У закреплённых итогов собственная версия/result/outcome, не обязательно
текущий transcript. Пустота/title/placeholder/error не получают атрибут.
Разрешённый текст без аудио/права экспорта остаётся подходящим. Выдача proof
не означает показ или создание события. Сам proof нужен только в невидимом
атрибуте соответствующего блока, не в poll URL, link, cookie, ledger,
параметрах аналитического провайдера, логах, tracing или общих replay данных.

Отсутствие/ошибка proof enrichment не превращается в ошибку GET/HTMX. Его
собственное ожидание ограничено и не наследует незавершённый service task;
новый analytics запрос не удерживает лишнюю product DB-сессию, мешающую ему
получить соединение из небольшого pool. Существующий GET с прочими нужными
product storage/profile чтениями не объявляется целиком двухсекундным POST.

## POST — валидный, истёкший и сменившийся блок

После свежих locks обычная HMAC проверка сравнивает proof с exact binding.
`valid` ведёт только в общий атомарный admission двух прежних событий;
`expired` может обновить proof только при том же полном совпадении и свежих
условиях, не создавая ни одной вехи или provider попытки. Неверная подпись,
будущее время, другая session/device, source/version/slot/text/deletion или
недоступность — unavailable, без renewal по ID, извлечённым из недоверенного
payload. Смена версии требует нового обычного render.

Общий owner сохраняет guard expiry и T113 непосредственно перед каждой
INSERT и commit. Renewal/выдача тоже завершаются свежим guard. Нельзя
проверить expired отдельно, закрыть транзакцию и во второй самостоятельно
открытой транзакции обновить proof или принять пару. Повтор после unknown
commit допускается только при следующем настоящем клиентском переходе;
внутри запроса SQL/application retry не появляется.

Только точные ответы accepted/renewed/unavailable, private/no-store во всех
собственных ответах, включая ранние format/size/timeout отказы. Штатные
auth/CSRF ошибки сохраняют свой статус и смысл. Редирект, ошибка и неизвестная
JSON форма не превращаются в accepted. Серверная реализация этих входов пока
не доказывает клиентскую видимость, frame/native check либо ограничение
одним renewal на переход; это следующий browser/Swift срез.

## Обязательные причинные проверки следующей реализации

- Оба реальных alias через собранное FastAPI/ASGI приложение: cookie+CSRF и
  штатные auth headers, нет auth/неверный CSRF/чужой owner/admin/shared,
  closed настоящий T113 и открытый только изолированный внутренний context.
- Non-JSON/urlencoded/multipart с ловушкой `request.form`: ранний отказ до
  form/body allocation; допустимый JSON всё равно проходит реальный CSRF.
- 2048/2049 body bytes, 1536/1537 ASCII proof bytes, non-ASCII, лишнее поле,
  array/null/number/дубликат ключа, ложная/отсутствующая Content-Length,
  chunked, slow stream и disconnect. Нет входа в ledger/transport на отказах.
- GET/HTMX обоих callers: равный render/fresh binding даёт proof при нуле
  ledger writes; mutation между product read и issuance, pinned summary,
  source/summary selectors и empty блок не получают ошибочный proof.
- Valid proof даёт одну пару/accepted после commit; matching expired даёт
  renewed с новым valid proof при 0 INSERT/0 provider; expired changed,
  tampered, future и чужая session не обновляются. Повтор пары идемпотентен.
- Настоящий малый pool: ожидание подключения на auth и service отдельно,
  удержанный lock, медленный query/commit/rollback/close, отмена и сбой cleanup.
  Измерять end-to-end время, открытые sessions/tasks и pool checkout после
  завершения; внутренняя заглушка `admit_result_view=False` этого не доказывает.
- Отдельно проверить штатный `session_renewal_middleware` после handler:
  на двух новых aliases writer не запускается даже при prepared renewal
  state; на обычном product маршруте запускается как раньше. Это RED для H1.
  Исключение/timeout
  после возможного commit не вызывает автоматического повторного INSERT.
- Большая реальная проекция: синхронные digest/JSON/render операции не
  прерываются одним asyncio timer. Нужен консервативный закрытый отказ по
  оставшемуся абсолютному дедлайну до proof/INSERT/commit и проверка общего
  времени; нельзя обрезать текст и выдать digest другой проекции.
- Inspect сохранённых payload, логов и fake transport: нет proof/частных
  refs/текста/IP/URL, нет egress; прежние 190 тестов — регрессия этого шага,
  а не замена новых HTTP/budget проверок.

## Матрица применимости списков

Каждая строка объединяет уже перечитанные отдельные вопросы, не заменяет их
новой отметкой. Основа качества неизменна, дополнительный HTTP договор её
не ослабляет.

| Вопросы | Основание для сохранения отметок в этом шаге |
| --- | --- |
| requirements, все16 | spec FR-021/025, SC-006/007, Session16.11; plan/tasks T112; result-visibility §§1–7 и quickstart дают смысл, границы, зависимости и положительные/отказные критерии. H1 уточнён до кода; это исполнение уже определённого ограничения. |
| security001–004, privacy001–007/016–021 | Только прежние metadata вех, transient proof и текущие server-memory projection; §§2/3/5/6 запрещают перенос содержимого/refs в durable/external аналитику. |
| security005–009/016–020, privacy008–015/022–030/043–045 | Получатели/основание/отзыв и unknown attribution прежние; client JSON не становится trusted trigger; новый маршрут не открывает optional сбор. |
| security010–015/021–025, privacy031–042 | Ledger lifecycle/доходящий отзыв/операторский доступ и ресурсы по прежнему T113 договору; выдача proof не создаёт новую категорию хранения или обход receipts. |
| security026–027, infra026–029 | Прокси, IP writer и срок T098 не меняются; encoded path/неожиданный alias не получают нового разрешения. |
| privacy046 | Новый приём и started_at — только source/audit/T113, без выдуманного capture/external статуса. |
| privacy047 | Proof одной exact render проекции, renewal без счёта; реальный client/native показ остаётся обязательным отдельным шагом. |
| privacy048 | Fresh auth/owner/source fences перед issue/renew/admission; оба маршрута сохраняют CSRF/tenant. |
| privacy049 | Capture false/absent/true и каталог/отчётные фильтры не меняются. |
| privacy050 | Одна account-пара, прежний payload, partial existing/unknown commit/replay правила в §§5/6. |
| privacy051 | Общий owner/закрытый T113, runtime не включается; Уточнение H1 конкретизирует исполнение уже заданного бюджета. |
| privacy052 | Quickstart HTTP/negative/concurrency/failure и приведённые причинные условия; tests ещё не исполнены. |
| infra001–025 | Копии/restore/ресурсные пределы и деградация сохраняются; неизвестные receipts не заменяются успешным GET или локальными тестами. |

## Оригиналы, происхождение и границы чтения

Продолжение того же reviewer-диалога и той же области. Прежнее собственное
полное чтение отражено в t112-requirements-review, server/fresh preflight и
fresh-verifier-review. После сжатия восстановлены применимые оригиналы:
result-visibility полностью; spec Session16.11 и FR-021/025/SC-006/007;
plan §продолжение T112/T113 и §T112; tasks T112/T113 с уточнением16.11;
quickstart весь профиль T112; research §T112; data-model transient proof;
activation-milestones триггеры/доверенная сторона/одна транзакция и T113 fences;
конституция II/III/IV/VI/VII, PRD meeting detail/privacy и product-gates;
README/document-reading/spec-kit-flow. Новые зависимости фактически прочитаны:
auth principal/CSRF/tenant, session renewal, support sessions, main middleware,
existing ingress guard, оба detail callers, proof helpers, request logging.

Все13 прежних requirement/checklist/analyze входов побайтно совпали с
`503805cb6188f942adb159ea2bab8560969b7b0e`. Result-visibility совпал с
последним принятым fresh preflight `ee1005…270d8`; с более старым503805cb он
не совпадает и не выдан за неизменный относительно той версии. Четыре
основных документа и document-reading совпали с прежними собственными
записями. Карта ниже привязывает решение к конкретным текущим байтам.

## Ограничение большой проекции — допустимая конкретизация

Предложенный DB preflight cardinality/size допустим как закрытый отказ
аналитики, не ограничение отображаемого продукта. Выполнять его под тем же
Meeting fence до загрузки большого review. Считать на стороне БД и возвращать
только ограниченные числовые агрегаты; нельзя сначала скачать текст/JSON в
Python, чтобы затем узнать его размер. Ограничения задаются явными
консервативными константами с тестами границы, без новой настройки, открывающей
T113. Неизвестный/слишком большой случай не получает proof или события.

Guard должен покрывать все потенциально загружаемые коллекции и крупные
scalar/JSON поля общего reader и binding path, а не только число transcript
segments: diarization, выбранные и исторические result/outcome/slot данные,
audit/source inputs, участники/activity/прочие prefetched коллекции, если
они загружаются текущим helper. Упрощённый reader вместо общей проекции не
разрешён. DB aggregate сам имеет statement/remaining deadline; большой
размер/timeout не превращается в усечённый digest. После синхронных операций
снова проверяется абсолютный остаток до выдачи/INSERT/commit. Нужны как
большое число строк, так и одна большая текстовая/JSON строка, с доказанным
ранним отказом до materialization review.

## Контрольные суммы входов

Пути относительно корня рабочей копии.

| Путь | SHA-256 |
| --- | --- |
| `specs/273-paid-traffic-analytics/spec.md` | `a7f23904625df9b06aed1e09c05f2ffa75ec3e5ec9ac0eda0531cd88c949c645` |
| `specs/273-paid-traffic-analytics/plan.md` | `5207a988f666c47f65203718a1212cf352312009f1c3804163abd093318a8b3c` |
| `specs/273-paid-traffic-analytics/tasks.md` | `3870e4d091557e0c40dd5500aa8fb5932b933cfe877e684c930d7f7e4f93a7d5` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `4f2488aa98a3fba478eed042304279f408dc2530bd3f2b0449cedabaf39dd074` |
| `specs/273-paid-traffic-analytics/research.md` | `64caef3d9a78f0021c2b37ca86e0f388724bf117e899bd044f4ca557a1ba094f` |
| `specs/273-paid-traffic-analytics/data-model.md` | `478c18546d1240c4a1c15c5b07e76f7aeb551082273b75bc1fbf4cdd8d1ae8ab` |
| `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` | `4835c0c6672a464366c9657d9285b28429ec2ed4d4e234c0c4897a65ed5027c4` |
| `specs/273-paid-traffic-analytics/contracts/result-visibility.md` | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| `specs/273-paid-traffic-analytics/checklists/requirements.md` | `d771fe1f54e69b297346bfde3ea52f82d484fc241f13576efc34e09feffe80f4` |
| `specs/273-paid-traffic-analytics/checklists/security.md` | `dbd65a5afb7829789d8b4aa48f8c0b32243cc039681d15a5b851b381ca3b8b92` |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | `5b4164d0ce3e11ea6bca8419f4f0d6f6d33de163e3745cbb4cbfccd90ce07840` |
| `specs/273-paid-traffic-analytics/checklists/infra.md` | `a3319849bcd8be93803415495b42b4e50476cf1e08eb57ef898d34293f2be0cf` |
| `specs/273-paid-traffic-analytics/validation/t112-requirements-review-20261116.md` | `bb7c8592b302d6cb9ef21e0ecfc1045778afd39f07efed29787091ae3aaf91a5` |
| `specs/273-paid-traffic-analytics/validation/t112-analyze-20261116.md` | `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `66ba7daa70519c8848a6daea51cd593220fccf75d4b5ea3a4a154e5ae139c3ca` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/agent-guidance/document-reading.md` | `5c3ab1f885dbf324edab70c0f4b7a5451208b3d7307c1ca7a5afdd7af0c8eb22` |
| `apps/server/src/twobrain_rec_server/auth/dependencies.py` | `559bcc1c46cdf49cd283d8a199e089fc7047401b669c0ab17ae9b6d98c94d311` |
| `apps/server/src/twobrain_rec_server/auth/session_renewal.py` | `0fea864d2aeb6028666e9ba8befe5c351871f5fd095328d7bc8e3b36beb81fd1` |
| `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `decbf06e7f3e9e39bbd45b58fb8a111285ef96bfb04859857d9e39ff2ca2817a` |
| `apps/server/src/twobrain_rec_server/main.py` | `88c75ce3f34d69ebd1e3ffd6f096d3bfe40ec4de22abab383beec24946509a10` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/support.py` | `f4c5c6143372ec6aa8d5bd4f71225578e2751839e6af5b4129011f9ec46dff27` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py` | `1969ad5c2402bd9a9130db7d5fab228b5156ef2a1e030138da2257be8461e9ba` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/desktop.py` | `e85ada18152f8211f8a9a21e467e643aa8ef20aaef078459ad2b7142947a1959` |
| `apps/server/src/twobrain_rec_server/cabinet/result_visibility.py` | `b59aa36240282748ed88696e1cfee04710302364ce9df9f2b5fc3315fdedb5e7` |
| `apps/server/src/twobrain_rec_server/cabinet/queries.py` | `cf0e7b622c60e53513df78140ddf2d2ab74937a55a15ce7c719de56fa14f50da` |
| `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` | `b718fd0c23c08c1b51cfe2062254c1433b026f4bc68c1f37a2b79b2c5f31095a` |

## Окончательное уточнение H1: внешний ASGI foundation

Прочитан новый `validation/t112-http-boundary-design-20261116.md` целиком.
Он является последним проектным решением. **Промежуточный вариант выше с
`request.state.auth_session_renewal=None` больше не выбран и не должен
внедряться.** Штатный renewal остаётся внутри внешней границы. APIRoute
по-прежнему может быть узким parser/router, но не единственным таймером.

Первый foundation срез можно реализовать и проверить до полной DB интеграции:
он не открывает T113, не выдаёт proof и не создаёт ledger. Буферизация должна
охватывать весь внутренний ASGI вызов, а не только response.start: только
после его окончательного возврата и проверки срока разрешён один внешний
ответ. Размер буфера и число сообщений ограничены; неожиданное streaming/
large/незаконченное сообщение закрывает ветвь, а не наращивает память. Нельзя
буферизовать произвольные остальные product routes. Заголовки штатного auth
response, в том числе Set-Cookie, сохраняются в успешном допустимом ответе.

Перед чтением body проверять точный scope/method/path и media type. Бюджет
ставится перед первым receive; body полностью разбирается один раз и лишь
принятые ограниченные bytes повторно передаются внутреннему приложению.
UUID parser guard и actual route должны быть согласованы, чтобы encoded/
невалидный/неожиданный путь не обходил бюджет либо не захватывал соседний
маршрут. Отказы form/auth/CSRF и клиенты с неправильным телом причинно
разделяются тестами. При disconnect не надо ещё раз посылать HTTP ответ
закрытому клиенту, но отмена и cleanup всё равно принадлежат текущему запросу.

### Конкретные условия отмены и cleanup до полной HTTP интеграции

Существующий проект не требует новой фабрики сессий или альтернативной auth.
Нужно использовать текущие `app.state.db_sessionmaker` и штатные зависимости.
Но один внешний timer не даёт доказательства, что все созданные ими ресурсы
закрыты в остаток 0.5s. Независимо прочитаны фактические библиотеки локальной
проверки: SQLAlchemy2.0.51/asyncpg0.31.0/FastAPI0.138.1/Starlette1.3.1;
версии совпали с `apps/server/uv.lock`.

1. **Один deadline и владелец задач.** Рабочая часть прекращается не позже
   start+1.5s, всё завершение — до start+2s. Все waits используют остаток,
   а не новый timeout. Внутренняя ASGI задача при timeout/disconnect отменяется
   и присоединяется; нельзя вернуть unavailable, оставив её в background.
   Обычный `wait_for` может ждать завершения отмены дольше своего timeout;
   сам факт TimeoutError не является измерением законченного cleanup.
2. **Видимые ресурсы всех штатных фаз.** Auth lookup, service и post-response
   activity renewal последовательно могут открывать разные сессии. Проверка
   только `context.db` service не покрывает auth или middleware. Нужен узкий
   request-scoped учёт владельца уже созданных sessions/connections и cleanup
   задач либо эквивалентный способ доказать их завершение, используя прежнюю
   фабрику. Нельзя собирать/закрывать чужие сессии, делать engine.dispose или
   менять общую фабрику ради этого маршрута. Если для реальной очистки ещё
   нет такого способа, foundation PASS нельзя объявлять полным HTTP PASS.
3. **Shielded close не исчезает от отмены caller.** В установленном
   `AsyncSession.__aexit__` создаётся отдельная `self.close()` task и ожидается
   через `asyncio.shield`. Отмена ASGI task может оставить close task живой.
   Нужен проверяемый владелец её завершения, а не допущение, что выход из
   `async with sessionmaker()` уже всё закончил. Если добавляется узкий helper
   владения закрытием, он использует текущую sessionmaker и не подменяет
   Principal/CSRF/tenant проверку; обычные маршруты сохраняют поведение.
4. **Invalidate не равно мгновенный force-close.** Публичный
   `AsyncSession.invalidate()` существует, но штатный asyncpg adapter при
   invalidation в greenlet сначала ждёт shielded graceful close; его собственный
   `asyncpg.close(timeout=2)` уже длиннее всего резерва. Поэтому нельзя назвать
   `await db.invalidate()` без оставшегося deadline гарантией 0.5s. Для
   подтверждённо принадлежащего запросу соединения допустим ограниченный
   graceful cleanup и, при необходимости, документированный публичный
   driver `Connection.terminate()` без ожидания данных, затем корректное
   SQLAlchemy invalidation/освобождение и присоединение cleanup task.
   Не использовать private `_terminate_force_close`, ручную подмену pool
   internals или новый raw SQL login. Нельзя получать новое соединение из pool
   в момент timeout лишь для того, чтобы вызвать invalidate.
5. **Точное владение и гонка возврата.** Принудительно завершать можно только
   исходное соединение запроса, пока оно ещё принадлежит ему. После checkin
   тот же pooled connection может обслуживать другой запрос. Ссылки без
   актуальной принадлежности/поколения не разрешают terminate; общий engine
   и соседние запросы не должны пострадать. Штатный pool/SQLAlchemy bookkeeping
   должен увидеть invalidation, а испорченное соединение не попасть в reuse.
6. **Исход commit остаётся неизвестным.** Cancel/terminate после начала commit
   не доказывает rollback: сервер уже мог сохранить пару. Не возвращать
   accepted и не делать retry, если commit outcome не установлен. Следующая
   настоящая видимость разрешает прежние authoritative account keys. Проверять
   0 либо2 новые строки в ambiguous случае, неизменность старой пары и
   отсутствие частичной новой пары; результат не подгоняется к обязательному0.
7. **Наблюдение БД после завершения.** В изолированной PostgreSQL нужны реальные
   случаи pool wait до получения соединения, SQL cancellation, commit и
   rollback/close. После ответа/завершения запроса независимый observer
   проверяет отсутствие относящейся к нему активной/idle-in-transaction работы,
   захваченных locks, checked-out connection и cleanup task. Новый обычный
   product запрос успешно использует pool. Естественное серверное разрешение
   уже начатого ambiguous commit не объявляется подтверждённым rollback;
   при неразрешённой транзакции DB/fence cleanup приёмка ещё закрыта.
8. **Не путать две причины ограничения.** SQL lock/statement limits и 1.5s
   рабочий таймер покрывают разные ожидания. Pool connect/pre-ping/auth renewal
   идут до service SET LOCAL; они требуют внешнего deadline. Большие
   синхронные JSON/digest операции ограничиваются отдельным preflight и
   проверкой времени; отмена async SQL не решает CPU materialization.

Это конкретные условия последующего DB шага, не поручение строить новую
систему сессий или менять auth поток. Foundation может сначала доказать
ASGI/body/buffer/cancellation на ограниченном fake app и на существующем
middleware с причинной задержкой. Быстрый положительный case затем обязан
проверить настоящий renewal, а реальные pool/driver/transaction сценарии
обязательны до полного HTTP/issuance PASS.

### Прочитанные реализации библиотек

Пути локальной установленной среды относительно
`/Users/yshishenya/Documents/crisp/apps/server/.venv/lib/python3.13/site-packages/`:
`sqlalchemy/ext/asyncio/session.py` (__aexit__, close, invalidate),
`sqlalchemy/connectors/asyncio.py` (AsyncAdapt_terminate),
`sqlalchemy/dialects/postgresql/asyncpg.py` (rollback/commit/terminate),
`sqlalchemy/engine/base.py` (exit exception/disconnect),
`asyncpg/connection.py` (close/terminate/cleanup). Библиотеки не менялись;
поведение установленных исходников не заменяет причинный PostgreSQL тест.

| Дополнительный вход | SHA-256 |
| --- | --- |
| `specs/273-paid-traffic-analytics/validation/t112-http-boundary-design-20261116.md` | `7a9a912c424676c2bf88dcdebe968166c3e0c8fbfaf94b8216684d32d21f856f` |
| `apps/server/uv.lock` | `c7bba4a373661487b1c13ac931f3d2c1ad0ade7c28b12dd1b8c21316b40ca52d` |
| `sqlalchemy/ext/asyncio/session.py` | `875e89b14110e7b9bd435c86bf26716a1e38031638e80179bc044f1292c43e7e` |
| `sqlalchemy/connectors/asyncio.py` | `44d173217bfaf38174149b84d396bed502bf769a98ad41f022269408edf69f9b` |
| `sqlalchemy/dialects/postgresql/asyncpg.py` | `c5784dd0e262892cbd0ba6cae2daf69b3152037152ada95619a9fb10f6f12bda` |
| `sqlalchemy/engine/base.py` | `53f38e544004d329ac38e243104bf4bbbaf7d0f0cecabd112b1923b78dde5614` |
| `asyncpg/connection.py` | `e9abd5c153bc70cfadb61215f11140e90741c2fed5929e574b6548ef8092b48c` |

## Независимый preflight владения ресурсами после PostgreSQL RED

Область этого дополнения: только предложенные request ContextVar, публичные
Pool events и завершение задач после отмены. Последнее поручение основного
агента — дополнить именно этот отчёт; отдельный resources report не создавался.
Прочитан целиком новый раздел «RED настоящей БД» в boundary-design.
Чужие изменения guard/tests не менялись и здесь не проверяются как реализация.
13 requirements/checklist/analyze входов и договор остаются прежними по
предыдущему чтению; основные reviewer-owned отметки сохраняются **124/0**.

**PASS минимального проекта для точного владения уже выданными соединениями,
P1=0/P2=0 в этом узком подшаге, при выполнении условий ниже.** Это допуск к
исправлению наблюдённого pg_sleep cleanup, а не полный PASS всех стадий
подключения/БД или двухсекундного HTTP пути. Сам RED 56PASS/1FAIL и ~1.55s
сообщён основным агентом в проекте; журнал этого нового запуска независимым
проверяющим не запускался и не выдаётся за заново подтверждённый GREEN.

### Почему направление допустимо

Публичные checkout/checkin/invalidate события дают конкретный pool entry и
DBAPI connection, а public `driver_connection` — точный asyncpg connection.
В установленном SQLAlchemy hard invalidate event вызывается **до** штатного
`__close(terminate=True)`. Поэтому синхронный `driver.terminate()` внутри
ограниченного invalidate callback своего lease может закрыть underlying
transport до создания долгого graceful-close ожидания adapter. Это сохраняет
штатное SQLAlchemy invalidation/bookkeeping, не требует новой sessionmaker,
private adapter API, engine.dispose или альтернативной авторизации.

У `Pool.checkin` событие вызывается до `_return_conn`, поэтому сброс lease
в нём предотвращает использование прежним владельцем уже переиспользуемого
соединения. Request ContextVar наследуется обычными дочерними asyncio Tasks,
включая `AsyncSession.__aexit__` shielded close; публичный Task.get_context()
позволяет их связать по identity уникального owner объекта, а не по имени
корутины/задачи. Версии Python/библиотек и поддержка API проверяются также
в фактическом server test/deploy окружении, не только на Mac.

### Обязательные условия реализации

1. Owner — новый непрозрачный объект для каждого запроса, установленный только
   на точных двух result-viewed POST до body/app и сброшенный token.reset
   в finally. Он не содержит IP, proof, account/token/meeting refs. На обычных
   запросах events ничего не меняют. Listeners регистрируются один раз на
   существующем нужном engine/pool; не накапливаются на каждом запросе.
2. Lease проверяет одновременно **owner identity, pool entry identity,
   DBAPI wrapper identity и underlying driver identity**. Сам record ID
   недостаточен: после invalidation/reconnect у того же entry другой driver.
   У одного owner может быть несколько последовательных/одновременных leases.
   Checkout заново создаёт поколение; checkin удаляет только совпавшее текущее
   поколение до возврата в pool. Callback checkin с dbapi_connection=None после
   hard invalidation тоже очищает прежний lease по record/поколению.
3. Нельзя стирать invalidating lease до завершения собственного terminate:
   invalidate event наступает раньше фактического close. Событие другого
   engine/чужого owner/старого driver не даёт права закрыть ресурс. Нормальный
   soft invalidation не подменяется hard terminate без обоснованного закрытия
   именно этого принадлежащего запросу ресурса.
4. Terminate выполняется синхронно, без await между последней проверкой lease
   и вызовом публичного driver.terminate(); callback не читает private
   `_connection`/`_terminate_force_close` и не открывает SQL/новое соединение.
   Сначала закрываются ещё принадлежащие запросу драйверы, затем отменяется
   и присоединяется owned ASGI task. Ошибка/уже закрытый driver обрабатываются
   без падения pool bookkeeping, без логирования входного proof и без
   автоматического retry. Успешные запросы terminate не вызывают.
5. Процесс cleanup принадлежит внешнему guard. Он исключает свою current task
   из списка отменяемых задач; ASGI worker и все обнаруженные дочерние задачи
   сравниваются по **тому же owner object** в Task.get_context(). Нельзя
   отменять все asyncio tasks процесса, предполагать родство по stack/name
   или захватывать другой запрос с совпавшим URL. ContextVar не очищается
   раньше, чем перечислены и присоединены его задачи.
6. Один snapshot задач недостаточен: отмена worker может создать новый
   shielded close/graceful/cancel task. После отмены и присоединения выполняется
   повторный ограниченный поиск до отсутствия живых задач владельца. Поздние
   завершившиеся исключения извлекаются, чтобы не остался never-retrieved task.
   Cleanup не должен сам создавать бесконтрольную цепочку новых задач.
7. Все этапы используют тот же hard deadline. Нельзя по очереди дать каждой
   task/connection ещё 0.5s; это один общий остаток. Не считать `cancel()` либо
   `asyncio.wait(timeout)` доказательством завершения. Если задача остаётся
   pending к пределу, тест и общий DB-cleanup gate не пройдены; нельзя вернуть
   успех или молча назвать оставшуюся работу законченной. Перенос cleanup в
   фоновый dispatcher или открытие нового таймера не соответствует договору.
8. После possible commit — только unavailable/0 retry при неизвестном исходе,
   даже если все локальные tasks закрыты. Transport terminate не доказывает
   rollback на сервере. Проверка authoritative keys и отсутствия частичной
   пары остаётся следующему настоящему показу и причинным DB тестам.

### Известный предел checkout — не скрывать в итоговом PASS

`create_engine` сейчас включает `pool_pre_ping=True`. В фактически прочитанном
SQLAlchemy `_ConnectionFairy._checkout` ping повторно используемого connection
идёт **перед** `pool.dispatch.checkout`. Новое физическое подключение и часть
диалектной инициализации также могут выполняться до checkout. Поэтому один
registry checkout/checkin ещё не видит lease при timeout/cancellation
connect/pre-ping. ContextVar может связать родившуюся cleanup task, но сам по
себе не даёт права terminate не зарегистрированный чужой driver.

Для текущего pg_sleep после успешного checkout это не опровергает проект.
До полного HTTP PASS нужно отдельно причинно проверить real connect/pre-ping,
пустой/занятый pool и initialization cancellation. Если остаётся живой driver
или закрытие выходит за предел, требуется отдельное минимальное публичное
решение этой стадии; нельзя распространить PASS checked-out case на неё,
отключить pre-ping у всех маршрутов или приписать собственность по одному
текущему ContextVar без точного lease evidence. Это открытый validation предел,
не новый запрос продуктового решения владельца.

### Причинные проверки именно этого исправления

- Сохранённый реальный auth `pg_sleep(10)` RED становится GREEN: ограниченное
  время, нет `_terminate_graceful_close`/session.close/request tasks и нет
  удержанного checkout/transaction после завершения; pool снова пригоден.
- Отдельный медленный close/rollback после отмены; обнаруживается close task,
  созданная уже после первого списка потомков. Не заменять этот случай только
  `asyncio.sleep` в route либо счётчиком вызовов terminate.
- Два запроса одновременно: один прерывается, другой продолжает SQL и commit.
  Terminate затрагивает только точный lease первого; второй не получает
  отмены/driver error и сохраняет результат.
- Запрос A возвращает connection в pool, запрос B получает тот же entry/driver,
  затем срабатывает timeout/cleanup A. B остаётся рабочим; stale lease A не
  закрывает его. Отдельно invalidate/reconnect в том же entry меняет driver.
- Последовательные auth→service→renewal сессии одного request; нормальный
  быстрый renewal сохраняет cookie/expiry. Обе alias ветви и три прежних
  analytics ingress/обычные product routes сохраняют прежнее поведение.
- Pending pool wait без полученного connection ничего не terminate; app
  task отменена и присоединена. Проверки connect/pre-ping отмечаются отдельно
  и не объявляются покрытыми только pool-wait сценарием.
- В завершённом профиле проверить остаточные tasks по owner identity, pool
  checkout и PostgreSQL activity/locks независимым observer. На обычном успехе
  registry очищен, listeners не растут, чужой owner никогда не завершается.

Чтение публичных event ordering основано на установленном
`sqlalchemy/pool/base.py`; private имена приведены здесь только как указатели
исследования библиотечного исходника, не как разрешение пользоваться ими в
продуктовом коде. Независимое review будущей реализации остаётся обязательным.

Точный проект RED/resources и дополнительно прочитанная библиотека:

| Вход | SHA-256 |
| --- | --- |
| `specs/273-paid-traffic-analytics/validation/t112-http-boundary-design-20261116.md` | `dcb2481b24728def8f477df86f0392c87bc9b1b12f00d5e925579a10a1a55b9a` |
| `/Users/yshishenya/Documents/crisp/apps/server/.venv/lib/python3.13/site-packages/sqlalchemy/pool/base.py` | `5dbe91e32ec424f1e4cfee5db84896b96cfb23c601020e291d0a6644ff50883f` |
