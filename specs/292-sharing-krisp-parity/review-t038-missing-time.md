# Независимая проверка требований T038 до кода

Текущий результат 2026-11-12: **требования PASS, C0/H0, checklist 3/0** на базе `494ddc70f88a865b5df3ff8b5b2f663a5af96d7a` плюс документы T038. Подробности повторной проверки и контрольные суммы — в разделе «Текущий вывод» ниже. Первые разделы сохраняют историю замечания H1; тесты и реализация этим отчетом не подтверждаются.

Исторический контекст первой проверки: рабочая копия F292, база c8c2c149f9d07829df187f22b1e8faa7627d349a; reviewer-owned requirements lane. Код, тесты, Git/GitHub, приложение и сервер не менялись. Прочитаны относящиеся к T038 spec/plan/tasks/quickstart, constitution/product-gates и цепочки формирования/чтения итогов.

## Исторический вывод первой проверки

Готовность к коду пока не подтверждена: C0/H1. Checklist после записи перечитан: 2 отмечены, 1 открыт. Дефект None.isoformat подтвержден исходниками и обезличенным receipt производственной синтетической проверки; это не результат нового запуска reviewer.

## История H1 — план не покрывает смысловую дату HTML

В cabinet/summary_sharing.py:183–216 preview_summary получает nullable дату из shared_meeting_display_metadata (cabinet/queries.py:837–848), затем вызывает isoformat. Исправление транспортным fallback соответствует FR-031 и восстанавливает создание снимка. Но в api/cabinet.py:2800–2818 публичный summary_only HTML передает тот же snapshot projection прямо render_public_meeting_reader; cabinet/rendering.py:3017–3019 преобразует строку occurred_at в datetime, шаблон shared_meeting_reader.html:11 отображает дату. При proposed one-point fix неизвестное начало станет ложной датой записи, вопреки FR-031 и обязательной HTML проверке quickstart. Нельзя утверждать, что дополнительная смысловая HTML дата уже применяется к summary_only.

Нужное уточнение до кода: способ отдельной смысловой HTML проекции для публичных сохраненных итогов без изменения JSON/snapshot schema и без подмены snapshot contents; явно указать, как сохраняются дата и смысл у адресных и почтовых сохраненных итогов (api/cabinet.py:2709/2900, api/summary_sharing.py:623) и почему эти consumers затронуты либо остаются вне узкого среза. Указать прямой caller preview_summary в api/summary_sharing.py:96. Исправление helper shared_meeting_display_metadata для возврата created_at повсеместно не подходит.

## Подтвержденные границы

create_summary_snapshot общий для новой публикации, scope/update/rotate и summary delivery batch; preview route вызывает preview_summary напрямую. Возобновление expired ссылки проходит change_general_access→change_link(scope)→create_summary_snapshot, затем отдельный expiry под текущей транзакцией. Срез должен сохранять owner/CSRF/workspace/fingerprint/version/scope fences и не менять порядок открытия доступа.

Существующий тест full_reader_keeps_required_json_date_when_recording_time_is_unknown проверяет только full JSON/HTML. Текущий expired transition matrix не убирает started_at, поэтому не заменяет две новые регрессии. Новые PostgreSQL RED→GREEN, независимый обзор, exact-SHA PR и новый release-full заданы требованиями, но еще не подтверждены.

## Доказательства и ограничения

/private/tmp/graf-release4-production-acceptance-b.log содержит source c8c2, полный reader/audio metadata PASS, expired_resume_probe_failed=AttributeError lines=75,196,119,725,51,836,427,216,205, затем synthetic_cleanup и revoke404 PASS. Содержимое встреч, секретные адреса и токены не копировались в отчет. Сами production/browser/PG сценарии reviewer не выполнял.

Изменены только checklists/missing-time.md и этот отчет. Перед реализацией нужно согласовать plan/tasks с H1 и повторить независимую проверку.

## История — повторная независимая проверка уточнения

Общий HTML helper с optional published_projection выбран верно: snapshot title/известная дата могут сохраняться, а неизвестная смысловая дата остается None; manual_upload сохраняет метку загрузки. Новая схема/миграция не требуется. Однако H1 пока не закрыт: обнаружен пропущенный пятый HTML consumer cabinet/web_routes/browser.py:_render_shared_summary_for_grant:143–147. При saved != None он передает saved occurred_at напрямую render_shared_meeting_summary_page; общий metadata helper вызывается лишь в ветке без saved. Это обслуживает /shared-meetings (и обычную страницу с ограниченным доступом), поэтому список «все четыре» ошибочен. В api/cabinet.py третья HTML ветка2900 относится к accept_meeting_share_invitation_route, а не к /shared-meetings.

Необходимо включить browser.py и его saved-ветку в план/задачу/проверки. Формулировка «helper менять нельзя» также требует уточнения как запрет смены прежней семантики, иначе противоречит optional argument. После этого основание H1 будет устранено; до изменения остается C0/H1, checklist2/1. Код и тесты reviewer не менял и не запускал.

## Текущий вывод — требования T038 PASS, C0/H0

Повторная независимая проверка 2026-11-12 выполнена на базе `494ddc70f88a865b5df3ff8b5b2f663a5af96d7a` с текущими незакоммиченными документами T038. Выше сохранены прежние замечания и прежняя база c8c2 как история. **H1 устранен документами; других CRITICAL/HIGH в узком срезе не найдено. Checklist: 3 отмечены, 0 открыто.** Это приемка качества требований до кода, а не приемка реализации или выпуска.

### Почему H1 закрыт

`plan.md:178`, `tasks.md:171` и `quickstart.md:158` согласованно включают все пять HTML входов опубликованных итогов:

| HTML вход | Проверенный код до реализации |
| --- | --- |
| Адресный API | `api/cabinet.py:2703–2719` |
| Общедоступная страница | `api/cabinet.py:2780,2803–2816` |
| Принятие приглашения | `api/cabinet.py:2895–2910` |
| Доставка сохраненных итогов | `api/summary_sharing.py:608–627` |
| Сохраненные итоги в браузере | `cabinet/web_routes/browser.py:143–147`; callers `659,750` для обычной ограниченной страницы и `/shared-meetings` |

План больше не запрещает изменение кода `shared_meeting_display_metadata`: он запрещает изменение прежней смысловой семантики. Для HTML задана опубликованная проекция: сохраняются заголовок и известная дата снимка; неизвестная смысловая дата остается None, manual_upload сохраняет признак загрузки. Требование охватывает будущий общий путь и все пять consumers. Существующие renderers и оба HTML шаблона прочитаны: прямое преобразование snapshot occurred_at в datetime пока остается в коде; именно его будущую замену описывает план. Это не новое замечание к требованиям и не доказательство уже выполненного исправления.

### Общая точка исправления и сохраненные границы

- `cabinet/summary_sharing.py:183–216`: preview_summary формирует транспортную проекцию и вызывается create_summary_snapshot; fallback `occurred or meeting.created_at` задан в одном месте. Прямой owner preview `api/summary_sharing.py:86–99` указан в плане.
- Все вызовы create_summary_snapshot просмотрены: новая публикация `350`, scope `427`, update `439`, rotate `458`, delivery batch `570`. Они получают исправление через общую точку, без новых схем и миграций.
- Все текущие callers shared_meeting_display_metadata просмотрены: `cabinet/summary_sharing.py:201`, `cabinet/public_sharing.py:240`, `cabinet/access.py:2205`, `api/cabinet.py:2705,2896`, `cabinet/web_routes/browser.py:193`. Сохранение прежнего поведения без опубликованной проекции задано планом; full reader и invitation preview сохраняют разделение транспортной/смысловой даты.
- `cabinet/queries.py:837–847` подтверждает исходную семантику: без started_at manual_upload получает created_at как время загрузки, остальные источники получают None. `cabinet/rendering.py:424–453,3017–3046` и `cabinet/templates/cabinet/pages/{shared_meeting_reader,shared_meeting_summary_content}.html` подтверждают реальные HTML consumers даты/метки.
- `spec.md:227,242–244` и `plan.md:178–180` сохраняют FR-036: существующие owner/CSRF/workspace/fingerprint/version/scope ограничения и атомарность сужения перед продлением. Код `cabinet/summary_sharing.py:796–856`, в частности scope→expiry на `836–842`, соответствует этой границе. Review не меняет права, URL, срок, сохраненное содержимое снимка или запреты transcript/audio.

### Полнота будущих проверок

`quickstart.md:156` требует две реальные PostgreSQL регрессии с started_at=None: новую summary_only публикацию и expired full→summary, сначала воспроизводящие AttributeError, затем успешный результат с обязательной JSON датой, без ложной HTML даты начала и без transcript/speakers/media_version/audio. Сохраняются URL, выбранные срок/состав и опубликованный снимок. `quickstart.md:158` отдельно покрывает все пять HTML входов для неизвестного/известного начала и manual_upload с меткой загрузки, заголовок/известную дату снимка и неизменность JSON.

Исходник `test_full_reader_keeps_required_json_date_when_recording_time_is_unknown` и `test_general_access_resumes_expired_link_without_widening` просмотрен: первый проверяет full reader, второй не убирает started_at; они не подменяют новые случаи. `plan.md:180` / `tasks.md:171` сохраняют прежние проверки, независимый обзор, exact-SHA PR и новый frozen candidate с release-full. Никакая из этих будущих проверок в этом review не выполнялась и не объявляется пройденной.

### Версия документов и независимая сверка

Прочитаны текущие части T038 spec/plan/tasks/quickstart, checklist и предыдущий report, constitution, product-gates и относящиеся к срезу правила Spec Kit. Дополнительный независимый read-only агент сверил consumers/цепочки вызовов и требования, вернул C0/H0; reviewer сопоставил его вывод с перечисленными исходниками. Дополнительный агент файлов не менял.

SHA-256 проверенных документов; база Git сама по себе не идентифицирует незакоммиченный текст:

| Документ | SHA-256 |
| --- | --- |
| `spec.md` | `a712a46da646f33a0fd1e8e9c6fc384280de0435445b2e234d4f5a4b078d6730` |
| `plan.md` | `aae6f837722fc912b3dddcc8db47d71b367bec467f9c589c9b8916be87de8a7a` |
| `tasks.md` | `924195150ca808cf6d75bc46bf2c140a3691b27b18d92d371748c9e4cd67eabf` |
| `quickstart.md` | `dcce86a5580edab80fe5776ecbaa164f7ffc05a099ed6eab07109f1974990acf` |

### Ограничения и разрешенная запись

Изменены только `checklists/missing-time.md` и этот отчет. Чужие правки сохранены. Код, Git/GitHub-состояние, приложение, сервер, релизы и зависимости не менялись. Тесты, CI и production не запускались; .env, секреты и закрытые материалы не читались. Старый production receipt не открывался: его описание выше остается историческим свидетельством предыдущего reviewer. Текущий вывод основан на документах и чтении исходников.

PASS снимает только замечание к требованиям T038. Обязательные analyze, issue sync, реализация и последующие проверки сохраняются; завершение T038 или готовность к выпуску этим отчетом не подтверждаются.
