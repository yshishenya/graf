# T113: независимое ревью кода чтения завершённых копий

30.10.2026. Проверяющий `/root/f273_release_boundary`, исполнитель `/root`.
Основа `6524c1de4a2c199aed365947c2d54adba5370d4e` и зафиксированные локальные
байты; F273/T113/#7804, полоса `high-risk-product`.

## Решение

**SCOPED PASS `_read_coherent_backup`, `_verified_backup_set` и связанных
проверок на финальных SHA256 ниже. Неустранённых блокеров в этой области
не обнаружено.** Найденные при первоначальном чтении R1–R3 исправлены;
финальные код, тесты и завершённые журналы независимо прочитаны и сверены.

Реализация сопоставлена с полностью прочитанным precode SHA256
`397b1a12dc62efea5c14b1c03dbf5cbefee2a9ba604c22c68231892baaf75e44`
и [проектным ревью](t113-backup-verification-design-review-20261030.md),
SHA256 `22e575d258609347729e2244f8dce2da4fec8dbb3637655da5796acc7b1bb1a5`.
Прежний общий проект оператора сохраняется. Данный PASS не принимает всю
T113, верхний вход/initial/ready/T0, actual restore/resume или выпуск.

## Исходные замечания и исправления

**R1 — нестрогое сравнение типов native metadata.** Обычное Python equality
принимало manifest snapshot format_version=2.0 за вычисленное целое2.
Это нарушало точный producer contract даже при пересчитанном latest digest.
Теперь сравниваются детерминированные JSON digests всего metadata объекта:
2 и2.0 дают разные значения. `float_metadata` изменяет именно это поле и
требует HOLD. Исправление не нормализует повреждённый JSON в допустимый.

**R2 — потеря идентичности selected directory после чтения.** Первоначальный
reader проверял root inode внутри одного чтения, но set сохранял лишь
содержимое. Замена уже выбранного companion каталогом с теми же bytes
могла пройти финальное сравнение. Теперь reader возвращает private dev/ino,
а финальный selected loop заново проверяет type/owner/mode и эту identity
вместе со всеми bytes. `replaced_companion` после настоящего чтения
переименовывает каталог и копирует его на прежний путь: содержимое то же,
inode новый, ожидается HOLD.

**R3 — неконечный отказ на глубоко вложенном JSON.** Повреждённый manifest
с глубиной10000 мог выпустить `RecursionError`, который не входил в прежний
перечень обработанных ошибок. Обе новые внутренние границы теперь переводят
его в фиксированный `ActivationHold` без исходного содержимого. Тест
`deep_manifest` проверяет и тип отказа, и допустимый конечный код. Исполнитель
зафиксировал причинный1FAIL до исправления; финальный unit профиль прошёл.

Все три замечания сообщены до приёмки. Первоначальный вариант со старыми
SHA256 не объявляется принятым по последующему зелёному общему журналу.

## Проверенная реализация и границы доверия

Reader принимает фиксированный backup-UUID private root0700/euid/no symlink.
Полный `_file_manifest` проверяет типы, права, ссылки, ключи, размеры и все
SHA256. Raw manifest читается `private_bytes` с пределом его фактического
размера, а его digest совпадает с прочитанным физическим файлом. Нет
неподходящего ограничения16К/10MiB. `_object` запрещает duplicate keys.

Проверяются ровно20 version1 полей producer, integer version, run UUID/name,
binding grammar, UTC times в правильном порядке и не из будущего,
cleanup=confirmed, exact code keys/digest grammar. Artifact/object entries
строго списки из key/int-size/hash, отсортированы, уникальны, без file/prefix
collisions и неоднозначных UTF8/NFC ключей. Bool не считается int. Artifacts
совпадают со всеми физическими файлами кроме manifest, objects — с точным
minio-objects subset, count/bytes пересчитаны. Каталог объектов обязателен
и при нулевом count. Native `_backup_metadata` заново проверяет реальные
artifacts и возвращает header/schema/revision/roles/ledger/inventory;
сохранённые значения строго совпадают с вычисленными. Повторяются полный
byte manifest и root identity до возврата.

Set читает собственный bounded latest-attempt, проверяет exact prior schema,
completed, trusted current binding, настоящий destination manifest digest
и равенство finished_at. Свежесть строго `0 <= now-finish <26ч`, по одному
внутреннему UTC DB clock. Missing/failed/in_progress/unknown/future/26ч не
маскируются двумя старыми копиями. Attempt bytes, fence identity/revoked
и parent identity/owner/mode сверяются до/после. Родитель открыт nofollow
и удерживается FD до finally; каталожный mtime не определяет latest.

Companion выбирается детерминированно среди distinct UUID names. Каждый
candidate проходит те же physical/native проверки; invalid/incomplete
старый candidate исключается, а ошибка parent или общий deadline дают HOLD
всего набора. После выбора обе копии ещё раз проверяются по bytes и inode.
Два одинаковых run UUID не принимаются за два комплекта. Исторический
допустимый binding companion разрешён как полная точка той же canonical DB
в доверенном parent, а latest обязан соответствовать текущей установке.

Эти функции ничего не удаляют и не chmod, не открывают DB/provider и не
принимают внешних callback/pass/SQL. Trusted caller удерживает deployment/
filesystem EX, фиксированную установку, capacity и общий deadline. Native
integration вызывает set через `_settled_sql(asyncio.to_thread(...))`,
поэтому чтение остаётся во владении до завершения. Верхний рабочий caller
ещё относится к остатку общего оператора; тестовый вызов не выдаётся за
установленный initial/verify. Reader не заменяет current lifecycle/code
matching, rehearsal<=30дней, rehearsed reference, ротацию или admission.

## Причинные проверки и точные версии

Основной профиль на загруженных до исправлений operator `a15f320…`, unit
`e210250…`, integration `5697fc…` завершился **201 passed, 2 warnings,
493,56 с**, exit0. Он подтверждает общий исходный набор, но не финальные
изменения R1–R3.

На финальных байтах выполнены отдельно:

- полный unit operator: **88 passed, 2 warnings, 1,77 с**, exit0;
- native две coherent copies → reader → прежний restore/replay/COMMIT/
  новое physical reduced readback/cleanup: **1 passed, 38 deselected,
  2 warnings, 15,85 с**, exit0.

Итоговая совокупность — **204 уникальных случая,86 повторов**. Это не один
общий прогон204 на финальном SHA. Все новые reader paths проверены полным
финальным unit и повтором native успеха; исходники существующих стадий
producer/rehearsal при этом не изменялись. Предупреждения прежние: pytest
fixture module уже импортирован и deprecated httpx в Starlette TestClient.

Unit fixture намеренно подменяет native metadata, проверяя строгий parser
и physical byte contract. Матрица включает нехватку двух копий, failed latest,
malformed/duplicate/extra fields, bool/count/bytes/artifacts/keys, native
metadata mismatch, current binding, future/26ч, parent link, changed attempt,
deleted/replaced companion, same-size object/dump corruption, extra файл,
invalid старый candidate, исторический companion, digest и deadline,
а также R1–R3. Такой unit не выдаётся за native metadata proof.

Native proof создаёт первую настоящую coherent copy и подтверждает отказ
set при одном комплекте. Затем создаёт вторую, читает оба настоящим native
verifier без metadata mock, сверяет latest/companion/digests. Выбранная
latest проходит существующий native restore, пониженный replay, COMMIT
и физическое новое чтение. Initial/T0 не создаются, готовность отозвана.
Собственные стенды удалены по сообщению исполнителя; ревьюер Docker
и серверные команды не запускал.

## Контрольные суммы и оставшиеся ворота

| Файл | SHA256 |
|---|---|
| activation_operator.py, финальный | `cf7a6d1107eb6c5c7c58e3db88a9b571bd51b32b8d558ca82e55cbdc3a91fabd` |
| test_activation_operator.py, финальный | `687ddcc2e585274f4af184b9a0cd40f8e8097407ebb5c11f2f194740cdf91da1` |
| test_activation_restore_replay.py | `5697fc9787e8a4dd0a7b992f01afd263db54de6cb21be4812a9f45129e3820e6` |
| .dev/growth/t113-backup-reader-final-profile.log | `e32e5b0254b2cac8541d2de2f1ac8f8f3135f702df1db43107a95dff03f06de1` |
| .dev/growth/t113-backup-reader-final-unit.log | `ff476f5c07f2ae19ac601dfe898d27c5d0ce434a4a794ac7bde9d53c048d9e91` |
| .dev/growth/t113-backup-reader-final-native.log | `a7753966fe575bef7097d078e7097a17e170c1fdbd478087058ec2b24e12d30f` |

Неизменные требования и все117 вопросов перечитаны/сверены в предшествующем
проектном ревью: requirements16/0, privacy45/0, security27/0, infra29/0.
Checklist state не менялся и не является приёмкой продукта. Два учебных
комплекта не подтверждают два рабочих комплекта или capacity рабочего узла.

Перечитаны последние status-добавления: tasks.md SHA256
`8b98cf6be36e549b52aabe3c6959fac27fd1560288cc43ad0cfa5f89a88bc059`,
organic-growth-plan.md `e85341ed9e0138de39014fb2dc84b6f3ab2dc68508280f066f89bc8a711f3ddd`
и F273.yaml `ca85dea9aba17c7d964e916ec501a3765c4e7ac980520a62666a19322543f014`.
Они фиксируют локальный прогресс и оставляют общий оператор/рабочее
измерение открытыми; новых обязательных задач или требований не добавляют.

Рабочие initial/T0/ready, trusted верхний вход, current proof/rehearsal,
actual restore/resume, ежедневные retention/access/resource проверки,
ротация, shell delegation, CD/rollback и T112 остаются открытыми.
Локальные результаты не подтверждают GitHub CI точного PR SHA, выпуск,
включение аналитики/IP, внешние посещения, клиентов или продажи.

Ревьюер создал только этот отчёт. Код/spec/plan/tasks/checklist/governance,
Git/GitHub/runtime не менял, тесты/SQL/сборки/серверные команды и выпуск
не запускал. Чужие изменения сохранены.
