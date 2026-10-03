# F280 T045 — сходимость перед выпуском

2026-10-03. Active Spec Kit/high-risk-product; существующий plan/tasks, новая фича не создавалась. Уточнение T045 после failed release-full не меняет FR032/035/036/037, SC013.

| Обязательство | Реализация и доказательство | Состояние |
|---|---|---|
| Старый initial_checkout recovery по FR035 | общий GET/POST helper; сохранённый прежний key/snapshot; owner25 | реализовано |
| FR032 ожидание/главное чтение/вторичное продолжение | h2 Проверяем оплату, local GET primary, quiet continue, no false success/auto check | реализовано |
| Старые финансовые assertions |7 ожиданий текста; резервирование/вызовы/суммы прежние; causal57 и full410 | сохранены |
| Независимое review | requirements17/0; P2 заголовка исправлен; финальные source/test | PASS remarks0, оба P2 закрыты |
| Выпуск T032 | новый PR/source/train/candidate/full/GO/CD/live proof | partial: требуется production |

Новых actionable implementation findings после исправления S1 не выявлено. missing0/contradicts0/unrequested0; T032 остаётся явно partial до выпуска и чтения настоящего платежа. Это не утверждение всей финансовой приёмки F278 или банковского зачисления/возврата/живого продления. Старый candidate e1012f98 и CI37107429605 сохранены как FAILURE/NO-GO. Совпадающая авторитетная полная проверка потребуется новому выпуску.

После второго P2: view-model awaiting_payment_result сохраняет заголовок/пояснение и primary local GET без финансовых форм; причинныйRED5/20→full410PASS264.96с на окончательных code/test bytes. Финальные независимые SOURCE/TEST reviews подтверждают remarks0, опубликованы в соответствующих review reports.
