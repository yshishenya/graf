# Clean-Room Reference Notes: 036 Owner Review Live Polish

Feature: `036-owner-review-live-polish`

## Reference Boundary

Feature 030 V8 remains the accepted clean-room implementation baseline for this
runtime UI slice. Krisp may inform information architecture lessons only:

- meeting workspace first;
- list/detail review flow;
- transcript, speaker, playback, and assistant/notes areas;
- contextual actions for search, filters, upload, share/export/delete, and
  templates;
- dense but readable review content.

## Forbidden Reference Use

- Do not commit private Krisp screenshots.
- Do not copy Krisp brand assets, icons, color expression, or non-generic copy.
- Do not make 2brain Rec visually indistinguishable from Krisp.
- Do not hide unavailable product behavior behind polished but false controls.

## 036 Runtime Focus

This slice targets runtime-critical surfaces only:

- installed desktop meeting workspace;
- desktop active/paused/resumed/stopped capture states;
- embedded desktop meeting list/detail;
- web meeting list/detail;
- notes/action truth states;
- governance/access/deletion states already supported;
- responsive fit and text containment.

## Baseline Finding

The current installed app is safe and functional, but it still reads as a
local/diagnostic operations surface before it reads as a meeting review product.
036 should move the main hierarchy toward V8 while preserving native capture
authority.

## Runtime Finding After Desktop Polish

The installed `/Applications/2brain Rec.app` runtime now starts from a
meeting-workspace-first shell: meetings are the main area, native capture
controls stay persistent in the right inspector, and low-level diagnostics are
collapsed. This is closer to the V8/Crisp-inspired information architecture
without copying Krisp brand assets, colors, or private reference content.

The current production desktop cabinet state is intentionally truthful rather
than complete: the packaged production server is configured, but the embedded
workspace has no owner session, so it shows `Нужен вход в кабинет` and keeps
local recording available. This preserves launch safety and avoids presenting a
fake meeting list.

Remaining clean-room/product gaps:

- embedded owner sign-in/session handoff is not complete;
- real owner list/detail/governance content still needs metadata-safe live
  proof;
- active/paused/resumed/stopped recording walkthrough still needs final
  screenshot evidence;
- transcript/player/chat surfaces remain future embedded web work, not copied
  from Krisp.
