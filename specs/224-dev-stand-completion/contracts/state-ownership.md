# F224: контракт принадлежности US1

Это проект существующего harness, не описание уже выпущенного поведения.
Новая команда входит в infra/scripts/dev-harness.sh; второй workflow не вводится.

## Канонизация

- Один origin. Raw URL и effective URL после Git insteadOf должны определять
  тот же canonical github.com/owner/repo. Ошибка Git — безопасный общий отказ.
- Поддерживаемые формы: https://github.com/owner/repo[.git],
  ssh://git@github.com/owner/repo[.git], git@github.com:owner/repo[.git].
  Один конечный slash допускается; GitHub host/owner/repo сравниваются без регистра.
- Owner/repo — ровно две непустые компоненты, допустимые для GitHub; точки
  пути, пустые компоненты, escapes, query/fragment, control characters,
  credentials, HTTP/локальные пути, неизвестные host/protocol и нестандартные
  порты отвергаются. Сообщения не содержат исходного URL.

## Одноразовое принятие состояния

Проектируемая форма:

    infra/scripts/dev-harness.sh adopt-state --state-root <существующий-root> \
      --expected-repository github.com/owner/repo \
      --expected-active-sha <40-hex> --confirm-repository-ownership

Для нового пустого стенда вместо --expected-active-sha используется --expect-empty.
Эта форма допускается только при отсутствии установленного Dev, живого процесса
и общего graf-dev runtime; неизвестный результат проверки означает отказ.

Принимать существующий стенд можно только после согласованного освобождения
стенда и исключения самостоятельных jobs старого контроллера. Confirmation
подтверждает историческую принадлежность, а не разрешает пропуск проверок.
В этой работе реальный adopt-state пока не выполняется.

Порядок:

1. Проверить формат аргументов, canonical origin/ожидаемый repository, исходные
   компоненты путей, владельца и допустимость доступа. Root находится под
   стандартным машинным GRAF Dev, имеет форму <storage-name>/harness.
   Символьные ссылки, production/broad paths и raw override для этой операции
   запрещены. Устаревший live state вне стандартного дерева требует отдельного
   плана восстановления; не переносится автоматически.
2. Взять registration lock в общем машинном каталоге. Прочитать binding:
   идентичная запись идемпотентна, отличающаяся/невалидная блокирует операцию.
3. Проверить стандартные непустые roots: неизвестное второе состояние не
   присваивать и не удалять; отказ до отдельной классификации оператором.
   Не выполнять поиск личных данных по диску. За старые нестандартные overrides
   отвечает явное операторское подтверждение, а не обещание исчерпывающего scan.
4. Взять прежний promote.lock без замены файла; проверить inode после ожидания.
   Перечитать active pointer/manifest/runtime. Проверить ожидаемый SHA,
   согласованность записей и отсутствие recovery-required/незавершённой схемы.
5. Атомарно и с fsync опубликовать один repository-state.json штатным _write_json.
   При ошибке не переносить данные и не создавать запасное состояние.
6. Перечитать binding и вернуть техническую квитанцию repository/root/active SHA.
   Повтор с тем же repository/root не требует прежнего active SHA, если стенд
   законно продвинулся после первоначального принятия; это не перепривязка.

Registration lock держит только adopt-state; operational lock остаётся прежним
promote.lock. Порядок регистрации всегда registration → operational, обратного
порядка нет. Обычные команды binding не меняют. Сами lock-файлы не заменяются
атомарной записью; symlink/чужой тип/владелец/смена inode дают отказ.

## Обычные операции

| Операция | Граница |
|---|---|
| build/promote/rollback/rehydrate/recover-schema/prune/reset-data | Canonical binding до первой мутации; прежний operational lock; binding и active/parent повторно проверяются после ожидания |
| status | Только чтение принадлежности и снимка, без создания каталогов/lock; не утверждает завершение параллельного перехода |
| smoke --live | Canonical binding; фактическая проверка и неизменность active identity при завершении, иначе отказ |
| schema-start-guard | Canonical root до startup; прежний frozen guard не подменяется |
| explicit fixture root | Только изолированные файловые данные; никакого app/Docker/shared-tag mutation |

GRAF_DEV_STATE_DIR остаётся явным средством искусственных проверок. Для живых
операций отличающийся root запрещён до state_lock/side effects. Изолированный
root не может совпадать с binding root или быть его родителем/потомком.
Невалидный существующий binding не обходится режимом fixture.
Изменение живого canonical pointer через metadata-only promote/reset/rollback
не допускается: на живом состоянии нужны штатные реальные операции.

Prune из изолированного root вообще не удаляет общие Docker tags. Старое
сравнение manifest IDs не является достаточной авторизацией такого удаления.
Прямые adapter paths, _live_state_owns_tags и build_manifest покрываются тем же
разграничением, а не только CLI --live.

## Закреплённые адаптеры

До первого stop/install/Docker mutation контроллер проверяет clean exact SHA,
canonical origin, tracked runtime bytes и runtime-definition digest прежнего
checkout. Затем отдельный ограниченный subprocess исполняет уже проверенные
bytes его harness и только запрашивает resolver при cwd=checkout. Результат
должен быть принятой физической state_root. Неизвестный результат/timeout/
несовпадение — отказ до остановки. Старый startup позже исполняет собственный
schema guard штатно; новый probe не предвосхищает writer phase.

Новый controller не гарантирует защиту от произвольного frozen старого бинарника,
запущенного вне правил. Старые scripts не запускаются самостоятельно; используются
только как проверенные adapters нового controller. Сохранение старого lock
сериализует уже удерживающий его прежний процесс.

## Проверки отказа

Для каждой ошибки принадлежности/пути/ожидания и несовместимого frozen root
проверка должна доказать отсутствие записей состояния и вызовов build/install/
stop/Docker до отказа. Adoption допускает только собственные регистрационные
технические файлы после допустимого preflight; исходные state files неизменны.
Нельзя превращать неизвестное состояние в пустое или выбирать последний файл.
