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
