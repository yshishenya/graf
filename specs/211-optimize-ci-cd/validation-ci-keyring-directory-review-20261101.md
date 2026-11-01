# F211/T114 — независимое ревью требований directory0777, 01.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Полоса проверки: дополнение действующего Spec Kit среза FR-057/SC-025,
ревью требований до кода. Подтверждены ветка
`codex/f211-ci-native-metadata-20261101` и HEAD
`08329a279f80bae9935405b511cdb63026ba7092`.

**PASS: 5 пунктов отмечены, 0 открыты; P1/P2/HIGH — 0/0/0.**
Это приёмка требований; реализация и фактический успех CI не приняты.

## Основания по пунктам

1. Spec отделяет наблюдение run41257402120/job124703432330
   (directory type16384 uid0 gid0 mode777) от неизвестного происхождения
   прав и пока не установленного hash ключа runner. Допуск ограничен точным
   `/usr/share/keyrings`, обычным нессылочным каталогом root:root0777,
   защищёнными нессылочными root-owned `/usr` и `/usr/share` без записи
   group/other. Прежние platform/environment/root ограничения T112 остаются.
   До первой записи обязательны полный разбор source, ограниченный canonical
   и точный официальный pin root:root regular ключа3607bytes mode0644 либо0777.
   Другие metadata/hash/ancestors отказывают. Hash не выводится из входа.
2. Проект требует открытия каталога O_DIRECTORY/O_NOFOLLOW, совпадения
   fstat с исходным fingerprint, fchmod только проверенного fd в0755,
   fsync, проверки fstat/path identity/mode/owner. После ужесточения повторно
   сверяются bytes/fingerprint source и ключа. Ошибки останавливают дальнейшие
   APT/npm/Playwright; уже выполненное ужесточение не выдаётся за откат.
   Защищённые предки предотвращают замену самого каталога непривилегированным
   процессом; новые права закрывают изменение имён внутри каталога. Root/kernel
   compromise остаётся вне прежней границы доверия одноразового runner.
3. После repair directory атомарная замена pinned key обязательна и для
   исходного0644: один chmod каталога не защищал бы ключ от уже открытого
   writable fd. Используется прежняя новая inode root:root0644 с теми же
   проверенными bytes, temp/fsync/rechecks/readback/cleanup и обновлённым
   снимком parent. Запрещены chmod inode ключа, chown, рекурсия, сеть,
   runtime загрузка эталона и новые зависимости/workflow. При безопасном
   каталоге прежняя безопасная ветвь остаётся no-op; безопасная будущая версия
   ключа не привязывается к старому hash. Source/Signed-By/package tuples,
   сторонние файлы и три существующих callers не меняются.
4. Spec/plan/tasks/quickstart требуют расширить существующий исполняемый
   тест трёх настоящих callers: сначала RED, затем whole GREEN; оба known-key
   modes0644/0777 и repeat, unknown hash, invalid source, dir owner/group/
   type/mode, unsafe/symlink ancestors, open/identity/chmod/fsync/readback
   ошибки и изменения key/source до/после ужесточения. До отказа по исходно
   некорректному входу directory/key/source должны остаться прежними; после
   частичного ужесточения любая ошибка запрещает следующие действия.
   Существующая root-model fixture расширяется явно, не подменяя production
   pin вычисленным из входа. Локальная модель не доказывает реальные права
   и bytes hosted runner. Реальный Prepare должен проверить ту же константу.
5. Область ограничена прежним helper и существующим модулем тестов;
   требования сохраняют before-code review → analyze → sync #7859 → RED →
   реализацию → whole/static → independent code review/converge → тот же
   draft7863 и конечные exact-SHA gates. Промежуточный native отказ не даёт
   merge/PASS. Full не запускается ради диагностики; выпуск, runtime,
   F273/T0 и коммерческая цель принимаются отдельно.

## Прочитанные зависимости и границы доказательства

Полностью перечитаны новые и применимые T114 sections spec/plan/tasks/
quickstart, checklist, T112/T113 условия до записи, официальный source report,
текущий helper и применимая root-model fixture. Проверены guidance index,
прежний requirements review и хеши ранее полностью прочитанных constitution,
PRD, merged status, product-gates, Spec Kit flow, release guidance и
процесса разработки: они совпадают. Использовано разрешённое владельцем
повторное чтение F211: затронутые разделы полностью, неизменные зависимости
по хешам. Оценка constitution III/VI before/after PASS согласуется с проектом:
нового доверенного содержимого/продуктовых данных нет, APT authentication и
обязательные выпускные проверки не ослаблены.

Native metadata и происхождение официального pin прочитаны по evidence
исполнителя; проверяющий не подключался к GitHub, не скачивал архивы и не
повторял наблюдение runner. Изменений helper/test/YAML относительно HEAD
на момент review нет. Checklist после отметок фактически перечитан и подсчитан: **5 отмечены /
0 открыты**. Проверяющий изменил только назначенные
checklist и этот report; чужие изменения spec/plan/tasks/quickstart сохранены.
Тесты, сеть, CI, APT, Git/GitHub mutations, серверы и выпуск не запускались.

## Контрольные суммы принятых файлов

- `specs/211-optimize-ci-cd/spec.md`: `1c19d388d4a4b55176cdf4fd497a41d948bdbe485fba7514f2a89fc1aa21f487`.
- `specs/211-optimize-ci-cd/plan.md`: `2d7579fd953a3ce4cc3cc04fbedf73d790ea07f9d256f72b9da0883be147cc4a`.
- `specs/211-optimize-ci-cd/tasks.md`: `d3e0eef8cb36488567c40f1d052a98191c84904dce69dc5d8c0ae53d85cc7d2d`.
- `specs/211-optimize-ci-cd/quickstart.md`: `6fc37e4926b9b901ceb060111048b1b9a913e3678e3b228a143c2bcf8938f8da`.
- `specs/211-optimize-ci-cd/validation-ci-keyring-sources-20261101.md`: `631f0cca9d7159cdbc8a9b2df0c5214125c6a71f55aa7675381c26c7c3a937ea`.
- `infra/scripts/prepare-ci-apt.sh`: `2f7b24b90edf3d0be8d5a498c1d055c79787ea0bc4f37899531688eca2d36b8e`.
- `tests/governance/test_governance_workflow.py`: `0d5248820e4beb21bc026075b7d7d8daeffe059c288169c5af614292f8747f2d`.
- `.github/workflows/governance-fast.yml`: `dfd738473dc9f8f47ea1a6c9e8e5f64dfcfda9e0fceb676a21a4995925dee258`.
- `.github/workflows/release-full.yml`: `e3342f96e9afd335892f5d850a7e03c2cee2264a4c20a9738ac5e5977472bb5a`.
- `.specify/memory/constitution.md`: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- `docs/prd-voice-layer-final.md`: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- `docs/current-product-status.md`: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- `docs/agent-guidance/product-gates.md`: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- `docs/agent-guidance/spec-kit-flow.md`: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`.
- `docs/agent-guidance/release-and-validation.md`: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`.
- `docs/agent-guidance/development-process.md`: `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864`.
