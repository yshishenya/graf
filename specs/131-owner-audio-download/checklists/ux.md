# UX Checklist: Owner-default audio egress

**Feature**: `131-owner-audio-download`

- [x] CHK001 Is the owner-facing success state defined for both the browser and embedded macOS cabinet? [Coverage, Spec §US1]
- [x] CHK002 Is the non-owner owner-only state distinct from a generic missing-audio state? [Clarity, Spec §US2]
- [x] CHK003 Is an explicit per-meeting denial represented as an intentional policy state rather than a silent no-op? [Clarity, Spec §US2, §US3]
- [x] CHK004 Does canceling the system save panel leave the meeting open and make a safe retry possible? [Recovery, Spec §US1, §US3]
- [x] CHK005 Does the specification preserve one shared server-mediated action so web and embedded surfaces cannot drift? [Consistency, Spec §FR-006]
- [x] CHK006 Are unavailable, deleting, processing, corrupt, storage-failure, and expired-session outcomes bounded without replacing the meeting page with an error document? [Degraded states, Spec §FR-007]
- [x] CHK007 Is the existing GRAF action copy reused without introducing a clean-room or brand-distance risk? [Brand distance, Spec §FR-006]
