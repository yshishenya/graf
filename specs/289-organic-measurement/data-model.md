# Data model

Схема, retention, UTC bucket, sanitizer и порог раскрытия прежние.

| path | surface |
|---|---|
| /transcription | public_transcription |
| /meeting-minutes | public_meeting_minutes |
| /record-without-bot | public_record_without_bot |
| /guides/rasshifrovka-zapisi-zoom | public_zoom_recording_guide |

Текущий фиксированный путь → существующее landing_path. Только проверенные UTM текущего URL → source/medium/campaign/content/term; грубые device/referrer/traffic классы. Cookie не источник. Повтор увеличивает requests, не уникальных людей. IP, raw UA/referer, yclid, opaque refs, аккаунт и содержимое встреч не записываются. Нет миграции или новой связи с аккаунтом.
