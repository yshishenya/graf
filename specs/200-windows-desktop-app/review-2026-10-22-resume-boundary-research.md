# T120 — независимое исследование границы Resume, 2026-10-22

## Решение и границы проверки

**SOURCE GO только на продолжение исследования неизменной границы запроса.**
Это не разрешение реализации, изменения норм, нового запуска микрофона или
приёмка T120. Для принятия предлагаемой замены текущего правила — **REQUEST
CHANGES: сначала clarify и поправка plan с независимым review**.

Короткий ответ: при достоверной корреляции позиции и QPC можно доказать более
узкое свойство — ни один возвращаемый кадр не предшествует неизменной отметке
после запроса Resume. Для этого не требуется попадание paired QPC внутрь
каждого отдельного вызова. Но это **не то же самое**, что свежесть позиции на
момент последнего измерения или сохранённого CLOSE. Простая замена нижней
проверки в текущем worker пока не доказывает весь действующий контракт паузы.

Проверка использует навык `code-reviewer`, прочитанный полностью. Полоса:
независимое исследование исходников и первичных источников внутри активного
high-risk-product F200; единственная разрешённая запись — этот новый отчёт.
Ни VM, ни микрофон, ни сборка/тесты не запускались. Нормы, checklist, tasks,
код, Git, GitHub и состояние сервисов не изменялись. Текущий T103 не проверялся
и его выполняющийся прогон не затрагивался.

Рабочая копия: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Состояние грязное; HEAD сам по себе
не идентифицирует исследованный незакоммиченный код. Injected `0309` не использован.

## Проверенные источники и фактический путь

Прочитаны актуальный guidance index, применимые правила Spec Kit/product gates,
constitution I/II/VI/VII и quality gates, относящиеся к паузе части product
baseline/current status, active feature pointer, spec FR-018 и уточнение
2026-10-04, desktop contract §3, plan T120 и same-stream 1652–1686, T120 из
tasks и ограничения native/portable acceptance в quickstart. Ничего из них
не переопределяется этим отчётом.

Путь по текущему исходнику:

1. `WindowsCaptureSessionController::requestPrivacy(false)` проверяет состояние,
   ставит команду dispatcher; ещё не меняет odd epoch. Время команды Resume
   не становится временем CLOSE.
2. `processPrivacy` вызывает private `resumeMicrophone`. Под `resumeMutex`
   создаются serial/expected odd epoch и единый deadline `now + 1s`.
3. Native worker обслуживает mailbox между отпущенными пакетами, в том числе
   при непрерывной FIFO и после WAIT_TIMEOUT. `readResumeClockSample` читает
   QPC before, same-stream `IAudioClock::GetPosition`, QPC after, затем wall и
   steady. Время after — не время записи кадра.
4. `servicePrivacyResume` проверяет exact S_OK, identity/epoch/deadline,
   frequency/rate/позицию/released end и сейчас именно bracket каждого вызова
   с допуском tick/100ns-округления, не drift envelope. Далее checked
   `B=floor(p*sampleRate/frequency)+1`; B/even epoch ставятся до READY.
5. Dispatcher под прежним порядком блокировок проверяет Stop/fault/deadline,
   принимает epoch, затем подтверждает worker. Принятие необратимо; поздний
   deadline не превращает принятый Resume в отказ.
6. Prefix до B обнуляется **до** normalizer. Сохраняются acquired epoch,
   sequence fence, подавление старых очередей и уже обнуленных накоплений
   timeline; один лишь B их не заменяет. Неизвестные/повреждённые входы всё
   равно проверяются. System/PTS/AEC/число кадров не чинятся этим управлением.
7. `privacyTime(receipt.wall, receipt.steady)` делает прежнее floor-to-ms.
   Writer получает эти значения как CLOSE; сохранение best-effort не отменяет
   Resume, при неуспехе остаётся прежний durable OPEN. Stop/EOS отдельно
   закрывают историю до финализации.

Ключевые места: `WasapiCaptureWorker.cpp:68`, `:382`, `:418`, `:550`;
`WindowsCaptureSessionController.cpp:115`, `:144`, `:161`, `:270`, `:499`,
`:602`; `AudioNormalizer.cpp:34`; `RecordingAudioTimeline.cpp:36`;
`V5LocalRecordingWriter.cpp:339`, `:366`; `Recording/NativeCapture.h:3031`.
Номера относятся к этому снимку и не являются неизменяемыми идентификаторами.

Контрольные суммы исследованных значимых файлов:

```text
65ddf184bbb884047f26b3f59176d47180f1f9f6ecdab1752d582a090891a9d4 WasapiCaptureWorker.cpp
061f3a1e36067e86522856cac93c2e8cedfcaeb834130d4854d250f827bf35c2 WasapiCaptureWorker.h
d18b771754dc443ec51afa180fbcd595a31717e0e803a7475e00e2d21222ee86 WindowsCaptureSessionController.cpp
a3066e2ec5c2259e88fe3ba3ead49970e363e8750d5cff685210c3a41c5b25ad CaptureFaultStateTests.cpp
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 spec.md
f3009717a5763a74b6207448f83496af1d5db9e1f48b360f5faf59aea7977bd2 plan.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f tasks.md
8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4 contracts/windows-desktop-contract.md
```

## Единственное реальное измерение — не новая проверка

Прочитаны существующие `t120-clock-native3/clock-summary.json` и
`run-result.json` в `/Users/yshishenya/Documents/graf-f200-public458.po8CtB`,
а также код уже выполненного ограниченного `native-clock.r6Lltd/ClockProbe.cpp`.
Диагностика вызывает настоящий private clock sampler, но **не** весь протокол
Resume с OPEN/epoch/CLOSE. Поэтому даже положительное измерение не было бы
проверкой приватности всего приложения.

Факты: exact S_OK, paired QPC на `34615 × 100ns = 3.4615ms` раньше call-before;
длительность call `270 × 100ns = 27µs`; один пакет получен и отпущен, valid
packets 0, read/Stop HRESULT 0, elapsed through cleanup 180ms. Receipt явно
пишет `measurement_accepted=false`, `MEASUREMENT_REFUSED`, cleanup verified,
owned processes 0, `audio_read=false`. Нулевой mapper fault не означает, что
mapper принял поток. Формат/PCM/устройства не менялись этой проверкой исходников.

```text
18e88c98522e9b38690694c4e6f039fe1a7694e27f10cda7379fb616ac7f545a clock-summary.json
dceec9d82165cd4f8e7d94b7cb93b7c1ef5395b1a632de8a93cf07868c4c4893 run-result.json
```

Это основание исследовать другую причинную границу, а не назначить допуск
3.4615ms или объявить VM единственной причиной. Повтора не было.

## Что именно гарантируют первичные API

- [Microsoft: IAudioClock::GetPosition](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getposition)
  описывает коррелированные stream position и QPC момента чтения позиции в
  ответ на вызов; QPC возвращается в 100ns. Exact S_OK означает точное чтение,
  S_FALSE не равен ему. Позиция переводится через частоту этого же потока,
  не через предположение о байтах/кадрах. Последовательные позиции не убывают.
  Документ **не** устанавливает разрешённый возраст кэшированного S_OK вне
  вызова и не даёт точности АЦП меньше одного кадра. Наблюдённый ранний QPC
  сам по себе не доказывает корректность пары. Предложенный вывод ниже условен
  относительно правдивой пары, а не доказывает её по двум сравнениям.
- [Microsoft: IAudioClock::GetFrequency](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getfrequency)
  связывает единицы p/f с временем потока; это не измеритель мгновенного
  физического дрейфа относительно QPC. Номинальная частота не позволяет
  достроить старую позицию до after без нового предположения.
- [Microsoft: IAudioCaptureClient::GetBuffer](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer)
  возвращает frame position/QPC первого кадра пакета, не время его извлечения.
  Буфер может содержать несколько ожидающих пакетов. Получение/освобождение
  парные, на одном потоке; держать COM buffer во время ожидания управления
  нельзя. Ни успешный GetBuffer, ни отсутствие очереди в приложении не
  доказывают отсутствие старого звука в endpoint FIFO.
- [Microsoft: high-resolution time stamps](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps)
  различает QPC и UTC; QPC не калибрует wall time. Для сравнений разных потоков
  порядок в пределах ±1 QPC tick неоднозначен, при переводе в 100ns добавляется
  целочисленная квантизация. Нельзя считать `floor(QPCrequest) <= paired`
  доказательством строгого «после запроса» при равенстве. Это основание
  консервативного округления/направленного запаса, **не** миллисекундного допуска.
- [Microsoft: IAudioClock2::GetDevicePosition](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock2-getdeviceposition)
  выдаёт необработанную аппаратную позицию shared-mode; частота устройства
  может отличаться от mix format. Это не непосредственная замена существующей
  client-frame границы. [Microsoft: IAudioClient::Reset](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclient-reset)
  очищает pending data и обнуляет stream position только у остановленного
  потока. Reset/reopen нарушили бы явно принятый same-stream/no-Reset проект.

Сторонний код не переносился. Прикреплённые в research ссылки OBS/WebRTC —
не доказательство точной приватной границы и не источник разрешения переносить
arrival timestamps, warning-only ошибки или restart в GRAF.

## Условное доказательство для неизменной границы

Обозначения: R — обработанный запрос Resume; L — одна отметка QPC строго после
R; q/p — достоверная коррелированная пара того же живого потока; A — QPC после
последнего измерения. Внутри **одного** serial L не передвигается. Принятие
возможно только при `L <= q <= A`, прежнем deadline, валидном p/f/rate и
проверенном `B=floor(p*rate/f)+1 >= releasedEnd`.

При этих предпосылках все кадры с device index < B подавляются, а допустимый
suffix строго после текущего кадра p не может принадлежать времени до L.
Накопления до запроса не оживают: уже извлечённые защищены odd/acquired epoch,
очередью и timeline, ещё не извлечённые — prefix B. Ни latency estimate, ни
экстраполяция p до A для этого доказательства не нужны. Постоянно отстающая
правдивая пара может пересечь **фиксированную** L; при новой L на каждом call
это свойство исчезает. Если пересечения за исходную секунду нет — отказ и
прежняя пауза, не принятие последнего приближения.

Ограничения вывода существенны: доверяются семантика пары и соответствие
client/device координат прежнему потоку; обычные packet/clock/route guards
не отменяются. `L <= q <= A` само по себе не обнаружит драйвер, который вернул
свежий q с несвязанным старым p. Один VM receipt этого доверия не устанавливает.
Это доказательство исключения **до L**, не «до A», не до UI ACK и не до CLOSE.

## Контрпримеры и обязательные решения до кода

### H1 — граница аудио и время receipt/CLOSE различаются

Конструируемый пример, не результат запуска: 48kHz, последний отпущенный
exclusive end 4800 (100ms), запрос/L сразу после 100ms. Следующий вызов около
110ms вернул пару для 106.5ms, то есть p соответствует frame 5112. B=5113
не раньше releasedEnd; `L <= q <= A` проходит. Ещё не извлечённый пакет
4800..5279 получает новую even epoch: prefix до 5113 подавлен, suffix
5113..5279 может содержать звук 106.52..110ms. Это укладывается в один
10ms пакет и не требует секундного переполнения FIFO. А текущий receipt и
CLOSE будут около 110ms после измерения. Millisecond floor этот интервал
не устраняет. При старом bracket такая пара отвергнута.

Следовательно, после простой замены проверки звук после запроса, но до
measurement receipt может вернуться из unread FIFO. Это **не доказанная
утечка до запроса**; это неподтверждённое изменение значения «во время паузы»
и связи с сохраняемой историей. Current plan прямо требует after-measurement
receipt. Нельзя молча назвать receipt точным физическим концом подавления.

Clarify должен выбрать и описать, что означает логический конец: запрос,
подтверждённый witness/frame B, measurement receipt либо epoch commit. Если
нужна гарантия отсутствия микрофона до времени receipt, одной старой пары с
q между L и receipt недостаточно. Нужна иная причинная последовательность:
например, явно одобренная отметка управления **до** неизменной L и последующего
witness, либо сохранение строгого отказа. Это варианты для решения, не новый
проект, разрешение на двухфазный протокол или перевод QPC в wall по оценке.
Нельзя подставлять вычисленное wall `receipt - (A-q)` и выдавать его за
измеренное; UTC может сдвигаться, а принятой QPC–wall калибровки нет.

### H2 — равенство, округление и место фиксации R/L

Если L — floor в 100ns, timestamp немного до запроса в том же квантованном
интервале может пройти равенство. Межпоточный ±1 tick нельзя использовать
симметричным послаблением нижней границы. Нужна доказанная направленная
граница: сравнение с консервативным upper endpoint request QPC с учётом
перевода/межпоточной неопределённости, без вычитания допуска из L. Её вывод
и overflow должны проверяться целочисленно. При отказе QPC/QPF нет Resume.

Уточнить и место R: UI enqueue или dispatcher mailbox. Более поздняя отметка
консервативнее относительно исключения звука, но не равна моменту нажатия.
Минимальный путь — существующий native mailbox/worker с тем же serial и
deadline, не второй UI/clock owner. Пример из тестов с константами 1000 не
проверяет настоящий захват и публикацию новой нижней границы.

### H3 — ожидание, повтор и Stop нельзя свести к замене одного if

Сейчас первый неподходящий clock sample отвергает запрос. Предложенный wait
добавляет состояния: ещё старый witness против повреждённых metadata/ошибки
и timeout. Ожидать можно только явно определённый недостаточно новый witness;
ошибка/исключение, S_FALSE, чужой поток/формат, плохая арифметика, future QPC,
нарушение обычного capture integrity не становятся успехом или скрытым repair.
Точная классификация должна быть утверждена в plan.

- L, seq, expected odd epoch и absolute deadline фиксируются один раз; retry
  после отказа получает **новые** seq/L/deadline даже при той же odd epoch.
  Поздний результат старого COM вызова нельзя сравнить с новым L и применить.
- Ожидание не держит `resumeMutex` вокруг COM и не держит GetBuffer. Между
  попытками worker продолжает отпускать/обрабатывать пакеты с paused epoch;
  иначе endpoint переполнится. Нельзя busy-loop читать часы вместо FIFO или
  ждать её опустошения. Верхняя/внутренняя loop и WAIT_TIMEOUT должны одинаково
  обслуживать запрос без нового отсчёта секунды.
- Dispatcher продолжает ждать без capture/dispatch mutex; существующая
  bounded очередь может расти. Новый протокол не повышает её лимиты и обязан
  пройти continuous-producer/Stop тест, а не только пару clock samples.
- Stop до epoch commit исключает apply; Stop после commit не отзывает ACK.
  Прежний порядок resumeMutex → captureMutex → dispatchMutex и проверки
  running/fault/deadline/epoch сохраняются. Late completion не возобновляет
  остановленную/новую сессию. Секунда ограничивает admission, но не обещает
  принудительно прервать зависший драйверный COM вызов.
- Checked conversion L/QPC, ceil/направленный запас, subtraction, p/f quotient
  и remainder, `+1`, packet exclusive end, seq и epoch не должны переполняться.
  `B < releasedEnd` нельзя чинить `max`; Reset/reopen не допустимы.

## Минимальный путь «сначала проверка» — без запуска в этом review

1. Сначала короткое техническое clarify H1/H2/H3 в существующем T120;
   поправить same-stream plan и затронутые desktop contract/quickstart/analysis
   только после отдельного разрешения. Новая feature/задачи-дубли не нужны.
   Constitution менять не требуется, если приватность/Stop/целостность не
   ослабляются; если меняется пользовательское значение паузы, это не следует
   называть чисто внутренней заменой проверки. Reviewer-owned checklist
   переоценивает независимый reviewer, не исполнитель.
2. RED в существующем `CaptureFaultStateTests.cpp` через private test peer и
   реальный mailbox/controller, не отдельная тестовая реализация алгоритма:
   stale-before-L → post-L-but-before-call witness в том же serial;
   immutable L/deadline и непрерывный producer; отсутствие fresh witness до
   timeout; exact lower/upper edges с целочисленным округлением и overflow.
   Существующие 13 clock rejection cases необходимо явно переразобрать, а не
   удалить их: меняется критерий stale, не S_OK/identity/position guards.
3. RED контрпримера H1 с **unread** packet suffix плюс перехваченные CLOSE
   wall/monotonic значения. Проверять точно утверждённую семантику сегмента,
   не только `state == recording`. Отдельно old queued/in-flight/prefetched,
   частичный prefix, resampler history и timeline накопления остаются нулями;
   уже записанный pre-Pause участок/system/PTS/count/AEC неизменны.
4. Сохранить и расширить `privacyResumeLateClock`/`CommittedAck`: same-epoch
   retry с новым L, старый результат после нового запроса, Stop до/после
   commit, timeout при ожидании, handler exception, accepted после deadline,
   OPEN failure и CLOSE failure, быстрые повторные сегменты. Начать с прежних
   fixtures/test peer; только минимальная seam для времени, если иначе нельзя
   детерминированно доказать новую границу. Нового capture adapter/backend нет.
5. После разрешённого минимального patch — отдельный независимый source
   review и обычные synthetic/native/installed gates. Новый реальный
   metadata-only запуск потребует собственного актуального разрешения,
   привязки исходников/бинарника и cleanup review; в этом поручении запрещён.
   Он всё равно не заменит unread backlog/actual Pause–Resume приёмку T120,
   зависимый T116, physical x64 и общую готовность Windows.

## Итог

Условная математическая идея fixed post-request fence состоятельна для
исключения pre-request backlog при правдивой same-stream паре; это не
миллисекундное послабление под VM. **Одна замена bracket на request lower
bound недостаточна**: текущие after-measurement receipt и fail-on-first-sample
требуют явного нового решения. SOURCE GO относится только к исследованию и
подготовке детерминированных отрицательных сценариев после согласования норм;
реализация/нормативная поправка/повтор микрофона/закрытие T120 не приняты.

## Дополнение: receipt T0 до неизменной L — ограниченная оценка

**Условный SOURCE GO проектному варианту:** он устраняет H1 для конца сегмента, не требуя новой кнопки или перехода UI.
Порядок одного serial: mailbox request → worker wall/steady T0 → консервативная L → same-stream witness q≥L, q≤after → B → READY → epoch apply/ACK → CLOSE(T0).
Обе составляющие T0 снимаются до L; нижняя граница направлена в безопасную сторону с учётом QPC tick/100ns, не L минус допуск; deadline остаётся исходным.
При правдивой паре p/q кадры <B подавлены, первый допустимый кадр после p относится ко времени после L, следовательно после T0; экстраполяция wall/PTS не нужна.
Старый H1 теперь даёт лишь лишнюю тишину от T0 до B; queued/in-flight/odd-epoch данные могут продлить её, но не оживить накопления паузы.
Контрпримера утечке ДО T0 при этих предпосылках не найдено; fresh q со старым несвязанным p либо небезопасное округление L по-прежнему ломают доказательство.
Это не доказательство достоверности пары по единственному VM receipt и не принятие кэшированного S_OK вне документированной семантики Microsoft.
Утверждение про весь OPEN..T0 наследует существующее исключение для уже записанного доверенного pre-Pause участка: OPEN time из запроса не является точной маской PCM.
Wall jump также запрещает трактовать UTC OPEN..T0 как физический интервал; порядок доказывается исполнением/монотонными координатами, floor-to-ms остаётся квантованной историей.
**Реальные продуктовые различия:** CLOSE отмечает ранний native receipt, а не позднее измерение; запись микрофона может начаться позже этой отметки, история не обещает точный PCM-cut.
UI остаётся paused/pending до apply; unread suffix после B может относиться ко времени до смены надписи, тогда как odd-epoch данные того же времени останутся нулями.
Если действующий смысл — «Resume разрешает новый звук после подтверждённой native границы», отдельный выбор owner о кнопках/состояниях не нужен; это технический вариант прежнего сценария.
Owner нужен лишь если требуется иное: гарантированное подавление вплоть до видимого recording/ACK либо точное совпадение CLOSE с первым слышимым кадром; данный вариант этого не обещает.
Предел 1s ограничивает admission, не точную длительность лишней тишины/обновления UI: задержанный COM/ACK и ранее подавленные пакеты не получают новой гарантии.
Поправка plan нужна содержательно для T0-before-measurement и bounded waiting вместо fail-first, но сама по себе не создаёт обязательного нового продуктового вопроса.
**Проверяемые условия до реализации (test oracle; здесь не запускались):**
1. Детерминированные T0/L: ни один принятый witness не ранее T0; равенство после квантизации, межпоточный tick и overflow не позволяют принять pre-T0 frame.
2. Старые q<L → первый валидный q≥L вне call-before bracket: тот же seq/L/deadline, CLOSE получает исходный T0, не время последней попытки/ACK.
3. Unread packet пересекает B: весь prefix нулевой, suffix допустим только после B; H1 fixture не выпускает pre-T0 сигнал, PTS/count/system/AEC сохранены.
4. Queued/in-flight/prefetched/timeline/resampler история не оживает; заранее записанный pre-Pause участок не переписывается; лишняя тишина не объявляется потерей целостности или точным latency claim.
5. Pending обрабатывает/отпускает paused packets без held COM buffer/busy-loop; непрерывная FIFO, WAIT_TIMEOUT и queue pressure не продлевают deadline/лимиты.
6. Нет witness, ошибка или Stop до commit: нет even epoch/CLOSE, прежний OPEN/paused либо Stop; retry получает новый seq/T0/L, late old result ничего не применяет.
7. Stop после commit, ACK после deadline, handler exception и CLOSE failure сохраняют прежние необратимость/Stop/fatal правила; OPEN failure не даёт принятого Pause.
8. Повторные сегменты, floor-to-ms, wall jump и недопустимый receipt проверяются отдельно; никаких вычисленных UTC из q и никаких скрытых max/repair.
Изменён только этот отчёт; нормы, код, checklist/tasks, тесты, Git, VM и микрофон не затронуты. Это оценка проекта, не разрешение реализации и не приёмка T120.

## Сверка с фактическим Mac на c8d67ccefe7848f731798b23d72d37757ad812f5

Независимое продолжение, только чтение pinned blobs через `git show`/`git grep`; checkout/fetch и изменения Git не выполнялись. Windows/history7 не затронуты.
Навык `code-reviewer` перечитан полностью. Следующие ссылки/строки относятся именно к pinned Mac, не к текущим файлам рабочей копии.

### Установленный порядок Mac и точные вызывающие функции

- `apps/macos/RecApp/App/TwoBrainRecApp.swift:289/292`, `:335/338`, `:634/635`: действия основного окна, панели и `DesktopControlModel.shared.onAction` ведут в одни `pauseManualRecording`/`resumeManualRecording`, без отдельного пути приватности.
- `TwoBrainRecApp.swift:2432–2478`: MainActor фиксирует `pausedAt = Date()` / `resumedAt = Date()` **до** `await localRecordingWriter.*PrivacyAsync(...)`; только после возврата вызывает `captureController.pause()/resume()` и присваивает опубликованную `captureSession`. При исключении показывает отказ; успешного Resume UI не получает.
- `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift:167–190`: `pause()/resume()` только проверяют переход и меняют state/visibleIndicator/Stop. Здесь нет часов CLOSE, FIFO snapshot или второго sample admission. Инъецируемый controller `clock` не выбирает время конца паузы.
- `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift:159–187`: async wrapper переносит уже выбранную Date на одну serial writer queue; continuation возобновляется после `*PrivacyOnQueue`.
- Writer `:428–451`: сначала создаёт OPEN с caller `startedAt`, сохраняет checkpoint, затем переключает privacy source в paused и обнуляет retained `pendingBatches[.microphone]`. Отказ checkpoint отменяет новый active segment, не объявляет Pause принятым.
- Writer `:454–463`: сначала `privacySource.update(.capturing)` получает точную границу, иначе throws `resumeBoundaryUnavailable`; затем закрывает сегмент **переданной ранней** `endedAt`, пробует сохранить checkpoint через `try?`, возвращает continuation. Ошибка CLOSE оставляет прежний durable OPEN и не отменяет Resume.
- `apps/macos/RecApp/Sources/Capture/PrivacySuppressingSampleSource.swift:36–54`: под собственным lock вызывает `base.withQueuedFrameCountSnapshot`; внутри producer FIFO lock заменяет `queuedFramesToSuppress` точным остатком и меняет state. `:57–77` сериализует read с переключением и гасит этот prefix, не PTS. `:83–97` подавляет prefetched batch без двойного учёта.
- `apps/macos/RecApp/Sources/Capture/RecordingSampleSources.swift:86–100,146–164,186–188,201–230`: snapshot, append и dequeue используют один FIFO lock. `MicrophoneCaptureService.swift:88–94,107–108,223–236,263–269` делегирует snapshot и добавляет извлечённый AVFoundation batch без отдельного временного фильтра Resume.
- Writer `:28,297–308,483–535` сериализует timer drain, retained batches и управление. `:730–737` передаёт caller `endedAt` в `ProductPrivacySegment.finalized`; `:933–935` вычисляет поле с именем monotonic через **Date minus startedAt**, с `max(0, ...)` и Int, не через независимые steady/QPC часы.

Итак, нормальный Mac путь: **MainActor Date Trequest → await/очередь → атомарный FIFO snapshot + capturing → CLOSE(Trequest) в памяти → попытка checkpoint → continuation → controller/UI active**.
Clock CLOSE не снимается после FIFO snapshot. Новые producer appends после snapshot могут быть приняты ещё до UI active; exact совпадение metadata конца с первым слышимым кадром или UI ACK Mac не обеспечивает.
Pinned tests подтверждают именно намерение исходников, не запуск в этом review: `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift:457,477,564` проверяют старый queued prefix/частичную границу/producer-lock; `:748` — отсутствие границы оставляет OPEN и отказ Resume.

### Что действительно отличается у предложенного Windows T0

**Условный SOURCE GO раннему receipt усиливается сравнением с Mac:** раннее CLOSE до доказанной sample boundary уже используется образцом. Различие «T0 до witness» само по себе не ослабляет принятую приватность/историю и не требует нового выбора UI owner.
Есть измеримое различие истории: Mac использует MainActor request Date, Windows T0 снимается позже на worker после mailbox request; при задержке worker конец/длительность сегмента Windows будут позже, чем при отметке нажатия. Это не точное побайтовое совпадение временных полей двух платформ.
Есть различие доступности checkpoint: Mac возвращает обычный UI ACK после попытки CLOSE, Windows текущий протокол допускает публикацию applied при ещё pending CLOSE. На Windows после UI active durable OPEN может временно сохраняться даже без отказа IO; при отказе CLOSE такой OPEN разрешён **обеими** реализациями. Скрывать это различие нельзя, но утечку микрофона оно не создаёт.
Есть различие границы: Mac исключает принятый producer FIFO до snapshot, не доказывает физическую границу ADC для ещё не доставленного callback; Windows B по достоверной same-stream паре плюс epoch guards исключает pre-T0 unread endpoint backlog. Эти реализации не sample-identical, но предложенная причинная граница не слабее по заявленному исключению накоплений; корректность пары ещё требует отдельного evidence.
Windows independent steady metadata не надо заменять Mac Date-derived «monotonic» или копировать его max; UTC jump не следует чинить ради буквального сходства. Это различие часов, не новый пользовательский сценарий.
Owner-вопрос обязателен только если под идентичностью понимается **точная отметка нажатия** в CLOSE, durable closed checkpoint уже при UI active или тишина вплоть до UI active; последний пункт не является гарантией pinned Mac. При существующем logical-history/best-effort CLOSE контракте новой обязательной продуктовой развилки не выявлено.

### Минимальный clarify/plan patch-кандидат — текст, не нормативная поправка

«CLOSE — ранняя логическая отметка управления, не точная PCM/ADC/UI-ACK граница, как у pinned Mac. Windows выбирает её как native-worker T0 (wall и steady) после текущего mailbox request и до консервативной неизменной L; допускается дополнительная тишина, не восстановление pre-T0 накоплений. Это не обещание точного времени клика».
«Один seq/odd epoch/исходный deadline1s связывает T0 и L. Worker, продолжая безопасно обслуживать paused пакеты, ожидает exact S_OK same-stream witness L≤q≤after с прежними identity/position/released-end/overflow guards; только q<L является определённым ожидаемым недостатком свежести. Повреждение/ошибка не чинятся; timeout/Stop/rejection не делают CLOSE или even epoch».
«Checked B/prefix устанавливаются до READY; существующие acquired-epoch/queue/timeline, admission/Stop/ACK и best-effort CLOSE правила неизменны. После принятия используется **этот T0**, не последнее measurement/ACK время; retry получает новые seq/T0/L, старый результат не применяется. No Reset/reopen/arrival PTS/VM tolerance».
Это минимальная техническая замена двух решений same-stream plan (call-bracket и after-measurement receipt), а не основание переписывать конституцию или изобретать новый продуктовый запрос.

### Одна наиболее важная RED-регрессия перед кодом

Кандидат `privacyResumeFixedFenceKeepsEarlyReceiptAndUnreadPrefix` в существующем `CaptureFaultStateTests.cpp`, через настоящий mailbox/controller/test peer; здесь не создан и не запускался.
Сценарий: последний released end соответствует 100ms; T0=105ms, безопасная L>105ms. Первый корректный, но старый witness q=104ms оставляет тот же запрос pending; затем q=106.5ms/p=5112 при call-before=110ms даёт B=5113 на48kHz и принимается в прежний deadline.
До ACK держать unread packet frames4800..5279 (100..110ms), после ACK дать его реальному consume/normalizer: prefix до5113 нулевой, новый suffix допустим; pre-T0 метка-сигнал не попадает в выход. Старые acquired-epoch данные не оживают, CLOSE получает **105ms**, не110ms/ACK; system/PTS/count неизменны.
Проверка должна отвергать кратчайшие ложные решения: «принять любой S_OK» выпускает pre-T0 prefix, «обновлять L/receipt каждым call» теряет ранний receipt/прогресс. Текущий исходник прогнозируемо RED раньше: первый q<call-before немедленно отвергает запрос вместо ожидания; это source-based прогноз, не результат исполнения.

Blob IDs для повторной проверки pinned источников: PrivacySuppressingSampleSource `e89c2bc278f2c949de0c78034c22f56e293cb677`; CaptureSessionController `1ddc9e5afa9dad51ba8b118631f2bb1da7ed69c7`; V5 writer `0632f67350eed340c648ce82c9e085ccc093b0ef`; TwoBrainRecApp `a4daeb0c911740a4c7c350d267c1205333b1900d`; RecordingSampleSources `c5f774ef5b359ca457668b0ac561904de12fb83f`.
Только этот отчёт дополнен; нормы/код/тесты/checklists/tasks/Git state не менялись, VM/build/микрофон/history7 не использовались. SOURCE GO проекту не равен реализации или приёмке T120.
