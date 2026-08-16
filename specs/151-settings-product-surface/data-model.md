# Data Model: Продуктовый раздел настроек

No new data model is introduced.

The feature consumes existing projections:

- `SettingsCategoryView` for navigation metadata.
- `AccountSettingsSurface` for profile, providers, devices, sessions and account closure.
- Existing workspace access and invitation views.
- Existing calendar settings surface.
- Existing notification preference record.
- Existing billing projections and launch-gated unavailable state.

All mutations continue to use existing server routes, CSRF tokens, tenant scope and owner/re-auth checks.
