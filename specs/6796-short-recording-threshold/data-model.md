# Data model

LocalRecordingManifest получает optional Bool shortRecordingDiscarded. nil/false сохраняет старую семантику. true означает завершённую новую штатную короткую запись, не отправляемую на обработку. status=blocked, transcriptionReadiness=degraded, failureReason остаётся none; не считать отказ по продуктовой политике сбоем захвата.

Проверка допустимости решения: v5; reason userRequested/meetingEnded; status saved; failureReason none; captureFailureCode nil; egress/transcription false; канонический mixedMeetingAudio имеет сохранный статус, frameCount>0, sampleRate.isFinite и sampleRate=16000, isCanonicalTranscriptionArtifact=true, frameCount/sampleRate<30. Не использовать rounded durationMs или reviewPlayback. Неизвестный результат сохраняется.

Переходы: active → saved (обычная/аварийная запись); active → blocked + shortRecordingDiscarded (штатная короткая) → удаление неотправленной строки очереди → удаление аудио → удаление manifest → удаление пустого каталога. Сбой до durable решения оставляет active для аварийного восстановления; после решения — повтор cleanup без upload.

Не меняются public API, сервер, политика старых записей, номера форматов v3/v4/v5. Старый клиент увидит blocked и не сможет загрузить пакет; новая версия повторит cleanup.
