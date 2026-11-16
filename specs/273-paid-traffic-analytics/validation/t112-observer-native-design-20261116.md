# T112 — уточнение интерфейсов observer/native до кода

Дата:16.11.2026. Основа `13edb699c1cee3c9b40808b44d3d8d3b0ba01852`.
Полоса `high-risk-product`, существующие FR-021/025/SC-006 и T112/#7698.
Это инженерное уточнение принятого договора §§4–5, не новый продуктовый
объём, получатель, разрешение включения или отдельная задача.

## Решение и проверка согласованности

После [независимого preflight](t112-observer-native-preflight-20261116.md)
в договор добавлены точные закрытые формы native и POST. Native возвращает
только готовность текущей поверхности, не proof/identity. Точный canonical
owned detail path исключает shared/public/action routes, которые существующий
route policy также относит к meetingDetail. Итоговое session generation
фиксируется после cookie reconciliation. Неизменное положительное refresh
и смена nonce сами по себе не создают новый переход видимости после ошибки.

POST accepted допустим только после подтверждённого общего durable решения;
renewed не принимает веху и требует нового frame/native наблюдения с одним
обновлением на настоящий переход. Unknown/extra/malformed/redirect/transport
не становятся успехом. Серверный путь и trusted T113 этим шагом не подключаются.

Проверка соответствия исходному scoped analyze:

| Требование | Уточнение и причинное покрытие |
| --- | --- |
| FR-021 | Browser body/viewport/focus/visible + точный current native document/foreground; исключены GET/poll/heading/hidden/stale/shared |
| FR-025 | Только закрытый durable accepted прекращает попытки блока; no timer retry, ограниченное renewal и повторная проверка после async |
| SC-006 | Одинаковая browser/embedded семантика; старый клиент без native проверки продолжает просмотр без нового счёта |

CRITICAL=0,HIGH=0,MEDIUM=0,blocking clarification=0 в изменившемся срезе.
Spec/plan/tasks/quickstart и остальные требования не меняются; T112 остаётся
открытой. Существующая issue mapping #7698 сохраняется, дублей/внешних
комментариев нет. Constitution II/III/IV/VI/VII сохраняет прежние ограничения
сбора, содержимого, lifecycle, качества и оформления. Новое независимое
подтверждение изменённого договора нужно до зависящего кода.

## Запланированная реализация и пределы

Общий observer добавляется в существующий cabinet.js: только разрешённые
body с bounded proof, IO/DOM/ancestor/geometry/visible/focus/not-prerender,
double RAF, cleanup HTMX/detached и свежие root/proof/CSRF/path проверки
после каждого ожидания. Same-origin POST содержит только proof, без redirect;
таймер допускается только для ограниченной отмены, не повторной отправки.
Неизвестный исход ждёт нового настоящего перехода, не native refresh/nonce.
Размер ответа также ограничен. Рабочие маршруты пока не выдают proof.

Новый узкий WK handler использует существующий main-frame/origin/session
образец, coordinator activation после cookie reconciliation и invalidation
на navigation/detach/termination/auth. AppKit foreground читается на MainActor;
native не пишет аналитику и не вызывает сеть. Тесты — синтетический browser,
policy/lifecycle и настоящий WK bridge, без ручной установки приложения.
Ручная приёмка остаётся единственному GRAF Dev через штатный dev-harness.

Первый browser RED: нет POST при показанном непустом теле, ожидалось1,
получено0; runner session5495 завершился EXIT1. Это отсутствие observer,
не доказательство какого-либо дефекта рабочего измерения, которого ещё нет.
Тесты production/T113/readiness/DB admission ещё не выполнялись.

Точный изменённый договор: SHA-256
`ee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8`.
Прочая принятая история и неизменные14/14 входов до этого уточнения проверены
существующим reviewer; после уточнения требуется проверить13 прежних входов
и один новый договор, а не выдавать прежний общий digest за актуальный.
