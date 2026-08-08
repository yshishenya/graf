# Чек-лист качества требований: security и privacy

- [x] CHK001 Trust boundaries browser/desktop/provider/worker и authority заданы. [FR-005, FR-012, FR-032]
- [x] CHK002 Owner/Admin/Member visibility и multi-workspace isolation непротиворечивы. [FR-003–FR-006]
- [x] CHK003 CSRF/session/role recheck и re-auth sensitive actions определены. [FR-005, FR-015–FR-018]
- [x] CHK004 PAN/CVC и provider secret запрещены во всех client/evidence paths. [FR-029, FR-075, FR-077]
- [x] CHK005 Opaque payment method encryption/masking/revocation определены. [FR-037–FR-038]
- [x] CHK006 RLS inventory и same/cross-tenant tests обязательны для каждой новой таблицы. [FR-078, SC-001]
- [x] CHK007 Analytics/replay/log/diagnostic forbidden fields перечислены. [FR-058, FR-071, FR-076–FR-077]
- [x] CHK008 Promo/referral abuse controls не превращают сигналы в единственное доказательство. [FR-061, FR-066–FR-069]
- [x] CHK009 Audit/correction/four-eyes требования покрывают sensitive operator actions. [FR-056, FR-079]
- [x] CHK010 Account close/financial retention/provider boundaries используют правдивую deletion copy. [FR-018–FR-019, FR-080]

Результат: PASS — privacy/security требования трассируются в contracts и launch gates.

## Перепроверка новых trust boundaries 2026-08-06

- [x] CHK011 Storage/add-on/observed-refund/time-credit tables включены в RLS/audit requirements, а product refund-case/execution tables запрещены. [FR-078–FR-079, FR-093–FR-102]
- [x] CHK012 Refund provider mutation доступна только audited operator; support/browser не может изменить money ledger. [FR-053–FR-056, contract security]
- [x] CHK013 Unlimited fair-use/abuse controls отделены от скрытой commercial quota и не снимают capture safety. [FR-024–FR-028, FR-080]

Результат перепроверки: PASS — новые данные и полномочия имеют fail-closed границы.

## Финальная проверка abuse/privacy 2026-08-06

- [x] CHK014 Transient media is non-chargeable, non-playable, short-lived and overdue purge becomes a privacy incident. [FR-106]
- [x] CHK015 Fair-use review cannot be decided by volume/IP/device alone and provides bounded evidence/appeal. [FR-107]
- [x] CHK016 Post-role-loss/closed-account refund claim route exposes only safe claim facts and no money mutation. [FR-003]
- [x] CHK017 Emergency stop preserves claim intake/refusal/cancel while blocking provider and off-provider execution. [FR-109]

Результат финальной проверки: PASS — safety controls do not become hidden billing or deny statutory intake.
