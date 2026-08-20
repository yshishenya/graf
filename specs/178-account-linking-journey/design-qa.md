# Design QA — Feature 178

## Evidence

- Source direction: выбранный пользователем mockup «Один профиль — все способы
  входа», сохранённый вне репозитория.
- Browser-rendered captures: два wide 1280 × 720 и четыре состояния 390 × 844,
  сохранённые вне git без реальных пользовательских данных.
- Reviewed states: confirmable preview, actions после внутренней прокрутки,
  expired intent, re-auth и billing blocker с recovery action.

## IA result

Mockup дал понятную модель «сейчас → после», но реализация делает путь короче и
точнее:

1. Сначала сообщает итог: один основной профиль, все подтверждённые способы
   входа и отдельные пространства.
2. Затем показывает сравнение «Сейчас / После подключения» без внутренней
   терминологии и ложного обещания смешать данные.
3. Отдельно и до CTA сообщает, что сохранится и почему потребуется повторный
   вход.
4. Редкие детали находятся в disclosure, а настоящий blocker заменяет CTA на
   конкретное безопасное действие.
5. Secondary action описывает пользовательский результат — «Оставить профили
   раздельными» — вместо технической отмены.

## Visual QA

- Typography and hierarchy: один H1, короткий lead, H2 для результата и H3 для
  blocker; технические IDs и provider subjects не отображаются.
- Layout: wide comparison использует две равные карточки; на 390 px они
  складываются в одну колонку без горизонтального overflow.
- Actions: primary CTA заметен, secondary не конкурирует с ним; в blocker state
  остаётся одно существующее recovery action и безопасный выход.
- Status: neutral, warning и danger используют существующие GRAF tokens; цвет
  не является единственным носителем смысла.
- Accessibility: логичный heading order, native disclosure, видимый focus,
  полноценные button/link labels и keyboard-reachable actions сохранены.
- Brand distance: не добавлены чужие assets, provider icons, layout-клон или
  новая design dependency; используются текущие tokens и cabinet primitives.

## Findings

После исправления верхней IA, duplicate email copy, mobile action ordering и
blocker recovery на визуальных состояниях не осталось подтверждённых P0–P2.
Финальный независимый UX review дополнительно нашёл и закрыл continuity sidebar
между страницами и конфликт Escape: первое нажатие закрывает меню профиля, а не
два уровня интерфейса одновременно.

final result: passed
