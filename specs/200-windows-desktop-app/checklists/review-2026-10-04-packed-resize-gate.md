# Packed Tree SetSize: независимая проверка требований

**Purpose**: Ограниченный requirements-quality gate worker-only `Tree.setSize(length)` внутри Step3/T116; не проверка реализации.
**Created**: 2026-10-04
**Feature**: [F200](../spec.md), [план](../plan.md), [packed contract](../contracts/windows-protected-packed-custody.md)
**Risk / lane**: high-risk-product; независимый checklist + scoped analyze до RED/code.
**Review Ownership**: Независимый reviewer. Исполнитель не изменяет пункты и markers.
**Marker Semantics**: `[x]` означает подтверждённое качество требований, не работающий код или завершённую T116.
**Generation**: Пункты первоначально созданы unchecked; последующая оценка выполняется отдельно в роли reviewer.

## Полнота и ясность

- [x] CHK001 Определены ли worker-only scope, допустимая длина0…64GiB и допуск только текущего selected proof без caller descriptors? [Completeness; packed §4:152–155, §5; plan Step3]
- [x] CHK002 Однозначно ли определён same-size committed no-op с прежним proof/generation только после write/identity/actual paired-head проверки и stale conflict без записей? [Clarity; packed §4:152–155]
- [x] CHK003 Определены ли generation+1 для действительного resize, shrink→0/EMPTY, неуменьшаемый extent (shrink→0: прежний committed extent) и запрет orphan reuse без превращения пустого media в normal package? [Edge cases; packed §4:155–158, §5]
- [x] CHK004 Заданы ли exact сохранённый prefix, ZERO только для grow suffix, запрет возвращения отброшенных bytes при shrink→grow и EMPTY за EOF? [Completeness; packed §4:129–137,159–161; local §3/6]
- [x] CHK005 Различены ли exact rewrite пограничного DATA, сохранение ZERO без materialization и отсутствие обязательного чтения удаляемых DATA при обязательной проверке используемых base nodes/граничного DATA? [Clarity; packed §4:160–163; Spec FR-012]

## Переход, отказы и владение

- [x] CHK006 Ограничена ли авторизация изменённых refs диапазоном SetSize с аутентифицированными base refs и двумя независимыми disk readback до HEAD/ACK без переноса чужого verified flag? [Consistency; packed §4:139–145,163–165; §5]
- [x] CHK007 Разделены ли pre-append invalid/exhaustion/stale/admission refusal без нового snapshot и physical/crypto/readback failure со sticky Owner; определены ли first fault и retained lease? [Exception coverage; packed §4:170–172; quickstart §14 Worker SetSize/Cuts]
- [x] CHK008 Согласованы ли notCommitted до HEAD, ambiguous после первой HEAD попытки, exact paired-head ACK и запрет нового commit/GC до reconciliation? [Consistency; packed §5:185–205; local §4]
- [x] CHK009 Сохраняются ли прежние bytes/length старого pinned proof/Reader/Clone, один Owner до actual release, read capability после writer release и инвалидирование proof/cache при ownership gap? [Lifecycle; packed §2, §4:168–176; data-model §13]

## Измеримость и связи

- [x] CHK010 Задан ли отдельный resize bound≤7 NODE+1 DATA/327680B append с padding без per-block массивов и без ослабления sequential≤1 DATA+3 NODE/290816B? [Measurability; packed §3/4:147–167; plan Step3]
- [x] CHK011 Сохраняются ли admission до allocation, owned64MiB/cache2MiB/dirty4/pins32/jobs4, физические orphan/pinned peaks и отсутствие обещания wall-time по record count? [Non-functional; packed §6; local §5; plan Step3]
- [x] CHK012 Есть ли измеримые требования приёмки empty/no-op/stale, tail/block/radix/64GiB, retained reads, shrink→grow, native fault cuts/refusals и cold обеих closures без giant fixture? [Acceptance quality; quickstart §14 Worker SetSize/Cold/Cuts]
- [x] CHK013 Согласованы ли contract, plan, quickstart, spec/data-model и существующая открытая T116, с reuse общего Tree publisher/Guard/Owner и без второго backend/lifecycle/новой задачи? [Traceability; plan Step3; tasks T116; Spec FR-012/013/022; Constitution VI]
- [x] CHK014 Явно ли остаются вне этого gate partial WriteAt, staged writer/stream adapter/adoption, T117 migration, T118 installed/hardware/cadence и T120 capture/UI, без закрытия полной Windows цели? [Scope/consistency; plan Steps3–7; tasks T116–T118/T120; Constitution IV/VI]

## Notes

- `$speckit-implement` читает gate, но не меняет markers.
- Этот файл — единственный разрешённый результат записи reviewer в текущем раунде. Старые отчёты неизменяемы.
- Оценка реализации, native receipts и source acceptance следуют отдельно после source-ready.

## Независимая оценка — 2026-10-04

**Вердикт: PASS; checked14 / unchecked0; C0 / H0 / M0 в bounded scope.**
Каждый пункт оценён reviewer по тексту требований после первоначальной генерации
unchecked. Это не выполнение tests и не перенос старого source acceptance.

### Основания отметок

- CHK001–003: packed §4:152–158 задаёт current selected proof, guarded same-size
  no-op с прежним поколением и generation+1 для изменения длины. Общая формула
  §5 относится к новому candidate, не no-op. Shrink→0: EMPTY/прежний committed
  extent; orphan не переиспользуется. Empty media не grants normal authority.
- CHK004–005: §4:129–137,159–163 задаёт exact prefix, ZERO только extension,
  запрет resurrection, EMPTY за EOF, точный boundary DATA и отсутствие
  materialization ZERO. Удаляемые DATA не читаются только ради truncate:
  это не разрешение игнорировать наблюдённый fault или используемую границу.
- CHK006: §4:139–145,163–165 и §5 ограничивают transition диапазоном SetSize;
  unchanged refs exact authenticated base; два independent disk delta readback
  до HEAD/ACK. Caller root/verified flag не является authority.
- CHK007–008: §4:170–172, §5:185–205 и quickstart Worker SetSize/Cuts разделяют
  pre-append refusal без нового snapshot, sticky physical/crypto/readback fault
  и ambiguous после первой HEAD попытки. Приёмка требует exact first fault и
  retained lease. No-op не обходит actual heads/write capability/Owner fault.
  Это Tree prerequisite, не новая классификация ошибок staged Writer API.
- CHK009: §2:42–53, §4:168–176, data-model §13 сохраняют old-root bytes/length,
  общий owner до actual release/completion и invalidation при ownership gap.
  Наблюдённый sticky fault нельзя скрыть retained cache.
- CHK010–011: §4:147–173 и §6 оставляют sequential и resize разными bounded
  операциями; global budgets/admission/physical peaks не расширены.
  Envelope limits §3 численно совместимы с resize bound:
  266240+7×8192+8×15=323704B≤327680B даже с до15B alignment на8 records.
  Это проверка непротиворечивости нормы, не доказательство будущего≤7 NODE
  алгоритма; последнее обязательно для source/tests acceptance.
- CHK012: quickstart §14:494 определяет empty/no-op/stale, block/tail/radix,
  compact64GiB ZERO, old Reader/Clone, shrink→grow, admission/exhaustion/revoked
  write, native cuts/throw и cold verification обеих closures.
- CHK013–014: plan Step3:1446–1453 связывает этап с общим transition/publisher
  и RED до implementation, исключает partial Write/stream adapter/app adoption.
  Spec FR-012/013/022, data-model §13, T116 и Constitution IV/VI согласованы;
  дальнейшие package/migration/T117/T118 gates сохраняются. T120 вне scope.

### Закрытие прежней gap-оценки

H1 снята для Tree.setSize: guarded no-op отделён от нового commit; staged
Writer candidate остаётся будущей работой полной T116, а не частью этого этапа.
H2 снята в текущем Tree scope: refusal/fault/ambiguous и first-error/lease
различены в contract и acceptance row, общий Guard/Owner путь сохранён.
Resize bound теперь проектная норма, не runtime claim. Новых C/H/M не выявлено.

### Scoped analyze

| Норма / граница | Покрытие | Что этот gate не принимает |
| --- | --- | --- |
| FR-012 exact logical bytes / faults | T116, plan Step3, packed §4/5, quickstart §14 | Полный protected consumer |
| FR-013 ledger preservation | T116, далее T117/T118 | Runtime ledger/migration |
| FR-022 truthful purge / retained roots | T116, далее T117/T118 | Delete authority |
| SC-006 security/metadata-only diagnostics | T116 + существующие bridge/security задачи | Весь SC-006/bridge |
| SC-003/005/008, integration/migration | T116–T118 и существующие общие gates | Cadence,100cycles,installed/hardware/release |

В bounded inventory4 relevant FR/SC IDs имеют task coverage4/4; новых
unmapped requirements/tasks и дублей в этом scope нет. Это не whole-F200 analyze.
Текущий tasks.md:120 задач,93 checked,27 open; T116/T117/T118 open.
#7444 OPEN — main сообщил live evidence; reviewer не обращался к GitHub
и не выдаёт своей live tracker verification. Новая задача не требуется.

### Снимок документов — SHA-256

| Документ | SHA-256 |
| --- | --- |
| packed contract | `374d8daa102a70b256fe4f03fb45d00248f6773e38bc68854dd054d610db0a75` |
| plan.md | `29c39620275a6d1f0cba0c274571ad7077b377cef70cb997a3618e68a8d4b5f3` |
| quickstart.md | `3045f730bc59bbc3abdeaf736a7e7e347825bdf6e8878bdaa10a34d293113acc` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| spec.md | `f59f95b967cf1b2bbf18b44e3a8ee99467418f46d4da2e956361527155132a7d` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| data-model.md | `90427dcfb14aaea27de331728ecae324ba600bc92927ebde2a637a55a4b1ea20` |
| research.md | `f24b604558d3eaacdbb09d97e980752bede714524c9d9e1cbdfb17231c47ac00` |
| desktop contract | `79a5b1870748f50f857e082d6ec5b2f99ba6a9149d846718865ef1de71cf5d2d` |
| local custody contract | `090f4511fb9f3e1aa9fc27caf8ba922f39fc1a5d1d778e7b29a3ae946ec65402` |

Canonical: /Users/yshishenya/Documents/crisp-worktrees/200-windows-followup.
Feature.json: F200/high-risk-product/codex/200-windows-followup/source_sha
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; Git HEAD отдельно не проверялся.
Три изменённых документа лично прочитаны в required scope; неизменённые
ранее лично прочитанные нормы/guidance переиспользованы после fresh SHA.
Constitution и skills checklist/analyze прочитаны лично, не делегированы.

### Метод и границы

Использованы speckit-checklist (unchecked generation, затем independent evaluation)
и speckit-analyze (read-only). Hooks YAML разобран: before/after checklist/analyze
все disabled. Штатный prerequisite не запускался: обычный режим может писать
feature.json, --require-spec отсутствует в installed script. Вместо этого лично
прочитаны feature.json/template, подтверждены наличие и SHA активных документов;
запись разрешена только этого reviewer-owned файла. Scripts не изменялись.

PASS допускает RED/implementation bounded worker Tree.setSize с отдельной
последующей source/native проверкой, не их автоматический успех. Partial WriteAt,
writer/IStream adapter/adoption, MF/consumer/schema/parser integration, migration,
T120 capture/UI, installed/audio/hardware/cadence/package/release и вся Windows
версия не принимаются. Старые source gates не принимают новый SetSize.
Единственная запись reviewer — этот checklist/report; код/tests/нормы/tasks/
старые отчёты/Git/GitHub/VM не изменялись и не запускались.
