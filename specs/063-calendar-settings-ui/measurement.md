# Measurement Plan: Calendar Settings UI

**Feature**: 063-calendar-settings-ui
**Cadence**: weekly during internal/beta rollout, then release-readiness review.

No live product analytics source was available in this run. This document defines what to measure going forward.

## Initiative Summary

The feature should make calendar setup discoverable, understandable, and safe. Success is not "many users connect calendars at any cost"; success is that users can find settings, connect intentionally, select calendars explicitly, understand read-only boundaries, recover from sync problems, and continue using manual recording at any time.

## Primary KPIs

### 1. Calendar Settings Setup Completion

- **Definition**: percentage of users who open Calendar settings and reach a usable state within the same session.
- **Usable state**: at least one source connected and at least one calendar selected, or user intentionally leaves all calendars unselected after seeing the inactive-state explanation.
- **Calculation**: `usable_state_sessions / calendar_settings_open_sessions`.
- **Why it matters**: reflects whether the flow is understandable without support.
- **Target**: provisional beta target `>=70%` for users with valid app-password, account, or CalDAV credentials.
- **Caveat**: separate provider/admin failures from UI abandonment.

### 2. Safe Understanding Confirmation

- **Definition**: percentage of tested users who can correctly answer the read-only boundary after seeing the settings screen.
- **Required answers**: 2brain Rec reads selected future events; does not change calendar events; does not auto-record in 063; does not send summaries or grant attendee access.
- **Calculation**: `correct_boundary_responses / tested_users`.
- **Why it matters**: calendar access is privacy-sensitive; misunderstanding is a product failure even if connection succeeds.
- **Target**: `>=90%` in moderated/internal comprehension checks before broad release.
- **Caveat**: do not infer comprehension from clicks alone.

### 3. Recoverable Sync Trust

- **Definition**: percentage of stale/error/needs-action source states where the user sees a safe cause and a valid next action without opening logs or asking support.
- **Calculation**: `recoverable_problem_states / total_problem_states_reviewed`.
- **Why it matters**: calendar features become untrusted when freshness is unclear.
- **Target**: `>=95%` of simulated problem states pass QA; track real support cases after rollout.
- **Caveat**: provider outages may be unrecoverable, but the UI still needs to explain what is known.

## Driver Metrics

| Driver | Definition | Decision It Supports |
| --- | --- | --- |
| Settings discovery time | Median time from cabinet entry to Calendar settings page. Target: under 30 seconds in usability check. | Whether navigation labels and IA work. |
| Provider start rate | Users who click a provider after opening settings. | Whether provider list and boundary copy feel clear enough to proceed. |
| Calendar selection completion | Connected sources that move from zero selected calendars to saved selection. | Whether the picker is understandable. |
| Manual sync success feedback | Manual sync attempts that show running/success/already-running/error state. | Whether sync feedback is observable. |
| Conflict chooser resolution | Overlap conflict prompts resolved by choosing event or continuing without context. | Whether ambiguity is handled explicitly. |

## Guardrails

| Guardrail | Definition | Must Not Happen |
| --- | --- | --- |
| Secret/private data leakage | Any rendered UI, logs, tests, screenshots, or evidence containing raw tokens, app passwords, private event text, attendee email dumps, signed links, passcodes, or raw provider payloads. | Zero tolerance. |
| Surprise automation | Any 063 path that starts recording automatically, joins a bot, mutates a calendar event, sends a message, sends a summary, or grants attendee access. | Zero tolerance. |
| Manual recording blocked | User cannot start/stop manually because calendar is disconnected, stale, empty, or errored. | Zero tolerance where policy allows recording. |
| Wrong context auto-switch | Active recording context changes automatically when another overlapping event starts. | Zero tolerance. |
| Accessibility blocker | Keyboard or screen reader cannot complete provider choice, calendar selection, manual sync, prompt settings, or disconnect. | No P0/P1 before release. |

## Instrumentation Events

Use metadata-only events. Do not include provider tokens, app passwords, full event text, attendee emails, signed links, passcodes, or private URLs.

| Event | Safe Fields |
| --- | --- |
| `calendar_settings_opened` | surface (`web`/`embedded_macos`), source_count, selected_calendar_count_total |
| `calendar_provider_connect_started` | provider_preset_id, method_category |
| `calendar_provider_connect_finished` | provider_preset_id, result_category (`connected`/`cancelled`/`denied`/`failed`/`admin_required`) |
| `calendar_selection_saved` | source_id_hash, selected_count, readable_count, zero_selected |
| `calendar_sync_requested` | source_id_hash, previous_sync_state |
| `calendar_sync_result_seen` | source_id_hash, safe_state, stale, has_last_success |
| `calendar_prompt_setting_changed` | setting_key, enabled |
| `calendar_overlap_conflict_seen` | candidate_count, recording_active |
| `calendar_overlap_conflict_resolved` | resolution (`event_selected`/`without_context`/`dismissed`) |
| `calendar_source_disconnect_confirmed` | provider_preset_id, had_selected_calendars |

## Review Questions

- Are users finding Calendar settings without support?
- Are users intentionally selecting calendars, or abandoning after provider connection?
- Do stale/error states lead to retry/reconnect rather than support confusion?
- Are overlap conflicts resolved explicitly instead of silently misattributed?
- Is any event suggesting hidden auto-record, bot join, summary sending, or attendee sharing?

## Target Recommendation

Use provisional targets until beta data exists:

- Find settings within 30 seconds in moderated usability checks.
- Connect valid provider and select calendars within 3 minutes.
- Safe understanding confirmation at or above 90%.
- Zero secret/private-data leakage.
- Zero surprise automation.
- Zero manual Record/Stop regression.

## Guided Check Evidence - 2026-06-28

Sample: `n=1` internal implementation walkthrough, no external moderated user
participants yet. Treat this as implementation-readiness evidence only, not as
final usability evidence for the 90% comprehension targets.

### SC-002: Connect And Select Within 3 Minutes

- Setup: synthetic provider fixtures and implemented cabinet routes.
- Result: automated flow covers connect success, zero selected by default,
  calendar selection, deselect-all, save feedback, and source contribution.
- Timing: not timed with a human participant; expected path is short enough for
  the 3-minute target, but real guided timing remains required before rollout.
- Blockers: no live provider participant run in this closeout.

### SC-003: Read-Only Boundary Understanding

- Setup: internal read-through of the implemented settings copy and contract
  assertions.
- Result: copy explicitly says 2brain Rec reads selected future calendar
  events, does not mutate calendars, does not send messages/summaries, does not
  auto-record in 063, and does not grant attendee access.
- Evidence: focused server contract/unit/integration checks passed `77 passed`;
  forbidden-content scan found no secret/private evidence leaks.
- Blockers: no moderated participant sample yet, so the 90% target is not
  statistically proven.

### SC-014: Prompt Settings And Manual Recording

- Setup: internal read-through plus macOS/native-shell tests.
- Result: prompt copy and unavailable-state copy state that manual Record/Stop
  remains available without calendar connection and that disabling prompts does
  not disable manual recording.
- Evidence: focused macOS calendar/cabinet checks passed `97 tests`; full
  macOS validation passed `693 tests`; full local CI passed with
  `968 passed, 4 skipped, 148 warnings` and
  `ci_local_result=pass`.
- Blockers: needs real participant comprehension check before beta rollout.
