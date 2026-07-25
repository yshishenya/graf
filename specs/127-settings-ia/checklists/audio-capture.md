# Capture Boundary Requirements Quality Checklist: settings IA

**Purpose**: Validate that the settings redesign does not silently redefine the
macOS capture contract.
**Created**: 2026-07-25
**Feature**: [spec.md](../spec.md)
**Audience**: Capture/product gate reviewer.

- [x] CHK001 — Is capture behavior explicitly out of scope except for discoverability and native handoff? [Scope, Spec §US4, Out of Scope]
- [x] CHK002 — Are manual start/stop, persistent active-recording visibility and one-action Stop preserved as non-negotiable outcomes? [Safety, Spec §FR-011, SC-008]
- [x] CHK003 — Is target-scoped automatic recording distinguished from a prohibited global “record everything” web control? [Clarity, Spec §US4, FR-011]
- [x] CHK004 — Is the removed audio-routing implementation explicitly excluded from navigation, fallback and copy? [Constitution alignment, Spec §FR-011, Out of Scope]
- [x] CHK005 — Does the native handoff requirement avoid claiming that browser settings can grant macOS permissions or change local capture policy? [Boundary, Spec §FR-011, Assumptions]
- [x] CHK006 — Are hardware capture tests intentionally excluded because no capture path changes? [Validation scope, quickstart.md]
