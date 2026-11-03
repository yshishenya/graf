# Независимый гейт требований: поправки резервных копий PR #7727

Дата: 23.10.2026. Проверяющий: `/root/f273_smoke_requirements_reviewer`.
Рабочая ветка: `codex/273-provider-smoke-recheck`.
HEAD: `e9a9929736c984df33469c7cccb0ee0278487074`.
Полоса: существующий высокорисковый срез F273, T116/T117.

## Решение и границы

**PASS качества требований; CRITICAL 0 / HIGH 0.** До реализации целиком
прочитаны новые разделы «Поправки PR #7727» в `contracts/operations.md:495`
и `plan.md:382`. Они достаточны для трёх ограниченных исправлений и проверок
ниже. Новый универсальный установщик, служба, bind или формат не нужны.

Перечитаны все вопросы четырёх reviewer-owned чек-листов, а не только прежние
итоги. Отметки сохранены: infra **25/0**, security **25/0**,
privacy-measurement **45/0**, requirements **16/0**; всего **111 отмечено,
0 открыто**. Это качество требований в назначенном срезе. Прежние записи
FAIL/PASS в истории чек-листов не переписаны. Реализация, реальные права
доступа, рабочие копии и восстановление не принимаются этим результатом.

Проверяющий изменил только настоящий отчёт. Код, спецификация, план, задачи,
Git/GitHub, приложение, реальные службы и рабочие данные не менялись.
Тесты, сеть, установки, выпуск и развёртывание не выполнялись.

## 1. Один явно выбранный GID во всех трёх службах

`operations.md:497–505` и `plan.md:388–392` требуют один и тот же числовой
`TWOBRAIN_RUNTIME_SECRET_GID`, явно выбранный для API, в существующих
`/etc/graf-posthog-{runtime-guard,backup,retention}.env`. При смене выбранной
группы установочный шаг повторяется. Подмена выбранного значения на1001
и надежда на переменную shell перед `systemctl start` прямо запрещены.

Фактические существующие источники подтверждают достаточность этого пути:

- `infra/docker-compose.yml:9–10` передаёт API дополнительную группу из этой
  переменной; три существующих bind состояния на строках191–193 доступны
  API только для чтения, включая retention. Нового bind не требуется.
- Три существующие service читают отдельные `EnvironmentFile` с теми же
  именами. Писатели guard/backup/retention уже используют выбранную группу
  для каталога2750 и результата0640. Архивы остаются закрытыми от API.
- Runbook описывает отдельную установку systemd в `/usr/local/libexec` и
  `/etc/systemd/system`, затем daemon-reload/включение. Поэтому обязательный
  исполняемый блок в том же штатном пути достаточен; синхронизация через CD
  или новый общий установщик не является необходимым условием исправления.

Требование сохраняет остальные параметры каждого существующего env-файла,
root ownership и0600, применяется до запуска служб/включения timers. При
дальнейшей реализации все существующие пути запуска должны направлять к
этому шагу; более ранняя инструкция установки guard не должна оставлять
обход обязательной подготовки. Примеры должны явно назвать переменную,
а не только полагаться на молчаливое значение по умолчанию.

Приёмка задана исполнимо: выполнить именно штатный блок на временных путях
с нестандартным выбранным GID, проверить все три результата, сохранность
посторонних строк, отсутствие дубликатов/старого выбранного значения и отказ
до запуска служб при отсутствующем/неверном GID. Подстановка install в тесте
позволяет проверить путь без root/systemd на Mac. Это локальная проверка
конфигурации; реальная читаемость API и установка требуют отдельного receipt.

Связанные вопросы: infra CHK004/006/009/025, security CHK002/022,
privacy CHK032/034/039/044, requirements: однозначность, границы,
зависимости, проверяемость и полнота отрицательных сценариев.

## 2. Владение временным каталогом текущей попытки

`operations.md:507–511` и `plan.md:393–395` однозначно ограничивают очистку
каталогом staging, который текущий процесс действительно создал после
получения существующей backup lock. Владение возникает после успешного
mkdir. Уже существовавшие incomplete/final и исторические повреждённые
наборы сохраняются. После rename обработчик отказа не удаляет final.
Ошибка очистки остаётся видимой и не может стать PASS.

Это минимальная коррекция существующего `fail_backup`; новые рекурсивные
обходы архивного каталога или удаление по возрасту из требований не следуют.
В коде сейчас нет такой очистки: при archive failure обработчик публикует
failed state/alert, а staging остаётся. Существующий тест
`test_failed_archive_does_not_publish_complete_set_or_rotate` проверяет лишь
отсутствие ротации/публикации. Его прежний PASS не доказывает очистку.

Текущий Docker harness пишет синтетический архив в временный путь. Для
регрессии требуется отказ после появления байтов, проверка удаления только
собственного staging, сохранность заранее созданного чужого staging и
final/history, а также отказ удаления. Коллизия до mkdir и отказ после
rename должны сохранить уже существующий/опубликованный final. Эти сценарии
соответствуют новым требованиям, не разрешают очистку настоящих архивов.

Связанные вопросы: infra CHK004/005/009, security CHK010/012/013/014,
privacy CHK034/035/036/044, requirements: границы/отрицательные сценарии.

## 3. Единый текущий префикс проекта без изменения исходного inventory

`operations.md:513–517` и `plan.md:396–398` требуют одинаковое преобразование
стандартного первого префикса `graf-posthog_` в префикс настроенного
`GRAF_POSTHOG_PROJECT` при discovery и в `verified_sets`. Уже существующий
`posthog-storage.py` применяет такое преобразование к шаблонам. Исходные
байты inventory, их копия в комплекте и SHA-256 не переписываются.

Текущий backup ищет старые шаблоны в discovery и проверке комплектов;
тест `test_backup_counts_only_copies_of_current_scope[project]` даже ожидает
успех нового проекта со старыми `graf-posthog_` томами. Это ошибочная
положительная проверка; она должна стать отрицательной. Положительная
проверка нового проекта должна использовать его настоящие имена и доказать
согласованность discovery/публикации/verified_sets при неизменном raw digest.

Исторические наборы с другим project/inventory/volume set остаются нетронутыми
и не считаются текущими. Проверки всех обязательных классов, неизвестных
томов по Compose label и фактическим mount, полноты manifest/архивов и
двух копий до готовности сохраняются. Восстановление/согласованность
PostHog этим изменением не доказываются.

Связанные вопросы: infra CHK001/004/005/008, security CHK022,
privacy CHK033/034/039/043/045, requirements: зависимости/приёмка/границы.

## Процесс и остающиеся ворота

Назначение соответствует открытым T116/T117; новых продуктовых решений и
поправки конституции не требует. Конституция IV/VI, scoped risk/process,
ограничения данных и tracker/release gates сохранены. До кода остаются
scoped analyze и диагностические регрессии, затем локальные проверки,
независимое code review/converge, три обязательные проверки точного SHA/base
и обычное слияние. Заменяемые PR #7721/#7723/#7725 допустимо закрывать с
объяснением переноса только после принятия #7727. Ни #7697, ни полные
T116–T119, T097, правовые/операторские критерии и production не закрываются.

## Проверенный снимок SHA-256 до реализации

| Файл | SHA-256 |
| --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/tracker-policy.md` | `06450200cabdef48000af51241564e9ee9e8d36b50c71e06a88f8c50b7365466` |
| `docs/agent-guidance/release-and-validation.md` | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| `specs/273-paid-traffic-analytics/spec.md` | `c6b318125e90cd19018f43cecc8fced90bb22ee3e5340849d81189e520e081da` |
| `specs/273-paid-traffic-analytics/plan.md` | `5e146b8dfa0fabdce6e565e7d80cc190e5e88a68b55b5eedc7c71f138dee2efa` |
| `specs/273-paid-traffic-analytics/tasks.md` | `309ff1e7d90893aac582ef390f3280b0acd116601fb2742c94db0ed5097c455d` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `deb057ca6722fac7dbab56fd8ecbc6dc71076977cc65c2dadeacb62b8f8c4676` |
| `specs/273-paid-traffic-analytics/contracts/operations.md` | `9cbd4fc9851f26ac676b92d1549e8f1a9bf02648d977f3382de6e03a04563759` |
| `docs/analytics/product-analytics-posthog-runbook.md` | `f217e8f19ff75abacc4aa73d1a32f3a59faea6c7acdde95f29c5bc95b78cc00d` |
| `infra/scripts/backup-posthog.sh` | `4021df17f0f335ec709a317c82eebea193063e5c6eea8c00c8f42d0c3c1ba6a5` |
| `infra/scripts/posthog-storage.py` | `cf28e72be43b2b887d694ff15a958d276677a30338ca3ba8cb294101410c46d1` |
| `infra/scripts/posthog-runtime-guard.sh` | `144884c16255ffe9b87d2c08cb2413f0d525fc33a6ace1650e46f72678d8bfaa` |
| `infra/scripts/enforce-product-analytics-retention.sh` | `ab367e1af976707fbc8cff91368e7fbba3b7308db0b2ae856de904587e2a6dcd` |
| `infra/docker-compose.yml` | `610bc756230f2762f20c5a59c6887e2b9496d06a69256a8cbd5b5e6fb83445d6` |
| `infra/posthog/backup.env.example` | `9bbcace7572daef8c91406d6ef1d923efe7b01ea5228073439ea0a53ec629ffd` |
| `infra/posthog/retention.env.example` | `4fa242e52b6cf5218aa4c475b867335d32dee4820d87a9bd8f767b857df93081` |
| `infra/posthog/runtime-guard.env.example` | `4cf64267a3bb93f91337aca70e2a6d2fd03b4358b262fa8a0412d1e4ca3de272` |
| `infra/posthog/graf-posthog-backup.service` | `8c10724404ce0b0b5594884fa923ee86e2ba125e379f88e2489ef3c5f36b7dcf` |
| `infra/posthog/graf-posthog-retention-enforce.service` | `0430c51e9a1d94d7e5b86985fc397a4c8a1158214726ff202ffd504c4790e826` |
| `infra/posthog/graf-posthog-runtime-guard.service` | `677b6d6612e135d0339e0a7286386f9c1846fefaccb6ecf6419ca6c5c47782d0` |
| `apps/server/tests/contract/test_analytics_retention_enforcement.py` | `f4792c36ae30b63fc6e02b7c2be20017f40093f4b11465ce3baada24b306ab57` |
| `specs/273-paid-traffic-analytics/checklists/infra.md` | `c3ef10636f4fd977cca6231b7ba2e1396f026ce8d58fc08d7eef5f071e67207b` |
| `specs/273-paid-traffic-analytics/checklists/security.md` | `0db087da3daeaa31a2cb8ca3e5d24b4363111881ed391098e062c03118249921` |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | `00a31550d0ab58f06f2712434bf915119095f3c77ca7dc099cb3c79f83513f4f` |
| `specs/273-paid-traffic-analytics/checklists/requirements.md` | `2c4a91701de2dcdb377f758064216125098bdc752e616115deb2bdb6a2607f9d` |
