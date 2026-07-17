# Текущий статус продукта

Date: 2026-07-17

Этот документ коротко фиксирует состояние продукта на текущей ветке
реализации. PRD остается базовой продуктовой линией; feature specs и
metadata-only evidence остаются подробной историей реализации.

## Accepted Now

- macOS is the selected MVP platform.
- The current macOS product identity is `GRAF.app` with bundle id
  `pro.2brain.graf`.
- Feature `100-provider-link-verified-callback` is merged, released as
  [`v2026.07.17.1`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.17.1)
  and deployed to production at `744b3ad25cf52cdb119b37a1900f14928428ee4b`.
  It adds a server-verified, explicit flow for a
  signed-in user to add another provider: callback stores only a temporary
  candidate and never issues or switches a GRAF session; only the exact
  initiating user/workspace/session may confirm. Browser and embedded Settings
  reuse one safe provider-only surface. Expired/replayed/rejected candidates are
  scrubbed and audit stores only codes plus a one-way intent fingerprint.
  Canonical local CI passes (`643` macOS tests, `1757` server tests, `28`
  expected PostgreSQL-only skips, Ruff, compile, Compose and deployment-evidence
  scan). A disposable local PostgreSQL RLS module passes 16/16 with zero
  database residue. Production dry-run and deploy pass; the deploy created a
  protected backup point, public health/readiness and metadata-only smoke pass,
  and the actual browser and embedded Settings pages show the same safe
  provider-only start surface without starting a provider flow.
  The standalone formal Codex Security scan for deferred feature `097` remains
  out of this feature's evidence by user instruction.
- Feature `105-macos-app-updates` is merged and live on the owner-only production
  channel as
  [`v2026.07.17.9`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.17.9)
  at exact merge `d6debe22b799e37f08fcbf77bec9b5123338acf7` through
  [#3702](https://github.com/yshishenya/crisp/pull/3702) and
  [#3703](https://github.com/yshishenya/crisp/pull/3703). The app embeds exact
  Sparkle `2.9.4`, checks the signed stable feed every 24 hours, exposes
  `GRAF > Check for Updates…`, and shows one VoiceOver-accessible
  `Доступно обновление` marker in both connected-cabinet and local-only sidebars.
  Automatic install and system profiling remain disabled. Update presentation
  and relaunch stay deferred while capture is active or paused, recording is
  starting/stopping/finalizing, or termination cleanup is pending. Production
  staging now fails closed unless the worktree is clean, `HEAD` equals
  `origin/master`, and the exact published CalVer tag points to that commit;
  versioned archives, packages, GitHub Release assets, and public checksums are
  verified before the appcast is replaced last. The installed `.9` keeps the
  stable `GRAF.app` / `pro.2brain.graf` designated requirement and retained
  microphone plus Screen/System Audio grants through sequential same-identity
  updates without TCC mutation. Its 120-second ScreenCaptureKit windows passed
  an installed-app start lasting 76 seconds and a successful Stop/finalization
  without false `capture_failed`. Focused rejection checks cover corrupt,
  unsigned, wrong-key, downgrade, incompatible, and wrong-identity updates;
  full CI passes 666 macOS tests and 1761 server tests with 28 expected skips.
  Existing installations without Sparkle still need one trusted `.pkg`
  bootstrap. This owner-only self-signed channel is not public Developer ID
  distribution; notarization, stapling, public Gatekeeper proof, and signing-
  identity migration remain deferred until Apple Developer access is available.
- Feature `095-macos-permission-retention` is implemented for local
  owner-machine validation: GRAF can be built with an explicit locally trusted
  self-signed app identity, same-identity reinstalls preserve already granted
  microphone and Screen/System Audio permissions on the validated Mac, and
  permission onboarding/AppKit sheets are dismissed during bounded termination
  cleanup so macOS quit/relaunch is not blocked. This is not public
  distribution readiness: Apple Developer account, Developer ID Application
  and Installer signing, notarization, stapling, and public Gatekeeper
  validation remain separate release-gate work. Release `v2026.07.09.6`
  refreshes the public download package with the local self-signed build so
  the owner machine can update from the hosted package while the Developer ID
  path remains out of scope.
- Feature `098-calendar-auto-context-match` is implemented, released and live
  in production. Feature PR
  [#3270](https://github.com/yshishenya/crisp/pull/3270) merged as
  `979dc497c1575baa886ce5d74d414e898f5ea464`; feature release
  [`v2026.07.13.2`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.13.2)
  introduced the behavior, and smoke-cleanup hotfix
  [`v2026.07.13.3`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.13.3)
  is deployed at exact SHA `f0e3ee4aef81c5d7a58cf632b6513b7f38414dc9`.
  A desktop recording start may request a server-owned,
  24-hour match attempt without blocking capture; the deterministic matcher
  accepts only one fresh eligible event, keeps overlaps/back-to-back cases
  ambiguous, and safely skips private/free-busy, all-day, stale, manual-upload
  and offline/unknown paths. Meeting creation atomically consumes only a
  same-owner/same-workspace attempt and persists one immutable context snapshot
  with safe title, time, bounded roster and hashed recurring-series evidence.
  Replaceable app/generic titles may use the safe calendar title; user,
  upload/file and legacy titles remain authoritative, and visible titles remain
  stable after correction or clear. Browser and embedded review reuse the same
  owner-managed chooser, no-context explanations, roster-not-speaker copy and
  independently authorized previous-series pointer. Calendar participants do
  not create access, shares, recipients, delivery or speaker-name assignment.
  Current focused evidence passes `145` unit/read-model, `99` contract, `162`
  integration, `195` focused macOS and `72` authorization/privacy tests;
  SQLite migration checks and disposable PostgreSQL/RLS probes pass with
  cleanup. Canonical local CI also passes with `631` macOS tests, `1414` server
  tests passed and `4` skipped, Ruff, compile, Compose rendering and deployment
  evidence scan. Its intentionally non-live RLS boundary reports that a
  PostgreSQL test URL is required; the separate disposable PostgreSQL/RLS run
  is the database receipt. User-approved Chrome QA also passes the web and
  embedded list/matched/recurring/ambiguity/correction/clear flow with keyboard
  focus and durable-state checks. That pass found and closed an invalid nested
  chooser-link/grid-wrap defect before the final screenshot rerun. Production
  is at migration `0021_calendar_auto_context_match (head)`; backup and restore
  rehearsal, RLS verification, synthetic no-context upload, cleanup, public
  live/ready probes and an independent zero-residue read-back all pass. The
  clear/ambiguous and browser/embedded receipts remain synthetic same-code QA,
  not a claim that private production calendars were inspected. Older app
  builds must be updated to gain feature 098; the server-only `.3` hotfix has
  no `apps/macos` diff and requires no additional reinstall. Feature `097` and
  its resumable standalone Codex Security scan stay separately deferred by
  user instruction and are not counted as 098 acceptance evidence.
- Feature `099-review-m4a-normalization` is implemented, validated and merged
  through [PR #3470](https://github.com/yshishenya/crisp/pull/3470) at exact
  merge SHA `da8b22ea069202d9d9961f9a4f46dd4192821da3`. Release
  `v2026.07.15.1` is tagged and published from exact release-preparation merge
  SHA `619c6ce3600d2d56e3461b69d523c4240ec8767a`. Its first production deploy
  stopped safely before migration/runtime mutation because the deploy script
  looked for the newly built media-worker image through an existing-container
  inventory. Staged rollback restored the prior production SHA and a clean
  worktree. The minimal image-resolution hotfix is merged through
  [PR #3472](https://github.com/yshishenya/crisp/pull/3472) at exact merge SHA
  `9081a942040d19819119feb6cf043c603514e401`. It passes independent review,
  its executable success/no-match/inspect-failure regression and fresh
  canonical CI: macOS `643/643`, server `1716 passed, 21 skipped`, Ruff,
  compile, Compose rendering and deployment evidence. Release
  `v2026.07.15.2` is published from exact release-preparation merge SHA
  `13fe923421df60da77a0b936a8b04cd63db6f891`. Its deploy passed backup,
  restore rehearsal, image/profile gates and migration `0022`, then stopped
  before dispatch because the non-root database-role bootstrap could not read
  a newly generated file-backed credential. Staged rollback returned schema to
  `0021`, restored production SHA
  `e77f942bf178862905ee98b27488d87e469c3e26`, and confirmed zero feature truth.
  A bounded private-group readability hotfix passed focused tests, fresh
  canonical CI and independent review from exact `.2` release SHA, then merged
  through [PR #3474](https://github.com/yshishenya/crisp/pull/3474) at exact
  merge SHA `f0fbd18bb7cf18410da16bda2f6ca7177b40ce98`. Release
  `v2026.07.16.1` was published, but its deploy stopped before dispatch because
  the restricted media role could not read the schema version. The narrow
  permission hotfix merged through
  [PR #3522](https://github.com/yshishenya/crisp/pull/3522), and release
  `v2026.07.16.2` was published. Its deploy applied migration `0022` and
  validated the media worker, then production smoke stopped on the stricter
  RLS boundary. Compatibility rollback kept the `.2` source and additive
  schema, disabled normalization/dispatch, removed the media worker and left
  public live/ready healthy with zero smoke residue. The corrective RLS/smoke
  hotfix passed real PostgreSQL tests, full CI and independent review, then
  merged through [PR #3524](https://github.com/yshishenya/crisp/pull/3524) at
  exact merge SHA `ff34413994d8e15f64149e7470db6539f2d7180c`. Candidate
  `v2026.07.16.3` is prepared from that merge and still requires release PR,
  publication, production deploy and E2E evidence.
  The feature gives every new first-party recording and supported manual
  upload one server-prepared,
  fully decoded canonical `meeting-review.m4a`; an already canonical M4A is
  reused byte-for-byte, a layout-only mismatch is remuxed without audio loss,
  and every other supported valid retained source is converted automatically.
  The user and workspace administrator receive no retry, repair, reprocess or
  backfill action: transient failures remain automatic, while only objectively
  invalid, unsupported, no-audio or missing retained sources can finish with a
  clear unavailable reason. Existing records are inventoried before mutation
  and then reuse, regenerate or report unavailable without fabricating source
  media. Playback uses only the validated canonical object, supports byte
  ranges without full-object request memory, and keeps playback readiness
  independent from transcript/summary readiness. Candidate, source, attempt
  and canonical objects participate in RLS, retention and deletion accounting;
  deletion wins every tested queued/running/publishing/retry race. The new
  `0022_playback_normalization` migration and isolated non-root media worker
  are required at deploy. The worker has one-activity concurrency, 1 CPU,
  1 GiB memory, 128 PIDs, a 6 GiB logical work budget, a 128 MiB output cap,
  bounded FFmpeg/FFprobe output and automatic free-capacity preflight. A
  near-four-hour dual-source synthetic package of about 5 GiB completed the
  full local production-equivalent normalization pipeline in `185.236` seconds
  with canonical/full-decode success, zero OOM events and zero
  container/volume/image residue. Focused
  evidence currently includes `497` focused server tests, a post-fix
  `21`-test resource/workflow/worker regression, `42` migration-focused and a
  final `19/19` disposable PostgreSQL/RLS role-policy run, `139` unchanged
  macOS regressions, the 14-case container matrix, authorized working-copy
  conversion with original hashes preserved, and deletion/cleanup evidence.
  The validated feature branch was integrated onto the `.7` interface base
  before merge. Canonical repository CI passes on that integrated candidate:
  macOS `643/643`, server `1713 passed, 21 skipped`, Ruff, Python compile,
  Compose rendering and deployment-evidence scan, with
  `ci_local_result=pass` and exit code `0`; a fresh native disposable
  PostgreSQL run also passes `23/23` plus the direct RLS probe with zero
  cluster residue. After independent review found a transaction-local tenant
  context gap across internal commits, the central PostgreSQL session boundary
  was repaired and its three exact restricted-media-role regressions plus the
  full normalization PostgreSQL file passed `3/3` and `12/12` respectively.
  T100 local synthetic UI acceptance is complete. Real Chrome and the embedded
  macOS cabinet show the same preparing/ready/unavailable and
  transcript-independent states with no repair control. Chrome Play/Pause held
  `10.9s`, forward seek reached `25.9s`, two tabs shared durable status while
  keeping independent playback position, and automatic preparing-to-ready
  refresh produced another Play/Pause/seek sequence through `24.5s`. The
  backend returned `206` with `Content-Range: bytes 0-35620/35621`. Embedded
  Play/Pause held `2.3s`, forward seeks reached `17.3s` and `32.3s`, and a
  post-seek cycle held `33.7s`; app close did not stop publication and relaunch
  read `Аудио готово`. Wide/narrow, keyboard focus, system light/dark
  preference and reduced-motion checks pass, with no Chrome console errors.
  A post-merge-base Chrome rerun against the `.7` cabinet also passed: the
  preparing state automatically became a `readyState=4` player, Play reached
  `1.935s`, Pause held `10.532s`, seek reached `25.532s`, and the browser
  received the same `206` Range response. Both `1440x900` and `740x900` had no
  horizontal overflow, reduced motion remained bounded, and cleanup residue
  was zero. The final browser pass also recovered automatically from synthetic
  `503`, login-redirect and disconnect responses with visible status copy; a
  confirmed delete changed an already-polling detail to the terminal
  unavailable state, returned `404` and did not resurrect the player after a
  delayed publication attempt.
  The initial control-channel-only top-level navigation block was recovered by
  the documented manual URL handoff; it is no longer a T100 limitation.
  Feature 099 changes server behavior and macOS regression tests only; it has
  no native macOS runtime-source diff, so this hotfix does not require an app
  rebuild or reinstall. The narrow follow-up cleanup fix is released as
  `v2026.07.17.5`: its active-lease selector and migration
  `0026_active_cleanup` are deployed. The previously interrupted production
  conversion reached canonical playback-ready state automatically; no retry,
  upload, or other user action was needed. Broader T115 browser/embedded
  production proof and T116 full feature issue cleanup remain separately open.
  Feature 097 and its resumable standalone Codex Security scan remain deferred
  and untouched; ordinary 099 authorization/RLS/subprocess/privacy gates do not
  complete it. Release `v2026.07.14.7` remains owned by the separate «новый
  главный экран GRAF» rollout. None of the immutable feature-099 release tags
  were moved. The next candidate is `v2026.07.16.3`; its hotfix merge and
  explicit production-deploy approval are recorded, while release publication,
  deploy and production proof remain pending.
  Current production evidence supersedes that historical candidate note:
  `v2026.07.17.3` deployed the startup-recovery fix and immediately dispatched
  the retained affected job, but its next cleanup pass exposed a separate
  active-attempt cleanup race before canonical publication. The narrow
  follow-up was released and deployed as `v2026.07.17.5`; the same job now has
  canonical playback-ready state without user action. Feature 097 remains
  deferred and is not part of this proof.
- The macOS recording path is app-owned: ScreenCaptureKit system audio and the
  app-owned microphone source are explicitly injected into
  `LocalRecordingWriter`, which finalizes `mic.wav`, `incoming.wav`, and
  `manifest.json`.
- The former separate audio-routing component, shared-memory bridge,
  lifecycle scripts, route orchestration, and user-facing setup/repair states
  have been removed from the source and app-only package surface.
- Current packaging contains one desktop application component and performs no
  privileged audio installation or Core Audio service mutation.
- Historical recording roots and unknown manifest fields remain readable for
  data compatibility; current recordings do not emit retired routing state.
- Generic Core Audio microphone discovery and metadata-only `AudioHAL`
  meeting-detection signals remain current OS integrations and are not the
  removed component.
- Diagnostics and validation artifacts remain metadata-only and must not include
  raw audio, transcript text, credentials, tokens, signed URLs, passwords, or
  meeting content.
- Public landing analytics from feature `093-public-landing-analytics` is live
  on production for `/` and `/download` only. It uses Yandex Metrica public
  page events, UTM/source attribution, consent-gated Webvisor/replay, and
  runtime-only provider configuration. Production deploy, provider smoke,
  rendered-page checks, negative `/login` scope check, and GitHub issue closeout
  passed on 2026-07-08. Paid campaign launch remains blocked until legal and
  campaign-readiness approval. Product activation analytics is not included in
  093 and is tracked as feature `094-product-activation-analytics`.
- Feature `094-product-activation-analytics` now has a safe implementation
  scaffold for product activation analytics without production provider launch.
  It defines the activation funnel from public download intent through first
  value, disabled-by-default runtime config, forbidden-field rejection,
  pseudonymous identity helpers, a mandatory product telemetry gate model,
  PostHog/Yandex provider-disabled wrappers, server-mediated validation API,
  macOS payload/client shell, env propagation checks, smoke helpers, dashboard
  evidence template, and rollout documentation. Live PostHog setup, Yandex
  all-pages expansion, Yandex offline conversion upload, production deploy, and
  paid campaign optimization remain blocked pending separate legal/product/
  security/QA/provider approval.
- Manual user-facing `Record`/`Stop` exists in the local macOS app with visible
  recording state and one-action stop from feature `007`.
- Local recording persistence from feature `008` is accepted for local artifact
  creation after manual `Record`/`Stop`: local mic track, remote speaker track,
  metadata-only manifest, saved/degraded/failed truth, and metadata-only
  diagnostics.
- One-minute manual recording smoke is accepted for Yandex Telemost, Chrome,
  Opera, and Zoom for features `007` and `008`: visible manual recording,
  one-action stop, and saved local recording artifacts.
- Feature `022-meeting-mute-truth` is implemented as the product-owned mute
  truth layer for local macOS recording. The desktop app exposes `Pause` and
  `Resume` beside always-available `Stop`; product Pause suppresses local
  microphone capture and records metadata-only privacy segments in
  `manifest.json`; unsupported/deferred meeting targets fail closed as
  `meeting_mute_unproven`, `unsupported`, `degraded`, or `failed`, never as a
  meeting-app-mute-respecting claim. Target-specific QA fixtures, validation
  script coverage, diagnostics redaction, and upload-queue regressions are
  included. This slice does not implement third-party Zoom/Telemost mute
  adapters or claim that meeting-app mute itself is respected.
- MediaScribe dual-track API contract is recorded in
  `docs/integrations/mediascribe-dual-track-api.md` for future backend
  transcription work. The real API key is intentionally not committed.
- Feature `010-recording-artifact-format` is accepted for local artifact
  format. Automated gates and a fresh manual `Record`/`Stop` smoke on
  2026-06-04 MSK confirmed a local package with `manifest.json`, `mic.wav`,
  `incoming.wav`, dual-track MediaScribe role mapping, readiness metadata,
  diagnostics redaction, and `007`/`008` regression validation.
- Feature `011-assisted-auto-recording` is specified but not planned or
  implemented. It records the future detect-and-ask rollout, automatic naming
  policy, and local-trust-shell/server-dashboard UI authority model.
- Feature `092-automatic-meeting-detection` is implemented locally as the first
  registry-driven detect-and-ask foundation for the Russian-market VKS scope.
  It adds server-side metadata-only meeting-detection telemetry, admin candidate
  review and registry publishing, RLS-covered registry/candidate tables, a
  server-published macOS target registry with last-good client cache, low-noise
  candidate rollups, macOS `AudioHAL` app-ownership parsing,
  detector debounce/end state, target-scoped prompt/auto-record policy gates,
  metadata-only diagnostics, meeting-detection settings with app auto-record
  checkboxes, and
  browser metadata plus calendar/join-intent foundation without requiring a
  browser extension. Prompt-capable first targets remain limited to locally
  verified native Zoom and Yandex Telemost paths; browser targets, unverified
  native apps, and unsupported metadata states stay detect-only/manual-only
  until separate live validation promotes them. This slice is local
  implementation readiness only: it is not committed, merged, released,
  deployed, or production-rollout evidence. Critical review remediation on
  2026-07-08 connected the native `AudioHAL` log stream to
  prompt/auto-record decisioning, moved the registry source to server publish
  plus last-good client cache,
  hardened browser-target validation, added candidate/non-target uniqueness,
  rejected admin merges into unknown target ids, and refreshed focused/full
  local validation evidence. Convergence remediation on 2026-07-09 routes
  prompt/auto-record eligibility through the existing recording prerequisite
  gate, expands the prompt with safe capture mode/source/policy/reason copy,
  scopes the `AudioHAL` log predicate to RunningBoard, records a passing
  10-minute resource gate, explicitly keeps Microsoft Teams diagnostic-only
  until installed runtime validation is available, and documents Firefox/
  non-Chromium browser metadata as manual-only when no safe adapter exists.
- Feature `012-server-ingest-foundation` is implemented as the first backend
  foundation slice in this repository: FastAPI ingest service scaffold,
  local/prod Docker Compose stacks, Postgres/Alembic schema models, MinIO
  server-mediated object boundary, provider-neutral tenant/device request
  checks, upload/session APIs, resumable/idempotent part acceptance, safe
  audit/logging helpers, status contracts, and inert processing placeholders.
  Final review remediation on 2026-06-04 added persistence/storage, forged-auth,
  missing-range, readiness, and lint coverage; local validation passed `36`
  server tests, Ruff, compileall, and compose config rendering. It does not
  deploy production, implement the desktop uploader, start Temporal workflows,
  call MediaScribe, or expose dashboard/share/delete surfaces.
- A second five-round review hackathon on 2026-06-04 found that 012 was not
  PR-ready until Phase 11 remediation completed. Phase 11 tasks T119-T180 and
  GitHub issues #112-#124 have now been remediated locally with traceability in
  `specs/012-server-ingest-foundation/tasks.md` and validation evidence in
  `specs/012-server-ingest-foundation/quickstart.md`. The remaining gate before
  PR/deployment-plan handoff is a final full repository sanity run, review of
  the dirty worktree, and an explicit commit/PR decision.
- Feature `013-federated-auth-foundation` is implemented on the backend and
  provides provider-based auth, workspace membership, session, account linking,
  and registered-device identity scaffolding for later desktop upload.
- Feature `015-mediascribe-processing-pipeline` is implemented as the first
  server-side processing slice after accepted ingest. It adds durable
  processing workflow/job/result/segment/audit/dependency tables, idempotent
  `processing/<meeting_id>` workflow identity, internal pickup, server-side
  dual-track MediaScribe submission from owner-controlled artifacts,
  poll/import services, content-safe processing status, failure/retry
  classification, restart-safe job reuse, and metadata-only dependency truth.
  On 2026-06-11, `master` at `4cda38c` was deployed to
  `2brain.dev:/opt/projects/2brain-rec` with the production processing worker
  and Temporal services running. A real local app recording passed production
  e2e through public upload/finalize, internal pickup, Temporal worker
  processing, live MediaScribe submit/poll, result import, content-safe status,
  and cleanup: workflow `processed`, MediaScribe job `ready`, result
  `imported`, transcript and diarization available, dependency state
  `mediascribe:imported`, and no cleanup residue.
  Desktop clients still do not call MediaScribe, hold MediaScribe credentials,
  receive signed dependency URLs, or receive transcript/audio/download surfaces
  in this slice.
- Feature `016-meeting-dashboard-review` is implemented as the server-owned web
  cabinet for meeting review. It adds authorized meeting list/detail APIs and
  HTML routes, ready/partial/processing/failed states, safe transcript and
  speaker timeline rendering, truthful unavailable states, non-mutating
  governance placeholders, desktop-embedded route variants, responsive
  screenshots, and no-secret/no-private-content validation. It intentionally
  does not execute share/export/download/delete/retention policies or replace
  native desktop capture controls.
- Feature `017-access-sharing-downloads` is implemented as the browser/server
  owned access, sharing, download, and export layer for accepted meeting review
  data. It adds effective owner/team/shared/denied access decisions for list,
  detail, share, download, export, and desktop-embedded routes; login-required
  share grants and revocation; server-mediated artifact downloads;
  policy-filtered export packages; metadata-only access/egress activity; truthful
  post-egress deletion copy; RLS coverage for the new access/egress tables; and
  synthetic screenshot evidence for desktop and compact layouts. It does not
  enable public links, external-recipient invitations, retention execution,
  deletion execution, admin policy editing, billing, or desktop-owned egress
  policy. On 2026-06-16, `master` at
  `39b8c5fbfae74159e5e50f5c2471f19ff64f1e36` was deployed to
  `2brain.dev:/opt/projects/2brain-rec`; production read-only verification
  showed `rec-api` healthy, Alembic `0006_access_sharing_downloads`, and
  `/api/v1/health/live` plus `/api/v1/health/ready` returning ok/ready. This is
  `infra_smoke_ready` evidence, not user rollout readiness.
- Feature `018-retention-deletion-execution` is implemented and production-smoke
  validated as the server-owned retention and deletion execution layer after
  access/share/download/export. It adds whole-meeting deletion requests,
  immediate access blocking for deleting/deleted meetings, metadata-only
  deletion verification reports, retention policy snapshots and scans,
  device-scoped local desktop purge tasks and acknowledgements, truthful backup
  expiry state, MediaScribe/Langfuse/workflow/temp/diagnostics dependency
  limits, post-egress copy limits from existing egress audit, lifecycle activity
  rows, safe retry guidance, and RLS coverage for deletion lifecycle tables.
  Desktop clients can list and acknowledge local purge tasks without uploading
  private proof payloads. On 2026-06-16, `master` at
  `ab875e7ba50f15ff57323581ba0edfa7abd5ad5c` was deployed to production and
  verified within the `infra_smoke_ready` boundary. This slice does not add
  public links, external-recipient invitations, partial deletion, legal-hold
  management, admin retention editing UI, billing, or desktop-owned deletion
  policy.
- Feature `034-mvp-loop-readiness` is implemented as the launch-readiness gate
  over the owner MVP value loop. It produces metadata-only JSON/Markdown
  readiness evidence, a launch gap register, clean-room reference comparison,
  desktop/web/policy lifecycle local-runtime regression evidence, and bounded
  claim rules. Its current outcome is `pilot_blocked`: the strongest production
  claim remains `infra_smoke_ready`, while `mvp_loop_ready`,
  `internal_pilot_candidate`, `user_rollout_ready`, and `production_ready` stay
  excluded until P1 launch blockers are closed.
- Feature `035-mvp-loop-live-evidence` is implemented as the current
  validation-only evidence pack after `022`. It covers the installed
  `/Applications/GRAF.app` desktop loop with Record, Pause, Resume, Stop,
  metadata-safe screenshots, and latest local artifact validation. It also
  checks the production web owner route on `rec.2brain.pro`: `/meetings` exists
  but live owner review remains blocked by `401 missing_auth_context`, while
  list/detail/governance behavior is covered by safe fixture-backed evidence.
  The strongest truthful claim remains `pilot_blocked` with bounded
  `infra_smoke_ready`; `mvp_loop_ready`, `internal_pilot_candidate`,
  `user_rollout_ready`, and `production_ready` remain excluded.
- Feature `042-recording-sync-transcription-loop` is implemented and
  local-gate validated in the current feature branch. It adds an offline-safe
  desktop upload queue v2, deterministic local media revision identity, server
  `MediaRevision`, resumable sync-state reconciliation, one logical meeting
  with one accepted initial revision, revision-keyed processing workflow
  identity, MediaScribe provenance, web and embedded desktop transcript review
  parity, visible conflict/recovery states, metadata-only diagnostics, deletion
  lifecycle accounting, and RLS coverage for the new media revision table.
  Focused validation passed macOS queue/review/diagnostic tests, server
  ingest/sync/processing/cabinet/RLS tests, and the final
  `infra/scripts/ci-local.sh` gate. This is local implementation readiness
  only: the branch is not merged, not PR-reviewed, not deployed, and has no
  production upload-to-transcript e2e evidence yet.
- Feature `045-transcription-results-pipeline` is implemented, merged,
  released as `v2026.06.24.1`, and deployed to production. Structurally valid
  local packages remain upload/transcription eligible even when local leakage,
  echo, silence, timing, or transcription-readiness checks are degraded,
  failed, inconclusive, or unavailable. Consent, permission, missing/unreadable
  files, package role/size/checksum/fingerprint integrity, lifecycle, and
  privacy boundaries remain hard gates. Accepted server finalization starts or
  reuses one processing workflow when processing is enabled, unavailable
  dependencies become visible processing blockers without rolling back upload
  success, and web plus embedded desktop review expose matching transcript and
  diarization availability for the accepted media revision. Quality warnings
  are retained as metadata-only artifact profile context, not as queue-blocking
  failure reasons. Production evidence on 2026-06-24 proved a real installed
  app recording could upload, finalize, process through MediaScribe, and reach
  a review state with transcript, diarization, playback, workflow presence, and
  both source roles visible. Speakerphone quality remains a product limitation:
  the pipeline accepts degraded-but-structurally-valid recordings, but this is
  not proof of clean echo/noise suppression.
- Feature `046-meeting-playback-timestamp-seek` is implemented, merged through
  PR `#1564`, released as `v2026.06.24.2`, and deployed to production. A ready
  meeting can expose a server-owned playback route, the review page can render
  an audio player, transcript timestamps can seek the player, and web plus
  desktop embedded review use the same playback state. For recordings with
  microphone and incoming/system audio, review playback must represent both
  retained sources in one review stream; if one source is missing, purged, still
  processing, failed, deleted, not allowed, or unsafe to combine, playback fails
  closed with a simple unavailable state. Latest closeout evidence on
  2026-06-24: focused 046 server quickstart `39 passed`, browser runtime
  `failures=[]` across web/embedded desktop/mobile and blocked states, macOS
  SwiftPM suite `575 tests, 0 failures`, GitHub Release published in Russian,
  open 046 GitHub issues `[]`, and production deploy `deploy_result=pass` with
  `readiness_verdict=infra_smoke_ready` on deployed commit `cd168c0`. The
  installed local app bundle is version `2026.06.24.2` and launches from
  `/Applications`. This still does not implement real echo cancellation,
  noise suppression, transcript editing, waveform generation, signed/notarized
  external distribution, or final user-rollout readiness.
- Feature `047-cabinet-runtime-truth` is implemented, merged through PR
  `#1635`, released as `v2026.06.25.2`, and deployed to production on top of
  the `048` playback baseline as the macOS cabinet trust correction. The desktop
  shell no longer treats a configured cabinet URL as proof that the server,
  session, or review surface is healthy. It starts configured cabinets in a
  neutral checking state, shows server-unavailable truth for offline/timeout
  navigation failures, treats successful login/sign-up page loads as
  auth-required instead of ready, and shows green cabinet status only after an
  allowed authenticated meeting list/detail route finishes. The runtime state
  is shared from the embedded WebKit cabinet into the native shell, while
  native Record/Stop/upload truth remains visible for every cabinet state.
  Local evidence on 2026-06-25: focused macOS cabinet tests passed
  `20 + 15 + 9` tests, full macOS SwiftPM passed `579 tests, 0 failures`,
  focused server cabinet tests passed `43 passed`, fixture and real-server
  Playwright/Chrome runtime checks passed with `failures=[]`, production health
  returned live `ok` and ready `ready`, full local CI passed
  `570 passed, 4 skipped, 8 warnings`, deploy dry-run returned
  `deploy_result=dry_run`, and production health returned live `ok` and ready
  `ready` after release closeout.
- Feature `048-real-playback-availability` is implemented, merged through PR
  `#1610`, released as `v2026.06.25.1`, and deployed to production as the
  product-visible playback correction after `046`. A normal ready owner review
  no longer needs `audio_download=allowed` to show playback: review listening
  is separated from file download/export policy, while the "Files" audio
  download action can remain policy-blocked. The web review and macOS embedded
  review render the same transcript-first surface with a persistent bottom
  player, timestamp seek controls, speed/skip/time controls, and diarization
  speaker lanes. The playback route is server-mediated, relative, range-aware
  (`206`/`Accept-Ranges`/`Content-Range`), and does not expose signed URLs,
  storage object keys, raw audio diagnostics, or private paths. Closeout
  evidence: RED reproduced the 046 real-product gap (`15 failed, 14 passed`),
  extended focused validation passed `48 passed, 1 warning`, the real local
  FastAPI/Playwright verifier on 2026-06-25 passed across ordinary web,
  mobile-width web, and desktop embedded review with range playback and no
  visible audio download link, full local CI passed
  `570 passed, 4 skipped, 90 warnings`, and production deploy returned
  `deploy_result=pass` with deployed SHA
  `94e6cbfa2c15d9e3e94ee8d533c13d91b0f5c4d9`; the later
  `v2026.06.25.2` production release still contains the 048 playback merge.
  This still does not implement materialized compressed share audio, public
  links, real echo cancellation, noise suppression, waveform generation,
  transcript editing, native Swift playback controls, signed/notarized
  distribution, or final user-rollout readiness.
- Feature `049-meeting-outcomes-mvp` is implemented, merged through PR `#1706`,
  released as `v2026.06.25.4`, and deployed to production as the stored meeting
  outcomes slice for MVP readiness. The notes/action output blocker is closed
  by stored, launch-safe outcome rows:
  summary, key points, decisions, action items, follow-ups, risks, questions,
  and evidence states are materialized only from transcript-backed source
  segments, with category-level not-found/not-inferable truth instead of
  fabrication. Web review and macOS embedded review share the same server-owned
  response, responsive layout, source evidence rows, processing/blocked/partial
  states, and playback coexistence. Privacy boundaries stay in force: outcome
  text is hidden from list egress and denied/deleted/deleting states, outcome
  artifacts are included in deletion accounting, RLS inventory covers outcome
  tables, and committed evidence remains metadata-only. The notes/action output
  blocker is closed for the MVP surface; follow-up work is quality, editing,
  richer controls, and rollout hardening, not basic outcome availability. This
  does not claim production rollout readiness by itself.
- Feature `050-mvp-launch-proof` is implemented, merged through PR `#1753`,
  released as `v2026.06.25.5`, and deployed to production as the MVP
  launch-proof closeout slice. It verifies the installed macOS app, production
  server, web cabinet, embedded review, playback, transcript, diarization,
  speaker timeline, stored outcomes evidence, product status, release notes,
  and deploy truth against a bounded MVP claim. The final 050 claim remains
  `pilot_blocked`: playback, timestamp seek, bottom speaker timeline,
  web/embedded parity, truthful macOS cabinet state, docs, release, and deploy
  gates passed; `mvp_loop_ready`, `internal_pilot_candidate`,
  `user_rollout_ready`, and `production_ready` stay excluded until a fresh live
  owner journey, stored outcomes on a production candidate, and representative
  one-hour timing proof pass with metadata-only evidence.
- Feature `058-web-cabinet-htmx-shell` is implemented and merged into
  `origin/master` through PR `#2096` and PR `#2234` as a local architecture
  refactor for the server-owned cabinet shell.
  It fixes the frontend foundation as Jinja templates, reusable cabinet
  component macros, one static CSS/token layer, centralized Lucide-style inline
  SVG icons, and locally vendored HTMX `2.0.10`; Tailwind, ready UI kits, SPA
  frameworks, CDN UI assets, frontend build pipelines, component preview apps,
  and separate design-system packages remain out of scope. Browser and desktop
  embedded cabinet list/detail routes share one online shell, HTMX updates are
  bounded fragments with full-page fallback, unsafe cookie-authenticated
  cabinet actions require CSRF proof, and desktop route policy uses exact
  approved route kinds including deletion reports. Native Record/Stop, active
  capture, upload truth, permission recovery, diagnostics, and offline recovery
  remain outside WebView ownership. Local evidence on 2026-06-26: targeted
  server checks passed `93 passed, 5 warnings`; runtime checker passed
  `result=pass` across `8` synthetic surfaces and `12` checks; desktop cabinet
  checks passed `63 tests, 0 failures`; static source guard passed; full local
  CI passed `685 passed, 4 skipped, 94 warnings` with `ci_local_result=pass`.
  This slice has no database migration or machine-readable JSON contract
  change and is not released, deployed, or production-smoked yet.
- Feature `059-recording-date-title` is merged into `origin/master` through PR
  `#2235` and included in release `v2026.06.27.1`. New recordings now carry
  persisted recording metadata from
  the local manifest start/stop instants plus a minimal safe title from
  already-approved app/platform context or a generic date fallback. The desktop
  create-meeting payload sends persisted `title`, `started_at`, and `ended_at`;
  server ingest persists safe values and rejects unsafe title-like values; the
  cabinet list/detail/search/sort surfaces use recording start time with
  truthful legacy fallback. Safe filename basename is metadata only and does
  not rename required local package files, upload idempotency keys, media
  revision identity, or storage object keys. Focused local evidence on
  2026-06-27 passed Swift filters for manifest, resolver, queue, client, and
  diagnostics (`22 + 6 + 43 + 13 + 20` tests), focused server pytest
  (`25 passed, 1 warning`), focused Ruff, full SwiftPM
  (`653 tests, 0 failures`), and full local CI (`ci_local_result=pass`; server
  tests `712 passed, 4 skipped, 103 warnings`; deployment evidence scan
  `pass files=7`). The local CI RLS boundary reported
  `rls_validation_result=blocked` because production enforcement was not
  inspected from the local `postgres_test` boundary, so that local run is not
  production RLS evidence. It deliberately does not implement calendar
  integration, window/browser title collection, rename UI/API, download/export,
  transcript-derived titles, or new app/window observers.
- Feature `060-calendar-context-ingestion` is implemented, merged through PR
  `#2286`, released as `v2026.06.27.2`, and deployed to production as the first
  calendar context layer. It adds server-owned
  read-only calendar source connection state, credential sealing, selected
  calendar sync state, normalized future event snapshots, participants,
  conference-link metadata, recording-time calendar context links, desktop
  one-minute join prompts, event-start record prompts, safe roster context in
  authorized meeting review, and future recipient-candidate counts without
  sending anything. Provider coverage is represented through Yandex/Mail.ru
  CalDAV presets, custom CalDAV/iCalendar for Russian and on-prem providers
  such as VK WorkSpace-compatible tenants, Mailion/MyOffice, R7-Office,
  CommuniGate Pro, RuPost, Nextcloud/SOGo-like deployments, plus native
  normalization adapters for Exchange EWS and Bitrix24. The slice deliberately
  does not auto-join, auto-record, mutate
  calendars, send summaries/transcripts/reports, create attendee share grants,
  fetch attachments, perform retrospective matching, or use live provider
  credentials in committed evidence. Production credential-bearing provider
  connect requires a durable Fernet key file through
  `GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE`; legacy
  `TWOBRAIN_CALENDAR_CREDENTIAL_KEY_FILE` remains accepted as a compatibility
  alias, but the canonical key is shared by server-owned provider credentials,
  not calendar-only. Without it, the API fails closed before accepting app
  passwords or OAuth-refresh-like material. Focused local
  evidence on 2026-06-27:
  after refreshing from `origin/master` `94ffcb6`, Ruff passed, backend focused
  calendar/cabinet/ingest checks passed `134 passed`, macOS calendar/upload/
  recording-metadata checks passed `155 tests`, full macOS suite passed
  `666 tests, 0 failures`, the forbidden-content scan found no matches, and
  full local CI passed `782 passed, 4 skipped, 103 warnings` with
  `ci_local_result=pass`. Release closeout on 2026-06-27: GitHub Release
  `v2026.06.27.2` published, production deploy passed with deployed SHA
  `02ee0a87f5f48036e514481495e7d26d02333dc2`, backup reference
  `/opt/projects/2brain-rec/backups/20260627T013238Z`, production smoke
  `smoke_result=pass`, readiness `infra_smoke_ready`, and local macOS installer
  build passed for app/package version `2026.06.27.2`. The local installer is
  not Developer ID signed or notarized; external distribution still needs a
  separate signing/notarization gate.
- Feature `063-calendar-settings-ui` is implemented locally in the current
  feature branch as the user-facing calendar settings layer on top of `060`.
  It adds the web and embedded macOS cabinet route
  `Настройки -> Интеграции -> Календари`, provider selection for Yandex,
  Mail.ru, Exchange/EWS, Bitrix24, VK WorkSpace/custom CalDAV,
  Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost,
  Nextcloud/SOGo-like CalDAV, and custom CalDAV, explicit calendar
  selection with zero selected by default, sync health/manual sync, safe
  disconnect confirmation, prompt preferences, upcoming preview, duplicate
  grouping, and overlap conflict choices including partial overlaps such as
  12:00-13:00 plus 12:30-13:30. The UI states plainly that access is read-only:
  GRAF reads selected future events, does not mutate calendars, does not
  send summaries/transcripts/reports, does not grant attendee access, does not
  auto-record or bot-join in 063, and does not retrospectively match older
  recordings. Desktop unavailable/auth copy keeps provider credentials
  server-owned and keeps native manual Record/Stop reachable. Local validation
  on 2026-06-28 passed focused server calendar settings checks (`77 passed`),
  server Ruff, focused macOS calendar/cabinet checks (`97 tests`), full macOS
  suite (`693 tests`), forbidden-content scan with only safe passcode-detector
  source references, removed-provider catalog scan with no matches in the
  calendar feature surface, and full local CI
  (`968 passed, 4 skipped, 148 warnings`, `ci_local_result=pass`). It was
  merged through PR #2498 and prepared for release `v2026.06.28.6`; release and
  production deploy evidence are recorded in the release closeout notes. This
  slice is not user-rollout validated yet; moderated
  usability/comprehension targets still need real participant evidence.
- Feature `069-universal-sidebar` is implemented, merged through PR #2532,
  closed through cleanup PR #2543 and release PR #2544, and included in
  production releases from `v2026.06.30.7` through the current
  `v2026.06.30.10` deployment. The browser cabinet and desktop embedded
  cabinet use one server-owned sidebar/shell contract; page templates own only
  their content region, fragments stay content-only, and the native SwiftUI
  product sidebar remains absent. Closeout evidence includes focused shell,
  route, fragment, and macOS boundary tests, full local CI, release notes, and
  production smoke with public health `ready`. This slice does not add admin or
  auth navigation and does not claim manual screenshot/browser QA beyond the
  recorded automated and deploy evidence.
- Feature `036-owner-review-live-polish` is implemented as the current owner
  review visual/auth baseline. It adds browser email login/signup flows, Postal
  delivery configuration, session-protected web cabinet routes, installed
  desktop login recovery, denser clean-room meeting list/detail surfaces, and
  native/embedded shell polish. The 036 readiness pack now records the bounded
  `pilot_blocked` outcome: visual/product polish and notes/action truth states
  are accepted, and the installed-app idle/active/paused/resumed/stopped
  walkthrough is covered by cropped native-inspector evidence. Live owner
  list/detail/governance proof is now committed as metadata-safe Chrome owner
  session evidence. Launchable generated notes/actions or an explicit pilot
  deferral, plus production user rollout evidence, remain separate blockers.
  Evidence remains metadata-safe and keeps the production
  claim bounded unless a separate rollout gate proves stronger live owner-review
  behavior.
- Feature `043-app-zoom-shortcuts` is implemented on top of the `036` owner
  review shell baseline as a local macOS readability feature. Standard macOS
  shortcuts adjust only the embedded meeting workspace zoom, persist the local
  supported zoom value, recover invalid saved values to 100%, and leave native
  Record/Stop/upload truth/local readiness outside the scaled WebKit surface.
  This slice does not change capture, upload, backend meeting data, retention,
  deletion, auth, or production rollout state.
- Feature `038-apple-voice-processing-spike` is implemented as a bounded
  metadata-only Apple candidate evidence slice. Its current primary outcome is
  `defer_to_webrtc_aec3`: Apple processing is not accepted for built-in
  speakerphone recording, original `mic.wav`/`incoming.wav`/`manifest.json`
  package truth remains authoritative, existing `020` leakage finalization
  remains the clean/leakage/unproven authority, and user-facing/release-facing
  copy must not claim clean speakerphone behavior from Apple evidence. The next
  technical slice is `039-webrtc-aec3-speakerphone-spike`.
- Feature `033-desktop-cabinet-embedding` is implemented as the macOS shell
  bridge for the accepted `016` cabinet route classes. The desktop app now
  opens a `Встречи` workspace after native capture controls, hosts embedded
  meeting list/detail surfaces through WebKit, preserves native Record/Stop and
  upload truth outside the embedded surface, shows bounded unavailable/auth
  states, and opens review only for uploaded queue items with server meeting
  identity. Screenshot evidence uses synthetic local fixtures and contains no
  Krisp private captures, real account identifiers, transcript text, raw audio,
  signed URLs, or live local paths.
- Feature `021-production-deployment-plan` is implemented as a remote-first
  infrastructure readiness slice for `2brain.dev` and `/opt/projects/2brain-rec`.
  It adds production Compose hardening, env/secret templates, remote backup,
  migration, restore rehearsal, rollback/halt helpers, internal smoke identity,
  first-smoke evidence templates, cleanup accounting, and forbidden-content
  scans. The highest allowed successful status is `infra_smoke_ready`; this is
  not production readiness, user rollout readiness, or internal pilot readiness.
- Feature `031-rls-hardening` is implemented and deployed as a backend tenant
  isolation hardening slice. It adds PostgreSQL RLS policies for accepted
  tenant-owned identity, auth/session/device, ingest, meeting, processing,
  transcript, audit, and dependency tables; explicit request, worker,
  auth-bootstrap, session-lookup, callback-lookup, and allowlisted maintenance
  DB contexts; rollout/rollback validation helpers; and ADR `003` for future
  tenant-owned tables. Production inspection on 2026-06-15 showed
  `/opt/projects/2brain-rec` at commit `3fd2162`, Alembic
  `0005_rls_hardening`, and every covered production table reporting
  `relrowsecurity=true` plus `relforcerowsecurity=true`. It does not add
  dashboard, share/download, retention, deletion execution, billing, admin UI,
  desktop capture/upload, or new MediaScribe behavior.
- Feature `032-rls-live-enforcement` corrects the stale `031` rollout truth:
  production RLS enforcement is verified enabled and forced through read-only
  PostgreSQL catalog metadata, while destructive same/cross-tenant probes
  remain limited to disposable or explicit test databases.
- Feature `025-system-audio-capture-pivot` is accepted as the macOS MVP
  recording path. It records local microphone plus incoming/system audio without
  requiring meeting-app audio-device reconfiguration, preserves dual-track local artifacts, and
  closes the final evidence gates for permission matrix, controlled artifact,
  CPU/resource behavior, 30-minute development validation, 75-minute release
  validation, forbidden-content scan, and final scope review.
- Feature `020-speaker-to-mic-leakage` is accepted as the post-stop
  finalization truth gate for local dual-track packages. After `Stop`, saved
  `mic.wav` and `incoming.wav` evidence is measured against
  `leakage-threshold.v1`; `manifest.json` uses
  `local-recording-manifest.v3`; contaminated, ambiguous, malformed,
  misaligned, not-measured, or unproven packages still record local
  transcription-readiness failure/degradation truth. Feature `045` changes how
  that truth is used for product upload/transcription eligibility: for
  structurally valid packages it is diagnostic metadata, not an upload blocker.
  The implementation is integrated on top of the accepted `025` system-audio
  capture path and does not replace scope approvals, permissions,
  capture-health evidence, dual-track role mapping, or system-audio recording
  truth.
- `020` diagnostics remain metadata-only: leakage status, transcription gate,
  route metadata, threshold metadata, and measurement summaries may be included,
  but raw audio, transcript text, credentials, tokens, signed URLs, passwords,
  meeting content, and live filesystem paths remain forbidden.
- `020` is finalization-only. It does not introduce external egress, a
  MediaScribe call, live echo cancellation, recording-time route remediation,
  an alternate audio-routing fallback, or a customer-visible auto-start policy.
- The unsafe separate audio-routing experiment from `019` / issue #234 is
  superseded by `025` and removed from active source, packaging, runtime,
  tests, and QA. Its failure report remains historical negative evidence only.
- ADR `001-local-trust-shell-and-server-dashboard` is accepted. Capture-critical
  desktop trust surfaces stay local/native; server/web surfaces own
  post-meeting, transcript, notes, admin, retention, deletion, audit, and fleet
  workflows.

## Not Accepted Yet

- A controlled 2026-07-13 app-owned recording produced both non-empty original
  tracks with granted permissions and tight duration alignment, but the review
  M4A subjectively masked microphone speech while system audio dominated and
  finalization reported `leakage_detected`. Driver retirement does not change
  the pre-existing review mixer or leakage policy, so review-mix balance,
  clean built-in-speaker capture, and end-to-end transcription quality require
  a separate high-risk recording-quality feature and fresh real-hardware proof.
- Yandex Browser is intentionally skipped/not accepted in the current
  browser/meeting smoke cycle.
- Third-party meeting-app mute adapters are not accepted yet. Local privacy
  truth is product-owned through 2brain `Pause`/`Resume`/`Stop`; Zoom/browser
  mute state remains unverified unless a future adapter provides fresh
  target-specific evidence.
- Built-in speakerphone clean dual-track acceptance remains constrained by
  `020`/`038` evidence: packages can be captured and, after `045`, structurally
  valid imperfect packages can still proceed to server transcription, but the
  product must not label polluted microphone audio as clean local speech.
  Feature `038` did not accept Apple processing for built-in speakerphone
  recording; `044` remains the real echo/noise suppression runtime candidate.
- Any future advanced routing requires a new approved spec, implementation,
  packaging model, and safety evidence; the removed implementation must not be
  revived as a hidden fallback.
- Public meeting links, external-recipient invitations, partial deletion,
  legal-hold management, admin retention editing UI, billing, and desktop-owned
  deletion policy remain later slices.
- Feature `042` production behavior is not accepted yet. The local
  implementation passed `ci-local`, but merge, PR review, deployment,
  production smoke, and production upload-to-transcript evidence still need a
  separate approval and closeout.
- Production RLS coverage is accepted only for the `031` covered table
  inventory. Future tenant-owned tables and product surfaces still need their
  own ADR `003` classification, tests, and metadata-only evidence before merge.
- Feature `011-assisted-auto-recording` remains requirements-only. Detect-only,
  detect-and-ask, automatic naming, and future auto-record behavior have not
  been implemented or accepted.
- Signed/notarized production installer evidence remains separate from local
  ad-hoc development package evidence.
- Feature `030-mvp-experience-design-system` now provides the MVP product
  experience/design handoff: full clean-room Krisp/2brain audit, native vs web
  route boundaries, status/provenance matrices, screen specs, server-owned
  embedded product UI contract, and the active Figma v8 clean Russian review
  candidate. V8 supersedes the v5-v7.4 prototype lineage after stakeholder and
  five-critic reviews found flow, density, settings, technical-copy, and
  visual-quality blockers in earlier drafts. Current V8 evidence covers 17
  top-level MVP frames, 98 valid click reactions, dark/light theme proof,
  shared upload/search overlays, desktop/web owner-value-loop coverage, and a
  stakeholder visual approval pack.
  V8 is the implementation baseline for the first real desktop/web UI slice;
  final stakeholder visual acceptance remains the polish gate for declaring the
  interface handoff final. This is design-readiness evidence only; it does not
  implement production desktop or web UI.

## Next Product Slice

Feature `050-mvp-launch-proof` is closed as the MVP launch-proof slice. Its job
was to decide, with evidence rather than optimism, whether the current product
can be called an internal pilot candidate.

Feature `051-mvp-owner-journey-proof` is implemented, merged through PR `#1799`,
released as `v2026.06.25.7`, deployed to production at
`67cb9a15752143881cb0123e1ef5fa9c9c60a632`, and followed by post-deploy
closeout release `v2026.06.25.8`. It did not add a new user feature. It checked
the installed app, production health, short production processing metadata,
stored outcomes, playback/timeline runtime, macOS cabinet truth, and readiness
docs before any MVP claim could be raised.

The 051 result keeps the product at `pilot_blocked`: installed app identity,
current production health, local web/embedded playback/timeline/outcome runtime,
and native false-green guards pass, but the three P1 proof gates below remain
open.

Feature `052-mvp-live-ui-proof` is implemented, merged through PR `#1844`, and
followed by production fix PRs after deploy and cleanup gates exposed real
blockers. It rechecks the real installed app, production cabinet, KRISP-style
playback/timeline reference, stored outcomes, and timing before any stronger
MVP claim. The current deployed release is `v2026.06.26.3` at
`6c1b2f2ffa2545ee3a2f5bc5af734b0f19bcbd1e`: public health returns live `ok`
and ready `ready`, production smoke passes, and synthetic timing artifacts were
cleaned up without residue. Earlier 052 production fix PR `#1845` shipped
`v2026.06.25.10` at `db1eca18f08d26f6816b2bd88067709d0e57e590`: production
smoke reported `processing=enabled`, `temporal=configured`, and
`mediascribe=dispatcher_only`; `rec-api` dispatches Temporal work, does not mount the MediaScribe key,
and the key stays on `rec-processing-worker`.

The allowed current claim remains `pilot_blocked`. The bounded shipped claim is
`infra_smoke_ready`; `mvp_loop_ready`, `internal_pilot_candidate`,
`user_rollout_ready`, and `production_ready` remain excluded until the
fresh owner journey, production stored outcomes on that journey, and live
owner-review UI gaps are closed. 052 fixture-backed web/mobile/embedded checks
pass playback, timestamp seek, speaker lanes, and stored outcome rows; the
installed macOS shell also avoids a false-green cabinet state. A production-safe
synthetic one-hour candidate processed in 37 seconds created-to-imported, under
the 180-seconds-per-hour target, with transcript, diarization, playback, speaker
timeline, and stored outcome counts available. Live production owner review
remains degraded. The latest fresh installed-app candidate proves record,
upload, finalization, and processing, but imported `0` transcript segments and
`0` diarization segments; its stored outcome set is blocked with
`outcomes_transcript_unavailable`. That candidate cannot close review,
speaker-timeline, or stored-outcome proof, so these local and production checks
still do not prove MVP rollout readiness.

Feature `057-local-upload-custody` is implemented, merged through PR `#2052`,
and released as `v2026.06.26.12` as the product-owned custody layer for local
desktop recordings.
It keeps the server WebView meeting list authoritative, removes normal-user
transport retry controls, preserves local recordings with automatic custody
processing, exposes compact native aggregate status, emits metadata-safe
admin/support incident truth, separates upload/processing/deletion/local purge
states, and fails closed on local purge acknowledgement unless deletion,
tombstone, or unrecoverability is verified. Focused local evidence passed the
057 Swift custody/purge/projection suites and focused server custody/purge
read-model suites on 2026-06-26. This is merged/released local implementation
readiness, not production-smoked evidence; feature `058` has since landed the
server cabinet presentation refactor baseline.

Current evidence already accepted before 050:

- `045` lets structurally valid recordings proceed to upload/transcription even
  when local audio quality diagnostics are degraded, while keeping permission,
  consent, integrity, lifecycle, and privacy gates hard.
- `046` and `048` provide real review playback, server-mediated range playback,
  and transcript timestamp seek in web and embedded review.
- `047` keeps the macOS cabinet status honest: green state requires a real
  authenticated allowed route, not just a configured URL.
- `049` closes the notes/action output blocker with stored meeting outcomes,
  transcript-backed evidence, category truth, privacy/deletion/RLS coverage, and
  web/embedded review parity.

Remaining launch boundary after 052:

- `fresh-owner-journey-evidence` stays open until a current live owner journey
  proves record/stop/upload/finalize/process/review from the installed app.
  The latest fresh candidate reaches processing, but not usable review content.
- `production-stored-outcomes-evidence` stays open until a current production
  installed-app candidate shows stored outcome states and counts without private
  generated text. Synthetic production-safe outcome counts exist, and the
  latest fresh candidate has a blocked outcome set, but neither replaces a
  fresh candidate with reviewable transcript content.
- Live owner-review UI proof stays degraded until authenticated production
  detail and embedded review can be opened and checked end to end; the
  historical production blocker remains recorded as `missing auth context`
  where the live route cannot prove owner context.
- Signed/notarized installer evidence, Yandex Browser support, real
  speakerphone echo/noise suppression, compressed share audio, public links,
  waveform polish, transcript editing, and native Swift playback controls remain
  outside the MVP launch-proof claim unless a later spec changes scope.

A remote `021` infrastructure smoke on `2brain.dev` can continue only within
the `infra_smoke_ready` boundary until user rollout slices and live journey
evidence are separately accepted.

Keep separate unless the next spec explicitly changes scope:

- Public-link and external-recipient sharing policy: optional public links,
  expiration, abuse controls, external invitations, and legal/admin copy.
- Notes/action output: `049` closes the MVP blocker with stored meeting
  outcomes. Follow-up work is quality/model improvement, editing, richer
  owner controls, or rollout hardening, not a replacement for the basic stored
  outcome surface.
- Interactive playback/timestamp seek: real visible owner review playback is
  implemented, merged, released, and production-smoked in `048`. Remaining
  playback-related work is post-MVP scope such as compressed share audio,
  public links, waveform polish, native Swift controls, or editing.
- Assisted auto-start and generalized meeting detection.
- Live speakerphone cleanup/AEC: Apple voice processing, WebRTC AEC3, custom
  AEC, and mixed-audio fallback remain decision records or future spike gates
  after `020`. They are not runtime behavior in the finalization-only slice.
  Detailed prepared backlog context is recorded in
  `docs/audio-capture-backlog.md`.
- Post-MVP editing and media revision work is tracked in
  `docs/post-mvp-editing-media-backlog.md`: local media trim/edit revisions,
  online transcript/speaker edit sync, video capture package foundation, and
  explicit replace/reprocess flows remain outside `042` MVP.

## Deferred Work Register

Use this register as the anti-drift memory for work intentionally left out of
the current accepted implementation or `012` ingest slice.

- Target-specific meeting-app mute adapters: future work only after separate
  privacy, platform, and QA evidence. Accepted feature `022` covers
  product-owned Pause/Resume truth and keeps unsupported meeting targets
  fail-closed; it does not claim third-party Zoom/Telemost mute interception.
- `011-assisted-auto-recording`: plan and implement detect-and-ask, automatic
  naming, and any future auto-start behavior from the accepted requirements.
- Public-link and external-recipient sharing policy: add optional public links,
  expiration, external invitations, abuse controls, and admin/legal copy after
  the login-required 017 flow is accepted.
- `021-production-deployment-plan`: use the remote-first runbook to reach
  `infra_smoke_ready` for the Rec stack, while keeping user rollout and pilot
  claims blocked until later product slices are accepted.
- `020-hardware-route-matrix`: complete physical-device route matrix rows that
  require unavailable hardware before claiming broad hardware speakerphone
  acceptance. Current automated acceptance covers persisted-package
  finalization behavior, not every physical device route.
- `037-microphone-sample-graph-foundation`: introduce an app-owned microphone
  sample graph before any live cleanup claim, while preserving the current
  `mic.wav`/`incoming.wav`/`manifest.json` package truth.
- `038-apple-voice-processing-spike`: evaluate Apple `AVAudioEngine` voice
  processing, `VoiceProcessingIO`, and Mic Mode/Voice Isolation as bounded
  spike candidates for reducing built-in speaker-to-mic leakage.
- `039-webrtc-aec3-speakerphone-spike`: evaluate WebRTC AEC3 with system audio
  as the render/far-end reference and microphone frames as capture input only
  after the app-owned microphone graph is available.
- `040-speakerphone-recording-fallback-decision`: decide headset-first,
  derived-cleaned, mixed-audio, pilot-only, or unsupported-route semantics if
  clean built-in speakerphone dual-track capture cannot be proven.
- `041-recording-permission-readiness-onboarding`: make microphone and
  Screen/System Audio readiness visible before the user starts recording.
- `031-rls-hardening` / `032-rls-live-enforcement`: future tenant-owned tables
  and product surfaces must follow ADR `003-tenant-isolation-rls`; destructive
  RLS probes stay on disposable/test databases, and production truth must be
  proven with read-only catalog metadata.
- `044-speakerphone-echo-noise-suppression`: clean-recording runtime slice for
  real echo cancellation/noise suppression. It must preserve package truth,
  metadata-only evidence, reversible fallback, and built-in speakerphone route
  limits before any clean speakerphone claim is allowed. It is separate from
  `045`, which lets imperfect-but-structurally-valid packages reach
  transcription/results without claiming the mic was cleaned.
- Post-MVP editing/media backlog still needs separate numbering after `048`:
  local media trim revisions, online transcript edit sync, video capture
  package foundation, and explicit media replace/reprocess flows are not part
  of `042`/`048` MVP, but current data/identity choices must avoid duplicate
  meetings later.
- `direct-object-upload`: future upload optimization only after a separate
  security and lifecycle review; `012` remains `server_mediated`.
- Calendar/contact-based speaker-name suggestions remain a separate future
  identity capability after `098-calendar-auto-context-match`. Feature `098`
  treats calendar participants only as invited roster metadata: they do not
  rename `SPEAKER_XX` transcript/diarization labels, create access or share
  grants, become recipients, or trigger delivery. Any future implementation
  requires its own consent, confidence, correction, speaker-truth, privacy and
  authorization design and evidence.
- Browser/packaging evidence still pending: Yandex Browser smoke, long-duration
  30/60 minute integrity, and signed/notarized installer evidence.
- `mediascribe-large-audio-proxy-ceiling`: do not raise MediaScribe just
  because Rec accepts larger upload packages or future video files. MediaScribe
  receives only audio. Raise its separate OpenResty/nginx body limit only if
  real combined `mic_file` + `incoming_file` audio approaches the observed
  public proxy ceiling and starts failing with `413`.
