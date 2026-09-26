# Data model

MediaRevision неизменяема после приёма. Новые first-party: initial_mixed_recording и manifest/media/playback. manual_upload сохраняет контракт.

initial_recording читается из существующих строк, но запрещён для новых загрузок и новых отправок. Новые MediaScribeJob имеют single_track и source_track_artifact_id. Исторические nullable columns остаются до отдельной миграции удаления данных; новая additive migration может сменить obsolete server default. Existing job fingerprint/ID/idempotency не переписываются.

Unsupported source без external ID → failed_terminal/unsupported_recording_source (или существующий равноценный конечный код), без usage reservation/new job/egress. Known ID → прежний poll/import/delete. Desktop unsupported package → blocked/manual-only с сохранением файлов и tombstones.
