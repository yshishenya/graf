# Feature 222 Infrastructure Checklist

- [ ] Trigger and target branch are explicit.
- [ ] Job/check name is stable and recorded in branch protection plan.
- [ ] Concurrency group is per PR and cancels in-progress runs.
- [ ] Requested SHA is validated against checkout and observed SHA.
- [ ] Workflow cannot invoke production/CD/migration mutation paths.
- [ ] Uploaded artifact is metadata-only and schema validated.
- [ ] Missing, failed, stale, cancelled and ambiguous evidence blocks merge.
- [ ] Required check is enabled only after a real PR run is observed.
- [ ] Full CI remains release-candidate-only.

Checklist state is reviewer-owned and must not be marked complete by the
implementation agent.
