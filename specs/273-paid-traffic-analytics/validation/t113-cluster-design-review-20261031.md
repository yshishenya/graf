# F273/T113: независимый проектный разбор охвата PG-кластера J2

31.10.2026, проверяющий `/root/f273_release_boundary`, `high-risk-product`.
Ветка `codex/f273-local-period-20261029`, HEAD основы
`521670ddc1db2b9db25bcf987d622034a54a4248`, T113/#7804.
Проверяется только уточнённый проект J2 до реализации. Рабочий сервер,
SSH/Docker/БД/Dev, Git/GitHub, конфигурация и код reviewer не менял;
тестов лично запущено **0**. Записан только этот отчёт. Чужие изменения в
рабочей копии сохранены.

## Решение и точная граница

**SCOPED J2 DESIGN/ANALYZE PASS**: открытых P1:0, P2:0, CRITICAL:0,
HIGH:0 в пределах проекта J2. Принят окончательный
[алгоритм охвата кластера](t113-cluster-inventory-20261031.md#конкретный-проект-j2-для-следующей-реализации),
SHA-256 `81d3dcd007beb7e5872524733ba9f4f9d039b9e1e3da17e03e7c104e6fb7a831`.
Затронутые разделы operations/plan/quickstart/tasks согласованы с ним.

Это закрывает проектную находку **J2** из
[предыдущего разбора](t113-installed-jobs-design-review-20261031.md).
Его **J1 остаётся открытой P1/HIGH**: полный host scheduler и конечная цепочка
косвенных executable/config/hooks ещё требуют конкретного проекта и отдельного
разбора. Старый отчёт не переписан; его общий DESIGN HOLD для полного
installed-jobs proof сохраняется с одной оставшейся проектной находкой.
Принятие J2 не подтверждает выполнение native проверок или готовность T113.

## Исправления, проверенные до PASS

Первый вариант J2 требовал ровно шесть DB после репетиции и разрешал только
добавочные цели текущего run. Это противоречило уже принятому actual restore:
он сохраняет прежнюю закрытую DB как `prior_UUID` для отката, после чего обычный
preflight/verify обязан продолжать работать. Reviewer сообщил **P1**; до
настоящего решения основной исполнитель исправил проект и связанные разделы.
Окончательные байты перечитаны независимо.

Теперь разрешён конечный retained prior набор, полученный из действительно
прочитанного trusted fsynced actual-run history с доказанным switch/complete.
Его связывают с cluster, прежним OID/source и неизменной T0. Для каждой prior
требуются точные owner/non-template, ALLOW_CONNECTIONS=false, limit0, ноль
сессий и prepared transactions, исходный native/catalog digest. Неизвестный
или незавершённый switch остаётся HOLD. Префикс не даёт допуска. Cleanup
репетиции prior не удаляет; обязательные решения об удалении и их сроки
охватывают сохранённые копии. Это устраняет конфликт с actual restore без
расширения допуска произвольных баз и без нового срока хранения.

Также независимо перечитаны две согласованные поправки:

- Эталон расширения сравнивается по полным нормализованным object identities,
  определениям и зависимостям, а не по случайным OID чистого экземпляра.
- Обычная смена PID/ticks/числа клиентов Temporal исключена из стабильного
  digest. Допустимые типы процессов проверяются повторно; неизвестный backend
  и любая активность/prepared в закрытой DB запрещают успех.

Открытых замечаний к этим исправлениям не осталось.

## Почему проект достаточен для следующей реализации

| Граница | Принятое доказательство в проекте | Что не считается доказательством |
| --- | --- | --- |
| Полный inventory | Шесть известных баз PG17, полные owner/template/locale/encoding/connection metadata; отдельно точные current-run targets и retained prior; cluster/PGDATA/OID binding до/после | Перечень только `twobrain_rec`, имя или prefix дополнительной DB |
| Эффективные настройки | Четыре фактических preload/library settings, pending restart и все соответствующие role/DB overrides; физическое read-only соединение с каждой доступной DB на том же endpoint и общий конечный deadline | Только cluster defaults или отсутствие известного имени расширения |
| Каталоги соседних DB | Полный independently derived clean-image эталон `plpgsql` и допустимого только в visibility `btree_gin`; все extension objects/dependencies; точная Temporal `convert_ts` вместе с атрибутами/owner/ACL | Количество87, одно имя, self-hash, `probin` или только MD5 тела |
| Закрытая `template0` | Известное закрытое состояние, ноль сессий/prepared, отсутствие preload/overrides/неизвестных background workers; unknown означает HOLD | Заявление, что непрочитанные внутренние каталоги пусты; временное открытие DB |
| Собственный drain | Уже удержанное reduced source соединение без reconnect; повтор остальных доступных DB и source catalog перед ready | Новое подключение к закрытому источнику или пропуск проверки после понижения роли |
| Изменения между стадиями | Повтор inventory/settings/catalog/cluster и разрешённых типов backend; стабильный digest с реальными OID/image/source | Разовый снимок, ложный отказ от обычной смены разрешённых клиентских PID |

Закрытая `template0` допустима именно как доказанная невозможность поддержанного
исполнения в текущей конфигурации, а не как якобы прочитанный каталог. Ручные
доверенные root/SQL действия сохраняют прежнюю границу; периодические задания
нельзя исключить этим допущением — они остаются J1. Установка неизвестного
background worker, лишняя DB или невозможность доказать состояние закрывают
допуск. Нового CLI, parser/framework, ролей/грантов или временного открытия
закрытых баз проект не вводит.

## Scoped analyze и reviewer-owned списки

Использован ранее прочитанный `speckit-analyze` для ограниченного среза.
Prerequisites подтвердили F273; установленный script не поддерживает
`--require-spec`, поэтому применялись `--require-tasks --include-tasks`, а
наличие spec проверено отдельно. Before/after hooks явно disabled;
меняющие состояние hooks не запускались. Это не полный повторный analyze
реализации всей F273.

| Требование | Существующие задачи | Покрытие проекта J2 |
| --- | --- | --- |
| FR-036/050 | T109/T113 | Кластерный охват доказательства local retention, отсутствие неизвестного scheduler/preload, unknown закрывает результат |
| FR-038 | T100/T113 | Привязка к pinned source/image, effective config и полным каталогам до/после |
| FR-034/035, зависимости | T110/T113 | Различение owned rehearsal targets и сохранённых prior после actual restore; прежний source binding и обязательное удаление сохранённых копий |

В scope пять FR, 5/5 имеют существующие задачи; новых непокрытых или
дублирующих задач0. Неопределённость J2 и конфликт retained prior устранены;
противоречий конституции в этом срезе нет. Это карта требований и проекта,
не процент готовой реализации и не закрытие T109/T110/T113.

Все **117** действующих вопросов четырёх списков перечитаны и заново оценены:
requirements **16 checked /0 unchecked**, privacy **45/0**, security **27/0**,
infra **29/0**. Итог **117 checked /0 unchecked**. Отметки не менялись.
Они подтверждают качество требований; ни одна не обозначает выполненный
runtime verifier. Для J2 особенно применимы privacy CHK033–037,
security CHK010–015/022, infra CHK005–009/025. Их backup/retention/config
основания сохраняются. Остальные пункты сохраняют основания полностью
прочитанных неизменных договоров: новых категорий/получателей/согласий,
изменений атрибуции и продуктовых решений этот проект не вводит.

Неизменные большие baseline проверены по хешам в пределах разрешённого
владельцем исключения F273. Затронутый проект и зависимости прочитаны
непосредственно. Контрольные суммы списков совпали; финальные117 вопросов
повторно перечитаны отдельно от исторических записей.

## Факты наблюдения и ещё необходимые проверки

Три закрытых файла метаданных основного исполнителя прочитаны. Они показывают
шесть DB PG17.8/170008, пять доступных соединений, наблюдавшиеся пустые preload,
отсутствие соответствующих overrides и штатные кандидаты btree_gin/convert_ts.
Reviewer серверные пробы самостоятельно не повторял. Эти файлы **ещё не
доказывают** чистый эталон полной extension closure, все атрибуты convert_ts,
locale/encoding, template0 activity/prepared/background и before/after.
Названия/число routines и MD5 тела не приняты как полный verifier.

До приёмки кода обязательны независимое code review и причинные изолированные
PG17 сценарии из quickstart: положительный шестибазовый путь; чужая/недоступная
DB; каждый preload/role override/pending restart; подмена extension object,
ACL/dependency или convert_ts при прежнем имени; неизвестный worker;
неверный endpoint/cluster/OID; неизвестная UUID-цель; замена после await;
сессия/prepared закрытой DB; retained prior в обычном verify и отказы при её
подмене/открытии/неизвестном switch/непокрытом обязательном удалении.
Дополнительно нужны нормализованный clean extension reference с иными OID,
разрешённая смена клиентских PID, source drain без reconnect и завершение
всех собственных соединений при отмене. Рабочая template0 не открывается.

Остаются J1, оба общих HOLD `full_preflight_not_implemented` и
`activation_recovery_unverified`, полный preflight/initial/backup/verify/
restore/resume/CD, protection/history, installed jobs и lifecycle proof,
ресурсный бюджет/место для двух полных копий+restore+staging, операторские
права/MFA, T112/T113, AC01–AC06, T0 и все проверки выпуска на точном SHA.
Рабочие IP/provider/writer не включены этим разбором. CI/Full/выпуск,
трафик и продажи этим отчётом не подтверждаются.

## Снимок прочитанных источников

| Источник | SHA-256 |
| --- | --- |
| J2 inventory/design | `81d3dcd007beb7e5872524733ba9f4f9d039b9e1e3da17e03e7c104e6fb7a831` |
| operations.md | `b1c3b925a3b1c68c78ac9eaf17635f6acd4e6c3fc5af789287260aa7d4262d93` |
| plan.md | `bfb977c8091500f58c2c3711aa1c41251e55aa21df8a2c6c7a60273687cb942d` |
| quickstart.md | `abd8870c4f0e67f7af20486ef6eef1c96b423c4d6287b2074ce0af5f122f456f` |
| tasks.md | `229e53d457b63f3b6cf29607e7dbb03cbe8076d8d5f220b7b30ef8b3992d1816` |
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current-product-status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| spec.md | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| data-model.md | `488833fcc4b8e4841672485b35cfa0161e1f02983d10ad98b52eb71d55bb55f5` |
| full-operator-design | `5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec` |
| activation_operator.py package | `b086459d5f3a2a16571041cc96c7120543a6ebfed3dd1ae4887a0a7405ea4ced` |
| local_retention.py package | `a9e50827c463800957738ba0192b6fe9d4c38f5c9c3541428ee5a6b89b0661b6` |
| extensions.yml | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |
| requirements16/0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy45/0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security27/0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra29/0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |
| closed metadata evidence | `fae33c408a909b35cdc7f69c54deca2c65c4fcb336633f1da3c979ba75820422` |
| closed catalogs evidence | `bc864542b354c1b2c4e3b00c71933465091e93429b247aa14da29b4448092823` |
| closed routines evidence | `ef54c4ed66e80afecf091ae534cfeac9d61bbfc4e63b6fcea9665bb8271e67b1` |

Проверки ссылок/заголовков/governance основного исполнителя не выданы за
собственные тесты reviewer. Общие документы могли параллельно меняться;
этот вывод относится к перечисленным байтам и точному J2 design. Перед
реализацией изменение его границы требует повторного scoped review.
