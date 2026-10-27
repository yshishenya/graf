# F224/T009: проверка сохранения невыбранных архивов, 27.10.2026

Ветка `codex/224-preserved-archives`, основа
`5dffd0537e66e7f4e88bd0d4fd5103393fc7c486`. Lane: high-risk-product,
существующая T009/#7640. Этот отчёт принимает только изолированную часть;
реальная T009 и T011/T012/T013/#6180 остаются открытыми.

## Что изменилось

Существующий adopt-state получил необязательный полный план классификации.
Выбранный root требует доказанной принадлежности; невыбранные неизвестные
состояния и явно перечисленные build сохраняются на месте без присвоения,
управления, исполнения, импорта, копирования или применения для восстановления.
Существующие блокировки и полный повтор снимков защищают принятие одной
привязки. Нет нового manager, реестра, команды, зависимости или схемы binding.

Подпись/source facts проверяются у перечисленных app artifact-only. Архивные
app selected/preserved-state — неизвестные байты полного снимка с безопасными
путями; существование sibling-каталога не принимает его bundle/SHA/подпись.
Активные manifest/runtime guards выбранного состояния сохранены отдельно.

## Порядок и независимое ревью

Уточнение FR-003/007, план, два reviewer-owned checklist, analyze и синхронизация
#7640 относятся к новому договору. Предварительные кодовая дельта и127PASS
появились до окончательного gate; они сохранены как предварительные и не
выдаются за соблюдение порядка или приёмку реализации. После промежуточного
замечания код остановлен до окончательного PASS требований34/0 и16/0,
затем повторены analyze/sync, RED и окончательная матрица.

Отдельный reviewer проверил реализацию и нашёл R1: общая фраза договора
обещала проверку каждого архивного app, хотя selected/preserved-state не
содержат соответствующих фактов. Автор уточнил только договор/модель и
операторские документы. Код и тесты после475PASS не менялись. Итоговые
отметки и вывод находятся в [независимом отчёте](review-classification-code-20261027.md);
проверен окончательный APPROVE, открытых замечаний0, infrastructure34/0 и requirements16/0.

## RED: воспроизведённый исходный отказ

Сохранённый исходник `06ad4cbfa95f34b0403b80bdbfb6ad420bf44ad6`
в отдельном TemporaryDirectory, текущие положительные fixtures artifact-only
и preserved-state с внутренними относительными build links:

- Новый полный формат: 2 ожидаемых FAIL, `invalid classified root record`.
  Это только несовместимость старой строгой схемы.
- Дополнительный адресный опыт: из всех entries убрано только поле
  build_archives, файлы/ссылки не менялись. 2 ожидаемых FAIL на
  `_classification_tree_digest`: `classified symlink leaves its archived app`.
  Это воспроизводит прежний запрет build links со старым допустимым форматом.

Временные исходники удалены штатным TemporaryDirectory. Оба журнала сохранены
в операторском каталоге graf-repository-audit за27.10, без копирования
реальных архивов. Последующий GREEN использует новый полный формат.

## GREEN и регрессии

Подготовленная Python-среда, без установки зависимостей:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -o addopts= \
  tests/governance/test_dev_harness.py \
  tests/governance/test_dev_launch_validation.py \
  tests/governance/test_dev_live_smoke.py \
  tests/governance/test_dev_promotion_transaction.py \
  tests/governance/test_dev_rollback.py \
  tests/governance/test_dev_runtime.py \
  tests/governance/test_dev_runtime_contract.py \
  tests/governance/test_dev_runtime_identity.py \
  tests/governance/test_dev_runtime_isolation.py \
  tests/governance/test_dev_safety_guards.py \
  tests/governance/test_dev_schema_transition.py \
  tests/governance/test_dev_state_ownership.py \
  tests/governance/test_dev_state_retention.py \
  tests/governance/test_graf_local_adapter.py
```

Итог: **475 уникальных PASS, 0 FAIL, 0 ERROR, 0 SKIP, 78.68s**,14файлов.
XML независимо перечитан; identity digest475 случаев:
`f50bbaaab57b92e97313d2c8f225f876ac5740927411dcd45a94fbf55f65bb66`.
Ownership содержит150случаев; промежуточные148PASS не суммируются с475.

Матрица включает полный строгий план, безопасные app/framework/build links,
18негативных build случаев, реальное ожидание locks и изменение bytes/link/
metadata/root set/плана/inode, перепроверку непосредственно перед binding,
конкурирующие регистрации, ошибки записи и прерывание до/после публикации.
Проверяются неизменные исходные деревья, отсутствие соседних lock/записей и
сохранение T010 fd. Внешние app/install/build/Docker действия подменены;
настоящие дочерние процессы используются только для файловой конкуренции.

## Сходимость и оставшиеся ворота

Повторный анализ:18FR+6SC,13задач,100% покрытия, CRITICAL/HIGH/MEDIUM/LOW0.
Ограниченный `$speckit-converge` текущей части T009: новых неохваченных
обязательств не найдено, tasks.md не изменён командой. Это **не сходимость всей
F224**: фактические app/службы и отрицательная остановка — T009; живое
восстановление — T011; Dev TCC — T012; полный итог/release-full — T013;
schema-changing приёмка принадлежит F249 T038/#6786. Дубли не создавались.

Process/context/changelog/governance/diff и frozen bootstrap: PASS.
GitHub governance-fast/macos-pr/pr-metadata на точном PR SHA/основе и общий
validate-pr-checks остаются обязательными до слияния. Локальный fast/full
не запускался повторно: это не дополнительный PR gate. Выпуск/production
не выполнялись. Свободно192GiB перед следующим возможным build.

Согласование: соседняя F273 сообщила об окончании прежнего окна без слияний;
нового frozen-кандидата/использования Dev у неё нет. Это не доказывает
неактивность всех остальных jobs: перед реальным adopt-state отдельно
проверяются/исключаются писатели и составляется текущий полный план.

## SHA-256

```text
scripts/dev-harness.py 98300cb86cb2986e3f342dc22c05b8332ed1e486da6f5b6036990d4f4817a4e9
tests/governance/test_dev_state_ownership.py 2b7435d0d6bc4d122857ca29dfb95db4caf36f7834f4ae76f90c421f98ac2047
contracts/state-ownership.md 97f117233d8bf3fb95d568c2a56c0df32905f281a187449988991e414d3ad78d
data-model.md cdd783aa71dcca720a9889577e6066341f21505b6a1a4fba5297db1de62aee5d
f224-classification-regressions.xml 5ce15c1a3c0fa8b27653a625bd0103f5397cfb5cb3d53ab85d3feebf7bb7a5f1
f224-classification-regressions.log 16a2a5b270a6463e857d309618f475596b5045345958aef67ad34b67fae6ef76
f224-build-contract-red.log ef049b1dce244daf5f2925ffae1943c54bf6289a412ae9965effd2e043b58476
f224-build-contract-old-format-red.log ea044fb431c9493bf54251d54c2247317bcb3bb8edd0939bcfff3b94c0f02ae1
```

Коммит/SHA и hosted CI фиксируются в PR отдельно после сохранения этого отчёта;
ни один старый результат не выдаётся за новый exact-SHA gate.


Ограниченная сходимость выполнена после реализации и475PASS по текущим
spec/plan/tasks/constitution и всем classifier callers: 18FR,6SC и11сценариев
трёх историй сопоставлены с13задачами. В данной части T009 новых отсутствующих,
противоречащих или непрошенных механизмов не найдено. Непринятая живая часть
FR-008–014/018 и SC-004–006 уже имеет открытых владельцев T009/T011/T012/T013
и F249 T038; новые дубли не добавлены. Before/after-converge hooks отсутствуют.
Prerequisite использует поддержанные --require-tasks --include-tasks вместо
неподдерживаемого --require-spec. tasks.md до/после команды совпал:
`dd1c2a0757f041abda811915a724869d81cfbfaa1284744b1dddd318d284675a`.
Окончательный analyze после R1:0 замечаний; issue sync/canon ensure/validate
успешны, проверены286issues, новых issues не создано.
