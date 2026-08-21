# Commercial readiness

## Code state

The public pricing view is derived from the same effective `billing_plan_versions` rows used by checkout. Exact 100,000/1,000,000 minor RUB units, matching storage/processing/offer version and enabled catalog rows make the approved tariff visible. Actual payment remains a separate fail-closed state: it additionally requires enabled checkout, no emergency stop, an exact production shop and release SHA, and every current billing launch gate.

The plan descriptor, landing, structured data, checkout snapshot tests and payment conditions use 1,000 RUB/month, 10,000 RUB/year, a seven-day trial and an exact 2,000 RUB annual saving.

## Production state to verify before sale

- A read-only production query on 2026-08-21 returned zero `billing_plan_versions` rows and zero `billing_launch_gates` rows. The current runtime therefore cannot show or sell the approved tariff yet.
- YooKassa test-shop and controlled production canary evidence is not recorded for this SHA.
- Product, unit economics, finance/accounting, security/privacy, QA/accessibility, infrastructure, provider canary and global rollout gates require current independent approval rows.
- Checkout runtime enablement and emergency-stop rehearsal require the documented dry-run and explicit production execute approval.

The approved tariff can be published after its two immutable catalog rows are provisioned. Legal approval alone does not prove that a real payment, receipt, cancellation, renewal failure and rollback work, so payment remains fail-closed until those operational facts exist.
