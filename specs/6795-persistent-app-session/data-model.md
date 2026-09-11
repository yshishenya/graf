# Data model

AuthSession сохраняет схему. issued_at не меняется; expires_at становится границей бездействия, last_seen_at обновляется не чаще пяти минут. Условный UPDATE требует status=active и expires_at>now; итоговый expires_at не уменьшается при параллельных запросах. Окончание и отзыв не имеют обратного перехода через activity. RegisteredDevice/binding сохраняют существующий heartbeat и проверки.

Cookie сохраняет name/domain/path/secure/httpOnly/value; меняется только срок. Успешный native ответ содержит X-GRAF-Auth-Expires-At как Unix seconds UTC, без значения токена. Нет новой таблицы, миграции или фонового хранилища.
