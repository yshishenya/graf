# F280 T051 — истекший ключ и доступное исправление карты

2026-10-04 · Lane: high-risk-product · Issue#7511 · external PR#7506 P2 review. До тестового изменения independent requirements refresh PASS14/0, targeted analyze2/2 и canon sync PASS. База причинной проверки: `b3b3ac1c63f256c8d6b6d39710ed7406f6e90ecf`.

## Причинный RED

Реальный GET `/billing/subscription`→изолированная PostgreSQL; провайдер только synthetic create double с запретом вызова. Матрица24case до root product edit: **11failed/13passed/125deselected**,73.66с pytest/83с штатный runner; контейнер удален. Восемь invoice случаев provider_key_expired (initial_checkout/storage_upgrade/renewal/early_renewal × наличие/отсутствие subscription), один resolution-only provider_key_expired неправомерно скрывали обычный checkout GET, хотя общий денежный набор состояний его разрешает. Два renewal manual_resolution + method_required до/после наличия provider_id скрывали безопасную ссылку проверки карты за веткой ожидания.

Исторический RED24 не содержит добавленный позже positive guard modern manual_resolution; его отдельный текущий GREEN явно проверяет современный snapshot purchase_schema2. Все прежние financial assertions сохранены.

## Проверяемая граница

Final матрица25case различает существующие provider_pending/unknown states, terminal provider_key_expired/legacy observation_expired и modern purchase_schema2 manual_resolution. Expired не становится новым блокером в представлении; безопасная GET навигация к оформлению доступна. Для ready активной подписки допускается существующий non-financial resume quote максимум1; новые operation/invoice/grant и provider payment запрещены. Modern manual_resolution остается blocker, путь к существующему invoice сохраняется; counts operation/invoice/grant/quote и operation/invoice states должны совпасть до/после GET.

Оба method_required состояния имеют modern snapshot purchase_schema2, отсутствующую сохраненную карту и operation manual_resolution, различаются только provider_id None/known. Безопасная ссылка «Проверить способ оплаты» обязана быть видна вне native details одновременно с проверкой существующего invoice; checkout/resume/early формы недоступны, quote/provider0, состояния неизменны. По одному reason code страница не утверждает «Уже отправленный платеж» ни до, ни после появления provider_id.

## Выполненные команды

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_review_regressions.py -k subscription_existing_payment_of_every_kind -q --tb=short --show-capture=no
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_billing_review_regressions.py -q --tb=short --show-capture=no
apps/server/.venv/bin/ruff check apps/server/tests/integration/test_billing_review_regressions.py
git diff --check
```

Targeted25case GREEN: **25passed/125deselected**,31.95с pytest/39с runner; collection digest `34794967059c8c4a150ab6d2f57eb0feb0d3fa520f392911432e71e043ac4a91`, контейнер удален. Полный existing150case файл: **150passed/0failed/0skipped**,245.26с pytest/255с runner; collection digest `3c99c53f1731b3b8e54454e21c313ac3e1e496bd940e7c95eb68aeb2a720a7ab`. Контейнер удален. Все125прежних регрессий и25current subscription cases выполнены; targeted иfull не смешаны.

Тестовый исполнитель меняет только existing integration файл и этот отдельный отчет. Root владеет template/query/contract/browser, независимыми обзорами и выпуском; денежные handlers/shared set/DB/API/JavaScript не изменены тестовым исполнителем. Никаких реальных платежей, списаний, возвратов, grants или пользовательских изображений; proof synthetic и переносимый. После обоихGREEN перечитаны source/test hashes: route иtest совпали, template изменился в отдельной ветке недоступной оплаты; предел переноса доказательства указан ниже. `ruff` и `git diff --check` PASS. Два прежних предупреждения imported fixture plugin иStarlette не являютсяskip.


## Привязка выполненной проверки

| Файл | SHA-256 на старте GREEN | SHA-256 текущего файла |
|---|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html` | `d99fa5832561649efc5f746772626ec409790f44872a5a256d9f82efb4b22cc3` | `3788ae2d22f8e414d5714b90c8c1bd4285cda38b44d5a04d8d28825d6f8c2541` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `b2ea985f0eb6726d160d4fd211620aa1f94871e7d41e3676179b336ad3d7b048` | `b2ea985f0eb6726d160d4fd211620aa1f94871e7d41e3676179b336ad3d7b048` |
| `apps/server/tests/integration/test_billing_review_regressions.py` | `9428b7d81dd2dce75301aa40bd37ffd8e84bb587acd9811ae110f80d97f0cd95` | `9428b7d81dd2dce75301aa40bd37ffd8e84bb587acd9811ae110f80d97f0cd95` |

Template drift относится к тексту ссылки в ветке `not billing_enabled and not payment_unresolved`: «Помощь с оплатой» заменена на «Обратиться в поддержку». В25case этой проверки billing_enabled=True, потому этот отдельный label не исполняется; route/test bytes неизменны, денежные ограничения и method_required markup текущие. Это не утверждение общего неизменного template; итоговые root contract/browser проверки должны подтвердить его актуальное представление.

Основной исполнитель подтвердил единственный template drift после заморозки; окончательный UI80 и browser16/16 покрывают новую подпись. Предложенное уменьшение ширины не принято: проверенная ширина подписки720 сохраняется и согласуется с invoice. CSS после GREEN не менялся; дополнительного DB повтора из-за геометрии не требуется.
