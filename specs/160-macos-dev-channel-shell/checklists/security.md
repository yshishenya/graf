# Security Checklist: macOS Dev Channel and Native Home

- [x] Production bundle ID, signing, entitlements, and Sparkle trust are preserved.
- [x] Dev rejects production and non-loopback origins.
- [x] Dev has no production Sparkle feed or updater trust keys.
- [x] Missing/mismatched signing identity fails closed before install replacement.
- [x] Application-support and preference namespaces cannot silently mix channels.
- [x] No TCC reset, database edit, hidden profile, driver workaround, or external-header leak is introduced.
