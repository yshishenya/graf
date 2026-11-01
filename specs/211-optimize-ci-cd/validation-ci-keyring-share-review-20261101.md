# F211/T114 — независимое ревью требований share0777

Дата: 01.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Исходная версия по поручению: `fbb5604c2ba0f03255bf9ede3c23882015cbbecd`.
Полоса: before-code requirements review дополнения активного Spec Kit среза.

**PASS: 5 пунктов отмечены / 0 открыты; P1/P2/HIGH — 0/0/0.**
Реализация share repair ещё не проверена; новых code/test изменений нет.

## Основания по пунктам

1. Последние spec/plan/tasks sections полностью прочитаны. Native наблюдение
   run41258703244 (share root:root0777, usr/root0755) отделено от неизвестной
   причины и пока не проверенного runner key pin. Разрешено только exact
   nonsymlink directory root:root0777→0755 для share и прежнего key parent.
   Root/usr всегда проверяются до key read, даже при безопасном key parent,
   никогда не исправляются. Прочие dangerous modes/owner/group/type/links
   сохраняют отказ с bounded metadata. Никакой рекурсии/listing/chown нет.
2. Snapshots обоих каталогов фиксируются до key read. При любом repair
   ключ должен быть regular/root:root/3607bytes/mode0644 либо0777 и совпасть
   с прежним точным official pin. Source полностью проверяется/парсится,
   canonical ограничивается до первой записи. Unknown644 и malformed source
   не вызывают изменения каталогов/key/source. Никакого нового trust,
   загрузки эталона или вычисления production pin из входа не разрешено.
3. Прежний O_DIRECTORY/O_NOFOLLOW fd блок применяется только к требующим
   ремонта snapshots строго share→key parent. Полный исходный fingerprint
   сверяется перед fchmod следующего fd. Поэтому child, изменённый во время
   ещё writable share, не принимается по обновлённому снимку. После chmod
   обязательны fsync/fstat/path identity readback и закрытие fd в finally;
   затем повторные key/source bytes/fingerprint. Shared I/O guards и новый
   changed-child после первого fsync должны доказать отказ второго fd.
   Частичное ужесточение при ошибке не выдаётся за откат; никакие следующие
   APT/npm/Playwright не допускаются.
4. Даже repair только share при безопасном key parent и key0644 требует
   прежнюю atomic replacement root:root0644 с новой inode. Это защищает от
   старых открытых writable fd и не доверяет исходному каталогу только по
   последующему chmod. Прежние temp/fsync/rechecks/readback/cleanup сохраняются.
   Если оба каталога и ключ безопасны, bytes/inode/mtime не меняются и
   будущая безопасная версия ключа не ограничивается старым hash. Source,
   package tuples, Signed-By, сторонние файлы и три callers прежние.
5. Требуются existing runnable RED→focused/whole/static, независимое code
   review/converge и конечные exact native gates того же draft. Новые
   позитивные комбинации share0777/key-parent0755 либо0777/key0644 либо0777,
   repeat и негативные unknown644/malformed-source/changed-child заданы
   явно. Unsupported ancestor отрицательный случай остаётся0775, так что
   он не превращается в новый позитивный допуск. Before-code analyze и
   sync #7859 не пропускаются. Новых модулей/workflow/configuration/
   dependencies нет. Full, production, F273/T0 и коммерческие AC отдельно.

## Применимые зависимости и границы

Прочитан прежний fd/atomic key replacement блок helper, новый checklist,
полные затронутые spec/plan/tasks sections и применимые T112–T114 ограничения.
Проверены совпадающие хеши ранее полностью прочитанных constitution,
product-gates, Spec Kit flow и release guidance по разрешённому владельцем
повторному чтению F211. Constitution III/VI before/after PASS согласуется
с узким восстановлением прав тех же pinned public bytes: новое доверие,
продуктовые данные, permissions CI и выпускные gates не добавляются.

Key_parent и share изначально недоверенные по правам до их закрытия;
требование исходного child snapshot и полной atomic key replacement
сохраняет прежнюю границу доверия. Root/kernel compromise остаётся вне
этого требования; root/usr защищены и не являются объектом ремонта.

Native наблюдение прочитано из evidence исполнителя, самостоятельно не
повторялось. Проверяющий не запускал код, тесты, сеть, Git/GitHub, серверы,
APT/root или выпуск. Изменены только назначенный checklist и этот report;
чужие изменения сохранены. Требования/код/тесты не менялись.
Checklist фактически перечитан после отметок: **5 отмечены / 0 открыты**.
Ни реализация/native успех, ни key hash runner, merge, Full/production/
F273/T0/коммерческие критерии этим заключением не принимаются.

## Хеши состояния до кода

- `specs/211-optimize-ci-cd/spec.md`: `810b1d21e655d609bb0c2ffec02c6b324efdd9d5b42d30d449ec411595d1d65f`.
- `specs/211-optimize-ci-cd/plan.md`: `9daa3ee8c10b9163df8536c2385700a32e8255b1e37926fa3124bcb026f551e7`.
- `specs/211-optimize-ci-cd/tasks.md`: `5ce513d6fd97a2a8d7482263afb85b2c1a3ead1a802b48c6704c824a099a5c9a`.
- `infra/scripts/prepare-ci-apt.sh`: `9330c5a53fd1025db74aa014e5371607ec40a7fa681aa4156ed24ee06ec04b0d`.
- `tests/governance/test_governance_workflow.py`: `eab71f505076ada14ec0a9d8a9facac72b5e1e25b8dc7d247d635716c399d96f`.
- `.specify/memory/constitution.md`: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- `docs/agent-guidance/product-gates.md`: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- `docs/agent-guidance/spec-kit-flow.md`: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`.
- `docs/agent-guidance/release-and-validation.md`: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`.
