# F211/T114 — независимое ревью реализации directory0777

Дата: 01.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Полоса: независимая проверка реализации принятого Spec Kit среза,
до окончательных проверок PR/выпуска.

**Scoped source PASS; открытых P1/P2/HIGH — 0/0/0.**
Замечаний, требующих изменения кода в проверенной области, не найдено.
Это не приёмка native CI, выпуска, F273/T0 или трафика/продаж.

## Предмет и результат

Повторно полностью прочитаны применимые T114 sections spec/plan, затем
фактический helper целиком и diff/окружение существующего исполняемого теста.
Прежний requirements checklist принят 5/0; требования spec/plan совпадают
с хешами независимого before-code ревью. Чужие изменения сохранены.

- `infra/scripts/prepare-ci-apt.sh:62`: исключение разрешает только regular
  directory root:root с точными правами0777. Прежний guard остальных
  unsafe metadata сохраняется. Проверка предков работает только для этой
  ветви: root-owned, directory, без group/other write. Symlink отказывает.
- Строки73–77: прежний bounded NOFOLLOW key snapshot дополняется exact
  uid/gid/size/mode и прежним literal official SHA256 для directory repair.
  Pin обязателен и для исходного key0644. Значение production pin совпадает
  с принятыми требованиями; оно не вычисляется из неизвестного входа.
- Строки78–123: source целиком проверяется и canonical ограничивается до
  первой записи. Исходно invalid source или unknown key не меняют каталог,
  ключ или source. Нет сетевой загрузки, chown каталога/ключа, рекурсии либо
  изменения Signed-By/пакетных сочетаний/сторонних файлов.
- Строки124–142: O_DIRECTORY/O_NOFOLLOW, полный fingerprint fd против
  исходного снимка до fchmod, затем0755/fsync/fstat/path identity; fd закрыт
  в finally. После закрытия записи в каталог повторно проверяются bytes и
  fingerprint обоих входных файлов. Необработанные I/O ошибки и fail дают
  ненулевой исход; shell set-e и прежние callers не выполняют APT/npm/
  Playwright. Частичное ужесточение не называется откатом.
- Строки143–162: repair_parent безусловно выбирает прежнюю atomic key
  replacement, включая исходный0644. Temp в уже защищённом parent,
  root:root0644, flush/fsync, повторная проверка исходника/parent, replace,
  finally cleanup и bytes/metadata readback. Новый inode отсекает ранее
  открытые writable fd старого ключа. После собственного temp допустимо
  изменение timestamps parent, но identity/mode/uid/gid guard сохранён.
- Safe branch при repair_parent=False остаётся прежней: дополнительных
  чтений предков/нового pin для безопасного ключа нет. Ключ0777 при уже
  безопасном parent сохраняет ранее принятую узкую ветвь. Source atomic
  write и все три caller не менялись; повтор нормализованного состояния
  не заменяет ключ/source.

Граница доверия прежняя: одноразовый GitHub-hosted Ubuntu24.04/amd64 с
root-owned защищёнными предками, без предположения защиты от root/kernel
compromise. Непривилегированный процесс не может заменить каталог через
защищённый `/usr/share`; после fchmod он теряет запись имён внутри него.
Изменение старого key inode между последней проверкой и replace не меняет
создаваемые проверенные bytes новой inode.

## Тестовые доказательства и их пределы

Тесты проверяющий не запускал. Прочитаны журналы исполнителя:

- `directory-red.log`: 9 failed/495 deselected, все три новых позитивных
  состояния × три настоящих caller отказали на прежнем unsafe-directory.
- `directory-green.log`: **63 passed /441 deselected /23.26s**.
- `directory-static.log`: восемь команд EXIT0 — Bash syntax, Ruff helper/test,
  actionlint двух прежних workflow, development-process, workflow self-test,
  Spec Kit governance, changelog fragments, git diff check.
- `directory-analyze.json`: scoped5/5, critical/high/medium0, ambiguities0,
  соответствующие хеши и issue7859.

Матрица включает known key0777/0644 и старый открытый writer, repeat/no-op,
unknown key, malformed source, dir group/other-mode, unsafe ancestor owner/
mode/symlink/upper-mode, fd opening mismatch, chmod error/no-op, directory
fsync error, path-mode readback mismatch и изменения key/source после fchmod.
Проверяются прежние bytes/inode/modes на отказе, отсутствие следующих
действий и временных файлов. Fixture root metadata/pin остаётся явно
учебной; реальное открытие fd/chmod/fsync/replace исполняется на временных
файлах. Она не доказывает настоящие metadata/bytes hosted runner.

### Финальное дополнение теста

Повторно прочитан итоговый test diff. Добавлен `key-parent-safe-unknown`:
каталог0777, ключ0644/root:root/3607bytes с несовпадающими bytes. Этот случай
проходит прежний metadata guard и упражняет новый pin для directory repair;
ожидается отказ до записи. Общие assertions подтверждают прежние key bytes/
inode/mode, directory mode, source bytes, отсутствие следующих действий и
временных файлов. В отличие от unknown777, отказ здесь достигает именно
нового условия доверия. Изменены только списки случаев и две установки
fixture; поведение остальных504 случаев от этих четырёх строк не меняется.
Helper не менялся.

Завершённые журналы исполнителя прочитаны отдельно:

- `directory-module.log`: **504 passed /0 skipped /191.01s** на предыдущем
  test hash `af64ec5afd524ff5c79fe37ded9dab49e6968cea02c02a8b729883a2cb1b61d3`.
- `directory-safe-unknown.log`: **3 passed /504 deselected /0.95s** на итоговом
  test hash `4ffb95eb130da7a60e46cd6af0cd005d6ad310f415ad7e3c9dc404e033a9fcbd`.

Это полный прежний модуль плюс отдельная проверка дополнения, **не единый
прогон507**. На итоговом тестовом файле все507 совместно локально не
запускались. Финальный Ruff/diff PASS сообщён исполнителем; прежний журнал
static8 прочитан непосредственно. Сохранённый helper hash совпадает во всех
этапах. Раздельных результатов достаточно для данного узкого review:
изменение теста только добавляет новый параметр, не меняя helper либо
семантику прежних случаев. Окончательные native/exact-SHA PR gates и converge
этим отчётом не заменяются. Настоящий Prepare должен пройти сохранённую
константу; mismatch остаётся отказом, а не основанием ослабить исключение.

## Проверка избыточности

Применён `ponytail-review` (прочитан его SKILL.md): лишних зависимостей,
workflow, настроек, абстракций или дублирующих подсистем нет. Новый блок
использует существующие snapshot/atomic replacement и stdlib. Проверки
прав, pin и повторные чтения нужны для конкретной writable-directory
границы; сокращать их без потери принятого свойства нельзя.
Lean already. Ship.
Последняя формулировка относится только к отсутствию лишней сложности,
не является разрешением на merge/deploy или заменой оставшихся gates.

## Границы действий

Изменён только этот отчёт. Код/requirements/checklist/Git/GitHub/server/
release не менялись. Проверяющий не запускал тесты, сетевые/APT/root/
production проверки и не создавал другие агенты. Native/exact-SHA gates,
merge, Full, выпуск/runtime, F273/T0 и коммерческие AC остаются отдельно.

## Хеши проверенного состояния

- `infra/scripts/prepare-ci-apt.sh`: `879306f087c4809fea3a3c26d004f78914e5541ac8490d9e3334058020e48023`.
- `tests/governance/test_governance_workflow.py`: `4ffb95eb130da7a60e46cd6af0cd005d6ad310f415ad7e3c9dc404e033a9fcbd`.
- `specs/211-optimize-ci-cd/spec.md`: `1c19d388d4a4b55176cdf4fd497a41d948bdbe485fba7514f2a89fc1aa21f487`.
- `specs/211-optimize-ci-cd/plan.md`: `2d7579fd953a3ce4cc3cc04fbedf73d790ea07f9d256f72b9da0883be147cc4a`.
- `specs/211-optimize-ci-cd/checklists/ci-keyring-directory.md`: `bc5fd935caaf17cecbd6f369d0bc4db3775de79168cf2f32f6a4c378a7766c8b`.
- `.dev/ci-official-sources/directory-red.log`: `512b7de7842074189375dce74c16d596dfbcb49f07ce0a49172149318148bb20`.
- `.dev/ci-official-sources/directory-green.log`: `f5712e25a164313db8d4f075bb02298ad13cd4a481a0a742b84ba87600263bbc`.
- `.dev/ci-official-sources/directory-static.log`: `b7fa2b0da7ab29efe8cc05f501479109733a59bdddd53db0c92a6d19978cf2c0`.
- `.dev/ci-official-sources/directory-module.log`: `5139c6d1a0662c0a6818759d1326ef67e1dc66826b32bca9fa8d87909dd97616`.
- `.dev/ci-official-sources/directory-safe-unknown.log`: `ff86290650f9b5408a95245d3d614dbc19d40d81d94e280e482c89c066ed246b`.
