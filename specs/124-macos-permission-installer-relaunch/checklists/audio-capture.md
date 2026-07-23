# Capture and permission requirements checklist

- [x] Microphone `unknown`, `granted`, `denied`, and `restricted` states are
  independently represented.
- [x] Only the normal AVFoundation request is used before first microphone
  denial.
- [x] Denied/restricted microphone recovery opens the system settings surface
  and does not promise a repeat prompt or bypass.
- [x] Screen/System Audio permission remains separate from microphone
  permission.
- [x] Installed metadata contains privacy explanations for both capture paths.
- [x] Recording remains manual, locally visible, and unavailable until both
  permissions are actually granted.
