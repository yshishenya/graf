# Независимое before-code ревью F211/T111 — 01.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Копия: `/private/tmp/graf-release-20261031.m9mTRg`.
Ветка: `codex/211-aws-apt-source-20261031`.
HEAD: `7040d2502cd39dbc7c586d1fa69e683ab3bb4a57`.
Lane: active Spec Kit slice / CI diagnostics.

## Решение

**PASS требований T111: 5 `[x]` / 0 `[ ]`; blockers и P1/P2/HIGH0.**
Это узкое расширение объяснения прежнего отказа, не поддержка нового
источника APT. Реализация, RED/GREEN, GitHub checks, AWS URI и выпуск
ещё не принимаются. Код helper на момент чтения не изменён.

## Матрица требований

| Пункт | Итог | Прямое основание |
| --- | --- | --- |
| CHK001 | PASS | Spec T111 и validation явно фиксируют оба набора,16/16 Azure, неизвестный AWS, отсутствие дальнейшей выборки. T110 и issue#7849 остаются открытыми до AWS факта. Отказ Full и прежняя приёмка не переписываются. |
| CHK002 | PASS | Один JSON в точке unsupported Ubuntu mirror source, boolean enabled, тот же ранее исправленный describe: точный mirror_list или DNS Ubuntu URI без credentials/port/query/fragment/control/non-ASCII. URIs≤4096 разбивается на токены; больше4096 даёт только UNKNOWN+SHA256 целого. Raw fields/environment/unknown запрещены. |
| CHK003 | PASS | Spec/plan требуют прежний ненулевой отказ после JSON, сохранение allowlist/parse/trust/keys/source/mirror/прочих источников и всех трёх callers. Нет новых модулей/настроек/зависимостей/YAML callers и действий после отказа. |
| CHK004 | PASS | Spec/quickstart требуют настоящий существующий трёх-caller harness; прямой Ubuntu URI, unknown/credentials, invalid DNS/NUL/empty-port/long остаются FAIL. Проверяются JSON/нераскрытие/байты источников/единственное событие mirror. RED должен доказать отсутствие JSON у прежнего helper, GREEN включает весь прежний профиль T099. |
| CHK005 | PASS | Временный YAML удалить до merge. Requirements/checklist/analyze/sync до кода, RED/GREEN, focused/static, независимые code review/converge и exact PR gates обязательны. Full ради выбора машины запрещён; успешное локальное/PR доказательство не является Full/CD. |

## Допустимость переноса describe

Перенос ранее принятой pure функции в существующий Python heredoc достаточен
и соответствует объёму. Она описывает строку, но не принимает решение о
допуске источника, не читает сеть/окружение/другие файлы и не меняет APT.
В существующем helper до проверки mirror-list уже выделены deb822 поля;
в момент прежнего URI/disabled отказа можно безопасно классифицировать
только уже полученное URIs и вывести enabled как boolean. Значение enabled
не следует печатать сырым. Для отсутствующего URIs диагностическая форма
должна оставаться ограниченной, прежний отказ сохраняется.

Известный для describe прямой Ubuntu URI всё равно остаётся неподдержанным
для helper: классификация метаданных не расширяет единственный допускаемый
mirror+file источник. Это явно сказано в spec и проверяется будущим
отрицательным тестом. Прежние source fields/parser/mirror bytes проверки
сохраняются; другая ошибка не требует чтения дополнительных конфигураций.
Существующее sudo относится к прежнему caller, не является новым правом.

Лимит4096 действует на диагностическое значение после прежнего parsing.
Требования не обещают нового ограничения размера всего source файла или
изменения старого parser. В обоих случаях вывода данные ограничены:
либо конечное число токенов ограниченной строки, либо один UNKNOWN/hash.
SHA256 длинного/неизвестного значения допустим, сырое значение — нет.

## Прочитанные зависимости и доказательства

Прочитаны полностью новые T111 sections в spec/plan/tasks/quickstart,
checklist, текущий helper, относящийся к задаче parametrized shell harness
resource preparation с тремя настоящими callers и validation report.
Большой первый вывод документов был частично усечён; plan T111 и настоящий
harness отдельно прочитаны повторно без усечения. Ранее принятый describe
используется из того же T110 YAML; его hash неизменен относительно собственного
предыдущего review. Первый и второй hosted итог в этом срезе приняты из
явно маркированного validation report и сообщения основного агента;
новой сетевой проверки run41241032858 проверяющий не выполнял.

Guidance index перечитан, active pointer подтверждает F211/T110,T111,
ветку/HEAD/owned paths. Scoped исключение владельца F211 применено к
повторному чтению базовых неизменных документов: constitution, PRD/status,
product-gates/spec-kit-flow сверены по SHA256 с прежним собственным чтением,
все совпали. Это не новое полное чтение и не приёмка продуктовых изменений.
Analyze5/5 C/H/M0 и canon/issue sync сообщены владельцем и записаны в
validation; GitHub самостоятельно не проверялся.

Тесты/сеть/Git/GitHub/CI/runtime/release операции проверяющим не выполнялись.
До review уже имелись изменения F211 документов и новый checklist — они
сохранены. Изменены только этот собственный отчёт и новый checklist.
После отметок checklist перечитан: **5 отмечены / 0 открыты**.

## Контрольные суммы состояния до кода

- spec: `edd876f6c922efcbe78edb81f74333a90033233716301f2c43b11bc13f3d6f25`.
- plan: `1702a592d1cdb65fb2188ead064e4fba79bb637a075eb9215f68a920523ea02a`.
- tasks: `ba3a15b211968b3d2b68334d664638ded4ecea164c7bc546128d88b17bfec3a2`.
- quickstart: `c9a9b1511453be4a1523ce714a6a8e79b1fcaf32e0119a68428e2155a0c63b10`.
- helper: `acb7a1a0b114d0446e893bf8961e0992d04c65078a7184ef3ac8072eba82d25f`.
- harness: `4f36e758305e8b959aab994951ca8f4667648ae840eee4e35c8d15b2111c7fe5`.
- T110 workflow: `d0c641cdc451e17f0d4606719a6173d0057ab89b5e28f14109d6aa502fc1feff`.
- constitution: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- PRD: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- status: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- product-gates: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- spec-kit-flow: `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e`.


## Независимое implementation review / scoped converge — 01.11.2026

**PASS реализации T111; открытых P1/P2/HIGH0.** Checklist целиком
перечитан: **5 `[x]` / 0 `[ ]`**. Исходный before-code PASS выше сохраняет
свою область; настоящий раздел принимает только описанный локальный срез.
Точные PR gates, AWS/T110/#7849, Full/CD/release остаются открытыми.

### Проверка фактического кода

Весь helper перечитан, diff содержит только стандартные imports,
перенесённый describe и JSON непосредственно перед прежним SystemExit.
Условие допуска URIs/Enabled, parser deb822 fields и дубликатов, проверки
обычных нессылочных source/mirror, точные mirror bytes и последующая запись
официальных зеркал не изменены. Три source helper callers на прежних
местах governance-fast/release-full сохранены; их YAML не изменён.
Временный ubuntu-apt-diagnostic.yml действительно удалён из diff.

Describe совпадает по существенным условиям с исправленным T110:
точный mirror+file, DNS labels/общая длина, ASCII без control/DEL,
netloc==host, http/https и /ubuntu[/], запрет credentials/port/query/fragment.
Unknown возвращает только kind/hash. Значение URIs≤4096 разбивается на
токены; больше4096 даёт один UNKNOWN+SHA256 целого, без raw значения.
В JSON ровно uris и boolean enabled, flush=True, затем прежний ненулевой
отказ. Даже описанный как ubuntu_uri прямой источник по-прежнему не
проходит allowlist helper. Enabled=no не превращается в разрешение.
Последующая запись mirror/install/npm/browser недостижима после SystemExit.
Дополнительного чтения environment/файлов/сети, новых зависимостей, ключей,
модулей, настроек или полномочий нет.

### Проверка исполняемого профиля и журналов

Прочитан реальный diff тестов и целиком относящийся к задаче resource
preparation harness. Он по-прежнему извлекает настоящие run blocks трёх
callers и исполняет настоящий helper с перенаправлением /etc/apt во временный
каталог. Все прежние tools_state и guards сохранены. Добавлены10 URI
сценариев на каждого caller: direct/unknown/credential/backslash/NUL/
empty-port/long/multi/query/fragment. Существующий disabled-source также
теперь проверяет JSON и enabled=false.

Новый профиль проверяет один JSON, корректный kind, точный hash unknown,
разделение составного значения, отсутствие sensitive marker в stdout+stderr,
неизменность source/mirror/third-party содержимого. После отказа события
ограничены [mirror], что исключает последующие установки и действия.
Положительные прежние случаи и повтор без перезаписи зеркала сохранены.

Первый вывод большого RED-журнала был усечён; отдельно перечитаны причина
assert len(metadata)==1 при прежнем constant refusal и полный short summary:
**30 failed / 243 deselected**, все10×3 диагностических случая.
GREEN-журнал целиком: **273 passed in87.33s**. Это причинное доказательство
добавления JSON с сохранением прежних случаев, а не ослабление отказа.
Тесты проверяющий не запускал. Bash/actionlint/Ruff/diff PASS явно записаны
в validation и сообщены владельцем; отдельных журналов этих команд здесь
не было, собственных запусков не выполнялось.

### Converge и границы

Все пять групп требований имеют соответствие в коде/профиле. Необоснованного
расширения scope или неподдержанных P1/P2/HIGH остаточных изменений не найдено.
T111 может продвигаться к commit/точным PR gates оператором после остальных
проверок. Это не основание закрыть T110/#7849: AWS URI остаётся неизвестным,
16/16 Azure не доказывают его формат. Новых выборок/Full ради выбора машины
не требуется и не принимается. Production/CD/release не затронуты.

Spec/plan/tasks/quickstart hashes неизменны относительно собственного
before-code review. Changelog fragment отражает безопасный отказ и честную
неизвестность AWS. Проверяющий изменил только этот отчёт и свой checklist,
не менял код/документы требований/Git/GitHub/CI/runtime и сохранил чужие
изменения. После дополнения checklist перечитан и подсчитан:5/0.

Хеши принятого локального состояния:

- helper: `c5e2e851d2b79ba9d1ab7bcdc5da2f9e52c6721bb9faefed6d6ded233fcf68c9`.
- harness: `110f6cd771f0786112bbefca628017d3857cd4fe5bc56499ad85dec582a5de6d`.
- RED log: `c1678dd9fe82134842111436aea87c1e57cddebe6cd2eafa2241b1e4bd715be6`.
- GREEN log: `a4d4307f7772122e726c0b45cbb8db094a18bd690a7da68484e6ed419c10eb2d`.
- fragment: `9eb4f519d4ee06d59415d37219859430428d0bf2977873e4f34e32f56037d231`.
