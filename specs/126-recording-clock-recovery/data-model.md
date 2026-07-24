# Data model: recording clock recovery

## Capture batch

Ограниченный fragment одного источника:

- `source`: `microphone` или `systemAudio`;
- `samples`, `sampleRate`, `channelCount`;
- `presentationTime`: PTS в исходном CoreMedia time domain;
- `observedHostTimeSeconds`: optional callback-time observation, только metadata;
- `discontinuity`: `none`, `knownGap`, `dropped`, `routeChanged`;
- `routeGeneration`.

Положение данных вычисляется из PTS и количества frames. Дата доставки callback-а
не добавляется к PTS.

## Source clock normalization

Внутренний normalizer делает только domain admission:

```text
sourcePresentationTime (valid PTS) -> comparable host-time label (same seconds)
wallClock / hostTime             -> unchanged
```

Нормализованный label не означает, что callback был доставлен в этот момент.
`observedHostTimeSeconds` не может сдвинуть batch или вызвать failure из-за
jitter. Несовместимый явный domain (`hostTime` против `wallClock`) по-прежнему
отбрасывается.

## Canonical timeline

- epoch — earliest admitted PTS после того, как видны оба required source;
- координата — signed `Int64` frame index на 48,000 Hz;
- source state хранит stateful converter, segments и `lastInputEndFrame`;
- reorder window допускает разный порядок callback-ов;
- gap в пределах configured bound заполняется нулевыми samples;
- overlap обрезается с начала позднего segment-а;
- late batch после emitted watermark, dropped/route-change/overflow и gap за
  пределом bound — integrity failure.

## Local package

Успешный v5 package имеет ровно:

```text
manifest.json
meeting-transcription.wav
meeting-review.m4a
```

Оба audio file строятся из одного `CanonicalRecordingWriter` и одной timeline.
`manifest` публикуется после непустых file checks, hash/duration metadata и
alignment checks. При failure финальные audio files удаляются, остаётся только
metadata-only manifest с bounded reason code.

## Upload gate

`DesktopUploadQueueService` видит `manifest.isComplete`/artifact profile до
создания server meeting или upload session. Неполный package остаётся blocked и
не может напрямую отправить данные в MediaScribe. Idempotency ключи server/ASR
остаются существующим источником истины.

## Диагностика

Допустимы session/directory identifiers, status, frame/byte/duration counters,
route generation и bounded failure codes. Raw audio, transcript, secrets,
signed URLs и живые local paths не входят в эту модель.
