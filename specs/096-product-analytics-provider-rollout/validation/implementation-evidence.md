# Implementation Evidence: Product Analytics Provider Rollout

**Feature**: `096-product-analytics-provider-rollout`

**Evidence status**: `implementation_validated_review_remediated`

This file records what has been completed for planning, implementation,
convergence, and review remediation. Future live rollout evidence must follow
the same metadata-only rules. It is safe to commit because it contains no live
secrets, counter IDs, project keys, payloads, screenshots, visitor/account
identifiers, meeting content, transcripts, audio, signed URLs, local paths,
cookies, or private provider exports.

## Planning Pass Evidence

| Item | Status | Evidence |
| --- | --- | --- |
| Risk lane | complete | High-risk Spec Kit provider/infrastructure rollout selected. |
| Baseline | complete | 096 starts after merged/deployed 094 scaffold and reuses 093 public analytics baseline. |
| Specify | complete | `spec.md` created for 096. |
| Clarify | complete | Clarifications recorded for PostHog first-party scope, Yandex counter reuse, hosting/domain posture, PostHog autocapture everywhere, and two Yandex offline conversions. |
| Plan | complete | `plan.md`, `research.md`, `data-model.md`, contracts, quickstart, and validation templates created. |
| Checklist | complete | `checklists/provider-rollout.md` reviewed against 096 artifacts. All 52 requirement-quality checks are complete after adding explicit same-server PostHog resource-threshold requirements. |
| Tasks | complete | `tasks.md` generated with 90 dependency-ordered tasks across setup, foundation, four user stories, and final validation. |
| Analyze | complete | `$speckit-analyze` found no critical blockers and identified RBAC/audit, lifecycle, deploy-dry-run, and placeholder consistency remediation. |
| Analyze remediation | complete | Planning artifacts and tasks were tightened so RBAC/audit access model, provider retention/deletion lifecycle truth, PostHog deploy dry-run handoff, and concrete script/doc paths are explicit before implementation. |
| Repeat analyze remediation | complete | Secret inventory owner/rotation coverage and stale plan wording were tightened before `$speckit-taskstoissues`. |
| Task-to-issues sync | complete | `$speckit-taskstoissues` created 90 GitHub issues for `feature:096`; issue canon validation passed. |
| Baseline validation before implementation | complete | `infra/scripts/ci-local.sh` passed before implementation: server tests `1160 passed, 4 skipped`, lint passed, compile passed, compose config passed, deployment evidence scan passed. |
| Agent context | complete with local tool caveat | Official agent-context helper was attempted, but the local Python environment lacked `PyYAML`; the managed `AGENTS.md` Spec Kit plan pointer was updated manually to the 096 plan path. |
| Implementation | complete | 096 provider layer implementation, convergence fixes, and review remediation are complete on the feature branch. Production deploy execute, live provider dashboard verification, live secret creation, product rollout readiness, and paid campaign launch remain separate blocked steps. |
| Production deploy | not started | `cd-remote.sh --execute` not run in this pass. |
| Paid campaign launch | blocked | Campaign launch remains outside 096 readiness. |

## Implementation Pass Evidence

| Task Range | Status | Metadata-Only Evidence |
| --- | --- | --- |
| T001-T008 Phase 1 setup | complete | Created durable PostHog, Yandex, rollback, PostHog infra, Compose handoff placeholder, runtime env example, and backup/restore shells. |
| Phase 1 no-deploy state | complete | `cd-remote.sh --execute` was not run; no live provider ID, project key, OAuth token, cookie, client ID, raw payload, screenshot, meeting content, transcript, audio, signed URL, or private local path was added to committed artifacts. |
| Phase 1 validation | complete | `docker compose -f infra/posthog/docker-compose.posthog.yml config` passed; `git diff --check` passed; file existence checks passed. |
| T009-T022 Phase 2 foundation | complete | Added provider config tests, env/secret propagation tests, provider secret redaction tests, page inventory tests, retention/lifecycle tests, 096 runtime flags, provider config value objects, redacted secret helpers, expanded forbidden-field coverage, 096 page inventory, provider lifecycle records, catalog output, rec-api-only env wiring, Docker secret mounts, PostHog dry-run handoff, env owner/rotation comments, and expanded no-live-secret scans. |
| Phase 2 owner/rotation inventory | complete | `default_provider_secret_inventory()` covers PostHog project key, stack secret, DB password, Redis/object-storage placeholders, Yandex counter, Yandex OAuth token, and product analytics flags with owner roles, rotation notes, committed defaults, propagation tests, and redacted evidence states. |
| Phase 2 redacted evidence status | complete | Provider config and secret helpers return `configured_redacted` / `not_configured` metadata only; focused tests verify synthetic values do not appear in redacted dicts or repr output. |
| Phase 2 validation | complete | `PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_product_analytics_provider_config.py tests/integration/test_product_analytics_provider_env.py tests/unit/test_product_analytics_provider_secrets.py tests/contract/test_product_analytics_page_inventory_096.py tests/contract/test_product_analytics_provider_retention.py tests/contract/test_product_activation_analytics_contract.py tests/unit/test_product_activation_analytics.py tests/integration/test_product_activation_analytics_rollout.py` passed: `45 passed`. `docker compose -f infra/docker-compose.yml config` passed. `infra/scripts/cd-remote.sh --dry-run` passed and reported `posthog_stack_handoff=dry_run_metadata_only`. `git diff --check` passed. |
| Phase 2 remaining blockers | blocked for rollout, not implementation | No production deploy execute, live provider secret creation, live PostHog stack start, Yandex offline upload, dashboard verification, legal/security/QA approval, product rollout readiness, or paid campaign launch has been performed. |
| T023-T037 US1 PostHog primary workspace | complete | Added PostHog provider contract tests, PostHog client tests, PostHog stack tests, provider smoke contract tests, self-hosted PostHog handoff labels/metadata/resource/health/secret boundaries, official generated runtime requirement, PostHog env example, DNS/TLS/resource/disk-full/RBAC/audit/move-out runbook details, backup/restore rehearsal procedure, PostHog readiness metadata, secret-file status checking, dry-run/live-safe-blocked client behavior, provider smoke script, and metadata-only dashboard evidence. |
| US1 validation | complete | `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_product_analytics_posthog_provider_contract.py tests/unit/test_product_analytics_posthog_provider.py tests/integration/test_product_analytics_posthog_stack.py tests/contract/test_product_analytics_provider_smoke_contract.py tests/unit/test_product_analytics_provider_config.py tests/integration/test_product_analytics_provider_env.py tests/unit/test_product_analytics_provider_secrets.py tests/contract/test_product_analytics_page_inventory_096.py tests/contract/test_product_analytics_provider_retention.py` passed: `34 passed`. |
| US1 deploy state | no execute | `infra/scripts/run-product-analytics-provider-smoke.sh` uses synthetic metadata and dry-run checks only. `infra/scripts/cd-remote.sh --dry-run` has a separate PostHog handoff; `cd-remote.sh --execute` was not run. |
| T038-T051 US2 Yandex measurement | complete | Added Yandex provider contract tests, offline conversion tests, page scope tests, env/secret tests, offline row builder with redacted identity source and deterministic dedupe/batch metadata, Yandex OAuth secret-file status handling, attribution bridge allowed identity-present fields, inventory-aware product Yandex context, browser Yandex gate, Yandex runbook details, provider smoke Yandex scenarios, and metadata-only dashboard evidence. |
| US2 validation | complete | `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_product_analytics_yandex_provider_contract.py tests/unit/test_product_analytics_yandex_offline_provider.py tests/integration/test_product_analytics_yandex_page_scope.py tests/integration/test_product_analytics_yandex_env.py tests/unit/test_public_analytics.py tests/contract/test_public_analytics_contract.py tests/contract/test_product_activation_analytics_contract.py tests/unit/test_product_activation_analytics.py` passed: `56 passed`. `infra/scripts/run-product-analytics-provider-smoke.sh` passed with `yandex_counter=runtime_only_redacted`, `yandex_public_baseline=preserved`, `yandex_blocked_pages=pass`, `yandex_auth=redacted_status_only`, `yandex_offline=dry_run_two_conversions`, and `yandex_duplicates=dedupe_key_stable`. |
| US2 live state | not executed | No live Yandex upload was performed from committed evidence. Runtime wiring is ready for secret-file backed smoke/live-safe validation, but paid campaign launch remains blocked. |
| T052-T068 US3 PostHog autocapture governance | complete | Added rendered-page PostHog autocapture tests for all current/future browser page classes, credential suppression/private attribute page tests, replay/Webvisor boundary tests, macOS PostHog-only direct-route tests, browser provider context helpers, public/cabinet/admin provider template injection, JS PostHog autocapture initialization separate from Yandex/replay, replay masking boundaries that keep `data-ph-mask` without provider-wide `data-ph-no-capture`, direct desktop PostHog-only request construction, provider page validation script, and 096 provider addendum docs. |
| US3 validation | complete | `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_product_analytics_posthog_autocapture_contract.py tests/integration/test_product_analytics_autocapture_pages.py tests/contract/test_product_analytics_replay_webvisor_boundaries.py tests/contract/test_product_activation_analytics_contract.py tests/unit/test_public_analytics.py tests/contract/test_public_analytics_contract.py tests/contract/test_product_analytics_yandex_provider_contract.py tests/integration/test_product_analytics_yandex_page_scope.py` passed: `44 passed`. `swift test --package-path apps/macos --filter ProductActivationAnalyticsContractTests` passed: `8 tests, 0 failures`. `infra/scripts/validate-product-analytics-provider-pages.sh` passed with `posthog_autocapture=current_and_future_pages_enabled`, `posthog_replay=disabled`, `yandex_public_scope=public_landing_public_download`, `webvisor_maps_forms=disabled`, `desktop_direct_posthog=contract_tested`, and `desktop_direct_yandex=blocked`. |
| US3 rollout state | governed, no replay/campaign launch | First-party PostHog autocapture is intentionally broad and reversible. PostHog replay, Yandex Webvisor/click map/scroll map/form analytics, direct desktop Yandex egress, paid campaign launch, and product rollout readiness remain blocked by separate approvals/evidence. |
| T069-T080 US4 smoke/dashboard/rollback/blockers | complete | Added smoke output contract tests, rollback contract tests, dashboard metadata-only evidence tests, readiness blocker integration tests, unified smoke output for dashboard/blocker/no-secret/rollback status, provider page validation output, dry-run rollback script, rollback runbook details, readiness states for legal/privacy/security/QA/disclosure/dashboard/RBAC/lifecycle/deploy/smoke/product rollout/campaign launch, dashboard evidence closeout metadata, and quickstart final validation order. |
| US4 validation | complete | `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_product_analytics_provider_smoke_output.py tests/contract/test_product_analytics_provider_rollback.py tests/contract/test_product_analytics_dashboard_evidence.py tests/integration/test_product_analytics_provider_readiness_blockers.py tests/contract/test_product_analytics_provider_smoke_contract.py` passed: `7 passed`. Smoke and rollback script execution inside tests used metadata-only dry-run output. |
| US4 blocker state | blocked for rollout/campaign, ready for validation | Readiness can report `infra_smoke_ready` for technical provider setup while `product_rollout_allowed=false` and `campaign_launch_allowed=false`. Legal/privacy/security/QA/disclosure/product/campaign blockers remain separate from provider smoke. |
| T081 focused server validation | complete | `PYTHONPATH=src uv run --extra dev pytest -q` over the 096/094 product analytics, public analytics, provider config, PostHog, Yandex, autocapture, smoke, rollback, dashboard, readiness, and cabinet-shell contract files passed: `107 passed`. |
| T082 focused macOS validation | complete | `swift test --package-path apps/macos --filter ProductActivationAnalyticsContractTests` passed: `8 tests, 0 failures`. |
| T083 provider smoke script | complete | `infra/scripts/run-product-analytics-provider-smoke.sh` passed with `provider_smoke_result=pass`, `posthog_stack=config_valid`, `posthog_stack_contract=handoff_valid`, `posthog_runtime_source=official_posthog_hobby_generated_compose_required`, `posthog_delivery=dry_run`, `posthog_live_safe_delivery=transport_verified`, `posthog_web_direct=render_config_present`, `posthog_desktop_direct=contract_tested`, `yandex_offline=dry_run_two_conversions`, `yandex_live_safe_upload=transport_verified`, `dashboard_readiness=metadata_only_live_safe_verified`, `dashboard_goal_visibility=metadata_only_contract_verified`, `product_rollout=blocked`, `campaign_launch=blocked`, `no_secret_scan=metadata_only_pass`, and `rollback_status=ready_not_executed`. |
| T084 provider page validation script | complete | `infra/scripts/validate-product-analytics-provider-pages.sh` passed with `provider_page_validation=pass`, `posthog_autocapture=current_and_future_pages_enabled`, `posthog_replay=disabled`, `posthog_replay_boundary=mask_only_no_no_capture`, `yandex_public_scope=public_landing_public_download`, `webvisor_maps_forms=disabled`, `desktop_direct_posthog=contract_tested`, and `desktop_direct_yandex=blocked`. |
| T085 provider rollback script | complete | `infra/scripts/rollback-product-analytics-providers.sh` passed in default dry-run mode with `provider_rollback_result=pass`, `rollback_execution=dry_run_no_state_change`, `target=all`, `product_impact=measurement_gap_only`, PostHog/Yandex/provider validation switch metadata, `normal_product_workflows=preserved`, and `secrets=not_printed`. |
| T086 no-secret/evidence scan | complete | Initial broad scan matched existing intentional macOS redaction fixtures only. The refined live-looking scan over `specs/096-product-analytics-provider-rollout`, `docs/analytics`, `infra`, `apps/server/src/twobrain_rec_server/product_analytics`, and `apps/macos` passed with `no_secret_scan=pass`. |
| T087 full local CI | complete | `infra/scripts/ci-local.sh` passed after convergence and review-remediation fixes: server tests `1231 passed, 4 skipped`, server lint passed, Python compile passed, RLS hardening validation boundary stayed safely blocked on missing production database probe, production compose config passed, deployment evidence scan passed, and `ci_local_result=pass`. |
| T088 deploy dry-run | complete | `infra/scripts/cd-remote.sh --dry-run` passed with `deploy_result=dry_run`, branch `096-product-analytics-provider-rollout`, required deploy steps listed, `posthog_stack_handoff=dry_run_metadata_only`, `posthog_stack_contract=infra/posthog/docker-compose.posthog.yml`, `posthog_stack_runtime_source=official_posthog_hobby_generated_compose_required`, and `posthog_stack_execute=requires_explicit_release_approval`. |
| T089 changelog | complete | `CHANGELOG.md` updated under `Unreleased` for 096 behavior, security, docs, and operations notes. |
| T090 task closeout | complete | `tasks.md` reviewed after validation; all implementation tasks are dependency-ordered and selected risk/validation lane remains high-risk Spec Kit provider/infrastructure rollout. |
| T091 convergence approval/campaign fix | complete | Added `live_safe` validation mode and explicit legal/privacy/security/QA/disclosure/dashboard/provider-smoke/rollback/live-provider approval gates. `campaign_launch_allowed` is always `false` in 096 redacted provider config and readiness output. |
| T092 convergence PostHog live-safe server delivery | complete | PostHog wrapper now loads the project key from a secret file, builds self-hosted `/capture/` requests, handles accepted/provider/network/configuration statuses, preserves retry/loss metadata, and returns redacted result metadata only. |
| T093 convergence browser autocapture delivery | complete | Browser autocapture now uses a first-party proxy endpoint (`/api/v1/product-analytics/posthog-web-capture`) with `sendBeacon`/`fetch`, no PostHog Cloud/CDN SDK, no replay enablement, and credential suppression preserved. |
| T094 convergence desktop PostHog route | complete | macOS direct provider config now supports first-party capture endpoint and `server_injected_redacted` project-key state. The request body uses PostHog-style `event`, `distinct_id`, `properties`, and `api_key_state` without shipping provider secrets. |
| T095 convergence Yandex live-safe offline upload | complete | Yandex exporter now builds multipart offline upload requests for exactly `desktop_account_connected` and `first_value_session_completed`, reads OAuth from secret file, records provider statuses redacted, and keeps direct desktop Yandex blocked. |
| T096 convergence smoke/dashboard evidence | complete | Provider smoke now verifies dry-run plus live-safe fake-transport delivery for PostHog and Yandex, checks dashboard/goal metadata contract markers, and keeps committed output metadata-only. Dashboard evidence was updated with convergence proof and blockers. |
| Phase 8 convergence validation | complete | Focused Python validation passed: `52 passed`. Focused Ruff check passed. `infra/scripts/run-product-analytics-provider-smoke.sh` passed with new live-safe markers. `swift test --package-path apps/macos --filter ProductActivationAnalyticsContractTests` passed: `8 tests, 0 failures`. |
| Review remediation: rendered PostHog pages | complete | Real rendered-page wiring now passes provider config through public/auth/cabinet/settings/calendar/detail/deletion/desktop routes. Focused validation `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_product_analytics_posthog_autocapture_contract.py tests/integration/test_product_analytics_autocapture_pages.py tests/unit/test_product_analytics_posthog_provider.py tests/unit/test_product_analytics_yandex_offline_provider.py tests/integration/test_product_analytics_yandex_page_scope.py` passed: `23 passed`. |
| Review remediation: PostHog first-party data vs secrets | complete | Self-hosted PostHog now allows first-party product-visible identity/context in provider smoke, but `access_token`/token-like, credential, signed URL, local-path, and raw-content material is rejected before dry-run success. `infra/scripts/run-product-analytics-provider-smoke.sh` passed with `posthog_secret_payload_rejected=pass`. |
| Review remediation: Yandex offline attribution linkage | complete | Yandex offline `UserId` rows now require explicit runtime `yandex_user_id_present=true` plus stable GRAF pseudonymous UserID, and browser JS binds that ID through Yandex `setUserID`/`userParams` on inventory-approved product pages. A plain `yandex_client_id_present` flag no longer uploads the GRAF pseudonym as `UserId`. |
| Review remediation: docs/runbooks | complete | PostHog and Yandex runbook statuses were updated from shell to validated/remediated. Dashboard evidence now records rendered-page proof, secret-material rejection, and Yandex UserID binding caveats. Production deploy execute, live provider dashboards, product rollout readiness, and paid campaign launch remain blocked. |
| Final review-remediation validation | complete | Focused provider/cabinet/OpenAPI validation passed with `68 passed`; provider smoke passed with `posthog_secret_payload_rejected=pass`, `posthog_live_safe_delivery=transport_verified`, and `yandex_live_safe_upload=transport_verified`; provider page validation passed with `posthog_autocapture=current_and_future_pages_enabled` and `webvisor_maps_forms=disabled`; full `infra/scripts/ci-local.sh` passed with `1231 passed, 4 skipped` and `ci_local_result=pass`. |
| Release-readiness preflight | complete | PostHog runtime examples now use the planned public analytics domain `analytics.2brain.pro` instead of an internal placeholder. DNS preflight found `rec.2brain.pro` at `162.120.16.66`; public resolvers `1.1.1.1` and `8.8.8.8` plus authoritative nameservers `launch1.spaceship.net` and `launch2.spaceship.net` resolve `analytics.2brain.pro` to `162.120.16.66`. No committed live provider secrets were found. `infra/scripts/cd-remote.sh --dry-run`, `infra/scripts/run-product-analytics-provider-smoke.sh`, `infra/scripts/validate-product-analytics-provider-pages.sh`, `infra/scripts/rollback-product-analytics-providers.sh`, `docker compose -f infra/posthog/docker-compose.posthog.yml --env-file infra/posthog/posthog.production.env.example config`, focused env/PostHog stack tests, `git diff --check`, and full `infra/scripts/ci-local.sh` passed after the domain alignment. Production execute still requires explicit approval, official generated PostHog runtime setup, and live secret/runtime setup outside git. |
| Pre-commit review remediation | complete | Admin rendered pages now receive authenticated pseudonymous PostHog identity when a principal is present. PostHog Compose no longer defaults to mutable `latest`; runtime must supply a reviewed pinned `POSTHOG_IMAGE` before production execute. A second pre-commit pass found the committed Compose was too simplified to be a full self-hosted PostHog runtime, so it is now explicitly a GRAF handoff/preflight contract and the runbook/deploy dry-run require the official generated PostHog Docker Compose runtime. Infra PostHog docs moved from shell status to validated/remediated. |
| Final pre-commit validation | complete | After the admin identity, image pinning, official PostHog runtime-source remediation, and legacy/fallback cleanup, focused provider/OpenAPI/rendered-page validation passed with `36 passed`; `infra/scripts/run-product-analytics-provider-smoke.sh`, `infra/scripts/validate-product-analytics-provider-pages.sh`, `infra/scripts/rollback-product-analytics-providers.sh --dry-run`, and `infra/scripts/cd-remote.sh --dry-run` passed; `swift test --package-path apps/macos --filter ProductActivationAnalyticsContractTests` passed with `9 tests, 0 failures`; `docker compose -f infra/posthog/docker-compose.posthog.yml config` and the same command with `--env-file infra/posthog/posthog.production.env.example` passed; `git diff --check` passed; live-looking diff scans found no real provider secrets, keys, tokens, cookies, raw payloads, local paths, or signed URLs; full `infra/scripts/ci-local.sh` passed after cleanup with `1233 passed, 4 skipped` and `ci_local_result=pass`. |
| Legacy/fallback cleanup | complete | Removed the admin `x-workspace-id` fallback for analytics workspace pseudonyms, removed shared anonymous distinct-id fallbacks from desktop-direct and server-mediated PostHog provider delivery, required desktop-direct `distinct_id` in OpenAPI/runtime, replaced Yandex offline anonymous dedupe material with explicit runtime-identity-pending metadata, removed stale `(partial)` task wording, and kept only intentional browser anonymous identity for public/auth pages. |

## Official Documentation Reviewed

Planning research reviewed official provider documentation for:

- self-hosted PostHog operations and operator responsibility;
- self-hosted PostHog environment configuration;
- self-hosted PostHog session replay storage;
- Yandex Metrica OAuth authorization;
- Yandex Metrica quick start and required scopes;
- Yandex Metrica offline conversion upload.

See [research.md](../research.md) for decisions and source links.

## Required Future Live/Production Evidence

096 implementation evidence is complete. Any later live production rollout must
append metadata-only evidence for:

- PostHog official generated Docker Compose/service readiness;
- analytics domain/TLS readiness;
- PostHog secret-file wiring;
- PostHog backup/restore proof;
- PostHog resource limit and retention proof;
- PostHog RBAC/access model and audit expectation proof;
- provider retention/deletion lifecycle proof for PostHog data, backups, exports, delivery gaps, Yandex offline conversions, and dashboard/report aggregates;
- separate PostHog stack deploy dry-run handoff proof;
- PostHog server-mediated delivery smoke;
- PostHog web-direct delivery smoke;
- PostHog desktop-direct delivery smoke;
- PostHog autocapture page inventory proof;
- PostHog replay disabled proof;
- Yandex counter reuse proof without live counter ID;
- Yandex `/` and `/download` baseline proof;
- Yandex blocked-page rendering proof;
- Yandex offline conversion OAuth secret-file proof;
- Yandex offline live upload smoke for exactly two conversion names;
- duplicate-protection proof;
- dashboard readiness proof;
- rollback proof;
- no-secret/evidence scan;
- local CI and deploy dry-run result.

## Required Future Validation Commands

Future live rollout or release work must record command names and pass/fail
summaries for:

```sh
rg -n "\[NEEDS CLARIFICATION\]|NEEDS CLARIFICATION:" specs/096-product-analytics-provider-rollout
git diff --check
infra/scripts/ci-local.sh
infra/scripts/cd-remote.sh --dry-run
```

Future rollout work may add focused pytest, SwiftPM, browser/page, Docker, and
provider smoke commands when validating live provider changes.

## Evidence Safety Rules

Allowed evidence:

- command names;
- pass/fail status;
- redacted environment labels;
- event names;
- conversion names;
- page-class states;
- dashboard/report names;
- retention days;
- backup/restore status;
- rollback status;
- blocker names.

Forbidden evidence:

- live PostHog project keys or internal secrets;
- live Yandex counter IDs or OAuth tokens;
- cookies, ClientIDs, Yclids, visitor IDs, or user IDs;
- emails, names, account identifiers, or private local paths;
- signed URLs;
- raw request/response payloads;
- Yandex CSV rows;
- PostHog event/autocapture/replay exports;
- screenshots with visitor/account/meeting data;
- raw audio, transcript text, meeting content, or meeting filenames.

## Current Blockers After Implementation

096 implementation is validated, but these remain blocked/out of scope:

- live production `cd-remote.sh --execute` for provider rollout;
- live PostHog secret creation or live stack start;
- live production Yandex offline upload;
- dashboard verification with real provider data;
- legal, privacy, security, QA, and disclosure approvals for rollout;
- product rollout readiness;
- paid campaign launch.

Known planning blockers closed before `$speckit-taskstoissues`:

- RBAC/audit access model is now explicit in tasks, contracts, data model, smoke, and dashboard evidence.
- Provider retention/deletion lifecycle truth is now explicit for PostHog data, backups, exports, delivery gaps, Yandex offline conversions, and dashboards.
- Separate PostHog stack deploy dry-run handoff is now explicit for `infra/scripts/cd-remote.sh` and validation evidence.
- Placeholder-style script/doc structure in the plan has been replaced with concrete paths.
