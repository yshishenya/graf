# T113 — независимое ревью проекта operational files, 30.10.2026

Вердикт: **SCOPED PASS до кода**. Блокирующих пробелов проекта в заявленной
границе не найдено (P1=0, P2=0). Можно реализовать этот участок существующей
F273/T113/#7804 в полосе `high-risk-product`, сохраняя перечисленные ниже
условия. Это не приёмка реализации, рабочего состояния, полного preflight,
хранения, lifecycle, T113 или выпуска.

Проверенная база: `0817654a05a84d9d8570ee774cdb7b4559900954`.
Рабочая копия перед ревью чистая. Проверен проект
`.dev/growth/t113-operations-precode-20261030.md`, SHA256
`3249d34bd1bd07c495dbf79f7bc59d5bf71f72ed8d637e28cdd9599803f29006`, и
уточнения исполнителя о границах v2/lifecycle, удержании обоих directory FD,
финальном времени и равенстве operational proofs всех running writers.
Полный принятый проект оператора остаётся прежним:
`t113-full-operator-design-20261030.md`, SHA256
`5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec`.

## Выбранный минимальный способ чтения guard snapshots

В существующий `runtime_guard_blockers` достаточно добавить один необязательный
именованный параметр `protection_state_file: str | None = None`. При `None`
остаётся прежнее чтение `protection-state.json` из выбранного guard directory.
При явно переданном пути reader читает именно этот путь; пустой/недоступный
явный путь не должен переключаться на default и давать готовность.
Все прежние проверки формата, recorded/sample age, inventory/budget,
deadline, protection status/reasons и latch сохраняются буквально.

В `_runtime_operations` alert snapshot задаётся существующим
`GRAF_ANALYTICS_GUARD_STATE_FILE` в отдельном explicit environ, protection
snapshot — новым параметром. Оба пути указывают на запечатанные memfd, их FD
живут до выхода контекста. Новый каталог файловой системы, новая переменная
среды и второй API разбора текста не нужны. Фразу проекта о «том же каталоге»
понимаем как текущую связанную схему двух исходных guard files: сами memfd
не обязаны быть соседними файлами; новый параметр устраняет эту зависимость.
Остальные вызовы reader сохраняют старую сигнатуру использования и defaults.

## Условия принятой реализации

1. У `_bound_runtime_file` режим `directory_bind=True` явный; прежний exact-file
   bind остаётся default. По actual mounts принимается ровно один RO directory
   bind — предок логического файла, без overlap и вложенного другого mount.
   Source вычисляется из actual Source и относительного пути. Каноничность,
   protected ancestry, ACL, владельцы и права проверяются до чтения. Символическая
   ссылка `/proc/PID/root` является только уже предусмотренным первым переходом;
   следующие компоненты пути не обходят `O_NOFOLLOW`.
2. Открыты оба source/proc-root directory FD и оба file FD; совпадает directory
   identity и точная file identity+bytes. Для каталога достаточно первых пяти
   полей `_settings_file_identity`: dev/ino/uid/gid/mode. Изменение mtime/size
   каталога при штатном atomic replace соседнего файла не является само по себе
   причиной отказа. Leaf-файл сохраняет полную identity, single-link, предел
   64 KiB, owner 0/1001, mode 0600/0640 и возможность чтения actual процессом.
   Путь/каталог/файл повторно открываются и сверяются при выходе: удержанный FD
   сам по себе не доказывает, что текущий путь всё ещё ведёт к тому же объекту.
3. Все пути четырёх файлов выводятся из `_runtime_environment(row)` и существующих
   path helpers/defaults. Host environ не участвует ни в выборе файла, ни в
   readers. Strict local_only конфигурация проверяется существующим методом
   Settings вместе с enabled/legal/disclosure. Исходные actual Env не заменяются
   данными другого writer. Четыре memfd служат только способом передачи уже
   проверенных байтов существующим readers.
4. Legal register доступен, без file_errors и без withdrawal уровня
   `attribution_profiles`. Дополнительно обязателен успешный
   `parse_disposition_cases(text, now=<aware UTC>)` формата v2; v1 не разрешает
   этот proof. Этот разбор подтверждает корректность/отзыв, но не исполнение
   accepted/applied/failed cases, сроки удаления, lifecycle coverage либо
   отсутствие остатков в БД. Будущая проверка через retained source,
   `_backup_lifecycle` и точные remnant queries остаётся обязательной.
5. Access reader и `access_governance_blockers` получают explicit environ и
   свежий `now`. Доверенное expected значение — `sha256:<64 hex>` от закреплённого
   `infra/scripts/posthog-runtime-guard.sh`, равное хешу фактического
   `/usr/local/libexec/graf-posthog-runtime-guard.sh`. Одного произвольного
   expected из Env недостаточно. Если это значение присутствует в actual Env,
   оно не может противоречить вычисленному expected. Installed script обычный,
   single-link, root 0755, без ссылок/ACL, с защищёнными root ancestors; FD,
   identity и bytes удерживаются и сверяются до выхода. Размер текущего исходного
   скрипта 28671 байт совместим с ограниченным чтением. Три digest access record
   должны совпасть с expected; нужны актуальные reviews, ≥2 оператора и MFA
   каждого принятого оператора. Metadata record не доказывает live membership
   и не принимает UID1003 в доверенную группу bootstrap.
6. Guard reader должен вернуть пустой набор blockers. Сохраняются границы
   `0 <= sample/recorded age <120s`, future rejection, budget expiry и latch;
   «причины исчезли» не снимает закрытое protection состояние. После последнего
   await на выходе контекста readers вызываются заново со свежим временем и
   повторяется сверка исходных bytes/identity. Даже штатная замена guard file
   в этом окне приводит к HOLD и новому полному запуску проверки.
7. `_runtime_preflight` удерживает operations contexts каждого actual running
   writer вместе с Settings/secrets/DB через финальные inspect/process/network/
   release/head/policy проверки. Proof каждого writer содержит только digest
   content/source identity четырёх файлов и installed guard hash; proofs всех
   running writers должны совпасть. Две независимо валидные, но разные копии
   реестра/access/guard не составляют один согласованный proof. Actual mounts
   уже связаны с aggregate runtime proof. Наружу остаются те же четыре поля;
   operational details входят только в `runtime_sha256`, без raw paths/IDs/cases.
8. Финальный исходный monotonic deadline после полного cleanup сохраняется
   ниже выхода всех контекстов, как в текущем DB срезе. Раннее создание result
   внутри контекста не допускает return до проверок при выходе. Исключение,
   отмена, reader/cleanup/identity/time failure не дают runtime verified.

Это условия уже заявленного проекта и его уточнений, а не новый механизм
готовности или исключение из проверок. Реализация потребует независимого
проверочного ревью и причинных отрицательных проб.

## Граница и оставшийся объём

В текущем Compose найден guard RO directory mount у `rec-api` и его Env.
Наличие legal/access/guard mounts и Env у всех требуемых writers ещё предстоит
согласовать в последующем объёме; default host path не становится доступным в
контейнере сам по себе. Этот этап должен отказывать при отсутствии actual bind,
а не подставлять host file. Runtime этим ревью не изменяется.

Сверка одного installed guard script не принимает все installed jobs,
config/helper files или фактический режим хранения. Полные local-retention
SQL/schema/trigger/jobs, category coverage четырёх таблиц, lifecycle reconciliation,
backups/restore/initial/ready, верхние операции, actual restore/resume и CD остаются
открыты. Текущие `activation_recovery_unverified` и bootstrap
`full_preflight_not_implemented` сохраняются безусловно. Рабочих T0/ready,
IP/аналитики/получателей, внешних отправок, выпуска и закрытия T112/T113/#7804
это ревью не разрешает и не подтверждает.

## Что проверить после кода

- Совместимость default guard reader и старого exact-file Settings пути;
  явный protection path меняет только источник байтов, не проверки.
- Missing/malformed/v1/withdrawn legal; актуальный и просроченный access,
  ложный expected/installed digest, неподтверждённая группа; stale/future guard,
  budget boundary/expiry, latched protection.
- Actual RO directory bind, каноничность/ACL/ancestry/право чтения процесса,
  symlink/hardlink, source/proc-root inode mismatch и overlap; замена файла и
  каталога в lifetime; отсутствие отказа только от mtime соседнего atomic update.
- Разные валидные operational копии двух writers; host environ poison;
  истечение sample/access/budget после await; reader/cleanup failure и общий
  deadline после освобождения DB и файлов.
- Настоящие Linux directory bind, memfd seals и FD lifetime на собственном
  изолированном стенде с очисткой. Учебные проверки не становятся рабочим PASS.

Тесты, Docker, SSH, production/Dev и Git/GitHub mutations в этом ревью не выполнялись.

## Проверка требований и неизменности

Повторно прочитаны все 117 строк вопросов четырёх reviewer-owned checklist.
Маркеры не менялись. Это проверка качества требований, а не число принятых
операционных тестов:

| Checklist | Отмечено | Открыто | SHA256 |
| --- | ---: | ---: | --- |
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |
| Всего | 117 | 0 | Маркеры без изменений |

По разрешённому исключению F273 подтверждены прежние четыре baseline hashes;
полное повторное чтение PRD/истории статуса не имитируется. Перечитаны затронутые
целые разделы spec (functional/extra requirements), plan (T113 local period и
полный оператор), operations (guard/resource, retention/access, readiness,
lifecycle/local period), activation-milestones (local period/settings/readiness/
locks), quickstart (degradation и local period), текущие заметки T113 tasks и
применимые readers/binding/context/cleanup функции. Baseline hashes:

| Документ | SHA256 |
| --- | --- |
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current-product-status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| spec | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| plan | `02f4b52274c61fdf69f01415448a28d9509a1c12274a09d5a7382d3fc3db1b19` |
| tasks | `09b008e44b51c0820aac6d090053f70d7d6902fb3aa5e5f8c300f2f9f49d9481` |
| quickstart | `5bde6a5f388a03b6df1440fca32429f49bd458fdf9203fdc8df880352d249fea` |
| operations contract | `7d68aa7dc06b170508cd8b2858ede6e3e929b2e7155cd03b0895e715cb2b3abb` |
| activation-milestones contract | `9898007a0e87400246f8c95b899dd807fab0424472143e15338429873982f3f9` |

Проверенные исходники до реализации:

| Файл | SHA256 |
| --- | --- |
| activation_operator.py | `6c2144a01a4b20a4fa3d89e13ecb54b34fec457cee5f1d2e0d64b27e4c380cef` |
| provider_readiness.py | `265cbd6a53ea08d83990bbacdd9416c74b266d2716837d3ebc193d2d64672a44` |
| access_governance.py | `a85f47c42bedf1978706d4b38420b9d11728c3b6ae43809944fd312c470a8b95` |
| legal_basis_lifecycle.py | `ac4eb465afb0c647b0d3501bdbeaca2a8a4b1d9c6cad59d4c9a9953cae5f81f9` |
| infra/scripts/posthog-runtime-guard.sh | `144884c16255ffe9b87d2c08cb2413f0d525fc33a6ace1650e46f72678d8bfaa` |
| infra/scripts/activation-operator.py | `e11efddb4001602014977be3dff5e86550978cf81bfe67f23d7ae60a0bdfbfb5` |
| infra/docker-compose.yml | `9098cb15c8c4a675beae529664e128d46a2dc50671dee8171d05b659b482bcc6` |

Перед передачей отчёт перечитан целиком; итоговый hash передаётся отдельно,
чтобы самоссылка не меняла проверенные байты.
