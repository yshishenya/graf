# Implementation Plan: Единый источник расшифровки

**Branch**: `275-retire-dual-transcription` | **Date**: 2026-09-23 | **Spec**: [spec.md](spec.md)

## Summary

Удалить старый отправитель и producers, включая desktop upload и служебные проверки. Сервер принимает актуальные источники, а старые сохранённые ревизии без внешнего job прекращают обработку до запроса. Чтение и удаление существующих данных сохраняются.

## Technical Context

- Python 3.13, FastAPI, SQLAlchemy/PostgreSQL, httpx, Temporal; Swift/macOS.
- Storage: существующие Postgres/MinIO и локальная очередь.
- Testing: pytest, Swift Testing/XCTest, ContractValidation, Ruff.
- **Risk / Validation Lane**: high-risk-feature — внешняя отправка, upload/retry и совместимость данных.
- **Release Gate**: no deploy; PR: governance-fast, macos-pr, pr-metadata на точном SHA; release-full и deployment отдельно.
- Performance: нет нового перекодирования и дополнительных запросов; потоковая отправка и существующие ограничения размеров сохраняются.
- Scope: apps/server/src, tests, scripts; apps/macos Sources/Tests/Tools; infra/scripts; текущие docs/contracts.

## Constitution Check

До исследования и после проектирования: PASS. Нативный захват двух физических источников и общая временная шкала сохраняются. Удаляется формат передачи. Видимый Stop, разрешения, tenant/access/deletion fences, серверные ключи и содержание результатов не меняются. Новых зависимостей нет. Независимый reviewer проверяет checklist до реализации.

## Design And Phases

1. Сервер: удалить submit_dual_track и paired staging. ProcessingSourceArtifacts имеет один source_artifact; load_processing_source выбирает поддерживаемые виды. Несовместимый источник получает failed_terminal с безопасным кодом до reservation/claim/egress. Старый неизвестный POST не повторяется; известный external ID допускает poll/import/delete. Из store удалить лишние mic/incoming параметры; исторические поля ORM сохранять только для чтения/удаления/provenance. Сохранить точные existing single-file fingerprints, включая прежнюю сериализацию null-полей: новая сериализация не должна ломать retry.
2. API: новый default соответствует v5; initial_recording и старые роли запрещены в новых/продолжаемых upload до dispatch. Enum допускает чтение старых строк. Ручной путь не меняется.
3. Desktop: удалить старые descriptors/payload; не-v5 блокируется до сети и остаётся удаляемым. Не удалять реальные capture-source microphone/system и декодирование deletion tombstones.
4. Fixtures/scripts: положительные проверки используют v5 или manual; синтетический WAV содержит корректный RIFF/PCM, M4A соответствует контракту. Проверить create_test_artifact.py, upload_test_artifact.py, seed_smoke_outcome.py, run-production-smoke.sh; seed выбирает media конкретной ревизии.
5. Docs: mediascribe-api.md заменяет активный dual-track документ; актуальные ссылки, PRD/status, readiness и owned changelog обновляются. Исторические specs/releases/migrations не переписываются.
6. Проверки, независимый review и converge. Поиск runtime/scripts/tests/current docs классифицирует остатки для historical read/delete, fingerprint compatibility, migrations и negative tests. Доступных старых senders/producers нет.

## Validation Plan

См. quickstart.md: single WAV, manual M4A, ambiguous/known jobs, retry/dedup, corruption rejection, read/delete historical, desktop v5 и scripts. После изменения shared fixtures проверяется server regression. PR checks обязательны; ручной запуск только GRAF Dev через dev-harness.

## Project Structure

- apps/server/src/twobrain_rec_server/{mediascribe,processing,workflows,ingest,api,db/models}
- apps/server/tests/{fixtures,fakes,unit,contract,integration}; apps/server/scripts
- apps/macos/RecApp/Sources/Upload; apps/macos/Shared/{Sources,Tests,Tools}
- infra/scripts; docs/integrations; docs/prd-voice-layer-final.md; docs/current-product-status.md
- specs/275-retire-dual-transcription; changes/unreleased/F275.yaml

## Compatibility And Rollback

Старые загрузки прекращаются намеренно. Данные/миграции сохраняются. Удаление исторических source roles из retention запрещено: иначе утекут объекты. Старый playback renderer/result-role reader нужен для сохранённых записей. Default модели нового job становится single_track; изменение database server_default — только новой additive migration, без переписывания истории. Возврат исходников возможен обычным release rollback и вновь включит старую отправку; production rollback здесь не выполняется.
