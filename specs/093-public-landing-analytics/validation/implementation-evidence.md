# Implementation Evidence: Public Landing Analytics

**Feature**: `093-public-landing-analytics`

**Current lane**: high-risk product/privacy/egress implementation.

**Release state**: implementation readiness only. No production deploy, live
provider smoke, provider dashboard access, paid campaign launch, or live
provider identifiers are part of this evidence unless a separate release or
campaign-readiness gate is approved.

## Baseline Review

Reviewed before implementation:

- `specs/093-public-landing-analytics/spec.md`
- `specs/093-public-landing-analytics/plan.md`
- `specs/093-public-landing-analytics/research.md`
- `specs/093-public-landing-analytics/data-model.md`
- `specs/093-public-landing-analytics/contracts/public-analytics-contract.md`
- `specs/093-public-landing-analytics/contracts/analytics-provider-setup.md`
- `specs/093-public-landing-analytics/contracts/phase2-activation-contract.md`
- `specs/093-public-landing-analytics/quickstart.md`
- `apps/server/src/twobrain_rec_server/public/web.py`
- `apps/server/src/twobrain_rec_server/public/templates.py`
- `apps/server/src/twobrain_rec_server/public/templates/public/landing.html`
- `apps/server/src/twobrain_rec_server/public/templates/public/download.html`
- `apps/server/tests/unit/test_public_landing.py`
- `apps/server/tests/contract/test_public_landing_contract.py`
- `apps/server/src/twobrain_rec_server/config.py`
- `infra/env/rec.production.env.example`

Baseline findings:

- Public web currently exposes `/` and `/download` through server-rendered
  Jinja templates.
- Public pages currently use local static assets and no analytics provider
  scripts.
- There is no existing public analytics runtime configuration, legal-page
  routing, consent UI, analytics event catalog, or analytics browser
  controller.
- Existing landing tests assert local assets, current copy, CTA destinations,
  keyboard skip link, and download handoff behavior.
- Phase 1 must keep Google, GA4, Google Ads, GTM, PostHog, Clarity, Amplitude,
  Mixpanel, Matomo, custom analytics storage, and live provider IDs out of the
  implementation.

## Validation Log

### 2026-07-08 - Setup Review

Commands:

```sh
python3 .specify/extensions/github-issue-canon/scripts/ensure_issue_canon.py
python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py
python3 -m py_compile \
  .specify/extensions/github-issue-canon/scripts/issue_canon_common.py \
  .specify/extensions/github-issue-canon/scripts/ensure_issue_canon.py \
  .specify/extensions/github-issue-canon/scripts/normalize_issue_canon.py \
  .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py
git diff --check
```

Result:

- `github-issue-canon: OK (68 Spec Kit issue(s) checked)`
- `git diff --check` passed

Notes:

- This setup evidence does not validate analytics behavior yet; focused
  analytics tests are added in later tasks.
