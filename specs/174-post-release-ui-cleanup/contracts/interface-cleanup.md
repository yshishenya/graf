# UI Contract: Пострелизная очистка интерфейса

## Responsive cabinet sidebar

- Compact rail — 64px; expanded sidebar — 176px.
- Toggle, navigation, optional update/download и profile targets — 40×40px в compact state и лежат на одной оси с допуском 1px.
- Profile имеет `display` отличный от `none`, visibility `visible`, opacity больше нуля и ненулевой rendered box на каждом supported viewport.
- Compact/expanded toggle занимает один top slot; два клика в одной координате возвращают исходное состояние.
- Main content не имеет horizontal overflow и не перекрывается sidebar.

## Settings ownership

- Outer cabinet sidebar — единственный settings navigation landmark.
- Content templates и HTMX fragments не импортируют и не вызывают inner settings navigation.
- Settings and calendar content используют одну рабочую колонку и standard main padding.
- Routes, forms, active state, CSRF/auth/role boundaries и fragment roots не меняются.

## Sidebar hint

- Видимая подсказка использует существующий rail-tooltip owner.
- Toggle сохраняет актуальные `aria-label`, `title`, expanded state, hover и focus-visible behavior.
- Неиспользуемый второй tooltip data contract отсутствует.

## Native inspector

- Collapsed width — 52px; expanded width — 308px.
- Toggle hit target — минимум 44×44px и остаётся top trailing.
- Accessible label/help отражают следующее действие.
- Inspector content занимает доступную высоту и прокручивается как раньше.
- В реализации нет wrapper, который получает geometry proxy и не использует его.

## Validation matrix

- Browser widths: 640, 720, 980, 981, 1120, 1121, 1280.
- Surfaces: standalone web and embedded.
- States: initial responsive, manually compact, manually expanded.
- Settings samples: overview, form, calendar fragment, billing.
- Native states: compact/expanded inspector at normal and constrained window.
