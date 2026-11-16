# Round447 — bounded source review crash cuts, green2

Independent read-only source review, 2026-10-16. High-risk-product validation
within existing T116/#7444; not runtime acceptance or task closure.

## Binding

- Authoritative repository: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
- Frozen green2 manifest SHA-256:
  `3545b37f48c40bf1ed23ef186a39e28fb2c5ed5c1d946bb8ce9be15cd884e0cf`.
- Current source matched all 216 manifest inputs; both retained source copies
  matched current byte-for-byte. Compared manifests with accepted446 green4:
  exactly CMakeLists.txt and V5LocalRecordingWriterTests.cpp differ.
- Production remains446. Historical green18 result is not green2 evidence.
- Used code-reviewer for correctness and ponytail-review for minimality.
  No tests, builds, VM commands, Git/index writes or GitHub actions performed.

## Verdict

No CRITICAL/HIGH source finding in the bounded test delta. Two P2 test-oracle
gaps remain before accepting the complete stated physical-cut coverage and
canonical-readonly preservation. Normative GO remains valid; runtime unqualified.

### P2 — assert required event coverage, not merely observed event replay

`V5LocalRecordingWriterTests.cpp:208–215`: required media/playback operations
0/1/4/5/6 are not asserted in the successful trace. The only shape assertion
counts before-renames for manifest/recovery/package-state; it also does not
check matching after-renames. Thus a missing DATA/HEAD/flush selector can remove
those cuts from both the trace and the loop while all remaining cuts pass.
Hard-coded HEAD offsets/length make a fail-closed coverage assertion especially
useful. Require the mandatory event kinds for each output and paired successful
before/after metadata publications; record the actual count separately.
No additional framework or production switch is needed.

### P2 — canonical readonly oracle omits canonical metadata/identities

`V5LocalRecordingWriterTests.cpp:219–221,231,259` preserve the canonical content
file and service custody map, but not the canonical role's complete file map.
`recoveryEvent:53–55` rejects writes/flushes to canonical packed content, while
canonical index renames (operations2/3) can still be recorded without refusal.
A forbidden canonical checkpoint/metadata rewrite could therefore preserve
content bytes and pass these assertions. Preserve/compare the entire canonical
role map (including id/index files) before/after crash and fresh retry, or make
every canonical mutation event fail. Preserve original package/role ID files
explicitly rather than inferring identity preservation from content SHA alone.
Package-state/output artifacts are legitimately mutable and must not be put
under an indiscriminate whole-package-before/after equality assertion.

## Closed concern and positive checks

- Green2 passes expected role/operation through the child CLI and asserts both
  at the reached ordinal before TerminateProcess(88). This closes the earlier
  ordinal-only target-binding concern. Missing cut returns89, not88.
- WriteFile/FlushFileBuffers/NtSetInformationFile wrappers call real native
  operations. Production Files.cpp is compiled in this test TU; CMake excludes
  its separate object only for this Windows target, preserving non-Windows
  linkage and other targets. No alternate storage implementation/dependency.
- Actual child process handle is waited and closed; timeout path is a failure,
  not a qualified cut. Birth owners leave scope before child/fresh reads;
  handles are not inherited. Self-termination does not run destructors.
- Started-output retry must refuse with whole post-crash map unchanged.
  A fresh sealedDegraded read requires genuine inspection and AAC decode;
  no normal result is accepted. Service queue/bootstrap map stays unchanged.
- Resource checks preserve exact charged-memory baseline plus reacquisition
  of all four native jobs and32 pins in the parent. These are not measurements
  of destroyed-child destructors or physical power-loss durability.
- Fixtures are generated; logged fields are operation/role/ordinal and status,
  not audio, tokens or meeting content. IO-return/cancel and late-inspection
  cuts are not executed by this process-crash matrix and remain distinct.

## Ponytail

Lean already. Ship. This refers only to complexity: no safe deletion or new
abstraction recommended; the two correctness oracles above need small local
assertions/maps, not a framework. It is not runtime approval.

Only this report was written; no checklist markers, source, tasks or norms changed.

## Green3 source recheck

Manifest `8db4ac06694be4a4ed9b78bc374e3265abaf2ac6f172001e062c8ac82c69770b`:
current matched216/216; both frozen source copies matched byte-for-byte.
Green2→green3 adds only the shape matrix and non-vacuous sealedCold check in
the test TU; no CMake/production change in this increment.

The media/playback part of the shape finding is addressed: both roles require
birth write/flush, first DATA and positive HEAD count equal to HEAD flush count.
The nonzero sealedCold assertion is sound: every counted occurrence must pass
the actual full inspection/decode assertion before the test can complete.

Remaining previously reported gaps: metadata rename before/after pairing is
not yet asserted by shape, and canonical role metadata/original IDs are still
outside the before/after preservation oracle. CRITICAL/HIGH0; no new issue in
the added guards. Runtime green3 and its regressions remain unqualified here.

## Final green4 source verdict — both P2 closed

Frozen manifest `0bac37108e974c4e06e3210f09e4910276f1b05df1165867881e2d51d24ba2fe`:
fresh current216/216 match; both retained files match byte-for-byte. Versus446
only the test TU and CMake differ. Test TU SHA-256:
`cf9f5ef46c67b8230402095891740015eda4715212586305433e6a78818c9c54`.

- Shape now requires matching before/after counts for metadata roles3/4/5,
  in addition to the existing mandatory media/playback and sealedCold guards.
- coldOriginalHashes retains every original id.bin under package custody plus
  every canonical role file in the existing flat layout, including index and
  content files. It compares the resulting map immediately after actual child
  termination and again after fresh inspection/retry. New output/index files
  outside canonical remain allowed; original identity replacement/deletion or
  canonical metadata mutation no longer passes the oracle.
- Both previously reported P2 findings are closed in this source. No new
  blocker found in the bounded increment. Bounded source GO for this exact
  final test/CMake delta; no framework or production change required.

Green4 primary runtime and six regressions are still pending independent
qualification. Historical green/green2/green3 results are not transferred to
green4. Source-origin/HEAD patch reconstruction and cleanup are not qualified
by this source-only addendum. T116 and unexecuted IO/cancel/late inspection/
power-loss gates remain open. Only this report was changed by the reviewer.

## Independent reconstruction qualification

Read source-origin.json and independently applied patches, without using any
retained source copy as the reconstruction base. Used a mktemp directory with
dedicated GIT_INDEX_FILE and GIT_OBJECT_DIRECTORY; original object storage was
read-only via GIT_ALTERNATE_OBJECT_DIRECTORIES. No checkout or normal index
operation was used. git apply --cached --check and actual --cached apply
succeeded; reconstructed blob bytes were read with cat-file and SHA-256 checked
against every manifest input. All input entries were regular stage0 files.

Base HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Final HEAD patch: 3,197,284 bytes, SHA-256
`ef3f52539824ab73ca0a0ec483aeb57c28b287be4a848a674e02bc586b5259f4`.

| Reconstruction chain | Exact manifest input matches | Inputs absent from HEAD |
| --- | --- | --- |
| HEAD → green4 | 216/216 | 33 |
| HEAD → green4 → green | 216/216 | 33 |
| HEAD → green4 → green2 | 216/216 | 33 |
| HEAD → green4 → green3 | 216/216 | 33 |

All four manifest digests, final patch digest/length and three historical patch
digests match source-origin.json. Historical deltas apply forward from final
green4 to each historical stage, not in the opposite direction. The source
bytes of all864 manifest entries are reconstructible from HEAD plus retained
patches; no dependency on the moving dirty worktree or temporary source copies.

Normal index SHA-256 before and after was exactly
`662a640f866392dde2940678f5d98c82c85c145c3be3aebedf2825a524e36229`.
All30 newly written Git objects and temporary indexes stayed in the isolated
temporary directory, removed after verification. No evidence source copy was
deleted, no original Git object/index was written, no VM/runtime action taken.

Reconstructibility PASS is only one cleanup precondition. It does not approve
deletion of any target set or substitute for final terminal runtime/regression
receipts, exact cleanup inventory and preservation of HEAD/patches/manifests/
source-origin/logs. Those checks remain separate and owned by Main.

## Final green4 bounded runtime qualification and cleanup gate

Freshly read final primary/result.json, test.stderr.log, actual TU build.log,
regressions.json, JUnit, complete LastTest.log, ctest.log and regression-build
log. Read the wrapper and exact delegated regression script; its SHA matches
the wrapper's required a033b916979d7009c87b4e2f15e0b547baad2a17cad24eabda650d6b9f0e7758.
Text logs were decoded with BOM-aware UTF-8/UTF-16 handling, not raw tail bytes.

Primary: terminaltrue/build0/test_exit0,105741ms,postflight216,owned_processes0.
Build log contains actual V5LocalRecordingWriterTests.cpp compilation. Primary
and CTest writer hashes agree:
`68c757ee626460a5865091c8857425036575cdd7eff164e2469a3e3249d92a51`.
Saved regression native hash:
`09f455ef47f50186a0af5201181817c9d0c19491a8cc39a10c2d61d99107d374`.
Native source is unchanged; regression build may correctly reuse its binary.
Scripts check guest216 pre/post and both PE hashes; this reviewer did not read
live guest binaries or run fresh CIM. Process0 is saved terminal evidence only.

Primary and CTest writer each contain exactly24 trace entries and24 cut
entries, ordinals1–24 with matching role/operation,child_exit88 and waited1.
Each run has2 unused-output observations and22 started-output observations;
sealed_cold_decode=1 is nonzero and source-bound to full inspect/AAC assertion.
This is24 distinct boundaries executed twice, not48 distinct crash cases.
Baseline trace includes media/playback birth,DATА,HEAD/flush and all observed
metadata before/after renames. Prior B3 positives/15 refusals and A capturing/
finalizing3-frame positives/9 refusals/3 sealed-phase refusals remain present.

Regressions: terminaltrue/build0/ctest0/executed_tests6/postflight216/process0.
JUnit exact6 names, statusrun, failures0/skipped0/disabled0; LastTest contains
six Test Passed markers. CTest real total209.33s.

| Actual test | JUnit seconds |
| --- | ---: |
| V5LocalRecordingWriterTests | 103.406 |
| NativeProtectedStartOwnerRecovery | 31.9433 |
| NativeProtectedStartOwnerDegradedRestart | 1.86333 |
| NativeProtectedRecoveryLivePlayback | 11.0663 |
| NativeProtectedPlaybackConsumer | 14.6396 |
| NativeProtectedPackageRevalidation | 46.3944 |

LastTest independently contains recovery modes0–7, foreign-B degraded drain
with unchanged generation2/ownerA, real resultReady/live generation5 playback/
seek and EOS/recovery cold-three-row markers, consumer reservation ACK/clone
fence, and revalidation cases0–3. JUnit's truncated output is not used instead
of the complete LastTest. No unrelated historical PASS promoted to green4.

Fresh current216 still matches final manifest0bac37108e974c4e06e3210f09e4910276f1b05df1165867881e2d51d24ba2fe.
All origin patch digests/length and historical manifest/delta digests were
rechecked and remain equal to the independently reconstructed chain above.

**Bounded source/runtime GO; no outstanding findings in this accepted scope.**
No artificial missing-API RED is required/claimed for this test-only addition
to existing B coverage. IO-error returns, cancellation/late-inspection effects,
power-loss durability and broader unfinished/started-output continuation are
not qualified by these process-crash tests. No Native B integration, installed/
hardware/public readiness, task closure or whole-feature GO.

### Exact cleanup permission, no deletion by reviewer

Read cleanup.rb and executed only its no-argument read-only preflight. It
requires final6 regression success and each stage's terminal primary success,
exact2-file inventory/hash, no symlinks and realpath(target)==target ancestry.
Inspected script SHA:
`bb6f8936f1558728626958645a8cdd388422d2cab7bda5fa1a2788fa86061677`.

Cleanup GO applies only to these4 stage/apps/windows source-copy directories
under evidence root,8 files/305932bytes total:

| Stage | Files | Bytes |
| --- | ---: | ---: |
| green | 2 | 75175 |
| green2 | 2 | 76393 |
| green3 | 2 | 76844 |
| green4 | 2 | 77520 |

Each directory contains only CMakeLists.txt and the writer test TU, with
source hashes matching its terminal receipt-bound manifest. Main may perform
this exact cleanup while keeping the inspected guards/artifacts unchanged.
Preserve source-origin, full HEAD patch, all historical deltas, all manifests,
scripts/logs/JUnit/LastTest/receipts and this report; guest build and authoritative
worktree are outside every target. No further cleanup scope is authorized.
Only this report was appended; no source/checklist/task/GitHub/VM changes.
