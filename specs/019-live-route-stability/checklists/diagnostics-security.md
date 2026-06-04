# Diagnostics And Security Checklist: Live Route Stability

**Purpose**: Validate metadata-only diagnostics, privacy, and security requirement quality before task generation.
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests requirements and planning artifacts, not implementation behavior.

## Metadata-Only Evidence

- [ ] CHK001 Are diagnostics requirements complete for route lifecycle, client activity, idle/release decisions, autorepair, external disruptions, recording timeline, and user-action audit families? [Completeness, Spec §FR-035, Contract §Route Evidence Events]
- [ ] CHK002 Are event payload requirements clear enough to reconstruct route state before/after, trigger category, physical route, virtual client state, frame continuity, autorepair outcome, and user action requirement? [Clarity, Spec §Logging And Evidence Contract, Contract §Route Evidence Events]
- [ ] CHK003 Are correlation requirements complete for connecting route sessions, autorepair attempts, validation runs, and recording manifests? [Traceability, Spec §FR-036, Data Model §RouteEvidenceEvent]
- [ ] CHK004 Are route diagnostics requirements measurable enough to prove every accepted run includes all required event families? [Measurability, Spec §SC-017, Contract §Validation Run Evidence]

## Privacy And Redaction

- [ ] CHK005 Are excluded data classes explicitly defined across spec, plan, contracts, and quickstart? [Consistency, Spec §FR-019, Plan §Constitution Check, Quickstart §Redaction Validation]
- [ ] CHK006 Are requirements precise enough to exclude raw audio, transcript text, meeting content, participant speech, credentials, tokens, signed URLs, passwords, API keys, and live credential paths? [Security, Spec §FR-019, Contract §Route Evidence Events]
- [ ] CHK007 Are safe device id/display-name requirements defined clearly enough to support reproduction without exposing secrets or full user paths? [Privacy, Spec §Logging And Evidence Contract, Data Model §MacOSDefaultRouteSnapshot]
- [ ] CHK008 Are future export requirements bounded by diagnostic redaction before any evidence leaves the machine? [Completeness, Spec §Logging And Evidence Contract]

## External Egress And Dependency Boundaries

- [ ] CHK009 Are requirements explicit that live route stability validation starts no upload, transcription, MediaScribe processing, Langfuse tracing, analytics, or external egress? [Security, Spec §FR-014, Spec §SC-007d, Spec §SC-010]
- [ ] CHK010 Are offline requirements complete enough to keep live passthrough independent from backend, upload, MediaScribe, Langfuse, and network state? [Completeness, Spec §FR-013, Spec §SC-011]
- [ ] CHK011 Are local-first storage requirements consistent with deletion/lifecycle accounting for metadata evidence? [Consistency, Plan §Storage, Constitution §IV]

## User Action Audit

- [ ] CHK012 Are user-action audit requirements complete for `Run Check`, meeting-target device reselect, app relaunch, and meeting settings reopen? [Completeness, Spec §Logging And Evidence Contract, Contract §Route Evidence Events]
- [ ] CHK013 Are accepted-run requirements clear that any required user action prevents clean acceptance? [Clarity, Spec §SC-007b, Contract §Validation Run Evidence]
- [ ] CHK014 Are successful-autorepair diagnostics requirements sufficient for QA to reproduce problems without showing disruptive user-facing modals? [Coverage, Spec §FR-044, Spec §FR-045]
