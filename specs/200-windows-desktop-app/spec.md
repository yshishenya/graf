# Feature Specification: Windows desktop-приложение GRAF

**Feature Branch**: `200-windows-desktop-app`

**Created**: 2026-08-23

**Status**: Draft

**Input**: Пользователь просит разработать Windows-версию GRAF, максимально
идентичную macOS-приложению: серверный web-кабинет загружается внутри desktop
shell, а запись звука, управление, разрешения и локальная сохранность остаются
нативными.

## Контекст и цель

### Конечная цель и критерии завершения — 2026-09-27

GRAF на Windows — тот же продукт, что актуальный GRAF macOS: одинаковые общие
функции, пользовательские сценарии, состояния и дизайн общего кабинета;
системные действия принадлежат своей ОС. По уточнению пользователя 28 сентября
окончательный эталон — запущенный GRAF Dev из F277,
`51bcff6b1abfdf2a01d59a7d3f00c831674c365c`, а не прежний master
`f5cca687a06dc57ad6ccbef840a0be897eaa6336`. Изменения F277 ещё не слиты в master;
их принятие как эталона не разрешает автоматически сливать чужую рабочую ветку
или развёртывать сервер. Проверенный Windows
checkpoint — `a9691d4d474d918f54493d55a3aba286c749b513`.

«Идентично» не означает копировать TCC, Sparkle или системные рамки macOS в
Windows. Разрешены только объяснённые различия платформенных механизмов,
сохраняющие пользовательский результат. Отсутствующая реализация общей функции
не является основанием скрыть её или назвать особенностью Windows.

Критерии ниже конкретизируют FR-002/003/004/015/020 и SC-001–010, не заменяя
измеримые аудио-, security-, recovery- и release-гейты:

1. **Общий интерфейс.** Один комплект серверных маршрутов, шаблонов и ресурсов;
   все обязательные строки `parity-matrix.md` приняты на обеих ОС на одинаковых
   синтетических данных. Проверяются меню, все страницы настроек, состояния
   загрузки/ошибки/пустого результата, темы и узкие окна. Нет неработающих
   действий, обрезанных панелей, горизонтального переполнения или необъяснённой
   разницы в составе и расположении общих действий. Различия системных рамок,
   метрик шрифта и разрешений записаны отдельно, а не маскируют дефекты.
2. **Разделение платформ.** Системные команды и подписи относятся только к своей
   ОС; общие действия остаются общими. Платформенная адаптация никогда не меняет
   названия встреч, расшифровки, заметки и другие пользовательские данные,
   включая отображение после частичного обновления страницы.
3. **Жизненный цикл записи.** Крестик главного окна скрывает его при доступном
   трее, не останавливая запись и не убирая видимый индикатор/Stop. Явный Quit
   отдельно завершает захват и сохраняет результат. Если скрытие оставит
   пользователя без управления, окно остаётся доступным. Перезапуск веб-части,
   потеря сети и переход в фон не лишают пользователя управления записью.
4. **Полные сценарии.** Record/Pause/Resume/Stop, автозапись, микрофон,
   вход/выход/смена аккаунта, оплата без повторного списания, локальная очередь,
   восстановление отправки и подтверждённое удаление проходят до конечного
   состояния. Проверяются успех и восстановимые отказы, а не только первый
   экран или успешный ответ вспомогательного метода.
5. **Напоминания и фоновые действия.** Выбранные срок 0/1/5 минут, звук,
   заголовок и включение напоминаний действительно влияют на результат и
   сохраняются для нужного аккаунта. По F277 используется одна компактная
   собственная карточка в выбранное время, без ранней карточки за 15 минут
   и без системного дубля. Тихий режим скрывает только необязательные сообщения
   и их звук; вопрос записи, индикатор и Stop сохраняются. Существенные результаты
   повторно доступны в нейтральной истории. Карточки работают только при
   запущенном GRAF. Фоновые окна не перехватывают фокус; ручное
   взаимодействие и управление с клавиатуры остаются доступны. Трей содержит
   общие Start/Settings и подходящие текущему состоянию Pause/Resume/Stop/Quit.
6. **Доставка и обновление.** Установленный подписанный пакет совпадает с
   проверенной сборкой. Проверка обновлений и предлагаемое действие работают
   через доверенный механизм Windows, а не отсутствующую кнопку или произвольную
   загрузку. Чистая установка/обновление/откат сохраняют согласованные данные.
   Development-подпись не подтверждает готовность к внешнему распространению.
7. **Измеримая приёмка.** Все SC-001–010 применены согласно заявленной
   архитектуре, включая физический x64, 60 минут, 100 циклов восстановления,
   доступность и отказные сценарии. Ноль открытых P1/P2 в обязательной области;
   у каждой обязательной строки есть результат и точный source/package SHA.
   Недоступное оборудование, непроведённый сценарий или незавершённое
   развёртывание обозначаются как непроверенные, а не PASS.

После достижения паритета общие функции развиваются сразу для обеих платформ:
каждая такая функция получает строку общей матрицы, общий контракт и проверки
обоих клиентов; системные реализации остаются нативными. Изменение общей страницы
проверяется в Chromium и WebKit, изменение нативного контракта — в обоих клиентах.
Осознанное отличие явно документируется до приёмки; незавершённая Windows-часть
не должна молча становиться постоянной отдельной версией продукта.

### Актуальная база после синхронизации 2026-09-06

База сравнения — `origin/master` `6ff8db3ee18dc7faf52fd8a31c8bade97c5ca548`.
Настоящее уточнение заменяет ниже историческое описание checkbox/opt-in
автозаписи и требования brand-distance; остальные границы Feature 200 сохраняются.
Автозапись следует Constitution 7 / Feature 214: локальный выбор для каждого
подтверждённого приложения `Всегда` / `Спрашивать` / `Никогда`, по умолчанию
`Спрашивать`. Общий выбор применяет одно из этих значений ко всем известным
приложениям; смешанные значения отображаются как `Разные`. Вопрос содержит
восьмисекундный таймер, `Записать сейчас`, `Не записывать`, `Запомнить выбор`.
Только явное действие с галочкой сохраняет выбор; таймер его не сохраняет.
Сервер не владеет этими настройками. Проверки разрешений, подтверждённой встречи,
локальной сохранности, видимого индикатора и Stop остаются.
Старый Windows `alwaysRecordTarget_` существовал только в памяти. Неиспользуемые
глобальные `assisted_auto_start`/`prompt_before_recording` не являются разрешением
для конкретного приложения и не переносятся в `Всегда`/`Никогда`. Отсутствующее
или повреждённое сохранённое значение конкретного target даёт `Спрашивать`;
ошибка сохранения явно показывается и не выдаётся за успешную смену правила.

FR-002/003/004/015/020 требуют реальной проверки установленного приложения:
запуск и повторное открытие кабинета, вход, навигация, восстановление после
недоступности сети/WebView, разворачивание и сворачивание панели, настройки,
выбор микрофона, Record/Pause/Resume/Stop, очередь и повторная отправка, tray.
Белая страница, ложное сообщение об отсутствующем Runtime при установленном
компоненте, недоступная кнопка восстановления и статическая имитация данных
являются провалом этих требований. Ошибка WebView содержит безопасный этап и
код, но не URL с секретами, cookies или текст ответа сервера.

Сходство проверяется с текущим macOS GRAF: одинаковые действия, состояния,
русские подписи и расположение; системные рамки/меню Windows могут отличаться.
Веб-кабинет остаётся общим серверным интерфейсом. Проверка существующего
production кабинета не разрешает deployment локально объединённого сервера.
ARM64 VM с x64-эмуляцией — отдельное свидетельство, не физический Windows x64.

Windows-клиент должен дать пользователю тот же продуктовый сценарий, что и
macOS-клиент: открыть кабинет, начать/поставить на паузу/остановить запись,
видеть честное состояние, сохранить запись локально и автоматически передать её
в GRAF. Веб-кабинет не должен дублироваться отдельной Windows UI-реализацией, а
нативная часть не должна передавать удалённой странице контроль над аудио,
файлами, разрешениями или локальной очередью.

Первая Windows-версия предназначена сразу для внешних клиентов. Решением
владельца продукта и Constitution 7 отменены условия запуска записи, связанные
с выбором юридической политики пространства, уведомлением участников,
подтверждением согласия или законного основания. Отсутствие этих данных не
блокирует ручную запись, transcript-only capture или автозапись; дополнительные
диалоги и серверное подтверждение не добавляются. Устаревшие проверки удаляются,
а не заменяются фиктивным согласием. Пользовательское соглашение — отдельная
работа, не часть условий готовности Record. Правило одинаково для Mac/Windows
и внутренних/внешних пользователей; права доступа к серверным данным сохраняются.

Готовность Record определяется разрешением микрофона, доступностью выбранного
или default input и render endpoint, поддерживаемыми форматами, готовностью
AEC3 и AAC, возможностью безопасно сохранить пакет, отсутствием другой активной
сессии и возможностью показать нативный индикатор с Stop до захвата. Сеть,
WebView, авторизация отправки и юридическая политика не являются условиями
локального старта. Автозапись дополнительно проверяет подтверждённую текущую
встречу, локальный выбор приложения и подавление повторов. Технический отказ
блокирует старт с конкретным действием восстановления; Stop остаётся доступен
после отказа и при сворачивании главного окна.

Рабочее решение для первого Windows-среза: Windows пишет общий микс звука устройства
вывода через системный WASAPI loopback и отдельный физический микрофон. Это не
изоляция звука конкретного приложения: во время активной сессии в запись может
попасть любой звук, который Windows выводит на выбранное устройство. Автозапись
по подтверждённому приложению только запускает видимую сессию; она не является
фильтром аудиопотока.

## User Scenarios & Testing

### User Story 1 - Записать встречу с нативным управлением (Priority: P1)

Как пользователь GRAF на Windows, я хочу открыть знакомое приложение, начать
запись, видеть её состояние и одним действием остановить, чтобы не зависеть от
доступности веб-кабинета во время встречи.

**Why this priority**: Запись и доверие к её состоянию — основной продуктовый
сценарий. Если web-страница зависла или сеть исчезла, пользователь всё равно
должен сохранить встречу и остановить захват.

**Independent Test**: Запустить Windows shell с недоступным кабинетом, дать
разрешения, выполнить Record/Pause/Resume/Stop и проверить локальный пакет,
индикатор и отсутствие обычной записи без готового захвата.

**Acceptance Scenarios**:

1. **Given** нативный shell запущен, а WebView не загрузился, **When** разрешения
   и локальное хранилище готовы, **Then** Record и локальный индикатор остаются
   доступны, а ошибка WebView не блокирует запись.
2. **Given** активна запись, **When** пользователь нажимает Stop в shell или
   tray-индикаторе, **Then** все источники останавливаются, trusted timeline
   закрывается, локальный пакет финализируется, а состояние меняется на честное
   сохранённое/ограниченное/ошибочное.
3. **Given** активна запись, **When** WebView перезагрузился, закрылся или
   перешёл на страницу входа, **Then** native indicator и Stop не исчезают и не
   передают управление странице.

### User Story 2 - Работать с тем же кабинетом, что и на macOS (Priority: P1)

Как пользователь, я хочу видеть тот же серверный кабинет, встречи, настройки,
review и deletion-report, чтобы Windows не стал отдельным продуктом с расходящейся
логикой и копией UI.

**Why this priority**: Единая web-версия сокращает расхождение поведения и
оставляет бизнес-правила на сервере.

**Independent Test**: Открыть `/desktop/meetings`, detail, settings и auth
recovery в Windows WebView2 и в обычном браузере; сравнить route/state matrix,
русский текст, focus/keyboard states и отсутствие native-only controls в HTML.

**Acceptance Scenarios**:

1. **Given** WebView2 runtime доступен и пользователь авторизован, **When** shell
   открывает кабинет, **Then** он загружает тот же origin `https://rec.2brain.pro`
   и desktop routes, что и macOS shell.
2. **Given** страница пытается перейти на неизвестный origin или native-only
   route, **When** route policy оценивает переход, **Then** переход блокируется или
   открывается в обычном браузере без изменения capture/local state.
3. **Given** пользователь перемещается по кабинету, **When** native shell
   получает route/load failure, **Then** он показывает bounded offline/auth/error
   state, а не подменяет серверный кабинет второй локальной встречной лентой.
4. **Given** доступно календарное событие, **When** пользователь нажимает
   «Подключиться» в кабинете, напоминании или нативном меню, **Then** GRAF заново
   проверяет доступ и актуальную ссылку, передаёт её приложению встречи либо
   браузеру и показывает результат без второго перехода от двойного нажатия.
5. **Given** приложение встречи не открылось, **When** пользователь явно выбирает
   «Открыть в браузере», **Then** GRAF заново проверяет событие и открывает свежую
   ссылку именно в браузере. Отмена ничего не открывает; ошибка допускает явный
   повтор. Успешная передача не называется подтверждённым входом во встречу.
6. **Given** подключение выполняется, **When** меняются аккаунт/пространство,
   закрывается/заменяется исходное действие или истекает его срок, **Then** поздний
   результат не открывает ссылку и не запускает запись. Нативное «Подключиться и
   начать запись» допускает Record только после успешной передачи ссылки,
   повторной проверки действия и технической готовности.

### User Story 3 - Не потерять локальную запись и догрузить её после сбоя (Priority: P1)

Как пользователь, я хочу, чтобы запись сначала надёжно сохранялась на диске, а
потом автоматически отправлялась в GRAF, чтобы перезапуск, отсутствие сети,
ошибка авторизации или закрытый WebView не уничтожили результат встречи.

**Why this priority**: Локальная custody и повторяемая загрузка — часть доверия к
записи и уже принятый контракт macOS.

**Independent Test**: Завершить запись offline, перезапустить приложение,
восстановить сеть и авторизацию через WebView; проверить возобновление upload по
серверной truth без дублирования meeting/upload session.

**Acceptance Scenarios**:

1. **Given** запись остановлена при отсутствии сети, **When** приложение
   перезапускается и сеть появляется, **Then** локальный пакет остаётся в
   `desktop-upload-queue.v2` и автоматически продолжает передачу.
2. **Given** часть байтов уже принята сервером, **When** upload возобновляется,
   **Then** native client использует подтверждённые диапазоны и не создаёт второй
   server meeting из-за повторного запуска.
3. **Given** локальная запись не прошла integrity gate, **When** queue её
   проецирует в UI, **Then** она не выдаётся за нормальную готовую встречу и
   показывает только metadata-safe причину и доступное действие.

### User Story 4 - Получить честный результат при ограничении Windows-аудио (Priority: P1)

Как пользователь, я хочу понимать, что именно записалось, если микрофон,
устройство вывода, Windows privacy, sleep/wake, exclusive-mode приложение или
защищённый DRM-поток помешали захвату, чтобы GRAF не показывал ложную уверенность.

**Why this priority**: Неполная или рассинхронизированная запись хуже явной
ошибки. Capture integrity — high-risk boundary.

**Independent Test**: В тестовой матрице отключать разрешение микрофона,
вынимать endpoint, менять default device, уводить машину в sleep, отдавать
protected audio и инжектировать разрыв clock; проверять fail-closed state,
постоянный Stop и metadata-only diagnostics.

**Acceptance Scenarios**:

1. **Given** Windows microphone privacy или выбранное устройство не готово,
   **When** пользователь нажимает Record, **Then** запись не стартует как
   нормальная и предлагает восстановить разрешение/устройство.
2. **Given** WASAPI сообщает invalidated endpoint, разрыв timestamp или overflow,
   **When** trusted capture segment больше нельзя продолжать, **Then** текущий
   сегмент завершается как degraded/failed, без raw-microphone fallback и без
   тихого склеивания разных clock domains.
3. **Given** loopback не содержит protected audio, **When** пользователь
   завершает сессию, **Then** manifest отражает ограничение и не заявляет, что
   защищённый звук был записан.

### User Story 5 - Пользоваться автоматической записью так же, как на macOS (Priority: P2)

Как пользователь, я хочу включать автозапись только для подтверждённых Windows
meeting-приложений с обратимой настройкой и видимым countdown, чтобы запись не
запускалась от музыки, видео или произвольного системного звука.

**Why this priority**: Это защищённая продуктовая capability macOS; Windows
сохраняет локальный выбор пользователя, подтверждённый источник и управление записью.

**Independent Test**: В тестовом registry зарегистрировать и удалить target,
проверить настройки, prompt, `Записать сейчас`, `Пропустить`, timeout и
`Всегда писать это приложение`, включая отказ в разрешении.

**Acceptance Scenarios**:

1. **Given** обнаружен verified Windows target без сохранённого разрешения,
   **When** пользователь видит prompt, **Then** появляется тот же восьмисекундный
   countdown с явными `Записать сейчас`, `Пропустить` и `Всегда писать это
   приложение`.
2. **Given** пользователь сохранил разрешение для точной identity target,
   **When** этот target обнаружен снова, **Then** автозапуск проходит через все
   capture prerequisites и оставляет persistent indicator/one-action Stop.
3. **Given** обнаружено неизвестное имя процесса или обычное media playback,
   **When** detector оценивает событие, **Then** запись не запускается и target не
   добавляется в allowlist догадкой.
4. **Given** главное окно свёрнуто или панель скрыта, **When** подтверждённая
   встреча допускает локальный автостарт, **Then** окно кабинета не является
   условием старта: отдельный нативный индикатор с Stop показывается до захвата.
   Если создать или показать его нельзя, захват не начинается.
5. **Given** запись началась автоматически, включая состояние `starting`,
   **When** подтверждённые потоки продолжаются в другом процессе той же точной
   идентичности приложения, **Then** запись продолжается. Другое приложение,
   неподтверждённый процесс или одно воспроизведение не продлевают её.
6. **Given** идёт автоматическая запись, **When** свежие полные снимки непрерывно
   подтверждают отсутствие её приложения 15 секунд, **Then** запись штатно
   останавливается и финализируется. Если детектор недоступен, устарел или
   отвечает с нарушением порядка, отсутствие не считается подтверждённым;
   через 600 секунд без положительного подтверждения запись останавливается.
   Отсчёт монотонный; повтор одного снимка не продлевает встречу. Эти правила
   не останавливают ручную запись и не возобновляют запись после ручного Stop.
7. **Given** для приложения выбран любой из трёх режимов, **When** проверенный
   каталог получает новую версию программы/сертификата или новую ревизию,
   **Then** выбор сохраняется по постоянному ключу продукта, включая `Никогда`.
   Новое приложение получает `Спрашивать`; неподтверждённая версия не получает
   разрешения только за совпадение ключа или имени. В настройках одна строка
   на продукт, даже если подтверждено несколько его версий.
8. **Given** устанавливается первый Windows-каталог, **When** читаются настройки,
   **Then** используется отдельный формат постоянных ключей; старые глобальные
   переключатели и дорелизный формат хеш-ключей не становятся разрешениями.
   Прежний рабочий каталог был пуст и не мог сохранять реальные правила через
   интерфейс. Старые значения не удаляются/не перезаписываются. Новые правила
   переживают перезапуск и временное отсутствие приложения в каталоге; ошибка
   записи сохраняет прежний выбор и явно показывается.
9. **Given** поставляется запись Windows-каталога, **When** решается её доверие,
   **Then** постоянный ключ взят из общего продуктового каталога, а точные хеши
   EXE и сертификата подтверждены метаданными установки и проверкой Windows.
   Обнаружение не добавляет приложения автоматически. Наличие в списке настроек
   не означает обнаруженную встречу или приёмку всех версий/архитектур продукта.

## Edge Cases

- WebView2 отсутствует, повреждён или его runtime ниже минимальной проверенной
  версии: native capture/local custody не ломаются; кабинет получает bounded
  runtime-unavailable state и инструкцию восстановления.
- Кабинет недоступен, auth-сессия истекла, route malformed или сервер вернул
  401/403/409/429/503: native queue сохраняет локальную truth и retry policy.
- Нет default render endpoint, endpoint занят exclusive mode, устройство
  отключилось, default endpoint сменился или Windows Audio Service перезапустил
  поток: текущий trusted сегмент не продолжается молча.
- Микрофон запрещён глобальной privacy-настройкой, выбранный input исчез,
  формат не поддерживает целевую конфигурацию или пользователь отключил input:
  Record блокируется или session становится явно degraded.
- Система уходит в sleep/modern standby, возвращается с другим device/clock или
  приложение получает suspend/termination: writer делает bounded recovery и не
  подменяет отсутствующие frames wall-clock padding.
- Render loopback возвращает тишину из-за protected/DRM-контента: состояние и
  manifest говорят об ограничении, а не о полноценной записи.
- Callbacks приходят не блоками 10 ms, с разным размером или с jitter:
  callbacks только публикуют timestamped batches; единственная timeline делает
  canonical 480-sample framing.
- Диск заполнен, файл нельзя атомарно закрыть, manifest повреждён или очередь
  записана частично: сохранённые байты не перезаписываются пустым ledger,
  документ quarantine-ится metadata-safely.
- Windows N не имеет нужного Media Foundation AAC encoder: installer/runtime
  readiness сообщает несовместимость до нормальной записи или сохраняет только
  проверенный degraded artifact по явно согласованному контракту; нормальная
  запись с отсутствующим playback artifact не заявляется.
- Приложение закрывается дважды, Stop нажимается во время старта/финализации или
  user запускает два потока одновременно: действует один idempotent session и
  одна очередь writer.
- High Contrast, DPI 200%, narrow window, keyboard-only, screen reader и
  Reduce Motion не скрывают indicator, Stop, permission state или важное
  degraded сообщение.
- Истёкший вход, отменённое событие, временный отказ сервера или приложения
  встречи завершают ожидание подключения с понятным результатом и доступным
  повтором. Частичное обновление страницы не создаёт браузерный дубль перехода.

## Out of Scope

- Process-isolated loopback, запись только Zoom/Teams/браузера, включение или
  создание `Stereo Mix`, виртуального аудиодрайвера, отдельной routing-системы,
  kernel component или driver installer.
- DRM bypass, обход Windows privacy, запись без видимого пользовательского
  контроля, запись в elevated/system process или service.
- Новая серверная meeting-list UI, отдельная Windows web frontend-копия,
  прямой доступ desktop клиента к MediaScribe/MinIO и хранение server secrets в
  клиенте.
- Изменение утверждённых macOS capture semantics, manifest v5 и server upload
  lifecycle без отдельной совместимой миграции.
- Browser extension, bot/participant joining, calendar provider integration,
  удалённое управление записью и скрытая запись от произвольного процесса.
- Автоматическая публикация в Microsoft Store, release/deploy и production
  rollout до отдельного release approval.

## Requirements

### Functional Requirements

- **FR-001**: Windows client MUST support Windows 10 22H2 (build 19045) and
  supported Windows 11 releases on x64; ARM64 MUST be built and tested before
  claiming ARM64 support. The app MUST NOT depend on a preview Windows SDK or
  preview Windows App SDK API. The exact Windows 11 build set and stable SDK/
  WebView2 versions MUST be recorded in the implementation lock/matrix before
  any Windows support or performance claim is made.
- **FR-002**: The product MUST preserve the macOS user-visible semantics for
  Record, Pause, Resume, Stop, recording states, permission recovery, local
  custody, upload status, auth recovery, calendar Join and deletion truth. OS-native window and
  tray conventions MAY differ only where Windows has no equivalent macOS surface.
- **FR-003**: The client MUST load the server-owned cabinet from the configured
  approved HTTPS origin, with production default
  `https://rec.2brain.pro/desktop/meetings`, and MUST NOT duplicate meeting list,
  detail, settings or review business logic in native Windows UI.
- **FR-004**: Native code MUST own audio capture, capture readiness, permission
  recovery, local recording files, local upload custody, diagnostics, persistent
  indicator and one-action Stop independently of WebView availability.
  Readiness MUST follow the native conditions above, never require legal-policy
  setup or participant-consent evidence, and never fabricate such evidence.
- **FR-005**: WebView navigation MUST be limited to exact approved route kinds on
  the configured origin. Unknown origins, arbitrary file URLs, local paths and
  native-only routes MUST be rejected or opened externally without mutating
  local state.
  The only embedded external-navigation exception is the bounded, unprivileged
  billing payment session defined in bridge contract §9: exact provider entry,
  subsequent HTTPS bank chain, no native authority, and 900-second expiry.
  This exception also qualifies the general external-origin rejection in US2;
  it never authorizes external native messages or arbitrary initial navigation.
- **FR-006**: Web-to-native requests MUST use a versioned JSON envelope,
  validate source origin, schema, session nonce, command and payload before
  acting, and MUST expose no generic host object or arbitrary script bridge.
  Native initialization uses the `native_ready` envelope. Native
  `local_recordings` display messages use the separate `command/nonce/rows/operations/recoveryRequired`
  shape, bound to the current approved document and nonce, and grant no native
  authority. Only typed `request_app_quit`, `local_recording`, `app_appearance`,
  `native_settings`, `delete_selection`, `request_app_update`, `calendar_join`
  and cancellation-only `calendar_join_cancel` requests are accepted, each on its
  exact approved route with its own payload/capability checks; no web
  acknowledgement establishes capture, upload or deletion truth.
  `request_app_update` is only a bounded intent to open the native update UI;
  it accepts no URL, path, command or installer payload and cannot install software
  directly from the web document.
  `calendar_join` accepts only event/request identities for an explicit current
  calendar action, never a URL or process command. Native code resolves the
  authorized target afresh and cancels stale actions; bounded replies reveal
  no meeting link and grant no recording authority. See bridge contract §10.
  `calendar_join_cancel` carries only the matching event/request UUIDs of the
  current document's pending action. It cannot cancel a native card/menu action,
  start anything, release an unfinished worker, or affect a later request.
- **FR-007**: The Feature 200 baseline system track MUST use WASAPI shared-mode loopback on the
  current/default render endpoint and MUST NOT require `Stereo Mix`, a hardware
  loopback device, a virtual driver or exclusive mode.
- **FR-008**: The Feature 200 baseline microphone track MUST use a user-selected or approved
  default physical capture endpoint through WASAPI shared mode. Windows
  microphone privacy and endpoint readiness MUST be explicit prerequisites.
- **FR-009**: Native capture MUST publish timestamped batches into one bounded
  timeline. The timeline MUST normalize to 48 kHz mono, process exact 10 ms /
  480-sample pairs through the pinned GRAF WebRTC AEC3 C ABI, and MUST own
  ordering, gaps, route generations and final framing.
- **FR-010**: AEC3 reference processing MUST receive the render/system frame
  before the microphone frame. Processor failure, missing reference, invalid
  samples, untrusted timestamps, route change or overflow MUST never fall back to
  an untreated raw microphone track or present the result as normal.
- **FR-011**: A normal finalized package MUST remain compatible with macOS v5
  custody: one canonical ASR WAV (PCM signed 16-bit little-endian, 16 kHz,
  mono), one playback M4A (AAC-LC, 48 kHz, mono), manifest metadata and the
  existing accepted track/queue roles. WAV/M4A/timeline duration difference MUST
  be no more than 100 ms for a normal package.
- **FR-012**: Local recordings MUST be written below the user-scoped Windows
  application-data directory with user-only ACLs, protected commit publication
  and bounded flush/error handling (v1 temp-file plus atomic-rename; packed v2
  verified two-head publication without an atomic-overwrite claim), and no credentials, cookies, raw
  transcript or raw audio in diagnostics.
  The inherited encrypted-local-buffer requirement applies to Windows: custody
  audio, manifests/recovery metadata, and content-bearing temporary files MUST
  be encrypted at rest, including while writing, encoding and recovering, not
  only after finalization. ACLs alone do not satisfy encryption. Protection MUST
  work offline in the standard-user context on the supported Windows editions,
  without a new password, consent dialog, administrator elevation or mandatory
  whole-disk configuration. Keys MUST NOT be stored in plaintext alongside the
  ciphertext or exposed through WebView/diagnostics. Playback, hashing and
  resumable upload MUST preserve the existing logical v5 bytes and ranges without
  creating an unprotected temporary audio copy. Protection/key/integrity failure
  MUST preserve existing artifacts, block unsafe writes and report a recoverable
  storage failure; it MUST NOT substitute an empty ledger or claim normal saving.
  Protected package-state JSON v1/v2 MUST use the single version key `schema`
  and the exact nine top-level fields defined in custody contract §8.1;
  `schema_version`, aliases, unknown and duplicate fields MUST be rejected.
  This does not rename or change the existing logical v5 manifest format.
  For the packed media representation, a live checkpoint MAY inherit the proof
  of unchanged data only while the same verified file owner remains continuously
  held. New data and the publication MUST be independently read back and checked
  before acknowledgment; every data read MUST check the requested data. After
  any ownership gap, a full bounded-memory verification MUST precede normal
  use. Latent corruption of unchanged data may therefore be detected at a later
  read or full verification, not at the next live checkpoint. This explicitly
  accepted detection-time tradeoff does not permit unchecked new data, plaintext
  fallback, metadata rollback or a normal result after an observed failure.
  Pre-existing unprotected packages need an explicit, restart-safe compatibility
  transition before protection is claimed; no automatic deletion or destructive
  replacement is permitted. Verified local deletion does not imply forensic
  erasure or cryptographic unrecoverability without separately proven key scope
  and destruction.
- **FR-013**: The Windows queue MUST reuse the compatible v3 ledger with a v2
  reader (the historical filename remains `desktop-upload-queue.v2`) and
  preserve immutable local identity, server truth, accepted ranges, retry records,
  retention and conflict state. It MUST quarantine malformed ledgers rather than
  replacing them with an empty queue.
- **FR-014**: Upload MUST go only through existing GRAF desktop APIs; the client
  MUST never send audio directly to MediaScribe or store MediaScribe credentials.
  Upload MUST resume after launch, activation, auth recovery, network recovery,
  wake and scheduled retry without the WebView route being open.
- **FR-015**: Active capture MUST have a persistent native visible status and a
  one-action Stop reachable from the main shell and the Windows background/tray
  surface. WebView failure, minimization or focus changes MUST NOT hide Stop.
- **FR-016**: Target-scoped automatic recording MUST use verified Windows target
  identity, explicit reversible settings, the existing countdown/prompt actions,
  capture prerequisites, visible indicator and Stop. It MUST NOT infer a target
  from arbitrary process names or start for arbitrary system/media playback.
- **FR-017**: Endpoint change, sleep/wake, audio-service interruption and
  protected-audio limitation MUST transition through explicit states with
  metadata-safe reason codes and recovery action. Silent cross-device continuation
  is forbidden for the first release.
- **FR-018**: Audio timestamps MUST use a monotonic QPC/WASAPI clock mapping and
  validate monotonicity, clock domain and drift. Wall-clock arrival time MUST NOT
  be used to invent missing audio or align independent streams.
  Подготовка начала потока может исключить один недостоверный стартовый пакет
  по ограниченному правилу контракта §5; его звук не считается записанным,
  исключение учитывается явно и не разрешает пропуск дальнейших ошибок.
- **FR-019**: WebView2 and native host MUST run as a standard user process. No
  driver, service, system/elevated process or privileged audio component may be
  required for the Feature 200 baseline.
- **FR-020**: The distributable MUST validate WebView2 Evergreen availability,
  Windows App SDK dependencies, package signature, architecture and rollback
  behavior before installation can be claimed as ready. WebView2 must be restored
  or installed by the supported installer path, not by silently switching to an
  arbitrary Edge browser.
- **FR-021**: Native diagnostics and committed evidence MUST contain only bounded
  metadata: version, platform, state, safe reason code, counts, durations and
  redacted device identity. They MUST NOT contain raw audio, transcript text,
  credentials, cookies, signed URLs, private meeting content or live private
  paths.
- **FR-022**: Windows deletion and local purge behavior MUST use the existing
  GRAF lifecycle truth and MUST acknowledge local purge only after deletion,
  tombstone or cryptographic unrecoverability has been verified.

### Key Entities

- **WindowsDesktopSession**: one native capture session with id, state, start/stop
  times, target evidence, permission snapshot, route generations and finalization
  result.
- **WasapiEndpointSnapshot**: stable device id hash, data-flow role, format,
  channel/sample rate, default/selected status, availability and route generation.
- **RecordingAudioBatch**: bounded mono/float sample batch with source role,
  sample count, monotonic presentation timestamp, clock domain, format and
  discontinuity marker.
- **RecordingAudioTimeline**: one trusted ordering/alignment owner with bounded
  source buffers, AEC3 processing counters, drift/drop/gap state and canonical
  output framing.
- **LocalRecordingPackage**: user-scoped directory containing manifest, canonical
  ASR artifact, review playback artifact, hashes, byte counts and integrity state.
- **UploadCustodyItem**: queue projection over the compatible v3/v2 ledger with local
  identity, server truth, retry owner/action, accepted ranges and retention state.
- **WebViewBridgeEnvelope**: version, message id, session nonce, origin-bound
  direction, request name and bounded payload. Used for web-to-native requests
  and native initialization/typed replies; `local_recordings` has its separate display
  shape. Validation errors are internal refusal results, not web acknowledgements
  or proof of saving, uploading or deleting.
- **VerifiedTargetIdentity**: exact Windows target evidence used by auto-record
  policy, including approved executable identity and registry version; process
  name alone is insufficient.

## Success Criteria

### Measurable Outcomes

- **SC-001**: On a reference Windows 10 22H2 and Windows 11 x64 machine, native
  shell and local Record readiness are available within 2 seconds after launch
  when permissions/storage are ready, independently of web/network state. A
  healthy cabinet loads its approved route within 15 seconds.
- **SC-002**: The parity matrix covers every macOS recording state, native action,
  permission state, upload custody state and cabinet route in scope; 100% of
  mandatory cases have matching user-visible meaning and no duplicate native/web
  ownership.
- **SC-003**: In a 60-minute synthetic/reference capture with source clocks at
  ±100 ppm, there are no dropped or duplicated output frames, WAV/M4A/timeline
  duration difference is at most 100 ms, and the system-audio component level
  differs by no more than 1 dB from the reference run. The level is the
  integrated RMS dBFS of the canonical 48 kHz mono system-render component over
  the same active synthetic interval, measured before the final mix. After
  warm-up on the reference four-core x64 machine, native process CPU time MUST
  stay at or below 25% relative to wall time, resident memory growth MUST stay
  at or below 128 MiB, and neither source queue may grow without bound.
- **SC-004**: 100% of active-capture fault injections keep a visible native
  indicator and one-action Stop, and 100% of permission, endpoint, clock,
  protected-audio and overflow failures avoid normal-status claims and raw-mic
  fallback.
- **SC-005**: Across 100 offline/relaunch/auth-recovery/wake upload cycles, local
  packages remain recoverable and no duplicate server meeting or upload session
  is created when server truth is available.
- **SC-006**: Security tests reject every message from an unapproved origin,
  invalid schema/nonce/command or oversized payload in the bridge matrix; no
  secret or content-bearing field appears in metadata-only diagnostics.
- **SC-007**: Automated-recording tests produce distinct outcomes for immediate
  start, skip, countdown timeout and saved target policy; unknown targets produce
  zero automatic starts.
- **SC-008**: Install, update, uninstall and rollback on supported x64 test
  images preserve authenticated web profile policy, local queue and recordings;
  a missing WebView2 runtime produces a recoverable bounded state.
- **SC-009**: Keyboard-only, screen-reader, high-contrast, 200% DPI, narrow
  window and reduced-motion checks retain visible focus, readable state, target
  size, indicator and Stop without horizontal overflow or color-only meaning.
- **SC-010**: Before ARM64 support is advertised, the same capture, writer, AEC3,
  WebView boundary, installer and rollback gates pass on an ARM64 Windows image;
  otherwise the release explicitly remains x64-only.

## Assumptions

- Existing server cabinet routes, authentication, desktop upload APIs, v5
  manifest and deletion contracts remain the source of truth; this feature does
  not fork server UI or invent a Windows-only API.
- The first Windows release targets a user-installed desktop app and standard
  user context. No enterprise driver, system service or admin elevation is
  required.
- Windows App SDK stable, WebView2 Evergreen Runtime, WASAPI, Media Foundation
  and the Windows SDK are available through a supported build/installer lane.
- Microsoft AAC encoder is available on supported Windows editions. Windows N
  is not part of the initial supported claim until its Media Feature Pack/AAC
  gate passes; otherwise the installer must exclude it and a normal
  playback-ready package must not be claimed there.
- The existing pinned WebRTC AEC3 dependency and its narrow C ABI remain the
  algorithmic contract; a Windows build must prove identical configuration and
  license provenance before implementation uses it.
- A healthy network is not required to begin or finish local recording; it is
  required only for server cabinet/authentication and upload progress.
- Product-owner approval is still required before implementation commits,
  release packaging or production distribution.

## Legacy Impact

Classification: remove

В затронутом Windows-потоке удаляются заменённые поля/ветви состояния,
синхронные дубли, старые команды моста, глобальные переключатели автозаписи
и разбор дорелизных хеш-ключей V1. Новая схема V2 не содержит migration reader:
пустой прежний рабочий каталог не позволял сохранять реальные per-app правила.
Неиспользуемые значения HKCU не удаляются, пользовательские записи не затрагиваются.

Действующие общие контракты v5 записей и совместимой v3/v2 очереди сохраняются как текущий
продуктовый формат, не как запасная устаревшая реализация. Удаление серверных
полей и API работающего macOS-клиента вне этого среза; Windows не расширяет их.
Трассировка удаления и проверки: T080–T084, quickstart.md и validation-2026-09-06.md.

## Clarifications

### Session 2026-10-04

- Q: Используем ли `schema` как единственное имя поля версии нового внутреннего
  формата защищённых записей? → A: Да, `schema`; подтверждено владельцем.

### Session 2026-10-04 — приватная пауза T120

- Повторный продуктовый вопрос не требуется: владелец уже подтвердил полный
  паритет с новым GRAF Dev. Для Pause/Resume FR-002/009 применяется поведение
  Mac F284 на `c8d67ccefe7848f731798b23d72d37757ad812f5`, не переключение
  одного признака при выдаче кадра. Записанный до Pause доверенный участок
  не переписывается. Накопленный во время паузы микрофон не восстанавливается
  после Resume, включая ожидающие, извлечённые и частично обработанные данные.
- Начало privacy segment обязательно сохраняется до принятия Pause;
  ошибка не даёт успешной паузы. Resume требует надёжной границы очереди;
  без неё остаётся paused и доступен Stop. Сохранение конца сегмента после
  успешного Resume — best-effort: его ошибка не отменяет Resume и оставляет
  прежнюю сохранённую открытую отметку. Это не разрешение потерять сегмент
  или признать неизвестную границу успешной.
- Сведения сохраняются только через защищённый путь T116. Текущий открытый
  V5 writer не разрешает новый временный plaintext journal. Управление
  асинхронно, не блокирует UI/Stop и не ждёт опустошения непрерывной очереди.
- Выявлено ограничение представления: manifest≤4096B несовместим с историей
  повторных пауз. Проектная поправка — manifest≤64KiB, как существующие
  служебные metadata, с проверкой полного сериализованного размера до
  сохранения OPEN. Это не увеличение аудиодопусков, общей памяти или размеров
  root/cache/queue. Изменение предела и приёмка существующих/новых manifest
  требуют отдельного независимого review перед кодом; молчаливое обрезание
  истории, новый открытый файл и произвольный предел количества пауз запрещены.
  Полная T120 остаётся зависимой от T116 и проверки установленного приложения.

### Session 2026-10-03

- Q: Разрешается ли вместо полного перечитывания всех ранее сохранённых
  данных при каждом подтверждении сохранения проверять новые данные сразу,
  наследовать проверку неизменённых данных только при непрерывном владении
  файлом и полностью проверять их после повторного открытия, учитывая, что
  скрытая порча старых данных может обнаружиться позднее при чтении? → A:
  «Разрешаю» — последнее подтверждение владельца в текущем чате.
- User-scope DPAPI и SHA-256 сохраняются. Это изменение алгоритма проверки
  больших media objects, не разрешение собственного AES/key/nonce lifecycle,
  открытой временной копии, увеличения аудиодопусков или выпуска. Небольшие
  authority metadata остаются в v1 с полной проверкой и запретом rollback.
- Поправка требует нового независимого design/checklist/analyze gate T115
  перед соответствующей реализацией T116. Прежнее принятие v1 и измерения
  примитивов не принимают packed путь, скорость или установленное приложение.

### Session 2026-10-02 — независимый срез защищённого хранения

- Q: Разрешается ли реализовать защищённое хранение записей отдельно,
  параллельно с исправлением аудиочасов, сохранив обязательные проверки записи,
  удаления, восстановления и выпуска? → A: «Разрешаю».
- T115–T118 составляют самостоятельный high-risk срез FR-012/013/014/022.
  После принятия T115, независимых checklist/analyze и синхронизации задач
  разрешена его последовательная реализация без ожидания clock T094–T096
  или календарного запуска T119. Начальные проверки используют искусственные
  данные, не реальные записи пользователя и не аудиоустройства.
- Это изменение порядка разработки, не исключение из требований: весь
  защищённый путь, сохранность старых данных, отказ без открытой запасной копии,
  общая приёмка звука и точного установленного пакета остаются обязательными.
  Срез хранения не разрешает перенос непринятого clock-кандидата, миграцию
  рабочих записей без её собственных gates или выпуск незавершённого Windows.

### Session 2026-10-02 — календарное подключение T119

- Дополнительных продуктовых вопросов нет: поручение полного паритета включает
  подключение актуального Mac. F277 остаётся эталоном уведомлений; F279 в master
  определяет общее подключение, не заменяет выбранный дизайн и не разрешает
  перенос чужой рабочей ветки или deployment.
- Область, роли, состояния, отказы, приватность, доступность и завершение
  определены US2/FR-002/005/006 и bridge contract §10. Передача ссылки отличается
  от входа; только явный native Join-and-record допускает Record. Нет
  автоматического browser retry, URL из страницы или новой интеграции провайдера.
  Способ запуска Windows — решение плана, не новый продуктовый выбор.
- Это уточнение требований, не подтверждение реализации T119, общего analyze
  или исправления аудиочасов.

### Session 2026-10-05 — корреляция отмены T119

- Нового продуктового решения нет: исчезновение/замена действия уже отменяет
  переход по §10. Уточняется только транспорт `calendar_join_cancel` с двумя
  UUID и без новых полномочий; исходный JSON проверяется до SDK-нормализации.
- Request UUID принимается не более одного раза за жизнь документа, включая
  busy/not-ready отказ. Предел — 1024 принятых UUID; по достижении новый корректный
  запрос получает cancelled/not_ready до обновления документа. Память ограничена,
  старые UUID не вытесняются ради повторного использования. Отмена не расходует
  новый request UUID и не освобождает actual pending-work lease.
- Сначала проверяется replay уже сохранённого UUID (нет ответа). Новый UUID,
  отклонённый именно из-за cap, не admitted/consumed: его повтор получает только
  cancelled/not_ready, без work и роста history. Это исключение из consume-on-
  not-ready, не разрешение последующего flight в том же документе.

### Session 2026-10-05 — ближайшие встречи в нативном меню T119

- Clarify: новых вопросов и ответов пользователя нет. Область, роли, общий
  путь подключения, приватность, ошибки, доступность и критерии завершения
  остаются определены US2/FR-002/005/006 и выбранным Mac. Недостающее техническое
  сопоставление CalendarTray относится к plan, а не к новому продуктовому выбору.
- Меню показывает ближайшие встречи отдельно от карточки напоминания: закрытая
  карточка, «Тихий режим» или текущая запись не запрещают явное подключение из
  меню. Название и время подчиняются серверным настройкам. Ошибка допускает
  только явный повтор с новой проверкой доступа; меню не начинает запись.
- Образец: собственный GRAF CalendarTray/CalendarMeetingOpener на
  `721b5125d799ea798a4af0b3625e18d3c1109039`. Native conventions отличаются, но
  список не заменяется двумя кнопками текущей карточки. Lifetime и admission
  определены в дополнении plan «T119: ближайшие встречи»; готовность исходников
  или установленного приложения этим не подтверждается.
- Уточнение Round243: «пользовательский часовой пояс» — выбранная в аккаунте
  зона, как DesktopUserTimeContext выбранного Mac; системная зона используется
  только при отсутствии принятой настройки. Зона принадлежит текущему
  подтверждённому аккаунту/сеансу/документу, не переносится между аккаунтами и
  не восстанавливается с диска. Переход летнего времени определяется зоной на
  момент самой встречи, не текущим фиксированным смещением. Нового выбора
  пользователя нет; источник и проверки Windows конкретизируются в plan.

### Session 2026-09-30 — часы и унаследованная защита хранения


- Дополнительных продуктовых вопросов не требуется: пользователь уже выбрал
  полный паритет, внешних клиентов и отсутствие новых препятствий. Требование
  encrypted local buffers из PRD и FR-043 F057 не отменялось; FR-012 явно
  распространяет его на Windows и временные файлы. Выбор нативного механизма
  относится к плану, а не к новому пользовательскому паролю или исключению
  из baseline. Историческое объяснение T083 про отсутствие шифрования описывает
  незавершённую реализацию, не целевой результат.
- Schema6 и синтетическое воспроизведение подтверждают разные наблюдения:
  непрерывный счётчик кадров, отклонение пакетной временной метки и окончательный
  отказ текущего mapper. Одиночное превышение timestamp budget само по себе не
  доказывает устойчивое изменение частоты устройства или потерю звука. VM как
  источник отклонения не установлена. FR-009/018 и SC-003 сохраняются; текущий
  численный контракт §5 не ослабляется этим уточнением. Новая обработка меток
  требует согласованного плана всей цепочки и независимой проверки до кода.
- Покрытие уточнения: область/поведение, данные/переходы, пользовательские
  действия, качество/сохранность, интеграции, отказы, ограничения, терминология
  и завершение определены. Техническая модель часов и механизм хранения ещё
  требуют исследовательского доказательства; это не разрешение начать их
  производственную реализацию и не подтверждение готовности выпуска.

### Session 2026-09-28 — фактический эталон GRAF Dev F277

- Q: Брать ли новый GRAF Dev из F277 с компактными карточками, тихим режимом и
  без системного канала окончательным образцом Windows вместо версии master?
  → A: «Да, повторить новый GRAF Dev».
- Проверено: `GRAFSourceSHA` запущенного `/Applications/GRAF Dev.app` равен
  `51bcff6b1abfdf2a01d59a7d3f00c831674c365c`; обновлённый origin/master остаётся
  `f5cca687a06dc57ad6ccbef840a0be897eaa6336`. Новое поведение нельзя выводить
  только из master. Нормативны spec/contracts/data-model F277 на указанном SHA.
- Это решение отменяет прежний проект T104 с двумя каналами и постоянным
  журналом системных попыток. Черновик того механизма не включается в продукт.
  T108/T109/T110/T111 продолжают свой согласованный независимый срез; перенос
  уведомлений требует обновлённых plan/contracts и повторного review/analyze.
- F277 также содержит защиту отменённого запуска от отправки. Её результат
  подлежит отдельной проверке на Windows; специфичные поля Mac не копируются
  без проверки фактического Windows-потока. Аудиоалгоритмы не изменяются.
- Результат проверки: Windows не принимает пакеты до готовности обоих workers,
  но преждевременно считает starting принятым автоматическим стартом. Критерий
  T113 — окончательная синхронная проверка актуальности решения до первого
  принятого пакета; отменённый старт не создаёт отправляемого аудио даже после
  перезапуска. Это эквивалент поведения F277, не требование одинаковых manifest.

### Session 2026-09-27

- Q: Какой результат считать конечной целью и как развивать продукт после неё? → A: Пользователь поручил исправить все найденные расхождения, довести Windows до полного соответствия Mac, определить критерии приёмки и затем разрабатывать функции параллельно для обеих платформ. Цель конкретизирована выше без ослабления действующих SC и без разрешения автоматического production deploy.
- Q: Доступен ли физический Windows x64 для заключительной приёмки? → A: Сейчас только Parallels на Mac. Разработка и VM-проверки продолжаются; физические SC и hardware matrix остаются неподтверждёнными до появления оборудования, без замены результатом эмуляции.

Дополнительных продуктовых вопросов не потребовалось: продуктовая граница, владение данными,
поведение, качество, интеграции, отказные сценарии, ограничения, терминология
и критерии завершения определены действующим контрактом и решением владельца.
Выбор конкретных API обновления/окон остаётся технической работой плана;
недостающие аппаратные и release-доказательства не заменяются предположениями.

### Session 2026-09-06

- Q: Первая Windows-версия предназначена для внутренней команды или сразу для внешних клиентов? → A: Сразу для внешних клиентов.
- Q: Нужно ли добавлять отдельную схему разрешений записи для Windows? → A: «Подтверждаю, что нужно сделать абсолютно так же, как в macOS»; отдельная Windows-only схема не согласована.
- Q: Оставлять ли юридическую политику пространства и подтверждения уведомления/согласия условиями запуска записи? → A: Нет; владелец продукта поручил исключить их, перенести юридические формулировки в отдельную работу над соглашением и реализовать приложение. Решение закреплено в Constitution 7.0.0.

### Session 2026-08-23

- Q: Which Windows render-capture scope is in the first slice? → A: Full default render mix
  through WASAPI shared loopback; process-isolated capture is deferred.
- Q: Which minimum Windows versions are in scope? → A: Windows 10 22H2 and
  supported Windows 11 releases; process-loopback-only builds are not a gate.
- Q: Which part remains native versus web? → A: WebView owns the online cabinet;
  native code owns capture, indicator, permissions, local custody, upload and
  diagnostics.
- Q: What does “identical to macOS” mean? → A: Same product semantics, routes,
  states, copy and safety gates; only unavoidable Windows window/tray conventions
  may differ.
- Q: What is the automatic-recording policy? → A: Preserve target-scoped verified
  identity, visible countdown, explicit opt-in and one-action Stop; never record
  arbitrary system audio by default.
