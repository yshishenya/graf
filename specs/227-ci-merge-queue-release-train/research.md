# Research: CI merge queue и provenance release train

## R1 — Event-specific target identity

PR workflows expose a PR head SHA, merge queue validation is represented by
`merge_group` and its synthetic head SHA, and manual dispatch has no trusted
target without an explicitly supplied full SHA. One resolver must reject all
other cases.

## R2 — Concurrency and cancellation

`pull_request` and `workflow_dispatch` currently use different concurrency
namespaces. A canonical key must be derived from the logical target (PR number,
merge-group ID or explicit manual target), with `cancel-in-progress: true`.
Cancellation is terminal non-success, never a pass.

## R3 — Final cleanliness

Local CI checks the tree before tests, but tests/builds can create files
afterwards. The final receipt must re-check tracked and untracked drift after
artifact generation and allow only documented metadata-only evidence paths.

## R4 — Release provenance

Candidate freeze/validate/decide already binds exact source SHA and changelog
digest. A separate train manifest is needed for PR/Feature IDs, merge-group
receipts and the post-merge SHA.

## R5 — Portable boundary

Event identity, receipt schemas, stale validation and train templates are
generic. GRAF-specific signing, capture/privacy, Temporal/worker readiness and
production deployment gates remain project-local.

## R6 — Merge-group mapping

GitHub's merge-group event provides the synthetic target identity but may not
embed every pull request in the group. The workflow must resolve the mapping
from GitHub's authoritative merge-queue API using the group ID or synthetic SHA;
commit-message parsing is not an acceptable source of provenance. Missing or
ambiguous mapping is a terminal non-success state.

## R7 — Применимость текущему master (2026-10-17)

Решение: сохранить serial release operator и обязательный synthetic SHA.
`scripts/release.sh` создаёт его через `git commit-tree` с деревом source и
родителями base/source; успешный изолированный повтор подтверждён до изменений.
Nullable SHA или новый режим не устраняют реальный дефект и не нужны.

Реальный отказ защиты: base из отдельной истории принимается, если он предок
synthetic. Общая функция останавливается на первом успешном из двух отношений.
Решение: проверять обязательное base → source; synthetic остаётся метаданными.
Не требуем source → synthetic: настоящий merge-group commit может предшествовать
post-merge source и отличаться деревом; это не даёт права выпускать его вместо source.

## R8 — Закреплённая матрица переносимого инструментария

`harness/harness.lock.json`: v0.1.13, immutable SHA
`6a8257186aee878087b68fd77716ddce595a012d`. Workflow self-test на этом SHA
содержит Python 3.9 и 3.12, оба задания run 33497610330 attempt 1 прошли:
https://github.com/yshishenya/graf-development-harness/actions/runs/33497610330
Это историческая проверка закреплённой версии, не новый CI GRAF и не гарантия
для всех версий Python >=3.9. Обновлять зависимость ради этого среза не нужно.

## R9 — Применимость native queue и существующих проверок (28.10.2026)

GET GitHub: `yshishenya/graf` public, `owner.type=User`. Официальная
[Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue):
“Pull request merge queues are available in any public repository owned by an
organization, or in private repositories owned by organizations using GitHub
Enterprise Cloud.” Проверено независимым исследованием F227 и исследованием
F230 от28.10; SHA256 полученного документа
`e399632c3e8d33cfaa81e69a5534f964e62e6c9c392a52b442e036ab0fd53d78`.

Решение: последовательные защищённые PR достаточны для личного раннего MVP;
переносить репозиторий или писать собственную очередь ради старого плана не
требуется. Отменяется только нынешняя native приёмка T029/T031, не действующие
fail-closed guards. Новая доступность и потребность требуют отдельной настоящей
приёмки перед включением. Ноль merge_group runs не доказывает недоступность.

T015: schema validator допускает корректный non-passed receipt, а общий
`validate-pr-checks.py::validate_source` отдельно требует passed. Недостающая
регрессия принадлежит существующему `test_pr_checks.py`, не новому producer.
T016: ручное дублирование подлинности не добавляет; настоящий artifact уже
связан с head/base/run/attempt. T028: workflow исполняет именно существующий
`infra/scripts/ci-local.sh --fast` с event base; runner соответствует исходной
функциональной проверке без обязательного второго повтора на Mac.
