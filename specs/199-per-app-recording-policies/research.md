# Research: Политики автозаписи по приложениям

## Existing flow

- `MeetingDetectionSettings` currently stores `autoRecordTargetIds` plus one
  workspace/device acknowledgement.
- `MeetingDetectionPolicy` maps selected targets to automatic recording only when
  the acknowledgement is valid; all other eligible targets become a prompt.
- `MeetingDetectionPromptView` owns the 8-second countdown, the prompt checkbox,
  the Start/Skip actions and timeout callback.
- `MeetingDetectionSettingsView` renders binary checkboxes and two bulk buttons;
  it also renders bundle IDs and long policy descriptions inline.
- `MeetingDetectionPolicyTests` and `MeetingDetectionCountdownTests` already cover
  the detector policy and countdown seams and are the smallest regression lane.

## Decisions

1. Use a target-scoped enum instead of a second boolean or another global switch.
   This gives the policy a total mapping for `always`, `ask` and `never` and makes
   mixed bulk state representable.
2. Keep the existing workspace policy/acknowledgement as a separate gate. A target
   rule is user intent for one application, not a workspace authorization.
3. Preserve the timer as a current-meeting fallback. It may start capture after
   eight seconds, but it cannot write a target rule; only a button plus checkbox
   can persist `always` or `never`.
4. Migrate ambiguous legacy target selections to `ask`. The existing global
   acknowledgement does not prove target-specific intent and must not authorize
   every target.
5. Reuse the product's radio-card/segmented selection pattern for per-target and
   bulk controls. Do not add a dependency or a parallel design system.

## Rejected alternatives

- Keeping a binary selected-target set and inferring `never` from absence: cannot
  distinguish an unset new app from an explicit user refusal.
- Persisting a timeout outcome: violates the user's requirement that only a
  conscious button decision can change future behavior.
- Reusing one acknowledgement for all targets: creates a cross-application
  authorization boundary and was the root issue found in the previous audit.
- Adding a home-screen status/count or a post-timeout undo banner: rejected by
  product direction and unnecessary when the existing active-recording indicator
  and Stop action remain visible.
