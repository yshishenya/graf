# Browser invitation error contract

## Browser requests

- Invitation browser paths include the external invitation GET and its
  continuation POST.
- For a browser-oriented request with `Accept: text/html`, missing `Accept` or
  generic `Accept: */*`, an invalid/replayed/expired/revoked/recipient-mismatch
  failure returns a server-rendered HTML page from GRAF.
- The page uses the safe unavailable state, contains no meeting content or
  bearer/continuation secret, and offers only a safe route back to GRAF/login.
- The response remains private and non-cacheable.
- An unauthenticated browser request to a protected GRAF page reached from an
  email follows the existing HTML login flow.

## API requests

- A request explicitly asking for JSON keeps the current status code,
  `application/problem+json` content type and Problem Details fields.
- No invitation state transition, auth session, grant, membership or RLS
  policy changes are made by content negotiation.

## Success behavior

- A valid first-entry invitation keeps its current HTML result or redirect.
- The contract does not change the number or contents of invitation emails.
