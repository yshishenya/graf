# F255: подготовка штатного GRAF Dev

Дата: 2026-09-06. Владелец разрешил коммит реализации и продолжение проверки GRAF Dev.

## Готовый первый кандидат

- Implementation commit: `1614e6787f7b99478a61601cf30e9ba6c20c0a7e`, рабочая копия после коммита чистая.
- Команда: `infra/scripts/dev-harness.sh build --sha 1614e6787f7b99478a61601cf30e9ba6c20c0a7e --feature-id 255 --operator codex-f255 --live`.
- Результат: PASS, `adapter.mode=live`, `status=ready`, manifest `dev-1614e6787f7b`.
- Собраны сервисы и настоящий `GRAF Dev.app`; `bundle_id=pro.2brain.graf.dev`, `channel=dev`, штатная локальная подпись. Это сборка кандидата, не установка и не публичный выпуск.
- PR: https://github.com/yshishenya/graf/pull/6766, draft.

## Ограничение продвижения

Установленный Dev занят текущей аппаратной проверкой F249: manifest `dev-d36074bfd8c4`, SHA `d36074bfd8c482abf14d138ed29714560f9b5da8`. F255 не останавливала и не меняла этот стенд.

Read-only проверка текущего управляющего скрипта выявила `active Dev runtime definition differs from checkout; explicit operator cutover required`. В F249 изменён управляющий код. Для перехода нужен согласованный оператором штатный путь с проверенным восстановлением прежнего runtime. Не удалять runtime record/блокировку, не менять digest и не устанавливать приложение вручную ради обхода проверки. Очередность аппаратной проверки ожидает согласования.

## Исправления после первого CI

GitHub run `34051439091` на первом кандидате обнаружил старое ожидание `aria-disabled=true == 10` в `test_cabinet_template_sections.py`. Контракт заменён проверкой отсутствия неработающих команд; остальные проверки ссылок, CSRF и выхода сохранены. Повторный профильный pytest с этим suite: **151 PASS**.

Дополнительно найден недостаточный контраст прежнего акцентного текста профиля на светлом фоне: #8c73ff на #ffffff = **3.49:1**, на #ececec = **2.96:1**. Новый нативный профиль явно использует `.foregroundStyle(.primary)`. Swift-проверки после изменения: **170 PASS**. Реальный контраст native в двух материалах остаётся частью T016.

В браузере по computed styles для пунктов меню и профиля: light **13–15.96:1**, dark **11.05–14.61:1**, порог обычного текста 4.5:1 выполнен. Это ограниченная проверка перечисленных элементов, не всей матрицы контролов/VoiceOver.

Первый кандидат заменяется следующим коммитом с этими исправлениями. Точный финальный SHA, новая Dev-сборка и результат GitHub публикуются в PR; старый неуспешный run не считается допуском.

## Дополнительный проход

Штатный build на `c8ac11778a7d86adf638e75bf32bb2d6177d6b7e`: PASS, manifest `dev-c8ac11778a7d`, bundle `pro.2brain.graf.dev`, channel `dev`, status `ready`. Не установлен: F249 продолжает аппаратную проверку.

GitHub run `34051908491` проверил metadata, 1443 server unit tests и 21 changed contract tests, затем остановился на F401: оставшийся неиспользуемый импорт `html.escape` в `test_cabinet_web_shell.py`. Импорт удалён; это не изменение поведения приложения. Следующий SHA требует собственного CI и Dev build.

Через штатный `run_local_postgres_tests.sh --focused` выполнены шесть admin browser contracts и `test_theme_only_form_survives_reload_without_changing_locale_or_timezone`: **7 PASS**. Использована одноразовая PostgreSQL, после проверки контейнер удалён. Первый запуск без PostgreSQL завершился ошибкой подготовки окружения; повторный штатный запуск успешен. Сохранение темы с перезагрузкой, неизменность языка/часового пояса и серверные границы админки проверены. Полная визуальная приёмка админки остаётся открытой.

Playwright: login/code/signup-email, истёкшее приглашение, общая сводка и недоступная встреча при 390/1440: **12 комбинаций**, HTTP 200, без горизонтального переполнения, по одному h1 и main. Производственные шаблоны на синтетических данных; реальный вход/рассылка этим не подтверждены.

## Совместимый exact-SHA Dev кандидат

- После merge с актуальным `origin/master` и коммита Compose-исправления `46d6938499730af3712e31e52abd227268cdf19c` собран `dev-46d693849973` из того же SHA.
- Подтверждённая Alembic head — `0087_merge_calendar_timezone`; старый Dev namespace содержал неподдерживаемую текущим checkout запись `0088_merge_notifications`, поэтому удалён только изолированный `graf-dev` volume и создан свежий namespace.
- Штатные build/promote dry-run/promote/status/smoke PASS, 13/13 live checks PASS; bundle id `pro.2brain.graf.dev`, channel `dev`, signing identity `GRAF Local Code Signing`.
- Визуальная приёмка exact-SHA окна ожидает разблокировки Mac; GRAF Local не использовался.
