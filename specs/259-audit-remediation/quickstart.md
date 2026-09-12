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
