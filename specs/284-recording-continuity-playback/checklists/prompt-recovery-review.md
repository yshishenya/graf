# Независимая проверка требований T016 — 2026-10-04

PASS: **4 отмечено / 0 не отмечено**, чеклист перечитан после изменения.
**CRITICAL 0 · HIGH 0 · MEDIUM 0** по качеству требований.
Риск: `high-risk-product`, текущая F284. Проверка до реализации T016.

Изменены только reviewer-owned `prompt-recovery.md` и этот отчёт.
Код, тесты, git-состояние, GitHub, приложения, аппаратная запись и выпуск
не изменялись; тесты и сборки не запускались.

| Пункт | Документальное доказательство | Вывод |
|---|---|---|
| CHK001 | FR014/SC010 и уточнение T016 в spec; контракт FR014; quickstart13 | Принудительное закрытие ещё ожидающего предложения отделено от принятой записи, Skip, Stop и «Никогда». Retryable относится только к текущему prompt до потери его идентификатора; отсутствие prompt не изменяет другую цель. |
| CHK002 | План T016; FR014; контракт FR014 | Общий dismiss получает необязательную причину существующего retryable; оба auth/registry caller используют его. Нет reset всего detector, изменений выбора/согласия,8s countdown или2s retry; nil registry по-прежнему запрещает новые предложения. |
| CHK003 | T016 в tasks; SC010; quickstart13; план T016 | Исполняемый red/green требует одно восстановленное предложение, отсутствие повторов и предложений при nil, сохранение accepted/terminal/Skip/Stop и8s; отдельно проверяется wiring обоих производственных callers. |
| CHK004 | План T016; SC010; quickstart13 и общие Dev/CI ворота плана | Независимое ревью и актуальные Dev/CI обязательны. Старый аппаратный контроль не заменяет проверку нового подключения; install/recording/release остаются отдельными воротами. |

Чтение существующего кода подтверждает точность локализации: смена auth
и отказ registry с признаками authFailure/обязательного remote refresh
вызывают общий dismiss после registry=nil. Общий helper очищает prompt/token,
но не сообщает detector, что принятое предложение больше не существует.
Существующий retryable снимает isHandled и фиксирует время2s задержки для
указанного bundleID. Требования ограничивают восстановление ожидающим
prompt, поэтому не разрешают переоткрыть принятую запись или явный отказ.
Остальные callers общего dismiss должны сохранять прежнее поведение.

Конституция7.1.0, spec-kit-flow и product gates были прочитаны в этой же
независимой проверке F284: сохранены target-scoped выбор, согласие,
видимый индикатор и однокнопочный Stop. Уточнение T016 новых разрешений,
данных, источников или зависимости не вводит.

HEAD при проверке: `6dc8d369656d171d1a81488a9ec1b3dd58d0e9aa`.
T016 проверен в ещё не зафиксированных документах рабочего дерева.

| Документ | SHA-256 |
|---|---|
| spec.md | `85fc572e4400be5ce14ad4c6630c1c7bf269011478ba2375546a7dbc87739e2e` |
| plan.md | `e37f92fb409de9e56438318f04a1f54e33b1cb772ad312449c1c8973f4344aba` |
| tasks.md | `d559af3976d8b505a34f5ff82fbd17b4fa353ac3a389225aa3ccb8e5c72ce901` |
| quickstart.md | `3396cce313234954fd9302ea3942f2e427e4ff7043db0f16486849a8b6d92015` |
| contracts/recording-and-playback.md | `2856caa3014b752b9808efc2b045e214d00694508c70375e3c90f18f461ff97d` |

Неясных или неподтверждённых пунктов качества требований нет. Red/green,
реализация общего helper, её независимое ревью, Dev на актуальном SHA,
физическая приёмка нового пути, CI и выпуск ещё не подтверждены.
PASS отчёта закрывает только независимые ворота требований; анализ,
issue-sync и остальные проектные ворота сохраняются.

## Первое ревью реализации T016

Результат: **CRITICAL 0 · HIGH 1 · MEDIUM 0**. Реализация заблокирована
до исправления H001 и проверки порядка вызовов ниже. Чеклист требований
перечитан: **4 отмечено / 0 не отмечено**; его PASS не подтверждает реализацию.

### H001 — обработчик уведомлений может закрыть prompt до auth helper

`DesktopNotificationPresenter.swift:158–162` подписан на тот же
authSessionDidChange, что `TwoBrainRecApp.swift:545`. Его callback синхронно
вызывает invalidate (`:200`), затем dismissAllCards (`:665`), который
вызывает invalidateEnvelope (`:514`) и envelope.onInvalidated (`:517`).
Производственный onInvalidated в `TwoBrainRecApp.swift:1707` вызывает
перегрузку dismiss с `.invalidated`; та записывает terminal outcome и
очищает prompt/token.

Если observer presenter исполняется первым, auth helper `:1167` уже не
видит prompt. Его новый scoped retryable не применяется, detector остаётся
isHandled. Возвращение registry и текущие snapshots не восстанавливают Ask,
нарушая FR014/SC010. Порядок подписчиков NotificationCenter не является
разрешением полагаться на обратный порядок. Ветка registry401/403 при
действующем prompt сама по себе использует helper правильно; проблема
остаётся в auth-порядке и общем onInvalidated.

Нужна минимальная обработка временного auth invalidation до превращения
ожидающего предложения в terminal, с сохранением явного Skip/Stop/accepted
и остальных причин invalidation. Отдельная исполняемая регрессия должна
вызывать реальный presenter.invalidate с подключённым onInvalidated и
показывать восстановление для обоих порядков presenter/composition.

Текущий behavioral test (`MeetingDetectionCountdownTests.swift:405–458`)
не подключает производственный onInvalidated. Он вручную записывает
retryable (`:424`) перед dismissRecordingPrompt (`:426`), поэтому не
проверяет обнаруженный порядок. Строковая wiring проверка подтверждает
новые два caller и common helper, но не ловит callback, очищающий prompt
раньше них.

### Прочитанные доказательства

- Wiring red: 2 теста / 6 failures на прежнем исходнике6dc8; все ошибки —
  source assertions. Behavioral test в этом запуске прошёл и не выдаётся
  за исполнение прежнего helper.
- Отдельный behavioral red: 1 тест / 1 failure с явным адаптером старого
  dismiss без retryable; не неизменный исторический SHA. Доказывает
  необходимость retryable для восстановленного предложения, но не H001.
- Green: 70 тестов / 0 failures,9.934s. Проверяет detector/notification
  2s/8s, nil registry, восстановление и accepted/terminal; H001 этим
  запуском не исключён.

Остальные callers общего dismiss прочитаны: окончательный Skip, принятие,
ended, завершение приложения остаются без retryableReason; permission setup
сохраняет свой прежний explicit retryable. Изменение ограничено текущим
prompt, не добавляет приватного содержимого или новых данных в диагностику.
Нет необходимости сбрасывать весь detector или менять правила записи.

| Проверенный файл | SHA-256 |
|---|---|
| TwoBrainRecApp.swift | `dd027e5fc051d2f0290db666f83d872367365da8ebe5cf9690cfb4c74cd397fa` |
| MeetingDetectionCountdownTests.swift | `d3585812eebd08706ec354dcdebcbb2d490e90b4d571b0622375a4f97fd1233b` |
| MeetingDetectionRecordingLifecycleTests.swift | `69f03d89cd8050c300cf76d3fa6df9cf42675696dd1513a6617d044ce3e30ac3` |
| DesktopNotificationPresenter.swift | `01c6c4bf5dac1fb2e05f6132249fccb66a1472eeb3a64ccb6ad95576386d632a` |

Локальные журналы не включаются в git. SHA-256: wiring-red
`3f58c92d5a2f9b8cc20c091348dc678773817b1d9024644251850376d7e9ff49`,
behavior-red `10f02cb548bb6bfc51656ecadd3c5e1a49f529dba2a3de6e74a2a7ac818fdc30`,
green `08b79533a722d3100cd5fb9fdf7daeba99097e3128a577f673504e9d83ea0891`.

T016 task ещё указывал PolicyTests вместо фактически изменённого
RecordingLifecycleTests; автор сообщил о планируемом исправлении пути.
Это уточнение трассировки не меняет критерии приёмки. Dev с T015/T016,
аппаратный тест нового подключения, окончательный CI и выпуск не подтверждены.
Reviewer не запускал тесты/приложение и изменил только этот отчёт.

## Уточнение требований после H001

Пока записывался результат первого ревью реализации, автор добавил CHK005 и
уточнил FR014, план, контракт и quickstart. Они отдельно перечитаны:
существующий authEpoch сохраняется при показе; onInvalidated при смене epoch
использует retryable, при неизменном — прежний terminal. Оба порядка observers
требуют настоящий presenter.invalidate, generic dismissAllCards/lock/sleep
остаются окончательными. Не нужны новый presenter state, событие или reset.
T016 теперь указывает фактический путь RecordingLifecycleTests.

CHK005 отмечен только по этим требованиям. Текущий чеклист перечитан:
**5 отмечено / 0 не отмечено, C0/H0/M0 по требованиям**. Предыдущие4/0
в разделе первого ревью — исторический результат. H001 реализации остаётся
открытым до отдельного чтения исправленного callback и red/green нового пути.

## Повторное ревью H001 — итог реализации

Исправление H001 прочитано независимо. Итог: **CRITICAL 0 · HIGH 0 · MEDIUM 0**.
H001 закрыт кодом и новой исполняемой проверкой порядка; прежний результат H1
выше сохранён как история. Текущий чеклист требований перечитан:
**5 отмечено / 0 не отмечено**.

Производственный present сохраняет существующий authEpoch. В onInvalidated
сначала проверяется текущий prompt/token, затем сравнивается epoch: изменённый
вызывает общий retryable dismiss; неизменный вызывает прежний terminal
invalidated. В presenter.invalidate epoch увеличивается до dismissAllCards,
поэтому presenter-first теперь возвращает только ожидающий prompt в retryable.
При native-first общий helper сообщает retryable, очищает prompt/token до
закрытия карточки; callback не проходит проверку актуальности и не затирает
retryable состоянием terminal. Нет ожидающего prompt — helper не сообщает
новый consumer outcome. Accepted/Skip/Stop и другие цели не сбрасываются.

Повторно прочитаны оба auth/registry caller и все прочие dismiss callers:
явные Skip, принятие, ended, завершение приложения и обычные invalidation
не получают новую retryableReason. Permission setup сохраняет свой прежний
explicit retryable. Показ новой карточки использует прежние rememberChoice=false,
8s countdown,2s retry, policy/prerequisites и актуальный реестр. Ни новый
detector reset, ни presenter state/event, ни приватные данные не добавлены.
T015 optional registry,15s и600s остаются в прежнем пути.

Новые журналы прочитаны без повторного запуска тестов:

- Ordering red: 1 тест / 1 failure на восстановленном предложении при
  прежнем terminal callback. Используется настоящий presenter.invalidate с
  подключённым callback; имитация прежнего callback в тесте не является
  исполнением неизменного исторического SwiftUI helper.
- Ordering green: 70 тестов / 0 failures,7.674s. Новый тест перебирает
  presenter_first/native_first/generic с настоящим presenter.invalidate;
  generic dismissAllCards сохраняет terminal. Проверены1.999/2s, nil registry,
  один новый Ask, старый start-button,7.999/8s, отсутствие повторов и
  accepted/Skip/Stop. Новая production source-проверка связывает сохранение
  epoch/две ветви callback/общий helper/два callers с реальным исходником.
  Она дополняет исполняемый presenter/detector тест и не выдаётся за
  физическое исполнение SwiftUI композиции.

HEAD остаётся `6dc8d369656d171d1a81488a9ec1b3dd58d0e9aa`; проверены рабочие
изменения. После green автор менял только отступы; итоговый исходник перечитан.

| Итоговый файл | SHA-256 |
|---|---|
| TwoBrainRecApp.swift | `796887841384370e22c67a857c83f90db1efa37494db1a21038f605d684b6b0a` |
| MeetingDetectionCountdownTests.swift | `710dcc7d44d181ada453d2120215b16e5ed3ae79c7e6e655341f1daf7c81f6b5` |
| MeetingDetectionRecordingLifecycleTests.swift | `b1647b1d68d79d2efbbfc195192e0ce80c15d06055ea4c7b3632bd7ee80a4c3c` |

Хеши локальных журналов: ordering-red
`5cba187cfcd91f6c981394e2be81defee9ffc965e845e578667d6c21dcf06160`,
ordering-green `d19c9ccd4b72ab26ab9f717f0f358e5f698941d5dbc9e7da84e84538afd03fe2`.
Журналы в git не добавлялись. Task теперь указывает фактически изменённый
RecordingLifecycleTests; требований без реализации по этому замечанию не осталось.

Неподтверждёнными остаются актуальный штатный Dev с T015/T016, аппаратная
проверка новой композиции, окончательный CI и выпуск.49min аппаратный
контроль старой версии не является приёмкой T016. Reviewer изменил только
этот отчёт; не запускал тесты/приложение и не менял код/git/GitHub/runtime.
