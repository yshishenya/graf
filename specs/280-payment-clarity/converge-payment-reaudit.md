# F280 — сверка текущей реализации повторного среза

2026-10-16. Сверены действующие spec/plan/tasks, constitution, product implementation и новые проверки FR053–055/SC018. Полоса high-risk-product, затем release-deploy. Prerequisite script поддерживает --require-tasks/--include-tasks; предложенный навыком --require-spec не поддержан, проверка spec выполнена явным чтением. Before/after converge hooks отсутствуют. Новых задач не добавлено: незавершенная работа уже явно представлена T065 и прежними T011/T012.

| Требование | Текущая реализация и доказательство | Остаток |
|---|---|---|
| FR053 / T062 | Общий hosted predicate и tenant-scoped recovery во всех callers; causal HTTP/PG RED→GREEN289. Legacy no-provider, actor/flags, missing/foreign/mismatch/terminal, сохраненные суммы и отсутствие нового create покрыты. | Полный дополнительный sibling набор250 PASS; затем exact PR gates |
| FR054 / T063 | invoice.succeeded требуется для paid receipt notice; forged query негативные состояния и paid service_gap проверены. | Exact PR gates |
| FR055 / T064 | Native hidden до binding, ручное выделение и fallback focus; Chromium59/WebKit20 полный PASS,78страниц и прежние темы/ширины/масштаб/клавиатура. | Exact PR gates |
| T065 / технический выпуск | Независимые requirements127/0 и source/browser review, собственный fragment, validation report. | PR, актуальные3gates, обычное слияние, один frozen release-full и штатный CD общего оператора, live сверка |
| T011 / T012 / SC005/006 / F278 | Прежние открытые отдельные критерии не заменены synthetic tests. | Установленный GRAF Dev, участники и измерения, банк/возврат/реальное продление; принадлежат existing tasks/issues |

Новых API, денег, таблиц, миграций, зависимостей или сторонних активов нет. Предвыбор оферты/необязательного автопродления, плотность и финансовые guards сохранены. Применимых незапланированных исправимых разрывов текущего среза не обнаружено. SC018 требует выпуска: до фактического доказательства T065 остается открытой.
