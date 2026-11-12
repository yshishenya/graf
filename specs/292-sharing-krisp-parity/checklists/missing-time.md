# T038 — снимок итогов без известного начала

Reviewer-owned: независимая проверка до кода.

- [x] CHK001 FR-031/036 и уточнение задают прежний транспортный fallback «начало или создание» для summary_only без изменения семантического HTML, API и прав; дефект подтвержден production synthetic AttributeError на None.isoformat.
- [x] CHK002 Общая точка preview_summary покрывает create_summary_snapshot и все его callers; срез не изменяет атомарность expired full→summary, адрес, срок, fingerprint, сохраненный scope и запреты доступа.
- [x] CHK003 RED→GREEN PostgreSQL включает новую публикацию и возобновление с сужением без started_at, JSON дату, HTML без ложной даты начала, прежние URL/срок/снимок и transcript/audio denial; прежние full/scope/expired/privacy тесты, независимый обзор, exact PR и новый release-full обязательны.

## Текущий статус — повторная проверка всех пяти HTML входов

2026-11-12, база `494ddc70f88a865b5df3ff8b5b2f663a5af96d7a` плюс текущие незакоммиченные документы T038: **3 отмечены / 0 открыто, C0/H0; требования PASS**. Ниже сохранена история двух предыдущих проверок; их H1 больше не является открытым замечанием.

CHK001 подтвержден текущими FR-031/036 и уточнением T038 (`spec.md:193,227,242–244`), планом (`plan.md:178`) и чтением `queries.py:837–847`, `summary_sharing.py:183–216`: неизвестная смысловая дата остается None, обязательная JSON дата получает fallback. Production receipt упомянут только как историческое доказательство предыдущего reviewer; в этой проверке он не открывался и production не запускался.

CHK002 подтвержден: `plan.md:178`, `tasks.md:171`, `quickstart.md:158` включают три HTML ветки `api/cabinet.py` (адресный API, public, принятие приглашения), delivery `api/summary_sharing.py` и saved-ветку `cabinet/web_routes/browser.py:_render_shared_summary_for_grant`. Последняя обслуживает обычную ограниченную страницу и `/shared-meetings` (`browser.py:659,750`). Общий helper допускает опубликованную проекцию с сохранением заголовка/известной даты снимка, None для неизвестного смыслового времени и признака manual_upload; запрет изменения прежней семантики не запрещает изменение кода helper. Прямой owner preview (`api/summary_sharing.py:96`), все пять вызовов `create_summary_snapshot` (`cabinet/summary_sharing.py:350,427,439,458,570`) и остальные callers metadata helper просмотрены. FR-036 и план сохраняют права, fingerprint/version, scope, URL и транзакционный порядок scope→expiry (`summary_sharing.py:836–842`). H1 закрыт документами, иных C/H в этом узком срезе не найдено.

CHK003 подтвержден как полнота будущих требований: `quickstart.md:156,158` задает две PostgreSQL регрессии, все пять HTML входов для неизвестного/известного начала и manual_upload, сохранение опубликованного заголовка/даты и JSON, прежние full/scope/expired/stale/permissions проверки; `plan.md:180` и `tasks.md:171` сохраняют независимый обзор, exact-SHA PR и новый release-full. Это не результаты выполнения тестов. Существующий full JSON тест и expired matrix просмотрены только как исходники.

Дополнительный независимый read-only агент сверил перечень consumers и границы; его вывод C0/H0 совпал с проверкой reviewer. Отметки относятся только к качеству требований. Реализация T038, analyze/issue sync, тесты, CI, приложение и выпуск этой проверкой не принимаются. Подробности и контрольные суммы документов — в `../review-t038-missing-time.md`.

## История — независимая проверка требований до кода

2026-11-12: проверено 2, не подтверждено 1; C0/H1. Отметки относятся только к качеству требований, не к прохождению будущих тестов.

CHK001: FR-031/036 и уточнение T038 разделяют обязательную дату JSON и смысловую дату HTML. Локальный обезличенный production receipt подтверждает AttributeError на цепочке836→427→216→205; исходный код подтверждает None.isoformat для неизвестного начала не manual_upload.

CHK002 оставлен открытым: план ограничен preview_summary, однако публичный summary HTML напрямую получает snapshot projection через render_public_meeting_reader; строка occurred_at после транспортного fallback становится датой создания и отображается как дата записи. Также preview_summary вызывается напрямую owner preview route, а HTML сохраненных адресных/почтовых итогов отдельно читает snapshot occurred_at. Нужен явный перечень HTML consumers и способ сохранения их прежней достоверной даты без изменения транспортной схемы/содержимого снимка; до кода устранить несоответствие scope.

CHK003: quickstart/T038 задают обе PostgreSQL регрессии, JSON/HTML/URL/срок/scope/snapshot и отказы transcript/audio, сохраняют прежние проверки и свежие PR/release gates. RED и GREEN еще не выполнены в этой проверке и не объявляются пройденными.

## История — повторная проверка уточнения плана

2026-11-12: 2 отмечены / 1 открыт, C0/H1. Общий optional published_projection в HTML helper — подходящее повторное использование; транспортный JSON остается отдельным. Но перечислены не все HTML consumers: cabinet/web_routes/browser.py:_render_shared_summary_for_grant при saved is not None напрямую отображает saved occurred_at (строки143–147), вызывается обычной и адресной страницами. Он не входит в заявленные три ветки api/cabinet.py + delivery. Это пятый общий вход рендера; shared-meetings находится именно здесь, а третья ветка api/cabinet.py — принятие приглашения. CHK002 остается открытым до включения browser.py и его проверок в scope. Дополнительно убрать в плане буквальную противоречащую фразу «менять этот HTML helper нельзя»: его прежняя семантика сохраняется, но optional projection предполагает изменение кода helper.
