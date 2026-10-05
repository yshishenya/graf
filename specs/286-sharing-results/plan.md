# Implementation Plan: Передача итогов и автоотправка

**Branch**: `286-sharing-results` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

## Summary

Повторно использовать права, Fernet, Postal, Temporal и PostgreSQL GRAF. Сохранённый узкий документ связывает общую ссылку и адресный пакет; новые правила не создают собственную систему авторизации. UI кабинета повторяет согласованный макет.

## Technical Context

**Language/Version**: Python 3.13, JavaScript, Jinja2; существующие Swift/WebView без изменения бинарника.
**Primary Dependencies**: существующие FastAPI, SQLAlchemy, cryptography, Temporal; новых зависимостей нет.
**Storage**: существующий PostgreSQL, tenant RLS по ADR-003; публикации/пакеты/правила хранятся долговечно.
**Testing**: pytest PostgreSQL, существующие JS-проверки, браузер CUA и GRAF Dev.
**Risk / Validation Lane**: high-risk-feature (privacy/auth/backend/UX).
**Release Gate**: точный PR SHA: governance-fast, macos-pr, pr-metadata; затем merged SHA, CalVer, frozen candidate, один release-full, CD dry-run/execute, public health и синтетическая feature smoke.
**Target Platform**: сервер Linux Docker, веб и встроенный кабинет GRAF Dev.
**Project Type**: существующий сервер и серверный интерфейс.
**Performance Goals**: один краткий snapshot на публикацию, до 50 получателей, ограниченные выборки due jobs; сеть вне транзакции и блокировок.
**Constraints**: отсутствие новых SaaS, секреты только серверно; immutable snapshot; unknown не повторяется; актуальные ACL/deletion/pause/suppression перед каждой попыткой.
**Scale/Scope**: внутренняя встреча/серия и ручная адресная передача, одна публикация на ссылку.

## Constitution Check

До исследования и после проектирования: PASS. Capture/MediaScribe/AI-провайдеры/observability не меняются. PostgreSQL/Temporal/Postal уже одобрены. Новые tenant-таблицы получают RLS; public lookup использует существующий узкий токеновый путь. Снимок — управляемые данные встречи и входит в deletion. Веб-страница с итогами не содержит replay/внешней аналитики. Собственные компоненты и переменные оформления; сторонние assets отсутствуют. Серверный выпуск не меняет публичный macOS installer/appcast; их текущее содержимое сохраняется. Любое изменение нативного бинарника потребует отдельной notarization цепочки. Approval: прямой запрос пользователя реализовать и выпустить; действия только после обязательных проверок, без обхода ворот.

## Design

1. Backend: `db/models/summary_sharing.py`, миграция от текущей Alembic head, `cabinet/summary_sharing.py`, `api/summary_sharing.py`, `workflows/summary_delivery.py`. Снимок содержит только явную проекцию (meeting label/date/duration, summary_sections, safe protocol). Стабильная общая ссылка хранит ciphertext в grant; hash остаётся проверкой. Старые ciphertext-less ссылки не ротируются молча: хозяину предложена явная замена. Старая запись и доступ сохранены.
2. Адресный пакет: сохраняет snapshot/список/ключ операции; delivery rows encrypt email, hash для dedupe. До dispatch прав нет. При адресном чтении сохраняется snapshot, подтверждённый email обязателен, независимые существующие ACL не меняются. Старые full_meeting API и объёмы существующих прав остаются совместимыми; ни старое, ни новое непринятое приглашение не создаёт сеанс из bearer-токена. Новый пакет создаёт summary-only. Invitation acceptance срок (до 7 дней) отдельный от reading expiry (30 дней).
3. AUTO: `db/models/summary_autosend.py`, `cabinet/summary_autosend.py`, `api/summary_autosend.py`. preferences owner/workspace default ASK=true, paused=false; meeting/series rule exact roster, template. Правило owner result plus organizer/explicit distributor, без title matching. Поддержанный Google снимок должен быть обновлён не более 15 минут назад, явно полный, с organizer.self; иной источник или недоказанная полнота требуют ручной проверки. Полнота календаря сохраняется при нормализации; external/unknown/declined/resources/private/stale/changes → ASK. Для безсерийной встречи только meeting scope. ENABLE time ограничивает будущие экземпляры, readiness deadline 24h. Ручное включение meeting scope до готовности; серия только будущие. Due batch scheduled after readiness+5m, no access during delay.
4. Durable sending: существующий DispatchIntent и Temporal; maintenance восстанавливает pending, workflow содержит только batch ID, не email/secret/text. Commit `sending` перед Postal; crash/ambiguous response → unknown. Provider idempotency не предполагается. Блокировки meeting→preference→rule→batch→recipient; deletion/revoke/cancel/pause/suppression проверяются до неначатой передачи. Сеть выполняется без открытой DB-транзакции; зарезервированная попытка может завершиться. Manual rate limits используют настоящий device; AUTO отдельный persisted authority и durable owner budget, не фиктивный device.
5. UI (основной агент): existing share dialog gets two sections; new isolated JS `summary-sharing.js` bound only to new controls, старый JS не запускается параллельно. Existing styles/tokens, details for link controls. Email exact addresses, staged selection, success plain. Settings block and meeting status/ASK; restore focus and reject ambiguous send retries.
6. Public receiver: existing summary renderer gets saved safe projection and one voluntary own-meeting CTA. Narrow address opt-out is signed/scoped; GET only shows, POST changes. No login needed to opt out. Invalid token never reveals name/roster; no third-party content on document.
7. Deletion: remove snapshots/ciphertext/recipient address and cancel queued sends in existing cleanup; no promises to retrieve outbound copies. Secret-safe logging: `/public-shares/` ingress masking and shared limiter validated before enabling public-links flag; existing approval flag is evidence, not sole check.

## Validation Plan

Follow [quickstart.md](quickstart.md). Independent requirements checklists before implementation; independent code/security review and convergence afterward. Full CI stays release-bound, never replaced by prototype/unit proof. Real emails may be sent only to explicitly controlled synthetic test destination; otherwise transport acceptance is proven with disposable fixtures and provider/runtime readiness reported separately. Actual unsolicited meetings are not used in smoke.

## Project Structure

`specs/286-sharing-results/{spec,plan,research,data-model,quickstart,tasks}.md`, `contracts/sharing.md`, `checklists/{requirements,security,ux,infra}.md`.
Implementation under `apps/server/src/twobrain_rec_server/{db/models,cabinet,api,workflows}`; tests `apps/server/tests/{integration,contract,unit}`; changelog `changes/unreleased/F286.yaml`.

## Complexity Tracking

No constitution exception. One snapshot table instead of generic version framework; one batch/recipient ledger instead of separate mail service; existing queue and transport. Native platform/runtime dependencies unchanged.

## Safe rollback

Disable new link creation/batches/rules and scheduling first; pause AUTO and cancel all unreserved recipients. Drain reserved attempts; interrupted sending becomes unknown and is never replayed. Roll back only to code compatible with additive nullable columns/tables; keep data schema until all readers/workers are stopped and cleanup is proven. Never restore revoked grants, cancelled jobs, prior ciphertext or expired tokens from rollback. Metadata-only backup/restore and runtime role checks precede deploy.
