# F262/T010 — проверка принятия удаления сервером

Дата: 2026-10-22. Issue: [#6885](https://github.com/yshishenya/graf/issues/6885).
Ветка: `codex/262-validate-deletion-receipts`.
Основа: `eb929969fd9323b7b6489d1d25c245562f2d7e7c` после PR #7724.
Lane: active Spec Kit slice, high-risk deletion. Это новая проверка текущей
реализации T010; она не восстанавливает истёкшее доказательство CI PR #6911.

## Анализ перед реализацией

Прочитаны действующие spec, plan, tasks, research, data-model, lifecycle
contract, quickstart, 51 сценарий и обязательные общие документы.
Повторный `speckit-analyze` существующей F262: 22 FR, 7 SC и 23 уникальные
задачи; каждый FR/SC имеет владельца по карте в `analysis.md`. Не связанных
с требованиями задач и новых обязательных уточнений нет; CRITICAL 0 / HIGH 0.
Для T010 применимы FR-002/004–009/013/014/019/022 и US3; прежние отметки всей
F262 не принимаются за свежую установленную приёмку.

Независимое ревью требований до изменения кода: requirements 10/0,
security-ux 10/0, PASS. Отдельный отчёт и основания:
[review-t010-receipt-checklists-20261022.md](review-t010-receipt-checklists-20261022.md).
Внешний владелец T010 подтверждён live чтением #6885: OPEN, описание и
критерии соответствуют существующей задаче; дубль не создавался.
Включённых before/after implement/analyze/converge hooks нет.

## Дефект и минимальное исправление

Общая сохраняемая `RecordingDeletionReceipt` игнорировала сетевой `phase`.
Прямой успешный HTTP и вложенный lifecycle receipt с rejected/неизвестным
phase проходили проверку identity. Очередь сохраняла accepted; для origin
cancellation это разрешало очистку управляемого локального пакета.
Неправильный ответ production и потеря пользовательских данных не установлены.

В `DesktopUploadClient.swift` добавлена одна закрытая Decodable-обёртка,
которая требует строку `phase == "accepted"`, затем декодирует существующий
receipt. Её используют прямой delete и каждый вложенный lifecycle receipt,
включая выяснение результата после meeting_not_found. Прежние проверки scope,
identity, вида receipt и epoch сохранены. Неверный ответ оставляет исходную
операцию в resolving с возможностью повтора; отказ декодирования не означает
доказанный отказ сервера и не разрешает очистку.

Сохраняемая модель, queue v3, серверный API и исполнитель очереди не менялись.
У законных старых accepted/verified операций вложенного phase нет; отдельная
сетевая проверка сохраняет возможность их чтения после перезапуска. Сетевые
фикстуры прежних тестов приведены к действующим серверным схемам accepted;
domain/queue фикстуры без phase сохранены.

## Исполненные проверки

До исправления новый тест прошёл через настоящий DesktopUploadClient,
исполнитель очереди и временные синтетические файлы. Воспроизведены ложное
accepted и очистка origin при неверном phase. Журнал RED: 120 assertion/error
сообщений в одном матричном тесте, включая 12 ошибок чтения уже очищенного
файла; это не 120 отдельных тестов. Второй тест совместимости сразу PASS.
Узкая предшествующая decoder-проба не выдаётся за эту файловую проверку.

После исправления профильная команда:

```sh
swift test --package-path apps/macos --filter 'RecordingDeletion|DesktopUploadClientTests|DesktopUploadQueueTests|DesktopLocalPurgeTests|DesktopUploadCustodyProjectionTests|DesktopMeetingShellWebViewBoundaryTests'
```

Результат: **223 уникальных XCTest PASS, 0 FAIL, 0 SKIP**.
Два новых теста входят в 223 и отдельно не прибавляются.

- Матрица: 5 путей × 7 вариантов phase = 35 сочетаний. Прямой origin,
  прямой meeting, origin→meeting, origin lookup и meeting fallback после404.
  В каждом accepted принимается; rejected, future, null, число, boolean и
  отсутствие поля не разрешают accepted/verified. Все 30 неверных ответов
  сохраняют байты локального файла, identity и исходный ID операции при наличии.
  Для origin lookup новая ложная операция не появляется. Все5 accepted
  проходят; origin очищается, meeting не выдаёт принятие за физический purge.
- Queue v3 с accepted и verified receipt без вложенного phase прочитана после
  настоящего перезапуска сервиса; исходные receipt/target/operation сохранены.
- Прежние проверки охватывают durable-before-network, ошибку атомарного
  сохранения, retry/restart, чужую сессию, старый сервер, Retry-After,
  монотонность, scope/target, partial bulk, purge и восстановленные файлы.
  Прежний bulk на100 операций и файловая очистка100 пакетов также PASS.
- `check_spec_kit_governance.py`, `check-development-process.py`,
  `validate-changelog-fragments.py`, `validate-legacy-impact.py` и
  `git diff --check` — PASS.

Сверка `speckit-converge` ограничена T010: прямой и оба вложенных сетевых
входа закрыты одной проверкой, сохраняемое состояние не изменено; новых
обязательных задач этого исправления не выявлено. `tasks.md` не переписан.
Это не повторная сходимость всех пользовательских/релизных критериев F262.

## Контрольные суммы

Журналы сохранены во внешнем аудите issues-334-audit; содержат только
синтетические тесты и технические результаты.

| Файл | SHA-256 |
| --- | --- |
| `DesktopUploadClient.swift` | `aa208b0d7fdaf62b94976a8741ed8b228eaaec5f0e89c0aa65a70a018d50812f` |
| `RecordingDeletionLifecycleTests.swift` | `88616cfc359b2f2a8038a48f41e7fa4c2667c78a2ac2568a3471db08901d47dd` |
| `RecordingDeletionRecoveryAcceptanceTests.swift` | `58e935dc8a729e18903167cbf7525ef8e510077e637f62d8eaf636f4caf29b5f` |
| `RecordingDeletionBulkAcceptanceTests.swift` | `5753fc12481fd93d52f7f4dc78ddbf8c34aeba6731f0e3e9bff49e89aa3dba51` |
| `f262-t010-receipt-red-20261022.log` | `d5b04de64d3f3813dd9e234dfc5ef5a67bae87c1270e5102b48ce607da21ebf9` |
| `f262-t010-focused-20261022.log` | `5062741bbbd960d144bffcc62deb436a373daeb4ba598adaa7008966a4ffbcd2` |

## Границы приёмки

Независимое ревью кода по `code-reviewer` — PASS, замечаний P0–P3 нет;
проверены исходники и журналы, повторного исполнения тестов reviewer не заявлял.
Основания: [review-t010-receipt-code-20261022.md](review-t010-receipt-code-20261022.md).

Обязательные GitHub governance-fast/macos-pr/pr-metadata
точного SHA и checked base, защищённое слияние и live closeout фиксируются
отдельно в PR и итоговом комментарии #6885. До их подтверждения issue остаётся
открытой. Полный release-full нужен замороженному кандидату при выпуске;
публикация, deployment, установленный GRAF Dev и пользовательские данные этим
исправлением не изменялись. Оставшиеся задачи и общая F262 не закрываются.

Legacy Impact: `untouched`; прежний поддерживаемый формат очереди сохранён,
новой миграции, зависимости, запасного пути или совместимого alias нет.
