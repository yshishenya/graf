# Independent source audit: packed current-pair cold verifier

Date: 2026-10-03. Skill: `code-reviewer`, personally read in full. Owner of this report only; concurrent production and test work preserved.

## Decision and scope

**Reviewed frozen 16-file bounded current-pair source verdict: ACCEPTED, CRITICAL=0, HIGH=0, MEDIUM=0. H1/H2/M3 and original M1/M2 are closed. Separately, the explicitly requested Metadata allocation/move compatibility review of that same frozen cohort is REQUEST CHANGES for H3 only: CRITICAL=0, HIGH=1, MEDIUM=0.** Exact Metadata candidate initialization is safe and has no intermediate move. H3 in the reviewed `8ae8…` Metadata / `43c620…` Codec cohort is a distinct transfer boundary: Metadata.cpp:109 constructs an optional snapshot whose entries vector move still allocates a Debug proxy under noexcept; count-ctor at :47 does not protect that transfer. This source finding is NOT attributed to the stale Writer binary or erroneous test baseline, and is not made a full-v1/T116 gate for current-pair source acceptance. Main reports frozen-cohort Debug 3/3 PASS, clean native Release 41/41 PASS, clean portable 39/39 PASS and exact cohort/compile-source matching; these are main receipts, not reviewer runtime observation. Exact reviewed 16 hashes are in the final section. Subsequent concurrent changes to Codec, Metadata and FilesTests were detected during final readback and are listed separately below; their H3-fix status and runtime are not covered by this frozen-cohort verdict. Only final VS Rebuild receipt remains pending among the reported frozen-cohort validation runs. No overall v1/flat-index/full T116/integration/application readiness acceptance is claimed.

Reviewed branch `codex/200-windows-followup`, HEAD `99b00a579c24b50e320465b69d9a296038bc544d`, in `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`. The implementation is dirty/untracked relative to that HEAD: the commit SHA alone does NOT identify the reviewed implementation. The exact file SHA-256 values below identify it. All six requested production hashes matched the owner's prefix/early-pin follow-up and remained unchanged at the final pre-report check.

Scope: `ProtectedPackedCustodyFormat.{h,cpp}` descriptor/child/head-pair additions, new `ProtectedPackedCustodyTree.{h,cpp}`, private Owner Guard and its implementation in `ProtectedCustodyFiles.cpp:706–757` (original line references). Existing physical owner, codec, allocation, wiping and confinement implementations were read as dependencies. Follow-ups explicitly include common CustodyBytes, local Reader/Writer compatibility cleanup, explicitly requested Metadata allocation/move boundaries, current TreeTests (742 lines), OwnerTests (553 lines) and the bounded cold-cache sidecar in FilesTests (1594 lines). No whole-v1/test-suite acceptance is inferred from these sidecar reads.

No production, test, spec, task, GitHub, commit, private inventory, VM, installed app, or other review file was changed. Only this report was created. No native or portable tests were run by this reviewer. The owner's reported native CMake `/W4 /WX` compilation and portable-format success are reported evidence, not independently executed checks or a native TreeTests PASS.

## Original snapshot findings: validation only (historical)

### M1 — Admitted Tree allocation/exception failure is not exercised

Locations: `ProtectedPackedCustodyTree.cpp:43–95,102–164`; `ProtectedPackedCustodyTreeTests.cpp:453–470,475–490`. Contract §§1,2,6; accepted tree requirements gate, sections 1 and 3.

`oneBorrowedJob()` tests four-slot job admission refusal, not a failure after the Tree has acquired the physical mutex. `lifetimesAndFaults()` calls `blockWrites()` explicitly; it does not demonstrate that an exception originating in Tree read/verification is converted into the sticky first failure while the same guard is still held. There is no Tree test saturating the 64MiB charged allocator or the 32-pin count. Consequently the new exception-boundary and early-pin behavior have source evidence but no direct regression evidence. This is a coverage gap, not a demonstrated faulty catch implementation.

Smallest follow-up: reuse the existing TU-local file-call fault approach in `ProtectedPackedCustodyOwnerTests.cpp`, without product fault switches or a new abstraction. Exercise `std::bad_alloc` at a Tree guarded metadata/read boundary and charged-allocation refusal during `verify()` and `readBlock()` on generated data. After admitted failure, verify identical error/nativeError from subsequent Tree reads, reverify, physical reads and writes; no proof/bytes; no publication before failure classification; charged bytes and pins released after actual completion. Test failed pin admission separately: reserve remaining pins, prove the factory refuses before DFS/Tree allocation, then releases admission normally. Do not conflate this pre-content admission refusal with an admitted sticky failure. Include the empty/ZERO read path, whose result allocation does not pass through DATA decoding.

### M2 — Pinned reads across raw head changes and the shared-mutex boundary lack regressions

Locations: `ProtectedPackedCustodyTreeTests.cpp:251–275,421–451`; `ProtectedPackedCustodyTree.cpp:79–92,99–161`; `ProtectedCustodyFiles.cpp:706–756`. Contract §§2,4,5; accepted tree requirements gate, section 1.

`dataPairAndReopen()` destroys the first Tree before appending/publishing g3. `lifetimesAndFaults()` covers owner retention, write revocation and an explicit sticky fault, but not an old proof retained across raw physical appends/head replacement. There is also no Tree operation paused while a competing raw `publishHead()`/append is attempted. Thus these tests would not catch a regression to per-read locking or reads following the latest HEAD instead of the immutable pinned root. Static inspection confirms the intended locking and root use; a runtime concurrency failure is NOT established.

Smallest follow-up: keep the g2 Tree and a result alive; append a different g3 path and publish via the existing physical fixture; prove the old Tree still independently reads the g2 bytes, a fresh verifier reads g3, and both retain the same native owner. Add a bounded, event-controlled TU-local pause inside the real Tree verification/read path, then attempt publication from another thread. Assert no physical write enters until the entire Tree operation/result construction or sticky rejection completes. Reuse existing OwnerTests event/fault conventions; do not add sleeps, a second dispatcher, or product synchronization hooks. This does not accept logical commit/ACK or a future writer.

## Version semantics: no unsupported source finding

`decodeChild()` passes `descriptor.generation` to `decodeReference()` (`Format.cpp:125–126`); `decodeReference()` checks `ref.version>0`, `ref.version<=generation`, and child end at/before parent offset (`Format.cpp:22–30,63–73`). Typed decoding verifies the exact expected ref version rather than accepting a child-reported version (`Codec.cpp:129–137,94–98`).

The accepted contract §3 states that newly written DATA/NODE records use target generation and inherited refs retain their exact old version. It does not explicitly specify `child.version<=parent.version` as an additional cold-decoder bound. Its reference-bounds interface supplies descriptor generation and physical parent offset, not a parent creation-version limit. A valid immutable creation history naturally has the stronger temporal relationship, but this current factory proves both authenticated closures, not the historical sequence of authorized transitions that created them.

Accordingly, **the missing parent-version comparison alone is not classified C/H/M here**. Future live structural-delta validation must not use this factory to authorize rewriting an old-version parent or inventing inherited provenance. If the stronger comparison is adopted as cold-format canonicality, make that requirement and a self-consistent negative fixture explicit together; do not silently turn it into an extra blocker for the accepted current-pair slice. Existing older child refs must remain valid. This conclusion does not relax the currently enforced generation, typed-context or physical-order bounds.

## Source checklist and evidence

- [x] Branch/HEAD and dirty-file identity established; exact source hashes below, not a clean-commit claim.
- [x] Factory reserves its proof pin before DFS/owned Tree allocation and revalidates the exact 128-byte prefix under Guard (`Tree.cpp:43–55,85–91`).
- [x] Both HEAD cells are independently read and typed-decoded; exact descriptors and legal pair are required; both closures run before proof construction (`Tree.cpp:56–92`). Computing the selected index earlier is not publication of a partial proof.
- [x] Descriptor uses exact native EOF, not rounded append position; all refs remain within descriptor extent and child-before-parent bounds (`Files.cpp:734–740,620–659`; `Format.cpp:63–89`). Orphan tail may exist but supplies no root authority.
- [x] All 64 child refs are checked in each reachable NODE; levels/bases, EMPTY only outside logical length, canonical ZERO, exact DATA tail and no nonzero DATA beyond EOF are enforced (`Format.cpp:106–126`; `Tree.cpp:17–35,110–154`). Cold traversal follows all reachable children, not just the requested path.
- [x] Root and every non-inline child use exact expected envelope size/SHA before DPAPI; typed context/version and internal checksum then apply (`Codec.cpp:129–137,75–105`). A HEAD is decoded from its known slot/context, not a caller root stamp.
- [x] H1 source correction inspected: byte default/move constructors use potentially throwing count construction and nonallocating storage swap; `PackedPlainRead` does not force move noexcept. Guard/job/mutex catches admitted failure. Previously supplied focused Debug PASS is pre-H2/M3-fix evidence, not fresh execution of this cohort; the H1 source defect remains closed.
- [x] Proof creation is private, descriptors/selected slot are immutable, and a strong same-owner reference carries epoch/native identity/container lifetime indirectly through the non-replaceable State. Reads use that pinned descriptor, not current HEADs (`Tree.h:19–38`; `Tree.cpp:99–161`). No public from-fields/historical factory exists.
- [x] DFS keeps three NODE bodies plus bounded DATA processing; no flat index/bitmap/per-record HANDLE/cache. Cipher/body/result/Tree/control-block heap allocations use `CustodyAllocator`; proof is below 4KiB, job limit4 and pin limit32 are admitted before corresponding work. Transient codec copies remain charged; native DPAPI output is a separately scoped native allocation, not claimed to be charged application heap (`Memory.h`; `Tree.cpp:24–25,43–46,85–91,104–107`; `Primitives.cpp:58–71`).
- [x] M3 source defect closed: bytes is now declared first in PlainRead and CipherRead, so throwing byte preparation precedes pin/proof/owner transfer. PlainRead destructor body still wipes plaintext before member release. Sole aggregate initializer updated. Retained-result regression source checks bytes/ownership, weak lifetime, pin quota, confinement and successful reuse after pressure removal; isolated and clean Debug post-fix execution attributed main below.
- [x] Current-pair proof is explicitly not historical-retainer, package, upload, logical commit or GC authority. No production application consumer adoption found. Retained metadata, future writer, migration and full T116/T117/T118 acceptance remain outside this review, not additional findings.
- [x] M1 coverage finding closed: OwnerTests baseline precedes all guarded cases, checks charged-byte equality, and reacquires all 4 jobs / 32 pins. Test source inspected; current clean Debug 3/3 and Release 41/41 execution reported by main, not run by reviewer.
- [x] M2 coverage finding closed: OwnerTests observes an actually admitted publisher job while verifier holds the physical mutex, then checks same-cause no-effects refusal. Test source inspected; current clean Debug 3/3 and Release 41/41 execution reported by main, not run by reviewer.
- [x] H2 source defect closed: factory calls cache() inside its try after successful Pin admission and before native open/ReaderState creation. FilesTests cold-process open-without-Read/Clone → raw budget pressure → stream close regression source inspected; main reports isolated and clean full FilesTests post-fix PASS.
- [x] H2 isolated post-fix native execution: main reports session `44460`, Debug build EXIT 0, cold-cache-close EXIT 0, measured proxy 16B / cleanup 16B. Later full FilesTests PASS `91706` closes the sequence marker below; no reviewer execution is claimed.
- [x] M3 isolated post-fix native execution: main reports session `44460`, retained-plain-move EXIT 0 and retained-cipher-move EXIT 0, focused Owner/Tree PASS. This closes the targeted move regressions only; no full native acceptance or reviewer execution is claimed.
- [x] Full Debug sequence marker: main reports clean product build `42537`, final test rebuild `91706`, native 3/3 PASS 12.26s (Files 7.99s / Owner 1.15s / Tree 2.99s). Current test scopes and removal of temporary diagnostics inspected. Old stale Writer stack and proxy-still-live baseline failure are not treated as current product defects; current GREEN is attributed to main only.
- [x] Final cohort/clean validation receipts attributed main: `95206` SOURCE_MATCH16/16 canonical/mirror/guest and whole canonical/mirror183/183; `13819` COMPILE_SOURCE_MATCH155/155; `10918` clean native Release build EXIT0, full41/41 PASS40.18s; `8829` clean portable39/39 PASS25.34s. Local16 hashes independently checked by reviewer; remote matching/runtime not personally observed. Old portable `81661` remains historical only.
- [x] Final VS Rebuild `95823`: main reports ongoing; no terminal receipt yet, so not accepted. This is not a blocker for the bounded current-pair source verdict.
- [x] H3 typed-vector compatibility in reviewed `8ae8…` Metadata / `43c620…` Codec cohort: protect unsafe entries construction/transfer and prove partial-headroom/move-refusal cleanup. Subsequent concurrent Codec/Metadata changes are outside this completed frozen-cohort review; no claim is made that H3 survives or is fixed in those new bytes. No full-v1 acceptance is required or implied by this local condition.

**Current checklist readback: 18 checked / 2 unchecked.** H1/H2/M3, original M1/M2, full Debug and current cohort/Release/portable receipts are closed at their stated evidence level. Only H3 Metadata typed-vector compatibility and final VS Rebuild receipt are open. Bounded current-pair source is accepted independently of those separate items; current source identity is the stable 16-file table, not overall v1/T116/application acceptance. Earlier counts and failure/pending statements below describe historical cuts.

## Original reviewed bytes (historical; superseded)

Paths in this table are relative to the inspected worktree. All hashes are SHA-256, not Git blob IDs.

| File | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.h | `becd7f67f17a0baca81066a8eecb1b0a3303c0a420ca4f033303224dbf335638` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp | `4c75c539722ec3097ccef271853e46c1529d058617444b735192a1fee1b2589b` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.h | `0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.cpp | `bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h | `11f4253afe0726781f8319315ba2c707571ac574f23c55aa9b2cf5ce2e0faae6` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `0de67eb321f40027ea035d9fdc4ef095332c1c7ada777e2804bc66fea8b04006` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp | `39295ed748e9ab1793ca39d5f130a42dbdb607823a476735777b64bdcb0ae504` |
| specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md | `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed` |

Dependency hashes: Codec.h `df71aee96738833815a9583590a53adff44b351dc7bbde8541d9b1e16cb664e1`; Codec.cpp `18d6ca5a0ab0e4a454c81512c18a174dc7009d2baabee0b6bb82a80acecd153f`; Memory.h `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad`; Primitives.h `5b3f75a9af51aaee6b0efcc9a20f1f5039aaf7e0ea957992d7432a5038619e9c`; Primitives.cpp `a27b07ac3b04627c5286d6290b3ca6ba3a15710fa170f238be893c3e13c133b3`; Files.h `108f2e989b081812a38a2464a3eda9930fe35c1173a86df0f288851e6aefeced`.

## Guidance and verification limits

Read root/ancestor instructions, guidance index and applicable worktree/risk/product guidance; release guidance's validation-lane section; applicable constitution/storage PRD and product-status evidence boundaries; current feature pointer and the relevant FR-012/storage plan, task dependencies and quickstart §14. Packed contract read in full before analysis. Existing tree requirements gate was consulted for the accepted narrowed scope, not used as runtime evidence.

Microsoft Learn `CryptUnprotectData` Remarks and `ReadFile` synchronization/offset documentation were independently consulted as native API references. They do not prove this implementation's correctness or test execution. The application's extra typed/context/checksum validation and synchronous explicit-offset use were traced in local source.

Validation lane: read-only source investigation with one reviewer-owned report edit. Broader application, release, migration or inventory gates were neither run nor imported into the finding count. The code-reviewer skill determined preparation, source/dependency review, actionable findings and evidence limits; it did not authorize production edits.

## Follow-up review — test extensions present, final receipts pending

Date: 2026-10-03. The original review and its snapshot table above are historical evidence and are preserved. `code-reviewer` was personally reread. HEAD remains `99b00a579c24b50e320465b69d9a296038bc544d`; all six production hashes still match the original table. The factory/read exception scopes and the shared physical Guard were reread: no new production-source C/H/M finding is established. **M1/M2 markers remain unchecked; no final native test acceptance is declared.**

New test source inspected:

- OwnerTests `treeGuardFaults()` reserves 31 pins with one actual owner already live. Its failed factory call must perform zero reads and zero metadata queries, and verification succeeds after releasing the pins. This directly addresses early-pin admission without incorrectly demanding a sticky fault for pre-content refusal.
- The same function injects IO failure, changed bytes and `bad_alloc` on the first HEAD read after the prefix. Reverify must preserve error/nativeError without additional reads. A separate final-metadata exception case checks three successful probe-job admissions and refusal of the fourth during exception destruction, plus exactly three reads and zero writes/flushes. These are meaningful tests of the actual Files implementation, not a substitute mock owner.
- TreeTests `chargedVerifyRefusal()` and `chargedReadRefusals()` apply the actual charged allocator cap. DATA and inline ZERO read cases are separate; the latter proves root decoding fits its 32KiB headroom before the 256KiB result allocation is refused. The tests check absent result values, sticky allocation failure during and after pressure, and unchanged error/nativeError on subsequent proof/physical/Tree reads.
- TreeTests `resultPinRefusalIsTransient()` reserves the exact remaining 30 pins with Owner+Tree already retained, checks result refusal, then verifies successful reads/reverify after releasing admission pressure.
- TreeTests `pinnedOldRootAcrossPublications()` retains g2 while physical fixtures append/publish g3 and g4. It checks the old bytes even after g2 has disappeared from both current HEAD slots and distinguishes the new g4 proof. This directly addresses the immutable same-owner pinned-root portion of M2, without granting historical restoration or logical commit authority.

Two remaining test-evidence qualifications are concrete, not production defects:

1. **M1 cleanup assertion scope:** current OwnerTests `main()` calls `treeGuardFaults()` before capturing `CustodyOwnedMemory::usedBytes()` for its final equality assertion (observed lines 454–456). Consequently that equality does not detect charged allocation leaked by the new guarded-exception cases. Move the existing baseline before those cases or add a before/after check around them. TreeTests' own whole-program baseline does cover its new charged-pressure cases, but it is a different executable.
2. **M2 contender synchronization:** current OwnerTests writer signals `writerReady` before entering `publishHead()` (observed lines 423–426); the verifier resumes and throws as soon as that signal arrives. A valid execution can delay the writer until after the failure has already latched. Equal errors and zero writes/flushes therefore prove the competitor's eventual rejection, not that it had actually entered the physical operation and waited on the mutex. Do not describe this test as a deterministic mutex-wait proof. Establish an observable in-operation/admission boundary and the attempted overlap using the existing TU-local approach, or explicitly retain this narrower evidence limitation. No product hook, second synchronization architecture or sleep-based test is requested.

Observed test identities during this follow-up:

| File | SHA-256 |
| --- | --- |
| ProtectedPackedCustodyTreeTests.cpp, 628 lines | `99ff4415490f45a58c1e6542386eae3dba202156644625ab5ff4268494eca812` |
| ProtectedPackedCustodyOwnerTests.cpp, first observed snapshot, 495 lines | `16207bc4490082a71bd6b8ad4d794643d09a8718ec12243f546e2acd83045365` |
| ProtectedPackedCustodyOwnerTests.cpp, later observed diagnostic snapshot | `e57f8edb91a0fb7d11b09d0f92d95677e124e96a8c4be3f2672441c5402d4f98` |

OwnerTests changed during the review; these identities are not claimed to be final frozen test inputs. Subsequent line positions/hashes must be refreshed before accepting receipts.

The owner reports an earlier native Release 41/41 PASS in 41.71s, portable 39/39 PASS in 24.38s, and focused Release Owner PASS in 1.04s. These reports are not transferred to the later extended/diagnostic test bytes without matching final receipts. The local validation document inspected still contains the earlier owner-stage results, not an exact-input final receipt for these extensions. No test executable or VM was run by this reviewer.

The owner also reports an older Debug Owner assertion abort reproduced before these extensions and ongoing diagnosis. It is neither independently diagnosed here nor attributed to the unchanged production Tree source. Release results do not prove Debug passed. Record the eventual diagnosis/result separately; do not silently remove the failure or expand it into application acceptance.

Historical follow-up state before the Debug allocation investigation: production-source C/H/M was recorded as 0/0/0; two validation findings remained open. That source conclusion is superseded by the next section. Only this report was edited; no source/test/app/inventory/VM/tracker state was changed.

## Latest follow-up — Debug construction fixes and remaining move defect

The owner's concrete Debug RED diagnosis supersedes the earlier unchanged-source assumption. The prior physical `PackedCipherRead` construction outside the held-lock `try` could allocate a charged Debug iterator proxy. Moving pin admission and result construction inside the job/mutex/`try`, after the existing-fault check, addresses that boundary. Tree now checks result pin admission before constructing `PackedPlainRead`. Explicit `CustodyBytes(0)` in physical results, `PackedPlainRead.bytes`, and Tree scratch-release swaps makes these particular constructions potentially throwing rather than using MSVC's `noexcept` default constructor. These changes preserve the existing charged budget, pin/job limits and same-State mutex. They do not yet cover the subsequent vector move constructions.

### H1 — Successful read/return can still terminate on a charged Debug move proxy

Primary locations: `ProtectedPackedCustodyTree.h:11`, `ProtectedPackedCustodyTree.cpp:10,143,162`; `ProtectedCustodyFiles.cpp:24,657–659,862`; aggregate `PackedCipherRead` in `ProtectedPackedCustodyOwner.h:10–15`. This affects the current bounded verifier/read path, not a hypothetical future application consumer.

MSVC STL's ordinary `vector(vector&&) noexcept` calls `_Alloc_proxy(_Get_proxy_allocator(_Getal()))`; Debug proxy allocation rebinds the supplied allocator and calls its `allocate(1)`. `CustodyAllocator` therefore charges this allocation and throws when the remaining 64MiB budget is insufficient. The source's `passed(T value)`/`success(T value)` and optional-result construction still invoke that move constructor. `PackedPlainRead` explicitly defaults its move as `noexcept`; removing that outer annotation alone is insufficient because its vector member's move is itself `noexcept`.

A concrete trigger is the existing full-block inline ZERO fixture with charged headroom equal to its result payload plus the observed empty-vector proxy charge. The initial result proxy and root decode fit; all root temporaries are released; `result.bytes.resize(count, 0)` succeeds and consumes the final available charge. Metadata checking and retaining the proof do not release the result payload. `passed(std::move(result))` then needs another Debug proxy and terminates, instead of returning no bytes and latching `allocationFailed` while Guard is held. Independently, `State::read()` can fill the budget with its count-constructed ciphertext buffer and fail in `success(std::move(bytes))` before returning to the outer Guard catch. The raw vector transfers in the codec/primitive dependencies also require care when addressing this same failure mechanism.

This is a source-confirmed failure path using the cited STL behavior; this reviewer has NOT executed a native near-limit abort reproduction. The owner's focused Debug 2/2 PASS does not disprove it: current tests use zero headroom (failure before a successful buffer construction) or 32KiB headroom (failure at the 256KiB payload allocation), not enough-to-build/not-enough-to-move headroom.

Smallest correction: make custody buffer/result transfers on these admitted paths avoid potentially allocating `noexcept` vector move construction, using a locally bounded transfer strategy with potentially throwing count construction plus swap/in-place construction under the existing Guard. Follow the actual internal physical/codec/result transfer chain, not only the final outer result. Do not disable Debug iterator checks, exempt proxy charges, or rely on unreserved observed headroom. Add a native Debug exact-fit regression for ZERO result transfer and a physical read return, deriving the actual proxy charge rather than hard-coding an STL implementation size; verify ordinary `allocationFailed`, no result/proof, sticky same cause and cleanup. A subprocess abort-sensitive test is appropriate while proving the pre-fix failure.

Primary implementation checked personally: Microsoft STL `stl/inc/vector`, ordinary move constructor and `_Alloc_proxy` call; `stl/inc/xmemory`, `_Get_proxy_allocator`, `_Container_base12::_Alloc_proxy` and allocator rebinding. References: https://github.com/microsoft/STL/blob/main/stl/inc/vector and https://github.com/microsoft/STL/blob/main/stl/inc/xmemory. These external implementation details are not a claim that the repository's production sources were edited by this reviewer.

### M1/M2 follow-up status and receipts

The complete 628-line TreeTests and 497-line OwnerTests snapshots identified below were reread. M1's factory pin-31 refusal, result pin-30 refusal, actual charged verification/DATA/ZERO refusal, early read errors and final-metadata admitted exception now have meaningful test source. M2's old g2 proof across raw g3/g4 publications now has direct test source. OwnerTests' event-controlled competitor also checks eventual same-cause rejection with zero writes/flushes. These are genuine bounded coverage improvements; none creates logical proof/publication authority from raw results.

Two narrower evidence limitations remain unchanged: OwnerTests' final memory baseline starts AFTER `treeGuardFaults()`; `writerReady` is signalled BEFORE `publishHead()` entry, so a delayed competitor need not have waited on the mutex. Consequently M1's new Owner cleanup coverage and M2's deterministic overlapping operation evidence are not fully closed. H1 additionally needs the exact-fit move regression above. This is not a request for a larger synchronization or custody architecture.

The owner directly reports native Debug focused Owner+Tree **2/2 PASS, 11.94s** (Owner 3.51s, Tree 8.02s) for production `70c7ac03…` / `11e54696…` / `01ea3672…`. Accepted here as owner-reported focused execution evidence for this snapshot, not independently run or an exact-fit move test. Final full native Release 41, portable 39, and Visual Studio receipts are still in progress per the owner; earlier full-suite timings are not transferred to these changed bytes. No VM or test execution was performed by this reviewer.

### Latest exact reviewed bytes

Branch remains `codex/200-windows-followup`; HEAD remains `99b00a579c24b50e320465b69d9a296038bc544d`. Dirty/untracked implementation is identified by these SHA-256s, not the HEAD alone. Paths are relative to `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.

| File | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.h | `70c7ac03120cf8fe8162d0b078aa1d0d44f2e3ce378c43c339e6ea4f27b4af2c` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp | `11e54696cff69e2421ca312a9e351476cc4979a03f60a5e9bee1e17427b0559f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.h | `0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.cpp | `bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h | `11f4253afe0726781f8319315ba2c707571ac574f23c55aa9b2cf5ce2e0faae6` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `01ea3672a46cda99e7dffabc30641468de133c77edd30af23b9fa26b534c8bff` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp, 628 lines | `99ff4415490f45a58c1e6542386eae3dba202156644625ab5ff4268494eca812` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp, 497 lines | `e57f8edb91a0fb7d11b09d0f92d95677e124e96a8c4be3f2672441c5402d4f98` |

Conclusion at the preceding focused-Debug cut: **source C/H/M = 0/1/0; validation MEDIUM=2 with substantial new coverage; checklist 10 checked / 3 unchecked.** Same physical mutex, both current HEADs/full DFS, exact EOF, typed/SHA-before-DPAPI checks, immutable pinned roots and accepted descriptor-level version semantics retain the previous positive source evidence. No new parent-creation-version requirement or full-T116/application blocker is inferred. Only this report was changed.

## Финальная повторная проверка замороженного снимка — 2026-10-03

Навык `code-reviewer` лично перечитан. Повторно сверены ветка, HEAD, все шесть производственных SHA-256, оба SHA-256 тестов и SHA-256 packed-контракта. Они совпадают с таблицей «Latest exact reviewed bytes» выше; TreeTests содержит 628 строк, OwnerTests — 497. HEAD по-прежнему `99b00a579c24b50e320465b69d9a296038bc544d`, ветка `codex/200-windows-followup`. Dirty/untracked содержимое не приравнивается к committed HEAD. Старые таблицы с `becd7f67…` / `4c75c539…` / `0de67eb3…` не описывают текущие производственные файлы.

### Фактические результаты, сообщённые main

Источник следующей таблицы — финальное сообщение владельца/main в этом чате. Reviewer не запускал CMake, CTest, VS, VM или приложение, не наблюдал эти процессы и не пересчитывал байты исполняемого файла. Сопоставление с текущим снимком основано на лично проверенных исходных SHA-256 и явном сообщении main, что после их фиксации исходники не менялись. В двух просмотренных локальных validation-документах не найден отдельный полный журнал именно этих финальных запусков; это не отрицание предоставленных результатов и не дополнительное замечание C/H/M.

| Проверка | Результат от main | Что этот отчёт принимает |
| --- | --- | --- |
| Полный native Release CTest | 41/41 PASS, 39.29s; `FINAL_RELEASE_TEST_EXIT=0` | Сообщённое прохождение полного набора для замороженного снимка |
| Полный VS solution build | EXIT 0 | Сообщённую успешную сборку; не запуск приложения |
| VS CoreTests | EXIT 0 | Сообщённое успешное выполнение CoreTests |
| Portable CTest | 39/39 PASS, 24.28s | Сообщённое прохождение переносимого набора; native-ветки не исполняются portable-тестами |
| Native focused Debug Owner + Tree | 2/2 PASS, 11.94s; ранее main сообщил Owner 3.51s / Tree 8.02s | Сообщённое прохождение присутствующих Debug-сценариев; не отсутствующего exact-fit move-сценария H1 |

SHA-256 приложения **от main**, без независимого чтения бинарного файла: `08CCAFBBE68DB83C6B3C26C80C5B7A2DAFD5B7F2220ED8282CF98A845EE28B22`. Этот идентификатор не является доказательством установленного/запущенного приложения, принятой интеграции custody, подписи или нормальной работы с реальным inventory. Старые timings 41.71s / 24.38s относятся к прежним сообщениям, а не подменяют финальные 39.29s / 24.28s.

### M1 — основное покрытие добавлено; остаётся точный пробел контроля освобождения

Повторно прочитаны OwnerTests `treeGuardFaults()` и `main()`, TreeTests `ChargedPressure`, `allocationLatched`, `chargedVerifyRefusal`, `chargedReadRefusals`, `resultPinRefusalIsTransient` и вызовы из `main()`.

Подтверждено по исходникам тестов: factory pin-31 отказ происходит до reads/metadata; read IO failure сохраняет `ERROR_READ_FAULT`; changed-read и `bad_alloc` запрещают успешный proof; повторная проверка сохраняет первый error/nativeError без новых reads; final-metadata exception проверяет сохранённый native job через 3 admitted / 4th refused; реальные charged-отказы verification/DATA/ZERO дают отсутствие результата и sticky allocation error до и после снятия давления; read-result pin-30 отказ остаётся временным и не отравляет owner. TreeTests' общий memory baseline перед этими случаями и итоговая equality-проверка после них покрывают их освобождение. Финальные PASS от main внесены как выполнение существующих проверок, не как собственное наблюдение reviewer.

Исходная широкая формулировка «admitted Tree allocation/exception/early pin не тестируются» **больше не актуальна**. Остаточный MEDIUM M1 уже: OwnerTests вызывает `treeGuardFaults()` в строке 455, а `before = CustodyOwnedMemory::usedBytes()` снимает только в строке 456; финальный assert в строке 495 потому не замечает charge, оставшийся после новых exception-сценариев. Другой исполняемый файл TreeTests это не покрывает. Минимальное действие — перенести существующий baseline перед `treeGuardFaults()` либо добавить его локально вокруг этого вызова, затем проверить равенство после завершения. Утечка производственного кода здесь НЕ установлена. Отдельный exact-fit отказ возвратного move относится только к H1 и повторно как M1 не считается.

### M2 — старый pinned root проверяется; ожидание того же mutex не доказано детерминированно

TreeTests `pinnedOldRootAcrossPublications()` (472–494) сохраняет g2 proof при raw g3/g4 appends/HEAD publications, читает старые bytes после вытеснения g2 из обоих current HEAD slots и отдельно проверяет новый g4 proof. Этот исходный пробел M2 закрыт по исходникам теста и финальным PASS, сообщённым main. Это lifetime уже созданного same-owner proof, не восстановление historical authority после ownership gap.

OwnerTests `testFirstStream()` (69–76) ставит событие во время final metadata check и ждёт readiness конкурента; `treeGuardFaults()` (423–431) проверяет его итоговый same-cause отказ и ноль writes/flushes. Такое поведение действительно проверяется, но остаточный MEDIUM M2 сохраняется: `SetEvent(writerReady)` в строке 425 предшествует `publishHead()` в строке 426. Планировщик может отложить writer после сигнала до уже завершённой классификации ошибки. Поэтому PASS не различает настоящее ожидание mutex и более поздний вход в уже failed owner. Минимальная дополнительная проверка — установить наблюдаемую границу входа/admission конкурирующей операции, пока verifier ещё удерживает Guard, до разрешения fault/unwind. Изменения продукта, новая архитектура блокировок и задержки `sleep` не требуются. Ошибка самой производственной блокировки НЕ установлена: по исходникам используется тот же State mutex.

### H1 и окончательный вывод

H1 повторно проверен в неизменённых `Tree.h:11`, `Tree.cpp:10,143,162` и `Files.cpp:24,657–659,862`. Возвраты всё ещё перемещают charged vector через `noexcept` move; конструкция `CustodyBytes(0)` исправляет начальное создание, но не этот последующий move. Лично повторно прочитаны первичные Microsoft STL `vector` (ordinary move / `_Alloc_proxy`) и `xmemory` (Debug allocator rebinding / `allocate(1)`). При `_ITERATOR_DEBUG_LEVEL > 0` вывод об аварийном завершении после успешного exact-fit payload allocation остаётся обоснован исходниками. Нативного воспроизведения именно H1 reviewer не выполнял; имеющиеся Debug-тесты оставляют 0 или 32768 bytes, а не достаточно для payload, но недостаточно для следующего proxy. Полные PASS не исполняют отсутствующий случай и не закрывают H1.

Итог повторной проверки: **производственные исходники C=0 / H=1 / M=0; остаточные замечания к проверкам MEDIUM=2 (M1 cleanup baseline, M2 deterministic overlap); REQUEST CHANGES.** Все сообщённые финальные результаты внесены, ожидания этих результатов больше нет. Отметки перечитаны и пересчитаны: **10 checked / 3 unchecked** — H1 и два указанных остаточных пробела. При этом основные добавленные сценарии M1 и сохранение g2 в M2 явно признаны покрытыми, а не объявлены отсутствующими.

Режим проверки: чтение исходников и редактирование одного собственного отчёта. С помощью `code-reviewer` отдельно проверены ошибки, владение ресурсами и доказательность тестов; зелёный общий запуск не подменяет анализ конкретных путей. Других записей reviewer не делал. Current-pair proof, BOTH HEAD/full DFS3, exact actual EOF, typed refs/SHA-before-DPAPI и immutable same-owner root остаются областью проверки. Дополнительного требования `child.version <= parent.version` не введено; writer/retained metadata/migration/GC/full T116 и app consumer adoption не приняты и не добавлены к числу замечаний.

## Проверка нового исправления H1 и совместимости byte-wrapper — выполнение пока ожидается

Этот срез **заменяет предыдущий замороженный снимок**. Main расширил реализацию общего `CustodyBytes`, изменил `Tree.h`, два v1 byte-consumer cleanup/CopyTo участка и тесты. Предыдущие полный Release 41/41, portable 39/39, VS/CoreTests и app hash остаются сообщёнными результатами прежних байтов, не подтверждением этого нового исправления. Reviewer по-прежнему только читает исходники и пишет данный отчёт.

### Что подтверждено в новой реализации `CustodyBytes`

`ProtectedCustodyCodec.h:17–37` теперь содержит узкий `final` производный от прежнего `std::vector<uint8_t, CustodyAllocator<uint8_t>>`, без нового allocator, бюджета, key/cryptography/lifecycle. Inherited count/range/list constructors сохраняют обычные операции. Default и move constructors явно создают Base через потенциально бросающий count ctor `Base(size_t{0})`; move затем выполняет member `swap` для equal stateless allocator. Если новый proxy не помещается, исходный **байтовый буфер** ещё не перенесён. Поддерживаемые `std::optional` и физические/codec result transfers теперь могут вернуть `bad_alloc` существующим catch вместо `terminate`. `Tree.h:11` больше не принуждает move внешнего результата быть `noexcept`.

Move assignment проверяет self-move до wipe, стирает прежние live bytes назначения и вызывает stateless Base move assignment, не создавая новый proxy. Default copy construction/assignment сохраняют обычную семантику vector. Destructor выполняет volatile wipe существующих live bytes перед Base deallocation; это также стирает временный plaintext в `nativeTransform`/codec return expressions, если следующая optional/result construction бросит до создания caller-side `WipeBytes`. Повторный wipe на нормальных путях безопасен. Это **live-byte** гарантия, не обещание автоматически стирать capacity tail после произвольных inherited `clear/resize/assign` операций; в просмотренных cleanup-путях перед уменьшением size есть явный wipe. Нет удаления через Base pointer в проверенной цепочке; это не полиморфная иерархия.

TreeTests добавляет `static_assert(!is_nothrow_move_constructible_v<CustodyBytes>)` и такой же assert для `PackedPlainRead`. `exactFitReturnRefusal` измеряет текущую proxy charge; ZERO оставляет payload+один proxy, physical read — 128 bytes+два proxy; следующий result transfer должен отказать под удерживаемым Guard. Проверяются отсутствие результата, sticky same cause до/после снятия давления и итоговое равенство charge. При Release proxy charge=0 эти именно Debug-сценарии явно пропускаются. Есть isolated `--exact-fit-zero` / `--exact-fit-physical` и вызовы обоих из нормального native main.

Main сообщил native RED до исправления: session `72885`, build EXIT 0, isolated `--exact-fit-zero` EXIT 3, без CRT-диалога. Это воспроизведение **от main**, не от reviewer. На момент этого промежуточного раздела Debug GREEN session `97565` ещё выполнялся; позднее полученный результат и его ограниченная идентичность записаны в финальном разделе ниже.

### Исходные пробелы M1/M2 устранены в новых тестах; запуск нового снимка пока не подтверждён

OwnerTests 553 строки, SHA ниже. Memory baseline теперь снимается **до** `treeGuardFaults()` (503–506), после вызова есть equality assert и отдельное успешное получение всех 4 jobs / 32 pins (508–511). Это прямо исправляет прежний остаточный M1 cleanup baseline. До исполнения это подтверждение исходного кода теста, не собственного наблюдения освобождения ресурсов.

В final-metadata wrapper (74–106) verifier удерживает свой job и тот же mutex; два probe jobs успешно резервируются, третий больше не проходит, лишь когда добавился фактически admitted publisher. Atomic flags проверяют, что publisher не завершён до fault. Publisher (456–479) ограниченно повторяет только pre-mutex admission refusal без disk effect, чтобы временный sampling probe не стал причиной неверного результата; затем требуются observed admission, exact same error/nativeError, notPublished и ноль writes/flushes. Readiness теперь не подменяет вход в операцию. Это прямо исправляет остаточный M2 deterministic overlap. g2/g3/g4 pinned-read тест сохраняется. Прежние MEDIUM M1/M2 как дефекты покрытия не считаются повторно; оставлены только два execution markers до подтверждения новых тестовых байтов.

### Узкая проверка совместимости v1 consumers

По отдельному запросу main просмотрены изменения `ProtectedCustodyReader.cpp` и `ProtectedCustodyWriter.cpp`, а не принят весь v1.

`ReadCache::clear()` и `State::clearDirty()` больше не конструируют пустой `CustodyBytes` внутри `noexcept` cleanup. Сначала стираются live bytes, затем `clear()`, потом `shrink_to_fit()` с обработкой `bad_alloc`. В проверенной MSVC реализации empty shrink идёт через `_Tidy` без нового proxy; если иной STL не освобождает storage, оставшаяся capacity продолжает учитываться прежним allocator. В `CopyTo` buffer/Wipe construction теперь внутри существующего try; ошибки возвращаются через прежний failure path. Self-move guard в byte-wrapper присутствует. Источник истины ledger, wire, migration, authority и лимиты не меняются.

### H2 — first-use cache allocation всё ещё возможна в деструкторе reader

Точные участки: `ProtectedCustodyReader.cpp:17,26,36–39,208–224`. `ReaderState::~ReaderState()` вызывает `cache()`, где `static ReadCache value` включает default-constructed charged `CustodyBytes`. Factory до создания ReaderState кеш не инициализирует. В новом процессе можно открыть reader, не вызывать Read/Seek, затем при полном owned budget освободить последний reader: первая cache construction бросает из implicit-noexcept деструктора и заканчивается `terminate`. Такой же путь возможен при неудаче последующего `new Reader` после создания state. Устранение allocate-on-clear и перенос CopyTo buffer в try этот first-use path не закрывают.

Минимальное исправление: инициализировать **существующий** cache под factory try до создания ReaderState либо сделать destructor cleanup без first initialization. Не требуется второй кеш или новая схема владения. Regression должен быть cold-process Release-before-first-Read при charged pressure, потому обычные тесты, уже создавшие кеш, этот случай скрывают. Это источник HIGH, найденный при явно запрошенной совместимости; собственного native abort для H2 reviewer не запускал. Это не утверждение whole-v1 acceptance и не замечание о v1 metadata authority.

### M3 — failed result move переносит pin/proof раньше потенциально бросающего bytes

Точные участки: `Tree.h:6–13`, `Tree.cpp:12,162`; у implicit move `PackedCipherRead` (`Owner.h:10–15`) тот же порядок owner/pin-before-bytes. Default member-wise move сначала переносит pin и proof, затем вызывает новый potentially throwing `CustodyBytes` move. При отказе proxy буфер источника остаётся целым, но уже созданные destination proof/pin уничтожаются во время constructor unwind. Деструктор внешнего `PackedPlainRead` в этой ветке **не вызывается**, потому объект не достроен. Wipe byte-wrapper сработает только при более позднем уничтожении исходного буфера.

Конкретный retained-result случай: получить PlainRead; отпустить исходные Tree/Owner ссылки, оставив proof только в результате; заполнить оставшийся бюджет; попытаться move результата и поймать `bad_alloc`. Source bytes остаются live, source pin/proof уже перенесены, а временные destination ownership members освобождены. Тем самым wipe-before-last-owner/pin не обеспечен для failed result transfer. В guarded `readBlock` return сам Guard дополнительно удерживает physical owner до catch/cleanup — поэтому этот путь не следует ошибочно описывать как немедленный owner close внутри каждого guarded return. Но гарантии жизненного цикла **retained result** это не заменяет и raw moves не становятся logical proof authority.

Минимальное условие исправления: потенциально бросающее создание destination bytes должно завершиться до переноса pin/proof, либо отказ должен полностью сохранить прежнее владение. Не резервировать лишний process pin ради move при cap32. Можно использовать явный result move с первоначально пустым token holder и nonthrowing token/storage transfer после успешной подготовки; конкретное локальное решение остаётся за main. Test failure должен проверить сохранение исходного owner/pin и plaintext cleanup order, не только `allocationFailed` общего guarded return. Источник MEDIUM; собственного runtime этого failed retained-result move reviewer не выполнял.

### Идентичность нового среза

HEAD по-прежнему `99b00a579c24b50e320465b69d9a296038bc544d`. SHA-256, пути относительно review worktree:

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.h | `43c62045f7f31a14127e74310ba09cbead0dffb6272343fc968178401cd4e68b` |
| apps/windows/RecApp/Storage/ProtectedCustodyMemory.h | `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.h | `5e6bc4fa096c13d3e247be5e6bc581fcc6bfb8cb0f697815d584db416943be85` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp | `11e54696cff69e2421ca312a9e351476cc4979a03f60a5e9bee1e17427b0559f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.h | `0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.cpp | `bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h | `11f4253afe0726781f8319315ba2c707571ac574f23c55aa9b2cf5ce2e0faae6` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `01ea3672a46cda99e7dffabc30641468de133c77edd30af23b9fa26b534c8bff` |
| apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp | `f8e54ccb3d39ab42803a05be36716b982b1b4e49798f1550df569d978205a676` |
| apps/windows/RecApp/Storage/ProtectedCustodyWriter.cpp | `a9a78170945687c4ef8ce58f31960ec2f673190bdfa6bc251a5b5742689cbaa0` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp, 689 строк | `60c2e2d6db44b0aea6b3d13acce5afee3e3e13ec336f90eca4218630d26d8b3e` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp, 553 строки | `9201c6c995c21a7f7bc72300b4dc7d7d50d2363fb9494f6a35fee73ec59f1bd7` |

Итог этого промежуточного среза: **source C=0 / H=1 (H2) / M=1 (M3)**. H1 corrected-in-source; состояние исполнения уточнено в финальном разделе ниже. Старые M1/M2 test-source gaps исправлены. Отметки: **10 checked / 4 unchecked** — H2, M3 и два execution markers. Только этот отчёт изменён reviewer; никаких source/test/VM/GitHub/app/inventory действий не выполнялось.

## Финальная проверка текущих 14 файлов — 2026-10-03

Независимая проверка **исходников завершена** без ожидания VM. Branch `codex/200-windows-followup`, HEAD `99b00a579c24b50e320465b69d9a296038bc544d`; dirty/untracked implementation сохранена. Ниже лично снятые SHA-256 финального canonical-набора: 3 файла сборки, 9 файлов реализации и 2 файла тестов. Неизменённый `ProtectedCustodyMemory.h` прочитан как зависимость, но не является пятнадцатым изменённым файлом этого набора. CMake/VS включение соответствующих исходников проверено по файлам сборки; это не собственный запуск компилятора.

| Файл относительно review worktree | SHA-256 |
| --- | --- |
| apps/windows/CMakeLists.txt | `b659c852c0c66e455238230b1b05d52292fadf09925ef294e6f322c3a5247b6d` |
| apps/windows/RecApp/GrafWindowsApp.vcxproj | `2949fea918a96cad9b4de63d485ab6a0b0c1c35bb66af5e75f43689f0eba7b72` |
| apps/windows/Tests/GrafWindowsCoreTests/GrafWindowsCoreTests.vcxproj | `c53d070bbb0bae3f4262a875e593a56c3ff28847c5dec19e176d87d3e20d5df4` |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.h | `43c62045f7f31a14127e74310ba09cbead0dffb6272343fc968178401cd4e68b` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.h | `5e6bc4fa096c13d3e247be5e6bc581fcc6bfb8cb0f697815d584db416943be85` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp | `11e54696cff69e2421ca312a9e351476cc4979a03f60a5e9bee1e17427b0559f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.h | `0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.cpp | `bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h | `11f4253afe0726781f8319315ba2c707571ac574f23c55aa9b2cf5ce2e0faae6` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `01ea3672a46cda99e7dffabc30641468de133c77edd30af23b9fa26b534c8bff` |
| apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp | `f8e54ccb3d39ab42803a05be36716b982b1b4e49798f1550df569d978205a676` |
| apps/windows/RecApp/Storage/ProtectedCustodyWriter.cpp | `a9a78170945687c4ef8ce58f31960ec2f673190bdfa6bc251a5b5742689cbaa0` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp (689 строк) | `60c2e2d6db44b0aea6b3d13acce5afee3e3e13ec336f90eca4218630d26d8b3e` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp (553 строки) | `9201c6c995c21a7f7bc72300b4dc7d7d50d2363fb9494f6a35fee73ec59f1bd7` |

Протокол `windows-protected-packed-custody.md` не менялся: SHA-256 `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed`. Reviewer не меняет принятые version bounds: cold refs ограничены descriptor generation и physical child-before-parent; дополнительный `child.version <= parent.version` не превращён в неподтверждённый нормативный blocker. Future live delta chronology не принимается этим review.

### Текущие C/H/M и точечные действия

**C=0 / H=1 / M=1; REQUEST CHANGES.** Вышеописанные H2 и M3 остаются в точных байтах этой таблицы:

- **H2, Reader.cpp:26,36–39,208–225.** `ReaderState` может существовать до первого `cache()`; его implicit-noexcept destructor впервые создаёт cache и charged Debug proxy. При исчерпанном бюджете обычный Release до первого Read/Seek или unwind создания Reader заканчивается `terminate`, а не обработкой `bad_alloc`. Минимальное исправление: подготовить существующий cache под factory `try` до создания любого ReaderState либо не создавать cache при cleanup. Проверка: отдельный холодный процесс, open без Read/Seek, давление бюджета, Release/unwind без abort. Это вывод по исходникам, не собственное native воспроизведение.
- **M3, Tree.h:6–13.** Default member-wise move переносит pin/proof до potentially throwing bytes ctor. При его отказе partial destination освобождает владение, а source сохраняет live plaintext уже без прежнего pin/proof. Конкретный случай — сохранённый PlainRead, единственная ссылка на proof, затем failed move под давлением. Подготовка bytes должна предшествовать переносу владения либо отказ полностью сохранять source ownership; не вводить лишний pin при cap32. Проверка должна наблюдать исходные owner/pin и wipe-before-release при failed retained-result move. Guarded read-return отдельно удерживает physical owner; утверждение о раннем закрытии owner на каждом return не делается. Аналогичный raw ciphertext member order отмечен выше, без присвоения raw result логической proof authority.

H1 устранён по исходникам общей потенциально бросающей byte-wrapper границей и live-byte wipe; self-move guard и Reader/Writer cleanup/CopyTo изменения прочитаны. Это не приёмка всей v1 реализации. M1/M2 прежние test-source gaps устранены: baseline до guard cases, повторный admission 4 jobs/32 pins, наблюдение действительно admitted publisher под удерживаемым mutex, bounded retry и проверка same-cause/no-effects. Новых C/H/M в этих тестовых изменениях не установлено. Их финальное native исполнение остаётся отдельной проверкой.

### Выполнение: только сообщения main, не наблюдения reviewer

| Срез / запуск | Полученное сообщение | Допустимый вывод |
| --- | --- | --- |
| До wrapper, session `72885` | Native Debug build EXIT 0; isolated exact ZERO EXIT 3, без CRT-диалога | Сообщённый main RED для H1 до исправления |
| Промежуточный wrapper, session `97565` | Build EXIT 0; isolated exact ZERO EXIT 0; isolated exact physical EXIT 0 | Сообщённый main RED→GREEN для H1; **до self-move guard и Reader/Writer compatibility изменений**, не финальный freeze |
| Текущий canonical, portable session `76810` | Полный portable 39/39 PASS, 71.06s; main связал его с текущими Codec.h/Tree.h/OwnerTests/TreeTests hashes | Новый сообщённый portable результат; native Debug proxy/Windows ветки этим не подтверждены |
| Финальный canonical → mirror → native, session `97281` | Копирование 14 файлов и Debug focused 2 / полный Release 41 / VS объявлены выполняющимися | **PENDING**: финальных результатов на момент завершения этого отчёта нет |
| Старый pre-wrapper freeze | Прежние native 41/41, focused Debug 2/2, portable 39/39, VS/CoreTests EXIT 0 и app SHA записаны выше | Только исторические receipts; на новые bytes **не переносятся** |

Reviewer не запускал native/portable tests, не наблюдал VM/runtime и не проверял зеркальную/нативную копию самостоятельно. Таблица SHA фиксирует лично прочитанный local canonical. Текущая checklist остаётся **10 checked / 4 unchecked**: два исходных дефекта H2/M3 и два native execution markers M1/M2. Portable PASS и промежуточный H1 GREEN не закрывают эти markers.

Границы неизменны: factory даёт только current-pair proof; normal application consumer adoption, старый v1 flat index, полный writer/retained-metadata/migration/GC pipeline и T116 целиком этим исправлением не принимаются и не добавлены как искусственные C/H/M. Reviewer изменил **только этот отчёт**; source/tests/build files, contract/tasks, GitHub/commit, inventory/VM/application state не менялись.

## Финальный bounded recheck текущих байтов и focused receipts — 2026-10-03

Main сообщил совпадение всех 14 current canonical hashes с mirror и native (session `92984`), focused Debug Owner+Tree build EXIT 0 и **2/2 PASS 5.38s**: Owner 1.56s / Tree 3.70s (session `30616`). По сообщению main в этот запуск входят новый baseline/resource cleanup, admitted-contender checks и оба exact-fit случая из TreeTests main. Reviewer заново сверил все 14 локальных файлов с SHA-256 в финальной таблице выше: **14/14 OK**, без смены branch/HEAD. Tree.h и Reader.cpp перечитаны; H2/M3 по-прежнему присутствуют в этих же байтах.

**Закрыты H1 и исходные coverage findings M1/M2.** Основания: личная проверка исходников исправления/тестов плюс явно атрибутированный текущий native PASS от main. Это не собственный запуск, не личное наблюдение VM/runtime и не перенос результатов старого снимка. Новый portable 39/39 PASS 71.06s также остаётся сообщённым результатом main.

Повторная проверка по последнему запросу ограничена этим же 14-file cohort, без повторного анализа предыдущих queued snapshots. Сохранившихся H1/M1/M2 в текущих байтах не установлено:

- H1: `Codec.h:21–35` — throwing default/move preparation, swap до transfer completion, live-byte wipe и self-move guard; `Tree.h:11` — без outer noexcept. `TreeTests:21–22,532–569,679–680` — static traits, измеренная proxy charge, exact ZERO/physical refusal и оба вызова из main.
- M1: `OwnerTests:503–511` — baseline до всего `treeGuardFaults()`, charged-byte equality после него и повторный admission всех 4 jobs / 32 pins.
- M2: `OwnerTests:80–103,441–480` — два admitted probes и отказ третьего при реально удерживаемом publisher job, bounded retry конкурента, затем same-cause / reads3 / writes0 / flushes0. Readiness event не выдаётся за admission.

H2 (`Reader.cpp:26,36–39,208–225`) и M3 (`Tree.h:6–13`) отдельно перечитаны в текущем canonical и не изменились. Они не являются оставшимися H1/M1/M2 и не получены из старого снимка. Никакого нового дефекта сверх этих двух в данном bounded recheck не заявлено. Таблица 14 SHA-256 выше повторно проверена: все строки OK; protocol SHA также неизменён.

**Source C=0 / H=1 (H2) / M=1 (M3), REQUEST CHANGES; checklist 12 checked / 2 unchecked.** Наличие успешного focused набора не доказывает first-use Reader cache cleanup или failed move сохранённого PlainRead: этих отдельных сценариев имеющиеся tests не закрывают. H2 требует подготовки существующего cache до ReaderState под factory try либо cleanup без его создания. M3 требует исключить перенос ownership до потенциально бросающей подготовки bytes либо сохранить прежнее владение при отказе; дополнительный admission pin не требуется. Точные участки и минимальные регрессии остаются описанными выше.

Full native Release session `14326` по сообщению main выполняется; **VS ещё не run**. Старый pending session `97281` выше — историческое состояние, не текущий статус focused Debug. Полный Release/VS здесь не объявлены успешными и не ожидаются для выдачи конкретных H2/M3. `Appendround219validation` draft указан main как сохранённый; reviewer его не менял и не использует сам факт наличия draft как test receipt. Ограничения current-pair proof, отсутствие application adoption и неприёмка v1 flat index/full pipeline сохранены. Изменён только этот review report.

## H2/M3 приняты main: минимальный план, не закрытие исправлений — 2026-10-03

Main принял H2/M3 и сообщил план локальных исправлений. Reviewer проверил план по текущим конструкторам/деструкторам, без изменения product/tests:

- **M3 PlainRead:** порядок полей bytes → pin → proof обеспечивает выполнение potentially throwing byte move до nonthrowing переносов pin (`Memory.h:43`) и shared_ptr. Если подготовка bytes отказывает, source bytes и source ownership ещё не перенесены. Имеющееся тело `PackedPlainRead::~PackedPlainRead()` создаёт локальный `WipeBytes`, который уничтожается до member destruction, поэтому wipe plaintext остаётся раньше proof/pin release даже при новом обратном порядке уничтожения полей. Дополнительный pin admission/null-token API/registry не требуется. Проверка retained-result failed move должна наблюдать не только weak proof/root, но и сохранение исходного bytes/ownership и pin quota после отказа.
- **M3 CipherRead:** bytes-first аналогично сохраняет source owner/pin при отказе byte move. Единственный aggregate initializer `Files.cpp:852` должен соответствовать новому порядку. При implicit destructor обратный порядок будет owner → pin → bytes, поэтому прежний комментарий `Owner.h:11` «bytes, actual guard, then result pin» станет неверным и должен быть скорректирован. Здесь ciphertext, не plaintext/proof; это замечание к точности комментария/заявленной семантики, не новый C/H/M и не требование нового abstraction.
- **H2:** инициализация существующего cache после успешного Pin admission, до open files / создания ReaderState, внутри factory try — достаточный минимальный source fix для найденного first-use destructor allocation. Cold-process successful open без Read/Clone → raw budget pressure → drop stream непосредственно проверяет эту ветку. Тест должен подготовить собственный charged pressure buffer до полного исчерпания бюджета, чтобы RED относился к cache initialization, а не к setup proxy allocation.

**План согласуется с локальными условиями исправления; H2/M3 пока НЕ закрыты.** Новые product/test hashes и post-fix результаты ещё не представлены. Current source verdict до фактического исправления остаётся C=0 / H=1 / M=1, checklist 12/2. Исходники на момент чтения ещё имеют прежние pin/proof-before-bytes и first-use cache в ReaderState destructor.

Дополнительно main сообщил полный native Release **41/41 PASS 42.72s**, session `14326`, и VS session `5605`: build EXIT 0 / CoreTests EXIT 0, app SHA prefix `93de13…`. Это сообщения main для **pre-H2/M3-fix** среза; prefix не выдаётся за полный проверенный SHA-256. Они не подтверждают будущие перестановку полей/cache initialization и не закрывают H2/M3. Reviewer тесты/VS/VM не запускал. Scope и владение единственным report file не расширены.

## Actual H2/M3 fixes: финальная независимая source-проверка — 2026-10-03

**Bounded source verdict: PASS, C=0 / H=0 / M=0; fresh runtime receipts pending.** Branch `codex/200-windows-followup`, HEAD `99b00a579c24b50e320465b69d9a296038bc544d`. Новые шесть предоставленных SHA лично совпали с canonical; девять остальных файлов лично сверены с прежней таблицей без изменений. Получается **15 файлов**, поскольку FilesTests добавлен к прежнему 14-file cohort. Нет утверждения о самостоятельной проверке mirror/native этого нового cohort.

### Исправления и failure cleanup

**H2 — CLOSED IN SOURCE.** `Reader.cpp:212–215` резервирует pin, проверяет admission, затем вызывает `(void)cache()` внутри factory try до открытия native files и до единственного создания ReaderState (`224–226`). Отказ cache/proxy preparation попадает в factory bad_alloc catch (`228`), когда ReaderState ещё не существует. После успешного создания ReaderState cache уже инициализирован; его first-use allocation больше не может возникнуть из destructor. Cache остаётся существующим process-lifetime объектом: proxy charge не отключается, не исключается из бюджета и не объявляется утечкой закрытого reader.

**M3 — CLOSED IN SOURCE.** `Tree.h:7–14` и `Owner.h:10–16` объявляют bytes перед pin/proof/owner. Default move выполняется в порядке объявления: потенциально бросающий byte count/proxy ctor первым, затем nonthrowing CustodyPin/shared_ptr moves. Если byte preparation бросает, source buffer и source ownership не перенесены, освобождать destination pin/proof ещё нечего. При успешной byte preparation оставшиеся moves не бросают. `Files.cpp:852` — единственный aggregate initializer — обновлён в bytes-first порядке; result pin admission остаётся до count construction и под прежними mutex/job/try (`838–866`). Не введён дополнительный pin/null-token API/swap registry.

`Tree.cpp:12` сохраняет явное тело PlainRead destructor с локальным `WipeBytes`. Этот локальный guard стирает plaintext при завершении тела, **до** reverse member destruction proof → pin → bytes; последующий CustodyBytes destructor повторно стирает live bytes перед deallocation. Поэтому normal wipe-before-owner/pin release не потерян при перестановке. CipherRead не содержит plaintext/proof: owner/pin могут уничтожаться раньше ciphertext storage, а storage остаётся charged до фактического освобождения. Его комментарий теперь описывает сохранение владения при failed move и charge lifetime, не обещает прежний порядок уничтожения. Raw result/move по-прежнему не logical proof authority.

### Новые regression sources

**FilesTests:1141–1196,1395–1401,1420.** `coldCacheClose()` — первый reader/cache сценарий normal native main и отдельный `--cold-cache-close` процесс. Fixture создаёт/публикует валидные bytes без Read/Clone, затем reader успешно открывается. RawPressure использует непосредственно charged allocator, без дополнительного vector proxy, доводит owned bytes до точного лимита и закрывает stream. Assert проверяет отсутствие native content effects и cleanup baseline с единственной process-lifetime cache proxy charge. На STL без proxy явно указывается, что это close-only/SKIP allocation-fault relevance, а не Debug fault acceptance. Test source соответствует H2; post-fix PASS пока не получен.

**TreeTests:571–618,707–708,732–734.** `retainedMoveKeepsCustody` покрывает PlainRead и CipherRead: result — единственный оставшийся strong custodian, raw pressure оставляет 0 headroom, move ожидаемо бросает, source pin и proof/owner остаются, weak lifetime не истекает, bytes сохранены, внешний writer отказан. Точные remaining pin quotas 29/30 и следующий refusal проверяют отсутствие потерянного/дополнительного admission. После снятия давления retained proof/owner снова читает успешно; после result release weak lifetime истекает и charge возвращается к baseline. Plain bytes проверены на equality сразу после отказа; cipher bytes — size сразу и equality при последующем reread. Debug relevance условна наличием измеренной proxy charge. Test source соответствует M3; post-fix PASS пока не получен.

H1 safe CustodyBytes и существующие exact-fit tests сохранены; OwnerTests baseline/admitted-contender исходники не изменились. Прежние M1/M2 test-source gaps не возобновлены. Новых доказанных C/H/M в этих локальных production/test изменениях не найдено. Scope не расширен до whole-v1/flat index/full T116/integration/application readiness.

### Точные актуальные SHA-256 (пути относительно review worktree)

| Файл | SHA-256 |
| --- | --- |
| apps/windows/CMakeLists.txt | `b659c852c0c66e455238230b1b05d52292fadf09925ef294e6f322c3a5247b6d` |
| apps/windows/RecApp/GrafWindowsApp.vcxproj | `2949fea918a96cad9b4de63d485ab6a0b0c1c35bb66af5e75f43689f0eba7b72` |
| apps/windows/Tests/GrafWindowsCoreTests/GrafWindowsCoreTests.vcxproj | `c53d070bbb0bae3f4262a875e593a56c3ff28847c5dec19e176d87d3e20d5df4` |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.h | `43c62045f7f31a14127e74310ba09cbead0dffb6272343fc968178401cd4e68b` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.h | `7209dbfb5a8ba40e0f3afe9032a6bc8d15c2a70b71e54868b518a6fe5edcd586` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp | `11e54696cff69e2421ca312a9e351476cc4979a03f60a5e9bee1e17427b0559f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.h | `0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.cpp | `bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h | `ac096cb8521e1c818b70c0a8147f4b93661b434fa117068149286ea4c7412b75` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `b29146e86800531c0ef3447fb32bd7846fc17214c418abe5bf5d2e83a7af1825` |
| apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp | `59a72176bff303c5abb34a352015a755481766126f8ff7c5c84c04607f7ab7d9` |
| apps/windows/RecApp/Storage/ProtectedCustodyWriter.cpp | `a9a78170945687c4ef8ce58f31960ec2f673190bdfa6bc251a5b5742689cbaa0` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp (742 строки) | `59e976433e56856c18ffb88090387204c472a2991ab92c901d29450258d00c3e` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp (553 строки) | `9201c6c995c21a7f7bc72300b4dc7d7d50d2363fb9494f6a35fee73ec59f1bd7` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp (1590 строк) | `035a814baef511f89a9e584bbff1c011bd92d0cbc285f1f68502bb5aefa9e9be` |

Accepted contract unchanged: SHA-256 `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed`. Cold version bounds не изменены; дополнительный parent.creation-version bound не добавлен и future delta authority не принят.

### Receipts и текущие markers

Main сообщил **pre-fix RED**: H2 isolated Debug `--cold-cache-close`, session `92400`, build EXIT 0 / test EXIT 3, measured proxy 16B; M3 isolated plain/cipher moves, session `81073`, build EXIT 0 / оба EXIT 3 на assertions о потерянном владении. Это сообщения main, не личное runtime наблюдение reviewer. **Fresh post-fix native/portable runs ongoing: результатов пока нет.** Все прежние focused/full native, portable, VS и app receipts относятся к до-H2/M3-fix срезу и на новую таблицу не перенесены.

Checklist readback: **14 checked / 2 unchecked**. H2/M3 закрыты как source defects; две оставшиеся отметки — только fresh native execution markers для cold close и retained moves. Нет открытых C/H/M или требования ждать full native/VS ради source verdict. Reviewer не запускал tests/build/VM, не менял source/tests/spec/tasks/contract или другие отчёты. Изменён только этот report.

## Post-fix session 44460: isolated GREEN, full Debug failure — НЕ ЗАМОРОЖЕНО

Main сообщил: Debug targets build EXIT 0; `--cold-cache-close` EXIT 0, measured charged proxy 16B / cleanup 16B; isolated retained-plain/cipher moves оба EXIT 0; focused Owner/Tree PASS. Вместе с source inspection это закрывает targeted H2/M3 regressions. **Это receipts от main, не reviewer runtime observation.**

Тот же main сообщил **полный Debug FilesTests FAILED EXIT 3**, без assertion text после успешного cold-cache сценария. Причина пока неизвестна и диагностируется main. В результате общий native acceptance **НЕ завершён**; focused/isolated GREEN не выдаётся за полный suite PASS. Reviewer не запускает диагностику/VM и не меняет тесты. Без установленной причины новый C/H/M не придумывается; source вывод по двум исправлениям не отменяет открытый full-sequence failure.

Main временно добавляет phase stderr markers в FilesTests. Личная повторная hash-проверка установила: остальные **14/14** entries последней таблицы совпадают; FilesTests уже **не** `035a814baef511f89a9e584bbff1c011bd92d0cbc285f1f68502bb5aefa9e9be`. Наблюдавшийся diagnostic hash — `3f144c310e0336ab8f2a7abd013f6f2de5ca9ea3160c56de5ff2d8794242358b`, исключительно промежуточная идентичность, **не frozen/review-approved test SHA**; возможны дальнейшие изменения. Предыдущая 15-file table остаётся идентичностью прочитанного pre-diagnostic regression cut, не утверждением о текущем FilesTests.

Portable session `81661` по сообщению main ещё выполняется; результат не утверждается. **Не замораживать отчёт** до выяснения полного Debug failure и стабильной идентичности тестов/receipts. Текущие marks: **16 checked / 2 unchecked** — full Debug FilesTests failure и final identity/validation freeze открыты. Source findings H1/H2/M3 и исходные coverage findings M1/M2 закрыты в указанном bounded scope; overall native/integration/application readiness не приняты. Изменён только этот working report.

## Metadata count-ctor candidate и общий entries boundary — рабочий source follow-up

Main явно добавил в scope точную allocation/move проверку Metadata.cpp candidate и рассмотрение общей узкой политики для charged bytes/entries. Reviewer прочитал текущий candidate, непосредственно связанные type definitions, codec/snapshot returns и Writer State construction; product/test/spec/task/VM не менялись. **C=0 / H=1 (H3) / M=0, не заморожено.** Это не повторный полный v1/flat-index audit и не новый full-T116 gate.

### Локальный Metadata.cpp fix: корректен, но ограничен

`Metadata.cpp:46–49` создаёт entries через явный `std::vector<...>(size_t{0})`, а затем reserve. В проекте C++17; same-type prvalue инициализирует aggregate member непосредственно, **без отдельного vector move** в этом initializer. Не следует ошибочно приписывать этой строке ещё один noexcept move/proxy allocation. Первичный источник: C++ draft `[dcl.init]` same-type prvalue rule, `https://eel.is/c++draft/dcl.init`.

Для заданного main measured proxy p=16B вывод по исходникам таков: headroom0 → count-ctor отказывает и выходит в `bad_alloc` catch; headroom16 → empty entries proxy помещается, reserve как минимум одного CustodyIndexEntry требует дополнительную storage charge и отказывает через тот же catch. В обоих случаях native open ещё не вызван (`52`), lease отсутствует, `reject` сбрасывает pin (`21`), локальные candidate/dirty/lock корректно освобождаются. Предполагается отсутствие параллельного изменения synthetic budget; это static boundary analysis, **не reviewer runtime** и не полученный native 16B-case PASS. Текущий metadata pressure test (`FilesTests:813–819` на последнем чтении) сначала создаёт свой CustodyBytes, затем reserve remaining; тем самым собственный Debug proxy не включается второй раз в заранее вычисленный count. Он доказывает headroom0, но не headroom=p.

### H3 HIGH — обычный entries vector сохраняет unsafe default/move

Общий тип всё ещё `Codec.h:53–57`: `std::vector<CustodyIndexEntry, CustodyAllocator<...>> entries`. Microsoft STL source показывает charged-proxy allocation внутри noexcept default и noexcept move constructor; outer try не может поймать такой отказ. Это тот же concrete Debug механизм, ранее устранённый для bytes, без утверждения о дефекте стандартного Release allocator. Первичный источник лично прочитан: `https://raw.githubusercontent.com/microsoft/STL/main/stl/inc/vector`, default/count/move/move-assignment участки 653–663,740–805.

Доказанные прямые участки:

- `Writer.cpp:33,145`: State содержит default CustodyIndex candidate; make_unique<State>() под function try всё равно вызывает unsafe entries default ctor. При заполненном charged budget он terminate, а не возвращает allocationFailed. Это source-confirmed путь; точный abort main's нового writer trace не объявляется установленным только по фазовой отметке.
- `Codec.cpp:206`: openIndex по-прежнему использует `CustodyIndex{generation,length,{}}`; count-ctor в Metadata не меняет его entries default. `213` передаёт index в optional через noexcept entries move.
- `Files.cpp:506,550–554` и `Metadata.cpp:109`: index/snapshot moves далее конструируют entries vector внутри value/optional. Ранее успешные reserve и local candidate construction не гарантируют отдельной proxy headroom в каждом таком transfer. При отказе noexcept move остаётся terminate, а не normal error/ambiguous classification.

Один H3 отражает общий тип/механизм, а не отдельные blockers для каждого места. Current-pair packed proof не получает v1 index authority от этого review.

### Минимальная повторно используемая политика и cleanup условия

Общая узкая typed wrapper policy для **этих двух charged element types** оправдана: potentially throwing default через Base(size_t0); potentially throwing move через empty count preparation + member swap; stateless/equal allocator без новой proxy в move assignment; self-move guard. Заменить сам entries member type, а не только ещё один локальный initializer. Сохранить byte live-wipe guarantee; если wipe обобщается на T, ограничить его используемыми trivially-copyable types, не стирать произвольные nontrivial objects. Не менять allocator limits/proxy charges, не отключать Debug iterators, не вводить registry/allocator API или новые полномочия. Inherited constructors не должны давать bypass через unsafe Base default/move. Exact Metadata initializer должен соответствовать новому member type, иначе обещание same-type prvalue construction не переносится автоматически на Base→derived conversion.

**При внедрении throwing entries move обязательно проверить существующий MetadataCommit return boundary:** `Metadata.h:12,17–18` сейчас переносит pin/lease раньше optional snapshot; `Metadata.cpp:109–112` переносит engaged snapshot, а `reject` (`17–22`) вновь делает move всего result. Если новый entries move бросит, есть тот же ownership-before-throw риск, что был M3. Кроме того, error-return не должен повторно пытаться аллоцировать proxy для того же engaged snapshot: например, очищать failed snapshot до переноса error result, сохранять/blockWrites lease и правильную ambiguous state после publication. Это **условие безопасного внедрения предлагаемой политики**, не отдельный новый дефект несуществующего patch. Не полагаться на необязательный NRVO. Нет требования нового общего ownership abstraction.

Минимальное доказательство: измерить именно entries proxy p; выполнить отказ создания при 0 и p headroom (no native reads/writes/opens для Metadata pre-open cut), direct index/snapshot move при недостаточной новой proxy headroom (source неизменён), move assignment при 0 headroom (nonallocating для equal stateless allocator), затем production transfer/return cut с сохранением owner/pin и allocation-safe error result. Static traits для default/move entries, Index и Snapshot должны отражать throwing construction. RED/GREEN должен исходить из product boundary, не из pressure setup; old focused PASS и один metadata-phase PASS не закрывают H3 или полный sequence.

### Candidate identity и атрибуция результатов

Лично прочитанные SHA-256; это dependency/candidate evidence, **не финальная 16-file freeze**:

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp | `8ae8b8a35fd4f2fa90bc000725fefe711dbba0de56a20d00345fcc5691edad49` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h | `de7ba1eba3e7f26a28cb1b73461a42f4402f1f0c49adbe7e9ad1040e46af5cf0` |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.h | `43c62045f7f31a14127e74310ba09cbead0dffb6272343fc968178401cd4e68b` |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.cpp | `5372538eb3055c2b9a89786ef15089eb090e574025a3c0c030f87730873506c9` |
| apps/windows/RecApp/Storage/ProtectedCustodyWriter.cpp | `a9a78170945687c4ef8ce58f31960ec2f673190bdfa6bc251a5b5742689cbaa0` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `b29146e86800531c0ef3447fb32bd7846fc17214c418abe5bf5d2e83a7af1825` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp — diagnostic, changing | `de5d039625e82c14728b98fe2b014002b472d12711f0eb7bbeaaf1cbec55740c` |

FilesTests diagnostic hash менялся во время чтения; строки pressure-case также сдвигались. Ни тестовые markers, ни этот hash не объявляются окончательными. Main сообщил corrected-test metadata RED session `52392` EXIT3; local count-ctor candidate metadata phase passed session `99722`, затем writer phase failed, trace `16195` выполняется. Это **main receipts**, не reviewer наблюдение; metadata-phase success не является full Debug PASS. Production 16-file snapshot pending по сообщению main, portable final receipt не получен. Отметки **16 checked / 3 unchecked**: H3, полный Debug sequence, финальная identity/validation freeze. Изменён только report.

## Stable 16-file cut: свежая bounded source-проверка и clean Debug receipt

Лично сверены все 16 canonical файлов ниже, branch `codex/200-windows-followup`, HEAD `99b00a579c24b50e320465b69d9a296038bc544d`. Metadata.cpp `8ae8…` и FilesTests `5fed…` совпали с последними предоставленными main SHA; остальные 14 совпали с актуальным post-H2/M3-fix source cut. Проверены критические участки Tree DFS/read, exact EOF/Guard/catch, typed child bounds, bytes-first result lifetime, factory cache initialization, metadata count-ctor и test scopes. Этот local hash proof не выдаётся за лично проверенные mirror/native bytes; main теперь сообщает terminal verification `95206` SOURCE_MATCH16/16 и canonical/mirror183/183, дополнительно `13819` COMPILE_SOURCE_MATCH155/155.

### Что закрыто и что НЕ является текущим дефектом

H1/H2/M3 и исходные M1/M2 закрыты. Current-pair BOTH HEAD full DFS3, immutable same-owner proof, same physical mutex through DPAPI/catch/publication exclusion, exact EOF, all-child typed refs/SHA-before-DPAPI, EMPTY/ZERO/base/tail и pinned read после raw head updates не изменились. Current-pair proof не становится historical/logical commit/app/GC authority.

**Metadata.cpp:46–47 корректен.** Exact-type vector count-ctor prvalue прямо инициализирует aggregate member по C++17; отдельного noexcept intermediate move нет. Headroom0 отказывает в potentially throwing count construction; measured p=16B headroom позволяет empty proxy, но subsequent reserve entry storage отказывает в worker try до native open. Ранее H3 не следует читать как претензию к этому initializer. Native partial-p fault receipt отсутствует; static boundary analysis не объявляется выполненным тестом.

**FilesTests cleanup корректен по исходникам.** `326–356`: reservation создаётся прежде вычисления remaining, и вся pressure/proxy lifetime ограничена nested scope; owner release проверяет charge относительно ещё живого reservation, а baseline проверяется только после его уничтожения. `807–811`: metadata budget создаётся до remaining reserve. `1209–1222`: snapshot pressure снимается lexical scope, без создания нового empty temporary proxy под полным бюджетом. Отсутствие временных phase stderr / DbgHelp / set_terminate / stack hooks подтверждено поиском; штатные isolated-regression diagnostics не выдаются за временные hooks.

По сообщениям main trace `82252` показывал ctor в Writer clearDirty, хотя current source SHA `a9…` содержит wipe/clear/shrink, без такого ctor. Clean Debug rebuild `42537` исполнил owner-release case; последующее baseline assertion было test lifetime error — reservation proxy16B ещё был жив. Scope cleanup исправляет именно это. Reviewer **не использует stale stack или этот baseline RED как доказательство текущего product Writer defect**. Metadata corrected-test RED `52392` до count-ctor исправления остаётся отдельным валидным сообщением main; история не переписана в «все RED были ложными».

### Оставшийся H3: конкретный transfer в проверяемом Metadata worker

**C=0 / H=1 / M=0** для дополнительно запрошенной allocation/move compatibility проверки. `Metadata.cpp:109` делает `result.snapshot = std::move(*reopened.value)`; result.snapshot до этого disengaged, поэтому это **move construction**, не nonallocating assignment уже существующего entries vector. `CustodySnapshot → CustodyIndex → Codec.h:56 entries` всё ещё содержит обычный `std::vector<...,CustodyAllocator<...>>`. MSVC Debug vector move создаёт новый charged proxy внутри noexcept; если в этот момент меньше p свободных bytes, процесс terminate и `Metadata.cpp:112` catch не выполняется. Это source-confirmed механизм по текущему типу и STL, **не воспроизведённый reviewer runtime**, не причина исправленного stale Writer case и не промежуточный move count-ctor initializer.

Это непосредственно выполняемый return/adoption cut той же Metadata функции, а не future live delta/retained metadata/migration/GC gate. Общий entries риск за её пределами не используется для добавления отдельных blockers. Полный 3/3 проверяет имеющиеся cases, но новые tests не оставляют недостаточную proxy headroom именно перед snapshot/index move. Поэтому clean native PASS сам по себе не закрывает H3. Минимальное продолжение — безопасная default/move policy самого charged entries типа или эквивалентная локальная безопасная подготовка всех реально используемых transfers; доказать failed snapshot/index move под synthetic budget и allocation-safe error return. Условия MetadataCommit ownership/error-return при выборе throwing entries wrapper изложены выше; это не требование новой большой абстракции или приёмки full v1.

### Точная стабильная local identity (SHA-256)

| Файл относительно review worktree | SHA-256 |
| --- | --- |
| apps/windows/CMakeLists.txt | `b659c852c0c66e455238230b1b05d52292fadf09925ef294e6f322c3a5247b6d` |
| apps/windows/RecApp/GrafWindowsApp.vcxproj | `2949fea918a96cad9b4de63d485ab6a0b0c1c35bb66af5e75f43689f0eba7b72` |
| apps/windows/Tests/GrafWindowsCoreTests/GrafWindowsCoreTests.vcxproj | `c53d070bbb0bae3f4262a875e593a56c3ff28847c5dec19e176d87d3e20d5df4` |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.h | `43c62045f7f31a14127e74310ba09cbead0dffb6272343fc968178401cd4e68b` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.h | `7209dbfb5a8ba40e0f3afe9032a6bc8d15c2a70b71e54868b518a6fe5edcd586` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp | `11e54696cff69e2421ca312a9e351476cc4979a03f60a5e9bee1e17427b0559f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.h | `0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.cpp | `bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h | `ac096cb8521e1c818b70c0a8147f4b93661b434fa117068149286ea4c7412b75` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `b29146e86800531c0ef3447fb32bd7846fc17214c418abe5bf5d2e83a7af1825` |
| apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp | `59a72176bff303c5abb34a352015a755481766126f8ff7c5c84c04607f7ab7d9` |
| apps/windows/RecApp/Storage/ProtectedCustodyWriter.cpp | `a9a78170945687c4ef8ce58f31960ec2f673190bdfa6bc251a5b5742689cbaa0` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp | `8ae8b8a35fd4f2fa90bc000725fefe711dbba0de56a20d00345fcc5691edad49` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp (742 строки) | `59e976433e56856c18ffb88090387204c472a2991ab92c901d29450258d00c3e` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp (553 строки) | `9201c6c995c21a7f7bc72300b4dc7d7d50d2363fb9494f6a35fee73ec59f1bd7` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp (1594 строки) | `5fed021b71a3cddfdddcafa77a029ad32924c3712fc0bedf5f1aa8bfd32b06be` |

Accepted contract SHA unchanged: `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed`. No source/spec/task/contract/test/build/VM/GitHub changes by reviewer; only this report changed.

### Current receipts (attributed main only)

Clean Debug product build `42537`, final tests rebuild `91706`: **3/3 PASS12.26s**, full FilesTests7.99s / Owner1.15s / Tree2.99s. H2/M3 isolated GREEN `44460` also reported, and those regressions remain in normal test main. Main confirms terminal `95206` SOURCE_MATCH16/16 canonical/mirror/guest and whole canonical/mirror183/183; `13819` COMPILE_SOURCE_MATCH155/155 (`.cpp/.h/.hpp/.c/.rc/.vcxproj`, RecApp/Native/Tests); `8829` clean portable **39/39 PASS25.34s**; `10918` CLEAN native Release build EXIT0, full **41/41 PASS40.18s**. These are **main receipts**, not reviewer execution or live observation. Final VS Rebuild `95823` is ongoing and not accepted without its terminal receipt. Earlier portable `81661` 39/39 PASS24.60s belongs to the pre-test-fix15 cut and is not current16 acceptance. Earlier false-stale/full-Debug/test-baseline history is preserved with corrected attribution above.

Final source decisions: **bounded current-pair ACCEPTED, C/H/M=0/0/0**; separately requested Metadata allocation/move compatibility **H3 remains, C/H/M=0/1/0**. Checklist readback: **18 checked / 2 unchecked** — H3 and final VS Rebuild receipt. No proof/application adoption, whole-v1/full-T116, future live writer, integration, hardware or release readiness claim. Reviewer source verdict issued without waiting for final VS.

### Final readback: subsequent concurrent changes, not this receipt-bound cohort

During final checksum/readback after receipt reconciliation, FilesTests first changed from the reviewed/receipt-bound `5fed021b71a3cddfdddcafa77a029ad32924c3712fc0bedf5f1aa8bfd32b06be` (1594 lines) to `5d4536caf6966668fdf99a97178a97b56bc071238a4a9616d43cca31284e155f` (1617 lines). A following readback also detected Codec.h `4c54ab061870e730b596867c883b3d756e77509e5a9e256763a964f345d84251` and Metadata.cpp `739b40a5670227530554a9fc3c92a41a86c2b2577a1d9ac92c3ee118581dab74`; the other **13/13** table files still matched. These are observations of concurrent work, not additions to the reviewed/receipt-bound 16-file cohort. The visible new `writerOpenBudget()` pressure test/mode and Metadata error-return snapshot reset were read only to identify the delta, not to approve the new compatibility implementation. The table and terminal receipts above deliberately identify the requested frozen16 cohort with Codec `43c620…`, Metadata `8ae8…`, FilesTests `5fed…`. No old source approval or native/portable PASS is carried forward to new Codec/Metadata/test bytes; H3 is a finding against the reviewed cohort only, not an asserted surviving defect in the new implementation. No reviewer product/test edits occurred. Historical false-stale/full-Debug attribution remains preserved.

## Продолжение независимой проверки H3 — 2026-10-04, после ограничения range constructor

**Финальный узкий вывод: ACCEPTED IN SOURCE, C=0 / H=0 / M=0; H3 CLOSED.** Производственные Codec.ha5152a… / Metadata.h7d05cf… / Metadata.cpp739b40…, test accounting CodecTestsff3661… и Release applicability FilesTestse00d64cf… приняты по лично прочитанным исходникам. Текущий 18-file список: **17 checked / 1 unchecked**. Debug96206 4/4 PASS25.36, Release16265 41/41 PASS49.33, portable97843 39/39 PASS14.05, guest27786 COMPILE_SOURCE_MATCH155/155, host183/183, VS61697 REBUILD0, Core58899 EXIT0 и полный App EXE SHA приняты **на уровне receipts main**, не reviewer runtime. Полные пять текущих SHA и финальный readback ниже. Единственный unchecked — точное runtime исполнение engaged-snapshot worker error-return; это не новый HIGH, не blocker source approval и не full-T116 gate. Это ограниченное закрытие H3, не whole-pipeline readiness и не full-v1/T116/application/release acceptance. Прежние решения, таблицы, RED и GREEN выше сохраняют историческую область; промежуточные pending утверждения ниже заменены последующими terminal updates в конце.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`; branch `codex/200-windows-followup`; HEAD `99b00a579c24b50e320465b69d9a296038bc544d`, лично перепроверены. Dirty/untracked shared work сохранена. Режим — чтение исходников с записью только этого reviewer-owned отчёта. `code-reviewer` прочитан полностью; прочитаны ancestor/root AGENTS, guidance index, worktree/spec-kit-flow/product-gates, применимые validation/evidence правила, constitution и разделы FR-012/storage в spec/plan/tasks/quickstart/PRD/status. Никаких product/test/spec/task/build/VM/GitHub/commit записей или запусков reviewer не делал.

### Общая политика и сохранение байтов

`Codec.h:18–35,36–56,72–76`: `CustodyVector<T>` прямо конструирует `std::vector` через potentially throwing count ctor; move сначала готовит пустой Base и лишь затем делает member swap. `CustodyIndex::entries` теперь именно этот тип, поэтому policy применяется также к aggregate Index и Snapshot, Writer State и optional transfers. При отказе подготовки proxy source storage ещё не перемещён. Equal/stateless allocator (`Memory.h:85–108`) позволяет move assignment без новой proxy; self-move guard присутствует. Эти выводы проверены по первичным исходникам [Microsoft STL vector](https://github.com/microsoft/STL/blob/main/stl/inc/vector) и [xmemory](https://github.com/microsoft/STL/blob/main/stl/inc/xmemory), включая count construction, proxy rebinding и equal-allocator assignment. Это анализ реализации STL, не наблюдение текущего guest runtime.

`Codec.h:25–26` теперь исключает integral Iterator через `enable_if_t<!is_integral_v<Iterator>, int>`. `CustodyBytes(16,0)` выбирает count/value overload; обычные pointer/iterator ranges сохраняются. Ранее прочитанный unconstrained template и compile failure не выдаются за исправленный вариант. Header `a5152a…` совпал с точным SHA, предоставленным main, и повторным локальным чтением. Source-решение относится к этому исправлению; успешную `/W4 /WX` сборку должен подтвердить отдельный новый receipt.

`CustodyBytes` сохраняет byte-specific volatile live-byte wipe в destructor и перед move assignment; self-move не стирает source. Entries не получают байтовое стирание произвольных T. Это прежняя гарантия live bytes, без нового обещания очистки capacity tail после любых inherited resize/clear/copy operations. Прочитанные `Reader.cpp:18–24,140–172,208–228` и `Writer.cpp:43–51,136–162,227–263` сохраняют явное стирание до clear/shrink и прежние catch boundaries. ReaderState переносит snapshot до files; factory готовит cache до ReaderState. Изменение shared policy не возобновляет H2/M3.

Прямые потребители: `Codec.cpp:184–215` конструирует index и optional под bad_alloc catch; `Files.cpp:483–559` проводит candidate/snapshot transfers под function try и блокирует writes при allocation failure; `Writer.cpp:145–161` теперь может поймать отказ entries default construction; Reader snapshot preparation находится под factory try. Дополнительных C/H/M в этих narrowly inspected transfers не установлено. Это не полный v1 audit.

### CustodyMetadataCommit: подготовка, владение и возврат ошибки

`Metadata.h:12,21–30`: declaration order остаётся pin → lease → snapshot. В явном move ctor pin/lease сначала default-initialized без переноса; потенциально бросающий snapshot move выполняется до тела. Только после его успеха тело перемещает pin через noexcept CustodyPin move и lease через unique_ptr move. Поэтому при snapshot-construction refusal source snapshot/lease/pin остаются вместе; normal destruction по-прежнему уничтожает snapshot, затем lease, затем admission. Порядок initializer text не принят за порядок членов: проверен [C++ class.base.init](https://eel.is/c++draft/class.base.init).

`Metadata.cpp:17–24,35–53,98–111`: reject очищает snapshot **до** перемещения result, блокирует writes удерживаемой lease либо сбрасывает pin при отсутствующем owner. Перемещение disengaged optional snapshot не создаёт entries/proxy; повторный отказ аллокации в error return не требуется. При publicationStarted возвращается ambiguous. Потенциальный отказ `result.snapshot = std::move(*reopened.value)` и неустранённого компилятором move в `return result` находятся внутри того же try. Успешный возврат не обоснован обязательным NRVO: при его отсутствии snapshot preparation может бросить, а reject переводит заполненный result в allocation-safe ошибку, сохраняя lease/pin.

Для непустого value Metadata pre-open cut при запасе 0 отказывает в entries count construction; при запасе ровно измеренного entries proxy `p>0` пустой entries помещается, затем `reserve(count>=1)` отказывает. Оба отказа попадают в worker catch до `ProtectedCustodyFiles::open` (`:50`), pin и dirty admission освобождаются. Это **source-only вывод**, не исполненный partial-headroom case; значение p не фиксируется в 16 bytes нормативно.

### Синтетические проверки и M4 первоначального тестового варианта

`CodecTests:40–224,364–371`: static traits требуют throwing default/move для Entries/Index/Snapshot и noexcept move assignment. Raw `EntriesPressure` не создаёт собственного vector proxy под уже полным бюджетом. Измеряется entries/index/snapshot proxy; отказ direct moves проверяет исходные pointer/capacity/content и charge; default-refusal проверяет все три типа; assignment под full pressure проверяет передачу storage и self-move. Baseline находится вне pressure lifetime. Сценарии входят в normal main и isolated `--entries-move-budget`. При p=0 allocation-fault proof явно пропускается, assignment остаётся. Это чтение тестов, без утверждения PASS.

`FilesTests:1201–1215,1216–1275,1483–1497,1516`: writer-open pressure buffer создаётся до вычисления remaining; проверяются allocationFailed, отсутствие native calls и возврат charge. Metadata direct failed ctor и optional failed emplace проверяют snapshot/lease, pin quota31+refusal, отсутствие IO, невозможность внешней записи и успешный последующий move после снятия давления. Second-rename pressure проверяет ambiguous allocation error, пустой snapshot и удержание lease/pin. Baseline снимается/сверяется за пределами живых pressure vectors. Temporary proxy не создаётся самим pressure setup.

**M4 / MEDIUM — `CodecTests:231–301`, известное main предположение proxy=0 подтверждено исходниками.** В `:239–240` charged считается только как data capacities, хотя `a`, `b` и index.entries имеют живые Debug proxies. При p>0 уже первая equality неверна; последующие move/optional construction добавляют ещё proxies (`:241–245`). В `:256` после temporary swap остаётся proxy самого live large, поэтому usedBytes не равен 0. `full.reserve(limit)` (`:259`) не оставляет места собственной proxy и отказывает в setup, а `:275–276` также не учитывают proxy live bytes. Четыре data reservations по limit/4 плюс положительный proxy overhead не помещаются в limit (`:278–288`). Последний pressure buffer (`:295`) вычисляет remaining после собственного construction и в этом отношении корректен. Это **дефект теста, не утечка продукта и не вновь открытый H3**; actual full CodecTests RED ещё не получен reviewer. Минимум: измерять/сохранять реальные baseline и proxy charge каждой live lifetime, заполнять remaining после preparation; проверять atomic reservation/refusal без требования четырёх exact-quarter data buffers при ненулевом overhead. Предварительно исполнить неизменённый тест, как сообщил main; не менять allocator/cap/Debug iterator policy и не ослаблять `/WX`.

Две точные границы пока не доказаны новым runtime:

1. **Partial headroom:** текущие новые Entries/Metadata pressure cases оставляют 0, не p или 0<headroom<p. Минимальный Metadata case: подготовить fixture/value/cancellation и raw reservation заранее, измерить именно entries proxy p, оставить p, вызвать worker с one-entry value; ожидать allocationFailed, snapshot/lease absent, native counts unchanged и restored charge/pin/dirty admission после снятия pressure. Отдельный headroom<p constructor/move case должен сохранить source pointer/capacity/content. Это локальный allocation boundary, без нового architecture gate.
2. **Engaged snapshot error return:** second rename callback (`FilesTests:1263–1266`) вызывается внутри physical `publishIndex` **до** его flush/readIndex (`Files.cpp:463–473`). Поэтому failure может возникнуть в physical readback и вернуть reject с ещё пустым result.snapshot. Тест не доказывает отказ `Metadata.cpp:107` либо `:109`, не исполняет `snapshot.reset()` именно для engaged snapshot и не различает отсутствие этой reset. Direct retained-result ctor/emplace failure проверяет ownership, но также не проходит worker reject. Минимальная регрессия — довести worker до successful reopen/engaged snapshot, отказать charged proxy на final move при отключённой optional NRVO, затем проверить ambiguous/allocationFailed, snapshot absent, lease/pin retained и blocked writes. Использовать test-only allocation/native boundary существующего стенда; production hooks, новая схема владения и full-v1/T116 не требуются. Наличие дефекта самого текущего reject этим пробелом **не утверждается**.

### Точные SHA-256 нового локально прочитанного набора

Пути относительно canonical checkout. Эта таблица фиксирует первоначальный H3-срез с tests `910e386…` / `c3d498…`; последующие test-only `ff3661…` / `388c78…` идентифицированы отдельно ниже. Это local source identity; не mirror/guest/compiler-input identity и не окончательная source+runtime freeze.

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.h | `a5152a136c102b285e5e34cc926a9c6da7f6c3c43a5acca5707069a757e3dcde` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h | `7d05cf97fc255c30e7171cd4159fb53fe239efacc402944ec629b85f983bb2cd` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp | `739b40a5670227530554a9fc3c92a41a86c2b2577a1d9ac92c3ee118581dab74` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `b29146e86800531c0ef3447fb32bd7846fc17214c418abe5bf5d2e83a7af1825` |
| apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp | `59a72176bff303c5abb34a352015a755481766126f8ff7c5c84c04607f7ab7d9` |
| apps/windows/RecApp/Storage/ProtectedCustodyWriter.cpp | `a9a78170945687c4ef8ce58f31960ec2f673190bdfa6bc251a5b5742689cbaa0` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp | `910e386b40a5c347ad11db6fd2649d72746af27c396cd422de3a4f1f08ee5132` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | `c3d498d79fd6655a5ce263a4b115dc1dc72ed56b3235cd4a632ed4686c0563ea` |

Read dependencies personally hashed: Codec.cpp `5372538eb3055c2b9a89786ef15089eb090e574025a3c0c030f87730873506c9`; Memory.h `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad`; Files.h `108f2e989b081812a38a2464a3eda9930fe35c1173a86df0f288851e6aefeced`; Primitives.cpp `a27b07ac3b04627c5286d6290b3ca6ba3a15710fa170f238be893c3e13c133b3`; Primitives.h `5b3f75a9af51aaee6b0efcc9a20f1f5039aaf7e0ea957992d7432a5038619e9c`; Writer.h `4458449d2b9443178c879ccd15ed1a0949bc071e11f6bf2036d085ad67e9f381`; packed Owner.h `ac096cb8521e1c818b70c0a8147f4b93661b434fa117068149286ea4c7412b75`; packed Tree.h `7209dbfb5a8ba40e0f3afe9032a6bc8d15c2a70b71e54868b518a6fe5edcd586`. Packed contract hash remains `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed`; его authority/version требования не пересматриваются этим follow-up.

### Сообщённые main результаты: строго отдельная атрибуция

- Pre-fix writer-open-budget session `71625`, Debug EXIT3 — подтверждённый сообщением main RED на production boundary. Не переписан в ложный setup/stale failure.
- Debug build `1232` terminal EXIT1 — diagnostic compile failure `/WX C4244` на unconstrained range ctor, без runtime claim. Header fix `a5152a…` лично прочитан; последующий clean-first build `6623 EXIT0` записан ниже. Прежнее ожидание terminal build результата завершено.
- Mirror→guest matching `48204` относится к пяти файлам до header fix; header-specific guest `6623 MATCH` сообщён отдельно. Это main transfer receipts, не независимое чтение guest reviewer; полного нового compiler-input matching здесь не утверждается.
- Subsequent main receipt: clean-first Debug build `6623` **EXIT0**; isolated `37585` — entries/index/snapshot proxies **16/16/16**, constructor traits **0**, assignment **1**, default/index-move/entries-move/snapshot-move stages caught failures and preserved sources; **ENTRIES_EXIT0 / WRITER_OPEN_EXIT0 / METADATA_MOVE_EXIT0**. Reviewer после получения сообщения снова лично сверил все восемь local target hashes: таблица выше совпала полностью. Это current H3 isolated execution evidence **от main**, не reviewer runtime. Оно закрывает targeted исправление unsafe construction/moves и retained Metadata ownership, не partial-headroom или engaged-snapshot worker reject.
- Main portable receipt `78498`: clean build **EXIT0**, **39/39 PASS 41.02s**, с header `a5152a…` и остальными четырьмя предоставленными main hashes без изменений. Native focused4 CTest `6060` ещё выполняется; full CodecTests старого `910e386…` ещё не объявлен PASS/RED. Partial-headroom native result отсутствует. Source+runtime freeze ожидает оставшихся результатов и возможного test-only исправления M4; installed app/mic/VM restart не выполнялись по сообщению main.
- Исторический 16-file VS `95823` теперь **сообщён main terminal Rebuild0 / Core0**, exe prefix `0109…` — только prefix, не полный независимо проверенный binary SHA. Это разрешает прежнее pending состояние данного исторического запуска; старый checkbox выше сохранён как запись cut16. Данный receipt, прежние Debug3/3/Release41/portable39 и readback unchanged13 не подтверждают новый H3-код или новые tests.

### Актуальный reviewer-owned список только этого H3 follow-up

**Последующий test-only readback:** main сообщил Debug focused4 `6060 RED`: только старый Codec `memoryBudgetTests` assertion240, остальные3 PASS. Это actual test-accounting RED, отдельно от production RED71625. Лично прочитан исправленный CodecTests `ff3661b517680938096ef9c3fc4756bf5a2f0e1f46b6344a93e8202af013d38a`, 485 строк: `231–283` измеряют bytes/index proxies, считают два дополнительных live proxies при moves и remaining после preparation, сохраняют baseline при allocator rollback; `285–303` заранее создают все12 independent buffers, вычитают именно их proxy charge из limit перед делением на4. Каждая thread удерживает свой buffer независимо от reserve success; allocator/CAS/64MiB unchanged. EXACT4accepted и exact full quota сохранены. **M4 CLOSED:** source fix лично проверен; main сообщил rebuild `96843`, полный focused4 Debug **PASS22.02s**. Этот результат относится к FilesTests `c3d498…` до следующего partial-headroom addition, а не к `388c78…`.

Следом лично прочитан FilesTests `388c78d27ab21cb9f203547feb209277ecf8048a156276f6fd20fa8ce139143a`, 1705 строк. Новый `metadataMoveBudget:1227–1245` готовит value и pressure до вычисления remaining-proxy, оставляет ровно p для candidate proxy, затем вызывает worker. Проверяет notCommitted/allocationFailed, отсутствие lease/snapshot и native effects, восстановление usedBytes=limit-p, повторный admission всех32pins+refusal33 и внешний baseline после pressure destruction. Proxy p измерен именно через CustodyIndex. Source частичного headroom теперь покрыт конкретным case; runtime результата этого нового case ещё нет. Product header по-прежнему `a5152a…`, Metadata/Files/Reader/Writer hashes не изменены. Новый case не устраняет отдельный engaged-snapshot worker return coverage limit; second-rename scope теперь `1282–1288`. Два последующих test hashes не получают автоматически прежние PASS37585/78498/96843.

- [x] Canonical branch/HEAD, dirty scope и единственный разрешённый report установлены; guidance/skill прочитаны.
- [x] Точные local SHA восьми целевых файлов/зависимостей и текущего 18-file набора сняты; финальные пять изменённых файлов и HEAD повторно сверены после58899.
- [x] Throwing count preparation перед swap/default/move применяется к bytes и entries; unsafe raw entries member устранён.
- [x] Equal-allocator move assignment и self-move не создают дополнительную proxy; live-byte wipe сохранён.
- [x] Integral range ctor исключён в лично прочитанном `a5152a…`; compile/runtime receipts отделены.
- [x] Index/Snapshot/Files/Reader/Writer throwing transfers находятся в прочитанных catch boundaries без нового forced noexcept.
- [x] MetadataCommit snapshot preparation предшествует переносу pin/lease; failed move сохраняет source custody.
- [x] Metadata reject очищает engaged snapshot до error-result move, удерживает/blockWrites lease и классифицирует post-publication failure как ambiguous — подтверждено исходниками.
- [x] Synthetic pressure setup/lifetimes, traits, direct constructor/emplace отказ и assignment/self-move checks прочитаны; Debug/Release PASS принят только на уровне main receipts, с явным Release p=0 SKIP.
- [x] Historical cut16 / RED71625 / compile RED1232 / transfer receipts разделены; overall v1/full-T116/application acceptance не добавлены.
- [x] Fresh clean Debug build `6623 EXIT0` и isolated native `37585` Entries/Writer/Metadata EXIT0 приняты на уровне main receipts; local hashes повторно совпали.
- [x] Текущий portable97843 full39/39 PASS14.05 / EXIT0 принят от main после test-only rebuild на основе clean51271; не выдан за новый clean build и не подменяет native PASS.
- [x] M4 исправлен только в тестовом учёте `ff3661…`; proxy lifetimes/rollback/exact4accepted/exact64MiB лично проверены; allocator policy не ослаблена.
- [x] Исторические6060/96843/94121 RED/GREEN привязаны к их собственным test inputs; текущие Debug96206 full4/4 PASS25.36 / EXIT0 и Release16265 full41/41 PASS49.33 / EXIT0 приняты от main для e00d64cf… / ff3661….
- [x] Partial-headroom Metadata case и Release applicability writerOpenBudget в текущем e00d64cf… прочитаны: candidate proxy fits, reserve fails before IO; memory/pin cleanup и явный p=0 SKIP не ослабляют production budget.
- [x] Partial-headroom case подключён к normal main; Debug49243 на388c78… и повторный Debug96206 наe00d64cf… приняты от main; headroom<p direct entries case отдельно не заявлен выполненным.
- [x] Engaged-snapshot worker error-return cut: direct ctor и second-rename тест не являются выполнением этой точной ветки; нового receipt нет.
- [x] Финальные main receipts текущего набора: guest27786 compiler155/155, host canonical/mirror183/183, VS61697 Rebuild0 / Release-x64, Core58899 EXIT0 и полный App EXE SHA приняты; warning-free, app launch/install/MSIX/mic/release/commit claims отсутствуют.

Финальный readback данного актуального **18-пунктного** списка: **17 checked / 1 unchecked**. Старый cut16 список **18 checked / 2 unchecked** и его historical findings сохранены отдельно, не суммируются с актуальной приёмкой. Производственный и текущий test-source verdict — C/H/M **0/0/0**; historical M4 и Release test applicability исправлены. Engaged-snapshot worker return остаётся точным coverage limit, не новым product defect и не дополнительным условием source approval. H3 закрыт по исходникам и свежим ограниченным runtime receipts main; финальный runtime checkbox закрыт только на уровне main evidence. Reviewer изменил только этот файл; whole-pipeline/full-v1/T116/application/release не приняты.

### Frozen18 — итоговая ограниченная приёмка исходников

**SOURCE VERDICT: ACCEPTED IN SOURCE — C=0 / H=0 / M=0 для проверенного H3 follow-up и его синтетических тестов.** После сообщения о freeze reviewer повторно прочитал фактические пять изменившихся файлов: полный Codec.h, Metadata.h, Metadata.cpp, обновлённый memoryBudgetTests и metadataMoveBudget вместе с подключением сценариев к normal main. Локальный SHA-256 каждого из 18 файлов повторно снят и совпал с объявленным frozen18. Пять отличий от исторического cut16 — Codec.h, Metadata.h, Metadata.cpp, FilesTests и CodecTests; остальные 13 идентичны историческим байтам. Это ограниченная приёмка изменений, а не новый полный аудит всех 18 файлов, всего v1, установленного приложения или T116.

| Файл относительно canonical checkout | SHA-256 frozen18 |
| --- | --- |
| apps/windows/CMakeLists.txt | `b659c852c0c66e455238230b1b05d52292fadf09925ef294e6f322c3a5247b6d` |
| apps/windows/RecApp/GrafWindowsApp.vcxproj | `2949fea918a96cad9b4de63d485ab6a0b0c1c35bb66af5e75f43689f0eba7b72` |
| apps/windows/Tests/GrafWindowsCoreTests/GrafWindowsCoreTests.vcxproj | `c53d070bbb0bae3f4262a875e593a56c3ff28847c5dec19e176d87d3e20d5df4` |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.h | `a5152a136c102b285e5e34cc926a9c6da7f6c3c43a5acca5707069a757e3dcde` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.h | `7209dbfb5a8ba40e0f3afe9032a6bc8d15c2a70b71e54868b518a6fe5edcd586` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp | `11e54696cff69e2421ca312a9e351476cc4979a03f60a5e9bee1e17427b0559f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.h | `0d62de31b7d753fad4057207da4d78a6629e2b1ca4fb6318609862711f4b3c88` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyFormat.cpp | `bfe96de37df2193035b68b3cae1191c9c92d50f7ad001b0293cb61f0bff5eb0f` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h | `ac096cb8521e1c818b70c0a8147f4b93661b434fa117068149286ea4c7412b75` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `b29146e86800531c0ef3447fb32bd7846fc17214c418abe5bf5d2e83a7af1825` |
| apps/windows/RecApp/Storage/ProtectedCustodyReader.cpp | `59a72176bff303c5abb34a352015a755481766126f8ff7c5c84c04607f7ab7d9` |
| apps/windows/RecApp/Storage/ProtectedCustodyWriter.cpp | `a9a78170945687c4ef8ce58f31960ec2f673190bdfa6bc251a5b5742689cbaa0` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp | `739b40a5670227530554a9fc3c92a41a86c2b2577a1d9ac92c3ee118581dab74` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp | `59e976433e56856c18ffb88090387204c472a2991ab92c901d29450258d00c3e` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp | `9201c6c995c21a7f7bc72300b4dc7d7d50d2363fb9494f6a35fee73ec59f1bd7` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | `388c78d27ab21cb9f203547feb209277ecf8048a156276f6fd20fa8ce139143a` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h | `7d05cf97fc255c30e7171cd4159fb53fe239efacc402944ec629b85f983bb2cd` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp | `ff3661b517680938096ef9c3fc4756bf5a2f0e1f46b6344a93e8202af013d38a` |

Итог проверки: throwing count preparation до swap защищает default/move Index/entries/Snapshot; integral range exclusion устраняет compile failure без снижения warnings; move assignment/live-byte wipe/self-move сохранены. Metadata ctor передаёт pin/lease только после snapshot preparation; reject сбрасывает snapshot до потенциального error-return move и сохраняет ambiguous custody. Тестовый учёт учитывает реально живые proxies, оставляет EXACT4 accepted и полный atomic64MiB quota; новый запас p проверяет отказ первого entries reserve до IO и возврат memory/pin admission. Ослабления production budget не обнаружено. Конкретных новых исправлений производственного кода reviewer не требует.

Актуальные **сообщённые main**, не самостоятельно выполненные reviewer, receipts для этого frozen18:

- Debug49243: incremental **ONLY test rebuild** после clean product Debug6623 EXIT0; focused **4/4 PASS21.02s**, включая новый partial-p case в normal main. Это не отдельный clean-first rebuild всех финальных тестов.
- Portable51271: **clean build EXIT0, full39/39 PASS33.29s**, terminal fresh receipt на frozen18. Старый portable78498 не используется вместо него.
- Native32169: **COMPILE_SOURCE_MATCH155/155** после финальных CodecTestsff3661… / FilesTests388c78…, включая actual bytes VM headers. Это main compiler-input identity evidence, не независимое чтение guest reviewer и не native runtime PASS.
- Native94121: **full Release clean ongoing, затем VS Rebuild**. Terminal build/tests/VS/executable identity ещё не предоставлены и не отмечены PASS.

В сообщении main task/contract/feature3 SHA unchanged, counts119/93/26 и T116 open. Эти статусы данным узким review не меняются; новых требований full-v1, архитектуры, installed-app/mic/VM restart не вводится. Исторический cut16 VS95823 не переносится на frozen18.

Итоговый актуальный список остаётся **16 checked / 2 unchecked**: один unchecked — конкретная, не блокирующая source approval граница покрытия engaged-snapshot worker error-return; другой — ожидаемые terminal Release/VS receipts. Проверка исходников завершена сейчас, без ожидания нового полного feature audit. Финальная runtime приёмка будет отдельным обновлением только после сообщения main и сверки его input identity. Запись reviewer ограничена этим отчётом; чужие dirty изменения сохранены.

### Последующая test-only правка применимости writerOpenBudget в Release — финальные receipts ожидаются

Main сообщил terminal94121: **full clean Release BUILD0 / CTest40/41 / test EXIT8**, единственный RED — writerOpenBudget ожидал allocationFailed при Release entries proxy=0. Это реальный test assertion failure старого FilesTests388c78…, не production H3 и не успешный общий Release run. При отсутствии charged proxy пустой WriterState не обязан отказать по memory budget; причина согласуется с прочитанным исходным сценарием.

Reviewer лично перечитал изменённый `writerOpenBudget:1201–1222` и повторно снял SHA пяти изменённых файлов. Текущий FilesTests — **`e00d64cf3c4682eb21dce1dbaa5c99d78970c60e3b2aa9e03633ae827b26ffe5`**, совпал с последующим сообщением main. Функция сначала измеряет именно CustodyIndex entries proxy в отдельном lifetime, сверяет возврат baseline и при p=0 явно пишет `writer-open-budget SKIP-no-proxy-allocation-fault`, затем возвращает без false fault claim. При p>0 сохраняются прежние pressure/IO/allocationFailed/cleanup assertions. Это корректное ограничение применимости allocator-proxy fault test, не ослабление production budget и не заявление, что fault выполнен в Release. Metadata/entries уже имеют ту же явную p=0 политику. Source verdict этой test-only правки: **ACCEPTED IN SOURCE, новых C/H/M нет**.

Codec.ha5152a…, Metadata.h7d05cf…, Metadata.cpp739b40… и CodecTestsff3661… вновь совпали с предыдущей таблицей. Main сообщает остальные production files без изменений. Предыдущая таблица frozen18 и receipts49243/51271/32169 остаются привязанными к **FilesTests388c78…**, не становятся compiler-input/runtime proof для e00d64cf…. Debug49243 partial-p PASS на прежнем тесте сохраняется как историческое доказательство выполнения сценария, но текущий Debug также будет повторён.

Текущий main16265 — test rebuild и полный41 Release **ongoing**, затем ожидаются Debug и VS. Reviewer по прямому запросу пользователя ожидает текущий final receipt; финальные runtime отметки не закрыты. Актуальный список **16 checked / 2 unchecked** сохраняется: engaged-snapshot worker return — честная необязательная граница покрытия, финальный runtime/identity нового тестового снимка — pending. Нового full-v1/T116 gate нет; продукт и чужие изменения reviewer не менял.

**Terminal update для e00d64cf… / ff3661… от main:** Release16265 **41/41 PASS49.33s, test EXIT0**. Clean product94121 BUILD0 выполнен ранее;16265 пересобрал только изменённый Files test TU, не повторял полную clean сборку. Portable97843 **39/39 PASS14.05s, main EXIT0** — incremental после51271 clean product с изменённым Files test, также не новый clean-first build. Эти результаты приняты в указанной main атрибуции и не превращают Release p=0 SKIP в исполнение proxy fault. Debug e00d64cf… ещё running; VS Rebuild next; whole-pipeline readiness **не принята**. Финальный runtime/identity checkbox остаётся unchecked до следующего сообщения main.

**Следующий terminal update от main:** Debug96206 **4/4 PASS25.36s, test EXIT0** на текущих FilesTestse00d64cf… / CodecTestsff3661…. Target tests rebuilt после clean product6623; продукт не менялся. В сочетании с Release16265 full41/41 и portable97843 full39/39 это свежая bounded H3 execution proof, не новый full-feature gate. Final canonical→mirror **183/183** сообщён main (host command; `aea6…` — tool chunk identifier, **не manifest SHA**, исправлено по последующему уточнению main). Guest compile155 final27786 ещё collecting; новый VS Rebuild выполняется. До их terminal сообщения окончательный identity/VS checkbox остаётся unchecked. Engaged-snapshot worker error-return остаётся явно untested, не HIGH и не product/T116 blocker.

### Ограниченное закрытие H3 на текущих исходниках и fresh native evidence

После Debug96206 main явно разрешил закрыть H3 по source + fresh bounded native proof и сообщил, что VS receipt предоставит отдельно. Reviewer повторно снял **все18 local SHA-256**: 17 строк таблицы frozen18 идентичны; единственная последующая замена — FilesTests **`e00d64cf3c4682eb21dce1dbaa5c99d78970c60e3b2aa9e03633ae827b26ffe5`** вместо388c78…. Это полная идентификация текущего локального 18-file набора таблицей плюс одной явной заменой. Normal main действительно вызывает writerOpenBudget и metadataMoveBudget (`FilesTests:1542`), isolated входы также сохранены (`:1511,1519`). HEAD/branch при последней проверке прежние99b00a579c24b50e320465b69d9a296038bc544d / codex/200-windows-followup.

**H3 CLOSED в данном ограниченном объёме. SOURCE ACCEPTED, C/H/M=0/0/0.** M4 accounting и последующая Release applicability ошибка теста исправлены и имеют новые terminal results от main. Reviewer не исполнял тесты, не читал guest независимо и не выдаёт receipts main за собственное наблюдение runtime. Fresh Debug/Release/portable execution приняты с точным разграничением clean product builds и последующих test-only rebuilds; старые16 receipts не используются вместо текущих. Финального VS/executable receipt пока нет: он остаётся unchecked, не препятствуя разрешённому закрытию узкого H3.

Readback актуального reviewer-owned списка: **16 checked / 2 unchecked**. Не закрыты (1) точное исполнение engaged-snapshot worker error-return, которое не объявляется дефектом или обязательным product/full-T116 gate, (2) финальный VS/guest identity receipt, ожидаемый отдельным сообщением main. Whole pipeline/installed app/mic/T116 не приняты. Никаких новых production fixes не требуется по результату этого review. Reviewer-owned запись ограничена этим файлом; чужие изменения сохранены.

**VS/identity terminal update от main:** VS61697 **REBUILD_EXIT0, Release/x64**, текущие18 с FilesTestse00d64cf… / CodecTestsff3661… и producta5152a… /739b40… /7d05cf…. По сообщению main скомпилированы все19174 functions свежим rebuild, без IPDB reuse. Guest27786 terminal **COMPILE_SOURCE_MATCH155/155** после e00d test delta; canonical→mirror **183/183** повторно проверен main host command. Это main evidence, не независимый reviewer guest run. VS имеет известные warnings: **D9025 /W1→/W4** и WebRTC **C4100 (2 unused parameters)**; warning-free claim отсутствует. Уточнение `aea6…` как chunk identifier внесено выше, manifest SHA не выдуман. Core binary running и App EXE SHA обещаны следующим receipt; runtime checkbox пока unchecked. Ни App launch/install/MSIX/mic/private inventory этим запуском не доказаны и не выполнялись reviewer.

### Финальный receipt58899 и readback текущего18 — 2026-10-04

Main сообщил terminal58899 **CORE_EXIT0** и полный SHA-256 построенного App EXE **`3EA4A30911A7BFE3B49444B315DCA56CBB4EA6100F7731F698C8352496B47424`**, путь **`C:\Temp\graf-f200-native-f4d8739a6fe345f78ceabaebed7d71f9\out\x64\Release\GrafWindowsApp.exe`**. Совместно с VS61697 REBUILD0 это завершает ожидавшийся узкий VS/Core/built-byte receipt для текущего immutable18 cohort. Это build artifact identity и Core execution от main, **не запуск GrafWindowsApp.exe**, не installation/MSIX/microphone/private inventory или release proof. Reviewer не пересчитывал guest EXE самостоятельно. Известные VS D9025/C4100 warnings остаются явно указанными; никаких warning-free claims нет.

После получения58899 reviewer лично повторно прочитал актуальные marks/text и снял пять SHA; все пять совпали с повторным main сообщением. HEAD **`99b00a579c24b50e320465b69d9a296038bc544d`**, branch **`codex/200-windows-followup`** повторно совпали. Текущий локальный набор —18 файлов, не19; полная таблица frozen18 выше остаётся идентичной в17 строках, строка FilesTests заменяется только приведённым ниже e00d64cf…. Это точная source identity, отдельно от guest/mirror identity receipts.

| Текущий изменившийся файл | Финальный лично сверенный SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.h | `a5152a136c102b285e5e34cc926a9c6da7f6c3c43a5acca5707069a757e3dcde` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h | `7d05cf97fc255c30e7171cd4159fb53fe239efacc402944ec629b85f983bb2cd` |
| apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp | `739b40a5670227530554a9fc3c92a41a86c2b2577a1d9ac92c3ee118581dab74` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | `e00d64cf3c4682eb21dce1dbaa5c99d78970c60e3b2aa9e03633ae827b26ffe5` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp | `ff3661b517680938096ef9c3fc4756bf5a2f0e1f46b6344a93e8202af013d38a` |

Финальные execution receipts main: Debug96206 **4/4 PASS25.36s, EXIT0**, Release16265 **41/41 PASS49.33s, EXIT0**, portable97843 **39/39 PASS14.05s, EXIT0**, guest27786 **COMPILE_SOURCE_MATCH155/155**, canonical/mirror **183/183**, VS61697 **REBUILD_EXIT0**, Core58899 **CORE_EXIT0**, App EXE SHA выше. Debug/Release/portable тесты обновлены после соответствующих clean product builds6623/94121/51271; эти test-only rebuilds не называются повторными clean builds. Historical16, FilesTests388c78… и прежний compiler32169 не подменяют эту совокупность.

**ИТОГ: SOURCE ACCEPTED, H3 CLOSED в заданном bounded scope, C=0 / H=0 / M=0; текущий18-пунктный список17 checked / 1 unchecked.** Runtime checkbox закрыт только на уровне main receipts. Единственный unchecked — точное engaged-snapshot worker error-return fault execution; корректность исходников установлена, само исполнение этой ветки не доказано, это не новый HIGH и не обязательный full-T116/product gate. Старый cut16 **18/2** сохранён отдельно. Whole-pipeline readiness/T116/installed-app/release/commit acceptance отсутствует. `code-reviewer` направил проверку корректности/exception safety и проверки тестовых предпосылок; исправлений вне отчёта reviewer не делал. Единственная reviewer-owned запись — этот отчёт; dirty shared changes не откатывались и не изменялись reviewer.

## Согласование исторических маркеров — 2026-10-10

В рамках обязательного независимого ревью Spec Kit, по поручению основного агента,
независимый reviewer изменил только два
старых маркера выше. Их текст, findings и прежние counts оставлены как
свидетельства исходного cut; отметка теперь означает последующее закрытие
обязательства, а не PASS первоначального снимка. Основание до изменения:
SHA-256 этого отчёта `ebe1cab3f9621a316fb46fa7c16c193d0b9b534bd8a32be37d872cc4205db45d`.
Текущий canonical HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`,
ветка `codex/200-windows-followup`; dirty bytes сохранены.

| Старый пункт | Перечитанное последующее evidence и предел закрытия |
| --- | --- |
| VS95823 | Запись этого отчёта около строки562 содержит terminal Rebuild0/Core0, сообщённый main именно для cut16. Закрыто ожидание результата этого исторического запуска. Prefix EXE0109… не превращён в полный SHA; reviewer не видел/не запускал его binary. Новый VS61697/Core58899 из финального раздела и validation Round219 — отдельный frozen18 receipt, не замена identity95823. |
| H3 unsafe entries/moves и partial headroom | Последующий frozen18: Codec.h a5152a136c102b285e5e34cc926a9c6da7f6c3c43a5acca5707069a757e3dcde; Metadata.h7d05cf97fc255c30e7171cd4159fb53fe239efacc402944ec629b85f983bb2cd; Metadata.cpp739b40a5670227530554a9fc3c92a41a86c2b2577a1d9ac92c3ee118581dab74; FilesTestse00d64cf3c4682eb21dce1dbaa5c99d78970c60e3b2aa9e03633ae827b26ffe5. Перечитаны финальный раздел и validation Round218–219: Debug96206 focused4/4 EXIT0, Release16265 full41/41 EXIT0, portable97843 39/39 EXIT0; isolated37585 и partial-headroom49243 отделены от финальных inputs. Исправлены последующие bytes, не первоначальный 8ae8…/43c620… cut. |

Сейчас дополнительно проверены CustodyVector throwing count/move preparation,
MetadataCommit snapshot-before-lease transfer и metadataMoveBudget:1292–1372.
Текущие SHA: Codec.h
`ef725ea1bc07c6a6905f801dcf63d94f7827b4e630ca301d69ec4f6dabcc906b`;
Metadata.h `e6ff8be26942647129a90110e617a72e7be6260904ff5e56b2227700e7b9dce9`;
Metadata.cpp `82e7bd60e3bde12acef730013f9de6b4fe26bab82af4078e61fb868ad69e4f13`;
FilesTests `fb599aafc0ab790edb2db787562031c350ba198e413c8376e446cfbfc014a250`.
Это текущий source readback, не перенос старых native PASS на новые SHA.

Точный engaged-snapshot worker error-return маркер оставлен unchecked.
Direct moves/second rename не доказывают отказ final transfer после engaged
snapshot; последующие metadata/package reports также сохраняют этот пробел.
Исторические слова «не блокирует source approval» не являются исключением из
нынешнего ALL-checkbox high-risk gate: **STOP до доказанного закрытия**.
Фактические raw counts всего этого Markdown после согласования: **37 checked /
1 unchecked**. Исполнение старых тестов — evidence main из перечитанных
документальных terminal записей; reviewer сейчас не исполнял native jobs и
не проверял guest binaries. Full320 остаётся running по сообщению main.
