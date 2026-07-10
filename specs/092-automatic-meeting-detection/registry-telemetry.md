# 092 Meeting Target Registry And Telemetry

**Status**: Planning contract for `$speckit-plan` and `$speckit-implement`.

**Date**: 2026-07-08

This document defines how GRAF should keep a broad meeting target registry
without hardcoding the full list into the macOS client, and how the client
should automatically send lightweight metadata-only meeting-detection telemetry
for likely VKS candidates without uploading a user's full application inventory
or causing noticeable CPU, memory, battery, or privacy cost.

## Product Goals

1. Include every researched global and Russian meeting target in the registry,
   even when the target is not ready for prompts.
2. Learn which targets work, which targets fail to emit expected signals, and
   which unknown apps repeatedly look like meeting clients.
3. Keep product behavior fail-closed: statistics can suggest support changes,
   but cannot by itself start recording or promote unknown apps to prompt mode.
4. Send only apps that pass a client-side VKS-candidate filter, not every
   installed app and not every microphone-using app.
5. Avoid heavy local work: one native observation stream, event-driven parsing,
   local aggregation, bounded persistence, and rate-limited upload.
6. Keep diagnostics metadata-only, auditable, and disableable by workspace/admin
   policy.

## Architecture

GRAF should split the system into five independent data surfaces:

| Surface | Owner | Purpose | Update path |
| --- | --- | --- | --- |
| Server target registry | Server/admin | Current support state for known targets. | Migration, database, or admin UI. |
| Last-good client cache | Client | Resilient copy of the latest validated server registry. | Automatic desktop fetch with `ETag`. |
| Local user policy | User/workspace | Detection mode, prompt suppression, target-scoped auto-record preferences. | Local settings and workspace policy. |
| Local telemetry rollups | Client | Metadata-only counters and VKS-candidate observations. | Local aggregation, automatic candidate upload, manual diagnostic export. |
| Server candidate review queue | Server/admin | Aggregated likely-VKS unknown apps and known-target health. | Admin review, QA, and registry publishing. |

The client MUST resolve the registry in this order:

1. Latest successfully downloaded remote registry when available.
2. Last-good validated remote registry cache.
3. No registry: automatic detection fails closed while manual recording remains available.

If the remote registry is malformed, unsupported, expired, unsafe, or fails
validation, the client MUST keep using the previous good registry cache when one
exists. Remote registry failures MUST NOT block manual recording.

The remote registry MAY add targets, change target support mode, update labels,
or mark targets as disabled. It MUST NOT disable compiled safety gates such as
visible recording state, one-action Stop, prompt/auto-record requirements,
metadata-only diagnostics, or forbidden-content redaction.

## Registry Shape

The registry should be represented as JSON so it can be served without rebuilding
the client. The server may store it in a database or file, but the client sees a
versioned document. The client/server contract starts at
`specs/092-automatic-meeting-detection/contracts/meeting-target-registry.schema.json`.

Example:

```json
{
  "schemaVersion": 1,
  "registryVersion": "2026.07.08.1",
  "generatedAt": "2026-07-08T12:00:00Z",
  "expiresAt": "2026-08-07T12:00:00Z",
  "targets": [
    {
      "id": "zoom_native_macos",
      "displayName": "Zoom",
      "market": "global",
      "platform": "macos",
      "targetFamily": "native_app",
      "nativeBundleIds": ["us.zoom.xos"],
      "mode": "prompt_enabled",
      "evidence": "runtime_verified",
      "requiredSignals": ["macos_audio_hal_assertion"]
    },
    {
      "id": "vk_teams_native_macos",
      "displayName": "VK Teams",
      "market": "russia",
      "platform": "macos",
      "targetFamily": "native_app",
      "nativeBundleIds": ["ru.mail.messenger-biz-avocado-desktop"],
      "mode": "diagnostic_only",
      "evidence": "installed_verified",
      "requiredSignals": ["macos_audio_hal_assertion"]
    }
  ]
}
```

Registry modes:

| Mode | Prompt behavior | Telemetry behavior |
| --- | --- | --- |
| `prompt_enabled` | May show prompt or honor target-scoped auto-record after hard gates. | Count starts, ends, prompts, decisions, and failures. |
| `diagnostic_only` | No prompt and no auto-record. | Count stable observations and missed/blocked evidence. |
| `blocked_missing_bundle` | No prompt and no native match. | Track whether discovery finds a plausible bundle later. |
| `manual_or_browser_only` | Native detector ignores this target. | Browser/manual paths may report safe support state. |
| `disabled` | No prompt and no detection behavior. | Record only registry health if needed. |

Targets should be stable by `id`, not by display name. Native macOS matching uses
bundle IDs. Browser matching uses service/provider identity and safe URL pattern
classes, not generic browser audio ownership.

## Local Telemetry Model

Telemetry is not a raw event log. It is a bounded rollup produced from detector
events after redaction and classification. The upload/export contract starts at
`specs/092-automatic-meeting-detection/contracts/meeting-detection-telemetry.schema.json`.

Allowed fields:

- `schemaVersion`, `clientVersion`, `platform`, `osVersionMajor`,
  `registryVersion`.
- Daily or hourly time bucket, not exact private meeting time when not needed.
- Known target id, support mode, target family, and safe display label.
- Signal family presence: audio ownership, browser metadata, calendar overlap,
  join intent, system audio activity, adapter health.
- Decision outcome: observed, weak, prompt-eligible, blocked, prompted, skipped,
  suppressed, recorded, ended, missed, health-degraded.
- Reason codes and blocker codes.
- Duration buckets such as `<5s`, `5-30s`, `30s-5m`, `5m+`.
- Counts: observations, stable starts, clean ends, prompt shown, prompt accepted,
  prompt skipped, auto-record started, manual recording near candidate.
- Client-side resource buckets: detector CPU/memory samples, parser restarts,
  dropped events, upload attempts.

Forbidden fields:

- Raw audio, transcript text, summary text, meeting content, screen content.
- Full private URLs, meeting IDs, passcodes, invite links, attendee emails,
  calendar agenda text, private calendar title.
- Raw unified-log lines.
- Raw remote IP addresses, credentials, tokens, signed URLs, passwords, secret
  paths.
- Full local app paths and user home paths.

Unknown app discovery needs one stricter rule: raw unknown app identifiers are
sensitive because they reveal installed or used software. The client MUST NOT
upload every unknown `AudioHAL` bundle owner. It may upload unknown app identity
automatically only after the app passes the VKS-candidate filter below. If
workspace/admin policy disables meeting-detection improvement telemetry, the
client keeps unknown candidate identity local and may upload only aggregate
health counters without bundle IDs.

## Unknown App Discovery

The detector should use the same low-cost macOS stream as known native matching.
It should keep a local candidate table for `AudioHAL` bundle owners that are not
in the registry, excluding known non-target categories such as browsers and
audio-processing utilities before upload.

An unknown native app becomes a local discovery candidate only when:

1. The app emits stable audio ownership after the start debounce.
2. The ownership remains active longer than the short-test bucket.
3. It is not in the explicit non-target denylist.
4. Optional safe hints raise confidence, such as calendar overlap, user manual
   recording soon after, repeated observations across days, or installed app
   metadata.

Unknown discovery MUST NOT show a record prompt in the first release. It only
helps product/QA decide what to add or validate next.

### VKS-Candidate Filter

The client should compute a local candidate score before uploading unknown app
identity. The filter is intentionally conservative: it is allowed to miss some
new apps at first, but it must avoid sending general software inventory.

The first scoring model:

| Signal | Score | Notes |
| --- | ---: | --- |
| Stable `AudioHAL bundle ownership` after debounce for at least 30 seconds | +2 | Baseline live communication signal. |
| Observation repeats on two different days or sessions | +1 | Helps separate one-off tests from real meeting tools. |
| User starts manual recording within a short window around the observation | +3 | Strong "probably a meeting" hint without reading meeting content. |
| Calendar or join-intent hint exists during the observation | +2 | Store only boolean/category, not event text or URLs. |
| App display name or bundle ID contains known meeting tokens | +2 | Examples: `meet`, `meeting`, `call`, `video`, `talk`, `conf`, `teams`, `telemost`, `jazz`, `link`, `trueconf`, `mts`, `vk`, `kontur`, `iva`, `dion`, `vinteo`, `pachca`, `express`, `tada`, `roschat`, `pruffme`. |
| Signing/vendor metadata matches a known VKS vendor pattern | +2 | Only for observed app bundle, not broad app scans. |
| Duration is under 5 seconds | -3 | Likely device check or transient open. |
| Explicit non-target category match | block | Browsers, Krisp/audio processors, system services, media players, audio editors, games, screen recorders, and known utilities. |

Upload rule for unknown identity:

1. Never upload if the app matches an explicit non-target rule.
2. Upload raw candidate identity only when score is at least 4.
3. Upload at most one candidate rollup per app per day.
4. Keep raw unified-log lines, window titles, full paths, URLs, and calendar text
   out of both local rollups and upload payloads.

This means GRAF sends "this unknown observed app looks like a meeting client"
instead of "here are all apps using the microphone."

Local unknown candidate fields:

- bundle ID, display name, signing team ID, version, and install source when
  available without privileged scanning.
- first/last observed bucket.
- stable observation count and duration buckets.
- whether manual recording started within a short window.
- whether a calendar/join-intent hint was present as a boolean/category only.
- whether the app matched an explicit non-target rule.
- candidate score and candidate filter reason codes.

Raw app path, full calendar details, raw log lines, and window titles are not
stored in unknown discovery rollups.

## Known Target Health

For every target in the registry, the client should count whether the target
behaved as expected:

| Case | Meaning |
| --- | --- |
| `target_observed` | Expected signal appeared and passed debounce. |
| `target_clean_end` | Expected signal disappeared and passed end debounce. |
| `target_short_test` | Signal appeared briefly and ended before the prompt window. |
| `target_prejoin_like` | Stable audio ownership appeared but prompt was blocked by prejoin/device-test heuristics or user skip. |
| `target_missed_manual_start` | User started manual recording near a known target observation that did not prompt. |
| `target_expected_signal_absent` | Registry/browser/calendar hints existed, but the required native/browser signal did not appear. |
| `target_health_degraded` | Adapter/log stream/parser permission or schema failed. |

This lets the product answer both questions:

- Which known targets are reliable enough to promote?
- Which targets are listed but not actually working on user machines?

## Upload And Review Flow

Local telemetry should be stored first in:

```text
~/Library/Application Support/GRAF/MeetingDetection/telemetry-rollups/
```

Automatic upload behavior:

1. Default release: automatically upload bounded metadata-only rollups for known
   target health and unknown apps that pass the VKS-candidate filter.
2. Unknown native app identity is included only after the candidate filter passes
   and the app is not in a non-target category.
3. Workspace/admin policy may disable improvement telemetry; detection and manual
   recording must continue to work without upload.
4. Manual diagnostic export remains available for richer troubleshooting, but it
   is not required for the normal candidate review queue.

Uploads should be batched and small:

- Endpoint: `POST /api/v1/desktop/meeting-detection/telemetry`.
- Max one upload attempt per 24 hours by default, plus an optional immediate
  upload when a new high-score candidate first appears and the app is idle.
- Flush on app quit only if data is already aggregated and small.
- Use exponential backoff after failures.
- Cap local retained telemetry, for example 14 days or 1 MB.
- Cap one upload payload, for example 50 KB compressed.
- Never keep raw unified-log lines after parsing.

Server-side review should aggregate:

- unknown native app candidates by number of reporting installations, duration
  buckets, manual-record-nearby count, and market/workspace segment if allowed.
- known target health by registry version, client version, OS major version, and
  app version when allowed.
- false-positive indicators: prompt skipped, prompt suppressed, short test,
  prejoin-like, manual stop soon after auto-start.
- missed indicators: manual recording near unknown/known observation, expected
  signal absent, adapter degraded.

## Admin Review Queue

The server should expose a workspace/admin page:

```text
/admin/meeting-detection
```

The admin review response contract starts at
`specs/092-automatic-meeting-detection/contracts/meeting-detection-admin-review.schema.json`.

The page should show three queues:

| Queue | Purpose |
| --- | --- |
| VKS candidates | Unknown native apps that passed the client VKS-candidate filter. |
| Known target health | Existing registry targets that work, fail, or miss expected signals. |
| Registry drafts | Proposed changes waiting for validation or publish. |

Candidate cards should show only safe metadata:

- display name, bundle ID, signing team ID, version samples, platform, OS major
  version buckets, registry version, client version buckets.
- candidate score, reason codes, stable observation count, duration buckets,
  manual-record-nearby count, calendar/join-hint count.
- number of reporting installations or workspaces, first/last observation
  buckets, and whether the app is already known as non-target.

Candidate cards MUST NOT show raw log lines, private meeting URLs, passcodes,
window titles, calendar titles, attendee emails, audio, transcripts, app paths,
or user home paths.

Admin actions:

| Action | Result |
| --- | --- |
| Mark as non-target | Adds or updates a server denylist entry so future clients suppress the candidate. |
| Merge with existing target | Links the candidate evidence to an existing registry target. |
| Add as `diagnostic_only` | Creates a registry draft with bundle IDs and safe label, but no prompts. |
| Request package/runtime validation | Keeps the candidate in review with a QA checklist. |
| Promote to `prompt_enabled` | Allowed only after package identity, runtime audio-ownership start, runtime end, idle/prejoin behavior, and product gates pass. |
| Disable target | Publishes a registry mode that prevents prompts and detector decisions. |

Every admin action must be audited with actor, timestamp, previous value, new
value, reason, and linked evidence. Publishing a registry version should be a
separate explicit action so review does not silently change client behavior.

Promotion from discovery to product behavior requires human review and QA:

1. Unknown app appears in telemetry or package research.
2. Add target to registry as `diagnostic_only`.
3. Validate package identity and real audio-ownership start/end behavior.
4. Promote to `prompt_enabled` only after target-specific QA and product gates.
5. Keep target-scoped auto-record opt-in separate from registry support.

## Resource Budget

The macOS client should avoid polling installed apps or windows as a baseline.
For the first native detector:

- Run at most one `/usr/bin/log stream` process while detection/detect-only is
  enabled.
- Parse only passive macOS `AudioHAL` ownership events.
- Keep active state in memory as a small map keyed by bundle ID.
- Aggregate counters in memory and write rollups periodically.
- Do not scan `/Applications` repeatedly. Resolve app metadata lazily only for
  observed candidate bundle IDs.
- Avoid network upload during active recording unless explicitly required.
- Fetch the remote registry with `ETag`/`If-None-Match` and a 24-hour default
  refresh interval.
- Stop or degrade the detector if parser failures, restart loops, CPU, memory,
  or battery thresholds exceed the resource gate.

Suggested first resource gates:

| Metric | First gate |
| --- | --- |
| Idle detector CPU | p95 below 1% over a 10 minute idle window. |
| Monitoring detector CPU | p95 below 2% while parsing normal ownership traffic. |
| Memory overhead | below 30 MB steady-state additional RSS. |
| Disk writes | below 256 KB/day for telemetry rollups before upload. |
| Network | one registry fetch/day, one telemetry upload/day, and at most one immediate high-score candidate upload/day. |
| Local retention | 14 days or 1 MB, whichever comes first. |

These are planning gates; implementation tasks should replace them with measured
thresholds if local validation shows different realistic numbers.

## Product Behavior Summary

| Observation | Registry state | Product behavior | Telemetry |
| --- | --- | --- | --- |
| Zoom emits stable `AudioHAL` ownership for `us.zoom.xos` | `prompt_enabled` | Prompt or target-scoped auto-record after hard gates. | Known target success/failure counters. |
| VK Teams emits stable audio ownership | `diagnostic_only` | No prompt in first release. Manual recording remains available. | Known target diagnostic counters. |
| Unknown app emits stable audio ownership and passes VKS-candidate filter | Not in registry | No prompt. No recording. | Automatic candidate upload to admin review queue unless workspace/admin telemetry is disabled. |
| Unknown app emits stable audio ownership but fails VKS-candidate filter | Not in registry | No prompt. No recording. | Local aggregate only; no raw app identity upload. |
| Browser emits audio ownership | Browser is excluded from native allowlist | No native-app prompt. Browser path may evaluate metadata/calendar/join intent. | Browser-support counters only after browser adapter rules pass. |
| Krisp/audio utility emits audio ownership | Explicit non-target | Ignore for decisions. | Optional non-target suppression counter, no app-specific upload by default. |

This design keeps the target list broad and updatable while ensuring a remote
registry or telemetry signal cannot silently broaden recording behavior.
