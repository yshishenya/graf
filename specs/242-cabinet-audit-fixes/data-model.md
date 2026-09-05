# Data model F242

Миграций нет. UserIdentity.locale/timezone/theme сохраняют прежние допустимые значения. Обновление under row lock только явно переданных полей, весь набор валидируется до мутации; audit fields соответствует набору. Organization mismatch → 404; no supported fields/invalid → 422 без commit/audit.

WorkspaceSubscription и TrialActivation неизменны: starts_at от server confirmation, ends_at = starts_at + TRIAL_DAYS. UI различает предварительный и фактический интервал. Invoice/payment method/recurring consent при trial не создаются.

Storage bytes остаются integer; форматирование только presentation. ProfileView из существующего helper; fragments без дополнительного lookup.
