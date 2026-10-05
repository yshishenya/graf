# F286 — анализ согласованности перед реализацией

2026-10-06. Read-only analyze выполнен после генерации tasks.md по активному prerequisite output. Установленный prerequisite script не поддерживает upstream --require-spec; использован --require-tasks --include-tasks, spec/plan прочитаны явно.

Результат: CRITICAL 0 · HIGH 0 · MEDIUM 0. Новых уточнений пользователя не требуется.

| Требования | Задачи |
|---|---|
| FR-001–007 | T003–006, T015, T017 |
| FR-008–011 | T007–010, T017 |
| FR-012–019 | T002, T009, T011–015, T017 |
| FR-020–021 | T002–005, T009, T015–017 |
| FR-022 | T006,T010,T014,T017 |
| FR-023 | T015,T017 |
| FR-024 | T016–018 |
| SC-001–005 | T003,T007,T011,T015,T017–018 |

Все 4 истории имеют независимые сценарии. Tests precede sensitive implementation; shared-file ownership исключает ложную параллельность. Новая публикация не ослабляет общий loader/старые ACL. Независимый вход явно обязателен всем непринятым приглашениям, включая legacy. API/version/auto_epoch и sticky review согласованы в модели/контрактах. Аудит/логи/Temporal payload не содержат документ/email/token. Существующие PostgreSQL/Temporal/Postal повторно используются; capture/провайдеры не меняются. Конституция/privacy/deletion/reference provenance и exact-SHA release/CD gates отражены.

Независимые reviewer checklists PASS 15/0 на проектировании; повторное чтение задач независимым reviewer и issue sync требуются перед кодом. Ни анализ, ни галочки не доказывают реализацию/выпуск. Все 18 tasks открыты; gates T017/T018 не могут быть закрыты только mock/prototype тестом.

Issue sync: 18 задач имеют отдельные issues #7547–7564, umbrella #7546. Mandatory canon hook запущен: глобальный validator обнаружил только чужой #7544 (missing area/type labels); его состояние не меняли. Тем же validate_issue проверены все 19 F286 issues: PASS. Этот внешний дефект не относится к F286 или её реализации.

Повторный analyze после точного уточнения migration path: src/twobrain_rec_server/db/migrations/versions/. Требования/очерёдность/покрытие прежние; CRITICAL 0 HIGH 0 MEDIUM 0.

Analyze повторён для независимой UI работы: T002 блокирует DB services/runtime integration; UI по reviewed API contract параллельно допустим, приемка только после интеграции. Новых FR/границ нет; CRITICAL/HIGH/MEDIUM 0.
