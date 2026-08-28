# UI Contract: Playback layout

## Shell geometry

- `.app-shell` задаёт две колонки: sidebar и content; при наличии playback задаёт строки `minmax(0, 1fr) auto`.
- Sidebar занимает обе строки.
- Meeting main занимает content-column и верхнюю строку; только main прокручивается вертикально.
- Playback занимает content-column и нижнюю строку, не использует viewport-fixed координаты.

## Observable invariants

- `main.right == playback.right` с допуском 1px.
- `main.left == playback.left` с допуском 1px.
- `main.bottom == playback.top` с допуском 1px.
- Вертикальный scrollbar main заканчивается на `main.bottom` и не пересекает playback.
- Rail toggle меняет ширину shell-column, но не playback state, source, currentTime или control order.
- Изменение высоты speaker timeline меняет высоту нижней строки и доступную высоту main без overlay.

## Responsive and degraded states

- Standalone narrow shell использует одну content-column; playback остаётся отдельной нижней строкой.
- Desktop-embedded narrow shell сохраняет rail-column и тот же row contract.
- Available, preparing и unavailable playback используют одинаковую grid placement.
- Страница без playback не резервирует пустую нижнюю строку.
- В no-JS narrow режиме navigation, main и playback занимают последовательные строки без пересечения.

## Accessibility

- DOM/focus order playback controls не меняется.
- Playback является именованным region «Воспроизведение записи».
- Keyboard resize, focus-visible и reduced-motion contracts сохраняются.
- Profile menu открывается в browser top layer: его правый край и подменю остаются поверх sidebar, main и playback и не обрезаются overflow-контейнерами.

## Access recovery

- При 401/403/404/410 playback немедленно останавливается, его media source очищается, а sibling panel удаляется до установки безопасного recovery main.
- Приватный audio и controls не остаются в DOM после потери доступа или удаления встречи.
