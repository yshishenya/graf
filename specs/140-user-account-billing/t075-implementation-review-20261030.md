# Независимая проверка F140/T075 — 2026-10-30

## Текущее решение

**Требования первой части операторского импорта B1–B3: подтверждены, 10/0.**
**Реализация: ещё не проверена; приёмка кода не выдана.**

Основа: `eed85acee40613165d79c39313b454cb4421c9aa`, ветка
`codex/140-registry-implementation`, активный указатель F140/T075.
Полоса реализации — `Active Spec Kit slice` с проверками высокого риска
для PostgreSQL, полномочий и финансовых данных. Данный проход — независимое
чтение и документальная фиксация границ, без тестов/БД или GitHub mutations.

## Подтверждение действующего ограниченного решения

Полностью перечитаны контракт `registry-operator-import.md`, действующий
отчёт `t075-import-design-review-20261030.md`, все восемь reviewer-owned
checklist и применимые правила reviewer gate. Проверены действительные
проверки роли в `billing/database.py`.

Независимый пересчёт даёт IMP001–IMP010: **10 отмечены / 0 открыты**.
Все 39 контрольных сумм входов из прежнего отчёта совпали с текущими файлами.
Это проверка неизменности входов, а не замена собственного чтения и не
доказательство поведения продукта. Все исходные 220 CHK-строк буквально
совпали с основой `847ccc82e7b2180a8c38f8769bc67ff39a342c8b`;
ни одна исходная формулировка/отметка этим проходом не меняется.

- B1: один внутренний CLI, реальная maintenance DB identity до чтения CSV
  и store access; две общие таблицы с узкими ENABLE/FORCE RLS; существующий
  workspace audit не ослабляется.
- B2: один явно ограниченный русский UTF-8 CSV профиль, обязательные поля,
  имя/шапка/дата/footer, точные RUB-суммы, уникальность внутри kind,
  multipart/last и различение пустоты/отсутствия; ограниченное чтение.
- B3: канонические hashes, scope lock, неизменяемый receipt, replay,
  сравнение текущего digest при замене, атомарные owned gaps с неизменным
  сроком и историей восстановления. Ошибка сохраняет прежний accepted набор.

Новых противоречий в этих десяти требованиях не обнаружено.
Это подтверждает сохранение предметного design gate и не заменяет обязательный
текущий анализ перед реализацией. Исторический `analysis.md` от 11.08.2026
не принимается как новый clean analysis: его 80/7 и завершённая T075 устарели.

## Общие контрольные списки

| Файл | Отмечены | Открыты |
| --- | ---: | ---: |
| `launch-readiness.md` | 32 | 8 |
| `operations.md` | 10 | 8 |
| `payments.md` | 14 | 6 |
| `post-plan-readiness.md` | 24 | 16 |
| `product-market-2026.md` | 35 | 5 |
| `requirements.md` | 16 | 9 |
| `security.md` | 11 | 6 |
| `ux.md` | 16 | 4 |
| **Всего** | **158** | **62** |

Глобальный PASS не выдан. Прежние X4–X7 и внешняя приёмка других частей
F140 не закрываются. F199/F272/F278 и конституционная граница Krisp
не возвращаются к прежнему поведению ради исторических пунктов списка.

## Следующая проверка реализации

После готовности diff отдельно прочитать весь изменённый код и вызовы;
проверить guard-before-read, реальные RLS/grants и inventory, ограниченность
ввода, содержательную CSV-валидацию, канонизацию, replay и current replacement,
атомарность и поколения gaps, сроки и безопасный вывод. Для положительной
приёмки необходимы фактические доказательства CLI → изолированная PostgreSQL →
новый процесс/status, отрицательных входов, конкуренции и отката.

В момент этой записи рабочее дерево до создания отчёта было чистым.
Готового diff и новых runtime-доказательств реализации ещё не было.
Самостоятельно тесты, БД, приложение, сборки, реальные платежи, Git/GitHub,
коммиты, выпуск или развёртывание reviewer не запускает.

`files_complete=true` обязан сохранять `financial_status=not_checked`.
Полная CSV ↔ authenticated provider API ↔ ledger сверка остаётся обязательной;
T075/#4930 остаются открытыми. Windows/F200, F254, GRAF Dev и production
не входят в этот проход.

## Прочитанные источники текущего прохода

Повторное чтение `AGENTS.md`, карты guidance, `document-reading.md`,
`development-process.md`, `spec-kit-flow.md`, `product-gates.md`, конституции,
`spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, трёх применимых контрактов
и нового registry-контракта проведено непосредственно. Все восемь списков
и scoped design review прочитаны полностью. Исторический `analysis.md`
прочитан как история; другие подсистемы и всё состояние продукта не принимаются.
Продуктовая основа и общий текущий статус не объявляются заново полностью
перепроверенными этим узким подтверждением design gate.

| Путь | SHA256 |
| --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/development-process.md` | `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `specs/140-user-account-billing/spec.md` | `964fa33382fa5f04940349f7e27eb1e1aab9b453397a568985f1b0d5f79f9a88` |
| `specs/140-user-account-billing/plan.md` | `5a78f4a17c78ae60922cddfe9804a5b285f30f60428bc21b6094397347f0882c` |
| `specs/140-user-account-billing/tasks.md` | `2cdccb7df2c8d0686be3dc83a21c8d1ea3c93be4899f40563101fbfce6214599` |
| `specs/140-user-account-billing/quickstart.md` | `f1b1c37dc92dc91c373cc461e9d9c7e41944ffbd049eac4a1d362ae3080778e7` |
| `specs/140-user-account-billing/contracts/registry-operator-import.md` | `297bfe6c3acb063d70a6ef634c287a901fc9c342549270eaeec2c15a35c5b0a5` |
| `specs/140-user-account-billing/contracts/operations-reconciliation.md` | `a3a1917b91e0370b0ef477519509c0333ec8701aa4ae7803ed6685022c7a1cba` |
| `specs/140-user-account-billing/contracts/security-privacy-compliance.md` | `38934189b91e33a070b49e61673020d41530eec3d06a4fad5bd00f3317071cfc` |
| `specs/140-user-account-billing/contracts/yookassa-integration.md` | `4524a7cb83b8dd9c3a24a70e162b54480ac602c63c03027980428987254740ae` |
| `specs/140-user-account-billing/t075-import-design-review-20261030.md` | `a93089f54f488a70421e7b66276d7140ff9dab4f94013d1e497977beaaa61d4a` |
| `specs/140-user-account-billing/checklists/launch-readiness.md` | `99268dc6ac32dab5bce0bb1303bcd26cd412a0feb9edbca2f395eb94e1d3ade5` |
| `specs/140-user-account-billing/checklists/operations.md` | `ed75a8c7f5c89cbc651894d08380a48058cba42bcb30475e04089a870460c665` |
| `specs/140-user-account-billing/checklists/payments.md` | `97b99ab9956295248ae10252a28afd13c3e7311dd387d7eec8e5e43f315238f5` |
| `specs/140-user-account-billing/checklists/post-plan-readiness.md` | `ef0fe6b8090d7a8669e45660b8bd91669d6c093ab5b790ed81ab10b74e13e74d` |
| `specs/140-user-account-billing/checklists/product-market-2026.md` | `982a90af611b4a81447198b4a1c71cf918aef198fcf1e73971ce693c65e3756d` |
| `specs/140-user-account-billing/checklists/requirements.md` | `8ec25571fd0a01a36c405cf9fc9823e5329218e4f738da2c63074c9a2f321898` |
| `specs/140-user-account-billing/checklists/security.md` | `e1210f57cdb45dd5a5599a766a332380e61e601357cd40cb69ef1be117aa5b31` |
| `specs/140-user-account-billing/checklists/ux.md` | `1eb1c6e68689fbdc7bf99746a04320c895c2b1ca6ab8b40efb10609e54bee126` |
