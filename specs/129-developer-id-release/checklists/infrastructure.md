# Infrastructure Checklist: Developer ID как единственный публичный macOS-релиз

**Purpose**: Проверить качество требований к release scripts, public host,
appcast и операторскому walkthrough.
**Created**: 2026-07-26
**Feature**: [spec.md](../spec.md)

## Публикация

- [x] CHK014 Определены ли exact tag/commit, CalVer и immutable versioned assets как единый release identity? [Completeness, Spec §Key Entities]
- [x] CHK015 Указано ли, что public download, GitHub Release и live host не получают artifact до прохождения trust gates? [Clarity, Spec §FR-001, FR-002]
- [x] CHK016 Описан ли конфликт с уже существующим versioned asset и запрет тихой перезаписи? [Edge Case, Spec §Edge Cases]
- [x] CHK017 Есть ли отдельная проверка package identity/staple/Gatekeeper, а не только app bundle? [Completeness, Spec §FR-002]

## Обычный update и bootstrap

- [x] CHK018 Определены ли совместимые bundle ID, team identity, designated requirement, feed URL и Sparkle trust generation для ordinary update? [Completeness, Spec §FR-005]
- [x] CHK019 Определены ли входы и ожидаемый результат для manual `.pkg` transition v2026.07.26.6? [Acceptance Criteria, Spec §SC-003]
- [x] CHK020 Явно ли запрещено использовать Sparkle trust-generation bootstrap как замену Developer ID migration bootstrap? [Terminology, Spec §Assumptions]
- [x] CHK021 Описана ли команда оператора от build до notary/staple/validation/publication без обращения к legacy instructions? [Coverage, Spec §SC-005]

## Документация и эксплуатация

- [x] CHK022 Охватывает ли единая терминология AGENTS, README, runbook, checklist и Spec Kit artifacts? [Consistency, Spec §FR-006]
- [x] CHK023 Явно ли каждая оставшаяся legacy-ссылка маркируется historical receipt или isolated test fixture? [Clarity, Spec §FR-007]
- [x] CHK024 Определены ли failure paths для отсутствующей identity/profile, rejected package, failed staple/Gatekeeper и недоступного Apple response? [Coverage, Spec §Edge Cases]
- [x] CHK025 Есть ли проверяемый критерий, что активный аудит не оставляет self-signed public instruction? [Measurability, Spec §SC-001]
