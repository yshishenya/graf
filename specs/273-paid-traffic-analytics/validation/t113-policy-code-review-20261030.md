# F273/T113 — независимое ревью кода политики запуска, 30.10.2026

**Результат: HOLD. Открытых P1: 0; P2: 3.**

Ревьюер `/root/f273_release_boundary`, существующий `high-risk-product`,
T113/#7804. База Git `3e8efb8d571497bdea5ae8a7149a6dacf526a488`.
Проверены полный diff activation_operator.py/test_activation_operator.py,
принятый precode и вызывающий `_runtime_preflight`, реальная нормализованная
Compose-модель, сценарии и предоставленные журналы. Код во время ревью получил
узкую правку BindOptions/rprivate от основного исполнителя; итоговые хеши этой
редакции указаны ниже. Тесты, Docker, SSH, SQL, Dev и production ревьюер не запускал.

## Замечания

### P2-01 — штатная форма Compose secret всегда отвергается

`activation_operator.py:2097` допускает ровно `{'file'}`. Штатный результат
Compose config в `.dev/growth/t113-policy-compose-20261030.json` имеет у каждого
top-level secret два поля: `file` и сгенерированное `name`, например
`twobrain-rec_twobrain_postgres_password`. Поэтому правильная установка
получит конечный `activation_operator_policy_unverified` при первом secret.
Синтетическая `_policy_sample` удаляет это поле и не воспроизводит настоящий
выход используемой CLI-команды.

Это дефект доступности, не обход допуска: неверно отклоняется правильный путь.
Минимальная правка — допустить только обязательный file и необязательное
сгенерированное name, проверяя точное `twobrain-rec_` + logical secret;
external/driver/прочие формы по-прежнему запрещать. Нужны положительная
реальная нормализованная форма и отрицательные чужое name/extra field.

### P2-02 — driver options существующего local volume не проверены

`activation_operator.py:2126` сверяет для named volume только Name и
Driver=local; блок HostConfig.Mounts ниже проверяет лишь запрос контейнера.
Уже существующий volume с тем же именем и драйвером local может иметь
Options `type=none,o=bind,device=/посторонний/каталог`. Эти options принадлежат
самому тому и отсутствуют в запросе контейнера, который использует только его
имя. Такой runtime проходит описанные сравнения, хотя source не объявляет
driver options, а контейнер получает посторонний каталог хоста под разрешённым
destination. При writable mount расширяется фактический доступ к хосту.

Это реальный пробел проверки установленной конфигурации; для него не нужна
подделка inspect или гонка злонамеренного root во время проверки. Достаточен
том, ранее созданный с отличающейся конфигурацией. Доверие Docker daemon не
заменяет чтение его собственной конфигурации этого тома.

Минимальная правка — readonly `docker volume inspect` только фактически
использованных закрытых имён: точные Name/Driver=local/Scope=local, пустые
Options, соответствие actual mount Source и Mountpoint, проверка канонического
пути и защищённых каталогов. Директория данных может иметь штатного владельца
PostgreSQL; её владение не следует искусственно приравнивать к UID установщика.
Нужны повтор inspect/identity в итоговой сверке и включение в private digest.
Никакого create/изменения томов или чтения содержимого для этого не требуется.

Предложенный исполнителем именно такой scoped design **принят**: private mapping
volumes, проверка защищённых ancestors и leaf FD identity, отказ group/world
write и ACL, точный Mountpoint, повторный digest. Это способ устранения P2 в
прежних двух кодовых файлах, не новый framework. После реализации нужны
причинные проверки options/driver/scope/name/Mountpoint/identity/final change.

### P2-03 — AutoRemove writer допускает потерю контейнера после stop

В цикле полномочий/пространств имён `_runtime_policy` не проверяет
HostConfig.AutoRemove; положительный контейнер с AutoRemove=true отличается
лишь игнорируемым полем и проходит policy. При этом `stop_product_writers`
(`activation_operator.py:485`) останавливает writers, а затем требует прежний
набор ID. Docker удаляет AutoRemove-контейнер при завершении. Проверка обнаружит
потерю только **после** остановки продукта, и предусмотренный полным алгоритмом
возврат через start прежних ID станет невозможен.

Это дефект доступности до stop, не утверждение об обходе защиты данных.
Минимальная правка — явно требовать AutoRemove=false до мутаций у контейнеров
установки; сверить RestartPolicy с существующим source restart, без новых
политик перезапуска. Нужен отрицательный causal control AutoRemove=true при
остальных правильных полях и подтверждение отказа до Settings/stop. Новый
механизм управления контейнерами не нужен.

## Прочитанные доказательства и ограничения

- Начальный локальный operator-профиль: 226 passed / 5 skipped / 2 warnings.
- Linux JSON: 57 passed, исходный operator SHA
  `979d8ea9644d7f8206c54b83d2a210cfa42cd67e9b1267976926b7677cb692f2`,
  tests SHA `7e9d8cc0917bca3cf0432587c5be972bed41ce2dbb5c0128f2b0a7d38cc10923`.
  Прочитан скрипт извлечения четырёх точных тел тестов; на Linux policy tests
  не подменяют ancestry/ACL. Это проверка механизма на кандидатном source,
  не установленного неизменяемого оператора и не полного runtime.
- Прочитана настоящая нормализованная Compose-модель; именно она доказывает
  несовпадение схемы secret с синтетической fixture. Отрицательные тесты
  проверяют закрытый отказ, но положительная fixture должна также сохранять
  настоящую форму выхода parser, иначе такой дефект остаётся незаметным.
- Прочитан сценарий собственной inspect-пробы. В момент чтения её JSON был
  пуст, поэтому PASS этой пробы не принят. Исполнитель отдельно сообщил об
  отклонённом rslave: причина — bind source внутри daemon root /var/lib/docker.
  Отказ соответствует policy; допуск rslave расширять не требуется.
- Текущая узкая правка допускает только явный rprivate BindOptions и
  CreateMountpoint bool, сохраняя запрет прочих propagation/options.
  Она не закрывает три замечания выше. Итоговые повторные доказательства
  после исправлений должны быть заново связаны с окончательными хешами.

Остальные рассмотренные границы согласованы с проектом: доверенный source/image,
Engine merge argv без исполнения shell, закрытая интерполяция, loader Env,
healthcheck/logging, caps/namespaces, точные limits/ports/tmpfs/mount lists,
общий logical-secret registry и повтор policy digest до выхода. FD закрываются
через finally; секреты не печатаются; ошибки дают конечный HOLD. Прежние
Settings/proc-root/memfd/ACL и финальные runtime проверки сохранены.

Доверенный daemon/toolchain, закреплённый source/image и отсутствие произвольной
параллельной root-подмены остаются принятыми допущениями. Проверка не обещает
идентичность произвольного child внутри контейнера. Эти ограничения отличаются
от конкретных трёх дефектов выше и не требуют нового sandbox/framework.

## Requirements/scoped analyze

Перечитаны все 117 quality questions; отметки не изменены:
requirements 16/0, privacy-measurement 45/0, security 27/0, infra 29/0;
**всего 117 отмечено / 0 не отмечено**. Применимые требования и принятый полный
алгоритм сохраняют прежние хеши; базовые четыре документа совпали с разрешённой
основой. Отметки подтверждают качество требований, а не приёмку кода.

Новых противоречий spec/plan/tasks/contracts или ослабления конституции не
выявлено. Scoped analyze реализации — HOLD по трём конкретным P2, перечисленным
выше. До их устранения независимый gate кода не пройден.

Полные T113/T112, верхний оператор, T0/ready,
full_preflight_not_implemented/activation_recovery_unverified, выпуск,
аналитика, трафик и продажи этим отчётом не принимаются. UID1003 по-прежнему
не подтверждён; повторных вопросов владельцу не задавалось.

## SHA-256 текущего снимка ревью

```text
apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py
a00419e9428a7389038d4d2ecce2d88ee947c411ed96d35c430e4b0514827708
apps/server/tests/unit/test_activation_operator.py
37002169187ec63ef4ccf206363cf6f873d5f69219c1d5a5c51db1c27cf04340
.dev/growth/t113-policy-precode-20261030.md
7fd99cf8c4b73d137cab023038d90d83c16da5449cc1d851164519b9fe5b79ec
.dev/growth/t113-policy-compose-20261030.json
94d4818314a12c048839a809462bdd261e685ece26ec44a903e2ab896a2fd9e1
.dev/growth/t113-policy-native-20261030.py
1eefe4e1172959742a1de42033939b501806391ef7c4a9c54e8bbf0fb5eec7e2
.dev/growth/t113-policy-native-20261030.json
905803c6a4f38f32428752bb68d4ff6963b925dbe2c6dc878117f5ca0f83ab00
.dev/growth/t113-policy-operator-20261030.log
e9d3aaccc527fa3c41ee60a6a607eb8d642295843b6e190471890ad1b8cb1bc8
checklists/requirements.md
6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2
checklists/privacy-measurement.md
8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f
checklists/security.md
57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8
checklists/infra.md
998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94
```

Короткие пути checklist относятся к specs/273-paid-traffic-analytics/.
