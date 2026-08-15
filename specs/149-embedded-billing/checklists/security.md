# Embedded billing security checklist

- [x] Existing validated session and tenant checks remain unchanged.
- [x] Existing CSRF and owner-only billing checks remain unchanged.
- [x] No secret or financial parameter crosses into a URL.
- [x] External payment navigation remains HTTPS and allowlist constrained.
- [x] Unknown external hosts remain blocked.
