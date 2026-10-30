# F273/T113: независимое ревью календарной поправки UTC

Дата: 30.10.2026. Проверяющий: `/root/f273_release_boundary`.
Рабочая копия `growth-guide-previews/crisp`, ветка
`codex/f273-local-period-20261029`, основа
`df0d0de932cdd9a164ff4ab46fb60d9621ca66b0`. T113/#7804,
`high-risk-product`. Проверен конечный незакоммиченный diff и замороженные
входы, а не будущий commit/PR или установленная версия.

## Решение

**SCOPED CODE REVIEW PASS. Открытых P1:0, P2:0.**
Конечная реализация соответствует
[проектному гейту](t113-schedule-design-review-20261030.md), SHA-256
`c12d2e661a437b01a006b74ce55fb33cfcbdca9949071a70b18fa71095896b6c`,
и precode `f3ab2420e137ee5522d86a6d916b7e656cf761ddfe953d207565e732c812ff35`.
Все **22/22** входа frozen inventory независимо пересчитаны и совпали;
его SHA-256:
`75c371fd8d2eef6a1a56e36644317ca5007f7f086258e77371d7b9c4c9ef4568`.
Контрольные списки перечитаны: **117 checked / 0 unchecked**.

## Изменение и соответствие требованиям

Прочитан весь diff десяти tracked-файлов и полный новый отчёт исполнителя
[t113-schedule-20261030.md](t113-schedule-20261030.md).
Три timer содержат по одной исходной OnCalendar; единственное изменение
каждого — суффикс ` UTC`:

| Timer | Полная строка |
| --- | --- |
| graf-posthog-backup.timer | `OnCalendar=*-*-* 02:30:00 UTC` |
| graf-posthog-restore-verify.timer | `OnCalendar=*-*-01,15 04:30:00 UTC` |
| graf-posthog-retention-enforce.timer | `OnCalendar=*-*-* 03:15:00 UTC` |

Persistent, Unit, Install и описания сохранены. Нет изменения монотонных
timers, service/helpers, системной зоны, прав, состояния или алгоритма данных.
Существующий contract независимо закрепляет нужные часы/даты и теперь ищет
строку в `timer.splitlines()`, поэтому произвольный хвост больше не принимается.
Проверки persistent/install и двух alert-служб сохранены.

Таблица и пояснение runbook согласованы с source: календарь явно UTC,
глобальная зона сервера сохраняется. Неблокирующее предложение предыдущего
ревью выполнено: в таблице backup-restore тоже явно написано UTC. Договор
ежедневной проверки03:15UTC из operations теперь соблюдён исходным выражением.
Пределы свежести26ч/30дней, until_decision, отдельное удаление и границы
исторического v1 restore не меняются. Прогресс plan/tasks/quickstart/fragment
правдиво оставляет installed-jobs, верхний оператор и T113 открытыми.

Карта девяти применимых FR/SC и существующих задач из проектного ревью
остаётся действительной: FR-033/034/035/036/038/050/051, SC-010/011.
Новых противоречий spec/plan/tasks или конституции не найдено. Никакие
рабочие ограничения не ослаблены ради прохождения профиля.

## Прочитанное доказательство исправления

Полностью прочитаны неизменная source-reading native probe, отдельный RED
и конечный native-журнал. Они связаны frozen inventory; probe получает
выражения непосредственно из трёх source timers, не из ожидаемых литералов.
Ожидаемые часы отдельно задаёт contract. Проверяющий probe/SSH не запускал.

RED содержит6 failed-групп старых календарей: результаты зависят от локальной
зоны; весеннее копирование пропускает29марта2026. Конечный журнал содержит
те же6 сочетаний трёх календарей и двух base-time, по две локальные зоны
и четыре момента: **48 результатов**, все попарно равны в UTC. Часы
02:30/04:30/03:15 и дни1/15 соответствуют source;29марта присутствует.
Число групп/моментов и равенство полных массивов независимо пересчитаны
из JSON журнала; финальная строка `native_calendar_result=pass`.
Исправление причинно связано с единственным изменением UTC suffix;
вычисление дат не является запуском задания или доказательством установки.

Контрактный журнал прочитан полностью: **222 passed, 2 warnings, 82.15s**,
без skipped/failed. Исполнитель фиксирует два полных модуля:
`test_analytics_degradation_alerting.py` и
`test_analytics_retention_enforcement.py`. Два предупреждения — импорт fixture
до pytest rewrite и существующая Starlette/httpx deprecation.
Локальный reviewer не выполнял повторный pytest и не выдаёт это за GitHub CI.

Полностью прочитаны отдельные статические журналы:
Ruff `All checks passed!`; governance/bootstrap `OK`; development-process
с agent-context/changelog/legacy-impact `OK`; fragments `OK`.
Журнал ссылок: `local_markdown_links=79 errors=[]`.
Проверяющий отдельно выполнил read-only `git diff --check`: exit0, вывода нет.
Прочтение журналов не означает повторного запуска этих проверок reviewer.

## Контрольные суммы доказательств

| Вход | SHA-256 |
| --- | --- |
| native probe | `acb248c668bae2f96c32a0860828165cf36216c0976445329f303bc1e6ed611f` |
| native RED | `f86cc4ad90f6b1ce8ecae8aa88e6a13e2ccf0c8cf63b07a3cfb9c6f1d30695df` |
| native final | `90818406e4468eff148dc6e104cf058665869fa66639346e1d2fb71140b2912c` |
| contract final | `26a3303ad4ec3e10730ad6bbdf646800139eb712a57d8d5c013ae1b1be67dbac` |
| основной отчёт | `e30de1732f74ff59b917fe23d0f6f32a0b00cf0b2e23b95c9dabc1d473098195` |

Конечные source/test/docs и все статические журналы перечислены в
`.dev/growth/t113-schedule-final-hashes-20261030.json`; полный набор22/22
совпадает, отсутствующих или изменившихся входов нет. Сам этот новый отчёт
в исходный frozen inventory не входит.

## Контрольные списки и повторное чтение

Все117 вопросов перечитаны в этом code review, counts и SHA пересчитаны.
Новых неподтверждённых требований эта правка не создаёт. Отметки не менялись.

| Список | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | --- |
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Отметки относятся к качеству требований, не к полному выполнению задач.
Прежние constitution/PRD/status/product-gates/spec/operations/data-model
проверены по SHA и совпали с проектным гейтом; применено прежнее исключение
F273 повторного чтения. Полные затронутые разделы runbook Scheduled Backup,
Restore Verification, And Retention с подготовкой группы и backup-restore
Scheduled Automation перечитаны после изменения; новые дополнения
plan/tasks/quickstart/fragment прочитаны целиком. Прежние требования и
зависимости из проектного этапа сохраняются.

## Ограничения и следующий допуск

Это scoped source review. Нет приёмки установленной конфигурации systemd,
drop-ins/overrides, cron, source-binding рабочего guard или полного
host-jobs catalog. Будущий local-backup03:10UTC не установлен и требует
отдельного проверенного механизма UTC. Наличие полной строки в contract
не обещает проверки всех возможных внешних переопределений на сервере.

Общие `full_preflight_not_implemented` и `activation_recovery_unverified`
сохранены. Полный graf-local retention/lifecycle, верхние
initial/backup/verify/actual-restore/resume, shell/CD/rollback/daily,
T112/T113/#7804, рабочие T0/ready/IP/получатели, GitHub exact-SHA CI,
Full/CD/выпуск и коммерческие AC01–AC06 остаются открытыми.
Эта календарная поправка сама по себе не доказывает трафик или продажи.

Reviewer изменил только этот отчёт, не менял checklist marks,
source/spec/plan/tasks/governance, Git/GitHub, сервер/данные/Dev.
Tests/SSH/probe не запускал. Отчёт после записи перечитан целиком;
frozen inventory и итог117/0 повторно проверены.
