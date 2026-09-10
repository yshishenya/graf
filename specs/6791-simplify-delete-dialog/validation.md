# Validation — 2026-09-09

## Scope and source

Lane: high-risk-feature / deletion UX, полный Spec Kit. Ветка codex/6791-simplify-delete-dialog, база 0ad486df265a2555be0284ce69119d9d68b10a4c + незакоммиченный diff. Это локальное evidence, не exact-SHA evidence готового релиза.

## Requirements and analysis

Specify/clarify/plan/checklist/tasks/analyze выполнены. Критических уточнений нет. Независимый reviewer deletion_review: UX 4/4, security 3/3; отметки принадлежат reviewer.

| Требования | Задачи | Покрытие |
|---|---|---|
| FR-001, FR-002, FR-003, FR-006 | T001, T002, T003 | Текст, количество абзацев/кнопок, отсутствие технического списка и ссылки, прежний отчёт |
| FR-004, FR-005 | T001, T002, T003, T004 | Форма, доступность, оба кабинета; ручная приёмка перед выпуском |
| SC-001–003 | T001, T003, T004 | Целевые проверки и измеримый состав окна |

Analyze: 6/6 FR и 3/3 SC покрыты, CRITICAL 0 / HIGH 0 / MEDIUM 0, противоречий и непривязанных задач нет.

## Local checks

- До реализации новый HTML-тест: 2 ожидаемых FAIL на старом тексте, 2 PASS на недоступном удалении.
- После реализации: 119 PASS в test_cabinet_web_shell.py, test_recording_governance_ui_contract.py, test_recording_workflow_accessibility.py, test_deletion_report_view_models.py, test_deletion_no_secret_leakage.py.
- Ruff трёх изменённых Python файлов: PASS. git diff --check: PASS.
- Первоначальное использование общей .venv обнаружило отсутствие recurring_ical_events; штатный uv run --extra dev создал окружение этого worktree, lockfile не менялся.
- Прямой запуск интеграционных проверок: 14 setup errors из-за отсутствия TWOBRAIN_DATABASE_URL; запущен правильный run_local_postgres_tests.sh --focused с изолированной базой. Окончательный результат ниже.

## Tracker and hooks

T001–T004 принадлежат открытому #6853: https://github.com/yshishenya/graf/issues/6853. Исходный reservation issue обновлён; новых дублей нет. Scoped validate_issue для #6853: PASS.
Общий speckit.github-issue-canon.validate: FAIL только на чужом #6852 (missing area label for governance; missing Spec tasks: T000). Чужая задача не изменялась; общий результат не объявляется успешным. Требуемые executable tasks текущей фичи имеют проверенного владельца.
Обязательные git.feature и github-issue-canon.ensure выполнены; validate выполнен с указанным результатом. Необязательные agent-context.update пропущены: корневые инструкции не требуют изменений. Commit hooks отключены конфигурацией.

## Release boundaries

Коммит, push, PR, governance-fast, release-full, deploy и ручная приёмка /Applications/GRAF Dev.app не выполнялись. Полный CI не запускался. T004 и issue остаются открытыми до соответствующей авторизации и evidence.

## Final local result and convergence

- Штатный изолированный PostgreSQL: 14 PASS, 63.13s; run_local_postgres_tests.sh сообщил focused status=pass и isolated_container_removed. POST, redirect и CSRF проверены. Итого 133 PASS.
- Owner/agent code review: diff ограничен текстом, ссылкой и её вычислением. Права, hidden поля, маршруты, обработчики, стили и отчёт не изменены.
- Converge: FR-001–006, SC-001–003, четыре acceptance scenarios и решения плана сверены с кодом и проверками. Новых пробелов реализации нет; tasks.md не дополнен дублирующими задачами. Ручная приёмка/точный SHA/релиз уже учтены открытой T004.
- Локальная реализация T001–T003 готова; выпуск и общий tracker closeout не завершены.

## Уточнение и реализация — 2026-09-09

По прямому указанию пользователя из подтверждения удалена оговорка о скачанных/отправленных копиях. Согласованный абзац содержит 9 слов; прежние записи о 12 словах описывали неверный подсчёт. Теперь один абзац и две кнопки. Spec/plan/research, тесты, changelog и issue #6853 согласованы с уточнением. Повторный независимый review требований: 7/7 PASS.

До удаления строки: новый тест дал 2 ожидаемых FAIL и 2 PASS. После правки: 111 PASS (test_cabinet_web_shell, test_recording_governance_ui_contract, test_recording_workflow_accessibility), Ruff и git diff --check PASS. Интеграционные проверки механизма удаления повторно не запускались: после предыдущих 14 PASS изменена только строка HTML. Полный CI и установленное приложение не проверялись.

Analyze/converge: FR-001–006 остаются покрыты T001–T003; новых пробелов кода нет. T004 остаётся открытой. Коммит и публикация не выполнялись.

## Подготовка PR по поручению пользователя — 2026-09-09

Пользователь разрешил довести работу до готового к релизу PR; необходимые коммит и push входят в эту подготовку. Production и merge отдельно от создания PR. Свежий origin/master совпадает с базой 0ad486df265a2555be0284ce69119d9d68b10a4c. Финальный текст повторно прошёл весь целевой набор: 133 PASS за 48.80s, штатная изолированная PostgreSQL удалена. Ruff и diff --check PASS.

Changelog перенесён в требуемый changes/unreleased/F6791.yaml; validator PASS. Spec Kit bootstrap integrity + GRAF invariants: PASS с CLI 1.0.1 на ref 9118ed15a0ba65053469a94c560ea5d233f75884. Локальная CLI установлена в игнорируемое окружение; глобальная CLI, bootstrap lock и исходники инструментов не менялись. Удалён только сгенерированный этим запуском Python bytecode из дерева расширения.

Owner/agent review: удаляются лишние статические абзацы/ссылка и её вычисление; DOM-контракт, права, форма и обработчики сохранены. Пользователь отдельно утвердил отсутствие оговорки о копиях. Legacy Impact: untouched; legacy_new=0, unowned_legacy=0, expired_exceptions=0.

Далее точный SHA, URL PR и CI, установленная приёмка фиксируются в PR/issue evidence, чтобы не подменять tested SHA последующим документальным коммитом. T004 остаётся открытой до всех её gates; release-full по политике выполняется только на post-merge frozen master, а не PR head.

## Исправление по установленной приёмке

GRAF Dev на 450ef2fbe14524efb5341f3d7d1704c1325388ab: текст, светлая/тёмная тема, Escape, отмена и возврат к меню проверены. Найден дефект FR-005: Tab после «Отмена» пропускает submit и уходит в native capture panel. Эта приёмка не объявляется PASS.

Корень: обычный переход между кнопками оставлялся системному WebKit, который может исключать кнопки из Tab-порядка. Существующий trapModalFocus уже поддерживает cycleAll; параметр включён только для окна удаления. Новых обработчиков и зависимостей нет. Регрессионная Node-проверка исполняет реальный обработчик окна и пять переходов Tab/Shift-Tab; до исправления FAIL, после PASS. node --check и diff --check PASS. Требования и lane не меняются; план/T002/quickstart согласованы. Новые SHA/CI/повторная установленная приёмка фиксируются в PR.

Независимый повторный review: code findings 0; reviewer воспроизвёл FAIL без исправления и PASS с ним. Устаревшая фраза «JS без изменений» в contracts/dialog.md согласована с планом.

После исправления фокуса повторён полный целевой набор: 133 PASS за 49.70s; изолированная PostgreSQL удалена. Node regression, синтаксис JavaScript, changelog validator, Spec Kit governance и git diff --check: PASS.

## Проверка подтверждения в установленном приложении

На 94d7a4eea0f6a58c8810fe729c5685545382a8b8 GRAF Dev прошёл 13/13 health gates. Подтверждены текст, обе темы, ширина 840 px, увеличенный масштаб, пять переходов Tab/Shift-Tab, Escape, отмена и возврат к «Ещё». При submit своей синтетической встречи показано «Функция недоступна»: DesktopCabinetRoutePolicy не разрешает /desktop/meetings/{id}/deletion-requests, хотя серверный маршрут существует. Это не PASS полного сценария.

Для FR-004/005 точечное разрешение добавляется в классификацию страницы встречи после существующих проверок origin и перед deny-by-default. DesktopCabinetNavigationRequestPolicy по-прежнему пропускает POST без пересоздания запроса. План, контракт и T002 согласованы; уточнения пользователя не нужны, цель — работающее существующее подтверждение. Новые SHA/CI/приёмка фиксируются в PR.

Native regression: до изменения 1 тест с 2 ожидаемыми FAIL (route blocked, meeting ID отсутствует); после изменения все 29 DesktopCabinetRoutePolicyTests и DesktopCabinetNavigationRequestPolicyTests PASS. Проверены внешние origin, другой порт, userinfo, лишний сегмент, неизвестное действие и отсутствие replay POST.

## Проверка фактического POST и исправление имени защитного поля

На c5a530f8448e96dfbe20ee0ed8e93a0625223bef независимая задача F257 проверила диалог/Tab и после прямого согласия владельца подтвердила удаление только созданной нами пустой F6791-встречи. Сервер вернул csrf_token_missing; БД подтвердила requests=[] и deletion_state=none. Это не PASS.

Причина: форма отправляла _csrf, а require_web_csrf ожидает CSRF_FORM_FIELD_NAME=csrf_token. Renderer теперь использует существующую константу; проверка CSRF и генерация токена не меняются. Новая интеграционная проверка загружает страницу с cookie-сессией, извлекает фактически отрисованные hidden-поля и отправляет форму без дополнительных заголовков для /meetings и /desktop/meetings. До исправления оба сценария FAIL; isolated PostgreSQL удалена. Историческая запись reviewer-owned security checklist про имя _csrf описывает прежнее поле, актуальный контракт задаёт каноническое csrf_token; гарантия защиты сохраняется и теперь проверяется реальным запросом.

После исправления имени поля: 135 PASS за 56.94s, включая оба реальных form-submit сценария; изолированная PostgreSQL удалена. Ruff четырёх Python-файлов, changelog validator, Node regression и diff --check PASS. Native-код после 29 PASS не менялся.

## Возврат после успешного удаления

На 9cf93b92eb608ccf952b477f7bd0beb6a45c560c подтверждённый пользователем POST завершил удаление пустой тестовой встречи: active_purge_complete, deleted_at установлен, один запрос owner. GRAF Dev promote/status/smoke: 13/13 PASS. После 303 сервер вернул список, но после штатного сброса истории WebView экран оставался пустым; полная установленная приёмка ещё не PASS.

Проверка размеров нового WebView до отложенного layout воспроизвела нулевой frame при ненулевом контейнере на двух размерах. Включён штатный AppKit autoresizing по ширине и высоте; эта регрессия стала PASS, весь набор route/request/zoom/reload — 32 PASS. Сброс истории после POST, запрет replay, права и сетевые запросы не меняются. Причинная связь с пустым экраном проверяется повторной установленной приёмкой на новом SHA; результат будет привязан к PR.
