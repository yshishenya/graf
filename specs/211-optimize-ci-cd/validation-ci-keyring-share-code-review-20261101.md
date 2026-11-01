# F211/T114 — независимое ревью реализации share0777

Дата: 01.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Полоса: реализация принятого Spec Kit среза share0777; только чтение кода
и журналов исполнителя, без запуска тестов/сети/сборок/GitHub/серверов.

**Итог: scoped implementation PASS; P1/P2/HIGH — 0/0/0.**
Найденный safe-child/share-only P2 исправлен и повторно проверен; whole528
и static8 завершены на окончательных hashes. Ниже сохранена история первого
HOLD0/1/0, требования к исправлению и его доказательства. Native/exact PR/
merge/Full/F273/T0 этим заключением не принимаются.

## P2 — проверить safe child до создания root temp

`infra/scripts/prepare-ci-apt.sh:136–162`: цикл skips исходно safe0755 child,
когда repair нужен только share. После fchmod share повторно проверяются
key/source bytes и fingerprints, но не lstat child-directory. Прежняя
проверка key_parent identity происходит лишь в строке170, после создания,
chown/chmod/write/fsync временного файла через путь этого каталога.

Непривилегированный процесс мог заменить child в ещё writable share между
последним fstat share и его fchmod. Последующая directory readback сравнивает
fd/path уже после изменения и не принимает исходный child snapshot за gate.
Key snapshot сам по себе не доказывает directory identity: тот же pinned
inode может быть виден через перенаправленный parent (например, сохранённый
каталог через ссылку либо заранее созданный hardlink writable key inode).
В результате root temp создаётся в parent, который ещё не подтверждён как
исходный защищённый nonsymlink root-owned каталог. Поздний guard перед
replace блокирует подмену итогового ключа/APT, но не отменяет уже выполненную
запись temp через недоверенный путь. Это нарушение принятого protected-parent
свойства; произвольная подмена ключа доверия этим review не утверждается.

Исправление: после закрытия записи в share, до повторных key reads/temp
создания, сравнить child directory с исходным snapshot и безопасными metadata
даже если он сам не требовал fchmod. Для repaired child использовать его
проверенный secured snapshot. Не обновлять исходный child snapshot по
непроверенному lstat. Добавить safe-child mutation/identity regression во
время fsync share: отказ до key temp/write/replace, следующие действия не
запускаются. Код проверяющий не менял, замечание передано исполнителю.

## Прочая проверенная логика

Exact repair_share ограничен root:root directory0777. Root/usr проверяются
и не изменяются. При любом repair metadata/pin ключа и source/canonical
проверяются до записи. Порядок fd repair share→key parent сохранён;
исходный unsafe-child fingerprint проверяется перед его fchmod. Любой repair
включает atomic new key inode0644, включая share-only/key0644. Прежние temp
cleanup, failure exit, source/package tuples/three-callers сохраняются.
Safe path не pin-ит будущий безопасный key старым hash. Новых зависимостей,
workflow/configuration и абстракций нет; прежний fd block переиспользован.

## Журналы на момент замечания

Прочитаны `share-red.log`:12failed/6passed/507deselected/6.84s;
`share-green.log`:84passed/441deselected/31.25s; `share-static.log`:8 EXIT0.
Полный `share-module.log` ещё выполнялся, содержал3FFF, итога не было.
Причину этих трёх ошибок reviewer не угадывает; окончательный whole/static
нужно перечитать после исправлений и привязать к новым hashes. Журналы
исполнителя не являются самостоятельно запущенными reviewer тестами.

## Границы действий и хеши исходного review

Изменён только этот отчёт. Чужие изменения сохранены. Requirements/checklist,
код/тесты/Git/GitHub/сервер/выпуск не изменялись. Native pin/Prepare, final
exact PR gates, merge, Full/runtime/F273/T0 и коммерческие AC не приняты.

- `infra/scripts/prepare-ci-apt.sh`: `8d1361e018f85cea78ad5f6b56a421ca580bd896cac2caf7640fbc7194f342c9`.
- `tests/governance/test_governance_workflow.py`: `b64b85db9642e70a21fb26287183d09120f39ab4c037c621bf25dfb63bd05dcf`.
- `specs/211-optimize-ci-cd/spec.md`: `810b1d21e655d609bb0c2ffec02c6b324efdd9d5b42d30d449ec411595d1d65f`.
- `specs/211-optimize-ci-cd/plan.md`: `9daa3ee8c10b9163df8536c2385700a32e8255b1e37926fa3124bcb026f551e7`.
- `.dev/ci-official-sources/share-red.log`: `88d2c4c01abcf4c723d8c7a00069c797b28524052ba9cc3c8eea04d4da74579d`.
- `.dev/ci-official-sources/share-green.log`: `84e0673c6b2fc58401c8fa4a77a89e5bb8d3b2bf92b534e9d89433e662cce3a6`.
- `.dev/ci-official-sources/share-static.log`: `19f10699a987ca252a9a9c7b1173b826a11984e73b9ef7b728daadff1b29be2e`.

## Before-code review уточнения P2 и fixture filename

Полностью прочитаны сохранённые последние уточнения spec/plan после
замечания. **Requirements PASS уточнения; P1/P2/HIGH требований — 0/0/0.**
Исходный код helper/test пока имеет те же проверенные hashes.

Требование явно закрывает найденное окно: exact key_parent fingerprint
проверяется после directory loop до повторных key/source reads и любого
key temp. Это распространяется на safe child, пропущенный fd loop.
Для repaired child сравнение использует уже проверенный secured snapshot;
для safe child исходный снимок не обновляется неподтверждённым lstat.
Regression наблюдает key-temp attempt, а не только поздний failure,
поэтому новый тест отличит правильный отказ до записи от прежнего170 guard.
RED должен быть показан до добавления минимального pre-read guard.

Fixture-only filename `<prepare-ci-apt>` соответствует характеру native
`<stdin>`: исключает показ root-model source через linecache, без изменения
production exception и без ослабления private-marker assertion. Это
узкое исправление исполняемой модели, не обход защиты stdout/stderr.
Фактический test diff и новые результаты ещё должны быть прочитаны.

Прочитан завершённый прежний whole: **522passed/3failed/204.83s**;
ошибки — три missing-source callers. Он не считается GREEN. Требуются
новые focused/whole/static и независимое after-code review. Начальный P2
по реализации остаётся открытым до фактического guard и regression.
Никакой native/exact PR/merge/Full/F273/T0 приёмки этим дополнением нет.

- `specs/211-optimize-ci-cd/spec.md`: `db7225cf16a1e4ee75508fc08b18effc4f24eee549dd917c418660316d3a2456`.
- `specs/211-optimize-ci-cd/plan.md`: `c41dc31ab2c862957e08760e20ecde92524186ee83eb5b59851efc635ae99c00`.
- `.dev/ci-official-sources/share-module.log`: `780482fb63187982e953bd019dad3c0509f533bea02453ff0b99a2db8339b765`.

## Повторное чтение исправления P2

Фактический guard добавлен непосредственно после directory loop и до
повторных key/source reads и NamedTemporaryFile: полный fingerprint
`keyring.parent.lstat()` должен совпасть с `key_parent`. Для repaired child
это ранее проверенный secured snapshot, для safe child — исходный снимок.
**P2 по source закрыт; текущий source PASS, P1/P2/HIGH — 0/0/0.**

Новый safe-child-changed case начинает с share0777/child0755/key0644,
во время fsync share меняет child в0777. NamedTemporaryFile обёрнут
наблюдателем, пишущим key-temp event; общий assertion допускает только
mirror, поэтому поздний отказ после создания temp больше не даёт PASS.
Прочитан `share-child-red.log`:3failed/525deselected/1.44s на прежнем коде.
Прочитан `share-child-green.log`:24passed/504deselected/11.12s после guard и
fixture filename fix. Новый тест и сохраняемый privacy assertion прочитаны.
Compile использует `<prepare-ci-apt>`; production exception не менялся.

Окончательные whole/static для этих новых hashes пока не приняты этим
разделом; предыдущий522PASS/3FAIL остаётся неуспешным историческим прогоном.
Новые результаты нужно перечитать отдельно, не объединять со старым84PASS.

- `infra/scripts/prepare-ci-apt.sh`: `4aa4f2aa7ccaaa5f1b8010d04d662290afa6871a89142cd3fa1155bc3ed010a1`.
- `tests/governance/test_governance_workflow.py`: `bd7f3f0720f68b8e628c89f47f6f6390332bd09c6eee331e7fd6c6f5f1cfb0b9`.
- `.dev/ci-official-sources/share-child-red.log`: `62019f4c00ee96d736cbc038102ab58de1f64a7a5a3db6a8c9961451afa78d85`.
- `.dev/ci-official-sources/share-child-green.log`: `3636674c24ade861a82d0a2156b31e082c8ce08330a5f80a15d977a2752f3ffc`.

## Окончательное заключение после whole/static

Завершённые `share-final-module.log` и `share-final-static.log` фактически
перечитаны. **Whole:528passed/0skipped/204.72s; static:8 команд EXIT0.**
Текущие hashes helper/test совпадают с переданными неизменными hashes
прогона и повторно проверенным кодом. Восемь команд проверяют Bash syntax,
Ruff helper/test, actionlint двух прежних workflow, development-process,
workflow self-test, Spec Kit governance, changelog fragments и diff check.

**Открытых замечаний P1/P2/HIGH — 0/0/0; P2 закрыт.** Причина закрытия:
полный fingerprint child проверяется до повторных reads/temp даже в safe
child ветви; RED3→GREEN24 и общий528 подтверждают отказ до temp, сохраняя
старые кейсы. Fixture filename исправлен узко; проверка отсутствия private
marker сохранена и проходит, включая прежние missing-source callers.
Первый whole522PASS/3FAIL не переименован в успех: его журнал и hashes
сохранены исторически. Финальный528 является отдельным новым полным
прогоном, а не суммой старых focused результатов.

Проверка избыточности: прежний fd block переиспользован, добавлен один
конкретный guard и наблюдаемый regression; новых механизмов/configuration/
dependencies не требуется. Удалять snapshot/pin/readback gates ради
сокращения нельзя: они обеспечивают прямо принятые свойства безопасности.

Проверяющий изменил только этот отчёт. Сам тесты/сеть/сборки/APT/root/
GitHub/серверы не запускал. Runtime/native hosted metadata и key pin ещё
не доказаны; source/локальная модель не заменяют следующие converge,
exact-SHA PR gates, merge, Full, штатный выпуск и F273/T0. Коммерческая цель
трафика и продаж этим техническим срезом не принимается.

### Окончательные проверенные хеши

- `infra/scripts/prepare-ci-apt.sh`: `4aa4f2aa7ccaaa5f1b8010d04d662290afa6871a89142cd3fa1155bc3ed010a1`.
- `tests/governance/test_governance_workflow.py`: `bd7f3f0720f68b8e628c89f47f6f6390332bd09c6eee331e7fd6c6f5f1cfb0b9`.
- `.dev/ci-official-sources/share-final-module.log`: `cf0b3d0a4f71b1fb88668553805f8b0076a86bec36773c59e90481b83e34a5b9`.
- `.dev/ci-official-sources/share-final-static.log`: `55dfffd7cb6c739b80527cd5c0b2123974b23eb42e04e8f1213ede904706d900`.
