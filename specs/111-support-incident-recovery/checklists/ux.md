# Degraded support-flow UX requirements checklist

**Purpose**: Validate clear, accessible and truthful user-facing requirements for the support flow.

## State clarity

- [x] Requirements distinguish accepted-and-synchronized, accepted-pending and not-accepted outcomes.
- [x] Each outcome has an explicit next action and does not rely on an unexplained generic retry message.
- [x] The accepted-pending copy does not claim that a private Issue exists before it is synchronized.
- [x] Authentication-required copy tells the user to sign into the embedded cabinet rather than implying a network or server outage.
- [x] A rejected report offers a safe clipboard fallback without suggesting that private data should be copied.

## Accessibility and localization

- [x] User-visible support state and actions are required to have localized Russian text and accessibility labels.
- [x] Status text remains understandable without a color-only signal.
- [x] The retry/check action and clipboard action have a clear purpose and accessible label.
- [x] The new state fits the existing native custody surface without adding a permanent debugging panel.

## Trust and scope

- [x] Copy avoids promising recovery, deletion or Issue creation that the server has not proved.
- [x] The flow does not expose debug data, raw provider errors or secret-bearing values to the product UI.
- [x] The requirements keep the native capture controls and stop path independent of embedded-cabinet availability.

## Notes

All UX requirements are testable through the three response states, accessible labels and the safe-copy boundary in the quickstart.
