# F227/T033: предварительное независимое ревью 21.10.2026

Reviewer: `f228_checklists_review`, навык `code-reviewer`.
Ветка: `codex/227-ci-merge-queue-release-train`.
Фактический HEAD: `0434a52aab0d86058540567cbe657538a14240eb`.
Область: уточнение plan по замечаниям PR7678
4314292416 (потребление прежних train) и4314292430 (`refs/replace`).
Lane: Active Spec Kit slice, инфраструктура и происхождение выпуска.

## Решение

**PASS плана и качества требований; блокирующих замечаний нет.**
Это предварительное ревью перед изменением кода, не APPROVE будущей реализации.
Прежние runtime результаты и отчёты19.10 остаются историческими: новый обход
потребления сохранённого train и подмены истории они не доказывали.

Все пункты requirements и infra перечитаны и сопоставлены с уточнением:
**requirements16 checked /0 unchecked; infra13 checked /0 unchecked;
всего29 checked /0 unchecked.** Отметки не менялись.

## Источники и предел чтения

AGENTS/index, active pointer и prerequisites подтверждают F227. Spec/tasks/
quickstart, конституция7.1.0, spec-kit-flow и release-and-validation побайтно
совпадают с уже прочитанными в этой работе версиями. Новый раздел plan21.10
прочитан вместе с полным plan. Перечитаны оба контрольных списка, FR011/SC007,
реальные validate_train/require_git_commit_relationship, все их callers,
train_current, candidate freeze, train-attest и decide, serial caller
scripts/release.sh и границы существующей regression.

Pointer source_sha `6288dabe6678960537c6a8e6a7f67fa74ff5ed2f` отличается от
фактического HEAD выше; reviewer не менял pointer и не использует его значение
как SHA проверенного текущего кода. Исходники дополнительно связаны SHA256 ниже.
Непроверенных внешних зависимостей для решения о достаточности плана нет;
GitHub review content рассматривается по формулировке задачи, live API не читался.

## Обоснование общего места проверки

Сейчас require_git_commit_relationship вызывается только train-freeze,
а validate_train проверяет структуру через существующий validator.
Поэтому сохранённый до исправления train может попасть в следующие пути
без повторной проверки raw Git ancestry:

| Потребитель | Текущее место validate_train | Требуемое поведение после исправления |
|---|---|---|
| train-validate, без и с --current | До необязательного train_current | Отказать несвязанной базе в обоих вариантах. |
| candidate freeze --train | До train_current и создания candidate/identity | Отказать без выходных записей. |
| train-attest | До acquisition lock и чтения candidate/evidence | Отказать без attestation/output/identity; исходные файлы не менять. |
| train-attest выходной go record | Перед записью go train | Повторная общая проверка остаётся обязательной. |
| decide --train | До train_current и Full CI/решения | Получить ту же ancestry защиту; decision не создавать. |
| train-freeze | Явный guard и последующий validate_train | Сохранить защиту создания train; при переносе не оставить обхода. |

Вызов существующей функции из validate_train после успешной проверки структуры
покрывает все эти пути без нового формата или нового набора правил.
Сначала schema, потом обращение к Git: malformed значения не должны попадать
в ancestry helper до их проверки. Generic scripts/validate-release-train.py
остаётся структурным валидатором; фактические release consumers проходят
через project-local validate_train в release-candidate.sh.

`git --no-replace-objects` необходимо применить и к cat-file, и к merge-base
в общей функции, чтобы обе проверки читали реальные commit objects и их
исходных родителей. Обычный exit1 (нет ancestry), ошибка Git, отсутствие
истории и недоступный commit должны завершаться отказом без успешного train.
Не требуется добавлять обратное source→synthetic: serial и будущая native
очередь сохраняют прежнее различие происхождения и выпускаемого source.

Immutable manifest/sidecars не мигрируются и не перезаписываются.
Старый несовместимый train отвергается при потреблении, а не исправляется
молча. Exact source/HEAD, clean tree, PR/Full proofs, candidate binding,
write-once identities и согласование release остаются отдельными воротами.

## Требования и задачи достаточны

FR011 описывает обязательную связь base с actual source; SC007 — настоящий
Git rehearsal и отказ без train/identity. Уточнение распространяет существующий
инвариант на доверие сохранённому train; не вводит новый пользовательский
результат, режим или формат. T032 сохраняет требование независимого анализа;
T033 владеет release-candidate и существующими regression tests. Текущего
ownership достаточно для исправления замечаний в том же PR.

Requirements1–16 продолжают подтверждать ясность, измеримость и полноту
требований. Infra1–6/8–10/12–13 не меняются. Infra7 и CHK011 теперь должны
проверяться также на путях потребления сохранённого train и при refs/replace;
новый plan явно задаёт это и реальный RED→GREEN. Качество требований PASS
не утверждает, что эти новые проверки уже прошли. Исходные T001–T031 и
native T029/T031 не закрываются; отмеченная T033 требует повторной фактической
валидации после correction. Новых продуктовых вопросов нет.

## Что обязаны доказать тесты перед итоговым APPROVE

1. Старый train с несвязанной базой должен иметь согласованную immutable identity,
   актуальные source/changelog и остальные корректные prerequisites. До правки
   он принимается через train-validate, candidate freeze и train-attest;
   после правки эти же сценарии отказывают именно по ancestry. Иначе отказ
   malformed/schema/identity/Full proof не доказывает устранение обхода.
2. В обычном Git merge-base refs/replace graft должен искусственно дать ancestry,
   а в `--no-replace-objects` — показать отсутствие реальной связи. Прежний
   runtime принимает этот сценарий, исправленный отказывает. Проверять freeze
   и сохранённый train через общий validator.
3. Проверить сохранность bytes/digest исходных manifest/identity и отсутствие
   новых candidate/go/attestation/decision identities при отказе. Decide тоже
   потребитель, даже если для него достаточно отдельного короткого
   отрицательного сценария с уже существующим candidate.
4. Положительные serial train с тремя PR, пустыми queue collections,
   candidate/attest/decide и прежние отрицательные тесты должны остаться
   успешными. Git fixtures временные; PR и Full proofs в них подставлены
   и не становятся настоящей GitHub/release приёмкой.

Это конкретизация содержащегося в plan требования «отказ всех потребителей»,
а не новый объём продукта. Код до исходных RED reviewer не менял, тесты
не запускал; итоговое APPROVE зависит от их результатов и чтения diff.

## SHA256 входов

| Файл | SHA256 |
|---|---|
| plan.md с уточнением21.10 | a50fb574d9b4a06e9c7a32b2dcfd45f5e488191f6008edad5bc0dbc88ff20c1c |
| spec.md | 196f4b6f02f0feca8446ba766c9e6c77c4ed200ba2e3b4930ba315afb82df071 |
| tasks.md | 3ffaf2a67c64a78962e3c3f260b97757211e7a10f97e7c0f884617a38a79eb90 |
| quickstart.md | d7f112e935b70dd9aba2c88aa31510c2794c2b37ec05b5f1d21ff0580ed9fbc8 |
| release-candidate.sh до исправления | dcfa09b9e643cbf64481926ffa8586b61e130ec9844893bd6121feeee625beeb |
| test_release_train.py до расширения | 186669f39ecc5e824e788250a2d49e7aa4b8e29468ea0079f801deb47a7cf84d |

Reviewer создал только этот отчёт; чужие правки, код/spec/plan/tasks,
checkboxes, Git/GitHub/сервер/GRAF Dev не менял. `git diff --check` и
оформление отчёта проверены. Слияния удерживаются на окно F280;
это ревью не даёт разрешение выпуска или развёртывания.
