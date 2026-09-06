# F244 — проверка реализации

Дата: 2026-09-06. Lane: high-risk-product. База F240:
`739d2e19cca9d45ab677b0c1012207a20ac09c56`, включена fast-forward до реализации.
Собственный код F244: рабочая копия, implementation SHA будет связан с PR и
проверкой GitHub после коммита, без самоссылочного SHA внутри этого файла.

## Процесс и границы

Requirements 16/16 и UX 6/6 одобрены ранее по отдельному поручению пользователя;
при реализации markers не изменялись. Tasks содержит 9 зависимых задач по US1–US3.
Analyze после исправления ссылки contracts/ui.md: CRITICAL 0, HIGH 0, MEDIUM 0;
FR-001/FR-002/SC-001 → T003, FR-003/SC-002 → T004/T005,
FR-004/SC-003 → T006/T007, FR-005/FR-006/SC-004 → T001/T002/T008/T009.
Исполнение US2/US3 не зависит от завершения отдельной численной приёмки палитры;
полная F244 остаётся зависимой до T003. Issue canon ensure/validate выполнены,
все задачи получили GitHub ownership до изменения продукта.

## Изменения

- Native dialog получает aria-labelledby единственного видимого заголовка.
- Окно прокручивается в пределах динамической высоты viewport; фокус прокручивает
  существующий контрол, для скрытого file input — видимую dropzone. Scroll padding
  и margin сохраняют место для индикатора фокуса. При повторном открытии scrollTop
  сбрасывается; Escape вызывает существующий closeDialog с возвратом фокуса.
- У trapModalFocus один необязательный cycleAll, включённый только у загрузки.
  Это сохраняет полный порядок Tab в WebKit, где платформенная настройка Tab
  пропускает кнопки; остальные 7 callers используют прежнюю семантику wrap.
- На ≤640 встроенный кабинет сохраняет grid64+main, раскрытая панель занимает
  свою прежнюю ширину поверх зарезервированной rail. Переход фокуса в main
  временно скрывает панель, без записи sessionStorage. Широкие пороги981/1121
  и явные toggle/Escape сохраняются. Текущий main запрашивается заново после
  замены страницы восстановления; нижние действия узкой панели прокручиваются.
- Standalone ≤980 сохраняет мобильную верхнюю навигацию F240, а не возвращает
  sidebar. Main там шире установленного минимума viewport−64. Доступность профиля
  этой мобильной навигации принадлежит совместной доработке F243, не дублируется.

## Проверки

Регрессии до исправления: **2 FAIL**, имя и narrow focus. После исправления
**198 PASS**: static assets contract 74 + shell/theme124. Node runtime проверяет
настоящие setRailPinned/initCabinetRail, новый main после замены и приоритет
модального окна. Отрицательная версия с удержанием старого main падает; исправленная
проходит. Общий modal helper и все его callers просмотрены перед изменением.

```sh
PYTHONPATH=apps/server/src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 apps/server/.venv/bin/python -m pytest --noconftest -p no:cacheprovider -p pytest_asyncio.plugin apps/server/tests/contract/test_cabinet_static_assets_contract.py apps/server/tests/unit/test_cabinet_web_shell.py apps/server/tests/contract/test_cabinet_theme_contract.py -q
PYTHONPATH=apps/server/src apps/server/.venv/bin/python specs/058-web-cabinet-htmx-shell/evidence/cabinet_runtime_check.py
bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_cabinet_manual_upload.py
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
apps/server/.venv/bin/ruff check apps/server/tests/contract/test_cabinet_static_assets_contract.py specs/244-cabinet-accessibility-fixes/evidence/browser_harness.py
python3 scripts/check_spec_kit_governance.py
python3 scripts/validate-changelog-fragments.py
git diff --check
```

Runtime fixture **13/13 PASS**, 10 production-rendered surfaces. Изолированный
PostgreSQL: **9 PASS**, 17.50s; временный контейнер удалён. CSRF/session/retry,
отклонение файла и embedded server paths сохранены. Эти тесты не меняли общую
БД или production. Прежние предупреждения pytest/Starlette не ошибки.
Ruff, node syntax, governance/frozen bootstrap, changelog и whitespace PASS.
Локальный repository-wide fast не запускался: GitHub выполняет authoritative PR
fast. Full CI, release-full, production, установленный WKWebView, VoiceOver,
публичная сборка/подпись не запускались этим исполнителем; ими владеет оператор.

## Браузер

Для отдельного loopback стенда с настоящими renderer/assets:

```sh
# из apps/server
PYTHONPATH=src:../../specs/244-cabinet-accessibility-fixes/evidence .venv/bin/python -m uvicorn browser_harness:app --host 127.0.0.1 --port 56645 --no-access-log
# из корня; NODE_PATH указывает на существующий установленный Playwright
node specs/244-cabinet-accessibility-fixes/evidence/browser-checks.cjs
```

`F244_BASE_URL` может указать другой loopback порт. `F244_WEBKIT_EXECUTABLE`
задаёт путь существующего pw_run.sh; использован установленный WebKit2336,
не отсутствующий default build. Chrome — установленный Google Chrome.

Runner проверяет обе поверхности × light/dark ×390×320/640×400 × четыре состояния:
без файла, корректный WAV с длинным именем, нечитаемый WAV и истёкшую сессию.
Проверяются настоящее AX-имя, геометрия после каждого Tab/Shift+Tab включая wrap,
колесо, Escape/кнопка, возврат фокуса и повторное открытие. Файл создаётся в памяти;
POST upload заблокирован runner. Не объявляем synthetic redirect проверкой auth.

Дополнительно resize1440→640→320→641→980→981→1120→1121→1440, reload,
проверка main≥viewport−64 и elementFromPoint сфокусированного поиска,
сохранение предпочтения при auto/resize и его изменение при toggle/Escape,
приоритет открытого dialog и достижимость нижнего профиля на короткой rail.
Результат: Chrome **639 PASS**, WebKit **639 PASS**. Необработанных page errors нет.
Первый runner неверно использовал force-click через раскрытую панель; это исправлено
на реальный focus→click и подтверждение открытого dialog, не продуктовая ошибка.
WebKit затем выявил два реальных пробела: Tab пропускал кнопки, Escape не возвращал
фокус при mouse-click trigger. Оба исправлены и повторная матрица прошла.
Синтетический screenshot390×320 просмотрен: заголовок, кнопка закрытия и dropzone
видны; нижняя часть достигается настоящей прокруткой.

## Review и convergence

Независимое correctness/Ponytail review оператора выявило P2: cached main после
replaceWith. Исправлено динамическим querySelector, отрицательный контроль и
положительная regression есть. Ненужные форматные изменения старых тестов убраны.
Подтверждение финального microdiff и exact-SHA GitHub записывается в PR comments.

Собственная реализация FR-003/FR-004/FR-005 проверена; FR-006 соблюдён.
FR-001/FR-002/SC-001 ещё требуют совместного численного контраста и динамической
смены темы с F243. Отдельный F244 не объявляется завершением всего аудита.
Converge: tasks_appended, не полная приёмка: T010 сохраняет эту HIGH-зависимость
и включает окончательную сверку соседних shared JS/CSS. T003 остаётся открытой.
T009 отмечается выполненной после публикации и exact-SHA GitHub gate; завершающая
связка хранится в PR, а не в самоссылочном коммите. Merge/deploy не выполнялись.

## Совместная приёмка общего выпуска — 2026-09-06

Lane: high-risk-product; последующий выпуск — Release / deploy. Исходные
частичные результаты выше сохранены как история. Эта проверка относится к
объединённым F238/F240/F242/F243/F244, integration source
`50defae4301cc3fa6388862c5234ca3a2b6b11ee`; финальные SHA отдельных PR и
обязательный governance-fast связываются в их описаниях после rebase.

Проверены production renderers/assets на синтетическом loopback стенде:

- 1620 сочетаний 27 состояний × 6 тем × 2 поверхности × 5 ширин
  320/390/768/1024/1440: HTTP 200, заголовок, отсутствие горизонтального
  выхода страницы. Список ready/empty/filtered, detail ready/processing/partial/
  failed/unavailable, настройки, тариф, shared ready/empty/summary/blocked,
  вход/код/регистрация/ошибка/успех. Календарь покрыт отдельным runner F243.
- По 438 Chrome/WebKit: подсказки, profile submenu, zoom200%, короткие окна,
  Escape/hover/no-JS, warning border. По 42: один профильный DOM, смена ширины,
  темы, формы и возврат фокуса. По 10: кнопки плеера не перекрываются.
- Численный контраст видимого текста и placeholder: Chrome3042 и WebKit3048,
  нарушений0. Шесть сочетаний явной/системной темы, список, поиск, detail,
  тариф, профиль и upload. Порог4.5:1 для обычного текста,3:1 для крупного.
- По 639 Chrome/WebKit: upload accessible name, файл/ошибка/нет сессии,
  Tab/Shift+Tab, scroll, Escape/reopen; narrow rail, сохранение предпочтения,
  фокус в заменённом main, hit-test поиска и нижние действия панели.
- По 63 Chrome/WebKit: auth/referral active/unavailable/invalid, ширины и темы,
  неперекрывающийся legal footer и динамический light→dark→light без reload.
  Явная тема остаётся выбранной, system следует ОС. Снимок регистрации390
  проверен после завершения анимации: поле и кнопка видны, legal ниже формы.

Найдены и устранены четыре интеграционных дефекта: потеря мобильного профиля,
перекрытие «Спикеры» и перемотки, отрицательный отступ legal footer и два
устаревших тестовых ожидания после удаления мёртвых компонентов F243.
Проверки не ослаблены: billing тест теперь рендерит обе реальные ссылки,
theme проверяет используемый selector. Theme-only POST дополнительно проверен
через настоящую сессию и свежую DB session: locale/timezone сохраняются.

Нативная проверка: сборка GRAF Dev PASS; реальный WKWebView на loopback,
ручные Record/Stop доступны. Настройки открываются через профиль; NSAlert
для выхода с других устройств отменяется Return и возвращает фокус.
После включения F244 повторно проверены доступное имя «Загрузить файл»,
Tab по контролам, Escape и возврат на «Загрузить запись» в собранном приложении.
24 focused XCTest (WKWebView/confirmation/routes/zoom) ранее PASS; добавленный
F238 имеет собственные17 XCTest и exact-head GitHub evidence. Проигрывание
синтетического WAV не считается доказательством Range или capture.

Correctness/Ponytail review: общий focus helper и все8 callers просмотрены;
cycleAll включён только для upload, cancel использует существующее закрытие.
Динамический main сохраняет recovery replaceWith. F242 trial_confirmation
сохранён при удалении старых macros F243. Mobile profile переносит существующий
DOM, не создаёт дубли форм. Новых зависимостей и производственных маршрутов нет.

Границы: это применимая матрица Spec Kit, не сертификат WCAG. VoiceOver в этой
среде не запустился; реальные имена/landmarks/focus проверены через macOS AX.
Синтетические страницы не доказывают успешные изменения production данных;
эти операции проверяются DB integration suites. Full CI, notarization и
production smoke выполняются отдельно для окончательного release candidate.
Review-owned checklist markers не менялись.

T003/T010 закрыты совместной приёмкой; converge: converged по реализации.
396 DB-backed tests PASS. T009 ждёт собственного exact-head GitHub gate после
переноса base PR на master. Это условие не обходится совместными тестами.
