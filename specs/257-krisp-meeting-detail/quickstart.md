# Validation: F257

## До изменения кода

Прочитать spec/plan/research/data-model/contracts/ui.md, reviewer-owned checklists; analyze должен иметь CRITICAL 0 / HIGH 0. Связать задачи с GitHub. Референс изучать только через Computer Use; приватное содержание не писать в evidence.

## Focused checks

Из корня репозитория:

```sh
cd apps/server
PYTHONPATH=src uv run pytest -q tests/contract/test_meeting_detail_reference_contract.py tests/unit/test_meeting_detail_copy_runtime.py tests/unit/test_meeting_source_viewport_runtime.py tests/contract/test_summary_template_ui_contract.py tests/contract/test_cabinet_playback_contract.py tests/contract/test_transcript_export_contract.py tests/contract/test_meeting_sharing_contract.py tests/unit/test_meeting_protocol_rendering.py tests/integration/test_cabinet_meeting_detail.py
uv run ruff check src/twobrain_rec_server/cabinet/rendering.py tests/contract/test_meeting_detail_reference_contract.py tests/unit/test_meeting_detail_copy_runtime.py tests/unit/test_meeting_source_viewport_runtime.py
```

Если тестам нужен PostgreSQL, использовать существующий `apps/server/scripts/run_local_postgres_tests.sh --focused <пути> -q`, не production и не общий Dev. Синтетические данные; не имитировать HTTP 200 вместо настоящего действия.

## Browser / GRAF Dev

1. Перед сборкой прочитать docs/agent-guidance/local-development.md; status --json общего dev-harness.
2. До одобрения коммита выполнить доступные тесты. Чистый точный SHA — обязательное условие build/promote единственного /Applications/GRAF Dev.app; не обходить dirty check и не создавать копию.
3. На синтетической встрече проверить web/embedded: шапка/колонка, обе вкладки, формат и каталог, текущий маркер, ожидание/ошибка, источник/возврат, название/отмена/конфликт, копирование/отказ, экспорт, Share/more/details/отмена удаления.
4. Повторить 390/768/1024/1440, 200%, dark/light, keyboard/focus; отдельно длинное название, пустое/processing/stale/access-revoked. Сохранять только агрегаты/метаданные.
5. Для копирования: переключение вкладки во время запроса не меняет scope; отключённая/replaced форма не записывает поздний результат в clipboard. Ошибка остаётся видимой; повтор доступен.
6. Без JavaScript проверить обе разрешённые панели/якоря и разрешённые скачивания артефактов; для owner/shared, disabled и replacement состояния не создавать обходов. Выбор/генерация формата требуют JavaScript; это должно быть объяснено.
7. Для источника проверять первую строку ниже закреплённой шапки и весь текст выше плеера, если текст помещается в доступную область. Если текст длиннее области, переход показывает его начало, остальное доступно прокруткой; одного пересечения блока реплики с viewport недостаточно. Повторить ссылку итогов, прямую ссылку на источник и переход из плеера. Сопоставить с референсом при нормализованном масштабе; задокументировать отклонения, проверить совместимость с плеером F256, не менять его самостоятельно.
   Прямую ссылку `#graf-source` открывать полной навигацией, проверяя начальный и поздний кадр в Chromium/WebKit. В установленном GRAF Dev такой пользовательский вход отсутствует (N/A); доступную кнопку источника проверять отдельно в WKWebView.
8. На синтетической встрече в web/embedded изменить существующую подпись голоса, проверить её после перезагрузки, восстановить исходную подпись и повторно проверить сохранение. Это проверка текущей функции GRAF; новая модель контактов и перенос отдельной реплики не добавляются.

## Closeout

`git diff --check`; ponytail review; converge, task/issue evidence. `infra/scripts/ci-local.sh --fast` требует чистый checkout: выполнить после одобренного коммита, остановка на dirty_worktree не означает PASS. Current-SHA governance-fast при PR. Full CI/release-full и production deployment — отдельный выпуск; без них не заявлять релиз. При блокировке Dev/коммита явно оставить соответствующие задачи открытыми.


## Дополнение выбора формата — 2026-09-09

1. Выполнить `tests/contract/test_summary_template_ui_contract.py`, `tests/contract/test_meeting_detail_reference_contract.py`, `tests/contract/test_cabinet_static_assets_contract.py` и `tests/unit/test_summary_format_picker_browser.py` с `tests/browser/summary-format-picker.test.cjs`. Проверить синтаксис JS и `git diff --check`.
2. Synthetic Chromium/WebKit: ≤4 быстрых option; список All в той же панели без dialog/backdrop, доступность последнего встроенного/личного формата; Back и управление личными форматами. Отдельно длинные русские имена и пустая группа личных форматов.
3. Клавиатура: initial/current focus, стрелки/Home/End только видимых option, Enter/Space, Tab/Shift+Tab до служебных действий и наружу, Escape с возвратом, внешний клик без кражи фокуса. Назначение одинаково доступно по hover/focus. Переключить вкладку при открытой панели.
4. Доказать отсутствие генерации при открытии/All/Back/hover/focus; один существующий выбор при активации другого формата. Проверить disabled/busy/current, ошибку и сохранение прежнего результата.
5. 390/768/1024/1440 CSS px, 200%, light/dark: нет горизонтального переполнения, полные названия/служебные действия достижимы, длинный список прокручивается и фокус виден. Записать только метаданные в `validation/format-picker.md`.
6. После одобрения коммита и штатного dev-harness проверить точный SHA в единственном GRAF Dev через Computer Use. До этого native acceptance остаётся открыта. Затем converge/review и current-SHA governance-fast для PR; release-full и выпуск отдельно. Исторические PASS T001–T011 не подтверждают дополнение.
