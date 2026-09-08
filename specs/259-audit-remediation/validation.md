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
