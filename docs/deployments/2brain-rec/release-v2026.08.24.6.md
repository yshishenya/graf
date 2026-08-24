# Production closeout: v2026.08.24.6

Дата: 2026-08-24  
Контур: `2brain.dev` / `https://rec.2brain.pro`

## Результат

- GitHub Release: [v2026.08.24.6](https://github.com/yshishenya/graf/releases/tag/v2026.08.24.6), опубликован.
- Production runtime SHA: `a12c0b55755169b184424f533305444ea7c342da`.
- Release tag SHA: `bdc07f0b79f4301d73ea435260922dcb5dee9c0c`.
- Production deploy: `deploy_result=pass`.
- Backup перед выкладкой: `/opt/projects/2brain-rec/backups/20260824T090824Z`.

## macOS update

- Public feed: `https://rec.2brain.pro/static/public/downloads/graf-appcast.xml`.
- Feed сообщает `2026.08.24.6` и ZIP длиной `7,693,540` байт.
- Sparkle archive/appcast signatures и fresh HTTPS readback: PASS.
- Apple notarization: ZIP и PKG `Accepted`.
- Stapler и Gatekeeper: PASS.
- Встроенное обновление на установленном `/Applications/GRAF.app` проверено: `.5` → `.6`.
- GitHub Release содержит ZIP, PKG, appcast, SHA-256 и русские release notes.

## Авторизация

- До исправления запущенный `rec-api` имел пустые `TWOBRAIN_WEB_LOGIN_WORKSPACE_ID` и отключённый email login.
- Auth-зависимые контейнеры пересозданы с production `.env`.
- После исправления workspace bootstrap, email delivery, Postal URL и from-address загружены в runtime.
- `/login` больше не показывает «Кабинет входа не настроен».
- Email form присутствует; Yandex и VK OAuth start возвращают `303` на провайдер.
- `/api/v1/health/live` и `/api/v1/health/ready`: `200`.
- Backup runtime-конфигурации: `.env.backup-before-auth-env-dedupe-20260824T103957Z`.

## Валидация и ограничения

- Focused Feature 199: `69/69 PASS`.
- Fast lane: `PASS`.
- Production smoke, health и контейнерная readiness-проверка: `PASS`.
- Full CI не запускался по прямому указанию пользователя и не считается PASS.
- Реальное письмо OTP намеренно не отправлялось без адреса пользователя; endpoint и runtime-конфигурация проверены без отправки внешнего сообщения.

## Связи

- Feature PR: https://github.com/yshishenya/graf/pull/5784
- Release PR: https://github.com/yshishenya/graf/pull/5785
