# T112 — инженерный разбор выдачи и обновления proof до кода

16.11.2026. Независимый проверяющий `/root/public_counter_readiness_review`.
Копия `/private/tmp/graf-f273-result-visibility-20261116`.
Заявленный исходник16323bc9336f7955a7d8f9f07730f76add1b6615; Git/remote
не опрашивались по границам задания. Полоса high-risk-product F273/T112.
Разрешена только запись данного нового отчёта. Код/tests/службы не менялись,
тесты/пробы/сборки/агенты и сообщения другим чатам не запускались.

## Вывод и статус

Препятствие подтверждено: `_account_transaction(require_period=True)` всегда
требует точный ResultAdmissionSession и после yield вызывает commit_pair;
его finish принимает только совершённую пару. GET issuance и expired renewal
нельзя подключить к этому пути как обычное успешное чтение. Возврат None из
verifier лишь создаёт отказ; он не доказывает успешное завершение обновления.

Предлагаю отдельную **строго читающую inspection-ветвь** с общей авторизацией,
оставив finish/два события/bool у существующего admission без ослабления.
Ниже — конкретный предлагаемый путь и обязательные решения следующего проекта.
Это инженерное исследование, **не DESIGN PASS или implementation PASS** ещё
не выбранного проекта. Основной агент должен зафиксировать интерфейсы/выбор
и вернуть их на независимый разбор до кода. Новых продуктовых вопросов
владельцу по прочитанному договору не требуется.

## 1. Один общий locked auth/period путь, два фиксированных владельца

Рекомендуемая структура:

- ResultProjectionSession остаётся со всеми прежними запретами DML/commit.
- Узкий ResultInspectionSession наследует прежние numeric/exact detectors,
  fresh RR Session/Connection и сроки. Он получает фиксированный shared
  advisory(273,3) и неизменяемую привязку account/source, но **не** admit_event,
  commit_pair и никакого allow_writes. Его успешное завершение — checkpoint,
  финальная проверка допуска и обычное rollback/close, без COMMIT.
- ResultAdmissionSession может наследовать эту общую locked read основу и
  добавлять только уже принятые фиксированные два INSERT/единственный commit.
  Его нынешний строгий finish остаётся без разрешения phase0/no-write успеха.
- Вынести существующую последовательность identity/session/membership/device/
  tenant из _account_transaction в один закрытый context/helper. Два узких
  wrapper выбирают заранее **точный** ожидаемый тип владельца: inspection либо
  admission. _result_period_context получает выбор только от доверенного
  server caller; JSON/query/header не задают тип или права. Проверка exact
  type/db/deadline/started_at/recheck остаётся обязательной для обоих.
- Настоящий _result_period_context при любой ветви по-прежнему yieldNone.
  Нельзя создать второй «читающий» источник с выдуманным started_at/receipt.
  Future T113 удерживает filesystem SH до DB исхода/cleanup, затем общий
  DB SH273/3 → identity → AuthSession UPDATE → membership/device → Meeting.

Общая проверка допуска должна сохранять failed **при любом BaseException**
из blocker/recheck до и после вызова, чтобы пойманный callback отказ не
оживлял inspection. Финальная проверка после inspector происходит внутри
этого же защищённого контекста; успешные значения возвращаются caller только
после finish/rollback/close. После закрытия owner уже detached/failed и не
может открыть новую фазу. Полагаться только на внешнее исключение C1 нельзя.

`admit_result_view` сохраняет точный bool:True только после принятой durable
пары/идемпотентного решения и завершения cleanup;False при любой неизвестности.
Новая инспекция возвращает proof map/renewed proof либо отсутствие результата
отдельным типизированным внутренним результатом. False из admission никогда
не преобразуется в renewed по заранее заполненному out-параметру.

## 2. POST выбирает read-only renewal до открытия единственной Session

Чтобы не ослаблять admission.finish и не открывать два снимка, предлагаю
до DB ветвления узко разобрать **подписанный** bounded proof:общий decoder
проверяет existing HMAC domain/secret,размер,форму,версию,тип issued_at и
отсутствие будущего времени. Он возвращает только классификацию возраста,
а не разрешение на доступ/выбор результата/веху. Его код разделяется с
verify_result_view_proof, без второго похожего HMAC/parser.

- Подписанный неистёкший proof: один существующий admit_result_view с прежним
  bool и свежим полным verifier внутри его собственной RR Session.
- Подписанный истёкший proof: один inspection context; заново get_review,
  bindings и полный verify_result_view_proof с фактической текущей сессией,
  owner/workspace/meeting/revision/source/result/outcome/epoch/digest.
  Только exact expired match разрешает issue нового proof без событий.
- Невалидный/будущий/неизвестный proof:unavailable; он никогда не задаёт SQL
  reference и не открывает доверенный inspection.

Полная проверка внутри выбранного owner обязательна независимо от предварительной
классификации. Если proof пересёк TTL между выбором и свежей проверкой,
не переключать ветвь/owner и не открывать другую Session:безопасный unavailable,
следующая настоящая видимость может обновиться. Contract разрешает renewal,
не обещает успех в точке гонки срока. Clock rollback/смена secret тоже не
должны создавать автоматическую вторую попытку.

Альтернативный общий POST-result enum с phase0 completion в admission owner
технически возможен, но расширяет уже принятый автомат полномочий и finish.
Его не предлагаю как минимальный следующий шаг. Если основной агент выбирает
его, нужны отдельные точные разрешённые переходы/terminal checks и новое
проектное ревью; одного булева allow_empty/allow_commit недостаточно.

## 3. GET/HTMX: нельзя привязать свежий proof к устаревшему render по ключу

Два текущих detail GET получают обычный MeetingReviewResponse через WebDbDependency.
`load_fresh_result_view_bindings` заново читает review в другой owned Session,
но возвращает лишь bindings. Между ними результат/слот/текст может смениться.
Словарь transcript:0/outcome:... с совпавшими ключами не доказывает равенства
показанного текста:без сравнения свежий proof попадёт на прежний DOM.

Минимальный путь без изменения продуктовой страницы:

1. Обычный разрешённый review/профиль/playback/share читаются прежним путём.
   Optional analytics отказ не заменяет успешный продуктовый ответ ошибкой.
2. Общая inspection на одной свежей RR Session получает текущий locked review
   тем же get_cabinet_meeting_review с storage=None и тем же выбором. Возвращает
   в памяти пару fresh_review + bindings; нового SELECT latest-result и другого
   извлечения текста нет. Не использовать обычную WebDbDependency Session как
   уже будто бы fresh/read-budgeted owner.
3. До issue proof сопоставить фактический render review и свежий:meeting/revision,
   для transcript — processing_result_id каждого показанного ряда,для outcome —
   outcome_set_id,и exact key/type/непереписанный текст общей функции
   result_view_text_blocks. Для совпавшего блока использовать fresh binding/
   source/digest. При смене источника/версии/порядка/текста — отсутствие proof
   соответствующего блока; простого совпадения key недостаточно.
4. Только итоговый bounded proof map после финальной проверки и cleanup идёт
   в существующие result_view_proofs аргументы **обоих** page/fragment render.
   Эти render helpers уже поддерживают атрибуты. Не расширять shared/admin/
   colleague страницы. Owner-only eligibility проверяется свежим доступом,
   не наличием export/audio/form/ready из JSON.

Это сравнение следует определить одной pure-функцией по общему extractor;
не писать две похожие процедуры digest. Если выбран другой путь — render прямо
из свежего owned review — проект обязан сохранить существующие playback/share/
profile/calendar свойства и отсутствие внешних сетевых вызовов в аналитике;
storage=None нельзя молча выдать за эквивалент всего продуктового review.

## 4. Query selection — точная семантика уже существующих GET

Обязательные параметры для общего inspector/verifier:

| Поверхность | Выбор |
| --- | --- |
| Browser GET/POST | последний summary_format + тот же UUID source_result_id |
| Desktop GET/POST | последний summary_format; source_result_id сейчас GET не использует |

JS уже копирует именно этот набор последних значений в POST. Starlette .get
использует последнее значение; нельзя в новом серверном parser внезапно брать
первое,пересылать все query или выбирать default вместо запрошенного формата.
Пустые/неизвестные template keys и fallback должны повторять существующий
get_review. Browser source_result_id остаётся узким сохранённым transcript
выбором той же текущей media revision. Desktop нельзя дать такой выбор лишь
через POST:GET его не отображает. Calendar action/UTM/произвольные поля не
становятся критериями результата или proof payload.

Закреплённые итоги могут иметь result_id/version,отличные от transcript.
Binding каждого блока должен сохранять собственный источник; одинаковая
показанная строка при другой версии/outcome_set не разрешает renewal.
Смена версии требует штатного render,не подписи нового результата на старый блок.

## 5. HTTP handler и общий срок

Один общий обработчик двух узких POST с теми же PrincipalDependency,
WebTenantDependency и WebCSRFDependency. Не использовать form parsing,
не вводить CSRF исключение и не определять поверхность из X-GRAF-Client.
Canonical path определяет cabinet_web/cabinet_desktop; auth session/device
и workspace берутся сервером. Body по прежнему только proof.

POST получает **исходные** result_view_deadline/result_view_cleanup_deadline
от существующего внешнего guard до body/auth/dependencies. Те же числа идут
в classifier/checkpoints,period,owner,digest,HMAC и cleanup; новый2s при
renewal/handler недопустим. Checkpoint до/после синхронного JSON/digest/sign.
И accepted,и renewed выходят наружу только после завершения внутреннего
ASGI/dependency/session-renewal/cleanup. Timeout после возможного commit даёт
unavailable без retry; после подготовленного нового proof — тоже unavailable,
не утечку заранее заполненного результата.

Запрет INSERT/COMMIT для issuance/renewal относится к owned **аналитической**
транзакции и ledger. Штатные auth dependency и session_renewal_middleware
имеют отдельные commits уже сейчас; существующий foundation намеренно их
сохранил. Нельзя считать нулём все SQL commits HTTP запроса или отключать
продление сессии ради теста. В тесте отличать exact owner connection/ledger
от обычного auth activity writer.

GET — продуктовый запрос,поэтому нельзя распространить POST work-timeout на
весь просмотр и сломать страницу. Для optional issuance нужен один заранее
выбранный budget до inspection/period,с0.5 cleanup reserve; не давать новый
срок после частичного отказа/повтора. Если он исчерпан — успешная страница
без proof. Проект должен явно назвать точку начала этой GET аналитической
фазы и не выдавать её за доказательство двухсекундного всего продуктового GET.
Private/no-store у cabinet_html_response уже есть; POST guard сохраняет его.

## 6. Исключения трафика и данные

Перед proof/допуском исключать настроенную smoke identity по существующим
smoke_identity_class/smoke_user_id и связанным operator IDs. Использовать
существующий classify_public_traffic с доверенным connection/internal_hosts,
а не public graf_traffic_class/header как разрешение. Known internal/support/
test/automated не превращаются в новые внешние AC. Его default external —
эвристика,не подтверждение внешнего клиента. IP/роль/admin не подтверждают
внешний статус. Нового реестра/таблицы/секрета/телеметрического поля не требуется.

Proof/body/выбранный частный query/тексты остаются только в текущей памяти/
первом party ответе. Не включать их в route exception text,обычные request
логи,provider replay/attributes,ledger/evidence. Шаблоны уже экранируют data
атрибут; ответ renewal содержит только status/proof. Отсутствие secret/БД/
receipt/access даёт отсутствие измерения,сохранённый продуктовый просмотр.

## 7. Причинные проверки следующего проекта — ещё не результаты

- RED на текущем строгом finish/отсутствующем HTTP wiring;настоящие четыре
  GET(full/HTMX ×browser/desktop) с открытой лишь тестовой boundary дают
  допустимые proof и **0 ledger INSERT/0 owner COMMIT**,показ не принимается GET.
- Закрытый настоящий T113:GET без proof,POST unavailable,0 новых ledger rows/
  provider calls;это отдельно от injected positive fixture.
- Подписанный expired→renewed:в точности тот же блок/source/session,
  read-only owner,0 inserts/commit;следующий новый frame/native показ с новым
  proof проходит существующий bool admission и сохраняет пару один раз.
- Перехваченный gate/decoder/read отказ внутри inspection:failed сохраняется,
  дальнейшие SELECT/переход в admission/обычный успех невозможны. Чужой тип/
  Session/Connection/begun context никогда не принимается;assertions вне sanitizer.
- Старый render review,между ним и fresh inspection настоящее изменение
  текста/версии/порядка/outcome slot/revision:совпадение transcript:0 не выдаёт
  fresh proof старому тексту. Unchanged pinned outcome + newer transcript
  имеют собственные правильные источники;export/audio не обязательны.
- Browser source_result_id и summary_format,duplicate/empty/malformed query,
  desktop лишний source_result_id:GET и POST выбирают один и тот же набор,
  старый блок другой версии не обновляется. Full/HTMX используют тот же map.
- Future/forged/unknown/1536–1537 proof,чужая session/device/owner/tenant,
  missing cookie-CSRF и стандартный header auth:без обхода dependencies/
  reflected input. TTL race не создаёт вторую Session или retry.
- Настоящий accepted только после pair commit+cleanup;second insert failure,
  unknown commit,cleanup/dependency/session-renewal timeout после commit или
  подписи proof:не выдавать предварительный accepted/renewed,не повторять.
- Один исходный POST deadline включает slow body/auth/lock/inspection/digest/
  HMAC/commit/response+renewal. GET analytics timeout даёт прежнюю страницу
  без proof;нет surviving tasks/соединений,чужой pool handoff сохранён.
- Обычная полная60min600+600 fixture проходит inspection/render compare/
  renewal/admission в прежних128SQL/2s/raw/JSON caps;max envelope отдельно.
  Нельзя уменьшать fixture,поднимать caps,кэшировать authorizing proof или
  запускать лишний SQL retry ради положительного результата.

## Контекст, checklist и границы

Полностью заново прочитан contracts/result-visibility.md;применимы все §§1–7.
Его зависимости activation-milestones и quickstartT112/planT112 — прежнее
собственное чтение того же диалога плюс заново целые T112 разделы. Правила
README/document-reading прочитаны;guidance spec-kit-flow/product-gates —
сохранённое собственное чтение с теми же hash/ограничениями. Конституция
II/III/IV/VI/VII,PRD14/23/25/31,current-status NotAccepted сохраняются:
новой продуктовой/архитектурной области вне уже принятой T112 не добавляется.
При чтении актуальных routes/dependencies/query/render/JS/proof/owner
использованы оригиналы,не только исторические отчёты. Старые H1/H2 полезны
для сохранения внешнего срока,не заменяют новую приёмку полной HTTP цепочки.

18 requirement inputs повторно сверены **18 SAME**. Checklist повторно
посчитаны:requirements16/0,security27/0,privacy-measurement52/0,infra29/0 —
**124 checked / 0 unchecked**. Отметки не менялись;это качество требований.
Ни код/HTTP/issuance/renewal,T112/T113 целиком,рабочий сбор/restore/readiness/
T0,GitHub/release,трафик/продажи этим исследованием не приняты. Настоящий
источник периода остаётся yieldNone. Следующий шаг — конкретный проект
основного агента и отдельное независимое ревью до реализации.

## Проверенные SHA-256

| Исходник | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/result_projection_session.py` | `60311e805510146be860f844e53931fe9570ae56d47eaf5fa1c9d6764ba37e01` |
| `apps/server/src/twobrain_rec_server/product_analytics/ingest.py` | `64d2a716584b9164744cfb1d9a575a03d1b27d39b2e3088157ebd9532e0b8e7f` |
| `apps/server/src/twobrain_rec_server/cabinet/result_visibility.py` | `b59aa36240282748ed88696e1cfee04710302364ce9df9f2b5fc3315fdedb5e7` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py` | `1969ad5c2402bd9a9130db7d5fab228b5156ef2a1e030138da2257be8461e9ba` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/desktop.py` | `e85ada18152f8211f8a9a21e467e643aa8ef20aaef078459ad2b7142947a1959` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/support.py` | `f4c5c6143372ec6aa8d5bd4f71225578e2751839e6af5b4129011f9ec46dff27` |
| `apps/server/src/twobrain_rec_server/cabinet/queries.py` | `a640ce364222d12e1a6ac71b5b569624ab21d8b954daa185526f50b51917fb9f` |
| `apps/server/src/twobrain_rec_server/cabinet/rendering.py` | `7b3145108fa5b4d5059266ae334b24f420d496d9c229fbf7fa63aaa43c9ba11d` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `7a5215a4794ff01c0662da0953a3f4e79248101008b8e4d558f88ecfb8f9c609` |
| `apps/server/src/twobrain_rec_server/auth/dependencies.py` | `559bcc1c46cdf49cd283d8a199e089fc7047401b669c0ab17ae9b6d98c94d311` |
| `apps/server/src/twobrain_rec_server/api/product_analytics_guard.py` | `de069df2ecf27abc99f185d4591bf44b06df22149a165bec6b629cdf6e35f3b9` |
| `apps/server/src/twobrain_rec_server/cabinet/templates.py` | `9f369d80c3dda4c2a9856a4174f259b7bbcdefa8395bc2951361899934f5099c` |
| `apps/server/src/twobrain_rec_server/product_analytics/traffic_class.py` | `38d720b2d96e2c150cb32392d79db7c4095f5c951e2349c6f9d8ed0382a0c7bc` |
| `specs/273-paid-traffic-analytics/contracts/result-visibility.md` | `ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8` |
| `specs/273-paid-traffic-analytics/validation/t112-analyze-20261116.md` | `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` |
