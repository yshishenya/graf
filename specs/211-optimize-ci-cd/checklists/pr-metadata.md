# PR metadata requirements checklist — A2

**Purpose**: Independent requirements-quality review before A2 tasks/code.
**Created**: 2026-09-09
**Feature**: [spec.md](../spec.md), US6, FR-019–FR-024, SC-012–SC-013.
**Review ownership**: Independent reviewer owns checkbox state. `[x]` means requirements quality, not implementation/merge/release acceptance. Implementation reads these marks and does not change them.

## Completeness and clarity

- [x] CHK001 Is the additive PR-only scope distinguished from required-check activation, merge-group support and elimination of edited-code reruns? [Completeness, FR-019/023/024]
- [x] CHK002 Are event/current PR number, open state, head/base/ref and checkout identity defined with failure on mismatch? [Clarity, FR-020, US6.3]
- [x] CHK003 Are newer title/body handling, no event-text fallback on API failure and the non-atomic snapshot limitation unambiguous? [Clarity, FR-020/022, US6.2/5]
- [x] CHK004 Are scoped, multiple-feature, deleted/renamed paths and exact-base ownership defined without relying on branch number or moving defaults? [Coverage, FR-021, US6.4]

## Safety and consistency

- [x] CHK005 Are malformed JSON/types, unavailable history/API and untrusted text failure requirements complete and compatible with the existing validator? [Coverage, FR-022, US6.3/5]
- [x] CHK006 Are fork/read-only/no-secret boundaries and separate concurrency defined without claiming GitHub approval bypass? [Security, FR-022/023, US6.6/7]
- [x] CHK007 Are the unchanged authoritative workflow, receipts, release/closeout trust and lack of live activation permission consistent across spec/plan/contract? [Consistency, FR-023/024]
- [x] CHK008 Are failed/skipped/cancelled/stale results and the prerequisites for later PR/merge-group/base-retarget activation explicitly distinguished from code PASS? [Completeness, FR-024, plan cutover gate]

## Acceptance quality

- [x] CHK009 Are the no-product-test path, five-minute execution cap and executable acceptance scenarios measurable without inventing overall time/token savings? [Measurability, FR-019, SC-012/013]
- [x] CHK010 Are local implementation completion, live acceptance, publication, issue closure and release clearly separate, with historical A1 approvals excluded? [Consistency, clarifications A2, SC-013]

## Notes

Generated unchecked; independently reviewed below. Old checklist marks do not approve A2. No A2 implementation was reviewed.

## Review record — 2026-09-09

**Reviewer**: independent Codex agent `/root/graf_requirements_review`, explicitly authorized by the user. Ownership is limited to this checklist; the reviewer did not author the A2 spec, plan, tasks or implementation.
**Result**: PASS for A2 requirements quality; CRITICAL 0, HIGH 0. No blocking user decision remains within this additive, non-required scope.

- CHK001/007/008: [spec.md](../spec.md), A2 clarifications, FR-019/023/024 and US6.8; [plan.md](../plan.md), A2 scope, design 4 and later-cutover gate; [contracts/ci-cd-cli.md](../contracts/ci-cd-cli.md), A2 entrypoint. The combined required workflow and all evidence consumers remain authoritative. Merge-group support, freshness/retarget acceptance and separately approved live protection changes are prerequisites for any later cutover, not silently completed by this package.
- CHK002/003/005: [spec.md](../spec.md), FR-020/022 and US6.2/3/5; [data-model.md](../data-model.md), PRMetadataSnapshot; [plan.md](../plan.md), design 1–3. Current open-PR identity must match the event and checkout. Current title/body replace stale event text only when identity matches. API/type/history errors fail without an event-text fallback. A one-time fetched snapshot is expressly not atomic merge authorization.
- CHK004: [spec.md](../spec.md), FR-021/US6.4; [plan.md](../plan.md), design 1; [research.md](../research.md), real-diff decision. Exact-base NUL-delimited paths and disabled rename collapsing cover deleted and both renamed ownership paths; scoped and multiple-feature rules reuse the existing validator. Branch 6789 does not become Feature ID 6789.
- CHK006: [spec.md](../spec.md), FR-022/023 and US6.6/7; [plan.md](../plan.md), design 3; [research.md](../research.md), isolation decision. PR-only execution, explicit read permissions, no application secrets, no privileged pull_request_target, no raw-text shell interpolation or API-response logging, and independent concurrency are specified. Fork approval remains a GitHub boundary. This agrees with [GitHub secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use) and [fork-token permission rules](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
- CHK009/010: [spec.md](../spec.md), FR-019, SC-012/013 and A2 authority; [quickstart.md](../quickstart.md), planned A2 focused acceptance. Five minutes is the job execution cap, not a queue-inclusive promise. Local synthetic/Git/shell checks, subsequent live acceptance, publication, tracker closeout and release are distinct; no eliminated reruns or measured total savings are claimed.

The review traced the existing `scripts/validate-pr-metadata.py` body-file CLI and `validate()` callers in the current `governance-fast` workflow. A2 must preserve their behavior and keep existing tests passing; unchanged YAML alone does not prove compatibility when its shared CLI changes. The plan and quickstart explicitly require those regression checks.

These marks approve requirements only. Tasks, clean analyze, issue synchronization, implementation review and focused tests remain separate gates. No code, old checklist, workflow, remote setting or release artifact was changed by this review.
