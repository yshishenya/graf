# T106 — независимое ревью регрессий полного прогона

Дата: 01.11.2026. Рецензент: `/root/public_counter_readiness_review`.
Рабочая копия: `/Users/yshishenya/.codex/worktrees/growth-protocol-result/crisp`.
Ветка прочитана: `codex/f273-consent-contracts-20261101`.
HEAD прочитан: `ad65b8f5dbbe8ff1ccceb998823e1ded203af965`.
Проверяется незакоммиченный срез, а не предыдущий metadata PR.

## Решение и границы

**PASS реализации проверенного среза. P1: 0; P2: 0; CRITICAL/HIGH: 0/0.**
Дополнительной обязательной реализации для перечисленных регрессий не найдено.
Действующие требования публичного выбора не расширяются и не ослабляются.
Checklist перечитан полностью: **6 checked / 0 unchecked**, не менялся.
Прежний analyze C/H/M0 передан основным исполнителем; новый общий analyze
всей F273 данным отчётом не заявляется.

Полный T106/T113, рабочее измерение, внешний SDK/replay, T0, выпуск и
коммерческие результаты остаются открытыми. Нужны точные PR-проверки нового
исходного SHA, защищённое слияние и новый замороженный кандидат с успешным
авторитетным Full и прежними условиями CD. Старый Full41311924603 не принят.

## Исходный отказ и проверенный состав

Прочитан сохранённый итог Full41311924603:
`/private/tmp/graf-release-20261031.m9mTRg/.dev/release/v2-full-final-status-20261101.json`.
Он фиксирует completed/failure на source9605d293, пять неуспешных
PostgreSQL shards и неуспешный итоговый агрегатор; static/governance,
macOS и strict/performance завершились успешно. Сеть/Actions в этом проходе
не вызывались. Число десять конкретных отказов и их распределение взято из
диагностики исполнителя `/private/tmp/graf-t106-full-failure-scope-20261101.md`,
а не из самостоятельно прочитанного полного журнала каждого shard.

Полный текущий `git diff` прочитан: шаблон auth, три контрактных теста,
интеграционный модуль страниц и учебная retention-модель provider smoke.
Дополнительно целиком прочитан новый `changes/unreleased/F273.yaml`.
Схема БД, API, consent controller, поставщики, рабочие настройки и права
не меняются. Fragment точно описывает этот объём и сохраняет открытые gates.

## Причина и все пути загрузки

Поиск всех loader/config мест в серверных HTML/Python выявил четыре
самостоятельных места: публичный `_analytics.html`, кабинетный `base.html`,
вложенный `cabinet/auth/analytics.html` и административный `admin/base.html`.
Прочитаны эти шаблоны, построители публичного/продуктового контекста,
`auth_rendering.py` и места передачи контекстов в auth routes.

`render_login_page`, `render_signup_page` и `render_email_code_page` передают
имеющиеся контексты в общий `_standalone_page` → `cabinet/base.html` с
surface_mode=auth. Именно здесь при активном product provider общий base
добавлял CookieConsent/analytics.js, а вложенный auth partial добавлял их
повторно. Ошибка относится к общему шаблону, поэтому исправление действует
также на другие auth-renderings, использующие тот же partial; их существующий
набор передаваемых контекстов не меняется.

Текущая правка повторяет **тот же** predicate enabled, что и родительский
base. При его истине библиотека и controller приходят из base, а public JSON,
legal/footer, status role=status/aria-live и retry остаются во вложенном
шаблоне. При ложном/отсутствующем product provider скрипты приходят из auth
partial. Если public context отсутствует, прежний product-only путь base
не меняется. Публичный и административный шаблоны не включают этот auth
partial и сохраняют свои прежние пути загрузки.

Все затронутые внешние скрипты имеют `defer`: controller запускается после
разбора документа и видит оба JSON-блока, даже когда public JSON находится
после product loader. Прочитан controller: он получает оба блока через
getElementById, отдаёт приоритет public config, использует серверный public
control и не подменяет его product-only выбором. Старый глобальный guard
controller сам по себе не устранял повторную загрузку библиотеки; новая
проверка устраняет причину на уровне выдаваемого HTML.

## Соответствие изменениям договора и проверок

| Изменение | Вывод по прочитанному коду |
| --- | --- |
| Default-render test | Прежнее отсутствие control UI заменено разбором настоящего JSON: consent_ui_enabled=true, enabled=false, external_counter_allowed=false, replay_allowed=false и counter ID=None. Это соответствует обязательной доступности отказа при выключенном измерении и сохраняет запрет необязательной отправки. |
| Webmaster parameters | Проверка точного verification meta/его расположения и запрета чужого host сохранена. Добавлен разбор публичного JSON с теми же выключенными provider flags; внешнего адреса Метрики в HTML по-прежнему нет. Отсутствие интерфейса отказа больше не служит ошибочным признаком отключённой аналитики. |
| FR-058 | Тест выполняет настоящие POST revoke→grant с точным Origin, случайным consent_id и epoch принятого revoke. Состояние customized соответствует выбранным necessary+analytics; relay получает действительный consent_epoch. Проверки202, отсутствия доставки, доступности двух страниц и ровно двух обезличенных просмотров сохранены. Отказ поставщика больше не смешивается с403 от отсутствующего серверного выбора. |
| Provider smoke | Добавлена только уже обязательная пятая категория public_consent_control с until_decision, no age сроком и decision_required. Список совпадает с REQUIRED_RETENTION_TERMS и штатным retention-script. Учебные файлы остаются во TemporaryDirectory, а реальный collector по-прежнему должен отвергать самозаявленное restore-подтверждение. |
| Integration | При активном product provider login/signup требуют ровно один analytics.js и CookieConsent при сохранённых двух config/control частях. Новый product-disabled/public-disabled сценарий требует отсутствие product config, ровно один набор скриптов и сохранённые public config/status. Прежние проверки публичных, кабинетных, desktop и admin страниц, identity и masking сохранены. |

Отдельно прочитаны две группы provider-smoke contracts и хвост smoke:
check_restore_blocked исполняется до и после учебного transport; до transport
ожидается0 вызовов, после — ровно один на получателя. Исключение
restore_consistent действует только внутри patch в учебном процессе.
Проверка без сети и output-маркеры synthetic_test_process_only,
restore_gate=blocked_before_and_after_transport_test, product_rollout=blocked
и campaign_launch=blocked сохраняются. Добавление retention-категории не
создаёт настоящего подтверждения восстановления и не включает поставщиков.

Договор `contracts/public-consent-control.md` прочитан целиком; его SHA-256
совпадает с прежней приёмкой. Требования FR-058/059 перечитаны. Сохранены
отдельный контроль отказа, новое явное действие revoke→grant, запрет фонового
grant, fail-closed и доступность интерфейса при выключенном измерении.

## Прочитанные локальные доказательства

- `/private/tmp/graf-t106-v2-regressions-20261101.txt`: **56 passed**, два
  предупреждения, 37.82s; isolated PostgreSQL cleanup подтверждён. Этот прогон
  был до добавления одного нового product-disabled integration test.
- `/private/tmp/graf-t106-autocapture-final-20261101.txt`: полный актуальный
  интеграционный модуль после этого добавления — **4 passed**, два
  предупреждения, 9.41s; isolated container removed. Новый сценарий явно
  присутствует в duration list.

Эти прогоны пересекаются; их количества не суммируются как60 разных тестов.
Они не являются новым авторитетным Full. Тесты рецензент не повторял.

## SHA-256 проверенного среза

```text
ba23ae026d7b9a448b7873956200f8446ccca6744b4f81735fb65345af8df22d  cabinet/templates/cabinet/auth/analytics.html
e5b6fd8b8bdcddafbf8bc5007d90fd509562cd5799f11efd19b202f07e253726  cabinet/templates/cabinet/base.html
7df8e31fe61bceef93d5911ed768700ff987c78fec027a4bc9185ccba9ab8ce4  public/static/public/analytics.js
385ac6bf3457f3ceabf3f23d3b48321f975d32a61c299455f6944b53212b36a0  tests/contract/test_product_analytics_measurement_contract.py
2bdbafaa492c2c2fe63b49a1058bbd957cbd822038ccecab9f7dc491eb70c4cc  tests/contract/test_public_traffic_measurement_contract.py
2fd2b71690d7596e69659e9ab51a84d11998c35effc9be922f85f2e44e383baf  tests/contract/test_public_yandex_webmaster_verification.py
a60fac0feb81a34f168c49331756f64243631ac17a08999625fd6dff35c426c7  tests/integration/test_product_analytics_autocapture_pages.py
d1e5688726bd6569fea5e01f6f791e705f1de0035de4584b1734e86a0a4cf455  infra/scripts/run-product-analytics-provider-smoke.sh
f8fdbd23210bc93e6ff6f746a5147fbbbb82575ac1a9e8d5f88f9c1a7cba7b89  changes/unreleased/F273.yaml
2bb000b982db96230c75d97037d85e91a3dd02ad7a24f5d892e42b08304e8f3e  contracts/public-consent-control.md
c40a0091d8180227fcce932a8226f249bd288d6509b21edb25a0fa2317829c48  checklists/public-consent-control.md
b56fe49b5296421c01eedfda075d275a31734e32b21f5407130dc9a2f87fdcc9  /private/tmp/graf-t106-v2-regressions-20261101.txt
7e04e6655dbc543f1f5a7e5892bbcdfce6111fc793420517dee4da702c8e5b96  /private/tmp/graf-t106-autocapture-final-20261101.txt
```

Пути cabinet/public относятся к `apps/server/src/twobrain_rec_server`,
tests — к `apps/server`, contracts/checklists — к этой F273.
Изменён только настоящий новый отчёт. Код, checklist, requirements,
plan/tasks, Git/GitHub, release и рабочие настройки не менялись; новых
агентов и тестовых прогонов не создавал. Отчёт подлежит полному чтению
после записи и перед передачей его контрольной суммы.
