# Capture Lifecycle Contract

- Detector prompt preflight may report capture readiness without prior assisted
  acknowledgement so a first-time verified target can show the prompt.
- `prompt_button` is explicit user confirmation and starts through the existing
  manual capture prerequisites.
- `prompt_timeout` and `saved_target_policy` must re-check current policy,
  acknowledgement, target activity, permissions, storage, indicator and Stop
  readiness immediately before starting.
- Every resolved start emits at most one capture session with its stable reason.
- Target end after the existing grace period routes to the existing stop and
  finalization path; duplicate end/stop requests are no-ops.
