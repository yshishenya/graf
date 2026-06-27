# Research: Support Incident Reporting

## Decision: Keep The Boundary In Desktop API And Support Services

The support report endpoint will live under the backend API/service layer as
`POST /api/v1/desktop/support-incidents`. This matches the existing desktop
API shape in `apps/server/src/twobrain_rec_server/api/ingest.py`, keeps tenant
and device dependencies on the server side, and avoids touching
`apps/server/src/twobrain_rec_server/cabinet/web.py`.

Rejected alternatives:

- Desktop direct-to-GitHub submission: rejected because the desktop must not
  hold tracker credentials, ask for a GitHub account, or publish incident data.
- `cabinet/web.py` route: rejected because feature 058 owns the server WebView
  meeting list and this feature is a native custody/support action.
- Copy-only support flow: rejected because the product goal is a clear primary
  `Отправить отчет` action with an incident number.

## Decision: Success Requires A Private GitHub Issue

The server will treat submission as successful only after creating or updating
a private GitHub issue in `yshishenya/crisp` and receiving the issue number.
The user-visible incident number is `CUST-{github_issue_number}`. A persisted
internal incident without a GitHub issue is useful for audit/retry, but it is a
failed send from the user's point of view and must return the copy fallback.

Implementation constraints:

- Confirm target repo owner/name is exactly `yshishenya/crisp`.
- Confirm the target repo is private before issue mutation.
- Create/update issues only from the server using server-owned credentials.
- Use GitHub REST issue APIs with title, Markdown body, and labels.
- Treat GitHub outage, rate limiting, validation errors, missing labels, wrong
  repo, or public repo as fallback failure for the desktop.

Rejected alternatives:

- Internal-only support records: rejected by clarification; v1 success means a
  private GitHub issue exists.
- Public GitHub issues: rejected by privacy requirements.
- Dynamic problem-code labels: rejected because labels must remain bounded and
  managed for support agents.

Official GitHub docs consulted:

- GitHub issue template/forms docs:
  https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository
- GitHub REST Issues API:
  https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28

## Decision: Use Existing `httpx` For GitHub Calls

`apps/server/pyproject.toml` already depends on `httpx`. The implementation
should add a small server-side GitHub issue client that uses `httpx` with
bounded timeouts and test fakes. No new HTTP dependency is needed.

Rejected alternatives:

- Add a GitHub SDK: rejected for v1 because the required operations are small,
  the dependency surface would grow, and tests need deterministic fakes.
- Use synchronous shell `gh`: rejected because server runtime must not depend
  on local CLIs or leak environment state into logs.

## Decision: Redaction Is Allowlist-First And Server-Enforced

The desktop can assemble a metadata-only report, but the backend must validate
and redact it again before storage or issue generation. The server will build a
new deterministic safe report from an allowlist of fields, reject or replace
unsafe values with `unknown`, `not_applicable`, or `redacted_metadata`, and
generate the GitHub JSON block from that server-redacted object only.

Forbidden content includes audio bytes, transcript text, meeting content, raw
paths, filenames that reveal private content, tokens, cookies, credentials,
signed URLs, upload tokens, raw logs, screenshots, names, emails, account
labels, and other user-identifying display strings. v1 uses safe ids or
fingerprints instead of human-identifying values.

Rejected alternatives:

- Trust desktop `metadata_only`: rejected because client payloads are not a
  trust boundary.
- Store raw desktop payload for debugging: rejected because diagnostics must be
  safe by construction.

## Decision: Dedupe By Stable Safe Root Cause And Aggregate

The backend will derive a deterministic dedupe key from safe problem context:
stable `problem_code`, `failure_category`, `retry_class`, safe workspace/user
or workspace/device scope, app/build context, and a safe root-cause fingerprint.
Duplicate reports update the same support incident and GitHub issue, increment
`affected_count`, refresh timestamps, and keep at most 5 safe affected
identities in the generated issue body.

Rejected alternatives:

- One GitHub issue per local record: rejected because groups of repeated
  custody failures must aggregate.
- Unlimited affected identities in the issue body: rejected because report
  bodies must stay bounded and safe for support agents.
- Dedupe only by local recording id: rejected because duplicates should group
  by root cause, not by individual local files.

## Decision: Rate Limit Per Safe Scope And Dedupe Key

Support intake must apply rate limits by safe workspace, user/device
fingerprint, and dedupe key. Rate limiting prevents repeated failures from
creating unbounded persisted incidents or GitHub updates. Rate-limited desktop
submissions return the same copy fallback shape as other unavailable support
intake states.

Rejected alternatives:

- Rely only on GitHub API rate limits: rejected because rate control belongs to
  the product boundary and must work before external mutation.

## Decision: Validate Labels Before Enabling Issue Creation

The required labels are:

- `needs-triage`
- `feature:061`
- `type:bug`
- `priority:P0`, `priority:P1`, or `priority:P2`
- `area:macos`
- `area:api`
- `area:privacy`
- `source:user-report`
- `privacy:metadata-only`

Optional labels may be added only from the bounded project canon when materially
applicable, such as `area:lifecycle`, `area:observability`, or gate labels.
Missing required labels are a configuration failure; the server must not create
untagged support issues.

Rejected alternatives:

- Create missing labels at report time: rejected because issue creation should
  not need label administration privileges on the hot path.
- Proceed without labels: rejected because labels are part of the required
  routing contract for the future triage agent.

## Decision: Native UX Has Primary Send And Copy Fallback

The native custody UI will show `Отправить отчет` as the primary action when a
support/admin/terminal custody report is available. Success copy is:
`Отчет отправлен. Мы разберемся. Номер: CUST-{github_issue_number}`. Failure
copy is: `Не удалось отправить. Скопируйте отчет и отправьте в поддержку.`
The existing safe report copy remains a secondary/fallback action.

Technical custody enums remain available in metadata for support, but the main
user explanation must be human-readable:

- Terminal expired, no server identity, local media retained:
  `Автоматическая отправка уже не выполнится. Локальная копия сохранена на этом Mac. Отправьте отчет, чтобы мы проверили, можно ли помочь.`
- Admin/access issue:
  `Нужна проверка доступа или политики рабочего пространства. Отправьте отчет, мы передадим детали поддержке/администратору.`

Rejected alternatives:

- Continue showing only `Скопировать отчет`: rejected because users do not know
  what to do with raw report text.
- Expose enum values as primary explanations: rejected because support states
  need plain language.

## Decision: Retain Full Safe Metadata In The Private Issue

Clarification requires the full server-redacted metadata-only report to remain
inside the private GitHub issue indefinitely for the planned triage agent. The
system may manually redact only after a confirmed privacy/security incident or
explicit owner-controlled retention policy change.

Rejected alternatives:

- Store metadata only in the database and link from GitHub: rejected because the
  triage agent should process issues directly.
- Auto-redact closed issues: rejected by clarification and support workflow.
