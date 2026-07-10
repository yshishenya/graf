# Implementation Evidence: Product Analytics Provider Rollout

**Feature**: `096-product-analytics-provider-rollout`

**Evidence status**: `production_posthog_live_safe_validated_yandex_offline_blocked`

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
| Implementation | complete | 096 provider layer implementation, convergence fixes, review remediation, production deploy execute, runtime PostHog secret/config wiring, and live-safe PostHog delivery smoke are complete. Product rollout readiness and paid campaign launch remain separate blocked steps. |
| Production deploy/runtime provider enablement | complete for PostHog, partial for Yandex | Production deploy for the 096 branch passed before runtime provider enablement. PostHog was then configured outside git on the analytics domain and validated through GRAF live-safe delivery. Yandex public/all-pages inventory uses the existing runtime counter strategy, but Yandex offline upload remains blocked until OAuth token secret-file setup. |
| Paid campaign launch | blocked | Campaign launch remains outside 096 readiness. |

## Implementation Pass Evidence

| Task Range | Status | Metadata-Only Evidence |
| --- | --- | --- |
| T001-T008 Phase 1 setup | complete | Created durable PostHog, Yandex, rollback, PostHog infra, Compose handoff placeholder, runtime env example, and backup/restore shells. |
| Phase 1 no-deploy state | historical checkpoint | At the Phase 1 setup checkpoint, production execute had not run; no live provider ID, project key, OAuth token, cookie, client ID, raw payload, screenshot, meeting content, transcript, audio, signed URL, or private local path was added to committed artifacts. |
| Phase 1 validation | complete | `docker compose -f infra/posthog/docker-compose.posthog.yml config` passed; `git diff --check` passed; file existence checks passed. |
| T009-T022 Phase 2 foundation | complete | Added provider config tests, env/secret propagation tests, provider secret redaction tests, page inventory tests, retention/lifecycle tests, 096 runtime flags, provider config value objects, redacted secret helpers, expanded forbidden-field coverage, 096 page inventory, provider lifecycle records, catalog output, rec-api-only env wiring, Docker secret mounts, PostHog dry-run handoff, env owner/rotation comments, and expanded no-live-secret scans. |
| Phase 2 owner/rotation inventory | complete | `default_provider_secret_inventory()` covers PostHog project key, stack secret, DB password, Redis/object-storage placeholders, Yandex counter, Yandex OAuth token, and product analytics flags with owner roles, rotation notes, committed defaults, propagation tests, and redacted evidence states. |
| Phase 2 redacted evidence status | complete | Provider config and secret helpers return `configured_redacted` / `not_configured` metadata only; focused tests verify synthetic values do not appear in redacted dicts or repr output. |
| Phase 2 validation | complete | `PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_product_analytics_provider_config.py tests/integration/test_product_analytics_provider_env.py tests/unit/test_product_analytics_provider_secrets.py tests/contract/test_product_analytics_page_inventory_096.py tests/contract/test_product_analytics_provider_retention.py tests/contract/test_product_activation_analytics_contract.py tests/unit/test_product_activation_analytics.py tests/integration/test_product_activation_analytics_rollout.py` passed: `45 passed`. `docker compose -f infra/docker-compose.yml config` passed. `infra/scripts/cd-remote.sh --dry-run` passed and reported `posthog_stack_handoff=dry_run_metadata_only`. `git diff --check` passed. |
| Phase 2 remaining blockers | historical checkpoint | At the Phase 2 checkpoint, no production deploy execute, live provider secret creation, live PostHog stack start, Yandex offline upload, dashboard verification, legal/security/QA approval, product rollout readiness, or paid campaign launch had been performed. Current production runtime state is recorded in the 2026-07-09 section below. |
| T023-T037 US1 PostHog primary workspace | complete | Added PostHog provider contract tests, PostHog client tests, PostHog stack tests, provider smoke contract tests, self-hosted PostHog handoff labels/metadata/resource/health/secret boundaries, official generated runtime requirement, PostHog env example, DNS/TLS/resource/disk-full/RBAC/audit/move-out runbook details, backup/restore rehearsal procedure, PostHog readiness metadata, secret-file status checking, dry-run/live-safe-blocked client behavior, provider smoke script, and metadata-only dashboard evidence. |
| US1 validation | complete | `PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_product_analytics_posthog_provider_contract.py tests/unit/test_product_analytics_posthog_provider.py tests/integration/test_product_analytics_posthog_stack.py tests/contract/test_product_analytics_provider_smoke_contract.py tests/unit/test_product_analytics_provider_config.py tests/integration/test_product_analytics_provider_env.py tests/unit/test_product_analytics_provider_secrets.py tests/contract/test_product_analytics_page_inventory_096.py tests/contract/test_product_analytics_provider_retention.py` passed: `34 passed`. |
| US1 deploy state | historical checkpoint | At the US1 checkpoint, `infra/scripts/run-product-analytics-provider-smoke.sh` used synthetic metadata and dry-run checks only. `infra/scripts/cd-remote.sh --dry-run` had a separate PostHog handoff, and production execute had not run at that checkpoint. Current production runtime state is recorded in the 2026-07-09 section below. |
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
| Review remediation: docs/runbooks | complete | PostHog and Yandex runbook statuses were updated from shell to validated/remediated. Dashboard evidence now records rendered-page proof, secret-material rejection, and Yandex UserID binding caveats. At that checkpoint, production deploy execute and live provider dashboards still had not run; current production runtime state is recorded in the 2026-07-09 section below. Product rollout readiness and paid campaign launch remain blocked. |
| Final review-remediation validation | complete | Focused provider/cabinet/OpenAPI validation passed with `68 passed`; provider smoke passed with `posthog_secret_payload_rejected=pass`, `posthog_live_safe_delivery=transport_verified`, and `yandex_live_safe_upload=transport_verified`; provider page validation passed with `posthog_autocapture=current_and_future_pages_enabled` and `webvisor_maps_forms=disabled`; full `infra/scripts/ci-local.sh` passed with `1231 passed, 4 skipped` and `ci_local_result=pass`. |
| Release-readiness preflight | complete | PostHog runtime examples now use the approved public analytics domain `analytics.2brain.pro` instead of an internal placeholder. DNS preflight found `rec.2brain.pro` at `162.120.16.66`; public resolvers `1.1.1.1` and `8.8.8.8` plus authoritative nameservers `launch1.spaceship.net` and `launch2.spaceship.net` resolve `analytics.2brain.pro` to `162.120.16.66`. No committed live provider secrets were found. `infra/scripts/cd-remote.sh --dry-run`, `infra/scripts/run-product-analytics-provider-smoke.sh`, `infra/scripts/validate-product-analytics-provider-pages.sh`, `infra/scripts/rollback-product-analytics-providers.sh`, `docker compose -f infra/posthog/docker-compose.posthog.yml --env-file infra/posthog/posthog.production.env.example config`, focused env/PostHog stack tests, `git diff --check`, and full `infra/scripts/ci-local.sh` passed after the domain alignment. At that preflight point, production execute still required explicit approval, official generated PostHog runtime setup, and live secret/runtime setup outside git. |
| Pre-commit review remediation | complete | Admin rendered pages now receive authenticated pseudonymous PostHog identity when a principal is present. PostHog Compose no longer defaults to mutable `latest`; at this checkpoint, generated runtime image pinning was recorded as an out-of-git runtime hardening requirement and was completed later in the production runtime evidence section. A second pre-commit pass found the committed Compose was too simplified to be a full self-hosted PostHog runtime, so it is now explicitly a GRAF handoff/preflight contract and the runbook/deploy dry-run require the official generated PostHog Docker Compose runtime. Infra PostHog docs moved from shell status to validated/remediated. |
| Final pre-commit validation | complete | After the admin identity, image pinning, official PostHog runtime-source remediation, and legacy/fallback cleanup, focused provider/OpenAPI/rendered-page validation passed with `36 passed`; `infra/scripts/run-product-analytics-provider-smoke.sh`, `infra/scripts/validate-product-analytics-provider-pages.sh`, `infra/scripts/rollback-product-analytics-providers.sh --dry-run`, and `infra/scripts/cd-remote.sh --dry-run` passed; `swift test --package-path apps/macos --filter ProductActivationAnalyticsContractTests` passed with `9 tests, 0 failures`; `docker compose -f infra/posthog/docker-compose.posthog.yml config` and the same command with `--env-file infra/posthog/posthog.production.env.example` passed; `git diff --check` passed; live-looking diff scans found no real provider secrets, keys, tokens, cookies, raw payloads, local paths, or signed URLs; full `infra/scripts/ci-local.sh` passed after cleanup with `1233 passed, 4 skipped` and `ci_local_result=pass`. |
| Legacy/fallback cleanup | complete | Removed the admin `x-workspace-id` fallback for analytics workspace pseudonyms, removed shared anonymous distinct-id fallbacks from desktop-direct and server-mediated PostHog provider delivery, required desktop-direct `distinct_id` in OpenAPI/runtime, replaced Yandex offline anonymous dedupe material with explicit runtime-identity-pending metadata, removed stale `(partial)` task wording, and kept only intentional browser anonymous identity for public/auth pages. |
| Production execute remediation | complete | First production execute attempt reached remote backup/restore rehearsal and image build, then failed before `rec-api` recreation because Docker Compose required missing optional provider secret source files while product analytics was still disabled. Production health remained `ready`. The base Compose was remediated to default optional PostHog/Yandex provider secret sources to committed empty `infra/secret-placeholders/disabled_optional_provider_secret`; live enablement still requires out-of-git host secret files through `*_SECRET_FILE` variables. Validation after the remediation: focused env/secret tests `14 passed`, provider smoke passed, provider page validation passed, rollback dry-run passed, `infra/scripts/ci-local.sh` passed with `1234 passed, 4 skipped`, `infra/scripts/cd-remote.sh --dry-run` passed, `git diff --check` passed, and live-looking diff scan found no real provider secrets. |
| Production execute validator remediation | complete | Second production execute attempt stopped in local CI before remote deploy because the general forbidden-field validator treated a safe `graf_pseudo_user_<hash>` analytics identity as phone-like PII when the hash contained a long digit run. The validator now explicitly allows only strict `graf_pseudo_(user|workspace|account|bridge)_<hex>` pseudonymous values before phone matching; raw email/phone/path/secret values remain blocked. Focused validation passed with `27 passed`, the previously failing signup-to-meetings flow passed, direct safe/unsafe validator checks passed, provider smoke passed, `infra/scripts/cd-remote.sh --dry-run` passed, `git diff --check` passed, and full `infra/scripts/ci-local.sh` passed with `1235 passed, 4 skipped` and `ci_local_result=pass`. |
| Production execute migration-chain remediation | complete | Third production execute reached remote backup/restore and image build, then `rec-migrate` exited before `rec-api` startup because production DB was already stamped with `0019_publish_meeting_registry` while the 096 branch only carried migrations through `0017_meeting_detection`. Production health returned 502 after the failed recreate. The missing `0018_mediascribe_result` and `0019_publish_meeting_registry` migration artifacts plus registry data and migration tests were restored from `origin/master` into 096 so the branch knows the current production head. Focused migration validation passed with `10 passed`, `alembic heads` reported `0019_publish_meeting_registry (head)`, and `git diff --check` passed. |

## Production Runtime Provider Evidence: 2026-07-09

This section records only metadata. It contains no PostHog project key, internal
secret, Yandex counter ID, OAuth token, cookie, visitor/account identifier, raw
payload, event export, screenshot, meeting content, transcript, audio, signed
URL, or private host path.

| Area | Status | Metadata-Only Evidence |
| --- | --- | --- |
| PostHog placement | pass | Self-hosted PostHog is running in a separate Docker Compose project on the same production server as GRAF and is exposed through the separate analytics domain. |
| PostHog domain/TLS | pass | Internal and external `_health` checks for the analytics domain returned `ok`. |
| PostHog workspace/project | pass | First organization/project/admin bootstrap completed inside the self-hosted PostHog instance. The project key was written only to an out-of-git runtime secret file and is not recorded here. |
| PostHog runtime config | pass | GRAF runtime config reports product analytics enabled, `live_safe` validation mode, `parallel_measurement` provider mode, PostHog enabled, PostHog key configured/redacted, autocapture enabled, web-direct enabled, desktop-direct enabled, replay disabled, live provider delivery allowed, and no PostHog readiness blockers. |
| PostHog autocapture page rendering | pass | Live `/`, `/download`, `/login`, and `/sign-up` pages include the first-party product provider config. Live `/login` reports page class `login_signup`, PostHog enabled, autocapture enabled, replay disabled, Yandex disabled for that page class, and private attributes present. |
| PostHog live-safe delivery | pass | GRAF first-party web proxy accepted a metadata-only `graf_web_autocapture_pageview` smoke event with `live_safe_sent`. GRAF desktop proxy accepted a metadata-only `desktop_first_opened` smoke event with `live_safe_sent`. |
| PostHog storage confirmation | pass | PostHog ClickHouse aggregate query found one `graf_web_autocapture_pageview` smoke event and one `desktop_first_opened` smoke event. No raw event properties or visitor/account rows were exported into evidence. |
| PostHog service health | pass | All long-running PostHog services were running after the Redis env/TLS fix and the later digest-pinning restart; only one-time `kafka-init` was exited. No recent PostHog `level=error` logs were found in the checked window. |
| PostHog Redis runtime fix | pass | The generated PostHog runtime required explicit non-TLS Redis settings for logs/traces and the combined plugins service. After adding `LOGS_REDIS_*` and `TRACES_REDIS_*` host/port/TLS-false settings, `plugins`, `ingestion-logs`, and `ingestion-traces` stayed running. |
| GRAF runtime env/secret propagation | pass | Docker Compose config accepted the new product analytics env; `rec-api` initially failed closed when the PostHog key bind file was unreadable by the container user, then became healthy after runtime file permission correction. No secret value was printed. |
| GRAF production health | pass | `rec-api` health returned `ready` locally and through `https://rec.2brain.pro/api/v1/health/ready`. |
| Full production smoke | pass | `infra/scripts/run-production-smoke.sh --execute` passed with production config validation, migration verification, upload smoke, auth cleanup, and artifact cleanup. The readiness verdict remains `infra_smoke_ready`, not product rollout readiness. |
| Provider smoke scripts | pass | `infra/scripts/run-product-analytics-provider-smoke.sh` and `infra/scripts/validate-product-analytics-provider-pages.sh` passed after runtime enablement. |
| PostHog image pinning | pass | Mutable generated-runtime image references were pinned by reviewed digest outside git. Post-pinning Compose config validation passed, image listing found no remaining `latest`/`master` references, the analytics domain returned `_health=ok` after restart, and metadata-only web/desktop live-safe smoke events were ingested. |
| Yandex public/all-pages inventory | partial pass | Product analytics runtime reports Yandex all-pages enabled with counter configured/redacted, while the page inventory still allows only the approved public baseline classes and keeps blocked/replay-unavailable classes out of Yandex. |
| Yandex offline upload | blocked | Runtime reports Yandex offline disabled. OAuth token secret-file setup and live upload smoke for `desktop_account_connected` and `first_value_session_completed` remain required before offline conversion readiness can pass. |
| Paid campaign launch | blocked | 096 still reports campaign launch as blocked; technical provider smoke does not approve paid campaign launch. |
| Product rollout readiness | blocked | Production provider delivery is working for PostHog, but product rollout readiness remains a separate product/legal/security/QA decision. |
| PostHog backup/restore | blocked for full readiness | Runtime volume inventory exists, but a full PostHog backup and isolated restore rehearsal for the generated stack has not been completed in this pass. |
| Image pinning | pass | Runtime image pinning was completed outside git and verified by Compose config, mutable-tag scan, health check, and post-pinning delivery smoke. Repeat this check after every future PostHog stack update. |

## Post-Runtime Review Follow-Up: 2026-07-09

This section records the extra review requested after runtime enablement: Yandex
public counter troubleshooting, admin audit/metrics usefulness, cleanup, and
pre-commit validation. Evidence is metadata-only and does not include live
counter IDs, project keys, OAuth tokens, cookies, visitor/account rows, raw
payloads, screenshots, names, emails, meeting content, transcripts, audio,
signed URLs, or private local paths.

| Area | Status | Metadata-Only Evidence |
| --- | --- | --- |
| Yandex public counter troubleshooting | pass with consent caveat | Live `/` and `/download` pages render the public analytics config and Yandex counter state as configured/redacted. Browser verification showed no Yandex network traffic before analytics consent, and approved Yandex goal traffic after granted analytics/attribution consent for the public landing/download events. If real visitors do not grant consent, Yandex counters can remain at zero even while the code is present. |
| Public analytics controller duplicate | fixed locally, pending next deploy | Live troubleshooting found duplicate `analytics.js` loading on public pages. The branch now includes the shared controller only once on public pages and keeps a runtime guard so accidental duplicate loading cannot double-initialize PostHog/Yandex. Focused public/product analytics validation passed. |
| Admin audit usefulness | complete | Admin audit rows now include when/who/action/object/outcome/source/detail labels, actor/object drill-down links, and safe metadata summaries across admin, auth, egress, and lifecycle sources. |
| Admin metrics usefulness | complete | Admin metrics now include Russian family labels, reader-facing questions, value labels, drill-down labels, and audit-source breakdowns. Governance counts include admin, auth, meeting egress, and meeting lifecycle audit sources instead of only one audit table. |
| Admin tests | pass | Admin-focused validation passed with `54 passed`, covering browser, API, CSRF, no-secret egress, RLS, audit journal, workspace access, usage metrics, file governance, user management, permissions, invitations, file access, usage, and view models. |
| Focused public/provider tests | pass | Focused public/product provider validation passed with `40 passed`, including public analytics contract, autocapture page wiring, PostHog autocapture contract, and Yandex page scope. |
| Provider scripts | pass | Provider smoke passed, page validation passed, rollback dry-run passed, and deploy dry-run passed after cleanup. |
| Full local CI | pass | `infra/scripts/ci-local.sh` passed after cleanup with server tests `1238 passed, 4 skipped`, server lint passed, Python compile passed, RLS hardening validation truthfully blocked without production probe, production Compose config passed, deployment evidence scan passed, and `ci_local_result=pass`. |
| Diff live-secret scan | pass | High-signal diff scan found no live-looking provider keys, OAuth tokens, private keys, signed URLs, client secrets, or token assignments. |
| Cleanup | complete | Removed generated Python caches, replaced stale analytics scaffold wording, removed stale PostHog image-pinning blocker wording, and changed admin analytics script loading to the versioned shared public asset helper. |

## Final Production Deploy Closeout: 2026-07-09

This section records the final production deploy and live verification after
the post-runtime review fixes. It is metadata-only and contains no live counter
IDs, PostHog project keys, OAuth tokens, cookies, visitor/account rows, raw
payloads, screenshots, names, emails, meeting content, transcripts, audio,
signed URLs, or private local paths.

| Area | Status | Metadata-Only Evidence |
| --- | --- | --- |
| Final app deploy | pass | `infra/scripts/cd-remote.sh --execute` passed on branch `096-product-analytics-provider-rollout`; deployed SHA `f12b8761538a31152a1cf3db9780643cb55d1301`; readiness verdict remained `infra_smoke_ready`. |
| Final deploy gate | pass | Local deploy gate inside `cd-remote.sh --execute` passed with server tests `1238 passed, 4 skipped`, server lint passed, Python compile passed, production Compose config passed, deployment evidence scan passed, and `ci_local_result=pass`. |
| Remote backup/restore rehearsal | pass | Remote backup and restore rehearsal passed before the final app recreate. Artifact paths are intentionally omitted from committed evidence. |
| Production smoke | pass | Remote production smoke passed with migration verification at `0019_publish_meeting_registry (head)`, RLS disposable probe pass, upload smoke pass, auth cleanup pass, artifact cleanup pass, and no residue follow-up. |
| Live GRAF health | pass | `https://rec.2brain.pro/api/v1/health/ready` returned `ready` after deploy. |
| Live PostHog health | pass | Analytics domain `_health` returned `ok` after deploy. |
| Live analytics controller loading | pass | Live `/`, `/download`, and `/login` each rendered exactly one `/static/public/analytics.js` script, and each script URL was versioned. Public pages also rendered the public analytics config and product provider config; `/login` rendered only product provider config as expected. |
| Runtime provider catalog | pass | Runtime catalog reports product analytics enabled, `live_safe`, `parallel_measurement`, PostHog enabled with project key configured/redacted, autocapture enabled, web-direct enabled, desktop-direct enabled, replay disabled, Yandex counter configured/redacted, Yandex offline disabled, product rollout blocked, and campaign launch blocked. |
| PostHog web delivery | pass | First-party web capture endpoint returned `live_safe_sent` for a metadata-only post-deploy smoke event. |
| PostHog desktop delivery | pass | First-party desktop capture endpoint returned `live_safe_sent` for an allowlisted metadata-only `desktop_first_opened` post-deploy smoke event. A first attempt with a non-allowlisted `source` property was correctly rejected before retrying with the allowed body. |
| PostHog storage aggregate | pass | ClickHouse aggregate query over the last hour found both `graf_web_autocapture_pageview` and `desktop_first_opened` event names. No properties, person rows, visitor IDs, account rows, or payload exports were committed. |
| Yandex browser behavior | pass | Headless browser/CDP check found no Yandex requests and no Yandex goals before analytics consent; after granted analytics/attribution consent, the public landing page loaded Yandex tag traffic and sent one approved public landing goal request. |
| Admin UI improvement deploy | pass | Admin audit/metrics usability changes are included in deployed SHA `f12b8761538a31152a1cf3db9780643cb55d1301`; production smoke remained green. Authenticated production admin screen review still requires an operator session and must not use raw private evidence. |
| GitHub tracker closeout | pass | `feature:096` GitHub tracker now has 96 closed issues and 0 open issues. Initial task-to-issues sync covered T001-T090; convergence tasks T091-T096 were missing from GitHub, so metadata-only issues #3034-#3039 were created and closed with production/evidence closeout comments. Earlier task-backed issues #2889-#2978 were also closed with Russian closure comments. |
| Remaining blockers | expected | Yandex offline OAuth/upload smoke, real dashboard business review, product rollout readiness, paid campaign launch, and full PostHog backup/restore ops readiness remain separate gates. |

## Final Code Review Follow-Up: 2026-07-10

This section records the additional code-review pass requested after the final
production closeout. It is metadata-only and contains no live counter IDs,
PostHog project keys, OAuth tokens, cookies, visitor/account rows, raw payloads,
screenshots, names, emails, meeting content, transcripts, audio, signed URLs, or
private local paths.

| Area | Status | Metadata-Only Evidence |
| --- | --- | --- |
| Pseudonymous identity boundary | fixed | Server and macOS validation now require either the intentional browser anonymous ID or strict `graf_pseudo_(user|workspace|account|bridge)_<hex>` identities. Loose prefixed strings are rejected so hand-written names/labels cannot pass the provider trust boundary. |
| Desktop PostHog direct route | fixed | macOS direct PostHog delivery now requires an explicit first-party GRAF proxy endpoint. A PostHog host alone no longer causes the desktop client to synthesize a capture URL. |
| Admin audit usability | fixed | Admin audit filters now expose Russian select options for action/object/outcome, include an object-ID filter, render action summaries plus object-kind/ID context per row, include `calendar_audit_events`, and cover the calendar, provider-link, device, share, skipped, and partial audit values found during review. |
| Yandex zero-data preflight | tightened | Provider smoke now proves public/product Yandex render config can become enabled with runtime flags and prints `yandex_render_config=present` without exposing a counter ID. The Yandex runbook now calls out this marker in zero-data troubleshooting. |
| Focused Python validation | pass | `PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_product_activation_analytics.py tests/unit/test_product_analytics_posthog_provider.py tests/unit/test_product_analytics_yandex_offline_provider.py tests/integration/test_product_activation_analytics_rollout.py tests/contract/test_product_analytics_posthog_autocapture_contract.py tests/integration/test_product_analytics_autocapture_pages.py tests/integration/test_admin_audit_journal.py tests/contract/test_admin_browser_contract.py tests/contract/test_product_analytics_provider_smoke_contract.py tests/contract/test_product_analytics_provider_smoke_output.py tests/integration/test_product_analytics_yandex_page_scope.py tests/integration/test_product_analytics_yandex_env.py tests/integration/test_product_analytics_provider_env.py` passed: `65 passed`. |
| Focused macOS validation | pass | `swift test --package-path apps/macos --filter ProductActivationAnalyticsContractTests` passed: `11 tests, 0 failures`. |
| Diff hygiene | pass | `git diff --check` passed. A search for old loose smoke/test IDs found no remaining positive-use matches; remaining loose examples are negative tests only. |
| Full local CI | pass | `infra/scripts/ci-local.sh` passed after the review fixes with server tests `1239 passed, 4 skipped`, server lint passed, Python compile passed, production Compose config passed, deployment evidence scan passed, and `ci_local_result=pass`. The RLS hardening validation remained truthfully blocked without a production database probe, as expected. |

## Point-by-Point Closeout Recheck: 2026-07-10

This section records the follow-up closeout requested after the final code
review fixes, with special attention to product rollout readiness. It is
metadata-only and contains no live counter IDs, PostHog project keys, OAuth
tokens, cookies, visitor/account rows, raw payloads, screenshots, names, emails,
meeting content, transcripts, audio, signed URLs, or private local paths.

| Area | Status | Metadata-Only Evidence |
| --- | --- | --- |
| Provider smoke and Yandex zero-data preflight | pass | `infra/scripts/run-product-analytics-provider-smoke.sh` passed with `provider_smoke_result=pass`, `yandex_render_config=present`, `yandex_public_baseline=preserved`, `yandex_offline=dry_run_two_conversions`, `yandex_live_safe_upload=transport_verified`, `product_rollout=blocked`, `campaign_launch=blocked`, and `no_secret_scan=metadata_only_pass`. |
| Rollout/campaign blocker tests | pass | `PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_product_analytics_provider_config.py tests/integration/test_product_analytics_provider_readiness_blockers.py tests/contract/test_product_analytics_provider_rollback.py` passed: `13 passed`. These tests prove provider/live-safe delivery gates can be validated without approving product rollout readiness or paid campaign launch in 096. |
| Deployment-focused smoke contracts | pass | `PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_product_activation_analytics_rollout.py tests/contract/test_product_analytics_provider_smoke_output.py tests/contract/test_product_analytics_provider_smoke_contract.py` passed: `9 passed`. |
| Live-secret guard | pass | `PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_product_activation_analytics.py::test_no_live_product_analytics_secrets_are_committed` passed: `1 passed`. |
| Product rollout readiness | intentionally blocked | 096 remains a provider/infrastructure rollout, not a product rollout approval. `product_rollout_allowed=false`, `campaign_launch_allowed=false`, Yandex offline live upload still requires OAuth secret-file setup and live upload smoke, real provider dashboard review remains separate, and paid campaign launch remains blocked by 096. |

## Official Documentation Reviewed

Planning research reviewed official provider documentation for:

- self-hosted PostHog operations and operator responsibility;
- self-hosted PostHog environment configuration;
- self-hosted PostHog session replay storage;
- Yandex Metrica OAuth authorization;
- Yandex Metrica quick start and required scopes;
- Yandex Metrica offline conversion upload.

See [research.md](../research.md) for decisions and source links.

## Remaining Future Live/Production Evidence

096 PostHog production runtime delivery is live-safe validated. Remaining live
production evidence must append metadata-only proof for:

- full PostHog backup and isolated restore rehearsal for all generated runtime volumes;
- PostHog resource limit and retention proof beyond the initial health checks;
- PostHog RBAC/access model and audit expectation proof;
- provider retention/deletion lifecycle proof for PostHog data, backups, exports, delivery gaps, Yandex offline conversions, and dashboard/report aggregates;
- Yandex offline conversion OAuth secret-file proof;
- Yandex offline live upload smoke for exactly two conversion names;
- duplicate-protection proof;
- real dashboard readiness review with metadata-only freshness proof;
- rollback proof after any future runtime switch changes;
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

## Current Blockers After Production Runtime Enablement

096 PostHog runtime delivery is validated, but these remain blocked/out of
scope:

- live production Yandex offline OAuth setup and upload smoke;
- PostHog full backup/restore rehearsal;
- dashboard verification with real provider data using metadata-only evidence;
- legal, privacy, security, QA, and disclosure closeout for product rollout;
- product rollout readiness;
- paid campaign launch.

Known planning blockers closed before `$speckit-taskstoissues`:

- RBAC/audit access model is now explicit in tasks, contracts, data model, smoke, and dashboard evidence.
- Provider retention/deletion lifecycle truth is now explicit for PostHog data, backups, exports, delivery gaps, Yandex offline conversions, and dashboards.
- Separate PostHog stack deploy dry-run handoff is now explicit for `infra/scripts/cd-remote.sh` and validation evidence.
- Placeholder-style script/doc structure in the plan has been replaced with concrete paths.
