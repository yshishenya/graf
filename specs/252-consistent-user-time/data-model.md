# Данные

UserIdentity.timezone становится nullable, String(64), без default Moscow и ограничения на два значения. NULL — выбор ещё не сохранён; приложение показывает пояс устройства. Валидное IANA сохраняется существующей формой. Старый UTC сохраняется; Moscow сохраняется при auth audit account_preferences_updated с fields содержащим timezone, иначе снимается старое значение по умолчанию. Downgrade блокируется, если присутствует пояс вне Moscow/UTC; NULL возвращается к прежнему default. Сохранённые datetime обозначают абсолютный момент, naive историческое datetime считается UTC.
Пояс просмотра — проверенное zoneinfo IANA-имя из сохранённого предпочтения аккаунта, иначе cookie `graf_timezone`, область path=/, SameSite=Lax, Secure в HTTPS; не авторизация и не настройка финансовых периодов. Неизвестный/пустой пояс — UTC с подписью.
Эффективный timestamp: started_at; для ручной загрузки без него created_at, иначе NULL. Нативная запись: recordingMetadata.recordingStartedAt ?? createdAt. При равенстве стабильный id; неизвестные даты в конце.
Календарная дата и duration не превращаются в timestamp. API ISO-поля не форматируются для чтения человеком.
