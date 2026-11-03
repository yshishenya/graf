# Независимое ревью требований: промокод на месте F280

Дата: 2026-10-02. Рецензент: `/root/rejection_security_review`. Lane: независимая проверка требований активного high-risk-product среза. **PASS — checked16 / unchecked0**, применимых незакрытых замечаний требований0. Владение ограничено `checklists/promo-inline.md` и этим отчетом; остальные документы, продукт, GitHub, коммиты, выпуск и production не изменены.

Проверены новые FR-024–030 и SC-010–012, clarify2026-10-02, актуальный plan, research, contract, quickstart, существующий tasks.md и предварительные T026–T028 из plan. Окончательные tasks еще не сгенерированы: это обязательный порядок `.agents/skills/speckit-tasks/SKILL.md:66`, а не пропуск исполняемых задач. После этого PASS требуются окончательная генерация задач, текущий read-only analyze и канонический issue sync до реализации. Старые T011/T012 прочитаны и остаются открытыми.

## Основания отметок

| Пункт | Конкретное доказательство качества требований |
|---|---|
| CHK001 | Spec FR-025/029, US1 дополнительные AC1/3/5 и SC-010; contract «Транспорт и выбор» явно разделяет JS-inline и native303, Apply/Enter/empty/cycle; quickstart matrix1/7 требует document marker/event trace/history0. |
| CHK002 | Spec FR-024, contract «Отказ без внутренней терминологии», plan architecture5 различают недоступный код и запрет аккаунта; оба имеют понятное действие, удаление кода не обещает обход workspace fence. |
| CHK003 | Research решение public ошибка перечисляет5loader callers и direct reserve; plan architecture5 и quickstart matrix6 требуют все соответствующие предварительные/окончательные пути и неизменные guards. Это coverage requirement, не claim выполненных tests. |
| CHK004 | FR-029, contract транспорт, plan сроки: MAX48, HMAC/binding/TTL300 отдельно от quote10мин; GET/cycle/start error не продлевают draft, explicit replace может начать новые300с. |
| CHK005 | FR-026, US1 AC4, contract локальные состояния и quickstart matrix3: обе bool states, несколько errors/corrections/remove/cycle, throws storage, scope user/workspace/session. Client bool не становится финансовым разрешением. |
| CHK006 | FR-026/027, clarify и contract checking/recovery: оферта снята при новом/недостоверном расчете; same-document persistence отдельно от best effort полного перехода при JS/storage unavailable. Исторический FR-019/020 уточнен явно. |
| CHK007 | FR-028, contract финансовые границы и quickstart matrix3/4: owner/tenant/session/CSRF/rate limit/catalog/receipt/pending/quote/offer/authority/idempotency; preview может создать quote, но не operation/invoice/promo reservation/provider call. Start перепроверяет независимо. |
| CHK008 | FR-011/029, FR-026, contract локальные состояния и транспорт: временная память только bool/scope; no code/quote/offer в URL/JS persistent storage/logs/analytics. Синтетические evidence и private/no-store headers не подменяют серверную авторизацию. |
| CHK009 | FR-027 и SC-011, contract checking/recovery, plan architecture2/3: один запрос, busy/input/Apply/cycle/start blocking, timeout15с, ручной повтор и отсутствие автоматического money retry. |
| CHK010 | FR-027/028, US3 AC3, contract локальные состояния, plan architecture3: stale/detached/request mismatch/unexpected checkout/login/owner/scope не подменяют форму; явный вход/кабинет, чужой bool не наследуется. |
| CHK011 | FR-027 и SC-011, contract recovery required, quickstart matrix5: network/timeout/500/429/swapError снимают ожидание, удерживают start blocked и offer unchecked до нового успешного server quote; ошибка сети не считается отказом кода. |
| CHK012 | FR-025, plan architecture4, research URL решение, quickstart matrix2: year→inline month и обратный путь/reload, replace без history entry, без code/quote/offer; серверный приоритет явной ссылки сохранен. |
| CHK013 | FR-030, SC-010, contract визуальные границы, quickstart matrix1/5/7: input-associated aria-invalid/alert, единое status, логичный focus, keyboard/Enter,320px/200%/обе темы и Chromium/WebKit. |
| CHK014 | SC-010–012, quickstart RED/GREEN/матрица/выпуск, research harness решение: настоящий browser→ASGI→PostgreSQL, отдельный native JS-off, RED до изменения; placeholder screenshots/исторические PASS не заменяют новый результат. |
| CHK015 | Plan architecture1–6 и ownership T026–T028, research alternatives: existing HTMX/form/303→GET/main/lifecycle/purchases.py; no new API/migration/payment machine/shared-shell rewrite. Product и test files разделены; пересечение согласуется до изменения. |
| CHK016 | Plan admission/release, quickstart допуск/выпуск, SC-012 и открытые T011/T012: requirements gate→final tasks→analyze→issue sync→RED/GREEN→3 current reviews/converge→exact-SHA PR/Full/CD/runtime/publication. F278/человеческая/банк/возврат/конверсия отдельно. |

## Конституция, guidance и проверка исходных предпосылок

Прочитаны `.specify/memory/constitution.md` §III/VI/VII и workflow gates; `docs/agent-guidance/README.md`, `spec-kit-flow.md`, `product-gates.md`, применимые части `release-and-validation.md`; продуктовая модель и ограничения из `docs/prd-voice-layer-final.md` и `docs/current-product-status.md`. Противоречий независимому reviewer gate, secret isolation, правдивости финансового результата, доступности и выпуску по точному SHA не найдено. Capture/AI/deletion/native distribution этим срезом не меняются. Новые внешние зависимости/активы не вводятся; copy соответствует собственным применимым условиям GRAF.

Дополнительно только чтением сверены реальные исходники: `cabinet/templates/cabinet/base.html:25` уже загружает HTMX2.0.10; `billing_checkout_content.html:20/27/28/59/60` содержит существующую preview form и associated controls; `cabinet.js` содержит initBillingRenewalChoice/initBillingFocus/initCabinet/afterSwap; `cabinet/templates.py:144–147` подтверждает private/no-store/DENY/no-referrer; `billing.py:194–196` задает draft300с; `purchases.py:495` задает quote10мин; `purchases.py:173` имеет dedicated workspace budget fence, `:1017` общий validator с внутренними public errors. Эти чтения подтверждают проектные предпосылки, но не доказывают будущий HTMX swap/фокус/безопасность результата. Требуемые новые браузерные/серверные проверки остаются обязательными.

## Снимок прочитанных артефактов

| Файл относительно F280 | SHA256 |
|---|---|
| `spec.md` | `3a025d9db042e70ce327c23b10dad1d834f94031e511e3ca9b6bee4ea198f869` |
| `plan.md` | `9431920f20c145361a3febdcdc33f8eef44d06cc50fd3550c9d145b3052998f5` |
| `research.md` | `c0774e0357447832793fccea4de4345039f4935f53bc76df5c83ce476da16ead` |
| `contracts/payment-journey.md` | `a48f4ff5e5a239f72010f5ffa2a9726c1d47db64693c24100e26d9a89c213a17` |
| `quickstart.md` | `be182de8e8a8846d1af8d96d41c1df3473ab0189037bf28d642180ce705e4bdd` |
| `tasks.md` | `82071405948069a4cbc95ade7d0fd3f4e9c96ef6b6949f270b22b6e76be8371a` |
| `data-model.md` | `f49d566ed31da1fe56a2e32be380bc65a7a7d90e13e16ca9fbfc5f4de4546d68` |

Источники HTMX/WCAG и локальные source pointers рассматриваются как основания выбора дизайна, не гарантия конверсии. Отчет относится к записанным требованиям; последующее изменение существенного поведения требует повторной независимой проверки затронутых пунктов. Ссылочные уточнения research без изменения требования сами по себе не требуют повторять продуктовые тесты.

## Границы заключения

Новые tests/browser/payment не запускались этим рецензентом. Этот PASS разрешает переход к окончательным задачам/анализу/трекеру; реализация по-прежнему ждет остальных ворот. Реальный введенный промокод, новая привязка карты/списание/чек/зачисление/возврат и желание клиента оплатить не объявлены подтвержденными. Свежая отдельная READ ONLY проверка кампании не заменяет браузерный результат. Отметки16/0 сверены после записи checklist; другие checklist markers сохранены. Итог текущих reviewer-owned checklist69/0; всех checklist включая author requirements77/0. Это не повторная приемка прежнего кода. Последние ссылочные уточнения research и уточненный предварительный T026 server/public copy → T027 inline → T028 review/release перечитаны; verdict unchanged.
