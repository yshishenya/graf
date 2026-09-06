# Release evidence: Feature 232

Дата закрытия: 2026-09-04

Validation lane: release / deploy

Релиз: [`v2026.09.04.1`](https://github.com/yshishenya/graf/releases/tag/v2026.09.04.1)

Выпуск выполнен после последнего реально опубликованного релиза
`v2026.09.02.1` и включает исправление запуска GRAF из Feature 232 вместе с
остальными готовыми изменениями общего release train.

## Граница выпуска

- Feature 232 implementation PR #6362: head
  `0988ec65d493e2261c6fee177cd4a8d858b6b0c9`, merge
  `c9ad0ba26b8489bbcd08b87e62b6ee0f50be7801`; `governance-fast` PASS:
  <https://github.com/yshishenya/graf/actions/runs/33641938434>.
- Candidate SHA, tag и production runtime:
  `704a374f0eee454fa41e7bd820154c900cd0e910`.
- Immutable release evidence:
    - `.dev/release/trains/train-v2026.09.04.1-704a374f0eee.json` — SHA-256
      `6a479770d5d09002deb7a187d4404de2b8f2ea63d81c3919b80f504dec69bd81`;
    - `.dev/release/trains/train-v2026.09.04.1-704a374f0eee-go.json` — SHA-256
      `15af28471eeb0cc90b115383095aa0d420aed4330eb2c5e60eaba64661a28da2`;
    - `.dev/release/candidates/rc-v2026.09.04.1-704a374f0eee.json` — SHA-256
      `c12852edc33fde63d23d246dd1b7e2847fda36dbe2e37072f45fdb4513482940`;
    - `.dev/release/decisions/rc-v2026.09.04.1-704a374f0eee.decision.json` —
      SHA-256 `a5da224087407b202ca36c91732d0970f6ebac51b180a446045698338c92e5c4`;
    - `.dev/ci-evidence/authoritative-rc-20260904T115032Z-dded694a248d.json` —
      SHA-256 `84c92c41b326ac30b28fae603fc85a564886aa3c3e6d1de315a8ef376bebefd1`.
- Authoritative GitHub `release-full`:
  <https://github.com/yshishenya/graf/actions/runs/33869861986> — PASS для
  macOS, server/infrastructure и aggregate evidence.
- `infra/scripts/cd-remote.sh --dry-run --branch master`: PASS на
  `704a374f0eee454fa41e7bd820154c900cd0e910`; execute остался привязан к
  immutable decision/evidence.
- Production deploy: PASS; backup
  `/opt/projects/2brain-rec/backups/20260904T122317Z`, restore rehearsal,
  миграции, RLS, smoke, cleanup и public health прошли.
- Publication attestation:
  `pa-rc-20260904T115032Z-dded694a248d`; файл
  `.dev/release/attestations/rc-v2026.09.04.1-704a374f0eee.publication.json`,
  SHA-256 `58a81edee267dd38918dcbb4af329a0c7105d0a7960b811c5bbce0e04991aab9`.

## macOS-публикация

- Universal app: `arm64 + x86_64`, версия `2026.09.04.1`.
- Mach-O UUID: `2BC2FF33-2A77-35FC-99E7-A47934E65CEC` (`x86_64`) и
  `77012DFB-26BE-33CC-A21C-2CB43B3C3FD5` (`arm64`).
- Developer ID Application и Developer ID Installer: PASS.
- Apple notarization: ZIP `581bf6c8-8c82-4c24-a5f5-9594c571df46` — Accepted;
  PKG `783c81ff-a4bd-47b4-90dd-111fb4ecd2b9` — Accepted.
- APP/PKG stapling и Gatekeeper: PASS.
- Публичный ZIP: `GRAF-2026.09.04.1.zip`, `7 732 852` bytes, SHA-256
  `70bd9ebfbb0fdaaaba249ba40f4bdb5ae93e39237e997e043cc973493cf057b3`.
- Публичный PKG: `GRAF-2026.09.04.1.pkg`, `7 543 553` bytes, SHA-256
  `e3091c4f2a7e8238e19f0802f7eb6008b489381baf737fc914ba73f18cde7be0`.
- Публичный appcast: `3 205` bytes, SHA-256
  `9ab8c33b2d35c34dac8b9144da9262513b62c8a43f2a3c10b6eb79cf5da6474f`;
  enclosure version `2026.09.04.1`, length `7732852`.
- Версионные ZIP/PKG и checksums опубликованы до замены appcast. Предыдущие
  `graf.pkg` и `graf-appcast.xml` сохранены с отметкой
  `pre-v2026.09.04.1-20260904T124635Z`.

## Обратная проверка и установленное приложение

- Публичные ZIP, PKG, `graf.pkg` и appcast скачаны обратно с
  `https://rec.2brain.pro`; размеры и SHA-256 совпали.
- ZIP integrity, Sparkle signature, Developer ID continuity, APP/PKG staples,
  Gatekeeper и запуск на `arm64`/`x86_64`: PASS.
- `GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1
  apps/macos/Scripts/validate-app-updates.sh <new-app> <v2026.08.28.11-app>
  <public-zip> <public-appcast>`: PASS для последнего подтверждённого рабочего
  predecessor `v2026.08.28.11`; version, designated requirement, Developer ID,
  Sparkle archive signature и appcast согласованы.
- Нерабочая установленная `v2026.09.02.1` заменена проверенным публичным
  приложением с тем же bundle ID, Team ID и designated requirement.
- `/Applications/GRAF.app` сообщает версию `2026.09.04.1` и успешно запущено
  из каталога приложений. Предыдущая копия сохранена локально до завершения
  проверки выпуска.

## Ограничения

- Для уже установленной нерабочей `v2026.09.02.1` нужен ручной переход на этот
  выпуск; данные и настройки сохраняются.
- При повторной обработке вручную заданные имена спикеров сбрасываются.
- Серверное изменение ротации backup, сохранённое в production stash, не входит
  в релиз и требует отдельной фичи и PR.
