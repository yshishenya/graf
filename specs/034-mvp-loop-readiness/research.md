# Research: MVP Loop Readiness

Date: 2026-06-16

## Decision: Treat 034 As A Readiness Gate, Not A New Product Surface

**Decision**: Implement 034 as a repeatable readiness report and evidence
matrix, with bounded hardening only when required to make an existing claim
truthful.

**Rationale**: Accepted slices already own the user-facing capabilities:
capture, upload, processing, review, access, retention/deletion, and desktop
embedding. The launch risk is integration truth across those slices. A new
screen would hide the actual question: can the product loop be proven end to
end today?

**Alternatives considered**:

- Build another web dashboard page: rejected because it duplicates 016/017/018
  and does not itself prove desktop or production integration.
- Do only a manual checklist: rejected because evidence would be hard to rerun
  and easy to overclaim.
- Defer readiness until every known backlog item is implemented: rejected
  because MVP planning needs a ranked blocker register now.

## Decision: Use Explicit Claim Levels

**Decision**: Readiness claims must use bounded claim levels:
`infra_smoke_ready`, `desktop_loop_verified`, `web_review_verified`,
`policy_lifecycle_verified`, `internal_pilot_candidate`, `pilot_blocked`, and
`mvp_loop_ready`.

**Rationale**: Prior deployment work intentionally capped production claims at
`infra_smoke_ready`. 034 must not collapse infrastructure, pilot, user rollout,
and production readiness into one ambiguous word.

**Alternatives considered**:

- Single boolean ready/not ready: rejected because it would hide partial
  progress and specific launch blockers.
- Existing feature statuses only: rejected because feature-level acceptance
  does not prove cross-feature user journeys.

## Decision: Separate Evidence Strength From Stage Status

**Decision**: Each stage records both a functional status and an evidence
strength: `live`, `production_smoke`, `local_runtime`, `synthetic`, `docs_only`,
`missing`, or `blocked`.

**Rationale**: A stage can look ready in synthetic screenshots while still
missing live app evidence. Evidence strength must be visible so launch claims
do not become stronger than the proof.

**Alternatives considered**:

- Treat all passing tests as equivalent: rejected because server unit tests,
  synthetic HTML, desktop screenshots, and production smoke prove different
  things.

## Decision: Store Metadata-Only Evidence In Docs

**Decision**: 034 evidence lives under `docs/evidence/034-mvp-loop-readiness/`
and may include JSON, Markdown, and sanitized screenshots.

**Rationale**: The readiness record must be reviewable in PRs and must not
depend on an operator's local terminal history. Docs evidence also matches
prior feature slices and deployment evidence scans.

**Alternatives considered**:

- Store in production database: rejected because readiness artifacts are release
  evidence, not product data.
- Store only in GitHub comments/issues: rejected because evidence should remain
  versioned with the code and specs.

## Decision: Use Existing Runtime Scripts For Production Proof

**Decision**: Reuse `infra/scripts/ci-local.sh`, `infra/scripts/cd-remote.sh`,
`infra/scripts/run-production-smoke.sh`, and public health checks for
production evidence instead of creating a separate production mutation path.

**Rationale**: The deployment helpers already encode backup, restore rehearsal,
secret scans, migration verification, smoke upload/cleanup, and public health
truth. Creating a second path would increase risk and weaken operator trust.

**Alternatives considered**:

- Direct ad hoc SSH/Docker commands: rejected except for read-only inspection,
  because the CD scripts are the canonical gate.
- Browser-only health checks: rejected because they cannot prove backup,
  migration, smoke upload, cleanup, or secret hygiene.

## Decision: Reference Comparison Is Category-Level Only

**Decision**: The reference comparison records allowed IA/category lessons and
forbidden similarity checks. It must not commit private Krisp screenshots or
copy Krisp visuals, copy, icons, colors, assets, exact layout, account data, or
proprietary behavior.

**Rationale**: The product is in the same category as Krisp but must remain
clean-room. Existing audits already preserve allowed lessons; 034 needs to
verify implementation alignment without importing protected expression or
private content.

**Alternatives considered**:

- Pixel-level reference matching: rejected because it would move toward copying
  rather than clean-room category alignment.
- Ignore reference during readiness: rejected because the user explicitly asked
  to keep comparing with final mockups and Krisp desktop/web behavior.

## Decision: Treat Live Private Content As Unsafe By Default

**Decision**: Live private meetings may be inspected locally when necessary, but
committed evidence must be sanitized, synthetic, redacted, or metadata-only.

**Rationale**: The reference and product data contain private account names,
emails, meeting titles, transcripts, audio, local paths, and dependency IDs.
Evidence must prove product behavior without leaking that content.

**Alternatives considered**:

- Commit live screenshots with redaction boxes: rejected unless a specific
  screenshot is audited, because redaction can miss hidden strings in PNG
  payloads or accessibility text.
- Avoid all screenshots: rejected because UI readiness and reference alignment
  require visual proof.

## Decision: Update Product Status As Part Of 034

**Decision**: 034 owns updating `docs/current-product-status.md` so 018 is no
longer listed as next work and the next slice recommendation follows actual
readiness evidence.

**Rationale**: The current status document is stale after the 018 merge and
deploy. Leaving stale roadmap text would cause the next Spec Kit cycle to drift.

**Alternatives considered**:

- Update status in a separate housekeeping PR: rejected because readiness
  evidence and next-slice selection belong together.
