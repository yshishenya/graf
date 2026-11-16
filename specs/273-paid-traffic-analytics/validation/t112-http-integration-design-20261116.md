# T112 — полный HTTP-путь: выдача, обновление и приём подтверждения

16.11.2026. Исполнитель /root. Основа16323bc9336f7955a7d8f9f07730f76add1b6615,
/private/tmp/graf-f273-result-visibility-20261116. F273/T112/#7698,T113/#7804,
high-risk-product. Инженерное уточнение существующих требований, не новый
продуктовый scope и не сокращение T112. Код/tests ещё не менялись.
Нужен отдельный независимый DESIGN review до реализации.

## 1. Основание и выбранный путь

Прочитан независимый инженерный разбор
[t112-http-issuance-renewal-preflight-review-20261116.md](t112-http-issuance-renewal-preflight-review-20261116.md),
SHA256759e774834bf68b5c30035300ad42d4c65949955e2966038b647017a517a0887.
Это не PASS настоящего проекта. Принято его предложение: отдельная строго
читающая inspection-ветвь, прежний bool admission и неизменный строгий finish
после двух вех. Промежуточная идея phase0 completion внутри admission не выбрана.
Контракт result-visibility §§1–7, activation-milestones, T112 plan/quickstart,
18 неизменных inputs/checklist124/0 и analyze0252da92 сохраняются.

## 2. Два точных владельца и один защищённый auth/period путь

ResultProjectionSession остаётся read-only с прежними полномочиями.
Добавляется ResultInspectionSession(ResultProjectionSession): только общие
start/shared advisory(273,3)/bind_account, уже существующие у admission.
ResultAdmissionSession наследует эту locked-read основу и сохраняет свои
фиксированные admit_event/commit_pair/terminal/finish без no-write успеха.
Прежние тела start/bind_account переносятся в inspection без изменения:
SQL/одна AsyncConnection/RR/caps/deadlines/исключения сохраняются.
Inspection не имеет admit_event/commit_pair и не разрешает DML/flush/commit.
Её finish — обычный checkpoint и исходный rollback/close, не COMMIT.
Фиксированный result_inspection_session wrapper использует тот же внутренний
_result_session_context и обязательную пару work_deadline/cleanup_deadline.

_account_transaction получает внутренний inspection=False, допустимый только
при require_period. Источник один: _result_period_context получает этот выбор
от серверного caller; настоящий метод при обоих значениях остаётся yield None.
Нет другого started_at/receipt или config-источника, включающего измерение.
Ожидаемый exact type заранее выбран: ResultInspectionSession при inspection,
ResultAdmissionSession иначе. Совпадение db/owner/deadlines/started_at/recheck
проверяется как прежде, чужой/begun/unstarted контекст закрывается.
Общая identity/session/membership/device/tenant процедура остаётся одна;
переносить её в похожую копию для GET запрещено. Bind account/source и SH
получаются обоими владельцами в прежнем порядке. Фиксированные source_kind
browser/desktop описывают поверхность, не доказательство capture.

После callback в inspection выполняется _check_admission и checkpoint;
затем контекст выходит через finish/rollback/close. В admission всё по-прежнему
завершается commit_pair. _check_admission при любом BaseException из gates/
recheck/checkpoint сначала сохраняет owner.failed/budget.failed и bare raise,
чтобы перехваченный отказ не оживил чтение. Нет нового срока, refund/retry,
записи решения на GET или ослабления C1. Успешное значение inspection
возвращается только ПОСЛЕ выхода из owned context и cleanup, не из побочного
out-параметра при False/error. Старый admit_result_view сохраняет exact bool.

## 3. Подписанный proof выбирает POST-ветвь до единственной Session

Из существующего verify_result_view_proof выделяется один общий bounded
HMAC decoder. Он проверяет размер/ASCII/форму,domain/secret/signature,валидный
base64/JSON object,точные ключи v/issued_at/binding,version1,int issued_at,
aware now и отсутствие будущего времени. Возвращает только encoded/issued_at;
binding JSON не превращается в доверенные SQL references. Полный verifier
затем сохраняет точное сравнение encoded с _proof_payload свежего binding.
Отдельная функция классификации возраста переиспользует этот decoder:
valid/expired/invalid. Парсер/HMAC не дублируются. Срок600с не меняется.

Один кабинетный result_views.py регистрирует два POST alias с общим handler:
/meetings/{meeting_id}/result-viewed и /desktop/meetings/{meeting_id}/result-viewed.
PrincipalDependency,WebTenantDependency,WebCSRFDependency остаются прежними;
WebDbDependency/storage/network/provider calls в handler не добавляются.
UUID/поверхность определяются path, не X-GRAF-Client или JSON. Секрет —
app.state.web_csrf_secret;settings/sessionmaker штатные. Внешний guard остаётся
до body/auth/CSRF/dependencies и post-response session renewal/cleanup.
JSON body ровно proof; guard уже проверяет duplicate keys,ASCII1536/body2048.
Handler также принимает только этот закрытый body, не отражает его в ошибке.

- invalid/future/unknown proof: unavailable до analytics checkout.
- valid: один прежний admit_result_view с полным свежим verifier в одной
  admission Session. Только valid fresh match допускает пару. Пересечение TTL
  во время чтения даёт unavailable, не смену ветви/вторую Session.
- expired: один общий inspection context с той же auth/source/projection
  последовательностью; callback получает свежие bindings и требует exact
  expired match полного verify_result_view_proof. Затем issue нового proof;
  перед/после sign checkpoint и свежий _check_admission, выход/cleanup.
  Только успешная inspection возвращает renewed. Ни INSERT/ledger/COMMIT,
  ни принятия показа, ни превращения False admission в renewal.

Отдельные сервисные методы issue_result_view_proofs и renew_result_view_proof
используют один закрытый _inspect_result_view callback helper с фиксированным
inspection context. Возвращают dict[str,str] либо str|None соответственно;
helper не публичный endpoint и не новый trusted JSON flag. Callback видит
только bounded db/started_at, решения записывать у него нет. Тот же ранний
principal/session/workspace/surface guard, что у admit_result_view.

## 4. GET: совпадение именно отображаемой версии и блока

Обычный разрешённый review/профиль/playback/share читаются прежним путём.
Только после успешного owner/full-view review выполняется optional analytics
helper. Его бюджет начинается при ВХОДЕ helper, ДО classifier/period/checkout:
cleanup_end=loop.time()+2,work=cleanup_end−0.5. Это срок добавленной фазы,
не ограничение всего продуктового GET. По отказу helper возвращает{} и тот же
обычный review продолжает render, без изменения текста/layout/playback/share.

Inspection заново вызывает тот же get_cabinet_meeting_review с storage=None,
со всеми auth/Meeting/source fences и тем же query selection. Возвращать этот
ограниченный review вместо продуктового нельзя: storage=None не эквивалентен
обычному playback/share состоянию. Внутри inspection используются fresh review
и load_result_view_bindings; нет второго SQL latest-result/extractor.

Обычный MeetingReviewResponse не хранит точные result_version. Для сохранения
исходной версии добавляется optional keyword collector в
get_cabinet_meeting_review; два owner GET передают пустой внутренний словарь.
Он заполняется только из фактически выбранных ORM-строк в том же product
read, без новой SQL,identity_map эвристики или полей публичного JSON:
owner/workspace/meeting/revision/fingerprint/deletion_epoch,
transcript result(id,version), outcome(id,result.id,result.version).
Current transcript берётся из локального result ПОСЛЕ source_result_id override.
Pinned result уже есть в CabinetReadPrefetch.outcome_resolutions: пара
(outcome,result), полученная тем же SQL из default/selected_outcome_result.
Collector выбирает её по фактически выбранному outcome.id; fallback при
неизвестном шаблоне следует выбранному outcome,не переданному query.
Неполная пара/невалидный fingerprint дают отсутствие аналитического selection,
не исключение из продуктового GET или догадку по свежему snapshot.
Для остальных callers collector=None, прежний ответ/SQL count сохранены.

Одна pure-функция сопоставляет original render selection и fresh binding:
meeting/revision/fingerprint/epoch/result-id/version/outcome-id и exact key/type/
непереписанный текст из result_view_text_blocks. Старый текст хешируется тем же
result_view_block_digest со свежими refs,после строгой сверки версий; digest
должен совпасть с fresh binding. Простого совпадения transcript:0/текста мало.
Отдельное совпавшее pinned outcome не теряет собственную версию при новой
расшифровке. Mapping может содержать только совпавшие непустые блоки.
Текст/collector/fresh review существуют только в текущей памяти.
Итоговый proof map после final gate и cleanup передаётся в уже существующие
result_view_proofs обоих page/fragment render. Shared/admin/colleague не получают
proof. Export/audio/form не являются условием доступного владельцу текста.

## 5. Полный срок и очистка двух поверхностей

POST использует исходные request.state.result_view_deadline и
result_view_cleanup_deadline: новые2s/retry на handler/renewal не возникают.
Ограничения128 всех SQL,2s/250ms locks/500ms statements,raw/JSON неизменны;
проверка времени до/после sync digest/HMAC/JSON и final gates обязательна.
Штатные auth/renewal commits остаются: нулевой COMMIT inspection относится
ТОЛЬКО к analytics owner, не всем соединениям HTTP запроса.

GET analytics должен получить то же точное владение checkout/pre-ping/
rollback/close,что внешний POST,не полагаться на глобальное закрытие продукта.
Из _run_result_view_app выделяется только его существующее тело владения
в _run_result_view_operation(operation):тот же уникальный ContextVar,
create_task,children/join,cancellation DB-owner first,точные lease checks и
завершение своего поколения; функция возвращает значение operation после
cleanup. Старый ASGI wrapper вызывает её с lambda:app(scope,receive,send),
сохраняя прежнее поведение. GET helper вызывает её для inspection callback.
Обе timeout_at границы(work и hard) охватывают эту операцию; при work-timeout
отмена/cleanup используют остаток до hard,затем{}. Никакого подставного ASGI
scope/receive/send,engine.dispose или сброса чужого pool. При недоказанной
очистке хотя бы одного нужного пути — implementation HOLD, не PASS по таймеру.

## 6. Query, исключения и секретность

Browser: последний summary_format и UUID source_result_id,как GET. Невалидный/
пустой UUID сохраняет422. Desktop: последний summary_format;source_result_id
игнорируется как его GET. JS уже отправляет именно эти последние значения.
Calendar action/UTM/другие поля не определяют proof или полномочия.

До analytics checkout classifier classify_public_traffic получает request.client,
product_analytics_internal_hosts,headers/UA. Known internal/support/test/automated
исключаются,публичный query/header не разрешает обход. Точная настроенная smoke
identity и связанные smoke_user/workspace/device IDs исключаются. Эвристическое
external и отсутствие smoke не аттестуют внешнего нового клиента;нет нового реестра.
Новые helper без network/provider calls,таблиц,секретов,миграции и durable очереди.
Proof/collector/body/query/content не попадают в exception text,request logs,
provider replay/attributes/ledger/evidence. Только первый-party private/no-store
HTML/JSON. Ответ accepted лишь после commit/cleanup; renewed — после inspection
cleanup. Ошибки auth/CSRF прежние,аналитики — закрытый unavailable. Другие ответы
и неизвестные формы клиент не принимает. Ни T0,ни сбор не включаются.

## 7. Причинная матрица следующей реализации — не результаты

- Исходные реальные alias404/GET безproof воспроизводятся до кода. После wiring:
  real auth/tenant/CSRF/PG source/ledger при явно подставленной T113 boundary,
  accepted после двух durableaccount rows. Настоящий yieldNone:unavailable/0rows.
- Четыре GET(full/HTMX ×browser/desktop):exact bodies/proof при открытой testboundary,
  0analytics INSERT/COMMIT,прежний текст/layout/JSON/SQL. Отказ/secret/db/time/gate
  сохраняет обычную страницу. Shared/admin/colleague0proof;безexport/audioowner подходит.
- Expired→renewed:тот же блок/source/session,inspection0inserts/commit;новый frame/native
  POST valid принимает пару. Future/forged/unknown/TTLrace не создают2Session/retry.
- Оба owner типы:plain/foreign/read-only/unstarted/begun доverifier. Inspection
  directDML/flush/commit/rawConnection отказ;пойманныйgate/decoder/read отказ остаётся
  failed,нетпоследующегоSQL/превращениявadmission. Assertions внеsanitizer.
- Реальные изменения между original GET и inspection:text/version-only при техже
  id/text/order/outcomeslot/revision. Новая подпись никогда не попадает на старыйDOM.
  Unchanged pinned outcome и newertranscript имеют собственные refs/versions.
- Last/duplicate/empty/malformed query в обеих поверхностях;desktop лишнийsource_result_id
  не меняет выбор. Нормальный/repeated GET не принимает событие;observer существующий.
- Cookie/CSRF/nativeheader/foreignsession/owner/tenant/invalidUUID/duplicateJSON/chunked2049/
  proof1537/extraFields:отказ без обходов/reflectedinput. Existing authrenewal сохранён.
- Две вкладки/алиасы/restart/replay сохраняют uniqueaccount keys/payload. Real revoke/
  delete/sourcechange/withdrawal перед INSERT/commit,secondINSERT/unknowncommit и
  cleanup/dependency/sessionrenewaltimeout проверяют настоящий handler,не synthetic200.
- GETslowcheckout/preping/close/rollback и POSTslowbody/auth/inspection/digest/HMAC/
  commit/send/cleanup:исходныйсрок,нетsurvivingtasks/driver;foreignpoolhandoff сохранён.
- Полная обычная60мин600+600,pinned версии и maximumraw/row/node/time дляissuance/
  renewal/admission;не обрезать fixture и не повышатьcaps. Browser observer exactstatuses/
  renewalframe/native/regression;nativeunit не заменяет ручную GRAFDev приёмку.

## 8. Ворота и пределы

До code: независимое exact design review с124/0checklist/18SAME/analyze0252da92/
existingissues. После: причинные PG/browser/failure,implementation review и полный
converge/CI. Истёкшее T098 не продлевать,validator/classification не ослаблять.
T112/T113/readiness/filesystem/receipts/restore/ресурсы остаются обязательными;
fixture не открывает рабочий период. Контент/layout/рабочие nginx/DNS/Compose/
службы/Postal/очереди/письма/аналитика/IP не меняются. Новых визитов/продаж/публикаций
этот проект не доказывает. Предыдущий16323bc93 PASS не переносится на новый код.
