# Независимое ревью F140/T048 — содержание сообщений

**Текущий результат: SCOPED REQUIREMENTS PASS — 8 отмечены / 0 открыты.**
Первоначальный BLOCK ниже сохранён как история; основание снятия и точные
границы — в заключительном разделе повторной проверки.

Дата: 01.11.2026. Проверенный HEAD:
`125b51042ff39a1a7b1d4d051ce2503ea8d1250c`.
Область: существующие подтверждение оплаты и включение автопродления,
issue #4903; новый финансовый механизм не требуется.

## Первоначальное решение — до уточнений

**SCOPED REQUIREMENTS FAIL / BLOCK.** Сейчас нет согласованного описания
источников и проверок нового содержимого producer → outbox → render.
Реализацию этого среза пока не начинать. Достаточно коротких уточнений
существующих артефактов T048; новая фича, инфраструктура или дополнительная
задача не нужны.

Это предварительное fail-fast ревью, не заявление о полной повторной приёмке
всех обязательных документов или F140. Полностью прочитаны конституция,
product-gates, guidance README/document-reading, notification contract,
analysis и применимые списки payments/security/operations/UX и два прежних
списка срезов. PRD прочитан частично; длинный product status и полное
содержание spec/plan/tasks/quickstart на этом этапе не приняты: проверены
применимые разделы, текущие уточнения T048 и источники кода ниже. Перед PASS
нужны собственное полное чтение всех обязательных документов и повторная
предметная проверка обновлённых артефактов. Контрольная сумма не заменяет чтение.

## Проверенные основания

- `contracts/notifications-support.md` требует amount/period для payment
  success и resulting state/date/amount/action для cancel/resume;
  последствия даты должны иметь явный часовой пояс.
- `spec.md` FR-070/071 требуют точное содержание и безопасное действие.
  Последние принятые уточнения посвящены UNKNOWN, окончательному отказу и
  напоминанию. Они сохраняют отдельный остаток late-success/manual-resume.
- `notifications.py:309/317/380` возвращает общий текст и допускает только
  invoice для PAYMENT_SUCCEEDED, ни одного предметного поля для
  AUTORENEWAL_ENABLED. Исправления одного renderer недостаточно.
- `entitlements.py:411/670` содержит **два** настоящих производителя
  PAYMENT_SUCCEEDED; оба передают только invoice/action_path.
  Перед каждым уже есть фактический grant и запись
  `service_starts_at/service_ends_at` в invoice. Эти границы могут отличаться
  от исходного планового периода или текущего состояния подписки.
- `billing.py:3482` создаёт AUTORENEWAL_ENABLED в той же транзакции, где
  принят `resume_quote`. Его snapshot сохраняет catalog_snapshot,
  storage_price_snapshot и next_attempt_label. `compose_personal_catalog`
  уже включает цену хранилища в общую сумму catalog_snapshot — второй раз
  прибавлять storage amount нельзя.
- `_next_renewal_projection` возвращает как дату, так и честную фразу для
  уже наступившего окна. Нельзя потребовать единственный формат будущей даты
  и подставить его там, где пользователю было показано «в ближайшее время».
- Внешний probe `late-producer-probe/test_late_notice_content.py` проверяет
  committed row и реальный текст. Две параметризации позднего успеха и
  включение после последующей отмены полезны, но сами по себе не покрывают
  первичный/ранний успех, rollback, повтор, старые сообщения без новых полей
  и оба варианта срока включения. Существующие red JSON/XML не исполнялись
  этим reviewer повторно и не выдаются за новый запуск.
- `analysis.md` датирован 11.08.2026 и называет T048 завершённой, тогда как
  текущая T048 `[ ]`. Он не является актуальным допуском нового среза.

## Минимум до реализации

1. В существующих spec/contract кратко назвать два подтверждённых события,
   источники суммы/фактического периода и принятого resume quote, получателя,
   МСК и историческую формулировку при поздней доставке.
2. В plan указать оба настоящих производителя PAYMENT_SUCCEEDED и маршрут
   AUTORENEWAL_ENABLED, прежний общий builder/renderer и неизменность денег,
   grants, согласия, event_id, транзакции и доставки. Отдельно определить
   честный renderer для уже сохранённых сообщений без новых полей.
3. В tasks сохранить исходную T048 `[ ]` и #4903; добавить только описание
   этой проверки/доработки. Не присваивать выполнение всей T048.
4. В quickstart зафиксировать проверки настоящих производителей, committed
   payload, повтора/rollback и неизменности текста после будущего изменения
   подписки; дата/сумма не должны читаться из текущей подписки при доставке.
5. После уточнения повторить независимый checklist review и текущий анализ
   с точной областью. Это не требует открытия новых задач или нового слоя.

## Отметки и ограничения

Создан reviewer-owned `checklists/notification-content.md`. Все восемь
пунктов оставлены `[ ]`, поскольку текущий согласованный срез не подтверждён.
Список перечитан после записи: **0 отмечены / 8 открыты**. Общие списки
F140 не изменены, старые принятые срезы не отменены. Код, spec/plan/tasks,
Git/GitHub, деньги, приложение и runtime reviewer не менял.

## Дополнительное исследование перед повторной проверкой

Полностью самостоятельно перечитаны конституция, PRD, текущий статус продукта,
product-gates, guidance README/document-reading/spec-kit-flow/development-process,
spec/plan/tasks/quickstart, analysis, notification contract и применимые списки
payments/security/operations/UX, renewal-unknown/final-failure/reminder.
Усечённые части вывода прочитаны отдельными диапазонами; пересказ и хеши не
считались чтением. Это завершает чтение для повторного ревью, но не снимает
предварительный BLOCK без согласованных уточнений требований.

Найден третий реальный PAYMENT_SUCCEEDED в `billing/purchases.py:827`.
Успешное увеличение хранилища может иметь несколько фактических сегментов;
renderer общего события обязан отличать такой период от базовой подписки.
При `service_expired/service_elapsed` существующая ветка сохраняет отдельное
SERVICE_RECONCILIATION, её нельзя переименовывать в полный успех. Все три
реальных producer и эта отрицательная граница включены в CHK001/007.

Состояние после дополнения: **0 отмечены / 8 открыты**, SCOPED REQUIREMENTS
BLOCK. Полное чтение документов само по себе не принимает код или доставку.

### Проверенные контрольные суммы требований

Пути ниже относительны корню репозитория. Основной пакет F140 прочитан
полностью; в зависимостях F278 прочитаны применимые FR001–041, в research
R8–R10, в data-model определения invoice/grant/notice и инварианты,
billing-lifecycle — полностью. Это не приёмка остальных частей зависимых фич.

| Путь | SHA-256 |
| --- | --- |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `specs/140-user-account-billing/spec.md` | `44f3d1d2ffdd110a87a85c39e7ebc8cbdf97c4bd18b3e988e2cbf8c1dc5797e0` |
| `specs/140-user-account-billing/plan.md` | `30ca2a01a60ed8e7a7ee7e4221b062e80bd43d11511652470ca291faf964b961` |
| `specs/140-user-account-billing/tasks.md` | `f21448f5c8eb536263e4e258030deb02fc110904b493b6ac3ed921df060bffc5` |
| `specs/140-user-account-billing/quickstart.md` | `a8a40e99036f91b128f9129494e7e1e7b57a334dc73d35c97aea6a38d5ee19fc` |
| `specs/140-user-account-billing/analysis.md` | `6c643edb08246d749afaf0402903ff924ebce5aeef647929576ac97ac9890534` |
| `specs/140-user-account-billing/contracts/notifications-support.md` | `3b5d29fc37d63087a70d05151da42f7bbe873276c98234a77e9826bba0fdac97` |

Проверка `git diff --check` — PASS. Тесты и приложение в этом назначении
не запускались; финансовые и внешние действия не выполнялись.


## Повторная независимая проверка требований — 01.11.2026

**SCOPED REQUIREMENTS PASS — 8 отмечены / 0 открыты; CRITICAL 0 / HIGH 0.**
Полоса: active Spec Kit slice в финансовой области, только независимая проверка
качества требований T048/#4903. Допуск ограничен существующими PAYMENT_SUCCEEDED
и AUTORENEWAL_ENABLED: их сохранёнными безопасными данными и исторически
правдивым текстом. Первоначальный BLOCK снят после уточнения источников,
сценариев и текущего анализа. Код и доставка этим результатом не принимаются.

Рабочая копия: `/Users/yshishenya/.codex/worktrees/f140-referral-reversal/crisp`;
ветка `codex/140-notification-snapshots`, HEAD
`125b51042ff39a1a7b1d4d051ce2503ea8d1250c`.
Прежняя копия `f216-tracker-recheck/crisp` в этом повторном ревью не изменялась.

### Чтение и источники

После автоматического сжатия истории повторно полностью прочитаны оригиналы
constitution (530 строк), PRD (2474), current-product-status (2385),
AGENTS, guidance README/document-reading/product-gates/spec-kit-flow/
development-process, а также шесть изменённых файлов F140: spec, plan, tasks,
quickstart, analysis, notifications-support. Усечённые диапазоны прочитаны
отдельно; контрольные суммы и пересказ не считались чтением. Целиком
перечитаны восемь общих списков и три прежних списка UNKNOWN/итогового отказа/
напоминания. В зависимостях повторно прочитаны применимые F278 FR-001–041,
research R8–R10, определения invoice/grant/notice и инварианты data-model,
полный billing-lifecycle. Заменённые финансовые условия в исторических
разделах не использованы как текущий допуск.

Повторно прочитаны действующие три производителя PAYMENT_SUCCEEDED в
`billing/entitlements.py` (два) и `billing/purchases.py` (storage), маршрут
возобновления `cabinet/web_routes/billing.py`, `_resume_renewal_snapshot`,
`_next_renewal_projection`, `compose_personal_catalog`, builder/renderer
`billing/notifications.py` и существующий bridge `billing/events.py`.
Эта проверка чтением не утверждает исполнения этих путей.

### Восемь проверенных пунктов

| Пункт | Конкретное основание и предел |
| --- | --- |
| CHK001 | Последнее уточнение spec перечисляет initial/early/normal/late/storage; plan называет оба entitlements producer, purchases и resume route. Исходники подтверждают три payment producer и отдельный SERVICE_RECONCILIATION при expired/elapsed service. Получатель и финансовые проверки сохраняются; новая политика адресатов не создаётся. |
| CHK002 | Spec/contract/plan задают invoice amount_minor/currency=RUB и фактические grant/отдельные storage segments. Trial, бонус и текущая подписка не заменяют оплаченный срок. Planned FR-105 честно остаётся незавершённой частью T048. |
| CHK003 | Потреблённый resume quote сохраняет catalog_snapshot и next_attempt_label; compose_personal_catalog уже включает storage. Уточнение сохраняет полную сумму один раз, явную зону принятой даты либо точную фразу «после подтверждения возобновления, в ближайшее время». |
| CHK004 | Spec/contract требуют прошедшее время, неизменные сумму/сроки после отмены или смены цены, отсутствие обещания текущего согласия/тарифа/будущего списания. Quickstart3 проверяет изменение подписки после события. |
| CHK005 | Minor units/RUB, фактические даты МСК, принятая resume дата с исходной явной зоной, safe invoice и относительное действие; неизвестные поля не становятся подтверждёнными. Старые строки направляют в кабинет без backfill и чтения текущей подписки при доставке. Формулировка чеклиста приведена к этому различию часовых поясов. |
| CHK006 | Spec/contract сохраняют event_id/recipient/channel, транзакцию/rollback/dedup и ограниченную доставку. Plan переиспользует builder/renderer/outbox/Postal без миграции/службы; деньги, grants и согласие не меняются, отправки до commit нет. |
| CHK007 | Пять сценариев quickstart включают настоящие HTTP/producer пути и новый сеанс после commit, initial/early/late/storage segments и gaps, resume до/внутри окна, позднее изменение подписки, rollback/повтор/получателя/отрицательные guards и malformed/старые поля. Синтетическая PostgreSQL/MockTransport проверка отделена от настоящих денег/почты. |
| CHK008 | Актуальный analysis сопоставляет восемь групп и пять сценариев, явно помечает старую сводку80/7 исторической; tasks содержит87 уникальных исходных ID, T048/T068 остаются `[ ]`, #7524 не принимается. M1/M2 записаны отдельно; новых несвязанных задач нет. |

### Применимость остальных списков

Все общие отметки сохранены. Применимость проверена для этого среза; это
не общий PASS F140 и не устранение всех исторических расхождений.

| Список | Применимые требования и сохранённый остаток | Фактические отметки |
| --- | --- | --- |
| payments | CHK001–004/018: provider/invoice authority, неизменная сумма, отсутствие нового charge и отдельный actual grant. CHK006/011/017 и старое after-refusal правило не принимаются глобально; текущая F278 имеет приоритет. | 14 / 6 |
| security | CHK001–007/011: существующие server owner/scope/CSRF/RLS, allowlist и запрет секретов. Новых таблиц и полномочий нет. Общие refund/operator/tenant пробелы за пределами среза не закрываются. | 11 / 6 |
| operations | CHK007: прежние dedup/failure state и ограниченная доставка. Общая reconciliation/stop/renewal/canary приёмка не входит. | 10 / 8 |
| ux | CHK003/004/007/009/013/020 в части правдивого текста, понятного действия, локализации и устойчивого исторического исхода. Новый экран, ручная доступность и глобальный late/refusal UX не принимаются. | 17 / 3 |
| launch-readiness | CHK020/026/033/039: чек не обещается из payment success, получатель/деньги/период безопасны; текущий срез не завершает store/RLS/durable/full recovery gates. | 32 / 8 |
| requirements | CHK007/009/012/013/018/023 применены только к тексту/источникам и сохранению защит. Внешние launch/security/financial приемки и planned interval не объявлены завершёнными. | 17 / 8 |
| product-market-2026 | CHK016/024/027/028/030/033: принятая сумма и срок, paid/bonus distinction, допустимая роль, исторический статус, действие и приватность. WTP/COGS/новые цены не выводятся из уведомления. | 36 / 4 |
| post-plan-readiness | CHK023/026/031/034/036/037 в ограниченной части исходного события, immutable данных, безопасной доставки/получателя и локализации. Полная финансовая матрица, provider outage и launch остаются отдельно. | 25 / 15 |

Фактический итог восьми общих списков: **162 отмечены / 58 открыты**.
Подсчёт сделан по самим строкам чекбоксов; исторические итоговые предложения
в общих списках местами не отражают последующие четыре отметки reference
review и здесь не переписаны. Прежние UNKNOWN/final-failure/reminder checklist
сохраняют свои области; их реализационные PASS не доказывают новый payload.

### Неустранённый остаток и следующий допуск

- **M1 MEDIUM, T048:** immutable planned interval FR-105 не подтверждён во
  всех invoice snapshots. Нельзя выдумывать его из текущего paid_through,
  объединять отдельные storage segments или выдавать бонус за оплаченный срок.
  Это не требует строить новую финансовую модель ради минимального actual
  уведомления и не позволяет закрыть всю T048.
- **M2 MEDIUM, историческая документация:** старые charged-after-refusal
  строки notification/billing/data-model contracts заменены F278 FR-041;
  текущий срез сохраняет оплаченный срок и не восстанавливает recurring authority.
  Старый RENEWAL_LATE_SUCCESS_REFUSED шаблон этим ревью не принимается.
- Ограниченная строка `service_periods` с календарно проверенными числовыми
  интервалами и отдельным перечислением через `; ` согласуется с требованиями;
  неизвестные/слишком длинные значения не должны становиться придуманной
  непрерывной услугой. Resume label сохраняет принятую явную зону или закрытую
  фразу. Конкретный код проверки/ограничения ещё подлежит независимому ревью.
- Дальше обязательны причинный RED, настоящие producers → commit → новый
  PostgreSQL сеанс → renderer, rollback/повтор/отрицательные guards, профильная
  регрессия, независимое review/converge и governance-fast/macos-pr/pr-metadata
  точного нового SHA и проверенной основы. Отдельного допуска к деньгам,
  настоящей почте, GRAF Dev, выпуску или production этот отчёт не даёт.

### Точные контрольные суммы текущих требований

| Путь | SHA-256 |
| --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/development-process.md` | `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864` |
| `specs/140-user-account-billing/spec.md` | `9129a529803696308ad8c7c2ca8e2854c752f0daa12c91188b03a691f367dc38` |
| `specs/140-user-account-billing/plan.md` | `af915b52c60662f8fe7e1a8bc1af247db03e8ca6ea011ea8127fcdff6eab4b95` |
| `specs/140-user-account-billing/tasks.md` | `143e7310a8ec8082fd0efdce703c907f9ccd8b92d97f82a255bcdbd956418559` |
| `specs/140-user-account-billing/quickstart.md` | `92678b072305c6078935d6634b6c6f8527bdc0cb7696b5dbe5cc72cfc4207098` |
| `specs/140-user-account-billing/analysis.md` | `a2a9de4223bde8cd0ebbfeccfc76d268676c39ba42dd82c03cf83e9237a3a1cf` |
| `specs/140-user-account-billing/contracts/notifications-support.md` | `e6da1b00370c7219b45f4d381d2a391b4c5f163d2e0a0d4b8a33c1579b63f988` |
| `specs/278-production-billing/spec.md` | `d452d625cf5035edcdd144c34561aeb2c5d1a19c29826c61505801a3dd53e09c` |
| `specs/140-user-account-billing/data-model.md` | `cfc590a2085c40d925421f86055a2e6779c365e3c6bcb1c633d0eaed3c354e21` |
| `specs/140-user-account-billing/research.md` | `572a9ffc3a66e2146f22e6f6b74e204e67378cba25ff516b9d5561d2f5d6f871` |
| `specs/140-user-account-billing/contracts/billing-lifecycle.md` | `1d3e8fe3a672a34a4bc7a34bb6135800781d840e6e9350e0659bd142c5931ff7` |

Тесты, приложение и внешний runtime не запускались. Reviewer изменил только
назначенный checklist и этот отчёт; spec/plan/tasks/code/Git/GitHub не менял.
Список после записи перечитан: **8 отмечены / 0 открыты**. Выполнение всей
T048/#4903, T068/#4922, #7524 и публичный запуск этим результатом не приняты.
