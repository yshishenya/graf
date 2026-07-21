# Capture And Privacy Requirements Checklist: 119 Registry Expansion

**Date**: 2026-07-21
**Purpose**: Validate requirement completeness and safety before implementation.

## Recording Boundary

- [x] Requirements distinguish recognition from prompt/recording support.
- [x] Newly catalogued native identities are prompt-capable, while actual
  auto-record still requires explicit user selection and existing capture gates.
- [x] Post-enable live QA includes start, end, idle/prejoin, false-positive,
  visible indicator, and one-action Stop evidence.
- [x] Existing Zoom and Telemost prompt modes are explicitly preserved rather
  than inferred from the expanded count.
- [x] Unknown, malformed, duplicate, and browser-generic inputs
  have explicit fail-closed outcomes.
- [x] Manual Record/Pause/Resume/Stop behavior is explicitly out of the changed path.

## Privacy And Evidence

- [x] Allowed evidence fields are bounded to public app identity, product label,
  service family, evidence level/source, and verification date.
- [x] Raw logs, app inventory, URLs, room codes, participant/title data, audio,
  transcript, credentials, and private paths are prohibited.
- [x] Browser requirements require metadata plus calendar/join intent and forbid
  generic browser audio as meeting evidence.
- [x] Catalog evidence does not authorize new egress or permissions.
- [x] Package/source verification and live call verification are clearly separated.

## Registry Safety

- [x] Case-insensitive duplicate identity behavior is specified for server and client.
- [x] Cache failure preserves the previous valid registry and manual recording.
- [x] Migration ownership, workspace precedence, and downgrade restoration are specified.
- [x] Target IDs and preferences from the released baseline must be preserved.

## Outcome

All capture/privacy requirement-quality checks pass. Implementation remains
blocked until tasks, GitHub issue sync, and analyze are complete.
