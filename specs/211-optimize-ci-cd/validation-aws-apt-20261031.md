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
