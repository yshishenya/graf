# Требования к восстановлению cleanup

Reviewer-owned requirements-quality review; область только FR023–27, предыдущие сценарии не переоценивают текущий product rollout.

- [x] CHK001 Указаны точный retryable SQLSTATE и только precommit граница. [FR-023/025, data-model §Cleanup transaction retry]
- [x] CHK002 Определены весьtransaction rollback, максимум попыток и паузы. [FR-023, plan §Узкий high-risk cleanup срез]
- [x] CHK003 Явно сохранены synthetic identity/prefix/tenant filters и запрет широкой очистки. [FR-024, spec §Уточнения 2026-10-02]
- [x] CHK004 Определены счетчики committed-only и storage только послеcommit. [FR-024/026, data-model §Cleanup transaction retry]
- [x] CHK005 Определены exhausted/non40P01/postcommit fail-closed сценарии. [FR-025, spec §Acceptance]
- [x] CHK006 Требуется реальная конкурентная PostgreSQL репродукция, не только mocked exception. [FR-026, plan §Стенд, T067]
- [x] CHK007 Требуется проверка соседних не-smoke данных и отсутствие production fixtures. [FR-026, quickstart §Изолированная проверка bounded deadlock recovery, T069]
- [x] CHK008 Сохранены CLI/output shape, residue/readiness/backup/rollback gates. [FR-027, contracts/smoke-evidence-contract §Bounded cleanup retry]
- [x] CHK009 Границы полномочий и запрет нового CD/F283/UI изменений однозначны. [FR-027, plan §Узкий high-risk cleanup срез, T070]
- [x] CHK010 Указаны безопасные evidence, independent review и exact-SHA CI. [FR-027, plan §Constitution, quickstart §Изолированная проверка bounded deadlock recovery, T069/070]

Независимый review требований: [cleanup-safety-review.md](../cleanup-safety-review.md). Отметки подтверждают качество требований, а не готовность реализации или разрешение deployment.
