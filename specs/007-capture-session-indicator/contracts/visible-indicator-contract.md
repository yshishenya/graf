# Contract: Visible Capture Indicator

## Purpose

Ensure active recording is always locally visible and stoppable.

## Required Surface Behavior

During active recording:

- at least one persistent local indicator is visible;
- the indicator copy clearly says recording is active;
- the indicator does not rely on color alone;
- a Stop action is available in one interaction;
- stop is keyboard reachable and has an assistive label.

If the main window is closed or hidden:

- another local surface must remain visible; or
- recording must stop/fail closed.

If the floating widget is hidden or unavailable:

- tray/menu/status-item or equivalent persistent local indicator must remain
  visible; or
- recording must stop/fail closed.

## Forbidden Behavior

- Active recording with `hidden` visible indicator state.
- Disabled Stop action during active recording except during a fail-closed
  transition that is already stopping.
- Recording copy that implies upload, transcription, summary, or dashboard
  publication in this feature.
- User/admin setting that makes recording invisible.
