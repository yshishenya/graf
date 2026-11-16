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
4. **Given** одна запись или группа записей в очереди имеет отказ, для
   которого актуальный Mac предлагает обратиться в поддержку, **When**
   пользователь явно выбирает это действие, **Then** Windows отправляет
   только допустимые диагностические метаданные и показывает подтверждённый
   номер. Если запрос принят, но ещё не передан в поддержку, номер остаётся
   доступным после перезапуска и действие проверки использует тот же номер.
   При потере ответа без номера приложение сообщает, что результат неизвестен,
   и сохраняет копирование безопасной сводки выбранной группы. Оно не
   повторяет отправку автоматически. Другой пользователь того же пространства
   не видит номер и не может применить результат исходного обращения.
5. **Given** обращению уже присвоен номер, **When** пользователь повторно
   проверяет синхронизацию, в том числе после перезапуска, **Then** Windows
   показывает состояние того же обращения и не отправляет отчёт заново.
   Если передача в поддержку ещё не подтверждена, номер и копирование
   остаются доступны, а интерфейс не сообщает об успешной передаче.
   При смене пользователя или пространства поздний ответ не обновляет
   текущий экран.

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
4. **Given** активная запись и достоверно отключился только выбранный
   микрофон, **When** тот же системный источник остаётся исправным,
   **Then** GRAF показывает ограниченное состояние, сохраняет уже принятый
   звук и продолжает системную дорожку той же записи до Stop. Он не начинает
   новый захват микрофона. После Stop результат явно неполный, доступен
   локально, а пользователь может заново выбрать микрофон.

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
  Экспорт использует нативный выбор папки и имени внутри окна кабинета.
  Новый файл сохраняется без перезаписи; явная замена привязана к конкретному
  файлу. Отмена, конфликт и ошибка оставляют данные и понятный следующий шаг.
  Право сохранить и восстановить фокус ограничено актуальным исходным
  документом, окном и запросом. См. [контракт T123](contracts/windows-export-save.md).
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
  authority. Only typed `request_app_quit`, `local_recording`, `visible_recordings`, `app_appearance`,
  `native_settings`, `delete_selection`, `request_app_update`, `calendar_join`
  and cancellation-only `calendar_join_cancel` requests are accepted, each on its
  exact approved route with its own payload/capability checks; no web
  acknowledgement establishes capture, upload or deletion truth.
  Local access MUST also match the current document, cookie and native local
  scope; a session fingerprint or document hint alone MUST NOT establish the
  currently active workspace or network-confirmed identity.
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
  Для нового Windows-микса `canonical-mix.v1` нормированные системный
  и очищенный микрофонный отсчёты имеют равный вес 0,5, как в утверждённом
  GRAF Dev macOS. Системный сигнал до смешивания не изменяется.
  Приватная пауза по действующим правилам подавляет исходный микрофон
  до AEC, без повышения веса системного звука. Неконечный выход AEC
  не выдаёт новый пригодный блок.
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
- **Start-owner recovery (FR-012/FR-013/FR-014)**: Before accepting the first
  audio block, Windows MUST durably preserve the recording's initial ownership:
  confirmed user/workspace, proven signed-out, or unresolved authentication.
  An unavailable account check MUST NOT be mistaken for signed-out or prevent
  local offline recording; unresolved ownership grants no assignment/upload.
  Recovery
  MUST preserve that original binding, not substitute the account active after
  restart. Existing packages without proven ownership MUST remain preserved;
  absence of a queue row or account fields MUST NOT authorize reassignment,
  automatic upload or the ordinary `confirmUnowned` action. This does not add a
  user confirmation dialog or require connectivity for local recording. A
  storage acknowledgment failure MUST prevent audio admission and a normal
  saving claim, without deleting existing artifacts. The carrier and its
  crash-safe transitions belong to the scoped T116 plan; this requirement does
  not itself authorize a new persistent format or weaken short/delete fences.
- **FR-013**: The Windows queue MUST write the local v4 ledger and read v2/v3/v4
  (the historical filename remains `desktop-upload-queue.v2`), preserving local
  identity, server truth, accepted ranges, retries, retention and conflicts.
  Persisted access and same-session local scope MUST preserve Mac offline access
  after restart; a new network lookup MUST NOT be a prerequisite for that access.
  Malformed legacy ledgers retain existing isolation rules; protected payload
  refusal preserves artifacts and blocks unsafe effects, never an empty queue,
  silent downgrade or fallback to a peer slot that omits newer access truth.
- **FR-014**: Upload MUST go only through existing GRAF desktop APIs; the client
  MUST never send audio directly to MediaScribe or store MediaScribe credentials.
  Upload MUST resume after launch, activation, auth recovery, network recovery,
  wake and scheduled retry without the WebView route being open.
- **FR-015**: Active capture MUST have a persistent native visible status and a
  one-action Stop reachable from the main shell and the Windows background/tray
  surface. WebView failure, minimization or focus changes MUST NOT hide Stop.
  On Windows, explicit F6 from the active main window MUST focus the available
  notification card or native Stop, including when keyboard focus is inside the
  cabinet. It MUST NOT start or stop recording. An outdated focus request MUST
  NOT activate GRAF or a replacement surface after deactivation or target change.
  Escape within an explicitly focused card dismisses that card and restores the
  prior focus when still valid and permitted by the OS; Stop remains available.
- **FR-016**: Target-scoped automatic recording MUST use verified Windows target
  identity, explicit reversible settings, the existing countdown/prompt actions,
  capture prerequisites, visible indicator and Stop. It MUST NOT infer a target
  from arbitrary process names or start for arbitrary system/media playback.
- **FR-017**: Endpoint change, sleep/wake, audio-service interruption and
  protected-audio limitation MUST transition through explicit states with
  metadata-safe reason codes and recovery action. Silent cross-device continuation
  is forbidden for the first release.
  Продолжение системного звука допустимо только при подтверждённой потере
  фактически активного микрофона (явно выбранного или разрешённого
  по умолчанию при старте) в уже начатой записи, когда тот же системный источник
  и его временная шкала остаются достоверными. Это явное ограниченное
  состояние без замены устройства и без нового захвата микрофона.
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
  Для первого публичного x64-выпуска по T124 выбран прямой MSIX с сайта GRAF
  через системный App Installer (решение владельца 2026-11-12).
  Правила T112 сохраняются: только ручное обновление после явного действия,
  без начала установки при записи или незавершённом сохранении и без
  автоматического либо случайного понижения версии. Публичный `.appinstaller`
  не включает `OnLaunch`, `AutomaticBackgroundTask` и `ForceUpdateFromAnyVersion`.
  Утверждённое легальное имя издателя — «ИП Шишеня Ян Александрович».
  Оно не задаёт ещё не полученный CA-verified Subject (имя в сертификате,
  проверенное удостоверяющим центром). Владелец GRAF / оператор выпуска
  утверждает точные параметры пакета и канала до публичной производственной
  сборки по [порядку T124](release-execution-plan.md#как-принимаем-публичную-поставку-t124).
  Решение не подтверждает готовность публичной подписи и не вводит получение
  сертификата как новое предварительное условие разработки; существующие
  независимое ревью требований и выпускные проверки сохраняются.
- **FR-021**: Native diagnostics and committed evidence MUST contain only bounded
  metadata: version, platform, state, safe reason code, counts, durations and
  redacted device identity. They MUST NOT contain raw audio, transcript text,
  credentials, cookies, signed URLs, private meeting content or live private
  paths.
- **FR-022**: Windows deletion and local purge behavior MUST use the existing
  GRAF lifecycle truth and MUST acknowledge local purge only after deletion,
  tombstone or cryptographic unrecoverability has been verified.
  Persisted non-owner access MUST block content, including active consumers and
  upload, without granting deletion/purge authority; later access updates MUST
  NOT clear an accepted receipt or a newer revocation via a stale upload result.

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
- **UploadCustodyItem**: queue projection over the v4 ledger (v2/v3 readable),
  with local identity, persisted nullable access truth, retry owner/action,
  accepted ranges, retention and one last authenticated local-session context.
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

Контракт v5 записей сохраняется. Локальная очередь получает узкое расширение
v4 T088 с чтением v2/v3/v4; совместимость прежних очередей является продуктовым
форматом, не запасной реализацией. Серверные и crypto-envelope схемы не меняются.
Удаление серверных полей и API работающего macOS-клиента вне этого среза;
Windows не расширяет их.
Трассировка удаления и проверки: T080–T084, quickstart.md и validation-2026-09-06.md.

## Clarifications

### Session 2026-11-16 — T116: штатный FFmpeg

- **Q:** Сохранять полный учёт и затирание внутренних выделений FFmpeg либо
  подключить штатную библиотеку с отдельным измерением памяти?
  **A:** Владелец выбрал обычный FFmpeg: закончить приложение, отдельно измерить
  расход памяти и честно зафиксировать ограничение. Собственные буферы GRAF
  сохраняют предел 64 MiB и обязательное затирание; файлы остаются защищёнными.
- Для FR-009/012/013/017/018, SC-003/004/005/006 применяется
  [контракт §5.1](contracts/windows-protected-local-custody.md#51-штатный-ffmpeg--решение-владельца-от-2026-11-16).
  Общий расход процесса может быть больше 64 MiB; затирание всех внутренних
  копий библиотеки не гарантируется. Измерение короткого тестового процесса
  около 39 MiB не доказывает память длительной записи или одного FFmpeg.
- Отдельная доработка allocator FFmpeg больше не является условием T116.
  Не ослабляются шифрование файлов, лимиты GRAF, качество/длительность звука,
  сохранность prefix, Stop, обработка отказов и установленные проверки T118.

### Session 2026-11-12

- Q: Какой канал выбираем для первого публичного выпуска Windows? → A: «Установщик с сайта GRAF — рекомендую для первого выпуска». Принят прямой MSIX с сайта GRAF через системный App Installer; первый выпуск — x64, ARM64 требует отдельной приёмки SC-010.
- Q: Какое официальное легальное имя издателя утверждено? → A: «ИП Шишеня Ян Александрович». Это владелец будущей идентичности издателя, а не выданный Subject сертификата; технические параметры до публичной сборки утверждает владелец GRAF / оператор выпуска по порядку T124.

### Session 2026-11-10 — T126: потеря выбранного микрофона

- **FR-002, FR-009, FR-015, FR-017, FR-018, SC-004.** Основание —
  утверждённый паритет и [сценарий F293](https://github.com/yshishenya/graf/blob/73fdf67f9bec371468093a6bc55410b06c1f4eab/specs/293-interface-hardening/spec.md#L56).
  После достоверного отключения именно выбранного микрофона сохраняются
  та же сессия и достоверные отсчёты обоих источников до границы.
  После неё принимаются только новые пакеты прежнего системного источника.
  Событие чужого устройства ничего не меняет.
  Продолжение не применяется к незавершённому запуску, потере системного
  источника, сомнительной причине, сбою часов или хранения. Здесь
  «выбранный» по явному решению владельца от 2026-11-12 означает
  фактически активный микрофон, проверенный и привязанный при старте этой
  сессии: явно выбранный пользователем либо разрешённый по умолчанию.
  Это заменяет прежнее ограничение T126 только явно выбранным входом.
  Смена устройства по умолчанию и ошибка перечисления сами по себе не
  доказывают отключение и не требуют прерывать исправный захват. Свежая
  проверка относится к прежнему активному endpoint, а не к новому default.
  При независимо выявленном отказе без доказательства T126 выполняется
  обычное прерывание; позднее событие его не отменяет.
- Отметка об ограничении появляется при обработке подтверждённого
  события; индикатор и Stop остаются доступны. Повторное подключение
  микрофона, смена устройства по умолчанию и повтор Resume не возобновляют
  захват микрофона в этой сессии. Если отключение произошло на паузе,
  её защита сохраняется до Stop; накопленный микрофон не возвращается.
- Не терять принятые достоверные отсчёты до границы. После неё пустой
  вклад микрофона не выдаётся за записанный микрофон, а недостающий
  системный звук не дорисовывается. Длительность и целостность проверяются
  по файлам и временным меткам, включая отдельные системные сигналы до
  и после границы. Завершение помечает результат как ограниченный и
  сохраняет его по действующим правилам локальной защиты и восстановления;
  неполный результат нельзя отправить автоматически или вручную.
  Повторный выбор микрофона — после Stop.

### Session 2026-11-10 — T125: расположение главного окна Windows

- **FR-002, FR-015, SC-009.** По поведению GRAF Dev
  `73fdf67f9bec371468093a6bc55410b06c1f4eab` и F293 FR-008
  GRAF Windows после штатного выхода и нового запуска восстанавливает
  последний пригодный размер и положение главного окна в обычном состоянии.
  Это предпочтение текущего профиля Windows: оно не синхронизируется между
  компьютерами и работает без входа, сети и WebView2.
- При неизменном экране, рабочей области и масштабе полностью помещавшееся
  окно возвращается к тому же видимому прямоугольнику (допуск один физический
  пиксель). Окно, сохранённое на границе экранов, ограничивается рабочей
  областью выбранного экрана.
  При смене масштаба сохраняется логический размер, насколько позволяет
  рабочая область. Если прежнего экрана больше нет, окно центрируется на
  основном экране с сохранённым логическим размером, ограниченным его
  рабочей областью. При изменении рабочей области положение и размер
  ограничиваются так, чтобы весь прямоугольник был доступен.
- Сворачивание, разворачивание на весь экран и скрытие в трей не стирают
  последнюю обычную геометрию. Новый процесс открывается в обычном состоянии.
  Если значение отсутствует, повреждено или недоступно, сохраняется
  начальное размещение 1080×620 логических точек с ограничением рабочей
  областью. Сбой чтения или сохранения не мешает запуску и управлению записью.
- Системный индикатор и Stop остаются доступны по FR-015; окно не должно
  исчезать за пределами экранов. Поведение крестика, фоновый индикатор,
  окно настроек, WebView, выбор устройств и настройки записи не меняются.
  T108 отдельно проверяет продолжение записи после скрытия и явный выход,
  T097 проверяет общий визуальный результат.


### Session 2026-11-08 — T104: подсказка в панели записи

- **FR-002/FR-015, SC-002/SC-009.** Образец — выбранный новый GRAF Dev:
  «Предлагать запись» управляет отдельной нативной подсказкой в панели
  записи во время актуальной встречи, в том числе без ссылки. «Предлагать
  подключиться» и локальные настройки уведомлений F277 сохраняют свои
  отдельные правила. Тихий режим не скрывает подсказку в панели записи.
- Одна встреча предлагает обычное начало записи с автоматическим
  определением календарного контекста. При пересечении встреч — явный
  выбор события или «Начать запись без связи с календарём». Последний
  выбор запрещает автоматическую привязку для этой записи. Открывать
  ссылку, начинать запись или сохранять решение только по факту показа нельзя.
- Исчезновение/перенос встречи, изменение настройки, устаревание
  запроса, смена сеанса/пользователя/пространства, блокировка и уже
  начавшаяся запись отзывают ранее показанное действие. Отказ календаря
  оставляет доступным обычный ручной запуск, когда он штатно разрешён.
- Если ответ на создание встречи потерян, Windows сверяет, что именно
  эта попытка выбора или отказа была применена к этой записи. Наличие
  встречи само по себе этого не доказывает. Подтверждение доступно только
  исходному владельцу записи с исходного устройства; оно не содержит
  события, участников или названия. Отсутствие подтверждения не меняет
  решение и не уничтожает локальный звук.
- При явном выборе или отказе сервер либо применяет точное решение
  вместе с созданием встречи, либо не создаёт встречу. Повтор той же
  принятой отправки не создаёт вторую встречу и подтверждается даже
  после истечения срока попытки. Чужой выбор, неподтверждённое создание
  и удаление не дают подтверждения. Если после отката сервера строгий
  путь недоступен, звук остаётся локально: Windows не подменяет выбор
  автоматическим сопоставлением.

### Session 2026-11-08 — T097: живая смена контрастной темы Windows

- Когда пользователь меняет контрастную палитру Windows при открытом GRAF,
  уже открытые нативные окна обновляются без перезапуска. Это требуется
  и при смене одной контрастной палитры на другую, даже если выбранный
  в GRAF режим «Светлая», «Тёмная» или «Системная» не изменился.
- Основные действия «Начать запись» и «Остановить запись» остаются
  читаемыми и доступны с клавиатуры. Фон и подпись используют
  предназначенные друг для друга системные цвета. При смене палитры
  остаются прежними фокус, доступность действия и состояние записи.
- Выключение контраста возвращает выбранное оформление GRAF. Отдельной
  настройки не добавляется. Кабинет использует штатные цвета WebView2;
  настройки и поведение macOS не меняются. Это уточнение FR-002/SC-009
  внутри существующей T097, а не самостоятельная функция.

### Session 2026-11-08 — T121: актуальная позиция публичной встречи

- Публичная встреча сохраняет уже достигнутую позицию при смене вкладки
  и отменяет ещё не применённый переход из прежнего адреса. Новый
  явный таймкод, в том числе 0, действует для своего фрагмента. Это
  уточняет F292 FR-018 и T022, реализует F200 FR-002/003/005 и SC-009.
- «Открыть в GRAF», «Войти» и «Начать пользоваться GRAF» используют
  текущий допустимый фрагмент даже до обработки события его смены.
  Общие правила версий, права просмотра и механизмы входа сохраняются.
  [Подробные критерии](t121-public-pending-seek-proposal.md).

### Session 2026-11-07 — T123: нативное сохранение экспорта

- Применён выбранный пользователем актуальный GRAF Dev: выбор папки и
  имени, сохранение под новым именем и отмена происходят внутри
  исходного окна. Отдельное окно не должно возвращать фокус из другого
  приложения. Сервер и общий кабинет остаются источником экспорта.
- Имя, уже занятое другим файлом, не даёт права его заменить.
  Сохранить действующий пользовательский выбор Windows «Заменить»
  только как явное подтверждение для определённого файла; отказ или
  изменившийся файл оставляют исходные данные и позволяют выбрать другое
  имя. Поведение AppKit при показе подтверждения и результат WebKit
  проверяются раздельно; успешную замену в установленном Mac не считать
  доказанной по одному наличию кнопки.
- Ошибка места сохранения должна оставлять ясный следующий шаг. При
  отмене, смене исходной страницы, потере готовности или смене аккаунта
  до начала окончательного сохранения запрос теряет право записи
  необратимо. Старый запрос не выдаёт результат в новую страницу и не
  меняет более новый запрос. Если безопасная операция замены уже начата,
  допускается только её завершение либо восстановление; интерфейс старой
  страницы не активируется. Приёмка — на точном MSIX и GRAF Dev.

### Session 2026-11-06 — T083: обращение по записи

- Применён ранее выбранный пользователем эталон Mac. Поддержка из строки
  очереди не заменяет общую ссылку «Техническая поддержка» и не отправляется
  автоматически. Принятие обращения не меняет права на запись, отправку или
  удаление.
- Отчёт Windows указывает свою платформу и версию ОС. Действующий F114 v2
  не сохраняет Windows-поля и назначает метку macOS. Не отправлять Windows
  под видом Mac: общий приёмник должен поддерживать Windows до включения
  отправки. При несовместимости сохраняется действие копирования; оно
  не считается выполненным сценарием обращения.
- Существующий контракт поддержки Mac сохраняется. Не включаются аудио,
  расшифровки, названия встреч, исходные идентификаторы, пути, журналы,
  файлы или данные входа. Точные сценарии проверки — в quickstart T083.
- Повтор проверки с выданным номером не является новой отправкой.
  Пока общий приёмник не подтвердил передачу, Windows показывает
  существующий номер и состояние ожидания. Если номер ещё не выдан,
  ручной повтор возможен только с тем же исходным отчётом и областью
  пользователя; при невозможности это подтвердить остаётся копирование.
  Требование «одно обращение — одна задача поддержки» проверяет общий
  серверный контур F114, включая одновременные запросы и потерю ответа.
  До этой проверки подключение отправки из Windows не принимается.

### Session 2026-11-04 — T088: подсказка видимости и внешняя квитанция

- Пользователь уже выбрал актуальный Mac как образец. Существующий publisher
  `visibleRecordings` переносится без нового пользовательского действия.
  Технический выбор: отдельная строковая команда `visible_recordings` в нынешнем
  allowlist `WebViewBridge::isAllowedWebCommand`, конверт и поля §3 bridge contract,
  точный Mac payload `{"action":"visibleRecordings","version":1,"ids":[]}`.
  Подходящей существующей команды нет; новый enum/универсальный dispatcher не
  нужен. `local_recording` сохраняет ровно `action:open|send|delete` и `id`;
  `delete_selection` для подсказки и внешней квитанции не вызывается.
- Подсказка содержит не более 100 уникальных local IDs последней нативной
  проекции, проверяется по текущему nonce/message_id/маршруту, cookie, аккаунту,
  пространству и поколению авторизации. Она меняет только приоритет в памяти;
  не является полномочием или намерением удаления. Старый документ/аккаунт не
  передаёт полномочия через очередь отложенных сообщений или сетевой ответ.
- Независимый нативный обход не зависит от видимости кабинета и продвигает
  фоновый курсор при повторяющихся приоритетах. Ответ существующего lifecycle
  API проверяется целиком в подтверждённой области аккаунта. Внешняя квитанция
  без прежнего локального delete intent принимается сразу как подтверждённое
  состояние существующей модели, после защищённого commit/readback/adoption;
  до adoption её нельзя публиковать как принятую или разрешать очистку.
  Сама подсказка и приём внешней квитанции не требуют новых server/ledger схем,
  DELETE, purge ACK или разрешения очистки. Персистентный локальный доступ
  отдельно уточняется следующей сессией T088 с локальной queue v4. Это
  конкретизация T088 и FR-006/013/022, не новый task ID и не отметка о выполнении
  T088 или других открытых задач.

### Session 2026-11-04 — T088: персистентный доступ и offline scope

Агентское техническое уточнение исходного требования полного Mac-паритета.
Q/A ниже — структура проектной записи, не фактическая беседа с пользователем
и не его отдельное подтверждение схемы. Local v4, raw safe-code ≤64 и способ
вычисления fingerprint — инженерные предложения в этом scope для Main/reviewer;
пользователь выбрал поведение продукта, а не эти детали реализации.

- Q: Как сохранить Mac-доступ после холодного запуска? → A: В той же защищённой
  очереди хранить nullable bounded raw `access_state` и последний native scope
  с отпечатком сессии. Только `null` и точное `owner` сами по себе не блокируют
  содержимое; `unknown`, `access_revoked`, `stale_device_identity` и другие
  nonowner safe codes сохраняются и блокируют. Scope, deletion и integrity gates
  действуют независимо. `allowed` даёт `owner`, `unavailable` даёт `unknown`
  только записи с meetingId; отсутствие sync-state поля не стирает отказ.
- Q: Что доказывает совпадение session fingerprint? → A: Только ту же native
  сессию для восстановления локальной области, не актуальность online workspace
  и не network confirmedIdentity. Cold offline разрешён при совпадении области
  записи и текущего документа/cookie. Same-cookie переход A→B требует новой
  native проверки области; HTML/hint лишь запускает сверку или отказ. Документ B
  не использует cached A. Выход/смена сессии отзывает старые потребители.
- Q: Каков совместимый формат? → A: Только local `desktop-upload-queue.v4`,
  чтение v2/v3/v4, прежнее имя файла. Protected reads сохраняют старые bytes до
  обычного commit; old v3 reader отвергает v4 при проверке BOTH без выбора
  старого понятного slot. T117 exact-source migration и сохранение originals
  не заменяются upgrade; server/crypto/bridge API и таймер не добавляются.
- Q: Когда новое состояние допускает эффект? → A: Положительное разрешение —
  после полного native ответа, проверки scope/subject/generation, protected
  commit/readback и adoption. Полностью проверенный restrictive answer сначала
  закрывает новые admissions и отменяет playback/upload; upload действительно
  освобождает flight до submit lifecycle-команды. Cancelled result получает ACK
  без применения; после drain новый private candidate проходит commit/readback/
  adoption. Late upload не снимает новый отказ. Receipt, deletion/purge/ACK fences, fair background и Start/Stop остаются.
  Это уточнение существующих FR-006/013/022 и T088, не новый task или приёмка.

### Session 2026-10-22 — безопасная история кабинета T103

- Новых вопросов пользователю нет: FR-002/005/006 и полный паритет уже задают
  результат. Для истории образец — merged Mac F136
  `0648784cf9a5365220e421d77c8eb51e3bea6907`; выбранный F277 остаётся эталоном
  уведомлений. Это уточнение не меняет общий кабинет и не разрешает deployment.
- Назад/Вперёд сохраняют полезную безопасную историю браузера, исключают
  повторную отправку/восстановление небезопасной POST-записи и не выводят метод
  запроса из адреса. Одинаковые URL GET и POST не означают одинаковую запись.
  Нельзя заменить всю историю новыми GET или навсегда выключить навигацию.
- Как в Mac, при отсутствии подходящей безопасной записи назад из просмотра
  встречи допускается новый переход к списку встреч и один безопасный возврат
  вперёд в текущей сессии. Это отдельный путь, не произвольная загрузка URL
  старой формы и не требование сохранить исходный browser entry ID.
- Выход, истечение входа, смена аккаунта/пространства и пересоздание WebView
  не позволяют восстановить полномочия прежней сессии через историю или
  отложенный результат. Отменённый до замены документа переход сохраняет
  действующий документ; настоящий новый документ проходит обычную проверку
  ответа и получает новое поколение/nonce. Same-document изменение не создаёт
  нового документа и не превращает POST в безопасный GET.
- Область, роли, состояния, безопасность, доступность, отказы и критерии
  завершения определены; механизм выбора записи и корреляция событий остаются
  технической работой plan/research. Это не принятие нового history owner,
  нынешних двух отказов Back или всей T103/T088/T097.
- Уточнение после исследования: Windows не переносит исключение Mac по одному
  `controllerTargetURL` при наличии старой формы. Обычная история реальных GET
  сохраняется. Если есть неподтверждённая запись или форма, из встречи доступен
  безопасный возврат к списку с одним новым GET-возвратом вперёд. После принятия
  списка прежняя история очищается, следующие обычные переходы снова образуют
  рабочую историю. Это ограниченное защитное отличие WebView2, не замена всей
  истории новыми загрузками. Старые страницы форм могут исчезнуть из «Назад»,
  но не восстанавливаются скрытно. Cookies, аккаунт, записи и пользовательские
  данные не очищаются. Ошибка очистки не разрешает старую историю; безопасные
  кнопки «Встречи»/повторной загрузки сохраняются. Полная приёмка остаётся открытой.

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

### Session 2026-10-22 — техническая сверка T120 с текущим Mac

- `$speckit-clarify`: новых продуктовых вопросов нет; используется уже
  подтверждённый паритет Mac. На `origin/master`
  `9b286f6d9df01f4b948d7db1673aff99c78635ff` соответствующие writer/FIFO и
  порядок Pause/Resume не изменились относительно образца c8d67c….
- Конец сегмента паузы — ранняя логическая отметка управления, не обещание
  точного времени нажатия, физического ADC кадра или переключения UI. Windows
  фиксирует её на native worker после запроса и до подтверждаемой границы
  потока. Дополнительная тишина допустима; возвращение накопленного до этой
  отметки микрофона — нет. Исходный доверенный pre-Pause участок не меняется.
- Пока надёжная граница не получена, UI остаётся paused/pending и Stop доступен.
  Неуспех ограниченного ожидания не закрывает OPEN и не принимает Resume;
  сохранение CLOSE после принятия по-прежнему best-effort. Никаких новых
  разрешений, диалогов, вычисленных UTC из QPC или послаблений целостности.

### Session 2026-11-06 — T120: устаревшее показание до свежей границы

Пользовательское поведение Mac уже согласовано: пауза сохраняется до
доказанной границы Resume; ничего из периода паузы не возвращается.
Проверка Parallels показала корректно оформленную, но старую пару часов
микрофона с позицией позади уже освобождённых кадров. Это не причина
принимать Resume или немедленно отменять исходное ожидание. Только
свежая достоверная пара с допустимой позицией даёт право продолжить.
Неуспех в пределах исходного срока оставляет паузу и открытый сегмент;
Stop доступен. Новый продуктовый выбор и новые разрешения не нужны.

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

### Session 2026-10-16 — принадлежность записи после сбоя

- Q: Сохранять ли владельца до первого аудиоблока, а старые записи без
  доказанной принадлежности сохранять без отправки и переназначения?
  → A: «Подтверждаю этот порядок восстановления».
- Подтверждённый при начале user/workspace сохраняется до audio admission и
  не меняется при Stop, выходе, новом входе или restart. Доказанное начало без
  входа отличается от утраты сведений о владельце: только первое может
  использовать прежнее отдельное подтверждение назначения текущему аккаунту.
- Недоступная проверка аккаунта не равна выходу: исходная принадлежность остаётся
  явно неподтверждённой, а не автоматически `unowned`. Это не блокирует локальную
  запись без сети и не разрешает последующее назначение/отправку такой записи.
- Файлы, уже потерявшие эту связь, не удаляются и не становятся `unowned`
  для повторного назначения. Их наличие/успешная расшифровка/проверенный sealed
  state не являются доказательством аккаунта. Полноценное восстановление
  использует исходную local identity и прежние deletion/server-truth fences.
- Уточнение относится к существующей T116/#7444. Перед кодом требуется узкий
  план durable carrier, ACK, restart и short/delete переходов, затем независимые
  checklist/analyze gates. Конституция, logical v5/package-state schema,
  сервер, Mac и публичный допуск этим ответом не изменены.

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

### Session 2026-11-04 — T121: переход к общей встрече F292

Уточнение существующих FR-002/005/006/021 и SC-002/006/009, owner T121.
Пользователь уже подтвердил равенство поведения с актуальным Mac; новых
продуктовых вопросов нет. Эталон — master5485b92 и его SharedMeetingHandoff,
DesktopCabinetWorkspace recovery и серверный F292 sharing contract.

- Допустимая внешняя ссылка открывает публичную либо адресную общую встречу
  на настроенном GRAF origin, сохраняет вкладку, позицию и версию записи.
  Она не назначает аккаунт/пространство, не переносит браузерную сессию и не
  разрешает запись, загрузку, удаление либо чтение локального inventory.
- Холодный и повторный запуск используют один ограниченный intent в памяти;
  последний допустимый заменяет прежний. Невалидная ссылка не меняет текущую
  страницу, pending или recovery. Новый допустимый переход начинает загрузку
  даже из прежнего recovery; уже потреблённый intent не оживает после отказа.
- Публичный reader доступен независимо от собственного входа приложения.
  Его серверные права повторно проверяются для reader и каждого media request.
  Summary-only не расширяется до full meeting. Истёкшая/отозванная ссылка и
  отказ адресного доступа не подменяются собственными локальными данными.
  Публичная и адресная страницы общей встречи не получают нативных
  полномочий, в том числе для владельца. Серверные права на аудио и экспорт
  проверяются отдельно; действия в собственном кабинете сохраняются.
- Вход выполняется собственной сессией приложения. Публичный возврат использует
  существующий серверный sealed-cookie continuation без share token в login
  query; адресный возврат сохраняет безопасный локальный путь, workspace,
  media_version и fragment. Поздний возврат отменённого входа не заменяет
  текущую страницу. Без версии открывается выбранная вкладка без перехода
  к прежней позиции. При несовпадении версии старая позиция не применяется;
  используется существующее явное действие общего проигрывателя.
- Нативные поля, маршруты и границы чтения определяет bridge contract §11.
  T106 attribution и T119 calendar join сохраняют собственную область.
  T121 остаётся открытой до независимого review/analyze/issue sync, реализации
  и проверок quickstart; это уточнение само не расширяет runtime allowlist.

### Session 2026-11-07 — T088: подпись приложения в списке сеансов

Уточнение FR-006, SC-002 и задачи T088. По уже согласованному паритету
список сеансов в общем кабинете различает собственный вход приложения
Windows («GRAF для Windows»), собственный вход Mac («GRAF для macOS») и
вход в обычном браузере. Путь завершения сеансов остаётся общим.

Тип клиента и версия служат только для показа. Их отсутствие, подмена или
некорректное значение не дают доступа и не изменяют владельца, привязку устройства,
пространство, срок сеанса, отзыв и правила показа локальных записей.
Прежние записи без надёжных сведений не переименовываются автоматически.
Сигнал приложения обрабатывает только доверенный GRAF, сторонние
провайдеры входа и оплаты не должны получать новый признак.
Обычная регистрация устройства не присваивает подпись Windows-приложения;
браузерный переход оплаты сохраняет подпись браузера.

### T104/B2c.14b — выпуск с исправлением после активации хранилища

Для сохранности записей и безопасного обновления (FR-012/013/022,
SC-005/008) незавершённый выпуск в активированной области нельзя
завершить обычным повтором или запуском прежних образов. Оператор
может применить только новый утверждённый выпуск, работающий с той
же фактической схемой и теми же PostgreSQL, MinIO и Temporal.
Пока не доказаны безопасность хранилища и готовность служб, система
не сообщает об успешном выпуске и не открывает строгую запись.
При обрыве допускается проверка и остановка потребителей, а не
автоматический повтор запуска или потеря истории попыток.

### Session 2026-11-12 — T088/T108/T110: account DOM и Stop

- Существующие FR-006/013/021/022 уточняются для T088: оба DOM-хранилища
  прежнего аккаунта очищаются в actual WebView profile/origin до принятой
  reload/new-account publication, при немедленном отзыве старых capabilities
  и сохранении error/unknown/stale fences. Нормативный результат и границы —
  bridge §6, регрессии сохранности T118/T121; новый task/API не создаётся.
- FR-015 для T108/T110 различает видимый статус и действие Stop:
  starting/recording/paused/degraded — доступен; stopping/finalizing — видимы,
  повторный Stop недоступен. Indicator readiness не равен enabled Stop.
  Нормативная матрица — desktop contract §8; установленная приёмка — T097.
  T125 и ранее уточнённые T126/T120/audio/custody границы не меняются.


### Session 2026-11-16 — T127: предупреждение о локальном месте

Уточнение US1, FR-002/012/015/017 и SC-002/004/009. Это требования к
пользовательскому предупреждению; существующие проверки сохранности обязательны.

- **T127-R01 — сценарий и вид.** До записи, во время записи и приватной паузы
  пользователь видит немодальное текстовое предупреждение при наблюдаемом
  заполнении локального защищённого хранилища от 80%: «Мало места для локальных
  записей. Проверьте свободное место на диске». Текст доступен средствам чтения
  экрана, не требует подтверждения, не перехватывает фокус и не кодируется одним
  цветом. Он не скрывает индикатор и Stop; ошибки сохранения, разрешений,
  приватности и потери микрофона имеют приоритет. Если место освободилось,
  следующее успешное наблюдение ниже 80% убирает предупреждение.
- **T127-R02 — прежняя политика.** Сохраняются лимит 5 000 000 000 байт,
  предупреждение от 4 000 000 000 байт (80%), критическая граница
  4 750 000 000 байт (95%) и резерв min(10 000 000 000 байт, 10% фактической
  ёмкости диска). Учитывается прежний физический объём всего защищённого
  хранилища: скрытые `.custody-v1`, метаданные, удержанные, осиротевшие,
  исторические и временные файлы; это не только удаляемый кэш и не серверный
  тариф. Для фактической группы записи сохраняется отказ при used + peak > 95%
  или available - peak < reserve; peak включает прежнее округление размещения.
  Равенство допустимо, если сама группа помещается. Числа и пределы не уменьшаются.
- **T127-R03 — наблюдение не допускает и не блокирует Start.** Ручной и
  автоматический Start сохраняют общий путь и свежую проверку существующей V5
  factory после reservation/adoption ACK, до запуска аудио. Нулевой запрос о
  месте, последнее предупреждение или его отсутствие не заменяют эту проверку.
  Предупреждение 80%, ожидаемый ответ и ошибка наблюдения не вводят новых
  запретов Record/автозаписи/Pause/Resume/Stop и не создают ложной готовности.
  Прежние отказы фактической записи и требования readiness остаются в силе.
  После освобождения места отрицательное прошлое наблюдение не мешает повторной
  попытке пройти настоящую factory.
- **T127-R04 — честное состояние.** До первого результата показывается
  «Проверяем место на диске…»; при подтверждённой нехватке — «При последней
  проверке было недостаточно места для сохранения. Проверьте свободное место
  на диске»; при иной ошибке — «Не удалось проверить место на диске».
  Последнее наблюдение не является гарантией текущего свободного места или
  сохранности всей будущей встречи. Числовой процент не показывается как точный
  размер файлов: давление при записи может включать ожидаемый пик группы.
  Настоящий отказ сохранения использует прежнее сообщение об ошибке с более
  высоким приоритетом, а не заменяется предупреждением.
- **T127-R05 — работа без задержки интерфейса.** Чтение диска выполняется
  существующим storage worker вне блокировки значений для UI, приоритетны
  Start/Stop и завершение сохранения. Повторные запросы объединяются; при записи
  используется уже вычисленное давление фактических операций, без повторного
  обхода файлов. Показ не зависит от входа в кабинет, HTTP или upload Retry-After;
  обновление использует существующие события запуска, активации и пробуждения
  и доступные плановые события, без новой числовой периодичности или TTL.
- **T127-R06 — сохранность и границы.** Наблюдение не пишет и не удаляет данные,
  не переводит исправного владельца в необратимый отказ, не меняет формат,
  миграцию, очистку, лимиты или полномочия WebView. Ошибки диска передаются
  безопасно, без путей и содержимого записей. Изменение места внешним процессом
  после factory по-прежнему обрабатывают проверки последующих записей и ошибки
  ОС; ранний опрос не резервирует место и не обещает сохранить уже принятые в RAM
  данные при последующем отказе диска.

**Принятые уточнения Main:** отдельный pre-factory probe не нужен, действующая
factory остаётся фактической проверкой допуска; TTL и новый жизненный цикл
не вводятся. Видимое предупреждение требует последующего подключения владельцем
AppMain; один getter не считается завершённым пользовательским результатом.
Независимый [чеклист T127](checklists/t127-storage-warning.md), analyze и связь
задачи с GitHub выполняет Main до допуска к исходникам. Эта авторская подготовка
не изменяет T088/B31 и не отмечает их проверки пройденными.
