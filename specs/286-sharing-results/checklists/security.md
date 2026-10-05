# Security requirements review — F286

Reviewer-owned. Requirements quality, not implementation proof.

- [x] CHK001 Are summary-only boundaries and exact independently verified invitation identity explicit, with old full-package compatibility? [FR-002,006,007,010]
- [x] CHK002 Are authorization, tenant/RLS/public lookup, deletion and metadata-free rejection requirements complete? [FR-006,020,021; plan Design 1,7]
- [x] CHK003 Are recoverable-token custody, expiry/revoke/rotation, idempotent publication and schema allowlist specified? [FR-003–005; data-model]
- [x] CHK004 Are no-secret logs/analytics, abuse controls, explicit public flag evidence and header constraints specified? [FR-021,024; quickstart 7]
- [x] CHK005 Are ambiguity/retry and cancellation concurrency boundaries defined without false provider exactly-once? [FR-009,011,019; data-model State rules]

## Независимая проверка — 2026-10-06

Проверены требования проектирования, не работа реализации. `tasks.md` и `analysis.md` перечитаны до реализации; задачи T001–T018 покрывают требования и последующие проверки.

- CHK002: spec FR-006,020,021; plan Design 1,7; data-model строки 3,7,27: права/изоляция, удаление и отказ без метаданных заданы.
- CHK003: spec FR-003–005; plan Design 1; data-model строки 7,11; contracts строки 5–6: ciphertext, стабильность, срок, явные операции и поддерживаемая схема заданы.
- CHK004: spec FR-021,024; plan Design 7; contracts строка 3; quickstart пункт 7: секреты, журналирование, заголовки, лимитер и включение после проверки заданы.
- CHK005: spec FR-009,011,019; plan Design 4; data-model строки 15,27: резервирование до сети, неизвестный исход и ограничения отмены заданы без обещания exactly-once.

CHK001: первоначальное замечание устранено. contracts/sharing.md строка 11: все непринятые приглашения требуют независимого входа; старый full-meeting объём прав сохранён, bootstrap сеанса запрещён старым и новым токенам.

Итоговое чтение перед реализацией: 5 [x], 0 [ ]. Уточнения auto_epoch, устойчивого requires_review, Google <=15 минут/organizer.self и исключения дубликатов прочитаны в plan/data-model; покрытие — T011–T013 и T017.
