# T038 — реализация и локальная проверка

2026-11-12. Действующий срез F292 высокого риска, база `494ddc70f88a865b5df3ff8b5b2f663a5af96d7a` плюс текущая реализация. Код и проверки локальные; commit/PR/CI, независимый обзор кода и выпуск ведет оператор отдельно.

## Изменение

- `cabinet/summary_sharing.py:preview_summary` сохраняет обязательную транспортную дату по прежнему правилу «начало или создание» при отсутствии смысловой даты.
- Существующий `queries.shared_meeting_display_metadata` принимает необязательную опубликованную проекцию. Заголовок и известная дата снимка сохраняются; неизвестное начало остается None; ручная загрузка сохраняет прежнюю смысловую дату и метку.
- Общий helper применен во всех пяти входах HTML снимка: адресный API, public и принятие приглашения в `api/cabinet.py`, delivery в `api/summary_sharing.py`, saved-ветка `cabinet/web_routes/browser.py`. Последняя проверена и через `/shared-meetings`, и через обычную ограниченную страницу встречи.
- В публичный шаблон добавлен существующий текст «Загружено» по признаку только HTML. Новых полей JSON, DTO, схем, миграций, зависимостей, прав или способов отправки нет. Остальные callers helper сохраняют прежний вызов и проверены существующей группой.
- `changes/unreleased/F292.yaml` описывает исправление для нового кандидата.

Пять HTML consumers были перечислены до правки. Прямой owner preview и все создания/обновления снимка получают исправление через общую точку preview_summary. Срок, URL, fingerprint, версия, транзакционное сужение перед продлением и проверки доступа не менялись.

## Ворота перед кодом

`analysis-t038.md`: C0/H0/M0, требования покрыты T038, конфликтов конституции нет. Независимый missing-time checklist 3/0, текущий report C0/H0. В расширениях before/after analyze/implement только выключенные hooks; Git не изменялся. Существующий issue #8045 и canon ensure/validate подтверждены оператором. Reviewer-owned файлы реализация не меняла.

## RED

Предметный новый модуль `test_summary_sharing_missing_time.py` добавлен до исправления. Настоящий PostgreSQL, команда:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q tests/integration/test_summary_sharing_missing_time.py
```

Отказ исходника на `None.isoformat()` подтвержден для owner preview, создания новых итогов и возобновления full→summary на 7/30/90 дней. В первом прогоне 5 отказов относились к этой причине; еще два были ошибками начального нового теста (ключ снимка). Они исправлены до использования доказательства HTML. Отдельная проверка known/manual выявила отсутствующую метку загрузки публичной страницы. Попутные ошибки нового теста с Mock return, нормализацией Z/+00:00 и обязательным media_version исправлены в тесте без ослабления рабочих ограничений.

Исторические локальные журналы RED: `/private/tmp/graf-t038-red.log`, `/private/tmp/graf-t038-red-html-b.log`. Содержат только синтетическую проверку и не включаются в Git.

## GREEN

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/integration/test_summary_sharing_missing_time.py \
  tests/integration/test_meeting_sharing_parity.py \
  tests/integration/test_summary_sharing.py \
  tests/integration/test_summary_delivery.py \
  tests/integration/test_shared_with_me.py
```

**63 passed**, 135.83 секунды. Прежние full/summary, стабильная ссылка, scope/expired/stale/permission, RLS, сохраненные итоги, Mock-доставка и смысловые даты проходят. Журнал `/private/tmp/graf-t038-green-b.log`; isolated container cleanup PASS.

После добавления явного покрытия второго вызова browser helper через обычную страницу:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/integration/test_summary_sharing_missing_time.py \
  tests/contract/test_recording_share_ui_contract.py \
  tests/contract/test_recording_share_invitation_contract.py
```

**23 passed**, 20.18 секунды. Журнал `/private/tmp/graf-t038-final-html.log`; cleanup PASS. Все семь предметных случаев прошли; три из них проверяют пять HTML consumers для unknown/known/manual, опубликованный заголовок после переименования, известную дату после изменения текущей даты и неизменный JSON. Сужение expired full→summary проверяет прежний URL, выбранный срок, снимок, отсутствие transcript/speakers/media_version/playback_available и audio404 с корректно сформированным запросом.

Ruff на пяти измененных Python modules и новом тесте: **All checks passed**. `git diff --check`: **PASS**. Два предупреждения pytest касаются уже загруженного plugin и устаревающего httpx TestClient; отказов нет. Изоляция и проверки существующего runner сохранены. Реальная почта не отправлялась: доставка полностью AsyncMock.

## Границы

Независимый обзор кода, converge, точные проверки PR, новый frozen release-full и production-проверка этого источника еще не выполнены в рамках реализации. Прежний успешный Full для выпуска .4 их не заменяет. Установленное приложение, браузер и обновление проверяет оператор; локальные PostgreSQL и HTML tests не объявляются native или production приемкой. Полный F292 и его остальные открытые задачи этим отчетом не закрываются.
