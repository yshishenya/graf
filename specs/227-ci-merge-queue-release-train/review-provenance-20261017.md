# Независимое ревью F227: происхождение выпуска

Дата: 2026-10-17 (Europe/Istanbul). Ветка:
`codex/227-ci-merge-queue-release-train`. Базовый SHA:
`c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.

Область: качество требований активного среза T032–T033 до изменения кода.
Ревьюер менял только оба контрольных списка и этот отчёт. Код, spec, plan,
tasks, GitHub, коммиты, выпуск и развёртывание ревьюером не изменялись.

## Решение

**Требования T032–T033: PASS, CRITICAL 0 / HIGH 0.**
Контрольные списки перечитаны после правок: infra **13/0**, requirements
**16/0**, всего **29 checked / 0 unchecked**.

Это разрешает пройти последующие ворота анализа и синхронизации issues перед
реализацией. Оно не завершает T033, всю F227, настоящие T029/T031, приёмку
будущего PR или выпуск. Отсутствие настоящего merge_group не подменено локальным
успехом. Утверждение о недоступности native queue не выводится из owner.type или
пустой истории API; применён действующий порядок последовательных слияний.

## Использованные доказательства

- Прочитаны текущие spec, plan, tasks, quickstart, research, data-model,
  clarifications и оба contracts F227, вся конституция 7.1.0, guidance index,
  spec-kit-flow и применимые разделы release-and-validation.
- Прочитан реальный serial caller `scripts/release.sh`: создаётся отдельный
  commit-tree с деревом source, родителями base/source и пустыми queue arrays.
- Прочитаны `require_git_commit_relationship` и train-freeze в
  `infra/scripts/release-candidate.sh`, schema/validator train, CI receipt schema,
  event resolver, mapping verifier, workflow identity/concurrency и финальная
  проверка чистоты локального CI.
- Из внешнего реестра прочитаны текущие факты репозитория и исходное
  воспроизведение: обычный serial поток проходит; несвязанная с source база
  ошибочно принимается, если она предок synthetic. Этот отрицательный результат
  подтверждает необходимость T033, а не её завершение.
- Независимо выполнено до реализации:
  `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/governance/test_release_train.py`:
  **8 passed / 21.14 s**; `python3 scripts/validate-release-train.py --self-test`:
  **OK**. Существующие восемь тестов ещё не проверяют новую регрессию ancestry.
  Fixture подставляет PR checks и Full CI: это не настоящее GitHub evidence.
- `harness/harness.lock.json` сверён с сохранённым workflow и proof точного
  pinned SHA `6a8257186aee878087b68fd77716ddce595a012d`, v0.1.13.
  [Run 33497610330 attempt 1](https://github.com/yshishenya/graf-development-harness/actions/runs/33497610330)
  содержит успешные jobs Python 3.9/3.12. Это исторический запуск закреплённого
  внешнего инструментария, не новый CI продукта и не все версии Python >=3.9.

## Каждый пункт infra

Здесь отмечается качество требований. Наличие будущего теста или читаемого кода
не объявляется исполненным runtime gate.

| Пункт | Результат и основание |
| --- | --- |
| 1. Event-specific target/base | PASS: FR-001/002, US1 и CI receipt contract различают PR head, merge-group synthetic и явный manual target; неизвестные значения отвергаются. |
| 2. Merge-group checkout/mapping | PASS: FR-003 и R6 требуют authoritative полный mapping и отказ при неоднозначности; T029/T031 отдельно сохраняют настоящий rehearsal. |
| 3. Concurrency | PASS: FR-004 и US2 определяют логическую цель и исключают отмену других целей; workflow использует отдельные PR/merge-group/manual namespaces. |
| 4. Cancellation/stale | PASS: FR-004/006/008, SC-002 и receipt contract задают terminal non-success, а не успешное evidence отменённого запуска. |
| 5. Final cleanliness | PASS: FR-005, US2/SC-003 явно требуют tracked/untracked проверку после тестов/артефактов с документированными metadata-only исключениями. |
| 6. Metadata/schema | PASS: FR-006, contracts и plan запрещают secrets/private data; существующие схемы и валидаторы ограничивают структуру. |
| 7. Synthetic/source | PASS: FR-007/011 и уточнения различают два SHA, сохраняют обязательный полный synthetic и existence commits, требуют base→source. Текущее нарушение — предмет T033. |
| 8. One Full CI | PASS: FR-008, US3, SC-004 и release contract требуют единственное authoritative evidence замороженного source и новый candidate после дрейфа. |
| 9. Operator ownership | PASS: FR-009, plan/out-of-scope и quickstart сохраняют отдельное решение оператора; текущий срез не меняет GitHub protection/queue. |
| CHK010 | PASS: уточнения и FR-009, plan, quickstart, tasks сохраняют serial/native границы и открытые T029/T031. |
| CHK011 | PASS: FR-011/SC-007 и release contract явно требуют base→source, локальные commits и отказ без train/identity; synthetic не заменяет source. |
| CHK012 | PASS: plan и quickstart прямо разделяют подставленные fixture proofs, обязательные реальные PR checks и одобряемый отдельно release-full. |
| CHK013 | PASS: R8 и quickstart содержат immutable harness SHA, версии 3.9/3.12, run/attempt и ограничения исторического доказательства. |

## Каждый пункт requirements

| Пункт | Результат и основание |
| --- | --- |
| 1. Нет лишних деталей реализации | PASS: обязательные поля и SHA — наблюдаемые контракты выпуска; изменения конкретной общей функции помещены в plan/tasks. |
| 2. Пользовательская ценность | PASS: цель и why каждой US связывают требования с безопасным слиянием и достоверным выпуском. |
| 3. Понятный язык | PASS: цели, сценарии, границы и новые уточнения читаются отдельно от неизбежных названий Git/GitHub и полей. |
| 4. Обязательные секции | PASS: цель, сценарии/приёмка, edge cases, requirements, measurable criteria, assumptions, exclusions и legacy impact присутствуют. |
| 5. Нет NEEDS CLARIFICATION | PASS: маркеров нет; clarifications C1–C6 и spec уточняют актуальные вопросы без нового решения владельца. |
| 6. Проверяемость/однозначность | PASS: FR-001–011 задают проверяемые identity, отказ, чистоту и происхождение; T033 не зависит от непроверенной доступности очереди. |
| 7. Измеримость | PASS: SC-001–007 содержат нулевой mismatch, 100% отрицательных случаев, минимум три PR, один Full CI и отсутствие output при ancestry отказе. |
| 8. Независимость результата от технологии | PASS: результат — достоверная идентичность/решение о выпуске; Git/GitHub ограничения нужны для описания существующей платформы. |
| 9. Приёмочные сценарии | PASS: три US описывают положительные/отрицательные пути, SC-007 добавляет точный serial/несвязанный-base случай. |
| 10. Пограничные случаи | PASS: malformed/missing identity, API mapping, cancellation, drift, untracked files, различие synthetic/source и неполная история указаны. |
| 11. Границы | PASS: нет runtime продукта, GitHub protection mutation, нового режима/nullable SHA, выпуска или закрытия native gates. |
| 12. Зависимости/допущения | PASS: актуальные PR checks, serial порядок, release-only Full CI и закреплённый harness явны; tasks T032→T033 сохраняет порядок. |
| 13. Критерии FR | PASS: FR-001–010 связаны с US1–US3/SC-001–006; новый FR-011 с SC-007 и T033. |
| 14. Основные потоки | PASS: US1 exact CI, US2 stale protection, US3 batch release покрывают цель; serial проверка выделена, native сохранена. |
| 15. Измеримые outcomes | PASS требований: измеримые SC присутствуют; этот пункт не удостоверяет фактическое достижение всей F227. |
| 16. Нет приватного содержимого | PASS: просмотренные изменённые требования содержат только metadata, публичные SHA/ссылки и воспроизводимые команды. |

## Обязательные дальнейшие проверки

T033 должна доказать отказ того случая, который до правки ошибочно проходит,
и сохранить положительный serial поток с тремя PR/пустыми queue collections.
Проверки существования трёх commits, distinct synthetic/source, current source,
чистоты и прежние PR/Full CI gates должны остаться. Полезно сохранить отдельные
отрицательные случаи недоступного commit и ошибки Git; отсутствие train и
identity должно проверяться явно. Это проверка реализации, не новый вопрос к
владельцу и не блокирующий пробел требований.

На момент этого предреализационного ревью новых CRITICAL/HIGH требований нет.
Код ещё содержит описанный дефект, исправление не проверено. Commit требует
отдельного согласия после проверки; merge, release и deploy остаются отдельными.

Повторная сверка перед передачей результата: прочитан
`analysis-provenance-20261017.md` (18/18 FR+SC, CRITICAL 0/HIGH 0) и актуальный
append-only хвост tasks с единственным владельцем T032–T033
[#7645](https://github.com/yshishenya/graf/issues/7645). Историческая
reconciliation 31 старой задачи остаётся в T030/#6237; она не выдана за
завершение текущего среза. Оба контрольных списка перечитаны полностью;
13/0 + 16/0 подтверждены подсчётом, `git diff --check` для них прошёл.

## Второй этап: независимое ревью реализации T033

**PASS, actionable findings 0.** Проверены фактический diff, общая функция и её
единственный caller train-freeze; реальный release operator продолжает создавать
отдельный commit-tree с деревом source и родителями base/source. Удалён только
прежний OR по происхождению synthetic/source: любой ненулевой результат
`git merge-base --is-ancestor base source` теперь блокирует заморозку. Проверка
существования каждого из трёх local commit objects осталась перед этим условием.
Новая проверка source→synthetic не добавляется: она могла бы неверно запретить
будущий queue synthetic, предшествующий actual post-merge source.

Независимо выполнено на рабочем diff:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/governance/test_release_train.py`: **9 passed / 21.15 s**.
- `bash -n infra/scripts/release-candidate.sh`: PASS.
- `python3 scripts/validate-release-train.py --self-test`: OK.
- `git diff --check`: PASS.
- `git diff --exit-code HEAD -- infra/release/train.schema.json scripts/validate-release-train.py scripts/release.sh scripts/validate-pr-checks.py`: PASS, эти файлы не изменены.

Новая исполняемая регрессия подтверждает:

1. Настоящие Git commits и serial commit-tree принимаются; manifest содержит
   source/synthetic отдельно, три PR и пустые merge_group_ids/receipts;
   `train-validate --current` проходит. GitHub PR proofs подставлены fixture.
2. Для base из отдельной истории создан собственный synthetic-потомок. Хотя base
   входит в его историю, base не предок source; train-freeze отказывает с точным
   сообщением до появления manifest и `.identity.json`. Конструкция этого
   synthetic задаёт parent явно, а отсутствие отношения с source проверено Git.
3. При корректном base, но отсутствующем synthetic commit train-freeze отказывает
   до появления manifest/identity. Обязательный полный SHA не стал nullable.

По исходному baseline этот отрицательный ancestry случай проходил; сохранённые
исходные восемь тестов не ловили дефект. Новая проверка закрывает именно этот
пробел. Схема, CLI и serial release caller не изменены. В train-freeze после
новой проверки сохраняются HEAD/origin master identity, tracked/untracked
cleanliness, changelog digest и authoritative exact PR set; write-once identity
создаётся ниже всех этих ворот. Attest/decide и один authoritative Full CI
проверены чтением неизменённого кода и существующими тестами, а не реальным
запуском выпуска. Fragment F227 описывает ровно это усиление и native ограничение.

SHA-256 проверенных файлов рабочего diff:

- `infra/scripts/release-candidate.sh`: `dcfa09b9e643cbf64481926ffa8586b61e130ec9844893bd6121feeee625beeb`
- `tests/governance/test_release_train.py`: `186669f39ecc5e824e788250a2d49e7aa4b8e29468ea0079f801deb47a7cf84d`
- `changes/unreleased/F227.yaml`: `60a8aad75b4a4f604c1e11eee947e2d0506d7450b9bfcd367b5e530dbe98225c`

Оба контрольных списка повторно перечитаны после ревью: infra **13/0**,
requirements **16/0**, всего **29/0**. Это сохраняет подтверждение требований
и локального исправления; не удостоверяет actual GitHub checks, merge, native
T029/T031 или release acceptance. Ревьюер по-прежнему изменял только разрешённые
списки и отчёт; другие файлы/внешнее состояние не менял.
