# Quickstart: Политики автозаписи по приложениям

## Focused Swift validation

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'MeetingDetectionPolicyTests|MeetingDetectionCountdownTests|CaptureControlV5Tests'
```

## Synthetic scenarios

1. Load a temporary settings store and a registry with two verified native targets.
2. Assert both new targets resolve to `ask` and no acknowledgement is created.
3. Exercise Start/Skip with checkbox off and on; assert the current outcome and
   persisted rule match the contract table.
4. Let the countdown expire with checkbox off and on; assert current start and no
   persisted rule in both cases.
5. Set one target to each of `always`, `ask` and `never`; assert detector policy
   output and final current-start gates.
6. Apply each bulk value, assert all eligible targets change, then edit one target
   and assert the others remain unchanged.
7. Decode a legacy settings payload and assert ambiguous targets become `ask` and
   the legacy global acknowledgement is not used as a target rule.

## UI/accessibility smoke

- Verify radio-card selection, mixed bulk state, keyboard focus and VoiceOver
  labels for both per-target and bulk controls.
- Verify technical switch hints appear on pointer hover and keyboard focus.
- Verify prompt countdown text updates, timeout starts only the current recording,
  and active capture still has the visible indicator and one-action Stop.

## Evidence boundary

Use synthetic target IDs and metadata-only assertions. Do not record a real
meeting or persist audio, transcript, cookies, tokens or credentials.

The full repository CI lane is not claimed unless explicitly run by the user.
