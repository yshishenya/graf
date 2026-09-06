# Feature Specification: MediaScribe v0.5.3 integration fidelity

**Feature Branch**: `203-mediascribe-v053-integration`

**Created**: 2026-08-25

**Status**: Draft

**Input**: User description: MediaScribe обновлён до API release v0.5.3; GRAF должен корректно использовать расширенный контракт, включая новые правила diarization-блоков, строгую типизацию words, source_role и существующий Temporal recovery.

## User Scenarios & Testing

### User Story 1 - Получить читаемую расшифровку без искажения блоков (Priority: P1)

Пользователь открывает готовую встречу и видит блоки расшифровки в том виде, в котором их сформировал MediaScribe. GRAF не склеивает соседние блоки, не делит их повторно и не теряет текст из-за неполных word timestamps.

**Why this priority**: Неправильная повторная агрегация меняет смысл и временную структуру записи, а потеря текста разрушает доверие к продукту.

**Independent Test**: Подать синтетический v0.5.3 result с повторным возвращением спикера, длинной паузой, punctuation и неполными word timestamps; проверить импорт, сохранённые строки и пользовательскую projection.

**Acceptance Scenarios**:

1. **Given** provider вернул два соседних блока одного спикера, разделённых допустимой паузой, **When** GRAF импортирует result, **Then** пользовательская projection сохраняет границы provider-блоков и не создаёт собственное объединение.
2. **Given** provider вернул блоки разных `source_role`, включая перекрывающиеся по времени, **When** GRAF импортирует result, **Then** роли и порядок сохраняются, а блоки не объединяются между дорожками.
3. **Given** provider вернул неполные timestamps в `words`, но полный `text`, **When** GRAF импортирует result, **Then** полный текст доступен и result не отклоняется только из-за отсутствующих word timestamps.
4. **Given** provider вернул `UNKNOWN` с одной пунктуацией, **When** GRAF отображает result, **Then** GRAF не превращает его в отдельного подтверждённого участника и не подменяет его соседним speaker ID.

---

### User Story 2 - Видеть результат независимо от summary (Priority: P1)

Пользователь получает расшифровку после готовности diarization, даже если summary ещё строится, отключено или завершилось ошибкой.

**Why this priority**: Summary — дополнительный артефакт; его задержка не должна оставлять пользователя без основного результата записи.

**Independent Test**: Импортировать результаты с `summary=null`, `running`, `ready` и `failed`, при готовых transcript и diarization, и проверить одинаковую доступность расшифровки.

**Acceptance Scenarios**:

1. **Given** transcript и diarization из одного result доступны, а summary имеет статус `running` или `failed`, **When** пользователь открывает встречу, **Then** расшифровка и speaker blocks видимы, а summary показывает собственное состояние.
2. **Given** transcript есть, но matching diarization ещё нет, **When** пользователь открывает встречу, **Then** текст встречи скрыт, показано понятное состояние ожидания diarization и доступен предусмотренный recovery path.

---

### User Story 3 - Обработка восстанавливается предсказуемо (Priority: P1)

Пользователь не получает тупик при временной ошибке MediaScribe: GRAF показывает следующий автоматический check, позволяет выполнить ручную проверку текущей job, а Temporal переживает перезапуск без дубликатов.

**Why this priority**: Сетевые и временные сбои неизбежны; повторная загрузка вместо reconciliation может создать дубликаты и расходовать лимит.

**Independent Test**: Прогнать fake provider через `202`, `409 result_not_ready` с `Retry-After`, `queue_state=retrying`, restart workflow и manual check race; проверить одну provider job и один durable schedule.

**Acceptance Scenarios**:

1. **Given** provider вернул retryable `409` или временный `503`, **When** GRAF планирует следующий check, **Then** используется provider hint с bounded fallback, а workflow ждёт durable timer без busy polling.
2. **Given** workflow или worker перезапустился во время ожидания, **When** обработка возобновляется, **Then** продолжается та же business attempt и provider job; новый upload не создаётся автоматически.
3. **Given** пользователь нажал ручную проверку во время countdown, **When** операция принята, **Then** текущий timer/schedule generation инвалидируется, выполняется не более одной проверки, а UI получает новое server-derived состояние.
4. **Given** provider сообщил terminal `failed`, `job_failed`, `invalid_audio_payload` или `queue_dispatch_failed`, **When** GRAF обновляет состояние, **Then** polling прекращается, countdown не показывается, причина и следующий допустимый путь остаются понятными.

---

### User Story 4 - Провайдерские данные остаются проверяемыми (Priority: P2)

Оператор может понять, каким runtime и каким контрактом сформирован результат, а GRAF не теряет полезные `words`, `source_role`, provenance и безопасные machine codes при импорте.

**Why this priority**: При расследовании проблем нужно отличать provider degradation от ошибки GRAF и воспроизводить контракт без хранения секретов или подписанных ссылок.

**Independent Test**: Подать result с полным provenance, неизвестными дополнительными полями, nullable/частичными words и отсутствующим source_role; проверить typed DTO, digest, durable projection и отсутствие content-bearing provider data в обычной telemetry.

**Acceptance Scenarios**:

1. **Given** `words` отсутствует, равен `null` или содержит nullable `start/end/probability`, **When** result проходит boundary validation, **Then** он принимается, а обязательным остаётся только строковый `word`.
2. **Given** provider добавил неизвестное поле ответа или provenance, **When** GRAF декодирует result, **Then** совместимость сохраняется, но пользовательские projection копируют только allowlisted поля.
3. **Given** `source_role` отсутствует у single-track result, **When** GRAF нормализует его, **Then** он получает семантику `mixed`, а не ошибочно `incoming`; для dual-track отсутствие роли не создаёт ложную атрибуцию.

### Edge Cases

- `diarization` может быть `null`, отсутствовать или быть пустым; это не должно превращать неполный result в готовую расшифровку.
- Строки provider могут иметь одинаковое время начала, перекрываться только между разными дорожками или возвращать одного speaker после другого; сортировка не должна быть основанием для склейки.
- `words` может содержать элемент без `word`, нечисловое время, отрицательное время или `end <= start`; boundary должен отклонить только malformed result безопасным machine code, не раскрывая payload.
- `source_role` может быть неизвестным; GRAF сохраняет bounded original token для диагностики и не выдаёт его за `mic`, `incoming` или `mixed` без основания.
- Summary может быть `null` при доступной расшифровке или закончиться ошибкой после готовности diarization.
- Provider может вернуть `502/503/504` после принятия upload; повтор обязан использовать тот же idempotency key и эквивалентный multipart body.
- Старые импортированные результаты без words и старые legacy source roles должны оставаться читаемыми.

## Requirements

### Functional Requirements

- **FR-001**: GRAF MUST treat MediaScribe v0.5.3 diarization items as final provider blocks and MUST NOT merge, split, or reorder their canonical rows or timestamps. A human-readable export may group headings only when every provider block remains a separate child line with its own text/timestamp.
- **FR-002**: GRAF MUST preserve `source_role` values `mic`, `incoming`, and `mixed`; it MUST keep the original bounded token separately when normalization is needed.
- **FR-003**: For single-track results with omitted `source_role`, GRAF MUST project the role as `mixed`; it MUST NOT default it to `incoming`.
- **FR-004**: GRAF MUST validate `words` as absent, null, or an array of WordItem objects with required string `word` and optional nullable numeric `start`, `end`, and `probability`.
- **FR-005**: GRAF MUST preserve complete segment `text` when word timestamps are absent or incomplete and MUST NOT reconstruct user text by concatenating only timed words.
- **FR-006**: GRAF MUST persist or otherwise durably retain validated diarization word metadata with the result lineage, without placing it in ordinary logs, analytics, Temporal search attributes, or public provider error text.
- **FR-007**: GRAF MUST keep transcript visibility gated by matching transcript and diarization readiness, while summary state remains independent.
- **FR-008**: GRAF MUST map v0.5.3 lifecycle, queue, retry, terminal error and response-header signals into existing safe processing state without treating `queue_position` as ETA.
- **FR-009**: Temporal workflows MUST use durable timers and bounded activity retry for provider polling; restart/replay MUST preserve determinism and the same business attempt/provider job.
- **FR-010**: A manual check MUST reconcile the existing provider job, atomically invalidate the superseded schedule, and be idempotent across tabs and repeated clicks.
- **FR-011**: GRAF MUST preserve allowlisted provenance and result diagnostics needed to distinguish provider degraded output from GRAF validation failure, while never storing MediaScribe credentials or signed URLs.
- **FR-012**: GRAF MUST retain compatibility with prior result rows and prior provider responses that omit v0.5.3-only fields.

### Key Entities

- **WordItem**: One provider word with required text and optional nullable timing/confidence metadata.
- **Provider diarization block**: One final speaker-attributed block from MediaScribe, including timing, text, speaker key, optional source role and words.
- **Processing result lineage**: The immutable GRAF result tied to meeting, accepted media revision, business workflow and provider job.
- **Recovery schedule**: Durable next-check state with generation, provider hint, manual override and terminal status.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Contract tests accept all valid v0.5.3 WordItem forms (absent, null, complete and partially timed) and reject malformed word items without logging their content.
- **SC-002**: For a provider fixture containing N diarization blocks, GRAF persistence and user projection expose exactly N provider blocks and no locally merged block is introduced.
- **SC-003**: 100% of tested single-track results omitting `source_role` project as `mixed`; no such result projects as `incoming`.
- **SC-004**: Across retry, worker restart, Temporal replay and two concurrent manual checks, each business attempt creates at most one provider job and one active durable schedule.
- **SC-005**: In the summary matrix (`null`, running, ready, failed), matching transcript+diarization becomes visible in all four cases; transcript-only remains hidden.
- **SC-006**: Focused MediaScribe, import, persistence, recovery and Temporal tests pass, and the repository validation lane reports no new failure attributable to Feature 203.

## Assumptions

- MediaScribe v0.5.3 remains a server-to-server dependency accessed only through `/v1`; credentials remain server-side.
- Existing Feature 195 recovery state, UI copy, manual-check action and Temporal workflow are the baseline and should be reused rather than replaced.
- GRAF does not need to create its own diarization segmentation algorithm; provider-owned block formation is the source of truth.
- Word metadata is retained for result fidelity and future word-aware playback/export, but no new word-highlight UI is required in this slice unless an existing projection can expose it without a new interaction model.
- No provider webhook is assumed; polling and provider retry hints remain the integration model.
- Production rollout, provider configuration changes and deployment are out of scope for this slice.

## Out of Scope

- Changing MediaScribe itself, its inference models, diarization algorithm or runtime configuration.
- Replacing Temporal or introducing a second retry/orchestration service.
- Inferring a person’s identity from provider speaker labels or matching labels across jobs.
- Making summary a prerequisite for transcript visibility.
- Adding a new frontend framework or redesigning unrelated meeting surfaces.
