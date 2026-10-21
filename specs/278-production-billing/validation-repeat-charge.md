# T035 — повтор обработчика продления

## Результат разработки

Активный срез F278/high-risk-product, ветка codex/278-repeat-charge-recovery от master `59ce47d54b6880138aceb7e619eaf472e34851fa`. Пользователь явно разрешил конкретное исправление, проверки и штатный выпуск; узкое исключение повторного полного чтения использует хеши документов и применимые разделы. Новые списания, настоящий provider POST и внешние письма запрещены.

Причина: общий charge_renewal_operation возвращал ORM-поля после rollback, который делает их истекшими. Сохранение immutable результата до rollback устраняет MissingGreenlet для обоих входов общей ранней ветки. Единственный рабочий вызывающий путь — фоновый worker; его защиту от повторной отправки не меняли. Цены, схема, сроки и полномочия не изменены.

## Фактические проверки

- Независимые требования: 6/6, scoped analyze CRITICAL 0 / HIGH 0, issue #7704; repeat-charge-review.md.
- PostgreSQL RED: 2 failed, оба unknown/noid и sent/knownid падают на исходном чтении после rollback.
- PostgreSQL GREEN: 122 passed, 0 failed, 0 skipped — существующие planner/renewal/workflow и два новых случая. Настоящий первый charge через MockTransport; повтор в новой AsyncSession/RLS возвращает прежний результат. Полные выбранные поля десяти таблиц неизменны, синтетический POST ровно один в каждом случае.
- Строгая изолированная цепочка PostgreSQL/Temporal: 1 passed, без перехвата MissingGreenlet. Потеря ответа → пустой поиск → поздний успех, настоящая отмена, три workflow/activity, три history replay, один новый grant, повтор duplicate не меняет выбранный снимок, recurring=false, authority сохранена. Синтетические HTTP POST1/LIST2/GET2. Это не наблюдение настоящей ЮKassa или календарного исполнения.
- Ruff check двух измененных Python файлов PASS; новый тест format-check PASS. Общий исходный renewal_charge.py уже имел отклонения format до правки; они не исправлялись массово и не заявляются как PASS. Governance и diff whitespace PASS.
- Использовано существующее Python окружение без установки зависимостей и отдельные одноразовые PostgreSQL/локальный Temporal. Журналы и безопасные результаты сохранены в ignored .dev/repeat-charge-20261022; приложение не менялось во время теста. Внешние API/списания/почта — 0.

## Контрольные суммы

- `postgres-red.log`: `ed666de307dfea75ba921d41fe45ca163599b3da93726cf220cf1f8463ba284f`
- `postgres-green.log`: `12a0baa740c16d3d7568b446b57d0f0b3f4f4c137908a7e161c18ad655de5b80`
- `recovery-green.log`: `8e6ca04b21da693b16e5e01909741b0a8fb8141ce558ee10adf05e03efa40710`
- `test_unified_recovery.py`: `55f3578c2f274ef0713bd7d86983e57a0bf9c4d0f868a8aa34ec872c0c73338e`

## Сверка реализации и границы

Сборка результата до rollback, обе PostgreSQL регрессии и строгая recovery-цепочка реализованы; новых buildable пробелов в этом узком изменении не найдено. Существующие релизные пункты T035 еще требуют точного PR SHA, трех обязательных checks, freeze/Full CI, CD и read-only production evidence. Это implementation ready, tracker pending; T035 пока не отмечается выполненной.

T026/T032, историческое ограниченное окно T030, живая календарная/почтовая/банковская приемка и ручная приемка всей F278 не закрываются синтетической проверкой. Неуспешный прежний тест настоящего тестового магазина сохранен. Новые реальные операции для этого выпуска не запрашиваются.

Legacy Impact: untouched; существующие общий helper, транзакции, provider client и тестовая инфраструктура сохранены. Новых alias/fallback/flag/dependency нет; legacy_new=0, unowned_legacy=0, expired_exceptions=0.
