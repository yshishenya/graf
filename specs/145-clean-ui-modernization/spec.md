# Feature Specification: Clean UI Modernization (UI Only)

**Feature Branch**: `145-clean-ui-modernization`
**Created**: 2026-08-08
**Status**: Implemented and validated

## Goal
Implement a safe, UI-only modernization of the web cabinet and macOS application, mirroring the bento-card aesthetic (dark theme, glassmorphism, rounded corners) without breaking existing server logic or introducing external dependencies like Google Fonts.

## Scope
- Update `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` to refine colors, shadows, and 12px border radiuses.
- Update `DesktopMeetingShellChrome` and related SwiftUI views in `apps/macos/RecApp` to match the web cabinet's dark theme and use `Material` backgrounds.
- Keep system fonts, **DO NOT** use Google Fonts.
