# T112 — общий владелец транзакции и согласованная пара

Дата:16.11.2026. Основа:46c989b959856c836ab0c2fc5ef0aeb255992a07.
Полоса:существующий `high-risk-product` F273/T112,T113. Это следующий
серверный подшаг принятого проекта, не закрытие полного защищённого входа.

## Реализованный объём

В `product_analytics/ingest.py` выделены общие `_account_transaction`, свежая
проверка admission и вызов существующего `admit_account_milestone`.
Прежний `ingest_authenticated` использует того же владельца commit и те же
правила получателей. Его формы, возвраты accepted/duplicate и отказы
trigger_unverified для обоих result/value имён сохранены.

Внутренний `admit_result_view` вызывает переданный серверный verifier только
внутри этой границы и под shared active identity lock. Принимается только
согласованный owner/workspace/session/device binding. Сами проверки свежей
сессии, членства, Meeting/source locks и proof должны выполняться будущим
verifier в той же DB-сессии. Этот callback — программный внутренний интерфейс;
JSON, query, header и settings не могут задать его или разрешение периода.

Для валидного binding переиспользуются прежние два построителя; каждая запись
проходит свежий gate. Оба INSERT и прежние намерения доставки принадлежат одной
транзакции и одному commit. True возвращается только после подтверждённого
commit. Сбой/unknown возвращает False без повтора. Прежние account+event keys,
payload и source_kind уже существовавшего решения не переписываются.
Общий callback readiness повторяется и перед commit, после обеих записей.

Источник `_result_period_context` в настоящем коде всегда возвращает отсутствие
контекста. Дата/снимок/флаг готовности не добавлены; legal gate по-прежнему
включает activation_recovery_unverified. Substitute в тесте передаёт только
синтетический started_at, отдельную disposable DB-сессию и её локальный guard.
Он не реализует filesystem/DB T113 fences, recovery или рабочий local_only.

Новая ветвь ставит lock_timeout250ms/statement_timeout500ms. Внешний предел
2s включает выход контекста; для SQL/verifier/commit выделено1.5s, остальное
оставлено на завершение соединения. Настоящий вход тела HTTP пока отсутствует;
его будущий общий бюджет должен охватывать тело и этот вызов. Тесты измеряют
закрытие обычного disposable asyncpg контекста; все возможные ошибки драйвера,
пула и очистки пока не принимаются как проверенные.

## Реальные проверки

Первый корректный RED входа: отсутствовал `admit_result_view`, AttributeError,
1failed/1warning; изолированный контейнер удалён. Предыдущая ошибочная команда
с относительным `apps/server/tests/...` из runner не собрала тесты и RED
продукта не является. Во время реализации исправлена ошибка fixture:
keyword-only review по ошибке передавался позиционно; это тоже не отказ продукта.

Промежуточный профиль20PASS, затем расширенный105PASS. После изменения
резерва времени и проверки прежнего first-result итоговый точный профиль:
**106passed,1 прежнее предупреждение,0skips,87.80s,EXIT0**;
runner91s,collection106,digest
`4b9cab7982c566be54413acce3d27c63c0ff17acc355b21f92f388fba095530d`.

Новые проверки охватывают:

- Настоящий источник контекста закрыт даже при подставленном legal gate;
  verifier не вызывается, строк нет. Unknown/naive/future started_at и отсутствие
  guard также не запускают verifier.
- Обе поверхности, proven manual_upload=false и неизвестный per-record capture
  без свойства; unknown attribution, без текста/proof/частных ссылок в payload.
- Replay и две независимые DB-сессии дают одну пару. Прежний first-result
  другого показа остаётся неизменным при добавлении first-value.
- Сбой второго INSERT, отзыв между INSERT, отказ commit и отзыв контекста
  после пары откатывают весь новый набор.
- Потеря подтверждения уже выполненного commit возвращает отказ без retry;
  следующий отдельный вызов разрешает прежние keys без переписывания.
- Чужие owner/workspace/session/device bindings не записываются. Занятый
  identity lock отказывает ограниченно; закрытый аккаунт не запускает verifier.
- Медленный verifier отменён и завершён в пределах2s; явная отмена вызывающего
  распространяется, verifier завершается и строк не остаётся.

В новых DB-сценариях callback использует настоящие source/binding/proof helpers
и синтетическую projection fixture. Авторизация сессии не выдумывается:
session UUID привязан синтетически; тест **не доказывает** fresh session,
membership/device locks, HTTP/CSRF, действительный показ или end-to-end T113.
Их остаётся реализовать следующим серверным шагом.

Регрессии: существующие ingress,ledger,delivery и unit funnel/campaign labels.
No-provider транспорт прежнего isolated_admission fixture запрещён;
новый путь вызывает только SQL и прежние локальные delivery decisions,
не transport. Настройки рабочей аналитики/провайдеров не менялись.

```sh
PYTHONPATH="$PWD/apps/server/src:$PWD/apps/server" \
UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
UV_NO_SYNC=1 GRAF_TEST_WORKERS=1 /opt/homebrew/bin/bash \
  apps/server/scripts/run_local_postgres_tests.sh --focused \
  "$PWD/apps/server/tests/contract/test_result_view_admission.py" \
  "$PWD/apps/server/tests/contract/test_activation_milestone_ingress.py" \
  "$PWD/apps/server/tests/contract/test_activation_milestone_ledger.py" \
  "$PWD/apps/server/tests/contract/test_activation_milestone_delivery.py" \
  "$PWD/apps/server/tests/unit/test_product_analytics_activation_funnel.py" \
  "$PWD/apps/server/tests/unit/test_product_analytics_conversion_campaign_labels.py" \
  -q --tb=short
```

Ruff/diff PASS. Runner удалил только свой disposable контейнер. Перед тестами
свободно165975572KiB, выше80ГБ. Mac-приложения, Swift/browser, production,
приватные встречи, почта/очереди, backup/restore и внешние публикации не трогались.
Единственный ошибочный wait с несуществующим cell не являлся диагностикой или
ожиданием; действительные runner sessions проверялись через write_stdin.

## Ревью, согласованность и остаток

Получено [независимое ревью](t112-account-pair-review-20261116.md):
**PASS изолированного подшага общей транзакции и атомарной пары, P1=0, P2=0**.
Ревью сверило окончательные кодовые хеши и журнал106PASS; полный свежий
verifier, HTTP-путь, выдача/обновление proof и рабочая T113 этим не приняты. Отдельное
[исследование writer fences](t112-server-writer-fences-review-20261116.md)
установило применимую точку Meeting FOR UPDATE и опасность helpers с внутренним
commit; это чтение существующего кода, не тест будущего verifier.

12 прежних requirements/analyze/checklist документов совпали с принятой
основой503805cb6188f942adb159ea2bab8560969b7b0e; отдельно договор равен
принятому observer уточнениюee1005b6a59ad1b42f0b7d0af25dd7099c8337a4d11930a3aba9ee6479d270d8.
Контрольные списки16/0+27/0+52/0+29/0=124/0, без изменения отметок.
Применимые ограничения и source восстановлены по оригиналам; неизменные
исторические требования не переоцениваются как новое выполненное поведение.
FR-021/025,SC-006,T112/#7698 и T113/#7804 остаются прежними и открытыми.

Далее: реализовать actual свежий auth/source/projection verifier под принятыми
locks, выдачу/обновление proof без INSERT и общий bounded POST обоих alias;
подключить callers и проверить mutation-first/analytics-first, HTTP/CSRF,
GET/HTMX, expiry/renewal и полный2s бюджет. Настоящий T113 context отсутствует.
Рабочий сбор, неизменяемый T0, три Product Radar сообщения и коммерческие AC
не приняты. PR/merge/CI/Full/CD/выпуска этого нового среза нет.

| Материал | SHA-256 |
| --- | --- |
| product_analytics/ingest.py | 78b6a0e90c4effe516385768fdcd73d9b6ae47a233cf33bb834a742b06c5e150 |
| tests/contract/test_result_view_admission.py | 2f5cb12ac816f849b9ce1b3a63e4d653636106c39b8db8efe1e61438de63dd6e |
| graf-t112-account-pair-final-20261116.log | 0a0cc016b911272ee9fdd7061efd5de1b1a4487141cec7370aa4441d456332fd |
