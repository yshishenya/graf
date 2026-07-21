# Feature Specification: Support Incident Reporting

**Feature Branch**: `codex/061-support-incident-reporting`

**Created**: 2026-06-26

**Status**: Implemented and deployed; production secret wiring is recorded

**Input**: User description: "When local recordings cannot be sent automatically,
replace the raw copy-report UX with a safe, metadata-only support incident flow:
primary action `Отправить отчет`, clear success/failure states, fallback
`Скопировать отчет`, server-side validation/redaction/persistence/deduplication,
required private server-side GitHub issue creation, and no audio, transcript, raw
paths, tokens, signed URLs, or private meeting content."

## Product Thesis

When `2brain Rec` cannot automatically deliver a local recording, the user
should not have to understand a diagnostic report or decide where to paste it.
The product should offer one clear action: send a safe support report. The user
receives a readable result and an incident number, while support receives only
metadata that is safe by construction.

This feature builds on `057-local-upload-custody`: local upload remains a product
custody obligation, not a user-managed queue. The existing safe report becomes a
fallback, not the primary user path. This feature must not change the
server-owned WebView meeting list introduced by `058-web-cabinet-htmx-shell`;
native custody UI may offer the support action, while server meeting-list
presentation remains owned by the web cabinet feature.

## Clarifications

### Session 2026-06-26

- Q: What counts as successful report submission for v1? -> A: A server-created private GitHub issue exists with safe user-problem details.
- Q: What must the private GitHub issue contain? -> A: Full safe metadata-only report in a structured best-practice issue format.
- Q: What incident number should the user see after success? -> A: `CUST-{github_issue_number}` from the private GitHub issue.
- Q: How long should the private GitHub issue keep the full safe metadata-only report? -> A: Indefinitely; a triage agent will process issues, so the title mask and labels must follow the project issue canon.
- Q: Where must the server create private GitHub issues? -> A: In the current private project repo `yshishenya/crisp`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Send A Safe Report From A Blocked Local Recording (Priority: P1)

As a meeting owner with a local recording that cannot be sent automatically, I
want to press `Отправить отчет` and receive a clear incident number, so I can
ask for help without handling raw diagnostic text.

**Why this priority**: This is the main UX gap after feature 057. Copying a raw
safe report is safe, but it leaves the user uncertain about what to do next.

**Independent Test**: Put a local recording into a support-owned or
admin-owned blocked custody state, send the report from the native custody UI,
and confirm the user sees a success state with an incident number while the
stored incident contains metadata only.

**Acceptance Scenarios**:

1. **Given** a local recording is in a state where automatic sending cannot
   continue without support or admin review, **When** the user selects
   `Отправить отчет`, **Then** the primary state changes to
   `Отчет отправлен. Мы разберемся. Номер: CUST-{github_issue_number}` only
   after the private GitHub issue for that user problem has been created.
2. **Given** the same blocked local recording remains visible after app restart,
   **When** the user opens the custody details again, **Then** the sent incident
   number is still shown and the report is not silently duplicated.

---

### User Story 2 - Fall Back Safely When The Report Cannot Be Sent (Priority: P2)

As a meeting owner who is offline or whose server cannot accept the report, I
want a calm failure state and a copy fallback, so I still have a safe way to
contact support.

**Why this priority**: The incident path must not make a difficult recording
state worse. Offline and backend failures are expected degraded states.

**Independent Test**: Block the support intake while a safe report is available,
attempt to send it, and confirm the UI offers `Скопировать отчет` without
blaming the user or exposing unsafe content.

**Acceptance Scenarios**:

1. **Given** the report cannot be sent because the app is offline, **When** the
   user selects `Отправить отчет`, **Then** the UI says
   `Не удалось отправить. Скопируйте отчет и отправьте в поддержку.` and shows a
   `Скопировать отчет` fallback button.
2. **Given** support intake is temporarily unavailable, **When** the send action
   fails, **Then** the local custody state and safe report remain available and
   no recovery of the recording is promised.
3. **Given** the user copies the fallback report, **When** the clipboard text is
   inspected, **Then** it contains only the approved metadata fields and no
   meeting content, raw local paths, credentials, tokens, or signed URLs.

---

### User Story 3 - Support Receives A Deduped Metadata-Only Incident (Priority: P3)

As a support or developer reviewer, I want a private, deduped incident record
with enough safe metadata to classify the problem, so I can triage the root
cause without seeing meeting content.

**Why this priority**: Support needs useful evidence, but privacy and
tenant-boundary safety are non-negotiable.

**Independent Test**: Submit multiple reports with the same stable problem code
and safe root-cause fingerprint, then confirm they update one private incident
record and the GitHub issue body follows the required safe structured format.

**Acceptance Scenarios**:

1. **Given** two reports share the same stable problem code, workspace
   fingerprint, app build, and root-cause fingerprint, **When** they are
   accepted, **Then** they update one aggregate incident rather than creating two
   separate support records.
2. **Given** private GitHub issue creation is available, **When** a new
   aggregate incident is accepted, **Then** the issue states that this is a user
   problem, contains the safe metadata-only details needed for support, and
   links back to the private incident record.
3. **Given** private GitHub issue creation is unavailable, **When** a report is
   received, **Then** the incident may be retained internally for retry or audit,
   but the user-facing send action is not successful and the copy fallback is
   shown.
4. **Given** five local records have the same root cause, **When** the user sends
   a report for the group, **Then** support receives one aggregate incident with
   `affected_count=5` and a bounded list of safe recording identities.

### Edge Cases

- A terminal expired local recording with no server identity but retained local
  media must explain: "Автоматическая отправка уже не выполнится. Локальная
  копия сохранена на этом Mac. Отправьте отчет, чтобы мы проверили, можно ли
  помочь."
- Admin or access-policy blockers must explain: "Нужна проверка доступа или
  политики рабочего пространства. Отправьте отчет, мы передадим детали
  поддержке/администратору."
- The UI must never say that a report can be copied without showing an actual
  `Скопировать отчет` button when copying is the fallback action.
- Repeated send attempts for an already accepted incident must return the same
  incident identity or update the aggregate count, not create user-visible spam.
- Reports with unsafe fields, malformed metadata, unsupported schema versions,
  or content-like values must be rejected or redacted before storage and before
  any GitHub issue body is created.
- If the user signs out, changes workspace, or the device identity changes, the
  app must not send a report into the wrong workspace or expose cross-tenant
  incident data.
- The feature must not add native rows to the server-owned WebView meeting list
  or require presentation changes in the server-owned cabinet list.

### Requirement Detail Gates

These gates narrow the wording above so implementation cannot drift.

**Report action availability**:

- `Отправить отчет` is primary only when a metadata-only report is available
  and the current custody owner/path is support, workspace/admin policy, or
  terminal local custody.
- Reportable custody examples are support-owned `cannot_send`,
  admin/access-policy blockers, terminal or retention-expired local media
  retained on this Mac, and processing blocked/failed states where support can
  classify the problem from safe metadata.
- `Отправить отчет` is unavailable while automatic upload can still continue,
  when the normal next user action is sign-in/workspace selection/permission
  grant, when local media is no longer retained, when the item is delivered or
  known by the server, or when the authenticated workspace/user/device scope
  cannot be matched safely.
- `Скопировать отчет` is shown as fallback only when a safe allowlisted local
  report can be built. It must never copy a raw payload that the server rejected
  as unsafe.

**Metadata-only policy**:

- Allowed value classes are schema versions, app/build identifiers, OS and
  locale metadata, safe host/base environment identity without query or path
  secrets, booleans, counts, timestamps, duration/size buckets, safe status
  codes, safe problem codes, and deterministic fingerprints of local/server
  identities.
- Missing safe values use `unknown` or `not_applicable`; values removed by
  redaction use `redacted_metadata`.
- v1 does not allow human names, email addresses, account labels, meeting
  titles, raw file names, raw local paths, transcript text, audio bytes,
  screenshots, raw logs, bearer tokens, cookies, credentials, upload tokens, or
  signed URLs in reports, storage, logs, GitHub issue bodies, comments, tests,
  support exports, or PR evidence.

**Dedupe and aggregation**:

- The dedupe key must be derived from safe root-cause inputs: `problem_code`,
  `failure_category`, `retry_class`, `sync_conflict_state`, safe workspace
  scope/fingerprint, safe device fingerprint, app build, and a safe custody
  root-cause fingerprint.
- Raw local recording ids, raw server ids, paths, URLs, names, emails, and
  meeting content must not participate directly in dedupe.
- One dedupe key maps to one support incident and one private GitHub issue.
  Repeated accepted sends return the existing `CUST-{github_issue_number}` or
  update the same aggregate issue; they must not create user-visible issue
  spam.
- The safe affected identity list is capped at 5 identities in the GitHub issue
  body. Additional matches increase `affected_count` and update aggregate
  timestamps without appending unbounded identities.

**External dependency and configuration failures**:

- GitHub issue creation/update must use bounded server-side timeouts so the
  desktop reaches success or fallback within the `SC-008` timing target.
- GitHub authentication failure, repo privacy check failure, wrong repo,
  missing labels, GitHub rate-limit response, GitHub timeout, and GitHub
  validation errors are all failed sends from the user's perspective and must
  show the same copy fallback when a safe report is available.
- Required GitHub labels must be provisioned before enabling support incident
  submission. Report-time label creation is out of scope for v1.

**Native UX, accessibility, and localization**:

- All visible report actions and status messages must be in Russian, match the
  required copy in this specification, and avoid enum codes as the main
  explanation.
- `Отправить отчет` and `Скопировать отчет` must have accessible names,
  keyboard/focus reachability through the existing native custody surface, and
  status text that remains readable without overlapping neighboring controls.
- The user-facing copy must not promise recording recovery. It may only say
  support will review whether help is possible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The native custody UI MUST present `Отправить отчет` as the primary
  action only for the reportable custody states listed in the Report Action
  Availability gate.
- **FR-002**: The native custody UI MUST keep `Скопировать отчет` as a secondary
  fallback when report sending fails, is unavailable, or is intentionally not
  configured.
- **FR-003**: The user MUST receive a clear success state containing
  `CUST-{github_issue_number}` only after the corresponding private GitHub issue
  has been created or updated for the user-reported problem.
- **FR-004**: The user MUST receive a clear failure/offline state that offers the
  copy fallback and does not blame the user or promise recording recovery.
- **FR-005**: Reports MUST be metadata-only and MUST exclude raw audio,
  transcript text, raw local paths, credentials, bearer tokens, cookies, signed
  URLs, secret values, private meeting content, human-identifying names, email
  addresses, and account labels. v1 may use only safe ids or fingerprints for
  people, workspaces, devices, and recordings.
- **FR-006**: Reports MUST include a schema version, app identity, app version,
  build version, operating system version, architecture, locale, timezone,
  safe environment/base URL identity, safe workspace/user/device identifiers,
  safe local/server recording identities, lifecycle state, upload state,
  retry class, normal user action, failure category, stable problem code,
  sync conflict state, timestamps, retention deadline, server identity presence,
  local media retained flag, data-loss risk flag, server-copy-known flag, upload
  attempt counts and safe timing, last safe problem/status code, upload session
  presence/fingerprint, bounded range mismatch metadata, local file completeness
  profile, local purge state, processing status, ledger schema version, and
  `redaction_state=metadata_only` when each value is available and allowed.
- **FR-007**: Support intake MUST validate and redact incoming reports again
  before storage, even when the desktop already marked the report metadata-only.
- **FR-008**: Support intake MUST persist accepted incidents with tenant/workspace
  boundaries, submitted timestamp, reporter-safe identity, redaction result,
  dedupe key, affected count, current handling status, and private GitHub issue
  linkage.
- **FR-009**: Support intake MUST dedupe and aggregate duplicate root causes by
  the safe root-cause inputs listed in the Dedupe and Aggregation gate,
  increasing `affected_count` and keeping at most 5 safe affected recording
  identities in generated issue content.
- **FR-010**: Support intake MUST be rate limited per safe user, workspace,
  device, and root-cause key so repeated failures cannot create unbounded
  incidents or support tickets; repeated accepted sends for the same dedupe key
  MUST return the existing incident number or update the same aggregate issue.
- **FR-011**: Private GitHub issue creation MUST be performed only server-side
  with server-owned credentials, MUST target the current private project
  repository `yshishenya/crisp`, and MUST create or update private issues only.
- **FR-012**: Report submission MUST NOT be user-visible as successful unless the
  private GitHub issue is created or updated successfully.
- **FR-013**: The primary user-visible incident number MUST be derived from the
  private GitHub issue number as `CUST-{github_issue_number}`. Internal incident
  ids may exist for storage but MUST NOT replace the primary user-visible
  number.
- **FR-014**: The desktop app MUST NOT create tracker issues directly, ask for a
  tracker account, publish incident data to a public tracker, or expose internal
  enum codes as the primary user explanation.
- **FR-015**: The private GitHub issue MUST include the full safe metadata-only
  report using the required structured issue format in this specification.
- **FR-016**: The private GitHub issue MUST use the required title mask and
  managed label set from this specification; support incident issue creation
  MUST fail configuration validation if required labels are missing.
- **FR-017**: The private GitHub issue MUST retain the full safe metadata-only
  report indefinitely for support/developer agent triage unless a confirmed
  privacy/security incident or explicit owner-controlled policy change requires
  manual redaction.
- **FR-018**: GitHub issue bodies, logs, tests, screenshots, PR evidence, and support
  exports MUST be safe by construction and contain no meeting content, raw local
  paths, human names, emails, account labels, tokens, signed URLs, or secrets.
- **FR-019**: User-facing copy MUST translate technical custody states into
  human explanations for terminal expired, admin/access-policy, offline, and
  backend failure states.
- **FR-020**: The feature MUST work without changing the server-owned WebView
  meeting list, duplicating local recordings in that list, or requiring users to
  manage a transport queue.
- **FR-021**: The support report action state MUST be preserved across app
  refreshes and restarts whenever the local custody item is still present,
  including `not_sent`, `sending`, `sent`, `failed_with_copy_fallback`, and
  `unavailable` states.
- **FR-022**: Validation MUST cover redaction, unsafe payload rejection, dedupe,
  rate limiting, backend failure fallback, UI action states, incident-number
  persistence, and private GitHub issue body safety.
- **FR-023**: Native report actions and status messages MUST satisfy the Native
  UX, Accessibility, and Localization gate.
- **FR-024**: External GitHub dependency, configuration, timeout, and rate-limit
  failures MUST follow the External Dependency and Configuration Failures gate.

### Private GitHub Issue Format

The server-created private GitHub issue is a support/developer intake artifact,
not a public user report. It MUST be created in the current private project
repository `yshishenya/crisp` and follow GitHub issue best practices plus this
feature-specific format: clear title, structured Markdown body, labels as
metadata, Russian plain-language sections, and no unsafe content. This format is
normative for the feature; planning may only add stricter privacy checks, not
remove or rename the required sections below. The full safe metadata-only report
remains in the private GitHub issue indefinitely so a support/developer triage
agent can process issues later.

**Title format**:

```text
[061][P1][support/custody] Пользовательская проблема: {human_problem_summary} ({problem_code})
```

Rules:

- `061` identifies this feature family.
- `P1` is the default priority for a blocked local recording that may affect
  custody; use `P0` only when the safe metadata indicates probable data loss at
  scale or active production-wide impact; use `P2` only for retained local media
  with no immediate data-loss risk and no user action blocked.
- `support/custody` is the required area.
- The title MUST say this is a user problem in plain Russian and include the
  stable problem code.
- The title MUST NOT include names, emails, raw local paths, meeting titles,
  transcript text, URLs with secrets, tokens, or raw recording identifiers.

**Required labels**:

Canon labels:

- `needs-triage`
- `feature:061`
- `type:bug`
- `priority:P0`, `priority:P1`, or `priority:P2` based on data-loss risk and
  affected count
- `area:macos`
- `area:api`
- `area:privacy`

Feature-specific labels:

- `source:user-report`
- `privacy:metadata-only`

Optional labels when they materially apply:

- `area:lifecycle` for retention, purge, terminal, or server-copy-known issues
- `area:observability` for report-generation, redaction, logging, or metrics bugs
- `gate:pr-blocker`, `gate:deployment-blocker`, `gate:pre-merge`, or
  `gate:backlog` only when the support agent or developer explicitly classifies
  the incident as blocking that gate

Label rules:

- The managed labels above MUST exist before support incident issue creation is
  enabled; missing labels are a configuration failure, not a reason to create
  issues without tags.
- The target repository MUST be exactly `yshishenya/crisp` and MUST be confirmed
  private before creating or updating an issue.
- Do not create dynamic per-problem-code labels. Put `problem_code`,
  `dedupe_key`, and `affected_count` in the issue body so labels stay bounded
  and useful for agents.

**Required body format**:

````markdown
## Кратко

Пользовательская проблема: {human_problem_summary}. Отчет безопасный:
metadata-only, без аудио, транскрипта, raw paths, токенов, signed URL и
приватного содержимого встречи.

## Контекст

- Фича: `061-support-incident-reporting`
- Приоритет: `{priority}`
- Область: `support/custody`
- Spec tasks: `{spec_task_ids_or_not_created_yet}`
- Источник: user report
- Гейт: support triage
- Связанные issues: `{related_issue_numbers_or_none}`

## Проблема

Пользователь нажал `Отправить отчет`, потому что локальная запись не может быть
отправлена автоматически. Пользовательский результат: `{user_visible_result}`.
Номер для пользователя: `CUST-{github_issue_number}`.

Не обещать восстановление записи, если оно не доказано.

## Проверенные факты

- Problem code: `{problem_code}`
- Failure category: `{failure_category}`
- Retry class: `{retry_class}`
- Normal user action: `{normal_user_action}`
- Dedupe key: `{dedupe_key}`
- Affected count: `{affected_count}`
- Data loss risk: `{data_loss_risk}`
- Server copy known: `{server_copy_known}`
- Server identity present: `{server_identity_present}`
- Local media retained: `{local_media_retained}`
- Retention deadline: `{retention_deadline}`
- Redaction state: `metadata_only`

Full safe metadata-only report:

```json
{full_safe_metadata_only_report_json}
```

## Границы задачи

Входит:
- Проверить пользовательскую проблему по safe metadata-only отчету.
- Учесть dedupe и affected_count.
- Проверить, нужна ли помощь support/admin/developer.

Не входит:
- Восстановление записи без доказанной возможности.
- Запрос у пользователя аудио, transcript text, raw paths, токенов или signed URL.
- Изменение server-owned WebView meeting list.

Приватность:
- В issue запрещены audio bytes, transcript text, private meeting content.
- В issue запрещены raw local paths и file names that reveal private content.
- В issue запрещены bearer tokens, cookies, credentials, signed URLs, upload tokens.
- В issue запрещены human names, emails, account labels, screenshots, raw logs,
  or attachments containing meeting content.

## Критерии приемки

- [ ] GitHub issue body contains only allowed metadata.
- [ ] Dedupe/affected_count is correct.
- [ ] User-facing copy does not expose internal enum codes as the main explanation.
- [ ] No server-owned WebView meeting-list change is required by this incident.
- [ ] The user-visible incident number is `CUST-{github_issue_number}`.

## Что проверить перед закрытием

- [ ] Redaction validation passed server-side.
- [ ] GitHub issue body still contains the full safe metadata-only report.
- [ ] Linked private incident record matches this GitHub issue number.
- [ ] No forbidden content appears in issue body, comments, logs, screenshots, or evidence.

## Заметки по реализации

- Full metadata-only issue details are retained indefinitely in this private
  GitHub issue for support/developer agent triage.
- Aggregate incident: `{incident_id}`
- Existing GitHub issue: `{github_issue_number_or_none}`
- Safe affected identities: `{max_5_safe_identity_list}`
- Last duplicate received at: `{last_duplicate_received_at}`

## Ссылки

- Private incident record: `{private_incident_link_or_id}`
- Related private GitHub issue: `{issue_url}`
- Spec: `specs/061-support-incident-reporting/spec.md`
````

Issue body rules:

- The body MUST include the full approved metadata-only report directly in a
  fenced JSON block so support can inspect the issue without opening another
  system.
- The body MUST also include a short human summary before the JSON block so the
  issue is triageable from a GitHub list view and readable by non-engineers.
- The body MUST preserve the canonical section order shown above, matching the
  project GitHub issue canon: `Кратко`, `Контекст`, `Проблема`,
  `Проверенные факты`, `Границы задачи`, `Критерии приемки`,
  `Что проверить перед закрытием`, `Заметки по реализации`, `Ссылки`.
- The JSON block MUST be generated after server-side redaction, not copied
  blindly from the desktop payload.
- The JSON block MUST use stable snake_case field names and deterministic key
  order for safe diffing and duplicate comparison.
- Required safe fields MUST stay present in the JSON block. If a safe value is
  unavailable, not applicable, or removed by redaction, the field value MUST be
  `unknown`, `not_applicable`, or `redacted_metadata` instead of omitting or
  renaming the field.
- The safe affected identity list MUST be bounded to at most 5 values.
  Additional matching reports update `affected_count`, timestamps, and the
  private incident record instead of appending unbounded identities to the issue
  body.
- Updating an existing deduped issue MUST preserve human sections and replace
  only the generated safe metadata block and aggregate counters.
- Closing the issue MUST NOT remove the full safe metadata-only report. Manual
  redaction may happen only for a confirmed privacy/security incident or an
  explicit owner-controlled retention policy change.
- The user-visible incident number MUST be `CUST-{github_issue_number}` for both
  newly created and updated deduped issues.
- GitHub issue creation/update MUST use authenticated server-side requests,
  avoid concurrent mutative requests for the same dedupe key, respect GitHub
  rate-limit responses, and surface failure to the desktop as the copy-fallback
  state.
- If the target repository is public or cannot be confirmed private, the server
  MUST NOT create the issue and MUST return the fallback failure state.
- If the configured target repository is not `yshishenya/crisp`, the server MUST
  treat configuration as invalid and return the fallback failure state.

### Key Entities *(include if feature involves data)*

- **Support Incident Report**: Metadata-only report assembled for a local
  custody problem. It represents the app/system/user/workspace/device context,
  safe recording identities, custody lifecycle state, upload/retry state,
  failure classification, and file completeness profile without content or
  secrets.
- **Support Incident**: Persisted private support record created from an accepted
  report. It has an incident number, tenant/workspace scope, dedupe key,
  redaction status, affected count, bounded safe affected identities, current
  status, private GitHub issue linkage, and the primary user-visible number
  `CUST-{github_issue_number}`.
- **Dedupe Key**: Safe root-cause fingerprint derived from stable problem code
  and non-sensitive context. It groups repeated reports for the same issue.
- **Private GitHub Issue**: Required private support/developer issue created or
  updated from a persisted incident before user-visible send success. It must be
  labeled and worded as a user problem, follow the required title/body/label
  format, contain the full safe metadata-only report, and must never be created
  directly by the desktop app.
- **Report Submission State**: Native UI state for a custody item or aggregate
  group: not sent, sending, sent with incident number, failed with copy fallback,
  or unavailable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 95% of users who encounter a reportable custody blocker
  can reach either `Отправить отчет` or `Скопировать отчет` from the visible
  custody UI in one action.
- **SC-002**: 100% of successful submissions create or update a private GitHub
  issue, return `CUST-{github_issue_number}` as the user-visible incident
  number, and remain visible for the same local custody item after app refresh.
- **SC-003**: 100% of stored incidents, copied fallback reports, logs, GitHub
  issue bodies, and validation evidence contain no audio, transcript text, raw
  local paths, credentials, bearer tokens, cookies, signed URLs, or private
  meeting content.
- **SC-004**: 100% of private GitHub issues created by this feature follow the
  required title, label, and body format, including the full server-redacted
  metadata-only JSON block.
- **SC-005**: 100% of private GitHub issues created by this feature are created
  in `yshishenya/crisp` after confirming the repository is private.
- **SC-006**: 100% of closed private GitHub issues created by this feature retain
  the full safe metadata-only report unless a confirmed privacy/security
  incident or explicit owner-controlled policy change required manual redaction.
- **SC-007**: Duplicate reports with the same root cause aggregate into one
  incident with the correct affected count in at least 95% of tested duplicate
  scenarios.
- **SC-008**: Offline or unavailable support intake states complete with a
  user-readable failure message and copy fallback in under 5 seconds in local
  validation.
- **SC-009**: Support reviewers can classify the problem category, custody
  lifecycle state, data-loss risk, and next ownership path from the incident
  metadata in 90% of seeded custody failure scenarios without requesting raw
  meeting content.
- **SC-010**: The server-owned WebView meeting list remains unchanged by this
  feature in 100% of validation scenarios.

## Assumptions

- This is a high-risk product/privacy/diagnostics feature and must continue
  through `$speckit-clarify`, `$speckit-plan`, `$speckit-checklist`,
  `$speckit-tasks`, `$speckit-analyze`, `$speckit-taskstoissues`, and
  `$speckit-implement` before code changes.
- The feature number is `061` because local branches already reserve `059` and
  `060`; the spec directory is independent from the branch name.
- Feature 057 provides the local custody projection and safe report foundation;
  this feature may refine report fields and action states but does not replace
  the local upload queue.
- Feature 058 owns server WebView/cabinet presentation; this feature may define
  support incident data and actions without changing the meeting-list UI.
- Private GitHub issue creation is required for v1 user-visible success; any
  internally retained incident without an issue remains a failed send from the
  user's perspective and must show the copy fallback.
- Full safe metadata-only reports remain in private GitHub issues indefinitely
  for support/developer triage agent processing.
- The support issue target is the current private project repository
  `yshishenya/crisp`; support incident issue creation must not silently fall
  back to any other repository.
