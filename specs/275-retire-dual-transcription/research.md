# Research

## Single-source only

Decision: удалить старый HTTP-отправитель и producers.
Rationale: initial_recording выбирает dual_track; desktop создаёт такой payload для не-v5. Повторы и служебные проверки вновь активируют путь.
Alternatives: выключатель или fallback не выполняют запрос полного удаления.

## Existing data and identity

Decision: unsupported sources завершаются до новых POST; known IDs и результаты сохраняются. Формат fingerprint существующих single-file requests сохраняется.
Rationale: изменение null mic/incoming ключей хеша сломает retry; удаление роли из purge оставит старые объекты. Миграции, playback/result readers и deletion metadata не являются доступным путём отправки.
Alternatives: удаление или смешивание истории нарушает сохранность и неизменяемость.

## Smoke tooling

Decision: актуализировать генераторы и seed.
Rationale: create_test_artifact.py пишет placeholder bytes под WAV-именами, upload_test_artifact.py полагается на старые defaults, seed_smoke_outcome.py выбирает paired artifacts по позиции. Это отдельный возможный источник невалидного аудио, но связь с job IDs пользователя не доказана.

## Evidence

Исследованы client.py, submit.py, store.py, api/schemas.py, ingest/media_revisions.py, DesktopUploadClient.swift и служебные scripts. Неизвестных продуктовых решений нет.
