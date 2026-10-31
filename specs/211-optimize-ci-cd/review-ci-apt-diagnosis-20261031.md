# Независимое ревью требований F211/T110 — 31.10.2026

Проверяющий: `/root/public_counter_readiness_review`.
Рабочая копия: `/private/tmp/graf-release-20261031.m9mTRg`.
Ветка: `codex/211-aws-apt-source-20261031`.
Точная основа: `4a6220af6f74d29eb2186ded8e1e247e621d9a15`.
Lane: **active Spec Kit slice / CI diagnostics**.

## Решение

**PASS требований описанной одноразовой диагностики: 5 `[x]`, 0 `[ ]`.**
Препятствий для реализации именно этого ограниченного объёма после analyze и
issue sync не найдено. Это не приёмка ещё не написанного workflow и не
разрешение изменения APT/helper. Ни CI, ни сетевые/серверные пробы проверяющим
не запускались. Полный выпускный гейт и фактический неизвестный источник
остаются открытыми.

## Матрица каждого пункта

| Пункт | Итог | Непосредственное основание |
| --- | --- | --- |
| CHK001 | PASS | Spec §T110 называет Full41239402369, исходный SHA, shard2, сообщение `unsupported Ubuntu mirror source`, AWS/us-east-1, Ubuntu24.04.5 и image20261018.96.1. URI прямо назван неизвестным, exact upstream tag404 не используется как доказательство нового формата. Историческая T099 не переписывается. |
| CHK002 | PASS | Spec/plan T110 задают PR-only trigger по собственному файлу, matrix0–7, fail-fast=false, ubuntu-24.04, timeout5min, permissions={}, один Python stdlib step, без checkout/actions, сетевых команд, sudo, установок и секретов. Системные источники не меняются. |
| CHK003 | PASS | Spec ограничивает чтение ровно `ubuntu.sources` и `apt-mirrors.txt`, обычными нессылочными файлами≤16KiB; unknown — только код и SHA256 значения. Вывод JSON без environment/сырых строк; известный URI ограничен точным mirror+file путём либо Ubuntu host и /ubuntu[/] без credentials/port/query/fragment. Plan требует проверки до read_bytes. Точный прежний mirror+file путь определён T099 и существующим helper. |
| CHK004 | PASS | Plan/quickstart требуют извлекать именно inline run из будущего YAML, перенаправлять только две path-константы в временный каталог и исполнять его. Набор включает известный mirror-list, прямой учебный URI, unknown/credential URI, GitHub command string, missing/symlink/oversize; stdout разбирается как JSON и проверяется отсутствие закрытых исходных значений. Actionlint/process/governance/diff и независимое code review следуют до hosted запуска. |
| CHK005 | PASS | Spec/plan/tasks/quickstart требуют удаления временного workflow до merge, metadata-only run/source/hash evidence и честного unknown при отсутствии AWS. Helper остаётся неизменным, новый формат требует отдельных уточнений/tests/review до кода; старый Full не повторяется, рабочий сервер/release gate вне scope. |

## Почему такой диагностики достаточно до следующего решения

Исходная подготовка CI намеренно принимает только прежний доказанный deb822
mirror-list. Непосредственно прочитанный `infra/scripts/prepare-ci-apt.sh`
отказывает при другом URIs, не переключаясь молча на произвольное зеркало.
Диагностика должна выяснить метаданные до установки пакетов, а не снять этот
отказ. Поэтому читать текущие два runner файла без checkout/дополнительной
зависимости — минимальный полезный срез. Восемь независимых jobs не гарантируют
AWS или тот же image; отсутствие нужного варианта остаётся пробелом. Нельзя
объявлять исправление AWS по одному другому региону или по локальному примеру.

Отсутствие сетевых команд относится к диагностическому Python/step. Сам запуск
GitHub-hosted job и доставка журналов требуют инфраструктуры GitHub; это не
доказательство сетевой изоляции виртуальной машины. План не требует нового
firewall или обхода платформы. Он запрещает diagnostic code обращаться к сети,
пакетным репозиториям и внешним API.

Ограниченный JSON с закрытым набором обычных строк и хешами unknown исключает
прямой вывод credential URI или строк `::...` как workflow commands. При
реализации URI проверяется целиком: точная граница ubuntu.com, допустимая схема
и путь; username/password/port/query/fragment и управляющие символы не могут
проходить через ветку известного URI. Unknown не должен попадать ни в exception
text/traceback, ни в stderr/raw dumps, ни в job summary. Это проверяемое
исполнение имеющегося запрета сырых неизвестных строк, не новый сбор данных.

Данные и секреты продукта отсутствуют в разрешённых источниках. Не требуется
читать полный apt-config, `/etc/apt/auth.conf`, environment, GitHub context,
другие `.list/.sources` файлы или содержимое runner workspace. Никакой причины
расширять этот набор требования не дают.

## Достаточность локальной проверки

Для ещё не написанного metadata parser достаточно указанного focused harness
с реальным inline кодом плюс actionlint, process/governance и независимое
implementation review. Широкая сборка приложения или повтор Full ради этой
проверки не нужен и не заменяет hosted наблюдение.

Перед PR-запуском проверяющий реализации должен подтвердить: реальное
отсутствие checkout/actions/secret expressions/network/sudo/install команд;
ровно8 jobs/ограниченное время/пустые permissions/нужный PR path filter;
исполнение того же YAML-кода в локальных случаях; валидный JSON и отсутствие
исходных unknown/credential/control значений во всех каналах вывода;
отказ для missing/symlink/oversize; отсутствие изменений источников/helper.

Требования позволяют safe error metadata для невалидного файла, а не чтение
его содержимого «ради диагностики». Hosted успех означает только получение
разрешённой записи конкретной машины. Он не создаёт release receipt, не
заменяет required governance-fast/macos-pr/pr-metadata и не принимает Full.
После наблюдения обязательны запись фактов/ограничений и удаление workflow до
merge. Поддержка нового формата оценивается отдельно по actual observed
формату; current review не разрешает fallback на недоказанные репозитории.

## Прочитанный контекст и границы доказательств

Прочитаны корневой AGENTS, guidance index и document-reading; конституция
прочитана целиком (включая повторно отдельно выведенный средний раздел после
усечения большого tool output). Применимые разделы spec-kit-flow сохранены из
предыдущего собственного чтения и сверены по хешу; release-and-validation
прочитан в разделах validation lanes, local development/PR, Full decision,
Git/evidence safety. Scoped исключение владельца F211 применено к повторному
чтению неизменных PRD/status/product-gates: хеши совпали; это не заявление об их
новом полном чтении или о приёмке продукта.

Active context подтверждён `.specify/feature.json` и явным prerequisites для
F211. Прочитаны целиком текущие дополнения T110 в spec/plan/tasks/quickstart,
все пять checklist-вопросов, зависимые разделы T099 во всех необходимых
артефактах, существующий helper. Прочитан локальный watch report Full41239402369,
подтверждающий отказ shard2/отсутствующие его artifacts; точные AWS/image/URI
не выводятся из этого watch report. AWS/image и upstream404 здесь приняты как
явно маркированные исходные факты текущей спецификации, а не заново выполненная
сетевая проверка. Фактический URI остаётся неизвестным и является целью T110.

До работы уже имелись изменения четырёх F211 документов и новый checklist.
Они сохранены. Проверяющий изменил только свой checklist и этот отчёт;
остальные reviewer-owned списки, код, Git/GitHub, runtime и release не менял.
Отметка5/0 относится к качеству требований, не к выполнению T110.

## Контрольные суммы прочитанного состояния

- `AGENTS.md`: `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958`.
- `.specify/memory/constitution.md`: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- `docs/prd-voice-layer-final.md`: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- `docs/current-product-status.md`: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- `docs/agent-guidance/product-gates.md`: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- `docs/agent-guidance/README.md`: `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb`.
- `docs/agent-guidance/document-reading.md`: `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411`.
- `docs/agent-guidance/spec-kit-flow.md`: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`.
- `docs/agent-guidance/release-and-validation.md`: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`.
- `specs/211-optimize-ci-cd/spec.md`: `11ae51936fffa6ad94914442d3482fc335a182d94e33a9e6c8863165fce6b1d5`.
- `specs/211-optimize-ci-cd/plan.md`: `28d0188ff109036314bd70c2fef5da9f715924d844eb105780b32f1d403900ef`.
- `specs/211-optimize-ci-cd/tasks.md`: `791932eddfc387eed7043cf12cba0eb245e4584def714c9728ad32ec5451af8e`.
- `specs/211-optimize-ci-cd/quickstart.md`: `f3cf15e3364267bf5330e8cfb32ea88e7428ee308a6a1d81ab7d39bd43e17ae6`.
- `infra/scripts/prepare-ci-apt.sh`: `acb7a1a0b114d0446e893bf8961e0992d04c65078a7184ef3ac8072eba82d25f`.
- `specs/211-optimize-ci-cd/checklists/ci-apt-diagnosis.md`: `ee97e0500bda9422f0338c153a4b97d09cd02b7243be5936bf210c851dbb06a8`.

## Дополнение перед передачей

Повторно прочитаны финальный T110 в tasks со ссылкой Issue #7849 и отдельный
`validation-aws-apt-20261031.md`: там записаны карта5/5 и
CRITICAL0/HIGH0/MEDIUM0. Ссылка на issue и запись анализа не меняют границы
разрешённого workflow-only подхода. Никакое расширение helper на предполагаемый
AWS URI не рассматривается и не разрешается. Checklists перечитан после
отметок:5 отмечены,0 открыты. Код диагностики ещё не написан.


## Независимое code review T110 — первая реализация, 31.10.2026

**HOLD реализации до hosted диагностики: одно исправление безопасного вывода.**
Предшествующий PASS требований остаётся исторически действительным. Повторно
прочитан checklist: **5 отмечены / 0 открыты**; это качество требований,
а не подтверждение отсутствия ошибки в их реализации. T110 не отмечена
выполненной проверяющим.

### Обязательное исправление

**P2 — валидация известного hostname неполна**, workflow строки35–42.
`urlsplit()` разделяет URI, но не проверяет синтаксис DNS имени. Проверка
`host.endswith(".ubuntu.com")` допускает недопустимые для имени узла символы,
например обратную косую черту или NUL внутри имени перед `.ubuntu.com`.
Такой URI удовлетворяет остальным условиям известной ветки, а исходный host
возвращается в JSON. JSON экранирует управляющий символ, но не делает
неизвестное значение известным и не скрывает остальную исходную строку.
Это нарушает принятую границу: повреждённые/управляющие значения должны
выдаваться только как UNKNOWN+SHA256. Замечание установлено чтением реального
условия и семантики `urlsplit`; эксперимент проверяющим не запускался.

Достаточное исправление — узкая проверка допустимого синтаксиса DNS имени
перед известной веткой, с уходом в UNKNOWN при нарушении. Не требуется
DNS-запрос, новый список зеркал или более широкое чтение runner. Локальный
профиль должен исполнить настоящий изменённый inline код на недопустимом
hostname/control случае, проверить UNKNOWN и отсутствие исходного значения
в stdout/stderr. После изменения требуется повторное независимое чтение.

### Остальные результаты чтения

- Trigger только PR opened/synchronize на master по собственному path;
  permissions={}, ubuntu-24.04, matrix0–7, fail-fast=false, timeout5min.
- Один Python stdlib step; отсутствуют checkout/actions, выражения секретов,
  сеть/sudo/install, изменение APT и выпускные операции.
- Разрешены ровно два пути; до чтения проверяются конечная ссылка,
  обычный файл и размер≤16KiB, после чтения размер проверяется снова.
- Поля credentials/port/query/fragment при разборе URI отвергаются; обычная
  неизвестная строка и GitHub command string получают только UNKNOWN+hash.
- Временный профиль извлекает настоящий inline код из YAML; перенаправляет
  только корень двух путей в TemporaryDirectory. Журнал показывает11 PASS;
  проверяющий прочитал его, но не исполнял профиль. Среди этих11 случаев нет
  недопустимого hostname/control внутри иначе известного URI — найденный
  пробел не опровергнут существующим журналом.
- `apt-mirrors.txt` в обычном plain-list формате даёт пустой `uris`, поскольку
  парсер ищет лишь deb822 строки `URIs:`. В имеющемся профиле именно такой
  mirror файл, но assertion касается только первой source записи. Это
  ограничение полезности, не отдельный blocker данного T110: принятая цель —
  установить неизвестное поле URIs source файла; mirror файл всё равно
  представлен размером и хешем. По пустому массиву нельзя заключать, что
  зеркало отсутствует либо состав mirror-list исследован.
- Для ошибочных/не-UTF8 файлов нет целевого покрытия stderr; проверяющий
  не утверждает утечку содержимого через traceback без доказательства.
- Scope соответствует T110: helper/production/release gate не изменены.
  Удаление временного workflow до merge и получение AWS факта остаются
  последующими открытыми действиями, не выполненными этим review.

Прочитаны целиком workflow, local check.py/focused.txt, fragment, текущие
T110 spec/plan и validation report; governance.txt содержит
`spec-kit-governance: OK (bootstrap integrity + GRAF invariants)`.
Actionlint/process/fragment/diff PASS приняты как явные результаты основного
агента; отдельные их журналы проверяющему не предъявлялись. Сетевые команды,
тесты, Git/GitHub mutations, CI и runtime проверяющим не запускались.
Изменён только этот собственный отчёт; исправление кода передано владельцу.

Контрольные суммы проверенной первой реализации:

- workflow: `7a518835970b379a3f0e1659005cf517baa17efa2e2024a1a6a0bd3e43ab08dd`.
- local check.py: `aea5002b87333e4120b15ac0800544ff69268a0fd4f6fe1071e88f8f271ba7e1`.
- focused.txt: `56e5421fb5c598d2f9c40845fcc997ac6db1c77960bec68fdba568f0cb87abb5`.
- F211 fragment: `79800fadf1cbd1a4f11470898c33f4277d468cd8955306d88b06be51d80e9474`.
- checklist: `ee97e0500bda9422f0338c153a4b97d09cd02b7243be5936bf210c851dbb06a8`.


## Повторное code review после исправления hostname — 31.10.2026

**PASS ограниченной реализации T110 перед hosted диагностикой. Открытых
P1/P2/HIGH замечаний по прочитанному коду: 0.** Первый HOLD выше сохраняется
как история найденной и исправленной ошибки, а не текущий вердикт.

Фактически перечитаны весь исправленный YAML, текущий local check.py,
causal-before.txt, focused-fixed.txt, обновлённый validation report и весь
checklist. DNS regexp принимает только непустые ASCII labels допустимой
длины с конечным ubuntu.com, ограничение общей длины253 сохранено.
Обратная косая черта/NUL/percent/другие недопустимые символы в host теперь
не проходят известную ветку. Проверка всех символов исходного URI исключает
C0/DEL и не-ASCII до вывода известных полей. `value.netloc.lower() == host`
дополнительно исключает credentials и суффикс порта, включая пустой `:`.
Остальные schema/path/query/fragment проверки и UNKNOWN+SHA256 сохранены.

Исправление узкое: новый import re — стандартная библиотека; network,
checkout/actions, secrets и изменение системных источников не добавлены.
Matrix0–7, fail-fast=false, Ubuntu24.04, timeout5min, permissions={}, один
step, trigger opened/synchronize/master/собственный path не изменились.
Проверки двух файлов и ограничение16KiB сохранены. Ограничение plain
mirror-list остаётся явно принятым: `uris` для него пуст, доступны размер
и хеш; состав зеркал этим не объявляется исследованным.

Текущий профиль исполняет inline Python исправленного YAML и содержит14
случаев. Causal-before показывает ожидаемый отказ старой suffix-проверки
на backslash; focused-fixed показывает14 PASS, включая backslash,
nul-host и empty-port. Исходные sensitive markers проверяются в stdout.
Явной assertion пустого stderr в профиле нет; это предел прочитанного
тестового доказательства, а не утверждение обнаруженной утечки. По коду
исправленной известной/UNKNOWN ветки вывода raw URI в stderr не найдено.
Проверяющий тестов или экспериментов не запускал.

Checklist повторно перечитан: **5 `[x]` / 0 `[ ]`**. Его требования и
отметки сохранены; в checklist добавлена ссылка на текущий implementation
PASS без утверждения о completed T110/hosted/Full/release. Spec/plan/tasks
и код проверяющим не изменены. Scope converge: реализация соответствует
описанному временному диагностическому срезу, необоснованного расширения
helper/production/release gate нет. AWS URI, окончательный hosted факт,
удаление workflow перед merge и новый Full остаются следующими действиями.

Контрольные суммы повторно прочитанного состояния:

- workflow: `6e41ccf0c5e91eb78cf0b9edd645b6015cbbaa682aca4e91607384190093b36b`.
- local check.py: `877530b92f00a7a16fa857e05ca5f985096c57e0f40cb0a240e7796a09e5c353`.
- causal-before.txt: `e17ccdf8f8a1f0dce6b2c96f0dc005cc06e1684f2af9a5a6df8ae2d9ddc20440`.
- focused-fixed.txt: `86cc2712bca07baf913417ed8a0339473493d5238431e1eb13977dc7299fbd20`.
- validation report: `51a3e7d1446cea48ee122f6702b8f7fcb2ca43676c401df374d4a376e603a057`.


## Требования второго ограниченного набора T110 — 31.10.2026

**PASS узкого уточнения до изменения runs-on; замечаний P1/P2/HIGH0.**
Прочитаны целиком новые одинаковые разделы spec/plan/quickstart, изменённая
T110 в tasks и отобранные platform/result строки безопасного журнала
hosted-41240805226.log по всем восьми matrix samples0–7. Первый большой
вывод журнала был усечён, поэтому metadata/result отдельно выведены для
всех8jobs. Каждый показывает Azure, image20261025.353.1 и два mirror_list
в ubuntu.sources; mirror-list файл представлен только hash/size. AWS URI
этим наблюдением не установлен. Статус SUCCESS сообщён основным агентом;
сам проверяющий GitHub API/сеть не вызывал.

Прочитаны реальные runs-on и callers prepare-ci-apt в workflows: нужные
три callers используют ubuntu-latest. Первый диагностический YAML на
момент requirements review всё ещё ubuntu-24.04, hash6e41ccf0…;
изменения кода до данного PASS не было. Разная метка является основанием
сопоставить ещё одну ограниченную выборку, не доказательством причины
различия Azure/AWS или гарантией AWS во втором наборе.

Требования задают ещё ровно8jobs, суммарно≤16 в двух наборах, с меткой
ubuntu-latest. Readset, inline safety,5min/permissions, отсутствие
checkout/actions/network/sudo/install и удаление workflow до merge
сохраняются. Если AWS не встретится, результат остаётся неизвестным;
старый Full не повторяется. Нужны точная проверка новой метки, прежние14
исполняемых случаев и независимое implementation review. Нового чтения
продуктовых/закрытых данных, изменения helper/trust/runtime не появляется.

Checklist перечитан перед дополнением: **5 отмечены / 0 открыты**.
Требования достаточны, расширения исходного задания не найдено.
Изменены только собственный отчёт и checklist. Это PASS требований;
изменение YAML и второй hosted запуск ещё не принимались проверяющим.

Хеши прочитанного:

- spec: `a2ebecf0b942d2228484140e74338ff4f73efce6b66c35922af19d820849baac`.
- plan: `abb906e95ed09087d8deb82d08c98610ce4db9a3ae5806145cdfa2e495221bfe`.
- tasks: `4993f3f06777d56ba5d1351eba5f354d710b7f2625780dc68c4a03593a2fc393`.
- quickstart: `acbf8889592fa18dcab0d673939acf50dd6ec3e3603413d3225041704773b248`.
- hosted log: `b211a8d29a8258bef2349b29ad50a3c8e8476db6caee0d8c9e8701f02fe8ffb4`.


## Implementation review второго набора T110 — 31.10.2026

**PASS узкого diff и converge; открытых P1/P2/HIGH0.** Реальный git diff
workflow содержит ровно одну замену runs-on ubuntu-24.04→ubuntu-latest.
Весь текущий YAML перечитан: inline code/readset/safety, matrix0–7,
fail-fast=false, timeout5min, permissions={}, один step и triggers сохранены.
Нет новых actions/checkout/network/install/sudo/secret expressions или
изменений helper/runtime/release gate. SHA256 совпал с переданным владельцем.

Текущий local check.py дополнительно проверяет точное runs-on ubuntu-latest.
Все14 прежних исполняемых случаев сохранены; sensitive-marker assertions
теперь проверяют stdout+stderr вместе. Это устраняет ранее отмеченный предел
доказательства только stdout. focused-latest.txt содержит14 PASS;
process-latest.txt — agent-context/changelog/legacy-impact/development-process
OK для F211. Журналы прочитаны, повторных тестов проверяющий не запускал.
Actionlint/diff PASS сообщены владельцем, собственных запусков не было.

Общий diff дополнен только ранее принятыми требованиями второго набора,
документами проверки и reviewer-owned материалами. Изменение source_sha
в ignored pointer после первого commit — объявленная коррекция актуальной
основы; она не даёт новых полномочий. Issue sync сообщён владельцем,
сам проверяющий GitHub не открывал и не менял.

Scope converge PASS для второго ограниченного набора: ещё8jobs и
общий предел16 остаются заданными. Этот code PASS достаточен для передачи
оператору последующих разрешённых действий, но не доказывает AWS/result,
удаление workflow до merge, Full или выпуск. T110 проверяющим не закрыта.
Checklist целиком перечитан и подсчитан: **5 `[x]` / 0 `[ ]`**.
Изменены только собственный отчёт и checklist; Git/GitHub/CI/runtime
мутации и тестовые запуски проверяющим не выполнялись.

Хеши:

- workflow: `d0c641cdc451e17f0d4606719a6173d0057ab89b5e28f14109d6aa502fc1feff`.
- check.py: `eaaf0f7db5c0f415c068e468a552dbc94e10bd223e59d236569e2de1ece89b79`.
- focused-latest.txt: `86cc2712bca07baf913417ed8a0339473493d5238431e1eb13977dc7299fbd20`.
- process-latest.txt: `caf1e7b86b6d45d75f3e8cb7294c2bdc9609059f0f159191b916f7ad9529ed76`.
