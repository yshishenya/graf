# F211 T110 — неизвестный APT источник, 31.10.2026

Lane: active Spec Kit slice, CI diagnostics. Основа
`4a6220af6f74d29eb2186ded8e1e247e621d9a15`.

## Исходный отказ

[Full41239402369](https://github.com/yshishenya/graf/actions/runs/41239402369),
attempt1, shard2 job124650068957: `unsupported Ubuntu mirror source` до тестов.
AWS/us-east-1, Ubuntu24.04.5, image20261018.96.1. Точный URIs отсутствует.
Ссылка runner-images на этот tag возвращает404. У текущего upstream
configure-apt-sources.sh (4da2307112a0fad2fd2ecaca8ba7d08683b8c581) известен
лишь прежний mirror-list. Эти сведения не доказывают формат отказавшей машины.

## Анализ требований до кода

Spec T110 → plan T110 → task T110 → quickstart T110: пять групп требований
покрыты5/5: известный отказ/неизвестный формат;8 bounded jobs/no installs;
read-only bounded sources/safe JSON; исполняемый профиль; удаление workflow
и сохранение release gate. CRITICAL0/HIGH0/MEDIUM0, unmapped tasks0.
Constitution III/VI сохранены; никакой поддержки неизвестных URI или обхода
доверия план не разрешает. Новый runtime/миграции/продуктовая аналитика не входят.
Независимое requirements review и issue sync остаются до кода обязательными.

## Повторное чтение

Применено прямое исключение владельца для F211: затронутые T099/T100/T110
spec/plan/tasks/quickstart, CI helper/callers/harness, constitution и guidance
прочитаны; остальные ранее прочитанные базовые документы сверены поSHA256:

- PRD: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- Status: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- Product gates: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.

Прежние T099/T100 и failed candidate не переписаны. Code/PR/hosted diagnosis,
новый кандидат, Full/CD и коммерческий рост пока не приняты.

## Окончательный Full

Run41239402369 завершён FAILURE. Десять частей static/macOS/PostgreSQL успешны; отдельный shard2
не прошёл подготовку; shard2 не дошёл до тестов, aggregate
отказал из-за неполного состава. Кандидат не повторяется, CD/tag/Release
не выполнялись. Окно слияний освобождено согласованной задаче репозитория.

## До hosted диагностики

Независимое requirements review5/0 PASS. Analyze5/5, CRITICAL/HIGH/MEDIUM0;
T110 синхронизирована с issue#7849, canon255 PASS. Локально тот же inline
Python прошёл11 случаев, actionlint/process/fragment/diff PASS.
Первый запуск локального профиля не нашёл YAML из-за лишнего .parent;
process отдельно выявил отсутствие fragment в ignored owned_paths.
Исправлены тестовый путь и ignored pointer; системные файлы не менялись.
Независимое code review и hosted факт ещё ожидаются.

## Исправление первого code review

Независимый reviewer нашёл, что suffix-проверка домена принимала NUL/\\
внутри hostname. До hosted запуска добавлены проверка DNS label/длины,
ASCII без управляющих символов и отсутствие port suffix. Тот же14-case
профиль на прежней проверке ожидаемо FAIL на backslash; исправленный14 PASS,
включая NUL/empty-port. Локальные журналы сохранены отдельно, APT не менялся.

## Допуск временной диагностики

Повторное независимое code review/converge: SCOPED PASS, P1/P2/HIGH0,
checklist перечитан5/0. `review-ci-apt-diagnosis-20261031.md` сохраняет первый
HOLD и принятый текущий код.14 локальных случаев и actionlint/process/fragment/
governance/diff PASS. До hosted факта и удаления workflow T110 остаётся[ ].

## Первый hosted набор

[Run41240805226](https://github.com/yshishenya/graf/actions/runs/41240805226)
SUCCESS, source5d42971c40625997ccc49a8b0d438a263f7fc523. Все8 машин Azure
Ubuntu24.04/image20261025.353.1; оба URIs — mirror_list. Их source SHA256
4508181e0dd5578c33d1247db48ab4847910b25da85e0789c8e7b3140d1fb289,
mirror-list SHA256e0d6b0af979e4662d16357a27ae456cc6f21e26da031540f4df8706ebed1d583.
Пустой массив uris mirror-list не доказывает состав строк; его hash отдельно
сопоставляется с известной константой. AWS не исследован, T110 открыта.
После факта уточнён следующий набор8 jobs с настоящей меткой Full
ubuntu-latest; новый review обязателен до изменения YAML.

Второе уточнение и diff реализации независимо приняты: checklist5/0,
P1/P2/HIGH0; YAML изменён только runs-on, safety code не менялся.
Точная метка и прежние14 сценариев PASS, actionlint/process/diff PASS.
Синхронизация issue#7849 сохраняет открытый AWS критерий и предел16 jobs.

## Второй hosted набор и срез T111

Run41241032858 SUCCESS, source7040d2502cd39dbc7c586d1fa69e683ab3bb4a57:
8/8 Azure/image20261025.353.1, идентичные hashes/URIs первого набора.
Всего16/16 Azure. Hash mirror-list совпадает с известной144-byte константой
T099, но фактический AWS URI всё ещё неизвестен. T110 остаётся открытой;
дальнейшие выборки/Full ради выбора облака не планируются.

T111 pre-code analyze: пять групп требований spec→plan→T111→quickstart
покрыты5/5: сохранение отказа/неизвестности; safe bounded JSON; trust/bytes/
callers;3-caller исполняемый профиль; удаление временного workflow/gates.
CRITICAL0/HIGH0/MEDIUM0, uncovered requirements0/unmapped tasks0.
Нет новой продуктовой политики или APT источника. Независимый checklist и
issue sync до кода ещё обязательны.


## T111 — локальная реализация и проверки 01.11.2026

До изменения helper новый профиль причинно завершился FAIL:30 failed,243
deselected — отсутствовал JSON перед прежним отказом. После переноса describe
полный существующий профиль: **273 passed in87.33s**. Три настоящих caller
по-прежнему отказывают на прежних неподдержанных входах; проверены безопасный
JSON, неизменные source/mirror/third-party bytes и отсутствие действий после
отказа. Сохранены RED/GREEN журналы в локальном .dev/ci-apt-diagnosis.
Bash syntax, actionlint двух существующих workflow, Ruff и diff-check PASS.
Временный ubuntu-apt-diagnostic.yml удалён; новых выборок не будет. Это
приёмка локального сообщения отказа, не исправление AWS или успешный Full.
T110/#7849 остаются открытыми; T111 ждёт независимого review/converge и
точных PR checks. Source до коммита7040d2502cd39dbc7c586d1fa69e683ab3bb4a57.

Независимое implementation review/converge PASS:5/0, P1/P2/HIGH0.
Принятые helper/harness hashes совпали; отчёт review-ci-apt-failure-diagnosis-20261101.md
прочитан. Process, governance, fragment и diff-check PASS. Коммит и PR
проверки следуют отдельно; T111 до их принятия остаётся открытой.
