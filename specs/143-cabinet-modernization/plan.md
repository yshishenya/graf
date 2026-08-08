# Implementation Plan: Modernize Web Cabinet UI

**Branch**: `143-cabinet-modernization` | **Date**: 2026-08-08 | **Spec**: [spec.md](spec.md)

## Summary
The goal is to modernize the web cabinet CSS, making it look professional, trustworthy, and visually aligned with the modernized public landing page.

## Phase 1: CSS Refactoring (`cabinet.css`)
- **Color Variables**: Update the CSS variables for surfaces and backgrounds to create depth (e.g., using subtle gradients or slightly different hex codes for elevation).
- **Typography**: Refine font sizes, line heights, and weights for headings and body text to improve legibility.
- **Buttons and Inputs**: Update border radiuses, add subtle transitions, and improve focus/hover states (e.g., replacing harsh borders with subtle glows).
- **Meeting Rows**: Redesign the `.cabinet-meeting-row` to look like a modern card or a highly polished list item with better padding and hover effects.

## Validation Plan
- Verify UI rendering visually.
- Run local validation: `infra/scripts/ci-local.sh --fast`.
- Run specific UI contract tests to ensure no breakages.
