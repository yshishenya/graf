# Данные и переходы

Содержимое не копируется. Сущности: Meeting, MediaRevision, ProcessingResult, MeetingSummarySlot, MeetingOutcomeGenerationAttempt, MeetingOutcomeSet.

Summary: not_requested → queued → generating/blocked_dependency → available/partial либо failed/unavailable. Ожидание без attempt допустимо лишь при доказанном намерении автоматических итогов. Опубликованный прежний результат и новая попытка — независимые оси; отсутствие новой версии не стирает старую. Запросы связаны с workspace+meeting+media/source result, deletion epoch и template.

Desktop sync добавляет optional summary metadata к review: отсутствие у старого сервера — unknown, не failed/ready. ServerTruthFingerprint читает старую очередь без потери значений. После transcript существующий GET follow-up продолжается до terminal summary. Транспортный сбой не стирает готовность.

Preferences: reminders/offset/showTitles/sound сохраняются; recap — явный контроль, отсутствующее старое значение false. Identity: auth context+session/meeting+milestone/occurrence; свежесть по текущему переходу. Startup не объявляет старые ready items новыми. Logout/scope change отменяет pending/delivered и старые responses; unknown sessions не перепривязываются. Новый error occurrence только после наблюдавшегося recovery.

Retention не меняется: freshness уведомления имеет собственный короткий срок. Клик проверяет доступность записи, owner и разрешённый внутренний маршрут без произвольного URL.
