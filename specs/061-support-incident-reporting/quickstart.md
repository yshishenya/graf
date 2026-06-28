# Quickstart: Support Incident Reporting

This quickstart is for the implementation slice after `$speckit-tasks`. Do not
use real secrets, live tokens, raw logs, screenshots with meeting content, raw
paths, audio, transcript text, or signed URLs as evidence.

## 1. Confirm Scope

```sh
cd /Users/yshishenya/.codex/worktrees/503d/crisp
SPECIFY_FEATURE_DIRECTORY=specs/061-support-incident-reporting \
  .specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Expected:

- Feature directory resolves to `specs/061-support-incident-reporting`.
- Current work stays on the native custody/support incident feature.
- No implementation touches are made to the server-owned WebView meeting list.

## 2. Server Focused Tests

```sh
cd /Users/yshishenya/.codex/worktrees/503d/crisp
uv --directory apps/server run pytest \
  tests/unit/test_support_incident_redaction.py \
  tests/contract/test_support_incident_contract.py \
  tests/integration/test_support_incidents.py
```

Required scenarios:

- Safe metadata-only report is accepted and server-redacted deterministically.
- Unsafe payload with raw path, token, signed URL, transcript text, meeting
  content, or email/name signal is rejected or redacted before storage.
- Successful report creates a fake private GitHub issue and returns
  `CUST-{github_issue_number}`.
- Duplicate safe reports update the same incident and issue, increment
  `affected_count`, and keep at most 5 safe affected identities.
- Missing required labels, wrong repo, public repo, GitHub outage, GitHub
  rate-limit, and support intake config failures return fallback failure.
- Durable rate-limit buckets prevent unbounded incident/issue churn and block
  GitHub mutation before the external call when the bucket is exceeded.
- GitHub issue body includes the full server-redacted metadata-only JSON block
  and no forbidden content.
- Local file completeness uses size/duration buckets, never exact durations,
  exact byte sizes, raw file names, or raw paths.
- Logs and evidence contain no secrets or private meeting content.

## 3. macOS Focused Tests

```sh
cd /Users/yshishenya/.codex/worktrees/503d/crisp
swift test --package-path apps/macos
```

Required scenarios:

- Reportable custody states expose `Отправить отчет` as the primary action.
- Failure/offline/backend-unavailable states show
  `Не удалось отправить. Скопируйте отчет и отправьте в поддержку.` and the
  visible `Скопировать отчет` button.
- Success state shows
  `Отчет отправлен. Мы разберемся. Номер: CUST-{github_issue_number}` only
  after the backend returns a GitHub issue number.
- Sent incident number persists across app refresh/restart while the custody
  item remains.
- Terminal expired/server-identity-absent/local-media-retained copy is:
  `Автоматическая отправка уже не выполнится. Локальная копия сохранена на этом Mac. Отправьте отчет, чтобы мы проверили, можно ли помочь.`
- Admin/access-policy copy is:
  `Нужна проверка доступа или политики рабочего пространства. Отправьте отчет, мы передадим детали поддержке/администратору.`
- Fallback copied report remains metadata-only.
- `Отправить отчет` and `Скопировать отчет` have accessible names,
  keyboard/focus reachability, and readable non-overlapping status text in both
  native custody surfaces.

## 4. WebView Boundary Check

Use focused tests or review evidence to confirm:

- `apps/server/src/twobrain_rec_server/cabinet/web.py` is unchanged unless a
  later explicit feature requires it.
- The server-owned WebView meeting list does not show unsent local recordings
  as native rows because of this feature.
- Native custody UI remains the place for local support report actions.

## 5. Repository Gate

```sh
cd /Users/yshishenya/.codex/worktrees/503d/crisp
infra/scripts/ci-local.sh
```

Expected:

- Local CI passes.
- Evidence notes mention the selected lane: `high-risk-feature`.
- Evidence contains only safe metadata and no issue body examples with secrets
  or private meeting content.

## 6. GitHub Issue Safety Manual Smoke

Use the fake GitHub client in automated tests by default. If a real integration
smoke is explicitly approved later, use a test-safe report and verify:

- Target repo is exactly `yshishenya/crisp`.
- Target repo is private.
- Required labels exist before issue mutation.
- Created/updated issue title matches:
  `[061][P1][support/custody] Пользовательская проблема: ... (...)`
- Issue labels include `needs-triage`, `feature:061`, `type:bug`,
  `area:macos`, `area:api`, `area:privacy`, `source:user-report`, and
  `privacy:metadata-only`.
- Issue body follows the required Russian section order and contains the full
  server-redacted metadata-only JSON block.
- Closing or updating a deduped issue does not remove the full safe
  metadata-only JSON block unless an explicit owner-controlled manual redaction
  policy is represented.
- User-facing desktop success uses `CUST-{github_issue_number}`.

Do not paste real credentials, raw logs, raw local paths, audio, transcript
text, signed URLs, or private meeting content into PR evidence.
