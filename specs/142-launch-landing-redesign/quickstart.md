# Quickstart: Launch Landing Redesign

## Prerequisites

- Work from the feature worktree.
- Use synthetic screenshots only.
- Do not enable paid checkout until the approved catalog, fiscal flow and
  effective payment terms are present.

## Focused contract validation

```bash
cd apps/server
uv run pytest \
  tests/unit/test_public_landing.py \
  tests/contract/test_public_landing_contract.py \
  tests/contract/test_public_analytics_contract.py -q
```

Expected: all focused public template, asset, analytics, focus and claim-boundary checks pass.

## Static source checks

```bash
rg -n "2brain Rec|Анна|Игорь|Борис|790|7 900|за рубеж ничего|Рабочая редакция|Phase 1|campaign launch" \
  apps/server/src/twobrain_rec_server/public/templates/public/landing.html \
  apps/server/src/twobrain_rec_server/public/templates/public/download.html
```

Expected: no obsolete brand, personal-style demo names, unapproved price or blocked claims in public templates.

## Local browser matrix

Start the existing server through the repository's normal local development path, then inspect `/`, `/download`, `/privacy`, `/cookies`, `/terms`, `/offer` and `/analytics-consent` at:

- 1440×1000
- 1024×768
- 768×1024
- 390×844
- 320×800
- 280×800

For each viewport:

1. Confirm zero horizontal overflow.
2. Follow the skip link and header anchors with keyboard only.
3. Confirm visible focus for every actionable element.
4. Confirm all `Скачать GRAF` actions reach `/download` and `Войти` reaches the existing login path.
5. Confirm Windows/Linux statuses are not focusable controls.
6. Accept, customize, reject and revoke consent; confirm analytics, attribution
   and replay follow their independent categories.
7. Open a URL with query/hash and confirm no provider hit contains either.
8. Disable images and confirm every proof remains understandable.
9. Enable reduced motion and confirm smooth scroll/transforms are removed.

## Visual QA

1. Capture `/` at 1440×1000 and full-page height.
2. Open the capture and `design/selected-direction-3.png` together.
3. Compare header scale, hero hierarchy, 12-column balance, numbered chapter rhythm, screenshot integration, dividers, whitespace, CTA weight and final platform note.
4. Record findings in `design-qa.md`.
5. Fix all P0/P1/P2 differences that do not violate the public truth contract.
6. Repeat until `design-qa.md` says `final result: passed`.

## Repository gate

```bash
infra/scripts/ci-local.sh --fast
```

Expected before closeout: fast local CI passes. Full CI, signed installer verification and deployment smoke remain separate release work.
