# Независимая проверка дополнения FR-012 — 2026-10-01

Результат: **APPROVED NARROW — достаточность документационного покрытия**.
Блокирующих замечаний к этому дополнению не найдено; реализация **STOP / NOT READY**.
Область: только plan.md:811–875 и tasks.md:503–548 поверх
`99b00a579c24b50e320465b69d9a296038bc544d`; не полная проверка F200 или исходного кода.
Применены ранее прочитанные локальные speckit-analyze/speckit-tasks и проектные ограничения.

## Проверенные критерии и свидетельства

- FR-012 (spec.md:435–455): plan.md:827–830 и T116 (tasks.md:546) охватывают canonical/WAV/AAC, manifest/recovery, queue/deletion, quarantine и atomic temporary bytes до первой записи; inspect/hash/upload/playback сохраняют logical v5 bytes/ranges без открытой дисковой копии.
- T114 (tasks.md:544): отдельное синтетическое исследование совместимости DPAPI/index/seek/Media Foundation, памяти/IO/Stop и отказов; арифметические bounds не подменяют измерения и SC-003. Не включает устройства, рабочую миграцию или продуктовые классы.
- T115 (tasks.md:545): будущий contract определяет format/integrity/authority, concurrency/lifetime, bounded IO/GC, account/delete/shutdown fences и переход старого reader с owner/removal trigger; нужны независимый checklist review, актуальный analyze и taskstoissues до кода.
- T116 (tasks.md:546): полная защищённая цепочка через существующие владельцы; native/reuse, без новой БД/службы/библиотеки; сначала регрессии, disk/crypto IO не в UI/capture callback, отказ не создаёт пустой ledger или ложный успех.
- T117 (tasks.md:547): streaming copy с проверкой hash/length и durable intent до переключения authority; UUID/ranges/delete intent/purge acknowledgements сохраняются, проверяются restart boundaries и retirement старого reader, без автоматического уничтожения original.
- T118 (tasks.md:548): generated v5 → restart → inspect/hash/playback/seek → partial upload/reconcile → deletion/recovery; ciphertext-only snapshots, key/integrity/disk-full failures, 100 циклов, exact source/package/EXE и standard-user/offline/update/rollback. Не заменяет физическую аудиоматрицу.
- Приватность и границы удаления: plan.md:862–870 запрещают раскрытие ключей, plaintext fallback, новые пароли/admin prerequisites и неподтверждённые forensic/cryptographic-erasure обещания; непереведённый inventory не объявляется защищённым.
- Порядок исполнения явный: tasks.md:524–529; T114 → T115 → review → analyze → taskstoissues → T116 → T117 → T118, без [P]. Открытые clock/storage Phase0 и Phase1 не обходятся (plan.md:872–875).
- Все названные существующие Storage/Recording/Upload/AppMain владельцы, три каталога тестов, validate-audio-contract.ps1 и research/data-model/quickstart существуют. Новый windows-protected-local-custody.md — результат T115, не уже принятый contract.
- Прежние 113 задач, их текст/отметки и исходная часть плана побайтно совпадают с HEAD; дополнения только в конце. Всего 118 уникальных task IDs: 91 checked, 27 unchecked; T114–T118 все unchecked. Новые задачи дополняют, не заменяют T009/T022/T037/T038 и T063/T071/T083/T087/T088/T094–T096; дублей нового результата не найдено.
- Новая таблица tasks.md:533–542 явно связывает восемь FR/SC с пятью задачами; существующие чеклисты и constitution не изменены относительно HEAD. Их 112 пунктов заново не проверялись и здесь не принимают будущий защищённый формат.

## Привязка и оставшиеся условия допуска

SHA256 plan.md: `7c32bca2821465a4b052839e0790b0b7938b1215c154b6c6e97f5206f19643d0`.
SHA256 tasks.md: `2019b804de49724efbb6e6bf31f6faa490b10c1869ff88ba6a26aa889c6e0655`.
SHA256 spec.md: `9f7e0d9ca96c6be1209af723e5fad0745a9b78cf8314f2b2996d6697de5c20b2`.
Открыты: combined proof T114, принятый contract T115, последующие reviewer-owned проверки, текущий analyze и связь с issues. Старый analyze не доказывает готовность нового contract; этот узкий отчёт его не заменяет.
Документарная достаточность не завершает Phase0/Phase1, не разрешает protected-storage code/миграцию и не принимает checkpoint, всё приложение, merge или release. Тесты, VM, UI и устройства не запускались; изменён только этот reviewer-owned отчёт, никаких отметок не поставлено.
