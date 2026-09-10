# Задачи F261

Источник требований: [spec.md](spec.md). Проверки: [quickstart.md](quickstart.md).
Ниже задачи локальной реализации; публикация релиза не входит в их завершение.
Обе задачи: [GitHub #6874](https://github.com/yshishenya/graf/issues/6874).

- [X] T001 [US1] Исключить источники из интерфейсного запроса копирования и экспорта в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` и убрать настройку из `apps/server/src/twobrain_rec_server/cabinet/rendering.py`.
- [X] T002 [US1] Проверить запрос, обе версии формы, экспорт итогов и комбинированного документа, сохранение источников внутри встречи в `apps/server/tests/unit/test_content_export_request_runtime.py`, `apps/server/tests/unit/test_cabinet_web_shell.py`, `apps/server/tests/unit/test_meeting_protocol_rendering.py` и существующих тестах расшифровки/переходов.

Результат повторных локальных проверок после синхронизации с master:
35 passed; Node syntax, Ruff и `git diff --check` passed.
Обе задачи связываются с одним issue F261; закрытие — после слияния PR и
проверки актуального GitHub evidence, не по одному локальному результату.
