# Calendar Settings UI Contract

**Feature**: 063-calendar-settings-ui

## Purpose

Define what the web cabinet Calendar settings surface must expose to users. This is a UI/read-model contract over the read-only calendar foundation from feature 060.

## Navigation Contract

- Entry path meaning: `Настройки -> Интеграции -> Календари`.
- The first screen is a working settings screen.
- The active navigation state must make the user understand they are in calendar integration settings.
- Users without connected sources see the read-only boundary and provider choices, not a disabled placeholder.

## Source Card Contract

Each connected source row/card must show:

- provider label;
- safe account/source label;
- connection state;
- selected calendar count;
- sync health state;
- last successful sync time when available;
- safe error category when applicable;
- actions available for the state: choose calendars, sync, reconnect, disconnect.

Forbidden:

- full email addresses in account/source/calendar labels;
- raw tokens;
- app passwords;
- refresh tokens;
- raw provider account IDs;
- raw calendar URLs;
- raw provider payloads;
- private event text;
- attendee email dumps;
- signed links;
- passcodes;
- full private meeting URLs.

## Provider List Contract

The provider list must include these user-facing labels from the provider catalog:

- Яндекс Календарь;
- Mail.ru Календарь;
- Exchange / Exchange Server;
- Bitrix24;
- VK WorkSpace / CalDAV;
- Mailion / МойОфис;
- R7-Офис;
- CommuniGate Pro;
- RuPost;
- Nextcloud / SOGo CalDAV;
- Другой CalDAV.

Each provider must show the connection method category in user language:

- app password or account credential;
- manual CalDAV URL;
- provider-specific/admin-limited connection.

## Calendar Selection Contract

- No calendars are selected automatically after source connection.
- A connected source with zero selected calendars is valid.
- The selection interface must show every readable calendar, selected state, source, selected count, and safe visibility state.
- Calendar labels must be redacted or replaced with a generic safe label when provider data contains URLs, email addresses, passcode-like strings, token-looking strings, signed/private links, raw IDs, or private names.
- Saving an empty selection keeps the source connected but inactive for upcoming meetings and prompts.
- The existing selected-calendar operation must support an empty selected calendar list for 063 behavior.

## Event Category Defaults Contract

Default behavior after calendars are selected:

- Include timed events with participants or a meeting link/location.
- Exclude all-day events.
- Exclude private/free-busy prompt candidates.

Users can change event-category preferences in settings. Manual recording remains available even when a category is excluded from prompts.

## Sync Health Contract

Show a source as stale when:

- last successful sync is older than 24 hours; or
- latest sync attempt failed.

Stale state must appear:

- on the source row/card;
- in source sync details;
- in upcoming preview only when the stale source affects preview confidence.

The stale state must show last successful sync time if available and an action such as manual sync, reconnect, or safe troubleshooting.

## Upcoming Preview Contract

Preview must reflect:

- selected calendars;
- event-category preferences;
- private/free-busy policy;
- source stale/current confidence;
- overlap conflict groups;
- duplicate event grouping.

Preview must not claim to be current when stale source data affects it.
Preview event titles must be redacted or replaced with a generic safe label when provider data contains URLs, email addresses, passcode-like strings, token-looking strings, signed/private links, raw IDs, or private names.

## Overlap And Duplicate Contract

- Overlapping different events are shown as a conflict group during the overlapping interval.
- The UI must not silently choose a calendar event for join or recording context.
- The user can choose one event or continue without calendar context.
- If recording already has calendar context, a later overlapping event must not switch the context automatically.
- Events are duplicates only when they share a stable provider event ID or the same meeting link.
- Similar titles, organizers, or close times alone do not deduplicate events.

## Prompt Settings Contract

Settings may control:

- one-minute-before-meeting join/open prompt;
- at-start record prompt;
- local upcoming display where available.

Settings must not enable:

- real auto-record;
- hidden recording;
- bot auto-join;
- calendar mutation;
- summary/transcript/report sending;
- attendee-based sharing.

If a future "do not ask again and record automatically" choice is visible, it must be disabled, policy-blocked, or clearly marked as outside 063.

## Disconnect Contract

Disconnect confirmation must state:

- future sync stops;
- credentials are removed or revoked where 2brain Rec controls them;
- already linked meeting context follows meeting retention/deletion policy;
- deletion outside 2brain Rec control is not promised.

## Accessibility Contract

The flow must be operable by keyboard and screen reader for:

- provider selection;
- connection method form;
- calendar selection;
- manual sync;
- prompt settings;
- upcoming preview;
- disconnect confirmation.

Progress, stale/error states, selected counts, and policy-constrained controls must have understandable labels.
