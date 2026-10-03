# Анализ текущего среза 096 — 2026-10-03

Область анализа: новые FR-030–034 и Phase10; исторические broad сбор/июльские runtime receipts не признаются готовностью нового режима.

| Требование | Задачи | Проверка |
|---|---|---|
| FR-030: личное текущее согласие, fail-closed | T105,T106,T109 | unknown/refused/revoked/stale0requests; accept only explicitauth action/current configured version |
| FR-031: server principal user pseudonym | T105,T106,T109 | forged/workspace ID не авторизует чужие события; auth switch reset |
| FR-032: accepted vs delivered, повтор | T107,T109 | failure не consumesmilestone; stableidempotency; ClickHouse syntheticreadback отдельно |
| FR-033: существующий allowlist | T108,T109 | запрещённые content/PII/IP поля, D7/payments вне минимальногоscope |
| FR-034: provider noIP, retention/access proofs | T108,T109 | $geoip_disable; no purge/runtimeflags/security changes; supportedconfig proposal |

Constitution check: privacy/authRLS/manualconsent/secrets/evidence gates сохраняются. Нет новыхproviders/credentials/OAuth. Primary implementationdraftdefault-off; legal/currentnotices readiness не фабрикуется. Отсутствие operationalbackup/access/retention proof блокирует production, но не syntheticisolatedvalidation.

Critical/high unresolved requirement findings:0 для изолированной подготовки. Runtimeacceptancepending по consentuser-actionpath, ingestdeliveryreadback, operatorsecurelogin, backup/restore/access/retention gates. Недостающие факты не заменяются claims. Независимый checklist review — отдельный обязательный gate до реализации.
