# T112 — сохранение выбора показанного результата

Дата:16.11.2026. Основа:a3ff5b8709dc5da61f4751c4eb3145eb84d9fc9e.
Полоса:существующий `high-risk-product`, T112/#7698. Не новый feature,
не приёмка полной T112/T113 и не включение измерения.

## Изменение и причина

Общий observer раньше строил POST из одного pathname и терял выбранную
проекцию. Browser detail GET выбирает `summary_format` и `source_result_id`,
desktop GET — только `summary_format`. Новый target переносит ровно эти
действующие параметры соответствующей поверхности. Desktop не начинает
применять проигнорированный его GET `source_result_id`.

Выбирается последнее значение каждого ключа, как Starlette QueryParams.get,
включая пустое последнее значение. Кодирование проходит через URLSearchParams.
Путь остаётся canonical собственным detail/result-viewed; proof только в JSON.
Посторонние параметры и fragment в новый target не попадают. Полный исходный
query по-прежнему проверяется после ожиданий и не создаёт нового перехода
видимости или автоматического повтора.

Выбор согласован с независимым server preflight и его разрешением отдельной
клиентской правки до рабочего T113. Применён минимальный вариант desktop,
сохраняющий семантику продукта. Сам proof и его binding не меняются.
Область: общий JS, его существующая browser fixture, собственный changelog
и этот отчёт. Серверные routes, ingest, auth и настройки пока не изменены.

## Выполненные проверки

Причинный RED до JS зафиксирован в
`graf-t112-view-selectors-red-20261116.log`: target имел пустую query вместо
выбранных двух ключей. Предыдущий GREEN16/1/0 дополнен окончательным
профилем: **16 passed,1 прежний fixture warning,0 skips,28.16s,EXIT0**.
В профиль входят оба настоящих движка Chromium/WebKit и14 прежних detail
контрактов. Endpoint в browser fixture синтетический, возвращает fake accepted;
это не доказательство серверного durable admission.

Новые10 случаев на каждый движок: каждый параметр отдельно, оба вместе,
дубли с последним значением, пустое последнее значение, UTF-8/спецсимволы,
исключение proof/UTM/других query/fragment и три desktop варианта.
Проверены pathname, точная query, отсутствие fragment и точное JSON-тело.
Существующие native freshness/no retry случаи сохранились.

Команда из корня этой копии:

```sh
PYTHONPATH="$PWD/apps/server/src:$PWD/apps/server" \
GRAF_NODE_MODULES=/Users/yshishenya/Documents/crisp/apps/server/tests/browser/node_modules \
UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
UV_NO_SYNC=1 uv run --project apps/server pytest \
  apps/server/tests/contract/test_result_visibility_observer.py \
  apps/server/tests/contract/test_meeting_detail_reference_contract.py -q --tb=short
```

Оба `node --check` и `git diff --check` PASS. Swift не менялся, прежний
завершённый69-test профиль не повторялся. БД, runtime, сайт, почта и
инфраструктура не проверялись и не менялись. Контент/вёрстка не редактировались.

| Материал | SHA-256 |
| --- | --- |
| cabinet.js | 7a5215a4794ff01c0662da0953a3f4e79248101008b8e4d558f88ecfb8f9c609 |
| browser/result-visibility.test.cjs | bd9f812fa15bdb33f0ec4f46f8654dde113e85a260e451831a5c960aa05c27ce |
| graf-t112-view-selectors-final-20261116.log | 919497704ab14ba36e2813bff9d7a756da90bb0e5c1c174a7012ea86110e5136 |

Журнал хранится в локальном временном каталоге; содержит только результат
синтетических проверок. Независимое [ревью этой правки](t112-view-selectors-review-20261116.md)
завершено: **PASS,P1=0,P2=0**, два точных кодовых хеша совпали; reviewer
прочитал окончательный журнал, не повторяя тесты. Прежние13/13 документов
совпали, требования124/0 без изменения отметок. Это приёмка только данной
клиентской правки, не серверной части или полного измерения.

## Согласование и остаток

Requirements/analyze/issue mapping не заменяются новым маленьким пунктом:
FR-021/025,SC-006 и открытые T112/T113 остаются прежними. Новый серверный
проект и независимый preflight сохранены отдельно; server-кода пока нет.
Следует реализовать общий внутренний admission в ingest, fresh auth/source/
projection fences, issuance/renewal, один ограниченный POST и атомарную пару,
затем выполнить причинную DB/failure/concurrency приёмку и exact-SHA gates.
Настоящий T113 context отсутствует: отключённый сбор и
activation_recovery_unverified сохраняются. Нет T0, новых публикаций,
визитов/регистраций/оплат, подтверждённых этим изменением.
