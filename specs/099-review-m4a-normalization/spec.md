# Feature Specification: Review M4A Normalization

**Feature Branch**: `099-review-m4a-normalization`
**Created**: 2026-07-09
**Status**: Clarified
**Input**: User description: "Давай вариант 3. У нас всегда в записи должен быть m4a. Для загруженных записей будем транскодировать. Запиши это как отдельную будущую фичу 099 с подробным контекстом."

## Product Context

После security review мы исправили playback path так, чтобы он не загружал весь аудиофайл в память перед `Range`-ответом. Новое направление: playback должен отдавать уже подготовленный playback-ready `meeting-review.m4a`, а не собирать звук на лету из разных источников и не пытаться каждый раз понимать исходный формат файла.

Это решение выбрано осознанно. У нас есть несколько конкурирующих вариантов:

- Хранить только исходники и при каждом playback читать исходный media file. Это плохо, потому что playback route должен знать все форматы, кодеки, контейнеры, ошибки исходников и поведение range requests.
- Для каждой записи на лету собирать WAV или другой temporary playback stream. Это опасно для памяти, CPU и latency, особенно на больших файлах и при частых seek/range requests.
- Стримить исходный файл кусками из MinIO без нормализации. Это частично снижает memory risk, но оставляет проблему совместимости: разные upload formats, video containers, variable codecs, source files without clean audio track, mobile/browser playback differences.
- Нормализовать запись один раз после ingest/processing и хранить стабильный playback-ready `meeting-review.m4a`. Это выбранный вариант для 099.

Главный продуктовый принцип 099: каждая запись, которую пользователь может открыть в review, должна иметь один понятный playback artifact. UI и API не должны угадывать, из чего собирать звук в момент просмотра.

## Clarifications

### Session 2026-07-14

- Q: Если загруженный файл уже M4A, когда его можно использовать без повторного кодирования? → A: Только после строгой проверки полного соответствия каноническому playback-профилю; при любом несовпадении файл транскодируется, а исходный source artifact сохраняется отдельно.
- Q: Как выбирать звук, если загруженное видео содержит несколько аудиодорожек? → A: Использовать единственную usable-дорожку или единственную дорожку, помеченную контейнером как основная; при отсутствии однозначного выбора завершать подготовку понятной ошибкой, не угадывая и не смешивая дорожки.
- Q: Кто должен запускать повторную конвертацию и обработку старых записей? → A: Никто из пользователей или администраторов; для каждого поддерживаемого исправного accepted source GRAF автоматически конвертирует, повторяет временные сбои и выполняет bounded backfill, а объективно поврежденный или не содержащий звука файл автоматически получает окончательный понятный статус.

### Session 2026-07-17 — production recovery hotfix

- Q: Что происходит, если worker был перезапущен, когда задача уже находится в долгой автоматической паузе именно с причиной `worker_interrupted`? → A: При старте worker GRAF немедленно и автоматически возобновляет только такую прерванную задачу с тем же record/job. Обычные временные ошибки сохраняют рассчитанную паузу; пользователь и администратор не выполняют никаких действий.

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

Для пользователя это означает: если файл уже принят как запись, refresh, automatic retry и automatic backfill работают с этой записью. Пользователь не должен получать второй record, второй upload session, второй source artifact или вторую playback-preparation линию только потому, что страница обновилась, сеть оборвалась или worker повторил задачу.

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

Допустимый продуктовый результат для тяжелых или проблемных файлов: bounded preparing state with automatic retry, permanent unsupported failure, or skipped automatic-backfill reason. Недопустимый результат: бесконечный spinner, process crash, duplicate record, partial playback artifact, user-facing retry work, or silent fallback to a wrong source.

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
- Decision: Транскодирование должно быть idempotent: refresh, automatic retry, повторный worker или повторный finalize не создают дублей и не ломают уже принятую запись.
- Decision: Загруженный M4A переиспользуется без повторного кодирования только после строгой проверки полного соответствия каноническому playback-профилю; при любом несовпадении он транскодируется. Исходный source artifact остается отдельным от canonical playback artifact.
- Decision: Для уже принятых файлов без playback m4a нужен безопасный автоматический reprocess/backfill path, не требующий действий пользователя или администратора.
- Decision: Ошибки подготовки playback artifact должны быть видны как статус записи, но не должны превращаться в silent broken review.
- Decision: Retention/deletion/audit должны учитывать новый playback artifact как controlled meeting content.
- Decision: Existing ingest/finalize остается единственной границей принятия source media для manual uploads and first-party recordings.
- Decision: 099 не создает новый upload/finalize service, новый playback assembly service или альтернативный source-of-truth для record ownership.
- Decision: Normalization starts only from accepted source artifacts and must not consume raw in-flight upload bodies or unfinalized upload parts.
- Decision: Normalization, automatic backfill and automatic retry must preserve the resource-bounded safety baseline: no full source-media buffering in user-facing request paths and no on-demand playback assembly.
- Decision: Temporary normalization outputs are never playback-ready until they are complete, validated, registered and lifecycle-accounted.
- Decision: Transcript processing and playback normalization may run in the same broad record lifecycle, but their statuses must remain independently truthful.
- Decision: Для media с несколькими аудиодорожками используется только единственная дорожка, однозначно помеченная контейнером как основная. Если usable-дорожка одна, используется она; если однозначного выбора нет, normalization завершается понятной ошибкой без выбора первой дорожки наугад, смешивания дорожек или нового selector UI.
- Decision: Пользователь и workspace owner/admin не запускают manual retry, reprocess или backfill. Поддерживаемый исправный accepted source автоматически должен дойти до valid playback m4a; временные infrastructure failures повторяются системой, а старые eligible records обрабатываются автоматическими bounded batches.
- Decision: Для legacy records система применяет тот же canonical gate: сохраняет уже валидный playback m4a, автоматически пересоздаёт невалидный artifact из retained accepted source и не фабрикует звук, если source утрачен или небезопасен; такой случай получает final unavailable state и safe operational alert.
- Decision: Normalization автоматически планируется после появления accepted source и не ждёт завершения transcript/summary processing; точный durable trigger и bounded scheduling mechanism определяются в implementation plan.
- Decision: Raw source file names не попадают в diagnostics, audit или committed evidence; пользовательское имя может отображаться только в уже авторизованной record UI по существующим access rules.

## Scope Summary

099 описывает нормализацию playback audio для recordings and manual uploads. Это не новая upload modal, не календарный matching, не speaker naming и не новый MediaScribe contract. Это lifecycle-фича: после того как запись создана и media accepted, у записи должен появиться стандартный playback artifact.

### In Scope

- Создание `meeting-review.m4a` для новых first-party recordings, если такой artifact не создан более ранним stage.
- Транскодирование supported manual upload media в `meeting-review.m4a`.
- Проверка валидности playback artifact перед тем, как запись считается fully review-ready.
- Статусы "playback audio preparing", "playback audio ready" и окончательный понятный "playback audio unsupported/failed" без пользовательского retry action.
- Idempotent automatic retry/reprocess/backfill для записей, у которых уже есть исходный файл, но нет валидного `meeting-review.m4a`.
- Lifecycle accounting для retention, deletion, audit и diagnostics.
- Защита от дублей при refresh, network retry, повторном finalize, повторном worker pickup или автоматическом retry.
- Четкое правило названия manual upload: user-entered title wins; otherwise file name.
- Ограничения по supported source formats and unsupported media failure states.
- Сохранение existing accepted-source boundary: normalization consumes accepted source artifacts, not raw upload bodies.
- Resource-bounded normalization/automatic-retry/backfill behavior for large files, near-limit files and multipart accepted sources.
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
- Выбор аудиодорожки пользователем в upload/review UI.
- Promising universal deletion outside GRAF-controlled storage.
- Adding broad new infrastructure when existing processing/lifecycle paths are sufficient.
- Новый параллельный upload/finalize subsystem.
- Direct-to-playback route from arbitrary original upload files.
- On-demand audio assembly/transcoding during user playback request.
- Direct MediaScribe-to-playback artifact ownership.
- Replacing existing single-track/dual-track transcription contracts.
- Ручные retry, reprocess или backfill controls для пользователей и workspace administrators.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Новая запись всегда получает playback audio (Priority: P1)

Как пользователь, который открыл готовую запись, я хочу сразу видеть рабочий player, чтобы запись была пригодна для review без технических деталей про source tracks, codecs или processing pipeline.

**Why this priority**: Playback is core review behavior. Если transcript есть, но audio не играет из-за отсутствующего normalized artifact, пользователь воспринимает запись как сломанную.

**Independent Test**: Создать новую first-party запись обычным recording flow, дождаться review-ready состояния и проверить, что запись имеет valid playback m4a artifact and player can seek/play via range requests.

**Acceptance Scenarios**:

1. **Given** first-party recording successfully finishes, **When** processing reaches review-ready, **Then** the record has a valid playback-ready `meeting-review.m4a`.
2. **Given** the recording already produced a valid m4a artifact earlier in the pipeline, **When** review readiness is evaluated, **Then** the existing artifact is reused and not regenerated.
3. **Given** a recording has transcript data but playback m4a is still preparing, **When** the user opens the list or review page, **Then** the UI shows a non-broken preparing state instead of a dead player.
4. **Given** a recording has no valid playback m4a yet, **When** the user opens review, **Then** playback shows automatic preparation/recovery progress or a final unsupported reason without asking the user to retry or reprocess it.
5. **Given** the user seeks inside playback, **When** range requests are made, **Then** the player reads from the stored m4a artifact and does not trigger new audio assembly.

---

### User Story 2 - Manual upload converts to review m4a (Priority: P1)

Как пользователь, который загрузил audio/video file, я хочу получить такую же запись в кабинете, как после обычной записи, чтобы playback, transcript and status behaved consistently.

**Why this priority**: Manual upload is a major user path. Users should not care whether the original file was WAV, MP3, M4A, MP4, MOV or WebM once GRAF accepted it.

**Independent Test**: Upload supported media file, wait for processing, confirm that source artifact remains available for lifecycle accounting, while review playback uses normalized `meeting-review.m4a`.

**Acceptance Scenarios**:

1. **Given** a supported audio file is uploaded manually, **When** upload is accepted and processing finishes, **Then** the record has normalized `meeting-review.m4a` for playback.
2. **Given** a supported video file with an audio track is uploaded manually, **When** processing finishes, **Then** playback uses the extracted normalized audio artifact rather than the original video container.
3. **Given** user entered a title during upload, **When** processing creates the record, **Then** that title remains the record title.
4. **Given** user did not enter a title during upload, **When** processing creates the record, **Then** the file name is used as the record title.
5. **Given** manual upload is complete, **When** calendar matching features run, **Then** the manual upload is not auto-matched to calendar context.
6. **Given** the original file already is an M4A, **When** normalization checks it, **Then** the system reuses it byte-for-byte only if it fully satisfies the canonical playback profile; a container-layout-only mismatch uses lossless remux, an audio-profile mismatch uses transcoding, and the original remains a separate source artifact.
7. **Given** uploaded media has multiple usable audio tracks, **When** exactly one track is marked as the container default, **Then** normalization uses that track; when no unique default exists, preparation ends with a clear ambiguous-track failure and exposes no playback artifact.

---

### User Story 3 - Automatic retry and refresh do not create duplicates (Priority: P1)

Как пользователь, который обновил страницу или потерял сеть, я хочу, чтобы GRAF сам продолжил подготовку аудио, а не просил меня исправлять обработку и не создавал дубли записей или playback artifacts.

**Why this priority**: Upload and processing are long-running. Refresh and temporary infrastructure failures are normal system conditions, but recovery is product responsibility rather than user work. Idempotency protects both UX and storage cost.

**Independent Test**: Start manual upload processing, refresh the page and inject a transient normalization failure, then verify automatic recovery with only one record and one active playback artifact for the logical upload.

**Acceptance Scenarios**:

1. **Given** upload was accepted and processing started, **When** the page refreshes, **Then** the existing processing state is reused and no second record is created.
2. **Given** finalize or processing dispatch is repeated with the same logical upload identity, **When** the backend receives it again, **Then** it returns or resumes the existing record/work instead of creating duplicates.
3. **Given** m4a normalization worker is retried after timeout, **When** the previous attempt already completed successfully, **Then** the worker observes the ready artifact and exits without overwriting it unexpectedly.
4. **Given** normalization fails transiently, **When** automatic retry policy schedules another attempt, **Then** the same record returns to preparing state and no user action or new record is required.
5. **Given** a previous failed partial artifact exists, **When** automatic retry succeeds, **Then** only the valid final artifact is exposed as playback-ready.
6. **Given** raw upload already finalized into an accepted source artifact, **When** automatic normalization retry or backfill runs, **Then** it uses the accepted source artifact and does not reopen the raw upload body or create another upload session.
7. **Given** two browser tabs observe the same manual upload during automatic recovery, **When** both tabs refresh, **Then** both converge on the same record, same source artifact and same normalization status without exposing a retry control.

---

### User Story 4 - Existing accepted files are backfilled automatically (Priority: P2)

Как пользователь старой записи, я хочу, чтобы GRAF автоматически подготовил для неё playback m4a, чтобы мне не приходилось обращаться к администратору или запускать техническую операцию.

**Why this priority**: The product already has accepted uploads/records from before this normalization rule. We need a controlled migration path without manually repairing each record.

**Independent Test**: Let the system discover records missing valid playback m4a, inspect its metadata-only plan/report, then let a bounded automatic batch process eligible records and confirm that they gain playback without duplicates or title changes.

**Acceptance Scenarios**:

1. **Given** existing records have source media but no valid playback m4a, **When** automatic backfill inventory runs, **Then** it records eligible actions and skip reasons before changing data.
2. **Given** an eligible record is scheduled in a bounded automatic backfill batch, **When** the batch runs, **Then** the record gets one valid playback m4a or a clear final reason without user/admin action.
3. **Given** an existing record already has user-edited title, **When** backfill creates playback artifact, **Then** the title is not changed.
4. **Given** an existing record has no usable source media, **When** backfill evaluates it, **Then** it is skipped with a clear reason and no fake playback artifact is created.
5. **Given** backfill is interrupted, **When** it resumes, **Then** already completed records are not reprocessed unnecessarily.

---

### User Story 5 - Unsupported or unsafe media fails clearly (Priority: P2)

Как пользователь, который загрузил неподдерживаемый или поврежденный файл, я хочу получить понятный статус, чтобы понимать, что файл не удалось подготовить, и не ждать бесконечно.

**Why this priority**: A strict playback contract is useful only if failures are explicit and recoverable. Silent failure would look like broken product behavior.

**Independent Test**: Upload unsupported, corrupted, no-audio, too-large or unsafe media and verify that the system classifies it automatically, exposes no playback m4a and never asks the user to retry an impossible conversion.

**Acceptance Scenarios**:

1. **Given** uploaded media has no audio track, **When** normalization runs, **Then** the record gets a clear unsupported/no-audio failure state.
2. **Given** uploaded media is corrupted or cannot be decoded safely, **When** normalization runs, **Then** the failure is recorded without exposing partial audio as playback-ready.
3. **Given** uploaded media exceeds configured product limits, **When** upload or normalization evaluates it, **Then** the user receives a bounded failure state rather than unbounded processing.
4. **Given** normalization fails due to a transient infrastructure issue, **When** retained source media is still available, **Then** the system retries automatically without requiring source re-upload or user action.
5. **Given** normalization fails due to a permanent unsupported or invalid source, **When** classification completes, **Then** the UI shows a final clear reason and offers no misleading retry action.

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

**Independent Test**: For manual upload and first-party recording, create accepted source media, run normalization/automatic retry/backfill, and verify that every resulting playback state points back to the existing record/source artifact lineage without creating another logical record or competing accepted-source path.

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
- Manual upload has multiple audio tracks with one default, no default or conflicting default markers.
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
- Two automatic retry attempts overlap for the same record.
- Automatic backfill is interrupted and resumed.
- Deletion starts while normalization is running.
- Retention expires source media before automatic retry.
- Retention removes original source media after valid playback m4a exists; lifecycle status must remain truthful about what can still be retried.
- Existing valid playback m4a exists but source media has been purged; retry/backfill must not fabricate source media.
- Same accepted source is observed by automatic retry and scheduled backfill at the same time.
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
- **FR-007**: If a valid playback m4a already exists for a record, repeated processing, automatic retry or backfill MUST NOT create duplicate active playback artifacts.
- **FR-008**: Manual upload title behavior MUST remain stable: user-entered title wins; when no user title exists, the original file name becomes the record title.
- **FR-009**: Manual uploads MUST NOT be automatically matched to calendar events as part of this feature.
- **FR-010**: Normalization, automatic retry and automatic backfill MUST be idempotent across page refreshes, network retries, duplicate finalize calls and duplicate worker pickup.
- **FR-011**: Normalization failure MUST produce a clear machine-readable and user-readable state; transient failures MUST be retried automatically, while permanent invalid/unsupported sources MUST reach a final state without a user retry action.
- **FR-012**: Permanent unsupported media failures MUST be distinguishable from transient infrastructure failures.
- **FR-013**: The system MUST NOT expose partial, temporary or failed normalization outputs as playback-ready artifacts.
- **FR-014**: Existing accepted records without valid playback m4a MUST enter a safe automatic reprocess/backfill path without user or workspace-administrator action.
- **FR-015**: Automatic backfill MUST record a metadata-only inventory/report of planned actions and skip reasons before changing records.
- **FR-016**: Backfill MUST preserve existing record titles and user edits.
- **FR-017**: Backfill MUST skip records without retained usable source media and record a clear skip reason.
- **FR-018**: Playback m4a artifacts MUST participate in retention and deletion accounting as controlled meeting content.
- **FR-019**: Audit events MUST distinguish normalization requested, started, completed, failed, retried, skipped and backfilled.
- **FR-020**: Diagnostics and evidence MUST NOT contain raw audio content, transcript content, signed URLs, provider tokens, credentials or live secret paths.
- **FR-021**: File-size, duration and processing limits MUST be enforced before or during normalization so unsupported inputs cannot cause unbounded resource use.
- **FR-022**: Status shown in the recording list and review page MUST be consistent across refreshes, multiple tabs and reconnects.
- **FR-023**: The system MUST automatically retry failed transient playback preparation without source re-upload while retained source media exists; no user or workspace-administrator retry control is permitted.
- **FR-024**: Automatic retry and reprocess attempts MUST avoid creating new records for the same logical upload or existing record.
- **FR-025**: The implementation MUST include validation for supported source media types, no-audio media, corrupted media, duplicate automatic retry and deletion/retention interaction.
- **FR-026**: Normalization MUST consume only accepted source artifacts that belong to an existing recording lineage; it MUST NOT consume raw in-flight upload bodies, unfinalized upload parts or unmanaged local files.
- **FR-027**: Normalization MUST preserve the existing recording/source lineage across first-party recordings, manual uploads, automatic retry and backfill.
- **FR-028**: 099 MUST NOT introduce a parallel upload/finalize source-of-truth for manual uploads or recordings.
- **FR-029**: Playback preparation MUST preserve bounded-resource behavior for large files and MUST NOT require loading complete source media into user-facing request memory.
- **FR-030**: Temporary normalization outputs MUST remain hidden from playback, export, share and ready-state surfaces until they are complete, validated and registered as canonical playback artifacts.
- **FR-031**: Normalization MUST treat temporary-storage pressure, dependency failure, source missing, source mismatch and decode failure as explicit bounded states, not indefinite processing.
- **FR-032**: Transcript/summary processing status and playback-normalization status MUST remain independently truthful; success in one MUST NOT imply success in the other.
- **FR-033**: Automatic backfill MUST use existing accepted source lineage and MUST NOT create replacement source media for records whose source artifacts are missing, purged or unsafe.
- **FR-034**: If a valid playback m4a exists but source media is unavailable, automatic retry/backfill MUST preserve the existing playback artifact and report that source-based regeneration is unavailable.
- **FR-035**: Normalization MUST include conflict handling for concurrent automatic retry/backfill/worker attempts so only one active canonical playback artifact exists per recording.
- **FR-036**: Deletion or retention actions that begin while normalization is preparing output MUST prevent newly prepared temporary output from becoming playback-ready after the lifecycle state becomes deleting, deleted or audio-purged.
- **FR-037**: Resource and lifecycle failures MUST be observable through safe status/audit metadata without exposing raw file names, raw audio, object keys, signed URLs or private provider payloads.
- **FR-038**: A manually uploaded M4A MUST be reused byte-for-byte only when validation proves full compliance with the canonical playback profile; any mismatch MUST trigger conversion, an audio-profile mismatch MUST trigger transcoding, a container-layout-only mismatch MAY use lossless remux, and the original MUST remain a separate source artifact.
- **FR-039**: Normalization MUST use the only usable audio track or the single container-designated default when multiple usable tracks exist; if no unique track can be selected, it MUST fail with a clear ambiguous-track state and MUST NOT guess, mix tracks or expose a partial playback artifact.
- **FR-040**: Every supported, valid accepted source with usable audio MUST automatically converge to one validated canonical playback m4a without user or workspace-administrator action; only objectively invalid, unsupported or missing-audio sources MAY end in a final non-ready state.
- **FR-041**: Automatic legacy backfill MUST validate any existing playback artifact against the canonical gate, reuse it when valid, regenerate it from retained accepted source when invalid, and produce a final unavailable state plus safe operational alert when neither a valid playback artifact nor usable accepted source exists.
- **FR-042**: Normalization MUST be scheduled automatically after accepted source media becomes available and MUST NOT depend on transcript or summary completion, while playback and transcript statuses remain independently truthful.
- **FR-043**: On worker startup, a retained-source normalization job in automatic retry with the machine-readable reason `worker_interrupted` MUST be re-queued and dispatched immediately with the same job/record lineage; this startup recovery MUST NOT shorten scheduled backoff for any other reason.
- **FR-044**: Automatic temporary-output cleanup MUST NOT select or delete an attempt while its normalization job is `running` or `publishing` with an unexpired worker lease; cleanup MUST remain available after that lease expires or the job leaves its active state.

### Key Entities *(include if feature involves data)*

- **Recording**: User-visible meeting or uploaded media record. It owns title, review status, processing state, lifecycle state and workspace/space ownership.
- **SourceMediaArtifact**: Original captured or uploaded media retained under product policy. It may be needed for processing, automatic retry or backfill, but it is not the direct playback source.
- **PlaybackM4AArtifact**: Canonical review audio artifact used by playback. It must be valid, complete, retained according to policy and tied to one recording.
- **NormalizationJob**: Durable work item that creates or validates playback m4a for one recording.
- **NormalizationStatus**: User-visible and machine-readable state: preparing, automatically retrying, ready, permanently unsupported/failed, skipped, cancelled or blocked.
- **BackfillRun**: System-controlled bounded batch that inventories and automatically reprocesses existing eligible records missing valid playback m4a.
- **AutomaticRetryAttempt**: System-owned retry of transient normalization failure for the same record without user action or duplicate record creation.
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
- **SC-004**: 0 duplicate records are created by refresh, automatic retry, duplicate finalize or duplicate worker pickup for the same logical upload.
- **SC-005**: 0 duplicate active playback m4a artifacts are created for the same recording by automatic retry or backfill.
- **SC-006**: 100% of unsupported/no-audio/corrupt/too-large media cases end in bounded clear states, not indefinite processing.
- **SC-007**: 100% of existing records considered by automatic backfill receive an explicit planned action or skip reason before mutation.
- **SC-008**: 100% of deletion and retention reports include playback m4a status when the record has or had a playback artifact.
- **SC-009**: 100% of user-visible recording titles after manual upload follow the rule: entered title first, file name fallback.
- **SC-010**: 0 logs, diagnostics, specs or validation evidence contain raw audio, transcript content, signed URLs, provider tokens, credentials or live secret paths.
- **SC-011**: Playback for normalized records supports seek/range behavior without full-object memory loading in the playback request path.
- **SC-012**: Transient normalization failures are retried automatically without source re-upload or user/admin action while retained source media exists.
- **SC-013**: 100% of normalization attempts use accepted source artifacts tied to an existing recording lineage.
- **SC-014**: 0 new competing manual-upload or recording-finalize source-of-truth paths are introduced by 099.
- **SC-015**: 0 playback-ready artifacts are exposed from partial, temporary, failed or unvalidated normalization outputs.
- **SC-016**: 100% of concurrent automatic retry/backfill/worker attempts for the same recording converge to one active canonical playback artifact or one clear blocked state.
- **SC-017**: 100% of deletion/retention events that overlap normalization prevent temporary outputs from becoming newly playback-ready after lifecycle state becomes deleting, deleted or audio-purged.
- **SC-018**: 100% of source-missing, source-mismatch, no-temp-storage and decode-failure cases produce bounded user/admin status rather than indefinite processing.
- **SC-019**: 100% of records with transcript-ready but playback-not-ready states show those statuses separately, and 100% of playback-ready but transcript-not-ready records avoid implying transcript success.
- **SC-020**: 100% of supported, valid accepted sources with usable audio reach validated playback-ready state without any user or workspace-administrator retry/reprocess/backfill action.
- **SC-021**: 100% of legacy records evaluated by automatic backfill either reuse a validated playback artifact, regenerate one from retained accepted source, or receive an explicit unavailable reason without fabricated media.
- **SC-022**: 0 supported accepted sources wait for transcript/summary completion before playback normalization is scheduled.
- **SC-023**: 100% of eligible `worker_interrupted` retry-wait jobs selected during worker startup are automatically dispatched without a user/admin action, while retry-wait jobs with another reason remain deferred until their scheduled time.
- **SC-024**: 0 active, unexpired normalization attempts are selected by automatic cleanup; expired or non-active attempts remain eligible for residue cleanup.

## Assumptions

- `meeting-review.m4a` is the canonical review playback artifact for the foreseeable product direction.
- The playback route already expects a stored, valid, range-readable m4a artifact.
- Existing MediaScribe transcription processing is separate from playback normalization; 099 should not require rewriting MediaScribe contract behavior.
- Manual upload source files may be audio or video, but review playback uses extracted/normalized audio, not video playback.
- Some earlier records may lack playback m4a and need controlled automatic backfill.
- User-entered manual upload title and file-name fallback behavior are product-level title rules and must not be broken by automatic backfill.
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

## Planning Inputs Resolved

- The canonical profile, accepted source matrix, duration/source/output limits,
  stream limits, probe and full-decode gates are fixed in
  [playback-normalization-contract.md](./contracts/playback-normalization-contract.md).
- The temporary-storage, worker concurrency, timeout and process-isolation
  budgets are fixed in
  [lifecycle-operations-contract.md](./contracts/lifecycle-operations-contract.md).
- Automatic attempt cycles, long-term recovery cadence, backfill page/batch
  limits and workload priority are fixed in
  [automatic-backfill-contract.md](./contracts/automatic-backfill-contract.md).
