# Независимое ревью требований — Feature 282

Дата: 2026-09-30 (Europe/Istanbul). Reviewer: отдельный агент `search_requirements_review`.
Область: качество требований до реализации и независимый анализ согласованности артефактов. Код, спецификация, план, задачи, governance, GitHub, commit и deploy не изменялись. Изменены только reviewer-owned checklist и этот отчёт.

## Вердикт чеклиста

**PASS: 9 checked / 0 unchecked.** Отметки подтверждают определённость требований; они не означают готовую реализацию, публикацию, индексацию, работающую атрибуцию новых входных страниц или рост посещаемости.

| Пункт | Доказательство в текущих артефактах | Решение |
| --- | --- | --- |
| CHK001 | `spec.md:12,36,39,66,78`: только три ссылки, точное сравнение после их удаления, четыре ширины; `plan.md:31,41`, `contracts/public-search-pages.md:11`; `evidence/baseline.md:8–13` содержит исходные hashes | Полнота определена |
| CHK002 | `spec.md:28–30,57,69`, `research.md:7`, URL/путь к продукту в `contracts/public-search-pages.md:5–7`; существующий `apps/server/src/twobrain_rec_server/public/templates/public/download.html:62` подтверждает macOS 14.5+ | Различены браузерная загрузка и desktop, нет обещания готовой Windows |
| CHK003 | `spec.md:25–30,64–65`, `contracts/public-search-pages.md:3–7`, T003/T005 в `tasks.md` | Три задачи и самостоятельное содержание определены; написание текста остаётся реализацией |
| CHK004 | `spec.md:54,67`, `contracts/public-search-pages.md:9`, `quickstart.md` Expected results, T002/T004/T005 | HTTP, метаданные, canonical, внутренние ссылки, sitemap и 404 определены |
| CHK005 | `spec.md:36,40,56,70,78`, `contracts/public-search-pages.md:11`, browser checks в quickstart; `.specify/memory/constitution.md:384` задаёт WCAG 2.2 AA | Размеры, клавиатура, фокус, структура и fallback определены |
| CHK006 | `spec.md:55,68`, `research.md:6`, `plan.md:41`, `quickstart.md` Expected results; `public/templates.py:120–155`, `public/analytics.py:660–746` | Используется существующий общий ответ и campaign cookie без новых типов/полей и allowlists; полноценная атрибуция новых путей не заявляется |
| CHK007 | `spec.md:29–30,65,69–70`, `plan.md:26`, существующий `public/static/public/fonts/OFL.txt:1–5`, `docs/agent-guidance/product-gates.md` UX Reference Fidelity | Правдивые ограничения AI, согласие/законность, свои активы и лицензированный шрифт определены |
| CHK008 | `spec.md:46–50,71,79–81`, `evidence/measurement-plan.md:5–25`, `evidence/baseline.md:3–6` | Подготовка, выпуск, индексирование и результат разделены; окна, источники, brand/nonbrand, unknown и малая выборка определены |
| CHK009 | `spec.md:71`, `plan.md:17,39–42`, quickstart Release and outcome, `tasks.md:27` | Откат предыдущей версией без миграции; commit/deploy требуют отдельных разрешений; чужая работа сохраняется |

## Независимый анализ spec / plan / tasks

Выполнен prerequisites `--json --require-tasks --include-tasks`; FEATURE_DIR указывает на `specs/282-organic-search-pages`. Существование `spec.md` проверено отдельным чтением: установленный скрипт не поддерживает `--require-spec`. Для анализа прочитаны все три основных артефакта, research/data-model/contracts/quickstart, чеклист, baseline/measurement-plan, constitution и применимые product-gates/spec-kit-flow. В `.specify/extensions.yml` before/after_analyze commit hooks отключены; мутации не выполнялись.

**CRITICAL 0 · HIGH 0.** Нарушений конституции и непокрытых buildable требований не найдено. Значительные изменения проходят полный Spec Kit и независимый reviewer gate; обязательные анализ, issue sync, converge, validation и последующие exact-SHA release gates не заменяются этим отчётом.

| Требование | Покрытие задачами | Проверка |
| --- | --- | --- |
| FR-001 | T003, T005 | Три фиксированных пути, доступность без auth/JS |
| FR-002 | T003, T005 | Разные самостоятельные инструкции, критерии проверки и ограничения |
| FR-003 | T001, T002, T004, T005 | Исходные hashes, точное сравнение лендинга, четыре ширины |
| FR-004 | T002, T003, T004, T005 | HTTP/meta/canonical/404, sitemap и ссылки |
| FR-005 | T002, T003, T005 | Существующие response/escaping/consent; отсутствие новых аналитических поверхностей |
| FR-006 | T003, T005 | Достоверные платформы, законность, уведомление, разрешения и видимые controls |
| FR-007 | T002, T003, T005 | Четыре ширины, focus/skip-link, доступность без JS/изображения |
| FR-008 | T001, T005 | Baseline/measurement/rollback, ограничения commit/deploy |
| SC-001 | T003, T005 | Самостоятельный ответ и существующий путь к продукту |
| SC-002 | T001, T002, T004, T005 | Сохранение исходной главной и браузерная регрессия |
| SC-003 | T001, T005 | План и статусы источников; unknown не равно нулю |

Buildable inventory: 11 требований, 5 задач, покрытие 11/11 (100%). Unmapped tasks: 0. SC-004/005 — результаты после публикации, исключены из buildable inventory; T001 определяет измерение. Числа 30 переходов / 3 активации являются рабочей гипотезой, не текущими данными.

Неблокирующее замечание **LOW P1**: T003 и Project Structure используют сокращённые `templates/public/search_guide.html` и `static/public/search-guide.css` после полного пути модуля. Их место однозначно из существующей структуры, но для точного соблюдения правила task paths лучше указать полностью `apps/server/src/twobrain_rec_server/public/templates/public/search_guide.html` и `apps/server/src/twobrain_rec_server/public/static/public/search-guide.css`. Требования или задачи проверяющий не редактировал.

## Границы доказательств и следующий шаг

Baseline прочитан как текущий артефакт автора, не как независимо повторённое live-измерение. Результат Grow My Website и публичные HTTP-проверки здесь повторно не запускались. Это не влияет на ясность требований, но будущая validation должна содержать собственные выполненные проверки и текущие результаты.

Перед T002/T003 основной агент должен подтвердить остальные analysis/issue-sync gates. После реализации нужны полная заявленная quickstart-проверка, сохранение главной, независимая проверка результата и converge. HTTP 200 и локальные тесты не доказывают поисковую индексацию или рост.
