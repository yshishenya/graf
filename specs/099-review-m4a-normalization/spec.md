# Feature Specification: Review M4A Normalization

**Feature Branch**: `099-review-m4a-normalization`
**Created**: 2026-07-09
**Status**: Draft
**Input**: User description: "Давай вариант 3. У нас всегда в записи должен быть m4a. Для загруженных записей будем транскодировать. Запиши это как отдельную будущую фичу 099 с подробным контекстом."

## Product Context

После security review мы исправили playback path так, чтобы он не загружал весь аудиофайл в память перед `Range`-ответом. Новое направление: playback должен отдавать уже подготовленный playback-ready `meeting-review.m4a`, а не собирать звук на лету из разных источников и не пытаться каждый раз понимать исходный формат файла.

Это решение выбрано осознанно. У нас есть несколько конкурирующих вариантов:

- Хранить только исходники и при каждом playback читать исходный media file. Это плохо, потому что playback route должен знать все форматы, кодеки, контейнеры, ошибки исходников и поведение range requests.
- Для каждой записи на лету собирать WAV или другой temporary playback stream. Это опасно для памяти, CPU и latency, особенно на больших файлах и при частых seek/range requests.
- Стримить исходный файл кусками из MinIO без нормализации. Это частично снижает memory risk, но оставляет проблему совместимости: разные upload formats, video containers, variable codecs, source files without clean audio track, mobile/browser playback differences.
- Нормализовать запись один раз после ingest/processing и хранить стабильный playback-ready `meeting-review.m4a`. Это выбранный вариант для 099.

Главный продуктовый принцип 099: каждая запись, которую пользователь может открыть в review, должна иметь один понятный playback artifact. UI и API не должны угадывать, из чего собирать звук в момент просмотра.

## Why This Matters

Пользовательский сценарий выглядит просто: пользователь записал встречу или загрузил файл, потом открывает запись и нажимает play. Внутри это пересекает несколько чувствительных зон: upload, storage, processing, MediaScribe, retention/deletion, playback, browser/mobile compatibility и DoS risk.

Если playback route умеет читать "что угодно" и собирать звук в момент запроса, мы получаем:

- тяжелую работу в user-facing request;
- риск полного чтения больших файлов в память;
- разные ошибки для desktop recordings и manual uploads;
- сложные retry/refresh/seek сценарии;
- сложную безопасность вокруг arbitrary media containers;
- неочевидную логику: запись вроде обработана, но play может падать из-за отсутствия отдельного playback artifact.

Если же `meeting-review.m4a` создается один раз как часть lifecycle записи, playback становится простым и предсказуемым:

- список записей может честно показывать статус подготовки аудио;
- review может использовать один стабильный источник;
- range/seek работает поверх известного формата;
- удаление и retention знают, какой artifact надо учитывать;
- manual uploads не требуют special-case playback behavior;
- MediaScribe и playback не смешиваются в один рискованный runtime path.

## Current-State Correction

Перед 099 уже принято и частично сделано:

- Playback route должен стримить stored playback artifact и поддерживать `Range`.
- Playback route не должен читать весь object в память.
- Playback route не должен на лету собирать combined WAV для обычного browser playback.
- Playback availability теперь зависит от наличия валидного playback-ready `meeting-review.m4a`.
- Для записей без такого artifact playback может быть временно unavailable.
- Manual upload уже идет через обычный lifecycle записи: record создается как нормальная запись, media принимается через upload session/finalize boundary, затем используется существующий processing dispatch. 099 не должен превращать manual upload в отдельную параллельную подсистему.
- Upload/finalize safety baseline уже усилен отдельным узким фиксом: очевидно oversized upload parts могут отклоняться до чтения тела, а multipart finalize не должен собирать accepted parts целиком в память. 099 должен сохранить этот baseline и не вернуть full-buffer поведение через normalization/backfill.
- MediaScribe submit уже отделен от playback-normalization цели: transcript processing может использовать свой bounded staging path, но не является playback artifact creation. 099 не должен смешивать MediaScribe submit, playback preparation и raw upload handling в один пользовательский request path.

099 закрывает оставшийся product gap: система должна гарантированно создавать этот artifact для всех supported recording types, включая manual uploads.

## Current Safety Baseline To Preserve

Эта секция фиксирует не новую реализацию 099, а границы, которые уже нельзя ломать при будущей реализации.

### Accepted Source Boundary

Source media становится пригодным для downstream processing только после того, как существующий ingest/finalize lifecycle принял его как controlled source artifact. 099 должен начинаться от этого accepted source boundary, а не от сырого browser upload body, не от временного upload part и не от отдельного direct-to-processing endpoint.

Для пользователя это означает: если файл уже принят как запись, refresh/retry/backfill работают с этой записью. Пользователь не должен получать второй record, второй upload session, второй source artifact или вторую playback-preparation линию только потому, что страница обновилась, сеть оборвалась или worker повторил задачу.

### No Competing Media Services

099 не должен создавать конкурирующие сервисы со своей собственной правдой о записи. В системе должна остаться одна цепочка владения:

1. запись и ее источник принимаются в существующем ingest lifecycle;
2. source artifact участвует в retention, deletion, audit and diagnostics;
3. playback normalization создает или переиспользует canonical `meeting-review.m4a`;
4. review playback читает только canonical playback artifact;
5. transcript processing остается отдельной зависимостью со своей правдой о transcript/result status.

Если будущий план предлагает новый upload service, new finalize service, direct playback from arbitrary source media, on-demand playback assembly или direct MediaScribe-driven playback artifact, это должно считаться scope conflict с 099.

### Resource-Bounded Lifecycle

099 должен сохранить invariant: большие media inputs не должны требовать full-object memory loading in user-facing request paths. Это относится к upload guards, accepted-source materialization, playback route, normalization, retry and backfill.

Допустимый продуктовый результат для тяжелых или проблемных файлов: bounded preparing state, bounded retryable failure, permanent unsupported failure, or skipped backfill reason. Недопустимый результат: бесконечный spinner, process crash, duplicate record, partial playback artifact, or silent fallback to a wrong source.

### Temporary Output Discipline

Любой intermediate normalization output является controlled temporary artifact, а не playback artifact. Он не должен быть виден player'у, считаться ready, попадать в export/share flow, заменять existing valid playback artifact или обещать deletion completion до тех пор, пока artifact не прошел validation и не зарегистрирован как canonical playback output.

## Product Decisions Captured For 099

- Decision: В каждой reviewable записи должен быть playback-ready `meeting-review.m4a`.
- Decision: Для manual upload исходный файл остается source artifact, но для playback создается normalized m4a artifact.
- Decision: Если пользователь ввел название при upload, оно остается названием записи.
- Decision: Если пользователь не ввел название при upload, название записи берется из имени файла.
- Decision: Manual upload не матчится с календарем в рамках этой фичи.
- Decision: Playback не должен транскодировать или пересобирать audio on demand.
- Decision: Playback не должен поддерживать arbitrary uploaded media directly as the review audio source.
- Decision: Транскодирование должно быть idempotent: refresh, retry, повторный worker или повторный finalize не создают дублей и не ломают уже принятую запись.
- Decision: Если normalized m4a уже существует и валиден, система не должна транскодировать его заново без явной причины.
- Decision: Для уже принятых файлов без playback m4a нужен безопасный reprocess/backfill path.
- Decision: Ошибки подготовки playback artifact должны быть видны как статус записи, но не должны превращаться в silent broken review.
- Decision: Retention/deletion/audit должны учитывать новый playback artifact как controlled meeting content.
- Decision: Existing ingest/finalize остается единственной границей принятия source media для manual uploads and first-party recordings.
- Decision: 099 не создает новый upload/finalize service, новый playback assembly service или альтернативный source-of-truth для record ownership.
- Decision: Normalization starts only from accepted source artifacts and must not consume raw in-flight upload bodies or unfinalized upload parts.
- Decision: Normalization/backfill/retry must preserve the resource-bounded safety baseline: no full source-media buffering in user-facing request paths and no on-demand playback assembly.
- Decision: Temporary normalization outputs are never playback-ready until they are complete, validated, registered and lifecycle-accounted.
- Decision: Transcript processing and playback normalization may run in the same broad record lifecycle, but their statuses must remain independently truthful.

## Scope Summary

099 описывает нормализацию playback audio для recordings and manual uploads. Это не новая upload modal, не календарный matching, не speaker naming и не новый MediaScribe contract. Это lifecycle-фича: после того как запись создана и media accepted, у записи должен появиться стандартный playback artifact.

### In Scope

- Создание `meeting-review.m4a` для новых first-party recordings, если такой artifact не создан более ранним stage.
- Транскодирование supported manual upload media в `meeting-review.m4a`.
- Проверка валидности playback artifact перед тем, как запись считается fully review-ready.
- Статусы "playback audio preparing", "playback audio ready", "playback audio failed", "retry available".
- Idempotent retry/reprocess/backfill для записей, у которых уже есть исходный файл, но нет валидного `meeting-review.m4a`.
- Lifecycle accounting для retention, deletion, audit и diagnostics.
- Защита от дублей при refresh, network retry, повторном finalize, повторном worker pickup или ручном retry.
- Четкое правило названия manual upload: user-entered title wins; otherwise file name.
- Ограничения по supported source formats and unsupported media failure states.
- Сохранение existing accepted-source boundary: normalization consumes accepted source artifacts, not raw upload bodies.
- Resource-bounded normalization/retry/backfill behavior for large files, near-limit files and multipart accepted sources.
- Explicit handling for temporary normalization outputs, partial outputs and cleanup/accounting after interruption.
- Consistent status composition when transcript result is ready but playback m4a is preparing/failed, or playback m4a is ready while transcript processing is still pending/failed.

### Out Of Scope

- Изменение дизайна upload modal.
- Calendar auto-match for manual uploads.
- Offline recording auto-match with calendar.
- Speaker identity or renaming speakers from calendar/contact data.
- Public sharing, attendee auto-share or permission changes.
- New MediaScribe API contract.
- Full video playback.
- Editing source media in the UI.
- Promising universal deletion outside GRAF-controlled storage.
- Adding broad new infrastructure when existing processing/lifecycle paths are sufficient.
- Новый параллельный upload/finalize subsystem.
- Direct-to-playback route from arbitrary original upload files.
- On-demand audio assembly/transcoding during user playback request.
- Direct MediaScribe-to-playback artifact ownership.
- Replacing existing single-track/dual-track transcription contracts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Новая запись всегда получает playback audio (Priority: P1)

Как пользователь, который открыл готовую запись, я хочу сразу видеть рабочий player, чтобы запись была пригодна для review без технических деталей про source tracks, codecs или processing pipeline.

**Why this priority**: Playback is core review behavior. Если transcript есть, но audio не играет из-за отсутствующего normalized artifact, пользователь воспринимает запись как сломанную.

**Independent Test**: Создать новую first-party запись обычным recording flow, дождаться review-ready состояния и проверить, что запись имеет valid playback m4a artifact and player can seek/play via range requests.

**Acceptance Scenarios**:

1. **Given** first-party recording successfully finishes, **When** processing reaches review-ready, **Then** the record has a valid playback-ready `meeting-review.m4a`.
2. **Given** the recording already produced a valid m4a artifact earlier in the pipeline, **When** review readiness is evaluated, **Then** the existing artifact is reused and not regenerated.
3. **Given** a recording has transcript data but playback m4a is still preparing, **When** the user opens the list or review page, **Then** the UI shows a non-broken preparing state instead of a dead player.
4. **Given** a recording has no valid playback m4a after processing, **When** the user opens review, **Then** playback is marked unavailable with retry/reprocess controls for authorized users.
5. **Given** the user seeks inside playback, **When** range requests are made, **Then** the player reads from the stored m4a artifact and does not trigger new audio assembly.

---

### User Story 2 - Manual upload transcodes to review m4a (Priority: P1)

Как пользователь, который загрузил audio/video file, я хочу получить такую же запись в кабинете, как после обычной записи, чтобы playback, transcript and status behaved consistently.

**Why this priority**: Manual upload is a major user path. Users should not care whether the original file was WAV, MP3, M4A, MP4, MOV or WebM once GRAF accepted it.

**Independent Test**: Upload supported media file, wait for processing, confirm that source artifact remains available for lifecycle accounting, while review playback uses normalized `meeting-review.m4a`.

**Acceptance Scenarios**:

1. **Given** a supported audio file is uploaded manually, **When** upload is accepted and processing finishes, **Then** the record has normalized `meeting-review.m4a` for playback.
2. **Given** a supported video file with an audio track is uploaded manually, **When** processing finishes, **Then** playback uses the extracted normalized audio artifact rather than the original video container.
3. **Given** user entered a title during upload, **When** processing creates the record, **Then** that title remains the record title.
4. **Given** user did not enter a title during upload, **When** processing creates the record, **Then** the file name is used as the record title.
5. **Given** manual upload is complete, **When** calendar matching features run, **Then** the manual upload is not auto-matched to calendar context.
6. **Given** the original file already is a compatible m4a, **When** normalization checks it, **Then** the system may reuse or register it as playback artifact only if it satisfies the product playback contract.

---

### User Story 3 - Retry and refresh do not create duplicates (Priority: P1)

Как пользователь, который обновил страницу, потерял сеть или нажал retry, я хочу, чтобы подготовка аудио продолжалась безопасно, а не создавала дубли записей или дубль playback artifacts.

**Why this priority**: Upload and processing are long-running. Refresh/network retry is normal user behavior. Idempotency here protects both UX and storage cost.

**Independent Test**: Start manual upload processing, refresh page or repeat finalize/retry, then verify that only one record and one active playback artifact exist for the logical upload.

**Acceptance Scenarios**:

1. **Given** upload was accepted and processing started, **When** the page refreshes, **Then** the existing processing state is reused and no second record is created.
2. **Given** finalize or processing dispatch is repeated with the same logical upload identity, **When** the backend receives it again, **Then** it returns or resumes the existing record/work instead of creating duplicates.
3. **Given** m4a normalization worker is retried after timeout, **When** the previous attempt already completed successfully, **Then** the worker observes the ready artifact and exits without overwriting it unexpectedly.
4. **Given** user presses retry after a failed normalization, **When** retry is accepted, **Then** the same record moves back into preparing state and does not create a new record.
5. **Given** a previous failed partial artifact exists, **When** retry succeeds, **Then** only the valid final artifact is exposed as playback-ready.
6. **Given** raw upload already finalized into an accepted source artifact, **When** normalization retry or backfill runs, **Then** it uses the accepted source artifact and does not reopen the raw upload body or create another upload session.
7. **Given** two browser tabs observe the same manual upload, **When** one tab retries playback preparation and the other tab refreshes, **Then** both tabs converge on the same record, same source artifact and same normalization status.

---

### User Story 4 - Existing accepted files can be backfilled (Priority: P2)

Как администратор или оператор системы, я хочу безопасно reprocess/backfill already accepted records that lack m4a playback, чтобы ранее загруженные файлы не оставались навсегда без audio review.

**Why this priority**: The product already has accepted uploads/records from before this normalization rule. We need a controlled migration path without manually repairing each record.

**Independent Test**: Select records missing valid playback m4a, run backfill in dry-run/report mode, then reprocess a bounded set and confirm that records gain playback without duplicates or title changes.

**Acceptance Scenarios**:

1. **Given** existing records have source media but no valid playback m4a, **When** backfill report runs, **Then** it lists eligible records without changing data.
2. **Given** operator approves backfill for eligible records, **When** backfill runs, **Then** each eligible record gets one valid playback m4a or a clear failure reason.
3. **Given** an existing record already has user-edited title, **When** backfill creates playback artifact, **Then** the title is not changed.
4. **Given** an existing record has no usable source media, **When** backfill evaluates it, **Then** it is skipped with a clear reason and no fake playback artifact is created.
5. **Given** backfill is interrupted, **When** it resumes, **Then** already completed records are not reprocessed unnecessarily.

---

### User Story 5 - Unsupported or unsafe media fails clearly (Priority: P2)

Как пользователь, который загрузил неподдерживаемый или поврежденный файл, я хочу получить понятный статус, чтобы понимать, что файл не удалось подготовить, и не ждать бесконечно.

**Why this priority**: A strict playback contract is useful only if failures are explicit and recoverable. Silent failure would look like broken product behavior.

**Independent Test**: Upload unsupported, corrupted, no-audio, too-large or unsafe media and verify that record state is clear, no playback m4a is exposed, and retry/cancel controls behave safely.

**Acceptance Scenarios**:

1. **Given** uploaded media has no audio track, **When** normalization runs, **Then** the record gets a clear unsupported/no-audio failure state.
2. **Given** uploaded media is corrupted or cannot be decoded safely, **When** normalization runs, **Then** the failure is recorded without exposing partial audio as playback-ready.
3. **Given** uploaded media exceeds configured product limits, **When** upload or normalization evaluates it, **Then** the user receives a bounded failure state rather than unbounded processing.
4. **Given** normalization fails due to transient infrastructure issue, **When** retry is available, **Then** authorized users can retry without re-uploading the original file if source media is still retained.
5. **Given** normalization fails due to permanent unsupported format, **When** retry is offered, **Then** retry guidance does not imply that repeating the same file will succeed without changing the file.

---

### User Story 6 - Lifecycle and privacy stay truthful (Priority: P2)

Как privacy-conscious пользователь или администратор, я хочу, чтобы normalized playback audio obeyed the same retention, deletion, audit and diagnostic boundaries as other meeting content.

**Why this priority**: `meeting-review.m4a` is meeting content. If lifecycle accounting misses it, deletion and retention promises become false.

**Independent Test**: Create record with source and playback artifacts, run retention/deletion/reporting paths, and verify that playback m4a is included in lifecycle status without logging private audio or secret paths.

**Acceptance Scenarios**:

1. **Given** a record has source media and playback m4a, **When** the record is deleted everywhere GRAF controls, **Then** playback m4a is included in the deletion plan/status.
2. **Given** retention policy removes audio artifacts, **When** retention applies to a record, **Then** playback m4a follows the same product retention decision as other controlled audio artifacts.
3. **Given** diagnostics or audit logs are emitted during normalization, **When** evidence is reviewed, **Then** logs contain metadata and status only, not raw audio, transcript content, signed URLs, provider tokens or private meeting content.
4. **Given** normalization uses external or internal processing dependencies, **When** dependency failure occurs, **Then** failure status is visible without leaking credentials or source media content.

---

### User Story 7 - Existing ingest boundary stays authoritative (Priority: P1)

Как product/security owner, я хочу, чтобы 099 использовал уже принятую границу source media, а не создавал второй upload/finalize path, чтобы запись, source artifact, playback artifact, transcript processing, deletion and audit stayed consistent.

**Why this priority**: Без этого 099 может случайно стать конкурентной media subsystem. Тогда manual upload, recording, playback, transcript, deletion and backfill начнут иметь разные source-of-truth, что создаст дубли, ложные статусы и непроверяемую deletion truth.

**Independent Test**: For manual upload and first-party recording, create accepted source media, run normalization/retry/backfill, and verify that every resulting playback state points back to the existing record/source artifact lineage without creating another logical record or competing accepted-source path.

**Acceptance Scenarios**:

1. **Given** manual upload produced one accepted source artifact, **When** normalization starts, **Then** the normalization work references that accepted source artifact and does not create a second source artifact for the same logical upload.
2. **Given** first-party recording produced accepted microphone/system source artifacts, **When** playback m4a is created, **Then** the playback artifact is attached to the same recording lineage and does not replace source artifact truth.
3. **Given** source media is not finalized, failed, aborted, expired or marked unsafe, **When** normalization is considered, **Then** no playback artifact is created from that unaccepted source.
4. **Given** transcript processing succeeds while playback normalization fails, **When** the user opens the list or review page, **Then** transcript status and playback status are shown as separate truthful states.
5. **Given** playback normalization succeeds while transcript processing is still pending or failed, **When** the user opens review, **Then** playback can be ready without pretending transcript/summary processing succeeded.
6. **Given** deletion starts while normalization is preparing a playback artifact, **When** lifecycle state is evaluated, **Then** the temporary output is blocked or cleaned up and no new playback-ready artifact is exposed after deletion begins.
7. **Given** backfill evaluates older records, **When** it finds records with missing or unsafe source lineage, **Then** those records receive explicit skip reasons rather than creating replacement source media.
8. **Given** a future implementation proposes a direct original-file playback path, **When** requirements are reviewed against 099, **Then** the proposal is rejected unless it is explicitly moved to a separate approved feature that changes the canonical playback contract.

## Edge Cases

- First-party recording already has valid playback m4a.
- First-party recording has transcript but no playback m4a due to older pipeline behavior.
- First-party recording has playback m4a but transcript processing is pending, failed, or permanently unavailable.
- Manual upload is WAV, MP3, M4A, MP4, MOV or WebM.
- Manual upload is video-only with no audio track.
- Manual upload has multiple audio tracks.
- Manual upload file extension does not match actual media/container.
- Manual upload source is corrupted, truncated or partially uploaded.
- Manual upload is rejected before body streaming because declared size exceeds product limits.
- Manual upload is accepted, page is refreshed, then user uploads another file.
- Upload finalize is retried after network timeout.
- Upload finalize has accepted source media but playback normalization has not started yet.
- Accepted source media consists of one source object.
- Accepted source media consists of multiple accepted parts that were finalized into one source artifact before normalization.
- Worker picks the same normalization job twice.
- Normalization succeeds but status update fails.
- Status update succeeds but artifact registration is incomplete.
- Partial or temporary artifact remains after failure.
- Temporary storage becomes unavailable while normalization or backfill is preparing output.
- Dependency returns success but produced playback artifact is empty, corrupt or not seekable.
- Source artifact exists in metadata but the controlled object is missing from storage.
- Source object is readable but has a different byte length or digest than the accepted source metadata.
- Existing source media has been deleted by retention before backfill.
- Existing record has user-entered title.
- Existing record has file-derived title.
- Existing record has manually edited title after upload.
- Calendar context exists for first-party recording but manual upload must not be calendar-matched.
- Playback range request arrives while normalization is still preparing.
- Playback range request arrives after normalization failed.
- Multiple browser tabs observe the same preparing/failed/ready state.
- User presses retry while another retry is already running.
- Admin backfill is interrupted and resumed.
- Deletion starts while normalization is running.
- Retention expires source media before retry.
- Retention removes original source media after valid playback m4a exists; lifecycle status must remain truthful about what can still be retried.
- Existing valid playback m4a exists but source media has been purged; retry/backfill must not fabricate source media.
- Same accepted source is observed by manual retry and scheduled backfill at the same time.
- Older record has legacy playback metadata that conflicts with the new canonical playback m4a contract.
- Diagnostics must avoid raw file names if file names contain private content, unless the UI surface is authorized for that record.
- Evidence must avoid raw audio, transcript text, signed URLs, provider tokens, credentials and live secret paths.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every reviewable recording MUST have a single canonical playback audio artifact named or identified as `meeting-review.m4a`.
- **FR-002**: Playback surfaces MUST use the canonical playback m4a artifact and MUST NOT assemble review audio from source tracks or uploaded source files on demand.
- **FR-003**: Manual upload processing MUST create a normalized playback m4a artifact from every supported uploaded audio or video file that contains usable audio.
- **FR-004**: First-party recording processing MUST create, reuse or register a valid playback m4a artifact before the record is considered fully playback-ready.
- **FR-005**: A record MAY show transcript or processing results before playback m4a is ready, but playback state MUST clearly indicate preparing, unavailable or failed rather than exposing a broken player.
- **FR-006**: The playback artifact readiness check MUST reject missing, empty, corrupted, partial or incompatible playback artifacts.
- **FR-007**: If a valid playback m4a already exists for a record, repeated processing, retry or backfill MUST NOT create duplicate active playback artifacts.
- **FR-008**: Manual upload title behavior MUST remain stable: user-entered title wins; when no user title exists, the original file name becomes the record title.
- **FR-009**: Manual uploads MUST NOT be automatically matched to calendar events as part of this feature.
- **FR-010**: Normalization, retry and backfill MUST be idempotent across page refreshes, network retries, duplicate finalize calls and duplicate worker pickup.
- **FR-011**: Normalization failure MUST produce a clear machine-readable and user-readable state with retry eligibility when retry is safe.
- **FR-012**: Permanent unsupported media failures MUST be distinguishable from transient infrastructure failures.
- **FR-013**: The system MUST NOT expose partial, temporary or failed normalization outputs as playback-ready artifacts.
- **FR-014**: Existing accepted records without valid playback m4a MUST have a safe reprocess/backfill path.
- **FR-015**: Backfill MUST support a report/dry-run mode before changing records.
- **FR-016**: Backfill MUST preserve existing record titles and user edits.
- **FR-017**: Backfill MUST skip records without retained usable source media and record a clear skip reason.
- **FR-018**: Playback m4a artifacts MUST participate in retention and deletion accounting as controlled meeting content.
- **FR-019**: Audit events MUST distinguish normalization requested, started, completed, failed, retried, skipped and backfilled.
- **FR-020**: Diagnostics and evidence MUST NOT contain raw audio content, transcript content, signed URLs, provider tokens, credentials or live secret paths.
- **FR-021**: File-size, duration and processing limits MUST be enforced before or during normalization so unsupported inputs cannot cause unbounded resource use.
- **FR-022**: Status shown in the recording list and review page MUST be consistent across refreshes, multiple tabs and reconnects.
- **FR-023**: Authorized users MUST be able to retry failed transient playback preparation without re-uploading the original file while source media is retained.
- **FR-024**: Retry controls MUST avoid creating new records for the same logical upload or same existing record.
- **FR-025**: The implementation MUST include validation for supported source media types, no-audio media, corrupted media, duplicate retry and deletion/retention interaction.
- **FR-026**: Normalization MUST consume only accepted source artifacts that belong to an existing recording lineage; it MUST NOT consume raw in-flight upload bodies, unfinalized upload parts or unmanaged local files.
- **FR-027**: Normalization MUST preserve the existing recording/source lineage across first-party recordings, manual uploads, retry and backfill.
- **FR-028**: 099 MUST NOT introduce a parallel upload/finalize source-of-truth for manual uploads or recordings.
- **FR-029**: Playback preparation MUST preserve bounded-resource behavior for large files and MUST NOT require loading complete source media into user-facing request memory.
- **FR-030**: Temporary normalization outputs MUST remain hidden from playback, export, share and ready-state surfaces until they are complete, validated and registered as canonical playback artifacts.
- **FR-031**: Normalization MUST treat temporary-storage pressure, dependency failure, source missing, source mismatch and decode failure as explicit bounded states, not indefinite processing.
- **FR-032**: Transcript/summary processing status and playback-normalization status MUST remain independently truthful; success in one MUST NOT imply success in the other.
- **FR-033**: Backfill MUST use existing accepted source lineage and MUST NOT create replacement source media for records whose source artifacts are missing, purged or unsafe.
- **FR-034**: If a valid playback m4a exists but source media is unavailable, retry/backfill MUST preserve the existing playback artifact and report that source-based regeneration is unavailable.
- **FR-035**: Normalization MUST include conflict handling for concurrent retry/backfill/worker attempts so only one active canonical playback artifact exists per recording.
- **FR-036**: Deletion or retention actions that begin while normalization is preparing output MUST prevent newly prepared temporary output from becoming playback-ready after the lifecycle state becomes deleting, deleted or audio-purged.
- **FR-037**: Resource and lifecycle failures MUST be observable through safe status/audit metadata without exposing raw file names, raw audio, object keys, signed URLs or private provider payloads.

### Key Entities *(include if feature involves data)*

- **Recording**: User-visible meeting or uploaded media record. It owns title, review status, processing state, lifecycle state and workspace/space ownership.
- **SourceMediaArtifact**: Original captured or uploaded media retained under product policy. It may be needed for processing, retry or backfill, but it is not the direct playback source.
- **PlaybackM4AArtifact**: Canonical review audio artifact used by playback. It must be valid, complete, retained according to policy and tied to one recording.
- **NormalizationJob**: Durable work item that creates or validates playback m4a for one recording.
- **NormalizationStatus**: User-visible and machine-readable state: preparing, ready, failed, retryable, skipped, cancelled or blocked.
- **BackfillRun**: Operator-controlled batch that reports and optionally reprocesses existing records missing valid playback m4a.
- **RetryRequest**: Authorized user or operator action that resumes failed normalization for the same record without creating a duplicate record.
- **LifecycleReportEntry**: Retention/deletion/audit entry proving how source media and playback m4a are accounted for.
- **AcceptedSourceBoundary**: The product state where source media has passed upload/finalize validation and is safe to use as input for downstream processing. 099 starts after this boundary.
- **TemporaryNormalizationArtifact**: Intermediate output created while preparing playback m4a. It is controlled meeting content but not playback-ready until validation and registration complete.
- **PlaybackReadinessGate**: The product decision that determines whether review playback is ready, preparing, failed, unavailable or blocked for the user.
- **SourceLineageLink**: The relationship tying playback m4a, source artifacts, normalization attempts and backfill attempts back to one recording without creating duplicate records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of new successfully processed first-party recordings have valid playback m4a before being marked playback-ready.
- **SC-002**: 100% of supported manual uploads with usable audio produce valid playback m4a or a clear failure state.
- **SC-003**: 0 playback requests trigger on-demand source-media transcoding or combined audio assembly.
- **SC-004**: 0 duplicate records are created by refresh, retry, duplicate finalize or duplicate worker pickup for the same logical upload.
- **SC-005**: 0 duplicate active playback m4a artifacts are created for the same recording by retry or backfill.
- **SC-006**: 100% of unsupported/no-audio/corrupt/too-large media cases end in bounded clear states, not indefinite processing.
- **SC-007**: 100% of existing eligible records in backfill dry-run receive an explicit planned action or skip reason before mutation.
- **SC-008**: 100% of deletion and retention reports include playback m4a status when the record has or had a playback artifact.
- **SC-009**: 100% of user-visible recording titles after manual upload follow the rule: entered title first, file name fallback.
- **SC-010**: 0 logs, diagnostics, specs or validation evidence contain raw audio, transcript content, signed URLs, provider tokens, credentials or live secret paths.
- **SC-011**: Playback for normalized records supports seek/range behavior without full-object memory loading in the playback request path.
- **SC-012**: Retry of transient normalization failures succeeds without requiring source re-upload while retained source media exists.
- **SC-013**: 100% of normalization attempts use accepted source artifacts tied to an existing recording lineage.
- **SC-014**: 0 new competing manual-upload or recording-finalize source-of-truth paths are introduced by 099.
- **SC-015**: 0 playback-ready artifacts are exposed from partial, temporary, failed or unvalidated normalization outputs.
- **SC-016**: 100% of concurrent retry/backfill/worker attempts for the same recording converge to one active canonical playback artifact or one clear blocked state.
- **SC-017**: 100% of deletion/retention events that overlap normalization prevent temporary outputs from becoming newly playback-ready after lifecycle state becomes deleting, deleted or audio-purged.
- **SC-018**: 100% of source-missing, source-mismatch, no-temp-storage and decode-failure cases produce bounded user/admin status rather than indefinite processing.
- **SC-019**: 100% of records with transcript-ready but playback-not-ready states show those statuses separately, and 100% of playback-ready but transcript-not-ready records avoid implying transcript success.

## Assumptions

- `meeting-review.m4a` is the canonical review playback artifact for the foreseeable product direction.
- The playback route already expects a stored, valid, range-readable m4a artifact.
- Existing MediaScribe transcription processing is separate from playback normalization; 099 should not require rewriting MediaScribe contract behavior.
- Manual upload source files may be audio or video, but review playback uses extracted/normalized audio, not video playback.
- Some earlier records may lack playback m4a and need controlled backfill.
- User-entered manual upload title and file-name fallback behavior are product-level title rules and must not be broken by backfill.
- Product should prefer small, durable, idempotent lifecycle changes over a large new media platform.
- Implementation planning may choose exact codec validation details, but the user-facing contract remains: valid playback-ready m4a or clear failure state.
- Manual upload remains modeled as a normal recording/source lifecycle, not a special media-only object outside the recording list.
- Existing bounded upload/finalize safeguards are baseline behavior; 099 should preserve and build on them rather than supersede them.
- Normalization may require temporary working storage, but temporary working output is controlled meeting content and must follow privacy/lifecycle rules.
- Transcript processing and playback preparation may finish in either order; the UI and status model must represent both dimensions truthfully.

## Dependencies *(mandatory)*

- Current cabinet playback behavior that streams stored playback m4a with range support.
- Existing manual upload ingest/finalize/processing flow.
- Existing recording artifact registry and lifecycle accounting.
- Existing retention/deletion policy surfaces.
- Existing audit/diagnostic redaction requirements.
- Existing bounded upload/finalize safety baseline for accepted source artifacts.
- Existing processing submit staging behavior that keeps transcription submission separate from playback normalization.
- MediaScribe processing remains a dependency for transcript, but playback normalization should be modeled as a separate artifact lifecycle concern.
- Feature `098-calendar-auto-context-match` remains separate: manual upload is not calendar-matched.
- Feature `097-workspace-account-onboarding` may affect workspace/space ownership checks later, but 099 must respect whichever active-space model is current when implemented.

## Clarifications Needed Before Implementation

- Which exact media limits should apply to normalization: max duration, max source size, max audio tracks and max retry count.
- Whether compatible uploaded m4a may be reused as `meeting-review.m4a` directly or must always be re-encoded to a strict canonical profile.
- Whether video uploads with multiple audio tracks should select the first usable audio track, fail with user choice required or follow a workspace policy.
- Which user roles can manually retry normalization and which roles can run backfill.
- How much of the original file name can appear in diagnostics when names may contain private meeting content.
- Whether playback normalization should be scheduled immediately after accepted source media, after transcript submission starts, after transcript result import, or through an independent readiness job. The required product outcome is independent truthful statuses either way.
- What temporary working-storage budget, concurrency limit and retry budget should apply to normalization and backfill so large files cannot starve normal recording review.
- Whether older records with legacy combined-review playback metadata should be migrated, skipped until source reprocess, or marked playback-unavailable with a clear reason.
