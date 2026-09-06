# Product Gates

Use this file with `.specify/memory/constitution.md`,
`docs/prd-voice-layer-final.md`, and `docs/current-product-status.md`.

## Capture And Platform

- The MVP recording path is macOS system-audio-first.
- The former separate audio-routing implementation is removed legacy. It must
  not be packaged, started, repaired, or represented as an available fallback.
- Any future advanced-routing work requires a new approved Spec Kit slice,
  safety evidence, packaging model, and rollback plan; it must not revive the
  removed implementation.
- Capture-critical macOS implementation is native by default:
  Swift/Cocoa/ScreenCaptureKit/AVFoundation/Core Audio where appropriate.
- Windows and other platforms require separate future native stacks and
  architecture decisions.
- Manual `Record`/`Stop` remains available whenever workspace policy permits
  recording.
- Active capture must always have a persistent local visible indicator and a
  one-action stop path.
- No user or admin setting may make active capture invisible.
- Target-scoped automatic recording is a protected MVP capability. The active
  contract is advanced by Feature `214-reliable-auto-recording` and uses the
  verified native macOS meeting-app registry and the `Автозапись` settings
  page. Each app has exactly one local state: `Всегда`, `Спрашивать` or
  `Никогда`; a new installation defaults every app to `Спрашивать`.
- In `Спрашивать`, the prompt shows the designed eight-second countdown and
  starts the current recording when it expires. `Записать` starts immediately
  and `Не записывать` suppresses the current recording. With `Запомнить выбор`,
  those actions persist `Всегда` and `Никогда` respectively; without it the
  setting does not change. `Всегда` bypasses the prompt and `Никогда` shows no
  prompt. All states remain visible, accessible and reversible in settings.
- The three-state preference is client-owned. Server assisted-auto-start policy
  and acknowledgement are not start gates and must be removed only after a
  compatible client that ignores them has shipped. General workspace recording
  and consent restrictions, approved-target detection, permissions, local
  storage, visible indicator and one-action Stop remain mandatory.
- A bulk `Для всех приложений` choice applies one of the same three values to
  currently known apps. It is not a fourth state or a global “record arbitrary
  audio” switch.
- Removing or materially weakening the target list, per-app permission,
  countdown, automatic start, remembrance choice or three-state settings
  requires a new approved Spec Kit feature with migration/compatibility notes,
  focused regression tests, and explicit product-owner approval.

## Audio, Artifacts, And Diagnostics

- Features that touch capture, recording integrity, buffering, permissions,
  system audio, microphone capture, or future advanced-routing UX must define
  measurable latency, dropout, track alignment, authorization, recovery,
  degraded-state, and QA requirements.
- Langfuse observations and the retained Generation Call ledger intentionally
  retain complete plaintext transcript/model content for internal-MVP debugging;
  Temporal History intentionally retains the complete plaintext transcript.
  Ordinary product logs, screenshots, audit, and committed evidence remain
  metadata-only.
- Never include raw audio, transcript text, credentials, tokens, signed URLs,
  passwords, live local paths, or private meeting content in committed evidence.

## Server, Storage, And AI Boundaries

- GRAF-owned meeting data stays in configured owner-controlled
  infrastructure by default.
- Content-bearing LLM calls leave GRAF only through an owner-controlled,
  explicitly allowlisted LiteLLM gateway. GRAF workers never store upstream
  provider credentials or call upstream model endpoints directly.
- Every LiteLLM route that can receive meeting content requires operator
  approval for destination, data classes, retention/deletion limits, and
  rollback. Langfuse Prompt Config is the single editable authority for prompt
  text, selected LiteLLM model route, allowlisted request-level generation
  settings, and strict response format. A multi-prompt pipeline MUST expose one
  versioned root bundle Prompt Config as its only production label/activation
  point; that root pins exact numeric child versions/hashes, schemas,
  validators/verifiers, renderer and route/settings. Runtime never resolves
  child labels. Langfuse label mutation is not assumed to provide native
  expected-source CAS: production movement uses one authorized writer/lock,
  expected-root read/compare, immutable candidate-root qualification,
  protected-root-label move, exact read-back and immutable promotion-event
  binding. Runtime, model calls and publication evidence MUST carry the complete
  typed event binding and re-fetch/re-hash the passing event and qualification;
  a bare event digest or label lookup is non-authorizing. The event remains
  outside the already-hashed root/activation body to avoid a digest cycle.
  Mismatch fails closed on last-known-good root + activation + event binding. A
  mixed partially promoted bundle cannot execute. The root also pins a secret-free immutable LiteLLM
  route-binding descriptor: exact alias, binding version/hash and allowlisted
  actual provider/model pairs. The gateway MUST compare the expected hash before
  provider egress and return that hash plus actual provider/model; absence,
  mismatch or an unallowlisted pair fails closed. Mapping changes require a new
  evaluated/promoted root. LiteLLM owns mapping to the approved upstream
  provider and upstream secrets; workflow code owns neither.
- A private Langfuse Cloud EU project with public trace publishing disabled is
  explicitly approved for internal-MVP AI observability and prompt control; each
  deployment must configure and allowlist its destination and operator-managed
  project roles.
- Desktop clients never send audio directly to MediaScribe and never store
  MediaScribe credentials.
- MediaScribe credentials are server-side only.
- Each completed outcome model call whose response reaches GRAF has exactly one
  logical Generation Call and intended Langfuse `generation` identity binding
  the compiled logical request, complete pinned canonical transcript, raw
  response and validated result. Related AI workflow observations may contain
  the same plaintext content when useful for debugging; GRAF does not redact,
  mask, truncate, encrypt, or delete it.
- Langfuse v4 duplicate ingest is not an upsert or exactly-once guarantee. The
  sole publisher records pending/confirmed/ambiguous delivery, retries only a
  proven pre-export failure, never repeats inference, and collapses any physical
  duplicate by Generation Call identity before evaluation or annotation.
- Raw audio and runtime credentials are not model inputs and are not deliberately
  attached as observability attributes. Credential-like speech inside the
  canonical transcript is preserved verbatim without masking.
- A call that may have left GRAF but has no durably captured response is marked
  `ambiguous`; missing response content is never fabricated.
- Langfuse uses the configured private EU destination and deterministic
  observation identity. One sole publisher keeps each completed-call delivery
  durably pending until confirmation, including after meeting deletion; export
  retry never repeats a completed model call, and recording/transcription remain
  available during an outage.
- Langfuse cannot own meeting, acceptance, or deletion truth. Prompt fetch may
  fall back only to an integrity-checked export of the same promoted Langfuse
  version; with no approved snapshot, AI generation waits.
- Outcome-generation Temporal History contains the complete canonical transcript
  in plaintext and may naturally contain other workflow/failure content. The
  exact full request/response/result is guaranteed in Langfuse and the retained
  Generation Call ledger rather than deliberately duplicated in History.
  Deterministic plaintext chunks stay within both pre/post-serialization payload,
  transaction, and History limits and reconstruct the transcript without omission.
- Do not add a transcript PayloadCodec, application-layer encryption, masking,
  redaction, or GRAF-managed Temporal History deletion for the internal MVP.
  Search Attributes and Memo remain bounded operational indexes, not transcript
  storage.
- Durable model calls and offline prompt optimization use Temporal. GEPA may
  create exact numeric candidate prompt versions and evaluation evidence with
  no manually assigned deployment label, but project-global
  production labels require held-out validation, deployment-operator approval,
  serialized expected-source verification, protected-label plus sole mutation
  credential readiness, and a rollback target. Without that readiness,
  automated promotion stays disabled.
- Feature 121 prompt optimization is synthetic-only. Any later use of real
  transcript/output/feedback requires an approved consent, provenance,
  retention, deletion-invalidation, and owner-controlled storage design.
- Synthetic optimizer Langfuse observations and Temporal histories may contain
  complete plaintext inputs, outputs, judge feedback, and optimizer state;
  real-meeting optimization remains out of scope for Feature 121.
- External dependency features must define egress, secret, timeout, failure,
  retention, and deletion behavior.

## Deletion Truth

- Product copy must not promise universal erasure outside `GRAF` control.
- Preferred deletion wording: "Delete this meeting everywhere GRAF
  controls."
- Deletion reports must distinguish server purge, local desktop purge, backup
  expiry, MediaScribe state, diagnostics, post-egress limits, and unreachable
  clients. They must state that the retained GRAF Generation Call ledger,
  Langfuse observations, and Temporal History are not deleted by meeting
  deletion.
- If a dependency cannot confirm deletion, the UI and admin report must say so.

## UX Reference Fidelity

- UI may faithfully reproduce the approved observable Krisp UX/UI/IA,
  including layout, hierarchy, navigation, interaction states and visible copy.
- Functional UI labels and interaction microcopy may match the approved
  observable reference literally; no paraphrase or brand-distance rewrite is
  required merely because the result matches Krisp.
- Review measures reference fidelity and documents deviations required by
  accessibility, localization, privacy, security, deletion truth or a known
  reference defect; first-glance brand distance is not required.
- Implementation code must be independently written. Extracted assets, source,
  binaries, private APIs, protocols, secrets and private user content remain
  prohibited. Third-party assets, logos and trademarks require documented
  usage rights. GRAF-specific legal, consent, privacy, plan/pricing and
  marketing claims remain independently truthful and applicable.
- High-risk UX includes tray/widget, onboarding, deletion, admin policy,
  accessibility, localization, and unavailable/degraded states.

## Deployment

- MVP server target is `2brain.dev` with public URL
  `https://rec.2brain.pro`.
- MVP infrastructure runs in Docker containers.
- Dedicated Postgres and MinIO are required for `2brain_rec`.
- Temporal is the selected durable workflow engine unless the constitution is
  amended.
- Deployment features require Docker secret handling, health checks, backups,
  restore, rollback, log redaction, and disk-full behavior.
