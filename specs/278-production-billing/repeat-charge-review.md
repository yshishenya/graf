# Независимое ревью требований T035

2026-10-22. **PASS качества требований до изменения продукта.** Чеклист перечитан после отметок: **6 checked / 0 unchecked**. Это проверка определенности требований и согласованности документов, а не результат исполнения тестов или допуск выпуска.

Рабочая копия: `/Users/yshishenya/.codex/worktrees/billing-repeat-recovery-fix/crisp`, ветка `codex/278-repeat-charge-recovery`, исходный HEAD `59ce47d54b6880138aceb7e619eaf472e34851fa`. Выбран high-risk срез существующей F278, T035/US3, частичное продолжение T026. Владение reviewer ограничено новым чеклистом и этим отчетом; продукт, спецификация, план, задачи, остальные чеклисты и внешние состояния не изменялись.

Применены code-reviewer и scoped speckit-analyze. По прямо разрешенному пользователем узкому исключению проверены новые разделы T035, относящиеся к ним требования и guidance; прежняя полная F278 не аудировалась повторно. Существующий проверенный базис чеклистов сохранен. Конституция прочитана в применимых частях VI и Development Workflow And Quality Gates; product-gates — в части внешних зависимостей. Guidance index и правила validation/release использованы для границ последующих проверок. Поддерживаемая команда `check-prerequisites.sh --json --require-tasks --include-tasks` успешно определила текущий каталог F278; `spec.md` проверен отдельно. Указанный в шаблоне skill неподдерживаемый `--require-spec` не использован в итоговой проверке. В before/after analyze нет включенных hooks. Никакие тесты, HTTP, SSH или production действия этим reviewer не запускались.

| Пункт | Конкретное основание качества требований |
|---|---|
| R01 | `spec.md:291–293`, `plan.md:221`, `quickstart.md:63`: оба состояния unknown/noid и sent/knownid, сохраненные status/provider_id, отсутствие второго POST. |
| R02 | `plan.md:219`: immutable результат из уже загруженных скалярных полей до rollback; блокировки освобождаются, новая схема/API/зависимость отсутствуют. Это минимальная коррекция существующей общей ранней ветки `renewal_charge.py:916–918`, без нового запроса или commit. |
| R03 | `spec.md:293`, `plan.md:221`, `quickstart.md:63`: настоящие PostgreSQL/AsyncSession и ограниченные роли/RLS, штатный первый charge через MockTransport, повтор в новой session; отдельные исходный RED и итоговый GREEN обязательны. Их выполнение еще не утверждается. |
| R04 | `spec.md:291–293`, `plan.md:221`, `tasks.md:163`, `quickstart.md:63`: снимок операции/счета/grants/согласия/уведомлений, деньги и срок неизменны, синтетический POST=1, реальные provider операции и внешние письма запрещены. Полнота конкретных полей снимка проверяется при code review. |
| R05 | `spec.md:293`, `plan.md:221`, `quickstart.md:63`: отдельная полная recovery-цепочка, потеря ответа → пустой поиск → поздний успех, отмена, три workflow/replay, одна выдача и duplicate; MissingGreenlet нельзя принимать за успех. |
| R06 | `plan.md:221`, `tasks.md:163`, `quickstart.md:63` вместе с действующими release правилами: независимый обзор кода, точные PR gates, frozen Full CI/CD и проверка production только чтением; отдельная живая финансовая/календарная/почтовая приемка сохранена. |

Scoped analyze T035: **CRITICAL 0, HIGH 0, MEDIUM 0, LOW 0**. Все шесть групп требований имеют покрытие одной явной задачей T035 с точными путями и проверками (6/6, 100%); потерянных требований, противоречий состояния/POST, новых полномочий или обхода release gates не найдено. FR-014/025 и уточнение T035 согласованы; FR-033 задает последующую живую приемку, а не доказательство от synthetic теста. Перечисление release gates в T035 наследует действующие обязательные точные PR проверки и полный frozen release; оно их не сокращает.

Другие чеклисты перечитаны для сохранения базиса, не переотмечались: billing 8/0, infra 8/0, notification-delivery 10/0, receipt-recovery 16/0, refund-observation 12/0, renewal-order 6/0, security 8/0, ux 8/0; requirements 16/0 остается прежней первичной проверкой требований. Всего прежних отметок 92/0, вместе с новым repeat-charge 98/0. Исторические записи в этих документах не превращаются в новую проверку T035 или текущего выпуска.

Контрольные суммы прочитанного базиса SHA-256:

| Документ | SHA-256 |
|---|---|
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `spec.md` | `db906afb6bb2ae5f3034e64b77db2eb4ff1ea5c144f5d69e2a5aee0cf6cb7d83` |
| `plan.md` | `f8416dfd543057644599c54c24684f605637e72d58d41794720e7f3c25b7466e` |
| `tasks.md` | `4949ba7cee616405f445b7d5d4c7863cd72d80441929c9926671e01022320c89` |
| `quickstart.md` | `31e92739c016c25b6d9b834b69212d21eb80dd3283cfcb56f730821b61147229` |

Т035 issue sync еще требуется по плану до реализации; состояние GitHub этим reviewer не проверялось. Исходный RED, исправление, GREEN, полный изолированный recovery без обхода исключения, независимый code review, changelog, exact-SHA PR/full release/CD и read-only production доказательства остаются последующей работой. **T026, T032, реальные календарные/почтовые/банковские доказательства и человеческая приемка не закрыты.** PASS данного этапа снимает только reviewer-owned gate качества требований. Существенное изменение требований или объема требует повторного узкого обзора.

## Независимый обзор кода T035 до получения GREEN/recovery

2026-10-22. **PASS статического обзора точной правки, новой PostgreSQL регрессии и строгого локального recovery-сценария. Существенных замечаний нет.** Root сообщил о синхронизации T035 с issue #7704; внешнее состояние reviewer самостоятельно не менял и не проверял. Предыдущие требования и прежние открытые границы сохранены.

Продуктовый diff состоит только из переноса создания `RenewalChargeResult` перед `await db.rollback()` в общей ранней ветке `renewal_charge.py:916–919`. Загруженные скаляры UUID/str/optional str копируются в frozen dataclass (`:95–99`); после rollback обращения к истекшим ORM полям больше нет. Блокировки освобождаются прежним rollback. Новых запросов, commit, миграций, зависимостей, POST или финансовых переходов не добавлено. Остальные существующие rollback в этом helper не используют тот же ошибочный возврат истекших полей и не требуют расширения патча.

Поиск всех `charge_renewal_operation` в `apps/server/src` подтвердил единственный рабочий caller `workflows/worker.py:553`. Обычный отбор `pending_renewal_charge_candidates` (`renewal_charge.py:583–636`) допускает только scheduled/no provider_id; unknown уже исключен. Проверяемая общая ранняя ветка нужна при гонке после отбора до отдельной charge session, а также при явном повторе helper. Worker пооперационно журналирует исключение и продолжает (`worker.py:549–562`); это подтвержденный дефект повторного чтения, без доказательства двойного списания или потери денег.

Регрессия `test_billing_renewal_planner_postgres.py:423–528` параметризована unknown/noid и sent/knownid. Она не присваивает эти состояния вручную: штатный planner и реальный charge через синтетический provider создают первый исход. В unknown ответ HTTP200 уже принят MockTransport, затем чтение stream вызывает ReadTimeout; второй случай получает валидные id/pending. Второй charge вызывается в новой реальной session и сравнивается с исходным immutable результатом. До/после сравниваются все колонки всех строк выбранного workspace в 10 таблицах: subscription, operations, invoices, entitlement grants, storage grants, payment methods, acceptance budgets/reservations, audit, notification outbox. Порядок детерминирован первичным ключом, timestamps в этой регрессии не исключаются. Это проверяет неизменность денег, оплаченного срока, прав, согласия, бюджетов и уведомлений. Единственный POST дополнительно проверяется и внутри mock handler, и итоговым счетчиком.

Реальность ORM/RLS: используется штатный `create_sessionmaker` с AsyncSession, а не FakeDb; fixture проверяет роль twobrain_rec_maintenance, nosuperuser, nobypassrls, отсутствие владения таблицей и row_security=on (`:182`). Миграции/реальные роли создаются существующей fixture; `tenant_context.py:55–76` восстанавливает валидированный transaction-local контекст после rollback. Повтор в новой session и реальный rollback сохраняют чувствительность к первоначальному дефекту даже при expire_on_commit=False. Полнота иных сценариев tenant isolation не утверждается этим тестом.

HTTP остается синтетическим: синхронный send запрещен исходной fixture, async send допускает только host api.yookassa.test и идентичность точного MockTransport перед вызовом настоящего httpx send. Другой transport, proxy или неожиданный запрос не сможет пройти guard. Временный ключ создается той же fixture по ожидаемому пути, все provider секреты фиктивны. В PostgreSQL регрессии нет независимого глобального socket sandbox; гарантия данного кода опирается на HTTP guard и неизменный локальный DB runner.

Исходный RED журнал `.dev/repeat-charge-20261022/postgres-red.log` прочитан: строки4–9 и198–203 показывают оба варианта повторного charge и прежнее чтение operation.state после rollback; итоги286–290 — **2 failed / MissingGreenlet**, контейнер удален. Это причинное воспроизведение исходного дефекта; GREEN и новый recovery на момент этого обзора еще не заявлены.

Строгий ignored recovery harness `.dev/repeat-charge-20261022/test_unified_recovery.py` прочитан целиком. Узкий перехват MissingGreenlet и финальная bugflag конструкция удалены. Повтор на строках184–193 обязан вернуть unknown/noid без исключения, сохранить снимок и POST=1. Затем настоящий owner cancel handler (`:195–212`), три самостоятельных реальных Temporal workflow/actual worker activity (`:224–266`), три history replay (`:269–271`) и duplicate GET/apply_confirmed_purchase (`:272–282`) предшествуют SAFE (`:283`). Любое исключение/assert прерывает сценарий до SAFE. Фиктивный provider дает пустой LIST в +2м, валидное совпадение полного binding и GET в +7м, а +12м и duplicate сохраняют состояние; provider_id и grant в recovery не назначаются вручную. В новом сценарии нет отдельного notification sender и внешней почты.

Ограничения harness сохранены: planner использует будущий fixture t0; recovery clock отдельно опирается на реальное DB created_at с +2/+7/+12м. Это не живая проверка календарного расписания. Вызывается настоящий cancel handler с подготовленными principal/scope; HTTP auth/CSRF этим прямым вызовом не проверяются. Снимок recovery сравнивает оплаченный срок/согласие/authority и все колонки operations/invoices/grants/notifications кроме updated_at; расширенная неизменность десяти таблиц покрывается отдельной PG регрессией. Python socket guard допускает loopback, локальный Temporal SDK/CLI явно настроен на127.0.0.1; общий OS sandbox для native SDK не утверждается. Все это не заменяет T026/T032, реальные деньги/письма/банк и человеческую приемку.

Зафиксированные SHA-256 на момент code review:

| Файл | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/billing/renewal_charge.py` | `1a3aee3233509b1737f55f505852799eb992a21d3901c27912616042011b77f7` |
| `apps/server/tests/integration/test_billing_renewal_planner_postgres.py` | `2ac1c1c485a8b500bffbb61a8c6c912b02d42afedf042652f3356269c611bf67` |
| `.dev/repeat-charge-20261022/test_unified_recovery.py` | `55f3578c2f274ef0713bd7d86983e57a0bf9c4d0f868a8aa34ec872c0c73338e` |

Reviewer запускал только чтение/поиск и контрольные суммы, не тесты/HTTP/SSH, не трогал работающую GREEN session. Чеклист остается **6 checked / 0 unchecked** как качество требований. Для допуска следующего этапа нужны завершенные GREEN/recovery журналы, затем обычные точные PR/full-release/CD и read-only production доказательства.

## Независимая проверка фактического GREEN и recovery

2026-10-22. **Локальный PASS исправления T035 и строгой изолированной recovery-цепочки.** Повторно проверены неизменные SHA-256 продукта, регрессии и harness из таблицы выше. Reviewer самостоятельно тесты не запускал; вывод основан на прочитанном коде и завершенных журналах root.

- `postgres-green.log:1–3,13–20,31–34`: выбраны122 теста, оба варианта unknown-no-id/sent-known-id реально исполнялись, итог **122 passed, 0 failed, 0 skipped**, runner status=pass и isolated_container_removed. Вместе с исходным RED2failed это подтверждает исправление общей ветки на настоящем PostgreSQL/AsyncSession.
- `recovery-green.log:122–142`: настоящий локальный Temporal CLI1.8.2; SAFE на127 появляется только после всех последовательных assertions проверенного strict harness. Итог **1 passed, 0 failed, 0 skipped**, runner status=pass и isolated_container_removed. SAFE: status=PASS, repeat_charge_error=null, recovery_chain_passed=true, 3 workflow / 3 completed activity / 3 history replay, один новый grant, отмененное согласие и authority сохранены, duplicate_state_unchanged=true; синтетический POST1/LIST2/GET2. Перехвата MissingGreenlet в этом harness нет, поэтому прежний обход дефекта не может дать этот результат.
- В обоих журналах одно предупреждение PytestAssertRewriteWarning для ранее импортированного `tests.fixtures.postgres_test_database`; это не пропуск теста, не отключение Python assert и не ошибка результата.

Нули provider_http/real_charges/external_mail относятся к этим изолированным исполнениям и подтверждаются проверенным MockTransport/HTTP guard, фиктивными секретами и отсутствием notification sender; они не являются внешним аудитом provider/почтового сервиса. В GREEN наборе два синтетических первых POST для двух параметров, в recovery еще один; это отдельные fixture и разные операции, а POST=1 означает один POST на операцию, не один на все запуски. Исходный RED имел еще два синтетических первых POST; все они локальные, новых реальных списаний и внешних писем эти тесты не создают.

`format-baseline.json` прочитан: baseline и current оба имеют format_changes=true, exit0, пустой stderr. Это подтверждает существующее расхождение форматирования всего helper с текущим formatter, но не является PASS format-check файла. Массовая переформатировка вне узкого исправления не требуется для принятия данного минимального diff. Ruff check, format нового testfile и governance PASS сообщены root; отдельного машинного журнала этих проверок reviewer не перечитывал. Точные обязательные CI проверки по-прежнему нужны.

SHA-256 завершенных доказательств:

| Файл в `.dev/repeat-charge-20261022/` | SHA-256 |
|---|---|
| `postgres-red.log` | `ed666de307dfea75ba921d41fe45ca163599b3da93726cf220cf1f8463ba284f` |
| `postgres-green.log` | `12a0baa740c16d3d7568b446b57d0f0b3f4f4c137908a7e161c18ad655de5b80` |
| `recovery-green.log` | `8e6ca04b21da693b16e5e01909741b0a8fb8141ce558ee10adf05e03efa40710` |
| `format-baseline.json` | `f1daa3297217d4d1c490362d94fd44950044f5ce280126c2a1e2dae988e675d6` |

Прочитан новый `changes/unreleased/F278.yaml`: FR/схема/деньги/согласие не расширяются; T035/#7704 и high-risk lane указаны, живая приемка T026/T032 сохранена. Существенных замечаний к текущему локальному объему не найдено. Чеклист вновь перечитан: **6 checked / 0 unchecked**. Независимый gate требований, code review и локальные RED/GREEN/recovery доказательства удовлетворены; можно переходить к подготовке commit/PR в пределах пользовательского разрешения. **Exact-SHA PR checks, frozen Full CI, CD и read-only production проверка пока не подтверждены этим отчетом. T026/T032, живая календарная/почтовая/банковская и человеческая приемка остаются открытыми.**
