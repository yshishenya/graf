# Security Requirements Checklist: «Поделились со мной»

**Purpose**: Assess whether the access-boundary requirements are complete and
unambiguous before implementation and review.

**Created**: 2026-07-27

**Feature**: [spec.md](../spec.md)

## Recipient Isolation

- [x] CHK001 Are recipient eligibility requirements explicit for both direct
  grants and accepted external invitations? [Completeness, Spec §FR-002,
  Assumptions]
- [x] CHK002 Is the meaning of a "confirmed account" unambiguous and aligned
  with the existing invitation verification flow? [Clarity, Spec §FR-002,
  Edge Cases]
- [x] CHK003 Do requirements explicitly exclude pending-address invitations
  from both list contents and metadata disclosure? [Completeness, Spec §FR-006]
- [x] CHK004 Are cross-workspace discovery boundaries specified without
  implying workspace membership for the recipient? [Completeness, Spec §FR-008]

## Authorization Freshness

- [x] CHK005 Do requirements distinguish initial listing eligibility from the
  authoritative check when a card is opened? [Clarity, Spec §FR-005]
- [x] CHK006 Are revocation, expiry, deletion and recipient-proof changes all
  covered as reasons to omit or deny access? [Coverage, Spec §FR-005, §FR-006]
- [x] CHK007 Is the required behavior defined when a listed source meeting can
  no longer be authorized without disclosing why? [Coverage, Edge Cases]
- [x] CHK008 Are requirements for duplicate grants clear enough to determine
  the single effective access level without expanding it? [Clarity, Spec §FR-007]

## Metadata and Actions

- [x] CHK009 Is the allowed card metadata exhaustively bounded rather than
  described only by examples? [Clarity, Spec §FR-003]
- [x] CHK010 Do the prohibited owner, workspace, calendar and service data
  categories align with every listed recipient action? [Consistency, Spec §FR-008]
- [x] CHK011 Is the destination requirement specific that cards use the
  restricted result page rather than a workspace-owned route? [Clarity, Spec §FR-004]
- [x] CHK012 Are no-share, no-reshare and no-workspace-membership boundaries
  explicit for browser and embedded cabinets alike? [Coverage, Spec §FR-008,
  §FR-010]

## Failure and Review Boundaries

- [x] CHK013 Are failure-state requirements clear that stale or partial
  recipient data is not retained or exposed? [Coverage, Edge Cases]
- [x] CHK014 Are assumptions about the existing shared-result access contract
  identified as a dependency for implementation and review? [Dependency,
  Assumptions]
- [x] CHK015 Can the 100% isolation success measures be evaluated against a
  stated recipient/access-state matrix? [Measurability, Spec §SC-002, §SC-004]
