# A8 image reuse requirements review

Owner: independent reviewer. FR-044–048 / SC-021, T068–T071. Implementation may not mark review items.

Текущий результат: **PASS, 5/5** после независимой повторной проверки требований 2026-09-13. Реализация и production validation этой отметкой не подтверждаются.

- [x] CHK001 Are dependency/package/FFmpeg equivalence and actual cache verification explicit without adding a registry or weakening Full evidence?
- [x] CHK002 Are previous source/container/one-off identity, external refs, platform and missing-image refusal complete before mutation?
- [x] CHK003 Are retry, immutable overrides, helper availability after reset and interrupted-attempt handling clear?
- [x] CHK004 Are downgrade/compatibility/previous rollback, all smoke paths and existing backup/dispatch safeguards preserved?
- [x] CHK005 Are executable negative lifecycle checks, actual image validation, live dry-run/release boundaries and owned task paths complete?

## Первичная независимая проверка требований — 2026-09-13

Проверено: FR-044–048 / SC-021, A8 plan, T068–T071, A8 acceptance; сопоставлены действующие CLI/rollback договоры и требования конституции к deployment. Это проверка качества требований, а не готовности кода или production. Владелец реализации не меняет отметки.

Первичный результат: **требуются уточнения, 2/5 принято**; замечания закрыты повторной проверкой ниже. Архитектурный выбор уже согласован: два локальных образа, без registry, новых служб и полномочий; повторного решения пользователя не требуется.

- CHK001: FR-044 и SC-021 задают сохранение dependencies/resources и reuse после source-only изменения; A8 quickstart вместо этого требует `source-SHA-only build`. Изменение только label не доказывает, что реальное изменение приложения сохраняет dependency/FFmpeg cache и обновляет упакованный код. Нужны два явных случая: новый SHA при прежних байтах и настоящий source-only diff, с проверяемым изменением application output при прежнем наборе dependencies/resources. [Consistency, Spec FR-044 / SC-021; Quickstart A8]
- CHK002: принято по FR-045/046 и plan A8.2–3: предыдущие реальные контейнеры, labels, one-off migration, old/new external refs, platform и отказ при отсутствующем образе описаны до изменения runtime. [Completeness, Spec FR-045 / FR-046]
- CHK003: plan A8.6 говорит закрывать `failed/recovered attempts`, тогда как FR-047 связывает обычное повторение с успешным/откаченным мягким выходом. Не определено, что происходит после мягкого сбоя, если rollback либо восстановление public download не удались. Нужна явная граница: новый attempt разрешён после подтверждённого неизменённого runtime либо подтверждённого восстановления; неизвестное/неуспешное восстановление сохраняет baseline и блокирует повтор до recovery. Сам факт исполнения EXIT trap не подтверждает rollback. [Ambiguity, Spec FR-047 / FR-048; Plan A8.6]
- CHK004: принято по FR-048 и plan A8.5–6: downgrade и compatibility используют candidate, настоящий rollback использует previous, smoke/cleanup получают override, существующие gates остаются обязательными. [Consistency, Spec FR-048]
- CHK005: для нового сохраняемого state отсутствует приёмочный сценарий disk-full/ошибки атомарной записи. Конституция требует disk-full behavior для deployment. Следует явно описать отказ подготовки до stop при невозможности сохранить baseline/helper/override и состояние после ошибки записи итогового результата: не выдавать `deploy_result=pass` и не разрешать затереть незавершённую попытку. Добавить эти случаи в исполняемые lifecycle tests. [Gap, Constitution Development Workflow And Quality Gates; Spec FR-047 / SC-021]

До clean analyze также согласовать действующие формулировки `research.md` Decision 6 и `contracts/ci-cd-cli.md` о неизменности production build/rollback с явным A8; старые решения можно обозначить историческими, сохранив их факты. A8 не требует изменения авторитетного Full или нового registry-проекта.

После устранения этих пунктов reviewer повторно проверяет только уточнённые договоры и обновляет оставшиеся отметки. Затем — analyze и issue sync, до implementation.

## Повторная независимая проверка — 2026-09-13

Повторно рассмотрены только изменённые FR-047 / SC-021, plan A8.6, quickstart A8 acceptance, research Decision 6 и A8 extension в contracts/ci-cd-cli.md. Первичные CHK002/CHK004 сохраняют приёмку; новые решения о registry, инфраструктуре или полномочиях не требовались.

- CHK001 — принято: SC-021 и quickstart теперь различают новый SHA при прежних исходных байтах и реальное source-only изменение с проверяемым новым application output. Для обоих явно сохраняются dependency/FFmpeg cache и distributions/resources. [Consistency, Spec FR-044 / SC-021; Quickstart A8]
- CHK003 — принято: FR-047 и plan A8.6 разрешают новую попытку только после подтверждённого неизменённого runtime либо успешного восстановления обязательных gates, включая public download. Неуспешный rollback, compatibility/forward-fix и неизвестное состояние оставляют baseline блокирующим до recovery; EXIT trap не заменяет доказательство. [Clarity, Spec FR-047; Plan A8.6]
- CHK005 — принято: FR-047, SC-021 и quickstart включают disk-full/ошибку записи до stop и отказ сохранения итогового результата. Последний не выдаёт deploy_result=pass и не снимает блокирующее состояние attempt. Оба случая входят в исполняемую lifecycle acceptance. [Completeness, Constitution Deployment Gates; Spec FR-047 / SC-021; Quickstart A8]
- Согласованность границ — принято: research Decision 6 явно помечен историческим, а CLI contract отдельно описывает локальное расширение A8 при сохранении исходных safety gates и авторитетного Full. [Consistency, Research Decision 6; Contract A8 local image identity extension]

Итог: **PASS 5/5, открытых замечаний проверки требований A8 нет**. Следующий обязательный шаг — clean analyze, затем issue sync и реализация T068–T071. Исполняемые и реальные image/cache проверки остаются задачами реализации; этот review их не запускал и не объявляет выполненными.

## Независимая проверка требований T097 — 2026-09-15

- [x] CHK006 T097 разделяет сохранение опубликованного runtime PKG и начальную установку отсутствующего файла; определяет источник download smoke, сохранность при rollback, отказы invalid/symlink/owner/write и отдельные границы публикации, clean Git, exact-SHA CI/Full.

**PASS требований T097, CHK006: 1/1.** Режим: независимая проверка требований
действующей high-risk F211, ограниченная запись reviewer evidence. Основание:
HEAD `3325f366951bf871edf6cce9f1901bd45c2883d3` и текущие дополнения
`spec.md` (Release convergence / Clarify T097), `plan.md` и T097 в `tasks.md`.
Эта отметка не подтверждает реализацию, production-состояние или прохождение
тестов и не закрывает T097.

- **Сохранение:** существующий обычный непустой runtime `graf.pkg`, прошедший
  проверки пути и каталогов, сохраняет свои байты. Отличие от tracked source
  не является основанием для копирования. Для download smoke выбирается этот
  runtime-файл; CD не создаёт для него rollback backup и не отмечает его
  обновлённым. Последующий `restore_public_download` не удаляет и не заменяет
  сохранённый PKG. Это задано FR-010/048 и Clarify, без новой схемы state.
- **Начальная установка:** только отсутствие target допускает прежний
  источник из репозитория и существующие `mktemp/install/cmp/mv` с режимом
  `0644`. При восстановлении исходно отсутствующий файл вновь отсутствует.
  Ошибки подготовки/записи/сравнения/перемещения не становятся PASS; очистка
  временного файла и сигнал о неудачном restore остаются в прежнем договоре.
  Существующая ветка `public_download_restore_failed` продолжает блокировать
  подтверждение восстановления и завершение release-image attempt.
- **Недопустимые пути:** symlink, включая dangling link, отвергается до
  толкования target как отсутствующего. Пустой обычный target, каталог или
  иной тип не заменяется исходником автоматически. Существующие проверки
  source, runtime directory, target directory и владения каталогами
  сохраняются. Требование owner относится к прежним directory guards;
  новый механизм назначения прав или смены владельца не требуется.
- **Исполняемая приёмка:** настоящий извлечённый Bash helper и временная
  файловая система уже используются в существующем `public_installer` блоке.
  Новый случай обязан сравнить независимо заданные байты/hash runtime до
  вызова, сразу после `sync` и после `restore`, при отличающемся source.
  Только `cmp target source` недостаточно после выбора target как source;
  прежняя проверка лишь после restore также пропускает временную подмену.
  Сохранённые состояние `updated=0`, отсутствие backup и выбор runtime для
  smoke должны быть проверены вместе с прежними bootstrap/restore случаями.
  Отрицательная матрица охватывает пустой/необычный target, ссылки, неверного
  владельца каждого проверяемого каталога и ошибку записи при initial copy.
  Это уточняет способ доказать уже записанные требования, не расширяя scope.
- **Публикация и Git:** только штатный оператор macOS публикует новый пакет
  в runtime-каталог; server CD не является повторной публикацией. Tracked PKG
  больше не изменяется публикацией. Уже изменённый production tracked файл
  восстанавливается отдельно после сохранения его bytes и сверки с digest
  опубликованной версии; проверки clean worktree не обходятся и не ослабляются.
  Эта рецензия не проверяла фактические bytes версии `.3` на production.
- **Границы доказательства:** выбор существующего файла для download smoke
  доказывает обслуживаемые байты, но не заменяет Developer ID, notarization,
  staple, Gatekeeper, Sparkle и public/installed приёмку. FR-010/048 и T097
  сохраняют required CI на новом окончательном SHA, один авторитетный Full,
  dry-run, public hashes и дальнейшие gates выпуска. Согласование инструкций,
  quickstart и фрагмента явно принадлежит реализации T097.

Прослежены `sync_public_download`, `restore_public_download`, download smoke,
ветка failed restore и существующие реальные filesystem-тесты. Проверены
действующие правила deployment/public distribution. Блокирующих пробелов или
противоречий в требованиях T097 не найдено. Изменён только этот reviewer-owned
checklist; код, другие документы, GitHub, тесты, сборки и production не менялись
и не запускались в рамках проверки.

## Повторная проверка требований T097 — свежесть публичной ссылки — 2026-09-15

- [x] CHK007 Дополнение T097 задаёт обновление SHA URL после атомарной замены canonical PKG без перезапуска API; сохраняет ограниченный кэш неизменных файлов, проверку old/new HTTP cache headers и прежние границы публикации.

**PASS требований дополнения T097, CHK007: 1/1.** Прочитаны обновлённые
spec/plan/tasks, исходный `public/templates.py`, его вызов из download template,
подключение `VersionedPublicStaticFiles` и существующий integration-тест.
На момент проверки cache-код совпадает с HEAD
`3325f366951bf871edf6cce9f1901bd45c2883d3`; изменения runtime helper и его тестов
принадлежат основному исполнителю и этой рецензией реализации не принимаются.
Прежний PASS требований CHK006 сохраняется.

- Требование отделяет дешёвую проверку filesystem identity от вычисления
  SHA-256: публичная функция каждый раз получает текущий Path/stat, один
  существующий расчёт сохраняет `lru_cache(maxsize=32)`. Ключ включает путь,
  device, inode, size, mtime и ctime; временные поля следует передавать с
  доступной точностью `st_mtime_ns`/`st_ctime_ns`, без округления до секунд.
  Формат URL и первые 12 hex SHA-256 сохраняются. Отсутствие файла не должно
  превращаться в прежний успешный cached URL.
- Атомарная замена другим файлом того же размера с восстановленным mtime
  должна обновить результат благодаря остальной identity. При неизменном
  файле повторные вызовы не перечитывают его bytes для вычисления hash.
  Отдельный read counter проверяет именно вычисление версии, не неизбежное
  чтение файла HTTP-сервером при скачивании. Проверка выполняется без cache
  clear или пересоздания процесса между публикацией и новым обращением.
- Действующий `VersionedPublicStaticFiles.get_response` уже сравнивает query
  `v` с результатом этой функции. Требуемая новая ссылка получает текущие bytes
  и `public, max-age=31536000, immutable`; обращение по прежней версии к тому
  же canonical path получает текущие bytes с `no-cache`. Настоящий ASGI-запрос
  должен проверить headers и bytes после замены, а не только строки в source.
  Это договор ответов сервера, без нового механизма очистки внешних кэшей.
- Старый integration-тест явно утверждает неизменность URL после replace.
  Plan правильно заменяет именно это ожидание независимым hash новых bytes;
  сравнение лишь двух разных строк не доказывает их связь с содержимым.
  Оба текущих вызова `public_static_asset_url.cache_clear()` найдены только
  в этом блоке и могут следовать новому месту существующего LRU. Очистка
  остаётся подготовкой/уборкой теста, не способом исправления production.
- Scope ограничен public helper и указанной приёмкой: download template
  использует `public_static_asset_url('downloads/graf.pkg')`, cabinet helper
  не участвует в вычислении версии PKG. Cabinet cache, продуктовые маршруты,
  форматы release state, Apple/Sparkle и clean Git правила не меняются.
  Новый актуальный SHA, required CI/Full и публичная проверка остаются T097.

Блокирующих пробелов или противоречий в этой дельте требований не найдено.
Режим — независимая проверка требований действующей high-risk F211. Изменено
только это reviewer-owned дополнение; cache/runtime-код, другие документы,
commit, GitHub и production не менялись, тесты не запускались. Текущий
production digest и переданные результаты runtime-тестов здесь повторно
не проверялись и не объявляются evidence этой рецензии.

## Независимая проверка реализации T097 — 2026-09-15

**PASS реализации T097; блокирующих замечаний нет.** Режим: независимая
проверка действующей high-risk F211 с записью только reviewer evidence.
Основание: HEAD `776a68920ec9e2371a178192189a98f678b56b07` и текущий diff
runtime helper, public cache и существующего integration-теста. Сопоставлены
FR-010/FR-048, Clarify T097, plan/tasks и принятые CHK006/CHK007.

- Существующий обычный непустой target проходит прежние проверки source,
  каталогов и владельцев; затем становится public_download_source без
  копирования, backup и public_download_updated. Последующий restore его
  не меняет. Отсутствующий target сохраняет прежние mktemp/install/cmp/mv
  и удаление при rollback; write failure очищает временный файл. Пустой
  target, каталог, symlink/dangling и неверные владельцы дают отказ.
- Прослежены sync перед запуском API, проверка скачанного SHA по выбранному
  source, restore перед восстановлением runtime и обязательный повтор
  download/health gates перед подтверждением recovery. Отказ restore
  по-прежнему не запускает предыдущий API и не подтверждает recovery.
  Docker mount обслуживает runtime/public-downloads; шаблон /download и
  VersionedPublicStaticFiles используют один публичный URL helper.
- Обёртка cache каждый раз читает Path/stat, а существующий ограниченный
  LRU учитывает filename, путь, device/inode/size/mtime_ns/ctime_ns.
  Изменение файла получает новый SHA URL; отсутствие файла не возвращает
  старый cached success. Формат URL, 12 hex SHA и maxsize=32 сохранены.
  Cabinet cache, release state, Apple/Sparkle и production guards не меняются.
- Исполняемые проверки используют настоящий Bash/filesystem и ASGI:
  сохранение отличного от source PKG до/после restore, initial copy/rollback,
  отказ записи с уборкой, девять invalid-path/owner случаев; атомарная
  замена при том же размере и mtime без cache_clear между запросами.
  Ожидаемые SHA вычислены независимо, обе HTTP ссылки возвращают новые
  bytes; прежняя получает no-cache, текущая — immutable. Счётчик чтения
  подтверждает один расчёт на версию и отсутствие лишнего хеширования.
- Просмотрены сохранённые журналы: cache regression до исправления —
  1 FAIL; связанный полный набор deployment readiness и public landing —
  59 PASS / 1,48 с; отдельные invalid-path/owner — 9 PASS / 0,25 с.
  Это результаты исполнителя из /tmp/graf-t097-cache-red.log,
  /tmp/graf-t097-cache-green.log и /tmp/graf-t097-owner-green.log.
  Reviewer тесты повторно не запускал.

Проверенные SHA-256:

- infra/scripts/cd-remote-runtime.sh:
  `f1c0419cca948cdc13172143d9d9c09f4d35e1bc27f75ff945468cb7d5d5ce53`.
- apps/server/src/twobrain_rec_server/public/templates.py:
  `c7b1d96cb6afcb9f631cc4c566204e636946bf9948b63f9284422da6ad5d0b30`.
- apps/server/tests/integration/test_deployment_readiness_gates.py:
  `959c577afa853de8abd84c8f6263cd502c74535f320dfbd5ee8916ca3e4fe4b9`.

Изменена только эта отдельная секция checklist; прежние отметки сохранены,
T097 не закрыта. Код, другие файлы, GitHub и production reviewer не менял.
Согласование публикационных инструкций, итоговые exact-SHA CI/Full и реальные
public/package/feed hashes остаются отдельной приёмкой основного исполнителя.
