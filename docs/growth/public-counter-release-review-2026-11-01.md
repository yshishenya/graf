# Публичная Метрика после v2026.11.01.1 — узкая независимая сверка

Дата:01.11.2026. Проверяющий `/root/public_counter_readiness_review`.
Полоса:read-only investigation; изменён только этот отчёт.
Точный release clone HEAD проверен локально:
`d7d87beec52a8f71b36cf53eca30dd31158eb643`.
Предыдущий диагноз31.10 использован как перечень требований, а не как
подтверждение нынешней runtime конфигурации.

**Можно продолжить полезный узкий T106 независимо от незавершённого полного
T113. Включение публичной Метрики одной сменой revision всё ещё HOLD.**
Готовность общей account→recording→result→payment воронки не является
предпосылкой прежних analytics-only просмотров `/` и `/download`; прямые
условия согласия/основания/остановки/раскрытия этих просмотров сохраняются.

## Что действительно изменилось в точном исходнике выпуска

| Прежнее условие | Итог после выпуска | Доказательство и предел |
| --- | --- | --- |
| T106: актуальное серверное основание для HTML, relay и worker | Закрыт узкий code/test срез | public_analytics_blocker заново читает существующий register, отказывает при !available/file_errors/provider_analytics withdrawal; вызывается builder, route после normalization и worker до клиента. Final PostHog gate сохранён. Actual production register/permission пока не прочитан в этой сверке. |
| T106: локальный выбор нельзя брать только из памяти страницы | Закрыт узкий code/test срез | canUseAnalytics сверяет revision/state/categories с localStorage; storage/pageshow/focus/visibility повторяют проверку. Поздний callback не заменяет новый library choice. Это локальный выбор, не свежее глобальное разрешение сервера. |
| T106: очистка очереди не ломает SDK destruct | Закрыт code/test срез PR7857 | reverse splice сохраняет ym.a и custom push, удаляет только свой counter. Точный analytics.js hash совпал с принятым SDK report. |
| T106: настоящий SDK останавливается при локальном отзыве | Доказан конечный analytics-only профиль | Настоящий SDK с зафиксированным hash, реальные controller/CookieConsent,4 сценария `/`/`/download`×same/cross-tab: positive watch3/6, затем instance отсутствует и0attempts20s. Все HTTP/WS локально fulfilled/aborted/closed. Это не настоящий receiver/settings/replay/runtime. |
| T106: открытая вкладка видит отзыв глобального основания | Не закрыто | Browser publicConfig всё ещё snapshot из HTML. В controller нет запроса текущего server permission; fetch/sendBeacon относятся к отправке событий. Storage refresh не перечитывает серверный register. |
| T105: текущая внешняя published/provider copy и metadata receipt | Не закрыто нынешним выпуском | Проверка четырёх страниц31.10 нашла только stale configured revision, но свежая сверка реальных страниц, фактической revision и provider-facing copy на принятом режиме после выпуска здесь отсутствует. Новый SDK код не создаёт такой receipt. |
| T111: текущие policies/runbooks/provider settings соответствуют режиму | Частичный source результат; runtime не принят | Редакция2026-10-22.1 и until_decision раскрытия в source; прежние production replay=true и кабинет «все поля» не переоценены и не считаются выключенными. Полные T111/IP/provider policies этим узким review не принимаются. |

SDK report/read-only re-review содержат finite20s/analytics-only/local-backend
ограничения и scoped PASS0P1/P2/HIGH. Их нельзя превратить в доказательство
любого будущего момента, автономного replay SDK, реальных настроек Метрики,
глобального основания или индивидуального серверного принятия отзыва.
Более ранние HOLD о неисполненном destruct/отсутствии storage hooks больше
не описывают текущий код; перечисленные оставшиеся HOLD сохраняются.

## Что известно о рабочем сайте и что пока нельзя заключать

Из поручения владельца,01.11 09:41UTC: руководство200, DOCX39652bytes/
SHA256 `db3382c12973eaa95a4c1737094386c77a6c5877faf0e630cad914a5c4906692`,
analytics config/controller отсутствуют; каталог enabled=false,
provider_mode=disabled, rollout blocked. Эти наблюдения reviewer сетевыми
запросами не повторял. Они не доказывают отсутствие людей и не позволяют
выбрать единственную текущую причину отключения context.

Исторический диагноз31.10 established stale revision. Новый source добавил
ещё и readable basis gate, поэтому сейчас нельзя без нового безопасного
runtime snapshot утверждать, что нужна только смена даты. Каталог product
provider и public_analytics_* — разные настройки; выключенный product
provider не доказывает public replay=false или готовность внешней Метрики.
Settings default не является наблюдением runtime env.

Старый кабинетный Webvisor/«все поля» receipt31.10 сохраняется как открытый
риск соответствия. Analytics-only narrow scope может исключить replay;
тогда runtime flag и отправляемые init options должны это подтвердить,
а фактические кабинетные настройки всё равно сверяются с раскрытием F266.
Не требуется принимать IP writer, product PostHog/advertising upload либо
replay ради простых публичных просмотров. Их нельзя включить попутно.

## Конечный перечень оставшихся проверок

- [ ] **Текущее решение public, metadata-only.** При восстановленном доступе
  прочитать для `/` и `/download` только public flags/validation/env,
  configured и required revision, counter-present, replay flag и стабильный
  blocker code. Подтвердить readable valid register/no provider_analytics
  withdrawal без вывода пути, содержимого, visitor/IP/секретов. Сверить
  фактически отдаваемый controller/template с принятым release source.
- [ ] **Открытая вкладка и глобальное основание T106.** В существующей T106
  конкретизировать и независимо принять узкий механизм свежего разрешения
  для уже открытой страницы, затем причинные тесты withdrawal между render
  и send, unknown/error/timeout/stale permission, поздний positive/callback,
  resume/BFCache. Он должен учитывать уже работающий SDK, а не только новые
  вызовы GRAF. Маленький permission route или опрос сам по себе не доказывает
  отсутствие передач между проверками; заявленная граница нужна до кода.
  Пока внешний счётчик закрыт, этот инженерный срез можно выполнять локально.
- [ ] **T105/T111 для ровно принятого public режима.** Каноническим
  consent_copy_consistency сверить реальные `/analytics-consent`, `/cookies`,
  `/privacy`, `/terms` с опубликованными docs и фактической configured
  revision; получить metadata-only receipt без divergences. Отдельно сверить
  нужную provider-facing copy и параметры счётчика/F266, включая Webvisor,
  поля форм и автоматические функции. Source policy без runtime receipt
  не закрывает пункт; unknown replay не называть выключенным.
- [ ] **Зафиксировать узкую конфигурацию до применения.** Если принимается
  analytics-only на двух прежних страницах, подтвердить отсутствие replay/
  maps/form analytics и отсутствующих scopes в HTML/init/network. Product
  PostHog/offline/replay/IP остаются закрыты до своих gates. Ревизия
  согласия меняется только после принятия предыдущих прямых условий.
- [ ] **Реальный consent/SDK профиль на принятом backend/settings.** В чистом
  браузере: до выбора0optional; отказ сохраняется; явный analytics grant
  даёт ожидаемый просмотр; локальный и cross-tab revoke прекращают SDK и
  новые optional передачи; reload/resume не оживляют старый grant. Проверить
  `/` и `/download`, отсутствие external SDK на guide/auth/legal routes.
  Не заменять его уже пройденным локальным20s профилем. Перед реальной
  учебной отправкой в рабочий счётчик нужен явный допуск владельца.
- [ ] **Readback и исключение технического трафика.** Разрешённый технический
  просмотр должен появиться в правильном счётчике/отчёте, с проверенным
  временем/доменом и исключением своих проверок. HTTP202, tag load либо
  sdk init не являются readback. Зафиксировать начало подтверждённого
  публичного измерения отдельно от account T0; историю не достраивать.

Индивидуальный серверный отзыв и отказ повторному старому accepted payload
не доказаны новым локальным SDK профилем. Нельзя закрывать их в полной T106
или разрешать на этом основании relay/provider rollout. Если узкий public
срез не включает серверный приём такого отзыва и PostHog остаётся закрыт,
этот остаток сохраняет свой отдельный объём, не переименовывается в готовый.

## Следующая полезная работа без полного T113 и доступа к Mac

Продолжить второй пункт: маленький согласованный T106 срез свежего public
разрешения/остановки открытой вкладки и его причинные изолированные проверки.
Сначала scoped requirements/plan/checklist/analyze по текущему source,
затем independent review и минимальная реализация существующего приложения.
Это не требует нового marketing аккаунта, идентификатора посетителя,
аналитического хранилища, внешних отправок или повторного аудита ОС.
Параллельно можно сверить repository policy/runbook с analytics-only режимом;
фактический кабинет и live receipt честно остаются зависимыми от доступа.

Завершённый технический выпуск позволяет строить этот срез на стабильном
источнике. Full T113 с durable account milestones, T112/T0, регистрации,
новые записи/результат/оплата и продажи остаются отдельными. Public Метрика
не считает руководство через внешний SDK: оно идёт в first-party relay,
а при disabled PostHog подтверждённого guide visit/readback этим нет.
ProductRadar публикации и эффективность размещений здесь не принимаются.

## Действия reviewer и контрольные суммы

Прочитаны прежний diagnosis и T106 gate, exact-release code/functions,
SDK report/review/checklist, применимые T105/T106/T111 sections и canonical
consent consistency. Это узкая сверка, не новый полный audit. Runtime,
браузер/кабинет, SSH/sudo/секреты, API credentials, GitHub и сеть не трогались;
тесты/сборки не запускались. Locked Mac и metadata SEO tier=-1 не обходились.
Изменён только этот отчёт, чужие файлы/отметки checklist не менялись.

- Release `apps/server/src/twobrain_rec_server/public/static/public/analytics.js`: `2d05b53cd6087cfb80258687bc798e99d910bfde6249cadc4045ac444c08c0c1`.
- Release `apps/server/tests/browser/public-analytics-sdk-network.test.cjs`: `8e42c8d02b09e1e20485f6e119c2f01c030f5ee6a50f2b498e09d9417691571b`.
- Release `apps/server/src/twobrain_rec_server/public/analytics.py`: `c789fa7ab77ee5090c0542fd422fadab175e50a618c8d7229e10c34416d3694d`.
- Release `apps/server/src/twobrain_rec_server/public/web.py`: `d61c93bb74ae6b0f1bd193844a093985b9d85f25b11e9b4e78e01d3cf9ec19a3`.
- Release `apps/server/src/twobrain_rec_server/product_analytics/consent_copy.py`: `7ff18be6d41a2279cb196bf08170eef063f83bd71459264f8b4a6feb0b4c612d`.
- Release `specs/273-paid-traffic-analytics/validation/public-sdk-network-20261101.md`: `059547788980dad8e991f7227c3cf173964ecf9ef4a797be7c25c53706d5db60`.
- Release `specs/273-paid-traffic-analytics/validation/public-sdk-network-review-20261101.md`: `fa44ee3bde628c4d72ba0fa23f4a2e35c0458af1c0f673fcc256d50c3575d616`.


## Завершающее уточнение направления T106, 01.11.2026

Это уточнение заменяет рекомендацию раздела «Следующая полезная работа без
полного T113 и доступа к Mac» начинать с обновления разрешения открытой
вкладки. Предпочтительное минимальное направление — сохранить HOLD внешнего
SDK и завершать существующую отправку публичных событий через сервер.
Новый опрос браузером серверного разрешения для этого не нужен.

FR-048 требует прекращения обработки после отпадения основания, FR-049 —
прекращения дальнейшей передачи после отзыва. Проверка перед управляемым
ym-вызовом, короткий срок разрешения или уведомление по SSE не контролируют
самостоятельные HTTP-запросы уже загруженного SDK. Между серверным отзывом и
обнаружением его браузером остаётся окно передачи; недоступная или
приостановленная вкладка не даёт гарантии своевременной остановки. Эти
механизмы сами по себе не закрывают FR-048/049 или T106.

Обновление разрешения допустимо как отдельное частичное улучшение при
сохранённом HOLD: проверить, что после обнаружения запрета браузер блокирует
управляемые действия и вызывает destruct. Это не доказывает отсутствие
передач до обнаружения и не даёт основания включить SDK. Поэтому сейчас
такой опрос добавляет работу, сохраняя прежний блокирующий пробел.

Следующий узкий T106 следует направить на существующие приём события,
серверную проверку и отправку через PostHogClientWrapper, без автономного
браузерного SDK и без нового сервиса. Сохранить свежую проверку основания
при приёме и перед отправкой, а также независимый
resolve_provider_delivery_gate. Оставшийся проверяемый результат — после
принятого сервером индивидуального отзыва старое положительное содержимое
запроса и отложенное событие не дают новую передачу. Само поле
consent_state=accepted не доказывает актуального согласия. Проектирование
должно определить существующую границу приёма отзыва и устойчивый отказ
повторной передаче; готовность такой реализации этим отчётом не утверждается.
Это не требует нового опроса, инфраструктуры или аудита ОС и не означает
автоматического принятия всего T113 либо рабочего включения провайдера.
Внешний SDK остаётся закрыт до отдельного доказательства его границы.

### Переданный рабочий снимок — наблюдение основного агента

Основной агент передал конечный metadata-only снимок штатным read-only
docker compose exec rec-api: env=production, public_enabled=true,
validation=disabled, replay_enabled=true; configured revision=2026-08-13.1,
required revision=2026-10-22.1. Для / и /download поля enabled,
consent_ui_enabled, external_counter_allowed и replay_allowed равны false;
blocker=consent_revision_mismatch, counter_present=true.
read_basis_withdrawal_register сообщает available=false,
file_errors=false, provider_analytics_withdrawn=false. Последнее не означает
валидное отсутствие отзывов: реестр недоступен. После одной смены редакции
согласия следующей преградой останется public_basis_unavailable; сохранённый
replay_enabled=true нельзя представлять как выключенный режим replay.

Reviewer самостоятельно этот рабочий снимок не получал и сеть не повторял.
В рамках завершающего уточнения прочитаны только требования и существующие
серверные границы в рабочей копии основного агента; изменён только этот
отчёт. Код, spec/plan/tasks, checklist, Git и рабочая конфигурация не менялись;
тесты, сетевые действия и привилегированная инвентаризация не выполнялись.
