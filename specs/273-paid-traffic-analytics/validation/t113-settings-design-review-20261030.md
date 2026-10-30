# T113: независимое ревью проекта actual Settings

30.10.2026, проверяющий `/root/f273_release_boundary`, исполнитель `/root`.
Основа `426cde62b308fa9630fe872de72e8c321ade2325`, high-risk-product,
T113/#7804. Только precode/scoped analyze, без запуска рабочего оператора.

## Решение

**SCOPED PASS исправленного проекта actual Settings; обязательных замечаний
до кода не осталось.** Конкретный host-путь доказательства фактического bind,
sealed memfd для обычных validators, закрытая таблица disabled placeholders
и владение FD до конца preflight теперь согласованы с принятым алгоритмом.
Ни реализация, ни рабочий запуск, ни полный preflight этим PASS не принимаются.
Первоначальные замечания ниже сохранены как история; итоговое повторное
ревью находится в конце отчёта.

Полностью прочитана последняя редакция предложения
`.dev/growth/t113-settings-precode-20261030.md`, SHA-256:
`a0d4aedef0030f230cfacee35fb2ab74e4c9e5a3c034f121b5b4c2c89d61b267`.
Первоначальная редакция имела SHA-256
`52e71659518ecd08b9c6b4aa463a91d8a9ecf9fac347dcd834ddcd79e7c8bc85`.
Дополнительные сообщения об ExitStack/сроке FD, native proxy переменной
и runtime readability включены в финальный раздел самого проекта.

## Первоначальное замечание1: actual mount — закрыто

Linux file bind удерживает inode, а Docker Mounts.Source хранит исходный
путь. Если host secret был заменён через rename, работающий контейнер
продолжает видеть старый inode, хотя новый host файл по тому же пути может
иметь корректные owner/mode/content и быть стабилен всю проверку. Повторение
Docker inspect, host FD/stat/hash этого расхождения не обнаруживает.
Уже прочитанный учебный runtime-user JSON имеет отдельный отрицательный
контроль `direct_replacement=negative_control_stale`; это известная граница,
а не гипотетическое требование нового контейнерного IPC.

Минимальный host-only способ для выбранного точного RO file bind:

- использовать уже доказанный running PID/его starttime и actual mount
  destination; не читать произвольный контейнерный путь;
- открыть видимый этому процессу точный mount destination через host
  `/proc/PID/root` с закреплённым root FD и ограниченным проходом по компонентам
  без ссылок после этого единственного намеренного proc-root перехода;
- сравнить dev/ino и безопасную file metadata destination FD и source FD,
  а также ограниченные байты; несовпадение означает HOLD;
- удерживать FD и повторить PID/starttime, mounts и destination identity
  перед итоговой проверкой. Исчезновение/новый PID/невозможность доказать
  связь не заменять чтением текущего host-path.

Это не `docker exec`, новый IPC, общий path resolver или mount mutation.
Допустим другой столь же конкретный host-путь доказательства, но одного
`Mounts.Source + source.lstat()` недостаточно. Нужна учебная причинная проверка:
файл подключён, host pathname заменён, source новый, mount старый — отказ.

## Первоначальное замечание2: проверенные байты validators — закрыто

Полностью прочитанный `config.py` содержит обычные `Path.is_file/open/read_text`:
production credentials, database password substitution/URL quoting,
MinIO/CSRF, billing и sharing. Удержание исходного FD не заставляет эти методы
использовать его. Проверки stat/hash до/после не исключают подмену пути на
период самих validators с возвратом исходного файла; подмена на FIFO может
также заблокировать синхронный validator вопреки общему deadline.

Минимальный проект должен явно связать значения `_file`, переданные parent
Settings validators, с проверенным ограниченным снимком байтов. Например,
прочитать verified FD с лимитом64KiB и дать валидаторам private sealed memfd
через собственный `/proc/self/fd/N`; обычные Path semantics сохраняются,
config.py и globals не меняются, секреты не записываются в журнал или Git.
Внутренний намеренный FD path не должен разрешать произвольный внешний
symlink. Seals предотвращают изменение/рост снимка во время `read_text`.
Другой способ допустим, если явно гарантирует те же проверенные байты и
ограниченное чтение всеми существующими validators.

Сообщённый исполнителем contextmanager/ExitStack принимается как минимальный
срок владения: original/destination/snapshot FDs остаются открытыми до конца
всего `_runtime_preflight`, после yield повторяется proof до закрытия finally.
Settings с живыми FD-path нельзя выдавать после закрытия этих FD. Просто
возвращать Settings из синхронной функции с уже закрытыми FD недостаточно.
Тесты должны подменить host путь во время validation и показать, что validator
не прочитал чужой файл/FIFO, а итоговый changed proof дал HOLD.

## Первоначальное замечание3: disabled placeholder — закрыто

В Git `infra/secret-placeholders/disabled_optional_provider_secret` — точный
пустой файл mode100644. Прочитанный CD выбирает его для выключенных billing/
calendar интеграций; Compose при этом сохраняет настроенные `_file` пути
внутри контейнера. Settings намеренно не требует непустой provider secret,
когда соответствующая возможность выключена. Универсальное правило
«каждый configured `_file` непустой0600/0640» всегда отклонит такую штатную
конфигурацию, даже не связанную с включением аналитики.

Минимально определить закрытую таблицу разрешённых inactive placeholders
из настоящих Settings flags и штатного CD/Compose, без общего «disabled значит
пропустить файл». Для точного canonical committed empty placeholder при
выключенной соответствующей возможности проверить readonly bind, отсутствие
подмены, правильную public nonsecret identity/пустые байты и включить marker
в proof. Допуск0644/пустоты относится только к этому nonsecret placeholder;
настоящие секреты сохраняют строгие owner/mode/непустоту/лимит и runtime
readability. Нельзя молча заменить path на None, включить development либо
ослабить production validators. Включённая возможность с placeholder — HOLD.
Нужны парные учебные случаи одной возможности off/on с тем же placeholder.

## Учтённые уточнения и сохранённые границы

Выбор единственного captured EnvSettingsSource с `parse_env_vars` сохраняет
JSON/NoDecode/aliases/empty parsing и устраняет host TWOBRAIN/GRAF, init,
dotenv/file-secret sources. Duplicate/case-fold collision отвергаются до
разбора. Не требуется новый ручной parser `.env`.

Единственный прямой `os.environ` validator — native FORWARDED_ALLOW_IPS.
Сообщённый исполнителем вариант принят: host native ключ обязан отсутствовать
(иначе HOLD); actual case-sensitive ключ проверяется тем же точным ipaddress
правилом отдельно. Нельзя изменять глобальный os.environ или config.py ради
обхода этого validator; production остаётся production.

Исполнитель дополнительно обнаружил различие root-readable и runtime-readable.
Его предложение подтвердить actual `/proc/PID/status Groups` вместе с уже
проверенными UID100/GID101, разрешить чтение file owner/group только по этим
actual IDs и повторить process proof принято. Root-only0600 с владельцем0,
недоступный runtime, не принимается лишь потому, что оператор-root его читает.
Это относится к фактически смонтированному файлу, а не только Source pathname.

Секреты, model dump, Env и пути не печатаются; ошибки только конечные причины.
Настоящие FD/identity/content digests остаются приватными, общий proof связывает
runtime и Settings, а не имя файла. Не заявляются executability media paths,
полная Compose command policy, DB роли/схема/retention/resources/access/capacity.
До остальных ворот итог всегда HOLD/full_preflight_not_implemented;
activation_recovery_unverified сохраняется, T0/ready не создаются.

## 117 требований и исходные материалы

Все117 фактических вопросов повторно прочитаны, отметки не менялись:

| Список | Отмечено | Открыто | SHA-256 |
| --- | ---: | ---: | --- |
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Итого **117 отмечено/0 открыто**. Это качество требований, не приёмка
реализации или рабочего выполнения. Spec/plan/quickstart/contracts/constitution
и полный верхний проект имеют прежние hashes; собственное прежнее полное
чтение переиспользовано по разрешённому исключению F273. Полностью прочитаны
1101 строка Settings, применимые EnvSettingsSource/parse_env_vars, действующий
runtime binding и относящиеся к placeholder CD/Compose участки. Новое чтение
всей PRD/истории статуса не заявляется; история маркетинга до T0 не добавляется.

| Материал | SHA-256 |
| --- | --- |
| config.py | `2cd24aff502295b9eabbdf5ddbdbf853466f63b10c67cf3cbdf00fd426e3cfeb` |
| activation_operator.py | `18a49160c68f59ca714d25950c48b17e81d36b673f8d12a9c60f17a569eb3dcc` |
| Полный проект | `5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec` |
| Runtime-user negative-control JSON | `710e97160b942b0bea8ec5d660bbcea6e12e07b7dcf979ccf312a2bd12abc153` |

## Финальное повторное precode/scoped analyze ревью

Полностью прочитана редакция
`a0d4aedef0030f230cfacee35fb2ab74e4c9e5a3c034f121b5b4c2c89d61b267`,
включая все concrete corrections. Три замечания закрыты следующим алгоритмом:

1. Точный RO file bind проверяется со стороны source и доказанного PID через
   намеренно закреплённый `/proc/PID/root` FD. После него проход только по
   компонентам точного mount destination, NOFOLLOW, финальный regular file.
   Сравниваются source/destination fstat и полные ограниченные байты;
   destination повторно открывается в конце, PID/starttime/groups и mounts
   повторяются. Stale bind после rename source больше не принимается.
2. Parent production Settings читают внутренний sealed memfd с теми же
   проверенными байтами, не host pathname. Проверяются все четыре seals,
   snapshot нельзя изменить/расширить. Один ExitStack охватывает Settings и
   original/destination/sealed FDs до последнего await и итоговых runtime
   проверок. Settings не выходит за этот срок; finally закрывает все FD.
   Нового config.py parser/validator или глобального env monkeypatch нет.
3. Только точный canonical committed empty placeholder допускает пустоту0644
   по закрытой семипольной таблице реальных parsed feature flags. Включённая
   функция, другой source, произвольный пустой/public файл или core DB/MinIO
   credential с placeholder — HOLD. Настоящие секреты сохраняют private
   mode/owner/nonempty/bounds и проверку фактического runtime read.

Дополнительные уточнения actual EnvSettingsSource, native proxy отсутствия
на host, actual case-sensitive proxy parsing и реальных supplementary Groups
также вошли в финальный проект. В реализации runtime-readable означает и
чтение конечного файла, и разрешённый проход actual UID/GID/groups по
destination каталогам; host-root возможность открыть их сама не доказывает
runtime доступ. Это входит в уже принятое требование runtime readability,
а не отдельный сервис или разрешение менять права.

Проект сохраняет точную readonly границу, один существующий deployment lock,
очищенное окружение, неизменяемый установленный пакет и конечный deadline.
Новых противоречий применимым spec/plan/contracts и полному проекту не найдено.
Воспроизведение CD environment, контейнерный exec/IPC, общий path resolver и
дисковая plaintext staging не вводятся. Предусмотренные причинные Linux
проверки должны подтвердить stale bind отказ, exact bind успех, seals и пару
inactive/active placeholder; их будущий PASS не является рабочим запуском.

Четыре checklist после повторного чтения117 вопросов сохранили прежние hashes:
requirements16/0, privacy45/0, security27/0, infra29/0; **117 отмечено/0 открыто**.
Отметки не менялись. Scope согласован только для реализации и проверки этого
Settings-среза. Итог верхнего оператора остаётся
HOLD/full_preflight_not_implemented, activation_recovery_unverified не снимается,
T0/ready, полный T113/T112 и выпуск не приняты.

Изменён только этот отчёт. Код/spec/plan/tasks/governance/Git/GitHub/Dev/
production и данные ревьюер не менял, тесты/Docker/SSH/SQL не запускал.
UID1003 не подтверждён; новых вопросов пользователю нет. T113/#7804, полный
preflight, T0, выпуск, трафик и продажи этим ревью не приняты.
