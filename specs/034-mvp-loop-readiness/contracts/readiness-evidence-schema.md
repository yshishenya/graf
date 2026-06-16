# Contract: Readiness Evidence Schema

Date: 2026-06-16

The JSON report must use this top-level shape:

```json
{
  "feature": "034-mvp-loop-readiness",
  "generated_at": "2026-06-16T00:00:00Z",
  "deployed_commit": "unknown",
  "claim_summary": {
    "outcome": "partial_readiness",
    "bounded_claims": [],
    "excluded_claims": [],
    "p0_p1_blockers": 0
  },
  "stages": [],
  "evidence": [],
  "launch_gaps": [],
  "reference_comparisons": [],
  "forbidden_content_scan": {
    "status": "pending",
    "commands": [],
    "matches": []
  }
}
```

## Enumerations

Stage status:

- `ready`
- `degraded`
- `blocked`
- `not_accepted`
- `out_of_scope`

Evidence strength:

- `live`
- `production_smoke`
- `local_runtime`
- `synthetic`
- `docs_only`
- `missing`
- `blocked`

Evidence type:

- `command`
- `screenshot`
- `document`
- `endpoint`
- `github`
- `runtime`
- `production_smoke`
- `reference_review`

Claim outcome:

- `mvp_loop_ready`
- `internal_pilot_candidate`
- `partial_readiness`
- `pilot_blocked`
- `evidence_blocked`

Forbidden-content scan status:

- `pass`
- `blocked`
- `pending`

## Stage Object

Required fields:

```json
{
  "id": "meeting-detail",
  "label": "Meeting detail review",
  "owner_surface": "web_cabinet",
  "status": "ready",
  "evidence_strength": "synthetic",
  "evidence_ids": ["016-ready-detail-screenshot"],
  "launch_gap_ids": [],
  "claim_impact": ["web_review_verified"],
  "notes": "Synthetic fixture evidence; live private content not committed."
}
```

## Evidence Object

Required fields:

```json
{
  "id": "production-ready-health",
  "type": "endpoint",
  "source": "https://rec.2brain.pro/api/v1/health/ready",
  "captured_at": "2026-06-16T00:00:00Z",
  "scope": "Public readiness endpoint returned ready.",
  "strength": "production_smoke",
  "safe_to_commit": true,
  "forbidden_content_scan": "not_applicable",
  "limitations": ["Health endpoint alone does not prove user rollout readiness."]
}
```

## Launch Gap Object

Required fields:

```json
{
  "id": "live-desktop-private-safe-capture",
  "severity": "P1",
  "affected_journey": "desktop-embedding",
  "current_evidence": "Synthetic desktop evidence exists.",
  "missing_evidence": "Fresh live app capture or explicit blocked reason.",
  "recommended_next_action": "Capture metadata-safe desktop app screenshots.",
  "owner_area": "desktop",
  "deferred": false,
  "deferral_guardrail": null
}
```

## Validation Rules

- Every stage must reference at least one evidence id unless its status is
  `blocked`, `not_accepted`, or `out_of_scope`.
- Every P0/P1 launch gap must have a non-empty `recommended_next_action`.
- `mvp_loop_ready` is invalid when any P0/P1 launch gap remains.
- `safe_to_commit=false` evidence must not appear as a committed screenshot or
  content-bearing excerpt.
- `forbidden_content_scan.status` must be `pass` before acceptance.
