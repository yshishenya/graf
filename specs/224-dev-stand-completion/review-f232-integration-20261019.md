# Независимое ревью совмещения F224 и F232 — 19.10.2026

**Область:** F224 US1/T008, PR #7676; принятая F232, PR #7677.
**Основа:** `74712f33c0cec6da2b7b7547a3be372387802d86`.
**Повторяемый F224 commit:** `7471527a1d6911895c09ce5ff5ad0d6e29160edb`.
**Состояние проверки:** rebase приостановлен; итоговый код ещё не имеет нового
commit SHA. Проверка относится к байтам файлов, указанным ниже.

## Вывод

**APPROVE совмещения F224 US1 с принятой F232. Нерешённых замечаний: 0.**
Итоговый предоставленный XML независимо пересчитан: **229 различных случаев,
229 PASS, 0 failure, 0 error, 0 skipped**. Это одобрение объединённых байтов
после исправлений исполнителя, не разрешение merge/live adoption/выпуска и
не принятие всей F224.

Разрешение конфликта `state_lock` сохраняет обе стороны. F224 проверяет
принадлежность и исходные пути, берёт прежний lock безопасным способом,
повторяет ownership после ожидания и только затем создаёт marker. F232
проверяет `app-launch-validation-recovery.json` внутри той же блокировки
непосредственно перед допуском вызывающей операции.

Первоначальный совместный прогон дал **227 разных случаев, 210 PASS / 17 FAIL**:
прежний искусственный стенд тестов F232 подменял только `global_state_dir`,
не создавая требуемую теперь привязку. Исполнитель исправил подготовку
временных данных; весь итоговый набор прошёл повторно. Reviewer код не менял.

## Метод и сохранность сторон

Прочитаны объединённый код, обе Git conflict stages, все восемь вызывающих
операций `state_lock`, F232 lifecycle/launch-validation методы и весь
`test_dev_launch_validation.py`. Использована процедура `code-reviewer` для
локальных изменений. Рекомендации о checkout/предварительном запуске проверок
не исполнялись: назначение разрешает чтение и только этот отчёт.

Синтаксическое дерево Python разобрано без исполнения harness. Проверены:

- `_state_file_lock` совпадает с F224 стороной конфликта; сохраняет тип,
  владельца, режим доступа, nlink и inode после flock.
- `_terminate_dev_app`, `_launch_dev_app`, `_app_launch_identity`,
  `_assert_launch_tooling`, `_validate_launch_bundle` и
  `operation_validate_app_launch` совпадают с принятой F232 основой.
- Все глобальные присваивания принятой основы сохранены.
- Блок `operation_status`, показывающий незавершённую launch validation,
  совпадает с F232 основой.
- Parser и dispatch содержат и `adopt-state`, и `validate-app-launch`.
- В объединённом исходнике нет conflict markers; `git diff --check`
  не сообщил ошибок. Состояние index `UU` до завершения rebase ожидаемо и
  само по себе не доказывает неразрешённый текстовый конфликт.

## Вызывающие операции `state_lock`

| Операция | Сохранённая граница |
|---|---|
| build | Lock до manifest/build/retention; recovery marker отказывает до adapter |
| promote | Кандидат читается до lock; active/parent проверяются после ожидания; marker до lifecycle |
| recover-schema | Marker до изменения журнала и запуска восстановления |
| rehydrate | Manifest читается до lock; marker до Docker image load |
| prune | Marker до удаления артефактов и общих tags |
| validate-app-launch | Live ownership до lock; marker до нового временного журнала и lifecycle |
| rollback | Lock и marker до восстановления app/runtime; запрет shared metadata-only сохранён |
| reset-data | Запрет реального shared metadata-only reset сохранён; допустимый dry-run также проходит marker guard |

`status` остаётся чтением снимка и показывает recovery receipt; `smoke` не
меняет lifecycle. Прямые адаптеры не являются новым самостоятельным CLI;
F224 добавляет их ownership boundary, F232 запуск остаётся под controller lock.

## Найденное, исправления исполнителя и повторная проверка

1. **Исправлено:** прежний fixture F232 не удовлетворял новой
   принадлежности. Для настоящей проверки F232 нужно изолировать HOME,
   создать временный допустимый root и полную synthetic binding до
   `build_manifest`/`_publish_active`, сохранив реальные ownership проверки.
   Простая подмена нового guard либо принятие любого `HarnessError` не
   подтверждают сценарий запуска/восстановления. В итоговом fixture HOME
   направлен во временный каталог; state создан под временным machine base;
   synthetic binding записан до вызовов build/publication. `global_state_dir`,
   `_state_ownership` и `_state_file_lock` не подменяются. Существующие подмены
   нативных lifecycle/signing действий остаются искусственными и не выдаются
   за приёмку macOS. Все41 тест F232 проходят с настоящей файловой принадлежностью.
2. Промежуточная адаптация создавала binding после `build_manifest`, что
   дало **197 PASS / 30 setup ERROR**. Это диагностический отказ порядка
   подготовки данных, не новая продуктовая регрессия. Порядок исправлен:
   directory → binding → manifest → active pointer.
3. В случае F232 `reset-data` реальный shared reset теперь правильно
   запрещается раньше lock по F224. Чтобы проверить именно marker guard,
   допустим `--dry-run`; запрет настоящего shared reset отдельно покрывает
   ownership suite. В итоговой F232 matrix добавлен только `--dry-run` этому
   случаю; другие пути и обязательный regex recovery guard сохранены.
4. `adopt-state` использует `_state_file_lock` напрямую. Его исходный список
   recovery markers содержит schema/rollback, но не новый F232 receipt.
   Это не найденный обход lifecycle: после принятия все обычные mutating
   операции всё равно блокируются marker в `state_lock`. Однако контракт
   принятия требует отсутствие recovery-required; исполнителю передано
   предложение явно проверить новый receipt при adoption. **Исправлено**:
   новый файл включён и в исходную path/type проверку, и в запрет принятия
   alongside `rollback-required.json`. Новый параметризованный ownership test
   проверяет оба markers: полный набор bytes существующих файлов и inode lock
   сохраняются, binding не появляется. Проверка использует временный Git/стенд;
   приложение/Docker не вызываются. Оба случая PASS.

## Доказательства и ограничения

XML предоставленных запусков пересчитан независимо от итоговой строки pytest.
Reviewer сам тесты не запускал. Initial XML: 227 testcase, 227 различных
пар classname/name, 210 PASS, 17 failure, 0 error, 0 skipped. Все17 failures
в F232; восемь прежних файлов F224 дают186 PASS. Остальные24 случая F232
из первоначального запуска не заменяют повтор после исправления fixture:
часть отказных тестов принимала любой HarnessError и могла остановиться раньше
предназначенной проверки.

Реальные приложение, Docker, серверы, живое состояние, Git/GitHub, rebase,
коммиты, слияния и выпуск reviewer не менял. Единственная разрешённая запись —
этот отчёт. T009–T013, реальное adoption, Dev smoke/rollback/TCC и общий #6180
остаются открытыми. Успех изолированной матрицы их не закрывает.

## Итоговая совместная матрица

| Файл | PASS |
|---|---:|
| test_dev_state_ownership.py | 48 |
| test_dev_harness.py | 23 |
| test_graf_local_adapter.py | 47 |
| test_dev_schema_transition.py | 51 |
| test_dev_promotion_transaction.py | 3 |
| test_dev_runtime_identity.py | 5 |
| test_dev_live_smoke.py | 2 |
| test_dev_state_retention.py | 9 |
| test_dev_launch_validation.py | 41 |
| Всего | 229 |

Итоговый файл `post-f232-joint-accepted.xml`: 229 testcase, 229 уникальных
пар classname/name, failures/errors/skipped — 0/0/0. Длительность suite35.334s;
вывод pytest — `229 passed in 35.50s`. Предыдущие/пересекающиеся прогоны
не прибавляются к этому числу. Перед завершением ревью повторная проверка
синтаксических деревьев подтвердила неизменность шести F232 lifecycle/validation
методов относительно принятой основы. Новые правки касаются только принятия
recovery marker и подготовки тестовых данных; recovery guard `state_lock`
остаётся внутри сохранённой F224 блокировки.

## Контрольные суммы исходного диагностического снимка

```text
07d84be75fb8f956ab3f091872f5e0e0caf12b992a81eca27e6844e6fe707490  scripts/dev-harness.py
e76ba1082ba83384a37469cf09815fa2a94206149db99b1e7dcf7c20034f1c3d  tests/governance/test_dev_launch_validation.py (до адаптации fixture)
e0c5ed3a60334e6c637eb1b564a48c363b55bfe8d6e9dc5a70cda7bd69b3e75a  post-f232-joint.xml
999e8e4befbd3166a853bec6545899a9ab8f57cf789ccec05a3be21db82bf68e  post-f232-joint.log
```

Внешние журналы расположены в
`/Users/yshishenya/Documents/Codex/2026-10-19/f224-current-preflight/`.

## Контрольные суммы итогового проверенного снимка

```text
7a4ab28fa2972e1d7466e0bf4a3ec218320bdd66fbf070243fc9b29cb99d02f9  scripts/dev-harness.py
24b8ca9412d7a7b85f20fe88b34b2bc49056034bf5800fbada60229c6609f51b  tests/governance/test_dev_launch_validation.py
aa47d731b045344d7a50a14a5b794ddf772e92ec633dfd49191dd5abbd809ea3  tests/governance/test_dev_state_ownership.py
6a378a61a975ed49257cc9ba2cce932fbf63b879de5a246d171e9911fb71bbec  post-f232-joint-accepted.xml
fa03e75a3fca78493267da7285adff860e280f24ecff9a7e38d4b01d9ae3d154  post-f232-joint-accepted.log
```

Суммы относятся к незакоммиченному результату rebase. Будущий source SHA
и required CI должны проверяться отдельно. Этот отчёт не хеширует сам себя;
его итоговую сумму reviewer передаёт основному агенту после записи.

## Итоговое подтверждение после Ruff-правки — 19.10.2026

**APPROVE сохраняется; новых замечаний: 0.** После предыдущего снимка
изменён только ownership test: удалён неиспользуемый импорт `os` верхнего
модуля, выражения с `;` разнесены по строкам; нужный `import os` оставлен
непосредственно во встроенных дочерних программах. Внешний модуль больше
не обращается к `os`; дочерние программы с обращениями к `os` независимо
разобраны через AST и имеют собственный импорт. Проверки отказа, ожидаемые
коды процессов, синхронизация, сохранность файлов и inode не ослаблены.

Последняя матрица `post-f232-final-verified.xml` независимо пересчитана:
**229 testcase, 229 уникальных пар classname/name, 229 PASS,
0 failure / 0 error / 0 skipped**. Распределение девяти файлов совпадает
с таблицей выше, включая48 ownership и41 F232 launch validation.
Длительность XML suite36.171s, строка pytest — `229 passed in 36.34s`.
Это текущий итог; предыдущие диагностические/успешные результаты сохранены
как история и к нему не суммируются. Неудачная промежуточная механическая
попытка не является итоговым доказательством и не маскируется этим повтором.

Перечитана добавленная запись `Совмещение с принятой F232` в validation.md:
она верно описывает общий guard, adoption marker, действительные временные
bindings, dry-run reset и сохранение открытых T009–T013/#6180. Указанные там
35.50s относятся к предшествующему успешному прогону до Ruff; актуальное
подтверждение после механической правки —36.34s в настоящем дополнении.
Runtime source и F232 test сохранили прежние SHA256. Reviewer не менял
код, validation.md, Git/index/rebase или какие-либо живые ресурсы.

```text
7a4ab28fa2972e1d7466e0bf4a3ec218320bdd66fbf070243fc9b29cb99d02f9  scripts/dev-harness.py
24b8ca9412d7a7b85f20fe88b34b2bc49056034bf5800fbada60229c6609f51b  tests/governance/test_dev_launch_validation.py
81a1f0b9dc06f608a3f620f318a3cfdca2d20e71dd4c45c9158816f2c269bbb2  tests/governance/test_dev_state_ownership.py
8ba239eeb51aa536ec9bd96c9cee3f9ffecbe5f62014196ca14728fe756b8a91  specs/224-dev-stand-completion/validation.md
a5a189af313f4d6e5df9e39909ff335939744065329500f3a2e5176c58968dc1  post-f232-final-verified.xml
5d96fead62765e6b9dc9cbf4b5ba0d91edd4be6ee773d813605b4e8b15779f12  post-f232-final-verified.log
```
