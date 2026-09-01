# Contract: Bounded legacy retirement slice

An approved `remove` contour may be implemented only in a fresh Feature with a
single scope fence and independently testable validation. The slice must carry:

- contour IDs and the supported client/data compatibility boundary;
- owner, risk lane, exact validation commands and Dev rehearsal;
- explicit abort conditions and a reversible rollback target;
- applicable migration, Temporal, MediaScribe, macOS/Sparkle or deploy evidence;
- GitHub issue, PR, task and release-candidate links.

Missing protected-domain evidence blocks the slice. The slice must not edit
neighboring contours, root `CHANGELOG.md`, reviewer checklists or production
state. A release train may include only merged slices with validated per-PR
fast evidence and immutable task/issue lineage. After the aggregate candidate
is frozen, exactly one authoritative Full CI receipt must bind the candidate
SHA to every included slice; per-PR fast CI is not release evidence.
