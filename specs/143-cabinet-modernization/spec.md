# Feature Specification: Modernize Web Cabinet UI

**Feature Branch**: `143-cabinet-modernization`
**Created**: 2026-08-08
**Status**: Draft

## Goal
Modernize the web cabinet UI to make it feel like a trustworthy, production-ready system. The update will bring the cabinet's visual language closer to the recently updated public landing page (which utilizes modern dark-mode techniques, subtle depth, and refined typography), while strictly adhering to the `GRAF` original design system constraints.

## Scope
- Update `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` to refine the color palette, shadows, border radiuses, and typography.
- Improve interactive states (hover, focus) for buttons, inputs, and meeting rows.
- Increase whitespace and visual rhythm.
- Apply modern "soft" styling (subtle borders, subtle glows/shadows instead of flat borders) to components.

## Out of Scope
- Backend logic changes.
- Modifying the macOS native app SwiftUI code.
- Adding completely new features or modifying the HTML structure heavily (only CSS and minimal HTML class tweaks).
