# Общая шкала: отвергнутая реконструкция и исследуемая фазовая модель

Статус: конкретная witness-PTS реконструкция round164 отвергнута проверкой
качества; фазовая модель round167 проходит отдельные исследования, но ещё
не принята; round168 добавил отдельный соседний guard, round169 проверил
зависимость от разбиения и точность команды; round170 различил идеальную
и фактическую опору ядра и проверил большие начальные метки.
2026-10-02. Ниже сохранены различия и результаты последовательных вариантов.
Не заменяет §5 `windows-desktop-contract.md`, не разрешает производственную
реализацию и не считается исправлением установленного клиента.

## Вход и границы доверия

- Опора для начала — контракт `IAudioCaptureClient::GetBuffer`: QPC в 100 ns
  относится к первому кадру полученного пакета. Это доверие семантике API,
  не утверждение об измеренной абсолютной аппаратной точности в пределах 1 ms.
  Отсутствие TIMESTAMP_ERROR не даёт такой численной гарантии.
- Действующий ClockMapper остаётся перед нормализацией. Не меняются предел
  накопленного остатка 100 ppm + 1 ms + один кадр, непрерывность device/count,
  flags, монотонность, неизменность формата/domain/route, supplementary clock
  и необратимость отказа в текущей сессии. Принятый SILENT-пакет содержит ровно
  его frame count нулей; отсутствие пакета не становится тишиной.
- Обработка не удерживает WASAPI buffer ради AEC. Данные копируются в owned
  staging; продвижение resampler и публикация возможны только после проверенного
  ReleaseBuffer(count). Ошибка освобождения оставляет отказ, не новый выход.
- Первый допустимый пакет каждого источника имеет собственные `q0` и device
  origin. `q0` один раз округляется до общей 48 kHz сетки; дробный остаток
  сохраняется в начальной фазе. Нельзя заменять q0 временем callback/Start/UI,
  текущим GetPosition, нулём или device origin другого источника.
  Все преобразования QPC/frame/counter проверяются на переполнение до cast.

## Отвергнутая witness-реконструкция round164

Используется уже закреплённый WebRTC `SincResampler`, не PushResampler и не
новый сервис часов. Исследовательский OriginAlignment проверил именно этот
алгоритм на 44.1/48 kHz; это не доказательство всех допустимых входов.

У каждого источника сохраняются origin, fractional phase, счётчики admitted
input / consumed source position / generated output и ограниченный staging.
Номинальный шаг source frames на output frame: `r = sourceRate / 48000`.
После каждого прошедшего mapper пакета оценка отклонения:

```text
observedOffset = packetStartFrame - sourceRate * (q - q0) / 10000000
consumedOffset = consumedPosition - initialPhase - r * generatedOutput
correction = clamp((observedOffset - consumedOffset) / sourceRate, -0.0005, 0.0005)
ratio = r * (1 + correction)
```

`packetStartFrame` — накопленный count до нового пакета, не его device origin.
`consumedPosition` учитывает реальные callback requests и фазу SincResampler,
а не только опубликованные семплы. `initialPhase` вычитается после её применения;
до первого шага consumed offset равен нулю. Horizon 1 s и correction ±500 ppm —
параметры этого кандидата управления фазой, не новый допуск исходных часов.
Они пока требуют проверки границ; отклонение, отвергнутое mapper, до формулы
не доходит. Не вычислять nan/overflow с последующим clamp до нормального значения.

Начальная fractional phase задаётся одним непубликуемым шагом с nominal ratio
плюс initial phase, затем восстанавливается выбранный ratio. Этот шаг не является
частотной коррекцией ±500 ppm. SetRatio сохраняет историю и фазу; между пакетами
нет reset/recreate. Все принятые QPC участвуют в оценке, а не только первый.
`ReachablePhase` из fixture — oracle с дополнительными предположениями о генераторе,
не новый runtime validator и не ещё одно условие запуска записи.

## Выход, ограниченная память и завершение

- Для входа timeline выходная PTS восстанавливается из QPC пакетной опоры и
  дробной позиции центра первого пригодного Sinc-семпла. Нельзя заранее
  объявлять её равной q0 + generatedOutput: это скрывало timestamp-gap отказ.
  Опора — реально принятый пакет, содержащий центр исходного семпла;
  его start/count/QPC сохраняются до прохождения соответствующих центров.
  Это позиция центра, не число кадров, прочитанных callback, и не конец блока.
  История и EOS filler без полного диапазона реальной опоры не публикуются.
  Источник отдаёт диапазоны отдельно при смене пакетной опоры; объединение
  через смену опоры ради удобного размера sink запрещено. Дальнейшее bounded
  разбиение сохраняет метки каждого реального первого семпла, а не пересчитывает
  их по arrival. Теги опор ограничены вместе с input staging; точный layout/
  bound тегов ещё требуется проверить, полный массив истории не разрешён.
- Округление сохраняет общий origin. Пусть G — однократно округлённый q0 на48k,
  epsilon — его сохранённый дробный остаток в кадрах48k. Для первого центра s
  и пакетной опоры (qPacket,nPacket) сначала вычисляется только относительное
  время, без потери точности большой абсолютной QPC:

  ```text
  relative48 = (qPacket - q0) * 48000 / 10000000
             + (s - nPacket) * 48000 / sourceRate
  witnessPTS = G + llround(relative48 - epsilon)
  ```

  Здесь epsilon=G−q0×48000/10000000 вычисляется через integer quotient/remainder,
  не вычитанием больших floating-point значений. s включает initialPhase.
  Для точного nominal потока это G + реальный output index, включая half-frame
  tie, но пакетный QPC не исчезает из проверки. Signed offsets, finite значения,
  conversion/add/subtract overflow проверяются до выдачи. Это candidate formula:
  packetization invariance, rounding edges и динамическая ratio ещё не приняты.
- Callback получает только полные запросы из уже admitted input. Поддерживаемый
  pinned request равен 64 mono frames. Предложенный предел source staging:
  максимум один пакет 4800 frames плюс остаток одного request 64, отдельно
  фиксированная история ядра. Существующий интерливированный вход ограничен
  4800 frames × 32 channels; новые полные массивы записи не создаются.
  При низкой sourceRate выход одного пакета может превышать 4800 frames:
  выдача разбивается на bounded batches, а не увеличивает общий лимит.
  Этот предел нужно подтвердить по реальному callback/cursor до реализации;
  фиксированный массив всей fixture не доказывает bounded production memory.
- `normalizedFrameOffset` передаёт непрерывный диапазон пригодного Sinc-выхода
  ДО коррекции timeline, первый offset может быть ненулевым. Generated, пригодные
  pre-correction и окончательные canonical counts различаются; полный trim
  потребляет pre-correction диапазон, но не вызывает AEC/writer.
  Старый пакет/пропуск/count loss не становится новой phase correction.
  Существующий RecordingAudioTimeline — единственный владелец выравнивания:
  получает реальные семплы/witnessPTS/offset, проверяет domain/route/count,
  выполняет интерполяцию или trim до48, сохраняет nondecreasing end и отказывает
  при превышении. Нет второго виртуального end или legacy normalizer.
  Пустой output не обновляет end; полный trim не двигает end/last sample назад.
  Только после этих действий общий пригодный префикс выдаётся парами480;
  AEC reverse предшествует обработке microphone.
- После Stop source count заморожен. Неподтверждённые EOS filler допускаются
  лишь для вычисления хвоста: публикуется только full-support диапазон реальных
  samples. Два разных filler должны давать побитно одинаковый доверенный выход.
  Начальная неподтверждённая история исключается из общего начала; полный общий
  пригодный префикс нельзя выбирать по удобному сокращённому окну качества.
  Неполный финальный блок не дополняется wall-clock тишиной.
- EOS/fence/timeline close/finalizer и 5 s drain остаются по действующему
  контракту. Формат и коэффициент mixed output проверяются отдельно: isolated
  `0.5 * (system + cleanedMicrophone)` соответствует Mac; текущая product сумма
  ещё не исправлена этим документом.

## Что этот кандидат не исправляет

Rounds165–166 проверили полную цепочку на generated данных: actual ClockMapper,
packet-center anchor, native Sinc, real RecordingAudioTimeline и native AEC3.
13 zero-signal healthy cases и 6 отказов на8ms не оказались доказательством
качества. При nominal physical rate и допустимом sinusoidal metadata jitter
0.4ms far reduction упал до0.946dB вместо20dB, double-talk до9.82dB вместо10dB.
Без jitter при прочих равных far22.41dB и double-talk28.43dB проходят.
Отключение controller SetRatio не устраняет отказ: far0.946dB/DT9.75dB,
actual trim1802/1675frames за12s. Следовательно, controller не необходим
для воспроизведения; непосредственная пакетная QPC-привязка с существующим
timeline corrector уже достаточна для регрессии этой fixture.

Из этого не следует, что виноват только trim, что AEC3 неисправен или что
испытание доказывает причину живого VM clock_drift. Но эта конкретная формула
публикации непригодна для реализации: raw admission и <=48 correction не
гарантируют качество. Следующий проект должен отличать uncertainty меток от
изменения физической частоты, не искажая waveform на каждом packet boundary,
и одновременно сохранить явный отказ при реальном разрыве. Скрыть raw метки,
ослабить thresholds либо объявить старый uniform-PTS draft принятым нельзя.
Конкретное новое правило, его bounds и изменение нормативного контракта
ещё не выбраны. Полные результаты/фrozen SHA — validation rounds165–166.

Уточнение round164 заменяет отвергнутый вариант ровной входной PTS, а не
исторические результаты rounds162–163 ниже. Independent requirements review
допускает применение48-frame правила к реальным новым границам Sinc, а не
точное воспроизведение всех выходных границ linear Normalizer. Пример441/441
в §5 условен («когда первый выдал479»): нужно продолжать реально выданный offset,
не искусственно выпускать479 в новом алгоритме. Изменение границ названо явно;
тождественное множество решений старой и новой цепочки для любых разбиений
не обещается. Позиции/значения точного непрерывного сигнала при разном разбиении
по-прежнему должны сохраняться. Review принял только направление, не формулу,
tag layout, все входы, весь план или реализацию.

Round162 обнаружил обязательный пробел этого draft: при cumulative mapper PASS
скачок QPC−4ms→+4ms на50s даёт старой шкале gap384frames и fail-closed. Ровная
новая PTS скрывает этот отказ. Counter model восьми частот подтвердил8000us
ошибку фазы; Sinc runtime этим опытом не проверен. Кандидат неполон до сохранения
существующей защиты gap>48. Возможная точка проверки — разность соседних
округлённых остатков QPC относительно input count; её sampled equivalence со
старым Normalizer не заменяет независимое принятие и proof variable/EOS случая.

Independent review round163 оставил P1 непрерывной PTS и два P2 против простого
R_i−R_prev: старый Normalizer может не выдать samples; после полного trim
маленького выхода endPts не продвигается. Поэтому сравнение соседних raw R
не является общей эквивалентностью существующего timeline guard. Исполнимые
actual-core counterexamples подтверждены: empty-output raw deltas30/30 проходят,
но emitted gap60 обязан отказать; full-trim raw delta49 при actual gap2 допускается.
Точная legacy-equivalence требует непустых output boundaries и сохранённого
неубывающего end. Такой виртуальный monitor пока не выбран: он не должен
неявно превратиться в второй legacy normalizer или в новый аппаратный oracle.
Перед изменением проекта нужно явно согласовать это с §5 и новым Sinc выходом;
простой соседний guard не принят как готовое решение.

Schema6 показала отказ текущего mapper при непрерывном count и превышении
численного QPC budget. Кандидат нормализации после mapper не может принять такой
пакет и поэтому сам по себе не устраняет остановку в текущей VM. Причина
аппаратной/виртуальной неточности и совместимое решение этого отказа остаются
отдельным открытым вопросом, а не скрытым исключением из §5.

Неопределённое постоянное аппаратное смещение первой метки — ограничение
проверки, а не дополнительное требование доказать аппаратную точность до
выбора архитектуры. Installed/live, физический x64, 60 min SC-003, аппаратная
матрица и производительность остаются отдельными обязательными воротами.
Четыре long far FAIL исследования не удалены и не превращены в PASS; это
дополнительные исследовательские проверки, не вновь назначенный SC.

## Исследуемая фазовая модель round167 — не замена §5

Новое направление использует те же raw mapper и pinned Sinc, но не публикует
packet-QPC jitter через повторный trim/interpolation. QPC остаётся входом
phase feedback и отдельного отказа; own first origin/fraction не заменяются
callback time либо чужим device count. Full-support Sinc output получает
gridOrigin+outputIndex после физического пересчёта; это явно новая семантика,
а не утверждение о прежнем packet-center witnessPTS.

Для исследованного Source:

```text
observedOffset = acceptedInputStart - sourceRate * (packetQPC - firstQPC) / 1e7
consumedOffset = sincCursor - initialPhase - nominalRatio * generatedOutputs
innovation48 = (observedOffset - consumedOffset) * 48000 / sourceRate
```

До новой команды nonfinite или abs(innovation48)>48 необратимо прекращают
Source. Иначе прежний candidate controller с horizon1s/command±500ppm меняет
actual Sinc ratio, не выполняя reset/seek/drop/prime-silence. Raw admission
100ppm+1ms+frame, device/count/flags/clock не ослабляются. Это hypothesized
innovation bound, не принятое production число или доказанная точность часов.

Последняя команда не может применяться к произвольной накопленной очереди:
перед admit оба callback supplied<=accepted, unread<64. Нарушение даёт отдельный
terminal staging rejection до новых metadata/mapper/tag mutations. После
одного допустимого packet<=4800 unread<=4863; source должен опустошить доступный
выход до следующего приёма. Generator проверяет этот порядок, но реального
owned FIFO allocation layout/требуемого dispatcher/controller ещё не реализует.
Full-support/EOS/normalized offset и custody gates сохраняются отдельно.

Native research: 12/12 existing quality metrics PASS при nominal/opposite
±100ppm/sinusoidal99ppm,0.4ms metadata jitter,12s/48000+44100/variable packets;
far21.82…21.86dB, no trim. 13 zero healthy cases и6 admitted8ms jumps проходят
ожидаемым образом; queued94admit regression отказывает на третьем вызове
при480 accepted input, без дальнейшего продвижения. Неполный или пропущенный
семпл не превращается в подтверждённую тишину. Scope — generated native chain,
не live/hardware/performance/installed acceptance.

**Существенное незакрытое отличие:** abs(innovation48)<=48 ограничивает ошибку
относительно текущей накопленной коррекции, а не изменение между соседними
опорами. Пример+47.52→−47.52 может иметь разность около95frames при обеих
допустимых отдельных величинах. Поэтому этот вариант нельзя назвать сохранением
старого правила «jump>48 прекращает сегмент». Требуется отдельная проверка
этого случая и явное согласование нового guard со спецификацией; просто
публиковать ровные PTS и забыть raw timing защищённой реализацией не считается.
Действующий нормативный §5 пока не изменён.

### Поправка round168: отдельное ограничение соседнего raw остатка

Native counter replay с ±40-frame QPC residual подтвердил пробел round167:
adjacent79.9968frames, maxinnovation41.5589<48, old phase model healthy/299blocks.
Это replay нового generated metadata, не утверждение об аппаратном скачке.
В следующем derivative добавлено независимое от consumed/Sinc correction
`phaseStep48 = (observedOffset - previousObservedOffset)*48000/sourceRate`.
Nonfinite или abs(step)>48 дают irreversible source refusal до новой команды,
ratio/accepted/packet progression. Первая опора имеет step0; previous value
обновляется лишь после прохождения обеих phase проверок. Raw mapper и ring
уже могли принять текущую метку: отсутствие такой мутации при отказе не
обещается; последующие вызовы не продвигают состояние/выход.

Native повтор: все12quality metrics численно прежние PASS,13zero healthy,
six8ms negatives и backlog94call PASS. Adjacent79.9968 теперь отвергнут
именно phaseStep, при maxinnovation40.2224<48 и healthy raw mapper;
сохранено200blocks, поздние вызовы не продолжают output. Independent source
review узко Approved formula/order of failure, не §5/whole design/native run.

Этот guard является ограничением соседнего **исходного** остатка; не доказана
тождественность прежним output boundaries/empty-output/full-trim решениям.
Source-phase output semantics по-прежнему требуют принятого нормативного
описания, integer/partition/resource/full-prefix проверок и полного review.
Новый guard закрывает этот конкретный counterexample, не всю Phase0.

### Поправка round169: точность представления в команде, не допуск часов

Нативный тест одного номинального ненулевого сигнала на 11 частотах обнаружил
7 FAIL из 44 сравнений: все 22 варианта без controller имели точное совпадение,
а включённый controller менял значения при одинаковых начале и длине.
Варьировались и входные пакеты, и размер drain, поэтому это нарушение
независимости от их комбинации, не изолированное доказательство роли каждого.
Порог сравнения `0.00001` взят из существующего AudioNormalizerTests, не увеличен.

Следующий исследовательский вариант меняет только команду:

```text
feedback = observedOffset - consumedOffset
command = 0, если controller выключен или abs(feedback) <= sourceRate/1e7
command = clamp(feedback/sourceRate, -0.0005, 0.0005), иначе
```

Обоснование одного тика условно: разность **двух идеальных меток, округлённых
до ближайшего целого 100-нс тика**, имеет ошибку округления не больше одного
тика. Сам формат WASAPI не гарантирует такой точности измерения/виртуализации.
Feedback также включает фактический остаток Sinc, не только квантизацию QPC.
Поэтому это исследуемая зона нечувствительности управления, не новый критерий
истинности часов и не доказательство глобального предела вычислений double.
Комментарий о one-tick в frozen prototype следует читать только в этой модели;
для продуктового кода такая условность должна быть записана прямо в комментарии.
Внутри зоны выбирается номинальный ratio, не удерживается прежняя команда;
история/позиция Sinc не сбрасываются. Raw mapper, innovation48, step48 и
staging bound выполняются раньше и не изменены.

Native: 44/44 сравнений PASS с max_error=0, включая полный пригодный хвост.
Дополнительный запуск проверил независимые nominal границы ядра `[jfirst,jend)`
и число полных блоков: все 66 прогонов/44 сравнения PASS. Это закрывает
возможность одинакового укорочения трёх вариантов в пределах данной fixture,
но не доказывает границы динамического ratio, всех origins или длительностей.
12/12 проверок качества и прежние healthy/jump/adjacent/backlog cases PASS.
Independent source review условно принял команду в этой модели; отдельный
review принял формулы полного диапазона, не native результаты/весь проект.
Подробности и fingerprints: validation-2026-10-02.md, Round169.

### Уточнение round170: фактическая опора, не идеальный rational cursor

Отбор full-support следует проверять относительно всех32 входных отсчётов,
которые фактически передаются закреплённой Sinc-свёртке. Идеальная формула
номинального центра не всегда точно воспроизводит floor её последовательного
double cursor. При8k/origin0/count400 идеальный диапазон `[96,2310)` не пройден:
фактический Source выбирает `[97,2311)` той же длины2214. Этот FAIL сохраняется,
не превращается в PASS изменением допуска или публикацией startup history.

Независимое наблюдение настоящего native input_ptr через существующий test seam
подтвердило: j96 читает[-1,30] и не имеет полной опоры; j97 читает[0,31];
j2310 читает[368,399]; j2311 читает[369,400] и уже выходит за реальный вход.
Поэтому Source в этом случае правильно отбирает полный фактический диапазон,
а не теряет пригодный native output. Свёртка вызывается прежней функцией с
неизменными аргументами; библиотека/алгоритм не патчатся. Это offline research
seam, не новая производственная зависимость/точка доступа.

Короткая nominal матрица:11rates,6absoluteQPC origins (включая около2^53,
выше2^63 и околоUINT64_MAX),6first-offsets,3packet/drain variants.
1188 Source runs совпали по границам/длине с независимо наблюдаемой фактической
опорой; сравнение значений с native reference прошло прежний допуск0.00001.
792partition comparisons имеют max_error0. Native-reference error0 напечатан
только для subsetorigin0/start0; нулевая ошибка всей reference matrix не заявлена.
Independent source review observer узко Approved, не весь §5 или аппаратная
точность. Dynamic ratio, длинные counters, nonfinite tests и concurrent seam
этим не проверены. Подробности/fingerprints: validation Round170.

Первая integerQPC конверсия отдельно допускает аналитическую проверку:
`q*48000/1e7 == q*3/625`; вычислять произведение большогоq не нужно.
Для всехuint64q maxroundedG=88544371553805848<INT64_MAX;
максимальный remainder product479999952000, signed residue abs<=4992000.
Exact half-frame tie для целого100ns q на48k невозможен (знаменатель625 нечётен).
First ratio остаётся не меньше nominal×0.5008>0; binary64 margin до прежней
проверки abs(initialPhase)<=rate/96000 не исчезает. BigInt cross-check3491q
проверил period625 и большие эпохи. Это обоснование first-origin arithmetic,
не предел всех последующих cursor/counter/feedback операций.

### Поправка round171: большие счётчики без вычитания больших double

Числовой стенд воспроизвёл ложную команду старого исследовательского Source
и неправильную выборку центра при больших счётчиках. Это введённые числовые
состояния, не доказанная достижимость настоящего Sinc или причина сбоя VM.
В проверенных состояниях до одного часа ложных команд не обнаружено.

Исследовательский successor использует разложение `count*rate/denominator`
на целую часть и остаток через quotient/remainder без большого произведения.
В feedback сначала вычитаются целочисленные остатки observed и consumed,
затем добавляются небольшие дроби, локальный cursor и однократная initialPhase.
Нельзя заменять это `floor(double(base)+index)` для выбора пакета: сохраняется
исходный `base+floor(localIndex)`, уже проверенный при отборе full-support.
Соседний phaseStep вычисляется из разности текущей и предыдущей пары n/q,
а не вычитанием больших накопленных floating residuals.

Существующий продуктовый предел submitted input `2^52` сохранён в admission
successor; representability/scale/signed difference проверяются до преобразования.
Ошибка арифметики закрывает исследуемый сегмент; это пока не typed product fault.
Raw mapper, шаг/innovation48, зоны команды и качество не ослаблены. Формулы
изменяют численную реализацию, не заявляют принятие новых §5 semantics.

Native numeric check:16896 введённых состояний/10 guards PASS; старый расчёт
дал2003 ложные команды/949 несовпадений центра. На этой матрице отдельное
вычитание split floating residuals также не дало ложных команд; его провал
не заявлен. Последующие actual-kernel support792/792, quality12/12 и прежние
healthy/jump/adjacent/backlog проверки successor PASS. Большие numeric states
не заменяют длинный native/live runtime. Fingerprints: validation Round171.

## Перед принятием проекта

### Исследование fixed-output-grid rounds179–180 — не принятая замена

Offline команда обновляется при generated output index кратном480; drain
заканчивается на границе ячейки. Опора вычисляется интерполяцией соседних
полученных n/QPC после integer origin subtraction. Raw/innovation/adjacent/
staging guards остаются; grid innovation48/clamp1000ppm/representation floor
применяются дополнительно. Metadata заранее preload-ится; финальный span4800
input frames удерживает прежнюю команду по известному fixture count. Это не
live доступность опоры, Stop, bounded input queue или accepted output semantics.

Numeric linear66cases PASS не переносится на waveform: rounded drift native
matrixFAIL1/24; successor с fractional relative QPC вместо llroundFAIL4/24.
Отдельная exactinteger fixture declared48001/physical48000 и кратные3 input
partitions даёт старому controllerFAIL2/4, новому offline gridPASS4/4/error0.
Это cadence counterexample даже без QPC quantization, а не готовое устранение
rounded/jitter случаев. Норма §5 не имеет nominal-only исключения; точность
реальных целочисленных наблюдений отдельно не выводится из формата100ns.
Доказательства/фингерпринты/пределы исследования — validation179–180.

### Причинный grid rounds181–183 — проверен как опыт, не принят для runtime

CausalSource фактически копирует input в fixed16384-float rings; отдельный
grid хранит только принятые n/QPC опоры в fixed16384-point ring. Open cell480
ждёт received anchor n>=virtual n+4800; EOS hold-tail определяется только после
sealed. Source/grid heap placement исправляет stackoverflow стенда, не clocks.
Exactprofile0.5s/3s PASS4/4+4/4, включая190 ненулевых fractional projections;
rounded11rate matrix остаётся11/132FAIL при прежнем0.00001. Cap16384 и measured
peak10045 не принимают предыдущий4864 input bound, dispatcher slot reservation
или latency budget. Producer known count не используется grid до EOS, но сам
EOS ещё fixture event, не пользовательский Stop/admission fence.

Узкое source review Approved не заменяет нормативное принятие. Различение
точных и noisy наблюдений не создаёт nominal-only исключения, не выводит
округление/±100ppm/jitter из покрытия и не превращает historical FAIL вPASS.
Сохраняются existing nominal rounded44100 regression, AEC/SC-003 и действующее
timeline±48 правило; innovation48 исследовательское. Нужны numerical uncertainty
и quality proof, independent dynamic completeness и реальные FIFO/Stop bounds.
§5 остаётся неизменным; Phase0 продолжается, gate реализации не пройден;
fingerprints181–183.

### Предложение размещения FIFO/Stop — независимый design review round178

Не принятый нормативный контракт. Минимальный вариант сохраняет Sinc и mono
FIFO внутри существующего worker-owned `AudioNormalizer`, не переносит raw
пакеты/готовность источника в dispatcher. Worker владеет input/supplied/cursor/
generated/delivered counters; controller под одним mutex владеет разрешением
приёма, поколением сессии и резервами своей очереди; timeline — только alignment.

- Owned-копия входа остаётся ограниченной4800×32float. Предлагаемый mono ring
  4864frames; unread<64 до нового пакета/<=4863 после, request64, native Sinc
  buffer96 с историей. Это layout-предложение, не реализованный bounded FIFO.
- Existing dispatcher256 мест:254data+2typedEOS. Резервировать выходные data
  места до принятия input, отдельно держать tail место на источник. Reviewer
  предлагает семь мест по4800 для одного worst-rate пакета; точное обоснование
  maximum pending output/tail, включая native resident input, ещё требуется.
  Не использовать непроверенную оценку как runtime guarantee. Fixed array
  existing DispatchItem вместо deque рассмотрен для безаллокативной постановки
  EOS, не как новая очередь/библиотека; payload allocation fault остаётся fault.
- GetBuffer → preliminary validation/owned copy → successful ReleaseBuffer →
  input admission с output reservation → FIFO/Sinc → existing dispatcher.
  Preliminary mapper может работать на копии; commit admission и Stop
  линеаризуются одним controller mutex. Непринятый пакет освобождается целиком
  и не продвигает Sinc. Queue exhaustion отказывает до admission без ожидания
  с удерживаемым WASAPI buffer.
- Stop закрывает новый input и фиксирует accepted end/deadline5s; не отменяет
  уже принятый input. Producers завершают его normal drain и full-support хвост
  с замороженными metadata/command. Только после обоих producer-complete
  callbacks controller ставит дваEOS после всех data и завершает dispatcher.
  Finalizer ждёт существующие worker/dispatcher/sink fences, закрывает timeline,
  передаёт общий полный префикс writer и завершает его единожды. Нынешние
  немедленные EOS/late callback drop для этого недостаточны.
- Native Stop HRESULT failure остаётся visible fault; timeout не разрешает
  освободить живой sink. Sinc Flush/reset не заменяет tail drain. EOS filler
  не увеличивает real accepted count; публикуется только фактическая полная
  опора `[center−16,center+15]`, нет final wall-clock padding/raw mic fallback.

Три открытых согласования: разрешить только производный output принятого до
Stop input; определить здоровый прежний tail после отказа НОВОЙ метки отдельно
от corruption/AEC/sink fault (нынешний witnessRejected запрещает любой drain);
точно разделить preparation/readiness и recorded admission, не допустить
выдачу отменённого starting после UI guard. Без этого, доказанных capacities,
resolved phase semantics/partition и review/analyze runtime не меняется.

Round178 обнаружил обязательный dynamic partition дефект Command1000:
constant physical±100ppm/no metadata jitter,0.5s/44100+48000Hz дают8/24 FAIL,
maxerror0.00257591158152 при прежнем допуске0.00001. Один derivative с постоянным
drain480 подтвердил тот же результат; начало/длина сравниваемых диапазонов
совпали. Controller=false и nominal controller=true имеют error0. Packet-
cadenced feedback не принят: long/quality PASS не устраняют это противоречие
независимости точного непрерывного сигнала от input partitions в §5.
Новая cadence/metadata interpolation/lookahead/EOS модель ещё не выбрана;
нормативный допуск и критерий не меняются. Fingerprints — validation round178.

Round177: неизменный Command1000 прошёл один час generated native Sinc/AEC3
48000/44100Hz/−100/+100ppm/jitter0.8ms,359999blocks/3599.99s,trim0/0;
maxinnovation43.435980frames/maxgenerated phase0.122556ms. Streaming driver
не сохраняет запись, timeline ограничен4800frames на источник. Положительный
длительный результат не принимает новую семантику §5: нет real WASAPI,
owned FIFO/Stop protocol, dynamic partition proof, WAV/M4A или SC-003.
Доказательство и fingerprints — validation round177; source не менялся.

Уточнение исследовательского покрытия round175: actual Sinc controller
достигал обоих пределов ±500ppm в22 generated cases,11rates8–192k и обычный/
nearUINT64_MAX firstQPC, противоположные physical ±100ppm, metadata jitter0.8ms,
фиксированные пакеты около10ms. Все cases завершились с399 полными непрерывными
блоками, без timeline trim; maxgenerated phase error0.210121ms. Raw mapper/
innovation/adjacent guards не ослаблены; два EOS filler побитно сравнивались
существующим Source. Это проверка saturation accounting на данной fixture,
не всех dynamic packet/origin/kernel-support states, не long run, AEC quality,
owned FIFO layout или 60min SC003. IdentityStage вместо AEC3 выбран явно.
Числовая модель нормы §5 не изменена. Узкое независимое source review принято;
fingerprints и ограничения сборки — validation-2026-10-02.md, round175.

Уточнение round176: положительный 4-секундный результат выше не переносится
на 12 секунд и пару 48000/44100 Hz. При jitter0.8ms и physical−100/+100ppm
прежний controller±500ppm был отвергнут innovation guard: microphone packet471,
48.1112550067frames при здоровом raw mapper, step14.1744frames и без staging
refusal. Три номинальных quality cases прошли; остальные девять исходной
матрицы не завершены. Отказ возникает в metadata/cursor обратной связи,
а не доказывает дефект AEC или причинность содержимого сигнала.

Отдельный исследовательский derivative меняет только actuator clamp±500→±1000ppm,
не raw/innovation/step thresholds, horizon или фазовую сетку. Actual native
Sinc/AEC3:12/12 quality cases PASS при прежних quality thresholds и новых
asserts generated phase<=1ms/command<=1000ppm. Maxinnovation43.424079frames,
maxgenerated phase0.122486ms, peakcommand904.668295ppm: насыщение нового предела
1000ppm этим опытом НЕ проверено. Новый command пока не нормативное решение §5:
подробности, fingerprints и отдельные проверки отказов — validation round176.

Независимо проверить соответствие §5, first phase/cursor accounting, весь
разрешённый диапазон 8–192 kHz и переменных размеров пакетов, permitted QPC
envelope, saturating controller, integer edges, bounded staging, full-support
start/EOS и fail-closed paths. Затем согласовать plan/data-model/quickstart/tasks,
reviewer-owned checklist, analyze и issue sync. До этого кандидат не принят
для реализации; результаты 44.1/48 kHz не закрывают T094–T096.

Источники семантики API:
[GetBuffer](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer),
[GetPosition](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getposition),
[GetFrequency](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getfrequency).

## Дополнительная граница кандидата — rounds200–202

Constant-period/exact-first±.5tick interval model не является общим runtime
решением: четыре generated metadata случая, принятые исходным ClockMapper,
делают её period intersection пустым. Уже неизвестная первая дробь.49tick
исключает истинный nominal period. First-error/changing-rate/noise должны
рассматриваться явно, не как новое основание отказать приложению.
Симметричное окно устраняет воспроизведённый скачок native kernel и проходит
частную actual-AEC quality проверку, но оставляет5/132 waveform FAIL.
Эти результаты не меняют норматив§5, не разрешают реализацию и не закрывают
T094–T096; подробные premises/pins/границы проверки — validation200–202.
