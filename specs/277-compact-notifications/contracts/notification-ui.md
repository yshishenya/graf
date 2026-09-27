# F277 — Общая карточка

## Геометрия

- Visible380pt, radius12; systemfont≥14text/13commands, accessibility text растёт. Textcontrast≥4.5:1, controls/focus≥3:1, цвет не единственный смысл.
- Padding12, icon18, gap8. Closecenter на верхнем левом крае; circle18/glyph9/hit28, вне horizontalstack. Внешний windowinset вмещает hitregion, не перекрывающий текст/icon.
- Short: только «Запись не сохранена — короче 30 секунд», безdetail/actions,44–52pt standardfont. Largefont важнее лимита высоты.
- Optional title/detail не оставляют rows. Actions всегда ниже, secondaryleft/primaryright, gap8, buttonheight≥32. Длинные labels переносятся вертикально, не обрезаются/уменьшаются.
- Prompt: «Встреча в {приложении}», «Запись начнётся через N секунд»; checkbox «Запомнить выбор для {приложения}» отдельной строкой, off; «Не записывать»/«Записать». Нет процентов.
- Спокойная подложка/тень безglow/pulse. Reducedtransparency→opaque; reducedmotion→безанимации.

## Решения записи

| Event | Current prompt | Persist |
|---|---|---|
| explicit start+remember | start once after gates | Always |
| explicit skip+remember | suppress current | Never |
| explicit start/skip without remember | current only | unchanged |
| close/focused Escape | suppress current | unchanged |
|8s expire, remember either | start once after gates | unchanged |
| invalidation/sleep/lock/targetended | cancel, no late action | unchanged |

Перед action проверять token/context и актуальный checkbox, не capturedinitialvalue. Dismiss старой panel не закрывает новую карточку из callback. Doubleclick/expiry race≤1action. Отменённый prompt не стартует послеwake.

## Клавиатура, VoiceOver и сроки

Automatic appearance не активирует GRAF. Первый click исполняет control. Меню «Перейти к уведомлению» даёт panel keyfocus; Tab/ShiftTab достигает close/checkbox/actions, Space/Return действует на focusedcontrol, Escape только focusedpanel. После явного focus закрытие возвращает предыдущий контекст насколько разрешаетmacOS. Глобального Escape нет.

VO: одна initialannouncement, AXButton/AXCheckBox labels/states, читаемыйcountdown. Tick не заменяет controls и не повторяет wholeannouncement; checkbox не объявляется сохранённым доaction. Informational20s/preview6s hover/keyfocushold сохраняет remainingtime; recording8s безhold. Calendarharddeadline120s отdue независимо отhover, действие остаётся в календаре.

Одна карточка, prompt не вытесняется. После него пересчитать snapshot; preview никогда не вытесняетprompt. Sound однократно для реального optional события при sound=true/quiet=false, неtick/update. Quiet не скрывает prompt/indicator/Stop, не обходит Focus.

### Конкуренция и следующий показ

| Вид | Приоритет | Вытеснение |
|---|---:|---|
| recordingPrompt | 4 | Может заменить необязательную карточку; другой prompt не заменяет действующий без явной отмены старого доменным владельцем |
| problem | 3 | Только меньший приоритет, никогда prompt |
| shortRecording | 2 | Только meeting или preview |
| meeting | 1 | Только preview |
| preview | 0 | Только свободная поверхность; занятость возвращается в настройки без очереди |

Равный приоритет не вытесняет карточку другого события. Обновление той же identity меняет данные на месте, не сроки/порядок/фокус. Новая проблема, делающая текущий prompt недопустимым, сначала отменяет его по правилам capture gates; это инвалидирование, а не визуальное вытеснение.

Вытесненная уже показанная необязательная карточка завершается как invalidated и повторно не всплывает: её оставшееся время не переносится и не начинается заново. Существенный результат сохраняется в истории, проблема — также у записи. Ещё не показанные актуальные problem/meeting выбираются заново из текущего snapshot после освобождения поверхности; сначала больший приоритет, затем самый ранний момент события, затем стабильный идентификатор как tie-break. Непоказанный короткий результат допускается держать один (самый новый) до 20 секунд от его появления; все короткие результаты попадают в историю. Если показ состоялся, его обычные 20 секунд считаются от первого показа. Это ограниченный набор кандидатов, не бесконечная очередь.

Пример: во время prompt появляются problem и meeting — окно prompt остаётся; после его завершения показывается ещё актуальная problem, затем meeting только если её исходный hard deadline не истёк. Preview во время любого реального события отклоняется. Problem поверх уже показанной meeting завершает её показ; она не возвращается после закрытия problem. Повторные refresh не повторяют звук и не возобновляют закрытые события.

## Lifecycle/экран

Правый верхний угол visibleFrame выбранного экрана, стабильный якорь при heightchange. При screenchange держать surface/hitregion внутри рабочей области; при коллизии с собственным indicator/Stop сдвигать вниз. Не следить за чужими OS notificationwindows. Sleep/lock/logout/contextswitch отменяют устаревшие callbacks. Quit убирает окна/timers/observers. Закрытие settings не равноquit и не прекращаетcapture.

При первом показе экран выбирается по текущему указателю; если он не найден — NSScreen.main, затем первый доступный. Идентификатор экрана сохраняется до завершения события: tick, флажок и перемещение указателя карточку не переносят. При изменении visibleFrame она пересчитывает положение на том же экране. При отключении выбранного экрана выбирается main/первый оставшийся; срок не сбрасывается. Одна nonactivating panel доступна в текущем Space, включая fullscreen через fullScreenAuxiliary/canJoinAllSpaces; переключение Space не активирует GRAF и не создаёт второй экземпляр.

Вся поверхность вместе с областью закрытия должна помещаться в visibleFrame с внешним запасом 8pt. При узком экране ширина уменьшается от 380pt до доступной (не менее 220pt); текст переносится, кнопки становятся вертикальными. При нехватке высоты текст помещается в доступную прокручиваемую область с клавиатурным/VoiceOver доступом, а close, checkbox и actions остаются достижимыми без уменьшения шрифта. Если даже минимальная область органов управления не помещается или нельзя избежать перекрытия собственного Stop, показ возвращает явный отказ: prompt отменяется без автозапуска, необязательный результат остаётся в истории/основном интерфейсе. Отсчёт невидимого prompt не запускается. Нет экрана — тот же отказ. Простое появление нового экрана не возобновляет отменённое предложение.

## Reference

Старый literal420×82 эталон заменён по указанию пользователя. Только systemfonts/SFSymbols/собственный код. История в существующем меню, не отдельный вид всплывающего окна. Capture permissiondialogs не входят в унификацию.
