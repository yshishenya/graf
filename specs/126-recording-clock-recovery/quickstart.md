# Quickstart: проверка восстановления записи

Команды выполняются из корня репозитория.

## Быстрые тесты

```sh
cd apps/macos
swift test --filter RecordingAudioTimelineTests
swift test --filter SystemAudioRecordingPackageTests
swift test --filter SystemAudioCaptureServiceTests
```

Эти тесты не печатают samples или transcript. Они проверяют frame counts,
durations, status, reason codes и набор файлов во временной директории.

## Полная локальная проверка

```sh
cd /Users/yshishenya/.codex/worktrees/39b6/crisp
infra/scripts/ci-local.sh
```

При ошибке сначала повторить узкий XCTest filter, затем классифицировать
ошибку как product regression, environment/dependency или existing baseline
failure. Не добавлять raw audio/transcript в logs или evidence.

## Сценарная матрица

| Сценарий | Ожидаемый результат |
| --- | --- |
| оба источника, callback delay 0–500 мс | complete v5 package, no timeline failure |
| обратный порядок callback-ов | маркеры остаются на PTS frame index |
| 44.1 kHz/stereo + 48 kHz/mono | stateful conversion в 48 kHz mono |
| короткий gap/overlap | bounded silence/trim, deterministic counters |
| route change/drop/overflow/missing source | fail-closed manifest, no upload |
| Stop во время pending batch | native queue drain, ровно один package |
| повторный Stop/relaunch/queue refresh | no duplicate package/meeting/ASR |

## Hardware evidence (не входит в локальный CI)

После отдельного разрешения и на тестовом аккаунте выполнить headset-first
60-minute Zoom run с unchanged audio route. Сохранить только metadata receipt:
session id, route/permission state, frame/byte/duration counters, drift,
dropout/reason codes, upload/ASR idempotency result. Не считать synthetic tests
подтверждением T063 hardware gate.
