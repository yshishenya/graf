# T113: независимое precode ревью стадий rehearsal

30.10.2026. Проверяющий `/root/f273_release_boundary`, исполнитель `/root`.
Основа `29d1c67f9d5447228295406054eb4b4ce2583bbe`, F273/T113/#7804,
полоса `high-risk-product`. Назначение — конкретизация принятого полного
алгоритма, без изменения целей или рабочего состояния.

## Решение

**SCOPED PASS конкретного проекта стадий `_rehearsal_resources` для
реализации. Блокирующей неопределённости алгоритма не обнаружено.**
Готовая реализация или новые рабочие доказательства не требуются как условие
этого проектного PASS. Код стадий, причинные тесты и их независимый обзор ещё
впереди. Этот PASS не подтверждает верхний operator/CLI, T0/readiness, actual
restore, рабочее расписание, выпуск либо завершение T113.

Полностью прочитана `.dev/growth/t113-rehearsal-stages-precode-20261030.md`,
SHA256 `b8460c488b78f9ab31fb659272a0ab1f9294462428ba69c335289440500fe9c0`.
Она конкретизирует R2 принятого 473-строчного проекта с неизменным SHA256
`5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec`.

## Почему алгоритм достаточен

Входы внутренние и привязаны к одной проверенной установке: owner в postgres,
container/cluster/network/image IDs, закрытая копия/secret files, SDK и общий
deadline. Подготовка проверяет файлы/права/отсутствие ссылок, настоящий
`rec-db-verify --inventory` и совпадение PostgreSQL identity через оба пути.
Роли, grants, HBA или runtime secrets при этом не ремонтируются.

Порядок native стадий выбран однозначно: UUID DB limit0 → pg_restore;
отдельная UUID schema DB limit0 → native schema parse; закрытый container
staging → capture обеих целей → копирование и проверка metadata → прежний
полный native verifier. Затем собственный UUID bucket и native mirror из
read-only копии. До yield выполняется byte readback либо оно завершается
внутри того же staged lifetime. Replay/точные удаления/COMMIT/новое физическое
пониженное readback происходят до finally, не после удаления целей.

Прочитан весь текущий `rec-db-verify.py`, включая source/target/schema сравнение,
и соответствующие native стадии shell. Новый путь переиспользует их проверку
полной схемы/ролей/count/states, не заменяя её `count>=0` или произвольным
pass receipt. Связность **live source и копии** отдельно остаётся обязанностью
верхнего controlled export; одна успешная sandbox репетиция её не доказывает.

Владение и отмена имеют конкретный исход: один owner prepare task разрешается
до возврата отмены; успешный create фиксирует OID/ownership до обработки отмены.
Неизвестный create не даёт права DROP лишь по похожему UUID-имени. Он оставляет
HOLD и материал для incident пути верхнего оператора. Finally защищён от
повторной отмены; проверяет текущий name/OID перед DROP без FORCE и затем
отсутствие ресурса. Admin идёт через `postgres`, не закрытую рабочую БД.
Caller закрывает все source/target replay-сессии до выхода из context.
Очистка bucket/staging ограничена подтверждённым владением. Продление времени
ради завершения cleanup не продлевает право успешного результата после общего
deadline. Новых resume/ready/start действий в этой стадии нет.

Byte manifest имеет определённую проверку: приватное дерево без links/special/
hardlinks и неоднозначных mappings, строгие UTF8/NFC keys, потоковый SHA256;
SDK читает все байты, проверяет count/size/hash и list/stat до/после, закрывает
и освобождает каждый response. Versioning/object-lock/lifecycle запрещены.
Worker thread остаётся во владении до окончания при отмене, чтение ограничено
таймаутами и общим deadline. Это не допускает брошенный `to_thread` после cleanup.

Сокращённое `slash/dot/dotdot` читается совместно с полным проектом: обычные
вложенные ключи `audio/file` допустимы; запрещены leading/trailing slash,
пустые/dot/dotdot компоненты и collisions, а не любой `/`. Это уже принятое
правило, не новое ограничение. Проверка реализации должна следовать этой
точной интерпретации и не потерять рабочие вложенные object keys.

## Причинные проверки и границы следующего кода

Прочитано построение текущего `replay_world`: полный migrated dump, девять
delivery states, известный accepted account-closure case, native metadata
verification и отдельные source/target/schema DB. Его повторное использование
даёт конкретную непустую основу для теста стадий; fixture не объявляется
готовым тестом нового context manager.

План предусматривает успешный полный путь и schema mismatch, same-size object
corruption, неизвестный create без удаления неподтверждённой цели, body error,
двойную отмену create/cleanup и cleanup failure. Внутри теста обязательны
прежний reduced replay, COMMIT и новая физическая readback; после выхода —
проверенное отсутствие owned ресурсов. Для проектного PASS этого достаточно:
готовые результаты этих будущих тестов здесь не запрашиваются.

Standalone shell пока не переключается; его перевод на этот же конечный
внутренний путь остаётся в одном общем кандидате. Отдельного keep-target,
callback/pass-file/SQL интерфейса или helper-релиза нет. Собственные временные
ресурсы rehearsal не смешиваются с сохраняемой будущей рабочей DB actual restore.

## Scoped analyze и 117 вопросов

Все 117 reviewer-owned вопросов перечитаны: requirements **16/0**,
privacy-measurement **45/0**, security **27/0**, infra **29/0**;
итого **117 checked / 0 unchecked**. Их байты и отметки не изменились.
Это качество требований; не завершение реализации, CI или рабочего измерения.

Spec/plan/quickstart/activation/operations/constitution сверены по прежним
SHA256 в рамках разрешённого владельцем F273 исключения повторного чтения.
Изменившийся tasks дополнен только перечитанным состоянием внутреннего export:
T113/#7804 открыты, upper backup/rehearsal/replay/actual restore/resume/ready/T112
впереди, T0 не назначена, blocker сохранён. Новая конкретизация не конфликтует
с FR-025/034–036 и договорами полной копии/replay/проверяемой очистки, не
ослабляет права/основания/удаления и не возвращает требование всей маркетинговой
истории до T0. Новая отдельная задача или общий DR каркас не нужны.

## Контрольные суммы

| Файл | SHA256 |
|---|---|
| spec.md | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| plan.md | `02f4b52274c61fdf69f01415448a28d9509a1c12274a09d5a7382d3fc3db1b19` |
| tasks.md | `c77ba44f0476b026a5e4d8bebb4d000e792a113d23d73bfa9add8a9f9a21b4a1` |
| quickstart.md | `5bde6a5f388a03b6df1440fca32429f49bd458fdf9203fdc8df880352d249fea` |
| contracts/activation-milestones.md | `9898007a0e87400246f8c95b899dd807fab0424472143e15338429873982f3f9` |
| contracts/operations.md | `7d68aa7dc06b170508cd8b2858ede6e3e929b2e7155cd03b0895e715cb2b3abb` |
| constitution.md | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| rec-db-verify.py | `9878ffa671eacede35b599fe7a8c6fed0a2c8a75561a8d6d7d7911c13e28ebad` |
| rehearse-rec-restore.sh | `1d597450088a7667aa83fad718b3aa6469df04782a979e20d02fb9eebb922a35` |
| test_activation_restore_replay.py | `3259347bf1ea46fae06473a4c1a28d4bc7c9a7a762a2e5187062d955114efd0e` |
| checklists/requirements.md | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| checklists/privacy-measurement.md | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| checklists/security.md | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| checklists/infra.md | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Ревьюер создал только этот отчёт. Исходники, spec/plan/tasks/checklist,
Git/GitHub/runtime не менял, тесты и серверные команды не запускал.
Чужие изменения сохранены. T113/T112 и коммерческие критерии открыты.
