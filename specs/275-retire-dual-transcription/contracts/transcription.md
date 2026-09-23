# Transcription contract

- Единственный создающий endpoint: POST /v1/audio/transcriptions, multipart file и прежние параметры diarize/summarize.
- First-party: meeting-transcription.wav, audio/wav, PCM s16le mono 16 kHz; playback не подменяет ASR.
- Manual: проверенный manual-media.m4a, audio/mp4, после normalization; здесь playback является каноническим источником по действующему контракту.
- API meetings/revisions: default initial_mixed_recording; initial_recording получает 4xx (422 schema validation или 400 ProblemDetail). Продолжение ранее созданной старой загрузки отвергается до dispatch.
- Desktop проверяет формат до сети; старые данные остаются декодируемыми для удаления.
- Старый неизвестный POST не повторяется и не конвертируется под прежним ключом; известный job читается и удаляется.
- Secrets только на сервере. Evidence не содержит аудио, ключей или содержания встреч.
