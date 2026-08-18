# Feature Specification: Понятная подсказка на таймлайне

**Feature Branch**: `codex/161-graf-ux-regressions`

**Created**: 2026-08-18

**Status**: Ready for implementation

**Input**: Отзыв пользователя по задаче 3: действие на таймлайне неочевидно;
нужна элегантная минималистичная подсказка.

## User Scenarios & Testing

### User Story 1 - Понять действие без обучения (Priority: P1)

Пользователь видит таймлайны спикеров и сразу понимает, что цветной фрагмент
можно нажать, чтобы начать прослушивание с этого места.

**Why this priority**: Таймлайн без объяснения выглядит как только
индикатор; пользователь может не обнаружить ключевую возможность точного
прослушивания фрагмента.

**Independent Test**: В synthetic browser и embedded render открыть встречу,
проверить видимую подсказку рядом с панелью, её смысл без контекста и
доступность track control с клавиатуры.

**Acceptance Scenarios**:

1. **Given** таймлайн содержит цветные отрезки, **When** пользователь видит
   панель до любого действия, **Then** рядом с ней отображается одна короткая
  подсказка: что нужно нажать и что произойдёт.
2. **Given** пользователь использует клавиатуру или screen reader, **When** он
   фокусирует track control, **Then** accessible name повторяет тот же
   смысл, а визуальная подсказка не является единственным каналом информации.
3. **Given** таймлайн недоступен, пуст или встреча не имеет playable audio,
   **When** отображается status state, **Then** misleading click hint не
   добавляется в статусный блок.

### Edge Cases

- Длинное имя спикера не должно выталкивать подсказку за пределы панели.
- На узкой ширине текст может занимать две строки, но не создаёт horizontal
  overflow и не конкурирует с playback controls.
- Повторный HTMX/partial render не должен дублировать hint.
- Reduced-motion и dark/light themes не должны менять смысл или контраст
  подсказки.

## Requirements

### Functional Requirements

- **FR-001**: Таймлайн MUST показывать ровно одну постоянную inline-подсказку
  в playable state, сформулированную через конкретное действие «нажать на
  цветной фрагмент» и результат «перейти к этому месту записи».
- **FR-002**: Подсказка MUST быть короткой, вторичной по визуальному весу и
  располагаться непосредственно перед таймлайном; она не должна выглядеть
  как отдельная кнопка или banner.
- **FR-003**: Каждый track control MUST иметь keyboard focus, accessible name
  и действие, описывающее переход к фрагменту; смысл MUST совпадать с видимой
  подсказкой.
- **FR-004**: В unavailable/empty playback state подсказка MUST отсутствовать
  или быть заменена только существующим truthful status copy.
- **FR-005**: Подсказка MUST корректно переноситься на узком viewport, не
  перекрывать lane controls и не добавлять горизонтальную прокрутку.
- **FR-006**: Изменение MUST использовать существующую server-rendered
  timeline markup и CSS; новые зависимости, tooltip framework, storage и
  playback semantics не входят.

### Key Entities

- **Inline playback hint**: короткая локализованная подсказка рядом с
  playable timeline; не хранится отдельно.
- **Track control**: существующий focusable control дорожки с seek action и
  accessible label.

## Success Criteria

### Measurable Outcomes

- **SC-001**: В playable synthetic render присутствует ровно один hint, его
  текст содержит действие и результат, а duplicate render не добавляет второй.
- **SC-002**: Keyboard/accessibility contract подтверждает, что смысл hint
  доступен и без визуального текста через track accessible name.
- **SC-003**: Browser/embedded narrow matrix проходит без horizontal overflow,
  перекрытия controls или misleading hint в unavailable state.
- **SC-004**: Focused checks и `node --check` проходят без изменения playback
  behavior.

## Assumptions

- Постоянная inline-подсказка предпочтительнее first-use-only state: для
  server-rendered shell нет надёжной причины вводить storage, а повторный
  пользователь может вернуться к встрече через время.
- Формулировка «Нажмите на цветной фрагмент, чтобы перейти к этому месту
  записи.» достаточно короткая, конкретная и truthful для текущего seek
  поведения.
- Web и embedded используют один и тот же rendered fragment.

## Out of Scope

- Редизайн playback controls, waveform, colours или speaker labels.
- Генерация итогов и логика аудио.
- Analytics по просмотру hint или persistent dismissal.
