# Feature 098 Chrome Visual QA

**Recorded**: 2026-07-13 (Europe/Moscow)
**Status**: PASS
**Browser**: Google Chrome 150, profile `Default`
**Fixture**: loopback-only synthetic server and SQLite database
**Viewport**: existing Chrome window; captured output `1800x916` for web and
embedded routes without a viewport override

## Reference Boundary

The rendered states were compared at the same viewport with the current GRAF
cabinet primitives and with the checked-in meeting-list/detail references:

- `specs/030-mvp-experience-design-system/design/reviews/v6-krisp-code-audit-2026-06-13/screenshots/v6-web-meetings.png`;
- `specs/016-meeting-dashboard-review/validation/screenshots/02-ready-detail.png`.

The review reused the existing `state-row`, `chip`, `truth-copy`, `state-list`,
sidebar, detail-panel and compact-row language. No parallel visual system or
new asset family was introduced.

## Executed States

| State | Chrome receipt |
|---|---|
| Compact list | Matched, ambiguous and generic no-context labels rendered together; protected/private state stayed generic and exposed no private reason. All dates and actions remained in one aligned row after the fix below. |
| Matched auto | Safe title, `14:00–15:00` interval, bounded two-entry roster, room/participant labels and change/clear actions rendered without overflow. |
| Recurring | Current context rendered a safe `Предыдущая встреча · 6 июл` pointer with safe readiness in the accessible name and no email/provider identifier. |
| Ambiguity | Chooser received initial focus, exposed two safe source/time radio labels, and showed no email, URL or provider-internal value. |
| Keyboard | Selecting the first radio then pressing `ArrowDown` moved checked state and focus to the second radio. |
| Correction | The selected candidate produced durable `matched_user`; the chooser disappeared and focus returned to `Контекст встречи`. |
| Clear | The inline confirmation copy preceded the mutation; the result exposed durable `data-calendar-context-state="cleared_by_user"`, kept the recording title stable and removed the roster. |
| Embedded parity | The desktop route rendered the same matched and ambiguity copy/actions. Real embedded choose and clear POSTs stayed on `/desktop/meetings/...`, produced `matched_user` then `cleared_by_user`, and returned focus to the context heading. |

## Defect Found And Closed

The first Chrome list pass found a real HTML/layout defect: the ambiguity
`Выбрать` anchor was nested inside the existing meeting-title anchor. Chrome
repaired the invalid markup by moving the inner anchor into the row grid, which
pushed the date into a new implicit row. The list also retained the legacy
`46px` row minimum despite the feature contract's `64–80px` target.

The final implementation now:

- points the existing meeting-title link at `#calendar-context-chooser`;
- renders `Выбрать` as text inside that single valid link;
- keeps deletion on the fragment-free meeting path;
- uses a `64px` row minimum in desktop and narrow layouts.

Focused recovery validation:

```text
3 passed, 0 failed, one existing Starlette warning in 1.85s
85 passed, 0 failed, one existing Starlette warning in 39.20s
```

The final screenshots and DOM checks were repeated after restarting the
synthetic server and reloading Chrome. No feature-specific clipping, overflow,
spacing drift, broken focus, or private/provider-detail exposure remained. The
unchanged canonical `infra/scripts/ci-local.sh` was then repeated on this final
diff and returned `ci_local_result=pass` with macOS `631/631`, server
`1414 passed, 4 skipped`, Ruff, compile, Compose and deployment-evidence gates
green.

## Screenshot Index

1. `screenshots/01-web-meeting-list.jpg`
2. `screenshots/02-web-matched-detail.jpg`
3. `screenshots/03-web-recurring-detail.jpg`
4. `screenshots/04-web-ambiguity-chooser.jpg`
5. `screenshots/05-web-corrected-detail.jpg`
6. `screenshots/06-web-cleared-detail.jpg`
7. `screenshots/07-embedded-matched-detail.jpg`
8. `screenshots/08-embedded-ambiguity-chooser.jpg`

All fixtures and screenshots contain synthetic labels only. The temporary QA
server was stopped and the Chrome automation tab was closed after the pass.
