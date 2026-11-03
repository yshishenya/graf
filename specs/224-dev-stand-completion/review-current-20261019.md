# F224 US1: текущая независимая проверка до коммита

Дата: 2026-10-19. Reviewer: отдельный агент f263_performance_review.
Ветка: `codex/224-dev-stand-completion`.
Основа HEAD: `f4b38141af2fad64bae219e8c012b0a54f237491`.
Режим: независимое чтение реализации и журналов, без запуска тестов и сборок.
Путь проверки: **high-risk product area**, существующий Spec Kit срез US1.

**Решение: APPROVE текущей локальной US1 T001–T007. Новых блокирующих
замечаний: 0.** Требования: requirements **16 checked / 0 unchecked**,
infra **20 checked / 0 unchecked**, всего **36 / 0**. Это качество требований,
а не приёмка установленного приложения или всей F224. T008 и T009–T013
остаются открытыми. Слияние удерживается до согласованного завершения F280.

## Объём и способ проверки

Прочитаны текущие spec, plan, tasks, quickstart, research, data-model,
contracts/state-ownership, оба чеклиста, design/implementation review,
validation; AGENTS, guidance index, spec-kit-flow, constitution7.1.0,
product-gates, local-development и применимые release-and-validation правила.
Проверены diff harness, README/guidance, identity probe, адаптерных/retention
тестов и фактический новый ownership suite, который пока не отслеживается Git.
Обычный git diff сам по себе этот новый файл и восстановленные specs не покрывает.

Проверены прямые вызывающие пути state_dir/global_state_dir, build_manifest,
state_lock, build/promote/rollback/rehydrate/recover-schema/prune/reset-data,
status/smoke, startup guard, _checkout_adapter, _assert_supported и retention.
start-dev-runtime.sh вызывает штатный schema-start-guard, wrapper запускает тот
же harness. Новых зависимостей, второго приложения или обходного workflow нет.

До моих разрешённых документальных правок **17 из 20** файлов реестра
F224-US1-validated-files.json совпали побайтно. Различались только текущие
plan/status, quickstart и validation. Они прочитаны целиком: уточняют дату,
свободное место, текущий повтор и оставшиеся ворота без изменения требований
US1, алгоритма и критериев US2/US3. Runtime/test/guidance paths в локальном
origin/master не менялись относительно основы f4b3814; сеть и GitHub в этой
проверке не использовались, свежесть удалённого master здесь не подтверждается.

## Проверка реализации US1

| Граница | Независимый вывод по текущему коду и тестам |
|---|---|
| Origin | _repo_identity читает ровно один raw origin и effective origin через настоящий Git; разрешены явные HTTPS/SSH/SCP формы. Ошибка Git не возвращает basename; query/fragment/credentials/escapes и подмена insteadOf дают безопасный отказ без вывода URL. |
| Binding | _read_repository_binding строго проверяет набор полей, схему, canonical repository, абсолютный допустимый root, SHA и дату. Повреждённую запись нельзя обойти fixture override. Общее состояние без binding не создаётся автоматически. |
| Явное принятие | operation_adopt_state требует подтверждения, ожидаемого repository и ровно одного expected SHA/expect-empty. Прежний root не переносится. Проверяются другие непустые стандартные roots, recovery/schema markers, pointer/manifest/runtime и записанные images. Идентичный повтор не перезаписывает binding. |
| Пустая машина | _assert_empty_dev_machine проверяет отсутствие Dev app, его процесса, graf-dev containers и всех трёх жёстких data volumes. Неизвестный ответ даёт отказ; найденные тома не удаляются. После ожидания старого lock проверка повторяется. |
| Сериализация | Registration lock предшествует старому promote.lock. _state_file_lock проверяет исходный путь, тип, владельца, доступ, nlink и inode после flock. state_lock повторяет ownership после ожидания и лишь затем пишет .dev-boundary. Active SHA при принятии и parent при promote перечитываются внутри lock. |
| Прерывание принятия | Публикация binding использует существующий fsync→replace→fsync каталога. Процессные тесты прерывают до/после публикации; запись либо отсутствует, либо полна. Старые manifests/runtime и inode lock сохраняются. Это не доказательство атомарности обычного promote. |
| Общие операции | CLI и прямые live adapter paths проверяют принадлежность до воздействия. Shared metadata-only promote/rollback/reset и publication запрещены. Fixture root должен быть изолирован, не пересекаться с shared root и не даёт live прав. |
| Prune | _apply_retention проверяет ownership до файлового удаления. _live_state_owns_tags удерживает все общие tags при fixture независимо от manifest IDs; реальная временная binding матрица проверяет и fixture, и принятую общую ветвь, Docker подменён. |
| Старый адаптер | _checkout_adapter сохраняет clean exact SHA, committed tracked bytes и runtime-definition digest; сравнивает canonical origins. До первого stop/install исполняет ограниченный resolver probe проверенных bytes. Несовпадение/timeout дают отказ, frozen startup guard не переписывается. |
| Чтение и smoke | Status читает снимок, не создаёт lock/root и не обещает завершённый параллельный переход. Smoke --live повторяет ownership и сравнивает active identity по окончании. Fixture receipt явно неавторитетна. |

Изменения двух старых retention-тестов прямо моделируют общую принадлежность;
внешние действия в них подменены. Это не доказательство самой binding или
реальной Docker очистки. Подлинная ownership матрица находится отдельно.
Положительный frozen-adapter test временно отключает только платформенную
проверку в искусственном committed checkout; clean/tracked-byte/resolver gates
сохраняются. Это не приёмка macOS адаптера на установленном стенде.

Предыдущие три замечания implementation review остаются исправленными:
проверка томов, исходного symlink startup root и порядок записи marker после
lock. Прочитаны исходные журналы: новая начальная матрица дала 24 FAIL / 1 PASS,
семь дополнительных случаев — 7 FAIL; текущий XML подтверждает прохождение
их актуальных версий. Начальная матрица включает отказы отсутствующих новых
API; её число FAIL не выдаётся за число самостоятельных runtime-дефектов.
Новых runtime-воспроизведений в этом ревью не делалось.

## Самостоятельный пересчёт текущих журналов

Из внешнего реестра f224-current-preflight прочитаны current-governance.log,
current-governance.xml и identity-probe.log. XML разобран независимо от итоговой
строки: **186 testcase, 186 различных (classname,name), 186 PASS,
0 failure, 0 error, 0 skipped**. Длительность suite5.891s; округлённый вывод
pytest5.90s. Пересекающиеся исторические прогоны не суммируются.

| Файл | PASS |
|---|---:|
| test_dev_state_ownership.py | 46 |
| test_dev_harness.py | 23 |
| test_graf_local_adapter.py | 47 |
| test_dev_schema_transition.py | 51 |
| test_dev_promotion_transaction.py | 3 |
| test_dev_runtime_identity.py | 5 |
| test_dev_live_smoke.py | 2 |
| test_dev_state_retention.py | 9 |
| Всего | 186 |

Identity receipt содержит основу f4b38141af2fad64bae219e8c012b0a54f237491 и
четыре true: разные repositories изолированы, Git failure отклонён, другой cwd
не меняет identity, alias одного repository совпадает. Исходник probe использует
настоящие временные Git repos. Сохранённое имя relative_common_dir... теперь
обозначает независимость от cwd: resolver больше не использует git-common-dir.
Это проверка identity; она не читает и не принимает установленное состояние.
SHA в receipt относится к HEAD основы с незакоммиченными изменениями,
а не к будущему коммиту.

Журналы предоставлены исполнителем; reviewer самостоятельно пересчитал XML,
сверил содержимое probe и контрольные суммы. Reviewer не запускал эти186 тестов
повторно и не выдаёт просмотр журнала за собственное исполнение.

## Повторная проверка каждого пункта требований

| Пункт | Текущее достаточное основание |
|---|---|
| Q001 | Spec задаёт результат, выбор binding/locks/parser находится в plan/contract. |
| Q002 | Три истории раскрывают пользу достоверной версии, сохранности и восстановления. |
| Q003 | Истории/FR понятны как наблюдаемые действия и отказы; нужные обозначения точны. |
| Q004 | Все обязательные разделы spec заполнены. |
| Q005 | Clarifications разрешают границы из исходных issues и правила одного Dev; технические решения заданы отдельно. |
| Q006 | FR-004/006/008/016 и contract сохраняют один root/lock/app и исключают fixture shared effects. |
| Q007 | SC-001–006 задают проверяемые пары identity, процессы, сохранность, версию и разрешения. |
| Q008 | SC не навязывают алгоритм хранения или новый слой. |
| Q009 | Три истории имеют положительные и отказные сценарии и независимые тесты. |
| Q010 | Edge Cases включают origin/cwd/clones/paths/конкуренцию/старое состояние. |
| Q011 | FR-017/018 и T008–T013 сохраняют полный объём #6180 отдельно от US1. |
| Q012 | Assumptions/quickstart/validation сохраняют границы занятого Dev; текущие254GiB отделены от старых27GiB. |
| Q013 | Таблица requirements coverage связывает все18 FR и6 SC с задачами и приёмкой. |
| Q014 | US2 задаёт штатный lifecycle, US3 — сбои, schema compatibility и Dev TCC. |
| Q015 | Статусы spec/tasks/validation отделяют существующий локальный код от принятия PR и установленного стенда. |
| Q016 | Input/Status явно называют восстановление отсутствующих оригиналов; итог всей F224 не заявлен. |
| CHK001 | Contract канонизации задаёт формы/aliases/отказы без публикации URL. |
| CHK002 | US1/FR-001–002 и quickstart разделяют worktrees/clones/чужие origins без basename/cwd. |
| CHK003 | Research/data-model/contract требуют операторского подтверждения исторического владельца, совпадения SHA мало. |
| CHK004 | FR-006/data-model сохраняют данные, secrets, manifests, runtime, journals, archives и старый lock inode на месте. |
| CHK005 | Contract отказывает при неизвестных стандартных roots и честно ограничивает обнаружение нестандартных overrides. |
| CHK006 | Contract/data-model различают registration и operational locks, порядок только registration→operational. |
| CHK007 | FR-005/contract требуют повторной проверки binding/parent/expected SHA после ожидания. |
| CHK008 | Binding transitions задают единственную атомарную публикацию, повтор и запрет перепривязки. |
| CHK009 | Contract задаёт исходные symlink/owner/type/inode/path проверки до воздействия. |
| CHK010 | Contract обычных операций называет все CLI shared callers, status/smoke/startup/direct adapter/build_manifest/prune. |
| CHK011 | Contract запрещает fixture app/Docker/shared tags и metadata-only смену общего active pointer. |
| CHK012 | FR-009–011/contract различают snapshot, fixture и живой smoke с проверкой identity в конце. |
| CHK013 | Contract adapters сохраняет exact SHA/clean/tracked-byte/digest и ранний resolver probe. |
| CHK014 | Contract/research явно ограничивают защиту от самостоятельного старого controller; его jobs исключает оператор. |
| CHK015 | FR-008–014/017–018, US2/US3 и T009–T013 сохраняют широкую отдельную приёмку. |
| CHK016 | Research/plan/T010 сохраняют ordinary-promote crash gap; T011 оставляет миграцию F249 T038/#6786. |
| CHK017 | Quickstart/T012 задают Dev-only до/update/relaunch/после, signer/entitlements и оба разрешения без reset/второго app. |
| CHK018 | FR-017–018/research/validation отделяют исторические результаты от текущего source и полного umbrella. |
| CHK019 | Quickstart/contract/T003–T007 требуют отрицательные и межпроцессные сценарии, сохранность и отсутствие shared effects. |
| CHK020 | Plan/quickstart/tasks разделяют US1, будущий проект US3, post-commit fast, точные PR checks и frozen release-full. |

Checkbox state не менялся: в оба списка добавлена только запись о текущем
независимом перечитывании. В старом implementation report заменён только один
личный абсолютный путь интерпретатора на переносимый python; остальные
исторические выводы, команды, числа и контрольные суммы сохранены.

## Незавершённые ворота

- T008/#6188: разрешённый проверенный коммит, bounded fast неизменного SHA,
  governance-fast/macos-pr/pr-metadata точного PR SHA и проверенной основы,
  сверка критериев каждого закрываемого issue после принятия изменения.
- T009: фактический один Dev, процесс/путь/bundle/signer/channel и SHA всех служб;
  отрицательная проверка отсутствующей обязательной службы.
- T010: сначала воспроизводимый crash обычного promote, затем отдельный
  уточнённый проект/reviewer/analyze/sync до исправления recovery.
- T011 и F249 T038/#6786: штатный живой цикл, совместимый откат и отдельно
  доказанный переход схемы; исторические доказательства не закрывают нынешний SHA.
- T012: фактическая Dev-only матрица сохранения разрешений.
- T013/#6180: полная сходимость18 FR/6 SC/13 tasks, принятые PR, frozen
  release-full и все живые критерии. US1 не разрешает закрыть общую задачу.

Реальный adopt-state, приложение, Docker, TCC, Windows, GitHub, коммиты,
слияния, выпуск и развёртывание reviewer не менял. Поддерживается согласованное
удержание слияний до завершения выпуска F280. Новое независимое ревью даёт
основание готовить текущую US1 к коммиту/PR в рамках действующего разрешения,
при соблюдении оставшихся ворот.

## Контрольные суммы прочитанного снимка

SHA256 после разрешённых правок reviewer. Report не хеширует сам себя.
Изменение кода или проверяемых требований требует оценки затронутого вывода;
любой будущий commit получает собственный source SHA и обязательные CI gates.

```text
5db4ca35b7b795b11842f15b6d9cd883e302c54abecfe1a2d9da5b4d64bfe63f  changes/unreleased/F224.yaml
904745b03ca97ac28f76b92cc056ad7936f7051b3a2ae7910bfb3e02cd55f356  docs/agent-guidance/local-development.md
86eea95c893fddf9eee22fbf2f199e6d661d69d19ca88c97ea426450e495587e  infra/dev/README.md
1b6a7492f75969de1f90cc187f28d6f99f66a94ea7288f1862424dc4b19f6143  scripts/dev-harness.py
9f028482fb4e9effbb8deb115f5f7a7cd62c1cf6e60330212fe693d7255af6b9  specs/224-dev-stand-completion/checklists/infra.md
080b064ec213d39f1b43e297dd1f95430e3ed776533d8d723ca141508d943319  specs/224-dev-stand-completion/checklists/requirements.md
ee4d3d6e618dd83f5ce414edc70f15c403688434180532e04f3fdcb35e38018d  specs/224-dev-stand-completion/contracts/state-ownership.md
0227601333fb82afe7e99cdfe95cab2ae1a7860efe1f42e058a121830a5fb9ab  specs/224-dev-stand-completion/data-model.md
75302bc8a06ffb4e7cb473f1f6a0bbb78c3ae772a89f8f7d1435700302f6ff02  specs/224-dev-stand-completion/plan.md
a563f834d7fc95f350273bcacade4cb023f0add4cb1bbdca05ca47d041e6f1f7  specs/224-dev-stand-completion/quickstart.md
bfffa6f74ba41e6fc51e1ef490b1e644c4d15eaf1fe56b45b5c546658425cc8d  specs/224-dev-stand-completion/research.md
1a68b1573d00bd3abb109be577567683e2c98610235b0f468c1f9db83784b02e  specs/224-dev-stand-completion/review-design-20261016.md
f792c4f20aff0c69cc21b4ed59485675f7e956eb5ff1ac9b2767276bd45ac92d  specs/224-dev-stand-completion/review-implementation-20261016.md
10f19dfc5ad304073d35942357c7732d9ed79de441340266ca8528b7bc583a63  specs/224-dev-stand-completion/spec.md
fb132158055ba2b8dcbd3626e7d5f3817f98dd8a23123f313286cfa95cd28ab3  specs/224-dev-stand-completion/tasks.md
9c3be3c740838bbbddbb60afdefacc59813f7b584150f739fb6ecee79027413f  specs/224-dev-stand-completion/validation.md
9ea3f1b7519b0ff7bd2e2ada078456e3907236c07e1b768c1eaa35047f967eef  specs/259-audit-remediation/evidence/dev-identity-probe.py
e787abbcd1fc77962e1161cdbd478af49a6a83fa6b44cc302bd2455b8bbf2a49  tests/governance/test_dev_state_ownership.py
d243de998852ed4c54ffc8fdc85222902f3f3436fbc4403d574e5591b2a99428  tests/governance/test_dev_state_retention.py
35b56cb3c785c00854091d05ffd8ce51778d5b08bb777b6a41055e7ed49d1bbb  tests/governance/test_graf_local_adapter.py
```

Контрольные суммы текущих журналов внешнего реестра:

```text
29772e8b1d3b9526073397f09a6fe20a59e54634fa295ee0ad8bf17908566988  current-governance.log
a06522f63a3aca37f5a848778ddedc6936d6cb91e0a5b8bf5761c015a2d9f451  current-governance.xml
21bbd53f008921cb7f97991bdd6e3f9d5005c0a85e7ae535e3288ce370b7e50f  identity-probe.log
```
