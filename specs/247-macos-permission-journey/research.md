# Исследование F247

Decision: компактное окно по явному действию. Rationale: «Позже» не требует отдельной персистентной политики; нельзя потерять путь возврата. Alternatives: автоматический модальный onboarding и многоэкранный мастер добавляют переходы и повторные прерывания.
Decision: названия по пользе — «Ваш голос» / «Голоса собеседников». Rationale: Granola показывает подобное разделение. System label остается в контекстной помощи.
Decision: нативная иллюстрация рядом с инструкцией. Rationale: Screen Studio использует визуальный ориентир Settings; нет необходимости в overlay или Accessibility.
Decision: право != функциональная готовность. Rationale: code audit выявил ложный restart unknown→granted, SCShareableContent до согласия и повторный sheet при активации. Проверка bounded/passive-first; stale не доказывает обязательный restart.
Decision: правила автозаписи сохранены. Research review permission_design_review подтвердил: закрывать старый ask без отказа + retryable, проверять queued decisions, после настройки обычный цикл. Иначе текущая встреча получает вечный accepted или запускается из старого таймера.
Sources (проверены в предшествующем исследовании этой задачи):
- https://developer.apple.com/design/human-interface-guidelines/privacy
- https://support.apple.com/en-ge/guide/mac-help/mchld6aa7d23/mac
- https://docs.granola.ai/help-center/getting-started/setting-up-granola-for-the-first-time
- https://screen.studio/guide/setting-up-permissions
Audio-only permission из новой macOS не доказывает совместимость текущего ScreenCaptureKit фильтра; миграция API вне scope. Не утверждать, что GRAF не получает screen frames: текущий pipeline отбрасывает их, поэтому copy «не сохраняет видео экрана».
