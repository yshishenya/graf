# Независимая проверка T026/T027

Дата: 2026-09-09. Проверяющий: основной агент F257, не автор реализации F6788.
База diff: `533a25b65946ad76cb3f82687e2eff15a5b3362e`; проверено незакоммиченное состояние по хешам ниже.

**Вердикт: замечаний P0/P1/P2 к рассмотренным изменениям нет.** Это проверка кода и адресных тестов, не приёмка установленного приложения и не разрешение merge/release.

T026 устраняет обе причины цикла: `transcript_only/not_requested` больше не считается незавершённой генерацией, а готовая расшифровка с продолжающейся генерацией не вызывает новое полное обновление после каждого ответа. Первое появление расшифровки всё ещё вызывает загрузку полноценной строки; серверная отметка `data-processing-transcript-visible` прерывает повтор. Завершение итогов обновляет строку и выводит её из опроса. Проверки принадлежности строки списку, meeting_id и поколения запроса остаются перед изменением DOM. Структурный тест теперь моделирует `processed` как готовые итоги, сохраняя своё исходное назначение; новый исполняемый тест отдельно возвращает строку через сброс/afterSwap и фиксированные часы.

T027 удаляет отдельный путь сборки/запуска и передаёт все аргументы существующему отказу `run-local-app.sh`. Он не вызывает запись, установку, завершение приложения или системные изменения. Удалённый Swift invariant проверял только строки удалённого поведения; вместо него добавлена исполняемая проверка запрещённых вызовов. Проверка afinfo принимает наблюдённые пробелы и обе формы AAC, сохраняя начало строки, mono, 48 kHz и границу имени кодека; отрицательные случаи не ослаблены.

Ponytail: повторно используются существующие проекции, generation fence, 15-секундное ограничение и отказ запуска. Новых зависимостей, таймеров, маршрутов, классов или альтернативных механизмов нет.

Самостоятельно выполнен один bounded набор:

```text
PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/test_meeting_progress_ui.py::test_list_summary_poll_does_not_loop_through_authoritative_swaps tests/unit/test_cabinet_web_shell.py::test_list_polls_only_requested_summary_work tests/contract/test_cabinet_static_assets_contract.py::test_processing_list_projection_only_polls_active_rows_and_refreshes_terminal_once
```

Результат: **3 PASS, 0.17с**, два прежних предупреждения зависимостей. Внутри сценария опроса проверены24 сочетания pending/первой расшифровки/terminal с реальным сбросом состояния и повторной инициализацией. Прочитаны также governance trap test, afinfo self-test и соответствующий diff ContractValidation; их самостоятельный повтор этим проходом не заявляется. Авторские173PASS/1SKIP и нативная запись — отдельные доказательства.

UI, стенд, задачи, контрольные списки, PR и продуктовые файлы проверяющий не менял. Записан только этот отчёт.

## SHA-256 проверенных исполняемых файлов

| Файл | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/cabinet/rendering.py` | `77881a61ff0c9d84bb1f61e95c77825e5d5a580dd8871806ad5ee83ccee6734a` |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` | `ef7e871460dc098f09673b14c559583bc7eb9a3395a2186dbc757d0d55e143d2` |
| `apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh` | `5517d2bbab0019b99217881e401dc81f43f5828834f6e6924d15699a6bac3361` |
| `apps/macos/Scripts/validate-system-audio-capture-pivot.sh` | `45bbd0e1845a8475952d3b4da5bc772eae65c4d136dab6ad524a5c6e65ea2d9e` |
| `apps/macos/Shared/Tools/ContractValidation/ContractValidationV5.swift` | `21f65c909072fd477ce419baf5dd1281ca5ea56027ff1e77e80b7c0906f120c9` |
