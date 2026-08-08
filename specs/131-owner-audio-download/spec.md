# Feature Specification: Скачивание аудио владельцем по умолчанию

**Feature Branch**: `131-owner-audio-download`

**Created**: 2026-07-26

**Status**: Implemented locally; full CI closeout remains open because of an unrelated SC-017 load-sensitive timing failure

**Input**: User decision: "Владелец встречи должен скачивать аудио по умолчанию без отдельного разрешения"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Владелец сохраняет готовое аудио (Priority: P1)

Как владелец встречи, я хочу скачать доступную запись без отдельной настройки
разрешения, чтобы сохранить её для разрешённого использования вне кабинета.

**Why this priority**: Сейчас владелец видит отказ при стандартной политике
рабочего пространства, хотя имеет право просматривать собственную встречу.

**Independent Test**: На синтетической готовой встрече с валидным playback-аудио
владелец открывает меню действий и получает непустой аудиофайл через браузер и
встроенный macOS кабинет без ручного включения audio-download policy.

**Acceptance Scenarios**:

1. **Given** встреча принадлежит текущему пользователю, аудио готово, а явного
   запрета на скачивание нет, **When** владелец выбирает «Скачать аудио…»,
   **Then** начинается штатное сохранение файла без отдельного разрешения.
2. **Given** владелец отменил системный выбор места сохранения, **When** встреча
   остаётся открытой, **Then** владелец может повторить скачивание.
3. **Given** владелец открывает встречу в браузере или встроенном кабинете,
   **When** audio-download policy не задана отдельно, **Then** оба интерфейса
   показывают одинаковое доступное действие и используют один server-mediated
   поток.

---

### User Story 2 - Явные ограничения сохраняют силу (Priority: P1)

Как владелец рабочего пространства, я хочу явно запретить выгрузку конкретной
встречи или ограничить её кругом владельцев, чтобы default-доступ не отменял
осознанные privacy-решения.

**Why this priority**: Изменение default egress не должно превращаться в обход
явного запрета или расширение доступа другим участникам.

**Independent Test**: Для одной синтетической встречи задать явный запрет, для
другой — owner-only, а для третьей — разрешение всем permitted reviewers;
проверить, что каждый viewer получает только соответствующий результат.

**Acceptance Scenarios**:

1. **Given** для встречи задан явный запрет на audio download, **When** владелец
   обращается к действию или прямому адресу, **Then** сервер отклоняет запрос и
   не выдаёт аудиобайты.
2. **Given** для встречи задан режим owner-only, **When** permitted non-owner
   пытается скачать аудио, **Then** запрос отклоняется, а владелец может скачать
   готовый файл.
3. **Given** политика разрешает скачивание permitted reviewers, **When** viewer
   проходит текущую проверку доступа, **Then** действует существующий policy и
   audit flow без изменения trust boundary.

---

### User Story 3 - Отказ остаётся понятным и безопасным (Priority: P1)

Как пользователь, я хочу получить bounded result, если аудио отсутствует,
удаляется, ещё обрабатывается или сессия недействительна, чтобы не принять
тихий отказ за успешное скачивание.

**Why this priority**: Аудио — чувствительный артефакт; отказ должен быть
fail-closed и не должен раскрывать storage или содержимое встречи.

**Independent Test**: Для синтетических состояний отсутствующего артефакта,
активного удаления, истёкшей сессии и ошибки хранилища вызвать тот же поток и
проверить bounded UI state, отсутствие аудиобайтов и сохранение открытой встречи.

**Acceptance Scenarios**:

1. **Given** playback-аудио отсутствует или ещё не готово, **When** владелец
   пытается скачать его, **Then** запрос не выдаёт файл и действие не обещает
   успешное сохранение.
2. **Given** сессия истекла или встреча удаляется, **When** пользователь повторяет
   скачивание, **Then** доступ отклоняется по существующей политике и встреча не
   заменяется ошибочным документом.
3. **Given** сервер подготовил успешный ответ, **When** сохранение отменено,
   **Then** встреча остаётся доступной и повторная попытка не создаёт второй
   неконтролируемый экспорт.

### Edge Cases

- Существующая запись с policy source `workspace_default` и отсутствующим
  явным per-meeting решением получает owner-default только для audio download.
- Явный per-meeting запрет имеет приоритет над owner-default.
- Transcript, summary и package export не становятся доступными из-за этого
  изменения.
- Non-owner viewer не получает доступ к аудио только потому, что владелец имеет
  owner-default.
- Browser и embedded macOS cabinet сохраняют один server-mediated egress и не
  получают storage URL или signed URL.
- Двойное быстрое нажатие и отмена системного save panel сохраняют возможность
  безопасной повторной попытки.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Система MUST разрешать владельцу встречи скачать готовый audio
  artifact без отдельного включения per-meeting разрешения, если нет явного
  запрета и текущая проверка доступа проходит.
- **FR-002**: Owner-default MUST применяться только к audio download; transcript,
  summary и package export MUST сохранять существующие default policy.
- **FR-003**: Явный per-meeting запрет MUST иметь приоритет над owner-default и
  MUST блокировать выдачу аудиобайтов как по интерфейсу, так и по прямому запросу.
- **FR-004**: Режим owner-only MUST продолжать запрещать audio download
  permitted non-owner viewers и разрешать его владельцу при готовом artifact.
- **FR-005**: Существующие проверки авторизации, workspace membership, lifecycle,
  deletion и validated playback artifact MUST оставаться fail-closed.
- **FR-006**: Browser и embedded macOS cabinet MUST использовать тот же
  server-mediated audio download и MUST NOT получать storage URL, signed URL или
  credentials.
- **FR-007**: Недоступное, удаляемое, неготовое или повреждённое аудио MUST
  возвращать bounded отказ без пустого успешного файла и без замены открытой
  встречи ошибочным документом.
- **FR-008**: Скачивание, отказ и повторная попытка MUST сохранять существующий
  metadata-only audit contract без аудио, transcript text, secrets, object keys,
  private paths или content-bearing diagnostics.
- **FR-009**: Policy resolution MUST различать отсутствие явного решения и
  явный запрет, чтобы owner-default не отменял privacy-решение владельца
  рабочего пространства.

### Key Entities

- **MeetingArtifactPolicy**: per-meeting решения для audio, transcript, summary и
  package egress, включая источник policy и явное изменение.
- **Meeting owner**: пользователь, создавший встречу и имеющий owner access.
- **Audio playback artifact**: валидированный server-owned playback файл,
  доступный для скачивания только после текущих проверок.
- **Egress audit event**: metadata-only запись разрешённого или отклонённого
  действия.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: В 100% синтетических сценариев с готовым аудио и без явного запрета
  владелец получает штатное начало сохранения в браузере и embedded cabinet без
  ручной настройки policy.
- **SC-002**: В 100% сценариев с явным запретом или non-owner viewer аудиобайты не
  выдаются, а политика остаётся fail-closed.
- **SC-003**: В 100% сценариев с отсутствующим артефактом, удалением, истёкшей
  сессией или storage failure встреча остаётся доступной для восстановления, а
  успешный пустой файл не создаётся.
- **SC-004**: В 100% успешных и отказных сценариев audit evidence остаётся
  metadata-only и не содержит содержимое встречи, storage URL или секреты.
- **SC-005**: Изменение не добавляет новые зависимости, endpoint или storage
  boundary.

## Assumptions

- Owner-default означает отсутствие явного per-meeting решения; явный запрет
  сохраняет приоритет.
- Текущий server-mediated endpoint, validated playback artifact, auth session,
  audit и native WebKit save flow переиспользуются.
- Внешний браузер, embedded macOS cabinet и текущая policy model остаются в scope;
  мобильные клиенты и новые форматы не входят в работу.
- Committed evidence использует только синтетические данные и безопасные
  признаки результата.

## Out of Scope

- Изменение transcript, summary или package default egress.
- Добавление нового endpoint, storage format, signed URL или MediaScribe path.
- Удаление явных per-meeting запретов или расширение доступа permitted non-owner
  viewers.
- Редизайн кабинета, нового save panel или изменение capture/transcription flow.
