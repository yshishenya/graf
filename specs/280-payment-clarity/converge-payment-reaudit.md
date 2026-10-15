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

После первого PR governance-fast выявлен разрыв в старом money-path ожидании: terminal replay требовал hosted URL вопреки FR053. Причинный повтор дал6failed; исправлена только итоговая проверка Location после двух succeeded состояний. Полный файл71passed/0skipped за48.80с; pending hosted replay и все финансовые проверки сохранены, product bytes прежние. Этот тест уже включен в quickstart. Новый SHA и новые exact PR gates обязательны; первый failed run не является допуском.

Дополнение оператора выпуска: новые exact-SHA gates и общий валидатор для head `698ebfa5202986f1a681fd46eb4f12e505352ded` прошли; PR #7606 штатно объединен в `e8d85cabc1246e1774b0af0b385d8e3a61fda237`. Реализация T062–T064 подтверждена, отметка T062 согласована с доказательствами. Прежние записи об ожидании PR gates выше исторические. Остаток T065 — один общий замороженный выпуск, его полная проверка и выкатка. Частичная установленная проверка GRAF Dev на тех же байтах не закрывает оставшиеся сценарии T011; T012 и финансовая приемка также учитываются отдельно. Новых задач или изменений требований не требуется.
