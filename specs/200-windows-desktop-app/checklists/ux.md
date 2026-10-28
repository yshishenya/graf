# UX Checklist: Windows desktop-приложение GRAF

**Purpose**: Проверить требования к parity с macOS, нативному indicator/Stop,
permissions, automatic recording, accessibility, localization и degraded copy.
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md), [windows-desktop-contract.md](../contracts/windows-desktop-contract.md)

### Независимая проверка требований 2026-09-06

Проверены изменения spec/plan от 2026-09-06 относительно Constitution 6,
принципы II и VII. CHK010–CHK013 и CHK020 обновлены и проверены как требования
с учётом research.md, решение 8, и data-model.md, §9. Остальные прежние отметки
не означают повторной проверки реализации. Старые формулировки US5, Phase 5,
quickstart §7, parity-matrix и ux-evidence не подтверждают новое поведение:
приоритет имеет датированное уточнение и Constitution 6.

CHK023 повторно проверен после явного уточнения совместимости в spec.md:
неоднозначность снята, проверка полноты требований пройдена (23/23).
Ни одна отметка здесь не подтверждает работу WinUI, физического Windows x64, доступности или
подписи пакета. Эти доказательства остаются в T070/T071/T063/T084; T080–T084 и
статусы реализации этим обзором не закрываются.

## Product parity и ownership

- [X] CHK001 Parity matrix перечисляет каждое macOS recording state/action, permission state, custody state и cabinet route, а для Windows указывает same meaning и допустимое native convention difference. [Completeness, Spec §FR-002, §SC-002]
- [X] CHK002 Web cabinet reuse явно отделён от native-only capture controls, чтобы Windows не получил вторую meeting-list/detail/settings UI. [Consistency, Spec §FR-003]
- [X] CHK003 Copy для shared-loopback scope прямо сообщает, что записывается общий микс выбранного render endpoint, а не только звук одного приложения. [Truthfulness, Spec §Context and goal]
- [X] CHK004 Состояния idle/ready/checking/starting/recording/paused/degraded/stopping/finalizing/saved/queued/uploaded/blocked/failed имеют короткие русские названия и recovery action. [Clarity, Contract §Session transitions]

## Indicator и управление

- [X] CHK005 При active capture persistent native strip содержит state, source scope и one-action Stop вне зависимости от WebView, focus, minimize или network. [Completeness, Spec §FR-015]
- [X] CHK006 Tray/background surface сохраняет читаемый state и Stop, а repeated Stop не создаёт вторую finalizer или двусмысленное состояние. [Recovery, Contract §Indicator and accessibility]
- [X] CHK007 Native indicator является источником capture truth и не может быть скрыт/удалён изменением DOM или сообщением WebView. [Ownership, Contract §Indicator and accessibility]
- [X] CHK008 Pause/Resume copy объясняет privacy semantics, включая отсутствие raw microphone fallback и сохранение timeline/reference. [Clarity, Contract §Session transitions]
- [X] CHK009 Permission denial, endpoint missing, clock failure, protected audio, disk full и WebView unavailable имеют разные понятные причины, а не общий «что-то пошло не так». [Coverage, Spec §Edge Cases]

## Automatic recording

- [X] CHK024 Определены ли независимость фонового старта от видимости кабинета, подготовка отдельного индикатора/Stop до захвата и отказ при невозможности его показать? [Completeness, Spec §US5/AC4, Plan §Phase 5]
- [X] CHK025 Однозначны ли начало слежения с starting, продолжение по той же проверенной identity, пороги 2/15/600 секунд, правила повторных/старых снимков и независимость ручной записи? [Clarity/Recovery, Spec §US5/AC5–6, Plan §Phase 5]

Уточнение 2026-09-06: исторический CHK013 читается с отменой правовых условий
Constitution 7, зафиксированной в security.md CHK024/CHK025. Правовая политика
и согласие не являются текущими условиями записи.

- [X] CHK010 Для «Спрашивать» определены видимый восьмисекундный таймер, немедленное «Записать сейчас», подавляющее текущую запись «Не записывать» и «Запомнить выбор»: явные действия с галочкой сохраняют соответственно «Всегда»/«Никогда», без неё настройка не меняется; истечение таймера запускает текущую запись при выполнении условий и никогда не сохраняет выбор. [Completeness, Spec §Уточнение 2026-09-06, Research §8, Constitution II]
- [X] CHK011 Настройки перечисляют подтверждённые приложения и для каждого показывают ровно одно обратимое значение «Всегда»/«Спрашивать»/«Никогда», по умолчанию «Спрашивать» для новой установки/приложения. «Для всех приложений» применяется только к известным приложениям; «Разные» не является четвёртым состоянием. Идентичность и область захвата объяснены без обещания изоляции звука. [Clarity, Spec §FR-016, Research §8, Data model §9]
- [X] CHK012 Неизвестное приложение, обычное воспроизведение, неподтверждённая встреча, отсутствие разрешения/устройства и подавление не разрешают автозапуск. «Всегда» обходит только вопрос; «Никогда» не запускает запись и не показывает вопрос. Истечение видимого таймера в «Спрашивать» не ошибочно отнесено к запрещённым стартам. [Safety, Spec §FR-016, §SC-007, Research §8, Constitution II]
- [X] CHK013 Трёхрежимный выбор принадлежит клиенту и не требует сети, серверного разрешения или acknowledgement. Общая политика записи/согласия, подтверждённая встреча, разрешения, локальное хранилище, подавление, видимый индикатор и Stop сохранены; разрешённый ручной Record независим от выбора автозаписи. Удаление старого серверного контракта требует ранее выпущенного совместимого клиента и не входит в этот срез. [Ownership, Spec §Уточнение 2026-09-06, Research §8, Constitution II]
- [X] CHK023 Совместимость определена явно: старый `alwaysRecordTarget_` только в памяти; глобальные HKCU `assisted_auto_start`/`prompt_before_recording` не мигрируют в выбор приложения. Отсутствующее/повреждённое значение даёт «Спрашивать» (`Ask`), перед сохранением проверяется точный enum, ошибка записи не выдаётся за успешную смену настройки. [Compatibility, Spec §Уточнение 2026-09-06, Research §8, Data model §9, T082, Constitution II]

## Accessibility, localization и layout

- [X] CHK014 Keyboard-only flow имеет видимый focus для Record/Pause/Resume/Stop, permission recovery, tray action и prompt choices. [Accessibility, Spec §SC-009]
- [X] CHK015 Screen reader получает accessible name/description и state announcement для indicator, Stop, degraded reason и upload/custody state. [Accessibility, Contract §Indicator and accessibility]
- [X] CHK016 High Contrast, 200% DPI, narrow window, reduced motion и system theme сохраняют читаемость, target size, focus и отсутствие горизонтального overflow. [Coverage, Spec §SC-009]
- [X] CHK017 Active/paused/degraded/failed различаются текстом, icon/shape или accessible state, а не только цветом. [Clarity, Spec §SC-009]
- [X] CHK018 Русские тексты native shell согласованы с macOS/web copy, не раскрывают технические секреты и не обещают невозможную process isolation. [Localization, Spec §FR-002, §FR-021]
- [X] CHK019 Offline, auth-expired, runtime-missing и upload-pending состояния не маскируются под нормальную встречу и предлагают действие в текущем контексте. [Truthfulness, Spec §US1–US3]
- [X] CHK020 Проверка сходства с утверждённым эталоном охватывает нативную панель, tray, первый запуск, разрешения, настройки, вопрос автозаписи, ошибки и границу кабинета; действия, состояния, русский текст и расположение сравниваются с текущим GRAF macOS. Буквальные функциональные подписи и наблюдаемое Krisp UX/UI/IA допустимы без требования визуально отличаться; отклонения обоснованы доступностью, локализацией, приватностью, безопасностью или правдивостью. Код написан независимо, права на сторонние ресурсы/шрифты/значки/логотипы подтверждаются до выпуска; извлечённые ресурсы, чужой код, частные API и неправдивые юридические/маркетинговые заявления запрещены. [Design gate, Spec §Уточнение 2026-09-06, Constitution VII]
- [X] CHK021 Quit/close/relaunch during capture объясняет, что будет с локальным пакетом, и не оставляет пользователя без Stop или без custody status. [Recovery, Spec §Edge Cases]
- [X] CHK022 UI не требует WebView route для критического Stop, permission recovery или локальной сохранности записи. [Ownership, Spec §FR-004, §FR-015]


### Независимая проверка фоновой автозаписи 2026-09-06

PASS — CHK024/CHK025, только требования текущего среза T081/T082.
По `$speckit-analyze` сверены Constitution 7.0.0, US5/AC4–6, Phase 5,
quickstart §2, data-model §9 и текущий срез tasks.md: блокирующих пробелов нет.
Согласованы скрытая подготовка существующего CompactOverlay с Stop, фактический
показ до захвата и отказ при невозможности показа; слежение с принятого
`starting`, та же точная проверенная идентичность между процессами, пороги
свежести/подтверждённого отсутствия/нет положительного подтверждения 2/15/600
секунд, повторы и нарушение порядка снимков, независимость ручных Record/Stop.
Прежние отметки, включая CHK013 с соседним уточнением Constitution 7, сохранены.
Это проверка требований в `high-risk-feature`, не реализации: код, тесты,
сборка, VM и частные данные не проверялись. Каталог и миграция предпочтений
не оценивались; T081/T082/T084 этим обзором не закрываются.
