# UX Research: Calendar Settings UI

**Feature**: 063-calendar-settings-ui
**Date**: 2026-06-27

## Scope

Product: 2brain Rec calendar integration settings.
Audience: users who want future meetings to appear in 2brain Rec without giving the product surprising recording, sharing, or calendar-write power.
Time horizon: current public product and platform patterns available on 2026-06-27.
Sources: public references plus current feature 063/060 repository context. No internal analytics or support system was available in this run.

## Executive Read

Calendar settings succeed when the screen answers three questions immediately: what is connected, which calendars are active, and what will happen before a meeting. Public meeting-assistant products often connect calendars to auto-join, auto-record, and auto-share, so 2brain Rec needs unusually explicit copy that 063 is read-only and prompt-only. Calendar products also commonly separate connected account state from per-calendar selection, which supports the 063 choice to connect first and select calendars explicitly. Sync trust is a visible UI problem: users need last successful sync, current/failed state, and recovery actions near the source, not hidden in logs. The hardest interaction is not provider connection; it is ambiguity after multiple calendars are selected, especially duplicate events and partial overlaps. The best 063 design is therefore a calm settings page with strong status, explicit calendar selection, safe preview, and no automatic recording behavior.

## Ranked UX Problems

### 1. Users cannot tell which calendars the product is actually using

- **User goal**: connect an account but limit 2brain Rec to relevant work calendars.
- **Surface**: connected source list, calendar picker, upcoming preview.
- **What breaks**: if the UI only says "calendar connected", users cannot know whether personal, shared, delegated, or holiday calendars are contributing prompts.
- **Evidence**: Reclaim documents "Connected Calendar Settings" as the place to change which calendars are checked, and its overview points users to `Settings > Calendars` to inspect accounts and sub-calendars.
- **Severity**: P1.
- **Frequency signal**: high for users with more than one calendar or shared calendars.
- **Confidence**: high.
- **Product move**: show every connected source with selected calendar count; open into a per-source calendar list; make zero selected calendars valid and visibly inactive.

### 2. Users may assume calendar connection means auto-join, auto-record, or auto-share

- **User goal**: get useful prompts without surprise recording or sharing.
- **Surface**: read-only boundary, prompt settings, disabled/future auto-record affordance.
- **What breaks**: meeting assistant category norms teach users that calendar integration can trigger a bot or automatic recording.
- **Evidence**: Otter describes calendar connection as enabling Notetaker to automatically join, record, summarize, and share meetings. Fireflies exposes auto-join and auto-record rules, including "all meetings with web-conf link" and manual invite mode.
- **Severity**: P1.
- **Frequency signal**: high because these competitors shape expectations.
- **Confidence**: high.
- **Product move**: put the read-only boundary at the top of the settings page and repeat it near prompt settings: "не меняем события, не подключаемся сами, не рассылаем саммари".

### 3. Provider permission wording can be broader than product behavior

- **User goal**: understand what they are granting and why.
- **Surface**: provider connect sheet, app-password/CalDAV form, provider-limited state.
- **What breaks**: provider instructions and admin policies can use technical calendar-access wording; the product must translate that into practical 063 behavior.
- **Evidence**: Calendar and integration settings patterns separate connection method, active calendars, and sync health rather than expecting users to infer product behavior from provider wording.
- **Severity**: P1.
- **Frequency signal**: medium to high for admin-controlled workspaces and manual CalDAV deployments.
- **Confidence**: high.
- **Product move**: before credential submission and after provider-limited outcomes, show plain Russian copy: 2brain Rec reads selected future events for prompts/context, credentials stay server-owned, desktop does not store provider credentials.

### 4. Sync state loses trust when it lacks freshness and recovery language

- **User goal**: know whether upcoming meetings are current and how to fix failures.
- **Surface**: source card, sync details, upcoming preview.
- **What breaks**: "connected" can be technically true while data is old or latest sync failed.
- **Evidence**: Merge exposes current sync status, most recent finished sync, last successful finished time, and states like disabled, done, failed, partially synced, paused, and syncing.
- **Severity**: P1.
- **Frequency signal**: medium; failures are episodic but trust damage is high.
- **Confidence**: high.
- **Product move**: source card shows connected/needs action/expired/error/disabled plus last successful sync; stale means older than 24 hours or latest attempt failed; preview warns only when stale data affects confidence.

### 5. Overlaps and duplicates can create wrong recording context

- **User goal**: start or continue recording with the right meeting context.
- **Surface**: upcoming preview, pre-meeting prompt, at-start prompt, active-recording context chooser.
- **What breaks**: overlapping meetings are not always duplicates; choosing silently can attach the wrong title/context to a recording.
- **Evidence**: Public settings patterns show connected calendars as multiple inputs, while 2brain Rec's privacy model makes wrong context a trust issue. This is an inference from the feature 063/060 product boundary, not a direct competitor claim.
- **Severity**: P1.
- **Frequency signal**: medium for multi-calendar users; high impact when it happens.
- **Confidence**: medium-high.
- **Product move**: deduplicate only by stable provider event ID or same meeting link; show partial overlaps as conflict groups only during the shared interval; never switch active recording context automatically.

## Source Map

- Reclaim connected calendar settings and overview: useful for "connected accounts + choose calendars" mental model.
- Otter Notetaker auto-join and auto-share help: useful anti-reference for clearly separating 063 from auto-join, auto-record, and attendee sharing.
- Fireflies auto-join settings: useful anti-reference for why 2brain Rec needs manual-control language.
- Merge sync status docs: supports showing current sync, last finished sync, failed/partial/syncing/disabled states.
- Vercel Web Interface Guidelines: used as implementation-quality checklist for labels, focus, semantic controls, async status, long text, destructive confirmation, reduced motion, and locale-safe dates.

## Opportunity Map

### Fix This Week

- Make `Настройки -> Интеграции -> Календари` reachable in web and embedded cabinet.
- Keep the read-only boundary visible as progressive disclosure below the primary setup path, not as a top disclaimer.
- Show connected source cards with selected count, sync state, last successful sync, and actions.
- Add calendar picker where zero selected calendars is allowed and visibly inactive.

### Fix This Quarter

- Add safe upcoming preview that reflects selected calendars, event category preferences, duplicates, overlaps, and stale source confidence.
- Add per-source recovery states for expired credentials, provider-limited access, rate limits, timeouts, and manual sync already running.
- Add embedded macOS verification that native active recording controls stay visible while settings is open.

### Needs Deeper Research

- Whether real auto-record should exist at all and what consent/audit model it would require.
- Workspace-level admin policy for restricting personal calendar providers or provider methods.
- User comprehension test for Russian privacy copy before connecting a calendar.

## References

- Reclaim connected calendar settings: https://help.reclaim.ai/en/collections/3755428-connected-calendar-settings
- Reclaim connected calendar overview: https://help.reclaim.ai/en/articles/6516165-connected-calendar-overview
- Otter auto-join: https://help.otter.ai/hc/en-us/articles/13674910923671-Automatically-add-Otter-Notetaker-to-your-meetings
- Otter auto-share: https://help.otter.ai/hc/en-us/articles/20424842990999-Manage-auto-share-settings
- Fireflies auto-join settings: https://guide.fireflies.ai/articles/5074225515-fix-fireflies-auto-join-settings
- Merge sync status: https://docs.merge.dev/merge-unified/filestorage/data-management/sync-status/list
- Web Interface Guidelines: https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
