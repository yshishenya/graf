# Contract: Dashboards And Rollout Gates

**Feature**: `094-product-activation-analytics`

## Dashboard Ownership

| Dashboard | Primary Workspace | Owner | Required Caveats |
| --- | --- | --- | --- |
| Source to first value | PostHog | product/growth | consent/blocking, internal/support/smoke/test counted, attribution gaps |
| Installer intent vs first open | PostHog | growth + desktop | first open may be unlinked |
| Account connected | PostHog + Yandex offline conversion report | auth/server + growth | Yandex subset limited |
| Auto-record enabled | PostHog | desktop + calendar policy | policy/user-action distinction |
| First recording completed | PostHog | capture/server | recording completion is not first value |
| First result viewed | PostHog | cabinet | no transcript/content fields |
| First value session completed | PostHog + Yandex offline conversion report | product analytics + growth | ready useful result view only |
| Replay availability | PostHog/Yandex | product analytics + QA | page-class replay unavailable caveats |
| Yandex all-web behavior | Yandex | growth | Yandex is not product source of truth |
| Delivery gaps | PostHog or ops report | ops | provider/script/network loss caveats |

## Launch Blockers

Implementation or launch is blocked when any required item is missing:

- legal approval
- hard product telemetry gate copy
- provider decision
- provider configuration
- identity and attribution contract
- parallel measurement matrix
- Yandex all-pages inventory
- replay masking contract
- retention/deletion truth
- forbidden-field test coverage
- dashboard owner
- dashboard caveat for internal/support/smoke/test counted by default
- runtime propagation smoke
- rendered-page scope proof
- provider dashboard/goal visibility
- direct desktop egress approval, if direct route is used
- campaign interpretation caveats
- no-secret evidence scan
- local CI for implementation

## Runtime Smoke Evidence

Future smoke must verify:

- host env or secret source
- `docker compose config` contains expected runtime env placeholders/values
- live container env contains expected runtime values
- rendered HTML/JS includes provider config only on approved page classes
- rendered HTML/JS excludes provider config on blocked page classes
- replay-disabled classes show provider event/page behavior without replay/maps/
  forms
- provider script/API reachability
- PostHog dashboard/event visibility
- Yandex goal/offline-conversion visibility
- no live provider IDs, cookies, client IDs, visitor IDs, screenshots with raw
  user data, signed URLs, or tokens in committed evidence

## Campaign Launch Boundary

Paid campaign launch and Yandex Direct optimization remain blocked until:

- legal/campaign-readiness approval exists
- campaign naming canon is approved
- Yandex Direct linking is approved
- offline-conversion upload process is approved
- campaign reports clearly state that download intent is not product activation
- internal/support/smoke/test activity is counted by default
