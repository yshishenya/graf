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
