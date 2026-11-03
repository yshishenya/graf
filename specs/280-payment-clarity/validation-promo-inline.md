# F280 — понятный промокод без перезагрузки

Дата: 2026-10-02. Lane: `high-risk-product`, затем `release-deploy`. Продолжение существующей фичи F280, задачи T026–T028, issue#7460. Владелец разрешил исправления, коммиты, выпуск и публичное оформление. Реальную оплату за пользователя не выполняли.

## Причина и реализация

Внутренний текст закрытой кампании выглядел как неисправность всей оплаты. Заменены только сообщения существующих проверок: недоступный код предлагает убрать или исправить код; отключенный/истекший/исчерпанный бюджет аккаунта предлагает поддержку. Узкий тип AcceptanceBudgetUnavailable передается через откат основного initial checkout в фиксированный публичный account_unavailable; неизвестные/provider ошибки не раскрываются и не классифицируются как ограничение аккаунта. Денежные условия и блокировки прежние.

Существующая POST-форма предварительного расчета использует установленный HTMX2.0.10 и обновляет только main из полного ответа сервера. Денежная форма остается обычной. В документе сохраняется только scoped bool выбора продления, даже при отказе sessionStorage и двух ошибочных кодах подряд. Новая оферта всегда непринята. До завершения проверки ввод/период/start отключены; сбой дает явное восстановление и запрещает старый start. Ответ принимается лишь при совпадении запроса, подключенного main и user/workspace/session. Максимальное ожидание15секунд. Без JavaScript сохраняется обычный переход формы.

Cycle заменяет текущий безопасный URL без новой записи истории, чтобы reload не возвращал прежний месяц/год. Очистка кода раскрывает связанное поле перед возвратом фокуса. Новых зависимостей, API, renderer, миграций и финансовых переходов нет.

## RED и исправления

- До изменения сообщений:8 ожидаемых domain FAIL,21deselected; причины — прежние тексты campaign malformed/missing/disabled/expired/foreign и account disabled/expired/exhausted.
- До изменения UI: настоящая Chromium regression320px FAIL `Apply must retain the same window`; ASGI POST303→GET200, bridge errors0, isolated PostgreSQL cleanup PASS.
- Промежуточный browser тест сначала считал изменение URL за полную навигацию. Проверка уточнена до actual main document request и сохранения window/document; критерии не ослаблены.
- Следующий browser проход выявил скрытый фокус после clearing. Исправлено раскрытие details до focus.
- JS-off test уточнен к реальному обычному URL/подписи автопродления; native путь не обещает same-document сохранение.
- Тест отказа storage первоначально менял prototype лишь в текущем документе, поэтому после reload storage становилось доступным и False корректно сохранялся. Отказ должен моделироваться в каждом документе; продуктовую логику под неверную фикстуру не меняли.
- Для account route зафиксировано6 ожидаемых HTTP→SQL RED (disabled/expired/exhausted × обычная оплата/после удаления кода): прежний общий unavailable вместо account/support.
- Два независимых code обзора нашли потерю account-сообщения в initial checkout; исправлен отдельный тип ошибки, финансовый rollback сохранен.

- При постоянном запрете storage независимый браузерный проход затем нашел настоящий дефект старой инициализации: чтение состояния бокового меню выбрасывало исключение до установки renewal/afterSwap. Узко защищены чтение/запись состояния меню; при недоступном storage применяется существующая адаптивная раскладка. Полные старые runs с известным FAIL не принимаются; новый источник требует нового GREEN.

- Матрица второго запуска сохранила26PASS/2FAIL Chromium и24PASS/4FAIL WebKit. WebKit timeout был связан с удерживаемой interception; тест теперь продолжает настоящий запрос через loopback мост, который задерживает ответ на17секунд. Native ожидание15секунд не заменено искусственным общим таймером.
- Дополнительный RED detached-fresh-retry показал реальный дефект M2: HTMX2.0.10 получает предков формы после ее удаления; событие завершения может не всплыть на body. Прямой однократный `xhr.loadend` освобождает только собственное текущее состояние. Он не применяет поздний ответ и не изменяет новый блок; успешный afterSwap очищает указатель заранее.
- Усиленный тест проверяет следующий успешный preview в том же документе после удаления старого main. Независимый Chromium повтор1PASS/27deselected за13.69с; обе финальные boundary5 матрицы4PASS/24deselected (Chromium63.51с, WebKit65.04с), cleanupPASS. Исторические ошибки не переписаны как успех.

## Окончательные проверки

Подтвержденные независимые наборы (синтетические данные, изолированная база):

| Набор | Результат | Время pytest | Артефакт |
| --- | --- | --- | --- |
| Domain: причины отказа и тип ограничения | 29 PASS | 0.05с | `graf-f280-inline-copy-type-green-root.log` |
| Recovery/reconciliation | 30 PASS | 0.14с | `graf-f280-inline-recovery-reconciliation-tests-final.log` |
| HTTP/domain/UI/clarity | 205 PASS | 395.14с | `graf-f280-inline-http-domain2-tests-final.log` |
| Account disabled/expired/exhausted × обычный/удаленный код | 6 PASS,101deselected | 36.23с | `graf-f280-inline-account-green-tests-final.log` |
| Финансовые регрессии | 237 PASS | 446.56с | `graf-f280-inline-money-regression-tests-final.log` |
| Storage blocked: Chromium | 2 PASS | 47.98с | `graf-f280-inline-chromium-narrow2-tests-final.log` |
| Storage blocked: WebKit | 2 PASS | 49.56с | `graf-f280-inline-webkit-narrow2-tests-final.log` |

У account сценариев установлен явный запрет `_create_initial_checkout_payment`; список вызовов пуст, финансовых строк нет и счетчики бюджета прежние. PostgreSQL environments удалены после проверок. HTTP collection205/digest `aab51288926c504ea7fcf68781a2839132d4533cb1a52c78e493883b48be4cc2`; money collection237/digest `8bf1ab2541ffdd7863aa46a22fc397bb60930483287a25ed644c3cfa5e163f88`.

Историческая полная браузерная матрица до M2 исправления НЕ GREEN: второй Chromium run26PASS/2FAIL, WebKit24PASS/4FAIL; несовпадения относятся к позднему ответу detached target и таймауту. Причины устранены и подтверждены boundary5; окончательная полная матрица текущего источника остается обязательной. Окончательный запуск текущих исходников: Chromium28PASS283.89с/runner288с; WebKit28PASS404.66с/runner409с; обе изолированные базы удалены. Collection28 на каждый engine, digest `a91f230d0d5e001e4b5a6bc582be774595e05504d88706d752d9b101838e219e`. Артефакты `graf-f280-inline-chromium-3-tests-final.log` и `graf-f280-inline-webkit-3-tests-final.log`. Прежние неудачи не считаются успехом.

## Границы

Синтетические браузер/ASGI/PostgreSQL проверки не подтверждают настоящую оплату, привязку карты, последующее списание, чек, зачисление, возврат или конверсию. Не проводились проверки установленного GRAF Dev и приемка людьми. T011/T012, F278/#7285 и umbrella#7366 остаются открытыми. Прежняя кампания по поручению владельца продлена отдельно; результат в validation-promo-extension.md. Ее код и хеш не публикуются.

## Воспроизводимые окончательные команды

Из корня репозитория, для ENGINE=chromium и ENGINE=webkit:

```sh
GRAF_PROMO_BROWSER=1 GRAF_BROWSER=ENGINE apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_billing_promo_refresh_browser.py -q --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit/test_billing_purchases.py tests/integration/test_billing_promo_refresh.py tests/contract/test_billing_ui.py tests/contract/test_billing_clarity.py -q --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_promo_refresh.py -k account_restriction -q --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_return.py tests/unit/test_billing_money_path_e2e.py tests/integration/test_billing_purchase_quotes.py tests/integration/test_billing_purchase_journey.py tests/integration/test_billing_purchase_storage.py tests/unit/test_initial_checkout_recovery.py tests/unit/test_billing_reconciliation.py tests/unit/test_billing_purchase_observation.py tests/contract/test_billing_security.py -q --tb=short --show-capture=no
```

Accessibility16+16 выполнена после rail fix и до узкого loadend fix; новых markup/style/a11y изменений после нее нет. Итоговые браузерные28+28 выполнены на текущем JS и проверяют focus/status/error/timeout/retry. HTTP205 предшествует test-only усилению provider sentinel; отдельные account6 выполнены после него. Серверные производственные файлы после соответствующих GREEN не менялись. Scoped Ruff, JS syntax, whitespace, governance и changelog-fragments PASS. Единственное ошибочное имя локального валидатора фрагмента не запускало проверки; исправлено на штатный `scripts/validate-changelog-fragments.py`, PASS.

Безопасные metadata: [promo-inline-validation.json](evidence/promo-inline-validation.json) содержит SHA256 проверяемых исходников, завершенных журналов и точные counts/durations; реальные payloads, cookies, promo code/hash не сохранены. Три независимых актуальных обзора — review-promo-inline-flow.md, review-promo-inline-security.md и review-promo-inline-browser.md; отдельное сведение в review-promo-inline-final.md. Выпускные проверки остаются в T028 до фактического rollout.

## Исправление модели событий после первого GitHub run

Первый governance-fast37063682491 на `b46aaa36ca6709a8d9e57fbb6bbb2669c66867eb` завершился FAIL. Диагностический локальный fast воспроизвел3FAIL/98PASS: три meeting-list runtime теста брали `listeners.get(event)[0]`; новые scoped billing listeners регистрируются раньше meeting-list initialization, поэтому тест вызывал только billing no-op. Реальный браузер вызывает все обработчики, а не первый. В этих трех существующих сценариях dispatch теперь вызывает весь список; assertions авторизации, stale response, focus и объявлений сохранены. Production исходники и успешно проверенная browser матрица не менялись. Расширение test ownership ограничено `apps/server/tests/contract/test_cabinet_static_assets_contract.py` по доказанной необходимости.

Прямой текущий file run:76PASS2.37с, `graf-f280-inline-static-contract-green.log`; команда из apps/server: `.venv/bin/python -m pytest tests/contract/test_cabinet_static_assets_contract.py -q --tb=short --show-capture=no`. Новый exact-SHA PR run обязателен. Первый локальный fast также выявил неполный ignored context pointer; его обязательные ownership/branch/source поля заполнены только локально. Проверка dirty worktree затем штатно отказалась выпускать receipt; она не объявлена PASS.


## Дополнительные замечания PR7465

На b2ce252 независимый read-only reviewer подтвердил два medium замечания: account_unavailable сохранял активную денежную форму, а ручной recovery без draft мог терять year. Пять новых contract случаев до исправления:5FAIL; настоящий Chromium annual recovery:1FAIL (неверный href). Минимальный template-only fix исключает account_unavailable из checkout_available и формирует recovery href только cycle=month|year. При account отказе нет start/quote/idempotency/consents/редактора и нет ложного pending; период восстановления — последний подтвержденный сервером.

После исправления: UI/clarity74PASS0.24с; account6PASS12.26с; Chromium inline-errors320/1280:2PASS19.58с, WebKit:2PASS21.89с. Проверен явный recovery переход без draft: year/10000₽, False сохраняется, новая оферта unchecked, платежных POST0. Apply/повтор/ошибки до recovery сохраняют document/window/history; только явная ссылка открывает новый документ. Изолированные PostgreSQL среды удалены. JS/серверная денежная логика не менялись; существующая полная матрица28+28/money237 остается подтверждением остальных сценариев, а новая template ветка покрыта этими отдельными доказательствами. Template SHA2569c68661848504e02b02f067f7e2a3f759fa0c04fd7f808354e4388c1d06d54b2.

Локальный диагностический fast на чистом b2ce252 завершен PASS228с до этих template/test изменений; он не заменяет новые GitHub checks и frozen Full. Proof sha256 и boundaries дополнены в evidence/promo-inline-validation.json. Новые обязательные задачи не требуются: исправления входят в FR024/025/027–029 и SC010/012, действующие T026–T028.
