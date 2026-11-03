# Проверки B019

Для текущего ремонта T014–T017 дополнительно: specs259/6788 с явным
исключением6788 →263 при занятых260..262; занятость263 в GitHub →264;
исключённый ID всё ещё недоступен для резервирования. Проверить malformed,
нечитаемую политику, unknown/duplicate keys, bool/string/zero/negative/duplicate IDs,
отсутствие политики и F1000+. Все оболочки дают то же предложение.
Live read-only сравнивает claims/pointer/refs до и после. Результат263 —
снимок, не обещание будущего номера. Основной старый checkout не изменяется.

1. `python3 scripts/claim-feature.py --self-test`.
2. `python -m pytest tests/governance/test_feature_allocator.py tests/governance/test_validator_safety.py -q`.
3. `bash -n .specify/extensions/git/scripts/bash/create-new-feature-branch.sh`; Python compile changed scripts.
4. `python3 scripts/claim-feature.py --json`: read-only, до/после сравнить claims и active pointer; предложение не должно идти от 6788.
5. Выполнить Bash/Python dry-run в изолированном git fixture: один номер с direct suggestion, нет branch/issue/label writes; PowerShell тот же сценарий при доступном pwsh.
6. Тесты: service refs/tags/nested numbers/timestamps, real F1024 collision, GitHub error/partial response, occupied next ID, repeated allocation, existing/missing label, отсутствие изменения чужих меток.

Полный CI, создание тестовых issues в реальном GitHub и release не требуются для локального исправления. Для frozen doctor использовать отдельное окружение с CLI 1.0.1 из ref, указанного в lock; глобальный CLI 1.0.4 не заменяется. Воспроизводимость и ограничения source refresh записаны в validation.md.

## Регрессия 2026-09-11

Проверить FR-027–029 через tests/governance/test_feature_allocator.py:
каскад6788/6791/6792 не поднимает последовательность, GitHub проверяется,
999 выдаётся если свободен, затем явная ошибка; неверные пределы отклоняются,
новые большие claims запрещены, старые retries сохранены. Общие проекты без
max_feature_id по-прежнему допускают1000+. Проверить совместный номер branch/
spec/pointer и сохранение его полей, идемпотентность bootstrap overlay.
Live online proposal не резервирует номер и не меняет refs/claims/pointer.

## Владение главной issue (2026-10-16)

```sh
/Users/yshishenya/Documents/crisp/apps/server/.venv/bin/python -m pytest tests/governance/test_validator_safety.py -q
python3 scripts/validate-issue-closeout.py --self-test
python3 scripts/check_spec_kit_governance.py
git diff --check
```

До исправления направленная проверка канонического владельца в главной issue
падает с `T010 has no task-backed issue`. После исправления эта проверка и
весь существующий validator suite проходят. Отдельно проверить отказ для
unchecked, неверной ссылки, двух владельцев, временной T000, открытого
ребёнка и более раннего closedAt главной issue. Тестовые GitHub объекты
синтетические; реальные issues тест не изменяет.

Две прежние положительные синтетические связки (pytest и `--self-test`)
согласовать с каноном: выполненная T017 → #6415 в tasks и T017 в комментарии
главной issue. Сохранить все прежние assertions и отрицательные ожидания;
не добавлять исключение для неизвестной задачи.


## Связь CI и повторного PR — 2026-10-16

Сначала воспроизвести прежний отказ при пустом run.pull_requests и
неоднозначной commit-связи, но успешном точном полном proof. После изменения
это PASS; отсутствующий/чужой/неуспешный proof, неправильные workflow/event/
path/SHA/PR, непустая противоречащая API-связь остаются FAIL. Проверить
кэширование полного proof при нескольких issues одного PR/head/run.

Выполнить весь tests/governance/test_validator_safety.py и
python3 scripts/validate-issue-closeout.py --self-test. Общие proof-проверки
не менять; существующий tests/governance/test_pr_checks.py выполнить как
регрессию, если этот путь присутствует. Реальный single/live replay #7020
с временным proposed closure и PR #7123/head751d52a9381f8db2b2464dd5fcccfcbf4c7e480d
должен пройти; для старого #7059 общий proof обязан отказать.
Это только чтение GitHub: комментарии и закрытия этим replay не публикуются.
Локально не запускаются приложение, Docker или полный выпускной CI.

У существующего test_feature_closeout_verifies_github_workflow_conclusion_and_head_sha
ожидание FAIL после commit_prs.append(9999) при успешном common proof является
самим воспроизведённым дефектом. Заменить его на PASS с проверкой точного
вызова общего валидатора. Отдельно сохранить отказы для неправильной непустой
run-связи и отсутствующего/чужого proof; остальные защитные assertions не
ослаблять. Синтетический mock не является живым доказательством.
