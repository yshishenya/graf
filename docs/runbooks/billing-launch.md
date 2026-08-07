# Запуск биллинга GRAF

Этот runbook описывает только контролируемое включение биллинга. До получения
всех подписей checkout остаётся `default-off`, а merchant refund выполняется
только во внешнем кабинете YooKassa.

## Перед canary

- [ ] Product: утверждены `Free`/Trial/`Личный`, storage ladder и fair-use copy.
- [ ] Unit economics/finance/accounting: подтверждены COGS, gross-margin floor,
  54-ФЗ/VAT, чеки и финансовое хранение.
- [ ] Legal: опубликованы оферта, recurring consent, immediate-Free и
  email-only refund boundary.
- [ ] Security/QA: пройдены RLS, CSRF, redaction, accessibility и test-shop
  сценарии; есть backup/restore evidence.
- [ ] YooKassa: test/prod shop разделены, webhook secret и encryption key
  ротированы, provider capabilities подтверждены письменно.

## Canary procedure

1. Включить `BILLING_CHECKOUT_ENABLED` только в test shop и проверить monthly,
   yearly, saved-card, decline, timeout/unknown, late success и receipt.
2. Проверить exactly-once entitlement, immediate Free без grace/retry,
   storage admission и отсутствие refund mutation.
3. Включить production для одного allowlisted cohort с emergency stop,
   owner-on-call и read-only reconciliation.
4. Наблюдать webhook lag, unknown age, duplicate prevention, storage gaps,
   referral/promo liability и support-contact guardrails.

## Stop и rollback

При любой расходимости суммы/валюты, неизвестном исходе без восстановления,
RLS/redaction нарушении, двойном списании, storage over-admission или missing
receipt немедленно выключить checkout/binding/renewal mutations. Не удалять
ledger и не запускать возврат из GRAF. Сохранить metadata-only incident,
заморозить cohort, восстановить последнюю миграцию только по утверждённой
процедуре и разбирать refund во внешнем merchant cabinet.

## После canary

Сохранить exact-SHA evidence, результаты миграции/backup, список владельцев
инцидентов и решение о расширении cohort. Отдельно подтвердить, что checkout
и automatic renewal остаются выключены при отсутствии любой обязательной
подписи.
