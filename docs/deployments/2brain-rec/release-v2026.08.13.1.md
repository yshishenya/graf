# Production receipt: v2026.08.13.1

Дата: 2026-08-13  
Контур: `2brain.dev` / `https://rec.2brain.pro`  
Опубликованная ветка: `codex/release-2026-08-13-1`  
Опубликованный SHA: `f7c27341f37027a3415e341e78057f99dde856d7`

## Результат

- Production deploy — PASS; итоговый verdict: `infra_smoke_ready`.
- Полный локальный gate точного SHA — PASS: 2905 server-тестов прошли,
  1 пропущен; 42 strict-теста, Swift/macOS, ContractValidation, lint, compile и
  metadata-only evidence scan прошли.
- Remote backup, проверка миграций, processing/media workers и Temporal — PASS.
- Metadata-only smoke cleanup завершён без остатка.
- Резервная копия перед выкладкой:
  `/opt/projects/2brain-rec/backups/20260813T151305Z`.

GitHub Actions не выполнил шаги из-за billing/spending limit аккаунта. Это
ограничение runner, а не падение кода; обязательный полный локальный gate
точного SHA и production smoke выполнены.

## Публичный smoke

Проверено 2026-08-13 после выкладки:

- `/`, `/download`, `/login`, `/sign-up`, `/privacy`, `/cookies`, `/terms`,
  `/offer`, `/analytics-consent` — HTTP 200.
- `/api/v1/health/live` и `/api/v1/health/ready` — HTTP 200.
- Production runtime сообщает SHA
  `f7c27341f37027a3415e341e78057f99dde856d7`.
- Версия текста аналитического согласия — `2026-08-13.1`.
- Политика cookies правдиво описывает состояние с выключенной аналитикой.
- Public analytics, product analytics, генерация итогов и billing checkout —
  выключены.

## Публичный установщик

- URL со стабильным fingerprint:
  `/static/public/downloads/graf.pkg?v=6c6cb57affeb`.
- Размер: 6 136 432 байта.
- SHA-256:
  `6c6cb57affebd65430c8b49a4636506638950e6ecb9fc4c88b638b6067342c5c`.
- Immutable cache contract — PASS.
- Developer ID signature, Apple notarization, stapling и universal
  `arm64` + `x86_64` — PASS.

Публичный файл совпадает с asset GitHub Release `v2026.08.13.1`. Receipt
содержит только технические метаданные и не содержит пользовательских данных,
содержимого встреч или секретов.

## Граница релиза

После создания tag в `master` появились коммиты `eb486d04` и `b951ab07`. Они не
входят в этот релиз: production намеренно закреплён на проверенном SHA
`f7c27341`. Следующий релиз должен пройти собственный exact-SHA gate.

## Ограничения

- Поддерживается macOS 14.5+ на Apple Silicon и Intel; отдельный физический
  smoke на Intel Mac остаётся ручной проверкой.
- T058 остаётся открытым до внешних подтверждений размещения данных,
  уведомлений Роскомнадзора, трансграничного контура и processor/DPA register.
- T059 остаётся открытым до подтверждения YooKassa, 54-ФЗ, чеков, возвратов,
  автопродления и действующей checkout-оферты.
- Доказуемый versioned acceptance receipt при регистрации требует отдельного
  auth/privacy-среза.
