# Research: Provider-Neutral Federated Auth Foundation

## Decision: Use server-side provider adapter pattern with uniform identity tuple

**Decision**: Implement a provider adapter interface and represent external identity by `(provider, provider_subject)` in database.

**Rationale**: This supports `Yandex ID`, `VK ID`, and `Telegram Login` in MVP while keeping future providers isolated behind one contract and avoiding user-identity rewrites when `T-ID`, `Sber ID`, or `MTS ID` are enabled later.

**Alternatives considered**:
- Provider-specific hard-coded logic everywhere — rejected due to high maintenance and high regression risk.
- Storing only provider token data without normalized identity tuple — rejected because deterministic linking and auditability become fragile.

## Decision: Keep callback state in Postgres for auditability

**Decision**: Use a small server-side callback state store with short expiration (nonce, provider, workspace context).

**Rationale**: Stateful callback validation supports replay protection, deterministic failure handling, and incident review.

**Alternatives considered**:
- Signed stateless tokens only — rejected due to weaker forensic visibility.
- Browser-side-only state — rejected due to reduced revocation and audit capability.

## Decision: Explicit confirmation for cross-provider linking with limited verified auto-match

**Decision**: Use explicit user confirmation as primary behavior; allow deterministic verified-field match only with safe conflict checks.

**Rationale**: Prevents silent account takeover while still supporting a useful one-click multi-provider workflow.

**Alternatives considered**:
- Unconditional auto-link on any matching field — rejected because of collision risk.
- No assisted match path — rejected due to poor UX for expected user journeys.

## Decision: Device identity remains server-owned and distinct from provider identity

**Decision**: Add registered-device entities tied to workspace/user with trust status, heartbeat, and revocation.

**Rationale**: This supports secure upload continuity and allows immediate revoke semantics for lost devices.

**Alternatives considered**:
- Reusing provider sessions for all uploads — rejected because of token exposure and policy coupling.
- Client-generated IDs without server registration — rejected due to weak revocation and low audit confidence.

## Decision: RU-local residency as workspace policy

**Decision**: Enforce workspace-level residency and provider availability policy flags that gate storage targets and visible provider options.

**Rationale**: Workspace-level policy supports real deployment differences and gives admin evidence for compliance.

**Alternatives considered**:
- Global static policy — rejected for mixed-deployment realities and audit clarity.
- File-level manual policy only — rejected as non-operational for admin governance.

## Decision: Desktop clients consume only server-issued session proofs

**Decision**: Do not expose provider tokens, raw claims, or credential material to clients; consume server-issued short-lived session proofs for uploads.

**Rationale**: Maintains security boundary and aligns with existing server-mediated upload model.

**Alternatives considered**:
- Passing provider tokens to desktop client — rejected for leakage and revocation complexity.
- Triggering provider logic in client app — rejected as untestable for server-residency constraints.

## Security and observability decision: Redaction-by-default for auth metadata

**Decision**: Expand redaction rules for auth/event payloads and provider payload key names.

**Rationale**: New flow increases metadata intake; existing redaction utilities must explicitly handle provider fields.

**Alternatives considered**:
- Manual endpoint-by-endpoint redaction only — rejected as inconsistent.
- No additional redaction — rejected due to provider claims and callback fields.

## References

- OAuth/OIDC callback and state validation guidance from mainstream OAuth security practice.
- Existing product privacy/storage boundary requirements from PRD and user request.

## 2026-06-11 Provider and Legal Refresh

The MVP provider choice remains valid after a current-source refresh:

- `Yandex ID` remains a public OAuth-based identity provider for website/app authorization:
  https://yandex.com/dev/id/doc/en/
- `Telegram Login` remains available through Telegram's login library / OpenID Connect flow:
  https://core.telegram.org/widgets/login
- `VK ID` remains an active provider family, but current public integration material points
  implementers toward the newer `id.vk.com` / OAuth 2.1 + PKCE flow rather than older
  `oauth.vk.com` assumptions:
  https://id.vk.com/about/business/go/docs/ru/vkid
- `Sber ID`, `T-ID`, and `MTS ID` are real Russian-market identity products, but they
  require partner/business onboarding and are kept behind policy/config gates for this
  feature:
  https://developers.sber.ru/docs/ru/sberid/service/overview
  https://developer.tinkoff.ru/docs/intro/partner/tid
  https://business.mts.ru/moskva/mts-id
- RU-local storage remains a high-risk compliance requirement. Article 13.11 КоАП РФ
  includes large fines for personal-data localization violations and repeated violations;
  the 013 conservative default therefore keeps auth/session/device/audit metadata in
  owner-controlled RU-local policy scope:
  https://www.consultant.ru/document/cons_doc_LAW_34661/1f421640c6775ff67079ebde06a7d2f6d17b96db/
