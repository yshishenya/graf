# New Session Prompt: Start Feature 094 Correctly

Use this prompt when starting a fresh Codex session for
`094-product-activation-analytics`.

```text
Начинаем новую сессию по feature `094-product-activation-analytics`.

Работай из canonical checkout:

- `<repo-root>`

Сначала прочитай:

- `AGENTS.md`
- `docs/agent-guidance/spec-kit-flow.md`
- `docs/agent-guidance/product-gates.md`
- `docs/agent-guidance/release-and-validation.md`
- `docs/agent-guidance/github-issue-canon.md`
- `specs/094-product-activation-analytics/spec.md`
- `specs/094-product-activation-analytics/sdd-prompt.md`
- `specs/093-public-landing-analytics/validation/implementation-evidence.md`
- `specs/093-public-landing-analytics/contracts/analytics-provider-setup.md`
- `specs/093-public-landing-analytics/contracts/phase2-activation-contract.md`
- `docs/current-product-status.md`

Выбранный lane:

- high-risk Spec Kit discovery/specification;
- это не implementation;
- не добавляй PostHog SDK, Yandex на app/cabinet, product events, replay,
  auth/cabinet tracking, desktop tracking, migrations, deploy или provider
  setup без отдельного будущего approval.

Контекст 093:

- `093-public-landing-analytics` полностью закрыт для approved public scope.
- Production Yandex Metrica live только на `/` и `/download`.
- Настроены public Yandex counter/goals, dashboard access и production
  provider smoke.
- Production deploy прошел; live container env, rendered HTML for `/` and
  `/download`, Yandex script reachability, health endpoints, and negative
  `/login` scope были проверены.
- Paid campaign launch НЕ approved: он все еще blocked до legal/campaign-
  readiness approval.
- 093 не включает desktop/app/cabinet/authenticated/product analytics и не
  доказывает install, first open, account connected, first recording,
  result viewed или first value.
- Важный урок 093: нельзя считать analytics включенной только по host-side
  `.env`; future rollout smoke обязан проверять env/secret source -> compose
  config -> live container env -> rendered HTML/JS -> allowed pages -> blocked
  pages -> provider script reachability -> provider dashboard/goals.

Цель 094:

Спроектировать продуктовую activation analytics для GRAF так, чтобы product
owner видел полный путь пользователя:

campaign/source -> public landing/download intent -> desktop first open ->
account connection -> auto-record enabled -> first recording -> first result
view -> first value.

Текущая продуктовая позиция:

- primary daily workspace: self-hosted PostHog, если research/legal/ops gates
  не отвергнут его;
- Yandex Metrica: parallel all-web-pages measurement and advertising
  optimization surface после page inventory, masking, URL/title/referrer
  sanitization, legal review, QA evidence, and smoke gates;
- approved activation milestones may be sent to Yandex only as bounded offline
  conversions for ad optimization;
- no routine CSV/manual exports/custom ETL as the daily analytics workflow;
- no Google/GA4/GTM for now unless a later separate legal-approved slice changes
  that decision.

Обязательные outputs будущего SDD:

1. Parallel measurement matrix.
2. Yandex all-pages inventory.
3. Replay masking contract for PostHog Session Replay and Yandex Webvisor.
4. Identity and attribution contract centered on safe `graf_attribution_id`
   and/or expiring bridge token.
5. Legal/consent hard product-use gate: same B2B/B2C path; normal product use
   stops or is limited to account/legal/export/deletion flows if required
   terms/telemetry are refused or withdrawn.
6. Dashboard map: PostHog as source of truth; Yandex for web/ad/Webvisor/
   offline-conversion surfaces.
7. Launch blockers and production smoke plan.

Forbidden unless a separate future legal gate explicitly approves otherwise:

- raw email, names, company/workspace/account names;
- raw account/user/workspace/meeting IDs;
- meeting title, participants, transcript, audio, calendar text;
- local paths, object keys, signed URLs, tokens, passcodes, secrets;
- unmasked product/cabinet/meeting replay;
- ad retargeting pixels;
- routine manual exports as the normal analytics workflow.

Start correctly:

1. State the lane: high-risk Spec Kit discovery/specification.
2. Confirm you read the files above.
3. Run the next Spec Kit step: `$speckit-clarify`.
4. Ask only clarification questions that are still genuinely unresolved after
   reading `spec.md` and `sdd-prompt.md`.
5. Do not implement until clarify, plan, checklist, analyze, taskstoissues, and
   explicit implementation approval are complete.
```
