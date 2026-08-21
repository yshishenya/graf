# Link and package review

Checked on 2026-08-21 against the local integrated server preview.

- `/`, `/download`, `/privacy`, `/cookies`, `/terms`, `/offer`, `/analytics-consent`, `/robots.txt` and `/sitemap.xml`: HTTP 200.
- Every landing fragment target exists.
- The real application router contains `/login?next=/meetings` handoff support.
- The landing has one download destination: `/download`.
- The download page exposes exactly one clickable universal macOS package; Windows and Linux remain non-clickable planned states.
- Installer response: HTTP 200, `application/octet-stream`, 6,258,386 bytes.
- Installer SHA-256: `c4a36a0731d1d14b4d13b8faca0a55a638c2c3349bdd90aa73db4440e027a5d7`.
- Telegram support and all four Yandex disclosure/opt-out links returned HTTP 200.
- `mailto:yan@shishenya.ru` is the only support email link.

All visible prices use non-breaking thousands separators. The yearly value is stated as an exact 2,000 RUB saving; the mathematically incorrect `-20%` claim is not used.
