# A9 macOS release resume — requirements review

Purpose: independent requirements quality before public-release tooling changes.
Created: 2026-09-13. Feature: ../spec.md, FR-049–054 / SC-022 / US9.
Owner: independent reviewer; [x] means requirements approved, never implementation proof.

## Completeness and consistency

- [x] CHK001 Are compatible compilation reuse, mandatory fresh build, both architectures and preserved packaging trust clearly distinguished? [Spec FR-049]
- [x] CHK002 Does same-version identity cover every input/output, previous release, external asset identity and immutable bytes? [Spec FR-050/051]
- [x] CHK003 Are signer freshness, original public attestation TTL and public trust requirements explicit on resume/upload? [Spec FR-051/054]
- [x] CHK004 Are all-assets preflight, conflicts, interruption and concurrent draft publication bounded without overwrite? [Spec FR-052]
- [x] CHK005 Are durable submission intent, known/unknown ID recovery, original/stapled bytes and all Apple failure states complete? [Spec FR-053]
- [x] CHK006 Are locks, failed writes/fsync, measurable executable scenarios and real-release evidence boundaries testable? [Spec FR-054 / SC-022]

## Notes

Implementation reads this gate and does not change reviewer markers.

Independent requirements review, 2026-09-13: **PASS, 6/6**. Reviewed the working
A9 amendments on base `1b51bea23f07e468fda7186ca088c51dd9825897` in `spec.md`,
`plan.md`, `tasks.md` and `quickstart.md`, with the completed `research.md` and
`data-model.md` as supporting design. No concrete missing contract or unresolved
critical/high requirement finding. FR-049–054 and SC-022 all have task coverage
in T073–T077; these tasks remain implementation work, not completed evidence.

| Item | Requirement evidence and implementation boundary |
|------|---------------------------------------------------|
| CHK001 | FR-049, plan step 1, T073/T074: compatible per-architecture scratch excludes full source SHA, but every build invocation processes current source; toolchain/SDK/dependency changes invalidate compatibility and existing packaging checks remain. |
| CHK002 | FR-050/051/054, plan steps 2–4, T073/T075: content-bound inputs include previous release, tool/trust and external asset identity; tree modes/symlinks and complete output hashes are checked. Checksum and public attestation are staged with signed outputs before completion; an exact retry preserves their bytes. |
| CHK003 | FR-051/054 and Clarify A9, plan steps 3–4, quickstart: fresh Keychain verification does not replace the retained public proof. Its original 24-hour TTL, exact SHA, keyId and trustGeneration remain mandatory; expiry cannot authorize timestamp refresh or remote replacement. |
| CHK004 | FR-052, plan step 5, T073/T075: all four target assets are checked before the first upload, including duplicate/conflicting names and content/size; only missing files upload. Interrupted uploads require readback; draft/repository/release/tag/source identity is rechecked around transfers. Concurrent owner publication is detectable, not an atomic GitHub transaction guarantee. |
| CHK005 | FR-053/054, plan step 6, T073/T076: durable intent precedes submit, known IDs resume info/wait, and an unknown ID blocks resubmission. Recovery requires digest-bound Apple evidence, not history/time/name guesses. Submitted ZIP/PKG remain immutable; stapling uses separate copies and the final ZIP follows app stapling. Invalid/rejected/network results cannot become Accepted. |
| CHK006 | FR-054/SC-022, plan steps 2–3/6–7, T073–T077 and quickstart: ownership precedes mutable-state reads, stale locks are not blindly removed, failed atomic writes/file or directory fsync cannot acknowledge completion, and completed outputs are revalidated without rewriting. Synthetic failure scenarios and real source-bound release proof have separate acceptance boundaries. |

Existing guards were inspected read-only in `build-local-installer.sh`,
`prepare-app-update.sh`, `sign-graf-app-update-local.sh`,
`release-signing-common.sh` and `validate-app-updates.sh`, against constitution V
and the current release/notarization guidance. A9 preserves clean exact-source
provenance, predecessor continuity, safe extraction, pinned Sparkle tools, named
Keychain custody, Developer ID/team/designated requirement, notarization,
staple/Gatekeeper and both architecture startup checks. The explicit
`GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1` requirement is already recorded in research,
the quickstart public-flag case and current release policy; an unset public guard
is not a permitted implementation shortcut.

Lane: independent requirements review within the existing high-risk F211 slice.
Only this reviewer-owned checklist was edited. No builds, tests, GitHub calls,
application or release actions were performed. This PASS clears requirements
review only; implementation validation, issue ownership and release gates remain
as specified in Phase 20 and current policy.
