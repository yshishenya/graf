# T113/T116 — интеграция чтения восстановленных объектов, 03.11.2026

Полоса `high-risk-product`, продолжение T113/#7804 и ресурсной зависимости
T116. Локальный профиль и окончательное независимое ревью — scoped PASS,
P1=0/P2=0. Полная F273 этим не принята.
Рабочие копии не восстанавливались и не удалялись. PR/выпуска этого среза нет.

## Что изменено

Штатный `rehearse-rec-restore.sh` снимает закрытый эталон до mirror и затем
вызывает host-container проверку с rec-api image из current-override.
Проверяющий процесс получает только пять read-only mounts и существующую
частную сеть, без API/.env/БД/Docker socket. Образ закреплён полным ID,
`--pull never`, read-only root, UID/GID оператора, cap-drop и no-new-privileges.
Нативное чтение сверяет полное множество объектов, размеры и SHA256 каждого
потока без HTTP-декодирования; источник и private manifest проверяются до/после.
Прежние БД/SQL/аргументы scheduled caller сохраняются.

Свой контейнер удаляется только после проверки имени, image, label и полного
ID. Маркер cleanup создаётся после подтверждения отсутствия контейнера,
проверки identity манифеста и родителя, через удержанный parent FD.
Shell дважды сверяет inode/UID/mode собственного staging. Журнал удерживается
одним исходным FD9; последующие команды не открывают commands.log по пути,
который мог быть подменён. FD9 отделён от lock/notification FD проверкой wrapper. Подменённый каталог
с чужим файлом не удаляется; неизвестные цели сохраняются и не дают PASS.

Чтение ограничено600с. Один абсолютный монотонный срок cleanup60с сохраняется
в закрытом create-only control file и повторно используется shell; смерть
supervisor не начинает новый бюджет. Уведомление идёт по унаследованному pipe,
не по PID. При SIGKILL supervisor резервный watchdog использует остаток того
же срока и может завершить только свою изолированную группу процессов.
Завершение локальных CLI не считается остановкой Docker daemon: timeout
всегда FAIL/resources_unverified, оставляет остатки и запрещает переход ко
второму комплекту до разбора. Сигналы HUP/INT/TERM во время cleanup не прерывают
его проверяемые действия и исключают успешный результат.

## Новые причинные проверки

Прежняя история ошибок сохранена в независимом отчёте и частных журналах:
повторный InterruptedError мог поглощаться selectors; неизвестное второе
communicate ошибочно разрешало proof; JSON без identity принимал подмену
манифеста; прежний shell cleanup был неограниченным и прерывался сигналом.
Добавлены отрицательные случаи для каждого дефекта, source drift во время
cleanup, foreign parent/foreign-keep, неизвестного CLI, create collision,
отказов inspect/rm/readback и обоих тайм-аутов. На Mac directory nlink может
измениться при создании собственного control file; для parent сверяются
dev/inode/mode/UID/GID, а полная identity манифеста остаётся строгой.

Первый полный профиль выявил также устаревшую подготовку objects-link:
rmdir непустого дерева. Фикстура теперь сохраняет исходное учебное дерево
через rename. Поздний профиль выявил слишком ранний учебный alarm: он мог
сработать до входа в readback. Учебный таймер теперь привязан к фактическому
входу в фазу; production600с не менялись. Проверка смерти supervisor
включает момент ДО и ВО ВРЕМЯ reader cleanup, расход1,1с из учебных2с и
последующий timeout bucket/DB. Новые unit случаи отклоняют неизвестный,
не конечный, длинный, связанный или доступный посторонним deadline.

## Окончательные результаты локальных проверок

- unit + synthetic shell + backup regression окончательного FD9-среза:
  **165 passed, 0 failed, 0 skipped, 2 warnings, 201.27с pytest, exit0**.
  Полное время runner205.035с; хеши пяти файлов до/после совпали.
- Настоящий MinIO: **9 сценариев PASS и cleanup PASS; exit0**.
  exact1003objects/Unicode/пробелы/нулевой файл, пустая корзина,
  same-size/missing/extra/gzip mismatch, точный gzip, HTTP301/503 без retry,
  остановленный MinIO. Host orchestrator и маркер очистки исполнены реально.
- MinIO image `sha256:460b46057cbcf8d01c2f7ceae9209290334b75dc1912235b10ad9bd35de056db`.
- SDK image `sha256:48a65586a6a6ceb9359372fabdb325a113f1f109709b3acfefd281ff8bf59959`;
  отдельным запуском подтверждены Python3.13.14/minio7.2.20/urllib3 2.7.0.
  Прежний локальный b52eb... отсутствовал при свежем inspect; этот отказ
  сохранён, не выдан за skip или дефект checker. Новый образ уже установлен;
  сборки/загрузки не было. Рабочий server image не подменялся.
- Все собственные native контейнеры/тома/сеть/учебные файлы очищены.
  До последних проверок на Mac146GiB свободно.
- Ruff, sh -n, git diff --check, fragment validator PASS.
- Frozen Spec Kit doctor PASS в своей временной среде specify1.0.7;
  глобальные инструменты не менялись. Среда удаляется после проверки.
- Общий development-process **HOLD**: прежнее исключение T098 истекло03.11.
  Pointer не удалён, срок и classification не менялись. Отдельное конкретное
  [предложение решения](t098-expiry-decision-20261103.md) не является согласием
  владельца или закрытием T098. Выпускные ворота сохраняются.

Частные безопасные журналы и JSON с exit/временем/хешами:
`.dev/growth/object-readback-pipe-full-20261103.*`,
`.dev/growth/object-readback-held-log-full-20261103.*` и
`.dev/growth/object-readback-pipe-native-current-image-20261103.*` в кодовой копии.
Независимая история: [integration review](t113-object-readback-integration-review-20261103.md).

## SHA256 окончательного кода

| Файл | SHA256 |
| --- | --- |
| `infra/scripts/rec-object-verify.py` | `4acb585b6e83f13dce5ed4c57977ce2e8c4ef8118a0e3b4f1849efae327a39e1` |
| `infra/scripts/rehearse-rec-restore.sh` | `bf5fe1c6f9944ea9454c3eeaf66225dd0c4abcc4e0044b9567ec07e82f0d7af7` |
| `apps/server/tests/unit/test_rec_object_verify.py` | `1a3fa14224eac038017a699470c583adf965324d3186122ce88d123390cbc3e0` |
| `apps/server/tests/integration/test_deployment_restore_safety.py` | `5be97f667202dd35582c96c882d9d9c8f62d48d896283674ee08c8402ada3776` |
| `apps/server/tests/integration/test_deployment_object_restore.py` | `7f633e320f7970c6100c0a6990170140c0677ab1acaf877da2d786ff89497869` |

## Следующие отдельные ворота

Scoped convergence O1–O8 не выявила новых buildable gaps; существующие
открытые рабочие и выпускные задачи не дублировались. Требуются полная приёмка
T098 без продления исключения (решение владельца03.11), свежая master и
exact-SHA PR checks, защищённое слияние и общий штатный
выпуск. Затем свежий расчёт DB/WAL/staging/объектов/inode и две поочерёдные
настоящие проверки `20261101T151338Z` и `20261101T173314Z` с cleanup/health
до второй. Только после этого — окончательное отдельное решение по точным38
кандидатам на удаление под общей блокировкой. Большую F273-ветку не сливать.
Полная F273/T113/T116, измерение/T0, Product Radar и коммерческие AC открыты.
