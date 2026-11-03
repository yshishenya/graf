# T113 — независимое ревью интеграции readback, 3 ноября 2026

Статус: **HOLD**. Проверено host/container/shell взаимодействие по O1–O8.
Предыдущий PASS выделенного проверяющего файла не переносится на эту интеграцию.
Полоса: high-risk-product, независимое read-only code review; изменён только этот отчёт.

## Проверенная основа

Рабочая копия: `/private/tmp/graf-object-readback-mxz0q0a0/crisp`.
Переданный владельцем HEAD: `2f36c09d4ef2612c9bd221c179dfb654e54bfe4a`;
Git в ходе ревью не использовался для изменения или подтверждения HEAD.
Проверялись текущие незакоммиченные файлы, поэтому привязка — по SHA256:

| Файл | SHA256 |
| --- | --- |
| `infra/scripts/rec-object-verify.py` | `112aebc622562e6334d05c945e8f75f8ebabeeca1b0d4ec7268ff3d190b28bec` |
| `infra/scripts/rehearse-rec-restore.sh` | `358a42db4dce241ee1f5bda01743326c9158d1b72ed202e94aa33ff7290effd1` |
| `apps/server/tests/unit/test_rec_object_verify.py` | `88aaf0b7974913d5f15c9cbc8217d7c5fcf76ca67c6606911dcd0ebaaa4363a9` |
| `apps/server/tests/integration/test_deployment_restore_safety.py` | `8079e2a3dd5e6fedb4521d16f6de8a601c44b395f4286d3054d026df70c19336` |
| `apps/server/tests/integration/test_deployment_object_restore.py` | `7f633e320f7970c6100c0a6990170140c0677ab1acaf877da2d786ff89497869` |

Дизайн: `t113-object-readback-design-20261103.md`, SHA256
`0e02c8fadb1cab3b59fce85d5f1719432c039006b6bb6a1df5d858d43d6f8e93`.
Требования checklist `object-readback.md` имеют 10 checked / 0 unchecked;
это качество требований, а не отметка приёмки реализации. Checklist не изменялся.

## Открытые замечания

1. **P1 — повторный сигнал может разрешить очистку без подтверждения остановки CLI.**
   `rec-object-verify.py:232–241,296–307`: `cli_unknown` устанавливается только
   при `TimeoutExpired` второго `communicate`. Если повторный обработчик сигнала
   выдаёт `RuntimeError` во время `kill` или второго `communicate`, признак
   остаётся False. Внешний finally затем выполняет inspect/rm и публикует
   `.cleanup`, хотя подтверждения завершения первого Docker CLI нет.
   Независимая причинная модель заменила только Popen: первый communicate
   прерван, kill запрошен, второй communicate прерван повторно; получены
   `cleanup_marker=True` и `removed_without_settlement=True`. Это модель окна
   сигналов, не доказательство реального состояния Docker daemon. Требование O6
   требует fail closed при неизвестном завершении. Следует помечать исход
   неизвестным до остановки и снимать пометку лишь после подтверждённого
   завершения; повторные сигналы не должны прерывать защищённый этап.

2. **P1 — общий cleanup shell не имеет предела и может прерваться сигналом.**
   `rehearse-rec-restore.sh:91–128`, особенно `trap - EXIT HUP INT TERM` на строке93.
   Предел60с/remember_stop защищает только reader container; последующие mc rb,
   проверка корзины, dropdb и staging cleanup выполняются без общего предела.
   В независимом учебном сценарии fake mc rb удерживался до разрешения;
   SIGTERM после его входа завершил wrapper с rc143, без итогового вывода.
   Обе собственные БД и host staging остались. Новый reader signal-тест
   посылает повторный сигнал во время удаления контейнера и не покрывает этот
   этап. Речь о незакрытой приёмке нового O6, а не утверждении, что вся прежняя
   shell-очистка впервые появилась в этой правке. Нужен отдельный общий срок
   cleanup и защищённое завершение всех собственных дочерних процессов под lock.

3. **P2 — подмена манифеста тем же JSON допускает PASS.**
   `rec-object-verify.py:221,284,313–314`: сравнивается значение JSON;
   identity файла и закрытого parent между фазами не удерживается/не сверяется.
   Независимый fake docker rm заменил манифест новым файлом0600 с теми же
   байтами, источник не менялся. Получены `rc=0`, `manifest-replaced=True`,
   `restore_rehearsal_result=pass`. Дизайн запрещает подмену/изменение манифеста;
   нужно подтвердить исходные inode/metadata и private parent на всём пути.

4. **P2 — регрессия подготовки теста objects-link.**
   `test_deployment_restore_safety.py:407`: fixture теперь создаёт обычный
   объект в `minio-objects`, но objects-link case вызывает rmdir непустого
   каталога. Собственный полный профиль получил OSError66 ещё до запуска
   скрипта; тест не проверяет запрет ссылки и весь профиль не зелёный.

## Независимые проверки

Команда с уже существующим окружением, без создания зависимостей/кэша:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/yshishenya/.codex/worktrees/growth-guide-previews/crisp/apps/server/.venv/bin/python -m pytest -q -p no:cacheprovider apps/server/tests/unit/test_rec_object_verify.py apps/server/tests/integration/test_deployment_restore_safety.py
```

Результат: **114 passed, 1 failed, 2 warnings, 121.81s, exit1**.
Единственное падение — objects-link, описано выше. Существующие предупреждения
pytest rewrite и Starlette/httpx не использовались для обоснования отказа.
Тестовый fixture создаёт собственный пустой Git-каталог как часть изоляции;
рабочее Git-состояние проекта не менялось.

Дополнительно исполнены три причинных сценария на временных синтетических
данных: замена манифеста теми же байтами; сигнал в shell bucket cleanup;
повторное прерывание CLI settlement через модель Popen. Временные материалы
этих трёх сценариев удалены после завершения. Рабочие серверы, Docker,
настоящие backup и secret files не использовались.

## Проверенные свойства и предел вывода

Код и локальный профиль подтверждают направленность реализации: исходный
snapshot до mirror, точное полное чтение байтов, read-only mounts, закреплённый
image/SDK, create-only имя и проверка label/image, отказ при неизвестном inspect,
container removal перед bucket removal, marker только после проверки отсутствия
контейнера, отказ при source drift во время reader cleanup. Unknown create
обрабатывается отдельным inspect; чужая коллизия без ожидаемого label сохраняется.
Общий deploy lock передаётся shell и удерживается через обычный cleanup-путь.

Эти свойства не устраняют четыре замечания выше. Реальный нативный профиль
`test_deployment_object_restore.py` прочитан, но reviewer его не запускал:
его фактические bind identities/версии/совместимость и очистку должен подтвердить
отдельный свежий receipt владельца. Его собственные subprocess timeout40 не
заменяют production-пределы600/60 и synthetic signal-профиль.

Решение: **интеграцию не принимать до исправления и повторной причинной
проверки замечаний**. Full F273, T113/T116, T0, восстановление рабочих копий,
PR gates, выпуск, аналитика и коммерческая цель этим отчётом не принимаются.


## Повторная проверка исправлений — промежуточный HOLD

История первого HOLD выше сохранена. Повторно проверен срез с helper SHA256
`eea2987d7bd303a8e462f1dadcf4a7c3adb0fcbb130a8478b0a736b50de10d14`,
shell `258132956d9fdf8b492e7d2e07b13cdcfe24d70d9585e827a1e11e12b65e4d4e`,
unit `90d6ab9fac6a124f6abadc089128218e5c56cfe886c88fcb7a07520243e64f13`,
shell tests `f60be704c96156bea8884aed97ae48365c2861ab2693c9baeb55f005c15ca6cd`,
native profile `7f633e320f7970c6100c0a6990170140c0677ab1acaf877da2d786ff89497869`.

Независимый полный повтор той же команды: **120 passed, 4 failed, 2 warnings,
143.37s, exit1**. Падали обычный положительный путь, проверка порядка cleanup,
положительное завершение parallel-lock и wrapper stop `[kill]`.
Срез начал изменяться владельцем в ходе этого прогона; результат относится к
скопированным каждым fixture версиям и не является приёмкой последующих правок.
После изменения parent identity `[:6]` на `[:5]` отдельный положительный
синтетический сценарий на более новом helper уже получил rc0; это не заменяет
полного повторного профиля на зафиксированном наборе.

Исправление `cli_unknown=True` до kill причинно закрывает первое окно повторного
communicate: новый unit не получает inspect/rm/marker при неизвестном завершении.
Общий supervisor использует отдельную собственную группу процессов, однократный
SIGUSR1 и невозобновляемый alarm60. Таймаут выдаёт только
`cleanup_timeout_resources_unverified`; он не называется остановкой Docker daemon.
Исправление objects-link сохраняет первоначальный каталог переносом и создаёт
отдельную ссылку; прежней ошибки подготовки больше нет.

В промежуточном срезе выявлены два дополнительных результата:

- Проверка identity после marker предотвращала PASS, но не удаление подменённого
  staging. Независимый сценарий добавил `foreign-keep` в replacement parent:
  rc1, PASS отсутствовал, прежний перемещённый staging сохранён, replacement
  staging и посторонний файл удалены. Владелец затем добавил проверки владения
  staging в shell и проверку parent через удержанный FD до marker; эта новая
  версия требует отдельной повторной проверки.
- В wrapper `[kill]` supervisor уже отсутствует; уведомление из helper finally
  через os.kill находится до защищённого container cleanup. Отсутствие supervisor
  способно завершить helper до удаления собственного контейнера. Тест подтвердил
  оставшийся bucket; окончательное исправление и профиль ещё не приняты.

### Действующий Legacy Impact gate — отдельно от качества кода

Только прочитаны `docs/agent-guidance/spec-kit-flow.md`,
`docs/agent-guidance/release-and-validation.md` (Legacy Definition of Done),
`specs/273-paid-traffic-analytics/spec.md` (Legacy Impact),
`scripts/check-development-process.py`, `scripts/validate-legacy-impact.py`
и текущий `.specify/feature.json`.

Самостоятельно исполнен только валидатор без Git/сетевых действий:

```sh
python3 scripts/validate-legacy-impact.py --feature specs/273-paid-traffic-analytics/spec.md
```

Результат: **exit1**,
`compatibility exception expiry must be in the future (UTC)`.
В spec указано retain-with-exception для T098, expiry2026-11-03;
валидатор отклоняет expiry <= текущей UTC-дате. Руководство выпуска требует
`expired_exceptions=0`. Текущий pointer честно указывает F273/T113/T116,
поэтому активный spec проверяется независимо от наличия изменения его текста.

Для текущего среза F273 нет документированного обхода этого release gate.
Удаление pointer, фиктивный untouched, дубль фичи ради обхода, перевод часов или
пропуск проверки не являются корректным путём. Требуется фактическое завершение
retirement T098 либо отдельно принятое, обоснованное и независимо проверенное
решение по совместимости. Само узкое исправление restore может быть подготовлено
и проверено, но не получает допуска к выпуску от этого ревью. Spec, expiry,
classification, pointer и правила не изменялись. **Выпуск остаётся HOLD**.


## Третье ревью — зафиксированный срез, code-only HOLD

Владелец зафиксировал пять файлов на весь этот прогон. SHA256 независимо
проверены до начала и повторно после завершения; изменений между проверками нет:

| Файл | SHA256 |
| --- | --- |
| `infra/scripts/rec-object-verify.py` | `ffc7a8182291fdbf4bd4bb4408b2ab75fa258ced51064c5dda7c740983fd87d4` |
| `infra/scripts/rehearse-rec-restore.sh` | `390d032c9cf58f4c0187ed0f76f3853acfe60cc4ff1dda15b507ee6e02299376` |
| `apps/server/tests/unit/test_rec_object_verify.py` | `90d6ab9fac6a124f6abadc089128218e5c56cfe886c88fcb7a07520243e64f13` |
| `apps/server/tests/integration/test_deployment_restore_safety.py` | `29a9bcae11c56fe4914cf2d3e9a56a4e1a7bf228c280273caa0c48b531e6664c` |
| `apps/server/tests/integration/test_deployment_object_restore.py` | `7f633e320f7970c6100c0a6990170140c0677ab1acaf877da2d786ff89497869` |

Повторён тот же независимый unit + shell safety профиль: **126 passed,
2 warnings, 150.40s, exit0**. Нативный профиль прочитан и его неизменность
подтверждена SHA256; reviewer его не запускал. Числа целевых проверок владельца
не выдаются за собственный прогон reviewer.

### Закрытые замечания предыдущих снимков

- Неизвестный исход CLI отмечается до kill; только подтверждённый communicate
  снимает пометку. Повторное прерывание не даёт inspect/rm/marker.
- Обычный supervisor запускает только свою process group и заводит один общий
  невозобновляемый alarm60 с первого cleanup notification. Повторные HUP/INT/TERM
  сохраняют неуспех и не обрывают защищённую очистку; профиль проверяет lock.
- Manifest identity проверяется до marker; parent identity не включает nlink,
  меняющийся при создании marker на APFS. Marker создаётся относительно удержанного
  проверенного parent FD; затем parent снова сверяется. Same-bytes replacement
  и parent replacement не дают PASS/marker.
- Shell сохраняет исходные dev/inode/UID staging и проверяет их до bucket cleanup
  и перед rm. Replacement parent с foreign-keep сохраняется, чужой путь не удалён.
- Objects-link case теперь проверяет ссылку и не падает при подготовке fixture.
- Исчезнувший supervisor больше не прерывает собственный container cleanup:
  ProcessLookupError сохраняет отказ, helper выполняет свою ограниченную очистку,
  shell использует защитный watchdog при отсутствии supervisor.

### Единственное открытое замечание текущего кода

**P2 — watchdog повторно выдаёт полный cleanup-бюджет после смерти supervisor
уже во время reader cleanup.**

`rec-object-verify.py:297–304` начинает собственный cleanup60 и уведомляет
supervisor. Если supervisor получает SIGKILL после этого уведомления, reader
может ещё расходовать свой cleanup-бюджет. Когда reader завершается,
`rehearse-rec-restore.sh:127–139` запускает новый watchdog с полным sleep60,
не вычитая уже прошедшее время. Это не тот же общий невозобновляемый предел O6;
в неблагоприятном случае суммарный этап приближается к120с. Проверки отказа
и сохранности остатков корректны; замечание относится к сроку, а не ложному PASS.

Независимый причинный сценарий использовал только fixture и sitecustomize:
оба60с заменены на2с, supervisor убит после события reader cleanup-started,
собственный reader cleanup удержан1.2с и затем освобождён, bucket cleanup
удержан до watchdog. Получено:

```text
scaled_cleanup_budget=2
elapsed_from_first_cleanup=3.287s
shell_bucket_started=True
timeout_failure=True
pass=False
bucket_left=True
```

В отличие от текущего regression test, supervisor здесь убит не до mirror
release, а уже после начала первой cleanup-фазы. Все временные учебные
материалы удалены после сценария. Для закрытия требуется один абсолютный
монотонный deadline, который не теряется со смертью supervisor; резервная
защита должна использовать оставшееся время. Требования O1–O8 не изменялись.

**Итог только по коду текущего среза: HOLD, P1=0, P2=1.** Полный зелёный
профиль не покрывал описанную последовательность SIGKILL между двумя фазами.
Legacy Impact T098 — отдельный release HOLD из предыдущего раздела; он не
использован как причина этого code-only решения. PR/release, фактические
восстановления, Full F273/T113/T116 и аналитика этим ревью не принимаются.


## Четвёртое ревью — единый deadline и pipe, исправленный остаток журнала

История прежних HOLD сохранена. Проверен новый helper
`4acb585b6e83f13dce5ed4c57977ce2e8c4ef8118a0e3b4f1849efae327a39e1`,
первоначальный pipe shell
`caaf7332b371127be48b8660147a0346066eba28fa96ae70d9131092b5331fa8`
и safety
`7c50fa66e1c9a0ae479e20162247833349c4b07abdb4e8d689695be5aef2686d`.
Остальные unit/native hashes указаны в окончательной таблице ниже.

Независимый unit + shell safety запуск завершился **138 passed, 2 warnings,
166.59s, exit0**. До окончательной сверки хешей владелец уже исправил два файла
(shell/safety), поэтому этот результат не выдаётся за полный профиль окончательных
пяти хешей. Набор текущего изменения независимо проверен отдельно ниже.

Прежний P2 повторного cleanup-бюджета причинно закрыт. Самостоятельно повторена
та же последовательность:60→2с в учебной копии helper, supervisor убит после
reader cleanup-started, reader освобождён через1.2с, bucket удержан. Получено
**1.930с от наблюдения первого cleanup**, timeout_failure=True, PASS=False,
bucket сохранён. Прежние3.287с больше не воспроизводятся.

`cleanup_budget` создаёт create-only0600 deadline в проверенном собственном parent
и при следующих вызовах сохраняет тот же срок. Повреждение, неизвестный срок,
ссылки/hardlink, неверные режим/parent отклоняются. Supervisor/helper/fallback
используют остаток общего монотонного срока; inherited pipe заменяет сохранённый
PID. BrokenPipe сохраняет отказ и не запрещает очистку своего контейнера.

В исходном pipe shell найден ещё один узкий **P2**: после staging_owned=False
собственные DB cleanup-команды продолжали открывать >>$log внутри replacement
parent. Два независимых запуска неизменённого fixture reader-parent-replace
получили rc137, PASS=False и новый commands.log нулевой длины рядом с исходными
foreign-keep/manifest. Удаления чужого каталога и ложного PASS не было, однако
само перенаправление изменяло уже признанный чужим каталог. Замечание передано
владельцу до завершения отчёта; затем независимо проверено исправление ниже.

### Окончательный срез — scoped code PASS

**Решение по коду: PASS, открытых P1=0, P2=0.** Пять текущих SHA256 независимо
сверены перед целевым прогоном и после его завершения:

| Файл | SHA256 |
| --- | --- |
| `infra/scripts/rec-object-verify.py` | `4acb585b6e83f13dce5ed4c57977ce2e8c4ef8118a0e3b4f1849efae327a39e1` |
| `infra/scripts/rehearse-rec-restore.sh` | `bf5fe1c6f9944ea9454c3eeaf66225dd0c4abcc4e0044b9567ec07e82f0d7af7` |
| `apps/server/tests/unit/test_rec_object_verify.py` | `1a3fa14224eac038017a699470c583adf965324d3186122ce88d123390cbc3e0` |
| `apps/server/tests/integration/test_deployment_restore_safety.py` | `5be97f667202dd35582c96c882d9d9c8f62d48d896283674ee08c8402ada3776` |
| `apps/server/tests/integration/test_deployment_object_restore.py` | `7f633e320f7970c6100c0a6990170140c0677ab1acaf877da2d786ff89497869` |

Shell заново прочитан целиком. Исходный log inode удерживается через FD9;
последующие записи не открывают pathname в staging. Коллизия зарезервированного
FD с lock/notification FD отклоняется до запуска собственного shell. Обычное
исполнение, lock, таймеры и cleanup protocol сохраняются.

Независимая команда на окончательных shell/safety:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/yshishenya/.codex/worktrees/growth-guide-previews/crisp/apps/server/.venv/bin/python -m pytest -q -p no:cacheprovider apps/server/tests/integration/test_deployment_restore_safety.py -k 'cleans_only_confirmed or runs_object_reader or reader_failure or shell_cleanup_has_one or cleanup_timeout_survives or wrapper_stop'
```

Результат: **25 passed, 64 deselected, 2 warnings, 71.94s, exit0**.
Покрыты обычный PASS, порядок container/bucket/staging, все reader failures,
same-bytes manifest/parent replacement, повторные сигналы и общий таймер,
SIGKILL до/во время cleanup для bucket/DB, завершение wrapper.

Отдельная независимая причинная проверка неизменённого fixture на этом срезе:

```text
reader-parent-replace
returncode=137
pass=False
replacement_files=['foreign-keep', 'object-manifest.json']
foreign_keep='foreign data'
```

Новых файлов в чужом parent нет; прежний P2 записи журнала закрыт. Все временные
материалы дополнительных причинных проверок удалены после завершения.
Неизменные unit/helper/native не запускались заново только ради изменения
перенаправления журнала; результаты разделены по проверенному источнику.

### Прочитанные проверки владельца и границы нативного результата

Прочитаны фактические log/JSON receipts, не только сообщение владельца:

- `.dev/growth/object-readback-pipe-full-20261103.log` и `.json`:
  **165 passed, 2 warnings, 198.53s pytest; JSON exit0,202.292s**.
  Receipt содержит пять исходных pipe hashes (до FD9); это профиль владельца,
  не собственный прогон reviewer и не полный профиль окончательного shell.
- `.dev/growth/object-readback-pipe-native-current-image-20261103.log` и `.json`:
  **exit0,26.124s**, десять pass-строк: exact, empty, same-size, missing, extra,
  gzip, gzip-exact, no-retry, network-failure, cleanup. Helper/native hashes
  совпадают с окончательной таблицей. MinIO image
  `sha256:460b46057cbcf8d01c2f7ceae9209290334b75dc1912235b10ad9bd35de056db`,
  SDK image `sha256:48a65586a6a6ceb9359372fabdb325a113f1f109709b3acfefd281ff8bf59959`.
  Reviewer самостоятельно профиль не запускал. Это учебная нативная проверка
  названных образов, не доказательство текущего image рабочего сервера.

Scoped PASS означает отсутствие открытых P1/P2 в пяти рассмотренных файлах
и закрытие причинных замечаний интеграции O1–O8. Он не заменяет convergence,
exact-SHA PR/CI/release gates, проверку фактического release override/прав secret
files/дискового запаса/здоровья узла перед операцией, нативное восстановление
каждой выбранной реальной копии, согласование её исторической полноты или
полную приёмку F273/T113/T116/T0. Старое SQL/PG staging не объявляется принятым
как новый защищённый activation operator. Рабочее восстановление/удаление
backup не выполнялись и этим отчётом не разрешаются.

### T098 — прочитано только непринятое предложение

`t098-expiry-decision-20261103.md` прочитан целиком, SHA256
`5ef9f874c058b48bacaf9e636a0da946f776404563c65fddc19bcffaf4345f01`.
Документ явно предлагает владельцу expiry2026-11-06 с конечным окном,
сохранением compatibility boundary/removal trigger/retirement и без
автоматического повторного продления. Он не является принятым решением.
Повторно прочитан spec: действующая expiry по-прежнему2026-11-03.
Документ не доказывает рабочее отсутствие rec10444, завершение T098 или
разрешение включить измерение/назначить T0. Внешнюю историю #7698 reviewer
в этом проходе не проверял; её пересказ не использован как новая приёмка.
**Отдельный release HOLD T098 сохраняется и не изменяет scoped code PASS.**

Изменён только этот отчёт. Checklist требований не изменён; прежние
10checked/0unchecked относятся к requirements review. Git/GitHub, серверы,
реальные копии и чужие файлы не изменялись. Прежние HOLD и их основания
сохранены выше как история, а не как открытые замечания окончательного среза.
