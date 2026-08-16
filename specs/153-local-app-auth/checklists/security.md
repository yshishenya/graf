# Security Checklist

- [X] Local recovery is gated by an explicit loopback-only flag.
- [X] Existing email-code, CSRF and session cookie boundaries are reused.
- [X] No browser-cookie import, bypass header, password flow or OAuth change is added.
- [X] Production/default behavior is covered by regression tests.
