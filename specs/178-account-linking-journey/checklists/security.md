# Security Requirements Checklist: Подключение email без тупиков

**Purpose**: проверить полноту и однозначность требований безопасности до реализации
**Created**: 2026-08-20
**Feature**: [spec.md](../spec.md)

## Authentication and authorization

- [x] CHK001 Определены ли обе независимые proof-границы и запрет silent merge по совпадению email? [Completeness, Spec §FR-017–FR-018, Out of Scope]
- [x] CHK002 Однозначно ли закреплено, что текущий authenticated profile остаётся primary profile? [Clarity, Spec §FR-002]
- [x] CHK003 Определено ли повторное подтверждение непосредственно перед mutation при изменившемся proof/blocker/preview state? [Coverage, Spec §FR-017]
- [x] CHK004 Зафиксирована ли parity auth outcomes для browser и embedded routes без расширения route allowlist? [Consistency, Spec §FR-019, FR-023]

## Transaction and replay safety

- [x] CHK005 Описаны ли single-use, idempotency, expiry, cancellation, retry и concurrent request semantics? [Completeness, Spec §FR-018, Edge Cases]
- [x] CHK006 Требует ли спецификация all-or-nothing rollback без частичного переноса identities, ownership или memberships? [Clarity, Spec §FR-017–FR-018, SC-003]
- [x] CHK007 Определено ли поведение stale preview после изменения workspace, provider или blocker state? [Coverage, Spec §FR-017, Edge Cases]

## Data and privacy boundaries

- [x] CHK008 Перечислены ли запрещённые preview/audit данные: raw IDs, subjects, email, codes, tokens и meeting content? [Completeness, Spec §FR-011, FR-022]
- [x] CHK009 Согласованы ли stable workspace/meeting IDs с запретом silent workspace/content merge? [Consistency, Spec §FR-004, FR-007]
- [x] CHK010 Определено ли, что сохранённое пространство не получает вторые personal-only privileges и corporate semantics? [Clarity, Spec §FR-005, Assumptions]
- [x] CHK011 Требуют ли blocker requirements fail-closed поведения для billing, calendar, deletion и incompatible roles? [Coverage, Spec §FR-008, FR-015]
- [x] CHK012 Определён ли metadata-only support reference и честный fallback при ненастроенной поддержке? [Coverage, Spec §FR-015–FR-016]

## Session consequences

- [x] CHK013 Однозначно ли задан отзыв sessions и device trust обеих сторон после success, но не после cancel/failure? [Consistency, Spec §FR-014, SC-003]
- [x] CHK014 Определён ли безопасный post-merge re-login любым сохранённым verified provider? [Completeness, Spec §FR-003, FR-014]
- [x] CHK015 Привязан ли intent к точным session, source identity и callback proof records, а для provider-link-originated flow также к exact `provider_link_state_id` и равному source identity `target_provider_identity_id`; требует ли spec `proof_required` без account/data mutation для legacy intent без обязательных bindings и fail-closed recheck для missing/unusable/mismatched provider-link binding в Python и RLS? [Clarity, Spec §FR-025]
- [x] CHK016 Различены ли same-key replay, different-key conflict и expired confirm без ложного success? [Coverage, Spec §FR-026]
- [x] CHK017 Определена ли одинаковая browser nonce binding для login и settings provider-link callbacks? [Consistency, Spec §FR-027]
- [x] CHK018 Требует ли spec полного disposition inventory для каждого FK на user identity? [Completeness, Spec §FR-033, SC-011]
- [x] CHK019 Исключены ли для linked одновременно personal и corporate capability classes? [Consistency, Spec §FR-028, SC-010]
- [x] CHK020 Описаны ли lineage rules, предотвращающие повторный trial/referral и fair-use bypass? [Coverage, Spec §FR-030]
- [x] CHK021 Достаточно ли полно определён billing blocker beyond nominal free state? [Clarity, Spec §FR-029]
- [x] CHK022 Закреплён ли privacy-safe logical AND для каждого optional billing-notification channel? [Consistency, Spec §FR-034]
