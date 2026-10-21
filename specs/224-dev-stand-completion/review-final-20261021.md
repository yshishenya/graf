# F224: итоговое независимое ревью трёх исправлений PR7676

Дата: 2026-10-21. Проверяющий: отдельный агент `f224_identity_research`.
Ветка: `codex/224-dev-stand-completion`.
HEAD: `ee45ae2efd0ffd68e8984eb3130275565ccd6f83` плюс проверенный текущий diff.
Путь проверки: существующий US1, **high-risk product area**.

**Решение: APPROVE трёх локальных исправлений; замечаний 0, блокирующих 0.**
Исправления4313857009,4313857014,4314313869 соответствуют принятому
`review-plan-20261021.md` и существующим T003/T004/T005/T008. Это принятие
проверенных рабочих bytes; точные проверки будущего коммита/основы PR,
T008 и общая F224 остаются отдельными обязательствами.

## Проверка изменений

| Замечание | Проверенный результат |
|---|---|
| 4313857009: нестандартный путь приложения при adoption | Сравнение выбранного `_dev_app_destination()` с `DEV_APP_PATH` стоит непосредственно после проверки среды. Эта проверка среды только читает переменные. Отказ предшествует Git identity, созданию машинного каталога/регистрационного lock, operational lock, публикации binding и идемпотентному возврату. Существующее остановленное приложение в другом каталоге не принимается. |
| 4313857014: неизвестный runtime_mode | `_load_active` после проверки схемы и до manifest принимает ровно `live` и `metadata-only`. Проверка по tuple не требует хешируемости значения: JSON list/dict дают управляемый `HarnessError`. Отсутствие, `null`, числа, boolean и неизвестные строки не превращаются в безопасный режим. |
| 4314313869: внешняя Git identity в launch fixture | Подмена `_repo_identity(root=None)` применяется до создания временной binding. Она задаёт собственный канонический repository, сохраняя настоящие binding/ownership/lock проверки. Самостоятельный запуск suite из копии без `.git` успешен. |

В продуктовой части diff ровно четыре добавленные строки в двух существующих
функциях. Общий resolver пути и формат записей не менялись; новых зависимостей,
механизма восстановления или обходного пути нет. Launch fixture получила одну
явную подмену принадлежности. Ownership fixture очищает внешнюю переменную
пути установки; новые случаи дополняют прежние проверки настоящего Git,
не заменяя их подменённой принадлежностью.

Проверены фактические `_publish_active` и все его вызывающие пути: schema
recovery публикует `live`; promote/rollback публикуют `live` либо
`metadata-only`; dry-run указатель не публикует. `compose` остаётся значением
отдельного `runtime.json`, `live-dry-run` — диагностикой build.

Перечень обращений `_load_active` сохранён: adoption, build/build_manifest,
adapter build/promote, retention/prune, promote, status, launch validation,
smoke, rollback и повторные чтения. Прямое чтение указателя в fixture reset
не выдаётся за покрытое общим reader; shared reset по-прежнему запрещён своей
проверкой. Проверки recovery и запрет shared metadata-only publication сохранены.

## Доказательства исходного отказа и успешного исправления

Журналы исполнителя прочитаны из
`/Users/yshishenya/Documents/Codex/2026-10-21/f224-pr-closeout/`:

| Журнал | Подтверждённое содержимое |
|---|---|
| `red-adoption.log` | Исходный код не даёт ожидаемый отказ в16 новых отрицательных случаях; два допустимых режима проходят. |
| `green-ownership-launch.log` | 107 passed,31.64с. |
| `green-focused.log` | 247 passed,34.69с. Это общий результат девяти файлов по validation.md; один короткий журнал сам по себе не перечисляет состав команды. |
| `red-launch-archive-complete.log` | Исходная fixture в копии без `.git`:11 passed/30 errors,27.39с; trace указывает на недоступную Git identity до lifecycle. |
| `green-launch-archive-complete.log` | Исправленная полная копия:41 passed,26.49с. |
| `archive-incomplete-fixture-failure.log` | Первый неполный эксперимент:12 failed/29 passed из-за `launch validation tooling must be regular checkout files`. Этот результат не считается успешным и не скрыт. |

Короткие журналы не содержат собственного реестра SHA файлов. Поэтому
дополнительно выполнены независимые проверки именно текущих bytes:

1. `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -o addopts= -p
   no:cacheprovider tests/governance/test_dev_state_ownership.py -k
   'adoption_rejects_nonstandard_install_before_registration or
   active_pointer_unknown_runtime_mode_fails_closed or
   active_pointer_supported_runtime_modes'`:
   **18 passed,48 deselected,1.26с**.
2. **26 отдельных изолированных проверок границ** через существующие
   временные ownership helpers. По10 значений `null`, true, false,0,1,0.5,
   list,dict,`live ` и пустая строка проверены reader и adoption без runtime;
   до/после сравнены содержимое, inode и структура исходного состояния,
   новая binding отсутствует. Ещё два случая проверяют нестандартный путь
   существующего активного состояния до/после принятия, со снимком всего
   машинного каталога. Четыре положительных случая подтверждают unset,
   пустую строку, пробелы/tab и явный стандартный путь. Все26 PASS.
3. **Независимая копия без `.git`:41 passed,27.10с**. Скопированы ровно пять
   текущих файлов: harness, его wrapper, Swift lifecycle helper, shell
   launch validator и launch test. Для каждого сверены bytes/SHA256 до pytest.
   Тесты запущены из самой временной копии; стандартный origin не менялся.
   Собственные скопированные файлы и временные материалы удалены при выходе.

Независимые18,26 и41 не суммируются с247 как различные тесты: есть пересечения.
Первый запуск дополнительных26 проверок остановился на штатном запрете
символьного `/var` в пути tempfile на Mac. В повторе использован физический
путь самого тестового каталога; защитная функция продукта не менялась.

## Сохранность и границы принятия

Новые репозиторные тесты доказывают отказ нестандартного пути до регистрации
и до идемпотентного возврата, неизменность файлов/inode и отсутствие новой
привязки. Проверки неизвестного режима сравнивают исходные файлы и inode
`promote.lock` и запрещают новую binding. Независимые случаи дополнительно
покрывают существующее активное состояние и явный `null`, который исходный
параметризованный тест заменяет отсутствующим полем.

Оба допустимых режима проходят reader/adoption; `metadata-only` без runtime
не объявляется фактически работающим Dev. Проверки live runtime consistency,
точного SHA, прежней блокировки и frozen adapter не ослаблены. Строгие
реальные Git tests форм origin, Git failure, multiple origin, `insteadOf`,
чужого репозитория, clone/worktree и другого cwd сохранены.

Оба reviewer-owned списка повторно прочитаны: requirements **16 отмечено /
0 не отмечено**, infra **20 / 0**, всего **36 / 0**. Checkbox state сохранён.
Уточнение и реализация не меняют качество оставшихся требований, обязанности
US2/US3 и различие искусственной проверки/живой приёмки.

Три замечания имеют достаточное локальное доказательство исправления.
Их разрешение в GitHub выполняет основной агент в пределах своего назначения.
T008 требует текущие проверки точного коммита/основы PR. T009–T013,
live adoption, фактические lifecycle/rollback/TCC, миграционное принятие
F249 T038/#6786 и закрытие #6180 остаются открытыми. Выпуск/развёртывание
не выполнялись и этим ревью не принимаются.

В этом назначении менялись только примечания двух reviewer-owned списков
и этот отчёт. Код/spec/plan/tasks, Git/GitHub, Dev, Docker, серверы, настоящая
binding Mac и пользовательские данные не менялись. `git diff --check` PASS.

## Контрольные суммы текущих файлов

| Файл | SHA256 |
|---|---|
| `scripts/dev-harness.py` | `4d396a1ab7c3a7abaaee9b9f0cb97eca9872483ded9d81a1d18afdc545a31d50` |
| `tests/governance/test_dev_state_ownership.py` | `ae8be0f2e639b250117aa8f2f6a458c06fbf3ff57ce0802f96e2b1b4bccb0560` |
| `tests/governance/test_dev_launch_validation.py` | `2e3113f08808c36d4bae06c1a53e6535124a50d5e009782134db201f0a4384f9` |
| `infra/scripts/dev-harness.sh` | `713aaed031fab7ca6d3c6d6981e28f60a0d58d3ecf40fa119e682fd23f4e99ef` |
| `apps/macos/Scripts/dev-app-lifecycle.swift` | `74fe2bd3da8bfd3c068740642b40e0aaf625bdc9b28ad659163bc94b1fb62520` |
| `apps/macos/Scripts/validate-packaged-app-launch.sh` | `81a5af77b9b711ff9012c4176892193411ceddc6469473e833c6ab28c2d74b67` |
| `spec.md` | `10f19dfc5ad304073d35942357c7732d9ed79de441340266ca8528b7bc583a63` |
| `plan.md` | `b920a103d0f952943682330287e120571e4669e2813247ff4e7236348104ff27` |
| `tasks.md` | `fb132158055ba2b8dcbd3626e7d5f3817f98dd8a23123f313286cfa95cd28ab3` |
| `quickstart.md` | `a563f834d7fc95f350273bcacade4cb023f0add4cb1bbdca05ca47d041e6f1f7` |
| `validation.md` | `025f170b8ba3c1409ccf70bc07b6a6c2abbb96606cfa750d3799a4e6be4e306b` |

## Контрольные суммы журналов исполнителя

| Журнал | SHA256 |
|---|---|
| `red-adoption.log` | `ca8398cff1aea9495ad11f723b6e87371b8bdec06e90cd52c55aa5e087e5a194` |
| `green-ownership-launch.log` | `51a17ed5bf295f9bce7489493538299f20c5fd6a9833d16ab23ec13a0bed0ce8` |
| `green-focused.log` | `832b645f346574892c101f6aef0e20c89664c72b60f925f03b6ff5220207600c` |
| `red-launch-archive-complete.log` | `4b784c0d61a73317e92b52c54e6a4a61977afffd0b897db6975eed4d2f4a0fee` |
| `green-launch-archive-complete.log` | `ce2400f331ff5c12c82b74097d28e5cc275caa208ef57d524de0c61f6131f432` |
| `archive-incomplete-fixture-failure.log` | `385843186f48352cb6e8f8f9aa8552b4991f8dd3d92da0ed5d4fd35f8227ff96` |
