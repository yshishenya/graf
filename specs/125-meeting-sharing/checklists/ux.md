# UX Requirements Quality Checklist: Обмен встречами

**Purpose**: Validate clarity, accessibility and clean-room requirements before implementation
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## User flow and states

- [x] Share opens only after an explicit owner action
- [x] First surface answers who receives access and what they see
- [x] Search and grant are separate actions with a bounded next step
- [x] Loading, empty, duplicate, blocked, rate-limited and generic failure states are defined
- [x] Current grants, Copy link, revoke, rotation and expiry are discoverable without a role matrix
- [x] External/public unavailable states preserve the typed value and explain the policy
- [x] Recipient onboarding CTA never blocks the permitted summary or creates an account silently

## Accessibility and parity

- [x] Dialog name, modal semantics, combobox/listbox semantics and live status are defined
- [x] Keyboard focus, Escape, overlay close and focus return are defined
- [x] Browser and embedded cabinet share one state/copy contract
- [x] 320 CSS px, 200% zoom, VoiceOver, increased contrast and reduced motion are in acceptance
- [x] Disabled actions cannot trigger requests through stale JavaScript

## Trust and visual quality

- [x] Summary-only default and exclusions are understandable in Russian
- [x] Sent/delivered wording does not overpromise mailbox delivery
- [x] Calendar/address-book source and freshness are visible without implying consent
- [x] Email and recipient surfaces exclude transcript/audio/summary content
- [x] Visual direction remains original GRAF clean-room UI and requires product-design review

## Notes

All requirement-quality checks pass. A synthetic static browser audit of the
desktop and 320 CSS px modal states was completed on 2026-07-23; the live
browser/embedded acceptance matrix remains a release follow-up and does not
authorize external sharing rollout.
