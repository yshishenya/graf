# Contract: Artifact Egress

Feature: `017-access-sharing-downloads`
Date: 2026-06-16

## Ownership

All artifact egress is owned by the Rec server. Browser and desktop clients may
request downloads or exports, but they never receive dependency credentials,
object-store keys, signed dependency URLs, raw filesystem paths, or MediaScribe
identifiers.

Desktop shells may embed or open the web routes. They must not proxy artifact
bytes, store server credentials, or implement a separate policy decision.

## Egress Classes

- `audio`: stored local microphone/system audio artifacts when policy permits.
- `transcript`: generated transcript text or transcript file when processing is
  available and policy permits.
- `summary`: accepted summary/notes artifact when available and policy permits.
- `package`: policy-filtered bundle containing only currently permitted
  artifacts plus a metadata-safe manifest.

## Required Decision Order

Each download/export request follows this order:

1. Authenticate the viewer.
2. Resolve tenant/workspace/device context.
3. Compute effective meeting access without exposing private content on denial.
4. Re-check artifact lifecycle and per-artifact policy.
5. Persist a metadata-only audit event for the request and policy outcome.
6. Return content only if the audit event was successfully persisted.
7. Persist or confirm a completion audit event after successful egress when the
   response path supports it.

If step 5 fails for a share grant, share revoke, download, or export, the action
fails closed and no grant/content/package is created or returned.

## Denied And Unavailable Responses

Denied responses must not reveal:

- private meeting title;
- transcript or summary text;
- participant names;
- audio metadata that confirms private content;
- storage keys, signed URLs, object paths, or local paths;
- MediaScribe job identifiers.

Unavailable responses may explain safe lifecycle classes:

- artifact is still processing;
- artifact is missing;
- artifact failed;
- artifact was deleted by policy;
- workspace policy disables this egress class;
- audit is unavailable and egress failed closed.

## Audit Metadata

Allowed audit metadata:

- `artifact_class`;
- `policy_reason`;
- `viewer_access_state`;
- `request_class`;
- `outcome`;
- `byte_length` only when safe and non-identifying;
- `export_id`;
- `share_grant_id`.

Forbidden audit metadata:

- transcript text or summary content;
- audio bytes;
- participant names from private content;
- access tokens, bearer headers, API keys, passwords;
- signed URLs;
- storage object keys;
- local filesystem paths;
- raw dependency error bodies.

## Export Manifest

Export package manifests may include:

- package id;
- meeting id only for authorized package owners/downloaders;
- safe title;
- generated time;
- included artifact classes;
- excluded artifact classes with policy reasons;
- hashes of included files when available;
- deletion/egress truth copy.

Manifest must not include storage object keys, dependency URLs, credentials, raw
internal paths, or private data for artifacts that policy excluded.

## Deletion Truth Copy

Download/export surfaces must include copy equivalent to:

> Files already downloaded or exported are outside later 2brain Rec revocation.
> Deleting a meeting can remove what 2brain Rec controls, not copies already
> saved elsewhere.

Russian UI can use a shorter equivalent, but it must preserve the same control
boundary.
