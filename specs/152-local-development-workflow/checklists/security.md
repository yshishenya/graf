# Security Checklist

- [X] Loopback-only infrastructure.
- [X] Existing session, CSRF, tenant and device boundaries reused.
- [X] Development code and cookie require explicit non-production local flag.
- [X] Production `__Host-` Secure cookie/defaults unchanged.
- [X] Local `.app` has a separate bundle identifier, no update feed, and a
  loopback-only wrapper with no production fallback.
- [X] No password, bypass token, legacy auth or production secret added.
