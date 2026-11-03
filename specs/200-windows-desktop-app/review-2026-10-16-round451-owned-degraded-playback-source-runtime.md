# Round451 — bounded source, reconstruction and runtime review

## Checkpoint: GREEN2 primary qualified; regressions pending

Independent reviewer. Authoritative repository `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Evidence root `/Users/yshishenya/Documents/graf-f200-playback451.UQUxsU`.

This checkpoint is **bounded source GO and primary runtime qualification only**. Final regression/runtime acceptance and cleanup GO are pending. No VM commands, tests/builds, GitHub actions, source/norm/task changes, or evidence cleanup were performed. Only this reviewer report was created.

## Source verdict

Compared the three production deltas against frozen RED: `Recording/NativeCapture.h`, `Upload/DesktopUploadQueueService.h`, `Web/WebView2Host.cpp`; also reviewed the native scenario and the 15 new CalendarJoinHost policy cases. CRITICAL/HIGH findings: **0** in this bounded diff.

- Shared `isPreparedOwnedRecording` expresses row shape only; current account, alias/deletion, actual package and playback authority remain separate checks.
- Display-only `playableDegraded` is bound to the same immutable queue snapshot. Native admission checks the scalar and active session; storage then freshly reads queue/exact reservation, checks shared alias policy outside the work mutex, and allows only actual sealedDegraded for this quarantine exception.
- Full inspection/AAC and existing retained-package revalidation before open/resume/seek remain in the existing player/executor. No new proof authority, dispatcher, player, persistent field or queue mutation is introduced.
- Original normal playback branch remains; WebView retains current document/account, active reservation, deletion and Send gates.
- Mode0 distinguishes current B refusal from genuine resolution to A; mode1 starts with A and does not refresh account epoch to force post-B display. Native manual-send refusal already covers A in mode1. UI policy tests use synthetic timings intentionally and are not genuine package-proof runtime evidence.

Ponytail-review: **Lean already. Ship.** This is a minimality verdict, not release/runtime approval.

## Independent source reconstruction

Verified `source-origin.json`, full patch size **3,240,534 bytes** and SHA `2a1df7230bf672bd04ff6e85d271ee85ba57f7f079db4b39fc9d5e55ae688bd8`.

Used a newly created temporary `GIT_INDEX_FILE` and `GIT_OBJECT_DIRECTORY`, with the real object directory as a read-only alternate. Read HEAD, applied the full patch with `git apply --cached --binary`, then independently reset the temporary index to the reconstructed final tree before applying each historical delta. Retrieved indexed blob bytes using `git cat-file --batch` and SHA256-checked every manifest input.

| State | Reconstructed inputs | Manifest SHA256 |
|---|---:|---|
| GREEN2 | 216/216 | `9c58dd253a0f14d29969a05d7299051a97e670a983b59f5615eff5ea3fe5a7bc` |
| GREEN | 216/216 | `017369102f55ed46a86ff43c15aff2719c47bb7f52d41d9aaa0e0aee13d1596b` |
| RED | 216/216 | `e85a42604e92fafd0479bab9092279c223523ada94d1909a1b13d44ca14dcbb5` |

Historical delta hashes matched source-origin: GREEN `bf523655141baf3320a8a722e02ee13b76bc670d10daeec5a0923baf9cf14355`; RED `4e86e6d4a4e967009cb2fe446ae1695f2a4e8207eefa9f7005da51cab736e6b9`.

Current authoritative files independently match GREEN2 **216/216**. The ordinary Git index hash was unchanged before/after: `662a640f866392dde2940678f5d98c82c85c145c3be3aebedf2825a524e36229`. Temporary reviewer index/objects were removed; repository index/object writes and source-copy deletion were not performed.

## Saved runtime evidence consumed

Read PowerShell scripts, BOM-aware receipt JSON and native stderr; build/CTest logs were decoded as UTF-16LE before qualification.

RED: actual build0, test exit3 at `verified_owned_degraded_must_be_playable`, 3,683ms; successful B recovery and terminal no-change g2 ticket precede the exact assertion. Receipt binds RED manifest, native PE `4ff71ae955c33b5e66501b9f39a926d4ddf9c9d69ac6314f2b491cdd599103ee`, postflight216 and saved owned-process count0. It remains an expected failing run, not PASS.

GREEN's build log contains actual `WebView2Host.cpp` and `NativeCaptureStorageIntegrationTests.cpp` compilation. GREEN2 changes only CalendarJoinHostTests relative to GREEN, so its native incremental no-recompile is consistent with unchanged native PE, not the earlier stale-header failure pattern.

GREEN2 primary receipt: terminaltrue, build0, test0, **43,459ms**, manifest `9c58dd253a0f14d29969a05d7299051a97e670a983b59f5615eff5ea3fe5a7bc`, native PE `dc8d54ba87c9df84b389ca70f744d0d3788274a08eda21beb85b21e62f2f0bdf`, postflight216, saved owned-process count0. Script verifies prior source/idle state, all216 after execution and unchanged PE. No live guest/PE/CIM assertion is made by this reviewer.

Primary stderr includes both owned-degraded positive modes (muted progress, pause/seek, unchanged package/g2/HTTP0), cold sealedDegraded full inspection/decode; started-output and alias refusals; held-read shutdown cancellation; and inherited concurrent playback, Stop/EOS, ambiguous new finalizer, ambiguous deletion intent and physical purge markers. Their meaning was checked against the test assertions; log labels alone are not proof. Mode1's `actual_B=1` means construction B, **not** account B (initial_current_A=1).

The regression script selects 12 exact names, serial execution and stop-on-failure, checks JUnit count/names/status, source216 postflight and unchanged native/writer hashes after execution. At this checkpoint no terminal `green2/regressions.json` existed. Completed CalendarJoinHostTests is logged PASS1.75s; its regression-build log contains actual CalendarJoinHostTests.cpp compilation. The remaining live run is **not** counted PASS and no polling/wait loop was performed.

## Remaining gate and limits

Need the actual terminal regressions receipt, JUnit12 exact run names with no failures/skips, LastTest/CTest evidence, PE bindings and final current216 check. Cleanup remains **NOT AUTHORIZED by this checkpoint**; a cleanup script/allowlist has not been reviewed here. Preserve active evidence copies until final qualification and owner's fresh preflight.

Requirements gate remains separate (198 checklist files /458 checked /0 unchecked at accepted451 gate); no checklist or task markers changed here. No installed app, hardware audio, external account/network acceptance, release or whole T116 closure is claimed.

## Static app/cleanup script review — before execution

Read `build-app.ps1`, `cleanup.rb`, `cleanup-preflight.ps1` without executing them. Current on-disk inventory independently checked: exactly red/green/green2 × five allowed source paths = **15 regular files**; hashes match their own manifests and all actual realpaths equal their lexical paths. This observation is not a future symlink/ancestry guard.

Findings requiring attention before final cleanup/compile qualification:

1. **P1, cleanup.rb:6–7,30–32:** deletion is gated only by regression receipt and current source. It neither reads the app receipt nor consumes the fresh owner preflight; preserved source-origin/full/historical patch hashes are also not rechecked. Thus `--delete` can run after regression12 but before required app success/fresh preflight, or after reconstruction artifacts have disappeared. Minimum: enforce the stated app terminal/pass/source216/PE binding and fresh preflight (UTC freshness plus current manifest/native/app identities) before unlink, and verify retained origin/patch digests. Owner final review remains separate; no new product service is needed.
2. **P2, cleanup.rb:12–18,33–38:** stages are a regex rather than exact red/green/green2, while directory cleanup independently scans `root/*/apps`, including nonvalidated stages. Restrict both files and empty-directory removal to the exact three inventoried source trees; require exact 15-path inventory and realpath/ancestor checks before mutation. No current symlink or unexpected file was found.
3. **P2, build-app.ps1:42–43:** a successful incremental MSBuild plus existence/hash of the old output alone cannot prove the current451 app PE was rebuilt. Keep the correct output path, but bind evidence to actual current-TU compilation/link or otherwise qualified dependency freshness; record/check PE machine8664 and output freshness/identity. Do not treat a retained450 PE as current451 solely because Build returned0. This is an evidence-completeness issue, not evidence that the future build will actually be stale.

The build script otherwise keeps VerifyBuildArtifacts before restore/build, Release/x64, correct `apps/windows/out/x64/Release/GrafWindowsApp.exe`, source216 pre/post and idle checks, no install/launch, and correctly separates app HTTP from unmeasured NuGet restore networking. Recommended small sequencing guard: require the actual successful matching regression12 receipt before starting app build, not only absence of native processes. `cleanup-preflight.ps1` currently records only native PE; add current manifest/app binding if it is to guard the full declared cleanup gate.

Verdict: app script can support the planned diagnostic build with the stated qualification requirements; **cleanup script NOT YET GO**, no deletion authorized. No script/source changes or VM execution performed by reviewer.

## Terminal GREEN2 regression qualification and harness fixes

This append supersedes the pending-regressions status above, not the preserved history of original script findings. Independently read terminal `green2/regressions.json`, JUnit, the complete 391-line LastTest.log, decoded UTF-16LE CTest log, and the corrected three scripts. No VM calls, test launches, script execution or cleanup were performed.

### Bounded source/runtime GO

Receipt has terminaltrue/build0/ctest0/executed_tests12/postflight216/owned_processes0 and no failure. JUnit independently parsed: exactly the script's 12 distinct expected names, all status run, failures0/skipped0/disabled0. LastTest independently contains exactly those 12 test sections and 12 Passed results. CTest reports total **464.76s**. Current authoritative source independently rechecked **216/216** against GREEN2 manifest `9c58dd253a0f14d29969a05d7299051a97e670a983b59f5615eff5ea3fe5a7bc`.

| Test invocation | JUnit seconds |
|---|---:|
| CalendarJoinHostTests | 1.74733 |
| V5LocalRecordingWriterTests | 106.203 |
| NativeProtectedStartOwner | 14.2747 |
| NativeProtectedStartOwnerRecovery | 31.7373 |
| NativeProtectedStartOwnerDegradedRestart | 1.9888 |
| NativeProtectedStartOwnerUnfinishedRestart | 44.3704 |
| NativeProtectedRecoveryLivePlayback | 11.3687 |
| NativeProtectedDeletionDisplay | 3.47843 |
| NativeProtectedLocalPurge | 93.0364 |
| NativeProtectedLocalRemoval | 93.0165 |
| NativeProtectedPlaybackConsumer | 15.1395 |
| NativeProtectedPackageRevalidation | 48.2898 |

Saved native PE: `dc8d54ba87c9df84b389ca70f744d0d3788274a08eda21beb85b21e62f2f0bdf`, equal to GREEN2 primary. Saved writer PE: `13077e369bc4c8d1544629ca3de6dd445bf49f67f455b93699a336fe4f260885`. These are source/script-bound saved hashes, not a new live PE/CIM observation. The regression script checks native/writer hashes again after tests and source216 before/after; CalendarJoinHost compilation is in the build log, but the receipt does not separately hash that executable.

Complete LastTest confirms both new owned-degraded playback positives including initial-A post-B freshness; modes2/3/4 refusal/shutdown preservation; inherited concurrent playback/Stop/EOS, ambiguous finalizer/readback, ambiguous deletion and actual purge ACK; owner11, normal recovery8, local purge/removal9 each, playback seek/validation/clone drain, revalidation4 plus pinsFull. V5 includes 3 cold-playable positives,15 refusals, prefix and sealed-phase refusals, and24 actual child crash cuts with non-vacuous sealed_cold_decode1. Counts describe subcases inside the 12 invocations, not 12 new independent product features. UI15 is source-confirmed within successful CalendarJoinHostTests; it has no individual runtime markers. JUnit's truncated system-out was not used as complete evidence; full LastTest was consumed.

Verdict: **bounded current451 source + primary + regression12 runtime GO**, no new blocking finding. Requirements/source minimality verdict stands; no blanket quarantine access, normal upload authority, full T116, installed/hardware/UI or release acceptance is implied.

### Corrected harness static verdict

Original P1/P2 findings remain above as history. Their concrete fixes are present:

- App build now requires successful terminal matching regression12, primary manifest/native PE equality and records regression receipt SHA; requires actual AppMain/WebView2 log entries plus output path, fresh LastWriteTime and parsed PE machine8664. No old450 output is accepted merely for existing. AEC verify/restore/build and no install/launch boundaries remain.
- Cleanup now requires terminal successful app/source/AEC/x64 plus <=120s owner preflight; binds native/app PE and app receipt digest, verifies full/historical preservation patch hashes, exact historical stages, exact red/green/green2 file targets, realpath checks, exact15 files/2,722,781 bytes, and writes inventory before unlink. Directory removal is restricted to the same three stages.
- Owner preflight now compares actual current app PE with the app receipt, in addition to source216/native PE/idle checks.

**Static harness P1/P2 closed.** Final cleanup GO remains pending the actual terminal app-build receipt/log/PE qualification and owner's fresh preflight. The app is still an active build per user; no partial app outputs are accepted here. No deletion or script execution by reviewer.

## Final app compile qualification and conditional cleanup GO

Freshly read terminal `app-build.json`, the current build/cleanup/preflight scripts and all three app logs, decoded from UTF-16LE. Verified current branch `codex/200-windows-followup` and HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Independently rehashed current authoritative216 and the retained final/historical patches and copy inventory. No VM commands, executable reads through VM, builds, cleanup-script execution or deletions were performed.

### Bounded app compile GO

- App receipt: terminaltrue, AEC verification0, restore0, build0, preflight216/postflight216, owned_processes0, Release/x64, no failure/source_failure, elapsed **173,336ms**.
- Manifest `9c58dd253a0f14d29969a05d7299051a97e670a983b59f5615eff5ea3fe5a7bc` matches current216 and accepted GREEN2. Receipt binds regression12 by SHA256 `95860ac399b6658ff0ce57847039d24aa9bec0f91f9d40f9948f3862d784f365` and the build script checks primary/regression native PE equality before app build.
- AEC verification log confirms source/license identity `846fe90a289f58b7c9303a635142aa2c7caa93e5`; saved AEC provenance SHA `ebe9b371f9ef9ab8e78f45c607ab7a661235ad9396d4001e2079395b08aae0fe`. Restore log reports all projects up-to-date for restore; exit0 is recorded.
- Build log contains actual AppMain.cpp, WebView2Host.cpp, DesktopUploadQueueService.cpp and adjacent production compilation, library/output creation and LTCG. It reports **1,073 of28,637 functions compiled**,176 new functions,1,082 inline decisions re-evaluated. Therefore this is a real current-source incremental Release build/link, not a claim of clean/full rebuild. Warning D9025 (`/W1` overridden by `/W4`) remains; no warning-free claim.
- Correct output: `C:\Temp\graf-f200-start-owner-1a1oCY\apps\windows\out\x64\Release\GrafWindowsApp.exe`. Saved actual output hash **`83e6f7fdf7e43da046e69c0100e448168c44f6b03bee4217e91c61ad32607947`**, size **3,265,536 bytes**, parsed machine **0x8664**, written **2026-10-16T10:33:12.1749108Z**. The reviewed script checks actual output LastWriteTime against build start and MZ/PE headers, rather than trusting a pre-existing450 output. This reviewer qualifies the saved script/log/receipt chain, not an independent fresh read of guest PE bytes or live CIM.
- App receipt SHA256 freshly computed: `750a25f9d45228fc7b05b2bab3bee8aba981adc697f853b2a3bebc878d984f92`.

Verdict: **bounded current451 app Release/x64 compile GO**. Combined with accepted primary/regression12 and source review, no remaining blocker was found for the declared451 slice. No app launch, install, migration, device audio, app HTTP or full Windows readiness is established. NuGet restore networking was explicitly not measured. T116 remains open; this is not release acceptance.

### Conditional final cleanup GO — owner execution only

The earlier cleanup pending status is now superseded by this **conditional GO**. Authorize only the reviewed owner workflow after fresh `cleanup-preflight.ps1` succeeds immediately before deletion (age0–120s): guest216 unchanged, owned native/build processes0, native PE equal to accepted primary/regression, app PE equal to the accepted receipt, and exact app-receipt SHA binding. This fresh preflight has **not** been executed or claimed by reviewer.

Fresh static inventory again confirms exactly **15 regular source-copy files /2,722,781 bytes**: the same five allowed input paths in each of `red/apps/windows`, `green/apps/windows`, `green2/apps/windows` under the evidence root. All copy hashes match their own manifests; realpaths/ancestry are unchanged and no symlinks found. No other stage or source tree is in scope. Reviewed `cleanup.rb` persists checked inventory before unlink and restricts empty-directory removal to the same three stages. Script SHA256 at review: `3e417c7dc3b4a13599516601aea3a9e7c5f0e3fe99e891d3e7626986165eaae2`; preflight script SHA256 `4c27e49cc74ba17eee648e417bb909291d50cc9eed79f10b48b0f75923190170`.

Full HEAD patch and both historical deltas retain their previously independently reconstructed/hash-verified contents. Preserve source-origin, all manifests/patches, scripts, logs, JUnit/LastTest and receipts. Guest build/source and authoritative worktree remain untouched. If any source, script, receipt, PE, inventory or ancestry check changes/fails, this conditional GO does not permit bypassing the failed guard. No deletion was performed by reviewer, and no task/checklist marker was changed.

## Read-only post-cleanup confirmation and next narrow T116 gap

Owner subsequently reported fresh preflight exit0 and cleanup executed by absolute script path, after a relative invocation refused `root` before mutation. The absolute-root guard remains unchanged; reviewer did not execute either invocation.

Independently read cleanup.json (deletedtrue), all15 inventory entries and saved owner preflight. Verified exactly red/green/green2 × five allowed paths and2,722,781 bytes, each inventory hash against its preserved historical manifest. All15 files and all three stage `apps` trees are now absent. Fresh preflight binds guest216/process0, accepted native/app PE and exact app receipt digest. Cleanup receipt mtime is **13.649s** after preflight UTC, consistent with the required120s window; this is saved evidence, not a live process query. Current authoritative216 still match GREEN2. Full and both historical patches still hash-match source-origin; manifests, logs, scripts, RED/GREEN receipts, JUnit and LastTest remain. Final SHA256SUMS independently verified **37/37**, file SHA256 `4a7375dbac02e65246d54c7ba285885f60cfce3fb41f013655cb32669118ab10`. No cleanup was performed by reviewer; no loss of reconstruction evidence found.

### Minimum next implementation/validation slice, not a new task

Read current T116/T117 tasks and existing requestProtectedLocalRemoval/canLocalRemoval/planLocalRemoval plus protectedLocalPurge(userRemoval=true). T117 explicitly depends on completed T116. The specific next gap is **original-owner user-requested local removal of a genuine cold unfinished/recovered B package**, including recovery/player actual drain before physical purge. Existing local-removal modes create normal packages and, for userRemoval, server-history rows; the held mode covers display inspection, not a held unfinished B executor. Earlier own-origin deletion/purge evidence cannot silently stand in for this distinct public LocalRemoval entry and planLocalRemoval policy.

Use existing public requestProtectedLocalRemoval and existing genuine B fixture/canonical read cut. The smallest useful held case is: originalA request -> exact local_delete_pending intent commit/adoption -> actual B cancellation -> while read held, no OS absence/removed ACK -> release and actual retirement -> retained purge ACK/OS absence -> fresh cold queue/package absence and HTTP0. Preserve exact owner/IDs, unchanged pre-effect bytes and no late B recreation/promotion. The complementary already-recovered sealedDegraded ordering should reuse the same narrow helper/path (and actual player drain if open), not spawn a new framework or duplicate broad matrices.

Coverage authority: plan448 actual cancellation/drain and plan451 deletion/retirement fences, tasks.md T116 storage/deletion failures. No new schema, task, authority or user choice is needed. This is the smallest identified next unqualified boundary, **not a proof that it is the only remaining T116 item or that passing it automatically enables T117**. No code/norm/task/checklist edits or runtime experiment performed for this mapping.

### Scope clarification: reuse the existing held-B physical-purge scenario

Main proposes only `userRemoval=false` in existing `protectedDeletionDisplayDrain`, one additional `(true,true,true)` invocation in the same CLI, selecting `requestProtectedLocalRemoval(current projection, session, authGeneration)` instead of generic ownOrigin. Read the actual helper at1872+ and entry at NativeCapture734+: **existing normative gate is sufficient for this tests-only substep**. No new task, checklist, plan append or normative choice is required.

The existing `(true,true)` already proves ownOrigin held-B commit/adoption g2->3, no premature purge while the canonical read is held, actual retirement, retained purge ACK g3->4, OS absence and cold empty queue. The new variant must preserve this case unchanged and repeat its common assertions through the real LocalRemoval admission/plan path. Use the actual current snapshot/current original-owner epoch; no injected queue/projection, server history, proof or forced drain. Keep retained deletion-ticket lookup rather than latest unrelated worker ticket, correct shutdown polling, HTTP0 and exact memory. A metadata-only variant label is enough to distinguish the added invocation.

The earlier already-recovered/player-drain suggestion is **not an additional prerequisite for this narrow held-B entry-point validation** and should not expand it now. Runtime and source verdict for the future test diff remain pending. Passing this one scenario does not itself close umbrella T116 or authorize T117.
