# Production receipt: `v2026.08.23.4`

## Immutable release

- Tag and GitHub Release: `v2026.08.23.4`
- Release SHA: `9c67e1b89050f202582dcf602d8860e9b92d36ce`
- Runtime branch: `master`
- Runtime SHA: `9c67e1b89050f202582dcf602d8860e9b92d36ce`
- Implementation PR: https://github.com/yshishenya/crisp/pull/5560
- Release PR: https://github.com/yshishenya/crisp/pull/5561
- Feature: `specs/190-otp-code-input/`
- Validation lane: `release-deploy`
- Дата выкладки: 2026-08-23

Receipt содержит только агрегированные результаты. Секреты и пользовательские
данные в него не включались.

## Exact-SHA и release validation

| Гейт | Результат |
| --- | --- |
| Feature focused contracts | PASS; 155 тестов |
| PostgreSQL integration harness | PASS; 67 тестов |
| macOS Swift suite | PASS; 725 тестов |
| Fast local lane | PASS; 1168 тестов, lint и compile |
| Browser/embedded UI inventory | PASS; 5 сценариев, 6 слотов |
| CD dry-run | PASS; `infra/scripts/cd-remote.sh --dry-run --branch master` |
| Broad CI baseline | 3306 passed, 1 несвязанный calendar performance failure, 1 skipped |
| Full CI перед deploy | Не повторялся по прямому указанию пользователя |

## Production deployment

- Execute прошёл на точном SHA с явно согласованным `--skip-local-ci`.
- Backup: `20260823T025715Z`.
- Restore rehearsal: PASS.
- Migration head: `0077_provider_unlink_xworkspace`.
- API live/readiness: PASS; `/api/v1/health/live` — `ok`,
  `/api/v1/health/ready` — `ready`.
- `rec-api`, `rec-media-worker`, `rec-processing-worker`, Temporal, Postgres и
  MinIO — healthy/running.
- Production smoke, automatic dispatch и public download/update smoke — PASS.
- Remote `master` и runtime совпадают с release SHA.
- Rollback не потребовался.

## Product scope

Feature 190 меняет только общий визуальный и поведенческий ввод email-кода:
шесть квадратных ячеек, одна цифра на ячейку, вставка и автозаполнение. Формат
серверного поля `code`, данные пользователя и остальная логика авторизации не
изменялись.

Повторный exact-SHA full CI перед deploy не заявляется как пройденный: он был
пропущен по прямому указанию пользователя. Все перечисленные результаты
проверки сохранены в агрегированном виде.
