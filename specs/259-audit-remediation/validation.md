# F259 / B019 — локальная проверка исправления allocator

Дата: 2026-09-08. Ветка: codex/259-audit-remediation. База e81b412dff920cc29ed37de60be13dd8fc4d1c43; результат относится к незакоммиченному diff, не к опубликованному SHA.

## Результат

- Focused allocator + validator safety: 71 passed, 2 skipped.
- Весь tests/governance: 320 passed, 3 skipped за 34.58 s. Два пропуска — запуск PowerShell (pwsh отсутствует); третий — ранее существующая Docker restore rehearsal, требующая явного GRAF_SCHEMA_TARGET_MANIFEST.
- scripts/claim-feature.py --self-test: PASS.
- Bash syntax, Python compile и git diff --check: PASS.
- tests/unit.sh в source speckit-bootstrap: 29/29 PASS.
- Source overlay применён к исходным трём оболочкам дважды: получен точно текущий diff, повтор идемпотентен.
- Настоящее read-only предложение с GitHub и свежими remote heads: next_available=260, mode=github-checked. Проверено отсутствие изменения shared claims и active pointer. Тестовых live issues/labels не создавалось.

## Review и convergence

Проверены все входы suggestion/allocation/explicit claim и три оболочки. Удалены два независимых вычисления max occupied в пользу одного выбора после specs. Branch IDs больше 999 остаются занятыми, service refs и tags не поднимают номер; отсутствие fetch не скрывает remote-only branches. Strict GitHub error/partial results останавливают online работу. Повторная проверка под lock отклоняет stale proposal; конкурентный тест создаёт ровно одну umbrella. Существующая метка не перезаписывается; канонические padded IDs 002/012 совместимы с umbrella validation.

Авторская проверка code-reviewer не нашла оставшихся блокирующих ошибок в локальном объёме. Это не независимое одобрение PR. Перенумерация уже существующих чужих фич не выполнялась; настоящий большой ID в specs остаётся источником последовательности и требует отдельного содержательного решения, если ошибочен.

## Оставшиеся gates

T006 открыт: commit/push/PR, exact-SHA governance-fast и закрытие исходных issues ещё не выполнены. F225/B019 не объявлены полностью закрытыми. Full CI и production не запускались: только tooling, без продукта или выпуска. Frozen doctor ранее блокировался несовпадением установленного specify 1.0.4 с закреплённым 1.0.1; pin и lock не переписаны для маскировки. До merge также нужна штатная сверка lock с изменёнными generated adapters.

Source bootstrap содержит чужие незакоммиченные изменения; добавлен только собственный блок трёх замен, существующий diff сохранён. Изменения исходного ea3e worktree не тронуты.

## Дополнение: workflow и завершение issues

Проверены 12 последних merged PR: 11 без closing keywords. Отдельно GitHub ClosedEvent подтвердил автоматическое закрытие #6489 через #6491 после merge. Полный разбор и границы выводов — workflow-audit.md.

Изменён workflow (15 шагов), режим taskstoissues closeout и итоговый статус implement. Добавлен --verify-live для отдельного issue: подтверждает merged PR, успешный run правильного workflow, точный PR SHA (либо Candidate SHA при release gate). Ошибки и незавершённые задачи блокируют приёмку. Тесты используют имитацию GitHub и не закрывают реальные issues.

specify workflow info speckit успешно загружает новый граф. Source bootstrap overlay дважды применён к исходным файлам: результат совпадает с текущими навыками/workflow, повтор идемпотентен. Source bootstrap unit: 29/29 PASS. Независимого PR approval и remote exact-SHA CI пока нет; текущие изменения локальны.

Финальный прогон после проверки соответствия expected SHA и PR SHA: **323 passed, 3 skipped**, 34.54 s. Пропуски: два PowerShell без pwsh и отдельная Docker restore rehearsal без явного manifest. Полный CI/release не запускались. T007–T010 завершены локально; T006 остаётся открытым.

## Подготовка PR — 2026-09-08

Поручение владельца «доводи по PR» разрешает коммит и публикацию после проверок. Для воспроизводимости создано изолированное окружение specify-cli 1.0.1 из закреплённого ref 9118ed15a0ba65053469a94c560ea5d233f75884; глобальный CLI не менялся. Использован опубликованный bootstrap 0.9.9 с SHA-256 bdbfa1d56ab567de209ed55e2d2992284315bac43597a7c9f63f4f95b330a71c, как в governance-fast.

Шесть исходных преобразований повторно воспроизведены на файлах до F259: результат побайтно совпал с текущими навыками, workflow и тремя оболочками; повтор не меняет файлы. После удаления только Python cache штатные capture_project_dependency_state / capture_project_skills_state / write_lock_file обновили четыре ожидаемых поля lock: git tree, два skill tree и workflow SHA. Версии и закреплённые upstream refs сохранены. check_spec_kit_governance.py с опубликованным bootstrap: PASS.

Повтор tests/governance в закреплённом окружении: **323 passed, 3 skipped**, 36.12 s. Source bootstrap: Bash syntax и ShellCheck PASS, unit **30/30 PASS**, включая новый тест повторного применения, сохранения общего workflow и отказа при неизвестном исходном тексте. Ponytail review не выявил новых зависимостей, дублирующего сервиса или лишнего слоя: выбор номера и live проверка переиспользуют существующие функции.

Исходные преобразования опубликованы отдельным черновиком https://github.com/yshishenya/speckit-bootstrap/pull/39. Чужие незакоммиченные блоки bootstrap не включены в него. Полное применение всех старых преобразований к уже установленным GRAF skills остановилось на прежнем несовпадении speckit-git-commit; проверка не обходилась. Полный bootstrap refresh из upstream остаётся неподтверждённым до завершения исходного PR. Это ограничение не подменяет успешную проверку сохранности конкретных шести преобразований.

Общий checklist бэклога остаётся за проверяющим. T006 остаётся открытым до exact-SHA CI и согласования исходной приёмки F225; F259/#6827 не закрывается этим этапом. PR и его remote evidence фиксируются в GitHub, после коммита — на точном SHA. Merge, Full CI и production не входят в текущее поручение.

## Завершение проверки перед снятием Draft

По запросу «довели по meargable PR» устранены препятствия обновлению существующего GRAF в source PR #39. Полный и повторный bootstrap на изолированном клоне теперь PASS; doctor --frozen PASS; повтор не изменил файлы .agents/.specify. Настройки проекта и все изменения F259 сохранены. Подробности и границы авторского review — review.md. Этот результат заменяет прежнее ограничение о неподтверждённом полном обновлении. Общий checklist будущего бэклога остаётся неизменным.

Source unit 31/31 PASS; на обновлённом клоне governance 323 passed, 3 skipped (41.75 s). Продуктовые и релизные gates не запускались. Обязательный remote CI привязывается к окончательному SHA в PR; T006 остаётся открытым по содержательной приёмке исходного F225, хотя CI этапа выполнен.


## Дополнительное исправление перед выпуском — 2026-09-09

Независимая проверка требований B019 принята отдельно от будущего общего
бэклога (review.md). T001–T012 связаны с дочерней #6837.
Allocator читает GRAF_UMBRELLA_ISSUE в общем входе, исключает свою резервацию
из подсказки и проверяет её принадлежность до возврата номера. Общая файловая
блокировка использует fcntl на Unix и msvcrt на Windows; подсказка не импортирует
Unix-модуль. После converge добавлен явный gate с остановкой при новых задачах
до taskstoissues→implement→converge. Source bootstrap получил ту же запись
процесса; его ранее существовавшие незакоммиченные изменения сохранены.

Проверки: allocator/validator76PASS,2SKIP; весь governance325PASS,3SKIP
(два сценария PowerShell без pwsh и отдельная Docker restore rehearsal).
Windows API lock/unlock и отсутствие fcntl проверены имитацией, реальная Windows
не заявляется. Self-test, Bash syntax и git diff --check PASS. Source bootstrap
unit29/29PASS. Lock обновлён штатными capture/write функциями, изменён только
workflow SHA; версии и hash исходного архива сохранены. Frozen doctor с
закреплённым specify1.0.1 и bootstrap0.9.9 PASS. Новый GitHub gate ожидается.
T006 и T012 открыты до итоговой приёмки; F225 и общий бэклог не закрывались.

## T013: существующие названия с `_` и `.` — 2026-09-09

Замечание [PR #6831](https://github.com/yshishenya/graf/pull/6831#discussion_r3965958717) подтверждено на master 0ad486df265a2555be0284ce69119d9d68b10a4c. Общий `_sequential_id` ошибочно применял ограничения создания slug к инвентаризации существующих specs и refs. Исправление распознаёт префикс `NNN-` или голый числовой каталог; исключение timestamp остаётся перед ним, фильтр служебных refs — у вызывающей функции. Новые имена по-прежнему проходят прежнюю нормализацию и проверку.

Регрессия на реальных Git refs и каталогах: оба символа × specs/локальная/удалённая ветка. До исправления 6 FAIL: занятый 259 пропущен. После исправления allocator/validator: **82 passed, 2 skipped**, 8.96 s; все шесть случаев сохраняют 259 занятым и предлагают 260. Пропуски — PowerShell без pwsh. `python3 scripts/claim-feature.py --self-test`: PASS, включая конкуренцию claims между worktrees.

Авторский review/convergence T013: проверены оба потребителя общего parser и повторный выбор номера; FR-012/013 выполнены в ограниченном объёме. Дополнительных зависимостей, обходов проверки GitHub или изменений формата reservations нет. Общий reviewer-owned checklist сохранён. Lane: Active Spec Kit slice. Точный SHA и обязательный governance-fast фиксируются в новом PR после коммита; Full CI, продуктовая проверка и выпуск здесь не требуются. T006, #6837 и #6827 остаются открытыми до своей полной приёмки.

Дополнительно: `validate-agent-context.py`, `validate-changelog-fragments.py`, `check_spec_kit_governance.py` с закреплёнными CLI/bootstrap, Bash syntax и `git diff --check`: PASS. Read-only `claim-feature.py --json` на живом репозитории вернул 6792, mode github-checked; хеши active pointer и shared claims до/после совпали. Это наблюдение текущего инвентаря, а не завершённая приёмка всей F225.

## T014–T017: последовательность после исторической F6788 — 2026-09-09

Ветка `codex/259-sequence-policy`, база
`495cefab3d4a712a3e34bf922d315cc243817de8`, рабочая копия
`/tmp/graf-feedback.oy0uyz`. Результат относится к локальному diff, не к новому
коммиту или опубликованной версии. T013 в основе сохранён. Lane:
high-risk-product / significant governance, активный этап US3/B019.

Причины: основной checkout остался на старой F231 и выдаёт локальную подсказку
`spec_next=251`; актуальный прежний allocator считает настоящий исторический
каталог F6788 началом последовательности и перескакивает в диапазон 6789+.
Это разные источники ошибки. Новое руководство требует свежую отдельную
рабочую копию и общий online allocator; существующая работа не переключается.

Решение: явная project-owned политика исключает только F6788 из вычисления
начала, но не из занятости. Сохранены все IDs/specs/ветки/claims, обычные F1000+,
блокировка и повторная проверка GitHub. Политика строго проверяется, включая
повтор JSON-ключа, неверный тип, неположительные/повторные ID, invalid UTF-8 и
ошибки чтения. Без файла поведение прежнее. Upstream, generated skills,
оболочки, lock и глобальная установка CLI не изменены.

### Проверки

- До исправления новая регрессия: **4 FAIL, 3 PASS**; историческая F6788
  ошибочно поднимала начало до 6789, в том числе при нормальных F999/F1024.
- Итоговый запуск `apps/server/.venv/bin/python -m pytest -q
  tests/governance/test_feature_allocator.py tests/governance/test_validator_safety.py`:
  **107 PASS, 2 SKIP, 8.82 s**. Оба пропуска — отсутствие `pwsh`.
- В изолированных Git fixtures Bash/Python dry-run не меняют refs/claims/pointer
  и не вызывают запись GitHub; реальное создание ветки использует ту же политику.
  Явный claim исторической F6788 отклонён. Конкурентные allocate создают одну
  имитированную umbrella, второй устаревший запрос отклоняется.
- `claim-feature.py --self-test`, Python syntax, Bash syntax,
  `validate-agent-context.py`, `check-development-process.py`,
  `git diff --check`: PASS.
- `check_spec_kit_governance.py` с изолированными закреплёнными
  specify 1.0.1 / bootstrap 0.9.9: PASS, включая frozen doctor и инварианты GRAF.
- Live `python3 scripts/claim-feature.py --json`: **next_available=263**,
  `mode=github-checked`, `occupied_count=233`. Совпали SHA-256 до/после для
  pointer, политики, shared claims и heads/remotes. Это предложение на момент
  проверки, не резервирование F263; перед реальным резервом нужна повторная проверка.
- Основной `/Users/yshishenya/Documents/crisp` остался чистым на F231,
  HEAD `2d93584b6aa0224b2a29ba9bc90b19abbe9d20fa`.

### Review, converge и границы

Независимые checklists: numbering 6/6; requirements 13/13 — качество требований
и полнота датированного реестра, не выполнение бэклога. T014–T017 добавлены
к существующему #6837 без дублей. По точному разрешению владельца в #6852
добавлены только `area:governance` и `Spec tasks: T000`; номер, название,
остальной текст и состояние сохранены. Обязательная проверка канона прошла
для 300 возвращённых issues, не заявляется аудит всех issues репозитория.

Авторский code-reviewer: блокирующих замечаний в текущем diff нет; не является
независимым одобрением PR. Ponytail-review позволил сократить проверку повторных
ключей через stdlib `dict` без обхода ошибок; новые зависимости не добавлены.
Converge текущего ремонта: FR-023–FR-026 / SC-006–SC-007 — 6/6; проверены
решения политики, сохранения занятости, общих входов и начала новой работы,
принцип VI и ограничения Development Workflow конституции. Новых пробелов
missing/partial/contradicts/unrequested нет, новых задач не добавлено;
`tasks.md` в самом converge оставлен без изменения.

T006, F225 и общий бэклог F259 не завершены; #6837/#6827 не закрывались.
Commit, push, GitHub governance-fast на новом точном SHA, merge и выпуск не
выполнены. Full CI, продуктовые/аппаратные проверки и полный повтор bootstrap
в этом ремонте не запускались. Сокращение чтения PRD/истории и ускорение тестов
ещё не внедрены: следующий этап требует чистой основы после разрешённого
коммита этого ремонта. Формат автоматически создаваемых umbrella требует
отдельного исправления перед новой фичей; исправление старого #6852 не
устраняет этот дефект генератора.
