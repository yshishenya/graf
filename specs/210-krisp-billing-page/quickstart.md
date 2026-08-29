# Quickstart: Feature 210 validation

## Preconditions

- Use synthetic/local fixture data only; never record private meeting, account,
  payment or reference screenshots in git.
- Do not click final checkout, alter subscription/payment method, or invoke a
  production provider.
- Start from `210-krisp-billing-page` and record exact SHA/worktree status.

## Focused automated checks

```sh
cd apps/server
PYTHONPATH=src uv run pytest -q \
  tests/contract/test_billing_ui.py \
  tests/contract/test_billing_accessibility.py \
  tests/integration/test_billing_usability.py

cd ../..
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'CabinetBillingRuntimeTests|DesktopCabinetRoutePolicyTests|DesktopCabinetNavigationRequestPolicyTests|DesktopCabinetWorkspaceTests|EmbeddedCabinetWebViewZoomTests|AppControlAccessibilityTests'

git diff --check
infra/scripts/ci-local.sh --fast
```

## Safe local runtime

Start the documented local cabinet with synthetic account/billing fixtures.
Exercise `/billing`, `/billing/plans`, `/billing/checkout?cycle=month`,
`/billing/checkout?cycle=year`, promo preview, `/billing/history` and one invoice
detail. Stop before the final checkout/start action.

For each required state (free, trial, personal active/cancelled/expired,
owner/member, unavailable, pending/unknown/reconciliation/manual-resolution,
empty payment method/history, validation/provider error), confirm:

- one correct heading/status and at most one safe primary action;
- truthful amount/cycle/next charge and no competing checkout while pending;
- no DOM/main/section horizontal overflow;
- no clipped amount, focus ring, disclosure, consent or primary action;
- keyboard order, Escape/focus return for disclosures, named errors/live regions;
- no relevant browser console error/warn;
- usable links/forms with JavaScript disabled.

## Browser geometry matrix

Run dark and light themes at 390×844, 768×1024, 1024×768, 1280×720 and
1440×900. Repeat critical 390 and 768 layouts at 200% zoom/text. Check reduced
motion and forced/high contrast where supported. Capture only synthetic GRAF
screenshots.

## Installed macOS application

Using the exact local GRAF build, open billing inside the native shell at:

- 1040×680, inspector collapsed and expanded;
- 1280×760, inspector collapsed and expanded;
- 1440 fullscreen, inspector collapsed and expanded;
- minimum and standard window at 200% WebView zoom, then restore actual size.

Confirm overview → plans → checkout preview → history, sidebar/rail state,
native Record/Stop reachability, focus/AX names, external sanitized offer route,
and absence of provider navigation before explicit payment. If Computer Use is
unavailable, record the interruption and do not claim installed-app PASS.

## Fidelity ledger

Compare the final synthetic GRAF rendering to the observed KRISP baseline in
five categories: IA/order, composition/geometry, typography/color,
interaction states, responsive/desktop embedding. Record every material
difference and classify allowed deviations. No correctable material mismatch
may remain at closeout.

## Closeout boundary

Reconcile completed `tasks.md` items and GitHub issues with actual evidence.
Commit, PR, merge, real payment, release and deploy remain blocked pending an
explicit separate user authorization.
