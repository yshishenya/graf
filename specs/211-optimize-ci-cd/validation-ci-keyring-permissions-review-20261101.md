# F211 T114 — независимое ревью требований до кода, 01.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Непосредственно проверены ветка `codex/f211-ci-native-metadata-20261101`,
HEAD `ebb720844e9a52f4c80b535fc9f8050508a8729e`, активный указатель
F211/T112–T114 и отсутствие изменений code/helper/test/YAML T114.

**PASS качества требований: 5 checked / 0 unchecked.** Открытых блокеров и
замечаний P1/P2/HIGH — **0/0/0**. Это проверка проекта до кода; исходники
будущего исключения и actual native result ещё не приняты.

## Основания по пунктам

1. Полностью прочитан `validation-ci-keyring-sources-20261101.md`. В нём
   фактический отказ PR7863/run41255823281/job124698702639 отделён от
   эталона: наблюдались type32768/uid0/gid0/mode777/size3607, но runner hash
   и происхождение прав неизвестны. Приведены точные официальные HTTPS URL
   старого deb и project key, одинаковые SHA256/size, metadata root:root0644,
   hash/size самого deb и отдельный отличающийся новый пакет. Spec не выдаёт
   совпадение старого пакета и project key за доказательство runner bytes.
   Исследование владельца прочитано как metadata evidence; проверяющий
   архивы/ключи повторно не скачивал и не устанавливал.
2. Новое исключение задаётся только для фиксированного штатного keyring,
   обычного нессылочного файла root:root/0777/3607 и точного SHA256
   `80a36b0a6de2f69f49d2df75ef473ccde121e9e190b9ea01d20a4f63778d5c31`.
   Parent root-owned и защищён от записи посторонними. Иные опасные modes,
   owner/group/type/size, source0777, неизвестный hash и подмена сохраняют
   отказ. Уже безопасные файлы остаются на прежней ветви, поэтому новый
   безопасный официальный ключ не блокируется старым pin.
3. Spec/plan задают ограниченный снимок через O_NOFOLLOW с lstat/fstat
   fingerprints до/после чтения, точную проверку pin, отдельный temp в том
   же parent, root:root0644, write/flush/fsync, повторные проверки исходника
   и parent до replace и metadata/bytes/hash readback с cleanup. Новая
   inode исключает дальнейшую запись через старый открытый fd. Chmod
   writable inode или загрузка заменяющего ключа не разрешены. Ошибка
   после replace блокирует продолжение и не выдаётся за выполненный откат.
4. План сохраняет прежние platform/key trust/source/parser/package tuples/
   callers и безопасную key ветвь без записи. Runtime не скачивает эталон,
   не вводит новые зависимости/workflow, не меняет bytes/Signed-By/настройки
   доверия или продуктовые данные. Будущий native успех доказывает только
   совпадение с hardcoded pin при выполнении этой проверки.
5. Spec/tasks/quickstart определяют RED в прежнем actual-shell тесте трёх
   callers, whole GREEN, known0777 success+repeat, unknown/tampered/source/
   owner/group/mode/type/size/parent/races/read/write/replace/readback отказы
   и temp cleanup. Pin подменяется в локальной модели только на заранее
   известный hash учебных bytes, production pin не вычисляется из входа.
   Сохранены static/process, independent code review/converge, draft7863,
   реальная проверка actual bytes и конечные exact gates. Draft failure
   не принимается за merge readiness; Full/T0/коммерческие AC отдельны.

## Уточнение порядка записи

Во время ревью владелец явно конкретизировал пересечение с T112 «весь вход
до записи». Полностью перечитаны изменённые T114 sections spec/plan:
начальное чтение known key0777 возвращает только проверенный snapshot и
metadata, не меняя файл. Source проходит полную проверку/разбор, canonical
ограничивается до любой записи. Лишь затем выполняется атомарная нормализация
ключа, после неё прежняя запись source.

Это сохраняет прежний prewrite договор: malformed/unsafe source не вызывает
key write. При implementation review нужен исполняемый combined сценарий
known-key0777 + invalid source, подтверждающий эту границу вместе с прежней
матрицей. Это требование уже следует из явного spec, а не новое расширение
области. Идентичность и защищённые права parent фиксируются до snapshot и
проверяются перед replace; источник не меняется по одному предположению о
metadata настоящего runner.

## Прочитанные зависимости и ограничения

Полностью прочитаны новые T114 spec/plan/tasks/quickstart/checklist и source
report; текущий helper перечитан. Применимые T112/T113 guard, atomic write,
model/native и draft failure ограничения сохранены из прежнего полного
чтения. По разрешённому владельцем повторному чтению F211 хеши constitution,
PRD, merged status, product-gates и guidance совпали с ранее прочитанными.
Constitution III/VI before/after PASS в plan согласуется с независимой
оценкой: нет нового доверенного содержимого, подписи APT и обязательные
checks не ослабляются, изменение ограничено восстановлением безопасных
прав точного публичного файла на одноразовом runner.

Изменений T114 code/helper/test/YAML ещё нет, их хеши совпадают с T113.
Checklist перечитан после отметок: **5/0**. После данного gate обязательны
актуальные analyze и sync #7859, затем RED и только описанная реализация.
Если настоящий hash не совпадёт, это останется отказом, а не основанием
расширить pin/owner/mode исключение без нового проекта и ревью.

Проверяющий не запускал тесты/сеть/CI/APT/серверы, не менял Git/GitHub/code/
spec/plan/tasks/governance/release/deploy. Изменены только назначенные
checklist и этот report, чужие изменения сохранены. Реальный hash runner,
реализация, native PASS, exact PR gates/merge, T112–T114/#7859, Full/CD/
runtime/T0 и трафик/продажи этим заключением не приняты.

## Хеши принятого проекта

- Spec: `89e11bf1036c29ed05615227b6f85dd507061efa61df13a76496b62b1bbe2633`.
- Plan: `4719d1f7ca0f1d9f9a410ab541108ef2d053a3804161693f22f7ec7572a28a82`.
- Tasks: `ac930313c676027c11d02d11836ee780f0ef932589618f445ffc66b28774e245`.
- Quickstart: `9e8137192a50d977d4c1ac8ff46cf2948778a665eb4a3543543b2f893e181a8d`.
- Official source report: `631f0cca9d7159cdbc8a9b2df0c5214125c6a71f55aa7675381c26c7c3a937ea`.
- Неизменный helper: `b16a0c322e976a03c55cd60560e96b82bb97f2fce077a06951262118019d195f`.
- Неизменный test: `47a509fceddc090b652f05cc8287942f63cbf61940e5959958960b4eee4a2861`.
- Неизменный governance-fast: `dfd738473dc9f8f47ea1a6c9e8e5f64dfcfda9e0fceb676a21a4995925dee258`.
- Конституция: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- PRD: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- Merged status: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- Product gates: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- Spec Kit flow: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`.
- Release guidance: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`.
- Development process: `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864`.
