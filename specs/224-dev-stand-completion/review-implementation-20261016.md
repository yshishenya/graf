# F224 US1: независимое ревью реализации

Дата: 2026-10-16. Reviewer: review_f224_design, отдельный агент.
Итог после независимого повторного ревью: **PASS US1**. Все три первоначальных
findings исправлены и перепроверены; открытых замечаний0. Первый snapshot
получил REQUEST_CHANGES (один P1, два P2); его основания сохранены ниже как
история проверки. Checklist markers не изменялись.

Проверен текущий незакоммиченный diff, новый ownership suite, изменения прежнего
adapter suite, независимый probe F259, документация и changelog F224.
Использован skill code-reviewer. Предыдущие требования/план/контракт/задачи
и reviewer report сопоставлены с реализацией. Это ревью US1; US2/US3,
живое принятие, TCC, release/deploy не подтверждаются.

## Первоначальные findings — все RESOLVED

### [P1] F224-IMPL-01: --expect-empty не исключает существующие тома данных

Файл: scripts/dev-harness.py:320–324, _assert_empty_dev_machine.

Проверка Docker ограничена `docker ps -aq` по compose label. После обычного
`docker compose down` контейнеров уже нет, но именованные
`graf-dev-postgres-data` и `graf-dev-minio-data` сохраняются. Эти же имена
жёстко заданы в infra/docker-compose.dev.yml:336–340. При отсутствующем app
и пустом новом state root --expect-empty принимает машину как пустую,
публикует новую принадлежность, а последующий штатный запуск подключает
сохранившиеся данные без доказательства их исторического владельца.

Изолированное воспроизведение: подменены только ответы pgrep/Docker и путь
отсутствующего Dev. Docker ps вернул пусто; модель ответа volume ls содержала
два указанных тома. Функция завершилась успешно, список фактических запросов
содержал только ps; volume query вообще не выполнялась. Реальный Docker не
вызывался. Таким образом отсутствие containers ошибочно считается достаточным
доказательством отсутствия shared runtime/data.

Нужно до публикации binding явно исключить оба именованных тома; недоступность
проверки должна давать отказ. Не удалять/очищать найденные тома. Нужен
изолированный отрицательный тест «контейнеров/app нет, том существует».

### [P2] F224-IMPL-02: startup guard принимает исходный symlink state root

Файл: scripts/dev-harness.py:886–891, _schema_start_guard.

Сравнение `root.resolve() != state_dir(live=True)` нормализует исходный путь
раньше проверки его компонентов. Поэтому прямой `schema-start-guard
--state-root <symlink-to-adopted-root>` проходит, хотя contract US1/FR-003/004
и общий path checker запрещают символьные ссылки на этой границе.
Прямой startup guard явно входит в T005 и принятую матрицу всех callers.

Воспроизведено без приложения: настоящий временный Git repo, временный HOME,
принятый пустой fixture root, отдельная symlink на него. Вызов
`_schema_start_guard(alias, 'a'*40)` успешно вернул None при отсутствии журнала.
`_checked_state_path(alias)` для того же пути должен отказывать.

Нужно проверять исходный root через общий безопасный path/ownership guard до
resolve/чтения журнала. Добавить отрицательный тест прямого startup caller.
Проверку frozen startup не подменять и не обходить.

### [P2] F224-IMPL-03: state_lock пишет .dev-boundary до получения lock

Файл: scripts/dev-harness.py:2609–2615, особенно _mkdirs на2612.

После нового adopt-state у пустого root есть promote.lock, но нет
.dev-boundary. state_lock вызывает _mkdirs до flock; _mkdirs атомарно пишет
этот файл. Другой процесс в этот момент может законно удерживать прежний lock.
Заявленные FR-004 и contract требуют operational lock до первого изменения
shared состояния. Правильный ownership preflight не заменяет право записи.

Воспроизведено настоящей kernel flock и дочерним процессом на временных
repo/HOME/state: первый владелец удерживал promote.lock; второй ещё ожидал
получения lock, но .dev-boundary уже появился. Вывод проверки:
`marker_written_while_other_owner_held_lock=true, contender_still_waiting=true`.

Нужно перенести создание marker внутрь полученной operational lock. Для нового
fixture можно подготовить каталог, необходимый для открытия lock, но общие
файлы состояния должны записываться только после lock и ownership recheck.
Добавить минимальный отрицательный межпроцессный сценарий.

## Выполненная проверка

Команда из подготовленной среды, без установки зависимостей:

```sh
python -m pytest -q -o addopts= \
  tests/governance/test_dev_state_ownership.py \
  tests/governance/test_dev_harness.py \
  tests/governance/test_graf_local_adapter.py
```

Результат: **108 PASS,0 FAIL,3.26s**. Этот набор не покрывал три приведённых
пробела; их независимо воспроизвели дополнительными временными проверками.
Проверки вызывают временные Git repos и процессы, подменяют внешние действия.
Реальное приложение, Docker, installed state и production не изменялись.
Единственный созданный постоянный файл этого ревью — настоящий отчёт.

Подтверждены положительные стороны реализации: raw/effective origin сравниваются
без публикации URL; Git failure не возвращает basename; невалидный binding
не обходится fixture mode; old lock inode сохраняется и перепроверяется после
ожидания; frozen source bytes проверяются до resolver subprocess; fixture
retention не получает разрешение на общие Docker tags. Эти проверки не снимают
findings выше и не означают принятие полного исходного #6180.

Первоначально были обязательны повтор affected tests и независимое повторное
ревью нового snapshot; они выполнены в следующем разделе. Закрытие
issues/commit/merge этим отчётом не разрешены.

## Первый проверенный snapshot

HEAD основы: f4b38141af2fad64bae219e8c012b0a54f237491.
SHA256 файлов текущего незакоммиченного snapshot:

```text
c3e9c945a1bb7d36f9f6aea1424e1f95d5d291f1a125f86a395acba4f37fbf25  scripts/dev-harness.py
58827d300392ffb4603d6c345a1573ed435e241f6ca4883303594bba733667b0  tests/governance/test_dev_state_ownership.py
35b56cb3c785c00854091d05ffd8ce51778d5b08bb777b6a41055e7ed49d1bbb  tests/governance/test_graf_local_adapter.py
9ea3f1b7519b0ff7bd2e2ada078456e3907236c07e1b768c1eaa35047f967eef  specs/259-audit-remediation/evidence/dev-identity-probe.py
86eea95c893fddf9eee22fbf2f199e6d661d69d19ca88c97ea426450e495587e  infra/dev/README.md
d4fb4476f5d06b5b6e056563b253ac0a5a09f0e2d0cd6643938d7f701d4fdd15  docs/agent-guidance/local-development.md
5db4ca35b7b795b11842f15b6d9cd883e302c54abecfe1a2d9da5b4d64bfe63f  changes/unreleased/F224.yaml
10f19dfc5ad304073d35942357c7732d9ed79de441340266ca8528b7bc583a63  specs/224-dev-stand-completion/spec.md
bb52559d92153bbffd3d617e8ef35fa74292791e54687217455ae61e31705c2e  specs/224-dev-stand-completion/plan.md
bfffa6f74ba41e6fc51e1ef490b1e644c4d15eaf1fe56b45b5c546658425cc8d  specs/224-dev-stand-completion/research.md
0227601333fb82afe7e99cdfe95cab2ae1a7860efe1f42e058a121830a5fb9ab  specs/224-dev-stand-completion/data-model.md
ee4d3d6e618dd83f5ce414edc70f15c403688434180532e04f3fdcb35e38018d  specs/224-dev-stand-completion/contracts/state-ownership.md
baa4816bc760f2d9ac60a212f612b96e63421a7acfa956dbf8ebb94ce351c918  specs/224-dev-stand-completion/quickstart.md
ecdbe3f530815e896f9060c2fd0256919d47a7e79a6d65ec0885d77fd7683b0a  specs/224-dev-stand-completion/tasks.md
1a68b1573d00bd3abb109be577567683e2c98610235b0f468c1f9db83784b02e  specs/224-dev-stand-completion/review-design-20261016.md
```

## Независимая перепроверка исправлений

Повторно прочитан весь текущий diff harness, семь новых regression cases и
соответствующие call paths. Требования проекта не менялись: SHA256 всех семи
spec/plan/research/data-model/contract/quickstart/tasks совпали с принятым
review-design-20261016.md. Код и тесты исправляют существовавшие требования.

- F224-IMPL-01 RESOLVED: _assert_empty_dev_machine проверяет `docker volume ls`
  и отвергает все три жёстких тома из compose: PostgreSQL, MinIO, media-work.
  Ошибка запроса даёт безопасный отказ; удаления томов нет. Проверка присутствует
  также при повторном чтении после ожидания old lock.
- F224-IMPL-02 RESOLVED: startup guard перед сравнением вызывает
  _checked_state_path на исходном root. Symlink не нормализуется до проверки
  и теперь отвергается; обычный принятый root остаётся допустимым.
- F224-IMPL-03 RESOLVED: до flock создаётся только каталог, необходимый для
  открытия lock; .dev-boundary создаётся после lock и ownership recheck.
  При удерживаемом old lock marker отсутствует до освобождения.

Прочитан внешний журнал F224-review-regressions-before.log: все7 новых случаев
действительно FAIL до исправлений (38 остальных deselected). Независимо повторена
та же команда ownership+harness+adapter: **115 PASS,0 FAIL,3.44s**.
`git diff --check`: PASS. Реальные приложение/Docker/build не запускались.
Все репозитории, HOME/state и процессные locks для проверок временные.

Других блокирующих пробелов в проверенном текущем US1 snapshot не обнаружено.
Это утверждение ограничено прочитанным diff и изолированной матрицей; реальное
adopt-state, macOS smoke, TCC, US2/US3, exact-SHA PR checks и принятие общей
#6180 остаются открытыми. Файл требований reviewer и checkbox markers не менялись.

## Итоговый проверенный snapshot

SHA256 после исправлений; новый commit меняет source SHA и требует своих CI gates.

```text
1b6a7492f75969de1f90cc187f28d6f99f66a94ea7288f1862424dc4b19f6143  scripts/dev-harness.py
f245b8ff52923c0ef1656db3595701b4c30c958b971659c076e98e3fad0690db  tests/governance/test_dev_state_ownership.py
35b56cb3c785c00854091d05ffd8ce51778d5b08bb777b6a41055e7ed49d1bbb  tests/governance/test_graf_local_adapter.py
9ea3f1b7519b0ff7bd2e2ada078456e3907236c07e1b768c1eaa35047f967eef  specs/259-audit-remediation/evidence/dev-identity-probe.py
86eea95c893fddf9eee22fbf2f199e6d661d69d19ca88c97ea426450e495587e  infra/dev/README.md
d4fb4476f5d06b5b6e056563b253ac0a5a09f0e2d0cd6643938d7f701d4fdd15  docs/agent-guidance/local-development.md
5db4ca35b7b795b11842f15b6d9cd883e302c54abecfe1a2d9da5b4d64bfe63f  changes/unreleased/F224.yaml
10f19dfc5ad304073d35942357c7732d9ed79de441340266ca8528b7bc583a63  specs/224-dev-stand-completion/spec.md
bb52559d92153bbffd3d617e8ef35fa74292791e54687217455ae61e31705c2e  specs/224-dev-stand-completion/plan.md
bfffa6f74ba41e6fc51e1ef490b1e644c4d15eaf1fe56b45b5c546658425cc8d  specs/224-dev-stand-completion/research.md
0227601333fb82afe7e99cdfe95cab2ae1a7860efe1f42e058a121830a5fb9ab  specs/224-dev-stand-completion/data-model.md
ee4d3d6e618dd83f5ce414edc70f15c403688434180532e04f3fdcb35e38018d  specs/224-dev-stand-completion/contracts/state-ownership.md
baa4816bc760f2d9ac60a212f612b96e63421a7acfa956dbf8ebb94ce351c918  specs/224-dev-stand-completion/quickstart.md
ecdbe3f530815e896f9060c2fd0256919d47a7e79a6d65ec0885d77fd7683b0a  specs/224-dev-stand-completion/tasks.md
1a68b1573d00bd3abb109be577567683e2c98610235b0f468c1f9db83784b02e  specs/224-dev-stand-completion/review-design-20261016.md
```

## Окончательная сверка US1 перед запросом commit approval

Повторно прочитаны изменённые retention/ownership tests, tasks.md, validation.md,
уточнение local-development и внешние analyze/sync/convergence records.
Продуктовый harness совпадает с ранее принятым snapshot побайтно; шесть базовых
документов spec/plan/research/data-model/contract/quickstart также неизменны.
Итог: **PASS US1, findings0**. Отдельное разрешение на commit ещё требуется.

Два старых retention-теста явно подменяют принадлежность общему состоянию;
все Docker/native операции в них уже заменены искусственными вызовами.
Их назначение — сохранность retention logic, а не проверка origin/binding.
Расширенная отдельная ownership-матрица использует настоящее временное
adopt-state и проверяет обе стороны: fixture не вызывает image rm, принятый
root вызывает только подменённые docker image rm. Проверка не ослабляет
продуктовый guard и не является доказательством реальной очистки Docker.

Независимо повторены ownership+retention: **55 PASS,0 FAIL,2.80s**.
Просмотрен полный итоговый журнал восьми файлов: **186 PASS,0 FAIL,0 SKIP,5.11s**;
это результат исполнителя, не дополнительно выполненные reviewer186 проверок.
Пересекающиеся прогоны не суммируются. `git diff --check`: PASS.

Маркеры T001–T007 соответствуют локальным реализованным результатам и прочитанным
analyze/sync records; T008–T013 остаются открытыми. В tasks и validation явно
отделены локальные результаты от принятия GitHub issues/PR и живого стенда.
Convergence record не объявляет всю F224 сошедшейся: US1 gaps0, широкий остаток
имеет прежних владельцев, F249 T038/#6786 не продублирована. Validation честно
фиксирует dirty snapshot на прежней основе, а не будущий commit SHA.

Reviewer не менял markers/задачи/код/GitHub и не запускал live app/Docker/build.
Обновлён только этот отчёт. Реальный adopt-state, T008 exact-SHA fast/PR checks,
US2/US3, Dev TCC, принятие общей #6180 и выпуск остаются самостоятельными воротами.

Окончательные SHA256 прочитанных файлов (отчёт не хеширует сам себя):

```text
1b6a7492f75969de1f90cc187f28d6f99f66a94ea7288f1862424dc4b19f6143  scripts/dev-harness.py
e787abbcd1fc77962e1161cdbd478af49a6a83fa6b44cc302bd2455b8bbf2a49  tests/governance/test_dev_state_ownership.py
d243de998852ed4c54ffc8fdc85222902f3f3436fbc4403d574e5591b2a99428  tests/governance/test_dev_state_retention.py
35b56cb3c785c00854091d05ffd8ce51778d5b08bb777b6a41055e7ed49d1bbb  tests/governance/test_graf_local_adapter.py
9ea3f1b7519b0ff7bd2e2ada078456e3907236c07e1b768c1eaa35047f967eef  specs/259-audit-remediation/evidence/dev-identity-probe.py
86eea95c893fddf9eee22fbf2f199e6d661d69d19ca88c97ea426450e495587e  infra/dev/README.md
904745b03ca97ac28f76b92cc056ad7936f7051b3a2ae7910bfb3e02cd55f356  docs/agent-guidance/local-development.md
5db4ca35b7b795b11842f15b6d9cd883e302c54abecfe1a2d9da5b4d64bfe63f  changes/unreleased/F224.yaml
10f19dfc5ad304073d35942357c7732d9ed79de441340266ca8528b7bc583a63  specs/224-dev-stand-completion/spec.md
bb52559d92153bbffd3d617e8ef35fa74292791e54687217455ae61e31705c2e  specs/224-dev-stand-completion/plan.md
bfffa6f74ba41e6fc51e1ef490b1e644c4d15eaf1fe56b45b5c546658425cc8d  specs/224-dev-stand-completion/research.md
0227601333fb82afe7e99cdfe95cab2ae1a7860efe1f42e058a121830a5fb9ab  specs/224-dev-stand-completion/data-model.md
ee4d3d6e618dd83f5ce414edc70f15c403688434180532e04f3fdcb35e38018d  specs/224-dev-stand-completion/contracts/state-ownership.md
baa4816bc760f2d9ac60a212f612b96e63421a7acfa956dbf8ebb94ce351c918  specs/224-dev-stand-completion/quickstart.md
fb132158055ba2b8dcbd3626e7d5f3817f98dd8a23123f313286cfa95cd28ab3  specs/224-dev-stand-completion/tasks.md
b8d2aa85a41a2de5acaae304642c2fa0fc4fcf570433b6d75c20b79481cb72b6  specs/224-dev-stand-completion/validation.md
99432604b58ef42d66c468eb4d6e69e77bce47f328abd04e7f92ebcc3dd93a86  specs/224-dev-stand-completion/checklists/requirements.md
e6d0864d7cbceccb8d78633e54ee32598d04dfe399cc8a098fb1e1f94d70c237  specs/224-dev-stand-completion/checklists/infra.md
1a68b1573d00bd3abb109be577567683e2c98610235b0f468c1f9db83784b02e  specs/224-dev-stand-completion/review-design-20261016.md
```
