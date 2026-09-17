# Data model

LocalRecordingManifest получает optional Bool shortRecordingDiscarded. nil/false сохраняет старую семантику. true означает завершённую новую штатную короткую запись, не отправляемую на обработку. status=blocked, transcriptionReadiness=degraded, failureReason остаётся none; не считать отказ по продуктовой политике сбоем захвата.

Проверка допустимости решения: v5; reason userRequested/meetingEnded; isComplete; failureReason none; captureFailureCode nil. Точная исходная длительность48k восстанавливается из существующих reviewPlayback.frameCount - aacPresentationFrameDelta с checked subtraction; результат >0 и <1_440_000. Сырая AAC длительность, округлённый WAV16k и durationMs для порога не используются. Невалидный/неизвестный/переполненный результат сохраняется.

Переходы: active → saved (обычная/аварийная запись); active → blocked + shortRecordingDiscarded (штатная короткая) → удаление неотправленной строки очереди → удаление аудио → удаление manifest → удаление пустого каталога. Сбой до durable решения оставляет active для аварийного восстановления; после решения — повтор cleanup без upload.

Не меняются public API, сервер, политика старых записей, номера форматов v3/v4/v5. Старый клиент увидит blocked и не сможет загрузить пакет; новая версия повторит cleanup.
