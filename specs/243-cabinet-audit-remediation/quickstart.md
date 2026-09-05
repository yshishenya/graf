# F243 validation

Synthetic data only. Repository root unless noted.

1. `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
2. `apps/server/.venv/bin/python -m pytest` for affected cabinet/settings/admin
   unit+contract files; existing DB-free isolation when no DB needed. Record exact
   selection/count in evidence.
3. `bash apps/server/scripts/run_local_postgres_tests.sh` supported focused mode
   for account preferences/settings. No production mutations/provider credentials.
4. In `apps/macos`, focused `swift test --filter` cabinet suites plus
   confirmation tests; compile actual coordinator, not just source-string tests.
5. Existing loopback `tests.fixtures.calendar_visual_ui_harness:app` from
   apps/server with PYTHONPATH=src. Chrome/WebKit: six themes and four widths,
   812px/short height/200% zoom; account/calendar tooltips, profile submenu,
   list/search, upload, summary focus and warning dialog. Measure bounds/contrast;
   fixture redirects do not prove DB persistence.
6. Producer search for retired selectors/macros; catalog and current production
   renderer analytics/privacy and admin/auth compatibility coverage.
7. `git diff --check`, scoped lint, `python3 scripts/check_spec_kit_governance.py`,
   converge, correctness and Ponytail review.
8. Push PR, validate metadata/exact SHA, wait for GitHub governance-fast.
   Full CI, public signing/notarization, installed production app smoke, merge
   and deploy not performed or implied. Record every unavailable gate explicitly.
