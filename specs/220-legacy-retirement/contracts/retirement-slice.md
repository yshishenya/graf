# Retirement Slice Contract

Each slice MUST define:

1. input contour IDs and the exact legacy behavior being retired;
2. owner, risk and acceptance criteria;
3. migration/cutover boundary and compatibility window;
4. backup/restore, replay or signing rehearsal appropriate to the domain;
5. abort conditions and a tested rollback target;
6. focused tests, fast CI evidence and known limitations;
7. linked issue/PR and release-train gate.

No slice may delete production data, rewrite migration pointers, remove Temporal history or publish a macOS update without its own approved feature and release gate.
