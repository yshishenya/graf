# F211 T112 — независимое ревью реализации, 01.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: growth-protocol-result/crisp, ветка
`codex/f211-ci-official-sources-20261101`, исходный HEAD
`ca02e2cf9bb4d761cc1d24bde230a8071c078361`. Реализация пока без коммита;
итоги ниже относятся к хешам локальных файлов, а не к готовому PR.

## Первый проход — HOLD

**Открыто 1 P2; P1/HIGH — 0.** Полный итоговый GREEN ещё не предъявлен.
Checklist требований остаётся отдельным ранее принятым gate 5/0; данным
назначением проверяющий его не изменяет.

### P2 — допустимый вход может превратиться в непринимаемый выход после replace

В `infra/scripts/prepare-ci-apt.sh:77–95` проверенные списки Types/Components
разбираются через split, но в сериализацию передаются исходные строки с
внутренними пробелами. При разделении mixed stanza по suites эти строки
копируются в каждый выходной раздел. Пример по статическому чтению: вход
меньше 16KiB с `Types: deb` + 5000 пробелов + `deb-src` и четырьмя suites
проходит все проверки, но четыре копии Types уже превышают 20KiB.
`os.replace` выполняется до `checked_read(source, 16384)`; после замены helper
отказывает, оставляя файл, который он сам повторно принять не может.
Набор пакетов корректен, причина — только размножение допустимого форматирования.
Пример проверяющим не исполнялся.

Минимальное исправление: сериализовать проверенные token fields с едиными
разделителями (`' '.join(tokens)`), ограничить готовый canonical до записи и
добавить accepted long-whitespace/mixed сценарий с последующим no-op повтором.
В тестовом сравнении package tuples Types/Components нужно сравнивать как
семантические списки токенов, поскольку форматирование явно не является
настройкой. Код и тесты проверяющий не менял.

### Уже прочитано и сохранённые границы

Полностью прочитан текущий helper и существующий
`test_actual_media_resource_preparation`, все три настоящих YAML блока,
изменённые spec/plan/quickstart, T112/tasks, analyze.json и F211 fragment.
Before-code analyze заявляет покрытие 6/6, одну задачу, C/H/M0 и issue7859;
его хеши требований совпали с принятым проектом. Настоящий issue/canon sync
здесь не проверялся через сеть.

Входной URI не разыменовывается и не печатается, output hosts заданы
константами. Допуск hosted/Ubuntu/noble/amd64/no-foreign, строгие поля,
проверки root/мода/regular/no-follow/ограниченного чтения и сохранение
параметров по suite соответствуют проекту, кроме P2 выше. Source открывается
через O_NOFOLLOW с сопоставлением lstat/fstat и повторной проверкой после
чтения. Parent перед replace сравнивается по dev/ino/mode/uid/gid; это
правильно исключает собственное изменение mtime/size каталога при tempfile.
Write/flush/fsync/fchown/fchmod/replace/readback/finally cleanup и no-op
прочитаны; keyring/mirror/сторонние sources не записываются.

Модель теста явно подменяет root stat/fchown и native dpkg/os-release на
временных путях; это не проверка настоящих прав/платформы. Прочитанные три
workflow callers не меняются и вызывают helper до media/npm/Playwright.
Helper failure прерывает последующие действия через прежний shell fail-closed.
Реальная подготовка governance-fast выполняется только при server diff;
infra-only PR не даёт её actual root/native proof. Основной агент сообщил,
что уточняет чрезмерную фразу plan: required PR CI принимает hermetic профиль,
настоящий helper исполняется на server-change или штатном Full нового
кандидата. Это уточнение соответствует прочитанным callers; новую редакцию
документов и хеши ещё требуется перечитать.

Прочитан RED log: 6 новых mixed/unknown сценариев отказали на старом helper,
393 deselected. Старый green.log содержит 29 failed/202 passed/168 deselected
из первого неокончательного запуска и за успех не принят. По сообщению
исполнителя directory-mtime compare уже исправлен, working3/3 PASS, полный
повтор ещё идёт. Выполнение тестов проверяющим не производилось.

Внешний CI/exact PR/base/Full/merge/release/CD, настоящий hosted root/native
результат, T110 AWS, runtime/T0 и трафик/продажи остаются непринятыми.
Изменён только этот собственный report; checklist/code/spec/plan/tasks/Git/
GitHub и чужие изменения не тронуты.

Хеши первого прочитанного состояния:

- Helper: `e0a89498e0c34a16e8e26651701990a6e377734f48052506e0ae616d69c8b1ef`.
- Harness: `af29de85df76f88469f96a789ca668b934f75c753bc475ac4fc2e35dcee14f52`.
- governance-fast YAML: `191f01fc6837a7486f3ed6220b5cd6cc7e2d5966932678f5208686a87d54f0b5`.
- release-full YAML: `e3342f96e9afd335892f5d850a7e03c2cee2264a4c20a9738ac5e5977472bb5a`.

## Повторное чтение исправления P2 — результаты ещё ожидаются

Статическое замечание P2 устранено в текущем исходнике: после проверки
Types/Suites/Components сериализуются через `' '.join(tokens)`, готовый
canonical проверяется на предел 16384 до tempfile и replace. Новый
`wide-fields` содержит 5000 пробелов между допустимыми Types, четыре suites
и проверку входного размера; package tuples сравниваются как списки токенов.
Повторный no-op проходит той же общей веткой. Это сохраняет настройки и
меняет только форматирование, как разрешено spec.

Прочитан `whitespace-red.log`: 1 failed/399 deselected на прежней реализации,
причина — metadata/size отказ после замены, соответствующий находке.
Исправление прочитано, но окончательный GREEN всего модуля ещё не получен;
текущий этап не является итоговым implementation PASS.

Изменённые разделы T112 plan/quickstart полностью перечитаны. В них теперь
честно указано, что hosted test также моделирует root/native, infra-only PR
может пропустить внешний Prepare по прежнему server scope, а реальный helper
проверяется при server-change/штатном Full. Это принято как исправление
точности доказательств без изменения проверок или обхода полного выпуска.
Analyze.json ещё содержит прежние plan/quickstart hashes; владельцу передана
необходимость отразить узкое повторное сопоставление, прежде чем заявлять
актуальность этого артефакта для новых документов.

Хеши на этом этапе:

- Helper: `2364d3e6d5d66ef4b9081ae7d411380cdab37d09ca0dcaa1ca2f2670a7b9123f`.
- Harness: `64223c8b65a55c227b6789dd7d2db1355e000da0718b974536120477e11d5f99`.
- Spec: `bf303f86fcdb5c4ed5f6b5967ca12cbcf834bd2be1454c3d25eb015bfb7b450d`.
- Plan: `f5d14af2292d44af0d0017f6db2fc9e76cc4ee01ff2238dfe021eaff90863300`.
- Tasks: `eadea06a9fc2867938b6c3848581b5c4979a05c0335c29f3e4b417e1f525ac33`.
- Quickstart: `ff155e8c43dee15e6e2f7135815f35827e9d8cb45618e7207e031c761661f326`.
- Analyze до сверки новых документов: `73fc62bed8eb3c839621bf84afb10a7dd71b8a193f7649352b6f119bbf42cf3f`.

Базовые constitution/PRD/status/product-gates hashes повторно сверены,
совпадение с ранее прочитанными значениями подтверждено. Новое полномочие
проверяющего по-прежнему ограничено только этим code review report;
checklist проекта не менялся.

## Окончательное implementation review и scoped converge — PASS

**Открытых замечаний P1/P2/HIGH: 0/0/0.** P2 первого прохода устранено
минимальным исправлением; его история выше сохранена. Дополнительных
обязательных изменений кода в пределах T112 не выявлено. Checklist требований
повторно прочитан без изменения: **5 checked / 0 unchecked**. Это отдельный
итог требований, не отметка выполнения T112.

Прочитан завершённый `final-module.log`: **402 passed, 157.22s**, пропуски
не зарегистрированы. Его hash и неизменность helper/test на время прогона
подтверждены исполнителем; текущие source hashes независимо сверены.
Прочитан `whitespace-green.log`: **3 passed / 399 deselected**; новый
accepted wide-fields случай проходит те же три настоящих YAML блока, сравнивает
семантические package tuples, фиксированные HTTPS цели и повтор bytes/mtime.
Прежние RED6/6 и отдельный whitespace RED1 сохранены как причинные отказы,
ранний неуспешный green.log окончательным результатом не считается.

Прочитан `static.log`: все восемь команд имеют EXIT0 — bash syntax, Ruff,
actionlint двух прежних workflow, development-process, governance self-test,
Spec Kit governance, changelog fragment и diff-check. Содержимое извлечённого
для Ruff `.dev/ci-official-sources/helper.py` сопоставлено с настоящим heredoc:
отличается только отсутствием завершающего LF, исполняемые строки совпадают.
Проверяющий эти команды и тесты не запускал.

Обновлённый analyze.json полностью прочитан: покрытие 6/6, одна T112,
C/H/M0, issue7859 и явная граница modeled root/actual Full. Его текущие hashes
spec/plan/tasks/quickstart/checklist совпадают с файлами. Изменённый quickstart
T112, включая итоговые локальные результаты и честную границу hosted model,
перечитан. F211 fragment описывает только это поведение и сохраняет AWS/Full
ограничения. Задача T112 остаётся открытой до предусмотренной commit/PR
приёмки; историческая T110 не закрывается.

### Проверенный итоговый поток

- Shell требует GITHUB_ACTIONS/Linux/github-hosted до sudo. Python отдельно
  проверяет Ubuntu24.04/noble и native amd64 без foreign architectures.
- Parent/keyring/source проверяются на обычный тип, root ownership и
  отсутствие group/other write; bounded source/keyring reads используют
  O_NOFOLLOW и совпадение lstat/fstat до/после чтения. Небезопасные данные
  не печатаются. Root-owned runner остаётся заявленной границей доверия.
- Все sections разбираются до создания temp. Неизвестные поля, overrides,
  продолжения, повторы, пустые/неподдержанные token sets и неверные ключ/
  архитектура запрещены. C0 кроме TAB/LF, DEL и non-ASCII запрещены глобально.
  Старые URI только отбрасываются: к ним нет сетевых/файловых обращений.
- Unique suite получает ровно одну выходную stanza с прежними Types,
  Components, optional Architectures/Enabled и Signed-By. Формат token fields
  нормализуется, отсутствующие настройки не добавляются; security/archive
  выбираются только по разрешённой suite. Выход bounded до записи.
- Temp создаётся в прежнем parent, uid/gid/mode сохраняются; flush/fsync
  предшествуют повторному чтению source и проверке identity/bytes/metadata
  source и identity/mode/owner parent. После atomic replace выполнены
  bounded readback и проверка bytes/metadata; finally удаляет только temp.
  Уже совпадающий canonical ничего не записывает. Ошибки после replace
  блокируют следующие этапы и не выдаются за выполненный откат.
- Все три неизменённых caller вызывают helper до media/npm/Playwright;
  non-server/text-only scope сохранён. Actual-shell профиль проверяет
  prewrite/replace/readback отказ, отсутствие следующих этапов, исходные
  mirror/third-party/keyring bytes и temp cleanup. Модель root/fchown/dpkg
  явно локальна даже при запуске теста на GitHub; это не native proof.

Во время проверки ветка без изменения helper/test продвинулась fast-forward
на `a20ce7fc008de6df21967361317ed668ce29238b` (PR7858/F140). Проверяющий
непосредственно прочитал список изменённых между прежним ca02e2cf9… и новым
HEAD путей: только billing/F140, без helper/harness/F211/workflow/guidance.
Current branch, исходники, YAML и constitution/guidance hashes повторно
сверены. Этот вывод не переносит никакие прежние exact PR checks на новый
коммит и не является ревью самого F140.

**Границы окончательного PASS:** приняты исходники и предъявленная локальная
проверка T112 с моделью метаданных. Exact PR SHA/base checks, merge,
настоящий helper/root/native на server-change или Full, новый frozen Full,
release/CD/runtime/T0, T110 AWS и трафик/продажи остаются отдельными воротами.
Новой диагностической инфраструктуры, искусственного server diff или
случайных runners не требуется и здесь не запускалось. Полномочия reviewer
соблюдены: изменён только данный report; checklist проекта и чужие edits
сохранены.

### Хеши принятого конечного состояния

- Base HEAD: `a20ce7fc008de6df21967361317ed668ce29238b`.
- Helper: `2364d3e6d5d66ef4b9081ae7d411380cdab37d09ca0dcaa1ca2f2670a7b9123f`.
- Harness: `64223c8b65a55c227b6789dd7d2db1355e000da0718b974536120477e11d5f99`.
- F211 fragment: `74bf07abad3827fe6d77627ecb718a7c682c3fd86f8db1b4396645baf621bde2`.
- Spec: `bf303f86fcdb5c4ed5f6b5967ca12cbcf834bd2be1454c3d25eb015bfb7b450d`.
- Plan: `f5d14af2292d44af0d0017f6db2fc9e76cc4ee01ff2238dfe021eaff90863300`.
- Tasks: `eadea06a9fc2867938b6c3848581b5c4979a05c0335c29f3e4b417e1f525ac33`.
- Quickstart: `74d2ecebd62f99d8139a55fe6794b281e0c95b81f802883f1d46cffbad2d3c0d`.
- Checklist неизменён: `1a64c22ab2fc2fe5f260a20cfbd549b5d48a8d45103d8166dbd83c99374650af`.
- Analyze: `040f23c774368fccfd25687e85ef6307dd1f3368f7d0092eeb5e1d3e7ecb6468`.
- Final module: `186528465785764e51f8b6a9c86dd648c7cfe2ad55b792b18852fc2e7533fa53`.
- Static: `71c8d60bc01d0eab4ec210ec23b7d3bfd6160aaba7885a2a102a1907905baac9`.
- Whitespace GREEN: `82a7dcb77215e395972788e5825ef46ac73c45a2c94c69ca2d1b844b35ad803e`.
- Whitespace RED: `c1dd7eb21d7c5088a3729ce83c6656927707d93d2a1984a6c7cdd9db585fc92a`.
- Initial RED: `8d7e626e7500f127b79d10fed339653e343976e66cf8d387b0870565e8305c71`.
- governance-fast YAML: `191f01fc6837a7486f3ed6220b5cd6cc7e2d5966932678f5208686a87d54f0b5`.
- release-full YAML: `e3342f96e9afd335892f5d850a7e03c2cee2264a4c20a9738ac5e5977472bb5a`.
