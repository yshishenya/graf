# F296 parity в F200: авторская подготовка и границы review

Дата:2026-11-16. Lane: `high-risk-product`, requirements preparation only.
Владелец разрешил подготовить существующие F200 spec/plan/tasks/quickstart,
контракт и новый непроверенный checklist; production/VM/Git/issues не разрешены.
Это авторский отчёт о подготовке, не независимый requirements/source GO.
`validation-2026-11-16-stock-ffmpeg-native.md` принадлежит Main и не редактировался.

## R12: переданный результат

Proposal `.dev/t116-short-oracle-r12-proposal-20261116.patch`1836B,
SHA256 `1c519e535aeadc2d3e442847ecf5cc1b1f802d845b0fc5818430ddbf25b42ac9`
не изменён. Два hunks только protectedShortMediaEngine:30ms raw3072/container300000,
10ms raw2048/container100000 и один comment «Pinned stock encoder regression».
Предыдущая in-memory apply/reverse проверка подтвердила0других изменений:
negative same-bytes declaration10ms/hook/native error, zero-container exact1024,
input/EOS/flags/time/bounds и lifecycle/owned baseline сохранены. Опора — реальные
R7 JUnit counts/containers и R10 actual render; новое native execution не запускалось,
exact decoder/presentation gate остаётся UNKNOWN, fabricated PASS нет.

На начало этой подготовки tracked integration TU имел SHA256
`57d72b129f01de954433e46e3235f489607df86283fb7166f47309f7d642e06d`.
При заключительном чтении он стал
`04229c17246c2d5234266411ad7951ba57ed4282378686961b59f750550f87b5` — ровно ранее
вычисленный результат применения proposal. Эта внешняя mutation не сделана
данным автором; не объявлять прежний TU pin текущим или приписывать её этому
документальному изменению. Кто применил/текущий freeze и native evidence — Main.
Файл patch остаётся review artifact, его наличие не означает review/native PASS.

## Что подготовлено

В F200 добавлены только отдельные секции, без переписывания прежних требований:

- Spec: F296-R01–R08, источник решения владельца, guards и явное расхождение
  источников; US2/US3, FR-012/013/014/022 и SC-005/008 сохранены.
- Plan: existing transport/worker/queue/leases, новый versioned partial state,
  purpose-bound playback evidence, manual primitive → UI → auto reuse.
- Tasks: draft T128–T133, все unchecked, неисполняемы до gates; без новых issues.
- Quickstart: deterministic boundary/refusal и destructive crash cuts, cold
  partial restart/playback, manual/auto, UIA/account/purge/update/rollback,
  разные source/native/installed/release доказательства.
- [Contract](contracts/windows-local-cache-cleanup.md): только exact media/WAV,
  fresh proof, protected pending/completed/readback, partial inventory и обе slots,
  строгий retained validation/полный upload validator, compatible consumers и UI.
- [Reviewer checklist](checklists/f296-local-cache-cleanup.md): **0/12**, автор
  не отмечал пункты; прежние reviewer/checklist отметки не изменены.

| Requirement | Draft tasks | Quickstart |
| --- | --- | --- |
| R01 WAV-only/retained identity | T129,T130 |2–4 |
| R02 fresh proof/strict refusal | T128 |1 |
| R03 protected intent/delete/recovery | T129,T130 |2–3 |
| R04 partial consumers/rollback | T129,T130,T133 |2,4,7 |
| R05 manual UI/capability | T131 |5 |
| R06 auto settings/pressure/bounds | T132 |6 |
| R07 preserved admission/security | T128–T132 |1–6 |
| R08 new evidence | T133 |7 |

## Решение по finalized local revision — исправление Main после review

H1 исходного проекта исправлен: Windows требует оба local revision ID
(playback и finalized_upload), корректного типа и равных item revision.
Missing/null/malformed/mismatch/legacy unknown → keep/0effects для manual/auto.
Подстановка из playback/active session запрещена. Это обязательное правило
F296 wire §43 и exact server mapping; узкое защитное отклонение от Mac optional
guard для legacy/unknown названо явно. При полном proof parity сохраняется.
T128/quickstart включают otherwise-valid missing/null/mismatch и full positive.
Нового вопроса владельцу нет. Узкий независимый rereview остаётся отдельным.

M1 исправлен: общие checklist/analyze/issues допускают только неразрушающий
T128 GET/parser/eligibility. T129 сначала exact wire/consumer/rollback review,
затем его codec/readers/writers; T130 зависит от T129. Frozen partial artifacts
нужны для соответствующей приёмки, не старта T128.

**Отдельный запланированный design gate T129:** точная новая package-state/receipt
wire version/field layout и coexistence/rollback обеих slots требуют review до
codec writer. Текущие package.v1/v2 exact field sets не расширяются этой подготовкой.
Это инженерная детализация нового partial state, а не разрешение generic missing
WAV. Production edits не допускаются одним наличием данного плана.

Других решений владельца о продуктовой области не потребовалось: manual+auto,
WAV-only, existing protected native stack и свежие guards заданы текущим поручением
и проверенными источниками. Не создавался новый quota/billing UI как будто он уже
есть в Mac runtime; не перенесён plaintext Mac receipt на Windows.

## Spec Kit и проверки

Использованы project-local speckit-specify (existing feature update),
speckit-clarify (scope/ambiguity scan), speckit-plan, speckit-checklist и
speckit-analyze (авторская cross-artifact проверка). Прочитан speckit-tasks:
формальная генерация исполняемых задач требует reviewer checklist без пустых
пунктов; по прямому заданию владельца здесь только **draft**, gate не пройден
и успешное завершение gated tasks/analyze workflow не заявлено.

Feature pointer и read-only prerequisite scripts подтвердили существующий
`specs/200-windows-desktop-app`. setup-plan сохранил существующий plan;
setup-tasks прочёл действующий шаблон, не перезаписывал tasks. Новый feature/branch
не создавался. YAML hooks проверены: commit hooks disabled; optional
agent-context after_specify/after_plan не выполнялись, так как root context вне
разрешённых F200 docs. Taskstoissues/implement/converge не запускались.
Формальный independent analyze и review остаются Main; author selfcheck не выдаёт
независимую подпись или новые reviewer отметки.

Локальная проверка документов:8requirements/6уникальных draft IDs,12unchecked
quality items, существование относительных link targets, закрытые code fences,
неизменные прежние префиксы четырёх основных документов относительно HEAD.
Политики сверены с actual Mac: freshness120s/future skew60s,grace7days,
retention30days,default toggle/operator truthy,debounce60s/candidates20/deletes50,
scan200/proof5s/total120s. Неверное ожидание старого TU hash при параллельном
применении R12 не названо source regression; новый hash точно соответствует
предложению, source write этим автором не выполнялся.

Test file paths сверены: DesktopUploadRecoveryTests находится в
GrafWindowsContractTests, QueueV2/ProtectedCustodyCodec/Files — в CoreTests;
WebViewBridgeEnvelope/Lifecycle — ContractTests. Не выдуманы уже существующие
новые CTest registrations; точный actual argv берётся из будущего build при T133.
Windows/VM/network/cert/profile/production tests и expensive governance/build
не выполнялись. R11 staging/build/evidence doc не затронуты.

Итог после правок Main: документы передаются на узкий rereview H1/M1.
Общие checklist/analyze/issues ещё обязательны до T128; отдельный точный partial
codec/consumer gate — до T129 code. Задачи остаются unchecked; reviewer owns
checklist. Исторические PASS не переназначены.

## Исторические pins первоначального авторского проекта (до review/Main правок)

| F200 path | SHA256 |
| --- | --- |
| `spec.md` | `070134916e47d506d6ede937b736756de71a560b3339ece8747d07900921f013` |
| `plan.md` | `c74a3e43e11cce01d4cbdc59bf23c9b5dcbfb4eef70785990c71af8c9d665541` |
| `tasks.md` | `e7a86e7444283feb4b4bc9ca0e698fbcbc087da1c089bdb574888a5aab367f6e` |
| `quickstart.md` | `8c75d87771cca3ffdaeda2d2817f5d59bfb97d9e864e98ace2a4e4b157005774` |
| `contracts/windows-local-cache-cleanup.md` | `fb324b3f9fea001041e740c7eeb5c674076c2f7f6a1869d953737ef90777e419` |
| `checklists/f296-local-cache-cleanup.md` | `28cae6ece34f5cc1f782ed22bec3b49ee8acfad71284a6a6ce96f71963de8463` |
