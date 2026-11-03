# F211 T099 — проверка подготовки APT, 2026-10-23

Полоса: active Spec Kit slice / shared CI infrastructure.
Основа: d6243efb782d889e3b9b10da0b750c7a90f0707f, ветка codex/211-ci-package-source.
Исходный дефект: run39977036244 attempt1, подготовка34min10.7s;
FFmpeg61.7MB/25min30s, Playwright OS deps21MB/7min53s, Azure40–44kB/s.
Attempt2 cancelled; неуспехи не заменены старым PASS.

## Требования и анализ

Независимый requirements checklist7/0 PASS, report
review-ci-package-source-requirements-20261023.md.
Узкий analyze7/7 требований→T099/T100, CRITICAL0/HIGH0, без новых
противоречий конституции; canon ensure/validate PASS. Owner #7738.

## Локальная реализация и проверки

Один46-строчный helper и3 existing source callers. Список зеркал
меняется с известных3 строк на последние2 HTTPS; deb822/keys/source
metadata не переписываются. Подписи APT, package names, tests/timeout/
required names/permissions/concurrency/SHA/base остаются прежними.

Baseline: импортирован нынешний исполняемый harness, но все3 YAML caller
взяты побайтно через git show из исходной основы. В изолированных
временных каталогах все3 старых caller ожидаемо FAIL на отсутствии
подготовки зеркала. Продуктовые Git refs и дерево не переключались.

Итог: python -m pytest -q tests/governance/test_governance_workflow.py
—142 PASS/38.08s;75 resource случаев +67 прежних проверок.
Настоящие3 YAML блока и helper исполняются на временных файлах,
sudo/APT/npm/Playwright подставные, сеть не вызывается. Проверены working/
missing tools, update/install/broken media/npm/browser failure, sudo/
write denial, unknown/duplicate/missing/CRLF mirrors, missing/bad source
и symlinks. Повтор сохраняет bytes/mtime; non-server fast не создаёт
событий; text-only guards сохранены. Signature failure моделируется
обычным отказом apt update: криптографический proof этим не выдуман.

Bash, actionlint обоих workflows, Ruff, workflow validator/self-test,
development-process, Spec Kit governance и git diff --check PASS.

В диагностическом тесте повтора сначала был ошибочно запущен дочерний
bash, который не наследовал функцию sudo. Настоящий sudo отказал без
терминала; изменений на Mac не было. Исправление теста использует source
внутри harness; окончательный142-case прогон уже включает эту коррекцию.
Другой первоначальный отказ6 cases относился к слишком широкой проверке
missing-* в тесте; уточнены только два media состояния.

## Незавершённая приёмка

Независимое повторное code review PASS, открытых замечаний0;
review-ci-package-source-code-20261023.md. Исходный F1 воспроизведён
12 ожидаемыми FAIL (4 случая ×3 YAML): дополнительный URI в другом
разделе, продолжение URIs, отключённый раздел, повторное поле. Затем все
142 PASS, включая корректные несколько разделов. F2: plan согласован с
Python stdlib. Checklist повторно проверен7/0. T100 остаётся открытой: после merge нужна новая настоящая
server-change CI проверка endpoint/времени и всего набора. Локальный142
PASS не является hosted speed, Full, публикацией или релизом. PR должен
иметь три обязательные проверки exact SHA/base и общий validator.
Общие F211/F263 и исторические незавершённые задачи не закрываются.

## Итоговая сверка T099

Область сверки: только новый срез T099, семь требований/критериев и три
решения плана; действующие принципы III/V/VI сохранены. Новых пробелов
реализации, противоречий или незапрошенных механизмов не найдено.
Результат converged для локальной реализации T099. Уже существующая T100
полностью описывает остающуюся hosted приёмку; дубликат задачи не добавлен.
Общая историческая F211 не объявляется converged. Во время converge задачи
побайтно не менялись; отметка локальной T099 выполняется отдельным
завершением implement после review. Перед PR профильные static/governance
проверки повторены после исправления: PASS. Hosted PR gates ещё ожидаются.

## SHA-256 проверенной реализации

- `infra/scripts/prepare-ci-apt.sh`: `acb7a1a0b114d0446e893bf8961e0992d04c65078a7184ef3ac8072eba82d25f`
- `.github/workflows/governance-fast.yml`: `18d429b8ff8cc9210cec2097c675396dca1a70dacf9d06df5cb17967572eec0b`
- `.github/workflows/release-full.yml`: `22a9ba6d7c1e5db47359fcb2e3097b1078c7fb99d903d71205d0cc069a935987`
- `tests/governance/test_governance_workflow.py`: `00ef8bb79c4305b384690e0c8cfb38a67d6b2ab91a43699f31a77f2b4f98b95f`


## Итог T100 — настоящая приёмка в GitHub

Полоса этой сверки: docs-only / mechanical. Изменяются только отметка
существующей T100, этот отчёт и ограничение фрагмента F211; исполняемый код,
правила CI, продукт и выпуск не меняются. Предыдущие ожидающие формулировки
описывают состояние до публикации T099 и не являются текущим итогом.

Реализация T099 принята [PR #7739](https://github.com/yshishenya/graf/pull/7739):
PR SHA `8bc2e743ed2b822ae71ec5bb02d9cb7769e2a57b`,
checked base `d6243efb782d889e3b9b10da0b750c7a90f0707f`,
merge `21e80b29c7f23bddba9eae49c078974ebd244231`.
Его обязательные проверки governance-fast39994127211,
macos-pr39994127089 и pr-metadata39994127194 успешны; общий
validate-pr-checks.py подтвердил точные SHA/base.

После merge существующий серверный [PR #7737](https://github.com/yshishenya/graf/pull/7737)
обновлён на принятую основу. Окончательный source
`f15c1fc6ae812293abe2433ed9dab457f7a07f50`,
checked base `21e80b29c7f23bddba9eae49c078974ebd244231`.

- [governance-fast39999141863](https://github.com/yshishenya/graf/actions/runs/39999141863)
  SUCCESS, attempt1. Настоящий шаг Prepare browser resources only for server
  changes: 17:56:50–17:57:32 UTC, **42s**. Журнал APT содержит
  `https://archive.ubuntu.com/ubuntu` для noble/updates/backports/security;
  известное медленное Azure-зеркало не используется.
- Bounded fast: **453s**, **2465 pure unit +183 resource unit +100 changed
  contract PASS**, без пропусков этих групп. Выбор и результаты относятся
  к нынешнему source, не к предыдущему92-case варианту. Это выбранный fast,
  его полное выполнение не является release-full всего репозитория.
- [macos-pr39999142141](https://github.com/yshishenya/graf/actions/runs/39999142141)
  SUCCESS. После правки описания финальная
  [pr-metadata40003002514](https://github.com/yshishenya/graf/actions/runs/40003002514)
  SUCCESS; актуальные текстовые governance40003001795/macOS40003001836
  также прошли общий consumer. Описание не подменяет настоящие source runs.
- Перед слиянием общий validate-pr-checks.py повторно подтвердил source,
  base и актуальные обязательные gates. Все обсуждения разрешены по
  проверенным доказательствам, обычный rebase merge без admin bypass:
  `2964952dbd3c03f5730230f134f0715282ffa7fb`, 18:32:55 UTC.
- SHA-256 сохранённого журнала source run:
  `2b94c9afe9d3d2c1db4d24c8e3a058a7adae862e5b391f7e081466aa1c9a3937`.
  Малые исходные журналы, API snapshots и результаты валидаторов сохранены
  во внешнем реестре аудита; зависимости и сборки туда не копируются.

Прежние34min10.7s относятся к неуспешному исходному run39977036244,
42s — к одному нынешнему успешному наблюдению. Другие runner, сеть и состав
пакетов могут отличаться; медиана, гарантированная скорость либо процент
устойчивого ускорения не заявляются. Локальные142 проверки отдельно
подтверждают сохранность APT-конфигурации и отказы; настоящий GitHub run
подтверждает endpoint и выполнение выбранных тестов.

Содержательная приёмка T099/T100 завершена. Scope review/converge этой
сверки: все шесть исходных критериев #7738 имеют указанное доказательство,
новых задач или runtime изменений не требуется. Закрытие #7738 требует
трёх обязательных проверок и merge документальной сверки, затем повторной
live-валидации фактической issue. Общая F211, исторические незавершённые
задачи, F263, macOS-приложение, release-full, выпуск и production этим не
принимаются и не закрываются.
