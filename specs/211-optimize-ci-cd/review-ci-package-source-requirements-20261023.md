# Независимая проверка требований F211 T099–T100

Дата: 2026-10-23. Ветка `codex/211-ci-package-source`; исходный HEAD
`d6243efb782d889e3b9b10da0b750c7a90f0707f`.

**PASS: 7 checked / 0 open; CRITICAL 0 / HIGH 0.** Это проверка требований
перед реализацией, а не подтверждение исправления или результат GitHub CI.
Lane реализации: active Spec Kit slice, shared CI/infrastructure.
Reviewer изменяет только этот отчёт и `checklists/ci-package-source.md`.

## Поэлементная проверка

| Пункт | Проверенное основание | Результат |
|---|---|---|
| CHK001 | `spec.md:538` фиксирует исходный run39977036244 attempt1, задержку34m10.7s, медленный Azure APT40–44kB/s и отсутствие успешной проверки. Сохраняет T089/FR-057/SC-025; `tasks.md:279` добавляет T099 без переписывания исторической T089. | PASS |
| CHK002 | `spec.md:545` задаёт эффективную deb822 ссылку `mirror+file:/etc/apt/apt-mirrors.txt`; `spec.md:572` закрепляет буквальные URI, TAB/priority и LF. Допустимы только исходные три строки либо последние две; лишние/повторные/другие строки и не обычные файлы дают FAIL. `plan.md:533` ограничивает среду GitHub Linux и не вводит поддержку других образов. Повтор — без изменения байтов. | PASS |
| CHK003 | `spec.md:549–564` сохраняет все suites/components/архитектуры/Signed-By, ключи и проверки подписей APT, посторонние источники. `plan.md:533–545` запрещает переписывать deb822/ключи и требует побайтной проверки сохранности в исполняемом harness. Нового источника или обхода доверия нет: удаляется только известная Azure строка, сохраняются уже существующие HTTPS archive/security. | PASS |
| CHK004 | `spec.md:552` и `plan.md:533–540` задают все три callers: server-ветвь governance-fast и оба resource steps release-full. Общая подготовка идёт до условной установки ffmpeg и до Playwright APT, в том числе при исправных обоих media tools. Non-server/text-only не получают изменения APT или установки. Три существующих YAML блока прочитаны. | PASS |
| CHK005 | `spec.md:555–565` требует отказов при неизвестном/неоднозначном формате, read/write errors и mirror/update/install/media/npm/Playwright errors; прежние тесты,45min timeout, checks/permissions/concurrency/SHA/base сохраняются. Это распространение ошибок, не обещание локально воспроизвести настоящую APT-криптографию. | PASS |
| CHK006 | `spec.md:567`, `plan.md:541`, `quickstart.md:911` требуют исполнения всех трёх настоящих YAML блоков и helper на временных файлах с перехватом команд: оба missing-tool случая, исправные инструменты, no-op повтор, сохранность источников, unknown formats и каждый failure stage. Локальный shell не объявляется hosted или Full доказательством; T100 требует реальный server-change после merge. | PASS |
| CHK007 | `.specify/feature.json` задаёт F211 и owned paths; `plan.md:526–552` фиксирует risk lane/Constitution VI, requirements review→analyze→sync→RED→implementation→focused/static→independent review/converge→exact PR checks→merge. `tasks.md:281` выделяет зависимую T100 и сохраняет общие F211/F263 открытыми. Production, приложение и выпуск исключены; frozen Full gate сохраняется. | PASS |

## Уточнение, сделанное до PASS

В первоначальном разделе T099 перечислялись домены/priority, но отсутствовал
буквальный формат строгого known-list контракта. Рецензент запросил точные
три строки, разделитель и допустимый повтор. Основной исполнитель дополнил
`spec.md:572–583` до реализации; дополнение перечитано. Теперь обе допустимые
формы и отказ при остальных определены однозначно. Дополнительного селектора
зеркал, общего package manager или новой зависимости не требуется.

## Отдельные обязательные ворота

T099 — локальная реализация и проверки; T100 — зависимая настоящая hosted
приёмка. Они могут принадлежать одной узкой issue, но issue нельзя закрывать
по одному локальному PASS. Требуются analyze и issue sync до кода, затем
реальные RED/GREEN, независимое code review/converge и три обязательных
проверки точных SHA/base с общим валидатором. После merge нужен новый настоящий
server-change run на новой основе: endpoint, время подготовки и полный успех.
Только после этого допустим содержательный и live closeout узкой issue.
Общая F211, F263 и прежний остаток не объявляются завершёнными.

Текущий `test_actual_media_resource_preparation` уже расширен основным агентом
для диагностического baseline, но workflow и runtime helper ещё не изменены.
Рецензент тесты не запускал, результат baseline не выдаёт за собственный
проверенный PASS и полноту будущего harness здесь не утверждает. На момент
снимка diff обоих workflow пуст; helper ещё отсутствует. Требование before-code
относится к реализации; предварительная диагностическая регрессия сама по себе
не подтверждает новые требования или работоспособность решения.

## Проверенные источники и ограничения

Новые секции T099 spec/plan/tasks/quickstart прочитаны полностью, включая
добавленную T100. В большой исторической F211 прочитаны применимые T089/A12,
а не все прошлые фазы. AGENTS и индекс guidance прочитаны в этой рабочей копии.
Конституция и процессное guidance прочитаны ранее в этом же диалоге; хеши в
новой копии совпали, применимые VI/quality gates, risk/checklist/analyze/sync,
tracker closeout и exact-SHA/base release sections перечитаны.

Источником причинного разбора служит собственный ранее выполненный отчёт
`specs/263-fast-feedback/review-ci-prerequisites-20261023.md` в worktree
`fast-feedback-audit`, SHA-256
`2a9c32078763dd1c37e28c10ac51ec7c473a3497f9f5bb217267a718bf7a23c4`.
Он основан на сохранённом attempt1 полном журнале SHA-256
`577fb1d5ec7a47a9d7c06afe04192beb2082a7ceaf76b0d6ac8e175f8290ae69`.
Состояние attempt2 и upstream runner-images через сеть рецензент не проверял;
они не считаются новым самостоятельным hosted доказательством этого review.
Рецензент не выполнял сеть, тесты, установки, Git/GitHub мутации, запуск GRAF
или работу с пользовательскими данными. Чужие изменения сохранены.

Checklist после записи перечитан: **7 checked / 0 open**.

## Контрольные суммы проверенного снимка

| Файл | SHA-256 |
|---|---|
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/development-process.md` | `1037b91f153f0757fff372e26cd05dd31433158c9c35d149125197a8a523f20d` |
| `docs/agent-guidance/tracker-policy.md` | `06450200cabdef48000af51241564e9ee9e8d36b50c71e06a88f8c50b7365466` |
| `docs/agent-guidance/release-and-validation.md` | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| `specs/211-optimize-ci-cd/spec.md` | `a7624896ef6212f426ecd171707d742092ea14932f98f7988fc9847eccc81009` |
| `specs/211-optimize-ci-cd/plan.md` | `2a45f1997b3c419458af600ceffc2c478b5e1f3662edc36979fa8b0c917ab421` |
| `specs/211-optimize-ci-cd/tasks.md` | `49dd3b258563e99bfe65b85ce496daa7f165efe481770eed8856a3fd657c8deb` |
| `specs/211-optimize-ci-cd/quickstart.md` | `6f0e6dd4cfeda39f64954a3b6bdfb3546a90257dc7afed948b421097d2671dc1` |
| `specs/211-optimize-ci-cd/checklists/ci-package-source.md` | `7dc15ca59633b35bd60cc541242988bcec49aa156cb84a634005e8753b9b2001` |
| `.github/workflows/governance-fast.yml` | `b5261aaaf4b375a8eac6e36c16c7a523a969f107d81c58c3e23a1e402d381442` |
| `.github/workflows/release-full.yml` | `ca3c546ff5e6237bc9a9cebaeb2c69c07dab240111e62032e5f64c459c4ccff9` |
| `tests/governance/test_governance_workflow.py` | `dc2e0473edd7aab49cab7fa5909e9699c4a457bccb9c4deb2d2f30f6470ccd39` |
