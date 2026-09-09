# Проверки B019

1. `python3 scripts/claim-feature.py --self-test`.
2. `python -m pytest tests/governance/test_feature_allocator.py tests/governance/test_validator_safety.py -q`.
3. `bash -n .specify/extensions/git/scripts/bash/create-new-feature-branch.sh`; Python compile changed scripts.
4. `python3 scripts/claim-feature.py --json`: read-only, до/после сравнить claims и active pointer; предложение не должно идти от 6788.
5. Выполнить Bash/Python dry-run в изолированном git fixture: один номер с direct suggestion, нет branch/issue/label writes; PowerShell тот же сценарий при доступном pwsh.
6. Тесты: service refs/tags/nested numbers/timestamps, real F1024 collision, GitHub error/partial response, occupied next ID, repeated allocation, existing/missing label, отсутствие изменения чужих меток.

Полный CI, создание тестовых issues в реальном GitHub и release не требуются для локального исправления. Для frozen doctor использовать отдельное окружение с CLI 1.0.1 из ref, указанного в lock; глобальный CLI 1.0.4 не заменяется. Воспроизводимость и ограничения source refresh записаны в validation.md.
