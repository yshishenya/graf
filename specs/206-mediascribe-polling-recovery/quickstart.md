# Quickstart: MediaScribe polling recovery

Из корня репозитория:

```sh
cd apps/server
uv run pytest tests/unit/test_processing_recovery.py tests/unit/test_processing_recovery_contracts.py tests/unit/test_processing_temporal_workflow.py
uv run pytest tests/integration/test_mediascribe_processing_happy_path.py tests/integration/test_processing_failures.py
```

Сценарии: pending job остаётся recoverable; `ready` импортируется без нового
submit; provider `failed` показывает terminal recovery; retryable HTTP error
сохраняет same-job polling; watchdog оставляет ручную проверку; transcript
скрыт до diarization, а summary имеет независимый статус.

Для media recovery дополнительно проверить: повреждённый MP3 проходит tolerant
первый transcode, валидный canonical M4A публикуется для playback, а хвостовое
усечение отклоняется по authoritative длительности. Playback не подменяет
authoritative `media` в MediaScribe submit.

Repository gate перед PR:

```sh
infra/scripts/ci-local.sh --fast
```

Production deploy/reprocess не выполняются в этой slice без отдельного
одобрения и release gate.
