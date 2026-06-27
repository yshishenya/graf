# Admin UI Contract

The admin UI is a browser-owned workspace governance surface. It is not a
desktop-embedded recorder workflow and not a marketing or landing page.

## Common UI Rules

- Routes are available to active Owners and Admins only.
- Members and unauthenticated users see access denied or login, without admin
  data.
- Every page shows workspace scope and current actor role.
- Russian-first user-facing labels are required.
- Tables, filters, destructive confirmations, and page navigation must be
  keyboard usable and work on compact desktop/tablet widths.
- UI evidence, screenshots, and audit details must not include secrets, raw
  audio, transcript text, private meeting content, storage identifiers, signed
  URLs, or local paths.

## Desktop Handoff Boundary

- Desktop/embedded requests for `/admin` routes must not render the full admin
  UI inside the recorder shell.
- Desktop route policy must either hand allowed admin routes to the system
  browser or show an access-denied/blocked state without injecting desktop
  headers into an embedded admin surface.

## Navigation

Top-level admin navigation:

- `/admin` - overview
- `/admin/users` - users and invitations
- `/admin/users/{user_id}` - user detail
- `/admin/files` - files and meetings
- `/admin/files/{meeting_id}` - admin meeting/file review
- `/admin/balance` - read-only balance, usage, quotas
- `/admin/metrics` - product metrics
- `/admin/audit` - product audit journal

No support, Analyst, billing, payment, external log platform, global superadmin,
or quota-editing navigation appears in v1.

## Overview Page

Purpose: fastest workspace health scan.

Required content:

- user state summary;
- pending invitations;
- quota/usage risk summary;
- file/processing/deletion health;
- metric freshness summary;
- recent sensitive audit activity.

Required states:

- empty workspace except current Owner;
- quota policy missing;
- metrics current period incomplete;
- audit source unavailable;
- Member denied with no data exposure.

## Users Page

Purpose: create and monitor workspace users.

Required controls:

- search;
- role filter;
- status filter;
- invitation status filter;
- create invitation action;
- revoke pending invitation action where allowed.

Required behavior:

- Owner can invite Owner/Admin/Member if last-owner safety remains true.
- Admin can invite Member only.
- Admin can manage Members only.
- Last active Owner downgrade/deactivation/block/revocation/removal is blocked
  with a clear reason.
- Pending invites show source, target, invited role, expiry, creator, and safe
  status.
- User detail shows role, status, devices, sessions, files, usage contribution,
  and recent metadata-only audit events.

## Files Page

Purpose: govern server-known user files and meetings.

Required filters:

- owner;
- type;
- date;
- processing state;
- retention/deletion state;
- size;
- duration.

Required actions:

- open review;
- download allowed artifact;
- export allowed artifact/package;
- request whole-meeting deletion.

Required safety states:

- cross-workspace meeting denied;
- missing artifact unavailable;
- deletion active or completed unavailable;
- retention/lifecycle block shown truthfully;
- post-egress limits shown truthfully;
- local-only desktop state represented only with safe metadata, never local
  paths.

Deletion confirmation:

- normal destructive confirmation;
- required reason;
- no typed phrase;
- copy must not promise universal erasure outside `2brain Rec` control.

## Balance Page

Purpose: read-only operational usage and quota monitoring.

Required content:

- selected date period;
- recording minutes;
- storage bytes;
- processing jobs;
- usage by user;
- top consumers;
- quota policy state;
- quota risk labels;
- freshness state.

Required exclusions:

- no limit editing controls;
- no tariffs, invoices, debt, payments, credit ledger, top-up, or billing
  integration UI.

Missing policy state:

- say limits are not configured instead of inventing values.

## Metrics Page

Purpose: diagnose product health.

Required metric families:

- adoption/activity;
- usage/quotas;
- recording-to-processing funnel;
- reliability/quality;
- governance.

Each displayed metric must show:

- definition;
- denominator;
- date window;
- freshness;
- source category;
- drill-down path.

Required states:

- current/incomplete period clearly marked;
- metric unavailable when source-backed data does not exist;
- no sample-only production numbers.

## Audit Page

Purpose: one product audit journal for workspace accountability.

Required filters:

- period;
- user;
- action;
- object;
- outcome.

Required sources:

- auth/session/device events;
- admin user/invitation events;
- file review/download/export events;
- deletion request/report events;
- quota/admin metric sensitive events;
- denied sensitive attempts.

Required safety:

- metadata-only details;
- safe labels for deleted/private targets;
- no normal UI path to alter or delete audit history;
- future technical log export may supplement but not replace this journal.

## Desktop Handoff

If a desktop route or embedded view attempts to open an admin page:

- show browser handoff when the actor is allowed to administer the workspace; or
- show access denied when the actor is not allowed; and
- never render hidden full admin UI inside the native recorder.
