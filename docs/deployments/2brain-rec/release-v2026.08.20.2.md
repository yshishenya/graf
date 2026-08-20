# Production closeout: `v2026.08.20.2`

## Immutable release

- Tag and GitHub Release: `v2026.08.20.2`
- Release SHA: `6651db70c5776530e270967715df6798034f65ae`
- Runtime branch: `master` at the same SHA
- Implementation PR: https://github.com/yshishenya/crisp/pull/5456
- Release PR: https://github.com/yshishenya/crisp/pull/5457
- Release: https://github.com/yshishenya/crisp/releases/tag/v2026.08.20.2

## Validation and deployment

| Gate | Result |
| --- | --- |
| Full exact-SHA macOS suite | pass; 697 tests |
| Full exact-SHA server suite | pass; 3066 passed, 1 expected skip |
| Strict PostgreSQL/RLS matrix | pass; 47 passed, 1 expected skip |
| Lint, compile and release checks | pass |
| Backup and restore rehearsal | pass; backup `20260820T012758Z` |
| Migration and disposable RLS verification | pass |
| Production smoke and cleanup | pass; no residue |
| API, Temporal and workers | healthy |
| Runtime SHA | matches release SHA |
| Rollback | not required; guarded backup remains available |

## macOS release gates

| Gate | Result |
| --- | --- |
| Developer ID Application and Installer | pass; Team `94N8HYG672` |
| Apple app notarization | accepted; request `b21674de-22c2-4561-8c8e-503dcf61d520` |
| Apple package notarization | accepted; request `6bc82df4-d72d-4531-8ce4-b842777db9fa` |
| Stapler and Gatekeeper | pass for app and package |
| Sparkle Keychain custody | pass; active trust generation 1 |
| Developer ID continuity | pass against `2026.08.19.2` |
| Installed Sparkle update | pass; `2026.08.19.2` → `2026.08.20.2` and relaunch |
| Public archive/appcast validation | pass after fresh HTTPS download |

## Public artifacts

- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- ZIP: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.20.2.zip
- PKG: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.20.2.pkg
- ZIP SHA-256: `c0f25223739013c4fb5bda371bd0a18d8b3b9d26adb41d28e88cb2056f5b7f17`
- PKG SHA-256: `471ce22a4f50b50659907a688fb64db2adbfe8b45872ad41bdb02e590f5646fd`
- Appcast SHA-256: `92f39a6c8512582903b207e9d31970f0291514f5246024261f980e6381db82bd`
- Previous signed appcast was retained before the live feed was replaced.

## Post-deploy audit and compatibility

- Aggregate-only API log audit found `0` HTTP 500, `0` HTTP 405, `0`
  tracebacks and `0` automatic GET/405 replays on email-link routes.
- The production login surface rendered successfully in the in-app browser.
- Database schema and stored user data did not change in this hotfix.
- The installed production app detected `2026.08.20.2` through the live Sparkle
  feed, downloaded it, installed it and relaunched successfully. The existing
  production session remained active, account settings opened with email shown
  as confirmed, and no macOS permission prompt or generic meeting-load error
  appeared. The installed app passed stapler and Gatekeeper checks again.
- To halt rollout, restore the retained previous signed appcast. A client that
  already installed this version requires a higher-CalVer forward rollback;
  never publish an unsigned or lower-version downgrade.

All evidence is metadata-only and contains no email address, one-time code,
credential, meeting content, raw audio, transcript or private screenshot.
