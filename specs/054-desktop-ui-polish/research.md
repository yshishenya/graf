# Research: Desktop UI Polish

## Decision: Expand Existing Embedded Workspace

**Decision**: Raise the embedded cabinet workspace cap in the existing CSS/Swift constants instead of adding a new responsive layout system.

**Rationale**: The appshot shows a narrow center list surrounded by unused space. Existing CSS already owns `.desktop-embedded .cabinet-workspace`, so changing its max width is the smallest fix.

**Alternatives considered**: New design tokens or a separate embedded template. Rejected as unnecessary for a width/density issue.

## Decision: Keep Rows Table-Like And Compact

**Decision**: Adjust existing `.meeting-row.cabinet-row` grid columns, height, and typography to make recordings feel closer to the reference list density.

**Rationale**: Current row renderer already includes checkbox, icon, title/duration/status/actions/date. The problem is scale, not data shape.

**Alternatives considered**: New table markup. Rejected because current anchors are accessible and tested.

## Decision: Keep Native Inspector Narrower In Idle State

**Decision**: Preserve collapsed rail as the default idle state and modestly reduce expanded inspector width.

**Rationale**: The reference prioritizes the center workspace. The inspector should stay available without dominating idle review.

**Alternatives considered**: Hide the rail completely. Rejected because local capture/upload truth must remain visible and reachable.

## Decision: Clean-Room Reference Only

**Decision**: Use KRISP only for density, side navigation rhythm, and persistent control rail expectations.

**Rationale**: 2brain Rec must keep original brand, Russian copy, privacy/deletion truth, and server-owned review behavior.

**Alternatives considered**: Copying reference labels or visuals. Rejected by brand-distance and privacy gates.
