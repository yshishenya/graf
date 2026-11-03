# F273/T113: независимое ревью остановки репетиции — 28.10.2026

**Текущий результат: SCOPED PASS локальной реализации безопасности репетиции.**
P2 закрыта собственными причинными проверками с настоящим Python-supervisor.
Открытых critical/high/medium замечаний текущего узкого среза:0/0/0.
Reviewer самостоятельно выполнил56тестов: PASS,2прежних предупреждения,40.48с,exit0.
Требования четырёх списков после повторного чтения:117подтверждено/0открыто.
Это не приёмка полного T113, рабочего restore/writer, выпуска или роста.

Проверяющий activation_requirements_gate. Полоса high-risk-product,
существующая F273/T113. Перед кодом основания прошли независимый PASS:
[полная матрица117пунктов](t113-rehearsal-safety-review-2026-10-28.md).

## Точный проверенный источник

Локальная реализация поверх `fa40b08263f215730edbb575f2595113703f9950`.
Хеши считаны до и после собственных проверок; helper/test не менялись:

```text
6cb9de1f54dd1e46b79015fc81a7a70e8568cda64e4e5abfea52960754c0cd83  infra/scripts/rehearse-rec-restore.sh
ccd88833016ecc60344044c3da3a7cc3fd8c19956edb66138829bd0d7ef6027e  apps/server/tests/integration/test_deployment_restore_safety.py
442de7807675b906454660eaec43f5682aa901e5fac85732813679b80739fb37  apps/server/tests/integration/test_deployment_backup_restore_rehearsal.py
c2077aa210364e3a50b1c78a536fc000d0b9e93617c6729d901d5a574b0e6ad9  specs/273-paid-traffic-analytics/quickstart.md
```

Quickstart дополнение прочитано целиком:12случаев create-stop,3early-Popen,
настоящий интерпретатор и ограниченное окружение согласованы с узкой областью.
Полный schema/roles/RLS/ledger/deletion verifier им не заявлен.

## Что принято в коде

- HUP/INT/TERM handlers устанавливаются до Popen. Пока child отсутствует,
  ограниченный set сохраняет номера pending; после запуска они передаются child.
  При child!=None handler не меняет set, поэтому iteration не мутирует коллекцию.
- Передаётся исходный номер сигнала; INT→TERM normalization и polling отсутствуют.
  Сохраняются pass_fds того же flock, ожидание child и ненулевой исход остановки.
- Shell временно запоминает stop только вокруг create→owned. Успешный create
  успевает подтвердить владение до возврата обычного exit-trap и проверки stop.
  Failed create через set-e уходит в cleanup без owned=1; чужая цель не удаляется.
- Прежние cleanup-before-PASS, отдельный readback отсутствия, закрытые права,
  общая блокировка и выбор пригодного комплекта не ослаблены.
- Fixture явно закрепляет bin/python3 на sys.executable текущего тестового
  процесса, исключая PATH-launcher; окружение содержит PATH/LANG и учебные поля,
  без произвольных ключей оператора. Диагностика pytest не получает весь os.environ.
- В15новых случаях проверяются все12create-stop сочетаний и3сигнала до child;
  унаследованный SIG_IGN в create-stop воспроизводится намеренно.

## Собственная причинная матрица:12/12 PASS

Reviewer отдельно использовал TemporaryDirectory, текущую ограниченную fixture
и временную копию helper точного хеша выше. Успешная подставная команда сначала
создаёт маркер своей DB/bucket, ошибочная — маркер чужой цели; **затем** ждёт
разрешения вернуть0/7. Это усиливает обычный тест: цель уже существует при stop.
Для каждого прогона bin/python3.resolve совпадал с sys.executable.resolve,
а ps-команда PID supervisor показывала Python, без uv. Номера сигналов
направлялись именно этому PID; унаследованный INT перед запуском был SIG_IGN.

После stop reviewer попытался запустить вторую репетицию до разрешения create:
она всегда получала deployment_or_rehearsal_running. Затем первая команда
заканчивалась, и reviewer проверял отсутствие DB/bucket/staging, сохранность
foreign/unrelated и отсутствие PASS. Прочие внешние состояния не использовались.

| Цель | Исход create | HUP | INT | TERM | Общий итог |
|---|---|---|---|---|---|
| DB | successful | exit1 | exit1 | exit1 | свои ресурсы отсутствуют; блокировка удержана; PASS нет |
| DB | failed | exit7 | exit7 | exit7 | чужая цель сохранена; своих остатков нет; PASS нет |
| bucket | successful | exit1 | exit1 | exit1 | свои ресурсы отсутствуют; блокировка удержана; PASS нет |
| bucket | failed | exit7 | exit7 | exit7 | чужая цель сохранена; своих остатков нет; PASS нет |

Все12случаев также проверили отсутствие staging и сохранность unrelated.
Ни Docker daemon, ни сеть, ни серверы не вызывались. Учебные процессы завершены,
TemporaryDirectory удалены. Рабочие копии/данные не создавались и не удалялись.

## Собственная контрольная red-матрица исходной версии

Для исключения ложного исправления reviewer повторил шесть successful-create
случаев на helper из Git SHA fa40b08263f215730edbb575f2595113703f9950,
SHA-256 e5e80974aedc72e4a7b4a9fbd66f49b33df2d7634b098509acdc79e1b6ae3756,
с тем же закреплённым настоящим Python и проверкой PID. Ожидание также после
создания цели, до возврата0; inherited INT=SIG_IGN. Результаты:

| Цель | HUP | INT | TERM |
|---|---|---|---|
| DB | exit1; DB осталась | exit0; PASS, stop потерян | exit1; DB осталась |
| bucket | exit1; bucket остался | exit0; PASS, stop потерян | exit1; bucket остался |

Так исходная P2 подтверждена причинно в правильной среде. Отличие нового кода
закрывает эту гонку, а не только меняет интерпретацию прежнего launcher.

## Собственный объединённый профиль

```text
apps/server/.venv/bin/python -m pytest -q apps/server/tests/integration/test_deployment_restore_safety.py apps/server/tests/integration/test_deployment_backup_restore_rehearsal.py
56 passed, 2 warnings in 40.48s
exit_code=0
```

Это32случая restore-safety(17прежних+15новых) и24прежних backup/restore.
Включены ordinary concurrency, supervisor TERM/KILL, collision/foreign targets,
cleanup/readback failures, selection, права, ранняя остановка и12create-stop.
Два предупреждения — PytestAssertRewriteWarning и StarletteDeprecationWarning.
Собственный результат независим от переданного исполнителем56PASS/41.35с.

## Исправление вывода промежуточной диагностики launcher

Ранее в незакреплённой учебной среде PATH-python3 на Mac оказался shell-wrapper
с uv run и переключением проекта. Reviewer независимо подтвердил тип shell
script и наличие uv/project switch, не публикуя закрытый путь другого проекта.
PID Popen относился к launcher, настоящий Python-supervisor был его потомком.
Следовательно, прежние поздние INT, exit143/остатки и55/56 не доказывали дефект
доставки сигнала именно исправленного helper. Предыдущий промежуточный HOLD
в этом отчёте отменён после проверки среды и собственных правильных проб.

Для истории: временная версия с INT→TERM имела hash
88255367ac3a5690333a8ac6427b9b937b67eec8560fe782dfe3c489d9b27a43;
в незакреплённой среде наблюдались exit143 и DB/bucket/staging. Временный
опыт wait(timeout=0.1) с паузой0.2с менял timing launcher и давал положительный
исход; он не устанавливал причину в helper. Ни normalization, ни polling
не нужны и не входят в принятый код. Системный launcher reviewer не менял.

## Повторное чтение и границы приёмки

Все117вопросов четырёх списков и новые reviewer-records перечитаны после записи.
Итог требований requirements16/0, security27/0, infra29/0,
privacy-measurement45/0, всего117/0. Для текущего локального кода замечаний
critical/high/medium0/0/0. Файлы, ссылки и пробелы отдельно проверены.

Полный schema/roles/RLS/ledger/deletion verifier, readiness/fence/local_only,
настоящий actual restore, T112, T113 целиком, PR/CI/release/runtime и коммерческие
показатели этим SCOPED PASS не приняты. analyze/converge и выпускные ворота
основного исполнителя сохраняются. Доказательства доступны в Git без ignored logs.

Reviewer изменил только собственные отчёты и четыре списка независимой проверки.
Код/spec/plan/tasks, Git/GitHub, CI/CD, серверы и чужие рабочие изменения
не затронуты. В отчёте только безопасные учебные результаты и хеши.
