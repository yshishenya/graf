# Plan: Feature 235

1. Add regression tests for allocator and closeout evidence before changing
   implementation.
2. Fix allocator and closeout validator with the smallest existing patterns.
3. Make workflow metadata identity explicit for feature and scoped lanes.
4. Sync Feature 231 task rows to task-backed issues while retaining #6337 as
   umbrella.
5. Run focused governance validation and exact-SHA fast CI.

Risk lane: significant-governance. No production runtime or user data changes.

GitHub tracking: #6385 is the umbrella; executable tasks T001–T006 are
tracked by task-backed issues created after planning. The feature quickstart
is kept inside this feature directory so the repository root remains a stable
router.
