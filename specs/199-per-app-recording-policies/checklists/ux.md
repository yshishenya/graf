# UX And Accessibility Requirements Checklist: Политики автозаписи по приложениям

**Purpose**: Validate that the quiet prompt and settings interaction are precise
and accessible requirements.
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] CHK017 Are prompt controls, timer, persistence semantics and post-timeout behavior specified? [Completeness, Spec §US1]
- [X] CHK018 Are per-target and bulk controls, mixed state and individual override specified? [Completeness, Spec §US3]
- [X] CHK019 Are technical hint behavior and removed primary-path details specified? [Completeness, Spec §US4]

## Requirement Clarity

- [X] CHK020 Are the exact radio-card labels `Всегда`, `Спрашивать`, `Никогда` defined? [Clarity, Spec §FR-011]
- [X] CHK021 Is `Разные` defined as display-only until a concrete bulk choice? [Clarity, Spec §FR-012]
- [X] CHK022 Is the absence of home status/count and post-timeout undo UI explicit? [Boundary, Spec §FR-015]

## Accessibility And Scenario Coverage

- [X] CHK023 Are keyboard focus, VoiceOver names and pointer hints required for all new controls? [Accessibility, Spec §US4]
- [X] CHK024 Are reduced-motion and countdown announcement expectations included in validation? [Accessibility, Spec §quickstart]
- [X] CHK025 Are mixed, empty-registry, save-error and ended-meeting states covered? [Edge Case, Spec §Edge Cases]
