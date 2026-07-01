# Contract: Architecture Finding

Each finding in `audit/findings-register.md` must follow this contract.

```yaml
finding_id: F-072-000
title: Short actionable title
classification: delete now | split soon | keep intentionally | risky / needs spec
paths:
  - exact/repository/path
evidence:
  - "Repository-backed observation, command, or doc"
risk: "What could break if this is changed casually"
recommended_next_step: "Focused validation, small PR, or separate Spec Kit slice"
pre_refactor_checks:
  - "Exact test, script, review, or runtime proof required before change"
```

## Rules

- `delete now` requires caller evidence, runtime evidence, and a focused
  validation path. It still does not allow deletion in 072 stage one.
- `split soon` requires a small PR boundary and checks that can prove behavior
  did not change.
- `keep intentionally` requires contract evidence that explains why the item
  may look removable but is still needed.
- `risky / needs spec` requires the boundary or product rule that makes direct
  refactor unsafe.
- Evidence must not include secrets, raw audio, transcript text, signed URLs,
  private meeting content, or live credentials.

