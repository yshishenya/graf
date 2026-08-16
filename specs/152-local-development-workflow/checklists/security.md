# Security Checklist

- [X] Loopback-only infrastructure.
- [X] Existing session, CSRF, tenant and device boundaries reused.
- [X] Development code and cookie require explicit non-production local flag.
- [X] Production `__Host-` Secure cookie/defaults unchanged.
- [X] No password, bypass token, legacy auth or production secret added.
