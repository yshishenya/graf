# Production analytics status

Status: PENDING RELEASE CONFIGURATION AND PROVIDER RECEIPT.

Read-only runtime verification on 2026-08-21 found:

- the existing Yandex counter identifier is configured;
- public landing analytics is disabled;
- public replay is enabled in the old runtime configuration;
- private all-page Yandex analytics is disabled.

The release must enable only the public counter for `/` and `/download`, set replay to false, keep private all-page analytics disabled and then verify all nine configured goals in the authenticated Yandex interface. No runtime flag was changed during implementation testing.
