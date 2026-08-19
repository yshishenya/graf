# Review analysis: Пострелизная очистка интерфейса

## Итог

После correctness, frontend UX/accessibility, clean-room и Ponytail review
блокирующих замечаний не осталось. Исправления сохраняют существующие маршруты,
формы, CSRF/auth boundaries и принятую геометрию web/native панелей.

## Исправленные замечания

- Browser-проверка после удаления legacy settings navigation обнаружила поздний
  CSS-owner с двухколоночным `220px 368px` layout. Декларация удалена, а
  regression contract запрещает повторное появление второго layout-owner.
- Account aliases одновременно объявляли outer и inner navigation landmarks.
  Account shortcuts оставлены достижимыми как подписанная группа ссылок:
  текущий пункт семантически отмечен внутри этой группы, а основной current link
  по-прежнему однозначно принадлежит cabinet sidebar.
- Profile popup объявлял ARIA menu без полного menu keyboard pattern. Он
  переведён в нативный disclosure: button сохраняет `aria-controls` и
  `aria-expanded`, а ссылки и logout остаются нативными интерактивными
  элементами; Escape и outside-click по-прежнему закрывают popup.
- Расширенная settings-матрица выявила runtime-падение fair-use страницы из-за
  отсутствующего analytics page-class. Для неё добавлен отдельный fail-closed
  policy: PostHog autocapture/page view и Yandex отключены, потому что review
  status, reason, deadline, appeal state и references чувствительны.
- Исходная `720px` регрессия теперь проверяется в реальном WKWebView по computed
  geometry, а disclosure focus — реальными DOM-событиями. Native inspector
  accessibility copy проверяется через production runtime contract без
  зависимости от форматирования Swift-файла.

## Проверенные, но не принятые упрощения

- Settings layout/content wrappers сохранены: они по-прежнему владеют
  content-width, spacing и fragment-specific classes; их удаление расширило бы
  diff без подтверждённой пользы.
- Точные CSS regression guards сохранены: именно поздний дублирующий owner уже
  прошёл более общие source tests и был найден только rendered-проверкой.
- Отдельный native snapshot/AX framework не добавлен: production runtime
  contract, focused XCTest/build и ручная GRAF Dev проверка покрывают принятую
  геометрию и accessibility без новой зависимости.
- Новая Playwright-зависимость не добавлена. Обязательная computed geometry
  матрица выполнена во встроенном Browser; добавлять отдельный browser stack
  только ради дублирования closeout gate нецелесообразно.

## Clean-room и границы

- Решение использует существующий GRAF design system и native disclosure/link
  semantics; сторонние визуальные assets, разметка и proprietary UX не
  копировались.
- Capture, recording, transcript, AI, deletion, auth, CSRF и tenant/RLS
  поведение не менялись.
- Release, deployment, notarization и full CI остаются за пределами Feature 174.

## Финальный PR review

- В подписанной account group восстановлен `aria-current="page"`; primary
  navigation и account subsection проверяются независимо.
- Outside-click закрывает profile disclosure без кражи фокуса, Escape закрывает
  его и возвращает фокус на trigger.
- Два независимых security diff review не нашли правдоподобных security
  candidates; auth, CSRF, tenant boundaries и fail-closed fair-use analytics
  policy остались неизменны.
- Хрупкие проверки форматирования Swift удалены. Новых зависимостей и
  параллельных layout owners не добавлено.
