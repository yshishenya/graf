# T113: независимая проверка кода source lifecycle

Дата: 30.10.2026. Проверяющий: `f273_release_boundary`.
Активная область F273/T113/#7804, `high-risk-product`.
Проверяемая база: `94e1d147bce2f90eb9bd4b16152e24d73964bc7d`, ветка
`codex/f273-local-period-20261029`; проверены незакоммиченные изменения
двух модулей и двух файлов тестов, перечисленных ниже.

## Состояние проверки

**SCOPED CODE PASS, P1=0, P2=0** в этой узкой области. Проверка кода завершена,
законченный общий профиль исполнителя прочитан, хеши всех четырёх проверяемых
файлов повторно сверены и не изменились. Это приёмка текущей правки по содержимому,
а не exact-SHA GitHub CI: изменения ещё не закоммичены.
Общая готовность, T113/#7804, выпуск и рабочее включение остаются **HOLD**.

Основание: независимый проект
`t113-source-lifecycle-design-review-20261030.md`, SHA-256
`0e27ab78860e3c4289f05a570e62c15977b67b1881d9d7e8c06d30a085ad08dc`,
и прочитанный отчёт исполнителя `t113-source-lifecycle-20261030.md`.

## Проверенные свойства

1. `_backup_lifecycle` 740–789 сохраняет одну read-only `REPEATABLE READ`
   transaction удержанного source-соединения. Проверяются maintenance session
   user, отсутствие SET ROLE, включённый row_security и допустимый context.
   Проверка closure policy и SELECT сохранена.
2. Перед чтением ledger фактически вызывается `local_retention_database_catalog`.
   Затем проверяются ровно одна точная ledger policy, ENABLE/FORCE RLS и SELECT
   (761–772). Предикат читается из существующего доверенного `rec-db-verify.py`,
   без второй копии строки. Неполная видимость не используется как пустой ledger.
3. `source_replay_accounts` 172–198 вызывает прежний `replay_accounts` и
   добавляет source-проверки. Подтверждены все границы scheduled/canceled/completed,
   в том числе уточнение `finalize_at <= purged_at`; противоречивые/просроченные
   незавершённые состояния дают отказ. Учебный `reconcile` не переведён на новый
   helper; прежние parser, stages, allowed scopes и ограничение имён сохранены.
4. Completed account с accepted допустим с authoritative purge-result.
   Category требует applied. Новое идемпотентное applied не приравнивается по
   времени/числу строк к исходному purge. Дополнительного product-stage правила
   или расширения v2 parser нет.
5. Фиксированный `EXISTS` 780–782 проверяет точный набор аккаунтов из полного
   доверенного снимка или всю категорию. Читается только булев результат,
   payload не выбирается. При любом остатке — отказ. Непричастные аккаунты
   не мешают подтвердить отдельное account-удаление.
6. После проверки повторно читается закрытый реестр. Возврат по-прежнему
   `(digest, raw)`; coherent caller передаёт root (1090) и сохраняет второе
   чтение register после dump/mirror (1124). Данные исходной БД не меняются.
   В digest дополнены catalog/policy и ограниченное наблюдение
   `applied_after_recorded_due`, `historical_deadlines="unverified"`.
   Это не подтверждение исторических сроков. Операции с исходными идентификаторами
   и байтами реестра остаются внутренними, наружу выдаётся контрольная сумма.
7. Безусловные ограничения общей готовности сохранены: bootstrap
   `infra/scripts/activation-operator.py` 341, и учебный replay
   `restore_replay.py` 321,348 по-прежнему выдают hold. Новый helper не пишет
   readiness, не включает writer и не расширяет учебный CLI на рабочие имена.

## Доказательства проверки

Независимый проверяющий читал исходники, diff и журналы; собственные тесты,
Docker, SSH, Dev или рабочие изменения не запускал.

- Причинный native RED на старом коде прочитан в
  `.dev/growth/t113-source-lifecycle-native-red-20261030.log`:
  повторно вставленная строка закрытого аккаунта дала `DID NOT RAISE`.
- `.dev/growth/t113-source-lifecycle-red-20261030.log`: 14 отказов из-за
  отсутствующего helper; это не 14 доказанных ошибок прежнего продукта.
- Два прочитанных законченных журнала `first`/`second`: каждый
  **16 passed, 56 deselected, 2 warnings**.
- Законченный `units-final`: **33 passed, 2 warnings**.
- Законченный общий `profile`: **365 passed, 37 skipped, 29 deselected,
  2 warnings**, 252.52с. Пропущенные/невыбранные проверки не считаются пройденными.
  По подтверждению исполнителя выбранный набор включает все 18 native coherent-copy
  сценариев, source matrix, прежний account и category replay. Предупреждения
  относятся к уже импортированной fixture и устаревающей связке Starlette/httpx.

Прочитанные законченные журналы закреплены SHA-256:

| Журнал | SHA-256 |
|---|---|
| profile | `b623bc358806394e6dd99e0c936fc1cbff46946150b0bf25f6dd3f27147f4b7e` |
| units-final | `70b8d0d5510d2aca6d7e7203e686133397bd9411ccd075d5460f4bbe0719d119` |
| first | `3a7b1cbd6baa4c85845b2566ca996a75eda5f3bedee68b11e96524631a35c5ef` |
| second | `8e343ff7f1ab50dd6cf5809f3fc8c4ffc7f3b1c0c3ab7cd51e0e6d816931e4b1` |
| native-red | `8ff8ac1a661d7c5f2ba129171d89432c67fa60499a7e991a33a838c2f36d1a3c` |

`git diff --check` выполнен независимо и прошёл. Ruff, governance и
development-process отмечены как пройденные исполнителем; проверяющий их
повторно не запускал. Исполнитель подтвердил отсутствие оставшегося тестового
bootstrap container; проверяющий Docker не вызывал.

Новая native matrix в integration test 841–980 использует настоящий finalizer,
503 запроса closure и оставшиеся данные. Она проверяет повторно появившуюся
account-строку, unrelated rows, неверную роль/context, изменение register,
restrictive/изменённую policy, NO FORCE/DISABLE RLS, отсутствие SELECT,
просроченный scheduled и category accepted/applied при остатках и пустой БД.
После обратимых подмен повторяется baseline и проверяется выход из transaction.
Unit-примеры проверяют временные границы и новый идемпотентный replay-case,
а также позднее applied без объявления deadline/full-readiness PASS.

## Привязка к проверенным файлам

| Файл | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py` | `5b8226d3972d5f2f2afec4621efc4e8093244c0c2d06e79b834f1bb76ce168cf` |
| `apps/server/src/twobrain_rec_server/product_analytics/restore_replay.py` | `d234d766417d1085e422aca9f889b6ae13feb72a5a2a3ad05270d543d8747eb4` |
| `apps/server/tests/unit/test_activation_restore_replay.py` | `c2ac7b77048f13552a4f8f7c43f869ab52372cc6f10a14bcb3cd8b683eda7ec6` |
| `apps/server/tests/integration/test_activation_restore_replay.py` | `d1cb4db2c1d66974e4491859e72e3136d0fa672db71d9afab026398bfd8a3711` |

## Перечитанные чек-листы

Перечитаны все 117 вопросов; markers не менялись. Это состояние качества
требований, а не приёмка рабочего измерения.

| Чек-лист | Отмечено | Не отмечено | SHA-256 |
|---|---:|---:|---|
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Baseline и затронутые требования сверены с design review; все хеши совпали,
правила повторного чтения F273 применены в прежней разрешённой области:

- constitution: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`;
- PRD: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`;
- status: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`;
- product-gates: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`;
- spec: `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2`;
- operations: `7d68aa7dc06b170508cd8b2858ede6e3e929b2e7155cd03b0895e715cb2b3abb`;
- activation-milestones: `9898007a0e87400246f8c95b899dd807fab0424472143e15338429873982f3f9`;
- реестр: `db4a05ada72b400520b8bfad8fc13796998793b4fe94f5ddc6205696eebd3ebe`.

## Граница приёмки

Проверены два существующих v2 scope. Проверка не принимает lifecycle остальных
локальных категорий, полноту всей истории обязательных решений, standalone
functions/RLS dependencies/jobs, весь верхний initial/verify/actual restore/resume,
T112, shell/CD или рабочий T0. Этот отчёт не закрывает T113/#7804/AC01–AC06,
не доказывает трафик/продажи и не является разрешением на рабочее включение.
