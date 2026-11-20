# Round267 — SOURCE correction: доказательства отказа пути

Дата: 2026-10-06. Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`;
dirty preserved. Existing high-risk-product T116 / #7444; новый нормативный gate не вводится.

## Два отдельных решения

**SCOPED SOURCE correctness APPROVED** только четырём новым отрицательным
случаям пути и уточнению прежнего evidence claim. Новых production C/H
дефектов в этой correction области не обнаружено. Production CPP не изменён.

**CURRENT VALIDATION NO-GO / PENDING.** Release267e FAILED5/6 с deadline
assertion330 в DesktopUploadRecoveryTests. Debug267f имеет неоднозначный исход
dispatch/execution, terminal receipt отсутствует. SDK267g и readback267h,
по текущему сообщению main, НЕ запускались. Никакого final tested acceptance,
allReady, merge/release или full-T116 GO из SOURCE correctness не следует.
Это не изменение global goal status и не закрытие задачи.

## Исправление документальной оговорки

В старом SOURCE267 формулировка «decoded forbidden identity/path» слишком
широко описала выполненные отрицательные тесты SHA `1a81865e…f72dd0`:
decoded newline identity был проверен, valid Unicode escape в path был проверен,
но отдельных отрицательных decoded CR/LF/TAB path случаев там не было.
Path predicate имел SOURCE доказательство, не самостоятельный runtime PASS.

Старый отчёт **не переписан** и сохранён как исторический для прежнего набора:
`review-2026-10-06-queue-fields-source.md`, SHA
`9e7d4ae62e494d4d4a66bfbb58da68fb2ba5b905dff89ed74e4330c9f34fc281`.
Настоящий report исправляет именно границу этого evidence claim; не объявляет
ошибку test coverage новым production bug и не переносит267a/b PASS на267e/f.

## Лично проверенный код и новые случаи

Полностью прочитаны skills `code-reviewer` и `ponytail-review`; optional
preflight не выполнялся по явно ограниченному reviewer scope. Применяется
прежний REQUIREMENTS267 gate, без новых схем/правил/маркерных изменений.

Лично прочитан новый loop V2Tests:327–336, его реальная fixture:176–245,
replace helper и surrounding recovery. Документ writer содержит путь
`root / "package"`; replacement меняет конец именно package token и
оставляет JSON форму, а не подменяет локальную identity.

| Новая JSON последовательность в package_directory | Проверенный смысл |
| --- | --- |
| `\n` | JsonString декодирует LF; прежний path predicate отказывает. |
| `\r` | Декодирует CR; тот же predicate отказывает. |
| `\t` | Декодирует TAB; тот же predicate отказывает. |
| `\u0000` | Общий JsonString с allowNul=false отказывает ещё до построения path. |

Для каждого случая вызывается actual `queue.load()`, требуется false,
`assertRetained()` проверяет прежние row/owner/stamp/operation/ACK и quarantine
с недоступными pending/recycle effects; quarantine bytes сравниваются с
введённым invalid документом. Затем удаляется test backup, восстанавливается
прежний valid документ и actual load должен успешно пройти. Assertions
остаются включены в Release. Это не отдельное доказательство всех возможных
Unicode/control paths или полного OS read-race поведения.

CPP:55–64 использует прежний JsonString; CPP:263–268 проверяет decoded path
length и `find_first_of("\r\n\t")` до filesystem path assignment/candidate
publication. Лично прочитан этот guard и порядок. В172-map delta267a→267e
изменён только V2Tests; Production CPP и Recovery source совпадают.

`ponytail-review`: **Lean already. Ship.** Один loop на4 случаи переиспользует
существующую fixture, fault/assert/recovery поток; безопасных cuts нет. Здесь
это только complexity verdict, не разрешение ship при validation NO-GO.

## Лично прочитанные экспорты и неустановленная причина

Read-only stand `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI`.
JSON BOM снят только в памяти при разборе, SHA включает исходные байты.
Лично сверены172-map267e,172-map267f,179-map267g и receipt267e с canonical:
mismatches0. Наличие prepared f/g maps не доказывает их выполнение.

Release267e receipt terminal/failed,configure0/build0/test8. Raw содержит
ровно6 выбранных тестов,5PASS/1FAIL: V2 PASS17.16s, Recovery FAIL109.80s,
единственная assertion — steady_clock deadline, source line330.
Main сообщает CTest total131.89s; новый portable2 raw46/46 PASS, V2 PASS1.29s,
main total15.95s. Reviewer сам тесты/VM/EXE не запускал.

Лично сравнил EXE maps267a и267e: **изменился только V2 EXE**.
Recovery EXE одинаков: `f088c1ec10b8eb659573f5c4e40dabcc92f6ceec129a85c6ffb6f0eca5d29a57`.
Raw267a фиксировал Recovery PASS13.27s. Это исключает изменение tested binary
между этими receipts, но НЕ доказывает VM cause и НЕ отменяет failed267e.
Лично прочитан waitFor:326–333:3s deadline на каждое ожидание, не109.80s
лимит всего теста. Конкретный predicate/case, причина задержки/гонки/IO
по одному assertion log не установлены; timeout не ослаблялся.

Последние сообщения main: Debug267f prlctl session28121 exit255
`PrlJob_GetResult: Invalid argument`; не повторён, исход execution ambiguous.
Owned-process read-only status session22192 ещё без результата; guest f
liveness неизвестна. Лично при чтении stand f receipt и g SDK receipt
отсутствовали. Отсутствие export не доказывает, что guest тест не запущен.
Main сообщает SDKg/readbackh not started. CUA cgWindowNotFound не является
доказательством Mac locked; host VM running/memory60%free также сами по себе
не устанавливают причину Recovery deadline. Эти host/tool observations
атрибутированы main, не самостоятельному reviewer запуску.

Следующий шаг main — установить guest liveness и диагностировать native
deadline, сохраняя267e failure и условия теста. Повторное выполнение требует
обоснованного безопасного состояния; этот report не запускает retry,
не повышает timeout и не отключает тест. Старый ALL-native265k49/50 с AAC/B1
остаётся историческим NOT GREEN, не новым выполнением correction набора.

## Точные anchors

| Артефакт | SHA-256 |
| --- | --- |
| Production QueueService.cpp unchanged | `bdc76ef8cf30d83c53a75f83e844386285f2bad6dc6beb93bf2f77f276a66613` |
| V2Tests correction | `d49d2bd6a0d512d171522645c28d3950c23c49248c53d49c5ae2fa0b9a24c7e4` |
| source-queue-fields-round267e-release.json =267f-debug.json | `69633fde79a5495a58f71489740c4aa9c06a0bc2ae4b263ab28124e30e583891` |
| source-sdk-round267g.json prepared | `4f469fc9cf40127db98a0f7c7f1fa4905ec489b3c5f807ae7bf319d934d97661` |
| graf-f200-queue-fields-round267e-release.json FAILED | `2b2b78d8d5b782a27762be6fab6243e4f98d64c55a70979264a464090b212190` |
| Release267e raw | `a61f4e4477d8df23b089d1daf57a3737ffe0ebd7aa0209f6df8aedde8dfc071a` |
| Portable2 raw | `2cd3b0ee79e3b947a928c16702425387d65b7c2a62965d786580ac500fdd5ea4` |
| V2 EXE267e (receipt) | `8f1f3c533361f91e3859516535fc9af383df12d5806807f76bccc493c09c3bd7` |
| tasks.md unchanged | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |

## Сохранность и границы

До correction write132 checklist/report файла:131 прежних плюс SOURCE267.
Все132 hashes сохранены, added только этот report; после записи133.
Действующие10 normative checklist154/0 и отдельные historical checkbox
256/10 не меняются и не переклассифицируются. Tasks120/93/27, old SOURCE267
и REQUIREMENTS267 неизменны. Все6 before/after implement/analyze/checklist
git.commit hooks registered1/disabled, enabled0; reviewer dispatch0.

Reviewer пишет только этот новый correction report. Нет code/tests/spec/plan/
tasks/GitHub/VM/profile/runtime/commit edits, никаких checkbox closures.
**SOURCE четыре случая принят; обязательная native validation NO-GO/PENDING.**
FullT116/T117/T118/T119/T120, protected semantic/account/epoch/admission,
shared budget, installed/UX/hardware/release, H250 и legacy AAC/B1 остаются
отдельно открытыми, без global goal blocked/complete перехода.
