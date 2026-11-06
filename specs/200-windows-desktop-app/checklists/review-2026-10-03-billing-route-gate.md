# F200 — ограниченный допуск четырёх billing-маршрутов T102

Дата: 2026-10-03. Независимая проверка качества требований до реализации.

## Решение

**SCOPED PASS — unresolved CRITICAL 0 / HIGH 0** для добавления ровно четырёх
точных маршрутов в существующий Windows `billingRoute` и соответствующих
регрессий. Текущие требования, существующие задачи и проверенная связь с issues
достаточны для этого ограниченного продолжения T102. Изменять нормативные
документы, создавать новую задачу или новый issue для него не требуется.

Это не приёмка реализации и не полный PASS T102, T103, SC-002 или F200.
Незавершённые задачи, проверки установленного приложения, платёжной цепочки,
аппаратные, CI и выпускные условия остаются открытыми. Существующая пометка
`HIGH` в описании незавершённой задачи не является новым незакрытым HIGH
замечанием к качеству требований этого среза.

## Проверенный снимок и предел полномочий

- Каноническое дерево: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
- Ветка, проверенная через Git: `codex/200-windows-followup`.
- HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
- Локальный `origin/master`: `f3ec4dd95c3aa68fc7246338bd7c58908d24aee2`.
- `.specify/feature.json` указывает F200, ту же ветку и HEAD,
  `risk_lane=high-risk-product`. Read-only prerequisites подтвердили пути
  spec/plan/tasks. Поле BRANCH в их выводе — имя feature
  `200-windows-desktop-app`, не замена фактической Git-ветки.
- Допуск относится к текущим рабочим нормативным файлам по SHA-256 ниже:
  HEAD сам по себе не описывает чужие незакоммиченные изменения.
- Единственный разрешённый результат записи — этот новый отчёт. Чужие
  изменения сохранены; чекбоксы, код, нормы, tasks, GitHub и Git не изменялись.

Прочитаны действующие правила независимой проверки в `AGENTS.md`, указатели
guidance, применимые разделы `spec-kit-flow.md`, `tracker-policy.md`,
`product-gates.md`, `release-and-validation.md` и Constitution VI / Development
Workflow and Quality Gates. Проверены относящиеся к срезу spec, plan, tasks,
quickstart, parity matrix, bridge contract, анализ и исходная политика маршрутов.
После уточнения основного агента область не расширялась на подробное повторное
ревью неизменённых исторических журналов и несвязанных storage/audio работ.

## Пять действующих чеклистов

Статистика вычислена по фактическим строкам `- [X]` / `- [x]` / `- [ ]`.
Для каждого файла дополнительно проверено число уникальных CHK-ID: повторов
внутри файла нет. Идентичность пункта — `(файл, CHK-ID)`, поскольку номера
CHK повторяются между разными тематическими чеклистами.

| Чеклист | Отмечено | Не отмечено | Уникальных CHK-ID |
| --- | ---: | ---: | ---: |
| requirements.md | 22 | 0 | 22 |
| security.md | 27 | 0 | 27 |
| ux.md | 25 | 0 | 25 |
| audio-capture.md | 24 | 0 | 24 |
| advanced-routing.md | 14 | 0 | 14 |
| **Итого** | **112** | **0** | **112** |

Полный машинный просмотр каталога до создания этого отчёта нашёл 43 Markdown
файла: пять чеклистов выше и 38 analyze/review-документов без строк чекбоксов
(0/0). Это учёт файлов и отметок, не повторное одобрение всех исторических
выводов. Отметки не менялись. `tasks.md` отдельно содержит 93 отмеченные и
26 неотмеченных задач; T102 и T103 не отмечены.

## Фактическое сравнение Mac и Windows

Mac-код прочитан через `git show origin/master`, а не взят из сообщения
основного агента. `DesktopCabinetRoutePolicy.swift:707–739` задаёт точный
`isBillingRoute`; на строках 716–719 присутствуют следующие маршруты:

| Точный маршрут | Mac на указанном master | Windows до изменения |
| --- | --- | --- |
| /billing/storage/preview | billing, разрешён | отсутствует в billingRoute |
| /billing/storage/cancel-selection | billing, разрешён | отсутствует в billingRoute |
| /billing/subscription/early-preview | billing, разрешён | отсутствует в billingRoute |
| /billing/purchases/confirm | billing, разрешён | отсутствует в billingRoute |

Mac `isBillingRoute` требует первый компонент `billing`. Windows сейчас не
нормализует `/desktop/billing` в `/billing`. **Новые `/desktop/billing` aliases
не входят в допуск**; существующая обработка `/desktop` и нормализация URL
остаются неизменными. Не требуется переносить другую нормализацию Mac или
разрешать весь namespace `/billing`.

Mac `DesktopCabinetRoutePolicyTests.swift:8` содержит отдельную регрессию этих
четырёх действий и отрицательных соседних/внешних адресов. Windows
`WebViewRoutePolicy.cpp:93` содержит точный список billing-маршрутов без этих
четырёх; `evaluate:241`, `canStartPayment:337`, `allowsNativeBridge:347` и
`safeRecoveryUrl:385` сохраняют отдельные границы навигации, оплаты, моста и
безопасного возврата. Windows `WebViewRoutePolicyTests.cpp` прочитан: существующие
payment/response/recovery проверки не заменяют регрессии отсутствующих маршрутов.

## Текущий ограниченный междокументный анализ

Исторический `analyze-2026-09-27.md` сообщает CRITICAL/HIGH/MEDIUM 0 и связывает
FR-002/005/006 и SC-002 с существующими T102/T103. Его старый HEAD и старые
количества задач не считаются текущими. `analyze-2026-09-28.md` явно ограничен
уведомлениями T104/T105/T109/T113: его PASS не является billing-доказательством.

Допуск основан на повторной проверке текущих относящихся к срезу требований:

| Проверяемая связь | Фактически осмотренное основание | Вывод |
| --- | --- | --- |
| Паритет маршрутов и владение | spec FR-002/003/005, SC-002; parity matrix строка Cabinet routes; текущий Mac-код | Четыре существующих server-owned действия, не новая бизнес-логика |
| Точная граница навигации | FR-005; security CHK001–003; bridge §9; Windows evaluate/billingRoute | Дополнение точного списка, без wildcard/prefix разрешения |
| Оплата и внешний документ | plan раздел «Оплата»; bridge §9; T102; canStartPayment и payment tests | Сохраняются точный первый provider, HTTPS chain, 900 секунд и отсутствие внешней native authority |
| Возврат после входа | plan раздел «Вход»; bridge §9; T103; safeRecoveryUrl и response/recovery tests | GET-document allowlist отдельный от action allowlist, POST не переигрывается |
| Исполнение и независимая приёмка | Constitution VI / Quality Gates; tasks T102/T103; quickstart пункт T102 | Разрешено ограниченное продолжение существующей работы; закрытие требует собственной проверки |

Противоречий, недостающего владельца существующей задачи, новых решений об
оплате/backend или требований изменить доверительные границы для этих четырёх
точных маршрутов не установлено. Этот раздел — текущий scoped analyze,
а не утверждение о свежем полном анализе всех требований F200.

## Владение задачами и текущие issues

Независимое read-only чтение через GitHub connector подтвердило:

- `yshishenya/graf#7279`: T102, OPEN, автор `yshishenya`, `assignees=null`,
  labels `feature:200`, `priority:P1`, `area:web`, `gate:pr-blocker`.
- `yshishenya/graf#7280`: T103, OPEN, автор `yshishenya`, `assignees=null`,
  labels `feature:200`, `priority:P1`, `area:auth`, `gate:pr-blocker`.
- Автор/владелец репозитория не выдается за назначенного GitHub assignee.
  Основной агент является владельцем исполнения этого ограниченного T102
  среза по текущему поручению пользователя; назначение в GitHub не выдумано.
- T102 владеет платёжной навигацией в `WebViewRoutePolicy.*` / host и её
  регрессиями. T103 владеет auth HTML и безопасным возвратом; сохранение его
  действующих ограничений проверяется здесь, но его работа не закрывается.
- Issues уже существуют: ни дубликаты, ни изменение назначений/статуса, ни
  повторный taskstoissues с внешней записью для данного среза не нужны.
  Частичная будущая связь — `Refs`, не `Fixes`/`Closes`.

## Обязательные границы следующего изменения

1. Добавить только четыре точные строки из таблицы в существующий
   `billingRoute`, с регрессиями в существующем Windows route-policy test.
   Не менять server/business/payment/backend логику, HTTP method/body,
   нормализацию, provider список, сроки или bridge capabilities.
2. Для каждого маршрута проверять `allow + billing` только на доверенном
   origin. Лишний child, похожий suffix, percent-encoded путь, traversal,
   двойной slash и `/desktop/billing/...` не становятся разрешёнными.
   Сохранять существующее сравнение scheme/host/port, включая HTTPS default
   port, без новых исключений для чужого origin.
3. Внешние документы и frames никогда не получают native bridge, nonce,
   native bootstrap, локальные данные или cookie extraction. Уже существующая
   ограниченная payment chain остаётся непривилегированной; не вводить
   произвольный начальный provider или новое платежное состояние.
4. Для каждого из четырёх action routes `safeRecoveryUrl(url, "GET")` и
   `safeRecoveryUrl(url, "POST")` должны возвращать пустую строку. Не добавлять
   действия в безопасный GET-document allowlist и не воспроизводить POST.
   Регрессии должны удерживать прежние разрешённые страницы billing/detail.
5. Проверить новые позитивные и отрицательные регрессии после изменения и
   сохранить существующие payment/response/bridge проверки. Допуск требований
   не заменяет последующее source review, тесты или необходимые runtime gates.

Нарушение любой из этих границ выходит за данный PASS и требует нового анализа
до реализации соответствующего расширения.

## Что не является доказательством реализации

В осмотренных Round 212 записях `validation-2026-10-02.md:4750–4754` отражены
portable CTest 35/35 PASS и native Windows CTest 36/36 PASS. Основной агент также
сообщил, что это результаты до любых route changes. Рецензент их не запускал;
это исходное состояние до исправления, не успешные тесты новых маршрутов.
Полная VS сборка в записи отдельно ограничена предыдущим test TU.

Здесь не выполнялись runtime, build, тесты с исполнением продукта, microphone,
платежи, GitHub mutation, commit или изменение нормативных документов.
Разрешена следующая ограниченная локальная реализация, но не принят весь T102.

## Точные хеши осмотренных нормативных файлов

SHA-256 вычислен по байтам текущих рабочих файлов, не по одному HEAD.
Пути ниже относительны каноническому дереву; feature-пути — внутри
`specs/200-windows-desktop-app/`.

| Файл | SHA-256 |
| --- | --- |
| .specify/memory/constitution.md | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |
| spec.md | d778aa44725911288331beeddc5a2293333bf2fb39ab93e2087a471cdb4f1c0f |
| plan.md | 34e64befcd775c85ee524a8d0e097d7d08805545cec92966bfdbf98d446f71cc |
| tasks.md | 76c91845c3ce5da964351cca95b027562190bbc0fcb9f76b7159d0d021261287 |
| quickstart.md | 9946be5c60a192c2fcb92d7c8db1419827ff757fea8c13d40b9023b949ce1d59 |
| parity-matrix.md | 72c9b6556a4d18a3b6549322b44f02ff15959d8c2eb90f00d4a982ed280a24ab |
| contracts/windows-native-web-bridge.md | 127356a14df140364ce619554bcc42cab03286262065afa40c1fcdb73ac51ff4 |
| checklists/requirements.md | 91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55 |
| checklists/security.md | 50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9 |
| checklists/ux.md | 1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801 |
| checklists/audio-capture.md | 4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd |
| checklists/advanced-routing.md | bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12 |
| checklists/analyze-2026-09-27.md | eba3e7b7d85e000ab2ba6f38cca3719b57c55dabebd217ae3467dc5c7e7d5105 |
| checklists/analyze-2026-09-28.md | 59b369289c8c12069050159229597295365b62a816438cf74dbc83f6f3e2844a |

## Точные хеши источников сравнения

| Источник | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Web/WebViewRoutePolicy.cpp | 0ef91adfc500a1fbe63a4da33727d336ce13c2146f254941c502e6ccc638442e |
| apps/windows/RecApp/Web/WebViewRoutePolicy.h | 484164af5f6bf4cd4082705288ac35ba646579b0c89b42200eac9d6c9162c258 |
| apps/windows/Tests/GrafWindowsContractTests/WebViewRoutePolicyTests.cpp | 82b9b01e3f13c3748e6275a90161f158b490722ce5323a053d53db42e8580e16 |
| origin/master:apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift | a0688ae25b0d25ddc2329bf50ed58069eb1148f5c20e28930082ed4a3cd5c1ea |
| origin/master:apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift | 719dbbb0d0dbc63bd1752a1a6b3455cce2dc6e35bb11c0ab2da7b6d60221e7f9 |

Mac Git blob IDs соответственно:
`385f6e26a9408a3806c00a10504dd6b397fcb1dd` и
`f51806c9df56355f1a12f2b2fd9499dad22819a8`.

Для полного исходного каталога 43 checklist/analyze/review файлов SHA-256
манифеста равен `69bf9d1f6426e2e3c3cefd947bebeda197c493854d4794b61b5c653610a601e3`.
Алгоритм: имена `.md` отсортированы лексикографически; для каждого записаны
`имя + NUL + sha256(байты файла) + LF`; SHA-256 взят от объединения этих записей.
Новый отчёт в исходный манифест не входит и не содержит checkbox items.
