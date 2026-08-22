# Yandex goal configuration status

Status: PASS — exact nine goal identifiers configured in the authenticated production counter on 2026-08-21.

Counter: `110519381` (`GRAF production - rec.2brain.pro`, `rec.2brain.pro`). The authenticated owner account displayed `9 из 200 целей`. Existing acquisition goals were preserved; three missing interaction goals were added. No goal was deleted.

The goal list was checked twice, including after reloading the counter page. Each identifier below was visible with the condition `идентификатор содержит: <identifier>`:

| Event identifier | Display name in counter | Result |
| --- | --- | --- |
| `public_landing_viewed` | `093 public_landing_viewed` | already present |
| `public_landing_section_seen` | `093 public_landing_section_seen` | already present |
| `public_landing_cta_clicked` | `093 public_landing_cta_clicked` | already present |
| `public_download_viewed` | `093 public_download_viewed` | already present |
| `public_installer_download_clicked` | `093 public_installer_download_clicked` | already present |
| `public_login_intent_clicked` | `093 public_login_intent_clicked` | already present |
| `public_product_tab_selected` | `179 public_product_tab_selected` | created |
| `public_pricing_cycle_selected` | `179 public_pricing_cycle_selected` | created |
| `public_faq_opened` | `179 public_faq_opened` | created |

This is provider-side goal configuration evidence. A post-deploy synthetic public session and received-hit verification remain part of the release smoke; the browser UI list alone is not claimed as proof that a live landing event has fired.
