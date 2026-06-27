# Infrastructure Checklist: VK ID Web Login

**Purpose**: Validate deployment and secret-wiring requirement quality before implementation
**Created**: 2026-06-27
**Feature**: [spec.md](../spec.md)

## Runtime Configuration

- [x] CHK001 Are required production VK settings named clearly? [Completeness, Contract §Runtime Settings]
- [x] CHK002 Is the public callback URL specified exactly for provider-console registration? [Clarity, Spec §Clarifications, Contract §Provider Console Callback]
- [x] CHK003 Is provider-specific client ID selection required and measurable? [Measurability, Spec §FR-009, SC-004]

## Deployment Safety

- [x] CHK004 Are missing secret and empty secret failure modes defined before rollout? [Coverage, Spec §US3, Contract §Failure Behavior]
- [x] CHK005 Does the plan define local, repository, and deploy gates for this auth/secret change? [Completeness, Plan §Validation Plan]
- [x] CHK006 Are evidence-safe fields distinguished from prohibited credential evidence? [Clarity, Contract §Evidence Safety]

## Scope Control

- [x] CHK007 Is Docker secret wiring limited to `rec-api` and not worker or migration containers? [Clarity, Spec §FR-010]
- [x] CHK008 Is rollout blocked until VK credentials exist, avoiding an active broken provider in production? [Consistency, Plan §Release Gate]
