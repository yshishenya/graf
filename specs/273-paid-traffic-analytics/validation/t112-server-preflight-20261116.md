# T112 — независимая проверка серверного шага до кода

Дата:16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Основа: `a3ff5b8709dc5da61f4751c4eb3145eb84d9fc9e`; вход был чистым.
Полоса: существующий `high-risk-product`, F273/T112 с закрытой зависимостью T113.
Область: выдача/обновление proof и защищённый result-viewed trigger; не включение
сбора и не рабочая приёмка общей устойчивой границы.

## Решение

**PASS предложенного минимального подхода при точных условиях ниже; P1=0,
P2=0 для этого решения.** Требуется конкретизировать инженерный договор выбора
проекции и общую точку соединения с T113 до зависящего кода и независимо сверить
эту конкретизацию. Нынешние source/proof helpers сами по себе не дают допуска
к INSERT. Недостающие рабочие части T113 остаются закрытыми; это не требование
закончить их все до изолированной реализации T112.

Все13 документов прежнего принятого requirements/analyze среза побайтно
сверены с `503805cb6188f942adb159ea2bab8560969b7b0e`: совпали. Текущий договор
полностью перечитан и соответствует принятому observer/native уточнению
`ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8`.
Все124 действующих вопроса четырёх списков перечитаны отдельно от большой
исторической части; пересчёт: requirements16/0, security27/0, privacy52/0,
infra29/0 — **124 отмеченных,0 открытых**. Их отметки не изменены.
Это оценка качества требований, не выполнение T112/T113.

## Обнаруженная особенность выбора проекции

Текущее `get_cabinet_meeting_review()` принимает `selected_summary_template_key`
и `source_result_id`. Первый выбирает существующую пригодную закреплённую
версию итогов, второй — конкретный разрешённый результат расшифровки той же
принятой аудиоревизии. Значение proof связывает фактический текст и его
result/version/outcome, а не универсальную «последнюю запись».

Browser GET передаёт оба значения, desktop GET сейчас передаёт только
`summary_format`. JS запоминает и проверяет неизменность `location.search`,
но POST строит как `state.path + '/result-viewed'`, теряя выбор. При простом
копировании этого поведения сервер может проверить другую проекцию и
неправильно отвергнуть допустимый прежний блок. Проверка proof по новому
«самому свежему» результату или выдача renewal для другого блока недопустимы.

Минимальное исправление проекта:

1. Target остаётся проверенным canonical собственным browser/desktop pathname
   плюс `/result-viewed`. В query переносятся только штатные ключи
   `summary_format` и `source_result_id` из того же актуального снимка query.
   Произвольный URL, fragment, tracking/referrer/calendar/private-share ключи
   и proof туда не переносятся. В JSON по-прежнему только `proof`.
2. Сервер использует тот же разбор выбора, что и соответствующий GET, затем
   тот же общий review helper. Query — недоверенный выбор, не доказательство
   доступа/готовности. Неверный UUID/размер/неоднозначное значение закрывает
   измерение; HMAC и точное fresh binding остаются обязательными. Следует
   согласовать повторные ключи детерминированно с GET либо отвергать их в
   аналитическом запросе; нельзя брать разные значения на клиенте и сервере.
3. **Особо desktop:** нельзя начать применять `source_result_id` только на
   POST, пока GET его игнорирует. Минимальный вариант без изменения продукта —
   сохранить текущую семантику desktop: использовать `summary_format`, а
   `source_result_id` игнорировать так же, как GET. Если исполнитель выбирает
   поддержку этого штатного выбора и для desktop GET, нужно явно закрепить
   одинаковое поведение GET/HTMX/POST и причинно проверить его до приёмки.
   Эта развилка инженерная; отдельного вопроса владельцу не требует.
4. После любого await клиент вновь проверяет полный прежний query, root,
   node/proof/CSRF/nonce. Добавление разрешённых selection query не превращает
   смену query или новый nonce в новый переход видимости и не разрешает retry.
5. Формат/поля proof не меняются. Старый proof может оставаться допустимым
   только при равенстве своей свежей разрешённой проекции. Новый result/version/
   source/outcome/digest требует нового render, не renewal старого блока.

Это уточнение transport выбора в уже принятой проекции, не новый доверенный
флаг, не новый источник происхождения и не расширение каталога событий.

## Одна общая граница T113 вместо второго writer

Прочитанный `ProductAnalyticsIngestService.ingest_authenticated()` уже владеет
транзакцией обычного account ingress; обе result-вехи намеренно отклоняются
как `trigger_unverified`. `admit_account_milestone()` — SQL-примитив, который
не делает commit и прямо требует свежих общих gates у вызывающей стороны.
Его наличие не означает наличие готовой общей T113 boundary: сейчас нет
принятого runtime verifier started_at/fences, а legal gate безусловно
добавляет `activation_recovery_unverified`.

Минимальное корректное соединение:

- Доверенный серверный result-viewed вход находится в существующем
  `product_analytics/ingest.py` и переиспользует общий внутренний владелец
  транзакции/проверок account admission. Допустимо выделить этот общий
  внутренний участок из существующего `ingest_authenticated()`; route не
  открывает независимую commit boundary и не зовёт примитив напрямую.
  Не нужен новый сервис, универсальный брокер, ledger или система идентичности.
- Browser и desktop alias вызывают один обработчик/серверный путь. Входом
  служат проверенные principal/tenant и ограниченные selection/proof, а не
  payload произвольных событий. Сервер сам строит обе прежние вехи только
  после проверки факта. Никакого параметра `trusted=True`, допустимого в
  JSON/header/query/settings, переключения source_kind клиента или снятия
  `trigger_unverified` у обычных `/events`/desktop-capture нет.
- Получение общей защищённой готовности и её `started_at`, открытие отдельной
  аналитической DB-сессии, locks, вызов свежего T112 verifier, передача пары
  примитиву и единый commit относятся к одному внутреннему пути. Дата не
  передаётся route-ом как полномочие. Локальный snapshot readiness не живёт
  дольше закрывающего его контекста/блокировки и не разрешает поздний callback.
- До T113 настоящий источник готовности возвращает отсутствие разрешённого
  контекста; `activation_recovery_unverified` сохраняется. Ни issue state,
  paid approval, пустой ledger, сегодня, первое обращение, env с произвольной
  датой, fake receipt или один hash не становятся `started_at` периода.
  При настоящем отказе нет issuance/renewal/INSERT/egress, а обычный render
  возвращает прежнюю страницу без proof.
- Issuance и renewal используют те же source/access/readiness проверки как
  ограниченные чтения, без принятия события. Issuance связывается именно с
  projection, которую renderer сейчас отдаёт: если повторная проверка видит
  другой body, нельзя прикрепить proof нового body к старому HTML. Разрешено
  убрать proof при гонке, не мешая просмотру. Обычный GET/poll никогда не
  вызывает INSERT.

Внутренний протокол boundary допустимо подставить из теста. Замена только в
изолированной fixture, без runtime config/HTTP переключателя: она передаёт
заранее заданный синтетический `started_at` и ограниченную тестовую DB-сессию
в тот же verifier. Она не должна заменять проверку proof/owner/source/selection
готовым `True`. Проверка trigger с substitute admission отдельно обозначается
как таковая. Если тест сохраняет пару через реальные SQL primitives в тестовой
PostgreSQL, это доказывает изолированную атомарность пары, но не рабочую
готовность, filesystem/drain, recovery и полноту истории T113.

## Точные требования к свежести, locks и бюджету

Общий порядок настоящей T113: filesystem SH неблокирующе → общий PostgreSQL
SH transaction advisory lock `(273,3)` → identity → session/membership/device
→ meeting/source/result. Ключи доставки `(273,1)/(273,2)` не переиспользуются.
Filesystem lock сохраняется до разрешения commit/rollback и закрытия соединения
при неизвестном исходе. Пока настоящая boundary не готова, этот порядок нельзя
объявлять реализованным с помощью fake context.

Внутри допущенного аналитического контекста:

- Точная активная `UserIdentity` блокируется shared в порядке T113 до чтения
  частного источника; этот же identity lock использует account close перед
  purge. Сессия перечитывается из БД: id/user/workspace/device, active,
  expiry, действующее членство/workspace organization и trusted binding/device.
  Principal, созданный auth dependency в другой уже закрытой сессии, не
  заменяет эти свежие значения. Старый токен/legacy context без привязанной
  auth session не получает proof. Заголовки/клиентские ID полномочиями не служат.
- Режим блокировки должен конфликтовать с изменением проверяемого статуса/
  binding, а не только с удалением ключа. `FOR KEY SHARE` сам по себе не
  запрещает обычный non-key UPDATE status; для этого нужна действующая
  соответствующая shared row-блокировка либо эквивалентный продуктовый fence.
  Все аналитические захваты NOWAIT или с lock timeout≤250ms.
- Переиспользуется существующий meeting/source/deletion порядок. Meeting
  перечитывается под fence с `populate_existing`, проверяются exact owner,
  full-view access, workspace, deletion_state/timestamps/epoch. Нельзя
  создавать/обновлять `DeletionFence` через `ensure_deletion_fence()` только
  ради аналитического чтения. Занятость measurement fence даёт unavailable,
  не отказ продуктовой операции.
- Принятая текущая MediaRevision/fingerprint, workflow/result, собственный
  outcome-set закреплённых итогов и audit/upload lineage проверяются свежими
  после locks. Нужен фактический fence против смены текущей ревизии, публикации/
  удаления/редактирования выбранного результата или outcome между review и
  commit; обычный SELECT без координации с writer такого свойства не даёт.
  Сохраняются полный review/access и ровно показанный selection. Pinned outcome
  может иметь другой result, чем расшифровка; не заменять его latest result.
- Binding пересчитывается общими уже принятыми `load_result_view_bindings()`
  и text selectors, а не второй похожей выборкой. `load_result_view_source()`
  проверяет lineage, но его docstring явно оставляет caller-у locks/readiness/
  доступ/бюджет; переданное started_at само по себе ничего не разрешает.
- Непосредственно перед каждым новым INSERT общий boundary заново проверяет
  текущие legal/disclosure/withdrawal, readiness, mode и resource guard.
  Отказ между первым и вторым INSERT откатывает весь новый набор. Общий
  identity lock внутри SQL-примитива не заменяет более ранний owner/source fence.
- Два результата сохраняются одной транзакцией и одним commit через прежние
  account+event ключи. Ранее принятая строка не изменяется; отсутствующая вторая
  допустима по текущему полному факту. accepted выдаётся только по известному
  durable commit/прежнему решению; ни returned row до commit, ни начало commit
  им не являются. Unknown commit закрывается без автоматического повтора.
- На весь аналитический путь действует один общий 2s бюджет, включая bounded
  body read, ожидание пула/соединения, tenant setup, SQL/commit и завершение.
  Statement timeout≤500ms, lock timeout≤250ms выставляются до аналитических
  запросов; нельзя выдавать один timeout на каждый из множества запросов за
  общий предел. Нет SQL/application retry, зависшей фоновой session/task,
  неограниченного ожидания rollback/cleanup после timeout или сети к providers.
  Штатные auth/tenant/CSRF отказы сохраняются; их исходные зависимости не
  становятся доказательством, что аналитический участок уже ограничен.
- Client disconnect/cancellation обрывает работу и освобождает свои ресурсы.
  Отмена на commit не заявляет rollback гарантированным: закрыть/инвалидировать
  соединение по общему протоколу; отсутствие точного исхода — unavailable.
  Следующая настоящая видимость сперва сверяет авторитетные account keys.

## Ограниченный вход, ответы и запрещённые данные

`PrincipalDependency`, `WebTenantDependency`, `WebCSRFDependency` сохраняют
действующие cookie/header правила; отдельного обхода CSRF нет. Нужен потоковый
предел тела≤2KiB с общим временем, а не доверие только Content-Length или
проверка после неограниченного `request.json()`. Разрешён ровно один строковый
proof≤1536ASCII bytes; неверный тип, неизвестные поля/версия/подпись, будущее
время и чужое binding отклоняются. Разбор неоднозначного JSON не должен
создавать обход закрытой формы.

Valid proof и полностью совпавшая свежая projection могут идти в пару admission.
Expired proof может только получить renewal того же binding при действующих
общих условиях; **0 INSERT и0 provider calls**, после чего клиент снова
проверяет frame/native. Invalid/сменившееся binding не обновляется. Не более
одного renewal на настоящий переход видимости уже ограничено observer-ом.

Ответы остаются точными `accepted`, `renewed` с proof либо `unavailable`, без
exception text/причин/частного содержимого. `Cache-Control: private, no-store`
применяется к proof HTML и ответам. Не записывать proof, raw body, selection
частной страницы, содержимое, account/session/device/meeting/result references
в публичный log/diagnostics/providers или safe_payload. В ledger остаются
только существующие разрешённые свойства; source_kind — только внутренний
trusted caller route. Source происхождения записи определяется lineage,
поэтому desktop-поступление, открытое в browser, не становится manual_upload.
Manual_upload даёт capture false; неизвестный per-record capture — отсутствие
свойства, не true. Unknown campaign и внешний статус сохраняют unknown.

## Обязательная причинная приёмка после кода

До закрытия именно этого шага нужны изолированные RED/GREEN, без изменения
рабочих настроек и без повторения реальных записей:

1. Настоящий default gate off/recovery-unverified: GET/HTMX прежние, proof нет;
   POST unavailable, ledger/provider вызовов0, произвольные client result events
   по-прежнему trigger_unverified. Нет рабочего значения started_at из теста.
2. Substitute boundary: browser upload старого разговора с полной новой lineage,
   desktop-derived без capture proof, оба route aliases; ровно построенная
   пара разрешённых payload, без частных полей и выдуманной кампании/capture.
3. Различающиеся summary_format, старый разрешённый source_result_id той же
   ревизии, default/pinned outcome иной версии, desktop semantics и HTMX.
   Query реально приходит на endpoint; несовпавший body никогда не обновляется.
4. Auth/CSRF/tenant/colleague/admin/shared, revoked/expired session, membership/
   device revoke, identity close; не только mock principal, а реальные смены
   SQL-состояний между render и POST/во время ожидания locks.
5. Delete/epoch/source/revision/result/outcome switch между render и проверкой,
   а также во время verifier/admission. После mutation-first нет нового решения;
   если analytics-first, writer корректно упорядочен фактическими fences.
6. Expired matching proof →renewed без счёта; invalid/future/changed signature/
   selection/source/body →нет renewal. Новый настоящий observer show после
   renewal, старый client без native bridge и async freshness регрессии.
7. Ровно одна account+event строка в двух независимых DB сессиях/процессах,
   повтор/restart, уже существующая result другой встречи, сбой второй вставки,
   gate change между вставками, commit failure/unknown: нет частичного нового
   набора, перезаписи первого payload или автоматической повторной отправки.
8. Занятые identity/session/meeting/source locks, занятый DB pool, медленный
   body/SQL/commit/cancel: фактически проверенный общий бюджет и отсутствие
   остающихся задач/сессий. Отсутствие bridge/DB/secret/readiness/реестра
   сохраняет просмотр и0 egress. Browser endpoint test с fake accepted отдельно
   обозначен и не выдаётся за durable end-to-end.

Нужно независимое implementation review/converge на точном последующем срезе;
существующие regression suites и exact-SHA GitHub gates остаются обязательными.
Live issue readback/новый formal analyze здесь не выполнялись: исходное
`t112-analyze-20261116.md` и связь T112/T113 с #7698 сохранены неизменными.

## Доказательства чтения и предел

Карта применимости: `result-visibility.md` целиком; `activation-milestones.md`
целиком; spec Session16.11/FR-021/025; plan T112/связь с T113; tasks T112/T113;
quickstart весь §T112; data-model account decision/transient proof; research
T112; прежние requirements/analyze/preflight и124 текущих вопроса. Guidance
index/document-reading/spec-kit-flow и product gates прочитаны в применимой
области. Конституция II/III/IV/VI/VII и ограничения приватности/удаления/процесса,
PRD весь §23, текущий статус F093/F094 восстановлены по оригиналам.
Хеши четырёх базовых документов совпали с первоначальным T112 design-draft.
Полное новое чтение неприменимой истории PRD/статуса здесь не заявляется;
использован разрешённый владельцем порядок F273. Чужое чтение или hash не
выдаются за самостоятельную новую приёмку всех требований проекта.

Прочитаны server source/proof/projection, browser/desktop detail, auth session/
tenant/CSRF, account admission/SQL primitive/legal gate, meeting/deletion fences
и относящиеся существующие writer lock sections. Серверные тесты, сборки,
PostgreSQL, приложения, browser, runtime и публикации не запускались.
Изменён только этот отчёт; code/spec/plan/tasks/checklists/Git/GitHub не менялись.
P1/P2=0 относится к выбранному проекту при указанных условиях; это не ревью
будущей реализации и не допуск к рабочему сбору, T0, трафику или продажам.

## Точные входные хеши

| Путь | SHA-256 |
| --- | --- |
| `cabinet/result_visibility.py` | `bf7e12055b7db289cd9224a32e41beba7a0359df73de106cdc70705471795fa9` |
| `cabinet/queries.py` | `cf0e7b622c60e53513df78140ddf2d2ab74937a55a15ce7c719de56fa14f50da` |
| `cabinet/web_routes/browser.py` | `1969ad5c2402bd9a9130db7d5fab228b5156ef2a1e030138da2257be8461e9ba` |
| `cabinet/web_routes/desktop.py` | `e85ada18152f8211f8a9a21e467e643aa8ef20aaef078459ad2b7142947a1959` |
| `product_analytics/ingest.py` | `14a635f75ec4749af8b96e4bc405612358918c8fa86f51e66e5d68a91bf1bab5` |
| `product_analytics/milestones.py` | `f6fa054826632f5f6f40c16fd8449f05ea82c35f64750f3e5fea26480ee31f02` |
| `product_analytics/legal_basis_gate.py` | `adb849aca8b9c71a763e567fa507c6be797a84cefcb4460e24b55b3814dd85d1` |
| `auth/dependencies.py` | `559bcc1c46cdf49cd283d8a199e089fc7047401b669c0ab17ae9b6d98c94d311` |
| `processing/fences.py` | `1b4b8398d49212f5703a29e18460130d13d2c2bb39bcbc0b1d968804c63c4834` |
| F273 `contracts/result-visibility.md` | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |

Первые девять путей относительно
`apps/server/src/twobrain_rec_server/`; F273 относительно
`specs/273-paid-traffic-analytics/`. Неизменные13 входов сверены собственным
побайтным сравнением с принятым commit; их полный перечень соответствует
таблице предыдущего observer/native review и дополнению preflight.

## Независимое чтение конкретного продолжения проекта

После записи основного preflight полностью прочитан
`t112-server-admission-design-20261116.md`, SHA-256
`d32db25b482bf3fe4007aa37cc2539db964754c1e953fe3a10743940ae9122c9`.
Кода на этом этапе ещё не меняли. Документ сохраняет все ключевые условия:
один ProductAnalyticsIngestService/SQL primitive/commit, настоящий закрытый
recovery gate, доверенный общий started_at вместо даты, owner/session/source
fences и отдельный substitute тест. **PASS этого закрытого изолированного
серверного проекта; P1=0/P2=0, blocking clarification=0.**

Минимальная конкретная форма соединения, к которой относится PASS: общий
внутренний владелец account-транзакции в `product_analytics/ingest.py` вызывает
внутренний источник защищённого T113 context. Пока verifier не принят, его
настоящий результат — отсутствие допущенного context, без fallback даты и
без частичного разрешения. Только при таком context, пока его locks/session
действуют, выполняется callback свежей T112 проверки и выдачи либо построения
пары. Тест подменяет этот внутренний источник/context, не значение из запроса.
Существующий authenticated путь использует ту же внутреннюю account boundary;
новый route не владеет второй транзакцией и не вызывает admit напрямую.
Названия private helper/method свободны; универсальный framework не требуется.
Это конкретизация уже принятого проекта, не требование включить T113 сейчас.
Если реализация выбирает иное владение контекстом/commit или параллельный
writer, этот PASS на неё не распространяется.

**Отдельная клиентская правка разрешённых selection query может выполняться
сейчас под существующим requirements gate**, без ожидания рабочего T113.
Для каждого из двух ключей выбирается именно последнее значение, как
Starlette `QueryParams.get()`, после чего строится новая query из этих значений.
Нельзя использовать обычный JavaScript `URLSearchParams.get()` как эквивалент
при дублях: он возвращает первое. Пустое последнее значение также нельзя
незаметно заменить предыдущим непустым. Сохраняются canonical same-origin
path, proof только в JSON, общий query freshness и отсутствие retry от
переключения query. Нужны причинные тесты двух ключей по отдельности/вместе,
дубликатов/пустого последнего/кодирования и исключения proof, fragment,
UTM/других значений из POST URL. Серверная семантика desktop/source_result_id
должна остаться согласованной с его GET по отдельному замечанию выше.

Согласованность прежних FR-021/025/SC-006, открытых T112/T113 и исходного
analyze сохранена. Это независимая инженерная оценка конкретного продолжения;
новый live GitHub readback #7804 из draft не выполнялся и его текущий статус
здесь не утверждается. Полная T113/recovery/local_only/T0 и выпуск по-прежнему
не приняты. Дополнен только настоящий отчёт, проверки кода не запускались.
