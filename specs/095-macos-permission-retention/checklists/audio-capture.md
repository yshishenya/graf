# Audio Capture Checklist: macOS Permission Retention

> Historical capture-permission checklist. It does not change the current
> Developer ID-only macOS publication rule in Feature 130.

**Purpose**: Validate requirements quality for microphone and Screen/System
Audio permission continuity without changing the capture engine.
**Created**: 2026-07-09
**Feature**: [spec.md](../spec.md)

## Permission Requirement Completeness

- [x] Are microphone and Screen/System Audio permission states both included in
  acceptance, rather than treating one as sufficient?
- [x] Are granted, denied, restricted, unknown, and signing-drift states
  distinguishable in requirements and evidence?
- [x] Is permission onboarding required to stay quiet when both permissions are
  already granted?
- [x] Is normal user-granted permission flow preserved without hidden grants,
  TCC database mutation, or installer-side resets?

## Capture Safety Consistency

- [x] Do requirements preserve manual Record/Stop and one-action Stop?
- [x] Do requirements avoid starting recording from permission onboarding or
  termination paths?
- [x] Do requirements avoid changing artifact writer, upload queue,
  transcription, or AI behavior?
- [x] Is active-recording quit/update behavior kept under existing capture
  safety rules rather than silently broadened here?

## System-Audio Boundary

- [x] Is Screen/System Audio permission retention separated from the
  ScreenCaptureKit capture implementation?
- [x] Is the HAL virtual driver explicitly excluded from MVP permission
  retention?
- [x] Is CoreAudio restart excluded from normal acceptance?
- [x] Is the permission quickstart clear that validation must use metadata-only
  state labels and not raw audio?

## Acceptance Criteria Quality

- [x] Can permission continuity be measured after reinstall without recording a
  meeting?
- [x] Can permission onboarding suppression be measured from app logs/UI state?
- [x] Can failure be attributed to signing drift, missing permission, or ad-hoc
  signing without ambiguous success?

## Notes

Checklist pass complete. Implementation tasks must keep this feature at the
permission/signing/lifecycle layer and avoid reopening the ScreenCaptureKit
capture pivot or parked driver work.
