# Data Model — F285

Нет новых хранимых данных, API, событий или миграций. Временное selectedRecordingSessionID сохраняется в DesktopControlModel; focusedRecordingSessionID становится только целью assistive focus. Переход: явный navigation request → раскрытие/scroll → accessibility target. Start/Stop не создают нового navigation request. Поля/формы и их значения остаются существующими.
