# T113: проверка фактической рабочей среды

30.10.2026. Основа bade9285ee84b2767e4f1a8ac6ec8ffdbca6cfb8.
F273/T113/#7804, high-risk-product; Legacy Impact untouched.

## Что изменено локально

- [x] Закреплённый launcher вызывает установленный модуль Python3.13 с -I/-B/-m
  внутри срока жизни своей среды и удержания общего замка выпуска.
- [x] Один фиксированный локальный Docker socket; очищено влияние caller
  context/host/TLS. Linux daemon без rootless/userns-remap.
- [x] Штатный current-override завершённого выпуска и immutable image ID;
  source label/единственный source env проверяются в image и GRAF container.
- [x] Состав служб/private networks переиспользует существующий validator.
  Postal network получается из actual API и сверяется повторно по identity.
- [x] Настоящие Config/HostConfig/Mounts читаются только в памяти, связываются
  digest и повторной сверкой. Стабильность не объявляется правильностью policy.
- [x] Running GRAF writers проверяются через host PID/starttime, четыре UID100/
  GID101 и identity uid/gid maps. Остановленные optional не запускаются.
- [x] Сторонние initializers/infrastructure проверяются по собственным images;
  им не приписываются GRAF source/UID. Required writers running, health проверен.
- [x] Source/override/actual metadata/process/network/socket повторяются;
  child JSON bounded/exact, duplicate/extra/partial/noise отклоняются.
- [x] Независимое ревью реализации: открытых P1/P2 нет; принято ограниченное
  чтение runtime bindings, полный допуск по-прежнему закрыт.

[Ревью проекта](t113-runtime-design-review-20261030.md) разрешило ограниченную
реализацию после исправления матрицы initializers и выбора local daemon.
117 требований отмечены/0 открытых; это качество требований, не runtime PASS.

## Проверки и исправление

До реализации21 новых случая завершились отказом из-за отсутствующих функций.
Окончательный общий профиль operator/bootstrap/fence: **207 passed,1 Linux skip,
2 прежних warnings**,4,91с. Ruff, governance, development-process, fragments и
whitespace прошли. Это локальные проверки, не required GitHub/release evidence.

Собственная Linux-проверка реального процесса: UID100/GID101 PASS, root HOLD;
identity maps и правильный starttime прочитаны из настоящего /proc. Собственные
контейнеры удалены. Рабочий root-оператор не запускался.

Собственная native Docker-проба обнаружила ошибку шаблона: у контейнера без
healthcheck нет ключа State.Health. Доступ через `with index .State "Health"`
исправлен. Повтор настоящих runtime/image templates PASS; общий профиль после
этой правки повторён. Подмена ответов unit-теста не выдаётся за эту native пробу.
Пропущенный на macOS Linux-only supervisor отдельно выполнен из тела того
же отслеживаемого теста через AST, с текущим launcher в собственном Linux
контейнере без сети/capabilities: PASS, stderr пустой, контейнер удалён. Это
208 уникальных случаев в двух средах, а не единый прогон208 на Git SHA.
Полного native preflight всего GRAF с release record этим не выполнено.

Отдельный настоящий Git-тест с test-only имитацией другого владельца
воспроизводит dubious ownership без safe.directory; фиксированный ROOT даёт
успех, соседняя рабочая копия остаётся запрещённой. Окружение задаёт ровно один
свой safe.directory, без wildcard и наследования caller Git config. Рабочий
root-процесс на сервере этим не запускался.

## Контрольные суммы

| Материал | SHA256 |
| --- | --- |
| `infra/scripts/activation-operator.py` | `e11efddb4001602014977be3dff5e86550978cf81bfe67f23d7ae60a0bdfbfb5` |
| `apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py` | `18a49160c68f59ca714d25950c48b17e81d36b673f8d12a9c60f17a569eb3dcc` |
| `apps/server/tests/unit/test_activation_operator.py` | `e7ed94d2e0d1bb4644a186dfd0f5ef2f6dec8010b72f4938aaf2fa6b01b8af1b` |
| `apps/server/tests/unit/test_activation_operator_bootstrap.py` | `e448388f69f21f7e4681344054a50b2ec1797737306f0b99f618db0193248386` |
| `.dev/growth/t113-runtime-profile-20261030.log` | `6a3645c7b7937e7fb64035315d368499f51861f278d6d9c35c10cc263a090475` |
| `.dev/growth/t113-runtime-native-process-20261030.json` | `06be883436c2ba765f6f7edda3fcf7e6fa9cdcfb8b4ee26c30b9e845656f7fb6` |
| `.dev/growth/t113-runtime-docker-format-probe-20261030.py` | `1dbf77cc213edb6941d26e95182d0d7c9947765f1c6154b9204049cfcd280804` |
| `.dev/growth/t113-runtime-docker-format-20261030.json` | `d88d5b521a3e461f6fdc7eea3654035cc61de4588545b2e1e3336979015e446e` |

Native supervisor result SHA256:
`924ddde5b4e5c30fb0be3b716a8eae23bf4452ed8835f0cf15686ffecec4f670`.

## Ревью и сверка остатка

[Независимое ревью кода](t113-runtime-code-review-20261030.md): SCOPED PASS,
P1=0/P2=0,117 требований перечитаны/0 открытых. P2 root Git ownership
подтверждена и закрыта после чтения финального фиксированного окружения и
причинного Git-теста. Все четыре исходника/теста совпадают с проверенными хешами.
SHA256 отчёта: `4b225d2b13eee4709d63c94dcfac881593c5f79aab15626dd99d9b5edbe6b414`.

Проверяющий запускался отдельно в режиме только чтения. Его попытка напрямую
записать отчёт была отклонена этим режимом; завершённый текст сохранён без
изменений штатным `--output-last-message` внешнего процесса. Последняя фраза
внутри отчёта о несохранении описывает только попытку внутренней записи:
окончательный файл действительно присутствует и хеширован выше. Отметки
reviewer-owned списков основной агент не менял.

Сверка данного среза с принятым проектом: runtime bindings реализованы,
новых требований и дублирующих задач нет. Полный остаток уже покрыт открытыми
T113/T112 и перечислен ниже; полного convergence всей фичи не заявляется.

## Следующие обязательные шаги

- [ ] Собрать общий законченный кандидат после реализации оставшегося T113/T112.
- [ ] Полный preflight реальных Settings/mounted paths/secret policy, DB/schema/
  roles, storage budget/capacity, retention/access/legal/lifecycle.
- [ ] initial/backup/verify/actual restore/resume и rollback/shell/CD integration,
  проверка паузы продукта и ежедневный контроль.
- [ ] T112: новая запись после единственного T0 и видимо открытый готовый результат.
- [ ] Общий PR, exact required checks, один Full/CD и рабочая приёмка измерения.
- [ ] После достоверного измерения — опыт Product Radar и оценка оплат с возвратами.

Даже успешная эта стадия возвращает внешнему caller exit1/HOLD
`full_preflight_not_implemented`; activation_recovery_unverified сохранён.
T0/ready не созданы, рабочие IP/аналитика/получатели не включены. Подтверждение
доверия UID1003 не получено; права сервера не менялись. AC01–AC06 и цель3 оплаты
от3 новых внешних клиентов до19.01.2027 остаются открытыми. Учебные проверки
не являются трафиком, активациями или продажами.
