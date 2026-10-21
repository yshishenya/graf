# F290: проверка

## Первый CI-срез

Предусловия: requirements review полностью PASS, analyze без critical/high,
issue sync, чистая база c6c5441c930b8c1ecffed6de9b80773aa0e757e5; owned changes
F290 допустимы. Перед крупной сборкой проверить df -h, запас80ГБ.

```sh
python3 -m pytest tests/governance/test_governance_workflow.py tests/governance/test_pr_metadata_event.py -q
python3 -m pytest --confcutdir=apps/server/tests/contract apps/server/tests/contract/test_ci_cd_contract.py -q
python3 scripts/validate-governance-workflow.py
python3 scripts/validate-full-ci-workflow.py
python3 scripts/check_spec_kit_governance.py
actionlint .github/workflows/*.yml
git diff --check
```

В existing workflow harness исполнить реальный Bash выбора Swift с временным
подменным filesystem root: положительный swift/swiftc6.0.3, отсутствие каждого
binary,6.0.31/6.0.2, nonzero с корректным stdout, ошибка xcrun, SDK drift.
При ошибке GITHUB_PATH остаётся без новых записей. Проверить в трёх YAML
одинаковый шаг, новые cache key/restore-prefix, реальные build/tests/ContractValidation.
Это regression harness, не доказательство настоящего Apple compiler.

После независимого diff review и проверки открыть PR по действующему общему разрешению; затем:
```sh
python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr <PR>
```
Три exact-SHA checks и настоящий native build обязательны. macos14 brownout
не считается кодовым PASS. Новый frozen release требует отдельный Full;
старый опубликованный кандидат повторно не запускать.

## US2 — до ротации

Сначала закрытая read-only инвентаризация immutable stash OID, index и untracked
parent и сопоставление с чужими пятью файлами (release-v2026.10.16.6). Не применять
stash, не выводить сообщения/приватный diff. После уточнения design/review:
ошибка dump/mirror, незавершённый backup, disk pressure, delete failure,
конкуренция, protected last backup, symlinks/path escape и restore rehearsal.
Использовать existing test_deployment_backup_restore_rehearsal.py и dry-run
backup-rec-stack.sh/rehearse-rec-restore.sh. Полезные изменения — только после
согласования владельца, отдельной проверки и разрешённого commit. Удаление
сохранённой работы согласуется отдельно после доказанного решения.

## US3 — до production

Составить четыре точные процедуры в post-deploy-procedures.md: prerequisites,
source/time, синтетический fixture, действия, ожидаемые факты, rollback/cleanup,
владелец ошибки; затем независимое review. Изолированно выполнить существующие
retry/restart/backfill/priority/deletion/Range tests через штатный PostgreSQL runner.
Новые container builds только после дискового preflight и с очисткой своего temp.
Только затем запросить согласие на конкретные production действия.

- automatic_retry: управляемый отказ, автоматическое восстановление и cleanup.
- backfill_inventory: отдельное чтение агрегатов; inventory service пишет.
- range_playback: synthetic auth200/206/416, Range bytes и браузерная перемотка.
- normalization_cleanup: DB/object/temp residue и сохранность active lease/source.

Ни пользовательские записи, ни healthy worker, ни пустая выборка не заменяют
сценарии. #6501/#7646 остаются открыты до всех исходных результатов и live
feature closeout validator. Release/deploy и installed app acceptance раздельны.


## T015 — два MainActor method reference

После независимого допуска требований проверить минимальный diff двух map
в TwoBrainRecApp.swift и все callers методов; выполнить существующие
MeetingDetectionRecordingLifecycleTests/CaptureControlTests/DesktopNotificationAppIntegrationTests и построение
TwoBrainRecApp в отдельном временном scratch-path (без установки/запуска).
Исходный hosted отказ сохраняется; локальный новый compiler — диагностика.
Решающая приёмка: настоящий AppleSwift6.0.3 в macos-pr, все XCTest,
ContractValidation, governance-fast и pr-metadata одного PR SHA/основы.
