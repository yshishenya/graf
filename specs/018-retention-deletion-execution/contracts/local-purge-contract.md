# Contract: Local Desktop Purge

Feature: `018-retention-deletion-execution`
Date: 2026-06-16

## Ownership

The server owns deletion policy and report truth. Desktop clients own only
local filesystem actions within their sandbox/local buffer locations and return
metadata-only acknowledgement.

## Task Creation

When deletion starts, the server creates purge tasks for registered devices
that may hold:

- local recording buffers;
- local upload retry packages;
- local export/package artifacts created by the desktop;
- diagnostic snippets controlled by the app.

The task payload must include only:

- `task_id`;
- `meeting_id`;
- `task_type`;
- safe reason code;
- expiry deadline;
- acknowledgement endpoint.

The payload must not include local paths, filenames derived from private
meeting titles, object keys, transcript snippets, screenshots, or dependency
identifiers.

## Device Polling

Desktop clients may call `GET /api/v1/desktop/local-purge-tasks` with normal
authenticated device headers. The server returns only tasks scoped to the
current workspace and device id.

Valid task states visible to desktop:

- `pending`;
- `claimed`;
- `acknowledged`;
- `failed`;
- `expired`.

## Acknowledgement

Desktop clients acknowledge with:

- `state`: `acknowledged`, `failed`, or `local_expiry_relied_upon`;
- `reason_code`: safe enum;
- `client_version`: optional;
- `completed_at`: optional client timestamp.

Acknowledgement must not include:

- path strings;
- raw filenames;
- file hashes;
- private meeting title fragments;
- transcript or summary snippets;
- screenshots;
- diagnostic bundle contents.

## Offline And Unreachable Devices

If a device does not acknowledge before task expiry:

- the deletion report remains truthful as `local_unreachable` or
  `local_expiry_relied_upon` based on policy;
- server purge completion may still be shown separately;
- the report must not imply local cleanup was verified.

Late acknowledgements can update the report from pending/unreachable to
acknowledged when policy still allows it.

## Desktop UX

The desktop app may show a quiet local status only if user action is required.
It must not hide the native active capture indicator, one-action Stop, upload
queue truth, or current cabinet embedded route. Local purge work must not block
recording controls unless it touches an active local buffer, in which case the
recording remains protected and the task reports a safe failure/retry reason.
