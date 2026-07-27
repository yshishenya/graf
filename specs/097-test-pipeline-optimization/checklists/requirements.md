# Checklist требований

- [x] Цель сформулирована измеримо: fast lane и полный PostgreSQL lane.
- [x] Database fidelity и production-compatible test boundary явно определены.
- [x] Указана безопасная boundary для disposable database.
- [x] Указана worker/test isolation strategy.
- [x] Указан collection union guard против тихого снижения покрытия.
- [x] RLS, migrations и audio/export tests сохранены в полном lane.
- [x] Governance и hardware/spike suites отделены от обычного fast lane.
- [x] Secrets/meeting content/evidence ограничения зафиксированы.
- [x] Production topology и product behavior вне scope.
- [x] Owner-only default audio download, явные policy overrides и отказ другим viewers определены измеримо.
- [x] Порядок ordinary → governance → strict RLS и исключение optional spike tests определены измеримо.
