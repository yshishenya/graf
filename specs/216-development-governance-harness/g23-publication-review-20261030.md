# Независимое ревью G23 и публикации harness v0.1.15

Дата итоговой проверки: 30.10.2026. Проверяющий: отдельный агент
`f216_checklist_recheck`. Lane: read-only review с записью только этого
отчёта и reviewer-owned `checklists/governance.md`.

Итог: **APPROVE для G23 и проверенного consumer diff v0.1.15**.
Отмечен только G23; полная F216 остаётся **BLOCK** по G5/G8/G18.
Историческая проверка v0.1.14 с результатом BLOCK сохранена ниже.

## Принятая исправленная публикация

[Внешний PR #9](https://github.com/yshishenya/graf-development-harness/pull/9)
фактически слит: source `fd19514dc5e224bcd9f63348fb09ddea202e5aa4`,
merge/release source `8f41a53508d0c8ca27afb97cea4b020ae474c6ce`.
Reviewer независимо сверил равенство деревьев PR и принятого source и все
41 входной SHA256 из квитанции реальной сборки с Git на release source.

[PR CI 40992821794](https://github.com/yshishenya/graf-development-harness/actions/runs/40992821794)
и [push CI 40992902362](https://github.com/yshishenya/graf-development-harness/actions/runs/40992902362)
независимо прочитаны через GitHub API: event и head SHA верны, attempt 1,
оба задания Python 3.9/3.12 — success. В каждом фактически выполнен
`Lint source launcher before publication` до `Build and inspect publish artifacts`.
Исходный workflow не допускает пропуска или игнорирования отказа ShellCheck.

Прочитаны квитанция 51 успешной команды и независимый отчёт проверки состава,
байтов, лицензии и установленных файлов. Все журналы присутствуют, коды 0;
ShellCheck завершён в 02:25:43.921964 UTC, сборка началась в
02:25:44.687165 UTC. Отдельная чистая установка 0.1.15 на Python 3.12.11
и циклы 0.1.13 → 0.1.15 → 0.1.13 → 0.1.15 и 0.1.14 → 0.1.15 →
0.1.14 → 0.1.15 подтверждены. Сборка/циклы использовали Python 3.13.3.
Это принятие имеющихся доказательств; reviewer новых сборок и установок не делал.

Прежнее независимое замечание к внешнему PR body устранено до принятия:
живой body побайтно совпал с квитанцией успешной проверки реального SHA,
SHA256 `184fb02ccc43405863e9a1a7f12194de513a156bc9e596117e2940378a46f948`.
Проверка синтетического body в workflow отдельно за приёмку настоящего не выдана.

[Release v0.1.15](https://github.com/yshishenya/graf-development-harness/releases/tag/v0.1.15)
опубликован в 02:42:38 UTC, ID 428600220, draft=false, prerelease=false.
Reviewer повторно загрузил три GitHub asset в память, сверил байты с ранее
загруженными опубликованными файлами и контрольными суммами принятой сборки:

| Файл | SHA256 |
| --- | --- |
| development_process_harness-0.1.15-py3-none-any.whl | 366b3d767958829de5f75cc2202d9d7ca28480be4cc1e2f496ffe11c9187c6d8 |
| development_process_harness-0.1.15.tar.gz | f5c50ef741861959db621f4bf4565ca1e2de35a6f510c394826264bdfcfb0a70 |
| SHA256SUMS.txt | 2f500247f6dbecea63450f6a0e29b323631b36f8227d255519e59edc892f0cd0 |

Независимо пересчитаны wheel RECORD, CRC, лицензионные поля и LICENSE;
в sdist проверены безопасные имена, отсутствие ссылок и неизменённый LICENSE.
Обычные каталоги архива допустимы; 43 файла и 15 каталогов. В wheel 34 записи,
`Version: 0.1.15`, `License-Expression: LicenseRef-GRAF-Harness`,
`License-File: LICENSE`, без `Requires-Dist`. SHA256 LICENSE сохранён:
`5bf7aab19cd875ab4c38b87375a868c7bef61ca21c969423677cef7d68604f05`.
Юридические условия не менялись; исходный текст не объявляется стандартной MIT.

Живые русские notes побайтно равны принятому файлу, SHA256
`bbd6c46535c5b1fd736eb7d2f28d46e539ddc75ae4f254b0dd8310c73dbdeca8`.
Теги независимо разрешены через GitHub API: v0.1.15 — принятый release SHA;
v0.1.14 остаётся на `72cda3da0dcc559a9ee3df69dc56d8b4db1181d1`, v0.1.13
на `6a8257186aee878087b68fd77716ddce595a012d`. Старые версии не переписаны.

Прочитанный последовательный сценарий публикации требует принятую T061,
точные CI/source, совпадение входных и артефактных сумм, независимое ревью,
проверки состава/secret/path/provenance/license/clean install и обязательный
ShellCheck до создания tag/release. Пропущенный lint v0.1.14 исправлен в
следующей версии. Это достаточный для контракта контролируемый ручной путь;
он не объявляется техническим запретом владельцу вызывать GitHub API иначе.

## Итоговые изменения потребителя и границы

Прочитан весь текущий diff шести файлов реализации/документации и новый основной
validation report на GRAF base `78122f6df7cd0f0321cf48ab2de7c221b348cd84`.
Lock закрепляет версию 0.1.15, ref v0.1.15, source `8f41a53508d0c8ca27afb97cea4b020ae474c6ce`
и rollback v0.1.14. README/quickstart/changelog согласованы; предупреждение
ShellCheck при возврате v0.1.14 и scanner gaps v0.1.13 указаны явно.
В launcher одна правка `CDPATH=''`; местная версия 0.1.13 и исходный LICENSE
сохранены, license expression уточнён. Побайтное равенство местного каталога
опубликованному пакету не заявляется. Исторический FAIL v0.1.14 сохранён
в основном validation report и в этой истории; поздняя проверка не названа ранней.

Квитанция `f216-t062-consumer-check-20261030.json` подтверждает 8 успешных
команд: shellcheck, self-test с непустым CDPATH, governance, development-process,
fragment, Legacy Impact, package scan и diff check. Reviewer прочитал их
журналы и пересчитал все 9 входных хешей на текущих файлах до своих правок:
совпали. APPROVE относится к этим проверенным байтам и двум reviewer-файлам.
При изменении остальных файлов после ревью требуется сверка соответствующих
изменений, а коммиту — обычные обязательные проверки точного SHA/основы.

Reviewer отметил только G23 и полностью перечитал checklist:
**20 checked / 3 unchecked** предметных, **21 checked / 5 unchecked** вместе
с альтернативами решения. G5/G8/G18 и общий BLOCK сохранены. Spec/plan/tasks
не изменены. T062/#7824 не закрывается этим reviewer: нужны consumer PR,
три обязательных GitHub проверки, принятие и успешный live closeout.
Продуктовые Full/CD/Dev, выпуск приложения и общая приёмка F216 вне области.

Доказательства вне git: `f216-t062-v015-real-package-check-20261030.json`,
`f216-t062-v015-independent-review-20261030.md`,
`f216-t062-v015-external-pr-gate-20261030.json`,
`f216-t062-v015-publish-20261030.py`,
`f216-t062-v015-publication-20261030.json`,
`f216-t062-consumer-check-20261030.json` и предыдущая проверка provenance.
Конкретных недостатков принятого состава не обнаружено; всеобщая гарантия
авторства или обнаружения любых секретов не заявляется.

## Историческое ревью v0.1.14 — результат BLOCK сохранён

Дата: 30.10.2026. Проверяющий: отдельный агент `f216_checklist_recheck`.
Lane: read-only review, запись reviewer-owned отчёта и примечания checklist.
Итог: **BLOCK для полной приёмки G23/T062**. G23 остаётся открытым.

## Подтверждённая область

Внешний [PR #8](https://github.com/yshishenya/graf-development-harness/pull/8)
слит: source `d80ce8de68199484e7f4f3d2b48f52d6fb3f4bd9`, merge/release
source `72cda3da0dcc559a9ee3df69dc56d8b4db1181d1`. Деревья равны:
`9b0d62ed951aff6eb827e550c1a7da31966dcf20`; все 41 входных SHA256
совпали с принятым source и ранее проверенными артефактами.

[PR CI 40990151333](https://github.com/yshishenya/graf-development-harness/actions/runs/40990151333)
и [принятый source CI 40990255049](https://github.com/yshishenya/graf-development-harness/actions/runs/40990255049)
независимо прочитаны через GitHub API: правильные event/head SHA, attempt 1,
Python 3.9/3.12 и все предусмотренные шаги self-test, sample, package/context,
PR CLI, версии, настоящей сборки и состава — success.

Прежние независимые ревью установили происхождение доступного состава,
явное исходное разрешение и исправление лицензионных метаданных на
LicenseRef-GRAF-Harness при побайтно сохранённом LICENSE. Реальные артефакты,
34 успешные команды, отдельная чистая установка исправленной версии и цикл
обновление/возврат/обновление приняты в своих областях. Это не юридическая
гарантия авторства и не универсальное обнаружение любых секретов.

[Release v0.1.14](https://github.com/yshishenya/graf-development-harness/releases/tag/v0.1.14)
фактически опубликован 30.10.2026 в 02:20:24 UTC, ID 428588462,
draft=false, prerelease=false. Tag разрешается в принятый точный source.
Reviewer независимо повторно загрузил три asset в память; их байты совпали
с проверенными локальными файлами и повторной загрузкой основного агента:

| Файл | SHA256 |
| --- | --- |
| wheel 0.1.14 | 08d52143f27aaccd90f4f24afceaf4071282c2d78eb419a0ec5e61b161748839 |
| sdist 0.1.14 | 5b0b5161f9ab8a134e19f870a70e723f2eafa33c4de344e8fc21fb47c3494d39 |
| SHA256SUMS.txt | c87bef979dc91858f7341ac01e44085bd59e6fd8320a2fa7404db6d6a712a15c |

Полные опубликованные notes побайтно равны проверенному файлу, SHA256
`d6d41bacacce90a0702b19694672ca1ce7f610f0ed0c65954df9b900cb4ac61c`.
v0.1.13 остаётся на `6a8257186aee878087b68fd77716ddce595a012d`.

## Причина BLOCK

Прочитан контракт `contracts/harness-package.md`: до публикации обязательны
self-test, shellcheck/lint where available, secret/path scan,
provenance/license check и clean sample installation. Проверенный ручной
сценарий публикации действительно блокирует tag/release при отказе своих
проверок, но доступный shellcheck в этот набор не вошёл.

После замечания выполнен ShellCheck 0.11.0 на точном опубликованном launcher
с SHA256 `d3ec39d5672f3036d752dd5e5a8c025924eb63d56616b79c2d875d6dc91d2990`.
Квитанция прямо помечена как поздняя: 02:24:31 UTC. Exit 1, SC1007 в строке 4
на `CDPATH= cd`. Успешная функциональная проверка не заменяет отсутствовавший
обязательный lint. Полный контракт публикации этой версии не принят.

Минимальный следующий путь: узкий патч явного пустого CDPATH, обязательная
проверка в существующем CI, все применимые ворота до следующего неизменяемого
patch-выпуска. Старую v0.1.14 не переписывать; consumer закрепить только
после приёмки новой версии. Этот отчёт не принимает ещё не проверенный патч.
Дополнительная система лицензирования не требуется.

## Состояние reviewer checklist и потребителя

Полностью перечитан `checklists/governance.md`. Сохранены все 23 предметных
критерия: **19 checked / 4 unchecked**. С альтернативами решения в файле
**20 checked / 6 unchecked**. G5/G8/G18/G23 и общий BLOCK сохранены.
Ни одна отметка не изменена, добавлены только причина и ссылка на этот отчёт.

Предварительные consumer изменения v0.1.14 содержательно прочитаны:
точный lock, rollback, документация и минимальное исправление license expression
местного mirror согласованы; LICENSE и местная версия сохранены, равенство
местного каталога внешнему пакету не заявляется. Окончательное APPROVE
consumer PR не выдано: основной агент готовит следующий принятый pin и
исправленный validation report. После готовности требуется новое ревью байтов.

Внешние доказательства хранятся вне git: `f216-t062-final-review-20261030.md`,
`f216-t062-publication-20261030.json`, `f216-t062-real-package-check-20261030.json`,
`f216-t062-publish-20261030.py`, `f216-t062-shellcheck-late-20261030.json` и
прежние provenance/package-review. SHA256 поздней квитанции:
`d88c22178f71c754d9409ba1271cac4a7009c86e2fe88ae11240df27ffa5932d`.

Reviewer не менял code/spec/plan/tasks, Git/GitHub, releases или приложение;
новые сборки, установки, Dev, product Full и deploy не выполнял.
