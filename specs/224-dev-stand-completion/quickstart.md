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
