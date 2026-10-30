# T113 — каталог локального хранения

База `bc7fb3b6f2d01daf7a3219e6fa868ed6cbf06eba`, F273/T113/#7804,
полоса `high-risk-product`. Продолжение существующей задачи, без нового PR,
выпуска, рабочего T0, включения аналитики/IP или изменения продукта.

`local_retention_database_catalog` использует удержанную физическую source
сессию в read-only transaction. Четыре категории двух локальных уровней
сверяются с `LEVEL_RETENTION_CATEGORIES` и `retention_rule`: ровно четыре
PostgreSQL категории, `until_decision`, без возрастных сроков. Четыре public
таблицы обязаны быть обычными постоянными таблицами штатного владельца,
без inheritance/partition/rewrite. Каталог всех noninternal triggers
сверяется с семью штатными обработчиками и их точными function bodies/flags.
Ожидаемые тела извлекаются из закреплённых миграций без исполнения миграций;
для0100 проверяется прямой вызов единственного `_install_policies` из upgrade.
Неизвестные extensions и известные scheduler namespaces запрещают этот proof.

`_runtime_databases` получает digest до снижения owner. После yield тот же
reader повторяется в read-only transaction уже сниженной source-сессии;
повышения прав нет. Изменение каталога или ошибка запроса запрещают успех.
Наружу по-прежнему четыре поля runtime; подробности только в aggregate digest.

## Проверки

- [Проект и уточнение разборщика](t113-retention-design-review-20261030.md):
  независимый SCOPED PASS, P1/P2=0,117 вопросов перечитаны,117/0.
- [Независимое ревью кода](t113-retention-code-review-20261030.md):
  SCOPED PASS, P1/P2=0; проверенные hashes совпадают,117/0 без правки маркеров.
- Начальный RED:8 ModuleNotFoundError, отсутствие нового механизма, не8
  доказанных обходов. Первый native запуск выявил два различия реальных
  миграций: допустимое отсутствие SQL `;` и создание billing functions через
  `_install_policies`. Требование exact prosrc сохранено; parser уточнён.
- Окончательный профиль: **293 passed /37 skipped /27 deselected**, два прежних
  предупреждения,41,36с. Выбор включает unit operator/local_retention и8
  настоящих PG17 сценариев:7 runtime DB preflight плюс1 catalog matrix.
- Native catalog matrix принимает актуальные миграции и проверяет25 отказов:
  18 обратимых изменений таблиц/правил/обработчиков/функций/extensions,
  5 замен атрибутов trigger и отсутствие read-only transaction в2 формах.
  После каждой обратимой подмены штатный digest снова принимается. Оба
  допустимых enabled состояния O/A принимаются с разными digests. Тот же
  каталог прочитан после SET SESSION AUTHORIZATION maintenance.
- Отдельный runtime сценарий меняет trigger внутри yield: повторный reader
  даёт HOLD; физические соединения закрыты. Native targets учебные, fixture
  удаляет принадлежащие ему контейнеры/тома; текущий список bootstrap targets пуст.
- 11 unit случаев:4 ошибки coverage/policy и7 ошибок буквального SQL/его
  расположения/вызова helper/регистра dollar tags. Ruff, whitespace,
  development-process и Spec Kit governance прошли.

Ignored журналы: `.dev/growth/t113-retention-{red,first,second,third,profile}-20261030.log`.
Окончательная проверка и SHA256 находятся в `.dev/growth/t113-retention-final-20261030.json`.
Пропуски Linux root/proc/memfd и исключённые прочие PostgreSQL сценарии не
выдаются за выполненные этим профилем. Сохранённые результаты прежних стадий
не объявляются новым полным тестированием всего оператора.

## Оставшаяся граница

Это каталог, не полный retention receipt: standalone functions/dependencies,
прочие executable objects/rules, RLS/constraints/cascade, данные/lifecycle,
точные остатки удалений и реальные host/installed jobs/config ещё требуют
полного verifier. Закрытый trigger catalog не доказывает отсутствие SQL,
запускаемого другим процессом/БД. Shell scope graf-local/верхние операции/
Compose/CD/rollback/daily/T112 впереди. Сохраняются
`full_preflight_not_implemented` и `activation_recovery_unverified`.
T113/#7804/T112/AC01–AC06 остаются открытыми; трафик/клиенты/оплаты этим
учебным этапом не подтверждены.

Сверка принятого участка с FR-050/plan и текущей T113 не нашла нового
неучтённого объёма: перечисленный остаток уже входит в открытые задачи.
Полный `$speckit-converge` фичи не запускался, состояние converged не заявлено.
Задачи/issues не добавлялись и не закрывались; отдельный вспомогательный PR
не создаётся. Изменение сохраняется в общей ветке до законченного кандидата.
