# Component Inventory

This file is the reusable component contract for the MVP redesign. Screen specs
own layout; this file owns repeatable behavior, state, density, and copy rules.

## Component Rules

- All controls use a 4px focus ring offset and preserve visible focus in light
  and dark themes.
- Buttons do not grow when status text changes. Use fixed height, flexible
  width, and wrapping helper text outside the button.
- Every status component includes icon/shape plus text. Color never carries the
  only meaning.
- Meeting data in examples must be realistic but synthetic. Never use private
  meeting titles, transcript text, emails, card details, or signed URLs.
- Desktop components must keep native capture truth above embedded web content.
  Web components may show richer review/admin workflows but cannot start or stop
  local capture from inside an embedded cabinet.
- Product surfaces that are variable, server-backed, or shared across macOS,
  Windows, and Linux should be web/backend-owned and embeddable. Native shells
  should own only platform-critical capture, permission, local artifact,
  tray/menu, diagnostics, and host/route-guard components.

## Core Components

| Component | Surfaces | States | Size contract | Required behavior |
|---|---|---|---|---|
| Capture title bar | desktop | signed out, ready, recording, degraded, offline | 48px high; 16px horizontal padding | Shows only a minimal connection/session/policy badge, visible capture indicator, and one compact account menu entry. Full account/workspace summary belongs to embedded server-owned UI. No diagnostics-first layout. |
| Recording status rail | desktop | idle, ready, active, stopping, saved, degraded, blocked | 64-88px high strip | Native only. First visual object under title bar. Must include active source, elapsed time during recording, save path truth after stop, and a one-action stop while active. |
| `Остановить` button | desktop/tray | active, stopping | 40px desktop; 32px tray | Always visible while recording. Visible label is `Остановить`; spinner/progress text goes outside the button as `Останавливаем...`. |
| `Начать запись` button | desktop | ready, checking permissions, blocked, offline | 40px high | Starts only native recording. Visible label is `Начать запись`; disabled states name the blocker and the recovery action. |
| Status badge | all | every status matrix state | 24px min height; 8px horizontal padding; 6px radius | Uses semantic icon/shape, human label, and tooltip/secondary text for long details. |
| Meeting row | desktop/web | local, queued, uploading, processing, transcript ready, notes ready, failed, deleted, access denied | Desktop 72-88px; web 64-80px | Dense list row. Shows title, time, source provenance, primary status, last update, and one next action. Never an oversized marketing card. |
| Meeting filters | web/browser; limited embedded | all, owned, upload, recorded, saved, failed, date, contains, source, tags | 32px chips | Filter state must be visible as chips. Clearing a filter restores previous list without route confusion. |
| Search command | web/browser; optional embedded | closed, searching, empty, results, keyboard selected | 560px modal max; 44px input | Searches meetings, transcript text, notes, and action items. It must show scope and recent results. Desktop native shell may open browser search instead of embedding global search. |
| Upload drop zone | web/embedded | idle, dragover, validating, uploading, unsupported, no usable audio, too large, offline | 220px min height web; 160px embedded | Audio-first. Accepts owned audio and common video/meeting containers for extraction. Must not imply full video playback or guaranteed speaker separation. |
| Upload queue row | desktop/web | queued, uploading, retrying, uploaded, failed, paused, offline | 56-72px | Shows a human meeting title first, file/source details second, local/cloud status, retry count, last attempt, and safe actions: `Подробнее`, retry, pause, or open in browser when server accepted. |
| Processing stepper | web/embedded | uploaded, extracting, transcribing, transcript ready, notes generating, notes ready, partial, failed | 4-6 compact steps | Never shows a blank transcript as generic failure. Current step, elapsed/last update, and retry/recovery copy must be visible. |
| Transcript pane | web/browser; limited embedded | loading, partial, ready, low confidence, failed, redacted | 2-column review layout; transcript min 52% width | Timestamped speaker turns, active playback linkage, confidence/provenance notice, search within transcript. No private example copy. |
| Speaker assignment panel | web/browser; embedded desktop | loading, ready, low confidence, saving, saved, merge conflict, failed | 360-520px panel or full embedded detail route | Server-owned speaker naming, merge, assignment, talk-time, and segment evidence. Speaker separation renders one horizontal lane per speaker with that speaker's segments and talk-time percentage. Desktop may host it inside the embedded cabinet, but native macOS must not implement diarization/editing logic. |
| Playback strip | web/browser; optional embedded preview | unavailable, loading, ready, playing, error | 48-64px high, sticky inside review view | Shows play/pause, progress, time, source provenance, and speaker/channel context when known. Desktop embedded view may hide playback if route is browser-only. |
| Notes outcome panel | web/browser | generating, ready, partial, failed, edited | 320-420px side panel or right column | Summary, decisions, action items, and provenance. Copy must separate AI output from human approval. |
| AI assistant drawer | web/browser | closed, open, scoped to meeting, scoped to all meetings, disabled, no credits | 360-420px right drawer | Scope chip is explicit. User must see whether query is against this meeting or all allowed meetings. No hidden training or egress implication. |
| Browser handoff row | desktop | browser-only, disabled, offline | 48-64px | Explains why the route opens in browser and keeps the native window usable. Used for admin, billing, broad search, exports, deletion/account security, and complex sharing. |
| Settings console | desktop/web | account, recording, detection, sources, appearance, language, notifications, privacy, storage, diagnostics, browser-only | Left rail 220-248px; detail width 640-780px; toggle rows 52-64px | List-detail settings workspace. Groups launch-critical settings by user intent, not implementation layer. Theme uses a compact segmented control. Recording policy uses short labels `Спрашивать`, `Всегда писать`, and `Вручную`; explanatory copy stays outside the chips. Browser-only rows hand off instead of embedding risky account/admin actions. |
| Share/access modal | web/browser | invite-only, workspace, link-enabled, disabled, denied | 520-640px modal | Opens safely for review. Permission changes require explicit confirmation; desktop embedded view hands off to browser. |
| Export/download menu | web/browser | available, generating, denied, failed | 220-280px popover | Separates copy link, export transcript, download recording, and integrations. Desktop embedded view may display menu but browser opens for file generation. |
| Deletion/access entry | web/browser | available, confirmation, pending, deleted, denied | 520-640px modal | Uses bounded deletion language and lists controlled systems. No universal-erasure promise. |
| Empty state | desktop/web | no meetings, filtered empty, offline, signed out | 160-240px block | One compact reason, one primary next action, one secondary recovery. No decorative illustration. |
| Tray status item | desktop tray | ready, active, stopping, saved, uploading, failed, offline | 280-340px popover | Mirrors capture truth with `Остановить` first while active. Does not expose web admin controls. |

## Desktop/Web Differences

| Pattern | Desktop native | Embedded cabinet subset | Full browser cabinet |
|---|---|---|---|
| Capture control | Owns start, stop, permissions, local save | Never starts/stops capture | Shows past records only |
| Account/session | Shows minimal connection/session/policy badge and re-auth handoff only | Shows session expiry and allowed account routes | Full account, billing, security, admin |
| Meetings list | Hosts embedded route and may show local queue hints | Owner library and processing states | Full filters, search, sharing, exports |
| Review | Can open ready meeting in embedded mode | Transcript/notes plus server-owned speaker assignment when safe | Full transcript, playback, AI, tags, share, export, delete |
| Risky actions | Native permissions only | Browser handoff | Browser owns confirmation-heavy actions |

## Popover And Modal Rules

- Menus open from icon buttons with clear tooltips.
- Popovers close on Escape, outside click, and route change.
- Confirmation modals are required for deletion, public link access, account
  security, billing/trial changes, invite send, and recording start when a
  permission/policy warning exists.
- Disabled items explain the blocker inline instead of disappearing.
