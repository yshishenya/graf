# Contract: CI-кэш Swift и доказательства (Feature 269)

**Version**: 1 | **Date**: 2026-09-16 | **Applies to**: `.github/workflows/macos-pr.yml`, `.github/workflows/release-full.yml`, `infra/scripts/ci-local.sh`

## 1. Кэш Swift-сборки (GitHub Actions)

Во job'ах macOS-проверок добавляется шаг `actions/cache@v4` перед сборкой.

| Параметр | Значение |
|----------|----------|
| `id` шага | `swift-cache` |
| `path` | `apps/macos/.build`<br>`~/.cache/org.swift.swiftpm`<br>`~/Library/Caches/org.swift.swiftpm` |
| `key` | `swift-${{ runner.os }}-${{ runner.arch }}-spm6.0.3-${{ hashFiles('apps/macos/Package.resolved') }}-v1` |
| `restore-keys` | `swift-${{ runner.os }}-${{ runner.arch }}-spm6.0.3-` |

**Инварианты**:

1. Набор шагов проверки не зависит от попадания в кэш: `swift build`, `run-swift-tests.sh`, `ContractValidation` выполняются всегда.
2. Промах кэша и недоступность сервиса кэша приводят к полной сборке, не к пропуску шагов.
3. При попадании в кэш отдельный шаг обновляет mtime восстановленных артефактов (`find apps/macos/.build -exec touch {} +`): `actions/checkout` записывает исходники после восстановления, поэтому без обновления llbuild считает выходные файлы устаревшими и пересобирает все модули (измерено: ~98 с лишней сборки).
4. Ключ изменяется при изменении `apps/macos/Package.resolved` или версии Swift; литерал версии в ключе синхронизирован с `swift-version` в workflow (обе проверки используют `6.0.3`). При смене версии инструмента ключ обязан измениться.
5. Кэш не содержит секретов и не влияет на подпись/нотаризацию (эти шаги не используют кэш).

## 2. Артефакты доказательств (`ci-local.sh`)

- `--artifact "macos-build=<весь apps/macos/.build>"` заменяется на набор явных продуктов:
  - `macos-product-two-brain-rec-app=apps/macos/.build/debug/TwoBrainRecApp`
  - `macos-product-contract-validation=apps/macos/.build/debug/ContractValidation`
  - `macos-product-meeting-mute-truth=apps/macos/.build/debug/MeetingMuteTruthRuntimeProof`
  - `macos-product-webrtc-aec3=apps/macos/.build/debug/WebRTCAEC3Validation`
  - `macos-product-leakage=apps/macos/.build/debug/LeakageValidation`
  - `macos-tests=apps/macos/.build/debug/TwoBrainRecMacOSPackageTests.xctest`
- Добавляется только существующий путь; отсутствие отдельного продукта не делает запись недействительной.
- `source-revision`, `component_shas` и `candidate_id` сохраняют текущие правила привязки к точному SHA.
- Запись остаётся валидной по `harness/schemas/ci-evidence.schema.json` (имена артефактов не ограничены схемой).

## 3. Совместимость и проверка

- Существующие потребители evidence используют `artifact_digests."source-revision"` и компонентные SHA; переименование macOS-артефактов не затрагивает обязательные поля.
- Проверка контракта: `tests/governance/test_ci_cd_contract.py` и `test_local_postgres_test_runner.py` должны оставаться зелёными; при необходимости контрактные тесты дополняются проверкой наличия шага кэша и новых имён артефактов.
- Локально: `infra/scripts/ci-local.sh --fast` после изменения скрипта; `bash -n` для затронутых скриптов; GitHub `governance-fast`, `macos-pr`, `pr-metadata` на точном SHA PR; `release-full` на замороженном кандидате.
