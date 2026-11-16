# T112 — независимый вход перед свежей серверной проверкой

Дата: 16.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
HEAD: `41fdf6c11475819993a3584aa869496034a391e2`.
Область: существующая `high-risk-product` F273/T112, следующий изолированный
шаг fresh session/membership/device/Meeting/source/projection verifier.
Кода этого шага при проверке ещё нет; это допуск к его изолированной реализации,
не implementation review и не допуск к рабочему сбору.

## Решение

**PASS требований и минимального проекта при условиях ниже; P1=0, P2=0,
blocking clarification=0.** Все 124 действующих вопроса четырёх основных
reviewer-owned списков перечитаны и оценены с учётом этого шага.

| Список | Отмечено | Не отмечено |
| --- | ---: | ---: |
| requirements | 16 | 0 |
| security | 27 | 0 |
| privacy-measurement | 52 | 0 |
| infra | 29 | 0 |
| Всего | **124** | **0** |

Оснований менять reviewer-owned отметки нет: определения владельца, активного
доступа, свежести после конкурентного отзыва, общего допуска, происхождения,
пары и отказов уже содержатся в принятых требованиях. Эти 124 отметки относятся
к качеству требований. T112/T113 остаются открыты; runtime, T0 и продажи
выполненными не становятся.

Все 13 ранее принятых входов побайтно сравнены с
`503805cb6188f942adb159ea2bab8560969b7b0e`: все совпали. Четыре базовых
документа совпали с исходным T112 design-draft. Использовано собственное
прежнее полное чтение этого же диалога и разрешённый порядок F273 согласно
`document-reading.md`; изменившихся требований или новой продуктовой области
не обнаружено. Действующие вопросы перечитаны отдельно от исторических
дополнений списков, которые не являются новой текущей приёмкой.

## Применимость прежних решений

- `t112-server-preflight-20261116.md` сохраняется: один внутренний путь
  ProductAnalyticsIngestService, доверенный период только из T113 context,
  verifier только внутри действующих locks/session, без второго writer,
  route → SQL primitive, клиентского trusted-флага или даты из settings.
- `t112-server-writer-fences-review-20261116.md` сохраняется: все 18 хешей
  проверенных источников совпали. Meeting `FOR UPDATE` является общей границей
  текущих путей публикации результата/итогов/accepted revision/удаления.
  Одни shared locks существующих результатов не защищают появление нового
  результата или замену дочернего текста. После Meeting нужен свежий выбор.
- `t112-account-pair-review-20261116.md` сохраняется для общей транзакции и
  атомарной пары. Отдельное подтверждение основного агента о terminal EXIT0
  `session84157`, `chunk_id4e4a05` согласуется с самостоятельно прочитанным
  журналом 106 passed / 1 warning / 87.80s и его прежним SHA-256. Это прежний
  профиль account-pair, не проверка ещё отсутствующего fresh verifier.

Применимые оригиналы восстановлены: spec Session 16.11/FR-021/025/SC-006/007;
plan §T112; tasks T112/T113 и уточнение 16.11; quickstart весь текущий профиль
T112; research §T112; data-model transient proof; result-visibility §§2–7;
activation-milestones, общий account admission и прежние условия preflight.
Конституция II/III/IV/VI/VII и product gates: неизменность capture, запрет
содержимого/секретов в evidence и аналитике, контролируемые access/deletion,
без внешнего вызова внутри проверки, независимое ревью и выпускные ворота.

## Минимальная граница свежего verifier

Предложенная узкая реализация в `cabinet/result_visibility.py` допустима:
она принимает только внутренний подтверждённый principal, точный meeting и
тот же разрешённый выбор проекции, что GET; выполняется на DB-сессии общего
admission, не делает commit/rollback и не включает никакой runtime context.

Рекомендуемый порядок внутри уже существующей общей границы:

1. T113 filesystem shared fence → DB transaction advisory `(273,3)` → shared
   active UserIdentity. Настоящий T113 context пока возвращает отсутствие
   разрешения; тест может подставить только этот внутренний контекст.
2. На той же сессии заново прочитать UserIdentity с organization/status,
   AuthSession через `FOR UPDATE`, Workspace и точный WorkspaceMembership
   через `FOR SHARE`, все AuthSessionDeviceBinding этой сессии и связанные
   RegisteredDevice через `FOR SHARE`. Использовать `populate_existing=True`;
   отсутствующий обязательный объект означает отказ.
3. Проверить active identity, organization equality, session user/workspace,
   active/неистёкшую session, прежний допустимый customer workspace и personal
   owner rule, active membership. Роль admin и полный shared доступ не
   заменяют `Meeting.created_by_user_id == principal.user_id`.
4. Использовать штатную чистую `session_device_access()` на **всех** заново
   прочитанных bindings/devices. Результат должен совпасть с principal по
   session/device. Не выбирать лишь одну удобную trusted-связь: дополнительная
   blocked/чужая связь меняет решение. Прежний допустимый API bootstrap без
   session.device_id и без связей остаётся допустимым по этой функции; новый
   запрет всех таких сессий из текущих требований не следует.
5. Получить существующий Meeting `FOR UPDATE`, проверить точное владение и
   deletion state/epoch; затем заново вызвать общий
   `get_cabinet_meeting_review()`, `load_result_view_bindings()` и HMAC проверку
   конкретного proof. Весь source/result/outcome/слот остаётся под Meeting
   до единственного commit общего admission. Дополнительные shared row locks
   разрешены, но не заменяют Meeting.
6. Сохранить общий действующий T113/legal/resource recheck перед каждой
   вставкой и commit. Для времени дополнительно действует проверка session
   expiry, описанная ниже. Занятость/таймаут/изменение/неизвестность закрывают
   только аналитику, без retry и влияния на просмотр.

Это конкретизация существующих требований, не новая модель идентичности,
таблица, поток входа, конфигурационный флаг или запрос решения владельцу.

## Почему нужны именно эти блокировки

| Объект | Изменяющие существующие пути и нужный конфликт |
| --- | --- |
| UserIdentity | `auth/account_closure.py` получает identity `FOR UPDATE` перед closed и purge; `auth/account_merge.py` блокирует active account roots перед переносом/merged. Shared identity удерживает активность/organization выбранного аккаунта. |
| AuthSession | `auth/sessions.py:259` `revoke_auth_sessions` получает session до bindings и меняет status; `workspace_onboarding.py:242` `activate_workspace_session` получает current session `FOR UPDATE` и ставит replaced; `auth/dependencies.py:257` меняет expired/revoked через UPDATE; provider unlink в `cabinet/web_routes/settings.py:870` блокирует sessions, затем bindings. Все конфликтуют с выбранным `FOR UPDATE` той же session. |
| Новая device binding | `api/auth.py` регистрация получает AuthSession `FOR UPDATE` до INSERT binding и смены session.device_id. Новый binding имеет FK к AuthSession; parent `FOR UPDATE` также конфликтует с FK key-share вставки, включая допустимый bootstrap с пока пустым набором. Один `FOR SHARE` только найденных bindings не защищал бы их отсутствие. Другие найденные создания в callbacks/email/billing/workspace onboarding относятся к заново выданным session, а не бесконтрольному добавлению к текущей. |
| AuthSessionDeviceBinding | `revoke_auth_sessions`, provider unlink и account merge ставят blocked; `record_session_activity` меняет heartbeat. Shared locks всех существующих связей останавливают UPDATE/DELETE до завершения решения. `FOR KEY SHARE` не останавливает обычную смену device_state и здесь недостаточен. |
| RegisteredDevice | `revoke_registered_devices` ставит status/registration_state revoked после session locks; account closure/merge меняют те же поля; registration/activity обновляют metadata/last_seen. Shared lock самой device защищает её status, registration_state, user и workspace даже если writer не получает отдельный Meeting. |
| WorkspaceMembership | `admin/users.py:244` `update_workspace_membership` меняет role/status обычным ORM UPDATE; его storage advisory lock не является общим analytics fence. Account closure делает массовый inactive, merge меняет/удаляет membership. Нужен shared lock точной строки membership, не предположение, что session была проверена раньше. |
| Workspace | Проверяются organization, kind и personal owner. Shared lock строки защищает эти поля от изменения/переноса; один membership lock сам по себе не защищает workspace. |
| Meeting и выбранный source/result/outcome | Действует прежний writer-fences review: Meeting первым относительно контентных строк, свежий review после него, удержание до commit. Это не требует глобально переписывать существующие writers в данном подшаге. |

В некоторых широких existing writers порядок не совпадает полностью с
analytics, например merge ранее блокирует proof session, затем account roots,
а account closure берёт storage/workspace domain до identity. Здесь не
доказано глобальное отсутствие взаимных ожиданий. Именно поэтому обязательны
ограниченные locks/общий бюджет/закрытый отказ без retry; расширять этот срез
до общего изменения auth writers не требуется.

## Срок сессии перед каждой вставкой и commit

Строковая блокировка предотвращает status UPDATE, но не останавливает часы.
Проверки expiry один раз до большого review недостаточно. Минимальная
интеграция: fresh verifier сохраняет в текущем внутреннем контексте проверки
дедлайн **свежей заблокированной AuthSession**; общий `_check_admission`
проверяет его против нового `datetime.now(UTC)` перед каждым INSERT и перед
commit, одновременно сохраняя прежний T113 `recheck`.

Допустима эквивалентная композиция внутреннего guard: прежний period guard
плюс guard expiry, установленный после успешного verifier и до первой
вставки. Это один и тот же общий context, видимый как `_admit_event`, так и
pre-commit владельцу. Нельзя заменить T113 guard проверкой expiry либо сделать
`dataclasses.replace(context, ...)` только в локальной переменной
`admit_result_view`: владелец `_account_transaction` тогда продолжит видеть
прежний context при commit. Частная форма передачи проверенного дедлайна и
хранение guard в context — инженерный выбор; новый HTTP/proof field не нужен.

Истечение перед второй вставкой или commit должно дать rollback нового
набора. Изменение session status/device блокируется настоящими locks; для
времени выполняется повторная синхронная проверка. Продление сессии другим
запросом не обходится через снятие lock: при выбранном `FOR UPDATE` оно ждёт,
а аналитика может безопасно отказать по исходному дедлайну.

## Чистые helpers и опасные для этой транзакции вызовы

- `auth/sessions.py:is_session_token_valid` и `session_device_access` — чистые
  проверки уже прочитанных значений, без commit/записи/транспорта.
- `resolve_session_device` читает все связи/устройства, не делает commit,
  однако сам не берёт нужных locks. Для verifier предпочтительнее передать
  уже заблокированные строки чистой `session_device_access`.
- `processing/fences.py:lock_meeting_fence` — нужная блокировка без commit.
  `cabinet/access.py:decide_meeting_access` и membership readers сами не
  коммитят. При этом owner-ветвь `decide_meeting_access` сама по себе не
  отвергает отсутствие active membership: обязательна отдельная свежая
  проверка membership/session до неё.
- `get_cabinet_meeting_review` использует временный `_meeting_review_read_scope`,
  очищает старый list-prefetch и строит новый detail-prefetch после получения
  Meeting. Он не делает commit. Для analytics вызывать с `storage=None` и
  обычными выключенными optional correction/invitation параметрами: текст
  проверяется тем же helper без внешней проверки storage; наличие аудио и
  экспортное право не являются условием T112. Изменять GET-проекцию или
  собирать похожую ручную проекцию вместо общего helper нельзя.
- `load_result_view_source`, `load_result_view_bindings`, digest и proof
  helpers не делают commit/записи/транспорта. Они прямо требуют уже свежего
  доступа, общего периода, fences и бюджета у вызывающей стороны; сам
  `started_at` либо return binding не дают такого допуска.
- Нельзя вызывать в этой транзакции `_principal_from_session_token`, полный
  `get_device_context` из auth dependencies, activity renewal middleware,
  `set_workflow_status`, `set_dependency_state`, `persist_processing_result`
  либо операции export/download/playback: среди этих путей есть собственные
  сессии, записи, commit и/или I/O. Существующие HTTP principal/CSRF остаются
  внешней проверкой; verifier независимо перечитывает нужные строки без
  запуска auth workflow заново.

Выбор query сохраняет ранее принятую семантику: browser использует
summary_format/source_result_id, desktop — ровно то, что использует его GET
(сейчас только summary_format). Последнее значение повторного ключа, включая
пустое, обрабатывается одинаково. Proof остаётся только в JSON/data-атрибуте.

## Обязательные причинные проверки следующего кода

Положительный тест подставляет только внутренний period context и прежние
эксплуатационные receipts. Внутри verifier не подменяются доступ, исходники,
HMAC или текущая проекция. Нужны новые тесты самого fresh шага:

- настоящее новое разрешённое содержимое → valid binding и одна атомарная
  пара через принятый общий admission; closed настоящий context → 0 writes;
- чужой/неактивный аккаунт, другая organization/workspace/session/device,
  inactive membership, revoked/replaced/expired session, blocked/лишняя binding
  и revoked/unapproved device → отказ;
- session revoke, workspace switch, membership mutation и device revoke в
  независимой DB-сессии: writer-first меняет факт до чтения, analytics-first
  удерживает нужный конфликт до завершения или получает bounded отказ;
- bootstrap без связей и параллельная регистрация binding; отсутствие строки
  не принимается за защищённое shared lock, используется session parent lock;
- истечение session до второго INSERT и до commit → нет частичной новой пары;
- Meeting deletion, source/revision/result/slot/text switch → свежий review
  под общей блокировкой, старый proof не признаётся новой проекцией;
- занятые locks, callback cancellation и timeout → закрытый отказ, никаких
  остающихся tasks/session; общий 2s/250ms/500ms бюджет не расширяется.

Полный HTTP body/pool/cleanup budget, issuance/renewal, native/browser end-to-end,
runtime T113/readiness/restore/local_only/T0 и выпуск остаются вне этого
предварительного PASS и должны быть приняты своими последующими проверками.

## Доказательства неизменности

Все пути следующей таблицы относительно `specs/273-paid-traffic-analytics/`;
каждый файл побайтно совпал с принятой основой, а не только с именем/HEAD.

| Путь | SHA-256 |
| --- | --- |
| `spec.md` | `a7f23904625df9b06aed1e09c05f2ffa75ec3e5ec9ac0eda0531cd88c949c645` |
| `plan.md` | `5207a988f666c47f65203718a1212cf352312009f1c3804163abd093318a8b3c` |
| `tasks.md` | `3870e4d091557e0c40dd5500aa8fb5932b933cfe877e684c930d7f7e4f93a7d5` |
| `quickstart.md` | `4f2488aa98a3fba478eed042304279f408dc2530bd3f2b0449cedabaf39dd074` |
| `research.md` | `64caef3d9a78f0021c2b37ca86e0f388724bf117e899bd044f4ca557a1ba094f` |
| `data-model.md` | `478c18546d1240c4a1c15c5b07e76f7aeb551082273b75bc1fbf4cdd8d1ae8ab` |
| `contracts/activation-milestones.md` | `4835c0c6672a464366c9657d9285b28429ec2ed4d4e234c0c4897a65ed5027c4` |
| `checklists/requirements.md` | `d771fe1f54e69b297346bfde3ea52f82d484fc241f13576efc34e09feffe80f4` |
| `checklists/security.md` | `dbd65a5afb7829789d8b4aa48f8c0b32243cc039681d15a5b851b381ca3b8b92` |
| `checklists/privacy-measurement.md` | `5b4164d0ce3e11ea6bca8419f4f0d6f6d33de163e3745cbb4cbfccd90ce07840` |
| `checklists/infra.md` | `a3319849bcd8be93803415495b42b4e50476cf1e08eb57ef898d34293f2be0cf` |
| `validation/t112-requirements-review-20261116.md` | `bb7c8592b302d6cb9ef21e0ecfc1045778afd39f07efed29787091ae3aaf91a5` |
| `validation/t112-analyze-20261116.md` | `0252da92dd9c3ff435a13bf55c0234afbb010abd9a3a1c49f8e42461427c18dc` |

Текущий result-visibility:
`ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8`;
он соответствует принятому observer/native уточнению. Четыре базовых суммы:
constitution `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`,
PRD `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`,
status `66ba7daa70519c8848a6daea51cd593220fccf75d4b5ea3a4a154e5ae139c3ca`,
product-gates `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
Guidance document-reading:
`5c3ab1f885dbf324edab70c0f4b7a5451208b3d7307c1ca7a5afdd7af0c8eb22`.

Новые применимые источники auth прочитаны в оригиналах, включая весь
`auth/sessions.py`, функции проверки principal/device, регистрацию устройства,
membership mutation и относящиеся разделы больших workspace activation/
account closure/merge. Это чтение не означает полный аудит auth. Основные SHA-256:

| Server package path | SHA-256 |
| --- | --- |
| `auth/dependencies.py` | `559bcc1c46cdf49cd283d8a199e089fc7047401b669c0ab17ae9b6d98c94d311` |
| `auth/sessions.py` | `c94996ff2a4be814f43f502d7bc2f3fc925909311686d437aad32d7c9f528aab` |
| `auth/workspace_onboarding.py` | `e05cd05f61be794e42ec474e87c12d42fe1209b815c60ff59f28ab43f7d3b297` |
| `auth/account_closure.py` | `4e2f6ac7b799a56b19ad24371241dbe5a252f12aa1f2441e2c7a2d4b6358cac9` |
| `auth/account_merge.py` | `7840869e398b8f621d78c27119a7ecbba15f4f6058fac1d7f54e1dd4f598e205` |
| `api/auth.py` | `78defae4b1f7b86acd0f24a2a75c3fc18ad5a70435a73859285adf6f450dd6dc` |
| `admin/users.py` | `db9828759ee1230e3f3aed966e3b4aac4415b792f269d5c8867f707fd37c8811` |
| `cabinet/access.py` | `b4c055f84f8e8f51500e96468d20b01c72125aa19e910b43297a93b7677100bc` |
| `cabinet/queries.py` | `cf0e7b622c60e53513df78140ddf2d2ab74937a55a15ce7c719de56fa14f50da` |
| `cabinet/result_visibility.py` | `bf7e12055b7db289cd9224a32e41beba7a0359df73de106cdc70705471795fa9` |
| `cabinet/web_routes/settings.py` | `1e7e6d115aece1a8566b92f4cfb5b52bb9192642f5d7f9f21c20412a2df25bd6` |

Прежние отчёты: server-preflight
`326782d610867430e26a7e97c71803bb1e44e2c57472790c16a8f158f5eabf59`,
writer-fences `bbbf88c10a7b2981cfcdf5dc7058b95bbacd6ead6a7eab1987ed3c2fa55ddc8a`,
account-pair-review `fd5bf61de7aad0a69daace6a410ca6c22c4c71aacf5e2a75f6a4a661ecd11490`.
Они не подменяют новую независимую приёмку будущего кода.

Проверяющий изменил только настоящий отчёт. Списки, код, требования, план,
задачи, Git/GitHub и runtime не менялись. Тесты, сборки, браузер, БД,
публикации и внешний сбор не запускались. Перед дальнейшей реализацией
дополнительных вопросов владельцу не требуется; сохраняются независимое
implementation review/converge и обязательные проверки точного SHA.
