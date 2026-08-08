# Research: устойчивые часы и финализация macOS-записи

Дата: 2026-07-23

## Наблюдаемая причина текущего сбоя

В активном v5-пути `CMSampleBuffer` отдаёт PTS и дополнительное наблюдение
текущего host clock. Commit `769e3a6b` начал трактовать разницу между этими
двумя моментами как стабильное отображение часов источника и отклонять batch,
если разница между соседними callback-ами менялась больше заданного jitter.
Это неверно: callback может быть доставлен позже захвата из-за нагрузки и
очереди, а PTS описывает положение медиаданных. В результате нормальная
задержка доставки превращалась в `sourceClockMappingUnstable`, writer удалял
финальные WAV/M4A, а очередь блокировала upload до создания server meeting.

## Что подтверждено Apple API

- `CMSampleBuffer` содержит presentation timing; порядок доставки callback-ов не
  является медиапозицией: [CMSampleBuffer API](https://developer.apple.com/documentation/coremedia/cmsamplebuffer-api).
- CoreMedia предоставляет host clock и средства сравнения clock domains, но
  момент выполнения callback-а не является заменой timestamp медиаданных:
  [CMClock API](https://developer.apple.com/documentation/coremedia/cmclock-api)
  и [CMClock](https://developer.apple.com/documentation/coremedia/cmclock).
- `AVCaptureAudioDataOutput` вызывает delegate на serial queue и может отбрасывать
  поздние samples, если очередь заблокирована; callback должен делать только
  bounded work: [setSampleBufferDelegate(_:queue:)](https://developer.apple.com/documentation/avfoundation/avcaptureaudiodataoutput/setsamplebufferdelegate(_:queue:)).
- ScreenCaptureKit отдаёт audio buffers через `SCStreamOutput`; Apple отдельно
  предупреждает, что обработка должна успевать за потоком и не удерживать
  поверхности, иначе растут задержка и потери: [SCStreamOutput](https://developer.apple.com/documentation/screencapturekit/scstreamoutput)
  и [WWDC22: Take ScreenCaptureKit to the next level](https://developer.apple.com/videos/play/wwdc2022/10155/).
- Потоковая конвертация sample rate должна быть stateful; для AVAudioConverter
  нельзя предсказывать результат независимыми одноразовыми конверсиями:
  [AVAudioConverter](https://developer.apple.com/documentation/avfaudio/avaudioconverter)
  и [TN3136](https://developer.apple.com/documentation/technotes/tn3136-avaudioconverter-performing-sample-rate-conversions).

## Принятые решения

1. **PTS — authoritative media clock.** Нативный PTS ScreenCaptureKit и
   AVCapture сохраняется и приводится к внутреннему comparable host-time label
   без проверки `callbackNow - PTS` на стабильность. Это устраняет ложную
   ошибку при задержке до 500 мс и не сдвигает звук к моменту Stop.
2. **Callback observation — telemetry only.** `observedHostTimeSeconds` может
   отсутствовать или иметь jitter; он не отбрасывает валидный sample. Если
   значение доступно, оно сохраняется как metadata для будущих измерений, но не
   участвует в позиции batch.
3. **Одна каноническая шкала.** После bootstrap обе дорожки переводятся в
   существующий integer frame timeline 48 kHz mono. Gaps и overlaps обрабатывает
   уже существующая bounded логика; неизвестные потери, route change и overflow
   остаются fail-closed.
4. **Stateful converter per source.** Существующий `AVAudioConverter` остаётся
   одним экземпляром на источник и сбрасывается только при финализации. Новая
   независимая clock-correction/resampling подсистема не нужна для этого
   инцидента.
5. **Stop как barrier.** Нативные serial queues снимаются с output/delegate,
   дренируются, затем writer дренирует принятые timestamped batches, закрывает
   converters и публикует только проверенный набор v5-артефактов. Уже существующий
   ScreenCaptureKit drain сохраняется; изменение ограничивается фиксацией
   timestamp metadata при split.
6. **Никакого скрытого восстановления.** При настоящем dropped batch, gap сверх
   лимита, смене route, отсутствии источника, ошибке конвертера или диска пакет
   остаётся непригодным к upload. Исправление не подделывает звук тишиной за
   пределами существующего known-gap policy.

## Рассмотренные альтернативы

| Вариант | Решение | Причина |
| --- | --- | --- |
| Сдвигать batch по времени callback-а | Отклонён | Добавляет jitter и постоянную ошибку latency в аудио. |
| Собирать две дорожки FIFO и сводить по номеру чтения | Отклонён | Теряет PTS, не переживает reordering и разные sample rates. |
| Делать PLL/ресэмплинг по каждому callback | Отложен | Требует подтверждённого hardware clock evidence; может маскировать dropout. |
| Вернуть virtual audio driver или routing daemon | Запрещён scope | Нарушает system-audio-first MVP и продуктовые gates. |
| Добавить AEC/voice processing | Отложен | Это отдельная измеряемая функция, не исправление capture clock. |
| Перевести микрофон в ScreenCaptureKit | Отклонён | Меняет разрешения, ownership и принятый app-owned mic contract. |

## Открытый hardware gate

Детерминированные тесты доказывают поведение timeline/finalization, но не
заменяют 60-минутный controlled Zoom прогон. Аппаратный gate T063 остаётся
отдельным: unchanged route, headset-first, измерение drift/dropout/levels,
playback/transcript/deletion и ровно одна ASR job. Запись через speakers,
изменение route/volume во время сессии и AEC в эту фичу не входят.
