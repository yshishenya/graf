# Full MVP Completion Audit

**Feature context**: `045-transcription-results-pipeline`
**Date**: 2026-06-24

## Purpose

This audit checks the active goal against current evidence without narrowing
the definition of MVP to only the work already completed in feature `045`.

Statuses:

- `PROVEN`: current evidence directly proves the requirement.
- `PARTIAL`: important implementation exists, but proof is narrower than the
  requirement.
- `MISSING`: required proof or implementation is not present.
- `DECISION`: a product decision is still required before the requirement can
  be judged complete or intentionally deferred.
- `OUT OF 045`: explicitly outside this feature, but relevant to the full MVP
  claim.

## Product MVP Requirements

| Requirement | Status | Current evidence | Remaining gap |
|---|---|---|---|
| macOS native desktop app exists as first MVP platform | PROVEN | PRD baseline, current product status, installed app smoke evidence | None for local MVP platform selection |
| Manual Record/Stop remains available and visible locally | PARTIAL | Installed app smoke proves start/stop comparison; current branch UI proves control panel, build/launch/idle/quit preflight, permission blocker, and installed current-branch permissioned speakerphone/degraded Record/Stop | Clean low-leakage `saved` / `ready` artifact proof and production desktop-to-review proof are still missing |
| One-action stop during active recording | PARTIAL | Installed app comparison smoke, prior accepted 035 walkthrough, current branch non-recording preflight, and installed current-branch permissioned speakerphone/degraded Stop with user-requested stop event | Clean low-leakage stop/artifact proof and production desktop-to-review proof are still missing |
| Local mic plus incoming/system audio dual-track capture | PARTIAL | Accepted 025/010/020/042 status, local package tests, current branch non-recording preflight, installed current-branch permissioned package with saved `local_mic` and `remote_speaker` tracks, local server replay of that degraded package through finalize/processing-start, one fresh production speakerphone run with meaningful incoming/system audio, and current-branch speaker/source-role regression fix | Clean low-leakage `saved` / `ready` artifact proof and post-deploy speaker/source-role proof are still missing |
| Product must not require HAL virtual audio routing for MVP recording | PROVEN | PRD/status mark system-audio-first MVP; current 045 does not revive HAL path | None in 045 |
| Structurally valid imperfect recordings can continue to upload/transcription | PROVEN LOCALLY | 045 macOS/server tests, validation log, focused revalidation | Production evidence missing; proof path is `production-e2e-proof-plan.md` |
| Consent/permission/file/role/size/checksum/fingerprint gates remain hard blockers | PROVEN LOCALLY | finalize integrity, ingest contract, upload queue tests | Production evidence missing; proof path is `production-e2e-proof-plan.md` |
| Server-owned transcription path, desktop never calls MediaScribe directly | PROVEN LOCALLY | 045 plan/spec, server processing tests, privacy contracts | Production 045 e2e missing; proof path is `production-e2e-proof-plan.md` |
| Accepted upload starts or reuses exactly one processing attempt | PROVEN LOCALLY | finalize auto-start, processing pickup/reuse tests | Production 045 e2e missing; proof path is `production-e2e-proof-plan.md` |
| Processing states visible and user-safe | PARTIAL | processing status contracts, desktop sync tests, latest 9-page Playwright fixture runtime with `failures=[]`, one live production processed result after manual pickup, current-branch desktop post-upload reconcile proof, and current-branch speaker/source-role regression fix | 045 post-deploy auto-start/reuse and production proof of the alignment fix remain unproven |
| Transcript availability visible in web cabinet | PARTIAL | web cabinet fixture runtime, cabinet tests, latest Russian-first browser runtime output `/tmp/2brain-rec-045-web-cabinet-ru-20260624g`, one live production cabinet result with transcript available, and current-branch source attribution fix | 045 post-deploy result path and production source attribution proof remain unproven |
| Diarization/provenance availability visible in web and desktop review | PARTIAL | 045 MediaScribe/cabinet/desktop sync tests, one live production result with diarization/provenance present, and current-branch segment attribution fix | 045 post-deploy proof of the fix missing |
| Web and desktop embedded review show matching state | PROVEN LOCALLY | 045 desktop sync/cabinet parity tests and latest fixture runtime covering web, embedded desktop, and mobile routes | Production/live desktop embedded result path missing; proof path is `production-e2e-proof-plan.md` |
| Privacy/content boundary for status, diagnostics, logs, evidence | PROVEN LOCALLY | no-secret/no-content contract tests, diagnostic redaction tests, text scan | Production runtime log/evidence still needs post-deploy scan; proof path is `production-e2e-proof-plan.md` |
| One-hour processing budget under 3 minutes | PARTIAL | Synthetic one-hour orchestration benchmark with fake MediaScribe passed | Does not prove live MediaScribe speed, object storage throughput, or real one-hour audio; proof path is `production-e2e-proof-plan.md` |
| Offline/delayed upload does not create duplicate meetings | PROVEN LOCALLY | 042/045 upload queue tests and media revision identity tests | Production retry/reconnect proof missing; proof path is `production-e2e-proof-plan.md` |
| Deletion/access state remains authoritative during processing | PARTIAL | RLS/deletion/access contracts, status docs, and disposable Postgres direct SQL RLS proof | 045 production result access/deletion proof missing; proof path is `production-e2e-proof-plan.md` |
| Basic AI notes: summary, decisions, action items, follow-ups | DECISION | Notes/action truth states exist in current status | Stored/generated launchable notes/actions are not accepted, or need explicit MVP deferral |
| Basic diarization: reliable `You` vs remote track, best-effort remote labels | PARTIAL | Dual-track and diarization availability are exposed, one live production result returned two speakers, and the local/remote segment attribution confusion has a current-branch regression fix | Post-deploy production proof of the attribution fix is still missing |
| Audio playback linked to transcript timestamps | PARTIAL | timestamp labels, speaker/source-role mapping, and playback shell are proven locally by cabinet contract/unit/web-shell tests | interactive audio playback, waveform, and transcript-segment seek behavior are not implemented/proven; production processed-meeting playback proof is also missing |
| Authentication/session management | PARTIAL | 013/036 status and owner proof evidence | Production 045 result review under real owner session still missing; proof path is `production-e2e-proof-plan.md` |
| Retention/deletion/admin governance | PARTIAL | 017/018/031/032 status and tests | Production user rollout journey and future table classifications remain bounded |
| Signed/notarized production installer | MISSING | Local ad-hoc build and installed app smoke only | Signed/notarized production installer evidence remains separate |
| Production upload-to-transcript-to-review journey | PARTIAL | Local tests/fixtures, local replay of one real speakerphone/degraded artifact through server finalize/processing-start, one live production upload-to-MediaScribe-to-review result after targeted manual pickup, and current-branch source attribution fix | Needs 045 deploy and metadata-safe production e2e proving auto-start/reuse without manual pickup plus source attribution quality |
| Real echo/noise suppression for speakerphone microphone cleanup | DECISION / OUT OF 045 | 044 research/spec track exists separately | Product must decide whether 044 is required for MVP or truthful imperfect-audio processing is acceptable |
| Clean-room UI/UX distance from Krisp | PARTIAL | 030/036 status, clean-room reference evidence, and Russian-first web fixture runtime rechecked after evidence sync | Final stakeholder/production runtime evidence remains bounded |

## 045 Feature Requirements

| 045 requirement | Status | Evidence |
|---|---|---|
| FR-001 imperfect but structurally valid packages proceed | PROVEN LOCALLY | `DesktopUploadQueueTests`, leakage finalization tests, manifest tests |
| FR-002 unsafe packages remain blocked | PROVEN LOCALLY | upload queue tests, finalize integrity tests, ingest contract |
| FR-003 integrity status separated from quality status | PROVEN LOCALLY | queue profile/warning metadata tests, validation log |
| FR-004 accepted package auto-starts or reuses processing | PROVEN LOCALLY | finalize auto-start tests, processing dispatch helper |
| FR-005 idempotent pickup/retry | PROVEN LOCALLY | duplicate finalize/pickup tests |
| FR-006 safe processing states exposed | PROVEN LOCALLY | processing status contracts and cabinet runtime |
| FR-007 transcript/diarization availability visible in web and desktop | PROVEN LOCALLY | MediaScribe happy path, cabinet detail, desktop sync/review link tests |
| FR-008 failed/blocked processing preserves upload success | PROVEN LOCALLY | dependency blocker and status tests |
| FR-009 offline delayed upload preserved | PROVEN LOCALLY | upload queue restart/reconcile tests |
| FR-010 no content/secrets in status/diagnostics/evidence | PROVEN LOCALLY | no-secret contracts, redaction tests, include-set text scan |
| FR-011 deletion/access authoritative | PARTIAL | access/RLS/status tests, current status, and disposable Postgres direct SQL RLS proof | production 045 access/deletion proof missing |

## Conclusion

Feature `045` is locally implementation-ready and materially closes the
recording-to-transcript result loop. It is not enough to claim full MVP.

Latest local PR-readiness evidence also shows the 045 include-set patch applies
cleanly over `origin/master` `a89cf91`, focused macOS/cabinet rechecks pass,
`infra/scripts/ci-local.sh` passes with 546 server tests, and
`infra/scripts/cd-remote.sh --dry-run` still passes without production mutation.
Those checks lower PR and deploy-preflight risk, but they do not replace
merge/release approval, clean low-leakage desktop proof, or post-deploy 045
production e2e proof.

Prior production e2e evidence from earlier slices, including `015`, is useful
background proof that the deployed processing architecture can work. It is not
accepted as proof that the new `045` behavior is live, because `045` changes
local upload eligibility, server finalize-triggered processing, review state,
and evidence boundaries while the branch remains unmerged and undeployed.

The minimum remaining blockers before a full MVP claim are:

1. Commit, PR, review, merge, and release/deploy the 045 implementation.
2. Prove post-deploy 045 production upload-to-transcript-to-review with
   metadata-safe evidence and no manual processing pickup, using
   `production-e2e-proof-plan.md`.
3. Complete clean low-leakage/headphones `saved` / `ready` desktop proof from a
   trusted app identity. Speakerphone/high-leakage Record/Stop, upload, and
   manual-pickup production review are partially proven, but post-deploy
   upload-to-review and source attribution still need proof. The desktop
   post-upload reconcile gap is fixed locally and runtime-checked, but a
   system `/Applications` install proof still needs an administrator-
   authenticated install path. A metadata-only scan of local recording
   manifests on 2026-06-24 found 11 old `v2` `saved` / `ready` packages and 0
   current-branch/schema-v3 `saved` / `ready` packages suitable for closing
   this gate. A later continuation scan of the 12 newest schema-v3 dual-track
   manifests found only `degraded` or `failed` packages, so this blocker remains
   open.
4. Decide whether launchable AI notes/actions are required for MVP or explicitly
   deferred.
5. Implement/prove transcript timestamp seek and retained-audio playback, or
   explicitly defer that PRD meeting-detail requirement for a narrower pilot.
6. Decide whether real `044` AEC/noise suppression is required for MVP quality,
   or whether MVP accepts best-available transcription from imperfect recordings
   with truthful labels.
7. Capture production owner-auth web/desktop review proof for processed results.
8. Execute the ordered closeout path in `mvp-closeout-action-plan.md` and
   update this audit after each approval-gated evidence step.

Until those items are complete, the strongest truthful status remains local
045 readiness plus a clear PR/release path, not full MVP.
