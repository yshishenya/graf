# UX/accessibility checklist: Feature 168

- [x] Connect, sync and disconnect buttons show busy/disabled state during mutation.
- [x] Success/error is adjacent to the initiating action and survives reload.
- [x] Provider modal has labeled controls, error target, focus return and Escape/cancel behavior.
- [x] Empty, zero-selection, stale, unavailable and policy-limited states are explicit.
- [x] Destructive disconnect confirmation explains future sync, credentials and retained meeting context.
- [x] Browser and embedded IA/copy/state are parity-tested.
- [x] Keyboard-only and screen-reader flow has live `role=status` regions.
- [x] Narrow viewport and dark/light theme preserve action visibility.
- [x] Russian copy never implies hidden recording or provider writes.
- [x] Native manual Record/Stop remains reachable in every state.
- [x] macOS menu-bar tray has labeled loading, empty, sign-in, unavailable and stale states.
- [x] Tray uses safe event projection, bounded list and explicit user action for links.
- [x] Real installed-app visual receipt is retained without private event content.

**Audit result:** source, contract, authenticated browser/embedded DOM/AX probe
synthetic runtime evidence and the local tray popover pass. A physical
VoiceOver session is not recorded; private event content was not retained in
evidence; external provider runtime remains a separate gate.
