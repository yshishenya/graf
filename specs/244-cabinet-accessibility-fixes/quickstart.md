# Проверка Feature 244

Статус: план проверки; реализация и результаты после исправлений пока отсутствуют.

## Подготовка

Работать из корня текущего worktree с установленными зависимостями сервера, Node и Playwright CLI. Использовать только синтетические профиль, встречи и файлы. Реальные письма, оплаты, загрузки и внешние API не выполнять.

## Проверки кода

```sh
PYTHONPATH=apps/server/src python -m pytest apps/server/tests/contract/test_cabinet_static_assets_contract.py apps/server/tests/unit/test_cabinet_web_shell.py apps/server/tests/integration/test_cabinet_manual_upload.py -q
PYTHONPATH=apps/server/src python specs/058-web-cabinet-htmx-shell/evidence/cabinet_runtime_check.py
git diff --check
```

Перед исправлениями регрессионная проверка каждого изменяемого контракта должна воспроизводить дефект. После исправлений ожидается PASS. Отсутствующая тестовая зависимость или недоступный browser engine — ограничение, не PASS.

## Проверка браузером

Использовать локальный HTTP fixture с настоящими render functions и CSS/JS текущего worktree. Он не доказывает работу authenticated backend или установленного WKWebView. Воспроизводимые runner/fixture и итоговое metadata-only evidence сохранять в каталоге фичи при реализации.

1. Список, настройки и detail × standalone/embedded × ширины320/390/768/1024/1440: отсутствие неожиданного обрезания, доступность поиска и кнопок.
2. На согласованной совместной ревизии F240/F244: light/dark/system × system light/dark. Измерить текст/фон поиска, placeholder, фильтров/сортировки, строк normal/hover/selected/focus, empty/loading/error, upload, sidebar/profile, summary controls и диалогов. Normal text ≥4.5:1; значимые контроли/иконки/фокус ≥3:1; учитывать opacity/color-mix и не округлять значения для PASS. Сменить system preference без reload при открытом диалоге и сверить с явной соответствующей темой. Снимок сам по себе не доказывает численный контраст.
3. Upload на390×320 и640×400: проверить непустое имя, совпадение aria-labelledby с единственным h2, прокрутку колесом и полный цикл Tab/Shift+Tab от первого до последнего контрола и обратно. Повторить без файла, с корректным синтетическим WAV с длинным именем, с нечитаемым файлом и для недоступной загрузки. В каждом шаге сверить границы видимого контрола/индикатора фокуса с внутренней видимой областью dialog, а не только `closest('dialog')`. Для скрытого file input проверять label/dropzone. После прокрутки закрыть Escape/кнопкой, проверить возврат фокуса, повторно открыть и проверить начальный фокус. Tooltip архива аудио читаем, не обрезан и доступен клавиатурой. Не нажимать submit на реальном сервере.
4. Rail: fresh page, manual expanded/collapsed, resize1440→640→320→641→1440 и reload; отдельно980/981 и1120/1121. На320 main≥256px; toggle/Escape/aria-expanded согласованы. После Tab из sidebar в поиск и при сужении окна с уже сфокусированным поиском панель не закрывает контрол: сверить geometry и `elementFromPoint`, не ограничиваться `isVisible`. Автоматическое скрытие не меняет sessionStorage; явные toggle/Escape меняют по прежнему контракту. Проверить Tab/Shift+Tab, нижние действия sidebar при короткой высоте, Escape сначала для открытых dialog/profile menu. Режим без JavaScript не изменяется и не объявляется исправленным этим PR.
5. Проверить фильтр клавиатурой, profile menu, tabs, loading announcement и offline→retry. Ошибки неполной эмуляции backend не считать продуктовыми находками.

## Перед PR

Проверка требований рецензентом, tasks, analyze, issue ownership всех tasks, focused проверки, browser evidence, Ponytail review и converge. После разрешения на commit: точный SHA в русском PR и успешный GitHub `governance-fast` на этом SHA. Пока окончательный F240 не включён в проверенную совместную ревизию, FR-001/FR-002 остаются незакрытой зависимостью; использовать `Refs`, не закрывающий keyword для частичного объёма. Full CI, merge, release и deploy — не входят.

## Результат проверки требований

См. [evidence/checklist-review.md](evidence/checklist-review.md). Отрицательные браузерные пробы выполнялись с временными стилями/DOM, без изменения продуктовых файлов. Одобрение checklist не заменяет перечисленные проверки реализации.

## Реализация 2026-09-06

Воспроизводимые команды с изолированным PostgreSQL и browser runner, результаты и оставшаяся общая приёмка — [evidence/implementation.md](evidence/implementation.md). Верхняя историческая команда pytest требует DB fixtures; фактически выполнен поддерживаемый `run_local_postgres_tests.sh --focused`, не общая БД.
