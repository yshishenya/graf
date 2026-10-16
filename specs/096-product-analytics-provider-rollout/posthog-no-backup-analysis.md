# Анализ FR-034a / T110 — 2026-10-04

Lane high-risk-product. Активный срез096, branch096-explicit-funnel-remediation; prerequisite script --require-tasks --include-tasks подтверждает canonical feature path. Сборка данного prerequisite не поддерживает --require-spec; spec.md проверен напрямую.

Уточнение владельца: запуск минимального PostHog без нового резервирования; возможна невосстановимая потеря аналитики. Конституция8.0.0 явно разрешает только это исключение до code implementation. Backup/deploy основного продукта сохраняются.

| Требование | Ownership | Проверка |
|---|---|---|
| required default / owner_accepted_loss, invalid scope fail-closed | T110 / issue7472 OPEN | Settings validation, scope matrix, required rollback |
| Только PostHog explicit; никаких generic/direct/broad/Yandex | T110 | explicit UUID requirement; other providers retain ops blockers |
| Только8backup/restore blockers, truthful missing proofs | T110 | raw evidence unchanged, waived list and loss caveat; campaign false |
| Retention/access/legal/consent/noIP gates сохранены | T110, существующиеT105–109 | missing/stale evidence and forbidden switches block; regression suites |
| Обычный выпуск и реальный ingestion отдельно | T109 open / T110 | exact PR CI does not prove production; no fake receipts/runtime flags |

Historical FR-003/SC-003 и прежний FR-034 backup mandate superseded ONLY by explicit FR-034a for this limited path; history is not reattested. Campaign/full operations do not inherit waiver. Global user data/source contracts, privacy pages, notices, landing/download, new credentials/grants, TTL/purge untouched.

Unresolved critical/high requirement findings:0 after explicit constitutional exception. Implementation prerequisite: independent reviewer-owned posthog-no-backup checklist must pass. Production blocker facts remain operator access/MFA, legal mapping,365-day enforcement/noIP/readback, secret-file wiring and normal release candidate; owner decision about backups does not supply those proofs.

Issue7472 successfully updated with T110 ownership and current scope, no duplicate issue. Disabled after_implement and analysis auto-commit hooks are not executed.
