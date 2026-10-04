# Требования восстановления отложенного чека T031

Независимое ревью качества требований; не отметка выполнения кода или выпуска. Основание: FR-027/028/031/032, US5/AC2, plan: Отложенный чек T031.

- [x] RCP001 Указано различие успеха оплаты и поздней регистрации чека.
- [x] RCP002 Описана применимость ко всем четырём видам покупки и точная связь workspace/operation/invoice.
- [x] RCP003 Задан ограниченный фоновый срок 24ч и явное обновление после него.
- [x] RCP004 Получение истины только GET с проверкой shop/test/amount/currency/identity; новый POST отсутствует.
- [x] RCP005 Обновление чека сохраняет права, суммы, бюджет и отменённое автопродление.
- [x] RCP006 Повтор/монотонность и однократное уведомление проверяемы.
- [x] RCP007 Ошибка GET и выключение checkout не превращаются в отказ оплаченной услуги.
- [x] RCP008 Указаны локальные/PR/release/production доказательства и отдельно оставшаяся финансовая приёмка.
- [x] RCP009 Задано чтение pending-чека существующей `succeeded_projected` доплаты с запретом повторной финансовой проекции, новых alias/fallback и переписывания сохранённой истории.
- [x] RCP010 При ограниченном размере пачки незавершённые платежи имеют проверяемый приоритет перед успешными pending-чеками; определён сценарий limit=1 со старым чеком и новой оплатой.
- [x] RCP011 Явная проверка возвращает к защищённому фиксированному пути того же счёта с фактическим статусом чека или короткой ошибкой чтения, сохраняет успех оплаты и owner/tenant/CSRF/rate-limit, не принимает произвольный redirect.

- [x] RCP012 Определено receipt-only чтение существующего paid terminal `succeeded_refused`: фон/позднее ручное действие/отсутствие владельца и повторы сохраняют нулевые grants, service/renewal_resolution, деньги/бюджет и отключённое согласие; нетерминальные финансовые операции не классифицируются только по статусу счёта.

Первичное независимое ревью 2026-10-04 до расширения чеклиста: 8 checked / 0 unchecked, PASS качества требований среза T031. Проверены spec/plan/tasks/quickstart, data-model и contracts; доказательства каждого пункта — [receipt-review.md](../receipt-review.md). Это не выполнение T031, не допуск выпуска и не закрытие финансовой/человеческой приёмки.

Расширенное независимое ревью после замечаний PR #7520: 11 checked / 0 unchecked, PASS качества уточнённых требований до реализации RCP009–011. Три найденных дефекта реализации остаются открытыми до исправления и проверки; прежний локальный PASS их не закрывает. Доказательства и граница Legacy Impact — receipt-review.md.

Последующая фактическая сверка незакоммиченных исправлений RCP009–011: локальный PASS по diff и PostgreSQL журналу 183 passed; требования перечитаны, 11 checked / 0 unchecked. Подробности и пределы доказательства — receipt-review.md. Замечания GitHub, exact-SHA проверки и выпуск этой заметкой не закрываются.

Уточнение paid service-gap до реализации: RCP012 подтверждён планом/задачей и существующим producer; 12 checked / 0 unchecked, PASS качества требований. Локальный PASS предыдущих исправлений не подтверждает новую реализацию succeeded_refused. См. receipt-review.md.

Последующая независимая фактическая сверка RCP012: текущий локальный diff и завершённый PostgreSQL журнал 186 passed подтверждают receipt-only для succeeded_refused с сохранением нулевых grants/service gap/финансовых полей/autooff и прежнего нетерминального пути. Требования перечитаны: 12 checked / 0 unchecked. Это не новый exact-SHA/release/production допуск; подробности — receipt-review.md.

- [x] RCP013 Ограниченная успешная очередь чередует pending-чеки через время попытки чтения, включая HTTP/validation отказ, не меняет финансовую историю; задан limit=1 с двумя последовательными проверками.
- [x] RCP014 Поздняя проверка при реальном несовпадении billing_owner_id разрешена действующему owner только для receipt-only paid succeeded_refused/workspace_scope_invalid, создаваемого grant_confirmed_renewal; reconciliation_gap/owner_changed, чужой tenant/member и раскрытие контакта/карты/ссылки прежнего плательщика исключены.

Независимое уточнение требований RCP013–014 до реализации: 14 checked / 0 unchecked, PASS. Основание: plan.md «Дополнение T031 по повторной проверке PR», дополнительные проверки T031 в tasks.md и неизменные FR-005/027/031/032. Runtime-справедливость и реальная owner-changed ветка этим gate ещё не подтверждены; отчёт — receipt-review.md.

Последующая независимая фактическая сверка RCP013–014: локальный receipt diff и завершённый PostgreSQL журнал rotation-owner-complete (188 passed) подтверждают чередование и ограниченный late current-owner путь без новых финансовых полномочий/раскрытия данных прежнего плательщика. После перечитывания 14 checked / 0 unchecked; детали последовательности auth-negative и границы — receipt-review.md. Exact-SHA/release/production и T032 этой заметкой не закрыты.

- [x] RCP015 Поздняя проверка при смене владельца подтверждается вызовом настоящего producer с succeeded_refused/workspace_scope_invalid и сохранением созданных notice/audit/финансового снимка; reconciliation_gap/owner_changed не расширяет право. HTTP/validation отказ первой операции при limit=1 не блокирует следующий чек: после rollback выполняется повторный отбор под workspace lock с текущим receipt-фильтром и меняется только время receipt-попытки; путь без отдельного commit сохраняет те же terminal/scope ограничения.

Независимое уточнение требований RCP013–015 после чтения полного grant_confirmed_renewal и _record_paid_service_gap: 15 checked / 0 unchecked, PASS качества требований до реализации. Прежний synthetic succeeded_refused/owner_changed не создаётся producer и не доказывает настоящий late-owner путь; прежний локальный результат188 не заменяет новые регрессии. RCP014 исправлен на succeeded_refused/workspace_scope_invalid, RCP013 включает неуспешную попытку чтения. Требуются новый код/регрессии реального producer и ротации после отказа; receipt-review.md содержит причинную цепочку и пределы gate.

Последующая независимая фактическая сверка RCP015: настоящий producer refusal/workspace_scope_invalid, отдельный actor-mismatch reconciliation_gap/owner_changed отказ receipt-only, неизменные конкретные audit/service_gap notice и финансовые снимки очереди подтверждены чтением текущего diff и завершённого PostgreSQL журнала receipt-invariants-sorted (190 passed). Сортировка снимков по первичным ключам сохраняет все проверки полей кроме допустимого operation.updated_at. Локальный PASS receipt scope; после перечитывания15 checked/0 unchecked. Exact-SHA/release/production, T032 и общая финансовая/пользовательская приёмка открыты; детали — receipt-review.md.

- [x] RCP016 Доступность «Проверить чек» соответствует связанной операции того же workspace/invoice: разрешены четыре вида покупки, известный provider_id, paid invoice и terminal succeeded/succeeded_projected/succeeded_refused; reconciliation_gap/manual_resolution, неподдерживаемый вид и отсутствие provider_id исключены. Сведения о регистрации/контакте сохраняются по прежнему can_manage без раскрытия прежнего плательщика. Пропуск paid pending-кандидата без действующего personal owner обновляет только время наблюдения, без GET/state/финансового применения; limit=1 с двумя пространствами и реальный actor-mismatch invoice UI имеют проверяемые инварианты.

Независимое уточнение требований RCP016 до реализации:16 checked/0 unchecked, PASS качества требований. Прочитаны plan/tasks «Уточнение T031 по доступности действия и очереди без владельца» и существующие receipt_filter/invoice UI/owner checks. Предыдущий локальный190 PASS не доказывает доступность действия для нетерминальной операции или чередование ownerless очереди; требуются отдельные runtime-исправления и регрессии. Подробности и границы — receipt-review.md.

Последующая независимая фактическая сверка RCP016: scoped UI action query сохраняет сведения по прежним правам, actual actor-mismatch invoice не показывает неработающее действие, ownerless terminal receipt уступает очередь следующему пространству без GET/финансовых изменений. Подтверждено чтением актуального diff и завершённых PostgreSQL журналов eligibility-rotation192passed и eligibility-shapes1passed (поздние отрицательные assertions). После перечитывания16checked/0unchecked, локальный PASS receipt scope. Exact-SHA/commit/rebase/release/production и T032 этой заметкой не закрыты; подробности — receipt-review.md.

Узкое независимое уточнение release-контрактов T031 до патча на HEAD495bde122: RCP004/005/011 и FR-038 достаточны для единственной CSRF receipt-only refresh формы invoice; запрет refund form/action, create_refund/POST refunds и любых новых финансовых изменений сохраняется. Copy-convention остаётся е вместо ё без исключений. После перечитывания16checked/0unchecked, PASS качества уточнения; фактический патч/целевые тесты и новый exact-SHA release ещё нужны. Детали — receipt-review.md.

Последующая независимая фактическая сверка минимального release-контрактного уточнения T031: только две копирайт строки е вместо ё и строго одна receipt-refresh CSRF форма разрешена контрактом; history/refund form/submit/create_refund/POST refunds запреты сохранены, финансовый код не менялся. Прочитан завершённый PostgreSQL контракт/HTTP журнал198passed; локальный PASS этого diff. Checklist перечитан16checked/0unchecked. Новый exact-SHA/full release/production и общая приёмка остаются обязательными; детали — receipt-review.md.

Независимая фактическая сверка совместимости актуального master/F280: baseline1failed244passed подтверждал е/ё в подписи подписки; патч меняет только букву в подписи и трех exact browser locators без изменения href/условий/сценариев/финансов. Завершённый итоговый PostgreSQL/контракт/Chromium synthetic-pages набор261passed прочитан, локальный PASS этого diff. Checklist перечитан16checked/0unchecked. Synthetic browser не подтверждает live production; новый exact-SHA/full release/финансовая и пользовательская приёмка остаются открыты. Детали — receipt-review.md.
