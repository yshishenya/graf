# Feature Specification: Modernize Public Landing Page

**Feature Branch**: `feature/landing-modernization`
**Created**: 2026-08-07
**Status**: Implemented

## Goal
Modernize the public landing page (UI/UX) to use current web design trends (Bento grid, glassmorphism) and refine the copywriting to better align with the core product value proposition (system-audio capture without bots).

## Scope
- Update CSS and HTML for `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`.
- Improve layout (bento grid, pill tags).
- Improve typography (gradient text, non-breaking spaces).
- Update accessibility (forced-colors, prefers-reduced-motion).
- Keep existing analytics data attributes intact.

## Out of Scope
- Backend changes or API modifications.
- Changes to user authentication or application workflows.
