# T042 — проверка размещения окна «Поделиться»

2026-11-17. Ветка `codex/f292-final-native-acceptance`, база `72079434d3fa151725c16ed6044da175c8955e51`. Lane: active Spec Kit slice / high-risk UX. Этот отчёт подтверждает только локальную реализацию и браузерные проверки; T042 и #8124 остаются открытыми до независимого обзора, чистого Dev и нового выпуска.

До изменения кода прочитаны требования FR-039/040, план/quickstart/tasks T042, анализ C/H0 и независимые checklist `native-zoom.md` (3 отмечены,0 открыто) и `review-t042-requirements.md`. Каноническая задача #8124 создана основным оператором до реализации. Новая фича и отдельная панель не создавались.

## Область изменения

В существующем `summary-sharing.js:place()` обычная нижняя граница main сохранена. Если доступная высота меньше измеренных закреплённых заголовка/нижней строки, строки управления не менее44CSSpx, внутренних отступов/промежутков и внешних отступов12px, используется нижняя граница viewport. Существующий ResizeObserver дополнительно наблюдает main и измеряемые элементы: изменение высоты дорожек без resize окна пересчитывает режим. CSS, шаблоны, API, права, проигрыватель и зависимости не менялись.

Существующий `sharing-owner.test.cjs` дополнен геометрией400×300 с проигрывателем260px (main40px), обе темы,3/15 приглашений. Проверяются пригодная область между закреплёнными строками, фокус и указатель через elementFromPoint для первого поля, первого/последнего действия, срока, копирования и закрытия, отсутствие горизонтальной/вложенной прокрутки и новых мутаций. При уменьшении высоты проигрывателя без resize ожидается прежняя граница main, при увеличении — viewport; затем обычный размер восстанавливает размещение над проигрывателем. Снимок синтетического проигрывателя проверяет позицию, скорость, паузу, раскрытые дорожки и выбор спикера. Это не заменяет настоящий player/pageZoom в GRAF Dev.

## RED → GREEN

До производственного изменения новая регрессия упала на прежнем place(): `A high player must leave at least one usable control row between pinned edges`. Chromium:1failed,3deselected,14.34s. Приватный журнал оператора: `/private/tmp/graf-f292-t042-red.log`.

После изменения полный существующий контракт `apps/server/tests/contract/test_meeting_sharing_parity_ui.py`:

| Движок | Результат | Что включает |
|---|---|---|
| Chromium |4passed,35.79s|owner, public, auth-return, embedded reader|
| WebKit |4passed,40.44s|тот же контракт, обе темы в owner|

Окружение: существующий Python3.13 и Playwright из основной рабочей копии, без установки зависимостей; проверяемые исходники и тесты — из этой ветки. Команда для каждого движка:

```sh
GRAF_NODE_MODULES=/Users/yshishenya/Documents/crisp/apps/server/tests/browser/node_modules \
GRAF_BROWSER=chromium PYTHONPATH="$PWD/apps/server/src" \
/Users/yshishenya/Documents/crisp/apps/server/.venv/bin/python -m pytest \
  apps/server/tests/contract/test_meeting_sharing_parity_ui.py -q
```

Для WebKit задано `GRAF_BROWSER=webkit`. Журналы оператора: `/private/tmp/graf-f292-t042-chromium-full.log` и `/private/tmp/graf-f292-t042-webkit-full.log`. Единственное предупреждение pytest — уже импортированный plugin `tests.fixtures.postgres_test_database`; ошибок браузера/ResizeObserver нет. `node --check` обоих JS и `git diff --check` прошли.

После добавления явной проверки свойства выбора спикера (`checked`, а не только HTML) повторён только затронутый owner сценарий: Chromium1passed/3deselected25.56s, WebKit1passed/3deselected26.56s. Команда та же с `-k sharing-owner`; журналы `/private/tmp/graf-f292-t042-{chromium,webkit}-owner-final.log`. Производственный JS с полного GREEN не менялся.

В ходе подготовки новой проверки исправлены её собственные fixture ошибки: после reload заново задаётся подставной clipboard; копирование без мутаций проверяется при закрытой аудитории, а не в оставшемся от предыдущего сценария искусственном отсутствующем public-link состоянии. Эти промежуточные отказы не объявлены дефектами продукта и не заменяют приведённый предметный RED.

## Оставшиеся ворота

Нужны независимый обзор кода, точный чистый SHA, штатные Dev build/promote/status/smoke, настоящие800×600/pageZoom200%/дорожки/3/15/обе темы и клавиатура. Затем свежие exact-SHA/base PR checks, согласованный frozen candidate, один release-full, опубликованный runtime и установленное приложение. В этой локальной реализации коммиты, GitHub, приложение, стенд и выпуск не менялись; реальные встречи и адресаты не использовались.

## Итог независимого обзора перед коммитом

`review-t042-code.md`: PASS, CRITICAL0/HIGH0/MEDIUM0; независимо повторён
owner WebKit1passed/3deselected26.47s. Контрольные суммы JS в отчёте совпадают
с текущими файлами. Локальная governance-проверка обнаружила только ранее
известное расхождение установленного specify1.2.6 и lock1.0.7; не считается
PASS и не заменяет обязательный governance-fast точного PR SHA в GitHub.
