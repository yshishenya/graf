# Contract: Settings sidebar

## Canonical navigation

| Group | ID | Browser href | Embedded href |
| --- | --- | --- | --- |
| Встречи | recording | `/settings/recording` | `/desktop/settings/recording` |
| Встречи | summaries | `/settings/summaries` | `/desktop/settings/summaries` |
| Встречи | calendar | `/settings/integrations/calendar` | `/desktop/settings/integrations/calendar` |
| Пространство | workspace | `/settings/workspace` | `/desktop/settings/workspace` |
| Аккаунт | account | `/settings/account` | `/desktop/settings/account` |

The menu renders one semantic `nav[aria-label="Разделы настроек"]`, one visible
heading for each group and exactly one anchor per canonical ID. No arbitrary
  category or redirect is accepted. The `/settings` landing page is a separate
  compact entry point and is not repeated as a rail item.

## Active state

The active link has the existing `is-selected` class and
`aria-current="page"`. Other links remain ordinary navigable anchors. Calendar
and provider-link pages use their existing `active="calendar"` and
`active="account"` mappings.

## Layout and accessibility

- Desktop: rail on the left, settings content on the right.
- Each link is at least 44px high, wraps long labels, and retains the shared
  visible `:focus-visible` indicator.
- At 640px or less: one-column layout, full vertical menu, no horizontal-only
  navigation and no clipped label.
- Group headings are non-interactive text inside the navigation landmark.
- Existing global cabinet navigation remains a separate landmark.

## Preserved boundaries

The contract does not change routes, permissions, CSRF, mutation forms, safe
account fields, calendar HTMX fragment behavior, or the native macOS recording
handoff. The sidebar must not expose credentials, provider subjects, device
secrets, `/admin`, capture or diagnostics controls.
