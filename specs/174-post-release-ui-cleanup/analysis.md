# Review analysis: Пострелизная очистка интерфейса

## Итог

После correctness, frontend UX/accessibility, clean-room и Ponytail review
блокирующих замечаний не осталось. Исправления сохраняют существующие маршруты,
формы, CSRF/auth boundaries и принятую геометрию web/native панелей.

## Исправленные замечания

- Browser-проверка после удаления legacy settings navigation обнаружила поздний
  CSS-owner с двухколоночным `220px 368px` layout. Декларация удалена, а
  regression contract запрещает повторное появление второго layout-owner.
- Account aliases одновременно объявляли outer и inner navigation landmarks и
  два `aria-current="page"`. Account shortcuts оставлены достижимыми, но теперь
  это обычная подписанная группа ссылок с визуальным `is-selected`; единственная
  основная навигация и единственный current link принадлежат cabinet sidebar.
- Profile popup объявлял ARIA menu без полного menu keyboard pattern. Он
  переведён в нативный disclosure: button сохраняет `aria-controls` и
  `aria-expanded`, а ссылки и logout остаются нативными интерактивными
  элементами; Escape и outside-click по-прежнему закрывают popup.
- Расширенная settings-матрица выявила runtime-падение fair-use страницы из-за
  отсутствующего analytics page-class. Для неё добавлен отдельный fail-closed
  policy: PostHog autocapture/page view и Yandex отключены, потому что review
  status, reason, deadline, appeal state и references чувствительны.
- Swift source contracts ограничены конкретными view bodies и порядком
  layout modifiers, поэтому больше не принимают совпадение из постороннего view.

## Проверенные, но не принятые упрощения

- Settings layout/content wrappers сохранены: они по-прежнему владеют
  content-width, spacing и fragment-specific classes; их удаление расширило бы
  diff без подтверждённой пользы.
- Точные CSS regression guards сохранены: именно поздний дублирующий owner уже
  прошёл более общие source tests и был найден только rendered-проверкой.
- Swift source contract сохранён вместе с native interaction evidence: hosted
  AX/layout harness в этом срезе потребовал бы новую инфраструктуру, а текущая
  комбинация точного source guard, focused XCTest/build и ручной GRAF Dev
  проверки покрывает исходную регрессию.
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
