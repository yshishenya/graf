# Яндекс Календарь: real E2E certification contract

Этот документ определяет evidence gate для изменения capability state
`caldav_yandex` с `Скоро` на connectable. Synthetic tests не закрывают этот gate.

## Required matrix

| ID | Surface | Action | Required outcome |
|---|---|---|---|
| Y201-01 | Browser | Open settings and start Yandex connect | Yandex card is connectable; form asks only for account label, username and app password |
| Y201-02 | Browser | Submit invalid password | Safe error, no source and no secret echo |
| Y201-03 | Browser | Submit dedicated test account | Provider validates and returns non-empty catalog before source success |
| Y201-04 | Browser | Save zero and one selected calendar | Selection persists after reload; zero is intentional and safe |
| Y201-05 | Browser | Run sync and inspect upcoming projection | queued → syncing → synced; only selected safe rows appear |
| Y201-06 | Browser | Reconnect same account | No duplicate active source; committed selection policy is preserved |
| Y201-07 | Browser | Disconnect and reload | Exact GRAF disconnect copy; source/cache/credential are closed locally |
| Y201-08 | Embedded macOS | Repeat Y201-03 through Y201-07 | Same server truth; native Record/Stop remains usable |
| Y201-09 | Both | Repeat after session refresh | No stale success, raw provider error or credential in DOM/AX/runtime evidence |

## Evidence rules

- Record commit SHA, surface, scenario ID, viewport/app build, account class,
  state/count/timestamp and verdict only.
- Do not record password, OAuth/token material, event title, participant email,
  raw URL, private meeting content or raw provider response.
- A failed or incomplete row keeps the provider `Скоро`.
- Production launch additionally requires full CI, release notes, exact-SHA
  deploy gates and explicit approval; this matrix is necessary but not
  sufficient for production deploy.

## Rollback

If a post-enable regression appears, remove only Yandex from the certified
provider set, disable new connections/sync claims, and leave disconnect and
meeting retention paths available. Never restore purged credentials.
