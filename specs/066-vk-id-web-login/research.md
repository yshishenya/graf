# Research: VK ID Web Login

## Decision: Reuse the 013 VK provider adapter

**Rationale**: The existing 013 provider backend already contains `VkAdapter`, callback verification, provider policy, callback state, session issuance, audit events, and account linking. Reusing it keeps the new browser surface small and avoids duplicate token custody.

**Alternatives considered**:
- New web-only VK implementation: rejected because it would duplicate provider verification and increase takeover risk.
- Client-side VK handling: rejected because browser clients must not receive provider tokens or secrets.

## Decision: Enable VK browser start only, keep Telegram stubbed

**Rationale**: The user asked for VK after Yandex. Turning on every listed provider would broaden product and test scope.

**Alternatives considered**:
- Enable all providers: rejected as unrequested scope.
- Hide all non-VK providers: rejected because existing product copy already lists future providers.

## Decision: Use provider-specific client ID selection

**Rationale**: Browser start currently builds the authorization URL locally. VK redirects must use `TWOBRAIN_VK_CLIENT_ID`; using the Yandex client ID would create a broken redirect and could confuse provider-side audit.

**Alternatives considered**:
- Hard-code VK in a branch: rejected because the API auth module already has `_provider_client_id`.
- Add a new provider config abstraction: rejected because existing settings fields are enough.

## Decision: Mount VK secret through Docker Compose

**Rationale**: Production provider secrets must stay server-side and fail closed when missing or empty. The existing Yandex secret pattern covers the required behavior.

**Alternatives considered**:
- Put VK secret in `.env`: rejected because live secrets must not be environment values.
- Delay secret wiring until deploy: rejected because the code would otherwise expose an active provider without a server-side credential boundary.
