# Calendar provider runtime matrix

This matrix is product truth, not a roadmap promise. `Connectable` requires
both validation/catalog and worker sync routing through a tested read-only
adapter. A visible unavailable card is not an integration claim.

| Provider family | UI method | Runtime adapter | Current state | Evidence boundary |
|---|---|---|---|---|
| `google_calendar` | server OAuth | Google API | Production: `Скоро`; explicit local certification override only | local real OAuth/catalog/selection/full and incremental sync/upcoming/local disconnect/reconnect observed; production verification, secret rotation and dedicated test-account certification remain blocked |
| `caldav_yandex` | login + app password | shared CalDAV | `Скоро` until full real matrix passes | synthetic HTTP/runtime; real account not proven |
| `caldav_mail_ru` | login + app password | shared CalDAV | `Скоро` until full real matrix passes | synthetic HTTP/runtime; real account not proven |
| `custom_caldav_vk_workspace` | exact CalDAV URL + login + secret | shared CalDAV | `Скоро` until full real matrix passes | routing fixed and unit covered; real account not proven |
| `caldav_mailion_myoffice` | exact CalDAV URL + login + secret | shared CalDAV | `Скоро` until full real matrix passes | synthetic only |
| `caldav_r7_office` | exact CalDAV URL + login + secret | shared CalDAV | `Скоро` until full real matrix passes | synthetic only |
| `caldav_communigate_pro` | exact CalDAV URL + login + secret | shared CalDAV | `Скоро` until full real matrix passes | synthetic only |
| `caldav_rupost` | exact CalDAV URL + login + secret | shared CalDAV | `Скоро` until full real matrix passes | synthetic only |
| `caldav_nextcloud_sogo` | exact CalDAV URL + login + secret | shared CalDAV | `Скоро` until full real matrix passes | synthetic only |
| `custom_caldav` | exact CalDAV URL + login + secret | shared CalDAV | `Скоро` until full real matrix passes | synthetic only |
| `exchange_ews` | none | none | `Скоро` | dedicated EWS auth/discovery/event adapter and test server required |
| `bitrix24` | none | none | `Скоро` | dedicated Bitrix24 OAuth/REST contract, app registration and test portal required |

Rules:

- Every connectable family MUST resolve through `provider_for_connection()` and
  `provider_for_source()` or a provider-specific OAuth runtime.
- A missing adapter or missing complete real E2E receipt fails closed, has no
  active form and MUST be labeled only `Скоро`.
- A provider-specific local development override may expose one configured
  provider only for certification. It MUST NOT alter production availability or
  count as a public launch receipt.
- Exact credentials and event content never appear in this matrix or evidence.
- Any provider can move to connectable only with provider contracts, synthetic
  fixtures, tenant/deletion coverage and the full real browser/macOS matrix.
