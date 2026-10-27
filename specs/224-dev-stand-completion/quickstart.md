# F224: ограниченная проверка и реальная приёмка

## Исходные условия 16.10.2026

Исходный SHA: f4b38141af2fad64bae219e8c012b0a54f237491. Свободно27 GiB;
крупные сборки не разрешены правилом запаса. Единственный GRAF Dev занят.
Текущий документ не разрешает live adoption, установку, сброс TCC или Docker cleanup.

Из подготовленной среды проекта, без установки зависимостей:

    python \
      -m pytest -q -o addopts= tests/governance/test_dev_harness.py \
      tests/governance/test_graf_local_adapter.py

Исходный результат:70 PASS,0 SKIP,0 FAIL. Это текущая базовая проверка, не
доказательство исправления F224. Существующий независимый отрицательный probe:

    python3 specs/259-audit-remediation/evidence/dev-identity-probe.py --checkout <checkout>

На исходном коде exit1, три обязательных отрицательных результата false.
Probe построен для старого resolver; в реализации обновить его проверку
без подмены canonical origin/Git failure предположением об успешности.

## US1: обязательная изолированная матрица до принятия

Все Git repos, HOME и state — временные; тесты не запускают реальное приложение
или Docker. Сеть не требуется. Новые тесты должны сначала воспроизвести отказ.

1. Настоящие временные repos: HTTPS/SSH/SCP формы одного origin, worktrees,
   независимые clones с разными basename и другой cwd дают один binding root;
   разные origins/одинаковый basename не получают чужое состояние.
2. Ошибки Git, multiple origin, вместоOf-подмена, небезопасные URL, symlink/
   широкий/production/чужой путь, неизвестный binding и live override:
   отказ до записи и всех подменённых внешних side effects.
3. Реальные два процесса: старый код удерживает прежний promote.lock,
   adopt-state ждёт; изменение active SHA за время ожидания отклоняется.
   Второй тест: два кандидата одного parent, повторная проверка после lock.
4. Две регистрации разных roots: не возникает двух привязок. Прерывание до/
   после атомарной публикации и ошибка записи: исходные manifests/runtime/
   journals не меняются, один определимый результат, lock inode сохраняется.
5. Frozen checkout с совпадающим resolver root проходит ограниченный probe;
   несовпадающий/изменённый/грязный/чужой checkout отказывает до stop/install.
6. Fixture prune не вызывает docker image rm и не затрагивает canonical root.
   Повторить прежние tests; rollback/schema/recovery guards остаются строгими.

После кода: targeted matrix, независимое review, ограниченный converge US1,
process/context/changelog/governance/diff checks. Затем отдельное разрешение
на commit/PR; GitHub governance-fast, macos-pr, pr-metadata на exact SHA/base.

## Широкая приёмка #6180 — остаётся открытой

- US2: один установленный путь, PID/исполняемый файл/bundle identity, все образы
  и фактический SHA app/backend/frontend/workers; отказ при недостающей службе.
- US3: сначала изолированно воспроизвести SIGKILL обычного promote на границах
  stop/install/pointer, разработать и независимо принять минимальное recovery.
- Штатный живой build→promote→status→smoke→rollback после освобождения стенда,
  достаточного места, разрешённого коммита и приёма PR. Использовать только
  /Applications/GRAF Dev.app и существующий harness.
- Same-signer Dev TCC: до/update/relaunch/после, microphone/system audio,
  signer/requirement/entitlements; без reset и второй копии приложения.
- Миграционное принятие имеет существующего владельца F249 T038/#6786;
  сохранить его критерии и доказательства, не создавать дублирующую миграцию.
- Один authoritative release-full на frozen candidate; выпуск/production
  отдельно, не часть разрешения на локальную реализацию.

Ни70 исходных тестов, ни успешная US1 не закрывают эти ворота и #6180.


## Текущая перепроверка 19.10.2026

Свободно254GiB; прежнее ограничение по месту больше не действует. Единственный
GRAF Dev по-прежнему не меняется этой изолированной проверкой; живое adopt-state,
установка, TCC и Docker cleanup не выполнялись. В подготовленной среде проекта
повторены восемь файлов из validation.md:186PASS/0FAIL/0SKIP,5.90с.
Независимый identity probe дал все четыре true. После коммита T008 требует
ограниченный fast на неизменном SHA и обязательные текущие GitHub проверки.
Широкие T009–T013 и живая приёмка остаются открытыми.

## T010: изолированная проверка обычного восстановления, 26.10.2026

Исследование воспроизвело3неполные SIGKILL-границы; это ожидаемый исходный
отказ, не завершение задачи. До кода нужны независимые checklist/analyze/sync.
После их PASS из подготовленной среды проекта:

    python -m pytest -q -o addopts= tests/governance/test_dev_promotion_transaction.py

Файл уже существует с тремя статическими проверками. На этапе реализации он
дополняется исполняемой матрицей прерываний; прежние три проверки не доказывают
новый договор восстановления.
Полная матрица и её ожидаемые результаты находятся в
[договоре](contracts/promotion-recovery.md#матрица-приёмки).
Регрессии: test_dev_harness.py, test_graf_local_adapter.py,
test_dev_state_ownership.py, test_dev_runtime_identity.py и существующие
schema/launch/retention suites; точные имена уточняются по затронутым callers.
Все внешние воздействия заменены временными файловыми маркерами, реальные
процессы используются только для lock/startup/SIGKILL. Прямой запуск Dev,
Docker/Swift/сеть и рабочие данные запрещены в этом наборе.
Успех isolated tests не закрывает T009/T011/T012/#6180.


## T009: изолированная матрица уточнённого договора, 27.10.2026

До кода — новый независимый PASS обеих checklists, analyze/sync #7640.
Только временные HOME/Git/state; внешние build/install/app/Docker действия запрещены.

1. RED на06ad4cb: app+sibling build с relative chain; несколько build внутри
   preserved-state. Затем GREEN нового кода, полный снимок и inode неизменны.
2. Явно учтённые невыбранные roots неизвестного владельца сохраняются без
   присвоения/управления; выбранный недоказанный root, неизвестный/лишний объект
   artifact-only, скрытая управляющая запись вместо build или неверная граница
   дают отказ. Неполный/лишний/дублированный/изменённый план и root set — отказ.
3. Неперечисленный build, absolute/cross-build/app/root link, escape-and-return,
   broken/cyclic link, symlink boundary, special file/небезопасные права — отказ.
   Успех app signature не разрешает запуск/импорт/копирование build.
4. Настоящий отдельный процесс держит selected/sibling lock. Изменение плана,
   root set, metadata, app/build bytes или link во время ожидания — отказ до
   binding. Проверить каждый исходный tree/lock inode; соседние файлы не создаются.
5. Старый договор без плана, binding v1, повтор, schema/recovery и T010 yield fd
   сохраняются. Повторить ownership/harness/adapter/runtime/promotion/schema/launch
   suites из validation; это регрессия, не приёмка приложения.
6. План снят без selected lock: точный отказ, файл не создан, полные снимки
   всех roots неизменны, binding и внешние действия отсутствуют. Все existing
   locks сохраняют успешный сценарий и inode. Без классификации selected lock
   по-прежнему создаётся штатно. Удаление до открытия, подмена inode во время
   ожидания и небезопасный selected lock не разрешают пересоздания.

Команда из существующей подготовленной среды:
`PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -o addopts= tests/governance/test_dev_state_ownership.py`.
После независимого review/converge и обычных PR gates выполняется отдельное
реальное принятие/проверка всех компонентов и остановленной обязательной службы.
Архивы не исполняются/не импортируются/не перемещаются; временные тестовые
материалы удаляются, результаты/хеши сохраняются. T009 открыта до этого конца.
