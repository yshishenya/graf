# F211 T113 — независимое ревью реализации, 01.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Ветка `codex/f211-ci-native-metadata-20261101`, непосредственно наблюдённый
HEAD `208e0aee20629c0770ad6ce0457fc1ebfcb6a631`. Локальные изменения ещё не
закреплены коммитом; source verdict относится к хешам ниже.

## Первый проход: исходники проверены, полный результат ожидается

Открытых замечаний к прочитанному коду P1/P2/HIGH: **0/0/0**.
Итоговый implementation/converge PASS пока не объявляется: полный модуль
ещё выполняется. Checklist требований перечитан без изменения: **5/0**.

Полностью прочитаны текущий helper, четыре места вызова checked_read,
все три настоящих resource caller, diff существующего теста вместе с
сохранённой тестовой моделью, spec/plan/tasks/quickstart T113 и F211 fragment.
Конституция/PRD/status/product-gates и применимые guidance hashes совпали с
ранее прочитанными; использовано разрешённое владельцем повторное чтение F211.

### Диагностический вывод и прежние защиты

Diff checked_read меняет только сигнатуру/сообщение в прежней metadata ветви:
условия regular file/root uid/no group-other write/ненулевой bounded size
побайтно сохранены. Label во всех четырёх местах — литерал `keyring` или
`source`: начальный keyring, начальный source, pre-replace source, readback
source. Сообщение содержит лишь фиксированную фразу, category и числовые
stat.S_IFMT, uid, gid, stat.S_IMODE (восьмеричная запись), size. Не читаются и
не форматируются исходный path, URI, содержимое, environment или другие files.
Вызывается прежний SystemExit до открытия файла и дальнейших действий.

O_NOFOLLOW/fstat fingerprints, platform/native guards, keyring validation,
строгий deb822 parse, fixed HTTPS output, bounded canonical, atomic write,
readback/no-op/temp cleanup не менялись. Это сообщение именно прежней
metadata ветви, а не новая обработка всех возможных ошибок чтения.
Фактический файл и причина настоящего runner отказа по исходникам не угаданы.

### Selector и исполняемая модель

В governance-fast прежний server selector расширен ровно equality с
`infra/scripts/prepare-ci-apt.sh`, без glob или каталожного допуска.
Точное имя path заключено в прежнюю shell проверку, двойное quoting значения
сохранено. Новое имя существующего шага правдиво отражает это условие;
required job name, permissions, text_only gate, changed_files/base selection,
break и все действия внутри branch не менялись. Server путь прежний,
обычные docs и другая infra не получают новую подготовку. Два release-full
caller неизменны и вызывают тот же helper перед media/npm/Playwright.

Тот же actual-shell тест добавляет helper-change и other-infra, оставляет
non-server/docs и server fixtures; governance-fast docs/other-infra требует
нулевых действий, helper-only проходит общий успешный путь. Все три caller
остаются матрицей. Metadata fixtures проверяют точный stderr для source и
keyring owner/mode/symlink/empty/oversize: только ожидаемые category и числа,
никаких лишних строк/содержимого/URI/path. Прежние assertions отсутствия
дальнейших шагов и сохранности файлов остаются. Root/fchown/native модель
не расширяется и не выдаётся за настоящий runner.

### Прочитанные промежуточные доказательства

- RED: 7 failed / 2 passed / 399 deselected. Причины соответствуют отсутствию
  helper-only selection и прежнему общему сообщению вместо точных metadata.
- Новый focused GREEN: 9 passed / 399 deselected, 3.48s.
- Static log: все 8 команд EXIT0 — bash syntax, Ruff helper/test, actionlint,
  development-process, governance self-test, Spec Kit governance, fragment,
  diff check. Извлечённый для Ruff native-helper.py совпадает с настоящим
  heredoc после игнорирования завершающего LF.
- Full module на этом этапе ещё не завершён; частичные точки не приняты.

Прочитан локальный issue7859-t113-body.md: задана диагностика без ослабления
guard, native metadata/draft failure не считаются merge-готовностью.
Синхронизация GitHub сообщена владельцем; здесь не выполнялась сеть.
Сообщённый T113 analyze6/6 C/H/M0 пока не найден отдельным локальным
артефактом: имеющийся analyze.json относится к прежней T112. Его старые hashes
не выдаются за актуальный анализ T113; уточнение источника ещё ожидается.

Проверяющий изменил только данный report, не запускал тесты/CI/сеть/APT/
серверы, не менял checklist/code/spec/plan/tasks/Git/GitHub/release/deploy.
Функциональная адаптация, фактические metadata runner, native PASS, T112/
#7859, exact PR gates/merge, Full/CD/runtime/T0 остаются отдельными воротами.

## Хеши первого прочитанного состояния

- Helper: `b16a0c322e976a03c55cd60560e96b82bb97f2fce077a06951262118019d195f`.
- Test: `47a509fceddc090b652f05cc8287942f63cbf61940e5959958960b4eee4a2861`.
- governance-fast: `dfd738473dc9f8f47ea1a6c9e8e5f64dfcfda9e0fceb676a21a4995925dee258`.
- release-full неизменён: `e3342f96e9afd335892f5d850a7e03c2cee2264a4c20a9738ac5e5977472bb5a`.
- Fragment: `bbe6a01a13aea448351f9e7bd6feba7c16c7a22172b21d73152c5a0c285e8a17`.
- Spec: `ca756eeda2f0ff8945e79c5e61ef3b98d4a7dd9fc228bff91ba7a603e9746e7c`.
- Plan: `95922e211a5fc827576cc9270a932ede73f53d0edd17583511c7710a97ee022f`.
- Tasks: `8e7745c1911379ea460ac222f5c21d83f0e1a62b74671dcbc964401cde65fc79`.
- Quickstart: `099663e0d3e8ff5ccb88039bf1b678edf9104d47b3fa07aa0c051c5a903f61f1`.
- Checklist неизменён: `172fcfd6ea7cd60f0daf473a141338d7319bae9fef686c454dc7fdcc30a2dd14`.
- RED: `d2eea4e4139aedf37584bbc4dcd9967cbc9ef50303a58c5c3ea484bde56adea7`.
- Focused GREEN: `b6721c19466e7511b157f5adcd244625a40319e3842425d0244a23de6431bcda`.
- Static: `038d0915e19ab256d6524105805ae5af702fa7b88e9afcd19a2a6025d9eaee32`.
- Issue body local: `0e40fc1ff5b2edde1e94faff0daf87e73e0962c9ee4558fd9e2942fd8e76c1fa`.

## Окончательное implementation review и scoped diagnostic converge — PASS

**Открытых замечаний P1/P2/HIGH: 0/0/0.** В рамках диагностического среза
T113 дополнительных обязательных изменений кода не выявлено. Checklist
требований повторно прочитан без изменения: **5 checked / 0 unchecked**.
T112/T113 остаются `[ ]`; этот результат не закрывает ожидаемую настоящую
диагностику и последующую функциональную приёмку.

Прочитан завершённый `native-metadata-module.log`: **408 passed, 152.53s**,
пропуски не зарегистрированы. Это весь существующий модуль, включая прежние
402 случая и шесть дополнительных сочетаний selector×caller. Владелец
подтвердил неизменность helper/test/YAML во время прогона; текущие хеши
повторно сверены. Прочитаны focused GREEN9 и RED7/2 и полный static log с
восемью EXIT0. Тесты/команды проверяющий не исполнял и не выдаёт чтение
журналов за самостоятельное воспроизведение.

Полностью перечитан новый итоговый раздел quickstart T113: он честно
различает локальную root/native модель и предстоящий настоящий Prepare,
сохраняет draft failure как failure и запрет merge до функциональной
адаптации/конечных gates. Хеши spec/plan/tasks/checklist прежние. F211 fragment
содержит ту же границу и не объявляет функциональную причину известной.

Владелец уточнил источник T113 before-code analyze: read-only in-session
tool output, отдельный файл не создавался; найденный analyze.json намеренно
остаётся исторической T112. Также сообщил повторный scoped analyze текущего
состояния: 6/6, одна T113, C/H/M0, ambiguity0, duplicate0 и live #7859 OPEN.
Это принято как сообщение владельца о процессе, а не самостоятельно
прочитанный локальный JSON или live GitHub ответ. Отсутствующий новый файл
не является дефектом: требование создавать его отсутствует.

Независимое текущее сопоставление требований и реализации также не выявило
пробелов: (1) фиксированные category/numeric metadata → checked_read/exact
stderr assertions; (2) прежние guards/отказ/сохранность → неизменный guard и
общая матрица; (3) helper-only/server → точное OR условие и actual-shell
fixtures; (4) docs/other-infra исключены → два нулевых пути governance-fast;
(5) все три callers и проверки → 408-case модуль/static; (6) draft failure/
native/future fix gates → открытая T113, spec/plan/quickstart/fragment без
обхода. Новых необоснованных задач и функциональной адаптации не добавлено.

Настоящий runner ещё не принёс значения metadata в рамках этого задания;
сохранение uid/type/mode/size guard означает, что известный native отказ
может повториться. Это ожидаемый предел диагностики, а не основание ослабить
проверку или пометить её успешной. Исходники пригодны для разрешённого
диагностического draft PR после штатного commit checkpoint; merge по одному
этому заключению не разрешён. Exact PR SHA/base/required checks, фактические
metadata, новый проект функциональной адаптации, конечный native PASS,
T112/#7859, Full/release/CD/runtime/T0 остаются отдельными воротами.

Проверяющий изменил только этот report; чужие edits и checklist сохранены.
Git/GitHub/сеть/CI/APT/серверы/commits/releases/deploy не выполнялись.

### Хеши окончательного принятого состояния

- Base HEAD: `208e0aee20629c0770ad6ce0457fc1ebfcb6a631`.
- Helper: `b16a0c322e976a03c55cd60560e96b82bb97f2fce077a06951262118019d195f`.
- Test: `47a509fceddc090b652f05cc8287942f63cbf61940e5959958960b4eee4a2861`.
- governance-fast: `dfd738473dc9f8f47ea1a6c9e8e5f64dfcfda9e0fceb676a21a4995925dee258`.
- release-full неизменён: `e3342f96e9afd335892f5d850a7e03c2cee2264a4c20a9738ac5e5977472bb5a`.
- Fragment: `bbe6a01a13aea448351f9e7bd6feba7c16c7a22172b21d73152c5a0c285e8a17`.
- Spec: `ca756eeda2f0ff8945e79c5e61ef3b98d4a7dd9fc228bff91ba7a603e9746e7c`.
- Plan: `95922e211a5fc827576cc9270a932ede73f53d0edd17583511c7710a97ee022f`.
- Tasks: `8e7745c1911379ea460ac222f5c21d83f0e1a62b74671dcbc964401cde65fc79`.
- Quickstart с результатами: `1265790bd7fdcd74cc87e866a469620def25d75bcc8e7b9d9e91d48a5041ef3e`.
- Checklist неизменён: `172fcfd6ea7cd60f0daf473a141338d7319bae9fef686c454dc7fdcc30a2dd14`.
- Final module: `2be2b0b7e003fa63622728944ac802694640bb2ab24d16a7f9e9c70af7d0d180`.
- Static: `038d0915e19ab256d6524105805ae5af702fa7b88e9afcd19a2a6025d9eaee32`.
- Focused GREEN: `b6721c19466e7511b157f5adcd244625a40319e3842425d0244a23de6431bcda`.
- RED: `d2eea4e4139aedf37584bbc4dcd9967cbc9ef50303a58c5c3ea484bde56adea7`.
