# Sharing And Security Requirements Checklist: Complete Recording Workflows

**Purpose**: Validate template revision, sharing, invitation, link, tenant, egress, and deletion requirement quality
**Created**: 2026-07-21
**Feature**: [spec.md](../spec.md)

## Template And Summary Requirements

- [x] CHK001 Are built-in versus personal template ownership and mutation rules explicit? [Completeness, Spec §FR-026–FR-031]
- [x] CHK002 Are allowed template sections, language, detail, validation, and unsafe-content boundaries defined? [Clarity, Spec §FR-031]
- [x] CHK003 Are transcript/result/template version provenance requirements documented for every generated summary? [Traceability, Spec §FR-032]
- [x] CHK004 Are candidate, accepted, superseded, failed, and replacement decisions unambiguous? [Lifecycle, Spec §FR-033–FR-034]
- [x] CHK005 Does the spec prevent sharing a personal reusable template when only rendered notes are authorized? [Privacy, Spec §FR-035]

## Sharing Model Completeness

- [x] CHK006 Are audience, content scope, view, download, and export decisions independently specified? [Completeness, Spec §FR-036–FR-040]
- [x] CHK007 Is the default invite-only + summary-only + view/no-download/no-export posture explicit? [Clarity, Spec §FR-037, FR-040]
- [x] CHK008 Are user, workspace, team, and anyone-with-link audiences defined with policy gating? [Coverage, Spec §FR-038, FR-043–FR-044]
- [x] CHK009 Does Copy link preserve current policy rather than imply public access? [Privacy, Spec §FR-042]
- [x] CHK010 Are owner/current grants, scopes, capabilities, and revocation visibility requirements present? [Completeness, Spec §FR-041]

## Authorization And Identity

- [x] CHK011 Are summary-only direct-route denials specified for transcript, playback, participant, export, and private-template paths? [Authorization, Spec §FR-046]
- [x] CHK012 Are identity lookup and invitation errors required to avoid account/meeting enumeration? [Security, Spec §US6, FR-047]
- [x] CHK013 Are revocation, expiry, membership loss, and deletion required to take effect on the next controlled request? [Lifecycle, Spec §FR-045, SC-008]
- [x] CHK014 Are public-link expiry, rotation, revocation, and abuse-resistant access requirements complete? [Security, Spec §FR-044]
- [x] CHK015 Are public/external capabilities blocked until policy, abuse, identity, delivery, legal, RLS, and deletion gates pass? [Dependency, Spec §Assumptions]

## Egress And Deletion

- [x] CHK016 Does the spec reuse canonical export/download/deletion authorities instead of defining browser-side alternatives? [Consistency, Spec §FR-049–FR-053]
- [x] CHK017 Are review playback, audio download, and transcript/summary export permissions clearly independent? [Clarity, Spec §FR-050–FR-051]
- [x] CHK018 Is deletion required to win generation/share/invite/export races after it starts? [Lifecycle, Spec §FR-052–FR-054]
- [x] CHK019 Is deletion copy explicit that the GRAF Generation Call ledger, Langfuse observations, and Temporal History remain retained observability copies rather than failed purge artifacts? [Truthfulness, Spec §US7, FR-053]

## Tenant, Audit, And Evidence

- [x] CHK020 Are every new meeting/template/share/revision/export/deletion record and route required to be user/workspace scoped? [Tenant Isolation, Spec §FR-057]
- [x] CHK021 Are audit requirements metadata-only and complete for sensitive policy/access transitions? [Privacy, Spec §FR-048, FR-056]
- [x] CHK022 Are raw tokens, emails, signed URLs, provider payloads, content, and secrets excluded from diagnostics/evidence? [Security, Spec §FR-056, SC-011]
- [x] CHK023 Are broadened or irreversible actions required to explain privacy consequences before mutation? [Consent, Spec §FR-058]

## Notes

- 23/23 requirement-quality checks pass for the current spec.
- Collaborative comments/editing remain explicitly out of scope; download and
  export are separate capabilities rather than implied by view access.

## Durable AI And Cloud Observability Addendum

- [x] CHK024 Are prompt-injection, strict structured-output, and exact prompt/recipe/schema provenance requirements explicit? [Security, Spec §FR-032, FR-067]
- [x] CHK025 Are duplicate dispatch, activity replay, transient retry, terminal failure, and accepted-summary preservation requirements complete? [Lifecycle, Spec §FR-033–FR-034, FR-068–FR-069]
- [x] CHK026 Are full-content Langfuse AI observations and retained Generation Call storage plus complete-transcript Temporal History precisely separated from ordinary metadata-only audit/evidence? [Consistency, Spec §FR-056, FR-071, FR-088]
- [x] CHK027 Is sole-publisher Langfuse delivery durably pending until confirmation and excluded from model-call retry, candidate readiness, meeting deletion, and business-state authority? [Dependency, Spec §FR-070–FR-073, FR-077]
- [x] CHK028 Are worker-only secret custody, Cloud destination, and post-chat rotation expectations documented? [Security, Spec §Dependencies, Research §Decision 10]
- [x] CHK029 Are deletion checks before new inference/publication/acceptance plus pre-egress cancellation specified while completed-call observability delivery continues and all retained copies survive? [Lifecycle, Spec §FR-052–FR-054, FR-073]
- [x] CHK030 Are configured private Langfuse destination/environment, no-public-trace rule, operator-managed retention/access, and deliberate no-GRAF-delete behavior explicit? [Observability, Constitution §III]
- [x] CHK031 Are durability, exact full model content in Langfuse/Generation Call, exact transcript in Temporal History, pre/post-serialization payload ceilings, durable fail-open delivery, no masking/truncation, and retained-observability deletion copy objectively measurable? [Measurability, Spec §SC-014–SC-017]

Addendum result: 8/8 requirement-quality checks re-pass on 2026-07-22; total
31/31 against constitution v4.0.0.
