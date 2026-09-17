# Data model
Схема не меняется. AuthSession принадлежит пользователю и рабочему пространству; RegisteredDevice и AuthSessionDeviceBinding определяют доступ.
AccountSessionView.active = is_session_token_valid AND access_allowed. Неизвестное имя клиента не является признаком недоступности.
Current определяется точным ID текущей сессии. can_revoke = active AND not current.
Отозванные, истёкшие, replaced и access-blocked записи остаются в существующем хранилище, но не представлены в интерфейсе.
