# Contract: Desktop Update Client

## Configuration

The updater is enabled only when the installed main bundle contains:

- a valid `https` appcast URL;
- a non-empty public EdDSA key;
- signed-feed and verify-before-extraction flags;
- a strictly parseable installed bundle version.

Incomplete configuration returns a truthful unavailable state. It never opens an unsigned download URL or falls back to replacing the app directly.

## Check Behavior

| Trigger | User-facing behavior | Capture behavior |
|---|---|---|
| Scheduled, no update | No modal interruption; state becomes current. | No effect. |
| Scheduled, update, idle | Standard update offer may be shown. | No effect. |
| Scheduled, update, protected | No modal offer; badge appears and state is deferred. | Recording, stop, and finalization continue. |
| Manual/menu, no update | Standard current-version result. | No effect. |
| Manual/sidebar, update, idle | Standard update offer in focus. | No effect. |
| Manual/sidebar, update, protected | Offer may be shown, but install/relaunch is deferred and explained. | No quit, stop, pause, or replacement. |
| Any retryable network failure | Manual checks show a concise error; scheduled checks remain non-blocking. | No effect. |

## User Choices

- **Install**: continue immediately only when protected work is idle; otherwise retain one continuation and move to `deferredForCapture`.
- **Later/dismiss**: keep the trustworthy available state and sidebar marker.
- **Skip**: clear the marker for that version; a later manual check may still show it according to Sparkle behavior.

## Capture Gate

Protected work includes active/paused capture, start or stop transition, recording finalization/local persistence, and termination cleanup. The controller must apply this gate at the shared relaunch boundary, not only in menu or sidebar actions.

## Logging

Allowed fields: event name, installed version, offered version, trigger kind, phase, protected-work boolean, sanitized error domain/code, and result.

Forbidden fields: appcast body, archive body, release private key, signed private URL, credentials, account/workspace IDs, meeting titles, transcript text, audio paths, or raw audio.
