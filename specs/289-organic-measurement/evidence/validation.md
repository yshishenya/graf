# Локальная проверка F289 — 16.10.2026

Основа `d567a7dc51b0c4d99b22660d27950316ae609a66`, ветка `codex/289-organic-measurement`. На момент локальной проверки изменения ещё не были закоммичены. Risk lane: high-risk-product, полный Spec Kit. Независимый checklist требований: PASS 6 checked / 0 unchecked. Analyze: 0 critical/high/medium; T001–T005 связаны с #7601–#7605, umbrella #7593. Issues остаются открытыми до приёмки.

## Проверки

- До реализации: focused PostgreSQL test с `-x` упал на первом `/transcription`, поскольку отсутствовал bucket после двух GET. 1 failed, HTML 200. Это ожидаемое воспроизведение пробела, не ошибка окружения.
- После реализации: команда quickstart на восьми файлах — **138 passed, 2 warnings, 31.54s**; runner status=pass, изолированный контейнер удалён штатно. Подтверждены текущий путь и 2 GET → visits=2; источники organic/referral/direct, automated отдельно; unsafe UTM отброшены; без новых L2/связей/скриптов/изменения campaign cookie. Выключение, явный отзыв, отсутствие и сбой БД → HTML 200 без bucket.
- Два предупреждения среды: PytestAssertRewriteWarning для уже загруженного fixture-модуля и StarletteDeprecationWarning об httpx. Они не пропускают тесты; lock и зависимости проекта не менялись.
- Дополнительная проверка после усиления запрета чтения cookie в обоих alias и включения synthetic enabled production config: **37 passed, 2 прежних предупреждения, 27.24s**. Runner status=pass, изолированный контейнер удалён.
- Ruff изменённых Python: PASS после исправления только порядка импортов нового теста. Development process: PASS (agent-context, fragment, legacy impact). Spec Kit governance: PASS. Changelog fragments: PASS. Git diff whitespace: PASS.

## Объём и ограничения

Три исходных модуля, один новый contract test и две обновлённые проверки. Отдельный каталог PUBLIC_ANONYMOUS_CONTENT_SURFACES включён только в уровень 1, существующий optional inventory не расширен. HTML/templates/static/sitemap не изменены. Нет миграции и новых зависимостей, desktop не собирался и не запускался. Запуск уровня 1 следует существующим настройке и правовому шлюзу; отсутствие withdrawal register не заменено новым требованием положительного реестра.

138 tests подтверждают локальный контракт, не факт публикации или рост. Независимый code review: PASS, P0/P1/P2/P3 = 0, evidence/code-review.md. Converge: PASS, evidence/converge.md. Персональная воронка F273/F096, runtime approvals, восстановление Яндекс кабинетов, выпуск F282/F289 и новые материалы этим срезом не закрываются. На момент локальной проверки CI exact-SHA governance-fast/macos-pr/pr-metadata и frozen release-full/dry-run ещё не выполнялись; коммита и PR не было. После представления результата владелец ответил «действуй» на запрос разрешения создать коммит, открыть PR и провести обязательные проверки. Production deploy в этот шаг не входит. Последующие CI-результаты фиксируются в PR по его точному SHA.

## Воспроизводимость

Команда — quickstart.md, существующий frozen lock, временная среда `/tmp/graf-f289-venv`. Полные временные тестовые журналы не переносятся в Git: в долговечном evidence сохранены только команда, итоги и безопасные агрегаты. Персональных данных, учетных реквизитов и содержимого встреч в доказательствах нет. После завершения проверок временная среда удалена, рабочая копия и отчёты сохранены. Свободное место перед очисткой — 100 GiB.
