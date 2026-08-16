# Security Requirements Checklist

- [x] Email code remains state-bound, hashed, one-time and expiry-bound.
- [x] Production delivery failure creates no usable login state.
- [x] Production session cookie remains Secure, HttpOnly, SameSite=Lax and
  `__Host-` scoped.
- [x] Local fixed code remains non-production and loopback-only.
- [x] Local cookie support does not add a bypass header or cookie import protocol.
- [x] Safe redirect resolver remains authoritative after verification.
- [x] Evidence excludes secrets, tokens, credentials and live secret paths.
