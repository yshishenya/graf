# T117 delete_purge: текущий requirements gate и production r2

Дата: 2026-11-04. Независимая проверка в
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Risk lane: high-risk-product, полный Spec Kit. Задача T117 / существующий #7445.
HEAD `c3c07df72d5b5599393cd97286b06d620a046320` сообщён Main;
Git в этой проверке не использовался. Привязка исходников проверена по байтам.

**Requirements/checklist gate: PASS для существующего T117 single-operation
delete_purge среза. Test-only r2 RED разрешён этим gate. Production r2:
SOURCE GO, CRITICAL=0 / HIGH=0; применение только после qualified RED и
остальных действующих gates Main.** Это не runtime PASS и не закрытие T117.

## Точный пересчёт и применимость прежнего PASS

Независимо пересчитан весь каталог `checklists/`: 198 Markdown-файлов,
477 отмеченных checkbox-пунктов, 0 неотмеченных. В число 198 входят прежние
отчёты; это не 198 отмеченных пунктов из 477 и не 198 новых нормативных
списков. Отдельно проверены все 31 файла из текущего reading inspection:
те же 477 checked / 0 unchecked, все 31 SHA-256 совпадают с текущими байтами.

Пять основных списков сохраняют 112/0: requirements 22/0, security 27/0,
ux 25/0, audio-capture 24/0, advanced-routing 14/0. Существующий независимый
`checklists/review-2026-10-02-storage-independent.md` документирует PASS
качества storage-требований, отдельно от кода и исполнения. Его текущий
SHA-256: `4d6a6c32a6513f7a4ab796490ab6cfb173d1faaa3cca0bca7142bd64e4d90d94`.

Этот отчёт обновляет применимость PASS к точному текущему срезу. Это не
заявление о новом полном аудите всех исторических отчётов. Основания:

- Действующие AGENTS и `spec-kit-flow.md` требуют независимый reviewer-owned
  PASS; широкое согласие пользователя не подменяет его. Условие исполнено
  настоящей независимой записью, отметки Main не выставляет.
- Requirements CHK004/005/012/013/016/019/020/022 и security CHK008–015,
  CHK017–018, CHK022/023/025 сохраняют разделение native/server authority,
  ошибки без ложного успеха, отсутствие секретов и фактический proof удаления.
- Contract `windows-protected-local-custody.md` §§7, 8, 8.1 уже задаёт
  существующий подтверждённый delete_purge, свежую queue authority и право
  на **все исторические строки** ledger. Требуются одинаковая durable
  authorization в BOTH records до unlink, actual absence до complete;
  неизвестный владелец и произвольный JSON полномочий не дают.
- Этот срез не меняет capture/routing/UI/release требования остальных
  списков, схему, серверный протокол или полномочия для неизвестного quarantine.
  Новая T121 относится к другому срезу и не изменяет проверяемый T117 scope.

Отметки всех checklist-файлов сохранены без изменения. Новых unsupported
пунктов в проверяемых требованиях не обнаружено. Полный PASS требований
не заменяет analyze, issue sync, qualified RED/GREEN и установленные gates.

## Reading receipts и неизменность

Прочитаны текущие AGENTS/guidance и относящиеся к этому срезу требования,
разделы constitution, product gates, spec/plan/tasks/quickstart и contract;
проверены существующая независимая storage-запись и текущие checklist bytes.
Повторное чтение ограничено применимыми разделами, а не объявлено новым
полным чтением всех крупных документов. Сведения Main о прежнем полном
чтении не выдаются за заново выполненное чтение этого reviewer.

`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/resumed-c3c-reading-inspection.json`
SHA-256 `d33c1b8a01088d03c8b0fe75fb702db2754d4a2e1800b0c85933c757f7e9ca41`:
до применения Main документов T121 независимо сверены все 10 document pins
и все 31 checklist pins. Запись
сохраняет 9/10 документов неизменными относительно прежнего reading receipt;
tasks имеет новый T121. Текущие T117/T118 остаются открытыми.

Для воспроизведения полной инвентаризации 198 файлов: отсортировать имена
`checklists/*.md`, для каждого записать `sha256 + "  " + basename + "\n"`;
SHA-256 объединённых UTF-8 строк:
`c384dad729f815944fe248e3e056f47b4e9dc6986be9fe70f0804fa0e2ae60f3`.

## Production r2: проверка кода

Замороженный кандидат:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t117-delete-purge-single-scope-production-r2/production.patch`
SHA-256 `955e03ccc738117a0b0906d2b5a3c2c0e3055993d218fe699dc5f38c63ab6587`.
Полностью прочитан patch и проверены затронутые функции/вызовы. Patch наложен
только в памяти; все base и candidate hashes совпали с provenance.

| Файл в apps/windows/RecApp | Текущая база SHA-256 | Candidate SHA-256 | Diff |
| --- | --- | --- | --- |
| Recording/NativeCapture.h | `2d56774a0ad9fb32a843c11769097171903508db754ec642846e984fa4b36357` | `5183f0936834266d3fae8fe84744fdd7f297e14c4cd6f7bd1952e8663050185e` | +3/-1 |
| Storage/ProtectedCustodyMetadata.h | `8cd86308cc52af37500d7659aa7a4c8b7dac4aea4376ccb5c058b18bcd448669` | `724b0277527bb6910191939933e0a34371f3f9be261a1c1ca4c2473e1c62d255` | +4/-3 |
| Storage/ProtectedCustodyMetadata.cpp | `0bd8440bb7eed1dfc78968af928087dabe4ed09af27dc6b61b63becb8a1af1d5` | `a6f546692be6b254e134f01e1db3038f3419ac9005bbe0bb40235a1ebf3367fa` | +116/-24 |

Конкретные основания SOURCE GO:

1. `requestProtectedLocalPurge` передаёт origin текущего native flight;
   account/epoch/continuation/cancellation и worker admission guards сохранены.
2. `purgeLocalPackage` до recycle обнаруживает root history через существующий
   fixed-role Birth/BOTH validator. Неполная cleanup вызывает существующий
   cleanup state machine; history/job handles освобождаются до recycle.
   BOTH-complete не получает новую authorization от следующей операции.
3. `cleanupMigrationOriginals` выбирает **одну** принятую queue operation с
   непустым receipt, точными actor/workspace/origin и покрытием всех исторических
   строк. Нет объединения операций. Unknown owner, несовпадающий scope и другая
   durable operation дают отказ. Сохранившиеся строки сверяются по устойчивым
   идентификаторам; историческая копия не считается вечным current ledger.
4. Повторная проверка читает BOTH bootstrap/current queue; выбранные generation,
   queue hash, operation target и receipt сохраняются перед существующими
   эффектами. Continuation не перепривязывает уже записанную authorization.
   Правила BOTH cleanup_pending → unlink → absence → BOTH complete сохранены.
5. Нет нового parser/schema/framework, fallback старого reader, startup cleanup
   или GC authority. Используются существующие helpers, leases, state machine
   и cancellation. Не-server continuation сохраняет прежний отказ при
   deletionBlocks/local_delete_pending.

Test-only r2 остаётся отдельным:
`t117-delete-purge-single-scope-red-r2/test-only.patch`
SHA-256 `45db20f2715729a1f33e036aefda963b1b508de13116e4f38b3e4886af64f4ab`,
test source `c02d301fb1aa12f1d8b8cebd70cd36a265005ec25e05e07d54fcd7115233ce5e`.
Прежний scoped SOURCE GO r2 сохранён. Первый RED должен подтвердить setup и
достижение целевого отказа; ошибка сборки/fixture/ранний отказ не будет этим RED.

## Дополнение: применённые Main требования T121 docs-r2

Во время проверки Main применил четыре документа T121. Это изменение Main,
не reviewer; предыдущий reading inspection выше сохраняется как снимок до
этого изменения. Текущая привязка —
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t121-shared-meeting-docs-r2-om85ekpt/provenance.json`,
полный `docs.patch` SHA-256
`50a3e969dd779d2d5b7ed4178c221df10573c2b86fbcdfc84c4b46ffc6b42ab2`.
Прочитан весь этот patch; все четыре текущих документа совпадают с after pins.

| Документ | Текущий SHA-256 после T121 |
| --- | --- |
| spec.md | `34341183dfd7b68fb8886ec23bca4bccc9e0200202e9b1825751f16a37b80855` |
| contracts/windows-native-web-bridge.md | `9a62717a0d52c79820705ddaab38b7784a98f2dd5928d2a04ff37739b3e97590` |
| plan.md | `214098fbc0ce9d64236a05700c7d391f812a04a0cfeef9e31eef0fd9876de8fc` |
| quickstart.md | `68432031888324f66ee7d75003585a6a86a9f271ffb3649a0a925a12ec4ab310` |

**T121 requirements/checklist applicability: PASS, C0/H0 в области новых
требований.** Отдельного T121 checklist-файла нет; обязательного отсутствующего
покрытия не найдено. Используются существующие reviewer-owned requirements,
security и ux, с текущей проверкой применимости в этом дополнении. Их отметки
не выдаются за кодовую приёмку. Проверены следующие новые области:

| Новые требования T121 | Действующие критерии и конкретное основание |
| --- | --- |
| Строгий activation intent | Requirements CHK007/009, security CHK001–003/007/022: bridge §11.1 задаёт 16 KiB, единственность ключей, однократное decoding, UUID/token/position/version bounds и отказ без изменения pending |
| UUID syntax отдельно от authority | Requirements CHK004/005/013, security CHK023/025: upper/lower/nil допустимы только синтаксически; настоящий account подтверждается существующим независимым session/server proof |
| Navigation/media/native capabilities | Requirements CHK004/013, security CHK002/005–011, ux CHK002/022: exact routes §11.2, public reader без bridge/nonce/local rows/effects; media не становится download/export/native authority |
| Cold/repeat/recovery | Requirements CHK005/016, security CHK003/011/022, ux CHK019/021: один memory-only latest-valid intent, однократное потребление, invalid сохраняет pending, новый valid выходит из recovery, revoked intent не перезапускается |
| Login/cookies/stale callbacks | Requirements CHK013/016/020, security CHK003/007/017/018/023: sealed server continuation не переносит token в login next; native own-profile cookie reconciliation отделено от public bridge, связано с текущим host/document/response, unknown не равен logout |
| Parity, версия и воспроизводимая приёмка | Requirements CHK002/003/006/009/019, ux CHK001/019/020, security CHK020: quickstart задаёт generated parser/route/state/media/response/cookie сценарии, A→B/stale проверки, preserved regressions, actual SDK и отдельные installed T097/T063 |

Новая public surface не добавлена в закрытый список bridge-команд: §11
явно определяет внешний protocol activation без новых native полномочий.
Независимость Record/Stop, custody и T117 не переопределяется. Неподтверждённых
требований, требующих снять отметку существующего checklist, не найдено;
477 checked / 0 unchecked сохранены. Дополнительный список ради нового номера
задачи не создавался: требуемые области уже покрыты действующими критериями.

Это только текущий requirements gate T121. Его analyze, issue sync,
реализация, SOURCE review и quickstart/runtime/installed acceptance здесь
не объявлены выполненными. Подтверждение Helm/Main о прежнем review не
выдаётся за самостоятельно выполненную проверку Mac/Windows runtime.
T117 SOURCE GO выше привязан к тем же неизменным исходникам production r2.

При финальной повторной сверке три production-файла ещё совпадают с base pins
таблицы, а Main test уже совпадает с reviewed r2 candidate
`c02d301fb1aa12f1d8b8cebd70cd36a265005ec25e05e07d54fcd7115233ce5e`.
Это изменение параллельного Main; reviewer его не применял. Оно не является
свидетельством выполнения RED. Все checklist bytes остаются прежними.

## Остаток и границы

Для этого замороженного production diff actionable Critical/High не найдено.
MSVC, runtime и qualified RED/GREEN здесь не выполнялись. Новые generated cases
ещё не приняты по исполнению. Partial-unlink restart, cleanup busy/cancel/OOM и
следующий unrelated purge не объявляются заново проверенными этими десятью
cases. Общая полнота T117/T118, legacy retirement, реальный unknown quarantine,
installed/hardware/release acceptance остаются самостоятельными условиями.

Создан только этот отчёт. Checklist-маркеры, код, spec/plan/tasks, Git/GitHub,
VM, сборки, тесты и пользовательские данные этим reviewer не менялись.
