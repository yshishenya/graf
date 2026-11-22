# Independent requirements checklist: protected package metadata / F200 T116

**Purpose**: качество требований к ограниченному parser/serializer package.v1/v2 до правок кода, не source/runtime acceptance.
**Created**: 2026-10-04.
**Feature**: `../spec.md`, FR-012/013/022, SC-006; `../plan.md` dependency step5; существующая открытая T116.
**Review Ownership**: только независимый reviewer. `[x]` означает подтверждённую полноту/ясность требований, не выполненную реализацию. Main не меняет отметки.
**Lane**: high-risk-product storage; bounded requirements gate. Единственный разрешённый файл текущего reviewer.

## Полнота и точность формата

- [x] CHK001 Однозначно ли заданы точное имя поля версии и полный top-level field set package.v1/v2, без выбора `schema`/`schema_version` по аналогии? [Clarity, base §8.1:434–438, packed §6.1:305–308, Gap]
- [x] CHK002 Определены ли UTF-8 JSON grammar, decoded duplicate keys, unknown/missing fields, BOM/comments/trailing bytes и независимость от key order/JSON whitespace? [Completeness, base §8.1:417–427]
- [x] CHK003 Заданы ли ограниченные размер/глубина/keys/refs и общий owned budget до allocation, без расширения квот ради нового parser? [Bounds, base §3:124–126, §5:188–191, §8.1:426, packed §6:223–225]
- [x] CHK004 Точно ли определены integer/bool/id/SHA/identity/reason/enums и явно разрешённые null, без floating-point coercion или default recovery? [Clarity, base §8.1:421–430, 459–469]

## Согласованность представлений и состояний

- [x] CHK005 Однозначно ли сохранены шесть fields v1 ref, unique roles0–5, live/sealed triple и role bounds; v1 не принимает packed по угадыванию? [Compatibility, base §8.1:459–469, packed §6.1:299–317]
- [x] CHK006 Достаточно ли точно заданы десять fields v2 ref, representation/allowed roles/container ID/live null и sealed root/extent/length/generation/SHA, включая EMPTY только length0? [Completeness, packed §3:104–125, §6.1:302–317]
- [x] CHK007 Определены ли phase/reason/short-marker и обязательные refs вместе с границей externally validated trusted prefix/manifest predicate, без normal claim из одного JSON? [Consistency, base §4:174–184, §8.1:464–470, packed §6.1:314–317]
- [x] CHK008 Определены ли deterministic serializer, whole serialized size и target own generation/context до publication, при неизменности logical v5/v3/v2? [Measurability, base §8.1:419–432, §3:124–135, packed §6.1:299–305]

## Граница доверия и зависимости

- [x] CHK009 Разделены ли parsed structural value и verified authority: own protected context/pinned generation/role/directory/ref checks до effects, без сериализуемого RAM proof или полномочия из root string? [Security, base §8.1:428–430, 463–470, packed §2:42–48, §6.1:334–339]
- [x] CHK010 Заданы ли retained roots обоих metadata slots, cold full closure после ownership gap и lifetime/pins, без выбора только текущих media heads или GC права из parser? [Recovery, base §5:257–265, packed §6:231–240, §6.1:334–339]
- [x] CHK011 Определён ли отказ при unknown schema/representation/context/semantic conflict без пустого state, fallback, artifact removal или утечки payload в diagnostics? [Failure, spec FR-012/013/022, SC-006, base §8.1:427, packed §1:11–15, §6.1:338–339]
- [x] CHK012 Прослеживается ли parser/serializer-only prerequisite к существующей T116/plan step5, с отдельными consumer/MF/migration/GC/install gates и reuse, без новой задачи/backend или принятия приложения? [Traceability, plan:1440–1472, tasks T116–118, quickstart §14:497–507, packed §6.1:343–347]

## Notes

Создано12 unchecked критериев до независимой оценки. `$speckit-implement` читает итоговое состояние как gate, но не меняет markers. Ни source, ни runtime, ни full T116 этим checklist не принимаются. История prior cadence/Writer gates неизменна. Итоговая оценка и SHA anchors будут добавлены ниже после личного чтения и пересчёта.

## Независимая оценка — завершена

**REQUIREMENTS NEED CLARIFICATION: 11 checked / 1 unchecked; C0/H1/M0.**
Это конечная ограниченная оценка текущего нормативного снимка, не ожидание
runtime и не source verdict. CHK001 открыт по H1 ниже. Остальные markers
подтверждают написанные требования, а не готовый parser или future authority.

### Лично прочитанный контекст и режим

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Из `.specify/feature.json`: F200/high-risk-product, branch
`codex/200-windows-followup`, source_sha
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Это прочитанный anchor файла,
не новый Git HEAD check reviewer; свежую проверку branch/HEAD сообщает main.
Main отдельно сообщает fresh issue7444 OPEN; reviewer GitHub не вызывал.

SKILL speckit-checklist, speckit-analyze, code-reviewer лично прочитаны целиком.
Root AGENTS/guidance index, extensions.yml и checklist template прочитаны.
Все before/after checklist/analyze hooks git.commit disabled; ничего не
вызывалось. Prerequisites не запускались, поскольку скрипт использует Git,
а текущий scoped request запрещает Git: feature paths/template/docs
проверены прямым чтением. Spec Kit analyze здесь read-only; его вывод
записан в единственный разрешённый reviewer checklist, не в нормы.

Прежнее личное полное чтение неизменённых constitution/guidance/spec/plan/
tasks/quickstart переиспользовано только после свежих SHA. Дополнительно
прочитаны constitution I/II/IV/VI/platform, base §3 bounds/§4 state/§5 budgets/
GC и полностью §8.1:415–552, packed §1–4 и §6.1:297–347, plan:1410–1472,
tasks T116–118, quickstart §14:475–507, spec FR-012/013/022 и SC-006,
data-model §12/13. LocalRecordingPackage.h/cpp и ProtectedCustodyMetadata.h/
cpp прочитаны полностью; Tree.h и role/types codec read. PRD/current-status
прочитаны в platform/product-baseline области, не весь unrelated historical
implementation log. Бюджеты/wire/caller semantics не выводились из памяти
о старом MSIX или предыдущего cadence PASS.

### H1 — точное имя обязательного schema-поля не определено

**HIGH, CHK001; base:417–420,434–438; packed:299–308.** Таблица задаёт
точный schema string и «остальные точные поля», но нигде в этих нормативных
местах не задаёт literal JSON key этого schema string. `schema` и
`schema_version` — разные decoded keys. Packed.v2 наследует тот же top-level
field set; это не восполняет отсутствие имени. Data-model:467 и plan:1461
также указывают schema value/contract, не имя. Лично прочитанный старый
LocalRecordingPackage.cpp:126–127 использует `schema_version` для другого
logical manifest.v5: это не authority package schema и не норма нового codec.

Классификация HIGH основана на обязательном exact field whitelist и
unknown/missing rejection, не на желании получить H: без уточнения два
независимых совместимых по тексту writer/reader выбирают разные обязательные
keys и отвергают защищённый пакет. Приёмка exact writer/parser bytes и
compatibility становится неоднозначной. Принимать оба alias — самовольное
расширение exact field set, не безопасное устранение пробела. Конституционного
нарушения нет (C0), исполненного runtime fault здесь не заявляется.

**Минимум до RED/product edits:** main должен нормативно назвать один exact
обязательный decoded key для package.v1/v2 schema string; явно подтвердить,
что прежний logical manifest.v5 не источник этого имени, aliases/missing/
alternate key отвергаются. Packed §6.1 может наследовать уточнённый base
§8.1 — новые top-level данные/схемы/лимиты/задачи не нужны. После fresh SHA
нужна переоценка только CHK001/согласованных мест; reviewer не выбирает key
и не меняет норму самостоятельно. Это техническое уточнение существующей
T116, не новый продуктовый policy вопрос или разрешение migration.

### Основания остальных отметок

| Критерии | Подтверждённое требование и предел оценки |
| --- | --- |
| CHK002/004 | Base:417–427 задаёт JSON object/UTF-8 без BOM, decoded duplicate/unknown/missing refusal, unsigned literal/from_chars без fraction/exponent/overflow, bool/ASCII/hex/enums/null. Escaped key обязан сравниваться после decode; invalid/non-ASCII values не расширяют ID/reason/role grammar. Нет разрешения заменить это substring helpers. |
| CHK003 | Payload64KiB, package refs0–5, object≤16keys/depth≤4; v2 refs10keys помещаются. Общие64MiB/cache/pin/job/dirty прежние, serialization входит в owned. Не назначен новый native process threshold. Фиксированная allowed package shape не требует произвольного DOM глубже этого предела. |
| CHK005/006 | V1 refs ровно6fields, v2 ровно10; binding/triple и packed3 stamp fields null rules/role restrictions точны. Root128 lower-hex = Ref64B, NODE_L2/base0, extent/context и length≤role bound по wire. Служебные manifest/recovery остаются flat_v1; sealed EMPTY только length0 не разрешает normal empty capture. |
| CHK007 | Base:464–469 задаёт canonical live для capturing/finalizing; sealed_normal media/playback/manifest+empty reason+false short; degraded known nonempty reason+trusted prefix/no upload; discard true+positive predicate+protected marker. Проверка реальных prefix/manifest не может быть доказана текстом JSON и остаётся внешней authority validation. Это не причина расширить parser до audio/finalizer. |
| CHK008 | Deterministic order и whole serialized cap/own context/target generation до публикации заданы. Выбор единственного schema key остаётся отдельно H1; determinism не разрешает произвольную новую схему. Нет требования byte-for-byte сохранить whitespace чужого JSON; logical v5/v3/v2 не меняются. |
| CHK009 | Base:428–430/463–470 и packed:42–48/334–339 отделяют struct от verified context/root. Expected own context/generation/directory — отдельное trusted основание, не самоподтверждение input. Typed parse не создаёт Tree proof/pin, не открывает файл и не выдаёт upload/delete/GC/normal authority. |
| CHK010 | Persistent roots из обоих metadata slots сохраняются, в том числе вне двух current media heads; ownership gap требует full closure того же guard и pin/lifetime. В текущем Tree.h verify получает Owner, proof ctor private, caller-root admission не существует. Будущий retained-root validator/adoption ещё нужен, но parser-only не должен его подменять или считать реализованным. |
| CHK011/012 | Unknown/malformed/context mismatch — recovery-required без default/empty/fallback. Existing Metadata.h:38–42 явно оставляет semantic JSON/account/admission caller и не даёт effects. Current LocalRecordingPackage.inspect — plaintext v5/regex/filehash/URL MF, не готовый защищённый authority parser. Reuse этого имени не разрешает regular legacy path; consumer rewrite отдельно. |

### Bounded analyze / зависимости

FR-012 → строгий защищённый logical metadata/context/error prerequisite T116;
FR-013 → отсутствие default/empty/rollback и неизменность v3/read-v2 очереди
в T116, migration отдельно T117; FR-022 → parser не создаёт delete right,
actual lifecycle/effects отдельно T116–118. SC-006 → не помещать payload в
diagnostics; bridge/origin/nonce full matrix этим parser этапом не принимается.
Все4 scoped requirements имеют существующий T116 coverage (4/4), не новая
задача и не full feature coverage statement. Plan step5 требует schema gate
**до** V5/MF/hash/upload consumers; step6 отдельно migration.v2/T117.
На нынешний parser/serializer-only шаг нет task/constitution conflict;
единственный blocking requirement ambiguity — H1. Consumer adoption,
bootstrap/migration реализация/GC/install/app/audio/physical/release не входят.

### SHA-256 лично сверенных артефактов

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `f59f95b967cf1b2bbf18b44e3a8ee99467418f46d4da2e956361527155132a7d` |
| plan.md | `5b5996e9c35a185c470f23b6e9228ebe7d46337513741505ba77ffcfe88928e8` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `3045f730bc59bbc3abdeaf736a7e7e347825bdf6e8878bdaa10a34d293113acc` |
| base contract | `090f4511fb9f3e1aa9fc27caf8ba922f39fc1a5d1d778e7b29a3ae946ec65402` |
| packed contract | `6cb9bc197f44e689c83ddff4dc216ee818867abe06cca99fdd6c2fd8ba992644` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| data-model.md | `90427dcfb14aaea27de331728ecae324ba600bc92927ebde2a637a55a4b1ea20` |
| LocalRecordingPackage.h | `bd54424e3e9b826c3233d5a1158247ecec0ef5aff9cef34887097192c87dc698` |
| LocalRecordingPackage.cpp | `7cfc575282ae03714b52adc219d798121dcbf6d6c4af8a3398f7760de8c30a40` |
| ProtectedCustodyMetadata.h | `7d05cf97fc255c30e7171cd4159fb53fe239efacc402944ec629b85f983bb2cd` |
| ProtectedCustodyMetadata.cpp | `739b40a5670227530554a9fc3c92a41a86c2b2577a1d9ac92c3ee118581dab74` |
| Tree.h | `9c28432d20e49726033a1f855bc458b93040c6681d9155a81504dfad4a7a9b87` |
| extensions.yml | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |
| checklist template | `6c5888b55ebdfe63d2c2ce62496a029cdc3751075add407bb3a808d0eaeeab4c` |

Итоговые markers перечитываются после записи. Единственная запись reviewer —
этот новый файл; source/norm/tasks/old reports/Git/GitHub/VM/runtime не менялись.
**Конечный статус: 11/1, C0/H1/M0; requirements gate не PASS до H1 clarification.**

## Повторная независимая оценка — 2026-10-04, после подтверждения schema

**REQUIREMENTS PASS: 12 checked / 0 unchecked, ровно12 критериев; C0/H0/M0.**
Предыдущие 11/1 и H1 выше сохранены как история прежнего нормативного снимка.
Изменён только marker CHK001; эта запись задаёт актуальный конечный результат.
Это принятие качества требований package parser/serializer prerequisite T116,
не приёмка кода, защищённого пакета, consumer adoption или полного приложения.

### H1 закрыто нормативным уточнением, а не предположением reviewer

Лично перечитаны spec FR-012:472–475 и Session2026-10-04:642–645,
base §8.1:417–560, packed §6.1:297–349 и data-model §12/13, включая486–488.
Base:434–439 теперь задаёт **ровно9** обязательных top-level fields:
`schema/store_id/object_id/generation/directory_id/phase/reason/
short_recording_discarded/refs`. Единственный ключ версии — `schema`,
значение v1 — `graf.custody.package.v1`. Packed:305–319 наследует тот же
точный набор с `schema="graf.custody.package.v2"` и отдельными10fields ref.
`schema_version`, alias, unknown/missing/duplicate decoded keys запрещены.
Logical v5 manifest не переименован. Spec/base/packed/model согласованы.
Уточнение других authority records не входит в этот package-only PASS.

Все12 критериев перечитаны и независимо переоценены. CHK002–012 сохраняют
основания таблицы выше: JSON/decode/числа/null/role/phase/size semantics,
deterministic serialization и ожидаемые trusted context/generation/directory
не ослаблены уточнением. Parsed value не выдаёт RAM proof или полномочия.
Retained roots обоих slots и cold full closure до будущих effects остаются
обязательными; parser не объявляет их реализованными. Никаких увеличений
64KiB/owned64MiB/pins/jobs/dirty, plaintext fallback или новой задачи нет.

### Текущий bounded analyze и проверка окружения

Canonical и HEAD лично сверены read-only:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
`codex/200-windows-followup`,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
FR-012/013/022 и SC-006 имеют existing T116 coverage4/4; plan step5:1461–1463
оставляет schema prerequisite до V5/MF/hash/upload consumers, steps6/7 и
T117/T118 — отдельно. Новых C/H противоречий spec/plan/tasks/model/contract/
constitution в этом ограниченном срезе не обнаружено. T116 остаётся OPEN.

Required SKILL checklist/analyze/code-reviewer прочитаны лично полностью;
AGENTS, guidance index, spec-kit-flow, product-gates, constitution и extensions
прочитаны. Неизменные plan/tasks/quickstart и прежний исходный контекст
переиспользованы только после свежих SHA, релевантные sections перечитаны.
LocalRecordingPackage/Metadata h/cpp hashes неизменны относительно предыдущей
личной проверки; их старый logical v5/read/write flow не принят как новый parser.
Supported prerequisite `--json --require-tasks --include-tasks` прошёл;
`--require-spec` отсутствует в лично прочитанном `--help`, spec проверен отдельно.
Before/after checklist/analyze commit hooks disabled; GitHub hooks не запускались.
Git применён только read-only для identity/reference, без mutations.

### Актуальный SHA-256 нормативного снимка

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `0073b6f2ff8e3e9f07389473cf7fc0f5c2eaf146961f08426d140163dd5d4fe2` |
| base contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| packed contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| data-model.md | `dc91ac60f180e6221e85917c9a91e510e34008430dfb457e7a7cbeb97162e0a7` |
| plan.md | `5b5996e9c35a185c470f23b6e9228ebe7d46337513741505ba77ffcfe88928e8` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `3045f730bc59bbc3abdeaf736a7e7e347825bdf6e8878bdaa10a34d293113acc` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

Прежний report до этого изменения: SHA-256
`cac37ebbcdd9fb9b0e7944f99cb8fa0f02485c38df1c5159dece58912d8d6418`.
Разрешённые записи этого раунда — только этот файл и отдельный reviewer-owned
calendar-join-gate. Старые отчёты/код/нормы/tasks/GitHub не менялись reviewer;
сборки/VM/runtime не выполнялись. Финальные markers и полный report перечитываются
после записи, конечный hash передаётся main отдельно.
**Актуальный конечный статус: REQUIREMENTS PASS12/0, C0/H0/M0.**

## Завершённая независимая проверка после прерывания — 2026-10-04

**REQUIREMENTS PASS — 12 checked / 0 unchecked; C0/H0/M0.**
Лично переоценены все CHK001–012 по текущим требованиям. Результат не
унаследован от прерванного reviewer. При первом чтении этого раунда файл уже
содержал 12/0 и дополнение после schema clarification; прежние 11/1/H1 и
последующее дополнение сохранены полностью. Новых критериев не добавлено.

Репозиторий и фактический Git HEAD сверены read-only:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
`codex/200-windows-followup`,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Оценивается рабочий текст с изменениями, поэтому HEAD не заменяет SHA-256
каждого нормативного файла ниже.

### Основания по всем 12 пунктам

| Пункт | Итог | Лично проверенное основание |
| --- | --- | --- |
| CHK001 | PASS | Spec FR-012:472–475 и Session 2026-10-04:642–645 фиксируют подтверждённый владельцем ключ `schema`. Base §8.1:434–444 задаёт ровно девять верхних полей: schema/store_id/object_id/generation/directory_id/phase/reason/short_recording_discarded/refs. Packed §6.1:305–319 наследует их с точным значением package.v2. Model:486–488 согласован; schema_version/aliases/missing/unknown/decoded duplicates запрещены. Logical manifest.v5 не переименован. Исторический H1 закрыт этим нормативным уточнением. |
| CHK002 | PASS | Base:417–420: UTF-8 object, без BOM/invalid UTF-8/comments/trailing bytes, decoded duplicates/unknown/missing; все поля обязательны. Key order/JSON whitespace не значимы для чтения. Packed:299–303 сохраняет правила. |
| CHK003 | PASS | Base:124–126,188–192,426: payload≤64KiB, depth≤4, keys≤16, общий refs/sources≤6; package:466 уточняет refs0–5. Packed:223–227 сохраняет owned64MiB, cache2MiB, dirty4, pins32/jobs4. Serialization входит в owned budget до allocation; manifest64KiB не расширяет остальные квоты. |
| CHK004 | PASS | Base:421–430,444,466–476 задаёт exact unsigned decimal u64 без fraction/exponent/coercion, bool, lowercase ID/SHA, ASCII identity/reason, known enums и только явно разрешённые null. Unknown/overflow/context mismatch — recovery-required, без default. |
| CHK005 | PASS | Base:466–479: ровно шесть полей v1 ref, пять уникальных ролей, live triple=null только capturing/finalizing; sealed generation≥1/role-bound length/exact logical SHA и matching role/object. Packed:299–319 не расширяет schema1 и не разрешает угадывание representation. |
| CHK006 | PASS | Packed:302–319: ref ровно десять полей; flat_v1 имеет три null stamp fields, packed_v2 только canonical/media/playback с container ID; live/sealed null rules точны. Ref128 lowercase hex кодирует Ref64B; §3:104–125 задаёт root NODE_L2/base0/context/extent. EMPTY допустим только length0 и не обходит sealed_normal. |
| CHK007 | PASS | Base:174–184,471–479: canonical live для capturing/finalizing; sealed_normal требует sealed media/playback/manifest, empty reason/false short; degraded — nonempty known reason и validated trusted prefix без upload; discard — positive short predicate/protected manifest marker/true short. Наличие JSON не доказывает реальный prefix/manifest/index. |
| CHK008 | PASS | Base:419–420,428–432 задаёт deterministic order и target generation/context до публикации; payload whole-size ограничен. FR-012:475 и packed:299–319 сохраняют logical v5/v3/read-v2, не требуют переименования прежнего manifest. |
| CHK009 | PASS | Base:428–430,462–479 отделяет structural parse от own pinned context/directory/role/ref validation до effects. Packed:42–48,336–341: RAM proof привязан к непрерывному owner, не сериализуется и не выводится из строки root_ref. Parser не даёт upload/delete/GC authority. |
| CHK010 | PASS | Base:256–265,477–479 и packed:231–240,336–339 сохраняют roots обоих slots, в том числе вне текущих media heads. После ownership gap каждый retained root требует full closure под тем же guard; отмена не освобождает живой owner/job/pin. |
| CHK011 | PASS | FR-012/013/022, SC-006; base:427 и packed:9–15,340–343: unknown schema/representation/context/semantic conflict блокирует использование без empty/default/downgrade/plaintext fallback или удаления артефактов; diagnostics metadata-only. |
| CHK012 | PASS | Plan:1440–1472, особенно step5:1461–1463, ставит schema gate перед V5/MF/hash/upload consumers. Tasks:568–570 сохраняет существующие T116→T117→T118. Quickstart §14:497–507 отделяет strict metadata и retained roots от generated/installed/native acceptance; новый task/backend/lifecycle не нужен. |

### Ограниченная сверка согласованности

Использованы лично прочитанные правила `speckit-checklist` и
`speckit-analyze`: проверка требований, их покрытия задачами и конституцией.
FR-012/013/022 и SC-006 покрыты существующей T116 (4/4 в этом срезе);
T117 владеет migration, T118 — полной приёмкой. Новых противоречий,
дублирования задач, неясностей или непокрытых требований в этих 12 критериях
не обнаружено: CRITICAL=0, HIGH=0, MEDIUM=0. Полный анализ Feature 200 этим
результатом не заменяется.

Лично прочитаны applicable parent/root AGENTS (ближайший root запрещает Linear),
guidance index, codex-worktrees, spec-kit-flow, product-gates, tracker/canon,
относящиеся к срезу release/validation и PRD/current-status sections, constitution,
project-local skills checklist/analyze и extensions.yml. Before/after
checklist/analyze commit hooks disabled. Supported prerequisites
`--json --paths-only` и `--json --require-tasks --include-tasks` прошли;
`--require-spec` не поддерживается текущим скриптом, spec прочитан отдельно.
Никакие hooks, меняющие Git/GitHub, не запускались.

### SHA-256 текущего нормативного снимка

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `0073b6f2ff8e3e9f07389473cf7fc0f5c2eaf146961f08426d140163dd5d4fe2` |
| plan.md | `5b5996e9c35a185c470f23b6e9228ebe7d46337513741505ba77ffcfe88928e8` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `3045f730bc59bbc3abdeaf736a7e7e347825bdf6e8878bdaa10a34d293113acc` |
| data-model.md | `dc91ac60f180e6221e85917c9a91e510e34008430dfb457e7a7cbeb97162e0a7` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| contracts/windows-protected-local-custody.md | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| contracts/windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |

SHA-256 этого файла до настоящего дополнения:
`59e942fa28688320190f7f024335b2ab8989a1010e78daf286201b4838cc08c7`.
Все прежние байты сохранены как префикс. Итоговые markers перечитаны после
записи; SHA-256 итогового отчёта передаётся отдельно, без self-hash.

**Терминальный вывод: REQUIREMENTS PASS 12/0, C0/H0/M0; блокеров качества
этих требований нет.** Реализация parser/serializer, consumer integration,
retained-root authority validation, migration/GC и T116–118 runtime/installed
приёмка остаются отдельной незавершённой работой. Код, spec/plan/tasks,
GitHub, commits, сборки, установка, VM и устройства reviewer не менял.

## Независимая проверка следующего ограниченного шага T116 — 2026-10-06

**REQUIREMENTS PASS: 12 checked / 0 unchecked; C0/H0/M0/L0.**
Разрешённая область этого вывода — только structural value, строгий bounded
JSON parser и deterministic serializer `graf.custody.package.v1/v2` в
существующих `Storage/ProtectedCustodyMetadata.h/.cpp` **до consumer adoption**.
Это текущая независимая оценка требований, не source review нового кода и не
runtime acceptance. Round250 working-profile safety gate не повторялся и не
пересматривался. Его NO-GO не снимается этим PASS.

### Снимок, метод и границы

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, лично сверенный HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Dirty сохранён; вывод привязан
к SHA-256 рабочих файлов ниже, а не только к HEAD. Владелец реализации —
существующая T116/#7444 по tasks:550–570; задача остаётся `[ ]`.
Текущее состояние GitHub reviewer не запрашивал и не менял.

Лично целиком прочитаны project-local `speckit-analyze` и `speckit-checklist`,
AGENTS/index, spec-kit-flow, product-gates, codex-worktrees, constitution и
extensions.yml; относящиеся к области PRD/current-status и tracker/canon
sections. Лично перечитаны все 12 критериев, base §8.1 и bounds/phase/GC,
packed §1–3/6/6.1, spec FR-012/013/022 и SC-006, plan:1510–1597,
tasks T115–118, model §12/13:504–582, quickstart §12/14:381–431/500–533.
Лично прочитаны Metadata.h/.cpp, Codec.h, PackedFormat.h/.cpp и ReasonCode/
toString из WindowsDesktopContracts.h: это контекст reuse и разделения
полномочий, не разработка кода вместо main.

YAML hooks валиден; enabled before/after analyze/checklist hooks — 0.
Supported prerequisites `--json --require-tasks --include-tasks` и
`--json --template checklist-template` прошли. Вызов с `--require-spec`
отклонён существующим скриптом; его `--help` прочитан, spec прочитан отдельно,
скрипт не исправлялся. Analyze выполнялся read-only; его результат ниже
перенесён только в этот разрешённый reviewer-owned отчёт. Новый checklist
не создавался, существующие markers не менялись.

### Повторная оценка всех критериев на текущих нормах

| Критерий | Итог и основание для ограниченного шага |
| --- | --- |
| CHK001 | PASS — base:434–444 и packed:305–319 однозначно задают `schema`, exact девять top-level keys и две schema strings. Spec FR-012 и model §12 согласованы. Никаких aliases/schema_version или изменения logical manifest.v5. |
| CHK002 | PASS — base:417–427: key order/JSON whitespace принимаются, writer order детерминирован; decoded duplicate/unknown/missing keys, BOM, invalid UTF-8, comments и trailing bytes отвергаются. Ограниченный ASCII-allowed decoder подходит этой закрытой форме: допустимые JSON escapes декодируются **до** key comparison и проверки grammar поля, а не отвергаются целиком. Non-ASCII decoded text не имеет разрешённого поля; произвольный DOM не требуется. |
| CHK003 | PASS — package payload≤65536B, depth≤4, keys≤16/object, refs≤5. Typed fixed shape/ограниченные строки и reuse CustodyBytes не расширяют owned64MiB/cache/pins/jobs/dirty; динамическая сериализация учитывается существующим бюджетом до allocation. Size проверяется для всего результата, включая escaped spelling входа. |
| CHK004 | PASS — exact JSON unsigned decimal u64, без минуса/fraction/exponent/overflow/coercion; bool literal, lowercase id/SHA, ASCII identity/reason и known enums. JSON grammar исключает leading-zero number и неявное null/default. Пустой wire reason означает ReasonCode::none; существующий `toString(none)="none"` не отменяет это правило формата и не разрешает прямую сериализацию `"none"` вместо пустой строки. |
| CHK005 | PASS — v1 ref ровно шесть keys, пять уникальных разрешённых ролей; live triple весь null только в capturing/finalizing, sealed triple весь non-null, generation≥1 и role length bound. Schema v1 не угадывает packed representation. |
| CHK006 | PASS — v2 ref ровно десять keys; flat_v1 требует container/extent/root null. Packed только canonical/media/playback, live container non-null с остальными nullable stamps по §6.1; sealed exact non-null triple/extent/root. Root128 lowercase hex декодируется существующим Ref64B/PackedReferenceBounds: NODE_L2 для nonempty, EMPTY лишь length0, reserved/alignment/offset+length/version/extent bounds без overflow. Проверка actual node selector/base0 и ciphertext closure остаётся внешней, не выводится из Ref64B. |
| CHK007 | PASS — canonical live для capturing/finalizing; sealed_normal требует sealed media/playback/manifest, empty reason/false short. Degraded требует nonempty known reason, discard — true short. Trusted prefix/positive short predicate/protected manifest marker и exact member hashes проверяются будущим authority validator: parser не заявляет normal/discard только по JSON. |
| CHK008 | PASS — deterministic serializer проверяет ту же закрытую shape, context/generation/directory и whole-size limit до выдачи байтов. Допустим единый стабильный порядок refs, без новой семантики порядка чтения; повторная сериализация не обязана сохранять чужой whitespace/escape spelling. Целевой generation проверяется до будущей publication, serializer не публикует. |
| CHK009 | PASS — expected own package-state context, pinned generation и validated directory передаются отдельно; input не может сам подтвердить свои IDs. Structural success не выдаёт lease/pin/GuardOwner/proof, не проверяет actual directory/DPAPI/index/owner/rights и не открывает admission/upload/delete/GC. |
| CHK010 | PASS — base:256–265/477–479 и packed:336–339 требуют retained roots **обоих** slots и full closure под тем же owner после gap. Это будущий consumer prerequisite, не обязанность parser читать диск или принимать root в дерево. Исключение IO/retained-root adoption из текущего шага не отменяет требования. |
| CHK011 | PASS — malformed/unknown schema/representation/enum/context/shape отказывают без принятого value, empty queue, fallback, удаления и payload diagnostics. Reuse существующего CustodyCodecResult/CustodyCodecError достаточно; новый backend/сервис ошибок не нужен. Recovery-required product state остаётся обязанностью будущего caller. |
| CHK012 | PASS — plan step5:1586–1588 и открытая T116 уже владеют strict package prerequisite; v5/MF/hash/upload/finalizer integration следует после него. T117 migration.v1/v2 и T118 полная приёмка отдельны. Новый task/сервис/DOM/dependency или ослабление общей приёмки не требуются. |

### Ограниченный analyze / покрытие

| Требование | Покрытие | Что этот шаг не принимает |
| --- | --- | --- |
| FR-012 | T116, plan step5, base §8.1 / packed §6.1 | Защищённый полный writer/reader/encoder, actual publication/closure и installed приложение. |
| FR-013 | T116; совместимость/переход также T117 | Перезапись queue v3/read-v2, загрузку реестра, migration или recovery authority. |
| FR-022 | T116, дальнейшие T117/T118 | Право на purge/GC/discard и фактическое удаление/ACK. |
| SC-006 | T116, metadata-only failure contract | Полную bridge/origin/nonce security matrix и отсутствие утечек всего приложения. |

Итого scoped requirements4, implementation task1 (T116), coverage4/4=100%,
ambiguity0, duplication0, unmapped scoped requirements/tasks0, C0/H0/M0/L0.
Constitution II/III/IV/VI сохранены. Это не полный analyze 22FR/10SC/120tasks
Feature200. Нормы package и constitution неизменны относительно прошлого
package review; spec/plan/model/quickstart имеют новые общие SHA и перечитаны
в актуальных относящихся к package местах. Прежние line numbers не использованы
как доказательство текущего текста.

**Можно начинать RED/реализацию только указанного parser/serializer шага.**
Consumer adoption требует отдельной оценки связей own context/ref/index,
retained roots/owner/pins/cold full verify, authenticated actual hashes/prefix/
manifest predicates и no plaintext v5/MF/upload/playback пути. T117 всё ещё
требует restart-safe intent/fence/copy/switch/authorized cleanup с сохранением
UUID/bytes/ranges/delete ops; T118 — generated полный lifecycle/failure/100cycles,
standard-user/offline/install/update/rollback. Working-profile installation,
audio/hardware, accessibility, signing и общий parity/release здесь NOT RUN.

### Свежие SHA-256 рабочих артефактов

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `5cc51e712a6b1543771aab46ba922b3f90768f177e0e274d548df4a8eb6681d2` |
| data-model.md | `8dd54012c3bfe4003cd18db98ebc67e0b7730cbbdfb6523b881cce4cdc15ec19` |
| research.md | `0e7659d4cf5136d392bde28cb273c6ca0be6af2ac3eca50e23a617e1af129522` |
| base contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| packed contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| extensions.yml | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |
| speckit-analyze SKILL.md | `07ead5c0db569e93b75c4cada8139ef799d5721d6037c3ed15b7482d114d22d1` |
| speckit-checklist SKILL.md | `890ef64b5527a69a9661f1c100f15b066ec368b67f771d44c05fcc091fe1bbed` |
| ProtectedCustodyMetadata.h | `7d05cf97fc255c30e7171cd4159fb53fe239efacc402944ec629b85f983bb2cd` |
| ProtectedCustodyMetadata.cpp | `739b40a5670227530554a9fc3c92a41a86c2b2577a1d9ac92c3ee118581dab74` |
| ProtectedCustodyCodec.h | `a5152a136c102b285e5e34cc926a9c6da7f6c3c43a5acca5707069a757e3dcde` |
| ProtectedPackedCustodyFormat.h | `0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88` |
| ProtectedPackedCustodyFormat.cpp | `bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f` |
| WindowsDesktopContracts.h | `52d0667fba1122e4db1ed4f1d07e7e94aefb47c6da954a207da48155f254856e` |

Отчёт до append:31713B, SHA-256
`a93a08a1fda433a2a4523161edc39d6d0547eee8ed7cc5d42bc66675a5dc06f2`.
Существующие байты/12 markers сохранены; итоговый hash без self-hash передаётся
после перечитывания. Единственная запись reviewer — это дополнение.
Код/нормы/tasks/Git/GitHub/VM не менялись; тесты/сборки не запускались и LIVE
full49 session40892 не затрагивалась. **Итог: REQUIREMENTS PASS12/0,
C0/H0/M0/L0; T116/#7444 не закрыта, consumer/migration/installed acceptance
не приняты.**

### Уточнение main о reuse — учтено до product edits

**PASS сохраняется, нормы/12 markers не изменились.** Лично прочитан
DesktopApiClient.cpp:28–153: private JsonReader имеет другой числовой grammar,
2MiB/depth32 пределы и динамические set/map без package-specific key cap.
Он не переносится в Storage, auth/response parsing не ослабляется. Его SHA-256
`8eafdea3d06b85c329050be656bd980da34d4cd02719ee7f6cb238da8148a892`.
Borrowed input только на время parse, fixed decoded token≤300ASCII и
seen-field bitmask соответствуют закрытой форме: все допустимые строки/keys
помещаются, accepted package имеет depth3 и максимум10keys/object, refs≤5.
Unknown key не пропускается через generic skipUnknown/DOM. Результат не должен
удерживать dangling views входа; structural value остаётся своим fixed value,
без proof/pin. CustodyBytes serializer сохраняет charged allocator; own trusted
context/generation/directory проверяются до parse/serialize. Escapes/decode,
whole input≤64KiB и all-or-none null triples по таблице выше сохраняются.

Metadata.h/.cpp лично повторно сверены: прежние `7d05cf...`/`739b40...` hashes
точно совпали; product edits на момент gate отсутствуют. Main сообщает свежий
live read #7444 OPEN/canonical labels и old-source Owner PASS194.30s/Tree
PASS20.85s при ещё LIVE full49; reviewer это не выдаёт за собственную VM/
GitHub проверку или proof нового parser. Competing tests не запускались.
**Терминальный bounded verdict: REQUIREMENTS PASS12/0, C0/H0/M0/L0,
разрешён только согласованный structural parser/serializer prerequisite T116.**

## Независимое source review package codec — 2026-10-06

**SOURCE REQUEST CHANGES / NO-GO: C0/H1/M0/L0.** Requirements gate остаётся
PASS12/0; нормы и markers не менялись. Единственный HIGH ниже — неполнота
обязательных регрессий новой trust-boundary ветки, не доказанный runtime bug
и не новый нормативный вопрос. До устранения нельзя считать parser/serializer
принятым или переходить к consumer adoption. Full product integration и
working-profile installation по-прежнему NO-GO.

### Лично проверенный снимок и поток

Canonical/branch/HEAD прежние:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
`codex/200-windows-followup`, `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Лично целиком прочитан `code-reviewer/SKILL.md`; Metadata.h/.cpp и новый
ProtectedCustodyPackageTests.cpp прочитаны целиком, CMakeLists.txt целиком
и diff регистрации; callers найдены через rg. Новые API вызываются только
новым test, product callers не подключены. Metadata.cpp в процессе main
добавил `reserve(packageLimit)`; текущие bytes перечитаны после изменения
и hash повторно сверён. Старый persistence worker ниже API не изменён этим
diff. Existing Format/Memory/Codec и ReasonCode прочитаны как reuse context.
Base/packed/spec/plan/tasks/quickstart hashes совпали с requirements snapshot.

Статически не найден bypass decoded-key/field whitelist: string decode
предшествует поиску ключа, index фиксируется до перезаписи token; object
bitmask отвергает decoded duplicates. Top mask511 и deferred ref masks63/1023
проверяются после whole object, поэтому schema не обязана предшествовать refs.
Unsigned scanning/from_chars отвергают leading zero/overflow; fraction,
exponent, sign и literal suffix не проходят последующий JSON delimiter.
Identity/id/SHA/enum grammar закрыта; whitespace только четыре JSON bytes,
unknown keys не skipped. Нет сохранённых input views или allocation в reader.

Общий packageShape разделяет context/generation/directory, unique roles,
live/sealed triples, v1/v2 representation, flat null stamps и packed role/
container/root/extent bounds; root проверяется через existing decodeReference.
Существующий valid g1 empty-birth bound сохраняется. Проверки actual closure,
node base/selector, exact member hashes, trusted prefix/short predicate и
protected manifest не выданы за parser proof. Header явно отделяет structural
value от lease/pin/GC/upload/discard authority. No IO/auth/backend/adoption.

Writer проверяет shape до байтов, резервирует charged64KiB до plaintext,
не reallocates предыдущий plaintext buffer; full output cap проверяется при
каждом emit, результат CustodyBytes очищается существующим destructor.
Порядок keys/ref roles детерминирован; reason none пишется пустой строкой.
Bad_alloc/length_error возвращают typed failure без принятого value.
CMake registration добавляет один real test, включает production metadata
через common OBJECT, assert оставлен включённым даже Release. Никакого
ослабления timeout, существующих тестов или auth parser в этом срезе не найдено.

### H-S251-1 — packed package validation и failure paths не покрыты новым тестом

**HIGH, source acceptance gap**, ProtectedCustodyPackageTests.cpp:13–18,38–92;
Metadata.cpp:51–59,63–67,193–228. Оба прохода test (`v2=false/true`) создают
только flat_v1 refs; нигде нет packed_v2/container/root value. Поэтому даже
зелёный новый executable не исполняет новый packed package branch и связь
JSON→root bounds→serializer. Existing FormatTests доказывают отдельный decoder,
но не правильную передачу nullable stamp/generation/length из нового JSON.
Only usedBytes equality на success не проверяет charged allocator refusal.

Минимальная доработка в том же test, без нового backend/fixture service:

- Positive packed live и sealed roundtrip с valid NODE_L2 и EMPTY(length0);
  negatives: flat non-null stamp, forbidden packed manifest/recovery/schema1,
  missing container, mixed live/sealed nulls, nonempty EMPTY/root kind,
  reserved/alignment/overflow/version>generation/extent-before-root bounds;
  те же mutations typed value должны отвергаться writer.
- Complete structural phases: finalizing/discard_pending и неверные
  reason/short/mandatory refs; positive пяти unique roles и sixth refusal.
  Schema-after-refs/permuted keys, decoded duplicate внутри ref, valid escaped
  values, identity300/301 и exact u64 max/mismatched expected object context
  должны пройти/отказать без изменения норм. Эти случаи можно сгруппировать.
- Exhaust existing charged budget перед write: allocationFailed, no accepted
  output, charge восстановлен после освобождения; обычный valid write/read
  затем снова успешен. Не увеличивать quota и не трогать рабочий профиль.

Нужны fresh hashes и focused portable/native результат этого test после
доработки, затем narrow re-review. Reviewer не добавлял эти tests сам.
Разделение structural/authority остаётся правильным: empty degraded refs сами
по себе не доказывают prefix, а parsed sealed_normal не доказывает настоящий
нормальный package. Исправление тестов не разрешит effects без внешнего validator.

### SHA-256 source snapshot и предел доказательств

| Артефакт | SHA-256 |
| --- | --- |
| ProtectedCustodyMetadata.h | `bc5b665d0e28a10ade9b66e4c7966a8255055627746a1d0b5705343e4ed14f05` |
| ProtectedCustodyMetadata.cpp | `f8ad4a5ed733f803088e025e8de15a4f427e6f747241929a658dbadb9d646965` |
| ProtectedCustodyPackageTests.cpp | `e2c7526e17964efaa5c3dcae50ed42cb0d2c30a39806c91459f6e4cbe4287b6e` |
| CMakeLists.txt | `b0c2f16b2047d71f8e94395266e1c9b721b2f046ba7581ee5a893ac10d5aec8e` |

Main сообщил pre-parser RED clangsyntax444b70 exit1 по undeclared API и
завершённый old-source full49 terminal9afa53 total256.85s/source170 passed.
Reviewer не выполнял эти команды и не принимал старый49/49 как proof новых
bytes. Новые native/portable runs main ещё не предъявлены этому reviewer;
это source verdict, runtime NOT RUN reviewer. Competing tests не запускались.
Issue owner T116/#7444 сохранён; GitHub не запрашивался/не менялся.

Отчёт до append:47118B, SHA-256
`cb95a7475466c107bfa1c9da358c13e40de6e6298e0197beba13931ec6c9a80f`.
Единственная запись reviewer — это дополнение; код/test/CMake/нормы/tasks/
Git/GitHub/VM не менялись reviewer. Все прежние bytes и requirements12/0
сохранены. **Терминальный source verdict: REQUEST CHANGES, C0/H1/M0/L0;
T116 и product integration не приняты.**

## Повторный source review после расширения тестов — 2026-10-06

**SOURCE APPROVED для structural parser/serializer: C0/H0/M0/L0.**
Предыдущий source NO-GO сохранён как история другого test snapshot.
H-S251-1 закрыт в ограниченном source review; это не runtime PASS, не закрытие
T116 и не разрешение full product integration/working-profile installation.
Requirements markers неизменны:12 checked/0 unchecked.

### Что лично перечитано и почему снят H-S251-1

code-reviewer skill прочитан целиком. Расширенный test прочитан целиком;
packageShape/read/write вновь прочитаны, Metadata.h/CMake и прочий ранее
прочитанный Metadata.cpp сверены по неизменным hashes. Base:466–479 и
packed:305–319 лично перечитаны, hashes совпали. Canonical/HEAD остаются
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
`codex/200-windows-followup`, `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.

Новый test уже содержит valid packed live и nonempty sealed read/write
roundtrip; отказ без container, live extent, forbidden manifest role/schema1,
unknown representation; root/extent boundary, root version>generation,
nonempty EMPTY и length0/nonempty NODE conflict. Empty g1 root положителен
только со length0/extent32896 и не объявлен trusted prefix/normal capture.
Следовательно прежний полный пропуск нового packed package branch устранён,
а не замаскирован old FormatTests или old full49.

Schema-last положительный случай проверяет deferred masks при другом порядке
keys; missing opening brace отдельно rejected. Identity300 parse/write и301
refusal, sixth ref rejection, parsed/typed malformed triples остаются проверены.
Full charged pressure явно создаётся существующим CustodyAllocator:
reader остаётся allocation-free; writer возвращает allocationFailed без
accepted output, charge остаётся прежней до release, затем восстановлен.
Следующие ordinary/packed roundtrips используют write после снятия pressure.
Это проверка написанного test flow; выполнение reviewer не заявляет.

Остальные suggested mutations предыдущего review не объявляются все
исполненными: tests не являются exhaustive Cartesian matrix. Они не требуют
дублировать отдельный decoder/validator: reader и writer используют **тот же**
packageShape, capturing/finalizing — тот же active predicate, nested/root
objects — тот же decoded-key object/bitmask reader; wire reserved/alignment/
overflow проверяет переиспользуемый decodeReference. Лично проверенная общая
реализация плюс новые packed и allocator failure fixtures достаточны для
source approval. Fresh focused/native validation этого snapshot всё ещё нужна.

### Особая проверка phase/reason/short/ref

| Phase | Structural checks Metadata.cpp:63–67 | Не доказывает |
| --- | --- | --- |
| capturing / finalizing | canonical live обязателен; live triple весь null, sealed refs полностью stamped; short=false. Known reason grammar проверяется общим packageShape. | Actual paired live root/prefix и readiness. |
| sealed_normal | All refs sealed по общему nonactive rule; mask28 требует media+playback+manifest, reason=none/пустой wire, short=false. | Valid actual audio, positive duration, byte hashes или normal recording truth из одного JSON. |
| sealed_degraded | Nonempty known reason, short=false; live refs запрещены. | Trusted prefix; empty structural refs не дают upload/normal authority. |
| discard_pending | short=true, reason=none, sealed manifest обязателен; live refs запрещены. | Positive short predicate, actual protected manifest marker, право на discard/GC/delete. |

Такой structural gate не берёт на себя внешние short/prefix/manifest predicates
и согласован с принятой package-only границей; consumer обязан их независимо
проверять прежде effects. Нижний commit metadata IO flow не изменён и новые
API к нему/к product callers не подключены. No serialized proof/pin/authority.
Serializer reserve65536 сделан **до plaintext**, в старом charged allocator:
capacity не растёт и не освобождает unwiped старый plaintext buffer. Whole-size
limit остаётся65536, native/process quotas не увеличены.

### Снимок source / runtime остаётся отдельным

| Артефакт | SHA-256 |
| --- | --- |
| ProtectedCustodyMetadata.h | `bc5b665d0e28a10ade9b66e4c7966a8255055627746a1d0b5705343e4ed14f05` |
| ProtectedCustodyMetadata.cpp | `f8ad4a5ed733f803088e025e8de15a4f427e6f747241929a658dbadb9d646965` |
| ProtectedCustodyPackageTests.cpp | `6bb176332bceb6fd195d1eacb3c3ea4af827d029a03b819d3c30ab7397e9f3e6` |
| CMakeLists.txt | `b0c2f16b2047d71f8e94395266e1c9b721b2f046ba7581ee5a893ac10d5aec8e` |

Main сообщил portable build terminal56defc0/предыдущий40462-c27ebd0;
ранний b8e7391/1, начатый при LIVE build, не является final runtime evidence.
Новые focused/native runs после freeze пока не предъявлены reviewer.
Все эти сообщения отделены от личного source review: old49/49 не proof новых
bytes, нет собственного runtime PASS, competing runs не запускались.

Отчёт до этого append:55301B, SHA-256
`63e0196e9befaebc1d2018c1952a6388fb84d4928c510d818a5fcd82f316f9c7`.
Единственная запись reviewer — это дополнение, markers/старые bytes сохранены;
код/tests/CMake/нормы/tasks/Git/GitHub/VM не менялись reviewer. **Терминальный
вывод: SOURCE APPROVED C0/H0/M0/L0 для package structural codec;
full T116/consumer/migration/installed acceptance по-прежнему не приняты.**

## Exact-source подтверждение и ограниченный docs review — 2026-10-06

**SOURCE APPROVED и DOCS APPROVED в текущих ограниченных границах:
C0/H0/M0/L0.** Canonical HEAD остаётся
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; это HEAD с dirty source,
не commit новых parser bytes. Четыре лично повторно вычисленных hashes:

| Артефакт | SHA-256 |
| --- | --- |
| ProtectedCustodyMetadata.h | `bc5b665d0e28a10ade9b66e4c7966a8255055627746a1d0b5705343e4ed14f05` |
| ProtectedCustodyMetadata.cpp | `f8ad4a5ed733f803088e025e8de15a4f427e6f747241929a658dbadb9d646965` |
| Tests/GrafWindowsCoreTests/ProtectedCustodyPackageTests.cpp | `6bb176332bceb6fd195d1eacb3c3ea4af827d029a03b819d3c30ab7397e9f3e6` |
| CMakeLists.txt | `b0c2f16b2047d71f8e94395266e1c9b721b2f046ba7581ee5a893ac10d5aec8e` |

### Нулевая длина required refs и sealed_normal

Лично вновь прочитаны base §8.1:466–479, packed §6.1:305–319 и общий
packageShape. Base задаёт sealed length≤role bound и обязательные sealed
media/playback/manifest для sealed_normal; отдельного структурного lower bound
`length>0` для этих трёх refs в закрытой JSON-схеме не задано. Packed EMPTY
допустим только при length0, но не отменяет normal acceptance. Это не лицензия
на пустую normal recording: actual member bytes/hash/format, manifest и
подтверждённый префикс проверяются внешним validator до normal authority.

В разрешённом parser/serializer-only шаге принятое value с phase=sealed_normal
остаётся **структурным утверждением входа**, не доказанным normal package.
Следовательно отсутствие отдельного structural отказа для нулевых length
не объявляется дефектом этих двух файлов и не меняет SOURCE APPROVED.
Не добавляется новая норма нижней границы под видом source review. При consumer
adoption запрещено переносить phase/EMPTY в normal authority автоматически:
нулевые или недействительные обязательные члены не проходят actual normal
acceptance, даже если JSON структурно разобран. Одно `length>0` также не доказывает
нормальную запись. Это сохраняет прежнюю границу CHK007/CHK009 и не закрывает её
будущую реализацию. Degraded trusted prefix и discard positive short predicate/
protected manifest по-прежнему вне этого structural codec.

### Новый appendix quickstart

Лично целиком прочитан только новый раздел «Структурное описание защищённого
пакета — package.v1/v2» и сверена CMake registration всех пяти named targets,
включая Windows-only NativeCustodyProtectionFailureTests. Команды configure,
Release build с /nodeReuse:false и serial CTest имеют explicit exit checks,
anchored filter и timeout; результат требует5/5, source/EXE identity и actual
completion, не только PASS. Запрет competing runs и остановки чужих процессов
сохранён. Generated fixtures не подменены private audio/profile/migration.
Оговорки own structural value, charged reserve до plaintext, retained slots,
actual hashes/prefix/manifest/effects соответствуют прежнему approval.

Current quickstart SHA-256:
`f88d2931c59420ef74332f51f15952dd4a39f09b59457f1e0a6a9c3c0e060d08`.
Review этого appendix не означает повторную приёмку остальных dirty quickstart
разделов и не означает выполнение его команд reviewer. Spec/plan/tasks,
constitution и оба contracts лично сверены: прежние hashes неизменны.
Нормативная политика не изменена; requirements markers остаются12/0.
speckit-analyze/checklist и code-reviewer лично перечитаны; enabled pre/post
analyze/checklist hooks отсутствуют, git commit hooks disabled. Новые checklist
пункты, markers и нормы не создавались/не менялись.

### Runtime: main-reported, не own execution

Main сообщил final freeze80c093: portable package1/1 exit0; portable full
52039/b4295f/d8a13d terminal0,46/46,21.64s; native helper95925/0bb274/063a79
terminal0, configure/build/test0, focused5/5,7.84s. Эти результаты относятся
к сообщённому новому frozen source, а не old-source full49; reviewer не запускал
и самостоятельно не проверял terminal receipts/EXE в Windows.

Manifest source-package-round250.json лично прочитан: **171 entries**,
SHA-256 `a40ca7588c6f0114042a6306eabae5a62fd817b091dde276ddf31a8e8f091dfc`;
его четыре scoped entries совпадают с текущими canonical source hashes выше.
171 — число entries, не начало hash. Это личное source binding, не независимый
runtime PASS всех171 файлов. Full SDK/AppMain build73895 в последнем сообщении
main ещё LIVE; exit0 ему не приписывается. Нет запуска GRAF, install, private
audio/profile и working-profile acceptance. Competing builds/tests не запускались.

Remaining acceptance остаётся NO-GO: full T116, actual consumer/MF adoption,
paired retained slots/closure под владельцем, migration/GC/delete/effects,
protected manifest/prefix/short predicates, installed/profile и release gates.
Issue #7444 не закрыт этим review; GitHub не запрашивался и не менялся.

Отчёт до append:62050B, SHA-256
`ad33f8b1fe6882103aae9869bc6dbc8fbb682f22be6ea56d0a7adf4654ca44af`.
Единственная запись reviewer — этот append; прежние bytes и markers сохранены.
Код/tests/CMake/нормы/tasks/Git/GitHub/VM не менялись reviewer. **Терминальный
вывод: SOURCE/DOCS APPROVED C0/H0/M0/L0; full product integration NO-GO.**

### Терминальное сообщение main после docs review

Main затем сообщил Full actual SDK/AppMain build73895/81bb37/e312a8
terminal0, restore0/build0, source178 before/after hash check и pinned AEC
identity846fe… verified. Это обновляет прежний LIVE статус **по сообщению main**;
reviewer не выполнял сборку, не читал её terminal receipt/EXE и не удостоверяет
непредъявленный полный AEC hash по сокращению. Новый EXE не launch/sign/package/
install; final receipt reread ещё сообщён как запущенный, не как завершённый.

Терминальные обозначения владения доказательствами: requirements12/0 и
SOURCE/DOCS APPROVED C0/H0/M0/L0 — личный reviewer review текущих bytes;
portable1/1,46/46, native5/5 и full SDK restore/build0 — MAIN-REPORTED,
NOT REVIEWER-EXECUTED. Old49 не new parser acceptance. Full T116/#7444,
consumer/migration/installed/profile/release остаются NO-GO. Quickstart approval
ограничен новым package.v1/v2 appendix при SHA-256
`f88d2931c59420ef74332f51f15952dd4a39f09b59457f1e0a6a9c3c0e060d08`.
Отдельная новая норма zero normal data не открывается: прежний внешний
actual validation gate сохранён и не объявлен реализованным этим parser.

До этого append:68739B, SHA-256
`5c75fe02990c23660126f96ffd9fc92bc5bfab1fc7c245d587f463741f12f235`.
Разрешённый reviewer scope завершён без product/norm/task/Git/GitHub/VM edits.

### Последнее terminal update SDK — завершение limited review

Main сообщил final receipt20925/9acd25/24ea2e terminal0: source171 и пять
native EXE current match; SDK source178 all match, restore0/build0.
Сообщённый SDK EXE SHA-256:
`166f0ba8a311386a621810d1818a080fdb7f8ec3973957799187117d50f67843`.
Сообщённый SDK source manifest SHA-256:
`cf8f8ee62469c200640f024f9fdbb6676e1c5e66cf397d2e9b2e37f75f78f3d1`.
Это заменяет только прежний pending reread статус по сообщению main;
runtime/receipt/SDK EXE остаются MAIN-REPORTED, NOT REVIEWER-EXECUTED и
не объявляются лично проверенными reviewer. Новый EXE не запускался.

Limited SOURCE/DOCS APPROVED C0/H0/M0/L0 и requirements12/0 сохраняются;
H250-1/H250-2 не сняты. Full T116/#7444, consumer/migration/working-profile/
installed/release acceptance остаются NO-GO. Whole-feature audit, новые задачи,
сборки/тесты/VM действия не выполнялись. Единственная запись — этот append.
До append:70468B, SHA-256
`891ed772785dd0f478d16fd6e938b12fdc06585bacc79bca17170218a6d16f90`.
