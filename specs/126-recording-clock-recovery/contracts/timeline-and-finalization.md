# Contract: timeline and finalization

## Input contract

Каждый native audio callback передаёт `RecordingAudioBatch` с валидным PTS,
форматом и frame payload. PTS может быть доставлен позже соседнего batch-а.
`observedHostTimeSeconds` optional и не является временем начала аудио.

## Ordering and mapping contract

1. Принять batch только если samples, format, PTS и route metadata валидны.
2. Для `.sourcePresentationTime` использовать сам PTS как позицию; не вычислять
   позицию из callback delivery time и не сравнивать jitter observation с
   предыдущим callback-ом как clock stability gate.
3. Согласовать обе дорожки через одну 48 kHz integer-frame epoch.
4. Применять существующие reorder, known-gap, overlap и bounded-buffer rules.
5. При явной потере/смене route/несопоставимом domain/неограниченном gap не
   создавать валидный partial package.

## Stop contract

```text
stop requested
  -> stop native outputs/delegates
  -> drain serial callback queues
  -> drain accepted timestamped batches
  -> finish converters/timeline
  -> finish and validate canonical writer
  -> publish manifest + enqueue only complete package
```

Любая ошибка до publish переводит запись в bounded failure state, удаляет
финальные audio files и сохраняет metadata-only manifest. Повторный Stop не
должен создавать второй directory, second server meeting или ASR job.

## Artifact contract

Только complete package с ровно двумя непустыми ролями
`mixedMeetingAudio`/`reviewPlayback`, одной canonical mix profile и
`failureReason == none` может перейти в upload queue как uploadable. Existing
server/MediaScribe contracts не меняются.

## Test contract

Обязательны deterministic checks для:

- callback jitter/delay до 500 мс и reordering без false clock failure;
- absolute/native PTS без observation;
- sample-rate/channel normalization и stateful converter;
- known gap, overlap, drift, late batch и max gap;
- route change, dropped/overflow, missing source и converter/finalization error;
- Stop barrier, complete artifact set, blocked incomplete upload и повторную
  финализацию.
