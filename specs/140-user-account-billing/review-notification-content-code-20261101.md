# Независимое ревью кода содержания уведомлений T048 — 01.11.2026

**APPROVE для ограниченного среза. Блокирующих замечаний к рассмотренному
изменению кода и тестов не обнаружено.** Это приёмка содержания существующих
подтверждений оплаты/включения продления; не приёмка всей T048/#4903, T068,
#7524, FR-105, финансового выпуска или фактической доставки писем.

Рабочая копия: `/Users/yshishenya/.codex/worktrees/f140-referral-reversal/crisp`.
Ветка `codex/140-notification-snapshots`, HEAD
`125b51042ff39a1a7b1d4d051ce2503ea8d1250c`. Рассмотрены незакоммиченные
изменения относительно этого HEAD, а не несуществующий итоговый PR SHA.
Полоса: существующий Spec Kit срез в финансовой области; роль — независимый
проверяющий по навыку `code-reviewer`. Reviewer записал только этот отчёт.

## Основания решения

1. **Подтверждённый источник суммы и фактического срока.** Общий
   `billing/notifications.py:248` берёт сумму/валюту из проверенного invoice,
   отдельно форматирует каждый фактический интервал в МСК. Оба производителя
   `billing/entitlements.py:411` и `:672` передают созданный ими grant, а не
   текущий paid_through, trial или бонус. Исторические строки без данных не
   дополняются текущей подпиской. Проверки суммы/валюты, владельца, повторной
   выдачи, изменения согласия и аудит сохранены; diff меняет только импорт
   помощника и payload существующих событий.
2. **Покупка хранения не стала ложным полным успехом.** Прочитан целиком
   `grant_confirmed_storage` (`billing/purchases.py:691`). Существующие ветки
   expired/elapsed по-прежнему сохраняют расхождение и
   `SERVICE_RECONCILIATION`, возвращаясь до success. Успешный путь в строке 831
   передаёт исходные предоставленные сегменты отдельно; разрывы не
   объединяются в непрерывный срок. `utc` ранее отвергает время без зоны,
   поэтому новый форматтер не начинает трактовать такой снимок как локальное
   время компьютера. Изменение не затрагивает расчёт/выдачу хранилища.
3. **Принятое возобновление не пересчитывается при отправке.** В
   `cabinet/web_routes/billing.py:3482` используются полная сумма/валюта и
   `next_attempt_label` потреблённого resume quote. Прочитаны маршрут,
   `_resume_renewal_snapshot`, `_next_renewal_projection`, формат времени и
   `compose_personal_catalog`: storage уже включён в catalog amount, второй
   раз не прибавляется. Сохраняются явная зона принятой даты или закрытая
   фраза ближайшего окна, без выдуманного будущего календарного срока.
   Получатель, event ID с authority version, guards и общий commit прежние.
4. **Историческая семантика и совместимость.** PAYMENT_SUCCEEDED описывает
   подтверждённую оплату и предоставленные периоды, направляет за чеком и
   текущим статусом в историю, не объявляет чек готовым и не обещает новое
   списание. AUTORENEWAL_ENABLED описывает факт подтверждения и ближайшую
   попытку именно в принятом предложении, отдельно направляя к актуальному
   состоянию и отмене. Старый заголовок сохранён, но тело явно ограничивает
   утверждение историческим действием. Сообщения с прежним минимальным
   payload получают честные переходы к кабинету.
5. **Безопасные поля и существующая доставка.** Builder разрешает только
   положительные десятичные minor units/RUB, числовые календарно проверенные
   периоды, ограниченную строку даты со смещением либо точную закрытую фразу.
   Периоды длиннее 4096 символов и непригодные значения не отображаются как
   подтверждённые. Безопасные ссылки, event identity и mandatory kinds
   сохранены. Поиск всех употреблений PAYMENT_SUCCEEDED,
   AUTORENEWAL_ENABLED и помощника нашёл три прямых payment producer и один
   resume producer; все рассмотрены. Прочитаны bridge/outbox и единственный
   production caller renderer в `workflows/worker.py:710`: он использует
   сохранённый payload, а не текущие деньги/права/согласие.
6. **Транзакции и защита от повторов.** Новые поля сохраняются в прежней
   транзакции с бизнес-действием; отправки до commit и нового финансового
   действия нет. Проверки late renewal используют реальный producer:
   rollback удаляет grant и notice, повторная выдача фиксируется, новая
   session читает тот же payload, повтор подтверждения возвращает duplicate.
   Маршрут inside-window после duplicate/cancel сохраняет единственное
   принятое событие. Initial/early/storage/resume проверки действительно
   читают БД после соответствующих действий.

## Первый этап: 396 проверок и их предел

XML разобраны и применимые части журналов просмотрены из
`/Users/yshishenya/Documents/Codex/2026-11-01/graf-f140-final-failure/`.
Тесты, Ruff, compile, БД и приложение reviewer повторно не запускал.

| Доказательство | Самостоятельно подтверждённый результат |
|---|---|
| `notification-content-red-125b5104.xml` | 3 FAIL: оба поздних успеха не содержали сумму/срок, resume не содержал принятую сумму |
| `notification-content-green-probe.xml` | те же 3 PASS; внешний probe отдельно, в итог 396 не включён |
| `notification-content-existing-integration-corrected.xml` | 341 PASS, 0 FAIL/ERROR/SKIP; до усиленных утверждений, тот же рабочий runtime по сохранённой привязке |
| `notification-content-unit-expanded.xml` | 54 PASS, 0 FAIL/ERROR/SKIP; сохранённые суммы/раздельные периоды, зоны, старые/неверные/личные поля |
| `notification-content-producer-regressions.xml` | 6 PASS: late unknown/sent с rollback/regrant/dedup/new-session и четыре варианта storage success/gap |
| `notification-content-journey-regressions.xml` | 3 PASS: усиленные initial/early/storage/resume проверки, включая конкурентные варианты |
| `notification-content-resume-window-corrected.xml` | 1 PASS: настоящий маршрут, due-now предложение, duplicate, отмена и сохранённое письмо |

Заново пересчитано объединение пяти окончательных XML по `(classname, name)`:
**396 уникальных окончательных PASS, 0 FAIL, 0 ERROR, 0 SKIP**. Шесть и три
усиленных случая заменяют прежние результаты тех же ID, не прибавляются
повторно. Контрольные суммы всех пяти XML и четырёх runtime файлов
самостоятельно совпали с `notification-content-final-summary.json` и
`validation-notification-content-20261101.md`. Это привязка к записанным
рабочим файлам, не новое CI доказательство будущего коммита.

Сохранён первый FAIL inside-window: ошибочно ожидался `conflict`, тогда как
существующий ранний guard возвращает `already_active`. Текущий исходник
проверяет штатный результат и одну строку; финансовая проверка не ослаблена.
Предыдущие collection/точное текстовое ожидание ошибки описаны исполнителем
в validation report и не представлены как успех. Журналы успешных
PostgreSQL проходов содержат завершение и удаление изолированного контейнера.
Это синтетическая проверка провайдера, не подтверждение живых денег/почты.

Во всех пяти тестовых файлах прочитаны изменённые проверки и их diff.
Отдельно сравнение
87 исходных task-строк текущего tasks.md с HEAD дало побайтовое совпадение
ID, описаний и отметок. Новый validation report и fragment рассмотрены:
числа, ограничения и предметный вывод соответствуют проверенным источникам.
Quickstart содержит ссылку и сохраняет границу будущих GitHub gates.

## Дополнительная итоговая сверка: 498 проверок

После первого решения получен шестой набор
`notification-content-entitlement-compatibility.xml`. Независимо разобран
сам XML, полностью прочитан его журнал, перечитаны текущий
validation report и окончание quickstart, разобрана обновлённая внешняя
`notification-content-final-summary.json`.

Новый XML содержит **102 PASS, 0 FAIL/ERROR/SKIP** из существующих файлов
`tests.unit.test_billing_entitlements`,
`tests.unit.test_billing_money_path_e2e` и
`tests.unit.test_notification_preferences`. Журнал подтверждает штатный
изолированный PostgreSQL runner, успешное завершение и
`postgres_test_cleanup=isolated_container_removed`. Тесты reviewer не запускал.

Заново пересчитаны все шесть окончательных XML по `(classname, name)`:
**498 уникальных окончательных PASS, 0 FAIL, 0 ERROR, 0 SKIP**. Прежние 396
выше сохранены как история первого этапа. Повторные 6/3 случая по-прежнему
не прибавлены дважды; внешние три producer probe не входят в 498.
Контрольные суммы всех шести XML совпали со сводкой. Четыре файла продукта
снова сверены: их контрольные суммы не изменились и совпадают с принятым
первым этапом. **Ограниченное APPROVE сохраняется.**

Контрольная сумма дополнительного XML:
`7dae5a5efada6059cc8fbc441ec6729a3401eb1dc197bb2fbd3ae21468e9cdfe`.
Validation report и quickstart теперь корректно сообщают 498. Для истории
их контрольные суммы на первом этапе были соответственно
`1307c1d6cd5d7d429c35e7a36c15154c6795112b8ff0598aa9f2a307c5f53d12`
и `af547a2b7ed647fc00304afbedd3bff2f5a4e50ac4d375a49dcd0faf0ab5d5dc`;
текущие значения приведены в таблице ниже.

Согласованная пауза выпуска сохранена: следующий шаг основного агента —
только местный коммит после сверки; push, PR и слияние сейчас не выполняются.
Все ранее записанные продуктовые и релизные ограничения остаются в силе.

## Сохранённый остаток

- FR-105 planned interval не подтверждён во всех invoice snapshots. Этот срез
  честно показывает фактические периоды и не выдаёт полную T048 за выполненную.
- Старые after-refusal шаблоны и исторические финансовые условия не исправлены
  и не приняты этим решением; действующий F278 FR-041 остаётся приоритетным.
- T048/#4903, T068, #7524 и 58 общих открытых пунктов F140 не закрываются.
  Предметный requirements checklist имеет 8/8; reviewer его не изменял и не
  объявляет повторно принятыми общие списки.
- Перед commit/PR исполнитель должен сохранить этот результат, оформить
  итоговую сходимость/validation metadata и проверить неизменность рассмотренных
  байтов. При изменении runtime нужны соответствующая проверка и новое ревью.
  Будущий PR требует `governance-fast`, `macos-pr`, `pr-metadata` точного SHA
  и текущей основы, общий validator и соблюдение согласованного окна выпуска.
  Новый SHA не наследует автоматом доказательства CI прежнего HEAD.

## Область чтения и состояние

Прочитаны применимые новые разделы spec/plan/tasks/quickstart/analysis,
полный notifications-support, checklist 8/8 и актуальное решение requirements
reviewer. Использовано собственное прежнее чтение навыка code-reviewer и
spec-kit-flow в этом диалоге после проверки неизменных SHA256. AGENTS, README,
document-reading перечитаны; применены product-gates и предметные разделы
конституции, PRD и текущего статуса. Чтение чужого reviewer отчёта не выдаётся
за собственное полное чтение всех 8894 строк базовых/исторических документов.
Общее повторное продуктовое/релизное ревью этим назначением не проводилось.

Код, тесты, checklist, требования, задачи, Git/GitHub, БД, GRAF Dev, почта,
выпуск и production reviewer не менял. Разрешённая запись — только этот
отдельный отчёт. `git diff --check` прошёл; отдельная проверка пробелов
нового отчёта также прошла, без запуска тестов.

## Контрольные суммы рассмотренных файлов

| Путь | SHA256 |
|---|---|
| `apps/server/src/twobrain_rec_server/billing/notifications.py` | `88475b10bbadfbcfbbacaae58df41a498563751be2557cd40a52904c14c66049` |
| `apps/server/src/twobrain_rec_server/billing/entitlements.py` | `8ff60f8a8b22c853c1b81e8a72e690beffd8ddf6ad86fa9d31d53d374bf2708b` |
| `apps/server/src/twobrain_rec_server/billing/purchases.py` | `3dd32a57abaf51cb59de3d88df69e970abee54ce6d5ca929f2583fe3b14253c8` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `60aad306996ea565f303ca90634e811acc13951b9ea3dc6918e2d79f2af0c9c9` |
| `apps/server/tests/unit/test_billing_notifications.py` | `772b82c16f8864b43e5615ee05cb027d235ec88fb4335b9ffbcc9b2dd78b233b` |
| `apps/server/tests/unit/test_billing_lifecycle.py` | `48122fa9d701fc32d03d28ee8451d600026c59c7a5e2a2d702b828c6c86a7a8f` |
| `apps/server/tests/integration/test_billing_return.py` | `e38ac80a6e625171dfc2025c05398b5a1efe6862b4b5c102149e2e6e159729fc` |
| `apps/server/tests/integration/test_billing_purchase_journey.py` | `fc9c982918f47e2dda1611122e4c7186c42d3db0bc1d1c6ecbf8435075dd63bd` |
| `apps/server/tests/integration/test_billing_review_regressions.py` | `017d99c561a1c24422ef3963bc7d1af0a7b9595a566c9ce9ad3c17a73935baff` |
| `specs/140-user-account-billing/spec.md` | `9129a529803696308ad8c7c2ca8e2854c752f0daa12c91188b03a691f367dc38` |
| `specs/140-user-account-billing/plan.md` | `af915b52c60662f8fe7e1a8bc1af247db03e8ca6ea011ea8127fcdff6eab4b95` |
| `specs/140-user-account-billing/tasks.md` | `143e7310a8ec8082fd0efdce703c907f9ccd8b92d97f82a255bcdbd956418559` |
| `specs/140-user-account-billing/quickstart.md` | `b1624c48cfa169416e7835548114ec0c8fcc16a1bd97090131c3ac5cb28fec61` |
| `specs/140-user-account-billing/analysis.md` | `a2a9de4223bde8cd0ebbfeccfc76d268676c39ba42dd82c03cf83e9237a3a1cf` |
| `specs/140-user-account-billing/contracts/notifications-support.md` | `e6da1b00370c7219b45f4d381d2a391b4c5f163d2e0a0d4b8a33c1579b63f988` |
| `specs/140-user-account-billing/checklists/notification-content.md` | `7b7181e41ab3532c4ed159d035eb707b49d87ad980aa985e76e7a6a369c3568d` |
| `specs/140-user-account-billing/review-notification-content-20261101.md` | `c295438539c27f21f4ba786400cf5ee69428125aa26174646240cac11a80aabc` |
| `specs/140-user-account-billing/validation-notification-content-20261101.md` | `78c9c7336ff86fedf67254dad766d7b00011dc3f7b227ed5bfc2b933426af2cc` |
| `changes/unreleased/F140.yaml` | `e4b0ab021c9c3a769e4057b34a8e38b9dd35243facde2b8078257a17d05294d0` |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `/Users/yshishenya/.agents/skills/code-reviewer/SKILL.md` | `d2bd763e7cfa424845c54639d4a97cdb0aa03b5eedeabb1d171a16086584cec9` |
