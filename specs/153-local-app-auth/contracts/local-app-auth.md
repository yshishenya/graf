# Local App Auth Contract

`GRAF_LOCAL_APP=1` is valid only with `GRAF_CABINET_REQUIRE_EXPLICIT_BASE_URL=1`
and an `http://127.0.0.1:*` or `http://localhost:*` origin. In this profile,
unauthenticated cabinet recovery opens the same-origin `/login` route with a
safe `next=/desktop/meetings` path inside the existing WebKit session.

Without the explicit local profile, the existing production/default recovery
contract remains unchanged.
