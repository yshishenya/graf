# Раунд 460 — требования к дополнительным отметкам времени в тестах

Дата: 2026-10-19. Роль: независимый проверяющий требований; не исполнитель.

## Решение

**GO на подготовку узкого диагностического изменения.** Допускаются только
скалярные отметки `steady_clock` / `elapsed_ms` в одном тестовом файле
`apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp`:

1. В `protectedLocalPurge`: начало/конец каждого mode, до/после `finalize()`
   созданного тестом writer, после prepare async `.get()`, после recovery и
   после cold shutdown.
2. В существующей строке `V5_CASE stage=frames_3000`: дополнительное
   `elapsed_ms`, отсчитанное от уже существующего
   `deadline - std::chrono::seconds(180)`.

Это **диагностика, не исправление**. Конкретный diff ещё не представлен и
окончательного допуска исходного кода этим решением не получает. Прежний допуск
Dirac459 для failure-only helper не расширяется и не переоценивается.
Противоречий требованиям для описанного изменения не найдено; это не общий
PASS реализации, выполнения тестов, T116 или готовности Windows к выпуску.

## Зафиксированная рабочая копия

- Корень: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
- Ветка: `codex/200-windows-followup`.
- HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
- SHA-256 текущего тестового файла до новых отметок:
  `6a3f3a2b8be22b0e98d3b859f29bbee86eaa4ae421e61c15ca792758d0a3cdc3`.
- Рабочее дерево содержит прежние изменения; они сохранены, не включены
  автоматически в область данного допуска.

Перед созданием этого отчёта повторное сравнение 434 файлов с собственным
снимком начала проверки не обнаружило изменений. Снимок охватывает 198 файлов
checklists, 216 файлов `apps/windows`, активные нормативные документы,
указатель фичи, настройки расширений, корневой AGENTS и руководство проекта.
Это сравнение с началом данного review, не с чистым Git HEAD.

## Проверка требований и руководств

Применены `code-reviewer` и локальный `speckit-analyze`. Анализ исходных
артефактов оставлен read-only; сохранение только этого отдельного отчёта
разрешено пользователем. Активная фича установлена по `.specify/feature.json`
и read-only prerequisite script, а не по имени физической папки.

Прочитаны конституция, обязательные маршрутизирующие руководства и относящиеся
к диагностике разделы активных spec/plan/tasks/quickstart и контракта Windows.
У `before_analyze` / `after_analyze` нет включённых обработчиков;
коммиты и другие изменяющие состояние обработчики не запускались.
Исходная категория риска `high-risk-product` сохранена. Узкая диагностическая
вставка не отменяет полный путь приёмки исходного высокорискового среза.

| Основание | Ограничение для предлагаемого diff |
| --- | --- |
| FR-021; windows-desktop-contract.md §9, строки 692–722 | Только фиксированная метка этапа, номер mode/case и длительность; без содержимого, путей и секретов. |
| FR-012/013/022; конституция: защита хранения и правдивое удаление | Не менять writer, adoption, recovery, удаление, защищённое хранение и критерии успешности. |
| План и T116: интеграционная проверка защищённого пути | Использовать существующий тест, без новых производственных вызовов и без нового поведения продукта. |
| План P3; требования к доказательствам | Новый диагностический исходник и исполняемый файл учитывать отдельно от прежнего неуспешного запуска. |
| Конституция и правила приёмки | Не увеличивать ожидания и не ослаблять проверки ради зелёного результата. |

Хеши ниже совпадают с нормативной базой проверки 459/458:

| Файл | SHA-256 |
| --- | --- |
| `.specify/memory/constitution.md` | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| `spec.md` | `0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11` |
| `plan.md` | `8ae83e6a5c3ef7bc7376f2e25f70c2d686ad1589bf30e37b73b9c5323cca6c65` |
| `tasks.md` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| `quickstart.md` | `12f9029fd1e47ef4080bd2764e28385a386fabe59d45f3125f90c13c9c190fe7` |
| `issue-map.md` | `bbef57c4a1a51d6bc846406ca436c8c30173ba43282b7f97e53912c8aa517403` |

Имена без каталога относятся к `specs/200-windows-desktop-app/`.
Новые требования, политика, задача и синхронизация GitHub для этих наблюдений
не нужны: область уже покрыта T116 и FR-021. Ни одна задача не закрыта.

## Полнота проверки checklist

Инвентаризированы все 198 Markdown-файлов каталога `checklists`.
Перечитаны все 458 пунктов в 31 файле с checkbox: 458 отмечены, 0 открыты.
Из них 12 тематических файлов содержат 192 пункта, 19 исторических — 266.
Остальные 167 файлов не содержат checkbox; это в основном исторические
отчёты. Не заявляется построчное повторное чтение всех исторических отчётов
или повторная проверка всех описанных в них запусков. Их прежние отметки не
считаются доказательством текущего выполнения Windows.

| Тематический checklist | Отмечено / всего |
| --- | --- |
| advanced-routing.md | 14 / 14 |
| audio-capture.md | 24 / 24 |
| calendar-launcher.md | 5 / 5 |
| calendar-operation.md | 8 / 8 |
| calendar-wire.md | 5 / 5 |
| cold-prefix-recovery.md | 28 / 28 |
| packed-writer.md | 12 / 12 |
| privacy-pause.md | 12 / 12 |
| requirements.md | 22 / 22 |
| security.md | 27 / 27 |
| start-owner-recovery.md | 10 / 10 |
| ux.md | 25 / 25 |

Исторические пункты: packed-tree-source 38; calendar-join-gate 12;
calendar-resolver-gate 12; calendar-url-gate 12; manifest-cap-source 9;
packed-cadence-gate/source 12/18; packed-live-writer-gate/source 14/9;
packed-package-gate 12; packed-reader-gate/source 20/9;
packed-resize-gate/source 14/9; packed-rewrite-gate/source 16/9;
packed-tail-gate/source 14/9; packed-writer-source 18.
Это соответствующие файлы `review-2026-10-03-*` / `review-2026-10-04-*`.

Контрольный SHA-256 перечня всех 198 файлов:
`98fc8173b2cd698541da11c5ff28d0f873f75a437b205e8e30357b3222cb15a2`.
Сериализация: сортированные относительные пути, для каждого
`path + NUL + SHA256(file) + LF`, затем SHA-256 всей последовательности.
Это собственный снимок данного review, не отдельное доказательство равенства
каждого исторического отчёта версии 459.

Состояние `tasks.md`: 120 задач, 93 отмечены, 27 открыты. Изучены 22 FR и
10 SC; диагностический допуск не является выполнением этих критериев.
Метки задач и checklist не изменялись.

## Условия окончательной проверки diff

- Один тестовый файл; около 20 строк — ориентир минимальности, не разрешение
  добавить иную логику. Никаких правок production, fixture cleanup или CMake.
- Никаких новых ожиданий, дедлайнов, циклов, `pollUploads`, дополнительных
  API/покадровых обработчиков, профилирования CPU и чтения полезных данных.
- Не менять существующие `frames`, assert, порядок операций, `.get()`,
  продолжительность жизни объектов, future и границы владения.
- Сохранить общий CTest timeout 240 s и существующий deadline 180 s.
  Новые числа времени не должны управлять ветвлением или успешностью теста.
- Начало отсчёта `PendingStart` — именно создание deadline на текущей строке
  6220, не начало записи или жизни fixture. Меняется только существующий
  вывод строки 6227; цикл строк 6221–6226 остаётся прежним.
- Отметки LocalPurge размещаются только на указанных границах этапов.
  Захват времени внутри async должен иметь корректное время жизни; формат
  целочисленного вывода должен соответствовать типу аргумента.
- Вывод фиксированного объёма остаётся тестовым stderr. Он может влиять на
  планирование и сам является выводом: нельзя обещать нулевой IO или строго
  ограниченное время выполнения `fprintf`. Не добавлять flush/файлы/блокировки
  или вызовы продукта ради диагностики.

Текущие ориентиры LocalPurge: функция 1431, цикл 1440; writer finalize 1453;
prepare `.get()` 1503; recovery 1600; shutdown 1614 и cold shutdown 1626;
существующая отметка конца mode 1628–1629. Деструктор fixture вызывает
`remove_all(parent)` в `Tests/GeneratedRecordingFixtures.h:34` уже после
отметки конца. Поэтому такая отметка не доказывает завершение очистки fixture;
не требуется перестраивать область жизни ради её охвата в этом diff.
Номера строк относятся к указанному исходному SHA-256, до новых отметок.

## Неуспешные запуски и следующий этап

По сообщению main, CTest19 завершён: 17 PASS / 2 FAIL; PendingStart —
181.46 s, assert 6258; LocalPurge — 240.08 s, timeout. Это сведения main,
а не собственная проверка гостевой системы. Причина превышения времени и
связь с высокой нагрузкой CPU этим отчётом не доказаны. Отметки призваны
локализовать затраты времени, не объясняют их заранее.

Main отдельно сообщил о diag14-finalize с прежним helper и manifest
`1ce85bcf7577942b054a2e50dcc1a1e60d05f0068c75a8c9866aabed6a50f002`,
без новых отметок. Этот запуск и его manifest здесь не проверялись и не
получают нового допуска от reviewer. Подготовку host diff можно вести
отдельно, не меняя замороженный исходник/бинарник активного запуска.
Следующий запуск с отметками — после завершения текущего запуска и
отдельной окончательной проверки точного diff. Параллельные native-тесты
данным решением не разрешаются.

Reviewer не обращался к VM, не запускал сборки или тесты, не менял внешние
системы и не удалял файлы. Единственная запись — этот новый отчёт.
Аппаратные, установочные, интерфейсные и релизные условия приёмки сохраняются.

## Дополнение: окончательная проверка фактического diff

**Финальный source GO на диагностические отметки. Блокирующих замечаний нет.**
Решение относится только к переходу тестового файла между следующими SHA-256:

- Замороженный исходник diag14-finalize:
  `6a3f3a2b8be22b0e98d3b859f29bbee86eaa4ae421e61c15ca792758d0a3cdc3`.
- Проверенный host-кандидат:
  `fc85c594db6e82a7660b264a0dd58ef6cce4a74343733d73a66d229b5f4e655e`.

Оба хеша проверены самостоятельно по байтам. Замороженный файл прочитан из
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/diag14-finalize/apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp`.
Это не проверка установленного или запущенного guest-бинарника.

### Состав и обратная проверка

Diff содержит только 13 новых строк LocalPurge: шесть строк определения
`started`/`mark` и семь мест вызова. Дополнительно существующая однострочная
запись `V5_CASE stage=frames_3000` заменена трёхстрочной с `elapsed_ms`.
Итого 16 добавленных / 1 удалённая строка, чистое увеличение на 15 строк.

Независимое обратное преобразование выполнено только в памяти: удалены ровно
эти 13 строк и восстановлена прежняя однострочная запись V5_CASE. Получено
побайтное равенство замороженному файлу и SHA-256
`6a3f3a2b8be22b0e98d3b859f29bbee86eaa4ae421e61c15ca792758d0a3cdc3`.
Преобразование ничего не записывало на диск.

Повторное сравнение собственного снимка 434 файлов с requirements gate
показало изменение только указанного тестового файла. Остальные 433, включая
производственный код Windows, CMake, все 198 checklist и нормативную базу,
совпали. Проверка `git diff --no-index --check` не вывела замечаний по пробелам;
возврат 1 при сравнении этих разных файлов не трактуется как ошибка теста.

### Время жизни, синхронизация и формат

| Проверка | Фактические границы в кандидате | Вывод |
| --- | --- | --- |
| Захват переменных | `started` и `mark` объявлены в 1433–1438 перед циклом; worker создаётся в 1452, завершается через прежний `.get()` в 1512. | `mark`, `started`, `userRemoval` и текущий `mode` живы до окончания worker. `mode` меняется только после `.get()` и конца итерации; отметки ничего из этого не записывают. |
| Последовательность вызовов | `begin` 1447 до запуска async; `before_finalize`/`after_finalize` 1460/1462 внутри него; `prepared` 1513 после `.get()`. | Между новыми вызовами этого helper нет одновременного чтения изменяемого `mode`; callback нигде не сохраняется и не передаётся продукту. |
| Блокировки | Существующие короткие области `cutMutex` остаются в 1542, 1547, 1551; новые отметки не входят в эти области и не помещены в polling/callback продукта. | Нет нового удержания product/test mutex во время вывода и нет изменения порядка снятия блокировок. `fprintf` имеет собственную внутреннюю синхронизацию stdio; это не обещание отсутствия влияния на планирование. |
| Finalize | 1460 перед прежним assert, 1462 после завершения полного выражения `finalize().normalPackage()`. | Writer/owner остаются в прежних областях жизни; операции finalize и проверки результата не переставлены. Отметка после finalize не утверждает уничтожение writer или освобождение всех package leases. |
| Recovery | 1613 после прежних recovery, ожидания пустой проекции и assert отсутствия пакета/нового поколения. | Не добавлен вызов recovery, poll или иной переход состояния; отметка достижима только после прежних проверок mode 8. |
| Cold shutdown | 1639 после выхода из области `restarted`, его shutdown/drain и деструктора. | Отметка не продлевает и не сокращает время жизни `restarted`. |
| Cleanup | `end` 1642 до конца области fixture, следующий `begin` 1447 — на следующей итерации после её деструктора. | Следующий `begin` подтверждает последовательное прохождение предыдущей очистки; это не новый memory fence. Для последнего mode такой следующей отметки нет, и `end` сам по себе очистку не доказывает. |
| Типы printf | `%u`: `userRemoval ? 1U : 0U`, `unsigned mode`, `static_cast<unsigned>(test)`; `%s`: фиксированные строковые литералы этапов; `%lld`: явный `static_cast<long long>`. | Типы variadic-аргументов соответствуют форматам; динамический контент, пути и полезные данные не выводятся. |
| Смысл elapsed | LocalPurge — суммарно от входа в функцию; V5_CASE 6240–6242 — от прежнего `deadline - seconds(180)` в 6233. | Разности отметок локализуют интервалы. V5_CASE не измеряет всю жизнь записи/fixture и не превращает host steady_clock в источник временных меток аудио. |

`mark` содержит только чтение `steady_clock`, перевод длительности в
миллисекунды и вывод фиксированных полей. Семь мест вызова не являются
покадровыми: `before_finalize`/`after_finalize` пропускаются в mode 1,
`recovered` выполняется только в mode 8. В полном успешном проходе получается
53 новые строки PURGE_PHASE на один вызов `protectedLocalPurge`, независимо
от числа кадров и числа повторов polling. Нового flush, API-hook, CPU-профиля,
файлового журнала, доступа к аудиоданным или выделенного диагностического
потока нет.

Обратное побайтное равенство подтверждает сохранность всех прежних assert,
чисел кадров, ожиданий, deadline, `pollUploads`, операций продукта и их
исходного порядка. Изменился только наблюдающий код; его обычная стоимость
времени и влияние stderr на расписание не объявляются нулевыми. Общий timeout
CTest остаётся 240 s, внутренний deadline — 180 s. Измерения не влияют на
успешность или выбор ветки теста.

### Граница допуска

Это окончательный допуск **исходного diff дополнительных отметок**, а не
успешного выполнения, исправления двух RED, аппаратной приёмки или выпуска.
Сборка/запуск кандидата должны получить собственную привязку к точным байтам;
активный diag14-finalize на прежнем исходнике остаётся отдельным запуском.
Новый native-запуск — только после terminal текущего, без параллельного
захвата/нагрузки. Reviewer сборки, тесты и guest-проверки не выполнял.

Checklist totals не изменены: 198 файлов учтены, 31 с checkbox,
458 отмечено / 0 открыто; tasks — 93 отмечены / 27 открыты. Единственная
запись reviewer в этом дополнении — собственный round460 report.

## Дополнение: отдельная квалификация двух тестов в Release

**GO на предложенное узкое расширение внешнего harness и отдельную Release
qualification; не на исправление или замену Debug RED.** Прочитан целиком
55-строчный `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/validate.ps1`.
Его текущий SHA-256:
`d2e43789bc819a794c7e635c5e3d20efd45f4c1f75c7f136a671e1d8195b5b6c`.
Скрипт reviewer не менял. Это допуск описанного объёма; будущий фактический diff
harness и результаты запуска здесь ещё не проверены.

Проверяемый исходник теста остаётся
`fc85c594db6e82a7660b264a0dd58ef6cce4a74343733d73a66d229b5f4e655e`;
SHA-256 `apps/windows/CMakeLists.txt`:
`140943a00a74f3d0d27261e0a769192d03b795f35054c230dac666c1182ff950`.
Нормативный допуск выше сохраняется, новый полный анализ нормативной базы
не выполнялся. Нового разрешения на product patch это дополнение не даёт.

### Почему выбранные Release CLI не являются пустым PASS

Все строки ниже относятся к указанным байтам локальных файлов, не к уже
скомпилированному guest PE.

| Область | Источник | Заключение |
| --- | --- | --- |
| Наличие executable | CMake 115–117, 130–132 | Native integration target добавляется при WIN32, не только для Debug. |
| Регистрация CLI | CMake 196–197, 213–214 | Оба add_test не зависят от конфигурации; RUN_SERIAL TRUE и TIMEOUT 240 сохраняются. Для этих тестов нет DISABLED, SKIP_RETURN_CODE или SKIP_REGULAR_EXPRESSION. |
| Действующие assert | Тест 1–3 и 16 | NDEBUG снимается до всех include, включая NativeCapture, generated fixtures и cassert. В файле нет последующего определения NDEBUG и нет Release-only удаления assert. Нельзя просто считать, что обычный Release выключает эти тестовые выражения. |
| PendingStart dispatch | Тест 6910–6915 | Без условия _DEBUG вызываются оба vertical-case normal/signedOut с deferredStart, затем protectedPendingCancellation и проверка возврата памяти. |
| PendingStart содержание | Тест 6130–6762, 3715–3838 | Generated capture, 3000 кадров, EOS/finalizer, withheld adoption, cold verification/restart и cancellation cases не ограждены _DEBUG. Существующий deadline 180 s и failure-only helper также остаются. |
| LocalPurge dispatch | Тест 6848–6851 | Без условия _DEBUG вызывается protectedLocalPurge, затем проверяется возврат памяти. |
| LocalPurge содержание | Тест 1431–1644 | Все mode 0–8, generated writer/защищённый queue, native recycling, IoCut, read pause, held directory handle mode 8, recovery, cold shutdown и assert остаются. Семь мест elapsed-отметок не зависят от конфигурации. |
| Реальные native wrappers | Тест 128–365, 439–441 | Выбранные IoCut и native file/MF seams не скрыты за _DEBUG; Release не заменяет их фиктивными успешными результатами. |

Вывод: на уровне исходного кода оба CLI полноценно достижимы и сохраняют
проверки. Это не утверждение, что Release уже собирается или проходит;
предупреждения /WX, настройки SDK и фактический guest toolchain не проверялись.

### Что действительно отличается в Debug и Release

- Тест 42–121: только MSVC Debug имеет executable-local global new/delete,
  terminal allocation cut с stack/symbol qualification и вызов
  pauseDeletionRetirement при освобождении. Реализация retirement cut —
  144–150. Эти инструменты отсутствуют в обычном Release. Для выбранных двух
  CLI terminalAllocation не вооружается и deletionRetirementThread не
  устанавливается; при этом глобальная обёртка аллокатора в Debug всё равно
  существует и влияет на условия выполнения.
- Тест 934–961: отдельная protectedDeletionIntent проверяет удержанный
  retirement cut только в Debug; Release использует другую ветку ожидания.
  Этот отдельный CLI не входит в предлагаемую пару.
- Тест 3108–3117, 3431–3457, 3519–3544: symbol setup и terminal allocation
  fault case в protectedUploadFromCold — Debug-only. В normal/signedOut
  PendingStart ownedUpload=false, поэтому вызов в 6394 недостижим для пары;
  но Release-пара не доказывает этот отдельный Debug fault gate.
- Тест 6771–6774: настройка вывода Debug CRT assertions в stderr отсутствует
  в Release. Это настройка отчётности, не удаление обычных assert, для которых
  в начале файла уже снят NDEBUG.
- Отдельно компилируемые production OBJECT units и CRT собираются в своей
  конфигурации. Локальный undef NDEBUG относится к тестовому translation unit,
  а не ко всем библиотечным объектам. Их оптимизация, allocator/CRT и
  планирование могут отличаться. Сканирование RecApp и GrafAEC3 не обнаружило
  явных веток NDEBUG/_DEBUG, заменяющих выбранные product paths.

Возможный выигрыш времени в Release — полезное измерение различий
конфигураций, но не доказательство причины высокой CPU-нагрузки, отсутствия
гонки или исправления finalizer/LocalPurge. Debug RED остаётся RED со своими
исходником, PE, временем и assert/timeout.

### Допущенный объём будущего изменения harness

Только после terminal diag15, без изменения активного скрипта или исходников
его запуска:

1. Добавить `[ValidateSet('Debug','Release')][string]$Configuration='Debug'`.
2. Записать выбранное значение в `receipt.configuration`.
3. В строке 30 заменить только значение `cmake --config Debug` на параметр.
4. В строке 34 выбирать exe в подкаталоге выбранной конфигурации.
5. В строке 38 передать ту же конфигурацию в `ctest -C`.

Debug остаётся значением по умолчанию. Никаких новых CMake/product defines,
параметров оптимизации, принудительного _DEBUG в Release, снятия assert,
дедлайнов, per-frame hooks, повторных попыток до зелёного или изменения
test pattern по результату. Нельзя смешивать Release build с Debug exe/hash
или Debug CTest. Требуется существующий multi-config build с доступной Release;
этот факт должен быть подтверждён main по его конфигурации, здесь не проверялся.

Все прежние защитные проверки скрипта сохраняются: отсутствие Owned processes
до source upgrade (10–15), prior/source manifests и ровно 216 файлов (6–8,
15–26), -j 1 и /nr:false (30), source postflight 216 (44), неизменность PE
(45), terminal receipt и нулевое число Owned processes на выходе (48–54).
Нужен новый отдельный каталог результатов для Release; общие
Testing/Temporary/LastTest.log и guest source/build нельзя использовать
конкурентно с diag15 или иным native run. Основное ограничение — сериализация,
не только RUN_SERIAL внутри одного процесса CTest.

### Минимальные точные доказательства для Release qualification

- Зафиксировать configuration=Release, точный source manifest, хеш harness,
  фактический Release exe/размер/хеш до и после, build/test exit codes и
  pre/postflight 216. Значения конфигурации должны согласоваться между build,
  exe path и CTest; одного нового поля receipt недостаточно.
- Подтвердить действующие assert по точному source hash и фактическим
  параметрам компиляции этого TU. В source уже есть необходимый ранний undef;
  product/test patch для этого не нужен. В generated project/команде CL
  проверить отсутствие подмены assert и неучтённых forced includes/PCH,
  обходящих начало исходника. Обычное /DNDEBUG в Release само по себе не
  нарушение: оно снимается строками 1–3.
- Если фактическую цепочку include/параметры нельзя установить, после terminal
  получить отдельный preprocess-output с теми же Release compiler flags,
  без изменения исходника: выражения append/finalize в LocalPurge и проверки
  3000 кадров/deadline в PendingStart должны сохраниться как действующие
  проверки с обработчиком assertion failure, не как пустой `(void)0`.
  Это условная проверка артефакта, не просьба добавить новый assert-canary,
  намеренно обрушить тест или изменить compile flags.
- Для утверждения о прохождении именно пары проверить в JUnit/LastTest.log
  ровно NativeProtectedPendingStart и NativeProtectedLocalPurge, оба запущены
  из Release target, 0 skipped/disabled, 0 failure/error. Текущий скрипт
  проверяет только executed_tests >= 1 (43, 46), поэтому его exit 0 в одиночку
  не доказывает выполнение двух тестов. Это не требует расширять данный
  минимальный diff harness: проверку точных имён/числа main может оформить
  отдельным read-only разбором сохранённых результатов.
- В полном PASS-логе PendingStart нужны normal/signedOut stage=done,
  cancellation modes 0–5 и submit_refused; в LocalPurge — mode 0–8 и
  результат CTest после последней очистки/проверки памяти. Отдельная строка
  PURGE_PHASE end не заменяет завершение процесса; stage=done не отменяет
  последующие проверки CLI.

Нельзя подменять Release-парой Debug RED/Debug-only fault gates, всю T116,
прочие CLI suite, реальную запись на устройствах, 60-минутный clock/AEC gate,
физический Windows x64, installed MSIX/UI, auth/upload E2E, clean install/
update/rollback, security/adoption/deletion acceptance и выпуск. Статусы задач
и checklist не меняются. Qualification не даёт разрешения на исправления.

Сведения main о diag14 PASS и текущем diag15 приняты как контекст, не как
самостоятельно проверенный runtime evidence. Reviewer не проверял guest,
не запускал сборки/тесты и не менял validate.ps1; запись только в этот отчёт.

## Дополнение: окончательный source review Configuration в validate.ps1

**Финальный source GO** для отдельной Release-пары
`NativeProtectedPendingStart|NativeProtectedLocalPurge`.
Блокирующих замечаний по фактическому diff нет. Это не запуск и не runtime
PASS, не разрешение на product patch и не замена Debug evidence.

Проверены непосредственно два внешних файла:

- `diag15-native-delays/validate-input.ps1`, SHA-256
  `d2e43789bc819a794c7e635c5e3d20efd45f4c1f75c7f136a671e1d8195b5b6c`;
- `validate.ps1`, SHA-256
  `92fd57707b43bbd0c85f1a0864526e49f8a3c45afaa8018c319a563f54993463`.

Оба пути относительно `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/`.
В обоих файлах 55 строк. Изменены ровно строки 1, 5, 30, 34 и 38:

| Строка | Изменение | Проверка |
| --- | --- | --- |
| 1 | ValidateSet Debug/Release и Configuration=Debug | Значение по умолчанию сохранено; другие параметры не менялись. |
| 5 | receipt.configuration=$Configuration | В отчёт попадает выбранная конфигурация. |
| 30 | cmake --config $Configuration | Target, -j 1, /nr:false и обработка exit code сохранены. |
| 34 | Подкаталог exe из $Configuration | Хеш/размер и проверка PE относятся к той же выбранной конфигурации. |
| 38 | ctest -C $Configuration | Регулярное выражение выбора тестов, output-on-failure, JUnit и обработка exit code сохранены. |

Независимое построение ожидаемого кандидата из старых байтов с ровно пятью
согласованными заменами дало побайтное совпадение с новым файлом.
Обратная замена только этих пяти строк в памяти побайтно восстановила базу
с SHA-256 `d2e43789bc819a794c7e635c5e3d20efd45f4c1f75c7f136a671e1d8195b5b6c`.
Файлы при этой проверке не записывались. No-index whitespace check замечаний
не вывел; наличие diff объясняет возврат 1 команды сравнения.

Таким образом, остальные строки, включая Owned-process guards, prior/source
216, upgrade scope, source postflight, неизменность PE, обработку ошибок и
terminal receipt, сохранены без изменений. Дедлайны CTest/исходника не
менялись этим diff. Предыдущие условия Release qualification остаются:
отдельный каталог результатов, тот же source manifest, действующие assert,
фактический Release build/exe/CTest и проверка ровно двух названных тестов
без skips/errors. Скрипт по-прежнему проверяет минимум один выполненный тест;
доказательство пары берётся из JUnit/LastTest.log, не только exit 0 harness.

Перед этим review точечная повторная сверка подтвердила совпадение всех шести
нормативных хешей, общего отпечатка 198 checklist-файлов и тестового SHA fc85.
Поэтому прежние scoped analyze/checklist и вывод об отсутствии необходимости
новой задачи/issue sync сохраняются. Это не свежая проверка состояния GitHub
и не закрытие issues. Checklist остаётся 458 отмечено / 0 открыто;
tasks — 93 отмечены / 27 открыты. Полное перечитывание не выполнялось.

По сообщению main, diag15 terminal: build=0, test=0, postflight=216,
owned=0; PendingStart 161.99 s, LocalPurge 119.32 s. В этой узкой проверке
diff журналы и receipt diag15 повторно не исследовались, так что эти сведения
не объявляются независимо принятым runtime-результатом. Release-пара остаётся
отдельным последовательным запуском после terminal, без параллельной native
нагрузки и без переименования прежнего Debug RED в PASS.

Применён code-reviewer; reviewer не исполнял PowerShell/harness, сборки или
тесты, не обращался к VM/GitHub и не правил внешние файлы. Единственная запись
в рамках этого дополнения — собственный round460 report.

## Дополнение: количество native-проверок при чтении canonical в finalize

Независимый source-only вывод, без диагноза timeout и без предложения кэша.
Рассматривается успешный Windows packed path и обычный canonical float32
кадр 480 samples = 1920 bytes = 10 ms. Ниже посчитана именно сторона чтения
canonical в двух циклах преобразования, не вся стоимость finalize.

### Цепочка и точное число проверок

Пути в этом разделе относительно `apps/windows/RecApp/`:

1. `Recording/V5LocalRecordingWriter.cpp:721–723` вызывает `writeWav`, затем
   `writePlayback`. Первый цикл читает 1920 bytes на кадр в 376–379, второй —
   в 457–463. Каждый открывает отдельный reader из immutable packed snapshot
   (359 и 407). Само открытие даёт ещё один `checkRead` на reader, не на кадр:
   `Storage/ProtectedCustodyReader.cpp:494–508`, особенно 504.
2. `ProtectedCustodyReader.cpp:121–170`, `Reader::Read`: `status` до цикла
   (134), перед каждым пересечённым блоком (138), перед cursor/got ACK (169).
   `ReaderState::status:84–93` → `packed->checkRead()` →
   `ProtectedPackedCustodyTree.cpp:414–418` → `Guard::check()` →
   `ProtectedCustodyFiles.cpp:1388–1395` → `Owner::State::check:1255–1279`.
3. На cache miss: Reader 149–154 → `Tree::readBlock:429–492`.
   Его вход/выход — два `Guard::check` (434, 489). Для обычного non-ZERO DATA
   читаются три radix node (441–442) и DATA envelope (475). Каждое из четырёх
   `Guard::read` вызывает `check` до/после I/O (`Files.cpp:1407–1420`).
   Итого cache miss добавляет **2 + 4×2 = 10** полных native-check sweeps.

| Один успешный Read(1920) | Полных State::check |
| --- | --- |
| Кадр в одном блоке, plaintext уже в cache | 3 |
| Кадр в одном блоке, non-ZERO cache miss | 13 |
| Кадр пересекает блок, прежний cached + один новый non-ZERO | 14 |
| Кадр пересекает блок, оба non-ZERO блока требуют загрузки | 24 |

Общая формула: `2 + k + Σ(2 + 2*r_j)`, где k — число пересечённых блоков,
а r_j — количество envelope reads для каждого cache miss. Для non-ZERO
трёхуровневого дерева r_j=4. При authenticated ZERO обход заканчивается раньше,
DATA envelope не читается, поэтому к нему нельзя автоматически применять +10.
При отказе путь обрывается раньше, эти числа не являются счётчиками RED-запуска.

Размер блока — 262144 bytes (`ProtectedCustodyCodec.h:223`), не 1920.
Следовательно, +10 относится к загрузке блока, не к каждому 10-ms кадру;
полный блок содержит примерно 136.5 таких кадров. Существующий process-wide
cache хранит один plaintext block, keyed ReaderState/position
(`ProtectedCustodyReader.cpp:18–31,149–164`), с root proof в ReaderState.
Смена reader/чужой read может вытеснить его. Для двух указанных проходов обычный
внутриблочный cache-hit кадр даёт **3 + 3 = 6** sweeps только canonical-read.

### Состав одного State::check

Пусть D — число элементов `directories` по всей удерживаемой rootLease-цепочке,
P — число среди них с privateDirectory=true. Это зависит от admitted path,
поэтому единого числа Win32 API для любой машины из исходника вывести нельзя.
На успешном check(false) выполняются:

- **D+3 inspect**: все D ancestors и три файла — content.packed-v2,
  store.id, id.bin (`Files.cpp:1257–1275`). Каждый inspect вызывает
  GetFileType, GetFileInformationByHandle, GetFinalPathNameByHandleW и сравнение
  пути, проверяет reparse/type, для файлов — single hard link (204–217).
- **P+3 ACL-проверки**, каждая с GetSecurityInfo, проверкой защищённой DACL,
  единственного ACE/полного доступа/точного SID (`192–202,217`).
- **6 GetFileInformationByHandleEx(FileIdInfo)** — два для каждого из трёх
  файлов, с проверкой против удержанного identity и между before/after;
  ещё 3 GetHandleInformation проверяют запрет наследования HANDLE (1269–1276).
- **D+3 ADS inspections**: FindFirstStreamW для каждой directory/file;
  на трёх успешных file checks — также FindNextStreamW/FindClose
  (`1241–1253`). У directory допустим ERROR_HANDLE_EOF.

Например, один обычный cache-hit кадр — `3*(D+3)` metadata inspections,
`3*(P+3)` GetSecurityInfo и 18 FileIdInfo calls; два прохода — вдвое больше.
Это категории с вложенными вызовами, не сумма независимых syscall-счётчиков.
Каждый из четырёх Guard::read при non-ZERO miss дополнительно проверяет
фактический EOF через GetFileSizeEx (`Files.cpp:1281–1287,1308–1319`).
Четыре envelope reads не означают ровно четыре ReadFile: transfer делит
длинный envelope на chunks (`1289–1305`).

### Какие повторы связаны с границей доверия

Read не удерживает один Guard на весь COM-вызов: каждый status/checkRead
создаёт свой Guard; cache mutex удерживается на Read, но не заменяет native
owner/identity/fault checks. `Guard::read` защищает выдачу результата проверками
до и после native transfer; `readBlock` дополнительно проверяет owner на
границах операции и криптографическую цепь refs перед использованием plaintext.
Простое удаление этих барьеров без сохранения эквивалентной гарантии недопустимо.

Точечные основания: packed contract 35–49 — HANDLE/owner lifetime, confinement,
identity/ACL до effects, proof привязан к epoch; 112–118 — exact Ref SHA/length
до DPAPI и typed context/payload checks; 174–177 — validated cache разрешён,
но не через ownership gap и не вместо sticky-fault observation. Ошибка Read
обнуляет скопированные bytes, не продвигает cursor и не подтверждает частичные
bytes (`ProtectedCustodyReader.cpp:125–127,169–170`).

При этом контракт **не предписывает именно три одинаковых полного sweep на
каждом cache hit**. Это фактическая текущая композиция status перед Read,
перед копированием и перед ACK. Нельзя объявлять все повторы безусловно лишними
или, наоборот, считать точную кратность три самостоятельным требованием.
Эквивалентность иной реализации здесь не исследовалась и не допускалась.

### Граница подсчёта

Число 6 не является итогом всей финализации на кадр. Дополнительно существуют
WAV `writeAt` (V5:390; Writer:303–322/73–80), output MF Write/Seek/Finalize,
checkpoint/publish/readback, sealAudio-хеширование (V5:523–543; Sha256:222,
буфер 64 KiB), AAC decode (V5:511–515) и итоговый inspectProtected (735–743).
Они имеют собственные Guards и sizes/callback cadence, не один вызов на
canonical frame. В частности, sealAudio(canonical) уже читает весь canonical
для SHA до двух преобразований. Нельзя приписать всё это фиксированному
количеству native checks на один 10-ms frame или вывести время из числа вызовов.

Контрольные SHA-256 четырёх основных файлов:
V5LocalRecordingWriter.cpp `6da439e346cbf5f4fa72b83af13f51efea77ce8802112a9eecbbd6499764ec06`;
ProtectedCustodyReader.cpp `2bf35e4b9390f7c5f2dc3915fe43a72bd83a0dcf4a270dda309532415393cd3f`;
ProtectedPackedCustodyTree.cpp `7e148c7bcdf4d66bd1931a7db63590213c25d1827fed1fe66d153b55ecedba30`;
ProtectedCustodyFiles.cpp `8a64530c4f0770ce35a4d2798923d33827d342dc8799309f009f6e1b24bc69c2`.
Проверены локальные байты; привязка текущего Release16 PE здесь не проверялась.
Никаких VM/API probes, сборок, тестов, замеров CPU, изменений кода/нормативов/
checklist/tasks/GitHub не было; добавлен только этот раздел собственного отчёта.

## Дополнение: Reader initial-status candidate и actual Target extension

### Входы и границы вывода

Проверена текущая общая реализация Reader, её вызывающие стороны и существующие
native CLI. Production пока не изменён: SHA-256 ProtectedCustodyReader.cpp
`2bf35e4b9390f7c5f2dc3915fe43a72bd83a0dcf4a270dda309532415393cd3f`.
Ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty changes сохранены.
Это ограниченное read-only source review в действующем high-risk T116 lane,
а не новая приёмка T116, повторная проверка всех checklist или разрешение merge.

Main сообщил: Release16 terminal0, 2/2 PASS, PendingStart 185.871s,
LocalPurge 104.153s, post216/owned0; ранее Debug15 161.99s/119.32s.
Эти runtime результаты в данном дополнении независимо не перепроверялись.
Прежние DebugRED сохраняются в истории. Ни Release16, ни предлагаемый diff
не доказывают причину/исправление timeout, превосходство Release или готовность
приложения. Guest, тесты, сборки и внешние записи reviewer не выполнял.

### Предлагаемое удаление одной строки: scoped SOURCE GO

Допуск относится только к удалению строки Reader.cpp:134:
`const auto initial = state_->status(); if (FAILED(initial)) return initial;`.
Для будущего actual diff однострочный вариант вычислен только в памяти:
ожидаемый SHA-256 `50622e2a4468bf41a1246a6a692af88e08803ebbdd2f6fd218329a971ae453ec`.
На диск этот кандидат reviewer не записывал. Другие удаления status/Guard,
новые кэши authority, изменения length, locking, pin/admission не допущены.

Основание: Reader.cpp:135–136 выполняют только чтение удерживаемой длины и
ограниченную min/subtraction арифметику под прежним cache mutex (133).
ReaderState::length (63) — value accessor: packed->logicalBytes либо
snapshot.index.logicalLength. PackedTree.h:38–40,73–76 подтверждают immutable
descriptor/heads/retained stamp. Здесь нет allocation, callback, native I/O,
выдачи bytes, изменения cursor или публикации длины вызывающей стороне.

| Путь Read | Остающаяся защита |
| --- | --- |
| count>0, cache hit/miss, flat ZERO | status на 138 до первого/каждого chunk и до memset/memcpy/ReadBlock (146–165) |
| count=0: requested=0, пустой stream или EOF | status на 169 до S_OK/S_FALSE и got/cursor publication на 170–171 |
| Ошибка после нескольких chunk | reject на 125–127 стирает скопированный prefix, got остаётся 0, cursor не продвигается |
| Наблюдённый fault/cancel, в том числе через Clone/package | прежние shared atomic failure и observedStatus/fail на 71–93; cache-hit не обходит их |
| Неизменяемая длина, pin и native lifetime | прежние shared ReaderState/packed owner, Pin, Release/Clone; закрытие HANDLE не связано с удаляемым poll |

Invalid output pointer при requested>0 по-прежнему проверяется раньше любых
status (122–123). Для отказа до копирования reject не стирает чужой output:
copied=0. Его повторное fail сохраняет уже установленный sticky HRESULT.
Stat/Seek/Clone и их проверки не меняются (179–198,241–264).
Guard/readBlock/crypto/ref/identity/ACL проверки остаются без изменений.
Контракт packed:35–49 требует удержания owner и проверки native boundary до
content effects; 174–176 разрешает validated cache, но запрещает скрывать
наблюдённый fault. Три одинаковых check sweep на cache-hit не являются
самостоятельным требованием этого контракта.

Это эквивалентность обязательных границ и результата при наблюдаемом состоянии,
не идентичность trace/времени Windows API. Удаление poll меняет точки наблюдения
кратковременных внешних сбоев/cancel и call-count injection; нельзя обещать
наблюдение любого transient, исчезнувшего между проверками, или те же времена.
Оставшиеся проверки не отключаются при cached plaintext/EOF/zero.
Один cache-hit chunk теперь требует два, а не три status; count=0 — один
вместо двух. Это только source-count, не доказанное ускорение финализации.

### Вызывающие стороны общей Read

По поиску production RecApp найдены следующие прямые семейства; альтернативная
WriteStream::Read — другой класс, не объект кандидата:

- V5LocalRecordingWriter.cpp:379,463 — canonical 1920-byte reads для WAV/AAC.
- Sha256.cpp:213–252, особенно 236 — retained COM, 64-KiB reads,
  cancel до/после, проверка count и отдельный 1-byte EOF probe (233–240).
- LocalRecordingPackage.cpp:312–330 — protectedRead, metadata и EOF probe;
  точное количество bytes и cancel до/после не меняются.
- DesktopHttpTransport.cpp:735–749, особенно 744 — protected multipart body;
  Seek, cancel до/после Read, точные S_OK/count до передачи immutable body.
- Reader.cpp:216 — CopyTo; source/target удержаны (205), status перед
  destination Write и после callback (219–225), mutex не удерживается на callback.

Косвенные вызовы через Media Foundation: LocalRecordingPackage.cpp:434 и
ProtectedLocalRecordingPlayback.cpp:110 передают IStream в
MFCreateMFByteStreamOnStream. У playback сохраняются proof/Clone и native
consumer lifetime; удаление строки не меняет эти пути/сроки владения.

### Минимальный существующий набор для кандидата

Для scoped runtime допуска после actual одноcтрочного diff нужен Debug,
без параллельного выполнения, с отдельными source/PE receipts:

1. `ProtectedPackedCustodyTreeTests` — полный default CLI, без флагов.
   main:1973–1976 вызывает packedReader/releaseDrain/admission/CopyTo,
   а 1986–2003 — ZERO/pinned/fault/retained/refusal проверки.
   packedReader:569–572,624–642,660–670 покрывает zero/EOF/Clone/cancel/sticky;
   admission:744–761 — warm cache при отказе нового pin/allocation;
   CopyTo:819–835 — реальные callback/COM owners и cancel.
2. `ProtectedCustodyFilesTests` — полный default CLI, без флагов.
   Общий Reader используется и для flat/v1: protectedReader:977–1155,
   default main:5025. Здесь есть warm-cache isolation, authenticated ZERO,
   partial/EOF, callback cancel и sticky fault (1054–1077), native MF byte
   adapter (1093–1105), snapshot/pin/Clone lifetime (1110–1155).
3. `NativeProtectedPendingStart` — прежний CLI/CMake:196–197.
4. `NativeProtectedLocalPurge` — прежний CLI/CMake:213–214.

Tree/Files зарегистрированы как default tests через CMake:173.
Assertions не вырезаются в Release: TreeTests:6–11 и FilesTests:20–23 явно
undef NDEBUG перед cassert. Release остаётся отдельной qualification,
не заменой перечисленного Debug или прежних RED. Никакие TIMEOUT/deadline,
assertions, frames, polls или порядок consumer операций не меняются.
Узкий `--reader-release-drain` уже входит в полный Tree default, повторять его
отдельно в минимуме не требуется. Специального reader-only CLI не вводить.

В прочитанных Reader fixtures здоровые zero/EOF и sticky/cancel проверяются
по отдельности; прямой отдельный assertion `Read(nullptr,0)` уже после fault
не найден. Это не заявлено как выполненная комбинация runtime-покрытия:
её поведение здесь обосновано финальным безусловным status на 169.
Полная native/installed/security/consumer acceptance остаётся отдельной;
MediaEngine/PlaybackConsumer/ManualSend и другие действующие проверки не
отменены, но не объявляются новым обязательным минимумом этого одного удаления.

### Actual external harness Target extension: GO

Сравнены байты `release16-native-delays/validate-input.ps1` и `validate.ps1`.
Baseline SHA-256 `92fd57707b43bbd0c85f1a0864526e49f8a3c45afaa8018c319a563f54993463`;
actual SHA-256 `346fd4ad0f417725f1b9b8539a9398cda70c938ea70fc05fa382ed9818015d9f`.
Ровно одна изменённая строка param: в Target ValidateSet добавлен только
`ProtectedPackedCustodyTreeTests`. Все остальные строки побайтово прежние.
Проверка whitespace через --no-index --check не выдала замечаний.

GO на этот exact extension и последовательный baseline Tree default CLI с
`-Target ProtectedPackedCustodyTreeTests -Test ProtectedPackedCustodyTreeTests`.
Defaults NativeCapture/Debug, Configuration, Owned-process preflight,
216-source pre/post, scope/hash checks, PE checks и CTest порядок сохранены.
До Reader diff этот прогон даёт baseline, не кандидатную регрессию.

По уточнению main `native_metadata_probes` означает endpoint/AAC probes для
NativeCapture, а не универсальный запрет файловых native checks; при этой
явно указанной семантике его false для Tree не блокирует допуск.
В evidence обязательно различать: device audio/network/install не используются,
но generated-fixture native filesystem/ACL/identity/DPAPI операции выполняются
(Tree fixture:82–105,117–122). Нельзя описывать такой запуск как отсутствие
любых native metadata/IO проверок. Поле и его семантику reviewer не изменял.

Для полного минимального набора пункта 2 пока отсутствует
`ProtectedCustodyFilesTests` в Target ValidateSet. Нужен такой же отдельный
минимальный actual extension review до запуска через этот harness, а не
обход существующего ValidateSet/guards. Это не препятствует согласованному
baseline Tree. Source/PE manifests и каталоги каждого прогона не смешивать.

Текущие контрольные SHA: TreeTests
`9a47bbd2e8c3237b1bc4b51261172fdd4ecbe17735891a0d85368fce2fffc4cd`;
FilesTests `719322594711ab7bc91b83205d9da65cf894cd21dfd4d849720afe6f407571ce`;
NativeCaptureStorageIntegrationTests
`fc85c594db6e82a7660b264a0dd58ef6cce4a74343733d73a66d229b5f4e655e`;
CMake `140943a00a74f3d0d27261e0a769192d03b795f35054c230dac666c1182ff950`.
Изменён reviewer только собственный report; прежние части, код, markers,
нормативы, внешний harness и GitHub не менялись.

### Actual zero/EOF assertions и Files Target: scoped SOURCE GO

Независимо сравнены TreeTests с `reader17-before/tree-test-input.cpp` и внешний
validate.ps1 с `reader17-before/validate-input.ps1`. Tree diff — ровно 8 added
lines, без удалений. EOF Clone создан и Seek END выполнен до cancellation;
обычный cancel Read сохранён; после reset токена оба Read требуют прежний
ERROR_OPERATION_ABORTED и got=0, причём got перед каждым установлен в 9.
EOF Clone разделяет sticky ReaderState с исходным Clone; cursor независим,
нулевой запрос и фактический EOF идут без chunk. eof.Reset расположен перед
clone.Reset и cold reopen: лишний native owner не остаётся к новой эпохе.
GO на эти exact assertions, включая подготовку EOF и реальный COM lifetime.

TreeTests SHA-256 `1d3bb24c003c57e6a354a7b5abef8fc038a7950664f5db07fdd557969ac42fd5`;
Reader остаётся `2bf35e4b9390f7c5f2dc3915fe43a72bd83a0dcf4a270dda309532415393cd3f`.
Harness diff — только добавление ProtectedCustodyFilesTests в param ValidateSet;
SHA-256 `5294fcf0bc0db7ec54caff74f8fb4f65ae50297b6bedc54498d5070e64c968d7`.
Остальные guards/config/default побайтово сохранены: GO на exact extension.
GO на последовательный Debug Tree default с новыми assertions на старом Reader,
с новым source manifest и отдельными PE/receipt; это ещё не product candidate.
Baseline17 terminal build0/test0/1case/post216/owned0, 43.84s и PE3b90f22… —
сообщение main, здесь runtime receipts не перепроверялись. Новых builds/tests,
guest checks, production/нормативных/checklist изменений reviewer не выполнял;
добавлено только это дополнение собственного отчёта.

### Независимая проверка сохранённых receipts Release16 / Reader18

Scoped receipt GO: проверены только external файлы завершённых
`release16-native-delays` и `reader18-regression`, без guest/Files19.
Result JSON, XML, actual-test.log, build.log, frozen harness и manifests
согласованы. Ошибок идентичности/пропусков в проверенной области не найдено.

- Release16: ровно NativeProtectedPendingStart и NativeProtectedLocalPurge,
  XML tests2/failures0/skipped0/disabled0, status run; actual commands —
  build/Release/NativeCaptureStorageIntegrationTests.exe с существующими
  --protected-pending-start и --protected-local-purge. XML times 185.872s и
  104.152s (raw LastTest отображает округлённо 185.87s и 104.15s).
  Сохранённый cl-command.tlog указывает этот integration TU, /O2 /Ob2 /MD,
  /D NDEBUG и CMAKE_INTDIR Release; vcxproj содержит Release|x64/MaxSpeed.
  TU fc85c594… сам undef NDEBUG перед includes/cassert: assertions остаются.
  Manifest216 SHA c2e9d8b7016b80619f41b5f327de20092fb991586ed01ff445051a96559784ad;
  Reader старый 2bf35e4b…; test TU fc85c594…; changed.json пуст.
  PE receipt SHA 9ec6f78276ce9a7a1da55e58c0360669f216b3f8acd42790a1890bd84c99269d,
  bytes2556416. build0/test_exit0/executed_tests2/postflight216/owned0,
  terminal=true, failure отсутствует.
- Reader18: ровно ProtectedPackedCustodyTreeTests, XML tests1/failures0/
  skipped0/disabled0, status run, 39.4423s. Actual command —
  build/Debug/ProtectedPackedCustodyTreeTests.exe БЕЗ аргументов (default CLI).
  Build log подтверждает Debug target и компиляцию TreeTests.cpp.
  Manifest216 SHA a9d5c34de064b6e39b8f20c8661f896b3a5e5cba0ec17e2105a0c4b3043026dc;
  216/216 текущих локальных файлов совпали. prior.sha256 побайтово равен
  Release16 source.sha256; единственное изменение manifest — TreeTests
  9a47bbd2… -> 1d3bb24c003c57e6a354a7b5abef8fc038a7950664f5db07fdd557969ac42fd5.
  Сохранённая staged copy новых TreeTests имеет тот же SHA, Reader остаётся
  2bf35e4b9390f7c5f2dc3915fe43a72bd83a0dcf4a270dda309532415393cd3f.
  PE receipt SHA c95b206434b266f3976a148ea39a0130da408128b21b8dac35f024dfa6c5e51f,
  bytes7023616. build0/test_exit0/executed_tests1/postflight216/owned0,
  terminal=true, failure отсутствует.

Frozen harness SHA соответственно 92fd5770… и 5294fcf0…. В обоих сохранены
Owned preflight (14), source216 prior/pre (15,25), cmake --config (30),
ctest -C с anchored pattern (38), source216 postflight (44) и повторный
Get-FileHash PE против pre-test SHA (35,45); failure/owned запрещают exit0 (54).
PE equality после CTest подтверждается успешным receipt при этом неизменном
guard, не отдельным сохранённым after-hash: EXE и независимого after-hash
в этих external каталогах нет. Reviewer их заново не хешировал в guest.
Reader18 доказывает прохождение дополненных assertions на СТАРОМ Reader,
не runtime GO кандидата 50622… и не исправление DebugRED. Новых тестов/сборок,
изменений source/harness/checklist/нормативов/VM/GitHub не выполнялось;
append сделан только в собственный report.

### Reader20: окончательный actual SOURCE GO однострочного кандидата

Сравнены текущий Reader и `reader17-before/reader-input.cpp`: ровно удаление
initial status строки, без других изменений. Побайтовое обратное сравнение
подтвердило ранее допущенный кандидат; SHA-256
`50622e2a4468bf41a1246a6a692af88e08803ebbdd2f6fd218329a971ae453ec`.
TreeTests остался 1d3bb24c…; внешний harness остался 5294fcf0….
Manifest reader20-after SHA-256
`5512492a14b8499aba680f349eca343bbd997afba77ec5b9ff5e481854adfdb7`:
216 записей, 216/216 совпали с локальными файлами. От Reader18 изменён только
Reader; changed.json содержит только этот путь; staged Reader имеет 50622….

Окончательный scoped actual SOURCE GO, без findings. Проверены фактические
оставшиеся границы: Reader.cpp:137 — status до каждого chunk, native read и
cache-hit/ZERO copy; 168 — безусловный status для zero/EOF и перед cursor/got
publication (169). length/min (134–135) остаются value-only. Sticky fault/cancel,
reject wipe/no advance (125–127), Guard/crypto/ACL/identity, pins/Clone/lifetime
не менялись. Это не обещание одинакового API trace/момента transient observation.

Files19 baseline terminal0/build0/test0/post216/owned0/PASS404.57s и порядок
«изменение только после terminal» — сообщение main, здесь отдельно не проверены.
Reader20 Debug Tree live: runtime GO кандидата пока не выдан. Минимальные
кандидатные Tree/Files/PendingStart/LocalPurge проверки остаются необходимыми;
это не заявление об исправлении прежнего timeout и не закрытие T116.
Новых нормативных итераций, source/harness/checklist/guest/VM изменений,
сборок и тестов reviewer не выполнял; добавлен только этот раздел отчёта.

### Reader20-after: scoped Debug Tree runtime receipt GO

Независимо проверены только завершённые external reader20-after result.json,
result.xml, actual-test.log, source manifest и frozen validate-input.ps1.
Ровно один test ProtectedPackedCustodyTreeTests, Debug, status run:
tests1/failures0/skipped0/disabled0, XML time56.3501s. Actual command —
build/Debug/ProtectedPackedCustodyTreeTests.exe без аргументов: полный existing
default CLI, не --reader-release-drain subset. Drain marker: все девять
флагов равны 1; empty cache charge/delta16 совпадают.

Manifest SHA `5512492a14b8499aba680f349eca343bbd997afba77ec5b9ff5e481854adfdb7`,
216 уникальных входов; 216/216 текущих локальных файлов совпали.
Reader `50622e2a4468bf41a1246a6a692af88e08803ebbdd2f6fd218329a971ae453ec`,
TreeTests `1d3bb24c003c57e6a354a7b5abef8fc038a7950664f5db07fdd557969ac42fd5`;
staged Reader совпал, changed.json содержит только Reader.
Receipt: build0/test_exit0/executed_tests1/postflight216/owned0,
terminal=true, failure отсутствует. PE SHA
`219b163e81d90a1347dc1b85f93bc2c10d3d2296aa7914025b8f03ddd8f73538`,
bytes7023616. Frozen harness `5294fcf0…` сохраняет source216 pre/post и
PE-before/after equality guard. Как прежде, это evidence успешного guard,
не независимое хеширование EXE reviewer или отдельный сохранённый after-hash.

Scoped runtime GO только для полного Debug Tree на exact Reader50622… с
новыми zero/EOF-after-sticky-fault assertions. Несоответствий не найдено.
Это не общий T116/runtime/performance GO и не доказательство исправления
прежних timeout. Files21/session43577, partial/live logs и guest не читались;
сборки/тесты/production/checklist/нормативы не менялись. Append — только сюда.

### Files21-after: scoped Debug Files runtime receipt GO

Проверены только завершённые external files21-after result.json/XML, полный
actual-test.log, source/prior manifest, changed.json и frozen harness.
Ровно один ProtectedCustodyFilesTests, Debug, status run, XML time395.147s:
tests1/failures0/skipped0/disabled0. Actual command —
build/Debug/ProtectedCustodyFilesTests.exe без аргументов, полный existing
default CLI. XML system-out усечён CTest, поэтому прочитан полный actual log:
есть закрытый Output, Test Passed и End testing, в конце protected-v5
owned_before=16 owned_after=16; это не приёмка по усечённому XML выводу.

Source manifest SHA
`5512492a14b8499aba680f349eca343bbd997afba77ec5b9ff5e481854adfdb7`
побайтово равен Reader20 manifest: 216 уникальных входов, 216/216 локальных
файлов совпали. Reader50622…, FilesTests71932259…, TreeTests1d3bb24c….
Receipt: build0/test_exit0/executed_tests1/postflight216/owned0,
terminal=true, failure отсутствует. PE SHA
`3bddfa0a911140f5cc70da28228f52bec17f2f1a50e3d50f15eef801c19b319f`,
bytes8440320 — совпало с заявленным main.
Frozen harness SHA5294fcf0… сохраняет Owned preflight, source216 pre/post,
Debug --config/-C и сравнение SHA PE до/после CTest. Успешный receipt
подтверждает прохождение guard; отдельно EXE/after-hash reviewer не получал.

Scoped runtime receipt GO для полного Debug Files на кандидате Reader50622…;
несоответствий не найдено. Это не полный T116/performance/timeout-fix GO.
native22-reader-after/session16579 и его live logs не читались, guest/builds/
tests/production/checklists/нормативы не трогались. Append только в этот report.

### Scheduler-final: actual трёхстрочный identity-only diff GO

Сравнены только external scheduler-final.ps1 и
native22-reader-after/scheduler-before.ps1. Ровно три изменённые строки:
output -> native23-reader-scheduler (4), manifest ->
native22-reader-after/source.sha256 (7), expected Debug PE ->
`6a9d902537e6cbf3317018f27308a61a55aa3cfda02f70db682ecffb51731848` (10).
Frozen before SHA d2abb7cb36728cff2cce90432814d5392fae1baf02b203f6d7bcef1532e7b8b1;
actual SHA 74e9a84783400b8172cdff2aa188718aa4c5d420eb2a75c02b6a2a989bb0ce39.
Указанный сохранённый manifest имеет candidate SHA
`5512492a14b8499aba680f349eca343bbd997afba77ec5b9ff5e481854adfdb7`.
Остальные строки неизменны: OUTPUT_EXISTS, source216/PE checks, Owned guard,
четыре существующих scheduler CLI (30), проверки после каждого CLI, exit/receipt.

Scoped actual SOURCE GO только на этот identity-only diff, без findings.
Допуск запуска условный: дождаться terminal native22, owned0 и совпадения
expected PE с его завершённым receipt; при несовпадении не запускать и не
обходить guard. Guest hash здесь не получался и PE native22 независимо не
проверялся. Native22 live logs/session16579 не читались; прочитаны только
указанные frozen scheduler-before и manifest. Scheduler не запускался,
production/нормативы/checklists не менялись, append только в свой report.

### Native22-after: scoped Debug pair runtime GO; минимум Reader 4/4

Независимо проверены только завершённые native22-reader-after result.json/XML,
полный actual-test.log, source manifest и frozen validate-input.ps1.
Ровно NativeProtectedPendingStart и NativeProtectedLocalPurge, Debug,
tests2/failures0/skipped0/disabled0, оба status run и Test Passed.
Фактические команды используют один build/Debug/NativeCaptureStorageIntegrationTests.exe
и существующие --protected-pending-start / --protected-local-purge.
XML times: 137.551s и 94.1219s. Полный LastTestlog заканчивается End testing;
LocalPurge проверен по полному выводу, не усечённому XML system-out.

PendingStart: V5_CASE0/8 имеют start, frames_3000, finalized, cold_read,
cold_read_verified, done; оба PUBLIC_RECORD accepted=1 state3 reason0.
Frozen TU fc85c594… dispatch --protected-pending-start вызывает normal и
signedOut (6910–6912). cancel_case0–5 присутствуют по одному, все no_frames1/
no_saved1/released1; case2 devices2/guard1, остальные devices0/guard0.
submit_refused1/no_io1/released1 присутствует один раз.
LocalPurge: mode0–8 представлены полностью begin/prepared/cold_shutdown/end
и PROTECTED_LOCAL_PURGE результатом; mode8 содержит recovered. Cold_queue1,
audio0/real_network0 на всех девяти результатах. Это завершение всех режимов,
не предположение по последнему mode7 или одной общей отметке PASS.

Manifest SHA `5512492a14b8499aba680f349eca343bbd997afba77ec5b9ff5e481854adfdb7`
побайтово тот же, что у Tree20/Files21: 216 уникальных входов,
216/216 текущих локальных файлов совпали. Reader50622…, TreeTests1d3bb24c…,
FilesTests71932259…, Native TU fc85c594….
Receipt build0/test_exit0/executed_tests2/postflight216/owned0/terminal=true,
failure отсутствует. PE SHA
`6a9d902537e6cbf3317018f27308a61a55aa3cfda02f70db682ecffb51731848`,
bytes10085376. Frozen harness5294fcf0… тот же: source216 pre/post и PE equality
guard подтверждаются успешным receipt, не независимым чтением guest EXE.

Несоответствий не найдено. Scoped runtime GO Native22 и завершённый ранее
согласованный минимум 4/4 для ОДНОСТРОЧНОГО Reader50622…: Tree20, Files21,
PendingStart22, LocalPurge22 на общем manifest5512492a….
Это не установление причины прежних DebugRED/timeout, не performance acceptance,
не T116/full-product/release GO. Scheduler23 live, его журналы и VM не трогались;
порядок его запуска после native22 exit0/owned0 здесь принят как сообщение main,
не самостоятельная проверка scheduler execution. Новых проверочных запусков,
изменений production/нормативов/checklists нет; append только в свой report.

### Scheduler23: scoped saved runtime receipt/log GO, 4/4

Проверены только завершённые native23-reader-scheduler result.json,
scheduler-input.ps1 и все четыре полных UTF-16LE BOM logs. Frozen script SHA
`74e9a84783400b8172cdff2aa188718aa4c5d420eb2a75c02b6a2a989bb0ce39`
совпал с reviewed identity-only script. Receipt содержит ровно по одному
ожидаемому option в прежнем порядке, каждый exit0:

- --protected-scheduler, 73956ms: generated_recording_cold_prepare_network_result_adoption=pass.
- --protected-scheduler-ambiguous, 72162ms:
  failed_result_physical_readback=pass published=1 quota_refused=1.
- --protected-scheduler-not-committed, 71421ms:
  failed_result_physical_readback=pass published=0 quota_refused=0.
- --protected-scheduler-stop-prepared, 77555ms:
  cold_stop_prepared old1/status3/transport_unavailable/attempts1/server1,
  old0/status5/capture_prepared/attempts0/server0 и stop_prepared_while_result_busy=pass.

Во всех logs присутствуют V5_CASE7 start/frames_3000/finalized/cold_read/
cold_read_verified и prepare_state1/base3/target4/wire0 до конечных markers.
Первый stderr NATIVE_STORAGE обёрнут Windows PowerShell в NativeCommandError;
frozen script ставит EAP Continue на native invocation (32), берёт реальный
LASTEXITCODE (34), затем возвращает Stop, проверяет inputs/PE и code (37–38).
Обёртка сама по себе не принята за провал: фактические exit0 и последующие
полные pass markers подтверждают завершение, а не подавление ненулевого exit.

Manifest receipt и сохранённый referenced native22 source manifest совпали:
`5512492a14b8499aba680f349eca343bbd997afba77ec5b9ff5e481854adfdb7`,
216 уникальных входов. PE receipt/expected
`6a9d902537e6cbf3317018f27308a61a55aa3cfda02f70db682ecffb51731848`
совпал с ранее квалифицированным Native22. postflight216/owned0/terminal=true,
failure отсутствует. Assert-Inputs проверяет source216/PE до первого CLI и
после каждого; scoped equality evidence получено из script+успешного receipt,
не из нового guest GetFileHash. Скрипт при этих данных завершает exit0.

Scoped saved runtime receipt/log GO Scheduler23, несоответствий не найдено.
Это не полный T116/root-cause/performance/product/release GO. Native24/session
и partial/live logs не читались, VM/builds/tests/source не трогались.
Нормативы/checklists не пересматривались; append только в этот report.

### T116/#7444: узкая карта оставшейся реализации после P2/P3

Read-only source review по code-reviewer; не повторная приёмка receipts.
Native24/session18128, VM, live logs, builds/tests не трогались. Проверены
только текущие T116/P2/P3 и их production callers; нормативная база не менялась,
новые checklists и задачи не создавались. Аудит остановлен на известном остатке
P2, без поиска других дефектов по репозиторию. Полного T116 GO нет.

**(a) Подтверждённая незавершённая функциональность P2, не новая небезопасная
регрессия.** Plan:2319–2322 прямо оставляет continuation начатых outputs частью
T116; plan:2507–2515 ограничивает раунд457 полностью записанным terminal layout
и не закрывает P2 целиком. Текущая production цепочка:

- NativeCapture.h:2280–2299 — recovery worker проверяет queue/package и для
  capturing/finalizing вызывает V5LocalRecordingWriter::prepareRecovery.
- V5LocalRecordingWriter.cpp:165–168 — сначала openUnfinished обычного режима,
  при recoveryRequired — отдельный fresh completed acquisition; третьей ветки
  продолжения промежуточного started layout здесь нет.
- ProtectedCustodyMetadata.cpp:1721–1735 — обычная ветка требует unused roles;
  completed ветка проверяет завершённые роли/metadata. В
  ProtectedCustodyFiles.cpp:702–712 unused означает только id.bin; completed
  (716–755) требует точный inventory content/index файлов. Частичное содержимое
  не получает полномочий только из-за наличия или имени файла.
- V5LocalRecordingWriter.cpp:679 сначала выполняет writeWav, затем writePlayback;
  manifest/recovery/final seal идут далее, 683–686. Поэтому промежуточная точка
  после начала outputs существует в реальном production пути.
- V5LocalRecordingWriterTests.cpp:304–336 различает completed, started и unused:
  completed продолжает; started на 331–333 обязан отказать и сохранить все bytes.

Следствие: после такого прерывания автоматический recovery может не довести
сохранённый canonical до playable degraded, хотя unused и полностью terminal
варианты уже реализованы. Это сохранённый защитный отказ, а не утрата исходника,
plaintext fallback, normal promotion или доказанная причина прежнего timeout.
Не доказано, что произвольный частичный layout безопасно продолжать; убирать
этот отказ или менять все отрицательные тесты было бы неверно.

**(b) Production integration уже есть; source presence не равна runtime acceptance.**

- P3: AppMain.cpp:2478–2499 использует readiness/public record;
  NativeCapture.h:473–482 и 1844–1850 проверяют текущий protected queue/startup
  predicate и повторный admission. Историческое permanently-false поле из
  обоснования plan:2567 нельзя выдавать за нынешнюю отсутствующую реализацию.
- AppMain.cpp:1515–1544: unowned manual send с явным native подтверждением,
  актуальным snapshot/document/account и requestProtectedManualSend; P1 не missing.
- Playback: AppMain.cpp:1437–1464 → NativeCapture.h:666–687 →
  ProtectedLocalRecordingPlayback.cpp:73,110–115, protected IStream/MF adapter,
  без filesystem URL/export fallback. Worker dispatch отделён от UI.
- Upload: DesktopHttpTransport.cpp:1452–1481 принимает genuine protected proof,
  sealedNormal и retained logical stream; bounded hash/read вместо открытой копии.
- Recovery: AppMain.cpp:3417–3433 → NativeCapture.h:496–518 → worker выше;
  deletion: AppMain.cpp:1550–1565,1623–1629,1643–1645 →
  NativeCapture.h:762–815, current snapshot/account, durable selection и purge.

Эти пути не предлагается писать заново. Публичные AppMain сценарии на точном
установленном пакете, включая restart/account/cancel/error, требуют собственной
приёмки; generated native PASS её не заменяет. Native24 ещё не квалифицирован.

**(c) Отдельные границы:** tasks.md:569 T117 — переход старых plaintext данных;
570 T118 — сквозная protected acceptance/100 циклов/faults/installed; 583 T119 —
calendar join; 602 T120 — приватная Pause/Resume. Они не закрываются этим аудитом.
При этом явно отнесённая T120 к T116 поправка manifest64KiB остаётся storage
обязательством T116, а не основанием перенести весь privacy workflow в T116.

**Короткий порядок следующих действий:**

1. Следующий implementation slice — оставшийся P2: выбрать ровно один реальный
   промежуточный crash cut существующего writer и доказать условия безопасного
   continuation в рамках текущих BOTH refs/history/continuous owner протоколов.
   Затем минимальная реализация и RED/GREEN в существующем recovery тесте;
   неизвестные/partial-birth/ambiguous состояния по-прежнему сохраняются с отказом.
   Если для выбранного cut доказательств недостаточно, не ремонтировать его
   эвристикой. Это направление работы, не source GO ещё не предъявленного diff.
2. После покрытия согласованного P2 состояния — точная публичная AppMain приёмка
   уже подключённых record/playback/send/recover/delete путей. Не добавлять новые
   owners/readiness flags, кэш полномочий или открытые промежуточные файлы.
3. T117 и T118 вести отдельно по их зависимостям; T119/T120 не подменять
   завершением T116. Совпадение дизайна/полный Windows/release GO здесь не выдаётся.

### P2 feasibility: готовый media WAV, playback/recovery ещё unused

Только source review по code-reviewer; нормы не менялись/не пересматривались,
production не редактировался. VM/native24/session18128/logs/builds/tests не
трогались. Вывод: **NO-GO для design/correctness approval сейчас**; возможность
узкого продолжения не опровергнута, но следующие доказательства отсутствуют.

Первый API blocker — смешанное fresh acquisition отсутствует.
ProtectedCustodyMetadata.cpp:1671–1682 с самого начала получает writable
package-root/state, но role access определяется одним completed: обычный режим
делает media writable и требует unused (1734), completed делает все outputs и
manifest readonly и требует уже готовые playback/recovery (1721–1735).
Ни одна ветка не допускает готовый readonly media + writable unused playback/
recovery + writable existing manifest. Просто пропустить unused проверку нельзя:
packed openImpl:1494–1497 в ProtectedCustodyFiles.cpp отвергает writable prepared
role для readExisting. Readonly inspection → upgrade/reopen не предлагается.

Минимальные существующие точки reuse, не готовый проект и не разрешение patch:

- Fresh private openUnfinished должен с первого acquisition удержать нужные
  права каждой роли, BOTH package/history/ID проверки оставить прежними.
  Для media уже есть same-content-handle container discovery:
  ProtectedCustodyFiles.cpp:1471–1473,1538–1558. Дальше Tree::verify:112–123
  проверяет BOTH heads и полные closures; Format::selectHeads:92–103 отвергает
  пропуски поколений. Не использовать path-only reopen/старый сохранённый proof.
- Полная tree verify не доказывает отсутствие unknown physical tail:
  Format::decodeDescriptor:78–80 требует committedExtent <= actualBytes,
  не equality. Для выбранного строгого media layout недостаёт отдельного
  same-Guard доказательства exact EOF == selected committedExtent (Guard::size,
  ProtectedCustodyFiles.cpp:1398–1404); tail не обрезать и не принимать эвристикой.
  Это не требование менять допустимый неполный canonical logical tail.
- WAV preflight должен доказать exact 44+completeFrames*320 bytes и каждый PCM
  байт по нынешнему writeWav преобразованию (V5LocalRecordingWriter.cpp:352–395),
  включая header/EOF и конечную cancellation/sticky-fault проверку. Нынешний
  validateProtectedContent, LocalRecordingPackage.cpp:746–750, проверяет header,
  но не равенство WAV payload canonical; hash существующего WAV сам по себе
  этой связи не доказывает. Такой preflight пока отсутствует.
- Удержанные canonical/media snapshots можно использовать для sealAudio(...,
  false), которое формирует ref/hash без checkpoint (V5:523–555). Existing
  inspectUnfinished/unfinishedHistory (LocalRecordingPackage.cpp:476–559)
  сохраняют проверку canonical prefix и bound privacy/time history. Но нынешний
  retainPrefix:679 всегда вызывает writeWav, а createWriter:1815 отказывает при
  уже имеющемся packed owner. Значит существующий WAV нужно именно проверить и
  удержать, не вызывать для него writer; AAC может использовать writePlayback
  (V5:401–516) только после строгого unused admission. Manifest/recovery/final
  commit переиспользуют прежний rollover/ACK, не обходят его. Package/role IDs и
  canonical/media container IDs неизменны; container ID ещё не созданного AAC
  не следует объявлять восстановленным из исчезнувшего volatile reservation.

Physical child-cut evidence пока не доказывает заявленную точку полностью.
V5LocalRecordingWriterTests.cpp:86–101,117–131 уже наблюдает role=1 operation=6
после успешного media HEAD flush и завершает child без destructors. Fixture
(225–241) даёт WAV 32044 bytes, то есть меньше одного packed block. Но cut внутри
FlushFileBuffers предшествует native HEAD readback (Files.cpp:1801–1802), затем
Tree checkpoint ACK (Tree.cpp:399–407), затем sealAudio hash/ref (V5:537–555).
Это хороший существующий физический cut для повторной cold проверки, а не
свидетельство возврата всего checkpoint. Current tests:331–333 лишь требуют
отказа/byte preservation; exact proposed shape и positive continuation не проверены.

Кроме того, если «BOTH package-state finalizing» означает ОБА slots finalizing,
это не shape нынешнего coldCrashFixture на данной границе: commitMetadata в
capturing, затем retainPrefix:661–662/commitState:582–592 публикует один finalizing;
до playback предыдущий slot остаётся capturing. Если имелось в виду BOTH-valid
с selected finalizing, это соответствует существующему phase admission
(Metadata.cpp:1694–1699). Не добавлять лишнюю публикацию ради совпадения fixture.

Следующий ограниченный шаг — предъявить точное admitted shape + fresh mixed
acquisition/preflight diff и доказать его на существующем physical child cut:
unchanged canonical/WAV/IDs, unused playback/recovery, полный cold degraded
inspection и сохранённый отказ на tail/bad peer/partial birth/cancel. Сейчас нет
ни design GO, ни correctness/runtime/T116 GO; новый формат/кэш/owner не предложен.

### Native24: завершённая Debug consumer-регрессия, scoped runtime GO 19/19

Независимо прочитаны сохранённые native24-reader-consumers result.json,
все 19 testcase result.xml, весь actual-test.log, test.log/build.log,
validate-input.ps1, source/prior manifests и changed.json. Сопоставлены с
завершённым green12-final-consumers и ранее квалифицированным Native22.
Применён code-reviewer; это чтение evidence, без VM/build/test запусков,
GitHub/production/нормативных/checklist изменений. Append только в этот report.

XML: tests19/failures0/disabled0/skipped0; ровно 19 уникальных testcase,
каждый status=run, без failure/error/skipped элементов. Полный LastTest log
содержит ровно те же 19 блоков, по одному ожидаемому CLI и Test Passed в каждом,
все end-of-output/end-time и конечный End testing. Ни Not Run, ни skip/disabled
маркеров нет. UTF-16LE BOM у test.log/build.log; actual-test.log — ASCII/CRLF.
В пяти XML system-out штатное усечение после 1024 bytes: ShortDiscard,
DeletionApplication, LocalPurge, LocalRemoval, PurgeFlight; первые 1024 bytes
совпали с полным log. Остальные 14 system-out совпали полностью. Продолжения
пяти усечённых выводов проверены по actual-test.log, не по усечённому XML.

Все имена ниже имеют префикс NativeProtected; время — точное testcase XML, sec:

| Тест | CLI suffix после --protected- | PASS, sec |
|---|---|---:|
| BirthAdmission | birth-admission | 0.368703 |
| PendingStart | pending-start | 143.135 |
| ShortDiscard | short-discard | 113.833 |
| InspectionPreparation | inspection-prepared | 70.3605 |
| FinalizeAdmission | finalize-admission | 6.36761 |
| InspectionActiveStop | inspection-active-stop | 145.575 |
| ReadModel | read-model | 3.31093 |
| DeletionIntent | deletion-intent | 2.22224 |
| DeletionAnswer | deletion-answer | 2.74244 |
| DeletionApplication | deletion-application | 9.25406 |
| DeletionDisplay | deletion-display | 3.70342 |
| LocalPurge | local-purge | 94.0807 |
| LocalRemoval | local-removal | 96.7174 |
| ServerPurge | server-purge | 115.739 |
| PurgeFlight | purge-flight | 152.419 |
| ManualSend | manual-send | 25.5032 |
| AccountProblems | account-problems | 0.657631 |
| DisplayTiming | display-timing | 5.24312 |
| PlaybackConsumer | playback-consumer | 25.2619 |

Все CLI совпали с текущими add_test в CMakeLists.txt, executable path в каждом
блоке — build/Debug/NativeCaptureStorageIntegrationTests.exe. CTest log: 100%,
19/19, real1016.53s. PendingStart прошёл PUBLIC_RECORD normal/signedout (cases0/8)
через finalized/cold_read_verified/done, cancel0–5 и submit_refused/no_io/released.
LocalPurge и LocalRemoval прошли modes0–8, включая recovered8/cold_shutdown/end.
Проверены ShortDiscard отказы/physical effects/reconciliation и NATIVE_SHORT0–9;
DeletionIntent/Answer cuts0–4; DeletionApplication0–17 с forced_destroy13–15;
ServerPurge0–6, PurgeFlight0–12; ManualSend0–4/unowned/legacy refusal. Остальные
конечные semantic/display/playback/inspection markers присутствуют, включая
prepared cancellation zero-wire, active-stop both-EOS/sealed adoption/restart7,
playback generated_muted=1/UI_acceptance=0 и display stale/logout revocation.

Идентичность и завершение:

- Manifest SHA256 `5512492a14b8499aba680f349eca343bbd997afba77ec5b9ff5e481854adfdb7`:
  пересчитан, совпал с receipt и Native22; 216 уникальных paths. prior==source,
  changed.json пустой. Пересчитаны все 216 текущих host source files: 0 mismatches.
- Frozen harness SHA256
  `5294fcf0bc0db7ec54caff74f8fb4f65ae50297b6bedc54498d5070e64c968d7`,
  Debug default, прежние guards. Проверяет prior216/source216 до build, source216
  после тестов, PE после build и неизменность после suite; /nr:false, build -j1.
- PE receipt `6a9d902537e6cbf3317018f27308a61a55aa3cfda02f70db682ecffb51731848`,
  10085376 bytes, совпал с сохранённым Native22. Это receipt+прошедший script
  before/after guard, не новый независимый guest GetFileHash/локальный PE hash.
- Receipt terminal=true/build0/test_exit0/executed19/postflight216/owned0,
  failure отсутствует; saved harness при этих значениях возвращает exit0.
  Отдельный process18128 exit0 принят как сообщение main, процесс не опрашивался.
  device_audio_read=false/real_network=false/installed=false,
  native_metadata_probes=true; это не установленная UI/hardware приёмка.

Original green12: ровно тот же Test pattern, 19 имён, порядок и полная command
map. Тогда 17PASS/2FAIL: PendingStart181.459s/assert deadline6258 и
LocalPurge240.077s/Timeout; оба теперь PASS. У остальных 17 terminal semantic
output lines совпали после исключения QUEUE_ADMISSION scheduling observations,
добавленных PURGE_PHASE и elapsed_ms scalar stamps (у двух V5_CASE7).
Набор paths216 прежний; отличаются ровно три заранее рассмотренных source:
Reader 2bf35e4… → 50622e2…; IntegrationTU249f4a… → fc85c594…;
TreeTests9a47bb… → 1d3bb24…. CMake/production deadlines не изменены.
Это НЕ однострочный A/B performance experiment и не доказательство причины
прежнего timeout либо гарантии его устранения при другой нагрузке.

SHA256 сохранённых Native24 evidence:
result.json `9db3165e66edf38f14fdda57700437bda6bae40f20b372835eeb75c2e1c594b8`;
result.xml `9b12e236bb68bbd6bde329c4355467850061d57a6b071a2cc35bd14d25fbdb8e`;
actual-test.log `5017a66f7be0b2b925493dd633e624798bcb9181956ff5f5f4d232610e0450e6`.

Итог: **scoped saved runtime GO Native24 19/19**, несоответствий, блокирующих этот
вывод, не найдено. Не T116/full-product/release/design-P2 GO и не timeout
root-cause. Следующее действие reviewer — дождаться точного P2 mixed-mode
проекта для отдельного review; никакая реализация сейчас не начиналась.

## Append461 — requirements и scoped analyze WAV-ready

Дата: 2026-10-19. **Scoped design GO, CRITICAL=0/HIGH=0** для последнего
раздела plan «T116 / P2 — готовый WAV перед началом AAC», research461 и
quickstart461. Применён `speckit-analyze` к требованиям, не к будущему diff.
High-risk-product сохранён; product clarify Session2026-10-16 актуален:
новых решений о владельце, политике, схеме или полномочиях здесь нет.
Независимый gate разрешает предусмотренный tests-first этап, не подтверждает
source correctness. Native24 повторно не проверялся.

### Шесть новых критериев: основания

| Критерий | Поддерживающие требования и граница допуска |
| --- | --- |
| CHK029 | plan:2634–2639: BOTH-valid package, selected finalizing, previous capturing допустим; только live canonical/bound manifest; exact inventories; прежняя session/privacy/time/history validation. Flush не ACK и не proof. |
| CHK030 | plan:2641–2649: private internal unused/completed/wavReady вместо bool; каждая попытка fresh, отказавшие leases освобождены; canonical/media readonly, остальные нужные роли writable с начала acquisition; root/package/role удерживаются непрерывно; нет upgrade/proof transfer. Preheld writable bound metadata допускает лишь прежнюю inventory-проверку, не новый packed write capability. |
| CHK031 | plan:2650–2663: SAME opened content HANDLE/context, BOTH authenticated closure; private strict media extent под тем же Guard, actual EOF=selected committedExtent; ordinary/retained verify не меняется. Полное exact44+frames*320 сравнение через SAME writeWav converter, не header/hash-only и не второй converter; EOF/cancel/sticky до AAC. Canonical partial logical tail сохраняется. |
| CHK032 | plan:2664–2674: WAV не записывается, sealAudio(media,false) получает actual hash/ref; existing AAC только в unused playback; old canonical/WAV/role IDs и queue/original owner неизменны. Первый AAC container не выдаётся за ранее durable identity. Existing recovery/manifest/final sealedDegraded ACK и full AAC inspection обязательны; normal/upload/claim authority не появляется. |
| CHK033 | plan:2669–2671,2681–2685; quickstart:1147–1153: шесть отказов (unknown media tail, valid wrong PCM, invalid/partial peer, started playback, started recovery, cancellation); whole-tree snapshot equality до эффектов. После возможной публикации нет retry/cleanup/partial adoption; будущие shapes не получают допуска по аналогии. |
| CHK034 | plan:2676–2687; quickstart:1138–1155: existing physical child role1/op6, exit88 после HEAD flush до readback; old-source positive RED, тот же GREEN, actual cold inspection после release, обе старые ветки/полная crash/returned-fault/native matrix. Нет увеличения deadlines/resources или новых executors; VM-generated не installed/device/hardware/release proof. |

### Согласованность и охват

Проверены spec FR-012/013/014/022, SC-005/006 и Session2026-10-16;
tasks:567–570 (T116 открыта, T117/T118 отдельно), data-model:504–677,
local-custody §§1–2,4–7,8.1/package refs и Start-owner/owned-degraded append,
packed-custody §§1–7, конституция II/III/IV/VI и platform constraints.
Guidance: действующие AGENTS/router, spec-kit-flow и product-gates; PRD local
encrypted buffer/quotas и current-product-status не превращаются в доказательство
выпуска Windows. Spec Kit before/after analyze hooks disabled, не запускались.

Охват данного анализа: 6 FR/SC оснований → существующая открытая T116;
6/6 новых критериев имеют plan + исполнимую приёмку. Unmapped scoped tasks=0,
ambiguity=0, harmful duplication=0, C=0/H=0/M=0/L=0 в предъявленном проекте.
Это не повторный общий analyze всей Feature200 или закрытие SC-005/006.
Новая задача/новый wire не требуются для частной внутренней layout-ветки.

Прежние CHK001/003/020 не сняты: plan:2631–2632 и новый checklist header
явно сохраняют их unused-ветку и ограничивают исключение новым полным proof.
Completed branch plan:2505–2558 остаётся readonly terminal preflight + один
state commit; wavReady не подменяет её и не допускает начатый AAC/recovery.
Data-model B по-прежнему определяет unused через BOTH union/inventory и
отсылает детали к plan; это не декларация, что любой начатый output разрешён.

Start-owner CHK001–010 актуальны: marker/confirmed-vs-signed-out-vs-unknown,
fresh exact reservation, неизменный original owner, aliases/server/delete и
retirement остаются plan:2154–2265,2376–2415 и local contract:616–639.
New media proof не даёт account/queue capability. Security CHK012–018/021,
packed-writer CHK007–012 и privacy-pause CHK007–012 сохранены: user-only native
identity/ACL, encrypted bounded worker IO, sticky/cancel, no plaintext/temp/
diagnostic content, strict BOTH metadata, pin/job/actual-drain и deletion intent.
Owned-degraded display/local open по CHK023–028 не становится разрешённым по
одному WAV-ready scalar или успешной конверсии; прежние fresh native guards
и полный sealed proof остаются обязательными.

### Checklist totals и предел повторной проверки

Перечитаны все критерии 12 актуальных тематических checklist (не только новые6).
После review: cold-prefix-recovery34/0; start-owner-recovery10/0; security27/0;
packed-writer12/0; privacy-pause12/0; requirements22/0; audio-capture24/0;
advanced-routing14/0; ux25/0; calendar-launcher5/0; calendar-operation8/0;
calendar-wire5/0. Итого **198 checked / 0 unchecked** в 12 файлах.
Для не затронутых WAV-ready критериев проверена актуальность границы/отсутствие
конфликта append461, не заново вся реализация/календарь/UX или старая приёмка.
Другие 19 checkbox-файлов — прежние исторические source/gate review:266/0,
markers неизменны; их старые PASS не переиспользованы как proof нового кода.
Инвентарный итог 31 checkbox-файла:464/0 (до review458/6).
Новые checklist не создавались. Меняются только шесть markers и reviewer notes
в cold-prefix-recovery.md; остальной каталог не редактируется.

### Точная нормативная база

| Файл | SHA-256 |
| --- | --- |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| spec.md | `0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11` |
| plan.md | `f7c3c22ce75de9bf4b4c1977a03d03db9e13de12915926fdb4a2cc69379bb1d0` |
| research.md | `c38ac056c847fc4dd88f2a8387618505c79d6fae287f6d9e65333217ac1c2e5a` |
| quickstart.md | `537d4c7d0ced03529449cb1afe744d7f22f6c3bb96c70a2f8a13c7d3463e5c14` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| data-model.md | `6023a5095e3c6726fd5a885c4cf46c573dd8acc31235e0eb2d914460c33f8214` |
| local-custody contract | `a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490` |
| packed-custody contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |

### Отдельный внешний test-harness scope

**Source GO только однострочному расширению ValidateSet** в external
validate-v5.ps1: добавлен existing V5LocalRecordingWriterTests. Diff против
validate.ps1 проверен: ровно эта строка; target default/Debug default,
configuration/build/exe/ctest, guards216 pre/post, PE guard, owned/terminal/exit
и metadata flags не изменены. SHA-256
`b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a`.
native_metadata_probes=false для V5 означает отсутствие endpoint/AAC readiness
probes, не отсутствие native filesystem/DPAPI/MF IO. Этот source GO не означает
выполненный запуск, отсутствие skips или успех нового CLI; это проверяется
отдельными frozen source/PE/receipt/full-log доказательствами последовательно.

### Следующие условия и сохранённая история

Прежний **NO-GO** feasibility (выше, строки1047–1117) не стёрт: тогда ещё не
было предъявлено конструкции mixed acquisition/strict extent/full PCM compare.
Append461 задаёт эти обязательства, но не доказывает их реализацию. Сначала
tests-first physical RED на старом коде; до production GREEN — шесть refusal
fixtures; затем actual source-diff review (same-Guard/same-converter/lifetime/
cancel/sticky), тот же positive и полная предусмотренная matrix с source/PE.
Никакой допускаемый здесь проход не доказывает причину прежнего timeout,
произвольный P2 recovery, T116/T117/T118/T119/T120, установленный продукт или
внешний релиз. Код, VM, процессы, GitHub, tasks и нормативы reviewer не менял.

Контроль после reviewer edits: из 434 файлов собственного снимка изменился
только cold-prefix-recovery.md; все216 apps/windows, нормативные документы,
guidance, feature pointer, hooks и остальные checklists побайтово прежние.
Собственный отчёт дополнен этим разделом отдельно от снимка. Checklist после
правки перечитан целиком; git diff --check для двух разрешённых файлов PASS.

## WAV27 — окончательный actual SOURCE review перед native GREEN

**Scoped SOURCE GO; C=0, H=0.** Проверен именно frozen `wav27-candidate`,
не новый requirements gate и не повтор Native24. Source216 manifest SHA-256:
`957a9f548eb9d15a87ae81e3a0c5111b3f1473b3d50db2cab521281d588678d3`.
Все216 host inputs совпали с manifest; все предъявленные frozen copies также.
Имена216 совпадают с prior, prior.sha256 побайтово равен wav25-red/source.sha256;
changed.json точно описывает восемь различий: семь production files и V5tests.
Все семь before-production copies из wav25-before.16MORl совпали с prior.
V5tests SHA `dacbd886384bea9e4e0035920fcfc3d8076b7208065730a55086490e3be3ea54`.
От просмотренного wav26 отличаются только два harmless `(void)reservation`
в `ProtectedCustodyMetadata.cpp:1081,1141`, внутри `#ifndef _WIN32`;
возврат unsupportedPlatform и Windows-поведение не меняются.

### Проверенные существенные границы

- `ProtectedCustodyMetadata.cpp:1644–1765`, header:70,452: private acquisition
  enum unused/completed/wavReady не является доказательством содержания.
  `V5LocalRecordingWriter.cpp:165–170` делает свежие попытки только после
  recoveryRequired; отказавшие local package/proofs уничтожаются, не передаются.
  Canonical/media в mixed acquisition readonly, metadata и unused outputs
  получают writeExisting сразу, без повышения прав readonly capabilities.
  BOTH package slots проверяются; только live canonical и bound manifest;
  точный inventory canon/media, playback/recovery строго id-only. Неизвестные
  и уже начатые outputs не принимаются и не перезаписываются.
- `ProtectedCustodyFiles.cpp:716–721`: writable-исключение exact inventory
  относится только к metadata с проверкой роли manifest/recovery. Оно не
  допускает writable packed media/canonical и не создаёт write authority.
  Packed owner сохраняет role/root leases; media discovery использует тот же
  удержанный HANDLE, не pathname reopen или прежнее inspector proof.
- `ProtectedPackedCustodyTree.cpp:88–159`: обе HEAD и обе полные closures,
  selected committedExtent == physical EOF, финальная native проверка и
  конструирование proof под одним Guard. Несоответствие sticky-reject.
  Private exactExtent включён только WAV-ready (`V5...cpp:220–223`);
  публичные verify/verifyRetained используют прежний default=false.
- `V5LocalRecordingWriter.cpp:358–436`: тот же writeWav header и единственный
  canonical→PCM converter. Сравниваются все44 header bytes и frameCount*320
  PCM bytes; input1920 переиспользуется только после вычисления целого PCM320,
  поэтому сравнение не затирает ещё нужные canonical samples. Нового converter,
  незачтённого audio buffer и временного plaintext файла нет.
  Затем media Read(1) требует EOF/S_FALSE/got0, canonical Read(0) проверяет
  sticky fault/cancel, сохраняя разрешённый неполный logical canonical tail.
  Reader:137,168 сохраняет проверки перед chunk/copy и перед cursor/got,
  включая zero/EOF. sealAudio(media,false) не checkpoint/write media.
- `V5...cpp:234–237,700–741`: WAV-ready уже finalizing, поэтому до полного
  сравнения нет commitState; canonical/media sealing здесь readonly hash/ref.
  Только после этого existing writePlayback:445 создаёт AAC в unused role,
  затем прежние manifest/recovery/final sealedDegraded и полный inspector.
  Saved-normal/keepable/upload claim не появляется. Ошибка не ведёт к retry
  на том же writer или очистке возможной публикации. RAII readers/leases,
  charged buffers, исключения и существующие4-job/32-pin ограничения сохранены;
  job acquisition отпускается до nested Pair/packed IO (:1692). Runtime peak,
  drain и native fault acceptance этим статическим review не доказываются.
- Соседние callers проверены: openUnfinished только три private вызова V5;
  writeWav только finalize и retainPrefix; normal writer имеет пустой media
  snapshot и сохраняет write branch. completed enum проверяется в прежнем
  completeUnfinished (`LocalRecordingPackage.cpp:617`) и metadata completion;
  unused/completed права, public Tree default и wire format не расширены.

### Tests-first и фальсифицируемость

Прежний two-file tests-first diff принят SOURCE: отдельный WIN32 CTest
ProtectedRecoveryWav/--cold-recovery-wav, serial180; реальные child physical
role1/op6, обязательные wait/exit88, не новый product test knob. Assertions
активны независимо от NDEBUG. Сохранённый RED result.json имеет SHA
`b43afd4273b08d5cb55fc90b5569bffe2cf54f042dac27bb779be2996635e5a2`,
build0/test_exit8/executed1/post216/owned0; prior manifest75a361… и PE032b9038….
Прежнее чтение XML/full log:5.46606s, assertion frozen V5tests:329 на ожидаемом
positive continuation, не timeout. Child exit88 следует из обязательного
guarded parent flow; отдельный child stdout marker в parent log не наблюдался.

В actual test diff helper CreateProcess вынесен без изменения60s/10s guard.
Positive:347–376 требует degraded semantic result, неизменные WAV/canonical/
IDs/queue, release прежних owners и fresh cold inspect/decode с неизменным disk.
Filtered continued==1 и full matrix continued==3 исключают пустой проход.
Семь refusals:385–418 добавлены до GREEN: unknown media EOF tail; genuine
encrypted/header-valid32044-byte WAV с неверным zero PCM; bad/partial HEAD;
actual physical playback birth и recovery before-index; cancellation.
Каждый требует отказ, неизменный whole disk и возврат owned-memory к idle.
Wrong-PCM fixture:242–255 не подменяет этот случай ошибкой ciphertext/header.
Их успешное выполнение пока НЕ утверждается: RED останавливался на positive.

Неблокирующее замечание сохранено: test:383 печатает cases=events.size(), то
есть размер baseline trace (24), а не число filtered executed cuts (1).
Assertions не ослаблены, ложного PASS это не создаёт; такую строку нельзя
выдавать за runtime проверку24 cuts в filtered CLI.

Разрешён следующий scoped native GREEN на этом exact snapshot: positive+7
refusals и ранее согласованные полные crash/returned-fault/completed/native
регрессии с exact source/PE/terminal/owned evidence. Это **не runtime GO**,
не объяснение прежнего timeout, не full T116 или application/release acceptance.
Прежние NO-GO и ограничения отчёта сохранены. Reviewer не запускал VM, builds,
tests или процессы продукта и не менял code/norms/checklists/tasks/GitHub.

### WAV28-header — точечный actual SOURCE GO после BUILD failure WAV27

GO только для повторной scoped проверки с исправленным test source; C/H=0.
Manifest216 SHA `66062f8d3f25abae470f0014871003ad932be5b2520e3f43cfd0b07a5edec8d7`;
test SHA `936af1b85c21b81e3a66aedfc4fc52e8f9c2b9a7ce25cf646447c2d817c19bb0`.
Все216 host inputs совпали с manifest; frozen test совпал; prior побайтово
равен wav27/source; changed.json и actual manifest delta содержат только V5tests.
Actual diff ровно две правки: include ProtectedPackedCustodyTree.h (:6)
и замена строки fprintf (:384). Header содержит полное определение класса
и logicalBytes() (:29,40), необходимое для wrong-PCM fixture; утверждения,
fixtures, порядок, deadlines и production не меняются. Формат %zu соответствует
обоим size_t аргументам; trace_events показывает размер baseline trace,
executed_cuts —1 для filtered либо events.size() для full loop. Условное1
подкреплено обязательным continued==1 непосредственно перед выводом, не
заменяет assertion и не означает подсчитанное частичное выполнение при отказе.
Прежнее замечание о двусмысленном cases закрыто в source этого snapshot.

История WAV27 сохранена: saved result.json показывает terminal=true/build1,
failure=BUILD/owned_processes0; build.log содержит MSVC C2027/C2039 test:252
на incomplete ProtectedPackedCustodyTree при вызове logicalBytes. Тесты не
выполнены; предыдущий SOURCE GO не доказывал компиляцию и не является runtime
PASS. Отсутствующий include был пропущен source review и теперь явно исправлен.
Новый BUILD/GREEN требует отдельного terminal receipt на WAV28 source/PE;
reviewer ничего не запускал и дописал только собственный отчёт.

### WAV28 — независимая квалификация завершённого scoped runtime

**Scoped runtime evidence GO** для ProtectedRecoveryWav на manifest216
`66062f8d3f25abae470f0014871003ad932be5b2520e3f43cfd0b07a5edec8d7`.
Независимо полностью прочитаны saved actual-test.log, JUnit, receipt,
test.log/build.log и frozen validate-input.ps1; никаких запусков reviewer.
Manifest rehash совпал с receipt; все216 host inputs и доступные frozen
copies совпали с manifest. Frozen harness SHA
`b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a`.

- Receipt: terminal=true, Debug, target=V5LocalRecordingWriterTests,
  test_pattern=ProtectedRecoveryWav, build0/test_exit0/executed1/postflight216,
  owned_processes0, нет failure. Build log заканчивается Debug exe; full log
  запускает именно этот exe с --cold-recovery-wav. Harness использует anchored
  CTest regex, проверяет216 inputs до/после, PE hash до/после и owned processes.
- PE по сохранённому receipt:
  `e3de582d3eec443970e16cc33eceb04168dc311edf000eb727811791a6cb6c15`,
  6951424 bytes. При failure PE_CHANGED harness не смог бы дать этот terminal
  без failure. Это проверка saved guard/receipt, не новый hash guest binary
  reviewer: отдельный PE-файл здесь не предоставлен, VM не опрашивалась.
- JUnit: ровно1 testcase ProtectedRecoveryWav, status=run,21.8085s,
  failures0/disabled0/skipped0; failure/error/skipped nodes отсутствуют.
  Suite time=21 усечён до целых, не расхождение с testcase21.8085/test.log21.81.
  JUnit system-out штатно обрезан1024bytes; им не подменён полный actual log.
- Full log: trace ordinal1..24; единственный executed cut ordinal7 role1/op6,
  child_exit88/waited1/continued1/wav_ready1/canonical_queue_unchanged1.
  Summary trace_events24/executed_cuts1/sealed_cold_decode0/continued1 согласован
  с filtered CLI. sealed_cold_decode0 здесь ожидаем: fresh degraded cold
  inspect/decode для WAV-ready отдельно обязателен assertion test:366–376.
- Ровно по одному refusal case0..6: errors13,7,7,7,13,13,6;
  последний native000003e3 (cancel). После них complete marker cases7,
  unknown_tail1/valid_wrong_pcm1/invalid_partial_peer2/started_outputs2/
  cancelled1/unchanged_disk1. Все per-case whole-disk/idle assertions стоят
  до следующего case/final marker; actual log завершён Test Passed/End testing.
  Пропусков, failing expectations или противоречий receipt/log/XML не найдено.

Контрольные SHA saved evidence: result.json
`863fa41516444da2e941ce32378b162decf76762d467ace1ec4e0a6d7a2f0df4`;
result.xml `f8fba628ebc59c65f640490f15dd5325b9aa0ac7a18885615ac08787549fd4b5`;
actual-test.log `83af5106d2c50863861bc46e22d67d7b165d6cbeaeddcf239f74b9c7acc92816`.

Acceptance boundary: это1 filtered positive+7 refusals, НЕ24 physical cuts,
НЕ полный normal/unused/completed/returned-fault regression. Заявленный WAV29
с прежними deadlines и source216 — уместный следующий gate: default V5 main
вызывает full coldRecoveryCrashCuts и обычный writer flow, отдельные completion
и returned-fault CLI выполняют собственные ветки. Их результат пока не принят.
WAV27 BUILD failure сохранён; WAV28 GREEN его не стирает. Device audio/network/
installed=false; native filesystem/DPAPI/MF IO присутствуют. Нет вывода о причине
старого timeout, полном T116, установленном приложении или релизе. Другие файлы,
live WAV29, нормативы/tasks/checklists/VM/GitHub reviewer не менял и не трогал.

### WAV29 live RED — op5/op6: нормативное ожидание и проверяемое состояние

Независимо прочитан только разрешённый snapshot хвоста UTF16 test.log
wav29-regression, пока suite ещё live. Default V5 Failed52.38s, cuts1..5
завершены; далее assertion test:356 started_outputs_must_not_be_repaired_or_
overwritten. Следующий ordinal по trace —6 role1/op5. Завершающего cut6 marker
нет, потому что assertion стоит раньше него. Это не terminal qualification
suite и не PASS оставшихся completion/returned-fault; reviewer их не опрашивал.

**Вывод: подтверждён mismatch узкого ожидания теста с shape-based admission;
production bug этим RED не доказан.** Test:313 определяет wavReady только op6,
test:347 проверяет success только для него/completed, а :355–356 требует отказа
любого другого started shape. Поэтому успешный fresh recovery на op5 попадает
в ошибочно безусловный refusal branch. Это не timeout и не пропущенный guard.

Точная причинная цепочка: test wrapper:118–123 вызывает op5 ПОСЛЕ успешного
WriteFile HEAD (offset128/16512,count16384; hook допускает положительный done,
не отдельно доказывает done==count). op6:128–131 только после FlushFileBuffers.
ProtectedCustodyFiles.cpp:1800–1808 делает HEAD transfer → flush → checks;
Tree.cpp:383–411 предварительно flush/validate DATA, затем publish HEAD и
независимый readback ACK. TerminateProcess88 на op5 не выполняет последующий
flush/readback и не доказывает старый checkpoint ACK. Но он не моделирует
исчезновение OS cache/питания: наблюдаемый позже HEAD уже может быть полным.
На диске нет отдельного маркера «этот HEAD успешно прошёл FlushFileBuffers»;
одинаковые валидные bytes/closures/extent не раскрывают историю op5 либо op6.
Побайтовая идентичность двух конкретных cut trees этим чтением НЕ установлена;
наблюдаемый recovered.ok и прежний actual source flow доказывают только
прохождение текущего fresh proof, не power-loss durability.

Нормативное внутреннее противоречие локализовано: plan461:2633–2638 задаёт
точную допустимую структуру и прямо запрещает считать WAV готовым по flush;
п.2–4 требует BOTH closures/strict EOF/full PCM/cancel перед эффектом.
Однако acceptance:2675–2685 и quickstart:1151–1154 говорят изменить только одну
доказанную WAV точку, оставляя blanket отказ для op5. Требование исторического
op6 не может быть восстановлено из разрешённого durable format и противоречит
shape predicate. Это ограниченный пробел полноты acceptance, пропущенный
предыдущими requirements/source reviews; C/H0 не следует молча переносить
на исправленную формулировку. Прежний SOURCE GO/WAV28 runtime сохранены в
своих границах, WAV29 RED не стирается.

Безопасное узкое исправление ПЕРЕД следующим freeze/run:
1. Отдельно явно согласовать нормативное уточнение: op6 остаётся обязательным
   tests-first positive, а op5 — additional process-crash boundary, допускаемая
   лишь при том же полном fresh WAV-ready proof. Никакого допуска по одному
   событию WriteFile, repair/flush существующего WAV или нового persistence flag.
2. Разделить в тесте выбранный filtered op6 cut и shape-eligible op5/op6.
   Успешный op5 обязан пройти ВСЕ те же positive assertions: degraded-only,
   WAV/canonical/IDs/queue equality, fresh cold decode/history, exact memory.
   Для контролируемого полного HEAD fixture предусмотреть отдельное явное
   positive ожидание, а не удалить started-refusal assertion. Если op5 способен
   породить partial HEAD, refusal допустим только с доказанным неготовым shape
   и whole-tree equality; голое «success или refusal оба PASS» не принимается.
   Тогда учесть дополнительный cut в full continued counter (4 при полном op5),
   но filtered op6 оставить1; не расширять blanket acceptance прочих cuts.
3. Сохранить семь refusals, отказ started playback/recovery/unknown tail,
   sticky/returned-fault rules текущего owner, сроки и все guards. Не переносить
   op5 cold reconciliation на retry того же ambiguous writer/ACK/power-loss.
   После actual narrow diff — source review и новые frozen full regressions.

NO-GO для молчаливой смены expectation/общей приёмки WAV29; production patch
по этому факту не обоснован. Нормы, checklist markers, tests и product code
reviewer не менял; только этот append. Остальные runtime результаты main
продолжает собирать последовательно, без вмешательства reviewer.

### WAV29 terminal — GO узкому подходу коррекции expectation, до edits

Main сообщил terminal exit1/build0/executed3/post216/owned0: default Failed
52.3849s на cut6/op5, returned faults PASS55.7419s/26, completion PASS19.8514s/5.
Это сообщение зафиксировано отдельно от прежнего самостоятельно прочитанного
live tail; финальные receipt/XML двух последних CLI в этом append не
квалифицируются и не превращаются в общий PASS WAV29.

**GO предложенному подходу**, не ещё отсутствующему actual diff/runtime:
test-only wavReady=role1&&(op5||op6), filtered selector явно только role1/op6,
full continued==4, filtered continued==1. Оба WAV-positive обязаны проходить
прежние неизменные WAV/canonical/IDs/queue hash, fresh cold inspection/AAC/history,
degraded-only/no normal/no keepable и resource assertions. Это строгое ожидание
успеха controlled fixture, НЕ «refusal или success оба PASS». При partial write
оно должно упасть, а не обойти proof или автоматически принять неполный HEAD.
Общий отказ для других started shapes и все семь refusal fixtures сохраняются.
Source comment должен различать process crash/power loss и явно исключать
доказательство старого flush/checkpoint ACK; production и deadlines неизменны.

Append plan/research/quickstart допустим как явное уточнение прежнего matrix
expectation: старое «только одна точка» относилось к выбранному tests-first op6,
полная matrix теперь обязана проверить обе shape-eligible op5/op6, каждая через
тот же fresh full proof. Противоречие и WAV29 RED сохраняются, не объявляются
несуществовавшими; это не новый формат/authority/contract/task или общий repair.
Сам append меняет формулировку acceptance и требует отдельной узкой проверки
actual text вместе с test diff до нового freeze/run; прежний C/H0 автоматически
не переносится. Новых checklist или повторного полного нормативного обхода не
требуется при неизменных остальных входах. Reviewer одобрил только этот подход,
дописал свой отчёт; код/нормативы/checklist markers/VM/GitHub не менял.

### WAV29 clarification — actual requirements / scoped analyze GO

**GO требованиям перед test-only edits; C0/H0/M0/L0 в этом узком delta.**
Прочитаны именно обновлённые final plan461/research461/quickstart461 и весь
cold-prefix checklist. Метки CHK029–034 сохранены supported6/0; общий итог34/0.
Добавлена только reviewer note, никаких новых критериев/checklists/tasks.

Нормативная привязка:
- CHK029/030: прежняя exact shape, BOTH valid/selected finalizing, bound history,
  unused playback/recovery и fresh mixed leases неизменны. Исторический номер
  cut/flush не становится authority и не допускает readonly upgrade.
- CHK031/032: same-Guard EOF, BOTH closure, full same-converter PCM, cancel/
  sticky до эффекта, WAV/canonical/IDs/queue/owner equality, AAC onlyunused,
  final degraded/full inspector и no normal/upload сохраняются для обеих точек.
- CHK033/034:7 отказов неизменны; полный native HEAD transfer в wrapper теперь
  обязателен, full24/continued4, filteredop6 executed1/continued1. Нет «успех
  или отказ оба PASS», новых флагов, repair/flush старого WAV, retry failed owner,
  новых limits или deadlines. Power-loss и исторический checkpoint ACK явно
  отделены от process-crash fresh proof. WAV29 RED обязателен к сохранению.

Противоречие прежнего acceptance «только одна точка» устранено actual текстом:
tests-first выбор остаётся op6, full matrix явно включает controlled op5.
По FR-012/013/022 и SC-005/006 (5 scoped requirement anchors) покрытие
сохраняет существующий T116,5/5 mapped, новых unmapped tasks0; это не процент
готовности требований/всей фичи и не закрытие SC-005100циклов/T118. Конституция
IV/VI, Start-owner, local/packed contracts и data-model не изменены; task T116
остаётся [ ]. Требования к verified ACK в живом owner не заменены cold proof.

Проверены SHA: plan
`a0d91095f5e9f2b3391e760a7cd792e1070d7d7dbccbc981408704829cf82823`;
research `15902c70efd503bac858761206e51f2999b005205a444ae32f705fdabf471b67`;
quickstart `5fa936341776178cc67d1d33a48eb3575ada1ee741ec64ba75b1f78ed35f242f`.
Constitution/spec/tasks/data-model/оба contracts совпали с прежними SHA,
все216 source inputs остаются WAV28 manifest66062f8d… без различий.
Feature pointer/prerequisite подтверждают F200/high-risk-product. Локальный
prerequisite не поддерживает указанный в skill --require-spec: после help
использован поддерживаемый --json --require-tasks --include-tasks (успешно),
spec проверен чтением/хешем отдельно. before/after_analyze hooks disabled.

Анализ read-only, его запись и reviewer note выполнены отдельно по явному
разрешению. Следующий gate — actual минимальный test diff (включая full HEAD
transfer assertion, selector и counters), затем frozen regression, не уже
выданный runtime GO. Norm/code/tasks/VM/GitHub не менялись reviewer.

### WAV30-full-head — exact test-only SOURCE GO перед запуском

**GO; C0/H0**, только actual diff frozen WAV28 test → current/frozen WAV30.
Manifest216 SHA `c902038944f4bbf13dda2a36a17a486db0c10fea47170ff68a99202e3d666c17`;
V5tests SHA `94e74a5ac75bdda5bfaa6bb4ab22910fd40cfc669fc8e6dcac3678cadf6f47e6`.
Все216 host hashes совпали; frozen test совпал; prior точно равен WAV29
source.sha256 (и по содержимому WAV28). changed.json/manifest delta содержат
только V5LocalRecordingWriterTests.cpp, остальные215 inputs неизменны.

Actual diff содержит только согласованные три hunks:
- :123–125 assert(*done==count) после успешного native HEAD WriteFile и до
  op5 event. Внешний guard гарантирует done!=nullptr/positive transfer;
  assertion активен (#undef NDEBUG перед cassert). Short positive transfer
  вызывает failure до события, а zero/failed write не имитирует достигнутый
  cut: прежний обязательный child wait/exit88 исключает случайный PASS.
- :316–321 комментарий no old flush/checkpoint ACK/no power-loss claim;
  wavReady только role1/op5 либо op6. Filtered selector дополнительно требует
  op6, поэтому новый eligible op5 не удваивает tests-first CLI.
- :389 full continued==4 вместо3; filtered продолжает требовать1.

Неизменные :354–384 применяют полный strict positive path к ОБОИМ WAV cuts:
обязательный recovered.ok, degraded semantic/trusted1000ms, no normal/keepable,
WAV hash/canonical/IDs/queue equality, release и fresh cold inspect/AAC/history,
readonly disk equality/idle memory. Нет «оба исхода PASS». Остальной started
refusal branch,7 fixtures, job4/pin32 проверки, physical cuts, child60s/10s,
CMake deadlines и production не изменены. Блокирующих findings нет.
Новый source не запускался reviewer; GO разрешает только согласованный frozen
run, а не утверждает compile/runtime PASS или исправление прежнего timeout.
WAV27 BUILD/WAV29 RED сохранены. Norm/checklist rereview не повторялся;
изменён только собственный отчёт, никаких VM/tests/builds/GitHub действий.

### WAV30 — независимый scoped runtime GO,4/4

Независимо полностью прочитаны saved receipt, JUnit, actual-test.log,
build.log/test.log и frozen harness в wav30-full-head. **Scoped evidence GO**,
несоответствий/skip/failing expectations в этих четырёх запусках не найдено.
Receipt terminal=true/build0/test_exit0/executed4/postflight216/owned_processes0,
configuration Debug, target V5LocalRecordingWriterTests, без failure. XML
ровно4 нужных testcase/status=run, failures0/disabled0/skipped0, нет error/
failure/skipped nodes. Exact CLI в полном журнале:

| CTest | CLI | Время JUnit,с |
|---|---|---:|
| V5LocalRecordingWriterTests | default,без аргументов |128.274|
| ProtectedRecoveryReturnedFaults | --cold-recovery-returned-faults |46.6268|
| ProtectedRecoveryCompletion | --cold-recovery-completion |17.7776|
| ProtectedRecoveryWav | --cold-recovery-wav |20.0178|

Source216 manifest rehash
`c902038944f4bbf13dda2a36a17a486db0c10fea47170ff68a99202e3d666c17`
совпадает с receipt; все216 current host inputs и доступные frozen copies
совпали. Harness SHA b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a
неизменён: anchored regex,216 pre/post source checks, PE pre/post hash,
owned guard. PE receipt
`e9393e7373ee54ad4982bdb91577ba3e7b2d382380a5739c7dc5ebf777cc21e8`,
6951424 bytes; PE_CHANGED/failure отсутствуют. Это квалификация saved guard/
receipt, не независимый rehash guest EXE: бинарник отдельно не предоставлен,
VM не опрашивалась. Build и все4 Commands относятся к одному Debug exe.

Default full log содержит ВСЕ24 COLD_RECOVERY_CUT ordinal1..24 подряд, каждый
child_exit88/waited1/canonical_queue_unchanged1. continued1 ровно6,7,22,23;
wav_ready1 только6/op5 и7/op6. Summary trace_events24/executed_cuts24/
sealed_cold_decode1/continued4. Дальше normal writer assertions достигнуты:
PROTECTED_PLAYBACK held_jobs0/2 обаok1, frames48128, затем Test Passed.
Прежние playable positives3/refusals15 и prefix capturing/finalizing/refusals9/
sealed_phases3 также достигли полных markers.

Returned faults:26 отдельных hit1/rejected1, включая late-seal и cancel,
финал exact_memory1/canonical_ids_queue_unchanged1/late_seal_cold_decode1.
Completion:2 accepted positives и refusal cases1,2,3, итог cases5, generation
plus_one/five_members_ids_queue_unchanged/cold_aac_open_closed_history/exact_memory1.
Filtered WAV: только cut7/op6, executed1/continued1, затем ровно refusal0..6
и итог7/unchanged_disk1. Четыре Test Passed и End testing. JUnit output местами
обрезан1024bytes, эти результаты подтверждены полным actual log, не обрезкой.

SHA saved receipt `7db216aa116793e6bbe134a17a74fd9802b167b143f08d80a34da53c9e0b0a18`;
XML `df098a7f2896ccab514da74e12a81c49ab883df19148e13d2ebbb007d013ef23`;
full log `d0d26a029890cd120981de0d86e7fce1aad7f14ce280fd2d1aa523cbf6852d76`.
WAV27 BUILD failure/WAV29 RED сохранены, не переименованы в PASS.
Tree31/Files32/Native33 — отдельные ещё не квалифицированные affected gates;
reviewer их каталоги/live sessions не читал. No device audio/network/install;
filesystem/DPAPI/MF IO реальные. Нет full T116/goal/power-loss/hardware/release
acceptance или вывода о старом timeout. Изменён только этот отчёт, запусков нет.

### WAV31-tree / WAV32-files — независимая terminal qualification

**Scoped runtime evidence GO обоим existing default CLI**, не Native33/T116.
Полностью прочитаны receipt/JUnit/actual-test.log/build.log/test.log только
wav31-tree и wav32-files. Оба Debug, terminal=true/build0/test_exit0/executed1/
postflight216/owned_processes0, без failure; XML ровно соответствующее имя,
status=run, failures0/disabled0/skipped0, нет failure/error/skipped nodes.
Commands — соответствующий Debug exe БЕЗ аргументов; build logs подтверждают
те же target/path, full logs завершаются Test Passed/End testing.

| Stage / testcase | Actual JUnit,с | PE SHA-256 | Bytes |
|---|---:|---|---:|
| wav31-tree / ProtectedPackedCustodyTreeTests |34.6433|52034700f870c96a5f9ae1192f077cf412245d6e76c59a68461d013ed84bce29|7031296|
| wav32-files / ProtectedCustodyFilesTests |372.329|33ae2b6fe7a33881e9e973d35728a73b486253489cd022285de3ec1c074b5009|8444928|

Files время взято из XML372.329 (CTest372.33), не ранняя опечатка main372.334.
Оба manifest216 побайтово равны WAV30, rehash
`c902038944f4bbf13dda2a36a17a486db0c10fea47170ff68a99202e3d666c17`;
все216 current host inputs совпали. Frozen harness в обоих имеет прежний SHA
b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a,
сохранены216 pre/post/PE pre-post/owned guards. PE квалифицирован по receipt
и unchanged harness, не посредством нового чтения guest EXE reviewer.

Tree: reader-cache charge16/observed16; полный READER_RELEASE_DRAIN с cloned,
addref_unchanged,cancelled_still_live,external/all/owner/pins/memory_released1.
Files: readonly cases0..4 и owner cases0..3 с no_writes/released1;
bootstrap intent native-ID обеих subjects, allocation/cancel/migration markers,
AAC valid/damaged/30s,46 normal v5 cases и23 degraded cases (0..22), финал
owned_before16/owned_after16. Expected negative accepted0/native errors не
являются case failures; тест закончил все assertions. Files JUnit system-out
обрезан1024bytes, поэтому эти marker conclusions взяты из полного actual log.

SHA evidence (receipt/XML/full log): Tree
`5364f82cb68cbc4fbdc87eba11608fb810d2d173082c5cbd9f0798223fa3b548` /
`523cfe91e2a453bd9641ae45bb35449feb294293fdf76fd2fed2610cfe9f7d6c` /
`cadf496523f30c46ff6db71fea7ef43a2aa1eaf73ce647e19b66505928cae4b6`;
Files `0cd5182d22e49a243f06588bc625e0a915595e9e151f7ab001542bf14afe225b` /
`5a0bc3f468d64befeee08337c815915da12af579b9f1c3fe29a9d49e897c9475` /
`7759055e51ad398eeac966ca874ad421d78bffaafebbfd97a923e9eab226b0aa`.

Несоответствий не найдено. Native33/session79265, его каталог/журналы и любые
другие процессы не читались. Только собственный report append; без VM/builds/
tests/code/norm/tasks/checklists/GitHub действий. Прежние RED сохранены;
no audio/network/install, не full goal/T116/power-loss/release acceptance.

### WAV33-native — functional-only runtime qualification при сне хоста

**Scoped functional runtime evidence GO:13/13**, строго НЕ performance,
latency/continuous uptime/audio continuity/power-loss/hardware/full T116 GO.
Независимо прочитаны сохранённые receipt/XML/full actual-test.log/build/test
logs только wav33-native; никаких guest/build/test/GitHub действий reviewer.
Receipt terminal=true/build0/test_exit0/executed13/postflight216/owned_processes0,
configuration Debug, failure отсутствует. XML tests13/failures0/disabled0/
skipped0, все status=run; error/failure/skipped nodes отсутствуют. Full log
содержит те же13 уникальных имён в порядке JUnit, соответствующие CLI,13
Test Passed и End testing. Exact принят состав, без замены похожими тестами:

1. NativeProtectedStartOwner / --protected-start-owner
2. NativeProtectedNoLoginClaim / --protected-no-login-claim
3. NativeProtectedStartOwnerRecovery / --protected-start-owner-recovery
4. NativeProtectedStartOwnerDegradedRestart / --protected-start-owner-degraded-restart
5. NativeProtectedStartOwnerUnfinishedRestart / --protected-start-owner-unfinished-restart
6. NativeProtectedRecoveryLivePlayback / --protected-recovery-live-playback
7. NativeProtectedPrivacyFlow / --protected-privacy-flow
8. NativeProtectedPendingStart / --protected-pending-start
9. NativeProtectedPrivacyDegraded / --protected-privacy-degraded
10. NativeProtectedInspectionPreparation / --protected-inspection-prepared
11. NativeProtectedFinalizeAdmission / --protected-finalize-admission
12. NativeProtectedInspectionActiveStop / --protected-inspection-active-stop
13. NativeProtectedPlaybackConsumer / --protected-playback-consumer

Manifest216 rehash
`c902038944f4bbf13dda2a36a17a486db0c10fea47170ff68a99202e3d666c17`
равен receipt и побайтово WAV30 manifest. Все216 current host inputs совпали;
changed.json пуст. Harness прежний b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a,
с216 pre/post и PE pre/post/owned guards. Debug exe по receipt/build/Commands:
`38429c1a0b07ba10fa5eb500bd5d130d45594b5a1bf2954c9448c128496e868f`,
10091520 bytes. PE_CHANGED/failure отсутствуют; это saved receipt guard,
НЕ новый независимый rehash guest binary (VM не опрашивалась).

Functional evidence включает start-owner binding/classifications/finalize,
no-login scenarios0..5, recovery modes0..7, degraded и unfinished restart
с unchanged original owner/canonical/queue, actual recovery retirement,
deletion/purge held-read fences и cold decode, live muted playback/seek,
privacy closed/degraded/capacity, PendingStart normal+signedout V5 cases0/8
до cold_read_verified/done, cancel0..5 и submit_refused no_io/released1.
Inspection preparation/active Stop завершаются pass markers, finalizer
held_jobs0/2 keepable semantic1; playback consumer завершает generated_muted1/
UI_acceptance0. Отрицательные ожидаемые error/native значения не case failures.
Обрезанные system-out JUnit не подменяют полностью прочитанный actual log.

**Ограничение времени обязательно.** CTest total830.61s — сохранённое guest
measurement, не непрерывное host wall time. В actual log виден InspectionPreparation
13:02→14:50 при101.516s и ActiveStop14:50→14:56 при137.671s. Main сообщил
read-only pmset evidence: host sleep13:18:49 maintenance5171s,14:45:45/14:50:27
sleep и14:53:16 lid/HID wake (+0300), также UTC jump. Эти pmset строки здесь
зафиксированы как предоставленные main, не как заново выполненный reviewer
pmset check. Совпадение со sleep/suspend объяснением не доказывает точную
семантику clock accounting или отсутствие иных пауз. Никакого speed comparison,
latency/deadline/continuous-device acceptance из этих длительностей не делается.
Функциональный PASS после возобновления не означает audio continuity при сне.

SHA receipt `12c40c4b277cfcaede983acd10d2b1122265d530ac124448712e9776ce54bb3d`;
XML `0382a56c11c99d3ec8bfa8928c766d0d009bc889d09fee1ab08bea34e6a04928`;
full log `9efeab29a58ff8ea9f5746d264d874c675fe143d6d1990a42f0d623328c60452`.
Функциональных несоответствий не обнаружено. native_metadata_probes=true
относится к native metadata/readiness probes, device_audio_read/real_network/
installed=false. Это не настоящая запись устройства и не latency приёмка.
Прежние RED и sleep caveat сохранены; T116/full goal/release остаются открыты.
Изменён только собственный report, нормативы/tasks/checklists/code не тронуты.

### Partial AAC — ограниченный read-only feasibility, после Native33

Это исследование существующего T116/P2, НЕ design/source/runtime GO, не
диагноз timeout и не разрешение production patch. Native33 не пересматривался.
Текущая ветка codex/200-windows-followup, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; все216 файлов совпали с
wav30-full-head/source.sha256, manifest
`c902038944f4bbf13dda2a36a17a486db0c10fea47170ff68a99202e3d666c17`.
Применён code-reviewer; только чтение host sources/contracts, без VM/запусков.

**Причина текущего отказа — отсутствующая package construction, а не отсутствие
seek/rewrite primitive.** prepareRecovery пробует unused/completed/wavReady
(V5LocalRecordingWriter.cpp:165–170). openUnfinished разрешает BOTH refs только
live canonical + bound manifest (:1701–1711), wavReady требует playback/recovery
id-only (:1736); unusedPackageRole отказывает на любом другом child
(ProtectedCustodyFiles.cpp:702–712). completed требует уже существующую recovery
metadata pair generation1 (Metadata.cpp:1724–1733), а completeUnfinished требует
terminal degraded manifest с artifacts и recovery (:610–680). Поэтому готовый
AAC ДО этих metadata также ещё не admitted; это не тот же случай, что partial AAC.
plan.md:2505–2546/2634–2674 ограничивает принятые shapes и прямо не расширяет
writable packed reopen. Default crash matrix V5tests:334–364 сохраняет остальные
started outputs без repair. Это подтверждённый незавершённый P2, не новый regression.

**Примитивы и конкретный первый барьер интеграции.**

- ProtectedCustodyWriter::open(Tree,cancel), Writer.cpp:204–219, принимает уже
  доказанный writable current Tree; no-op setSize(current length) заново проверяет
  write capability/actual heads. Он НЕ сбрасывает длину и не повышает readonly.
- Owner::openImpl имеет standalone writeExisting, но prepared package lease
  допускает только createNew/readExisting (Files.cpp:1486–1497); discoveredContainer
  допускается только prepared readExisting (:1471–1473). Ни передать существующую
  заранее writable playback-role, ни discover её container при writeExisting
  текущий private API не позволяет. Обход standalone path не заменяет continuous
  package/root/role ownership. createWriter тоже только CREATE_NEW, с conflict
  при уже удерживаемом packed owner (Metadata.cpp:1811–1842).
- Fresh write-capable acquisition ИЗНАЧАЛЬНО, SAMEHANDLE prefix/context discovery
  и full BOTH closures, без readonly→write upgrade/release-reopen, требуют явного
  технического расширения этой construction/API; сейчас его нет. Наличие права
  GENERIC_WRITE в некоторых старых HANDLE само по себе не даёт capability.

**Разные физические состояния и предел переиспользования.**

1. Полный empty birth (обе одинаковые authenticated g1 heads) либо корректные
   соседние BOTH heads с частично committed AAC: низкоуровневая конструкция
   существует. После всех package/history/canonical/WAV proofs и budgets можно
   В ПРИНЦИПЕ открыть существующий Writer, явно setSize(0), затем переиспользовать
   MF encode с canonical, checkpoint/hash/full AAC decode/final degraded seal.
   Writer.cpp:168–179 публикует shrink через прежний Tree; Tree.cpp:193–222
   проверяет actual pair/stale/generation exhaustion; :342–343 сохраняет прежний
   committed extent при shrink0. Это логический новый derived stream, НЕ native
   truncate, не продолжение потерянного MF encoder state и не стирание старого AAC.
   writePlayback сейчас безусловно создаёт новый writer (:442–450), поэтому его
   wiring тоже потребует отдельного source review. Одного снятия guard недостаточно.
2. Uncommitted physical DATA/NODE tail при доказанной корректной паре: обычный
   verify проверяет обе достижимые closures, но НЕ требует EOF==selected extent
   (Tree.cpp:112–131). Новый append идёт после ACTUAL EOF (:286–305;
   Files.cpp:1677–1720), а не после старого committed extent. Возможна конструкция
   сохранения ВСЕХ неизвестных tail bytes на месте, без признания их authority,
   reuse/overwrite/GC; физический peak включает их + новый encode. Но текущий
   wavReady strict-extent predicate не является допуском такого playback.
   Разрешённый package predicate/retained refs/повторный crash должны быть явно
   определены и проверены до внедрения. Нельзя просто убрать strict EOF у WAV.
3. Incomplete birth, torn/invalid peer, неизвестные children или неподтверждённые
   authority/ID/history: writable Tree доказать нельзя. Contract packed §5:180–183,
   203–219 не позволяет достроить birth/reset generation/выдать surviving head за
   пару. Re-encode сам по себе не исправляет отсутствие authority. В действующей
   construction безопасного восстановления этих shapes при неизменных IDs нет.
   Новый versioned artifact/attempt с durable selection и сохранением старого
   объекта был бы отдельным явно согласуемым техническим протоколом, не готовым
   reuse; если все IDs должны остаться прежними, это также отдельное ограничение.
   Обязательность нового wire format из этого исследования НЕ доказана.
4. Готовый AAC ДО terminal metadata: сначала отдельный readonly preflight, не
   reset/re-encode. Переиспользуемы BOTH/strict physical extent, тот же WAV compare
   с canonical, hash/sealAudio(playback,false), readProtectedPlayback
   (LocalRecordingPackage.cpp:821–829) и прежний metadata/final seal. Existing
   decode проверяет фактический PCM/EOF/timestamps/длительность с прежним ±100ms
   допуском (:379–412), НЕ byte equality lossy AAC с canonical и НЕ прежний MF
   Finalize ACK. Наличие заголовка/полного DATA/успешного старого encoder не proof.
   Нужен новый точный mixed inventory/history predicate для unused recovery и
   отдельно для уже начатой metadata; completed branch его сейчас не покрывает.

**Криптография, границы эффектов и исходный владелец.** Собственного nonce/key
counter здесь НЕТ: nativeTransform вызывает DPAPI user-scope
(Primitives.cpp:55–70); Codec.cpp:47–72/107–128 связывает защищённый header с
IDs/role/offset/selector/version, entropy с domain/IDs/offset/selector.
Owner RAM epoch (Files.cpp:1479–1484) не persistent encryption nonce. Нельзя
обнулить generation, пересоздать birth поверх файла или повторно использовать
orphan offsets. HEAD alternating overwrite с новым checked generation — прежний
протокол, не новый AES/nonce lifecycle. Для корректной пары необходимость нового
формата или зависимости НЕ выявлена; необходимость явной package construction
и сохранения этих инвариантов — выявлена.

Для непустого AAC первый эффект hypothetical rewrite — setSize0/публикация HEAD;
для уже empty birth setSize0 — no-op, эффект начинается позже с encode writes.
Это не harmless preflight; все authority/history/finite canonical/WAV comparisons,
cancel/sticky/EOF, reference union и physical quota checks должны предшествовать
ему. После эффекта ошибка/ambiguous остаётся sticky с retained owners/artifacts,
без retry failed owner или cleanup. Repeated crash на reset/новом append/HEAD/
MF close/metadata/final seal нельзя исключить из будущей матрицы. Jobs4/pins32/
owned64MiB/dirty4 и старые roots сохраняются, orphan peaks не вычитаются из quota.
NativeCapture.h:2280–2299 заново проверяет текущую queue row перед prepare;
:1753–1768 оставляет исходную reservation без normal proof/queue promotion.
Именно этот маршрут остаётся reuse point, без новой owner pair/claim/upload.
После crash native owner неизбежно fresh; это не перенос RAM proof через разрыв
и не замена исходного account/workspace owner.

Итог: технически обоснована возможность derived rewrite ВНУТРИ packed v2 для
доказанной корректной BOTH пары с физическим сохранением старых bytes; это
НЕ разрешено автоматически нынешним package recovery contract. До source нужен
явный технический append про started AAC acquisition/authority/restart predicates
и проверяемые cuts. Bad birth/invalid peer и готовый AAC до metadata — отдельные
ветви, не побочные permissive fallbacks. Полный P2/T116/goal остаётся открытым;
исторические RED, отказные ожидания и ранее полученные GO не переписаны.

## Round462 — независимый requirements gate начатого AAC

2026-10-19. **NO-GO перед test-only edits; scoped analyze C0/H1/M1/L0.**
Это независимая оценка качества предъявленных требований, а не actual source
GO, запуск tests-first или приёмка T116. Предыдущая feasibility запись, NO-GO,
RED и результаты отдельных runtime проверок выше сохранены без изменений.

Рабочая копия: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Активная feature установлена чтением `.specify/feature.json`: feature200,
`specs/200-windows-desktop-app`, high-risk-product. Git не вызывался; branch/HEAD
из feature metadata не объявляются заново проверенными Git facts.
Использованы speckit-analyze и code-reviewer с явным ограничением пользователя:
нормативы/код/тесты только читать, изменять только markers/notes cold-prefix и
этот отчёт. Штатный prerequisite command не запускался: обычный get_feature_paths
имеет путь записи feature.json (check-prerequisites.sh:100–104,
common.sh:131–177,213–216), а Git и сторонние записи запрещены. Наличие spec,
plan, tasks и пути проверены чтением напрямую. before_analyze/after_analyze
hooks в extensions.yml disabled; исполнять нечего. Это scoped ручной анализ,
не утверждение о выполнении полной feature-wide команды/CI/governance.

### Выводы и минимальные поправки требований

| ID | Severity | Основания | Вывод / требуемая поправка |
|---|---|---|---|
| R462-I1 | HIGH | plan.md:2734–2737; data-model.md:683; packed contract:387–388 против того же contract:152–158 и Writer.cpp:168–178 | Безусловное следующее поколение reset противоречит same-length no-op для допущенного empty birth/empty reset. Явно разделить nonempty→0 (новое поколение) и empty→0 (прежний proof/generation, без HEAD write). Не требовать reset-HEAD cut для empty fixture; первый эффект там — последующая запись encoder. Не менять действующий Writer protocol ради этой формулировки. |
| R462-U1 | MEDIUM | plan.md:2743–2746,2756–2759; quickstart.md:1178–1183; Metadata.cpp:1881–1915; LocalRecordingPackage.cpp:539–560,610–688 | Повторные cuts перечислены, но обещанная конечная таблица physical shape→единственный outcome пока отсутствует. До тестов зафиксировать reset/append/HEAD, manifest retire/write/bind, recovery birth/commit, final seal с использованием прежних history/completed predicates; не выводить допуск из номера операции или старого flush ACK. |

R462-I1 — конкретное противоречие принятому commit contract, не предположение
о runtime ошибке. `ProtectedCustodyWriter::open(Tree)` :204–219 сначала вызывает
проверенный same-length Tree setSize, а `State::resize` :172 возвращает no-op
для 0→0. Это сохраняет capability/paired-head проверки открытия, но не создаёт
новый reset HEAD или новое поколение. Поддержка такого empty случая заявлена
plan:2756 и quickstart:1178, поэтому исключить его из анализа нельзя.

R462-U1 не объявляет существующий безопасный отказ ошибкой продукта и не
требует нового способа восстановления terminal history. Нужна точность
ожидаемых исходов, а не более разрешающий parser. Для будущей таблицы чтение
исходников даёт следующие обязательные различия:

- До смены manifest, включая valid empty reset/новый partial/сохранившийся
  orphan append: fresh BOTH/retained closures + прежняя unfinished history +
  strict canonical/WAV proof; только при всех остальных admission условиях
  разрешён новый derived encode. Broken HEAD/birth/identity — сохранённый отказ.
- При retire старого manifest ref до переиспользования metadata index
  `commitMetadata` :1881–1888 оставляет оба package slots связанными с текущей
  history. Нельзя принимать её по одному slot или придумывать старые times.
- Новая selected manifest generation при ещё старом package binding:
  `openUnfinished` :1724–1729 отказывает; откат к прежнему index/manifest ради
  продолжения запрещён. Это уже прямо сохранено в plan admission.
- Bound terminal manifest, но recovery всё ещё только id.bin: прежний
  `unfinishedHistory` :552 вызывает manifest(...,true), а parser :173 отвергает
  artifacts/degraded. Эта точка не становится playbackStarted success просто
  потому, что обе пары структурно читаются. Без отдельного нового проекта —
  отказ до записи, не возврат к older unfinished history. Эта незавершённая
  форма остаётся открытой P2, не исчезает из полного goal.
- Recovery birth/singleton/partial или invalid metadata не принимаются;
  полностью готовая recovery с terminal manifest рассматривается прежней
  completed continuation :610–688, с full content/history inspection и без
  повторного encode. Это не новый playbackStarted admission.
- После фактического sealedDegraded — прежний readonly sealed inspection,
  никакого reset. Неполная final publication требует прежних paired-state/
  phase predicates, не общего «success или refusal» для одного cut.

Это основания для требуемого уточнения норм, а не самостоятельно добавленная
норма или разрешение тестового diff. Продуктовых вопросов не выявлено: исходный
owner, Send=false, quarantine, удаление и пользовательские сценарии не меняются.
Оба замечания устранимы технической ясностью без ослабления security/authority.

### Проверенные непротиворечивые границы и source feasibility

1. Finalized immutable: local custody:174–184,502–505; plan462:2712–2719
   не допускает sealed AAC refs — только live canonical и bound manifest.
   Новый exception относится к unsealed output, не к sealed artifact или T117
   migration. Успешный старый encoder сам по себе не package authority.
   Готовый AAC ДО terminal metadata может пройти эту ветвь; AAC, связанный с
   terminal artifact history, не следует молча считать тем же admission.
   Privacy/optional times неизменны семантически; существующий manifest rollover
   не означает побайтовую неизменность metadata slots или право rollback.
2. validBoth + orphan: обычный Tree::verifyImpl :88–159 проверяет обе closure
   и retained roots; строгий actual extent :124–131 остаётся отдельным media
   требованием. Хвост playback не становится logical source/authority; новый
   append обязан идти после actual EOF, старые bytes сохраняются. Повреждение
   reachable DATA/одного HEAD не маскируется reset. No orphan cleanup/truncate.
3. Owner::openImpl Files.cpp:1471–1497 сейчас не даёт нужный prepared playback
   writeExisting. Проект честно требует узкое private расширение fresh rights,
   same-HANDLE container identity, nonfailed state и непрерывные leases, а не
   обещает, что оно уже реализовано. completedPackageRole:716–755 сохраняет
   readonly packed audio; расширять его без playback-only ограничения нельзя.
4. Tree commit :278–305 использует reserve и actual EOF; Files.cpp:998–1027
   учитывает physicalBytes/store cap. Old orphan и records не вычитаются из
   бюджета. DPAPI не требует нового пользовательского nonce counter; прежние
   generations/record references не сбрасываются. Jobs/pins/owned memory,
   failure/cancel stickiness и actual retirement не ослаблены проектом.
5. V5 finishRecovery:210–236 требует history до retainPrefix; :720–729 задаёт
   encode→manifest→recovery→final state→full inspect. План сохраняет exact
   canonical/WAV proof до первого эффекта и reuse MF converter/encoder, а не
   новую реализацию PCM/AAC. Это реализуемые reuse points, не source GO.

### Все действующие тематические checklist

Полностью прочитаны все 12 тематических файлов; исторические review-*.md
отчёты не выдаются за новые активные наборы требований. Старые отметки
сохранены. Их качество проверено на применимость round462, не переаттестован
runtime всей фичи и не объявлено, что предыдущий PASS относится к новому коду.

| Checklist | checked / unchecked после review | Применимость |
|---|---:|---|
| requirements | 22 / 0 | FR/SC, полнота Windows parity остаётся отдельной целью |
| audio-capture | 24 / 0 | Canonical prefix/AEC/Stop/resource gates не меняются |
| advanced-routing | 14 / 0 | Маршрутизация/устройства вне этой ветви |
| ux | 25 / 0 | Общий интерфейс/installed/accessibility не приняты этим review |
| security | 27 / 0 | BOTH authority/ACL/original owner/no empty ledger сохраняются |
| privacy-pause | 12 / 0 | История OPEN/CLOSE и отдельная T120 не ослаблены |
| packed-writer | 12 / 0 | No-op/generation/append/quota/Guard/pins действуют; R462-I1 в новом append, не отмена старого gate |
| start-owner-recovery | 10 / 0 | Нет назначения текущему аккаунту/нового claim/ложного drain |
| calendar-wire | 5 / 0 | T119 intent/auth/document gates без изменений |
| calendar-operation | 8 / 0 | Операции calendar вне этого проекта |
| calendar-launcher | 5 / 0 | Native launcher/внешние URL вне этого проекта |
| cold-prefix-recovery | 38 / 3 | Новые supported035/036/037/040; open038/039/041 |

Итого **205 критериев: 202 checked / 3 unchecked**. Новые7: **4 / 3**;
прежние34 cold-prefix — сохранены; остальные11 файлов — **164 / 0** без записи.
CHK035 принят с сохранением прежнего unfinishedHistory predicate, не как
допуск любого JSON, прошедшего generic manifest parser. CHK039/041 открыты
только по повторным exact outcomes; limits, fault preservation, actual RED/GREEN,
real MF partial>256KiB и отдельные device/release gates сформулированы.

Scoped coverage: 4FR (012/013/014/022) + 2SC (005/006) связаны с открытой T116
и новым plan append; требований этого slice без задачи не выявлено. T117
migration/T118 full acceptance, T119 calendar/T120 Pause остаются отдельными.
Конституционных MUST конфликтов не выявлено; конфликт I1 протокольный, HIGH.
Это не полное покрытие FR/SC/всех задач Feature200. C/H threshold0 не пройден.

### Точные SHA256 прочитанных нормативов

```text
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859  .specify/memory/constitution.md
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11  specs/200-windows-desktop-app/spec.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f  specs/200-windows-desktop-app/tasks.md
dcbdebbd7a24e3ef82048ff2122ac0df7ff6dcebebffca9a2ad1b0a87ceb1305  specs/200-windows-desktop-app/plan.md
9652a304061ea70ae6af995dc7e468a4efa2bb95547b02dce2999c21d06dbe4f  specs/200-windows-desktop-app/research.md
5c6d5ea63ce7434dacbcb39184674cdcc8d0ba8453e9f4aae05085361c4721a0  specs/200-windows-desktop-app/data-model.md
0a9e55305ea3c135beac316d2cdd4dac8ff9b050a9999b9aa3f994a0a413732e  specs/200-windows-desktop-app/quickstart.md
a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490  specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md
176b73ea199c9a83358e83c175abb559acd53f45c740d4e7c0f9b5f4887d2c5e  specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md
```

После разрешённого изменения markers/notes cold-prefix SHA256:
`ddd61c253570d65f027b648c7ab623b9011f93fd511285907d475db0afef1133`.
Точные SHA остальных неизменённых тематических checklist:

```text
91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55 requirements
4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd audio-capture
bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12 advanced-routing
1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801 ux
0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273 security
5e1c0a89ebb33f47876fafd345972e3e627e6597504d6b6a5dc4c8ac1ab10eec privacy-pause
a1f18f2cdfe6ebcdb369ad0ed6a877f77af4658bc388a4cab1475c50b45b62a0 packed-writer
1684307dd5d9ea36d9939842b53764839b87b6247e1a744e63d6640426189ec7 start-owner-recovery
0b58c484e25b5f37ec3b157f0bbe227ddcc2cff682dbae5ab0af882936796895 calendar-wire
a656adcd4d6cccf578cc7c98f385fe10ba5b422cfb47dba7e3662f8b24e0a834 calendar-operation
99f1a945f2b557ece837ea484633d3e61af5a7838c0068a182bea17de22e4355 calendar-launcher
```

Readonly checksum сверка всех216 source inputs с сохранённым WAV30 manifest
прошла216/216 без расхождений; manifest SHA256
`c902038944f4bbf13dda2a36a17a486db0c10fea47170ff68a99202e3d666c17`.
Это проверка сохранности исходников, не build/test/runtime результат round462.
Никаких VM/процессов проверки/тестов/сборок/Git/GitHub не запускалось. Записаны
только cold-prefix markers/notes и этот append. Перед test-only требуется
устранить I1 и зафиксировать таблицу U1, затем точечно повторно проверить три
оставшихся пункта. T116/#7444 и полный goal не закрыты.

## Round462 — повторный gate после исправления I1/U1

2026-10-19. **GO качеству требований перед предусмотренным test-only short RED.
Scoped analyze: C0/H0/M0/L0.** Предыдущий NO-GO и его точные SHA выше остаются
историческим evidence; настоящее дополнение относится к исправленным пяти
нормативам ниже. Это не GO будущему actual test diff, production source или
runtime; реализация не предъявлялась и не проверялась этим повторным gate.

Пределы прежние: authoritative worktree
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, T116/#7444,
high-risk-product. Прочитаны заново изменённые round462 разделы plan/research/
data-model/quickstart/packed contract; проверены условия прежних CHK035/036/037/040
и фактические source predicates Writer/history/metadata/completed/inspection.
Spec/constitution/tasks/local contract и11 остальных тематических checklist
побайтово совпали с предыдущим gate; их прежние прочитанные основания сохранены,
полный feature-wide обход и повторная runtime приёмка не заявляются.
`.specify/feature.json` вновь указывает feature200; analyze pre/post hooks
disabled. Штатный prerequisite script по прежней причине не запускался:
никакой неразрешённой записи feature.json/Git; пути установлены чтением.

### Закрытие замечаний и сохранение условий допуска

| Проверка | Текущий результат / основание |
|---|---|
| R462-I1, CHK038 | Устранено. Plan:2734–2742, data-model:683–684, packed:387–390, research:3173–3174 и quickstart:1181–1183 различают nonempty→0 +1 и empty→0 same proof/generation/no HEAD write. Для empty отсутствует reset-HEAD cut. Согласовано с прежним packed:152–158, Writer.cpp:168–178,204–219; менять этот код не предлагается. |
| R462-U1, CHK039/041 | Устранено как пробел требований. Plan:2775–2808 содержит15 строк и однозначные R/C/D/S; quickstart:1181–1186 и packed:398–403 ссылаются на неё. Outcome выбирается до запуска по фактическому shape; ordinal/flush не authority, отказ не разрешает задним числом заменить R на D. |
| CHK035 | Сохранено. Admission:2712–2719 и таблица разделяют unsealed unfinished history и terminal metadata; неподдержанные D остаются открытыми P2. Нет общего допуска started outputs или объявления всего P2 решённым. |
| CHK036 | Сохранено. Fresh mixed rights:2721–2727, same-HANDLE ID:2728–2729; непрерывные leases, private playback-only writeExisting, без readonly upgrade/новых IDs/переноса failed proof. |
| CHK037 | Сохранено. Full BOTH/retained closure, strict canonical→WAV bytewise/EOF/cancel/sticky preflight до эффекта:2728–2742. Orphan playback не authority и не удаляется; reachable corruption/invalid HEAD отказывают. |
| CHK040 | Сохранено. Degraded-only ACK/full inspection:2749–2753; canonical/WAV/IDs/queue/original owner неизменны, normal/keepable/HTTP=false. Unused/completed/WAV branches, immutable sealed и T117/118 boundaries не ослаблены. |

Все15 строк таблицы оценены, а не только short positive:

- Первые4 допускают R только после прочих неизменных preflight predicates:
  исходный/empty no-op, nonempty reset, orphan DATA/NODE до HEAD и полная новая
  HEAD до/после flush. Old physical playback extent сохраняется, append после
  actual EOF; power-loss/исторический ACK не заявлены.
- Строка5 — D для broken HEAD/birth; строка6 — R для valid retire со старой
  unfinished history. Строки7–11 — D для torn retire, metadata orphan/temp,
  newer-unbound manifest, terminal-bound+unused recovery и partial/singleton
  recovery. Это сохраняет exact inventory и `unfinishedHistory(...true)`
  (LocalRecordingPackage.cpp:539–560, parser:173), не ослабляет parser.
- Строки12–13 — C только с готовыми terminal members и selected finalizing;
  все five-member/history/hash/AAC checks прежнего completeUnfinished:610–688
  обязательны. Нет reset/re-encode ранее завершённых членов.
- Строка14 — S: recover отказывает, readonly sealed inspection отдельно
  успешна при всех остальных content/retained predicates. Это соответствует
  openUnfinished Metadata.cpp:1696–1701 и inspectProtected/Impl
  LocalRecordingPackage.cpp:575–595,767–809. Строка15 — D для torn final state
  или повреждённого retained member, не выбор surviving state.

Общая оговорка «остальные admission predicates» применяется к выбранной ветви
R/C/S, а не требует unused recovery от C: сами строки12–14 явно выбирают прежние
completed/sealed routes. Без прочих predicates/cancel-free/resource-admissible
условий таблица не обещает успех. Actual native/shortIO/flush/readback/crypto/
quota/cancel после эффекта остаются sticky failure без same-owner retry/cleanup.
Никакого metadata rollback, orphan authority, readonly upgrade или нарушения
immutable sealed не выявлено. Product clarification не требуется; исправления
технические и не меняют владельца/пользовательские правила.

Scoped mapping прежний: FR012/013/014/022 + SC005/006 → открытая T116, без новых
непокрытых требований/задач в slice и без ослабления constitution MUST. Новых
ambiguity/duplication/conflict findings в проверенном изменении0. Это не анализ
покрытия всей feature и не закрытие T116/T117/T118/T119/T120.

### Markers, сохранность исходников и точные SHA

Изменены только CHK038/039/041 и добавлено примечание cold-prefix; предыдущие
notes/NO-GO не удалены. Новые CHK035–041: **7 checked/0 unchecked**;
весь cold-prefix: **41/0**; остальные11 тематических checklist: **164/0**.
Все12 суммарно: **205 checked/0 unchecked**. Это качество требований, а не
исполнение long MF, repeated crash или полной regression matrix.

Все216 source inputs вновь сверены readonly с WAV30 source manifest:
216/216 совпали, manifest SHA
`c902038944f4bbf13dda2a36a17a486db0c10fea47170ff68a99202e3d666c17`.
Никаких VM/build/test/Git/GitHub действий не выполнялось. Записаны только
разрешённые checklist markers/notes и этот append.

```text
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859  .specify/memory/constitution.md
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11  specs/200-windows-desktop-app/spec.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f  specs/200-windows-desktop-app/tasks.md
5fff84e64d6c9acb7bc365a56ec8b63ab0594bca7219da312965f4a889d10c9d  specs/200-windows-desktop-app/plan.md
32dc689aef2066d5444e9b10598ce3cc9214d22922478f8773ff5de374726248  specs/200-windows-desktop-app/research.md
49f8623498842b6a2ef57243398c1c4c1230a1009a60d364e839f230750374b3  specs/200-windows-desktop-app/data-model.md
fd906ccbdb28355005db083badedfe6641f09cf0186deb6be7dadb4787e5f5d8  specs/200-windows-desktop-app/quickstart.md
a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490  specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md
f610c70062ee13711b1989b88562b3403458589701b445c0ba763ccac635ffea  specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md
9c7f0301ef5bfdf567d43e3abb48a84cf62870c5c43a082008588df286121116  specs/200-windows-desktop-app/checklists/cold-prefix-recovery.md
```

Следующий разрешённый этап по требованиям — test-only short playback HEAD RED
на прежнем production source с actual child exit88/wait и заранее выбранной R
строкой; actual diff отдельно предъявляется source review. Compile failure,
timeout или skip не заменяют RED. Успех короткого этапа не заменяет actual MF
partial>256KiB, repeated cuts/faults, исходные24 cuts, affected regressions или
installed/hardware/release; полного P2/goal GO здесь нет.

## Round462 — actual test-only source gate короткого playback RED

2026-10-19. **GO только предъявленному test-only diff перед отдельным short RED.**
Блокирующих source findings/новых C/H замечаний не выявлено. Это не выполненный
RED, не production/source GREEN и не приёмка полной repeated/long MF матрицы.
Проверка независимая, read-only через code-reviewer; записан только этот append.
Нормы, checklist markers/notes, код, VM, Git/GitHub, builds/tests не изменялись.

### Точный объём и идентичность

216 входов сверены с `wav33-native/source.sha256` (SHA256
`c902038944f4bbf13dda2a36a17a486db0c10fea47170ff68a99202e3d666c17`).
Совпали214; отличаются РОВНО CMakeLists и V5LocalRecordingWriterTests.
Production inputs неизменны. Для точного текстового diff использованы сохранённые
копии wav25-red CMakeLists и wav30-full-head V5tests, причём SHA обеих исходных
копий сначала подтверждены строками именно wav33 manifest — не допущено равенство
только по названию предыдущего stage.

```text
baseline c295cb348f9a205a0617b83a6f6e4da1746c5d1bcdd4f2e4ae1ac10368b628aa apps/windows/CMakeLists.txt
current  a3909bc1a0ef951d3419cd4ff761a7239d14ca82a712c3e9536005b16082854a apps/windows/CMakeLists.txt
baseline 94e74a5ac75bdda5bfaa6bb4ab22910fd40cfc669fc8e6dcac3678cadf6f47e6 apps/windows/Tests/GrafWindowsPackageTests/V5LocalRecordingWriterTests.cpp
current  c65226b12037780a4c4a0e92573be2197b82cbcadd65c87bed938a5b51f36bb5 apps/windows/Tests/GrafWindowsPackageTests/V5LocalRecordingWriterTests.cpp
```

### Проверка изменений и всех callers

- CMake:182–183 — ровно новый Windows-only CTest `ProtectedRecoveryPlayback`,
  существующий target `V5LocalRecordingWriterTests --cold-recovery-playback`,
  RUN_SERIAL TRUE/TIMEOUT180. Target sources/link/options и старые CTests
  не меняются; существующие child60s/cleanup10s guards сохранены.
- V5tests:288,301–338 — enum all/wav/playback заменяет bool. Все callers:
  :920 wav с прежними7 refusals; :923 новый playback; :937 default all.
  При all/wav `playbackReady=false`, значит derivedReady==старый wavReady:
  старые branches, выбор cuts, full continued4 и wav continued1 сохранены.
  Completion/returned-fault/child CLI :925–933 и их функции не изменены.
- Новый фильтр требует именно role2/op6. Baseline trace остаётся фактическим,
  role/operation/shape assertions :314–326 проверяются до loop. Child wrapper
  :277–286 требует реальный CreateProcess, WAIT_OBJECT_0 и exit88, не принимает
  missing event exit89/timeout/иной crash как нужный cut. В child :71–104
  наблюдаемый ordinal ещё сверяется с ожидаемыми role/operation. Full HEAD
  WriteFile assertion :124 и native Flush event :131–135 не ослаблены.
- Новый explicit assert :375 требует recovered.ok; затем :376–386 проверяют
  started, full semantic/trustedPrefix/sealedDegraded, duration1000 и отсутствие
  normal/keepable. На unchanged production именно отказ recover должен дать
  semantic RED здесь, а не «expected failure»/skip/обычный успешный возврат.
  До этого обязаны пройти setup/trace/actual child wait; иначе отказ stage
  НЕ квалифицируется как доказательство missing functionality.
- :340–346,395–396 сохраняют canonical, все исходные package/role id.bin и
  queue hashes до/после actual child и recover. :350,381 сохраняют whole WAV.
  :397–408 требуют fresh cold inspection после release, session/duration/times/
  decoded AAC и полную disk equality после readonly inspection. :409,412–415
  сохраняют owned-memory/job/pin возврат; continued==1 исключает hollow PASS
  при отсутствии подходящего cut или многократном продолжении в filtered CLI.
- Helper :289–300 имеет только2 callers :353/:384, оба guarded playbackReady.
  Проверяет appendOffset<=originalEOF<1MiB ДО выделения string; сохраняет
  ровно prefix128 + [32896,originalEOF). Между ними ровно две HEAD cells
  по16384B (128..16511 и16512..32895), не забытый data interval. Читает bounded
  generated ciphertext, не plaintext/живые записи; gcount/seek assertions
  ловят short read. :383 проверяет отсутствие shrink, повторный helper читает
  тот же OLD extent, исключая только разрешённые mutable HEAD и новый append.
  Ограничение относится к сохранённому one-second fixture, не продуктовым
  лимитам и не произвольному media файлу.
- Добавленные helper/enum/CLI находятся внутри существующего _WIN32 scope;
  C++17 уже задан CMake, mutable string::data допустим. Формат объявлен через
  прежние полные headers; новых forward-declaration/type/format hazards при
  чтении diff не выявлено. NDEBUG снимается :9–12, assert не превращается в
  пустой Release PASS. Факт MSVC build этим source review не доказан.

### Границы допуска

GO относится к короткому filtered CLI и неизменному production. На следующем
stage нужны build/actual trace/exit88/точный assertion/PE/source/owned receipts;
ни timeout, ни build fail, ни отказ helper/setup не считаются требуемым RED.
Номер ordinal заранее не фиксируется по памяти: выбирается роль2/op6 из trace,
но фильтр не меняет ожидаемый outcome по результату запуска.

Это unsealed one-second output после первой observed HEAD publication, НЕ
доказательство actual MF partial>256KiB или всех повторных прерываний. Старый
default all пока намеренно сохраняет started-playback refusal: после будущего
production изменения его ожидания потребуют отдельного доказанного обновления
по plan462, не молчаливого переноса этого GO на полный regression GREEN.
CHK035–041 остаются только requirements quality (7/0), cold-prefix41/0;
прежние NO-GO/RED evidence не сняты. T116/P2/full goal не закрыты.

## Round462 — окончательный test source после усиления EOF/generation

2026-10-19. **GO только короткому test-only RED на окончательном исходнике**,
не раннему frozen aac34-red и не production GREEN. Проверены actual diff и
реальное положение новых assertions; блокеров для этого запуска не выявлено.
Предыдущий test SHA c65226… относится только к предыдущей редакции и не является
идентичностью нынешнего source gate. Никаких запусков этим review не выполнено.

Окончательные SHA256:

```text
a3909bc1a0ef951d3419cd4ff761a7239d14ca82a712c3e9536005b16082854a apps/windows/CMakeLists.txt
a7af576e60b4e5eec81311d11e812149160f90021ce5c625862207e2783d25a5 apps/windows/Tests/GrafWindowsPackageTests/V5LocalRecordingWriterTests.cpp
```

- V5tests:383 действительно требует physical EOF строго БОЛЬШЕ сохранённого
  playbackEof после recover/finalize, а :384 по-прежнему сверяет весь прежний
  non-HEAD extent. Metadata-only completion без изменения playback этот
  conjunction не пройдёт. Это не разрешение append неизвестного мусора:
  fresh full hash/AAC/history inspection :413–419 также остаётся обязательной.
- :402–412 находится внутри derivedReady/fresh store/readPackage scope и
  дополнительно ограничено playbackReady. Перебирается current final package
  refCount; exact one playback проверяется found==1. На :408 сперва проверяются
  ref.sealed и наличие ref.generation, затем разыменованное значение>2.
  Тип generation — optional<uint64_t> (Metadata.h:292–300): short-circuit
  безопасен, сравнение относится к числу, не к optional и не к package generation.
  Сразу следующая full inspection подтверждает actual sealed content authority;
  structural ref сам по себе за proof не выдаётся.
- Нижняя граница>2 безопасна для корректного nonempty reset/re-encode, даже
  если исходное поколение выше2. Но комментарий «old g2» не заменяет отдельное
  доказательство pre-cut generation: birth действительно создаёт g1
  (Files.cpp:1325–1356), Writer::open проверяет same-length no-op, Tree mutation
  увеличивает generation на1 (Tree.cpp:204–218). Однако event filter
  V5tests:83–91 наблюдает HEAD лишь после первого append, а не любую HEAD:
  Writer::flushPacked:110–118 и checkpointImpl:409–415 допускают отдельный
  resize, WriteStream::SetSize/Commit (Reader.cpp:392–405) передают native MF
  вызовы. Исходник не утверждает отсутствие ВСЕХ таких вызовов до первой DATA.
  Поэтому >2 здесь принимается как нижняя граница, НЕ как runtime доказательство
  old==2 или final>actual-old. Это неблокирующая оговорка для short RED, но полный
  будущий reset/generation gate должен опираться на фактический old generation
  либо явно проверенный pre-cut g2, а не только этот комментарий.
- Остальные diff/callers/child wait/exit88/serial180/old all+wav expectations
  неизменны относительно предыдущей рассмотренной test-only редакции; новое
  усиление не вводит I/O hooks, ожиданий или product effects. Повторная сверка
  всех216 с wav33 manifest вновь дала только те же2 отличия, production214
  unchanged. Assertions/helper/setup failures всё ещё НЕ квалифицируют как
  требуемый semantic RED вместо explicit recovered.ok assertion :375.

Следующий stage должен быть создан из окончательного source, не использовать
предыдущий неисполненный frozen snapshot как доказательство. Stage manifest/PE/
runtime ещё не предъявлены; long MF>256KiB, repeated cuts и весь T116 открыты.
Изменён только этот append; cold-prefix markers/notes и нормативы не тронуты.

## Round462 — aac35-red: независимая квалификация завершённого short RED

2026-10-19. **SCOPED GO квалификации runtime RED**, не успешному восстановлению,
не production GREEN и не полной T116/P2 acceptance. Независимо прочитаны все
предъявленные source/prior manifests, changed.json, validate-input.ps1,
полные build.log/test.log/actual-test.log, JUnit XML и result.json из
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/aac35-red`.
UTF16LE build/test logs декодированы только для чтения; LastTest.log — ASCII.
Никаких повторных запусков/VM/build/test/Git/GitHub действий не выполнялось.

### Source / harness / PE identity

- Source manifest SHA256 точно
  `a9640c6a9644a2cb3166f071b1c96d48442f14fd69c8ff3d4499e3a2eebae96b`.
  prior.sha256 побайтово совпал с wav33-native/source.sha256. Diff manifests
  содержит ровно2 разрешённых замены, согласованные с changed.json:
  CMake `a3909bc1a0ef951d3419cd4ff761a7239d14ca82a712c3e9536005b16082854a`,
  V5tests `a7af576e60b4e5eec81311d11e812149160f90021ce5c625862207e2783d25a5`.
  Оба frozen файла перепроверены непосредственно; current216 также совпали
  с manifest216. Production214 прежние, superseded aac34 не используется
  как evidence этого запуска.
- Frozen harness SHA256
  `b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a`:
  Owned precheck:14, prior216:15, проверка staged source:20–25; Debug build
  target V5LocalRecordingWriterTests:30; PE hash/size до запуска:34–36;
  anchored CTest regex:38; postflight216:44 и неизменность PE:45.
- Receipt: terminal=true, Debug, build=0, test_exit=8, executed_tests=1,
  postflight=216, owned_processes=0, failure=TEST. Это согласуется с harness:
  PE_CHANGED guard расположен ДО формирования failure=TEST. Записанный
  before/after-guarded PE SHA256
  `c73cfb3a58b951964749b62db88f01d97d9193d25c6dd51311d3abee05e70817`,
  6960640 bytes. Свежий guest/binary rehash не выполнялся — квалификация
  сохранённого receipt и его исполняемого control flow, не новый live check.
  Harness должен завершиться exit1 при failure=TEST; сообщённый main terminal
  session6558/exit1 с этим согласуется, сам session повторно не опрашивался.

### Фактическая причина RED и уже пройденные предусловия

JUnit: ровно `ProtectedRecoveryPlayback`, tests1/failures1/disabled0/skipped0,
testcase status=fail, time=**5.28505s** (CTest display5.29s). Actual LastTest
command — Debug V5LocalRecordingWriterTests.exe `--cold-recovery-playback`.
Все24 baseline TRACE события присутствуют последовательно; единственный
selected playback role2/op6 находится на **ordinal12**, после role2 DATA op4
ordinal10 и HEAD WriteFile op5 ordinal11. Во всех трёх представлениях вывода
ровно ожидаемый assertion frozen V5tests:375:

```text
recovered.ok() && "verified_started_playback_must_rebuild_after_process_crash"
```

Достижение именно parent line375 доказывает прохождение предшествующего
неизменного control flow frozen test: baseline/setup/trace assertions, вызов
crashRecoveryAt:344 с WAIT_OBJECT_0 и GetExitCodeProcess==88:283–286,
canonical/queue/original-ID checks:345–346, чтение generated playback EOF и
bounded snapshot helper:352–353,292–298 и повторное открытие store:361.
Непопадание в physical cut вернуло бы child89, timeout был бы другим parent
assertion, helper/short read/setup failure не дошли бы до375. Это inference
по достигнутой строке и exact source/PE guards, НЕ отдельные printed receipts.

Строки child `COLD_RECOVERY_CRASH hit=…` в сохранённом выводе НЕТ; наличие
печатного child stdout/stderr не заявляется. NativeCommandError в test.log
отражает stderr CTest после реального failed assertion: harness EAP=Continue
сохранил test_exit8 и выполнил postflight/PE/owned/terminal. Это не build failure,
timeout, skip или shell wrapper failure вместо требуемого RED. Build.log
показывает успешную повторную генерацию CMake, компиляцию и Debug link; его
служебный generate.stamp result=-1 означает rerun, не ошибку сборки.

### Что этим запуском НЕ принято

После line375 исполнение прекращено. Поэтому post-recovery whole WAV equality,
strict EOF growth, final playback generation>2/exactly1 и fresh sealed/AAC/
history/times inspection НЕ исполнены и не объявляются PASS. Helper прошёл
только начальное чтение старых generated ciphertext bytes; их сохранность
после будущего successful encode ещё предстоит доказать.

Квалифицирован genuine short playback HEAD-flush boundary RED на unchanged
production; это не доказательство actual partial MF>256KiB, old g2, нового
reset/encode, repeated-crash/fault matrix, hardware/power-loss или performance.
Actual RED сохранён, expectations/таймауты/защиты не ослаблены. Ни source fix GO,
ни полного T116/P2/Windows goal GO нет. Checklist markers остаются только
requirements quality; чужая validation запись не изменялась. Записан только
этот append в собственный отчёт.

## Round462 — measured-generation/refusal test-only source gate перед aac37

Решение: **GO только на следующий short test-only RED; C0/H0/M1**.
Это не production/source-fix GO, не GREEN и не закрытие P2/T116. Применён
`code-reviewer`; просмотрены actual diff против frozen aac35, все вызовы новых
helpers и непосредственно используемые owner/tree/writer/rename/conversion
ветви. Нормативный gate целиком не повторялся; для квалификации замечания M1
прочитана только применимая таблица plan462. VM/build/test/Git/GitHub не запускались.

### Точный вход и compile hardening

Активная `.specify/feature.json` указывает feature200, high-risk-product,
branch codex/200-windows-followup, source_sha
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; это прочитанная привязка, не новый
Git HEAD receipt. Повторная checksum-сверка всех216 входов против
`aac35-red/source.sha256` дала ровно одно отличие — этот тест. Production214
и CMake unchanged. SHA256 исходного aac35 manifest:
`a9640c6a9644a2cb3166f071b1c96d48442f14fd69c8ff3d4499e3a2eebae96b`.

Окончательный рассмотренный V5LocalRecordingWriterTests.cpp SHA256:
`d15b52fc7c7098c688e759961588894947a6e8e4feaa783dae28fa7b7868378e`.
Промежуточные `03b2f4e9…`/`03b2…` и редакция с gcount()==id.size() не являются
этим входом. На test:298 теперь read(...,16), gcount()==16; CustodyId действительно
array<uint8_t,16> (ProtectedCustodyCodec.h:189). Выявленный при чтении ранней
редакции signed/unsigned compile risk снят, сборку PASS этим не утверждаю.
Полные owner/tree определения доступны через включённый Tree.h:3 → Owner.h;
новые helpers остаются внутри WIN32. CMake:163–165 сохраняет /W4 /WX,
asserts не выключены (test:9–12). Новых timeout/CLI/hooks/production ветвей нет.

### Source-подтверждения

- Test:289–307 читает настоящие store/object IDs и prefix container candidate
  по offset48 (Format.cpp:41–43), затем public Owner::open и Tree::verify.
  Сам prefix за authority не выдан: Files.cpp:1525–1559 проверяет удержанные
  identity/prefix, Tree.cpp:112–122 обходит BOTH closures, :155–159 проверяет
  boundary перед возвратом proof. Это media proof, не package authority.
- Legacy public route действительно получает собственные native права
  (Files.cpp:1512–1515,1538); даже readExisting здесь не следует называть
  production prepared read-only acquisition. Но это только внешний тестовый
  probe: его proof не передаётся в recover/StoreOwner. На test:430 временный
  shared_ptr освобождается в конце full-expression, до fresh store:442;
  scoped probes:323–325 и canonical writer:334–339 также освобождены до :355.
  Tree удерживает owner только своим shared_ptr; публичный verify не оставляет
  глобального cache/lease. No-write hash assertion :432 стоит после probe и до
  настоящего recover. Новый final check :488 сравнивает optional<uint64_t>
  после проверки наличия с фактическим old generation; found==1 сохранён.
- Case0 делает genuine same-length canonical replacement+checkpoint, а не
  повреждение ciphertext. Начальные 0.25F (test:241) заменяются на 0.5F в первом
  float. SAME converter V5Writer.cpp:415–417 усредняет первые три samples:
  первый WAV PCM становится 10922 вместо8191; это действительно иные bytes.
  Canonical proof/writer освобождаются до fresh store. Исходные ID/history/length
  не переписываются этим fixture. Case1 физически добавляет WAV tail; cases2/3
  портят первую HEAD/обрезают вторую; case4 flips appendOffset; case5 добавляет
  посторонний playback child; case7 меняет реальный object id; case8 требует
  changed>0 при порче настоящих block.* envelopes; case9 отменяет token после
  успешного store open. File/short-read/setup ошибки не обходят assertions.
- Case4 source подтверждает именно порчу байта первого append-region record;
  logicalBytes>0/<blockBytes и название комментария сами по себе не являются
  отдельным доказательством типа DATA против NODE либо полной long-MF матрицы.
  Этот short RED не квалифицирует полное reachable-DATA coverage по одному label.
- Test:402 помещает десять отказов ДО positive. Каждый требует !ok/non-none,
  whole-tree equality и возврат charged memory:352–361. Пока production отвергает
  любой started playback, такие отказы ещё не доказывают дифференцирующие guards
  новой ветви; это tests-first fixtures, не её runtime GREEN. Parent baseline
  trace/checks, actual child wait/exit88:277–286 и старые default all/wav callers
  :1010–1028 не ослаблены. Полный all по-прежнему требует continued4, filtered1.

### M1 — case6 не singleton recovery, а pre-index DATA/temp

Test:315 выбирает первое role4/op2, :317–318 берёт первое совпадение.
Wrapper test:142 вызывает op2 ДО реального NtSetInformationFile:144; op3
происходит ПОСЛЕ успешного rename:145. Настоящий Files.cpp:1072 уже создал
index.tmp, но вызов публикации :1094 ещё не произошёл. Поэтому этот fixture
не подтверждает наличие одного опубликованного recovery index; !ok может быть
правильным отказом на DATA/temp, без испытания singleton. Это подтверждённое
расхождение заявленного названия/покрытия, не дефект production.

Для допуска именно short RED это НЕ C/H blocker: plan:2766–2768 требует
started recovery; таблица :2797 явно объединяет DATA/temp/index singleton/
partial/invalid с одинаковым D. Поэтому уточняю предварительный комментарий
«нужно поправить перед запуском»: фактический DATA/temp отрицательный случай
допустим для этого запуска, но singleton coverage ему приписывать нельзя.
Если требуется именно singleton, минимальный отдельный test-only шаг — первое
role4/op3 и явная проверка одного опубликованного index при отсутствии peer,
до snapshot/recover. Не заменять отказ на успех и не ослаблять inventory guards.
В текущем review я этого изменения не делал и не требую нового полного плана.

### Границы runtime допуска

aac34/aac36 не исполнялись по сообщению main и superseded; runtime evidence ими
не заменяется. Следующий aac37 должен содержать именно рассмотренный test hash
и фактический prior aac35. Ожидаемый semantic RED — explicit recovered.ok
assertion test:456 ПОСЛЕ baseline/десяти refusals/измерения generation и no-write
hash. Падение на helper, fixture, child wait/exit, resource assertion либо build
не является таким RED. Final EOF/old-byte preservation/new-generation/full
fresh sealed inspection после positive всё ещё не исполнены на новом входе.
Long MF>256KiB, repeat cuts, post-effect faults, singleton qualification,
GREEN/regressions и полная Windows/installed/hardware приёмка остаются открыты.
Изменён только этот append; чужой validation/report, нормы, задачи и checkbox
markers не менялись.

## Round462 — aac37-red: независимая квалификация завершённого RED

**Scoped runtime RED qualified.** Прочитаны целиком сохранённые result.json,
result.xml, actual-test.log, UTF16LE build.log/test.log, validate-input.ps1,
changed.json и оба source manifests в external aac37-red. Ничего не исполнялось
в VM; session79447/exit1 сообщён main, повторного опроса процесса не было.

- Manifest SHA256 действительно
  `0c03d7770a00e47bcd58d3817bb79b94fad38ad42c73665e25aa1271cf1b4aec`.
  prior.sha256 побайтово совпадает с aac35-red/source.sha256. Единственный
  changed.json path — V5tests, frozen test SHA256
  `d15b52fc7c7098c688e759961588894947a6e8e4feaa783dae28fa7b7868378e`,
  тот же, которому дан предыдущий scoped source GO. В текущей рабочей копии
  уже были4 production changes; они не выданы за source aac37. Для source
  уточнения birth использована старая frozen wav27 копия Files.cpp с hash
  ee303f71…d1e139, совпадающим с записью manifest aac37.
- Receipt: terminal=true, Debug/V5LocalRecordingWriterTests,
  test_pattern=ProtectedRecoveryPlayback, build0/test_exit8/executed1,
  postflight216, owned_processes0, failure=TEST. PE
  `bd3321361f1436b8c7e1db48a36b166aecffbbe569430aefdf835695c4a43720`,
  6960640 bytes. Harness проверяет source216 до и после, PE_CHANGED guard
  расположен до failure=TEST, поэтому receipt согласуется с неизменностью
  before/after PE. Это сохранённый guard receipt, не новый guest rehash.
  При failure=TEST harness возвращает1; сообщённый process exit1 согласуется.
- JUnit: ровно1 testcase ProtectedRecoveryPlayback, failures1/disabled0/
  skipped0, status=fail, **26.9776s**; CTest отображает26.98s. Actual LastTest
  command — Debug exe --cold-recovery-playback. Build.log подтверждает
  компиляцию нового V5tests и успешный link. NativeCommandError в test.log
  относится к stderr реального CTest failure при EAP=Continue, не заменяет
  фактическую причину RED shell-ошибкой или build failure.
- Во всех представлениях вывода24 последовательных TRACE; selected playback
  role2/op6 — ordinal12. До падения присутствуют по одному refusal case0..9:
  cases0..7 error13, case8 error7, case9 error6/native000003e3. Затем ровно
  COLD_PLAYBACK_OLD_GENERATION generation=2 и EXACT frozen test:456 assertion
  recovered.ok() && verified_started_playback_must_rebuild_after_process_crash.
  Достижение :456 доказывает прохождение control flow: исходный baseline,
  всех refusal postchecks (включая последний equality/resource assertion),
  positive child WAIT_OBJECT_0/exit88:283–286, helper full BOTH proof :430,
  no-write hash :432 и fresh store. Это вывод по exact source/control flow,
  не несуществующие дополнительные printed receipts. Child stdout/stderr
  COLD_RECOVERY_CRASH в сохранённом журнале отсутствует и не заявляется.

Qualified именно genuine short HEAD-flush RED на unchanged production214,
теперь с фактическим old generation2, а не guessed g2. Это НЕ доказывает
отдельные future guard branches: прежняя production отказывает started AAC
целиком. Success-only EOF/generation/hash/AAC/final-inspection assertions ещё
не исполнялись. Case6 квалифицируется как pre-index DATA/temp D, не singleton.
aac34/aac36 остаются неисполненными superseded, по сообщению main. Long MF,
repeat/post-effect/native/full T116/application gates не закрыты.

## Round462 — aac38-green: actual six-file source gate

**NO-GO для предъявленного frozen patch; C0/H1/M1.** Причина H1 — оставшийся
противоположный expectation в существующем sibling CLI, не найденный bypass
production authority. Проверка bounded: сами6 diff и непосредственно связанные
callers/ownership/reset/conversion/guard/finalization. Нормативный gate не
повторялся. Сборок/тестов/VM/Git/GitHub actions не было.

### Точный snapshot

Manifest `1249a7b6c6c3766745e5cbe80fe4889f0517d353e1b212db655855eb281eb4ef`
проверен. prior побайтово aac37 manifest; оба списка216 paths, равные sets;
ровно6 hash differences, точно changed.json. Все6 staged bytes совпали со
своими manifest entries; рабочая копия также совпала со всеми216 aac38 inputs.
Изменённые entry SHA256:

```text
cffaadf9ae1058865e4bf98e0919c140f7c2a5e0446159503f4d3e6bfda5ee0b V5LocalRecordingWriter.cpp
625e18381c4e1764843e17ca81f05768fba56923af51aec5d542f54774e4529d ProtectedCustodyFiles.cpp
da0df6bb291da2aa5d73269a931bb4bec47ee5a606bdb59ddef882d39d51395d ProtectedCustodyFiles.h
555212f961813a731f5afa317fa68e91403f69f2134e02fff463e33ce6d40528 ProtectedCustodyMetadata.cpp
bd06910ff63ede37586eb35299abb20a684483d1b2b5cf17ff219bc1334e6aeb ProtectedCustodyMetadata.h
25a455b078190916013e01aad3d4b32bd6c6ec9e41b4648b16b73987db679493 V5LocalRecordingWriterTests.cpp
```

Production cpp/Metadata.h diff прочитан против wav27 copies с проверенными
совпадающими aac37 hash entries, не против полного исторического Git diff.
File.h private inventory declaration/комментарий и все его callers просмотрены;
нового public authority entrypoint или wire поля не найдено.

### H1 — старый WAV refusal противоречит newly supported empty birth

Frozen aac38 V5tests:526 в coldWavRefusals fault4 по-прежнему выбирает
RecoveryEvent{2,0}; :530 прерывает genuine child, затем без порчи playback
:545 вызывает recover и :546 безусловно требует !refused.ok(). Caller
--cold-recovery-wav:1019–1020 всегда запускает этот helper после positive WAV.
Но новый full-matrix playbackReady :420 включает тот же role2/op0/cut8,
:465 требует recovered.ok(). Оба fixtures начинают с coldCrashFixture([])
и доходят до того же physical cut; различается только противоположный assert.
Рабочая корректная реализация не может удовлетворить обоим expectations.
Фильтр --cold-recovery-playback этот sibling helper не запускает, поэтому
один будущий filtered GREEN скрывал бы доказанное несогласованное ожидание.

Уточнение main о birth верно: frozen Files.cpp:1325–1344 собирает prefix и BOTH
g1 HEAD в один32896-byte buffer. transfer:1289–1304 при таком размере делает
один WriteFile (<blockBytes). Test wrapper:118–120 вызывает op0 после успешной
записи, ДО flush; это process-crash cut, не power-loss. Полноту всё равно надо
подтвердить fresh BOTH proof: wrapper birth op0 сам не заменяет контроль
полного transfer. Нельзя объявить такой valid empty BOTH incomplete birth,
чтобы сохранить прежний D. Plan:2787/2791 различает эти состояния.

Минимальная безопасная правка — сохранить fault4 как настоящий negative,
но после cut создать ЯВНО incomplete/torn playback birth (и проверить shape
перед snapshot); затем оставить !ok, whole-tree equality и resource checks.
Например, укороченный playback с partial second HEAD вместо нетронутых BOTH.
Уже новый full-matrix cut8 проверяет valid empty positive. Не удалять refusal,
не заставлять production отказывать valid BOTH и не менять сроки/защиты.
Нужен отдельный exact test diff/source gate перед следующим runtime snapshot.

### M1 — граница полного exact-outcome заявления

Новая арифметика continued11 согласуется с baseline trace: WAV6/7 (2),
playback8..14 (7), completed22/23 (2); sealed24 отдельно S. Но started=false
ветка V5tests:480–483 всё ещё допускает success И refusal для первоначального
unused shape (cuts1/2), как и старый тест. Поэтому continued11 не означает
«все остальные12 — D» и не доказывает exact outcomes для всех24. Эти unused
cuts находятся вне valid-playback table462 и не должны молча получать D.
Замечание не расширяет partial-AAC контракт; перед заявлением полной24-cut
матрицы надо отдельно назвать прежний ordinary-unused outcome и его assert,
не вводя R-or-D или выбирая ожидание после исполнения. Для самого filtered
AAC cut этот branch не исполняется; C/H blocker текущего входа — H1 выше.

### Что source-проверка установила без runtime GO

- Причина прежнего RED — отсутствие started-playback layout: unused/wavReady
  inventory отвергали существующий packed output. Новый private layout
  пытается последним и только после recoveryRequired; успешная completed
  continuation не перекодируется. Старые layouts сохраняют прежние ветви.
- Metadata.cpp:1683–1687 оставляет canonical/media readExisting, playback
  получает fresh writeExisting только для новой ветви. Recovery остаётся unused;
  manifest pair generation/binding, exact role inventory и IDs/collisions
  :1701–1766 сохранены. RNG loop :1743 для playbackStarted пуст: новых IDs нет.
- Files.cpp:1471–1499 разрешает reusePlayback только private prepared+
  discoveredContainer+writeExisting+playback, требует исходный writable child,
  healthy state/root/package/context. Readonly→write upgrade не добавлен.
  :1540–1561 открывает OPEN_EXISTING, обнаруживает container на том же content
  handle и проверяет prefix; old public legacy route не стал production factory.
  completedPackageRole:722 допускает writable playback только в inventory-only
  проверке; имена/тип/точный набор/unknown children проверки не ослаблены.
- V5.cpp:212–243 выполняет unfinished/history/canonical, strict WAV BOTH/extent
  и playback BOTH proof до эффекта. Layout finalizing гарантирован в acquisition,
  поэтому retainPrefix:722–723 не делает initial capturing→finalizing write.
  :740 вызывает SAME writeWav compare/EOF/zeroRead/cancel и sealAudio(false)
  до writePlayback. Новый :454–462 открывает writer по full proof, передаёт его
  shared_ptr с прежним charged allocator и делает явный logical SetSize0.
- Writer::resize:169–178 и Tree::commitBlock:204–218 сохраняют empty no-op либо
  nonempty generation+1. Guard reserve:1429–1435 считает прежние physical bytes,
  включая orphan; Tree append адресуется после actual EOF. Старые bytes/IDs не
  удаляются, новых truncation/cleanup/nonce counters не добавлено. Writer open
  same-size validation не публикует HEAD. Отказ allocation/shared conversion
  освобождает writer; existing State failure/owner block и recoveryPending=false
  :189 запрещают повтор на том же recovery object. Same MF drain/shutdown,
  checkpoint/hash/decode/full sealed inspection :553–577,745–754 сохранены.

Это source observations, не уже выполненная zero-reset/nonempty-reset/orphan/
cancel/fault/repeated acceptance. Других подтверждённых C/H в просмотренных
ветвях не выявлено, но H1 не разрешает выдавать итоговый source GO. Frozen
aac38 не объявляется GREEN и не должен подменять будущий исправленный вход.
Только этот append; код, нормы, tasks, checklist markers и чужие записи не менялись.

## Round462 — AAC40 final: повторный scoped source gate после H1/M1

**SOURCE GO на frozen AAC40 до runtime; C0/H0/M0.** Прежний AAC38 NO-GO выше
сохранён: он относится к тому snapshot, а не стирается после исправления.
Применён code-reviewer, проверены только actual test delta и ближайший control
flow с учётом ранее просмотренного unchanged production. Нового полного
requirements/checklist/feature audit не было; VM/build/tests/Git/GitHub не
запускались. Разрешённый append внесён только в этот отчёт.

### Привязка окончательного источника

External `aac40-green/source.sha256` SHA256:
`335a4b036bafa325f0a291551ea5d9787db3235781c0ea255dfa32b2628b18a7`.
prior.sha256 побайтово совпадает с aac37-red/source.sha256, не AAC38/AAC39.
216 paths в prior и current; ровно6 manifest differences против AAC37,
точно changed.json, все6 staged file hashes совпали с current entries.
Сравнение полных manifests AAC38→AAC40 дало только V5tests: все5 production
файлов имеют прежние AAC38 SHA, не переоцениваются как новый патч.

Final V5LocalRecordingWriterTests.cpp SHA256:
`ae79c779bb1685aab7ac195c17de528cb6fb48ff02ee933ea55532646c09fac1`.
AAC38→39 diff прочитан полностью; AAC39→40 — ровно одна stderr summary строка
:566: invalid_partial_peer=3, started_outputs=1 вместо2/2. Это корректирует
описание fixtures, не runtime assertions/порядок/счёт executions. AAC38 и AAC39
не исполнялись и superseded по сообщению main; execution evidence им не дано.

### H1 закрыт в source, отказ для incomplete birth сохранён

Frozen AAC40 test:532/536 всё ещё получает genuine child role2/op0/exit88.
Затем :548–551 в отдельном scope открывает full coldPackedProof и требует
generation1/logicalBytes0. Helper через native owner+Tree::verify проверяет
BOTH; тем самым полный birth не объявляется повреждённым по имени cut.
Scope кончается ДО :552, поэтому пробный Tree/owner/native leases освобождены
перед resize. Реальный generated content.packed-v2 затем укорачивается до16576,
:553 проверяет physical size: сохранён prefix128+первая HEAD16384, от второй
HEAD лишь64bytes. Теперь это действительно torn/incomplete playback birth.

Whole-tree before snapshot расположен ПОСЛЕ этой deliberate fixture mutation
:555, а свежий store/recover — :557–560. Прежние !ok/non-none :561,
whole-tree equality и charged-resource equality :564 не ослаблены. Positive
valid empty BOTH в основном full-matrix cut8 больше не противоречит этому
negative. Итоговые7 cases и новый summary согласованы: три invalid/partial
peer — WAV invalid, WAV partial, playback torn birth; один started output —
pre-index recovery DATA/temp. Singleton coverage по нему не заявляется.

### M1 закрыт в source: unused outcome выбран до исполнения

- :391–392 требует начальные role5/op2 и role5/op3, а :424 заранее задаёт
  unusedReady=cut<=2. Эти ordinals связаны с asserted physical trace, не с
  выбором более удобного результата после recover.
- :483–488 больше не содержит either-success-or-refusal: требуется unusedReady
  И recovered.ok(), затем semanticVerified/trustedPrefixRetained/degraded,
  duration1000, !normalPackage/!keepablePackage; отдельный unusedRecovered++.
  Если unexpectedly started, сработают последующие fresh inspection/счётчик:
  один permissive D branch не даст всему тесту ложно завершиться PASS.
- :491–514 сохраняет canonical/queue/original ID checks и включает unused
  в fresh store/readPackage/full cold degraded+AАC/history/time inspection с
  no-write hash equality после readonly inspection. Окончательный :520 требует
  full continued11 И unusedRecovered2; filtered требует continued1 И zero unused.
  :516/522 отдельно печатают per-cut unused_ready и recovered_unused.
- В baseline24 это фиксирует13 успешных recoveries: ordinary unused1/2,
  derived WAV6/7 и playback8..14 (9), completed22/23 (2), отдельно sealed24 S;
  started D остаются3/4/5 и15..21 (10). continued11 намеренно не включает
  unused2; counters теперь не скрывают различие. Если новое unused R не пройдёт,
  это новый runtime blocker, не разрешение вернуть условие R-or-D.

Source-derived обоснование ordinary-unused R не требует нового product rule:
до derived birth роли id-only; прежний openUnfinished unused принимает valid
capturing/finalizing pair и старую unfinished history, а публикации используют
уникальные index.tmp имена вместо overwrite старого orphan. Данный source GO
НЕ доказывает, что fresh runtime каждого такого cut уже прошёл: ASSERT выбран
до запуска и должен быть квалифицирован сохранённым результатом отдельно.

Нет новых compiler/type/header рисков в рассмотренной delta: использованы
существующие helper/filesystem calls/unsigned counters; printf новые scalars
сохраняют соответствующие %u arguments. Release owner scope явный. Старые
deadlines, resource/security assertions, десять AAC preflight negatives,
measured generation, strict growth и сохранность old extent не изменены.
Filtered AAC40 ещё не проверяет sibling WAV fixture либо full24 сам по себе.
Long MF>256KiB, repeated/post-effect faults, полные regression suites и общий
P2/T116/application/installed/hardware/release GO остаются открытыми.

## Round462 — AAC40: независимая квалификация завершённого filtered runtime

**Scoped runtime GO для ProtectedRecoveryPlayback в AAC40.** Проверены только
сохранённые материалы aac40-green: result.json, result.xml, полные build.log и
test.log (UTF16LE), actual-test.log, validate-input.ps1, оба manifest и changed.json,
шесть frozen source files и соответствующий неизменённый остаток source216.
AAC41, его журналы, VM, сборки, тесты, Git/GitHub не затрагивались.

- SHA256 source.sha256 =
  `335a4b036bafa325f0a291551ea5d9787db3235781c0ea255dfa32b2628b18a7`;
  receipt.manifest совпадает. prior побайтово равен AAC37/source.sha256.
  Оба списка содержат216 уникальных путей; ровно6 различий, точно changed.json.
  Все6 frozen файлов совпадают с записями; остальные210 проверены по текущему
  authoritative repo, отсутствий/расхождений0. Frozen test SHA =
  `ae79c779bb1685aab7ac195c17de528cb6fb48ff02ee933ea55532646c09fac1`.
- receipt: terminal=true, configuration=Debug, target=V5LocalRecordingWriterTests,
  test_pattern=ProtectedRecoveryPlayback, build=0, test_exit=0, executed_tests=1,
  postflight=216, owned_processes=0, failure отсутствует. Полный build.log
  заканчивается успешным выпуском Debug/V5LocalRecordingWriterTests.exe;
  test.log: 1/1 PASS, CTest total30.94s. XML: ровно1 testcase с точным именем,
  status=run, time=30.9243, failures=0, disabled=0, skipped=0; нет failure/skipped
  children. Suite time=30 округлён, не заменяет точное testcase time.
- PE по сохранённому receipt:
  `816a8c078b64be6bf07e0db2defb8e49a29bef45a04ef0a3a8d578b43e2d1ad5`,
  6997504 bytes. Сохранённый harness проверяет Owned=0 до работы, prior216,
  staged hashes, current216 до build; после CTest — source216 и неизменность
  PE относительно pre-test hash; иначе ставит failure. Финальное owned=0 и
  отсутствие failure подтверждают прохождение этих guards по receipt. Сам PE
  в stage отсутствует: это проверка сохранённого receipt+guard logic, не новая
  независимая live GetFileHash. Session33118 exit0 сообщён main, не перепроверялся.

Полный LastTest.log, в отличие от усечённого XML system-out, содержит все24
последовательных trace events, десять COLD_PLAYBACK_REFUSAL case0..9, затем
OLD_GENERATION=2 и выбранный ordinal12 role2/op6, child_exit=88 waited=1,
started=1 continued=1 playback_started=1. Итог trace_events24/executed_cuts1,
continued1/recovered_unused0, process_crash1/power_loss0 и Test Passed; нет
пропусков, timeout, assertion или незавершённого хвоста. Фактический CLI:
Debug/V5LocalRecordingWriterTests.exe --cold-recovery-playback. Совпадает с
CMake ProtectedRecoveryPlayback (RUN_SERIAL TRUE, TIMEOUT180); исходник
отменяет NDEBUG перед cassert и вызывает playback branch без раннего skip.

Достижение end PASS сопоставлено с frozen test:277–286 (CreateProcess, wait60s,
exit88, закрытие handles), :309–361 (10 отказов с hash/resource equality),
:442–445 (реальная BOTH proof generation), :468–477 (обязательное recover/finalize,
degraded/trusted/1000ms, no normal/keepable, WAV hash, EOF строго больше и прежний
prefix+append extent неизменён), :491–514 (canonical/queue/ID equality, release
первого store, fresh store+sealed playback generation>measured exactly1,
full inspection/AAC decoded/history/session/time1000/1500, readonly hash equality),
:515–522 (memory equality, capacity4jobs/32pins, filtered counters1/0/0).
Это подтверждение выполненных assertions по source+полноценному завершению,
не утверждение, что каждая проверка печатает отдельную строку. Child stdout
отдельно не сохранён; child receipt в журнале печатает parent после assert wait/88.

Несоответствий для этого bounded runtime не найдено. Доказан короткий
first-HEAD AAC process-crash сценарий и10 preflight отказов. Full24, sibling WAV
H1, unused M1 здесь не исполняются; AAC41 не квалифицируется заранее.
Long actual partial>256KiB, repeated/post-effect faults, прочие регрессии,
power-loss, hardware/continuity, performance, полный P2/T116 и готовность
Windows-приложения к выпуску этим результатом не закрыты. Старые RED/NO-GO
сохранены. Изменён только этот собственный append; нормы/tasks/markers и чужая
validation запись не менялись.

## Round462 — AAC41-v5: квалификация четырёх завершённых regression CTests

**Scoped runtime GO для сохранённого AAC41-v5, 4/4 PASS.** Прочитаны целиком
result.json/XML, actual-test.log, build.log/test.log (UTF16LE), validate-input.ps1,
changed.json и source/prior manifests. Это не повтор requirements gate и не
полная приёмка T116. AAC42/его журналы, VM, процессы, сборки/тесты и Git/GitHub
не затрагивались. Применено ограниченное сопоставление по code-reviewer.

source.sha256 и prior.sha256 побайтово совпадают с AAC40/source.sha256:
`335a4b036bafa325f0a291551ea5d9787db3235781c0ea255dfa32b2628b18a7`.
changed.json пуст; 216 уникальных входов. Все216 повторно сопоставлены с
frozen6 AAC40 и остальными210 authoritative repo, расхождений/отсутствий0.
Harness побайтово равен AAC40: prior/current source guards216, PE до/после,
Owned до/после и deadlines не изменены. Receipt: terminal=true, Debug,
target=V5LocalRecordingWriterTests, build0/test_exit0/executed4/postflight216/
owned_processes0, failure отсутствует. PE совпадает с AAC40:
`816a8c078b64be6bf07e0db2defb8e49a29bef45a04ef0a3a8d578b43e2d1ad5`,
6997504 bytes. Это сохранённые receipt+проверки harness, не новый live PE hash;
session62028 exit0 сообщён main, отдельной проверки session не выполнялось.

XML: ровно4 точных testcase/status=run, failures0/disabled0/skipped0, без
failure/skipped children. Точные testcase времена:

| CTest | XML seconds | Фактический CLI |
|---|---:|---|
| V5LocalRecordingWriterTests | 143.562 | default, без аргументов |
| ProtectedRecoveryReturnedFaults | 47.2852 | --cold-recovery-returned-faults |
| ProtectedRecoveryCompletion | 17.668 | --cold-recovery-completion |
| ProtectedRecoveryWav | 19.5277 | --cold-recovery-wav |

Полный build.log завершается Debug EXE, без ошибки. test.log подтверждает
последовательный Start42→55→56→57, 4/4 PASS, total228.05s; actual-test.log
содержит четыре соответствующих Command и четыре Test Passed до End testing.
Усечённые XML system-out не использованы вместо полного LastTest.log.

Default V5: полный trace24 и cuts1..24 без пробелов/дубликатов, каждый child
waited1/exit88. Успехи ровно1/2,6/7,8..14,22/23; D3..5,15..21 и отказ recover
на sealed24. Summary: executed_cuts24, continued11, recovered_unused2,
sealed_cold_decode1, process_crash1/power_loss0. Итого13 восстановлений,
10 D и1 S, без R-or-D. Семь измеренных old generation перед AAC8..14:
1,1,1,2,2,2,2. Frozen source :424,468–520 подтверждает обязательность этих
ветвей, неизменность canonical/queue/IDs/WAV/old extent, рост EOF/generation,
fresh full cold inspection и ресурсы до итогового PASS. Initial1/2 действительно
прошли unused assertion+fresh inspection (M1), не скрылись за отказом.

ReturnedFaults: все26 per-case hit1/rejected1 и итог exact_memory/canonical IDs
queue unchanged/late seal cold decode. Completion: cases5, positive2, refusals3,
generation+1, five-members/IDs/queue unchanged, cold AAC/history, exact memory.
Wav: trace24, выбран только cut7 role1/op6, continued1; затем case0..6 и summary
unknown_tail1/wrong_pcm1/invalid_partial_peer3/started_outputs1/cancelled1.
Case4 действительно выполняет frozen :548–553: BOTH g1/zero proof, освобождение
owner, resize16576/file_size assert, затем fresh refusal и disk/resource equality
:555–564. Таким образом H1 проверен runtime, не только исправлена строка summary.

Несоответствий в этом завершённом наборе нет. Результат не заменяет отдельный
AAC40 playback-filter с10 отказами, но дополняет его полной short24 матрицей и
существующими recovery regression paths. Long actual partial>256KiB, repeated,
faults именно нового playbackStarted пути, Tree/Files/Native13, hardware,
power-loss/continuity/performance и полный P2/T116/application/release остаются
открытыми. Только этот append; нормы/tasks/checklists и чужая validation запись
не менялись. Старые RED/NO-GO сохранены.

## 2026-10-20 / Round462 — scoped requirements gate для real long partial AAC

**Requirements GO перед test-only long construction; CRITICAL0/HIGH0.** Это
продолжение существующего high-risk-product T116/#7444, plan462/CHK035–041,
а не новый product scope, actual-diff GO, runtime PASS либо закрытие Windows.
Проверка применимых implement/checklist и analyze gates выполнена независимо;
реализация, ignore setup, tracker sync/closeout и hooks с мутациями не запускались.
В extensions before/after analyze/implement commit hooks disabled; изменения
нормативов/markers не нужны. Prerequisite reader вернул текущий feature200.
Feature pointer содержит branch codex/200-windows-followup и source_sha
b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1; Git не запускался. Все current216
файлов совпали с manifest335a4b036bafa325f0a291551ea5d9787db3235781c0ea255dfa32b2628b18a7.
AAC42 runtime в этом gate не квалифицировался. VM/build/test/network не было.

Перечитаны действующие plan462:2704–2808, quickstart462:1167–1196,
research462:3151–3179, data-model462:679–687, packed contract:378–403,
FR-012/013/014/022, Start-owner, SC-003/005/006 и constitution7.1.0.
Проверены сохранение старых unused/completed/WAV правил и границы T117–T120.
Полная историческая реализация/checklist evidence не переоценивалась как PASS.

### Checklist gate и применимость

Все12 действующих тематических checklist критерии прочитаны на текущих файлах;
итог205 checked /0 unchecked. Повторный scan всей папки находит31 файл с
checkboxes, 471 checked /0 unchecked (включая19 исторических gate/source файлов;
это marker inventory, не новое утверждение их полного source/runtime review).

| Тематический checklist | Checked | Unchecked |
|---|---:|---:|
| advanced-routing | 14 | 0 |
| audio-capture | 24 | 0 |
| calendar-launcher | 5 | 0 |
| calendar-operation | 8 | 0 |
| calendar-wire | 5 | 0 |
| cold-prefix-recovery | 41 | 0 |
| packed-writer | 12 | 0 |
| privacy-pause | 12 | 0 |
| requirements | 22 | 0 |
| security | 27 | 0 |
| start-owner-recovery | 10 | 0 |
| ux | 25 | 0 |

Cold CHK035–041:7/0, все supported именно как требования. Admission/leases/BOTH
до эффекта остаются CHK035–037; nonempty reset+1, empty no-op и preservation —
CHK038; quotas/failure/drain/repeated — CHK039; degraded-only/no account/upload —
CHK040; реальный MF partial>256KiB и отдельные evidence gates — CHK041.
Packed/security/start-owner/privacy критерии сохраняют encrypted temporary,
immutable owner/queue, no readonly upgrade, no repair, реальные retirement и
неизменность privacy history. Audio/routing/UX/calendar требования не изменяются:
fixture не читает устройства и не принимает UI/hardware/SC-003. Markers/notes
не менялись, потому что нового requirements gap в данном срезе не выявлено.

### Обязательства test construction и оставшаяся feasibility

1. Baseline — полный настоящий recovery/MF60s того же deterministic finite
   canonical prefix:6000 полных480-sample frames, затем прежний47-float tail.
   Tail не включать в duration/encode, не обрезать canonical; finite требование
   относится к полным frames (прежний NaN в неполном хвосте не чинить).
   2,880,047 floats =11,520,188 bytes: charged/wiped CustodyBytes либо тот же
   CustodyAllocator, не массив12MB в stack/обычный uncharged whole-file buffer.
   Fixture allocation должна реально освободиться до финального idle equality.
2. Existing native hooks/child path, не подставленные AAC/файлы/encoder.
   Выбрать второй фактический role2/op6 из baseline trace, assert существование
   и ту же identity события в child, wait/exit88. Actual fresh BOTH tree должен
   дать committed logicalBytes>262144 И < baseline complete AAC logicalBytes.
   Одного ordinal, physical EOF, target bitrate или размера fixture недостаточно.
   При несовпадении — feasibility failure, не fallback на первый/short cut и
   не перевод результата в допустимый D. До run ожидаемый outcome — R.
3. Дополнительная old-AAC проверка через уже public readProtectedPlayback(Tree,
   60000,cancel) допустима и желательна: LocalRecordingPackage.h:125,
   .cpp:821–830 уже дают worker-only bounded codec evidence без package/account
   authority. Полный baseline должен декодироваться на тех же prerequisites.
   Если заявляется, что старый AAC не является полным60s, подтверждать реальную
   codec/content/duration неготовность, а не принимать любой !ok из-за quota,
   cancellation/COM/OS IO как доказательство partial. Нет нужды придумывать новый
   decoder/API или ослаблять production validator. Читаемые shorter stream/ошибка
   codec сами по себе не порча canonical. Все пробные readers/proofs/owners
   освобождаются до fresh existing-only recovery store.
4. Финал — existing re-encode полного60s, exact60000ms/degraded/trusted,
   !normal/!keepable/HTTP0, original IDs/owner/queue, неизменные canonical/WAV,
   old playback prefix+[appendOffset,oldEOF), monotonic actual generation/EOF,
   full fresh cold AAC/privacy/optional times/history inspection; readonly
   reinspect не пишет. Не переносить one-second hardcoded duration/expectations.
   Existing coldShortPlaybackBytes:363–374 намеренно ограничен fixture<1MiB и
   uncharged string; его нельзя расширить/использовать как unlimited long copy.
   Long сохранность проверять bounded comparison/hash с явными range/length
   assertions, исключая только две изменяемые HEAD cells, не прежний tail.
5. Production frame loops уже подходят без нового encoder:
   V5.cpp:366–447 writeWav тот же converter/strict EOF/zero-read;
   :450–575 writePlayback прежний MF/frameCount и full decode; writer loadDirty
   :135–153 публикует предыдущий block перед переходом, а native hook :80–100
   фиксирует реальные HEAD. Второй HEAD не равен гарантированно partial>block:
   именно поэтому обязательны измерения из п.2. Trace256 не повышать.
6. Existing child wait60s + cleanup10s и serial CTest180 остаются. Сам baseline,
   generated fixture, child и второй recovery входят в whole-run budget;
   60s аудио не обещает60s исполнения. Global reader cache один256KiB
   (Reader.cpp:19–31,130–163); writeWav чередует canonical1920/WAV320 и может
   вызывать повторные cache misses/decrypt/native checks на6000frames.
   Это source-backed performance risk, не диагноз и не разрешение cache/product
   patch либо ослабление Guard. Пределы job4/pin32/owned64MiB/dirty/physical cap
   прежние. Timeout/trace-limit/quota недостаточность сохраняется как blocker
   следующего source/runtime этапа; отдельная конструкция до изменения сроков.

### Scoped analyze / границы

Покрытие выбранного требования real partial: FR-012 integrity/encrypted logical
IO + FR-013 owner/queue + FR-014 no HTTP + FR-022 lifecycle, существующая T116,
plan462 acceptance и CHK035–041. Семь критериев mapped7/7; unmapped новый task0,
product questions0, constitution conflicts0, C0/H0. Это не feature-wide coverage
percentage. Согласованность empty/nonempty/immutable sealed/orphan/history и
единственных R/C/D/S сохранена. Существующие короткие RED/GREEN не объявляются
long evidence; новый source diff должен отдельно проверить размеры/casts,
lifetime, диапазоны сохранности, точный chosen event и старые default branches.
Long runtime, repeated/post-effect faults, Native13/прочие regressions,
полный P2/T116 и Windows parity/installed/hardware/release остаются открытыми.

Точные SHA256 текущих нормативов (совпадают с ранее принятым final462 там,
где зафиксированы; checked markers не обновлялись):

```text
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859  constitution
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11  spec.md
5fff84e64d6c9acb7bc365a56ec8b63ab0594bca7219da312965f4a889d10c9d  plan.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f  tasks.md
32dc689aef2066d5444e9b10598ce3cc9214d22922478f8773ff5de374726248  research.md
49f8623498842b6a2ef57243398c1c4c1230a1009a60d364e839f230750374b3  data-model.md
fd906ccbdb28355005db083badedfe6641f09cf0186deb6be7dadb4787e5f5d8  quickstart.md
f610c70062ee13711b1989b88562b3403458589701b445c0ba763ccac635ffea  windows-protected-packed-custody.md
a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490  windows-protected-local-custody.md
8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4  windows-desktop-contract.md
9c7f0301ef5bfdf567d43e3abb48a84cf62870c5c43a082008588df286121116  cold-prefix-recovery.md
1684307dd5d9ea36d9939842b53764839b87b6247e1a744e63d6640426189ec7  start-owner-recovery.md
a1f18f2cdfe6ebcdb369ad0ed6a877f77af4658bc388a4cab1475c50b45b62a0  packed-writer.md
5e1c0a89ebb33f47876fafd345972e3e627e6597504d6b6a5dc4c8ac1ab10eec  privacy-pause.md
0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273  security.md
```

Дополнен только этот отчёт; прежние NO-GO/RED и нормативы/checkboxes сохранены.

## 2026-10-21 / Round462 — AAC43 long partial: actual test-only SOURCE gate

**Scoped SOURCE GO; CRITICAL0/HIGH0.** Только предъявленные два test-only
файла и long function перед первым runtime; не runtime PASS и не T116 GO.
Сравнение manifest AAC42/AAC43:216/216, ровно два изменённых пути; все216
текущих файлов совпали с frozen AAC43, остальные214 (production) неизменны.
Старый тест AAC40 побайтно соответствует AAC42 manifest; удаление ровно двух
новых CMake строк в памяти восстанавливает baseline SHA. Git/VM/build/tests
не запускались. Requirements/history/checklists заново не переоценивались.

```text
504baa56d9d70667a564eb9849cf47d09288e0e64712dfbabbf2d1deac100164  aac43-partial/source.sha256
603e77cfd4497585572298bc6bc043bc47e85db0f43adc98c8b298e42c95a9d4  V5LocalRecordingWriterTests.cpp
8d30d891adecf889dbf2a3ca3dd42ed1ec4b184891f18c44d4fa6426ad465e31  CMakeLists.txt
```

- Test:230–258 сохраняет default100 (0.25F/последний NaN/47-float tail),
  long6000 использует конечный детерминированный noise в полном prefix.
  11,520,188 bytes хранятся в CustodyBytes, освобождаются до checkpoint;
  allocator реально charge/wipe/deallocate, не 12MB stack. Existing callers
  и wrongPcm100 не изменены. Include mferror.h предоставляет новые MF constants.
- :415–436 baseline делает настоящий recovery/MF, semantic finalize, измеряет
  complete logical bytes. Выбор считает именно второй role2/op6; child использует
  тот же fixture и существующие wait60s/cleanup10s/assert exit88/identity hooks.
  Trace256 остаётся. :444–459 свежий BOTH proof измеряет actual generation и
  требует blockBytes<partialBytes<completeBytes. Decoder принимает только
  content-specific MF HRESULT (INVALIDMEDIATYPE/INVALID_FILE_FORMAT/
  UNSUPPORTED_BYTESTREAM_TYPE), не произвольный IO/quota/cancel failure.
- :387–404 bounded64KiB scratch хеширует prefix128 и каждый byte диапазона
  [appendOffset,oldActualEOF), исключая только две HEAD cells. :470 требует
  strict EOF growth и равенство всех старых range hashes, включая старый tail.
  Сохраняются whole canonical/все исходные IDs/queue/WAV hashes.
- Old proof/decoder releases предшествуют fresh recovery store (:460–462).
  :465–468 требует full60000ms/trusted/degraded/!normal/!keepable. Fresh cold
  pair/inspection проверяют sealed playback generation>measured, full AAC,
  session/history timestamps/timezone и исходную privacy запись. Временный
  inspection освобождается до дополнительных readers; scopes завершаются до
  readonly disk equality/idle memory и проверки доступности4jobs/32pins (:501–503).
- CMake:184–185 добавляет только отдельный existing-target CLI,
  RUN_SERIAL TRUE/TIMEOUT180; default CLI и прежние cut expectations неизменны.

Доказанного compile/source blocker или пути ложного PASS в этом diff не найдено.
Это допуск первого запуска exact frozen source, не гарантия его feasibility:
second HEAD size, конкретный codec отказ и whole-run180s должны реально пройти.
Иной HRESULT/недостаточный размер/timeout — сохранить как отказ/ограничение
конструкции, не объявлять partial accepted и не расширять допуск молча.
Repeated/new-path faults/full suites/hardware/full P2/T116 остаются открытыми.
Дополнен только этот отчёт; старые RED/NO-GO и остальные файлы не менялись.

## 2026-10-21 / AAC43 follow-up — diagnostic-only source gate

**Scoped diagnostic SOURCE GO; CRITICAL0/HIGH0.** Сравнение с frozen AAC43
603e77cfd4497585572298bc6bc043bc47e85db0f43adc98c8b298e42c95a9d4:
из216 только V5LocalRecordingWriterTests.cpp изменён; текущий SHA256
8d08cc4fdbf3f621c6ba368fbe4fa6e046420e76264a85e3f06528390aeb1f3c.
CMake/production/остальные215 совпадают с прежним manifest. Это допуск
диагностики, не исправление failure и не повторная полная приёмка.

Точный diff добавляет failure-only fprintf перед прежним assert (:297–299),
локальный GetTickCount64 origin и синхронную phase lambda (:409–413), восемь
scalar phase calls вокруг существующих этапов. Lambda захватывает ещё живой
локальный origin, никуда не сохраняется; вызовы не помещены в native hooks,
mutex boundaries, покадровый цикл или callbacks. %lu соответствует DWORD,
elapsed приведён к unsigned long long для %llu. Новых wait/poll/deadline,
изменения branch predicate/assert/fixture/limits/порядка продуктовых действий нет.
Child marker выводится только ПОСЛЕ успешного прежнего wait/exit assert, а
old_partial_proved только после proof/codec assertions и readonly hash equality.

Ограничение интерпретации: wait — исходный результат WaitForSingleObject;
exit получен ПОСЛЕ прежней cleanup (при timeout возможен принудительный exit90),
а не обязательно самостоятельный exit дочернего процесса. GetLastError для
WAIT_FAILED не добавлен: по этому выводу можно отличить timeout/failed wait/не88,
но нельзя восстановить точную Win32 причину WAIT_FAILED. Phase deltas включают
все действия между stamps, не являются профилем CPU/отдельных native API.

Исходный AAC43 FAIL остаётся сохранённым; сообщённые178.22s/line297 не
переобозначаются как long/partial PASS или доказанная причина. Runtime receipts
нового запуска будут отдельным gate после terminal; здесь старый runtime
независимо не квалифицировался. Только append отчёта; VM/build/tests/Git,
нормы/checklists/source и исходные evidence не менялись.

## 2026-10-21 / AAC44 timing — независимая квалификация завершённого FAIL

**Scoped evidence qualification GO для genuine FAIL, не runtime acceptance.**
Полностью прочитаны saved result.json/XML, build.log/test.log/actual-test.log,
validate-input.ps1, changed/prior/source manifests и frozen test. Source216
совпадает с current216; prior точно AAC43, единственный delta — diagnostic test.
Manifest ea399366410ac9adf2fc212eb4e33aa1f9666ff54fc4ed00b9b6c533bd62e308;
test8d08cc4fdbf3f621c6ba368fbe4fa6e046420e76264a85e3f06528390aeb1f3c.
Receipt: terminaltrue/Debug/build0/test_exit8/executed1/postflight216/owned0,
failure TEST. PE c4f084622e50ac12e157ead0aafefc0aca84dc8ca84e58c914cca8fb3d8ed9cf,
7,041,024 bytes; harness хеширует до CTest и сверяет после postflight.
Это проверка сохранённых PE guards, не новый независимый guest hash.

JUnit: ровно ProtectedRecoveryPlaybackPartial, fail170.341s, failures1,
disabled0/skipped0. Actual command — Debug/V5LocalRecordingWriterTests.exe
--cold-recovery-playback-partial; не иной CLI. CTest summary170.36s и display
170.34s не заменяют testcase170.341s. NativeCommandError в PowerShell — wrapper
после реального CTest8, не самостоятельная причина failure.

Stamps: baseline fixture0→9687ms; baseline_recovered100500ms (разность90813ms
после fixture ready включает owner open/recover/finalize/releases, не профиль
writeWav); partial fixture100672→110015ms. Затем cut28/role2/op6 wait258,
exit90 и исходный assert line299. WAIT_TIMEOUT подтверждён самим результатом
wait;90 — прежний parent-forced cleanup. Это НЕ CTest180 timeout, не exit88,
не доказанный deadlock/ошибка кодека/скорость отдельного метода. Child cut,
old partial BOTH/codec proof и повторный partial recovery не приняты: markers
child_reached_cut/old_partial_proved/partial_recovered отсутствуют.
Generated-only/device_audio_read=false/real_network=false/installed=false;
native_metadata_probes=false — поле harness, не отсутствие filesystem IO.
Исходные AAC43/AAC44 FAIL остаются evidence, long partial пока не принят.

## 2026-10-21 / Round464 — scoped Requirements + Analyze gate writeWav32

**Requirements/Analyze GO; CRITICAL0/HIGH0 (M0/L0 в данном delta).** Только
append464 в plan/quickstart/research внутри существующего high-risk T116/#7444.
Обратное удаление последних append в памяти восстанавливает точные ранее
принятые SHA всех трёх файлов. Production216 пока совпадает с AAC44. Изменять
spec/constitution/data-model/contracts/tasks ради этого уточнения не требуется;
это не новый продуктовый ответ или scope. Requirements GO не разрешает иной
кандидат, batching MF/writePlayback, новый cache либо снижение Guard checks.

Prerequisites read-only подтвердили feature200/tasks. Analyze hooks before/after
disabled, мутации/hooks commit не выполнялись. Проверены применимые constitution
II/IV/VI и delivery gates; FR-012/013/014/022, SC-005/006 связаны с открытой T116,
не возникает новой немаппированной задачи. Это scoped анализ, не повторный
полный feature analyze или подтверждение общих SC-005/006 runtime.

Plan464:2810–2832 задаёт bounded32 полных10ms кадров, canonical<=61440/PCM<=10240,
charged/wiped CustodyBytes; actual last batch без incomplete tail, тот же triple
arithmetic/toPcm16/sample order. Input reusable только после полной конверсии
порции. Cancel на каждой10ms conversion boundary и до effect, прежние actual
Read/writeAt Guard/sticky/short IO/full counts, RIFF/strict EOF/zeroRead/sealAudio
и readonly comparison обязательны. Resource/format/history/identity/R/C/D/S,
cache256KiB, child60s/serial180 и MF10ms неизменны. Quickstart464 требует тот же
long test/strict proof плюс last partial batch100/6000, negatives/cancel и
affected regressions на одном source; research отделяет гипотезу от причины.
Ни одна из этих формулировок не принимает AAC44 timeout как actual partial RED
нужной физической границы; прежний short actual RED не заменяет long proof.

Checklist scope: cold CHK029–041 сохраняют first-effect/bytewise proof,
readonly/immutable identity и failure/runtime separation; CHK035–0417/0,
весь cold-prefix41 checked/0 unchecked. Packed12/0, security27/0,
start-owner10/0, privacy12/0; их неизменные SHA подтверждены. Повторно оценена
применимость затрагиваемых критериев (особенно packed004/007/009/010 и
cold031/033/034/037/039/041), не выдан новый общий runtime GO всем пунктам.
Новых checklist/markers/notes не требуется, ничего из них не редактировалось.

```text
d19c5655e5df217bc6d9a94c345a1fe902a8b7d8863fe5200dd3b02a70044237  plan.md
31f64c8c7689cbba700e8d11ffa8870dad194bd526e11e5247a6190623638635  quickstart.md
31be2e948412ab276d097c4f72462985c00f7ca97a73bcf801bccf4a4929d418  research.md
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859  constitution
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11  spec.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f  tasks.md
9c7f0301ef5bfdf567d43e3abb48a84cf62870c5c43a082008588df286121116  cold-prefix-recovery.md
f610c70062ee13711b1989b88562b3403458589701b445c0ba763ccac635ffea  packed contract
```

Следующий gate — actual минимальный writeWav-only diff: bounds/last batch,
buffer aliasing, cancel/effect ordering, сохранение всех EOF/Guard/failure
проверок; затем отдельная runtime квалификация без повышения сроков.
Причина задержек, performance/hardware/полный P2/T116/Windows/release не приняты.
Только append этого отчёта; norms/code/tasks/checklists/VM/Git/GitHub не менялись.

## 2026-10-21 / AAC45 — actual writeWav32 SOURCE gate

**Scoped SOURCE GO; CRITICAL0/HIGH0.** Применён code-reviewer к exact frozen
AAC45 vs AAC44, не к историческому полному diff. Manifest216 SHA256
ea5bc294e98c4f2932de78bf0db75578901095578b5cbbb44fb8533697bff513;
prior точно AAC44 ea399366410ac9adf2fc212eb4e33aa1f9666ff54fc4ed00b9b6c533bd62e308.
Ровно один changed path — Recording/V5LocalRecordingWriter.cpp; frozen и
current216 совпали. Before cffaadf9ae1058865e4bf98e0919c140f7c2a5e0446159503f4d3e6bfda5ee0b
(проверенная frozen AAC40 копия совпадает с AAC44 entry); after
15c50778cca79d86104bf76c6ba7c3eeb7aca995c9c59e616c4233741f8acc1c.
Остальные215, включая тест/CTest/reader/writer/decoder/MF/cache, неизменны.
Plan464/quickstart/research hashes совпадают с предыдущим Requirements GO.

- Единственные writeWav callers: finalize:792 normal path после canonical
  checkpoint/seal/length и retainPrefix(playable=true):748 из finishRecovery:244.
  Nonplayable fallback writeWav не вызывает. Их order/failure/finalized guards,
  existing wavReady/playbackStarted acquisition/full proofs и финальный full
  inspection не изменены; writePlayback следует только после true writeWav.
- :389–394 buffers61440/10240 charged/wiped; header44 помещается в input.
  :415–419 frames=min(32,frameCount-index), поэтому inputBytes<=61440 и
  pcmBytes<=10240. :428–436 считывает ровно frames*480 floats и вычисляет
  frames*160 PCM samples: последний triple заканчивается ровно inputBytes,
  порядок triple/toPcm16/байтов идентичен прежнему циклу. 100frames→32/32/32/4;
  6000→187*32+16. Старые bytes хвоста буферов не читаются/не выдаются, неполный
  canonical frame не включён. frameCount ограничен canonical logical limit;
  переполнения offset/index из-за шага32 не добавлено.
- Input используется emit для WAV comparison только после всей conversion;
  источник bytes — отдельный pcm/header. Aliasing/перезапись ещё нужного input
  не обнаружены. Exact header/offset44+index*320/счёт emit не изменены.
- Cancel проверяется до/после canonical Read, на каждом at%160==0 и перед emit.
  Фактические Read/writeAt по-прежнему используют настоящие owners/Guard,
  chunk/final status, cancel/sticky/short-count guards, включая cross-block.
  Ошибки по-прежнему прекращают pipeline и сохраняют первый fail; после false
  нет перехода к AAC/normal. Новых bypass/retry/cache authority нет.
- :439–452 сохраняет strict WAV EOF Read1/S_FALSE/got0, canonical zero-read
  status/cancel и sealAudio(media,!existing). Existing comparison readonly,
  новый WAV — прежний writer/checkpoint/hash; allocation exceptions unwinding
  и caller catches прежние, CustodyBytes wipes при освобождении.

Доказанных source/compile blockers не найдено. Это допуск frozen AAC45 к
первому runtime, не утверждение ускорения/причины или long partial acceptance.
Проверить неизменённый long CLI в прежнем budget, затем short/WAV negatives,
24-cut и affected suites на exact source. Более крупный pending write может
изменить физическую границу interrupted staging: runtime exact-shape outcomes
нельзя молча ослабить при новом failure. Исходные AAC43/AAC44 FAIL сохранены;
full P2/T116/Windows/hardware/release не закрыты. Только append своего отчёта;
source/norm/checklists/VM/build/test/Git/GitHub не менялись.

## 2026-10-21 / AAC45 — scoped qualification TIMEOUT и read-ahead feasibility

**Saved evidence qualification GO для genuine TIMEOUT; runtime acceptance
NO-GO.** Полностью прочитаны result.json/XML/build.log/test.log/actual-test.log,
validate-input.ps1/changed/prior/source manifests; frozen production и current216
совпадают. Manifest ea5bc294e98c4f2932de78bf0db75578901095578b5cbbb44fb8533697bff513,
prior точно AAC44, единственный delta writeWav32. Тест exact AAC44 SHA8d08cc4f...
не менялся. Receipt terminaltrue/Debug/build0/test_exit8/executed1/post216/owned0,
failure TEST. JUnit ровно ProtectedRecoveryPlaybackPartial, fail180.02s,
failure Timeout, skipped0/disabled0. Actual CLI --cold-recovery-playback-partial;
CTest total180.03s. Это внешний CTest180 timeout, не прежний child wait60 timeout.
PE fe1830b74a2eff462b8c81f4c8f1fb0c1a15731f0eb8976ed43095a8bbc32c59,
7,041,024 bytes; saved harness проверяет до/после; нового guest hash не было.
PowerShell NativeCommandError — wrapper после фактического CTest8.

Stamps: fixture ready10156, baseline_recovered63625 (разность53469ms, не
изолированный writeWav profile); partial fixture63781→73031; child_reached_cut
108359; old_partial_proved108843; partial_recovered176750ms. Child marker
достижим только после waitobject0/exit88 assert. Actual old BOTH generation3,
logical524288>262144 и <complete732186; decode_error6/native c00d36c4 прошёл
specific-codec assertion и whole-tree no-write equality до old_partial_proved.
Partial recovery result assertions semanticVerified/trustedPrefixRetained/
60000ms/sealedDegraded/!normal/!keepable также пройдены до partial_recovered.
Это подтверждённые промежуточные точки, не полный PASS.

Далее source:483–519 проверяет original IDs/canonical/queue/WAV/old EOF extent,
fresh cold pair/generation/AAC/history/privacy, readonly hash equality и ресурсы.
Ни одного stamp между ними нет. Отсутствует финальный COLD_PARTIAL_RECOVERED:
нельзя заявить конкретную точку timeout внутри этого хвоста, завершение всех
перечисленных проверок, resource acceptance или full T116. Даже пройденная
внутренняя inspection recovery не заменяет незавершённую внешнюю cold проверку.
Generated-only: audio/network/installed false; metadata_probes=false не означает
отсутствия native filesystem IO. Исходные AAC43/44/45 отказы сохранены.

### Следующий минимальный кандидат — только canonical read-ahead в writePlayback

**Source feasibility положительная, не design/SOURCE/runtime GO.** Текущий
writePlayback:526–538 читает1920 на каждый n; :539–559 создаёт отдельный sample,
PCM960, time=n*100000/duration100000 и вызывает MF через прежний call wrapper.
Возможен один charged/wiped canonical buffer<=61440 и refill до32 полных frames,
последний actual min(32,remaining). В MF остаются прежние480 samples→960 PCM
на каждый n, те же conversion order/timestamps/duration/WriteSample/Finalize.
Это не смена MF packetization. Нет основания менять shared cache/Guard,
quota/admission/decoder/adapter/выходные буферы либо child60/CTest180.

Обязательства будущего exact diff: правильные offset внутри заполненного
buffer и последний batch; никакого чтения stale tail/incomplete canonical frame;
каждый refill — прежний actual Read/Guard с exact expected got, observedFailure/
cancel до/после через call. На каждой MF frame по-прежнему выполняются call
checks cancellation/output observedFailure, даже если refill не нужен.
attempted/read/got относятся только к реально выполненному refill: нельзя
принять устаревший got за short read или назвать уже существующий output failure
canonical corruption. Существующие close/drain/release/MFShutdown и полный
decode/seal остаются. Prefetched bytes — owned staging проверенных bytes,
не новая authority/допуск failed owner; plaintext не уходит на диск/в logs.

Read-ahead переносит возможное обнаружение canonical ошибки на более ранний
момент (до подачи первого sample порции); точная прежняя interleaving native
read/output faults не тождественна. Нельзя обещать сохранение точного порядка
двух независимых будущих отказов. Нужно сохранить первый фактически observed
fault и no-success/no-retry, отдельно проверить отмену и fault attribution.
Нет доказательства, что это обеспечит whole-run180: native IO/refill уменьшится,
но MF sample calls и внешний fresh decode/audit остаются прежними.

Текущий plan464 явно исключает writePlayback; для следующего шага требуется
узкий technical append с этими границами и отдельный requirements/source gate,
не новая product policy. Здесь никаких нормативов или production не изменялось;
только append собственного отчёта. VM/build/tests/Git/GitHub не использовались.

## 2026-10-21 / Round465 — scoped Requirements/Analyze read-ahead32 gate

**Requirements + scoped Analyze GO; CRITICAL0/HIGH0/M0/L0 в delta465.**
Проверены только финальные append465 plan:2833+, quickstart:1208+,
research:3193+ и применимые прежние требования. Обратное удаление append465
в памяти восстанавливает точные принятые SHA464 каждого из трёх документов;
464 WAV правила сохранены. Current216 полностью совпадает с AAC45 manifest
ea5bc294e98c4f2932de78bf0db75578901095578b5cbbb44fb8533697bff513.
Production не менялся. Prerequisites read-only вернули feature200/tasks;
extensions YAML parsed, before/after analyze hooks явно disabled.

Конструкция bounded canonical staging<=61440 через charged/wiped CustodyBytes,
refill<=32 полных frames и min(32,remaining) однозначна; n выбирает только
заполненный frame, не tail. Каждый реальный Read сохраняет Guard/exact-count/
call checks, собственные attempted/read/got; на каждом MF sample остаются
output observedFailure/cancel даже без refill. PCM960/480samples/toPcm16,
time=n*100000/duration100000/WriteSample и close/drain/MFShutdown/checkpoint/
decode/seal прежние. First-actually-observed sticky fault явно отделён от
необещаемой прежней interleaving; output failure не маркируется canonical fault.
Cache/admission/limits/wire/history/authority/R/C/D/S не изменяются.

Constitution IV/VI/quality gates, FR-012/013/014/022, SC-005/006 и открытая
T116 покрывают этот шаг. Новых unmapped requirements/tasks/product entities
или конфликтов с packed contract/data-model не выявлено. Это не новый
read cache/proof authority: staged plaintext уже прошёл настоящий Read,
не выходит на диск/в diagnostics. Более раннее обнаружение canonical fault
нормативно названо, sticky first-fault не ослаблен. Конфликт с464 отсутствует:
запрет менять MF samples сохранён, scope465 явно расширяет только чтение.

Применимость checklist повторно оценена в области cold035–041 (7/0),
packed first-fault/bounded-memory/read/EOF/lifecycle и security/local custody;
start-owner/privacy/immutable IDs/WAV unchanged. Current markers: cold41/0,
packed12/0, security27/0, start-owner10/0, privacy12/0; SHA всех этих файлов
неизменны. Нового пробела требований нет, markers/notes не менялись.
Это оценка требований, не новое подтверждение всего checklist runtime.

Quickstart требует именно финальный COLD_PARTIAL_RECOVERED, все cold/hash/
privacy/history/resource assertions и terminal/no-skip receipts, а не только
partial_recovered. Long6000/short100 явно проверяют последний refill16/4;
отмена и fault attribution отдельно включены. Прежние AAC43/44/45 failures
сохраняются, child60/CTest180 не повышаются. Ускорение/whole-run feasibility
ещё не доказаны. Следующий этап — минимальный actual source diff и отдельный
SOURCE gate до runtime, затем full affected regressions на exact final source.

```text
ed75a761a0c83b64e57740f60b1c78d1072ad16baaeed2f33a3f9ad526187b4d  plan.md
f604abca58264286253197bc3596cff437133a5c156abd51c6ede8bd5096f90e  quickstart.md
9124819664db586ae943b110ce3c2ad6751056153c906a031c670d9ecb63ac83  research.md
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859  constitution
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11  spec.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f  tasks.md
49f8623498842b6a2ef57243398c1c4c1230a1009a60d364e839f230750374b3  data-model.md
f610c70062ee13711b1989b88562b3403458589701b445c0ba763ccac635ffea  packed contract
9c7f0301ef5bfdf567d43e3abb48a84cf62870c5c43a082008588df286121116  cold-prefix-recovery.md
```

Полный P2/T116/Windows/installed/hardware/release остаются открытыми. Дополнен
только собственный report; code/norm/tasks/checklists/VM/build/test/Git/GitHub
не изменялись и не запускались. Исторический audit не переоценивался заново.

## 2026-10-21 / AAC46 — scoped actual read-ahead source review

**Read-ahead .cpp SOURCE GO, C0/H0; полный exact two-file gate пока НЕ выдан:
отсутствует проверяемая before-копия header.** Это evidence gap, не найденный
дефект production и не требование менять код/нормы. Manifest216
0870912ff9f3693e3a675029030c3883726558b9b5f4eff533d6d3e629e0d9f3,
prior точно AAC45. Ровно два changed paths, current216 совпадает с frozen.
Cpp before из AAC45 совпадает с prior entry; его exact diff полностью прочитан.
Cpp after904e53cd64f6db735ac0e5b83146bb6792a01eace5bebc1ad8fccb3473709aac.
Test/CMake/остальные214 неизменны, нормы465 совпадают с Requirements GO.

В cpp:528–545 within=n%32, refill только при0, actual count=min(32,remaining)*1920.
До61440 charged/wiped, собственные read/attempted/got только внутри refill.
На последнем batch within всегда меньше фактически заполненного числа frames;
offset=within*1920+at*4 при at<480 укладывается в заполненный frame, не stale tail.
100→last4,6000→last16. Canonical stream последовательный, Seek не добавлен.
Actual Read остаётся под прежним call/Guard/exact-count. Если output fault/cancel
обнаружены до попытки, attempted=false и canonical failure не подставляется.
Проверка short/failed read действует только при настоящей попытке.

При no-refill первый MFCreateMemoryBuffer всё равно идёт через прежний call,
проверяет observedFailure/cancel; остальные MF calls сохраняют проверки.
PCM960/480samples/toPcm16/time=n*100000/duration100000/WriteSample не изменены.
Read-ahead first-actually-observed fault соответствует465; прежний порядок
независимых будущих fault не обещается. Close/drain/reset/shutdown/release,
seal/decode, writeWav32, adapter/reader/cache/quotas/timeouts не затронуты.
Нового source blocker/aliasing/ошибки последнего refill не найдено.

Current header:76–78 семантически соответствует принятому playbackStarted:
verified WAV/started AAC continuation, invalid/orphan metadata refusal, без
factory repair. Но AAC45 хранит лишь header hash, не прежние bytes; доступной
точной before-копии не найдено. Поэтому утверждение «diff только комментарий,
API неизменён» пока независимо не доказано. Header prior
4d5946e88622230f4e9567d0dc1bb95baaae526ea207a4a9aa58b4c063f1616a,
after0a0f5b2980dd63490c2a8b1dcf018d2067f5511c352bb278e9a3640c3628ba15.
Для закрытия нужен прежний .h с exact prior SHA либо его проверяемое
восстановление; расширение исторического аудита не нужно. До этого полный
AAC46 runtime gate не подтверждён данным reviewer. Runtime/build не запускались.
Только append своего отчёта; source/norm/tasks/checklists/VM/Git/GitHub неизменны.

## 2026-10-21 / AAC46 — header evidence gap закрыт

**Полный scoped SOURCE GO AAC46, C0/H0.** Проверена только предоставленная
before-V5LocalRecordingWriter.h против frozen header; cpp/norm gates повторно
не выполнялись. Before SHA256
4d5946e88622230f4e9567d0dc1bb95baaae526ea207a4a9aa58b4c063f1616a
точно совпадает с prior AAC45 entry; after
0a0f5b2980dd63490c2a8b1dcf018d2067f5511c352bb278e9a3640c3628ba15
совпадает с frozen AAC46 entry. Exact diff: только прежняя одна comment line
о Started/orphan outputs заменена двумя comment lines о verified reusable
WAV/started AAC и invalid/orphan metadata retained refusal. Все declarations,
типы/API/layout/includes и прочие bytes неизменны. Семантика комментария
соответствует принятой ветви playbackStarted и не создаёт новый допуск.

Единственный evidence blocker предыдущего раздела снят новой before-копией;
исторический условный NO-GO не стёрт. Вместе с прежним cpp GO это допуск exact
manifest216 0870912ff9f3693e3a675029030c3883726558b9b5f4eff533d6d3e629e0d9f3
к первому runtime с прежними сроками. Не runtime PASS/ускорение/full T116 GO.
Дополнен только этот report; guest/build/tests/source/norm/Git не трогались.

## 2026-10-21 / AAC47 — scoped revert + tail stamps SOURCE gate

**Scoped diagnostic SOURCE GO, C0/H0.** Manifest216
9e65695b22836d20e54d7a148619b6ff4a500ad7c0b141fd495f37829d54bb99,
prior точно AAC46. Ровно два changed paths: V5LocalRecordingWriter.cpp и тест;
current216 совпали с frozen47. Frozen cpp побайтно равен принятому AAC45
15c50778cca79d86104bf76c6ba7c3eeb7aca995c9c59e616c4233741f8acc1c:
read-ahead465 снят, WAV32 сохранён. Header-комментарий AAC46 не менялся.
Это проверенный exact revert, не новый общий production audit.

Тест before совпал с frozen AAC44/AAC46 SHA8d08cc4f..., after
14fa1f27c56ee2252a57e690cdcb479d1fd0a4927aaa23aa55af977a9f804295.
Exact test diff: только7 синхронных calls существующего phase/GetTickCount64/
fprintf+flush. Нет новых variables/IO чтения/ожиданий/сроков/branch predicates,
изменения order/assert/fixture/cut/codec или acceptance условий. Lambda живёт
в той же функции; ни callback, ни захвата с истёкшим временем жизни нет.
Новых mutex/native hook/perframe границ нет.

old_extent_and_originals_verified после canonical/IDs/queue/WAV/old extent
asserts; sealed_hashes_ready после whole-tree hash. cold_store_opened и
cold_pair_read следуют успешным open/readPackage. cold_inspection_complete
означает inspectProtected.ok, НЕ последующие evidence/history assertions.
privacy_reinspected следует manifest/privacy assertions, но до закрытия scope.
readonly_and_idle_verified — после hash/owned memory equality, но до проверки
доступности4jobs/32pins. Единственный прежний финальный COLD_PARTIAL_RECOVERED
остаётся после всех этих проверок. Поэтому промежуточные stamps не дают
ложного PASS и позволят сузить следующий terminal timeout без ослабления gates.
Сроки child60/CTest180 неизменны, ускорение и полный runtime ещё не приняты.

## 2026-10-21 / AAC46 — независимая saved-stage TIMEOUT qualification

**Evidence qualification GO для genuine TIMEOUT; runtime acceptance NO-GO.**
Использованы сохранённые AAC46, НЕ текущий reverted cpp: frozen .cpp/.h, тест
из AAC44 с совпавшим46 entry, остальные214 только после hash equality.
Итого216/216 соответствуют manifest
0870912ff9f3693e3a675029030c3883726558b9b5f4eff533d6d3e629e0d9f3.
Полностью прочитаны receipt/XML/build.log/test.log/actual-test.log; harness
побайтно совпал с уже прочитанным AAC45, его source/PE pre/post guards прежние.

Receipt terminaltrue/Debug/build0/test8/executed1/post216/owned0/failure TEST;
ровно CLI --cold-recovery-playback-partial. XML testcase180.015s/fail Timeout,
failures1/disabled0/skipped0. CTest display180.01s, total180.02s — не другая
точная длительность testcase. PE
c757c6c81ca7c3aef09291b8f607d9501b3bd97aceeea76b98cd0b4c037c7527,
7,041,024 bytes; saved receipt guard, не новый guest hash.

Stamps: baseline fixture9421, recovered62343 (52922ms после fixture ready,
не профиль отдельного метода); partial fixture62500→71859; child cut102875;
old_partial_proved103296; partial_recovered167046ms. Passed intermediate
asserts подтверждают child wait/exit88, actual BOTH g3/524288>262144 и
<732186, specific codec error6/c00d36c4, no-write old proof и recovery result
semantic/trusted/60000ms/degraded/!normal/!keepable. Финального маркера нет;
внешний fresh/history/privacy/extent/resource tail целиком не принят, точное
место остановки по старым stamps не установлено. Это внешний CTest180 timeout,
не child timeout; PowerShell wrapper не отдельная причина.

AAC46 не решил whole-run budget, но отдельный вклад read-ahead и причина
оставшихся затрат этим run не доказаны. Generated-only/no device audio/
network/install; native_metadata_probes=false не отрицает filesystem IO.
AAC43/44/45/46 отказы и465 как candidate history сохранены. Полный T116/Windows
не закрыт. Изменён только собственный report; VM/build/tests/Git/GitHub и
source/norm/tasks/checklists не трогались.

## 2026-10-21 / AAC48 — допустимость отдельного Release diagnostic comparison

**Scoped diagnostic comparison GO, C0/H0; не runtime qualification.**
Повторно прочитан validate-v5.ps1: Configuration ValidateSet(Debug,Release),
default Debug; значение используется в build --config, EXE path, ctest -C и
receipt.configuration. Source216 pre/post, PE pre/post и owned-process guards
не зависят от конфигурации. Текущие216/216 совпали с сохранённым AAC47 manifest
9e65695b22836d20e54d7a148619b6ff4a500ad7c0b141fd495f37829d54bb99.
Это host/source check, не проверка ещё работающего AAC48 guest или его receipt.

V5tests:9–12 снимает NDEBUG перед cassert; Windows CLI partial:1192–1193
без Debug/Release развилки вызывает ту же coldRecoveryPlaybackPartial.
CMake:184–185 оставляет RUN_SERIAL и TIMEOUT180; crashRecoveryAt:291–299
оставляет child wait60000, bounded cleanup10000 и обязательные wait/exit88.
Release не выбирает короткий профиль и не исключает full-proof assertions.

Оговорка сравнения: Debug-only resultAllocationCuts и CRT report setup
(test:174–198,1180–1184) в Release не выполняются; это существующая отдельная
проверка allocation failures до CLI dispatch, не часть partial AAC proof.
Поэтому сравнение исследует совокупный вклад конфигурации/Debug CRT/оптимизации,
но одним прогоном не изолирует конкретную причину прежнего timeout и не даёт
чистую оценку стоимости одного метода. Даже Release PASS не отменит Debug47 RED,
не закроет T116, hardware/performance/application acceptance. Квалификация
AAC48 требует terminal evidence, exact configuration/source/PE, полного лога,
XML no-skip и финального proof marker. Живой stage/логи/VM не читались;
build/tests не запускались. Дополнен только собственный report.

## 2026-10-21 / AAC48-release — независимая saved-stage runtime qualification

**Scoped runtime evidence GO / PASS для одного Release long-partial test;
C0/H0 в проверенных артефактах. Не full T116 acceptance.** Полностью прочитаны
result.json, result.xml, actual-test.log, build.log, test.log, changed.json и
validate-input.ps1 только завершённого aac48-release. Harness побайтно равен47;
source.sha256 и prior.sha256 побайтно равны47, changed=[], 216/216 текущих
файлов совпали с manifest
9e65695b22836d20e54d7a148619b6ff4a500ad7c0b141fd495f37829d54bb99.
Receipt terminaltrue/Release/build0/test0/executed1/post216/owned0, без failure.
Saved PE5856b29d8a86d322b3ae673343be4355848c8dce6cf1dc0d19cf38b72ec659ef,
1,026,560 bytes; pre/post guard в неизменном harness, не новый guest hash.
Build.log содержит успешные Release library links и Release test EXE link.

XML: ровно ProtectedRecoveryPlaybackPartial, time133.073s, failures0,
disabled0/skipped0; CTest display133.07/total133.10 не подменяют точный testcase.
Actual command build/Release/V5LocalRecordingWriterTests.exe
--cold-recovery-playback-partial. XML output обрезан1024-byte threshold;
финальное доказательство взято из ПОЛНОГО actual-test.log, где Test Passed и
COLD_PARTIAL_RECOVERED cut=28 role=2 operation=6 child_exit=88
duration_ms=60000 immutable_old_extent=1 readonly_unchanged=1 audio=0 network=0.

Stamps: fixture6469, baseline45109, partial fixture51094, child72594,
oldproof72906, recovered118547, original/extent118578, hashes118609,
store/pair118625, inspection126609, privacy132969, readonly/idle133000ms.
Old AAC actual BOTH g3/524288 bytes >262144 и <complete732186, codec refusal
error6/c00d36c4. По неизменным исходникам407–526 финальный marker следует
обязательным physical wait/exit88, восстановлению trusted60000ms sealedDegraded
(!normal/!keepable), сохранению canonical/IDs/queue/WAV/всего old ciphertext
до actual EOF кроме mutable HEADs, росту actual EOF и sealed playback generation,
fresh cold inspection/full playback evidence/original times/privacy, readonly
whole-tree equality/idle memory и доступности4jobs/32pins. Assertions действуют
в Release; никакой промежуточный stamp не принят вместо этих checks.

Это generated-data functional proof конкретной long interrupted AAC recovery
в Release с прежними child60/CTest180. Debug47 RED и все старые отказы сохранены;
сравнение не доказывает точный источник Debug latency, production/hardware/
installed/performance/full Windows acceptance. Следующие Release regressions
ещё не квалифицированы. Device audio/network/install не выполнялись;
native_metadata_probes=false не означает отсутствие native filesystem IO.
Изменён только этот report; VM/build/tests/Git/GitHub, source/norm/tasks и
checklist markers не трогались.

## 2026-10-21 / Playback-started returned faults — scoped proposal requirements/analyze

**Requirements-quality / scoped analyze GO перед test-only реализацией,
C0/H0. Не actual SOURCE/runtime GO.** Применены speckit-analyze и code-reviewer
только к предложению reuse coldRecoveryReturnedFaults(bool=false), без нового
продуктового решения/норматива/API/задачи. Prerequisites указывают Feature200;
YAML разобран, enabled before/after_analyze hooks отсутствуют. Текущие216
совпали с AAC48/AAC47 9e65695b...bb99; AAC49/50 receipts не проверялись.

Основание — plan462:2715–2753 (mixed leases, logical reset, old extents,
sticky failure) и2755–2772 (native/flush/readback/cancel после эффекта), packed
contract:378–404, FR-012 и открытая T116, constitution IV/VI. Предложение
проверяет существующий post-reset contract, не создаёт новый output authority.
Применимы cold-prefix CHK035–041 и прежние CHK009–012, packed-writer007–010,
security012/017/018 и original-owner fences. Отметки остаются требованиями,
не runtime acceptance. Counts без изменений: cold-prefix41/0, packed-writer12/0,
security27/0, start-owner10/0. Исторические checklists этим не переаттестованы.

Конструкция доказуема существующими native wrappers: unused baseline выбирает
реальный первый role2/op6 для child exit88; затем отдельный STARTED baseline
с fresh fixture/owner задаёт собственные reset/read/final-seal ordinals.
Каждый fault получает новый fixture и тот же physical child cut, а failed
writer/owner освобождаются до read-only cold observation. Исходные26 unused
cases/CLI остаются без изменения. Started table:5 playback write/flush cases,
12 metadata cases,4 late-read/cancel/final-seal,2 reset-readback =23 cases;
это не вся crash/crypto/quota/long-partial матрица и не закрытие T116.

Важное source уточнение: Tree.cpp:383 делает первый playback flush ДО
publishHead:403; сам Files.cpp:1805–1808 выполняет HEAD write/flush/readback.
Поэтому первый traced2/op1 нельзя называть доказанным HEAD flush/ACK. Для
nonempty→0 (V5.cpp:469) candidate root пустой, validate не читает DATA; guards
делают metadata/identity checks, не ReadFile. Следующий playback ReadFile после
arming на этом op1 — native HEAD readback. Actual diff должен подтвердить
nonempty old proof, собственный started trace и one hit после HEAD transfer,
не подменять арming ordinal числом из unused trace. Не нужны product hooks.

Условия будущего SOURCE gate: исключить media writes, но обязательно сравнить
полный WAV, canonical/IDs/queue и prefix+ВСЕ old playback records до actual EOF
(кроме mutable HEADs), без shrink/cleanup/retry; one-hit и exact native/HRESULT
ошибки/cancel обязательны. Reset-readback2/7,2/8 должны быть отдельно отличены
от late canonical0/7,0/8: старое operation>=7 в тесте:781 нельзя слепо reuse
как требование sealed/full decode. Full cold decode требуется только для
заранее выделенных actual terminal-seal/late canonical cases; остальные
проверяют rejection/nonnormal и неизменность cold observation. Не выводить
успешный recover из valid disk shape после неоднозначного ACK. Переменные
arming/token/trace очищаются до cold read; resource checks после release и
fixture destruction. CTest300 serial как у existing returned, child60/10,
память/job/pin/trace cap прежние. Любой timeout/zero-hit — FAIL, не новый допуск.

Нормативные SHA неизменны относительно принятого465: plan ed75a761...187b4d,
spec0065a781...bc4e11, tasks80fc15cd...0e024f, constitutiond28f8312...43d859,
research91248196...b63ac83, quickstartf604abca...96f90e,
data-model49f86234...374b3, packed contractf610c700...35ffea.
Противоречий scope/immutable sealed/no rollback/no accepted failure не найдено;
новых продуктовых вопросов0. Остальные long/repeated/crypto/quota/native/
installed/hardware/release gates открыты; Debug RED сохраняется. Дополнен
только этот report, norms/tasks/checklist markers/source/VM/Git не менялись.

## 2026-10-21 / AAC53-reset-faults — exact test-only SOURCE gate

**Scoped SOURCE GO, C0/H0.** Рассмотрен FINAL frozen AAC53, включая последнее
усиление actual fault offset/count, не промежуточный cbc589... test.
Manifest21640df97b9ac1299fa630dd69d42333e2ec73e24d1c6b93400c66edd06a8aed300;
prior побайтно AAC48/AAC47 9e65695b...bb99. Changed.json и manifest delta
согласованы: ровно CMake и V5tests, остальные214 неизменны. Текущие216/216 и
две frozen copies совпали; перед verdict SHA повторно прочитаны:

- CMake f5736bc0dd2e9497b4ac4cde723e804c71f8b412c6f74357c0a5b3f5d1d3320b;
- V5tests f75b9a4c1d1d0e9a086548faa97347e6315255720491f48f15fc118148f8d783.

Exact diff проверен против hash-matched AAC47 test14fa1f... и AAC43 CMake
8d30d891... (оба совпадают с prior entries). CMake:178–179 добавляет только
новый Windows CLI RUN_SERIAL/TIMEOUT300; main:1250–1251 вызывает тот же helper(true).
Старый CLI/defaultfalse остаётся отдельным26-case путём:1 baseline, обе audio
роли, те же native errors/late seal predicates/resource assertions/summary.
Новые guards role==0/5 эквивалентны прежним на его прежнем fault table.

Test:730–755 получает unused cut из первого actual trace, затем на свежем
fixture/child exit88 получает второй STARTED baseline с собственными
sealedEvent/resetReadEvent. Каждый из23 cases заново достигает physical cut;
785–787 full BOTH proof требует nonempty<block playback и освобождается до
fresh production owner. Поэтому reset не empty no-op и не guessed generation.
Старые canonical/IDs/queue, полный WAV, prefix128 и ВСЕ ciphertext bytes
[appendOffset,oldActualEOF) сохраняются; actual EOF не уменьшается. HEADs
исключены только как законно изменяемые cells. Short helper ограничен <1MiB;
это не long partial proof и не новая authority/cache.

Reset2/7,2/8 используют собственный first2/op1: pre-HEAD flush. По Tree:383–407
и Files:1805–1808 между ним и ближайшим playback ReadFile нет другого content
read на nonempty→0; следующий read — native HEAD readback. Новый scalar capture
в wrapper:153–160 происходит только при one-hit, offset128/16512 и count16384
assert на803–805 исключает ранний package-open/canonical/DATA read. Operation7
возвращает ERROR_READ_FAULT ВМЕСТО вызова системного ReadFile в этой точке:
это injected native-read failure, не утверждение об успешном чтении. Operation8
ставит живой cancellation token и ВСЁ РАВНО вызывает настоящий ReadFile.
Lambda синхронна/не сохраняется; token жив до возврата recover; one-hit/scalars
обнуляются перед каждым recover и fault/token/arming отключаются до cold read.
Для reset они выполняются до MF callbacks; новых concurrent hooks нет.

Early abort/zero-hit не PASS: требуется hits1, !recovered.ok(), exact native
или HRESULT_FROM_WIN32(expected), cancellation только в op8. Late canonical
0/7,0/8 и final-seal5 cases отделены от reset в cold observation: только первые
требуют прежнего sealedDegraded/full inspection; reset не выдаётся за готовый
AAC. После освобождения failed owner проверяются неизменность cold tree,
точная idle memory и доступность4jobs/32pins после fixture destruction.
Compile/source blocker или необходимый корректирующий diff не найден.

Допуск только к build/runtime этого frozen test-only candidate с прежними
child60/10/CTest300 и действующими asserts. Укладка23 cases в budget ещё не
доказана. Этот SOURCE GO не является runtime PASS; AAC49–52 не квалифицированы здесь,
Debug RED/T116/full product acceptance открыты. Применён code-reviewer;
изменён только этот report, без VM/build/tests/Git/GitHub/code/norm/checklists.

## 2026-10-21 / AAC49–52 — независимая qualification завершённых Release regressions

**Scoped runtime evidence GO/PASS для выполненных сценариев; AAC51 содержит
явные ограничения внутренних allocation-budget проверок. Не полный T116 GO.**
По code-reviewer проверены только saved stages aac49-regressions, aac50-tree,
aac51-files, aac52-capture: полностью receipt/XML/actual-test.log/build.log/
test.log; saved harness побайтно равен принятому48. Ни один runtime artifact
AAC53 не открывался; новых процессов/VM/build/tests/Git не запускалось.

Для всех четырёх terminaltrue, Release, build0/test0, postflight216, owned0,
failure отсутствует. Каждый source.sha256 И prior.sha256 побайтно равен48,
changed=[], manifest216
9e65695b22836d20e54d7a148619b6ff4a500ad7c0b141fd495f37829d54bb99.
Текущие214 совпали; два новых host test/CMake не подставлялись в старые runs:
для них проверены hash-matched frozen47 test14fa1f... и frozen43 CMake8d30d891...
из prior. Все три core test sources совпали с этим manifest. Source/PE pre/post
guards из неизменного harness сохранены; PE ниже — saved receipt identity,
не новый guest GetFileHash. Build logs содержат соответствующие Release links.
Assertions всех четырёх test TU действуют после #undef NDEBUG; существующие
Debug CRT/prelude checks не выдаются за исполненные в Release.

Точные testcase durations из XML, не округление CTest:

| Stage | Exact testcase | Seconds | Verdict |
|---|---|---:|---|
|49|V5LocalRecordingWriterTests|63.8393|PASS|
|49|ProtectedRecoveryReturnedFaults|21.5445|PASS|
|49|ProtectedRecoveryCompletion|8.11152|PASS|
|49|ProtectedRecoveryWav|7.72029|PASS|
|49|ProtectedRecoveryPlayback|13.3908|PASS|
|50|ProtectedPackedCustodyTreeTests|20.5273|PASS|
|51|ProtectedCustodyFilesTests|149.115|PASS с ограничением ниже|
|52|CaptureFaultStateTests|175.761|PASS, no capture|

XML totals49=5,50/51/52=1 каждый; failures/disabled/skipped0 у всех. Actual
CLI49: default EXE, --cold-recovery-returned-faults, --cold-recovery-completion,
--cold-recovery-wav, --cold-recovery-playback;50/51/52 — соответствующий default
EXE без selective flags, каждый из build/Release. Полные логи Test Passed8/8.
XML49/51 обрезает output1024, поэтому coverage взят из FULL actual-test.log.

PE identities:

- 49 V5 5856b29d8a86d322b3ae673343be4355848c8dce6cf1dc0d19cf38b72ec659ef,
  1,026,560 bytes (тот же48).
- 50 Tree1fa157935b1d1ea4dccaa2242529b4dc0af4e30bce74da2450cdfeaecff09241,
  565,248 bytes.
- 51 Files7e607c11f1b3fd225dc5f5dea7837288ee5981df4da63e5b08e02f675bb6ea83,
  1,437,184 bytes.
- 52 Capturec3644b6a4ae63d4411432a111074c58a5084ba417ea2d928bbccf65500198852,
  1,155,072 bytes.

49 full log: cold playable3, refusals15, capturing/finalizing prefix и9 refusals;
actual trace24 и cuts1..24 в порядке с child_exit88/waited1, continued11,
recovered_unused2, sealed_cold_decode1. Seven AAC old generations измерены;
предзаданные WAV6/7 и AAC8..14 продолжаются, completed22/23, sealed24 readonly;
неизвестные/metadata shapes отказаны. Returned26: каждая строка hit1/rejected1
с exact native codes, включая late canonical read/cancel и final seal ACK;
финальная summary exact_memory/unchanged/late_cold_decode. Completion5=2positive
+3preserved refusals. WAV filtered ordinal7:1/1 +7refusals (partial peers3,
started outputs1). Playback filtered ordinal12:1/1 после всех10refusals,
old generation2. Это short process-crash regressions, не power-loss proof
или новые AAC53 post-reset cases;48 long partial остаётся отдельным run.

50 default main выполняет packed writer/reader/cancel/CopyTo/pinned/retained/
mixed/native fault paths, без early selective return. Полная READER_RELEASE_DRAIN
summary: observed/cloned/AddRef unchanged/cancelled still live/external/all/
owner/pins/memory released=1; empty_proxy_charge0/observed_delta0. Это functional
reader/tree regression, не throughput/hardware qualification.

51 ВАЖНО: XML skipped0 относится к CTest, НЕ ко всем внутренним subchecks.
Полный лог содержит cold-cache-close relevance=SKIP-no-proxy-allocation-fault,
writer-open-budget SKIP-no-proxy-allocation-fault и metadata-move-budget с тем
же SKIP. Source FilesTests:1220–1270 измеряет emptyProxyCharge0, реально закрывает
reader под полным charged pressure и проверяет no IO/exact cleanup; лишь
charged-proxy-specific relevance не применима. WriterOpenBudget:1273–1279 и
metadataMoveBudget:1294–1303 действительно возвращаются при measured proxy0,
не исполняя свои allocation-refusal bodies. Это существующий shape-dependent
путь, а не скрытый CTest skip/неожиданный fail. **NO-GO утверждению «все внутренние
allocation checks выполнены без пропусков»; PASS ограничен выполненным default
Release functional suite.** Log подтверждает readonly admission/cancellation,
bootstrap native identities/cuts, migration history/pairs, logical queue cuts,
protected AAC positives/invalid codec и full normal/degraded manifest cases;
финальное owned_before0/owned_after0. Прежние Debug budget proofs не заменены.

52 full log: FIFO4/Prefetch6 combinations suppressed1; default main не выбирает
короткий CLI и содержит async privacy, interrupted-start recovery/gates, EOS,
clock/timeline/controller checks с синтетическим sink. Native endpoint ID
roundtrips2(no capture) — metadata enumeration/conversion, НЕ sample/audio read.
native_metadata_probes=false в общем harness значит не NativeCapture-specific
probe; не следует трактовать это как отсутствие filesystem или endpoint API.

Итого8 CTests functional PASS с явной51 оговоркой, без нового несоответствия
source/PE/terminal. Никакого вывода о Debug timeout root cause, speedup,
performance/continuity/реальном звуке/installed UI/release/full T116/Windows.
Изменён только собственный report; main validation, source/norm/tasks,
reviewer-owned markers, VM/Git/GitHub не менялись. AAC53 квалифицируется отдельно
только после его terminal evidence.

## 2026-10-21 / AAC53 — независимая runtime qualification old26 + started23

**Scoped saved runtime evidence GO/PASS: два Release CTests, не полный T116.**
Прочитаны receipt/XML и полные actual-test.log/build.log/test.log, frozen source
и harness из external aac53-reset-faults. Manifest216
40df97b9ac1299fa630dd69d42333e2ec73e24d1c6b93400c66edd06a8aed300;
от prior9e65695b... изменены только CMake/test, production214 прежний.
Frozen/current216 совпадают; test
f75b9a4c1d1d0e9a086548faa97347e6315255720491f48f15fc118148f8d783,
CMake f5736bc0dd2e9497b4ac4cde723e804c71f8b412c6f74357c0a5b3f5d1d3320b
соответствуют прежнему SOURCE GO. Harness равен48, source216/PE до и после
test защищены его прежними guards. PE — saved receipt identity, не новое
guest измерение:61e68d4d906c0ad2cee25c0aea3bd45384be8d76562d685e1f19d1a8ab3e3393,
1,035,264 bytes. Receipt terminaltrue/build0/test0/executed2/post216/owned0,
без failure; audio/network/install=false.

XML: failures0/disabled0/skipped0, exact cases:
ProtectedRecoveryReturnedFaults24.2236s и
ProtectedRecoveryPlaybackReturnedFaults41.0942s. Обе команды используют
build/Release/V5LocalRecordingWriterTests.exe с соответствующими
--cold-recovery-returned-faults / --cold-recovery-playback-returned-faults.
System-out XML обрезан1024bytes; coverage ниже подтверждён FULL actual log,
где оба Test Passed и обе финальные summaries, без skipped/disabled/fail.

Все49 COLD_RECOVERY_RETURN rows: hit1/rejected1/error6 и exact native codes.
Прежние26 rows побайтно совпадают с49: media/playback write/flush/HEAD,
metadata roles3/4/5, late canonical read/cancel и final seal23/24. Новые23:
playback5, metadata12, late canonical read/cancel2, final seal16/17 два,
reset HEAD readback failure/cancel2 после собственного event1. Native70 для
writes,1d flush, c000007f rename,1e read,3e3 cancel сохранены. Новая таблица
не подменяет WAV readonly записью и не копирует unused final-seal ordinal.
Финальные COLD_RECOVERY_RETURNS cases26 / COLD_PLAYBACK_RETURNS cases23
обе exact_memory1/canonical_ids_queue_unchanged1/late_seal_cold_decode1.

Hash-matched source assertions активны в Release (#undef NDEBUG): каждый
новый case имеет fresh fixture/physical child cut, failed owner освобождён
до cold observation; canonical/IDs/queue/WAV и весь старый playback extent
(кроме законно изменяемых HEAD) сохраняются; cold observation readonly,
idle memory/jobs/pins восстановлены до final summary. HEAD readback offset
128 либо16512/count16384 и child wait/exit88 проверяются assertions, НЕ
напечатаны в этом log. Op7 — injection отказа на actual read attempt;
op8 отменяет и вызывает native read. Completed AAC inspection относится лишь
к late canonical/terminal final-ACK, не к раннему reset readback отказу.

Несоответствий в этих saved receipts нет. Это short1s process-crash/returned
fault Release qualification при прежних child60/cleanup10/CTest300, не long
partial/repeated-crash/power-loss/device/installed/performance/full Windows.
Debug47 timeout RED и T116 остаются открыты. Изменён только собственный report;
VM/build/tests/source/norm/tasks/checklists/Git/GitHub не затронуты.

## 2026-10-21 / proposed playbackRestart — scoped requirements/checklist/analyze

**GO для подготовки отдельного test-only diff; C0/H0, продуктовых вопросов0.**
Это existing high-risk-product T116/#7444, не SOURCE/runtime GO будущему коду
и не принятие P2/фичи. Применены speckit-analyze/speckit-checklist/code-reviewer;
новый checklist/задача не нужны. Сопоставлены текущие plan462:2704–2808,
quickstart:1167–1198, research462, data-model462 и packed contract:378–403,
spec FR-012/013/014/022, SC-005/006, Session2026-10-16, T116:568 и Constitution
I/II/IV/VI. Связь #7444 подтверждена tasks:552/568, не новым GitHub запросом;
удалённое состояние issue этим review не проверялось. Prerequisite script
не запускался: его feature resolution использует Git/может persist pointer;
required paths прочитаны напрямую из .specify/feature.json, spec/plan/tasks.
Актуальных before/after analyze/checklist executable hooks нет.

Нормативные SHA256 подтверждены без изменений:

- constitution d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859
- spec 0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11
- plan ed75a761a0c83b64e57740f60b1c78d1072ad16baaeed2f33a3f9ad526187b4d
- tasks 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f
- quickstart f604abca58264286253197bc3596cff437133a5c156abd51c6ede8bd5096f90e
- research 9124819664db586ae943b110ce3c2ad6751056153c906a031c670d9ecb63ac83
- data-model 49f8623498842b6a2ef57243398c1c4c1230a1009a60d364e839f230750374b3
- packed contract f610c70062ee13711b1989b88562b3403458589701b445c0ba763ccac635ffea
- local custody a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490

Checklist inventory перечитан/пересчитан:31 файлов с checkbox criteria,
471 checked/0 unchecked (включая built-in requirements22); отсутствие checkbox
в остальных review documents не превращает их в незакрытые критерии. Это
инвентаризация состояния, НЕ повторный полный acceptance всех471 пунктов.
Применимость конкретно этому срезу сохранена: cold-prefix41/0, включая
CHK035–041=7/0 и прежние unused/completed/WAV/history/native-owner границы;
start-owner10/0, security27/0, packed-writer12/0, resize14/0, package12/0,
reader20/0. Остальные capture/UX/calendar/privacy и узкие исторические
storage gates не расширены и не заменены. Ни один marker не изменён;
исторический NO-GO462 и открытые runtime/Debug/полные T116 gates сохранены.

Source feasibility предложения проверена по test:64/90/113–138/279–305/
534–680 и production Tree:209–213/383–419, V5:182–245/459–473/728–765,
Metadata:1857–1920, Files birth:1325–1360. Reset nonempty→0 сначала flush
records, затем полный native HEAD write и его flush. Поэтому предлагаемая
test-only observe=true для полного HEAD делает видимыми reset op5/6 до DATA;
это не новая product capability. Birth остаётся одним native write prefix+BOTH
с offset0/не16384, поэтому не становится op5. Не переносить ослабление в
production или recoveryFail eligibility; прежние24 cuts/CLI/negative assertions
должны остаться прежними и быть повторно проверены после общего wrapper diff.

Два actual baseline passes и fresh fixture→first physical child cut→second
physical child cut→fresh third owner соответствуют full verification после
каждого ownership gap. Все parent proof/readers/owners отпускаются ДО child;
не readonly upgrade и не retry failed object. Сначала измеренный unused trace
выбирает первый playback2/op6; затем собственный started trace, не старые
ordinals. Заранее заданный exact19 vector и исходы согласованы с462-U1:

| Proposed second trace cuts | Shape | Outcome |
|---|---|---|
|1–7|playback operations1,0,5,6,4,5,6; valid BOTH до/после reset, append и HEAD|R7|
|8–9|retire package-state before/after rename, старая bound unfinished history|R2|
|10–16|manifest pre/post, binding pre/post, recovery first pre/post и second pre|D7|
|17–18|recovery second post и final package pre, готовые terminal members|C2|
|19|final package post, selected sealedDegraded|S1|

Это предопределённый oracle, не наблюдённый runtime: assert exact role/op/order,
R9/D7/C2/S1; неизвестный trace/shape — STOP, не переклассификация после fail.
Op5 означает complete WriteFile до flush, НЕ power-loss/старый ACK. Каждый
исход требует фактического shape/proof: R BOTH и измеренная generation;
nonempty reset+1, уже empty0→0 same-generation/no reset-HEAD. C сохраняет
completed members без re-encode; S recover отказывает, full sealed inspection
readonly и whole-tree unchanged. D whole-tree unchanged относительно второго
crash. R/C сохраняют canonical/WAV/IDs/queue/original owner и весь старый
physical playback extent, но НЕ mutable HEAD cells: prefix128 и
[appendOffset, oldActualEOF) хешируются отдельно, EOF не уменьшается.
Для R — append после actual EOF/монотонный конечный ref; нельзя требовать
нового reset поколения от уже пустого snapshot. Full cold AAC/privacy/time/
history/degraded/noNormal proof обязателен каждому success; освобождение
writers/readers/pins/jobs и readonly hash проверки — до final pass summary.

Serial CTest180/child60/cleanup10/trace256/существующие resource bounds прежние.
Достаточность времени не обещана: timeout сохраняется FAIL без сокращения
matrix/full proof или увеличения deadline. Short repeated-crash не заменяет
real MF partial>block, post-effect fault breadth, Debug long RED, native device,
power loss, installed/UI/hardware/release/T117/T118/full Windows acceptance.
Нормативного изменения для такого exact test reuse не требуется. Следующий
gate — actual test-only SOURCE diff; execution данным GO не квалифицируется.
AAC54/его runtime logs/VM не открывались; его reported Debug PASS пока не
independent qualification. Изменён только этот report, не source/norm/tasks/
checklists/Git/GitHub; main validation не затронута.

## 2026-10-21 / playbackRestart — actual test-only SOURCE gate перед snapshot56

**Scoped SOURCE GO, C0/H0; блокирующих замечаний в предъявленном diff нет.**
Применён code-reviewer. Сравнение напрямую с frozen AAC53, без Git/VM/build:
prior manifest40df97b9ac1299fa630dd69d42333e2ec73e24d1c6b93400c66edd06a8aed300,
216 paths; изменены РОВНО test/CMake, остальные214 побайтно прежние.
Frozen before hashes совпали с53 SOURCE gate: testf75b9a4c...8d783,
CMakef5736bc0...3320b. Точный разрешённый текущий source:

- V5LocalRecordingWriterTests.cpp
  c49ac36000b3f002c1f8d2bf93998fcefae237bea65014d016715470cbb77ee7
- CMakeLists.txt
  e2c6ddac85e973814cc22ce728ed1f16491a0c9159b4ad3f2f26155c8a3c96ac

Полностью прочитаны оба delta и относящиеся callers/helpers. Test:535–589
делает actual unused baseline, выбирает первый playback2/op6; второй pass
на fresh fixture после physical child crash измеряет собственный started
trace. Exact19 vector сверяется ДО обхода crash результатов. No R|D:1–9
playbackReady=>R,10–16=>D,17–18 completed=>C,19=>S. Counters:742 требуют
rebuilt9/completed2/continued11/sealed1/refused8, где8=7D+1S; final summary
refused7 плюс sealed_readonly1 корректно разделяет их, а не скрывает fail.
S не считается recovered success: readPackage/full inspection до recover,
затем !recovered и whole-tree unchanged; финальная отдельная cold inspection
обязательна для19 тоже. C сравнивает coldCompletedHashes (все members кроме
изменяемого package-state) после continuation; R требует новый append/strict
EOF increase и конечный sealed playback ref generation>измеренного.

Test:607–645 сохраняет initial canonical/IDs/queue, после первого child —
WAV/actual playback EOF/prefix128+ALL records до initialEOF. Full BOTH proof
непустого short AAC отпущен ДО второго child. После второго cut те же bytes
сверяются, для R дополнительно фиксируется ВЕСЬ второй extent до third owner.
Cuts1–5 проверяют measured generation: first+0 до reset, first+1 после,
и empty shape именно2–5; последующее empty→0 не заставляется менять generation.
После third attempt сохранность обоих старых extents/WAV/IDs/queue повторена.
D/S snapshot для whole-tree equality снят после second crash до recover.
HEAD cells исключены прежним bounded helper384–394; giant/unbounded fixture
не добавлен. Privacy:540–543 переиспользует уже применённый валидный сегмент;
714–736 требуют fresh full AAC/degraded/session/duration/times/timezone180 и
exact privacySegments в защищённом selected manifest, затем readonly hash
equality. Inspection освобождён до группы readers; их slot/ref indexing
соответствует existing openProtectedCustodyReaders. Idle memory и4jobs/32pins
проверяются до final summaries. Child60/cleanup10/exit88 guards неизменны.

Соседний fault point:64–66 сохраняет op5 eligibility=data; op6 теперь явно
data&&pending. Раньше pending устанавливался только при data, поэтому прежний
append-HEAD flush fault остаётся там же и НЕ смещается на reset flush. Новое
observe=true:90–91 видит полный reset HEAD;113–132 по-прежнему допускает op5
только offset128/16512,count16384 и actual done==count. Birth offset0 остаётся
вне op5. На reset: data=false, HEAD pending=true, поэтому tracing видит op6,
но returned op6 не инъецируется. После DATA eligibility эквивалентна53.
Dynamic sealedEvent/resetReadEvent в792–911 продолжают вычисляться из своей
baseline, не используют старые17/24 ordinals. Старые26/new23 tables/asserts
и три filtered/default callers не ослаблены; nonrepeated baseline дополнительно
требует events24. Global observer изменение всё же требует новых regressions
old24/WAV/playback/completion и обоих returned suites на final snapshot;
прежний AAC55, если он на53, этого нового wrapper diff не квалифицирует.

CMake:180–181 добавляет только WIN32 serial180 CTest с existing target/new
--cold-recovery-playback-restart; main:1307–1309 вызывает именно repeated
ветвь, default all/WAV/playback/child routes прежние. #undef NDEBUG до cassert
сохранён; явных compile/type/format/lifetime hazards в новых строках не найдено,
но компиляция reviewer не выполнялась. Runtime180 для двухchild19 ещё не
доказан; timeout/failure нельзя обходить ослаблением oracle/full proof/сроков.

Можно снять frozen216 с этими точными двумя SHA и использовать прежний harness
для нового serial run только после terminal/owned0 предыдущего main-run;
reviewer не подтверждает это внешнее состояние по сообщению о55. SOURCE GO
не означает runtime PASS, Debug long latency/power-loss/full T116 acceptance.
AAC54/55 receipts/logs не читались. Требования/markers/tasks/production не
менялись; добавлен только этот report. Никаких VM/tests/build/Git/GitHub действий.

## 2026-10-21 / AAC54 Debug + AAC55 Release — completed saved runtime qualification

**Scoped runtime evidence GO/PASS:54=2/2 Debug,55=5/5 Release; не full T116.**
Полностью прочитаны оба receipt/XML/actual-test.log/build.log/test.log и saved
validate-input.ps1. Source.sha256 И prior.sha256 обоих stages побайтно равны
AAC53 source216:40df97b9ac1299fa630dd69d42333e2ec73e24d1c6b93400c66edd06a8aed300,
changed=[]; это НЕ текущие новые c49ac/e2c6 host tests. Неизменный harness
b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a равен53,
с прежними owned0 preflight/source216/anchored CLI/config/PE/source post guards.
Оба receipt terminaltrue/build0/test0/postflight216/owned0 без failure,
device_audio_read/real_network/installed=false. Build links54 Debug,55 Release.
PE identities ниже — saved guarded receipts, не новый guest GetFileHash:

- 54 Debug a213ff5d0494e05df800bf5332f9789aeb0471536c2f4b0fed24c4e7f6cf41ff,
  7,042,048 bytes.
- 55 Release61e68d4d906c0ad2cee25c0aea3bd45384be8d76562d685e1f19d1a8ab3e3393,
  1,035,264 bytes, тот же53.

XML у обоих failures0/disabled0/skipped0/status run; exact durations:

|Stage|Exact CTest|Seconds|
|---|---|---:|
|54|ProtectedRecoveryReturnedFaults|37.2392|
|54|ProtectedRecoveryPlaybackReturnedFaults|69.7272|
|55|V5LocalRecordingWriterTests|75.1569|
|55|ProtectedRecoveryCompletion|10.152|
|55|ProtectedRecoveryWav|7.72221|
|55|ProtectedRecoveryPlayback|15.434|
|55|ProtectedRecoveryPlaybackPartial|156.232|

Actual commands54 build/Debug с обоими returned flags;55 build/Release default,
--cold-recovery-completion/wav/playback/playback-partial. Exact cases совпали с
receipt patterns; full log Test Passed2+5, никаких skip/disabled/fail/timeout
markers. XML output1024 truncation не использована как доказательство конца.
54 все49 returned rows побайтно равны53, включая native codes/hit1/rejected1:
old26 и started23, final seals23/24 vs16/17 и HEAD readback/cancel after_event1;
обе final summaries exact_memory/unchanged/late_seal_cold_decode присутствуют.

55 default: playable3/negative15, complete-prefix capturing/finalizing и9
refusals; actual trace/cuts1..24 без пропуска, все child_exit88/waited1.
Final24/continued11/unused2/sealed1; old generations измерены дляAAC8..14,
полные fixed outcomes и preserved failures не заменены flexible expectation.
Также protected playback held_jobs0/2 decoded48128. Completion5=2positive+
3preserved refusals. WAV cut7/1positive+7refusals с invalid_partial_peer3;
playback cut12/oldgen2/1positive после10refusals. Это старый53 observer,
а не новый repeated19 или доказательство соседнего fault point после его edit.

55 partial: genuine MF old524288>256KiB и<complete732186, generation3;
decode_error6/nativec00d36c4. Child reached cut28 elapsed83703ms,
old proof84031ms, partial_recovered140359ms. Далее реально достигнуты
oldextent/originals140390, sealed hashes140422, cold store/pair140422/140453,
full inspection149109, privacy156140, readonly/idle156187ms и FINAL
COLD_PARTIAL_RECOVERED duration60000/child_exit88/immutable_old_extent1/
readonly_unchanged1. Следовательно это полный Release long proof, НЕ только
intermediate result. Whole-run testcase156.232s; сроки180/child60 не повышены.

Несоответствий в проверенных saved stages нет; функциональные доказательства
Debug short returned и Release old/full/long раздельны. Они не отменяют47
Debug long timeout, не объясняют его причину и не принимают speed/continuity/
power-loss/device/installed/UI/hardware/release/full T116. Новый c49ac observer
и repeated19 требуют своих final-source regressions. AAC56 (live) не читался,
его frozen manifest/PE/runtime здесь не квалифицируются. Только report append;
VM/tests/build/code/norm/tasks/checklists/Git/GitHub/main validation не тронуты.

## 2026-10-21 / AAC56 saved RED + AAC57 child-phase diagnostic SOURCE gate

**AAC56: scoped evidence qualification GO, runtime RED сохраняется.**
Прочитаны saved result.json/XML, полный actual-test.log, декодированные
UTF16LE build.log/test.log и validate-input.ps1. Manifest216
48245c0e527cae1d89dafa26087dc52bf0b0f8cfce8d2e1cf0232e7c6c7e74f2;
prior40df97b9ac1299fa630dd69d42333e2ec73e24d1c6b93400c66edd06a8aed300.
Две реально сохранённые changed source copies совпали с manifest: CMake
e2c6ddac85e973814cc22ce728ed1f16491a0c9159b4ad3f2f26155c8a3c96ac и test
c49ac36000b3f002c1f8d2bf93998fcefae237bea65014d016715470cbb77ee7.
Остальные214 представлены manifest/receipt postflight, не отдельными копиями
этого stage; нового guest hash reviewer не получал. Saved harness b29873c2...
сохраняет owned preflight,216 source checks, anchored pattern, configuration,
PE post-identity и finally receipt. Receipt terminaltrue/build0/test8,
executed1/postflight216/owned0/failure TEST. Saved guarded Release PE:
f2063f94f61fc295d38318b961d7446a2d4c0d0d3000707e5eb0a6de717cf891,
1,039,360 bytes. CMake regeneration result=-1 не build failure: Release link
завершён. XML ProtectedRecoveryPlaybackRestart time165.495/failures1,
disabled0/skipped0; actual CLI --cold-recovery-playback-restart.

Полный baseline trace совпал с19 oracle. Cuts1..8 имеют completed markers
child_exit88/waited1/continued1/canonical_queue_unchanged1. Затем cut9,
role5/op3: wait258/exit90, assertion physical_recovery_cut_must_be_reached
в frozen test:306. Это child WAIT_TIMEOUT60000 с parent forced cleanup90,
НЕ whole CTest180 timeout. Cuts9..19/final R9D7C2S1 не приняты. Baseline trace
не доказывает, до какой операции дошёл именно failed child; нельзя заключать,
что он завис между retire op2/op3, в MF, proof или StoreOwner. NativeCommandError
в PowerShell — оболочка ctest8, не отдельная причина. Причина RED не доказана.

**AAC57: scoped test-only diagnostic SOURCE GO; C0/H0, не runtime PASS.**
Frozen /Users/yshishenya/Documents/graf-f200-public458.po8CtB/aac57-child-phases
manifest216065608b7fb73fda87f776c17d08b2cb182b8a73bcae3cc5ae976dba95a1388c1.
Только test отличается от56; changed.json совпал с manifest delta. Frozen test
и текущий host побайтно равны, SHA
8b70f36d6e737747cd0667aaadbdde7defe85b6ca89da0310a0e2aaf9d377249.
Использован code-reviewer для точного diff/callers, не новый full normative gate.

Проверены test:37–44,109,294–337 и GeneratedRecordingFixtures.h:19–34.
Generated parent уникален, root=parent/recordings; sidecar parent/
recovery-child-progress вне protected inventory и всех coldHashes(root).
Перед КАЖДЫМ CreateProcess parent truncates+closes parent_launch, child
truncates при входе: seed-child/stale previous evidence не подменяет запуск.
Журнал только fixed phase/tick/ordinal/role/op, без аудио, plaintext, путей,
ID или новых CLI/product hooks. Store-open/recover start/end не меняют
монолитный recover/leases/cancellation. Recovery events остаются под прежним
mutex; журнал добавлен после push, до прежней kill/fault-arming ветви,
без новых наблюдаемых событий, перестановки oracle или eligibility. Поток
использует обычный CRT IO вне macro-wrapped Files.cpp, рекурсии observer нет.
GetLastError сохранён вокруг stream write/flush; ошибки журнала дают test
failure, а не успешный cut. Flush означает diagnostic visibility, НЕ custody
durability/flush ACK; synchronous IO под mutex добавляет overhead, поэтому
тайминги instrumented run не являются исходной performance qualification.

Parent по-прежнему inheritHandles FALSE, CREATE_NO_WINDOW, hThread закрыт;
child wait60000/cleanup10000/CTest180 и финальный wait0+exit88 assert прежние.
Новый terminal хранит результат уже существующего cleanup wait; никаких
дополнительных ожиданий. Чтение только после WAIT_OBJECT_0, после закрытия
process handle: stack8192, actual gcount, EOF/nonempty/bounds assert, bounded
printf. Для этого19-event run размер существенно ниже8192; это не обещание
уместить произвольные256 событий. При неподтверждённом terminal чтения нет,
прежний assertion всё равно отвергает запуск. Не найдено C/H compile/lifetime/
format hazards; сборка reviewer не выполнялась.

Граница диагностического вывода: last persisted event плюс ticks локализует
наблюдённый префикс, а НЕ точное место остановки после него. store_open_begin/
end отделяют StoreOwner от recover; prepareRecovery/WAV proof/MF внутри recover
отдельно НЕ размечены. Op2/op3 показывают до/после actual rename; отсутствие
op3 после op2 само по себе не доказывает зависание в NtSetInformationFile,
так как возможна остановка до/во время записи следующего diagnostic marker.
Этого достаточно для следующего причинного наблюдения без production patch;
более точные внутренние фазы потребуют отдельного предъявленного diff/gate.
AAC56 RED не отзывается независимо от нового результата. Только own report
append; code/norm/tasks/checklists/main validation/Git/GitHub/VM/tests/build
не менялись и не запускались. Full T116/Windows acceptance остаётся открытым.

## 2026-10-21 / AAC57 — completed saved repeated19 runtime qualification

**Scoped runtime evidence GO/PASS: Release ProtectedRecoveryPlaybackRestart,
1/1, all19 physical cuts; НЕ root-cause fix/полный T116.** Полностью прочитаны
saved receipt, JUnit, actual-test.log, декодированные UTF16LE build.log/test.log,
validate-input.ps1. Никаких live stages/VM reviewer не открывал.

Exact source216 manifest:
065608b7fb73fda87f776c17d08b2cb182b8a73bcae3cc5ae976dba95a1388c1.
Prior побайтно соответствует56 manifest48245c0e527cae1d89dafa26087dc52bf0b0f8cfce8d2e1cf0232e7c6c7e74f2.
Manifest delta и changed.json — ровно один test. Saved test и host совпадают:
8b70f36d6e737747cd0667aaadbdde7defe85b6ca89da0310a0e2aaf9d377249;
CMake прежнийe2c6ddac85e973814cc22ce728ed1f16491a0c9159b4ad3f2f26155c8a3c96ac.
Текущие216 host inputs также совпали с57;215 неизменных относительно56,
включая весь production. Это локальное подтверждение manifest и сохранённого
changed файла; guest216 до/после подтверждаются saved guarded receipt, не новым
guest чтением. Harness прежнийb29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a:
owned0 preflight, source/prior216, anchored pattern/config и PE post-check.

Receipt terminaltrue/build0/test0/executed1/postflight216/owned0, без failure;
device_audio_read/real_network/installed=false. Guarded saved PE:
727f29f1e388c8ef637e8012eb1e71eb96d0df7a2e4d80f3673fa3ac101dcf03,
1,043,456 bytes. Build log успешно линкует Release V5LocalRecordingWriterTests.
Actual command build/Release/V5LocalRecordingWriterTests.exe
--cold-recovery-playback-restart. XML tests1/failures0/disabled0/skipped0,
status run, testcase time61.4998; CTest display61.50/total61.53 не подменяет XML.
XML output обрезан1024bytes: конец квалифицирован по ПОЛНОМУ actual-test.log.

Full trace19 точно прежний oracle; completed cut markers последовательно1..19,
все child_exit88/waited1/canonical_queue_unchanged1. R1..9 continued1 с measured
old generations2/3/3/3/3/4/4/4/4; D10..16 continued0; C17/18 continued1;
S19 continued0. Final COLD_REPEATED_CRASH cuts19/rebuild9/completed2/refused7/
sealed_readonly1/first_child_exit88/second_child_exit88/old_extent_unchanged1.
Final COLD_RECOVERY_CUTS trace_events19/executed_cuts19/sealed_cold_decode1/
continued11/recovered_unused0/process_crash1/power_loss0, затем Test Passed.
Frozen test:645–777 связывает эти markers с BOTH/generation/old extent, WAV/
canonical/IDs/queue, fresh cold AAC/degraded/history/privacy/time, readonly
hash и memory/jobs/pins assertions. Счёт refused8 внутри assert включает7D+S,
поэтому summary refused7+sealed1 согласован, не пропуск. #undef NDEBUG прежний.

Несоответствий в проверенных saved evidence нет. Failure-only dump не появился:
run прошёл, поэтому новых last-phase свидетельств причины56 здесь нет.
AAC56 child60 timeout остаётся неразрешённым;57 PASS НЕ доказывает устранение
intermittent причины, а instrumented61.4998s НЕ сравнение производительности.
Old/full/returned/long и иные final-source regressions57 требуют собственных
terminal receipts. Нет power-loss/hardware/audio/continuity/installed/UI/release
или full T116 GO. Применён code-reviewer для scoped source/evidence binding;
добавлен только этот own report, без code/norm/tasks/checklists/main validation/
Git/GitHub/VM/build/test действий.

## 2026-10-21 / AAC58 — final-source Release seven regression qualification

**Scoped runtime evidence GO/PASS7/7; не full T116 и не исправление AAC56.**
Полностью прочитаны только terminal stage aac58-final-source-regressions:
receipt/XML/full337-line actual-test.log и декодированные UTF16LE build/test.
Source И prior manifests побайтно равны57 source216:
065608b7fb73fda87f776c17d08b2cb182b8a73bcae3cc5ae976dba95a1388c1;
changed=[]; текущие216 host files соответствуют тому же manifest. Product и
test source не менялись: test8b70f36d6e737747cd0667aaadbdde7defe85b6ca89da0310a0e2aaf9d377249,
CMakee2c6ddac85e973814cc22ce728ed1f16491a0c9159b4ad3f2f26155c8a3c96ac.
Saved harness побайтно равен57, hashb29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a;
его prior/source216/pre-owned/anchored CTest/config/PE-post guards прежние.
Receipt terminaltrue/build0/test0/executed7/postflight216/owned0, без failure;
device_audio_read/real_network/installed=false. Saved guarded Release PE тот же57:
727f29f1e388c8ef637e8012eb1e71eb96d0df7a2e4d80f3673fa3ac101dcf03,
1,043,456 bytes. Guest hash reviewer не запрашивал. Build log Release link0;
actual CLI seven exact expected cases, no extra/missing cases. XML failures0/
disabled0/skipped0, все status run;7 Test Passed в полном LastTest.

|Exact testcase|XML seconds|
|---|---:|
|V5LocalRecordingWriterTests|90.7837|
|ProtectedRecoveryReturnedFaults|29.7016|
|ProtectedRecoveryPlaybackReturnedFaults|55.2928|
|ProtectedRecoveryCompletion|10.5902|
|ProtectedRecoveryWav|8.10529|
|ProtectedRecoveryPlayback|14.0532|
|ProtectedRecoveryPlaybackPartial|137.836|

XML output1024 truncation НЕ доказательство final markers — проверен полный
actual log. Default: playable3/negative15, prefix capturing/finalizing и9
refusals; trace24/cuts1..24 sequential/exit88/waited1; summary continued11,
unused2/sealed1. Измерены old generations AAC8..14=1/1/1/2/2/2/2.
PROTECTED_PLAYBACK held_jobs0/2 оба decoded48128. Old26 и started23 returned
rows все hit1/rejected1 с ожидаемыми native70/1d/c000007f/1e/3e3; final-seal
after_event23/24 vs18/19, reset HEAD read/cancel role2 op7/8 after_event1.
Обе summaries exact_memory/canonical_ids_queue_unchanged/late_seal_cold_decode.
Это также regression explicit data&&pending op6 eligibility при новом observer.
Completion5=positive2/preserved_refusals3 с final unchanged/history/memory.
WAV actual cut7/1continued +7refusals, включая invalid_partial_peer3 и valid
wrong PCM; playback10refusals затем oldgen2/cut12/1continued. Все final markers
достигнуты без childFAILED/assert/skip/timeout.

Long partial: old524288>block262144 и<complete732186, generation3,
decode_error6/nativec00d36c4; child cut28 reached75500ms, old proof75828ms,
partial_recovered122672ms. Далее old_extent/originals122703, sealed hashes122750,
cold store122750/pair122765, full inspection131281, privacy137765,
readonly/idle137781ms; FINAL COLD_PARTIAL_RECOVERED duration60000/exit88/
immutable_old_extent1/readonly_unchanged1 и Test Passed. Это полный final audit,
не только промежуточный recover result. Child60/CTest180 unchanged.

Несоответствий в проверенном saved stage нет. Функциональные regressions
квалифицированы на final57 instrumented source, но56 child-timeout причина
по-прежнему неизвестна и RED сохранён; timings не performance acceptance.
Debug59 не читался, его outcome не установлен. Hardware/audio/network/install/
power-loss/continuity/release/full T116 не принимаются. Code-reviewer применён
для scoped evidence/source binding; только own report append, без VM/build/
tests/source/norm/tasks/checklists/main validation/Git/GitHub действий.

## 2026-10-21 / AAC59 — final-source Debug returned49 + repeated19 qualification

**Scoped runtime evidence GO/PASS3/3 Debug; не full T116.** Прочитаны saved
result.json/XML, ПОЛНЫЙ actual-test.log и оба UTF16LE build/test после decode.
Source И prior побайтно равны57 manifest216:
065608b7fb73fda87f776c17d08b2cb182b8a73bcae3cc5ae976dba95a1388c1;
changed=[];216 текущих host inputs совпали, production/test code неизменён.
Test8b70f36d6e737747cd0667aaadbdde7defe85b6ca89da0310a0e2aaf9d377249,
CMakee2c6ddac85e973814cc22ce728ed1f16491a0c9159b4ad3f2f26155c8a3c96ac.
Saved harness побайтно равен57/b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a,
с прежними prior/source216/owned-preflight/anchored CLI/config/PE-post guards.
Receipt terminaltrue/build0/test0/executed3/postflight216/owned0 без failure;
device_audio_read/real_network/installed=false. Saved guarded Debug PE:
a712db6981206280ca354841dfd329fbcb23452008e06cff9bb451236b8bcde8,
7,078,912 bytes. Это receipt identity, не новый guest hash. Build log подтверждает
Debug link; full actual commands build/Debug с тремя exact expected flags.

XML tests3/failures0/skipped0/disabled0, все status run. Exact testcase durations:
ProtectedRecoveryReturnedFaults37.0871;
ProtectedRecoveryPlaybackReturnedFaults71.4014;
ProtectedRecoveryPlaybackRestart83.4297 seconds. CTest total191.93 не отдельный
test timeout. XML system-out обрезан1024: конец проверен по полному actual log,
с тремя Test Passed, без assert/failure/skip/childFAILED/timeout markers.

Все49 returned rows (26old+23started) побайтно равны58, включая hit1/rejected1/
error6/native exact codes, late-seal23/24 vs18/19 и reset-read/cancel role2
op7/8 after_event1. Обе final summaries cases26/23 exact_memory1/
canonical_ids_queue_unchanged1/late_seal_cold_decode1 присутствуют. Repeated
baseline trace19 совпадает с oracle; cuts1..19 последовательно завершены,
все child_exit88/waited1/canonical_queue_unchanged1. R1..9 continued1 с old
generations2/3/3/3/3/4/4/4/4; D10..16 continued0; C17/18 continued1; S19
continued0. Final COLD_REPEATED_CRASH cuts19/rebuild9/completed2/refused7/
sealed_readonly1/first_child_exit88/second_child_exit88/old_extent_unchanged1;
COLD_RECOVERY_CUTS trace_events19/executed_cuts19/sealed_cold_decode1/
continued11/recovered_unused0/process_crash1/power_loss0. Все final assertions
достигнуты на точном ранее reviewed57 source, не новый ослабленный oracle.

Несоответствий saved evidence нет. AAC56 intermittent child60 RED причина
остаётся неизвестной; Debug47 long НЕ повторялся и его RED не отменён. Short
Debug returned/repeated PASS не заменяет Debug long, performance/power-loss/
hardware/audio/continuity/install/UI/release/full T116 acceptance. Новых jobs
reviewer не проверял/не запускал. Использован code-reviewer для scoped source/
evidence binding; дописан только own report, без VM/build/tests/source/norm/
tasks/checklists/main validation/Git/GitHub действий.

## Round468-U2 — requirements-only gate перед test edits

2026-10-21. Authoritative worktree:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
HEAD b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1 — supplied context, не новая Git
проверка. Lane: requirements review внутри existing high-risk-product T116/#7444.
**GO качеству требований перед подготовкой test-only diff; scoped analyze
CRITICAL0/HIGH0/MEDIUM0/LOW0. Не SOURCE/runtime/full-feature acceptance.**

Применены speckit-checklist (качество существующих критериев, без генерации
нового списка) и speckit-analyze (отдельная read-only cross-artifact оценка).
Прочитаны current constitution/guidance, spec Session2026-10-16/affected FR/SC,
T116 и границы соседних задач, пять final append468 и current462-U1 row,
все47 cold-prefix критериев и применимость остальных тематических checklist.
Final plan включает уточнения mixed histories/interior records/value proposal/
sticky-before-commit и оба U cuts: repeated19/13 и old24/18. Старые runtime
отчёты не использованы как acceptance; AAC57–59 заново не квалифицировались.

### Покрытие и scoped analyze

| Критерии | Текущие основания и результат |
|---|---|
| CHK001–012 | Сохраняют историческую unused construction B; отдельный U не разрешает общий started repair, history rollback или same-owner retry. |
| CHK013–022 | Native startup/worker retirement/start-owner/deletion fences не меняются; U не назначает текущий аккаунт и не выдаёт mutation/upload ticket. |
| CHK023–028 | Owned-degraded local playback остаётся отдельной fresh authority/revalidation границей; новый recover result не открывает quarantine по одному bool. |
| CHK029–034 | WAV-ready и completed guards сохранены; новый U не пишет WAV/AAC/manifest и не ослабляет strict EOF/PCM. |
| CHK035–041 | Playback reset/nonce/generation/old extent/cancel/limits остаются прежними; current462-U1 меняет только terminal-bound exact-unused D→U. Остальные D/R/C/S не становятся условными. |
| CHK042 | plan468 п.1 + packed append: selected finalizing, actual selected bound terminal, BOTH refs/closures/inventory, recovery exact id.bin/no union ref. Valid old peer разрешён без второй terminal copy; newer-unbound/bad peer/metadata orphan/started recovery — D. |
| CHK043 | plan468 п.1 + data-model: fresh existing-only mixed acquisition, четыре readonly members, recovery/package writable; непрерывные leases/IDs, не readonly upgrade и не перенос failed proof. |
| CHK044 | plan468 п.2–3 + research: полный canonical/hash/finite complete480, strict WAV conversion+EOF, полный AAC decode, histories/session/privacy/optional times до первого эффекта; closed parser не ослаблен. |
| CHK045 | plan468 п.3–4 + packed append: hypothetical ref допустим только в private value proposal, не retained pair/current_/proof; genuine recovery g1 BOTH/readback и final seal/fresh inspection обязательны. Четыре старых member, IDs/queue/owner неизменны. |
| CHK046 | plan468 п.5: pre-effect D побайтно неизменен; possible effect начинается ДО commitMetadata, не с index/publicationStarted. Ошибка/исключение после успешного recovery commit также sticky failed package owner; recoveryPending=false недостаточно. Mandatory BOTH/readback после начала публикации не прерывается. Limits/actual retirement прежние. |
| CHK047 | plan/quickstart: meaningful physical positive RED, затем отдельные source/runtime gates; обе исходные fixture доказывают shape U, шесть новых cuts D/D/D/C/C/S заданы до запуска, прежние RED/полная цель не отменены. |

FR-012 покрыт encrypted existing ownership/strict verification/нефабрикованным
ACK/no plaintext и immutable members. FR-013 и Session2026-10-16 — неизменной
queue/original owner, без current-account inference/empty ledger. FR-014 —
отсутствием normal/upload/claim authority или нового egress. FR-022 — сохранением
leases/actual retirement/delete truth, без recovery cleanup. SC-005 получает
измеримые cold/repeated/negative/fault regressions, но требование100cycles этим
не закрывается; SC-006 сохраняет secret/content-free evidence и bridge boundary,
новых полномочий моста нет. Constitution I/II/III/IV/VI не меняются.
T116 остаётся OPEN; T120 privacy durable integration, T093 packaging и T027
route-policy границы не получают нового состояния от этого gate. Live GitHub
status/labels приняты только как сообщение main, самостоятельно не проверены.

Противоречий finalized immutable/validBOTH/orphan/no rollback не выявлено:
пишутся только изначально unused recovery и ещё finalizing package-state;
четыре готовых member readonly. Exact current physical extent исключает новый
необъяснённый tail, но не требует удаления старых interior orphan records.
Package peer может ссылаться на старую manifest generation; selected обязан
быть bound terminal, все retained refs проверяются без выбора старой истории.
Минимальные source reuse points существуют (LocalRecordingPackage.cpp:610–689
completeUnfinished, :691 value-only validator; V5LocalRecordingWriter.cpp:182–210
completed dispatch; ProtectedCustodyMetadata.cpp:1857–1933 commitMetadata и
:2035 mandatory postpublication readback). Это подтверждает форму технического
проекта, НЕ корректность будущей acquisition/sticky integration.

Fixed outcomes: repeated19 только13 D→U, итог R9/D6/U1/C2/S1; old24 только18
{package-state,op3} D→U, остальные23 сохранены. Ни ordinal, ни прежний flush
не admission authority: в каждой fixture нужен exact terminal-bound/unused
proof. Новые recovery index0/index1/final publication cuts дают D/D/D/C/C/S;
partial/singleton recovery не достраивается. 49 returned-fault ожиданий
rejected/sticky не меняются; cold observation не является retry failed owner.
Новых продуктовых вопросов0, технических blockers0; уточнение468 достаточно
для следующего test-only source gate, не для production edits или запуска.

### Перечитанные тематические checklist

| Файл | Checked / unchecked после reviewer update |
|---|---:|
| cold-prefix-recovery.md | 47 / 0 |
| packed-writer.md | 12 / 0 |
| start-owner-recovery.md | 10 / 0 |
| security.md | 27 / 0 |
| privacy-pause.md | 12 / 0 |
| audio-capture.md | 24 / 0 |
| advanced-routing.md | 14 / 0 |
| calendar-launcher.md | 5 / 0 |
| calendar-operation.md | 8 / 0 |
| calendar-wire.md | 5 / 0 |
| requirements.md | 22 / 0 |
| ux.md | 25 / 0 |
| **Всего** | **211 / 0** |

Cold-prefix до review41/6, после47/0: изменены только шесть новых markers и
добавлена собственная note. Прочие11 файлов неизменны: packed/security/owner/
privacy требования непосредственно ограничивают U; capture/routing/UX и
calendar gates сохраняются как не затронутые этим storage-срезом, не получают
нового implementation/runtime PASS. Исторические NO-GO/notes не стирались.

### Точные SHA-256 оснований (final normative snapshot)

```text
constitution.md d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859
spec.md         0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11
plan.md         ff12d7dfa5d3420809d3de484ec44c6df49485b04b77155ff09807918764e580
tasks.md        80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f
research.md     93c8fab9366b157ec23f66682fed51de1e3e265029c94569db54adf7656be2d5
data-model.md   32e644fb546816f6265cbd4a56630dd22109c43cfcc8b367368ce79425cc775a
quickstart.md   6892480695ae2adda176a65b93350c13a259fe793ab9c0b0d4cc23cb60daf2ff
packed contract f4624c6086fc585e1d0b976e20fcd99af1015249ae6b97dac93b88215699c555
feature.json    d4be889d623986959cc6b11beeb6227a4a33d0a1d9b2052e782db105439ba882
spec-kit-flow   5edf818b6ee27c7ee66d14edc003325ec7b16789eb1a195377cdeb901ae44887
product-gates   e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097
cold-prefix BEFORE markers/notes 1855b00f4c3b5b2736bd8ad9ef841fd4bacaf90d7dc5291bdacffe2b6a651221
```

Prerequisite discovery выполнен read-only вручную по feature.json/наличию
spec/plan/tasks/quickstart; script не запускался во избежание persistence.
Его прочитанный интерфейс не принимает --require-spec; успешный main
--require-tasks --include-tasks не выдаётся за наш запуск. Applicable enabled
checklist/analyze hooks отсутствуют. После завершения read-only analyze сделаны
только отдельно разрешённые reviewer-file updates. Никаких VM/build/tests,
Git/GitHub/source/norm/tasks/main-validation действий; старые AAC47/AAC56
TIMEOUT сохраняются unresolved, source216 unchanged — сообщение main, не новый
runtime факт этого requirements review. T116/full Windows/installed/hardware/
accessibility/release acceptance остаются открытыми.

## AAC60 — meaningful RED и допуск конструкции468-U2 до production diff

2026-10-21. **Saved runtime RED qualified; construction GO, C0/H0 в указанном
scope. Не actual production SOURCE GO и не runtime GREEN.** Использован
code-reviewer: только сохранённые evidence и read-only source tracing,
без Git/preflight execution. Основание требований — предыдущий final gate468-U2,
без повторной квалификации57–59 или нового полного обхода normative history.

Saved stage:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/aac60-terminal-unused-red`.
Прочитаны result.json, JUnit, FULL actual-test.log, декодированные UTF16LE
build.log/test.log, validate-input.ps1, source/prior manifests, changed.json и
точные staged CMake/test. JUnit: единственный ProtectedRecoveryTerminalUnused,
failures1/disabled0/skipped0, testcase time4.90482/status fail. Receipt terminal
true/build0/test_exit8/executed1/failure TEST/postflight216/owned_processes0;
Release, device_audio_read/real_network/installed/native_metadata_probes=false.
Build завершает V5LocalRecordingWriterTests.exe; CTest вызывает ровно
`--cold-recovery-terminal-unused`, filter anchored, serial180. Release asserts
не выключены: test:10 #undef NDEBUG. PowerShell NativeCommandError после CTest
не самостоятельная причина: фактическая причина — positive assertion.

Полный actual log содержит все19 baseline trace events и затем
COLD_TERMINAL_UNUSED_SHAPE cut13/role5/operation3/both_bound_history1/
recovery_children1/recovery_refs0/packed_both3/preflight_unchanged1. Следующая
строка — EXACT named assertion test:741:
`recovered.ok() && "terminal_bound_unused_recovery_must_finish_without_reencoding"`.
Timeout/build/helper failure нет. Helper test:312–337 перед возвращением требует
WaitForSingleObject=WAIT_OBJECT_0 и child exit88; два необходимых physical cuts
прошли helper до marker/assert. Это source-derived достижение assertion, не
утверждение о наличии child stdout. Setup: test:665–675 требует exact recovery
id.bin и три actual packed proofs; :703–725 проверяет actual BOTH bound histories,
selected degraded/artifacts против старого unfinished peer, privacy и unchanged
tree. Будущие positive final seal/AAC/preservation assertions после741 НЕ достигнуты
и этим RED не принимаются. Не long/repeated/full T116 или power-loss proof.

Exact identities, независимо сверены чтением файлов:
```text
source216 manifest 1c4a7dc59f0e466c006a988dc221aad10f4e51911927ba23171813d452229944
prior/AAC57       065608b7fb73fda87f776c17d08b2cb182b8a73bcae3cc5ae976dba95a1388c1
test              3bab3522dedf0a091e35cab1883653d764463e2a0460c720a66b62bfc393892b
CMake             75b8dd64056902eb152f4a277184c8c4e8e114d88e68e4f8ca52f1ba270cfa68
receipt PE        cfa6c2ef848fb8f858d040db534ae5a0a31bfd6b008ed73dddc727c2f356134d
PE bytes          1049600
```
Manifest содержит216 входов; source/prior и source/frozen57 отличаются ровно
двумя файлами CMake+V5test. Оба staged файла совпадают со своими manifest SHA;
все216 current host inputs совпали с AAC60. Production unchanged57 подтверждён
этим сравнением, не прежним отчётом. Сохранённый harness проверяет prior перед
upgrade, все216 до build и после test, PE до/после; failure TEST находится после
postflight и PE_CHANGED guard. PE здесь receipt-bound identity: отдельный PE
на host не читался, guest проверок reviewer не выполнял.

### Bounded construction permission

Предложенная private terminalRecoveryUnused конструкция соответствует468-U2;
блокеров C/H нет, можно готовить её exact production diff для нового source gate.

1. openUnfinished (ProtectedCustodyMetadata.cpp:1644–1772): добавить именно fresh
   mixed layout, selected finalizing/bound terminal, recovery exact unused/no
   BOTH-union ref. Все четыре готовых member readonly, recovery/package-state
   writeExisting; same native leases/IDs, без upgrade/create new identity или
   proof transfer. Остальные layout predicates не ослаблять. completedMetadata
   :1774–1802 можно расширить на новый layout для manifest и ПОСЛЕ настоящего
   recovery commit для recovery; manifest сохраняет actual bound generation,
   recovery требует genuine g1 BOTH. Простая установка enum не заменяет inventory.
2. V5 finishRecovery :182–248: новый layout отделить ДО unfinishedHistory
   (:215), который намеренно не принимает terminal artifacts. inspectUnfinished
   (LocalRecordingPackage.cpp:476–541) уже даёт finite complete480 без разрешающего
   history parser. Canonical/media/playback snapshots с полным требуемым strict
   extent, frameCount из prefix; existing writeWav comparison :365–455 только
   при готовом media snapshot и отсутствии writers. Никакого createWriter,
   writePlayback, retainPrefix/manifest rewrite в этом пути; temporary proofs
   отпустить до completed dispatch, native owners сохранить.
3. Один private recoveryJson builder вместо копии retainPrefix :740–744
   допустим; bounded/wiped CustodyBytes, тот же пятиключевой logical JSON.
   friend LocalRecordingPackage не становится public API/effect authority.
   Reason из selected terminal, frames=полный complete prefix, canonical tuple
   включает все logical bytes/SHA, включая неполный float tail без padding.
4. completeUnfinished :610–689 и value-only validateProtectedContent :691–766
   позволяют reuse BOTH history/hash/session/privacy/times/full AAC validation
   ДО birth с локальным proposal (recovery identity+sealed для semantic check).
   Не устанавливать этот ref в current_/retained pair/Inspection и не выдавать
   synthetic durable proof. После actual commitMetadata перечитать BOTH,
   потребовать byte equality с предложением и actual g1 identity/length/hash;
   заменить proposal настоящим ref до прежнего five-ref final commit и fresh
   sealed inspection. Уже существующий completed branch сохраняется.
5. Tiny local RAII bool& failed guard уместен: неактивен на preflight, active
   ДО commitMetadata, noexcept destructor маркирует package failed на каждом
   post-birth error return/exception (включая успешный recovery commit и более
   позднюю ошибку). recoveryPending=false/attempted index флаги это не заменяют.
   Отключить только после successful full final inspection. inspectProtected
   получает shared package COPY: исходный owner остаётся жив до уничтожения
   guard, поэтому ссылка на failed_ не висит при unwind. Не перемещать/сбрасывать
   последний package owner раньше guard. Обязательный publication BOTH/readback
   ACK внутри commitMetadata/commitImpl не прерывать UI cancellation.

Это условия уже предъявленной конструкции, не новый абстрактный план или
ослабление guard. На actual diff отдельно проверить first-effect/catch paths,
default branches, resource/pin retirement и отсутствие readonly upgrade/fake
ref publication. После source GO — предусмотренные positive/6cuts/refusal/
post-effect faults и регрессии; текущий RED разрешает construction, не GREEN.
AAC47 Debug long и AAC56 intermittent child timeout остаются unresolved, причина
ими не установлена. Записан только собственный report; source/norm/tasks/
checklists/main validation/Git/GitHub/VM/build/tests не менялись/не запускались.

### STOP — construction GO отозван до production edits: H1 dispatch classification

Уточнение в том же reviewer turn после сообщения main. **Construction NO-GO,
C0/H1: предыдущий construction GO выше преждевременен и отозван.** Историческая
запись сохранена; самостоятельная квалификация meaningful AAC60 RED остаётся
действительной, не разрешает production implementation.

Подтверждённый source путь: V5LocalRecordingWriter.cpp:165–172 вызывает layouts
unused → completed → wavReady → playbackStarted и прекращает поиск после
первого structurally successful acquisition. ProtectedCustodyMetadata.cpp:
1708–1737 проверяет bound manifest ref/generation и inventory, но не закрытую
семантику terminal history. Поэтому terminal-bound/exact-unused recovery может
успешно получить playbackStarted; новый fallback ПОСЛЕ него недостижим.
V5.cpp:212–216 затем вызывает unfinishedHistory, который в LocalPackage.cpp:
551–566 намеренно требует unfinished parser и отвергает terminal artifacts.
Отказ finishRecovery не вызывает новый fresh acquisition. Это не исправляется
добавлением enum или completed dispatch.

Перестановка нового layout перед playbackStarted также недостаточна: без
семантической классификации structural admission способен перехватить прежний
normal/unfinished playback R. Нужен отдельный bounded технический dispatch
predicate на fresh acquisition/preparation: strict selected-terminal/bound и
BOTH old/terminal history через reuse закрытой проверки completeUnfinished,
с отделением прежнего unfinished R ДО выбора новых прав/пути. Ни current.reason,
ни substring/ordinal, ни отказ старого owner не являются классификацией.
Четыре readonly member для U, continuous leases, no readonly upgrade и отсутствие
StoreOwner executor handoff должны сохраниться. Здесь не выбран новый дизайн:
main/Fermat готовят минимальное technical clarification, затем нужен отдельный
scoped requirements/construction и actual diff gate. Production ещё не менялся
по сообщению main; reviewer source writes не делал.

Недостающая dispatch формулировка затрагивает актуальность прежнего bounded
requirements вывода468 для этой конструкции: прежний C0/H0 не является допуском
обходить H1. Маркеры checklist сейчас не изменены (текущий write scope — только
own report); вопрос должен быть явно перепроверен при clarification. Это
технический пробел, не новый продуктовый выбор. RED/старые TIMEOUT не стираются;
никаких VM/build/tests/source/norm/tasks/Git/GitHub действий.

## Round469 — scoped requirements/analyze/construction re-gate

2026-10-21. **GO предъявленной конструкции469 до подготовки production diff;
C0/H0 в этом scope. H1 dispatch specification gap устранён amendment469.**
Прежний construction GO остаётся отозванным исторически: STOP выше не стёрт.
Это новый вывод на новых SHA, не actual production SOURCE/runtime GO.

Прочитаны целиком пять новых sections469, affected cold-prefix CHK042–047 и
относящиеся к dispatch текущие методы. Предыдущие468 требования вне delta
сохранены; полного feature/history audit или повторной runtime qualification
не было. Применены speckit-checklist, read-only speckit-analyze и code-reviewer
для API feasibility; затем отдельно выполнены только reviewer-file updates.
Hooks before/after checklist/analyze YAML разобран: все applicable disabled.
Prerequisite discovery read-only по feature.json и существующим artifacts,
script/persistence/Git не запускались.

Обязательный порядок теперь определён до первого openUnfinished: private
StoreOwner recoveryReason → metadata-only readonly classification → release
metadata → fresh corresponding acquisition → repeated full executor preflight.
Normal сохраняет старую unused/completed/wavReady/playbackStarted chain;
terminal использует только completed/U, никогда fallback R. Это устраняет
перехват в обе стороны, не перестановка структурных layouts и не эвристика.

Construction/source obligations, сохранённые при этом GO:

- Package slots и metadata slots НЕ обязаны совпадать: каждый BOTH bound ref
  сопоставить по object/generation/length/SHA с actual metadata; selected package
  manifest обязан совпасть именно с selected metadata, без rollback.
- Shared closed parser возвращает только CustodyFileResult<ReasonCode>/value,
  не Inspection/authority. Normal none — explicit unfinished parse selected и
  остальных bound histories; unreferenced metadata peer не получает нового
  semantic admission ограничения, privacy/times разных normal поколений не
  обязаны совпадать. Terminal — selected degraded/artifacts и полная строгая
  BOTH metadata privacy/session/optional-times проверка как в completeUnfinished.
- No-manifest none только если нет manifest в BOTH package slots, оба phases
  unfinished, canonical live/unsealed с согласованным object/container, иных
  refs нет, cancel проверен. Один отсутствующий selected manifest при наличии
  peer ref не none. IO/crypto/quota/cancel/parse/binding errors не normal.
- readPackage (Metadata.cpp:1473–1501, pair :924–990) удерживает изолированную
  readonly class lease и не сканирует audio. openPackageMember только manifest
  (Files.cpp:621–663) использует exclusive identity internally, но блокирует
  exposed write capability. Это не readonly upgrade или открытие audio.
  Не добавлять внешний NativeJob вокруг readPackage: его собственный job уже
  охватывает validation/discovery и pair admission. Caps64KiB/job4/pin32 прежние.
- Metadata ref binding/decryption reuse readValidatedMetadataPair и existing
  bounded logical read; shared closed semantic reuse RecordingJson::manifest
  (LocalRecordingPackage.cpp:127–175), normal unfinishedHistory :539–563 и
  terminal BOTH logic :660–675. Ни substring, ни current.reason не классификация.
- Все metadata buffers/pairs/member aliases и leases реально retire ДО fresh
  content acquisition; readonly classification не переносится как proof через
  gap. StoreOwner остаётся на worker. Executor снова проверяет history/content
  на genuine fresh acquisition; terminal не открывает audio/manifest writable.
- Остальная468 конструкция неизменна: full WAV/EOF/AAC preflight, local value
  proposal, actual recovery g1 BOTH/readback, sticky guard BEFORE birth включая
  subsequent exceptions, живой shared package до destruction guard, final ACK
  и fresh inspection без прерывания обязательного readback.

Affected CHK042–047 supported6/6; добавлена краткая review note, новых критериев
и marker changes нет. Cold-prefix47/0, остальные11 thematic markers неизменны;
existing aggregate211/0 — качество требований, не новая implementation приёмка.
FR-012/013/014/022 и SC-005/006 остаются у T116/#7444; spec Session2026-10-16,
original owner/queue/delete fences, Constitution и соседние задачи не меняются.
Нет новых unmapped tasks, product/schema/API answers или C/H contradictions в
этом delta. Общая feature coverage не пересчитывалась и не принимается.

Exact SHA-256 текущих оснований:
```text
plan.md         39d3f3bf9344e1c04c1acefda6fa9f5ec2870f0de8556dec507cf71545925a45
research.md     da53a2492e7cc0f1b058ab3d179718fab95aac8bf9957f33b8ff5f3a610bfe9d
data-model.md   d61235b9454564897fdacfdecd127fc0a9676b48a2b2011b1b1df692fcf7db9b
quickstart.md   6c4eb56f763f07dbbe83cdd59393437653d95b1c49c62666abe6d58e618ae564
packed contract e6af6d4d402c19fa47b8a71931f7573eb0c4673d3f19365926f78f140c65fc56
spec.md         0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11
tasks.md        80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f
constitution.md d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859
```

Следующий gate — exact actual production diff, включая reachable dispatch,
slot-independent binding, normal no-regression, no-manifest/cancel, lease/job
boundaries и post-birth RAII lifetime; до него runtime GREEN не допущен. AAC60
qualified meaningful RED остаётся, AAC47/AAC56 unresolved не исправлены и не
заменены. Записаны только own report и cold-prefix reviewer note. Код/tests/
norms/tasks/VM/build/tests execution/Git/GitHub/main validation не затрагивались.

## AAC61 — actual SOURCE gate dispatch469 и terminalRecoveryUnused

2026-10-21. **SOURCE GO точному frozen AAC61 перед GREEN; C0/H0, блокирующих
source findings не обнаружено. Не runtime PASS и не full T116 acceptance.**
Применён code-reviewer с read-only file diffs вместо Git/preflight по прямому
ограничению пользователя. Полный spec/history/runtime повторно не разбирался;
основание — accepted469 requirements/construction и meaningful AAC60 RED.

Frozen stage:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/aac61-terminal-unused`.
Manifest216 SHA-256:
`95e989ca923b82642a50b150da1d8e8fe96b878cce20849b8fa11d39264edf04`.
Prior AAC60:
`1c4a7dc59f0e466c006a988dc221aad10f4e51911927ba23171813d452229944`.
Независимое сравнение manifest/current показывает ровно шесть changed files;
все216 current входов и все шесть staged копий совпадают с manifest. Тест/CMake
и остальные210 входов AAC60 неизменны. Старые production bytes совпадают с
AAC57 по уже установленному baseline, но directory57 содержит не полный source:
пять before files найдены в прежних frozen stages и проверены по SHA из AAC60,
не по именам/времени. Для LocalRecordingPackage.h отсутствует отдельная старая
копия: in-memory inverse removal ровно шести новых private friend/comment/
declaration lines восстанавливает exact AAC60 SHA; иных header changes нет.

Exact six SHA-256:
```text
apps/windows/RecApp/Storage/ProtectedCustodyMetadata.h
4a6d9b74619b44aa84208e80d5c5bf6a1ef0b7a242dbf4767b7de4cd455e9c12
apps/windows/RecApp/Storage/ProtectedCustodyMetadata.cpp
010baad64c6bee80d315621f8bc8ad75390f0fc63e55fefaaa7c0bce75c8e043
apps/windows/RecApp/Recording/LocalRecordingPackage.h
a935cb155da2426f7d0ecc79fcf4eca4212af4d65084427e04b8a3febd3aef36
apps/windows/RecApp/Recording/LocalRecordingPackage.cpp
83d3469dff19e59a9dd25d51e957de5b6dab8ef49faa7bf37422afa1c7434e63
apps/windows/RecApp/Recording/V5LocalRecordingWriter.h
2893ddf0473599fc22eea48ea8b52e4f8b950b12d8680594661b088bd3e87ebd
apps/windows/RecApp/Recording/V5LocalRecordingWriter.cpp
d85e1ab669608180b0f32f9b9decadaeb4e9e71ab6671465616eb0a9156f8f09
```

### Проверенный фактический поток

1. V5LocalRecordingWriter.cpp:165–182: recoveryReason вызывается ДО первого
   openUnfinished. Error прекращает prepare; terminal идёт completed→U и
   возвращает отказ без R. Normal сохраняет прежнюю chain с прежними условиями
   recoveryRequired. Новый enum не оставлен недостижимым fallback после R.
2. Metadata.cpp:1644–1712: readPackage вызывается без внешнего NativeJob.
   BOTH phases unfinished, только live packed/unsealed canonical с одинаковыми
   object/container и optional sealed manifest одной identity; no-manifest none
   только после BOTH/canonical/cancel checks. Peer-only manifest при missing
   selected ref отвергается. Открывается только manifest через retained readonly
   package-state, не audio; job начинается ПОСЛЕ readPackage. Все temporary
   member/indices/bytes/pair leases освобождаются при возврате до fresh acquisition.
3. Metadata.cpp:1686–1707: selected bound generation совпадает с selected
   metadata; каждый ref ищется по generation среди независимых metadata slots,
   length/hash проверяются, object проверен при сборе manifestId/context и при
   genuine member open. Bound mask не определяется номером package slot.
   LocalPackage.cpp:611–640: explicit normal parse только bound histories,
   без новой equality и без semantic constraints на unbound metadata peer.
   Terminal требует selected degraded/artifacts/session и прежние BOTH
   privacy/times/degraded-peer-byte equality. Parse error не none; cancel
   перепроверяется StoreOwner после helper. Это value-only private helper.
4. Metadata.cpp:1726–1841: U требует selected finalizing, current bound manifest,
   прежние BOTH union/identity/container/validateRefs. Canonical/media/playback/
   manifest readExisting, recovery/package-state writeExisting; recovery exact
   unused, остальные actual completed inventories. Новые IDs/RNG для U не
   выделяются; все три packed owners readonly. Старые unused/completed/WAV/
   playback branches сохраняют прежние predicates и различия прав.
5. V5.cpp:201–218: U executor сначала inspectUnfinished finite complete480,
   canonical proof и strict media/playback extent; frameCount сравнен с canonical
   logical prefix. Existing writeWav с готовым media snapshot выполняет только
   bytewise comparison/EOF/canonical zero-read и sealAudio(media,false), без
   createWriter/checkpoint/encode. Temporary prefix/snapshots отпускаются, native
   owners остаются; далее общий completed dispatch. Full semantic history
   повторяется на executor, worker classification не proof и не StoreOwner handoff.
6. LocalPackage.cpp:642–752: existing selected manifest binding, full BOTH history
   helper, canonical/media/playback bounded hashes и decoder до эффекта. U
   recovery proposal создаётся только в LOCAL candidate/bytes; actual current_/
   retained pair/Inspection не подменяются. RecoveryJson :V5.cpp753–762 — один
   прежний пятиключевой builder, reused retainPrefix без смены logical JSON,
   canonical length/SHA включает полный stream, frames — floor(bytes/1920).
7. LocalPackage.cpp:734–750: readers/manifests retire до birth; cancel до эффекта.
   FailAfterBirth active=true ДО commitMetadata(DATA раньше index). Любой return
   или unwind после этого ставит package failed, включая allocation/error после
   successful recovery commit. completedMetadata читает actual g1 BOTH,
   проверяет exact inventory, и обе actual recovery bytes сравниваются с proposal;
   actual reference заменяет local proposed ref до unchanged final commit.
   Package passed COPY в inspectProtected, guard's bool& жив до его destructor;
   deactivate только после full fresh inspection OK. RecoveryPending=false сам
   по себе не используется как sticky protection. Прежний обязательный internal
   BOTH/readback ACK внутри publication не прерывается этим внешним guard.
8. Metadata.cpp:1846–1877: completedMetadata разрешён только прежнему completed
   и новому U для manifest/recovery, требует finalizing/not failed; recovery
   selected g1==metadataGenerations, actual BOTH read и inventory. Added
   completedPackageRole(&pair) допустим и при preheld writable metadata lease
   (Files.cpp:716–746), не readonly upgrade и не принятие singleton/orphan.

В reviewed delta нет новых pools, MF per-frame изменений, quota/cache/deadline
ослабления, прав normal/upload/claim, queue/original-owner изменения или записи
четырёх готовых member. Compile/link выполняться не пытались; conditional
declarations/friends/includes рассмотрены, actual build ещё не доказан.

Источник допущен к предписанному GREEN на exact snapshot; этот review не
принимает ещё не выполненные U six-cut/negative/post-birth fault/dispatch-normal
регрессии, полный old24/repeated19/long/native final-source набор. Старый
construction STOP/H1 сохранён; исправление маршрутизации доказано здесь именно
по actual source, не одним порядком enum. AAC47/AAC56 причины остаются
нерешёнными; hardware/installed/UI/release/full Windows/T116 открыты.
Дополнен только own report; source/tests/norm/tasks/checklists/main validation/
VM/build/tests execution/Git/GitHub не менялись/не запускались reviewer.

## AAC61/AAC62 — независимая квалификация сохранённых Release runtime

2026-10-21. **Scoped runtime PASS/GO: AAC61 1/1 и AAC62 7/7 на одном
зафиксированном source/PE. Несоответствий в предъявленных результатах нет;
это НЕ полный T116/U acceptance и НЕ установление причины прежних RED.**
Применён code-reviewer в границах saved-evidence review: без Git/preflight,
VM, сборок и выполнения тестов. Прочитаны полностью result.json/result.xml,
actual-test.log, validate-input.ps1, changed.json и декодированные UTF16LE
build.log/test.log обеих стадий. XML system-out усечён на 1024 bytes;
конечные markers проверены по полным actual-test.log, не по усечённому XML.

Stages: внешний BASE `/Users/yshishenya/Documents/graf-f200-public458.po8CtB`,
`aac61-terminal-unused` и `aac62-terminal-regressions`.
Оба manifest216 SHA-256:
`95e989ca923b82642a50b150da1d8e8fe96b878cce20849b8fa11d39264edf04`.
Независимо пересчитаны hash манифестов, все216 current inputs и шесть staged
AAC61 files: mismatch0. AAC61 prior60
`1c4a7dc59f0e466c006a988dc221aad10f4e51911927ba23171813d452229944`,
ровно шесть production changes; тест/CMake неизменны meaningful RED60:
test `3bab3522dedf0a091e35cab1883653d764463e2a0460c720a66b62bfc393892b`,
CMake `75b8dd64056902eb152f4a277184c8c4e8e114d88e68e4f8ca52f1ba270cfa68`.
AAC62 source и prior byte-identical source61, changed=[]; harness byte-identical
61, SHA `b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a`.

Обе квитанции: Release/target V5LocalRecordingWriterTests, terminal=true,
build=0/test_exit=0/postflight=216/owned_processes=0, failure отсутствует.
Одинаковый receipt-bound PE SHA-256
`37f5101a918ad7443cae4a2fdf7dece23296aaf4f2ebd3e9b57bf3268a6a02ad`,
1059328 bytes. Harness проверяет исходники до/после, prior до upgrade,
PE до/после CTest, owned processes до/после; успешно завершённый путь
подтверждён полями receipt. Сам PE на Mac не представлен и отдельно не хэширован;
его identity квалифицирована по сохранённому harness/receipt, не новым guest check.
Команды: cmake --config Release --target V5LocalRecordingWriterTests -j1,
ctest -C Release с anchored exact-name pattern; timeout/guards не менялись.

AAC61: ровно ProtectedRecoveryTerminalUnused,
CLI `--cold-recovery-terminal-unused`, JUnit time=6.65847s, status=run,
failures=0/disabled=0/skipped=0. Полный журнал: exact 19-event baseline,
shape13 role5/op3 BOTH bound histories + unused recovery, затем child_exit=88 /
waited=1 / terminal_unused=1 / continued=1 и
`COLD_TERMINAL_UNUSED cuts=1 continued=1 four_members_ids_queue_unchanged=1 cold_aac_privacy=1`.
Финальный CUTS marker executed1/continued1, затем Test Passed. Source mapping
подтверждает: child wait/exit88 assert до shape; positive recovered.ok,
semanticVerified/degraded/noNormal/noKeepable/duration1000, generation+1,
четыре готовых members/IDs/queue неизменны, fresh cold AAC/privacy/times,
readonly disk hash, idle memory/job/pin проверки до конечного marker.
Release assertions активны через #undef NDEBUG до <cassert>.
Это тот же tests-first positive, который падал в AAC60; positive теперь дошёл
до всех последующих assertions. Child stdout отдельно не предъявлен/не заявлен.

AAC62: JUnit ровно следующие семь status=run, failures0/disabled0/skipped0;
каждый CLI соответствует имени, полный log каждого завершён Test Passed:

| Test | CLI suffix после --cold-recovery- | XML seconds | Полный конечный результат |
|---|---|---:|---|
| ProtectedRecoveryReturnedFaults | returned-faults | 20.6233 | 26/26 hit1/rejected1; exact-memory/canonical IDs queue/late-seal cold decode |
| ProtectedRecoveryPlaybackReturnedFaults | playback-returned-faults | 40.6399 | 23/23 hit1/rejected1; reset read failures2/7,2/8 after_event1; exact-memory |
| ProtectedRecoveryPlaybackRestart | playback-restart | 50.5089 | 19 physical cuts; rebuild9/completed2/U1/refused6/sealed-readonly1 |
| ProtectedRecoveryCompletion | completion | 8.20065 | cases5: positive2/preserved refusals3; generation+1/five members/IDs/queue/history |
| ProtectedRecoveryWav | wav | 7.54061 | op6 cut7 continued1; seven WAV refusal cases0..6, unchanged disk |
| ProtectedRecoveryPlayback | playback | 15.0725 | ten refusal cases0..9; measured oldgen2, cut12 continued1 |
| ProtectedRecoveryPlaybackPartial | playback-partial | 128.161 | real partial524288<complete732186/g3, codec6/c00d36c4; full recovery/fresh cold/privacy/readonly/idle |

Repeated19 перечисляет все cut1..19 по порядку с child_exit88/waited1.
Cut13 теперь U; final summary continued12 = rebuild9+completed2+U1,
отказов6, sealed-readonly1; sealed не считается recovered continuation.
Long partial final marker: cut28 role2/op6 child_exit88 duration_ms60000,
immutable_old_extent1/readonly_unchanged1, достигнут ПОСЛЕ privacy и idle audits,
а не только partial_recovered. Полный CTest total270.76s; это время набора,
не замена индивидуальным deadline и не performance acceptance.

Явная coverage-граница: pattern62 содержит ошибочное `V5LocalRecordingWriter`
без `Tests`; anchored filter НЕ запустил default V5LocalRecordingWriterTests.
Поэтому квалифицировано 7, НЕ 8; отсутствие default не является skip внутри
этих семи, но default/full24 coverage данным stage не доказано. Отдельный
живой AAC63 не читался и результат ему не приписан. AAC61 и62 вместе не
доказывают новую U six-cut/negative/post-birth fault matrix. Исторические
AAC47 Debug-long и AAC56 intermittent child-timeout остаются нерешёнными;
их причины/устранение не выводятся из этих PASS. Generated data/native
filesystem+codec runtime не real audio/network/install/hardware/powerloss/
UI/release/full Windows acceptance. Записан только этот append own report;
implementation/norm/tasks/checklists/main validation и внешние системы не менялись.

## AAC63/AAC64 — saved final-source default24 и native recovery qualification

2026-10-21. **Scoped runtime PASS: AAC63 1/1 и AAC64 4/4.** Независимо
прочитаны полностью receipt/result.xml/actual-test.log и декодированные UTF16LE
build.log/test.log, проверены source/prior/changed/harness. Это квалификация
выполненных сценариев, не новый source/requirements gate и не полный T116 GO.
code-reviewer применён без Git/preflight/test execution по ограничению пользователя.

Внешние стадии BASE `/Users/yshishenya/Documents/graf-f200-public458.po8CtB`:
`aac63-v5-default`, `aac64-native-recovery`. Их source.sha256 и prior.sha256
byte-identical manifest61:
`95e989ca923b82642a50b150da1d8e8fe96b878cce20849b8fa11d39264edf04`.
Обе changed=[]; 216 строк, все216 current inputs independently hash-match,
никакого source upgrade внутри63/64. Оба validate-input.ps1 byte-identical61,
SHA `b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a`.
Harness сохраняет source pre/post, PE pre/post, owned pre/post checks и anchored
exact CTest pattern, Release configuration. Квитанции обеих стадий:
terminal=true/build=0/test_exit=0/postflight=216/owned_processes=0, без failure.
Все testcase status=run; failures0/disabled0/skipped0 в обеих JUnit suites,
полные журналы заканчиваются Test Passed для каждого exact name.
XML system-out усечён1024bytes; полнота markers проверена отдельно по FULLactual.

AAC63: target V5LocalRecordingWriterTests, CLI без аргументов, exact CTest
V5LocalRecordingWriterTests; XML time=62.6848s. Receipt-bound Release PE
`37f5101a918ad7443cae4a2fdf7dece23296aaf4f2ebd3e9b57bf3268a6a02ad`,
1059328bytes, тот же61/62. Это фактически выполняет отсутствовавший в62
default test, не переименовывает62 в8/8. Полный лог подтверждает playable3,
playable refusal cases0..14 с unchanged disk/memory/jobs/pins, finite prefix
capturing/finalizing и sealed/refusal проверки, exact trace24 и ВСЕ cut1..24
по порядку с child_exit88/waited1/canonical_queue_unchanged1. Cut18 role5/op3
имеет explicit terminal-unused shape и continued1. Summary:
trace_events24/executed_cuts24/sealed_cold_decode1/continued12/recovered_unused2,
process_crash1/power_loss0. Здесь continued12 не включает unused2; sealed24
не выдан за continuation. Также достигнуты protected playback held_jobs0/2
с успешным decode48128frames. Source Release assertions остаются активными;
результат не hollow PASS и не фильтр одного recovery подпути вместо default.

AAC64: target NativeCaptureStorageIntegrationTests, Release PE из квитанции
`ddfe06a0fa44aff8be77fb28f8fe045d1df5130dcbeb5b286cd53b1ba6e81794`,
2570752bytes. Точные CTest/CLI соответствуют CMake/source dispatch;
RUN_SERIAL TRUE/TIMEOUT240, #undef NDEBUG в начале native test source.

| CTest | CLI | XML seconds | Проверенные markers полного лога |
|---|---|---:|---|
| NativeProtectedStartOwnerRecovery | --protected-start-owner-recovery | 15.663 | modes0..7, sealed-before-finish/exact-row/cold/owner_A, actual final-queue ambiguous rename |
| NativeProtectedStartOwnerDegradedRestart | --protected-start-owner-degraded-restart | 1.20744 | drained attempt, healthy worker, generation2, owner_A/current_B, no mutation ticket,100frames, unchanged disk/exact memory |
| NativeProtectedStartOwnerUnfinishedRestart | --protected-start-owner-unfinished-restart | 24.7845 | modes0..4 плюс live-playback/stop/finalizer/deletion/purge subflows, ожидаемые cancellations/refusals, cold final checks |
| NativeProtectedRecoveryLivePlayback | --protected-recovery-live-playback | 5.98535 | actual result ready при live recording, muted play/seek, stale_command0, live unchanged, EOS finish, cold three owned rows/exact memory |

Unfinished CLI source действительно вызывает не только modes0..4, но и
protectedRecoveryLivePlayback(true/1/2) и три protectedDeletionDisplayDrain;
full log достигает UNFINISHED_LIVE_PLAYBACK, UNFINISHED_STOP,
UNFINISHED_FINALIZER actual_recovery_retirement/readback_ack/cold_new_valid_decode,
UNFINISHED_DELETION cancellation_before_release/premature_readback0/drain0 и
двух UNFINISHED_PURGE user_removal0/1 с actual retirement before purge,
cold rows0/OS absence/exact memory. Значения error2 и native995 в намеренно
отказных/отменённых подслучаях не являются ошибкой CTest и не замаскированы:
ожидаемые markers достигнуты до Test Passed. Purge здесь generated-fixture
сценарий; recycle_bin_not_shredding1 сохранён, реальное пользовательское
удаление/безвозвратное стирание не заявляется.

PE identity квалифицирована по сохранённым receipt и неизменному harness с
before/after hash guard; отдельный PE на Mac не хэшировался и guest не читался.
AAC64 native_metadata_probes=true соответствует прежней семантике target;
device_audio_read=false/real_network=false/installed=false и markers protected_http0
не превращаются в hardware/recording/HTTP/installed acceptance. Из этих PASS
не следует причина или исправление AAC47 Debug-long/AAC56 intermittent timeout.
Новая U six-cut/negative/post-birth матрица ещё не выполнена и не принимается;
T116/Windows full goal/release остаются открыты. Дополнен только own report;
source/norm/tasks/checklists/main validation/Git/GitHub/VM/build/tests не менялись
и не запускались reviewer.

## U six-cut actual SOURCE request — входной SHA изменён до начала diff review

2026-10-21. SOURCE verdict НЕ выдан; review остановлен на identity precheck
по условию пользователя «if hash still match». Дважды независимо прочитанный
current V5LocalRecordingWriterTests.cpp SHA-256:
`30a98c69048f4d5842c5e3ba56173a1f6c82372f9ce3a5ab3db9e20f082db19b`,
не предъявленный
`a46a16a1bfe51fda3558a39d30b7aa021d52ce2ce8b1f1c275351977ab36da86`.
CMake совпадает с запросом:
`2944bf566d44d186f478eb7405e311e0ecedf57e39c1be0939946297fb1647a7`.
Это blocker идентичности review input, НЕ найденный дефект теста и НЕ C/H
assessment. Нужен подтверждённый final test SHA/frozen snapshot, после чего
проверяется exact two-file diff против сохранённого AAC60. code-reviewer и
ponytail-review прочитаны, но содержательный review/complexity verdict не
выполнен для неподтверждённого input. Только append own report; VM/build/tests/
source/norm/tasks/checklists/Git/GitHub не затронуты.

## AAC65 — actual test-only SOURCE gate U six-cut, final frozen30a98c69

2026-10-21. **SOURCE GO / C0/H0 для точного AAC65 перед runtime.** Оркестратор
(основной агент), не человек, подтвердил final30a98c69 после прежней остановки
на input mismatch; это не подтверждение человека на коммит. Тот STOP
сохранён выше и не был source finding. Новая norm gate не выполнялась:
проверен exact two-file diff против AAC60, с применением существующего
468-U2/469 oracle. code-reviewer + ponytail-review прочитаны полностью;
Git/preflight/VM/build/tests по ограничению не выполнялись.

Stage `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/aac65-terminal-sixcuts`.
Manifest216 SHA-256:
`827b13cad75dba2469928d115cc51bcc06aecc7a7f367c0633337377d80942d9`.
Prior byte-identical AAC64 source95e989ca; changed.json и manifest delta ровно:
test `30a98c69048f4d5842c5e3ba56173a1f6c82372f9ce3a5ab3db9e20f082db19b`,
CMake `2944bf566d44d186f478eb7405e311e0ecedf57e39c1be0939946297fb1647a7`.
Все216 current inputs и обе frozen copies независимо совпадают с manifest;
остальные214 (включая production469) неизменны. Сохранённые AAC60 test/CMake
проверены по prior hashes3bab3522/75b8dd64, полный file diff прочитан;
финальное повторное чтение обоих current hashes сохраняет предъявленные SHA.

Проверенные места (V5LocalRecordingWriterTests.cpp):

- :360–405: extracted terminal shape сохраняет exact-unused recovery/id-only,
  actual BOTH packed proofs, BOTH bound manifests normal-peer/selected-terminal,
  privacy и selected generation. Все temporary owners/readers/proofs retire
  до возврата; whole-tree equality теперь проверена и после их destruction.
  Старый caller :746 проверяет тот же afterCrash и использует ту же generation.
- :406–439, :796/:838: original-member и sealed-inspection helpers сохраняют
  прежние hashes/semantic duration/times/AAC assertions. Старое repeated-only
  privacy условие передано явно; normal/default/WAV/playback expectations не
  расширены/не ослаблены. Фильтрация recovery bytes для U соответствует прежнему
  inline коду; id.bin и четыре готовых members остаются в сравнении.
- :854–918: новый generated1s fixture использует прежний genuine writer/MF,
  native wrappers и child helper. Original trace проверяется на ВСЕ24 tuples,
  fixture cut фиксирован18 {5,3}; затем actual shape подтверждается независимо
  от ordinal. До crash cases U baseline обязан дать ровно шесть native rename
  events {{4,2},{4,3},{4,2},{4,3},{5,2},{5,3}}, successful semantic/degraded
  generation+1 и fresh cold readonly proof. Idle baseline взят ДО fixture work,
  проверен после полного release обеих baseline roots/owners.
- :920–979: outcomes DDDCCS constexpr до результатов. Для каждого случая новый
  root→actual fixture child cut18→fresh shape→второй actual child cut1..6.
  Прежний helper :306–338 требует native selected role/op, wait OBJECT0 и
  exit88; missing event/child timeout/cleanup90 не засчитываются как D.
  Child60/cleanup10/trace256/native hooks не изменены. Контекст и handles
  не наследуются; metadata progress остаётся вне custody root.
- :928–951: после child проверены exact package phase/generation; readonly pair
  отпущен до fresh recovery acquisition. D/S требуют !ok с ошибкой и целое
  afterCrash дерево без изменений, включая ПОСЛЕ recovered/store destruction.
  C требует semanticVerified/trustedPrefix/degraded/noNormal/noKeepable/1000ms,
  generation+1 и все пять actual completed members byte-identical после
  recovery (исключены только разрешённые package-state публикации).
- :951–981: four originals/все IDs/queue сохранены во всех исходах; C/S fresh
  sealed current refCount5 с единственной sealed-flat recovery g1, full AAC/
  privacy/times и повторный recovery refusal; readonly hash после release.
  На каждой итерации память вернулась к pre-baseline idle, все4 jobs/32pins
  заново доступны. Конечные counters требуют ровно3D/2C/1S; нет either-outcome,
  skip или выбора результата по наблюдению. Данные только generated;
  audio/network/installation пути не добавлены.
- :1548–1549 и CMake:184–185: новый exact CLI
  --cold-recovery-terminal-unused-crash вызывает только новый тест; CTest
  ProtectedRecoveryTerminalUnusedCrash RUN_SERIAL TRUE/TIMEOUT180. Прежние
  CLI/default dispatch/CTest properties и Release #undef NDEBUG сохранены.
  Типы/объявления/порядок helper definitions и все callers просмотрены;
  конкретного compile/lifetime/false-PASS blocker не найдено. Build не запускался.

Ponytail (только сложность): **Lean already. Ship.** Извлечены реальные повторные
проверки, новых зависимостей/продуктовых hooks/параллельной инфраструктуры нет;
это не разрешение публикации и не runtime verdict.

Допущен запуск exact AAC65 six-cut, но 180s feasibility, actual six native
cuts/DDDCCS и регрессии извлечённых старых helpers должны быть доказаны runtime
на этом новом manifest/PE; PASS61–64 не приписывается изменённому тесту.
U preflight negatives/post-birth returned-fault/sticky gates и полный T116
остаются открыты. AAC47/AAC56 RED не отозваны/не объяснены. Дополнен только
own report, без code/norm/tasks/checklist/main-validation/Git/GitHub/VM действий.

## AAC65 — independent saved runtime qualification U six-cut Release

2026-10-21. **Scoped runtime PASS/GO: ProtectedRecoveryTerminalUnusedCrash,
1/1, XML16.7402s.** Прочитаны полностью saved receipt, JUnit, actual-test.log
и декодированные UTF16LE build.log/test.log. code-reviewer использован только
для saved-evidence review без Git/preflight/VM/build/test execution.

Stage `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/aac65-terminal-sixcuts`.
Независимо пересчитан manifest216
`827b13cad75dba2469928d115cc51bcc06aecc7a7f367c0633337377d80942d9`;
все216 current inputs и обе staged copies совпадают, prior byte-identical64.
Ровно test30a98c69048f4d5842c5e3ba56173a1f6c82372f9ce3a5ab3db9e20f082db19b
и CMake2944bf566d44d186f478eb7405e311e0ecedf57e39c1be0939946297fb1647a7;
остальные214 неизменны. Saved harness byte-identical64, SHA
`b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a`.
Receipt Release/target V5LocalRecordingWriterTests, terminal=true/build0/test0,
executed1/postflight216/owned0, failure отсутствует. Receipt-bound PE
`de9d8b614111f534e13daa03b5e0c25f80e91e73aa57c3131cb4e918e4d27e91`,
1085952bytes; identity основана на saved harness source/PE before-after guards,
не на новом guest check/локальном PE read. Build log содержит штатную CMake
regeneration после изменения CMakeLists, затем успешную компиляцию/линковку
Release теста; timestamp result=-1 там причина regeneration, не build failure.

Точное CTest имя и фактический CLI --cold-recovery-terminal-unused-crash
совпадают с source/CMake; serial180 и child60/cleanup10 не увеличены.
JUnit tests1/failures0/disabled0/skipped0, testcase status=run, без failure/skip
nodes. XML output усечён1024bytes, поэтому финал проверен по FULL actual log:
семь shape18 markers и шесть последовательных CUT ordinal1..6:
{4,2}D / {4,3}D / {4,2}D / {4,3}C / {5,2}C / {5,3}S.
Каждый marker имеет fixture_child_exit88/U_child_exit88 и immutable
four-members/IDs/queue. Финал явно cuts6/refused3/completed2/sealed_readonly1/
oracleDDDCCS/exact_memory1/process_crash1/power_loss0, затем Test Passed.
Child-failed markers0; непопадание в native cut или timeout не выдано за D.

Точное число13 children доказано source/control-flow: одна fixture в U baseline
и по две fixture/U-child на каждом из шести cut; каждая helper invocation
обязана пройти wait OBJECT0/exit88 assert. Отдельного13-line child stdout или
process census в saved log нет, и такой evidence не заявляется. Original24 и
U6 baseline traces проверяются assertions в source до cases, но целиком не
печатаются данным CLI. Сопоставление final markers с неизменным reviewed source
доказывает достижение whole-D/S-tree equality после owner destruction, C five
members invariance, fresh sealed generation+1/recoveryg1/AAC/privacy/times,
readonly hashes и final per-case idle/job4/pin32 assertions, не только успешный
recover(). Release assertions остаются активны через #undef NDEBUG.

Проверен только этот U six-cut physical process-crash срез на generated data.
U preflight negative/returned-fault/sticky after-birth coverage не принимается
по одной interruption матрице; полный T116/hardware/UI/install/release открыт.
AAC47/AAC56 unresolved RED сохраняются, причины этими PASS не установлены.
AAC66 live/stage/logs не читались и его regressions пока не квалифицированы.
Записан только own-report append; VM/tests/build/code/norm/tasks/checklists/
main-validation/Git/GitHub reviewer не трогал.

## AAC66 PASS / AAC67 Debug RED — saved qualification и узкий diagnostic proposal

2026-10-21. **AAC66 scoped runtime PASS3/3; AAC67 genuine Debug runtime RED1/1.**
Независимо прочитаны полностью receipt/JUnit/FULLactual и декодированные
UTF16LE build/test logs обеих завершённых стадий. Внешний BASE
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB`, стадии
`aac66-helper-regressions` и `aac67-terminal-sixcuts-debug`.

Оба source.sha256 и prior byte-identical frozen65:
`827b13cad75dba2469928d115cc51bcc06aecc7a7f367c0633337377d80942d9`.
Обе changed=[]/216inputs; independently current mismatch0. Оба saved harness
byte-identical65, SHA b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a.
Source/PE pre-post guards и owned checks сохранены; PE квалифицированы по
receipt/harness, не новым guest read/локальным PE hash. Две квитанции имеют
terminaltrue/build0/postflight216/owned0, device_audio_read/real_network/installed=false.

AAC66 Release: test_exit0/executed3/failure отсутствует, JUnit tests3/failures0/
disabled0/skipped0, все status=run; exact names/CLI, каждый полный log Test Passed:

| CTest | XML seconds | Доказанное FULLactual |
|---|---:|---|
| V5LocalRecordingWriterTests | 68.4093 | default без аргументов, playable3/refusals15/prefix checks, все24 cut по порядку включая U18, executed24/continued12/unused2/sealed1 и playback held_jobs0/2 |
| ProtectedRecoveryPlaybackRestart | 53.6347 | --cold-recovery-playback-restart, все19 cut включая U13; rebuild9/completed2/U1/refused6/sealed1, continued12 |
| ProtectedRecoveryTerminalUnused | 6.57687 | --cold-recovery-terminal-unused, shape13/child_exit88/waited1/continued1/four members IDs queue/cold AAC privacy |

Release PE совпадает65:
`de9d8b614111f534e13daa03b5e0c25f80e91e73aa57c3131cb4e918e4d27e91`,
1085952bytes. Full CTest total128.66s. XML system-out усечён1024bytes;
конечные markers сверены по полному actual, не по XML excerpt. Таким образом
эти три регрессии extracted helpers теперь проверены именно на final65 test
snapshot, а не перенесены со старого61–64 source.

AAC67 Debug: exact ProtectedRecoveryTerminalUnusedCrash и CLI
--cold-recovery-terminal-unused-crash. PE
`00b020c3b557b2bba3221e697d8f676eab38be8d2927c63cd1190539aa295ede`,
7078912bytes. Build0, test_exit8/executed1/failureTEST, JUnit tests1/failures1/
disabled0/skipped0, status=fail/time6.69085s. Полный actual содержит только один
shape18, затем exact assertion V5LocalRecordingWriterTests.cpp:918
`CustodyOwnedMemory::usedBytes()==idle`, Test Failed. CUT markers0/final U6
marker0. Отказ произошёл ПОСЛЕ обеих baseline scopes и ДО for six-cuts (:920),
не в одном из DDDCCS outcomes и не по child60/whole180 timeout. Предшествующие
baseline checks могли выполниться, но Debug U6 acceptance не получен.
PowerShell NativeCommandError в test.log — wrapper сообщения CTest; genuine
assert и test_exit8 подтверждены независимо actual/XML. Release65/66 PASS
не заменяет Debug67 RED. Размер остатка/утечка/cache/асинхронная причина по
этим artifacts НЕ определены; связь с AAC47/AAC56 не предполагается.

### Предложение двух scalar stamps — construction GO, не actual-diff GO

Узкий test-only proposal допустим / C0H0: один fprintf после уничтожения
normal baseline scope (:884, ДО prepareTerminal), второй после terminal
baseline scope (:917, ДО неизменного assert918), формат
`COLD_TERMINAL_MEMORY phase=normal_baseline|terminal_baseline idle=%zu actual=%zu`.
Передавать исходный idle и непосредственный CustodyOwnedMemory::usedBytes().
Memory.h:85–86 определяет usedBytes как noexcept relaxed atomic load,
только наблюдение, без reservation/reset/ожидания/получения нового proof.
Формат %zu соответствует size_t; только счётчики, без содержимого/путей/audio.
Нельзя переносить idle, scope или assert, сбрасывать counters/cache, вводить
warmup/retry/wait, менять guards/limits/control flow/production. Дополнительный
fprintf может влиять на timing, поэтому его цифры — диагностическое наблюдение,
не автоматическое доказательство причины. Точный two-line actual diff и hashes
требуют отдельного source gate ДО любого запуска. AAC67 сохраняется как RED;
новые строки не дают GREEN и не ослабляют equality. Нормативы повторно не
анализировались; это существующая T116 bounded диагностика без нового продукта.

Только own-report append; code/norm/tasks/checklists/main validation/VM/build/
tests/Git/GitHub reviewer не менял/не запускал. Full T116 и U negative/sticky
гейты остаются открыты; AAC47/AAC56 historical RED не отозваны.

## AAC68 — actual two-line diagnostic SOURCE GO

2026-10-21. **SOURCE GO / C0H0 только для Debug metadata diagnostic AAC68.**
Frozen `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/aac68-baseline-memory-diagnostic`:
manifest216 `a5634213fdf11a4a045f64282a51723e5556c1974666cd83cac8b4271d64424c`,
test `990fba71f7ec700ab8cbd0a2d867a71b9569d43f5e045238b73ed46d62da7dd5`.
Prior byte-identical67/827b13cad75dba2469928d115cc51bcc06aecc7a7f367c0633337377d80942d9;
ровно один changed test, остальные215 input hashes неизменны. Все216 current
и staged test независимо совпали. Before bytes взяты из65 frozen test, SHA
которого точно совпадает test entry67; полный diff ровно два добавленных fprintf.
Harness byte-identical67/b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a.

Первый stamp :885 расположен ПОСЛЕ destruction normal baseline root/owners;
второй :919 ПОСЛЕ terminal baseline destruction и ДО прежнего memory equality
assert (теперь :920). `%zu` соответствует обоим size_t значениям; исходный idle
не перенесён/не пересчитан, usedBytes — observation-only atomic load. Никаких
изменений lifetimes/assertions/guards/oracle/control flow/waits/timeouts/production,
содержимого/audio/путей в новых строках нет. Допустим exact диагностический
запуск после main serialization; reviewer ничего не запускал. Дополнительный
stderr/timing не исправление, expected RED не скрывается и не переименовывается.
ReadCache/static Debug proxy16 — пока только гипотеза, не установленная причина.
AAC66 PASS и AAC67 RED сохранены; runtime68 ещё не предъявлен/не квалифицирован.
Записан только этот own-report append, без source/norm/tasks/checklist/VM/Git действий.

## AAC68 saved RED / controlled reader-cache initialization construction gate

2026-10-21. **AAC68 genuine diagnostic RED квалифицирован. Construction GO /
C0H0 только усиленному test-only measurement proposal ниже; actual diff/runtime
ещё не предъявлены.** Не product patch, не разрешение игнорировать остаток.

Saved stage `aac68-baseline-memory-diagnostic` в прежнем external BASE:
полностью прочитаны receipt/XML/FULLactual и decoded UTF16LE build/test logs.
Независимый manifest216 hash
`a5634213fdf11a4a045f64282a51723e5556c1974666cd83cac8b4271d64424c`,
current216/staged test match; prior byte-identical67, changed только test
`990fba71f7ec700ab8cbd0a2d867a71b9569d43f5e045238b73ed46d62da7dd5`.
Harness unchanged67/b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a.
Receipt Debug/terminaltrue/build0/test8/executed1/post216/owned0/failureTEST.
Receipt-bound PE `00a6688704fcb5e786ecd7b3e7047da74a1c55b70f4952a0378d3637f573f6f7`,
7175168bytes, identity по сохранённым before-after guards, не новому guest read.
JUnit tests1/failures1/disabled0/skipped0, statusfail, **time8.19944s** (не
предварительное8.202). FULLactual: normal_baseline idle0/actual16, одна shape18,
terminal_baseline idle0/actual16, затем прежний equality assertion :920 и
Test Failed. Six-cut loop ещё не начат, нет CUT/final-U6 markers. Не timeout,
не compile failure; PowerShell wrapper не причина. Нет роста между этими
двумя наблюдениями, но они сами не устанавливают конкретного владельца16bytes
или отсутствие всех иных дефектов. AAC67/AAC68 RED сохраняются без перезаписи.

Узкая source feasibility: Codec.h:17–25 документирует и реализует пустой
CustodyVector через Base(count0), Debug iterator proxy остаётся charged.
Reader.cpp:18–31 имеет один lazy function-static ReadCache с CustodyBytes bytes;
:493–508 genuine packed-reader open вызывает cache() ДО создания ReaderState,
без stream Read; последующий checkRead остаётся обязательным. :67–70 освобождает
данные current reader, но не уничтожает function-static cache. Memory.h:85
usedBytes — noexcept atomic observation, deallocate освобождает charge. Поэтому
механизм постоянного пустого cache vector source-derived; совпадение именно
наблюдённого16bytes требует новой точной пробы, не выводится из комментария.

Допущена следующая усиленная конструкция в единственном generated U6 CLI,
ДО исходного idle/baselines, без production/public API/cache reset:

1. cold=used; локальный пустой CustodyBytes обязан иметь size0/capacity0.
   Измерить emptyProxy как точную добавку used (не hardcoded16; перед unsigned
   вычитанием подтвердить used>=cold). После уничтожения вектора used==cold.
2. fresh GeneratedRecordingRoot+coldCrashFixture; после возврата fixture helper
   used==cold. Создать canonical BOTH proof через existing coldPackedProof,
   cancellation; пока proof удерживается, взять beforeReader.
3. Во вложенном scope открыть existing packed reader без Read/Seek/Clone/MF,
   assert ok/verified/non-null stream. Полностью уничтожить result/CustodyReader,
   включая weak readerInstances/control block; никаких вынесенных копий.
   После этого while proof held used==beforeReader+emptyProxy.
4. Уничтожить ВСЕ fixture/proof/cancel/result scopes; used==cold+emptyProxy.
   Только тогда исходный idle=used; оба исходных baseline, их metadata stamps,
   exact memory equalities, DDDCCS, job/pin/hash/resource assertions без изменений.

Эти равенства не позволяют принять произвольный «прогрев» или отнять observed
baseline leak: измерена отдельная пустая allocation, helper должен вернуть
cold, после минимального reader-open допускается ровно эта allocation, а все
исходные baseline/U6 расходы по-прежнему обязаны полностью вернуться к idle.
Release может иметь emptyProxy0; Debug значение не фиксируется заранее.
Если cache уже initialized/иная остаточная allocation/утечка, строгая probe
должна отказать, не делать retry/wait/extra warmup. До следующего запуска нужен
отдельный actual-diff/hash SOURCE gate; construction GO не runtime/pass/commit
approval. Нормы не менялись; дополнительный product question не выявлен.

Только own report append; reviewer не менял source/tests/norm/tasks/checklists/
main validation/Git/GitHub, не запускал VM/build/tests. Full T116, U negative/
post-birth sticky и прежние AAC47/AAC56 остаются открытыми без общей cause claim.

## AAC69 — actual SOURCE gate controlled empty-cache measurement

2026-10-21. **SOURCE GO / C0H0 для exact AAC69 перед Debug запуском.**
code-reviewer: полный actual file diff against frozen68 прочитан, вызванные
existing packed-reader/allocator paths сверены; без нового norm/history gate.
Stage `aac69-controlled-cache-debug` в прежнем external BASE; manifest216
`ec0909c204e9897be58c63f1f9afdc995ec07f9f16878622a4f3f25b45a1381f`,
test `25cc3d9f44b7827caff8c066fed35c17cf87616254004e2c58e29a5add507c2a`.
Prior byte-identical68/a5634213fdf11a4a045f64282a51723e5556c1974666cd83cac8b4271d64424c;
changed/delta ровно test, все остальные215 inputs (production/CMake включительно)
неизменны. Все216 current и frozen changed copy match. Harness byte-identical68,
SHA b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a.

Diff только24 добавленных строки в начале coldTerminalUnusedCrashCuts, :857–882:
измеряется cold и пустой size0/capacity0 vector; >=cold ДО unsigned subtraction,
после deallocate exact cold. Generated fixture после helper тоже exact cold.
Canonical actual BOTH proof удерживается при beforeReader; внутренний scope
содержит ВСЮ CustodyFileResult<CustodyReader>, assert ok/verified/non-nullstream.
После уничтожения результата нет вынесенных stream/weakptr/state/proof copies;
used==beforeReader+emptyProxy. После outer fixture/proof/cancel destruction
used==cold+emptyProxy; только затем прежний idle=used и scalar print %zu.

Reader.cpp:493–508 действительно вызывает private static cache() внутри genuine
open до ReaderState allocation, сохраняет checkRead/cancel/pin predicates и
не выполняет IStream::Read. Marker reader_content_read0 означает отсутствие
stream Read именно в probe, не отсутствие native IO: fixture/proof открывают
и проверяют generated canonical. Размер proxy НЕ hardcoded; нет cache reset,
special allowance, warmup loop, retry, wait, публичного test hook или prod edit.
Ни один существующий assert/owner scope не удалён/перенесён относительно своих
baseline операций; оба scalar stamps и exact-memory assert (теперь :944),
per-cut exact-memory/job4/pin32, DDDCCS/child60/cleanup10/CTest180 неизменны.
Delta соответствует усиленной конструкции5144; compile/lifetime blocker по
исходникам не найден, но сборка не выполнялась.

Допущен exact AAC69 Debug для фактической проверки local-proxy/reader delta
и полного U6. Это ещё не подтверждение конкретных16bytes/исправления причины
или runtime GREEN; probe/guards обязаны реально пройти. AAC67/68 RED сохраняются,
AAC47/56 не связываются с этой гипотезой. Full T116/U negative/sticky и
installed/hardware/release открыты. Только own-report append, без VM/build/tests/
Git/GitHub/code/norm/tasks/checklists/main-validation действий reviewer.

## AAC69 — independent saved Debug runtime qualification controlled cache + U6

2026-10-21. **Scoped Debug runtime PASS1/1, XML34.3643s.** Полностью прочитаны
saved receipt/JUnit/FULLactual и decoded UTF16LE build/test logs стадии
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/aac69-controlled-cache-debug`.
code-reviewer применён в saved-evidence режиме, без новых запусков/Git/preflight.

Независимо пересчитан manifest216
`ec0909c204e9897be58c63f1f9afdc995ec07f9f16878622a4f3f25b45a1381f`;
все216 current и frozen changed copy совпали, prior byte-identical68. Единственный
changed test25cc3d9f44b7827caff8c066fed35c17cf87616254004e2c58e29a5add507c2a,
остальные215 неизменны. Harness byte-identical68,
b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a.
Receipt Debug/target V5LocalRecordingWriterTests/terminaltrue/build0/test0/
executed1/post216/owned0, failure отсутствует. PE по receipt/before-after guard
`fc28e883c249318abf37228856ead2d3dae7fe9e5bfca34ed646c401e8149cb0`,
7175168bytes; новый guest/PE read reviewer не выполнял.
Exact CTest ProtectedRecoveryTerminalUnusedCrash/CLI
--cold-recovery-terminal-unused-crash, JUnit statusrun/tests1/failures0/
disabled0/skipped0, failure/skip nodes0. Compile/link Debug успешны, полный
CTest total34.37s; XML excerpt обрезан1024bytes, финал проверен в FULLactual.

Фактические scalar observations: COLD_TERMINAL_CACHE cold0/empty_proxy16/
idle16/exact1/reader_content_read0; normal_baseline idle16/actual16 и
terminal_baseline idle16/actual16. Эти markers стоят после всех probe equalities
source69: local empty-vector full return, fixture return, reader/result release
delta exactly measuredProxy, outer release exactly cold+proxy. Значит в этом
Debug запуске стоимость постоянного пустого reader-cache действительно
совпала с отдельно измеренной charged empty-vector proxy16; baseline не получил
произвольный allowance. Это bounded объяснение нового baseline measurement RED,
а не product-memory fix, не доказательство происхождения всех allocations/утечек.
`reader_content_read0` относится к probe IStream, не отсутствию native proof IO.

Полный actual содержит семь shape18, все шесть ordinal1..6 с tuple/outcome
{4,2}D/{4,3}D/{4,2}D/{4,3}C/{5,2}C/{5,3}S и обязательными fixture/U child_exit88,
четыре members/IDs/queue unchanged. Финал cuts6/refused3/completed2/
sealed_readonly1/oracleDDDCCS/exact_memory1/process_crash1/power_loss0, Test Passed;
child-failed markers0. По точному source достигнуты также unchanged D/S tree
после owner destruction, C five members, fresh AAC/privacy/recoveryg1/sealed
readonly, per-case idle/job4/pin32 guards. Release результат сюда не подставлен.

AAC67/68 сохранены как genuine historical RED прежнего измерения. Их узкий
baseline факт объясняется согласованно source+controlled observations69;
AAC47 long timeout/AAC56 intermittent child timeout этим НЕ объяснены и не
отозваны. Full T116/U preflight negatives/post-birth returned/sticky и
installed/hardware/UI/release остаются открыты. Живой AAC70/stage/logs не
просматривались и не квалифицированы. Только own-report append; VM/build/tests/
code/norm/tasks/checklists/main-validation/Git/GitHub reviewer не затрагивал.

## AAC70 — independent saved final-source Release qualification 4/4

2026-10-21. **Scoped runtime PASS4/4**, не T116/full acceptance/commit approval.
Полностью прочитаны receipt/JUnit/FULLactual и decoded UTF16LE build/test logs
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/aac70-final-release`.
code-reviewer применён без Git/preflight/VM/build/test execution.
Независимый manifest216 SHA
`ec0909c204e9897be58c63f1f9afdc995ec07f9f16878622a4f3f25b45a1381f`;
source и prior byte-identical69, changed=[], все216 current match.
Harness byte-identical69, SHA
`b29873c2223561818a875b4bd79ec0059a2d90708ea1f784cf2102f5c0f86f4a`.
Receipt Release/target V5LocalRecordingWriterTests/terminaltrue/build0/test0/
executed4/post216/owned0, без failure. Receipt-bound PE
`a91e5600d9109c7213e716a088731ab1f7efe01f9dae484f5e3af9ebe32e3f79`,
1086976bytes; source/PE pre-post и owned guards сохранены в harness,
новых guest/PE checks reviewer не выполнял. Build log — successful Release
test compile/link; exact anchored filter выполняет именно четыре CTest.
JUnit tests4/failures0/disabled0/skipped0, все statusrun/failure-skip nodes0;
каждый FULLactual заканчивается Test Passed. XML excerpt truncated1024bytes
не использован вместо полных конечных markers.

| Test | XML seconds | Квалифицированное FULLactual |
|---|---:|---|
| V5LocalRecordingWriterTests | 75.572 | default CLI без args, playable3/refusals15/prefix checks, все24 child cut по порядку, U18, executed24/continued12/unused2/sealed1, playback held_jobs0/2 |
| ProtectedRecoveryPlaybackRestart | 64.084 | exact --cold-recovery-playback-restart; все19 child cut, U13, rebuild9/C2/U1/D6/S1, continued12/old extent unchanged |
| ProtectedRecoveryTerminalUnused | 7.21749 | exact --cold-recovery-terminal-unused; shape13/child88/continued1/four members IDs queue unchanged/cold AAC privacy |
| ProtectedRecoveryTerminalUnusedCrash | 19.5008 | exact --cold-recovery-terminal-unused-crash; seven shape18 и шесть real cuts DDDCCS, refused3/completed2/sealed-readonly1/exact memory |

U6 Release probe: cold0/empty_proxy0/idle0/exact1/reader_content_read0;
обе baseline idle0/actual0, затем все шесть assertions/исходов до final marker.
Это сохраняет Release zero-charge и не hardcode16 из Debug69. Final DDDCCS
и source guards требуют D/S whole-tree equality после owner destruction,
C five-members invariance, fresh sealed AAC/privacy/recoveryg1/readonly и
idle/job4/pin32 возврат. Physical process-crash1, power_loss0, generated data;
не real audio/network/install/latency/hardware acceptance. CTest total166.39s —
время четырёх последовательных tests, не изменение individual180s deadlines.

Debug69 и Release70 теперь подтверждают exact final69 measurement/U6 snapshot;
historical67/68 RED сохранены, не переименованы в PASS. AAC47/AAC56 причины
не установлены. U preflight negatives/post-birth returned/sticky ещё открыты,
как и полный T116/installed/UI/release. Никакие issue/task/checklist не закрыты,
commit/PR/merge/distribution не выполнялись. Только own-report append;
source/norm/tasks/checklists/main-validation/VM/tests/build/Git/GitHub не затронуты.

## После AAC70 — текущий requirements/analyze и construction gate U negatives

**GO для подготовки минимального test-only 10-case diff; scoped C0/H0.**
Это не SOURCE GO, разрешение запуска, новый runtime PASS, полный analyze всей
реализации или закрытие T116. Последнее уточнение предложения заменяет8 cases
на10. Старые source/runtime verdicts, AAC47/AAC56 и иные RED сохранены.
Новых продуктовых вопросов или изменений нормативов для этого среза не нужно.

Проверка выполнена в authoritative
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, active pointer
F200/`codex/200-windows-followup`, source_sha `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Это чтение pointer, не новый Git HEAD receipt. Использованы локальные
speckit-checklist/speckit-analyze; анализ оставался read-only, это разрешённая
отдельная запись reviewer результата. Before/after checklist/analyze hooks
прочитаны и YAML разобран: все четыре relevant hooks disabled. Обычный
prerequisites script не запускался: он сохраняет feature.json, а --require-spec
не поддерживается. Required spec/plan/tasks и указатель проверены чтением;
запись feature.json, Git/VM/build/tests не выполнялись.

### Чеклисты, применимость и трассировка

Независимый текущий inventory: **198 файлов, 477 checked, 0 unchecked**;
31 файл содержит checkbox, остальные167 — отчёты/сопутствующее evidence.
Перечитаны тексты всех477 отмеченных пунктов, включая12 тематических checklist
(211 критериев) и266 исторических source/runtime/evidence отметок. Эти266
не превращены в новые requirements approvals или повторную runtime приёмку.
Исторические предварительные формулировки читаются с последующими addenda,
не вместо текущего contract. Markers не менялись, новые checklist не создавались.
Cold-prefix: **47/0**, CHK042–047 supported6/6; остальные41 сохраняют область
своих этапов. Guard/reader/writer/resize/rewrite/tail/package критерии остаются
ограничениями reuse. Security/privacy/start-owner применимы напрямую;
calendar/bridge/UI/audio/hardware gates не затронуты test-only предложением
и не принимаются заново. Это не общий PASS Windows.

Детерминированный SHA256 набора198 файлов (sorted relative paths,
`SHA256  path\n`, затем SHA256 соединённых строк):
`0ff59d9f2f9b55a38ff814a62343ba9666d194a17fc3b9e7bf06a30b7d82916f`.
Cold-prefix file SHA256:
`b7c4113ea7cb0236ae125599b2dbdd4a6d5bcc7946b33a9fffabd462f1bfeb7d`.

Текущие неизменные normative SHA256 лично сверены:

| Артефакт | SHA256 |
|---|---|
| spec.md | `0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| plan.md | `39d3f3bf9344e1c04c1acefda6fa9f5ec2870f0de8556dec507cf71545925a45` |
| research.md | `da53a2492e7cc0f1b058ab3d179718fab95aac8bf9957f33b8ff5f3a610bfe9d` |
| data-model.md | `d61235b9454564897fdacfdecd127fc0a9676b48a2b2011b1b1df692fcf7db9b` |
| quickstart.md | `6c4eb56f763f07dbbe83cdd59393437653d95b1c49c62666abe6d58e618ae564` |
| windows-protected-packed-custody.md | `e6af6d4d402c19fa47b8a71931f7573eb0c4673d3f19365926f78f140c65fc56` |
| feature.json | `d4be889d623986959cc6b11beeb6227a4a33d0a1d9b2052e782db105439ba882` |

Scoped analyze:22 FR/10 SC/120 tasks (93 checked/27 open). Для затронутых
FR012/013/014/022, SC005/006 есть явное покрытие T115/T116/T117/T118 в
tasks:541–548;6/6 affected requirements mapped, новых unmapped tasks0,
блокирующих ambiguity/constitution/coverage conflicts0. Open T116 не является
новым uncovered requirement: это существующая работа, не завершённая приёмка.
T120, T119 и их native/privacy/calendar gates не подменяются этими fixtures;
T093/T027 не изменяются. Scoped threshold C0/H0, не повторная сертификация
всех32 требований по каждому production caller.

Read-only GitHub connector подтвердил #7444 OPEN, canonical title T116 и
feature:200/priority:P0/area:storage/gate:pr-blocker/type:hardening. Tasks:551–554
содержат mapping T115–118→7443–7446; старый issue-map.md доT113 не является
единственным текущим mapping. #7443/#7445/#7446 также OPEN с canonical labels.
Никакого issue sync write/ensure/close не выполнялось. Различие T115 [X]
(design accepted) и OPEN #7443 с отдельными PR/closeout условиями отмечено:
это не утверждение полной tracker reconciliation; перед closeout потребуется
отдельная сверка. Для продолжения существующей T116 test-only scope владелец
есть, повторного создания issue не требуется.

### Construction: разрешённый точный срез

Reuse `coldTerminalUnusedCrashCuts(bool refusalsOnly=false)` допустим.
Default warmup/normal24 baseline/positive U/шесть DDDCCS не ослабляются;
новый отдельный CLI/serial CTest180 после прежнего positive baseline выбирает
только10 fresh refusal fixtures. Child60/cleanup10/resources прежние.
`prepareTerminal`/`coldTerminalUnusedShape` сохраняют real cut18, valid BOTH
packed и exact unused recovery/bound metadata до каждой mutation.

1. Cases0–2 — genuine writer/checkpoint mutations: finite float .5 по byte0
canonical, NaN по byte67200 внутри complete100 frames, int16 zero по byte44
media. IDs/length не меняются. После writer/proof release fresh shape повторно
подтверждает structural BOTH/metadata, чтобы это были semantic invalidContent,
а не broken encryption/header/lease fixtures. Byte67200 находится за первой
65536-byte finite scan порцией (`LocalRecordingPackage.cpp:489–536`).
Cases0/2 доходят до existing canonical→WAV comparison
(`V5LocalRecordingWriter.cpp:201–215,390+`), а не ciphertext corruption.
2. Cases3–6 — unknown media EOF tail, reachable AAC DATA corruption, canonical
DATA corruption, extra recovery child. Для DATA offset должен быть фактически
достижимым record выбранной fixture; неверный HEAD/неиспользуемый orphan не
доказывает задуманный случай. Actual diff gate проверит это адресование.
3. Case7 — fresh U recovery child cut2 именно{4,3} с fixed6-event oracle и
exit88: singleton после первого index rename, не подстановка файлов.
Case8 — cancellation после успешного StoreOwner open, exact
ERROR_OPERATION_ABORTED. Ни один тест не должен проходить из-за open failure.
4. Case9 — genuine standalone manifest commit g+1 с context текущего bound
package, старые package refs неизменны; полный committed/readback результат и
все leases освобождаются до recover. `coldManifest` — корректное normal
значение, но здесь проверяется **newer-unbound binding**, не semantic
privacy/session. Нельзя объявлять semantic покрытие по более раннему binding
refusal (`prepareRecovery:165+`, `completeUnfinished:675+`).

Before snapshot берётся ПОСЛЕ намеренной mutation и release setup owners;
armRecoveryTrace очищает fixture/child events. Каждый recover обязан nonok,
cases0–2 exact invalidContent, остальные non-none, case8 exact native abort.
Whole-tree equality проверяется внутри отказавшего scope и ПОСЛЕ фактического
destruction всех owners/results/proofs; queue/IDs, exact idle,4 jobs/32 pins
проверяются на каждом случае. Никакого retry/cache reset/allowance/cleanup
вместо этих assertions.

`events.empty()` означает отсутствие наблюдаемых wrapper publication events,
не отсутствие native reads/всего IO: observer фильтрует metadata rename и
packed audio write/flush (`V5tests:82–108`). Вместе с whole-tree equality это
достаточный ограниченный oracle отказа без изменения дерева, но не forensic
proof «ни один байт никогда не переписывался». Не расширять wording acceptance.

Все указанные обязательства проверяются по actual diff ДО build/runtime;
GO сейчас только на конструкцию. Полный negative matrix history/privacy/
session/optional times/peer refs и отдельные U post-birth returned native/
short/crypto/quota/readback/cancel + sticky/no same-owner retry остаются открыты.
Нынешние10 pre-effect cases и прежние49 fault cases их не закрывают. AAC70
повторно не квалифицировался; T116/Windows/installed/hardware/release не приняты.
Записано только это дополнение own-report; checklist markers и все остальные
файлы/VM/Git/GitHub state не изменялись.

## AAC71b — окончательный scoped SOURCE gate terminal-unused refusals

**SOURCE GO; C0/H0.** Проверен именно frozen
`aac71b-terminal-refusals-release`, не superseded/unrun AAC71. Это допуск
исходников test-only среза к build/runtime, не результат выполнения и не
закрытие T116. Requirements/checklist/analyze предыдущего раздела не повторялись.

Точные SHA-256:

```text
source.sha256  cbb394d615a0cb6c90179f0834ee78cb6830cc1214e38e4172612b2bb5f1e740
prior.sha256   ec0909c204e9897be58c63f1f9afdc995ec07f9f16878622a4f3f25b45a1381f
V5tests        d5b05895501fc473fab94248e5c2eb64dd5cdf34cee29ba25f178f648e8c1b19
CMake          303e7489324a75e263680a52815a825ee9debd5413d5c5099e7573d0991e366a
```

Manifest содержит216 входов; текущий authoritative worktree совпал216/216.
От prior70 изменились ровно test/CMake, остальные214 входов неизменны.
Замороженные копии этих двух файлов совпали с manifest. Stage хранит changed
copies, а не утверждённые216 физических копий. Actual diff прочитан против
AAC69 test и AAC65 CMake. Production не менялся.

- `V5LocalRecordingWriterTests.cpp:346–376`: optional firstData применяется
  только двум новым tamper fixtures. Genuine Owner+Tree::verify сначала
  устанавливают BOTH closures; далее selected root L2→L1→L0/slot0/base0
  проходит retained owner readCiphertext и authenticated openReferenced.
  Codec задаёт NODE body4096 и проверяет envelope SHA/context/address до
  decodeChild. Format проверяет kind/payload/version и дочерний extent до
  parent; финальный DATA ограничен committedExtent, arithmetic overflow
  отвергается validShape. Plain body очищается после получения child; все
  промежуточные bytes/pins/owners освобождаются до tamper. Не используется
  предполагаемый appendOffset/orphan как адрес DATA, нет нового API/authority.
- `V5tests:961–1063`: десять fresh fixtures идут после прежнего controlled
  cache warmup, normal24 и successful U baseline. Cases0–2 используют genuine
  writer/checkpoint без изменения длины и повторный fresh shape: finite PCM,
  NaN за первой64KiB порцией и WAV PCM требуют именно invalidContent.
  Cases4/5 портят достижимый DATA выбранного playback/canonical дерева, а не
  HEAD или неподключённый record. Setup proof/lease прекращён до изменения.
- Case3 закрывает tail stream и доказывает actual file_size+1. Case6 создаёт
  extra recovery child. Case7 требует physical child cut2{4,3}/exit88,
  index.0 exists/index.1 absent и неизменный package-state. Это настоящий
  singleton, а не отказ из-за непопадания в cut.
- Case8 отменяет уже после successful StoreOwner open и требует exact
  ioFailed/ERROR_OPERATION_ABORTED. Case9 читает actual selected terminal
  manifest bytes/context/generation, завершает scope всех readers/pair/store,
  затем standalone commit требует committed/g+1 и неизменный package-state.
  Такой fixture проверяет newer-unbound binding, не privacy/session semantics.
- Before snapshot берётся после закрытия mutation streams/owners. На каждом
  recover обязательны nonok/no value/non-none error, empty publication trace,
  whole-tree equality внутри и после destruction owner/results, queue equality,
  exact idle и доступность4 jobs/32 pins. Watched root обязан быть пуст до
  setup. Default шесть DDDCCS, старые guards/assertions и lifetime boundaries
  не ослаблены; новый CLI лишь выбирает отдельную ветку и return до old loop.
- CMake добавляет только ProtectedRecoveryTerminalUnusedRefusals с точным
  `--cold-recovery-terminal-unused-refusals`, RUN_SERIAL и TIMEOUT180.
  Assert-enabled Release (`#undef NDEBUG`) и child60/cleanup10 сохранены.
  Связанные public Codec/Format/Owner/Writer declarations и callers проверены;
  подтверждённых compile/source blockers в этом diff не найдено.

`publication_events=0` не означает отсутствие всех native reads/IO; oracle
ограничен existing observer плюс whole-tree equality. Runtime duration всех
10 fixtures пока неизвестна; SOURCE GO не разрешает увеличить180/60 или
ослабить full proof при неуспехе. Runtime/полная negative matrix/U post-birth
faults/sticky/полная Windows приёмка остаются отдельными gates; AAC47/56
не разрешены этим review. Никаких VM/build/tests не запускалось. Изменён
только этот собственный отчёт; source/norm/tasks/checklists/Git/GitHub не менялись.

## AAC71b BUILD FAIL и AAC73 typed-byte — узкая квалификация и SOURCE gate

**AAC71b: подтверждён terminal BUILD FAIL, не runtime RED.** Прочитаны
сохранённый result.json и полный UTF16LE build.log. Receipt: terminal=true,
configuration=Release, manifest=cbb394d615a0cb6c90179f0834ee78cb6830cc1214e38e4172612b2bb5f1e740,
build=1, failure=BUILD, owned_processes=0. Сохранённых test.log/actual-test.log/
JUnit в этом stage нет; никакого результата выполнения тестов не принимаю.
В build.log MSVC14.44.35207 показывает C2220 и C4244 в xutility5310/5264;
template context прямо указывает V5tests367, std::fill<iterator<uint8_t>,int>.
Это установленная причина отказа данной сборки: literal0 выводит int и
вызывает narrowing warning при присваивании unsigned char под /WX.
Предыдущий SOURCE review этого предупреждения не выявил; его фраза об
отсутствии подтверждённых compile blockers была недостаточной. Сохранённый
BUILD FAIL остаётся evidence; прежний SOURCE GO не является build PASS.

**AAC73: однострочный SOURCE GO, C0/H0.** Проверен frozen
`aac73-typed-byte-release` относительно actual prior AAC71b. SHA-256:

```text
source.sha256  13303a40e3ee24ba47e0fdb7e15860185260888461635b2868a22af8f4abecda
prior.sha256   cbb394d615a0cb6c90179f0834ee78cb6830cc1214e38e4172612b2bb5f1e740
V5tests        090f3f2076371e72a7021e765fcd742aa38c3d9d685ac7bce748062d17cec6a1
```

Manifest216/current host216 совпадают; changed.json и сравнение manifest
показывают только V5tests, остальные215 входов неизменны. Frozen test copy
имеет указанный hash. Actual diff содержит ровно одну замену на строке367:

```cpp
std::fill(decoded.value->body.begin(),decoded.value->body.end(),std::uint8_t{0});
```

Тип fill value теперь совпадает с uint8_t элементом CustodyBytes; int→byte
template conversion устранена без casts warning suppression или изменения
compiler flags. Диапазон очистки, значение нуля, место wipe после decodeChild,
lifetimes, assertions, все10 случаев, CMake и deadlines не изменены. Требования/
construction повторно не анализировались; superseded unrun AAC72 не принят.
Это допуск exact AAC73 к сборке/выполнению, не подтверждение успешной компиляции
или runtime. Исправление не закрывает T116/остальные gates. Выполнялись только
локальные чтения/diff/hash checks и append этого отчёта; VM/build/tests,
source/norm/tasks/checklists/Git/GitHub не затрагивались.

## AAC73 Release — независимая квалификация сохранённого runtime

**Scoped runtime PASS/GO:3/3; несоответствий в предъявленных evidence не найдено.**
Прочитаны полный result.json, JUnit, весь actual-test.log(9551bytes), полностью
декодированные UTF16LE build.log/test.log и сохранённый validate-input.ps1.
AAC74/live VM не читались; прежние requirements/source construction не повторялись.

Manifest216 SHA13303a40e3ee24ba47e0fdb7e15860185260888461635b2868a22af8f4abecda,
prior=cbb394d615a0cb6c90179f0834ee78cb6830cc1214e38e4172612b2bb5f1e740;
единственный changed test имеет frozen SHA
090f3f2076371e72a7021e765fcd742aa38c3d9d685ac7bce748062d17cec6a1,
совпадающий с предыдущим exact SOURCE gate. Другие215 manifest entries прежние.
Receipt: terminal=true, configuration=Release, build=0, test_exit=0,
executed_tests=3, postflight=216, owned_processes=0, failure отсутствует.
PE SHA24c3b59e96eefbdfe7e361ec318c390fd361799bcc4e66bdc3af5e58d90b1ab2,
1101824bytes зафиксирован receipt. Saved harness выполняет pre/post216 и
сравнивает PE hash до/после CTest; failure/PE_CHANGED отсутствует. Это
квалификация сохранённого guard/receipt, не новое чтение guest executable.
Build log подтверждает успешный Release target link; C4244/C2220 в AAC73 нет.

JUnit: tests3/failures0/disabled0/skipped0, все status=run. Exact names/CLI/time:

| CTest | CLI | JUnit seconds |
|---|---|---:|
| ProtectedRecoveryTerminalUnused | --cold-recovery-terminal-unused | 6.6651 |
| ProtectedRecoveryTerminalUnusedCrash | --cold-recovery-terminal-unused-crash | 17.2783 |
| ProtectedRecoveryTerminalUnusedRefusals | --cold-recovery-terminal-unused-refusals | 17.5811 |

Все три actual commands указывают build/Release/V5LocalRecordingWriterTests.exe.
Полный test.log подтверждает3/3,100% и total41.54s; XML system-out усечён1024,
поэтому final markers проверены по FULLactual, а не по XML excerpt:

- Upositive:19 trace events, real cut13{5,3}/child_exit88, continued1,
  four_members_ids_queue_unchanged1/cold_aac_privacy1, final CUTS marker PASS.
- U6: все ordinals1..6 с обоими child_exit88, outcomes DDDCCS, итог refused3/
  completed2/sealed_readonly1/exact_memory1; controlled Release cache cold0/
  empty_proxy0/idle0 и обе baseline actual0. Нет пропущенного cut.
- Refusals: cases0..9 ровно по одному; ошибки7,7,7,13,7,7,13,13,6,7.
  Cases0–2 semantic invalidContent; cases4/5 actual reachable DATA fixtures;
  case8 native000003e3(ERROR_OPERATION_ABORTED). Каждый publication_events0;
  итог cases10/semantic3/unchanged_disk1/exact_memory1/jobs_pins_returned1.
  Каждая секция дошла до end output и Test Passed, не early/skip PASS.

Предел принятия: только эти3 Release tests на exact AAC73, generated data,
без device audio/network/install. Empty publication trace имеет прежний
ограниченный смысл; это не всеобщий no-IO proof. U post-birth/sticky и полная
negative matrix/T116/Windows/hardware/release не закрыты. AAC71b BUILD FAIL
сохранён отдельно, не переименован в runtime RED и не стёрт. AAC47/56 также
не объясняются этим PASS. Добавлен только этот own-report; VM/build/tests,
исходники/norm/tasks/checklists/Git/GitHub не затрагивались.

## AAC74 Debug — продолжение сохранённой квалификации AAC73

**Scoped runtime PASS/GO:2/2, несоответствий не найдено.** Независимо прочитаны
сохранённые receipt/JUnit, FULLactual-test.log и полностью декодированные
UTF16LE build.log/test.log. Live AAC75 не читался. Source/prior побайтно
совпадают друг с другом и с AAC73 manifest216, SHA
13303a40e3ee24ba47e0fdb7e15860185260888461635b2868a22af8f4abecda;
changed.json=[]; validate-input.ps1 побайтно прежний AAC73. Новой source
модификации или нового requirements/construction review нет.

Receipt terminal=true/configuration=Debug/build0/test_exit0/executed2/
postflight216/owned0, failure отсутствует. PE в receipt:
2ba1e6de040fc7d1ee6bc09a1a80979c5032bea780761e460f9bd8225786fcbe,
7221248bytes. Сохранённый harness сохраняет pre/post source216 и PE before/
after guard; квалифицирован именно этот receipt, не свежий guest-file read.
Build log подтверждает Debug compile/link target; ошибок/предупреждений нет.

JUnit tests2/failures0/disabled0/skipped0, оба status=run:

| CTest | Actual CLI | JUnit seconds |
|---|---|---:|
| ProtectedRecoveryTerminalUnusedCrash | --cold-recovery-terminal-unused-crash | 29.5308 |
| ProtectedRecoveryTerminalUnusedRefusals | --cold-recovery-terminal-unused-refusals | 30.4142 |

Оба actual commands — build/Debug/V5LocalRecordingWriterTests.exe.
Полный test.log:2/2,100%,total59.95s. XML system-out усечён1024bytes;
итоговые assertions/markers проверены по всему actual-test.log:

- Каждый CLI: cold0/empty_proxy16/idle16/exact1/reader_content_read0,
  normal и terminal baseline actual16==idle16. Нет допуска16 поверх baseline.
- U6: ordinals1..6 без пропусков, fixture/U child_exit88 каждый, DDDCCS,
  four_members_ids_queue_unchanged1; final cuts6/refused3/completed2/
  sealed_readonly1/exact_memory1/process_crash1/power_loss0, затем Test Passed.
- Refusals: cases0..9 ровно по одному и те же error vector7,7,7,13,7,7,13,13,6,7
  как AAC73. Cases0–2 semantic invalidContent; cancellation native000003e3;
  все publication_events0. Final cases10/semantic3/unchanged_disk1/
  exact_memory1/jobs_pins_returned1, затем Test Passed.

Совместно AAC73/74 подтверждают перечисленные Release/Debug срезы на одном
source, не дополнительный Debug Upositive standalone и не полную suite.
U post-birth/sticky/полная negative matrix/T116/hardware/installed/release
остаются открыты. AAC71b BUILD FAIL и прежние AAC47/56 не стёрты и не объяснены
этим PASS. Прочитаны только завершённые74 artifacts; VM/build/tests/AAC75,
исходники/norm/tasks/checklists/Git/GitHub не затрагивались. Append own-report only.

## AAC75 Release — сохранённые legacy regressions на финальном source

**Scoped runtime PASS/GO:2/2; несоответствий не найдено.** Прочитаны весь
actual-test.log15033bytes, полный JUnit/receipt, декодированные UTF16LE
build.log/test.log. Source/prior manifest побайтно равны AAC73 source216,
SHA13303a40e3ee24ba47e0fdb7e15860185260888461635b2868a22af8f4abecda;
changed=[]; сохранённый harness побайтно тот же AAC73. Никакого нового source
или requirements gate не выполнялось.

Receipt terminal=true/Release/build0/test_exit0/executed2/postflight216/owned0,
failure отсутствует. PE SHA24c3b59e96eefbdfe7e361ec318c390fd361799bcc4e66bdc3af5e58d90b1ab2,
1101824bytes — exact AAC73 Release PE в receipt с прежними pre/post216 и
PE before/after guards. Это проверка сохранённых данных, не новый guest hash.
Build log подтверждает успешный Release target, test.log2/2/100%,total113.03s.
JUnit tests2/failures0/disabled0/skipped0, status=run в обеих строках:

| CTest | Actual invocation | JUnit seconds |
|---|---|---:|
| V5LocalRecordingWriterTests | Release/V5LocalRecordingWriterTests.exe без аргумента | 63.5877 |
| ProtectedRecoveryPlaybackRestart | тот же exe --cold-recovery-playback-restart | 49.426 |

Поскольку XML system-out усечён1024bytes, all final markers сверены с FULLactual:

- Default: cold playable3/3, все15 refusal cases0..14 и final unchanged disk/
  exact memory/all jobs pins returned; capturing/finalizing prefix3frames,
  prefix refusals9/sealed phases3 с resource guards. Trace24 и cuts1..24
  полные, каждый child_exit88/waited1/canonical_queue_unchanged1. WAV6/7,
  playback8..14, terminal-unused shape18, completed22/23 и sealed24 дошли
  до итогового trace_events24/executed24/sealed_cold_decode1/continued12/
  recovered_unused2. Protected playback held_jobs0 и2 оба ok1,48128frames.
- Repeated: trace19 и cuts1..19 полные, каждый child_exit88/waited1/
  canonical_queue_unchanged1. Playback R1..9, D10..12/14..16, U13,
  C17/18, S19; final rebuild9/completed2/terminal_unused1/refused6/
  sealed_readonly1/first_child_exit88/second_child_exit88/old_extent_unchanged1.
  CUTS summary executed19/continued12/sealed_cold_decode1. Обе секции
  завершились Test Passed. Механически проверены43 cut markers и обе
  последовательности ordinals без пропусков/дубликатов.

Квалифицированы только эти две Release регрессии на unchanged final source.
Это не performance/power-loss/continuity/hardware/installed/full Windows или
T116 acceptance; U post-birth/sticky и остальная negative matrix открыты.
AAC71b BUILD FAIL и прежние AAC47/56 сохранены, этим PASS не объяснены.
Добавлен только собственный отчёт. VM/build/tests/другие live stages,
исходники/norm/tasks/checklists/Git/GitHub не затрагивались.

## После AAC75 — обновление gate для same-package U post-birth sticky test

**Scoped requirements/checklist/analyze/issue GO, C0/H0: можно готовить следующий
минимальный test-only срез внутри T116.** Это не actual construction/source GO
ещё не предъявленного diff, не разрешение production patch/запуска и не общая
приёмка. Новый продуктовый ответ/задача/checklist не требуются в данной области.

Контекст лично сверён read-only: authoritative worktree, HEAD
b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1, actual branch codex/200-windows-followup,
feature.json F200/high-risk-product/source_sha тот же. Safe prerequisite
`--json --paths-only` вернул тот же feature/spec/plan/tasks; его BRANCH
200-windows-desktop-app — resolved feature identifier, не замена actual git branch.
Обычный prerequisite command не выполнялся из-за persist feature.json; опция
--require-spec в installed script отсутствует, наличие required artifacts
проверено чтением. Hooks before/after analyze/checklist разобраны YAML: все4
disabled. Использованы speckit-analyze и ownership/requirements-quality правила
speckit-checklist; анализ сам по себе read-only, эта запись — отдельный reviewer append.

Свежий inventory checklist: **198files/477checked/0unchecked**,31 с checkbox,
167 без checkbox. Набор198 побайтно тот же по digest
0ff59d9f2f9b55a38ff814a62343ba9666d194a17fc3b9e7bf06a30b7d82916f
(sorted repository-relative `SHA256  specs/.../checklists/path\n`, затем SHA256).
Это уточняет способ воспроизведения прежнего digest: пути относительно repo,
не относительно самой папки checklists. Cold-prefix47/0, SHA
b7c4113ea7cb0236ae125599b2dbdd4a6d5bcc7946b33a9fffabd462f1bfeb7d.
Прежняя оценка всех477 пунктов сохраняет силу по неизменным inputs; полного
повторного обхода исторических198 отчётов не делалось. Перечитаны affected
cold-prefix CHK009/010/039/042–047, packed-writer12 и start-owner10; security27,
остальные thematic UI/audio/calendar/privacy gates остаются в своих областях,
без нового runtime смысла. Изменений markers/notes нет, оснований снимать
requirements-quality approval не обнаружено.

Normative SHA лично повторно сверены с таблицей после AAC70: все8 + feature
pointer неизменны. Основные exact identities:

```text
spec          0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11
tasks         80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f
constitution  d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859
plan          39d3f3bf9344e1c04c1acefda6fa9f5ec2870f0de8556dec507cf71545925a45
packed        e6af6d4d402c19fa47b8a71931f7573eb0c4673d3f19365926f78f140c65fc56
```

Scoped analyze: affected FR012/013/014/022/SC005/006 mapped6/6 на прежние
T115–118 (tasks541–548),120tasks/93checked/27open; T116 unchecked.
Новых ambiguity/coverage/constitution conflicts C/H нет. Plan468-U2 п.5
(2907–2917) и CHK046 прямо задают sticky boundary ДО commitMetadata, включая
return/exception ПОСЛЕ успешного recovery commit, без same-owner retry/cleanup;
recoveryPending=false не отменяет failed package. Packed contract407–414 и
quickstart1230+ согласованы. Full BOTH/readback ACK нельзя обрывать ради fault.
Существующая задача требует именно эти failure fences; её незавершённость не
является отсутствием владельца или требованием новой policy/схемы.

Read-only GitHub connector заново подтвердил #7444 OPEN, title
`[200][P0][storage] T116: Защитить всю локальную цепочку записи без открытых временных копий`,
body Spec tasks:T116, current local mapping tasks552 и labels feature:200 /
priority:P0 / area:storage / gate:pr-blocker / type:hardening. Assignees=null:
подтверждён canonical task/issue owner, не назначенный человек. Remote origin
yshishenya/graf совпадает. Sync write/ensure/comment/close не выполнялись;
это узкая актуальность существующей T116 связи, не полный tracker closeout.

Следующий test должен доказывать настоящий post-birth failure и последующий
отказ НА ТОМ ЖЕ удерживаемом package, не подменять его fresh factory/reopen,
снятием cancel или исчезновением последней ссылки. Сохраняются immutable four
members/IDs/queue, actual retirement, точные budgets/deadlines и absence normal/
upload/claim. Конкретные native fault points/ожидания/способ public/private reuse
main ещё уточняет; их construction и actual diff потребуют отдельного review
ДО build/runtime. Этот gate не обещает полноты будущего теста заранее.

AAC73–75 повторно не квалифицировались; AAC71b BUILD FAIL и AAC47/56 сохранены.
T117/118/119/120, U negative remainder/full native/installed/hardware/release
остаются самостоятельными gates. Записан только own-report; source/norm/tasks/
checklists/VM/build/tests/Git/GitHub mutation не выполнялись.

## AAC77 — construction и actual SOURCE gate same-package sticky13

**CONSTRUCTION + SOURCE GO, scoped C0/H0.** Verdict только для frozen
`aac77-terminal-sticky-release`; AAC76 superseded/unrun, по нему GO не выдан.
Прежний requirements gate после AAC75 сохраняется, новый normative audit не
выполнялся. Scope: test-only coverage через thin private delegates плюс одна
friend declaration, не изменение production исполнения или полный T116.

Exact SHA-256:

```text
source216  a555f9c284c67ada0a4223ecd25310cbe0578c994f139d3344cc4887f81cfe60
prior75    13303a40e3ee24ba47e0fdb7e15860185260888461635b2868a22af8f4abecda
V5tests    87b56e2150e550edd7f027bf8f3d8eec219a19458abf6e0d8472398f89521907
V5.h       df20d271fe2481c7fbbcb38913924268693b112670d37431d1e9aff9ee9c3a35
CMake      7ea3f943055cb0eb98a7d29cff54a45de9c3334075731c6ae1b09eaf2bb35986
```

Current authoritative host216/216 совпал с frozen manifest; staged3 copies
сверены с их manifest entries. Delta ровно эти3, остальные213 inputs прежние.
Actual diff сравнен с prior test AAC73, CMake AAC71b (те же prior75 entries),
header AAC61 SHA2893ddf0473599fc22eea48ea8b52e4f8b950b12d8680594661b088bd3e87ebd,
равным header entry prior75. Sparse stage не трактовался как216 физических копий.

### Конструкция и точки отказа

V5.h109 добавляет только friend struct; единственное определение peer находится
в Windows test TU: V5tests32–44, два delegate вызывают реальные private
prepareRecovery/finishRecovery. Нет fabricated package/proof, bypass admission,
нового public effect API или runtime fault knob в shipping implementation.
Existing Files.cpp wrappers остаются только test TU. Default normal24/Upositive
baselines, controlled cache, десять refusals и шесть crash cuts не ослаблены;
второй bool выбирается лишь новым CLI. CMake добавляет только
ProtectedRecoveryTerminalUnusedSticky/--cold-recovery-terminal-unused-sticky,
RUN_SERIAL/TIMEOUT180; assert-enabled Release, child60/cleanup10 и /W4 /WX прежние.

Fixed13 в V5tests974–975:

- Cases0–5: recovery role4 write/flush, index0 before/after rename, index1
  before/after rename. afterEvent2 для второго before-rename учитывает, что
  observer добавляет before event ДО recoveryFail; afterEvent4 выбирает второй
  successful rename с ambiguous returned ACK. Native status0xc000007f не
  выдаётся за Win32 disk-full, raw/HRESULT representation проверяется явно.
- Cases6–9: package-state role5 write/flush/before rename после recovery events4,
  after rename после event6. Required first4 sequence/index.0/index.1 existence
  проверяются. Write/flush ожидают ERROR_DISK_FULL/ERROR_WRITE_FAULT, rename —
  настоящий returned STATUS_DISK_FULL, не child crash simulation.
- Cases10–12: canonical role0 read-fault after4, read-fault after6, cancel at
  actual canonical read after6. Read arming зависит от observed sequence,
  matched native role и one-hit counter, а не одного номера попытки. Case12
  возвращает обычный ReadFile result при выставленном cancellation, дальнейшая
  проверка должна дать ERROR_OPERATION_ABORTED; остальные не меняют cancel.

Особо проверена замена AAC76 role4/read7/after4 на **role0/read7/after4**.
После четвёртого recovery rename metadata commit ещё выполняет внутренний
readValidatedSnapshot (Metadata2470+) и completeUnfinished — actual recovery
completedMetadata/readback (LocalPackage738–745). Они читают role4, не role0.
Только затем package commitImpl(candidate,true) делает validateRefs canonical
(Metadata2011+,2086–2087). При этом native read failure validateRefs возвращает
ошибку ДО attempted publication и БЕЗ установки package.failed_. Следовательно,
последующий reference/readPair recoveryRequired действительно зависит от
внешнего FailAfterBirth (LocalPackage654–658,737): без него recoveryPending=false
объяснил бы только retry finish invalidInput, но не блокировку package API.
After6 canonical faults аналогично проверяют failed owner после final publication
на пути fresh inspection. Полный actual ACK нельзя обрывать из-за cancel;
новый canonical injector не вмешивается во внутренний recovery role readback.

### Same-object, эффекты и освобождение

V5tests982–987 сохраняет genuine prepared writer и его package, удаляет только
лишнюю optional shared_ptr copy; до failure reference должен быть успешным.
finish получает копию того же writer. После exact one-hit/error/native checks
injector выключается, token сбрасывается: это устранение активной причины для
проверки sticky, не разрешение продолжения работы. Тот же writer finish обязан
invalidInput. Тот же package: reference/readPair/createWriter/commitMetadata/
commit — пять exact recoveryRequired, no value/no snapshot/notCommitted.
Никакого fresh factory/reopen вместо этих probes нет.

После КАЖДОГО probe unchanged lambda (1011–1025) проверяет trace size и whole
tree hash, затем четырёх original members/IDs/queue. После уничтожения всех
writer/package/store/results вновь проверяются hashes (1032–1033), после всего
fixture exact idle и4jobs/32pins. Все old baselines/lifetimes неизменны.
`!healthy()` само по себе не доказывает sticky: recovery writer finalized=true
ещё в prepare. Доказательством здесь служат пять package refusals и retry,
а не этот вспомогательный scalar. Publication trace имеет прежний ограниченный
смысл, не forensic no-IO claim. Same package pointer equality не заменяет
поведенческие probes; оба присутствуют.

Связанные declarations, conditional compilation, native error types/format и
ownership проверены; подтверждённых C/H source blockers не найдено. Успешную
компиляцию/время13cases/результат ещё нельзя утверждать: они требуют отдельного
runtime receipt. Это минимальная нужная проверка sticky данного пути, не весь
post-birth short/crypto/quota/exception matrix. T116/полная Windows/installed/
hardware/release открыты; AAC71b BUILD FAIL/AAC47/AAC56 сохранены. Никаких VM,
build/tests/code/norm/tasks/checklist/Git/GitHub writes: только append own-report.

## AAC77 Release / AAC78 Debug — независимая saved runtime qualification sticky13

**Scoped runtime PASS / GO для обоих завершённых запусков**, только
ProtectedRecoveryTerminalUnusedSticky. Полностью прочитаны result.json,
result.xml, actual-test.log и декодированные UTF-16LE build.log/test.log каждого
stage. Source/norm gate повторно не проводился; AAC79/live материалы не читались.

Общий exact source216:
`a555f9c284c67ada0a4223ecd25310cbe0578c994f139d3344cc4887f81cfe60`.
AAC77 prior75 `13303a40e3ee24ba47e0fdb7e15860185260888461635b2868a22af8f4abecda`:
ровно три changed entries соответствуют changed.json; staged test/header/CMake
совпадают с manifest, остальные213 entries неизменны. Текущий authoritative
host216/216 также совпал. AAC78 source и prior побайтно равны AAC77 source,
changed=[]; manifest каждого содержит216 строк. PE из prior75 не подменяет77.

| Сохранённый stage | Конфигурация / JUnit case time | PE SHA-256 / bytes по receipt |
| --- | --- | --- |
| aac77-terminal-sticky-release | Release / 25.1749s | dc480c88c49bc5c0efe53657dbe2762100cb16f599755b902f91f7489bea18a8 / 1111040 |
| aac78-terminal-sticky-debug | Debug / 43.4857s | 26dddbe7f0ef3984f7d325570cdac4a68aae6697a5fc36a670d520c219a9ac64 / 7221248 |

Оба receipt: terminal=true, build=0, test_exit=0, executed_tests=1,
postflight=216, owned_processes=0. Оба XML: tests1/failures0/disabled0/skipped0,
status=run, точное имя ProtectedRecoveryTerminalUnusedSticky. JUnit suite time
25/43 — округлённое поле; используются testcase25.1749/43.4857, а не оно.
CTest total real77=25.19s, 78=43.49s. Build logs завершаются получением exe
в соответствующей Release/Debug папке без diagnostic error; test logs содержат
100% tests passed out of1. FULLactual подтверждает настоящий CLI
V5LocalRecordingWriterTests.exe --cold-recovery-terminal-unused-sticky из
той же configuration папки, не default CLI и не пустой skip.

Оба FULLactual содержат в точном порядке все cases0..12 фиксированной таблицы;
автоматическая сверка всех role/op/after_event/native значений между77/78
совпала. Каждый case: hit1, error6, same_writer1, same_package1,
sticky_refusals5, no_retry_effect1. Cases10/11 — canonical read7 after4/after6,
native0000001e; case12 — canonical cancel8 after6/native000003e3. Recovery
write/flush00000070/0000001d и renamec000007f соответствуют ранее reviewed oracle.
14 shape18 markers в каждом (positive baseline плюс13 fixtures), затем ровно
один final cases13/same_package1/exact_memory1/four_members_ids_queue_unchanged1/
jobs_pins_returned1/audio0/network0 и Test Passed. XML system-out обрезан1024
байтами: полнота доказана actual-test.log, не этим усечённым XML фрагментом.

Release cache cold0/proxy0/idle0, normal/terminal baselines actual0==idle0.
Debug cache cold0/proxy16/idle16, normal/terminal actual16==idle16. Final exact
memory/resources reached в обоих, без allowance или изменения утверждений.
В ранее reviewed source per-probe tree/trace equality стоит после каждого из
пяти package refusals и retry, post-destruction equality и job/pin/idle guards
предшествуют final marker. Поэтому PASS включает их прохождение, а не только
печать чисел. !healthy само по себе по-прежнему не отдельное доказательство.

Граница identity evidence: SHA/bytes PE и guest postflight/owned0 подтверждены
сохранёнными receipt; сам PE в этих sparse stages не сохранён, независимо заново
хешировать бинарник здесь нельзя. Отдельных before/after PE stamps в прочитанных
logs нет: дополнительный такой guard не заявляется. Unified81870/78790 EXIT0 —
сообщение main, не отдельно прочитанный здесь terminal-session receipt; saved
terminal/test_exit0 и завершённые CTest logs согласуются с ним.
native_metadata_probes=false не означает отсутствие native filesystem I/O:
этот тест действительно выполняет защищённые файловые операции и их fault
injection. device_audio_read/real_network/installed=false — без записи устройства,
сети или установленного приложения.

Это квалификация sticky13 на exact source в двух конфигурациях, не полная
матрица post-birth short/crypto/quota/exceptions, не полное T116, не hardware/
installed/release acceptance. AAC76 historical unrun, AAC71b BUILD FAIL и
AAC47/56 unresolved сохранены. Отдельное runtime AAC79 не оценено. Изменён только
собственный отчёт; VM/build/tests/source/norm/tasks/checklists/Git/GitHub не тронуты.

## AAC79 — saved Release qualification пяти регрессий на source AAC77

**Scoped runtime PASS / GO: 5/5**, только сохранённый
`aac79-terminal-regressions-release`. Прочитаны целиком receipt/JUnit/FULLactual,
build.log и test.log после UTF-16LE декодирования. Source/requirements gate не
повторялся, AAC80 не просматривался. Навык code-reviewer применён с ограничением
на read-only evidence review; никаких preflight/VM/test запусков.

Source/prior SHA-256 оба
`a555f9c284c67ada0a4223ecd25310cbe0578c994f139d3344cc4887f81cfe60`;
216 строк, source побайтно равен source AAC77, prior равен source, changed=[].
Receipt: terminal=true/configuration=Release/build0/test_exit0/executed5/
postflight216/owned0. PE по receipt
`dc480c88c49bc5c0efe53657dbe2762100cb16f599755b902f91f7489bea18a8`,
1111040 bytes, совпадает с AAC77, не с prior75 PE. Бинарник в saved stage не
сохранён: независимый повторный hash PE или отдельный before/after PE guard
не заявляется. Unified27708 EXIT0 сообщён main, отдельного session receipt здесь
нет; сохранённый terminal/test_exit0 и завершённые CTest logs согласованы.

JUnit tests5/failures0/skipped0/disabled0, все status=run. Exact case times:

| CTest | JUnit seconds |
| --- | --- |
| V5LocalRecordingWriterTests | 61.2042 |
| ProtectedRecoveryPlaybackRestart | 53.2974 |
| ProtectedRecoveryTerminalUnused | 6.00782 |
| ProtectedRecoveryTerminalUnusedCrash | 15.8462 |
| ProtectedRecoveryTerminalUnusedRefusals | 16.5583 |

FULLactual показывает Release exe: default без аргумента и ровно четыре прежних
CLI --cold-recovery-playback-restart/--cold-recovery-terminal-unused/
--cold-recovery-terminal-unused-crash/--cold-recovery-terminal-unused-refusals.
Пять Test Passed, CTest100%/5 и total real152.93s; suite time152 округлён и не
используется вместо testcase times. Каждый XML output усечён1024bytes, поэтому
проверка final markers выполнена по полному actual-test.log.

Default: modes0..2/coldAAC/history,15playable refusals,9prefix refusals/3sealed
phases, trace24 и cuts1..24 все child_exit88/waited1; continued12/unused2,
terminal-unused shape18, process_crash1/power_loss0; playback held_jobs0/2 PASS.
Restart: trace19/cuts1..19 все child88/waited1; финальный rebuild9/completed2/
terminal_unused1/refused6/sealed_readonly1, first+second child88, old_extent
unchanged1. Filtered U: exact shape13/cut13, continued1/fourmembers_ids_queue
unchanged1/coldAACprivacy1. U6: ordinals1..6, строгий DDDCCS, fixture+U child88
на каждом, refused3/completed2/sealed_readonly1/exact_memory1. Refusals: все
cases0..9/publication_events0, semantic0..2 error7; unknown extent/orphan/
singleton error13; reachableAAC/canonical/unbound error7; cancel error6/native
000003e3; final cases10/semantic3/unchanged_disk1/exact_memory1/jobs_pins_returned1.
Обе U ветки сохраняют cachecold0/proxy0/idle0 и normal/terminal baseline0==0.

Неполноты/несоответствия в этом saved scope не выявлены. Поле native_metadata_
probes=false не отрицает actual native filesystem IO/fault/crash tests. Audio,
network, installed=false; это не hardware/installed/latency/powerloss или полное
T116/full Windows acceptance. Sticky13 самого AAC77 здесь не перепрогонялся:
это пять перечисленных регрессий. AAC47/56 unresolved и прежние BUILD failures
сохранены. Изменён только own report, никаких VM/build/tests/code/norm/tasks/
checklists/Git/GitHub действий; AAC80 ожидает отдельного terminal запроса.

## AAC80 — saved Debug qualification U6 и десяти refusals

**Scoped runtime PASS / GO: 2/2** в
`aac80-terminal-regressions-debug`. Полностью прочитаны result.json, result.xml,
actual-test.log и декодированные UTF-16LE build.log/test.log. Requirements/source
gate, нормы и task/checklist markers не переоценивались и не изменялись.

Source/prior оба
`a555f9c284c67ada0a4223ecd25310cbe0578c994f139d3344cc4887f81cfe60`,
216 строк, changed=[], побайтно равны source AAC78 (и77/79). Receipt terminal=true,
Debug/build0/test_exit0/executed2/postflight216/owned0. PE по saved receipt
`26dddbe7f0ef3984f7d325570cdac4a68aae6697a5fc36a670d520c219a9ac64`,
7221248 bytes, равен AAC78 Debug, не AAC77/79 Release. PE binary в stage не
перехеширован, дополнительный before/after PE guard не заявляется.
Unified60865 EXIT0 и terminal всех четырёх main handles — сообщение main;
самостоятельно прочитаны сохранённый terminal receipt и завершённые CTest logs,
а не live guest/session inventory.

JUnit tests2/failures0/skipped0/disabled0, оба status=run:
ProtectedRecoveryTerminalUnusedCrash **30.501s**,
ProtectedRecoveryTerminalUnusedRefusals **31.058s**. CTest100%/2, total real61.57s;
suite time61 округлён. FULLactual содержит точные два Debug exe CLI
--cold-recovery-terminal-unused-crash и --cold-recovery-terminal-unused-refusals,
два Test Passed и final markers (XML output усечён1024bytes и не заменяет full log).

U6: все ordinals1..6 в порядке DDDCCS, fixture_child_exit88/U_child_exit88,
four_members_ids_queue_unchanged1 у каждого; final cuts6/refused3/completed2/
sealed_readonly1/exact_memory1/process_crash1/power_loss0. Refusals: все0..9,
publication_events0 на каждом; semantic0..2 error7, extent/orphan/singleton13,
AAC/canonical/unbound7, cancel6/native000003e3; final cases10/semantic3/
unchanged_disk1/exact_memory1/jobs_pins_returned1. В обоих отдельных CLI:
cold0/empty_proxy16/idle16/exact1/reader_content_read0, normal и terminal baselines
actual16==idle16. Никакой allowance не понадобился, guard assertions сохранены.

Несоответствий в сохранённом AAC80 scope не выявлено. AAC79 Release5/5 из
предыдущего раздела вместе с AAC80 Debug2/2 — квалификация перечисленных
регрессий на exact source, не новая общая/fullT116 приёмка. Sticky13 отдельно
квалифицирован в77/78; остальные fault suites, longpartial, реальные устройства,
installed parity/release этим не добавляются. AAC47/56 unresolved сохранены.
native_metadata_probes=false не отрицает native filesystem IO; device_audio_read,
real_network, installed=false. Только append own-report, без VM/build/tests/
code/norm/tasks/checklist/Git/GitHub действий.

## После AAC80 — actual native parity к master c4dc6d (read-only)

Срез 2026-10-21, authoritative worktree
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`;
сравниваемая база `f5cca687a06dc57ad6ccbef840a0be897eaa6336`;
точный master `c4dc6d470446f03acfbafb1d3d80d780f8159314`.
Windows проверен по CURRENT DIRTY, не по HEAD. SHA256 потока
`git diff --binary HEAD -- apps/windows`:
`28e5fbfbbe5e0e9b61cb2d4a4dbf0902161bffe838d217417f4189d470a93e07`.
Это hash tracked Windows diff, НЕ manifest всех dirty/untracked файлов и НЕ
доказательство установленного пакета. Повторный read-only замер перед записью
дал тот же hash. Для конкретных выводов дополнительно зафиксированы SHA256:

- AppMain.cpp: `eb8a3dcaa6ea50965ab4cd6723a500451c6803d69cb96f623163afeb64c69a29`.
- Audio/WasapiCaptureWorker.cpp: `93a69fe35f505eabab19617b9ca6c448e93621e1cef69d81db5da839f82bd990`.
- Capture/WindowsCaptureSessionController.cpp: `f1e21f50bc2ba1ef2e54df0f9d0c92ac8f489993d7d225d1cd49cfed93717125`.
- Shell/MeetingReminderPresenter.cpp: `f4092215243d9f1fd78d3198f9b0fca4dddfd095bcce5b037ad0a749abc77dc2`.
- Shell/MeetingReminderModel.cpp: `a7c8feb048f5e032582d4f63b3ce267ff945035f950d08980843fb4a310c0806`.
- Upload/DesktopApiClient.cpp: `b0b706df18af64aad7a1adb6b86dee28151ea827d38562b1fc785505f6a54d7a`.
- Upload/DesktopHttpTransport.cpp: `0f644332c963908fecb0ca05accd79432bac6ed8b2480c6c8aca0be61e7a2acf`.

Использован code-reviewer, область — source-only native flows. Mac paths/lines
ниже относятся к git show точного master, Windows — к текущему dirty срезу.
Billing endpoints не объявляются отсутствующими; backend/business и shared
cabinet/routes оставлены main. Никаких VM/build/tests/remote/tracker действий.

1. **F284/T120, высокий приоритет: не закрыта граница непрочитанных WASAPI
   packets при Resume.** WasapiCaptureWorker.cpp:243–257 получает privacyEpoch
   непосредственно перед GetBuffer; :392–394 подавляет по этому поколению.
   Controller.cpp:137–149 меняет epoch и frontier уже принятых sequence;
   :594–599 повторяет эти проверки. NativeCapture.h:3031–3032 переключает
   только timeline; RecordingAudioTimeline.cpp:36–42 чистит её pending mic.
   Пакет периода Pause, оставшийся в native ring и впервые приобретённый после
   Resume, может получить новый разрешённый epoch и sequence. Кодовая защита
   уже acquired/queued/in-flight batches есть, но именно эта native граница
   ими не доказывается. Mac Capture/PrivacySuppressingSampleSource.swift:36–49,
   :57–76 устанавливает конечный FIFO snapshot и подавляет старый prefix после
   Resume. Это source-derived missing boundary; НЕ наблюдавшаяся утечка звука
   и НЕ установленная причина AAC47/56. Следующий шаг T120 — ограниченная
   причинная проверка этой native границы без empty-drain/ослабления PTS.
   Windows chronological timeline/dispatcher отличается от Swift drain;
   идентичный Mac starvation/chronology bug здесь не доказан.
2. **F277/T104–T105: временная ошибка календаря закрывает обычную карточку.**
   AppMain.cpp:3330–3351 вызывает calendarFailed при отсутствии пригодного
   snapshot. MeetingReminderPresenter.cpp:152–156 сохраняет лишь failed-Join
   card; остальные retirePresented и clearCalendar. Mac
   Notifications/DesktopNotificationPresenter.swift:279–295 сохраняет любую
   уже видимую current meeting envelope при temporarilyUnavailable до исходного
   deadline, удаляя прочую stale queue. Это конкретное поведенческое различие.
   Нативный F277 bridge/единый presenter/quiet/history уже существуют: открытая
   задача сама по себе не служит доказательством отсутствия реализации.
3. **Updates/T112: установка не подключена к approved release.** AppMain.cpp:3742
   создаёт appUpdate_ без approvedRelease; WindowsAppUpdateController.h:62–64
   default=nullopt, :92 const, :80 canInstall требует значение. AppMain.cpp:2365–2369
   поэтому не показывает Install. OS check/install adapter и safety gates есть;
   отсутствует production provisioning разрешённого выпуска, не весь updater.
   Нужны release-owned approved source/package/publisher и отдельная подписанная
   install/update/rollback приёмка, не удаление canInstall guard. Live feed не
   проверялся, placeholder AppInstaller не считается разрешением выпуска.
4. **Отдельная граница покрытия auto-detection, не обход доверия.** Bundled
   VerifiedTargetRegistry.cpp:32–47 содержит только точные Teams ARM64 и Telemost
   x64 pins; AppMain использует этот registry. Иные версии/архитектуры и Zoom
   не получают verified target. Это ограничение parity/матрицы T071, не ошибка
   требования verified-only; расширять лишь проверенными Windows pins.

F279 typed join/resolver/native opener, native close/hide, tray, no-activate
notification и Windows platform marker найдены в текущей реализации. В
осмотренных native paths конкретный Mac-only UI leak не установлен; общую
cabinet compatibility проверяет main. Source presence не заменяет runtime/UI
acceptance. Ближайшая последовательность main: F277 fix T104/T105, затем
высокоприоритетная native privacy boundary T120; далее release updater/coverage.
T116/full parity/installed/release GO не выдаётся, AAC47/56 unresolved сохранены.

### F277 — review минимальной конструкции обработки calendar failure

**Construction GO с нижеследующими обязательными границами; не actual source
или runtime GO.** `calendarFailed(bool temporary=false)` и
`clearCalendar(optional existing target)` достаточны, новый service/cache не
нужен. Безусловное `transportFailed/status0 => temporary` — NO-GO.

- Только temporary + существующий presented + действительно видимая та же
  meeting card (id/kind совпадают) + неистёкшие wall/steady deadlines сохраняют
  одну уже принятую event. clearCalendar фильтрует имеющиеся events по полной
  target identity (epoch/event/start/link presence/URL), НЕ вставляет target
  как новое событие; upcomingAvailable=false всегда. Сохраняются исходные оба
  deadline, claim/history/quiet/privacy, состояние pending Join/failed Join.
  Нет повторного beforeFirstShow/sound, нового candidate из старого snapshot
  или автоматического запуска/Record. Кнопка остаётся лишь намерением: fresh
  context/join-target и существующие operation fences обязательны.
- false всегда retire+clear, включая старый failedJoinUntil early-return:
  иначе definitive failure по-прежнему оставит карточку. Auth/logout/account/
  interaction invalidation, invalid context/JSON/owner, неподдержанная схема,
  redirect, TLS/certificate, cancellation, неизвестная ошибка/exception — false.
  При temporary и нет видимой допустимой карточки — тоже полная очистка.
- Два независимых wire paths сейчас теряют причину: DesktopApiClient.cpp:547–610
  calendar GET возвращает status/snapshot; AppMain.cpp:3365–3371 сжимает context
  failure/invalid decoded identity до той же пары. DesktopHttpTransport.h:93–104,
  :145–154 и cpp:941–969 сохраняют transportFailed, но не его тип. По этим
  данным отделить TLS от сети невозможно: нужен малый typed failure outcome
  от места ошибки, проведённый через оба paths. Нельзя восстанавливать причину
  по status0/пустому body/тексту сообщения.
- Сохранять first actual error непосредственно после failed WinHTTP call,
  ДО cancellation/clock/cleanup/другого API. request::phase cpp:298–300 сейчас
  делает active() после call, поэтому поздний GetLastError снаружи ненадёжен.
  Отмена/смена контекста имеет приоритет над temporary. Не переносить эту
  notification classification в upload retry/security semantics.
- Минимальный conservative network allowlist: ERROR_WINHTTP_TIMEOUT,
  NAME_NOT_RESOLVED, CANNOT_CONNECT в реальных send/receive/read network phases;
  всё неизвестное/неверная конфигурация false. ВАЖНО: CONNECTION_ERROR не
  включать без дополнительного доказательства — Microsoft документирует также
  incompatible SSL protocol. SECURE_*, certificate/client-cert/login, malformed
  response/redirect и cancellation не temporary. Никаких ignore-cert flags,
  permissive callbacks или новых retries ради этой правки.
- HTTP 408/429 и 500..599 temporary только при достоверном HTTP response с
  сохранёнными security/transport результатами, не если рядом уже sticky
  TLS/protocol/cancel/context error. 401/403 и прочие definitive ответы false.
  HTTP error context не нужно успешно JSON-decode: сам validated ответ может
  означать unavailable. Но accepted 200/202 + missing/invalid/mismatched decoded
  context — definitive, НЕ transport failure; model.update=false также не
  temporary. Декодирование успешного calendar response, size/deadline и owner
  guards не ослаблять. Auth expiry из неподтверждённого контекста не наследовать.

Источник различия WinHTTP error meanings (read-only Microsoft Learn):
https://learn.microsoft.com/en-us/windows/win32/winhttp/error-messages
CONNECTION_ERROR включает reset/termination И incompatible SSL; TIMEOUT/DNS/
CANNOT_CONNECT документированы отдельно. Это conservative UI retention policy,
не гарантия отсутствия всех возможных сетевых/TLS причин внутри ОС.

Минимальная последующая проверка actual diff: visible-card transient + другая
старая event удалена/menu unavailable; повторная ошибка не продлевает deadline;
expiry/no-visible/не та card не resurrect; HTTP status и две wire failure
ветви отдельно; TLS/CONNECTION_ERROR/invalid context/owner/redirect/cancel/
auth/interaction definitive; fresh successful removal/retarget прекращает card;
pending Join не получает launch/Record от cached projection. Source/VM/tests/
norm/tasks/checklist/Git/GitHub не менялись; добавлен только этот own report.

### T104 follow-up — terminal close против успешного JoinAndRecord handoff

Read-only текущих callers, 2026-10-21; AppMain/Presenter/Model hashes прежние
eb8a3dca / f4092215 / a7c8feb0 (полные SHA выше). **Безусловный purge внутри
completeAction или всякого retirePresented — NO-GO. Construction GO на
разделение ниже; actual diff/runtime ещё не предъявлены.** Это уточнение
жизненного цикла, не отмена definitive calendarFailed(false) => retire+clear.

Подтверждённая цепочка:

1. AppMain.cpp:3059–3064 фиксирует native action и её первоначальный steady
   expiry. :2952–2962 проверяет pendingActionExpiry, epoch, owner/workspace/
   origin; :2973–2979 связывает это с CalendarJoinOperation. Resolver отправлен
   через :3098–3104, launcher query/launch использует calendarCurrent в
   :3118–3124. Temporary card projection не заменяет fresh join-target resolver.
2. :3243–3245 после реального завершения OS operation требует matching complete
   и calendarCurrent. Только outcome=launched и finish(handedOff)=true
   (:3251–3256) допускают completeAction (:3257–3258). Operation::finish
   cpp:133–145 требует current, opening, отсутствие work, reason=none.
3. Presenter.cpp:251–256 ещё раз проверяет pendingActionExpiry/revalidate и
   закрывает показ; retirePresented :144–150 ставит dismissal, сбрасывает
   pending/presented, НО сейчас не удаляет event. Это намеренная зависимость.
4. AppMain.cpp:3259–3262 передаёт НЕ фоновый task, а синхронный predicate в
   recordCapture. Тот вызывает predicate до readiness, после refreshReadiness
   и непосредственно перед capture_->record (:2484–2499). Predicate проверяет
   auth/session/interaction, handoffRecordingCurrent и исходный action expiry.
   Presenter.cpp:285–287 -> Model.cpp:353–361 намеренно использует currentEvent,
   НЕ dismissed-aware revalidate. Поэтому закрытая completed card не оживает,
   но подтверждённый handoff ещё может пройти повторные Record fences.
   Удаление event при completeAction делает этот predicate всегда false.

Минимальное корректное различие:

- Неуспех/Close/expiry/quiet/invalidation/definitive failure уничтожает
  временно удержанную stale projection; она не переживает терминальное
  закрытие и не становится очередью новых уведомлений. При этом не добавлять
  глобальную очистку нормального свежего calendar snapshot в каждый
  retirePresented: это затронет меню/другие будущие встречи вне данной правки.
- Только успешный completeAction после тех же pending/revalidate guards
  получает явную внутреннюю ветвь successful handoff (например private
  retire argument default=terminal, либо отдельная узкая success cleanup).
  Для Join/JoinAndRecord оставить одну точную завершённую цель из уже
  удержанной projection доступной matchesHandoffTarget, не presented/pending.
  По умолчанию все прочие retire callers остаются terminal; никакого
  публичного произвольного retain target/нового launch grant.
- Различать сокращённую temporary projection и обычный подтверждённый
  snapshot в существующем владельце модели/представления. Если для cleanup
  нужен признак, это один локальный lifecycle flag, не новый cache/service.
  Successful handoff не повышает upcomingAvailable и не возвращает старую
  очередь. Для чистого Record отдельный handoff retention не нужен.
- Сохранённая цель — данные для повторной проверки, не право Record. В AppMain
  оставить условие реального launched+успешного finish+completeAction, только
  action=joinAndRecord; оставить все три current-проверки recordCapture.
  Не делать predicate потребляющим: второе/третье чтение тоже обязательно.
  Не заменять его на calendarCurrent после finish: операция уже терминальна,
  а source pending уже снят. Не заменять matchesHandoffTarget на revalidate:
  успешная цель уже dismiss и такой revalidate её закономерно отклонит.
- Обновление с удалением/заменой target, account/epoch/interaction change,
  quiet, другая карточка, начавшаяся запись и оба исходных expiry продолжают
  отзывать применимость. Новая temporary failure при отсутствии видимой
  presented card не даёт исключения для старого handoff. Не разрешать старый
  cached target для нового resolver/launch/повтора Record; успех операции
  остаётся обязательным отдельным условием её единственного caller.

RecordingNoticePresenter.cpp:261–271 подтверждает, что dismiss=finish(false)
не вызывает onInvalidated; close :304–308 вызывает onClose. Поэтому success
cleanup можно отделить без имитации пользовательского Close/invalidate и без
новых UI событий. Не ослаблять callbacks/fences при реализации.

Уже существующие source tests NativeSettingsBridgeTests.cpp:863–875 требуют
completeAction exactly once, handoff applicability после закрытия, отказ при
recording и при replaced/removed event того же epoch. Они должны сохраниться;
добавить целевые ожидания для temporary failure -> successful JoinAndRecord и
temporary -> Close/expiry/definitive clear, включая отзыв между тремя Record
checks. RecordingIndicatorTests.cpp:746–749 проверяет host ordering, но это
не runtime доказательство async OS handoff. Никаких тестов не запускалось,
ничего кроме собственного отчёта не менялось.

### T104 actual SOURCE + Ponytail — предъявленный calendar failure diff

2026-10-21, тот же authoritative worktree/HEAD. Прочитаны текущие методы и
callers одиннадцати предъявленных файлов, не весь накопленный historical diff.
**SOURCE verdict: REQUEST CHANGES / NO-GO до двух узких исправлений,
C0/H0/M2.** Это не отзыв meaningful RED и не новая полная приёмка T104/T119.

Exact SHA256 рассмотренного среза (пути относительно apps/windows/):

```text
909591a87f0ae91dbb8c78c20d635a5a989af20ca2da7cf204d1e2ec7eb488ad RecApp/Upload/DesktopApiClient.h
adc9245f1bc4a5c7adb3e2dd65b072cb8cd5d32fb775e626d963ec70bfc84dd2 RecApp/Upload/DesktopApiClient.cpp
c0f46b9495a9308a8aba2767aad8f19e4883b18c010e251348e6857e29c65b33 RecApp/Upload/DesktopHttpTransport.h
086c6e2b47ef015029c5e1366a882d97a2bda100c77d3f9abab7d273d4e274a3 RecApp/Upload/DesktopHttpTransport.cpp
c610bc7d7134f1454525042e9da6c9042458806bd80a26cc4c10856db88dd331 RecApp/Shell/MeetingReminderModel.h
8aab49cfcbe1a7cf4a688f6865fa8e97a975fa630c49e560392721faa4ee53d1 RecApp/Shell/MeetingReminderModel.cpp
4c8d73de2221911c59edac4b6de1db84977da8d4ecc84cbd83f3cb31d6aee6ab RecApp/Shell/MeetingReminderPresenter.h
6d43890036b799ffe6dd229a37c567985073badf16fa7cd5a3786ccc71be2107 RecApp/Shell/MeetingReminderPresenter.cpp
a7927bb8e84b05f0c747fdca7756edbd8b0509ce8f49a0083187ff9680f0ff38 RecApp/AppMain.cpp
6468a0094e0a5c2e40bab4ae2e5f4aa70d8f21d7d0e72ef5adc93997442ee263 Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp
24e1218203a5b37dace07b0d6375e54300595a34ab6c9cb94e365888cd51ac7b Tests/GrafWindowsContractTests/NativeCalendarJoinTransportTests.cpp
```

**M1: известный definitive HTTP status превращается в temporary после сбоя
чтения его тела.** DesktopApiClient.cpp:529–534 отдаёт приоритет allowlisted
nativeError при любом status кроме401/403. В реальном context path
DesktopHttpTransport.cpp:404–407 сохраняет, например, status404; :459–485 затем
читает тело и может получить TIMEOUT12002. Через deletionCall :974–977 и
AppMain.cpp:3371–3375 это становится CalendarReminderResponse{404, no snapshot,
no expiry,12002,true}. temporarilyUnavailable возвращает true и :3352 сохраняет
карточку. То же возможно для400/3xx. Согласованная конструкция требовала
definitive/auth/interaction => false. NativeSettingsBridgeTests.cpp:771–774
наоборот явно закрепляет true для404/400/301 с timeout — ложный oracle именно
этого случая, не отсутствие теста. Минимум: приоритет уже известного definitive
HTTP ответа над network body failure; при этом 200 с незавершённым чтением и
status0 network failure могут оставаться temporary. 408/429/5xx с TLS/cancel/
unknown transport error всё ещё НЕ temporary. Нужна целевая wire регрессия
context404 + read timeout, а не только изменение truth table.

**M2: исключение при возврате completeAction может предшествовать cleanup.**
Presenter.cpp:267 создаёт `const auto event`; :268 закрывает показ с
completingHandoff=true и оставляет retained projection; :269 возвращает
именованный const optional. NRVO допустима, но не гарантирована: без неё
возврат копирует optional/CalendarReminderEvent со строками, может бросить
bad_alloc. HandoffCleanup в AppMain.cpp:3259–3263 ещё не создан, поскольку
условие с completeAction :3257–3258 не завершилось. В таком пути projection
остаётся после закрытия, хотя Record не начнётся. Это source exception hole,
не наблюдавшийся runtime failure. Минимум: локальный `auto event` без const
для не бросающего implicit move std::optional<CalendarReminderEvent> при
отсутствии NRVO (текущие поля — std::string/scalars, стандартный allocator).
Не нужен новый guard/service и не нужно ослаблять terminal clear.

Остальной прослеженный поток:

- Presenter:154–163 сохраняет только matching видимую event, оба deadlines,
  failedJoinUntil; Model:289–295 фильтрует существующие records по полной
  target identity и запрещает upcoming. Старое исключение failedJoin при
  definitive false удалено. Terminal retire очищает лишь retained projection,
  не обычный свежий snapshot; обычный Join не оставляет temporary handoff.
- completeAction(joinAndRecord) оставляет модель только для synchronous Record;
  AppMain:3251–3268 сохраняет actual OS launched/finish/current checks.
  После успешного возврата completeAction cleanup уже охватывает construction
  predicate, readiness exceptions и все ранние возвраты recordCapture.
  Predicate не потребляющий, все три проверки остаются. finishHandoff
  Presenter:165–168 очищает retained projection. Fresh successful update
  :175–178 снимает retainedCalendar_, поэтому старый cleanup НЕ стирает новый
  snapshot; новый presented также защищён. Auth bind/invalidate сбрасывают flag.
- Pending Join переживает temporary failure без нового действия и deadline;
  pending Record с уже скрытой card не удерживается и не стартует по failed
  refresh. Наличие cached target не заменяет fresh resolver/launch fences.
- WinHTTP error фиксируется сразу после фактического call, до active/cleanup;
  raw code сохраняется по обеим production ветвям. Send/receive/available/read
  помечены network, TLS12030/12175 не включены. Explicit cancellation имеет
  ERROR_OPERATION_ABORTED; AppMain также отбрасывает cancelled response до
  применения. Неверный decoded context200/mismatched owner/status0 unknown
  не temporary. Upload retry классификация не переписана.

Saved `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t104-meaningful-red.log`
прочитан целиком: NativeSettingsBridgeTests failed0.56s на card visible /
generation / deadline, historical line782. Это содержательный RED ordinary
visible card, не build/timeout. Не приписываю этому 19-line логу самостоятельный
source manifest или последующий GREEN. Текущие tests проверяют same-card,
no-repeat sound/deadline, terminal boundaries, triple handoff predicate и cleanup;
Windows wire тест дополнен четырьмя phase failures, но не указанным M1 сочетанием.
Свежий snapshot при finishHandoff и failed Record host cleanup пока проверены
source trace, не отдельным выполненным runtime здесь.

Ponytail-review (только сложность): **Lean already. Ship.** Новых services,
dependencies/cache/abstraction нет; локальный scope guard оправдан ранними
выходами. net: -0 lines possible в безопасном complexity-only проходе. Это
НЕ source/release GO: correctness M1/M2 выше требуют правок. Не удалять tests,
native cause/fences или scope guard ради сокращения. Только own-report append;
без VM/build/tests/source/norm/tasks/checklist/Git/GitHub изменений.

### T104 bounded follow-up — CURRENT classifier после native3 snapshot

2026-10-21. Не перечитывал историю/нормы целиком, не читал live native3 или
native4. Main сообщил native2 PASS и native3 на предшествующем source; эти
runtime результаты здесь не квалифицируются и не переносятся на новый код.

M1 подтверждался source529–534 и ранее согласованной construction note
definitive/redirect=false. В CURRENT DesktopApiClient.cpp:529–535 исправлен:
snapshot и любой известный status кроме0/200/202/408/429/500..599 сначала дают
false; только затем оценивается allowlisted network cause. Поэтому301/400/
404/600 + TIMEOUT больше не удерживают card. TLS/unknown/cancel при retryable
HTTP остаются false, 200/202 malformed context без network cause также false.
**M1 закрыт по CURRENT source; bounded classifier SOURCE GO.** Negative truth
table NativeSettingsBridgeTests.cpp:765–779 соответствует этому порядку.

Проверены также только названные новые отличия: CMakeLists.txt:23 удаляет API
из common glob; :94–97 компилирует отдельный api object с прежними warnings;
:142–145 подключает его обычным tests, исключая native wrapper executable.
NativeCalendarJoinTransportTests.cpp:193–194 включает реальные transport и API
под теми же WinHTTP wrappers; :237–255 упражняет обе HTTP стадии (available
не относится к API reader, который читает ReadData напрямую). Дублирования
API symbols из common/object по этой конструкции не видно. Windows build не
запускался. Новый NativeSettingsBridgeTests.cpp:845–866 проверяет именно failed
Record refresh с уже скрытой card: pending снимается и свежий snapshot не
завершает старый intent; это не отдельный тест readiness failure после Join.
Избыточной новой инфраструктуры/зависимостей в этом delta не найдено.

**Полный прежний T104 source verdict всё ещё NO-GO только по M2:**
Presenter.cpp:267 в CURRENT по-прежнему `const auto event`, post-retire return
с optional NRVO, cleanup в AppMain создаётся позже. Hash Presenter и AppMain
не изменился относительно предыдущего actual review. Минимальное исправление
без const остаётся необходимым; M1 fix сам по себе не закрывает этот finding.
C0/H0/M1 remaining (это прежний M2, не новое замечание). После его actual diff
достаточен узкий повтор, не новый полный аудит.

Точные SHA256 новых/проверенных inputs:

```text
59cc7d25bc687160c64fc7dd78dd47c2a606fab1a6dab0cd497ae20abb27ea27 RecApp/Upload/DesktopApiClient.cpp
6d43890036b799ffe6dd229a37c567985073badf16fa7cd5a3786ccc71be2107 RecApp/Shell/MeetingReminderPresenter.cpp
a7927bb8e84b05f0c747fdca7756edbd8b0509ce8f49a0083187ff9680f0ff38 RecApp/AppMain.cpp
27ef43206a8c8b9bffd1d713bac1a988b835e70659dfbd4c9183f524be9ec3ed Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp
50b9e55eaaea7e023cfa23c5e843dd838123ec57f9a95f9ef60d4cbcb3d76aca Tests/GrafWindowsContractTests/NativeCalendarJoinTransportTests.cpp
a7a08a0796491698fdde74618ac82d96caf365a42871ea4c8068ac59f89a0574 CMakeLists.txt
```

Пути выше относительно apps/windows. Только append own report; без source,
norm/tasks/checklists/Git/GitHub/VM/build/test действий. Исторические M1/M2 и
meaningful RED сохранены; source qualification не выдаётся за native4 PASS.

### T104 final bounded SOURCE — M2 и новые regression inputs перед native5

2026-10-21, code-reviewer, только предъявленные отличия. **M2 закрыт;
scoped SOURCE GO, C0/H0/M0 в ранее рассмотренной области T104.** Старые
NO-GO/M1/M2 и meaningful RED выше сохранены как история, не удалены. Новых
runtime результатов здесь нет, native5/живые процессы и logs не читались.

Presenter.cpp:264–269 теперь `auto event` без const — единственное изменение
этого production файла относительно предыдущего review. Без NRVO return
получает implicit move optional; CalendarReminderEvent имеет только стандартные
std::string и scalar поля (DesktopApiClient.h:59–69), их move и optional move
не бросают. Post-retire allocating copy больше не требуется. AppMain scope
cleanup прежний и по-прежнему охватывает Record ранние возвраты/исключения после
успешного completeAction. Прежний M1 classifier fix source hash не изменился.

NativeCalendarJoinTransportTests.cpp:258–265 действительно вызывает production
notificationContext через native wrappers: HTTP status301/400/401/403/404/
408/429/503 сначала прочитан, потом ReadData выдаёт TIMEOUT. Проверяются сам
status, transportFailed и точный nativeError; temporary=true только для
408/429/503. Это реальная wire-combination construction, не одна truth table.
Соседний loop:240–255 отдельно упражняет обе HTTP реализации и TLS/non-TLS
causes; для ReadData-only API осознанно исключён available phase.

NativeSettingsBridgeTests.cpp:961–983 после temporary projection и успешного
joinAndRecord completeAction подставляет свежий snapshot либо предварительно
меняет context origin. Старый finishHandoff не стирает новое upcoming; старый
target теряет currency при context change. Без смены контекста совпавшая event
остаётся данными для currency, а не повторным launch/Record grant — отдельные
operation/host checks сохранены. Новый test и failedRecord old-intent test
действительно вызваны в main (:1721/:1724). FailedRecord :845–866 сохраняет
проверку снятого pending и невозможности завершить старый intent после fresh
snapshot. Это не тест реального OS launch/записи и не отдельное исключение
bad_alloc в host; source guarantees и runtime evidence не смешиваются.

Текущие SHA256 (apps/windows/):

```text
8dc420c5f19f3d80c029daa7d229c986bfeb34e4899f3c31b0369fee02faf1ff RecApp/Shell/MeetingReminderPresenter.cpp
59cc7d25bc687160c64fc7dd78dd47c2a606fab1a6dab0cd497ae20abb27ea27 RecApp/Upload/DesktopApiClient.cpp
d4c07768cfb3650b830c73fd741192d66d1931debd5668ef7b587e65e1bfdde7 Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp
ae2956f80a904449a8b289c1a9173145d7eae6a18ffb509047d1e2a95c04a6c0 Tests/GrafWindowsContractTests/NativeCalendarJoinTransportTests.cpp
a7927bb8e84b05f0c747fdca7756edbd8b0509ce8f49a0083187ff9680f0ff38 RecApp/AppMain.cpp
a7a08a0796491698fdde74618ac82d96caf365a42871ea4c8068ac59f89a0574 CMakeLists.txt
```

Остальная SOURCE область не переаудирована; новых complexity findings в этих
узких изменениях нет. Достаточно переходить к согласованному последовательному
native5 на exact frozen source, без заявления его PASS заранее. Не полный
T104/T119/T116/installed parity/release GO. Только own-report append, без
source/norm/tasks/checklists/VM/build/tests/Git/GitHub действий.

### T104 native5 — независимая квалификация сохранённого Debug 6/6

2026-10-21, bounded saved-evidence review. **Scoped runtime GO: native5
Debug 6/6 подтверждён; несоответствий в предъявленном receipt/XML/full log и
current216 не найдено.** Это не общий PASS portable/full application и не
закрытие T104/T116/T119/T120 либо installed/release acceptance.

Источник: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t104-calendar-native5`.
Полностью прочитаны result.json, result.xml, actual-test.log, декодированные
UTF-16LE build.log и test.log. Receipt: terminal=true, configuration=Debug,
build=0, test_exit=0, executed_tests=6, postflight=216, owned_processes=0,
без failure. device_audio_read/real_network/installed=false. Сообщённый main
terminal exit0 согласуется с сохранёнными результатами; отдельного внешнего
process-exit receipt в папке нет, самостоятельных guest checks не выполнялось.

SHA256 source.sha256:
`ce0eefe6314465e25c1e620358bc08047ff843f2768887e7252f5ee3b4e2d83d`.
Проверены **216 уникальных путей/216 совпадений** с текущими файлами
authoritative worktree на HEAD b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1;
missing/mismatch=0. Вычисленный delta prior→source совпал с changed.json:
только Presenter.cpp и NativeCalendarJoinTransportTests.cpp; удалённых inputs
нет, обе сохранённые sparse copies совпадают со своими manifest hashes.
Таким образом ранее проверенные M2 fix и actual wire combinations входят в
исполненный snapshot, а не только в более поздний source.

XML: tests=6, failures=0, skipped=0, disabled=0, все status=run. FULL
actual-test.log содержит ровно эти шесть executable commands, без CLI flags,
шесть Test Passed и заключительный End testing. Test.log: 100%/6 и total
3.08s; build.log содержит Debug outputs всех семи собранных targets, без
compiler failure. Точные testcase времена и receipt PE SHA256:

```text
CalendarJoinResolverTests 0.118961s 2ef3dda89416a8b51f3e5b1ef4da3aff4460e9f70ed26b8da7c6b8e6601dc959
CalendarJoinWireTests 0.0945851s e53482aeb07b9d2f167334260bdeafad1193dc5c9daae76fb1f8eeee3a32eefc
CalendarJoinOperationTests 0.101501s 7cc3c1905c485d6bd3395ae83a7610301ced1ebd89e0db377c53ac893f15d3c1
DesktopDeletionProtocolTests 0.656704s 46c1d93328cc617e72eed153e6ed65c04e567be10b2a6df81684462da7d06bb3
NativeSettingsBridgeTests 0.906503s 83131211daa0e51c75ed5fadda7204a6f800b6eba492e96e6155d38b3b7b503d
NativeCalendarJoinTransportTests 1.19655s 9119903f9342963f25266ebf6be9f7c03646205a675062302ee5b7e512c43499
```

NativeSettings и native transport assertions активны (#undef NDEBUG перед
cassert); новый failedRecord/fresh-snapshot/context cleanup tests вызваны
main, wire loop включает 301/400/401/403/404/408/429/503 + actual read timeout.
Полные их CLI дошли до PASS; отдельные новые asserts не имеют собственных
per-case log markers, их покрытие установлено по exact source + default CLI,
не выдуманным runtime строкам. CalendarJoinOperation вывод прямо ограничивает
себя state/fence, не adapter completion. Native transport также сохранил quota
и handle-cleanup markers. Это generated/wrapped transport, не live HTTP/OS join.

Read-only просмотр текущего external validate-t104.ps1 подтверждает: Debug
build семи targets; anchored CTest selection исключает RecordingIndicatorTests;
Assert-Source216 до/после; hashes PE до/после; итоговый owned-process guard.
Receipt failure отсутствует, postflight216 достигнут. Сам script не сохранён
как immutable validate-input внутри native5, поэтому это проверка текущего
harness, а не отдельная аттестация его исторического hash. PE binaries локально
не представлены: приведены receipt hashes, без нового guest hashing.
RecordingIndicatorTests имеет build output и PE в receipt, **но не исполнялся
в native5 и его PASS не заявляется**.

Сохранённые SHA256 артефактов:

```text
a253afd3da2c86333cc9296c69d50c85e81115994cf0e25f6a82501922f71c61 result.json
4245fc6970a23a63e15fa994400781ef175877272aac7770e970539e3b5788de result.xml
4218a0e16f8ed366c5d0cdceebef9643a0b22a450f07d8572368c7f59966c3cb actual-test.log
d17e4b588c9fb855700caaf56d634c4c4359ffd4080fe45d38e1a749d9cd64d7 build.log
c0025ab3e052b86a752f96e8f6ab1903ae3fc7927d65cf056a54c2ad869533ed test.log
```

Отдельный portable48 main сообщил как 46 PASS/2 FAIL:
DesktopUploadQueueV2Tests:506 unowned prepare и RecordingIndicatorTests:558
old manual-send source assertion. В этой bounded qualification тот прогон
повторно не исследовался; **общий PASS не выдаётся, оба FAIL сохраняются**.
Исторические RED/M1/M2 не удалены. Только own-report append; никаких VM,
build/tests, code/norm/tasks/checklists/Git/GitHub изменений или запусков.

### T120 — read-only WASAPI unread-source frontier и место причинного RED

2026-10-21, code-reviewer; только source/primary-doc feasibility, не новый
requirements/source/runtime GO. Authoritative HEAD b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1;
current216 повторно совпал с native5 manifest ce0eefe6314465e25c1e620358bc08047ff843f2768887e7252f5ee3b4e2d83d.
Mac сравнен через git show exact master c4dc6d470446f03acfbafb1d3d80d780f8159314,
без checkout/fetch/merge. В репозитории WasapiCaptureWorker.h, не .hpp.
T120 tasks.md:602 и plan:1599–1649 оставлены неизменными. **Подтверждён
пробел source-frontier; реальная утечка не воспроизведена и не заявляется.**

Причинная цепь и сохранённые защиты:

- Worker.h:67–101 имеет asynchronous Start/Stop, private epoch pointer,
  consumePacket и deviceRunForTesting; Resume/native-frontier command API нет.
  Worker.cpp:243–257 снимает epoch перед GetBuffer, а не при заполнении native
  queue. :352–364 валидирует clock; :390–398 переносит epoch/suppression в
  normalizer. Старый native packet, впервые acquired после even Resume epoch,
  этим признаком не отличается от нового. Строгое увеличение packet clock
  само по себе возраст относительно Resume не проверяет.
- Controller.cpp:113–134 public request не принимает Resume синхронно:
  UI ставит единственную команду; dispatchLoop:480–506 исполняет её отдельно
  от audio FIFO; :188–200 UI принимает completion. :137–149 serializes sink
  и меняет FIFO sequence frontier/epoch; :594–599 повторно подавляет queued,
  extracted и old-epoch mic. Это правильные, но не native unread, границы.
- NativeCapture.h:561–562 делегирует public pause/resume; AppMain:2596–2601
  вызывает их из UI, :3567–3569 блокирует кнопку на privacyPending. Handler
  NativeCapture.h:3031–3032 только вызывает timeline.setMicrophonePaused.
  :3034–3046 writer checkpoint принадлежит тому же dispatcher, не WASAPI/UI.
- Controller.cpp:160–177 OPEN предшествует Pause boundary; Resume boundary
  предшествует best-effort CLOSE. Не переносить CLOSE перед frontier и не
  превращать неизвестный frontier в обычный nonfatal CLOSE failure.
  Stop:261–289 закрывает admission под dispatchMutex, снимает control slots,
  останавливает workers и ставит EOS; late source ACK не вправе его отменить.
- ClockMapper.cpp:16–67 сохраняет sticky flags/clock/continuity/frame-count/
  drift checks. Timeline.cpp:36–42 чистит pending mic, :89–103 проверяет offsets
  и PTS, :134–158 обнуляет mic при сохранении интервала, :188–213 вызывает
  AEC на каждой полной паре 480 frames. Нельзя выкидывать native packets,
  reset mapper/normalizer, перезапускать stream, вставлять wall-clock silence
  или пропускать AEC ради Resume.

Mac PrivacySuppressingSampleSource.swift:36–49 захватывает finite queue count
под настоящим producer FIFO lock и меняет state; :57–76 снимает только старый
prefix, оставляет PTS/формат. RecordingSampleSources.swift:186–187 даёт именно
полный timestampedQueuedFrameCount под тем же lock; default interface без такой
возможности возвращает false. Writer.swift:454–463 при unavailable оставляет
paused, при успешном boundary CLOSE best-effort. Это смысл для паритета, не
готовый WASAPI queue-count API. Уже prefetched Mac batch отдельно :80–93.

**Отвергнутая короткая конструкция:** GetCurrentPadding/GetNextPacketSize не
дают суммарный unread count. Microsoft для shared capture определяет оба как
размер следующего packet; в buffer одновременно может быть несколько packets.
Один такой count пропустит хвост очереди. GetBuffer/ReleaseBuffer и
GetNextPacketSize должны оставаться на одном acquisition thread.

**Минимальное направление, требующее actual source review перед принятием:**
один private request/result slot для source boundary в существующем mic
worker, без новой FIFO/адаптерной иерархии. На acquisition thread между
завершённым ReleaseBuffer и следующим GetBuffer получить конечный cursor
того же IAudioClock через GetPosition(position, qpc), с уже полученной
GetFrequency. Только S_OK, действующие stream/route/command epoch и
проверяемый свежий correlated tuple; S_FALSE/exception/неизвестная единица,
overflow, stale/mismatching result не разрешают Resume. Position — НЕ
GetBuffer.deviceFrames: единицы могут быть bytes. Приведение через position /
frequency к native input frame domain требует checked rational arithmetic,
явного exclusive frontier и проверки согласованности с packet position/QPC;
никакой догадки frequency==sampleRate, raw hardware IAudioClock2 substitution,
неограниченной экстраполяции или произвольного timestamp tolerance. Current
поток ещё не реализует такой proof; таблица чисел в fake не доказывает driver.

Порог должен отсекать ВСЕ input frames до подтверждённой границы, включая
последующие чтения нескольких old packets, и заменяться при следующем Resume.
Не ждать queue-empty и не дренировать её отдельным control loop. Нормальное
чтение продолжает проверять и Release каждый packet; старые samples обнуляются,
не исчезают из clock/normalizer/timeline. Пересекающий frontier packet требует
точного prefix, не wholesale suppression допустимого suffix: текущего одного
batch.microphoneSuppressed bool недостаточно. Наименьший reuse — bounded scalar
prefix count в native input domain, применённый в существующем normalizer
ПОСЛЕ полной finite validation и ДО downmix/resampling. Сохранить его tail/epoch
защиту :53–57/:117–123, submitted/delivered offsets, PTS/count/channel shape.
Не маскировать NaN обнулением до validation. Exact rounding/current-frame
endpoint должны быть определены и проверены отдельно, не выдаваться за уже
доказанную математическую эквивалентность без предъявленного diff.

Source snapshot, suppression frontier и его activation должны иметь один
порядок относительно mic acquisitions и even epoch. Нельзя сначала публиковать
even epoch/recording, потом асинхронно искать cursor; нельзя применять ACK
предыдущего Resume. Controller уже имеет slot/completion plumbing: расширить
его source-frontier result, сохранив owner. UI/Stop не ждут. Dispatcher не
держит captureMutex/dispatchMutex при ожидании native ACK — worker callback
сам требует dispatchMutex; иначе deadlock. Final publish коротко сверяет Stop,
fault, source/route identity и command generation под существующей boundary
блокировкой. Unknown/pending не меняет odd paused epoch и UI; definitive
failure остаётся paused либо приводит к Stop при capture fault. Late ACK после
Stop игнорируется, не вызывает unpause/CLOSE новой сессии. Срок ожидания bounded,
не бесконечные S_FALSE retries. Старые queue/in-flight gates не удаляются.

**Meaningful RED без устройств уже имеет seam:** CaptureFaultStateTests.cpp:
66–114 (CaptureSessionTestPeer::device/packet/packetWithEpoch), production
consumePacket и реальные worker/dispatcher/timeline. :787–872 нынешний prefetch
тест снимает epoch ДО удержания; новый case должен удержать два+ generated
packets в fake source ДО первого чтения/epoch snapshot, выполнить public
async Pause/Resume с checkpoint fake, затем подать старые валидные contiguous
ClockObservation через packet(), который снимет уже новый epoch. Preload
pre-Pause prefix, continuous render и ещё один genuine post-frontier mic
packet: точное ожидаемое mic=0 для старого prefix, audible только suffix;
system/PTS/count/AEC/EOS/finalizer unchanged. В текущем source старые samples
не помечаются suppressed — это причинное ожидание RED, не выполненный тест.
Дойти до teardown/EOS/join перед named assertion. Не использовать только
peer.boundary(:138–146): это обход public/durable command, не admission proof.
Отдельно partial native packet, повторная Pause/Resume, continuous producer,
ACK held/failed/S_FALSE, Stop-race и release/NaN/clock faults.

deviceRunForTesting обходит настоящий COM acquisition loop: это полноценный
consumer/controller synthetic RED, но НЕ native GetBuffer-loop acceptance.
Готового fake IAudioCaptureClient/IAudioClock wrapper seam здесь нет. Для native
API proof достаточно test-only COM/wrapper по существующему образцу native
transport TU, либо узкого private snapshot primitive с test peer; не вводить
production device framework. Wrapper обязан моделировать FIFO нескольких
packets, точные position/frequency/QPC и thread/release order, не только
запрограммированную epoch. Нужен actual test diff review, прежде чем его GO.

Primary Microsoft references (read-only):

- [GetCurrentPadding](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclient-getcurrentpadding)
- [GetBuffer](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getbuffer)
- [GetNextPacketSize](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudiocaptureclient-getnextpacketsize)
- [GetPosition](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getposition)
- [GetFrequency](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getfrequency)

Reviewed SHA256, paths relative apps/windows:

```text
f3fb5d7da410b22d1f56e72093142de68e677aee58a77a0ed1a115c9020b74a1 RecApp/Audio/WasapiCaptureWorker.h
93a69fe35f505eabab19617b9ca6c448e93621e1cef69d81db5da839f82bd990 RecApp/Audio/WasapiCaptureWorker.cpp
055f7263011b8d554b57bec3477aa663f6df8c1c7576c5e9146e71d21fdff0fb RecApp/Capture/WindowsCaptureSessionController.h
f1e21f50bc2ba1ef2e54df0f9d0c92ac8f489993d7d225d1cd49cfed93717125 RecApp/Capture/WindowsCaptureSessionController.cpp
0955d5d2ed366e1f4843018d05a31b52ab0f1b76358c012fe8c6cbeaa6a78f48 RecApp/Audio/ClockMapper.h
3a2e325a72542070e670c0446ad42694f0951a0f0915aec0b39af20a4d555827 RecApp/Audio/ClockMapper.cpp
df1ecbeae057311944fca2b64cead721389c93de701fe95a32ffefa995b41d51 RecApp/Audio/AudioNormalizer.cpp
2fe2437d3f3f03e9850b6fad7c49a1464c79fe40c33059c20e3e393da381687a RecApp/Audio/RecordingAudioTimeline.cpp
2b46a0a3281da918ecaede370a7e14a2d760a29ba01c4dee416fcda8f3f8b25b Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp
6347083384e8628d9f49a9b729a14fc3e574a39b566f7fd9b1c7960531d5b037 RecApp/Recording/NativeCapture.h
```

Mac source SHA256: PrivacySuppressingSampleSource.swift ca8d3b86defb99d1945d18cc81795c0f528cfdbcc9add3ddea591caea920cd32;
RecordingSampleSources.swift dd851b69c5c41ffd27295a5ab0b3725f9debb8c1108a480ab31488f705210af5.
Только append own report; VM/audio/build/tests/code/norm/tasks/Git/GitHub не
трогались. Ни T120/full parity GO, ни фактический leak, ни причина старых
AAC47/56 не установлены. Следующий минимальный шаг — test-only consumer RED
и предъявленный finite-source-proof protocol, не немедленный product patch.

## 2026-10-21 / T120: scalar source-prefix normalizer prerequisite — technical qualification

Независимая узкая проверка предложения, не actual diff/source/runtime GO.
Authoritative worktree прежний; HEAD лично сверён:
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Lane high-risk-product,
existing T120. Production/controller/native frontier не принимаются.

### Requirements/checklist/scoped analyze

Лично перечитаны spec Session2026-10-04, FR-002/009/010, desktop §3,
plan T120, quickstart §15 и T120 tasks.md:602; constitution capture/control/
Spec Kit gates, current AudioTypes/AudioNormalizer и существующий
privacyResamplerBoundary. Использованы speckit-analyze и code-reviewer.
Анализ выполнен read-only; это последующее отдельно разрешённое reviewer
дополнение, не запись нормативов командой analyze. before/after_analyze
enabled hooks:0/0. Установленный prerequisite script не имеет --require-spec
(--help проверен); поддерживаемый --json --require-tasks --include-tasks
подтвердил F200, spec существует и прочитан.

Requirements-quality/scoped cross-artifact **GO: CRITICAL0/HIGH0**.
FR-002/009/010 покрыты существующим T120; новый scalar не wire/schema,
не новый capture owner и не новый продуктовый выбор. Desktop §3 пп2/5,
plan шаги1/2 и quickstart «Частичные данные»/«Неверные данные» прямо требуют
необратимое prefix suppression при сохранённом suffix и исходной валидации.
Отдельного изменения spec/plan/tasks для этого prerequisite не требуется.
Не расширять этот вывод на native snapshot/handshake или durable integration.

Перечитаны все критерии privacy-pause:12 checked/0 unchecked и audio-capture:
24/0; требования общего checklist requirements:22/0 сохраняются в данном
срезе. Применимы privacy CHK003/006/011/012, audio CHK005–014/023/024;
security diagnostics/egress/platform gates не ослабляются. Механический
подсчёт всей папки:198 Markdown files,477 checked/0 unchecked; это не новое
семантическое подтверждение всех198 файлов. Ни одна отметка не изменена.

### Единственный blocker предложенной конструкции: H-PREFIX-TAIL

**Construction NO-GO: CRITICAL0/HIGH1 до явного сохранения tail provenance.**
`AudioNormalizer.cpp:56–57,117–124,140–142`: прежний deferred index -1
защищён previousMicrophoneSuppressed_, но этот признак сейчас запоминает
только whole-batch/odd suppression. Одного previousSample_=0 недостаточно.

Контрпример по исходникам (не выполненный тест):44.1kHz,441 source frames,
even epoch2, whole=false, prefix=441. Первый batch оставляет deferred position
440.08125; в следующем batch той же epoch, prefix=0, fresh sample0.5 это
index=-1. Если previousMicrophoneSuppressed_ остался false, interpolation
выдаёт около0.040625 вместо0 для позиции старого полностью подавленного
хвоста. Добавление только current prefix>0 в suppressTail этого не закрывает.
Это пробел нового предложения, не утверждение о наблюдённой утечке продукта.

Минимальное условие исправления проекта: сохранять в существующем tail-state
признак последнего исходного кадра, то есть microphone &&
(wholeSuppressed || prefix==sourceFrames), и использовать его в следующем
suppressTail. Не переносить prefix>0 как признак всего предыдущего batch:
при 0<prefix<sourceFrames последний source sample и будущий tail остаются
достоверным suffix. Output.microphoneSuppressed остаётся только whole/odd;
tail-state не должен превращать частичный output в blanket-suppressed batch.
Новый owner/API/очередь или сброс фазы для этого не нужны.

Остальная предложенная семантика согласована: microphone prefix<=sourceFrames
после format/count и до zero; все raw finite/clock/route checks сохраняются;
system игнорирует microphone flags/prefix; mono zero до resampling; позиции
внутри prefix целиком0 без zero/fresh blend; native48k меняет только prefix;
output prefix0 как уже использованная input-coordinate metadata. Сохранить
default0 и совместимость aggregate callers, текущие bounds/count/PTS/phase.

Минимальная будущая проверка:48k prefix0/1/n-1/n/n+1 и preserved suffix;
44.1k inner-boundary interpolation плюс full-prefix→fresh при той же even
epoch (обязательный контрпример выше); partial-prefix→следующий fresh не
теряет валидный tail; NaN/Inf внутри/вне prefix и sticky refusal; system
flags/prefix ignored. Реюз существующего AudioNormalizerTests, не новый стенд.
Actual source gate и meaningful tests-first/runtime evidence ещё обязательны.
Unread consumer RED не должен становиться GREEN только от этого scalar:
native frontier ещё никто не публикует. T116/T120/full parity остаются OPEN.

### Точный прочитанный снимок SHA-256

```text
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 .specify/memory/constitution.md
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 specs/200-windows-desktop-app/spec.md
b2ef96a6c47eca3212f5e5a6d34f50529c8f0ab3aeb83a9126bf664ab8b4b9d3 specs/200-windows-desktop-app/plan.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f specs/200-windows-desktop-app/tasks.md
72b13fd5e8ded373b2b0e418e139b5566ac23f0d466d174c0302de7a1011391f specs/200-windows-desktop-app/quickstart.md
8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4 specs/200-windows-desktop-app/contracts/windows-desktop-contract.md
5e1c0a89ebb33f47876fafd345972e3e627e6597504d6b6a5dc4c8ac1ab10eec specs/200-windows-desktop-app/checklists/privacy-pause.md
7ca397eb7957c5bee3ca5910db07b939bc137d433a4b68217876af5bc59e3e23 apps/windows/RecApp/Audio/AudioTypes.h
df1ecbeae057311944fca2b64cead721389c93de701fe95a32ffefa995b41d51 apps/windows/RecApp/Audio/AudioNormalizer.cpp
d03ff9512ee45f82d31fbf5f36ff786a0b170046e03d38d76405d06805f94bc7 apps/windows/RecApp/Audio/AudioNormalizer.h
8ee08cbbfe96a468f19e666aa58ade825253c4b22dae0a72fe70f7adb50eb28a apps/windows/Tests/GrafWindowsCoreTests/AudioNormalizerTests.cpp
```

Записан только этот append own report. Код/нормы/tasks/markers/VM/build/tests/
Git/GitHub state не изменялись. Новый запрос пользователю не требуется:
H-PREFIX-TAIL — техническая полнота конструкции, не продуктовая неоднозначность.

Readback после append: нормативные SHA и AudioNormalizer.cpp прежние;
AudioTypes.h параллельно изменён другим участником: новый SHA
`fe07d0278f18f16a32d913d919e2abd900a91ea0d1d051c7371a07f41ba79080`,
добавлен input-only uint32 prefix default0. Его включение в будущий actual
diff не принято этим requirements review; таблица выше описывает исходный
прочитанный снимок. Reviewer этот source не менял. Report diff whitespace check PASS.

## 2026-10-21 / T120: actual scalar-prefix source follow-up — H-PREFIX-TAIL CLOSED

Узкий actual source review по code-reviewer, только AudioTypes.h,
AudioNormalizer.cpp и AudioNormalizerTests.cpp. Требования из предыдущего
дополнения не переоценивались целиком; прежний construction NO-GO сохранён
как историческое замечание к предложению, не к этому исправленному снимку.

**SOURCE GO: CRITICAL0/HIGH0/MEDIUM0; H-PREFIX-TAIL закрыт исходниками.**

- AudioNormalizer.cpp:108/151 в ОБОИХ native48/resampling выходах сохраняет
  `previousMicrophoneSuppressed_ = suppressed || suppressedPrefix == sourceFrames`.
  sourceFrames уже строго положителен. Для system suppressed=false/prefix0,
  поэтому этот tail-state не превращает system в microphone suppression.
- :61–62 и122–129 используют сохранённый tail-state; full-prefix→fresh в
  одной even epoch больше не смешивает deferred old zero со свежим голосом.
  При частичном prefix last mono sample и tail-state сохраняют fresh suffix.
- :27–38 проверяет ВСЕ raw finite до prefix error/zero, microphone prefix>count
  даёт sticky failure; system prefix игнорируется. Остальные format/route/QPC/
  count/bounds проверки остаются до подавления. :65 обнуляет mono до resampler;
  :134–141 не разрешает позиции внутри prefix заимствовать свежего соседа.
- Output :13 обнулён, prefix не переносится в output (input-coordinate only).
  :83 сохраняет только whole/odd microphoneSuppressed. Native48 не меняет
  sample count/phase и передаёт untouched suffix; расчёт PTS и лимиты прежние.
  Поле uint32 default0 добавлено в конец aggregate, прежние позиции не сдвинуты.
  Реальный caller WasapiCaptureWorker.cpp:398 по-прежнему проходит normalize;
  producer frontier/control/native acquisition patch этими тремя файлами не задан.
- privacyPartialPrefix:135–215 имеет160 положительных комбинаций:
  4rates(8k/44.1k/48k/192k)×2channels×2partitions×2sources×5prefix lengths.
  :151 фиксирует epoch2 во ВСЕХ трёх стадиях. Полный prefix и partial prefix
  в средней стадии с последующей fresh стадией проверяются как whole batch,
  так и one-frame partitions. Поэтому прежний H1 не скрывается сменой epoch.
  Oracle :174–179 основан на source-coordinate left position, не сравнении
  с ошибочным округлённым output prefix. Reference без prefix проверяет fresh
  values/PTS/count; scalar output0, offsets/route/domain/mono48k также проверены.
-16 negative cases включают prefix481>480, NaN/Inf внутри prefix, NaN в
  fresh suffix, format/route/domain/discontinuity до/после startup, empty output
  и последующий sticky refusal. System UINT32_MAX prefix заведомо игнорируется.
  #undef NDEBUG сохранён. Default CLI выполняет новый case до прежней матрицы;
  --privacy-prefix ограничивает запуск новым case, не выдаёт его за full suite.

Lean/minimal: один scalar, существующий mono/resampler/tail-state, никаких
новых очередей/owner/API/зависимостей. Новых actionable findings не обнаружено.
Достаточность runtime ещё не выдана: host RED179/host exit0 и source216
`63fae10e816fc005403783f243b7448a5cbae9ead16b9d9261125247768bbb0e`
сообщены main, самостоятельно по saved artifacts здесь не квалифицированы.
Native session46892 остаётся live по сообщению main; reviewer её/логи/VM
не проверял. Unread RED не закрывается этим prerequisite: producer ещё не
публикует frontier, полный T120/T116/installed/hardware/release остаются OPEN.

Лично сверенные SHA-256 actual трёх файлов:

```text
fe07d0278f18f16a32d913d919e2abd900a91ea0d1d051c7371a07f41ba79080 apps/windows/RecApp/Audio/AudioTypes.h
0fb6450791f7ffc51ffa2d8d7ab03ba59ef0e045bfe742df7b5ca5fcc1f116eb apps/windows/RecApp/Audio/AudioNormalizer.cpp
47c055bcd3655077d47382fe771b3a894d76a54b87d00a7ac7e92ab4a765b00a apps/windows/Tests/GrafWindowsCoreTests/AudioNormalizerTests.cpp
```

Только append own report; исходники/нормы/tasks/checklist markers/VM/build/
tests/Git/GitHub state не менялись. H1 снят только для указанных exact hashes.

## 2026-10-21 / T120: нормативный gate same-stream two-phase Resume

**Scoped requirements/analyze GO: CRITICAL0/HIGH0.** Проверены точный
technical append plan:1652–1696 и validation row quickstart:551, не весь
накопленный implementation/runtime audit. Lane: существующий high-risk-product
T120; reviewer выполняет read-only analyze, затем отдельно разрешённый append
только этого отчёта. Нового продуктового уточнения или задачи не требуется.

Сопоставление с согласованной конструкцией:

- Один mailbox/seq/expectedOdd/deadline и два этапа READY/ACK; callback только
  dispatcher, worker не хранит callback controller. Порядок блокировок,
  обслуживание после consumePacket/ReleaseBuffer, WAIT_TIMEOUT и непрерывной
  FIFO описаны. Нет drain-until-empty, второго capture owner или audio queue.
- Same-client/stream format/frequency, exact S_OK и paired QPC bracket с одним
  QPC tick/rounding; прежний drift envelope не используется как новый допуск.
  B=floor(p*r/f)+1, НЕ Bupper; арифметика checked, p monotonic и released end
  проверяются без max-repair. Логическая семантика API отделена от hardware proof.
- Exact expected epoch/deadline/Stop/fault проверяются внутри admission fence.
  Epoch commit необратим для accepted; исключение освобождает READY с fatal
  Stop. Seq защищает retry той же odd epoch; candidate отклонённой попытки
  деактивируется. Все CV waits имеют исходный absolute deadline; Stop не ждёт
  resumeMutex. Deadline1s — срок допуска, не гарантия прерывания COM/mutex.
- Receipt system/steady взят после native measurement до READY. OPEN/CLOSE
  используют ОДИН existing floor-to-ms: прежнее ceil-предложение исключено,
  последовательные исходные monotonic timestamps не инвертируются. Это не
  физическая верхняя граница serialized ms и не QPC–wall калибровка; PTS прежние.
- Сохраняются acquired-epoch/dispatcher/timeline guards и input-prefix путь.
  Quickstart добавляет native refusal/retry/Stop/exception/late accepted и
  быстрые OPEN/CLOSE, не заменяет прежние OPEN/CLOSE/storage/installed gates.

Privacy checklist перечитан полностью: **12 checked / 0 unchecked**.
CHK001–006 поддержаны spec FR-002/009/010, Session 2026-10-04, desktop §3 и
новым планом; CHK007–010 — прежними защищёнными metadata/T116/64KiB/legacy
требованиями, которые append не меняет; CHK011–012 — single owner/Stop/late
completion и явно отдельными source/runtime/installed/hardware gates.
Markers и notes checklist не изменялись.

Scoped coverage: FR-002/009/010 и SC-002/004 остаются покрыты существующим T120;
защищённая интеграция зависит от T116, а не новой задачи. Unmapped work,
новых противоречий/неясностей, нарушений конституции I/II/III/VI/VII в delta
не найдено. Это не full-feature analyze и не live issue-sync qualification.

Prerequisites: локальный скрипт отверг --require-spec; --help подтвердил его
отсутствие. Поддерживаемый --json --require-tasks --include-tasks успешно
подтвердил активный feature dir; spec.md прочитан явно. extensions.yml разобран
как YAML: before_analyze/after_analyze auto-commit hooks enabled=false,
исполняемых hooks нет. Никаких Git/VM/build/test действий не выполнялось.

Лично сверенные нормативные SHA-256:

```text
f3009717a5763a74b6207448f83496af1d5db9e1f48b360f5faf59aea7977bd2 plan.md
be5ad099a424e5d70d41721fc0fedeca59566e07885201cceb9298a5ce5625dc quickstart.md
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 spec.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f tasks.md
8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4 contracts/windows-desktop-contract.md
a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490 contracts/windows-protected-local-custody.md
5e1c0a89ebb33f47876fafd345972e3e627e6597504d6b6a5dc4c8ac1ab10eec checklists/privacy-pause.md
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 .specify/memory/constitution.md
```

Разрешён следующий минимальный production candidate с отдельным actual SOURCE
gate до runtime. Сам patch этим отчётом не проверен. Прежний unread RED,
T116/T120 и hardware/SC-003/installed/release acceptance не закрыты.

## 2026-10-21 / T120: actual SOURCE gate two-phase worker/controller Resume

**Scoped production SOURCE GO: CRITICAL0/HIGH0.** code-reviewer: лично прочитаны
WasapiCaptureWorker.cpp/.h и WindowsCaptureSessionController.cpp/.h, все
production consumers resumeFrame/acceptedResumeSerial и связанные synthetic
mailbox seams. Это actual current-source review против принятого plan:1652+,
не Git diff/merge review и не проверка runtime. Четыре production SHA ниже
повторно совпали в конце чтения; plan SHA также совпал с нормативным gate.

- Worker.cpp:226–267 использует capture/clock одного client и тот же фактический
  format/frequency. QPC bracketing, checked counter conversion, one-tick+round
  tolerance, receipt после native measurement не меняют packet PTS. Функции
  native readClock/release созданы до Start/GetBuffer; COM остаётся на worker.
- :281–301 обслуживает mailbox до GetBuffer, включая следующую итерацию после
  WAIT_TIMEOUT и каждый пакет непрерывной FIFO. Предыдущий consumePacket уже
  завершён; outstanding COM buffer не удерживается в ожидании READY/ACK.
- :372–405 dispatcher ждёт с отпущенным resumeMutex, без capture/dispatch
  locks. Callback исполняется локально под resumeMutex, не сохраняется worker.
  Даже если callback вернулся после deadline, true сохраняется accepted (:403).
  Исключение публикует rejected/notify, ставит worker error и пробрасывается;
  Controller:195–197 и515–518 закрывают admission/останавливают workers.
- :408–459 late clock result проверяет matching seq/status до effects. До READY
  проверены expected odd, deadline, S_OK, actual f/r, monotonic p, QPC bracket,
  overflow и B>=releasedEnd. B/expectedEven/serial установлены только worker.
  Reject очищает только соответствующий candidate, не вмешивается в новый seq.
- acceptedResumeSerial читается/пишется только под resumeMutex (:403/:457).
  Его проверка ПЕРЕД clear/reject сохраняет принятую границу, если dispatcher
  уже записал следующий pending seq до пробуждения worker. Новую границу
  установить может лишь тот же worker после возврата из старого service call;
  следующий accepted serial не может обогнать этот возврат. Serial не обнуляется
  при start, overflow отклоняется; stale accepted не совпадёт с новым request.
- resumeFrame consumers :542–545 применяют prefix только к matching acquired
  even epoch, вычитают лишь при B>D и ограничивают count. :493 проверяет packet
  exclusive-end overflow; :537 release предшествует normalize; raw finite и
  старые whole/odd/acquired guards сохраняются. Normalizer получает исходные
  координаты, output count/PTS не сдвигаются. :557–560 обновляет native baseline
  только после успешных mapping/release/normalize. Boundary не удаляется после
  первого старого пакета: несколько unread packets остаются подавленными.
- Worker-only frame/baseline fields не имеют concurrent dispatcher writes;
  start:612–620 сбрасывает их после join старого worker. Stop:660–663 не берёт
  resumeMutex. Оба CV waits используют исходный deadline и running/seq/status;
  потерянный Stop notify ограничен сроком, не является обещанием немедленного
  wake. Completion/error paths :636–648 notify; teardown join удерживает owners.
- Controller:144–158 сохраняет порядок resume→capture→dispatch, exact epoch и
  deadline проверяются внутри Stop fence перед epoch store. ProcessBatch
  capture→dispatch и enqueue dispatch не берут resumeMutex; обратного нового
  пути блокировок не найдено. ProcessPrivacy исполняется вне dispatchMutex.
- Controller:178–188 получает wall/steady из receipt до apply и CLOSE, не
  использует время UI ACK. :102–117 одинаковый duration_cast floor для OPEN/
  CLOSE с прежним recording origin. Stop/completion state guards не дают
  позднему Resume вернуть stopping session в recording. OPEN/CLOSE I/O остаётся
  на dispatcher; best-effort storage/fatal gates и EOS/finalizer не заменены.

CaptureFaultStateTests:225–249/815–915 действительно вызывает private service
реального mailbox из synthetic acquisition thread и public Resume через
dispatcher, затем consumePacket/normalizer/timeline; не выдаёт peer.boundary
за доказательство native frontier. Это чтение причинности, НЕ runtime PASS.
Тестовый файл параллельно изменялся: начальный SHA5afd8044… сменился на
69e2a30a… при повторном чтении. Его полный actual test diff и вся новая
отказная/race матрица этим production SOURCE GO не принимаются.

Проверенные стабильные production SHA-256:

```text
ecf010a71c9e5433da1fb0be7073747aeecf88634e14e88877ac490831a6a970 apps/windows/RecApp/Audio/WasapiCaptureWorker.cpp
0d5711205cc9316ec7808fdcb4840961ff720e2e4f4d3fd5a8c24fd1e506ec6c apps/windows/RecApp/Audio/WasapiCaptureWorker.h
ed28dfbf508a05ef0adde80d274c2978b44ccf6ecc64f692c368269c5968c23a apps/windows/RecApp/Capture/WindowsCaptureSessionController.cpp
a3e3a802bab532a09f9b501dea43e80fc6ebde466f57823effe7a268a51bfc75 apps/windows/RecApp/Capture/WindowsCaptureSessionController.h
f3009717a5763a74b6207448f83496af1d5db9e1f48b360f5faf59aea7977bd2 specs/200-windows-desktop-app/plan.md
```

Нужна отдельная validation на замороженном source/tests: unread/partial,
same-odd retry/late result, native refusals, Stop по обе стороны epoch commit,
exception и accepted после срока, быстрые OPEN/CLOSE. Сборки main/live logs не
просматривались. Нет hardware/physical clock proof, installed/release или
полного T120/T116 GO; прежний runtime RED не закрыт данным source review.
Изменён только этот report append; code/norm/tasks/checklist/VM/Git/GitHub
не менялись, собственных сборок/тестов reviewer не запускал.

## 2026-10-21 / T120: reason-race catch и frozen Resume test matrix

Узкий actual SOURCE review по code-reviewer: **GO для controller catch и
запуска предъявленного synthetic candidate; C0/H0, два M/P2 ограничения
покрытия ниже**. Это не GO полной race-матрице, runtime или закрытию T120.
Production worker не менялся относительно предыдущего SOURCE GO. Нормативную
базу, старые runtime и всю фичу повторно не принимал.

Controller.cpp:181–188 теперь перехватывает исключение applyPrivacyBoundary
непосредственно внутри dispatcher callback и делает latchFault(finalizationFailed)
ДО rethrow в Worker.cpp:394–400, где публикуется defensive initializationFailed.
Это правильное место: exception handler applyPrivacyBoundary уже отпустил
captureMutex/dispatchMutex; latchFault (:579–582) только atomic CAS, не берёт
новых locks и не перезаписывает ранее принятую причину. Далее прежние rejected/
notify/rethrow и processPrivacy catch сохраняют остановку и completion.
pollHealth может завершить начатое ранее чтение worker health с промежуточной
локальной source reason, но уже сохранённый finalizationFailed нельзя заменить
его CAS. finishStop:340–366 ждёт workers/dispatcher и затем заново получает
captureFailureReason с приоритетом captureFault. Поэтому найденный финализатором
ReasonCode3 из defensive worker error данным порядком устраняется по source;
это не утверждение об уже пройденном runtime нового SHA.

Tests.cpp:1226–1280: 12 отказов идут через public Pause/Resume, реальный mailbox
и service worker, а не прямую смену epoch. Проверяются S_FALSE, обе стороны QPC
bracket, backward position, mismatch frequency/rate, обратный bracket, нулевая
tolerance, старый steady receipt, B позади released end, quotient overflow и
throw clock provider. Для каждого — paused/no CLOSE, затем валидный retry на
том же odd epoch и EOS/finalizer. Helper :234–254 подменяет только acquisition/
clock; initial packet проходит consumePacket и задаёт actual native baseline.

Tests.cpp:1329–1371 mode2 вызывает исключение именно из pause handler после
epoch store, finalizer обязан получить finalizationFailed, а не ослабленный
набор допустимых причин. Modes0/1 удерживают handler после commit за deadline
и проверяют завершение/Stop. Atomic barriers и join/completion fences сохраняют
время жизни captures; ослабления assertion или production limits не найдено.

Tests.cpp:815–917 и вызовы :1398–1400/:1416–1417 проверяют B1440 и B1200:
второй случай режет packet D960/N480 на 240 старых и 240 свежих frames. Выход
реального normalizer/dispatcher/timeline проверяется посэмплово с неизменными
PTS/system/mix; новые mic samples обязаны вернуться. Named suppression assert
идёт после four releases/four frames/four AEC, EOS3 и finalizer1. Это genuine
partial unread synthetic proof по source, не COM/hardware acceptance.

Ограничения покрытия, которые нельзя включать в последующий runtime claim:

1. **M1/P2 — LateClock не гарантирует ABA interleaving** (:1314–1316).
   controller.resume() лишь ставит async command; release старого clock call
   следует сразу и не ждёт, что dispatcher уже записал новый resumeSerial в
   mailbox. Scheduler может сначала вернуть старый rejected call, затем
   обработать второй запрос; reads==2/CLOSE1 тогда всё равно PASS. Следовательно
   тест доказывает late-after-timeout + retry, но не неизбежно ветку
   "late result при уже переиспользованном slot". Для доказательства последней
   нужен bounded test-only barrier/наблюдение факта новой mailbox submission
   до release старого clock, без sleep как замены synchronization и без нового
   production cancellation protocol. Нынешний comment не является таким proof.

2. **M2/P2 — CommittedAck mode0 не проверяет retained frontier consumer**
   (:1349/:1358–1364; helper :240–251). После delayed ACK synthetic device
   больше не подаёт packets, sink возвращает true без анализа samples. Удаление
   resumeFrame после срока могло бы сохранить recording/CLOSE/EOS и пройти
   этот тест. Тест подтверждает accepted control после deadline, но не всю
   фразу comment "не discard installed frontier". Минимальное усиление —
   после delayed accepted ACK провести old unread packet и fresh suffix через
   existing consume/normalizer path и проверить samples после EOS/finalizer;
   отдельный обычный unread1200 не сочетает эти два условия.

Эти M — границы доказательства тестов, не доказанные production дефекты и не
запрет текущей сборки. До заявления полного покрытия соответствующих races
нужно их устранить либо явно не включать эти branches в acceptance.
Отдельные компактные clock-math cases полезны для exact +1 overflow и
nonintegral p*r/f (текущий case10 покрывает quotient overflow, B1200 — точное
деление); новая инфраструктура или расширение задачи для этого не нужны.

Повторные SHA-256 в конце чтения совпали с началом:

```text
ecf010a71c9e5433da1fb0be7073747aeecf88634e14e88877ac490831a6a970 apps/windows/RecApp/Audio/WasapiCaptureWorker.cpp
8c6f50254786353661981b4674f5c89c2d43ec25549f338a37fa40aed4908ac9 apps/windows/RecApp/Capture/WindowsCaptureSessionController.cpp
5b7f4f52be59fb38596189d4e4f71bb9b86fa4bce6397f4b67cdf473ef479925 apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp
```

Изменён только собственный report append. VM/Git/GitHub, live build/logs,
сборки/тесты, code/norm/tasks/checklist markers reviewer не трогал. Runtime
вердикта, native-clock/hardware proof и полного T120 acceptance здесь нет.

## 2026-10-21 / T120 native2: delta SOURCE GO, M1/M2 закрыты по source

code-reviewer, только frozen native2 delta против сохранённого native1, без
повторного normative/full audit. **SOURCE GO C0/H0; M1/M2 предыдущего review
закрыты на уровне конструкции теста**, runtime ещё не квалифицирован.

- Worker.cpp:372–375 / .h:106: private resumeRequestSerial читает только scalar
  под существующим resumeMutex; friend peer делегирует query. Новых callbacks,
  atomic/ownership протоколов нет. LateClock:1321–1325 ждёт serial>oldSerial
  ДО release старого readClock. Dispatcher уже записал pending нового запроса
  и отпустил mutex на CV wait, старый native callback всё ещё held; worker
  проверяет serial при возвращении. Это устраняет M1: нужное переиспользование
  slot больше не зависит от удачной очередности scheduler. Старый clock читает
  вне mutex, поэтому query не образует цикл ожидания с release.
- Tests:835–837/867/1408–1410/1426–1428: delayedAck=true в реальном unread
  consumer удерживает handler после epoch commit 1100ms, дольше admission
  deadline. После Resume старые и свежие packets проходят consume/normalizer/
  timeline. Прежние assertions output/system/PTS/AEC/releases/EOS/finalizer и
  возврата fresh mic сохранены, suppression assert после terminal fences.
  Ошибочное удаление B после позднего принятого ACK теперь наблюдаемо через
  nonzero old mic; M2 закрыт. Это test delay, не изменение production deadline.
- Native sample p=boundary*8-1 при f384000/r48000 даёт frame coordinate
  boundary-1/8, следовательно floor+1 ровно boundary. Это положительный
  fractional случай; ceil+1 дал бы boundary+1 и нарушил бы preserved fresh
  sample assertion. Для unread B1200 сохраняется partial240/240; последующий
  packet clock p1440*8 >= native sample, monotonic gate не обходится.
- Case12: initial f=r8000/p479 задаёт настоящий matched baseline; bad p=UINT64_MAX
  не переполняет quotient*rate+fraction (сумма ровно MAX), но переполняет только
  заключительный +1. Ранее стоящие gates valid, поэтому это именно целевой
  отказ, затем прежние paused/no CLOSE/retry/EOS/finalizer. Старые12 cases и
  committed/exception assertions не ослаблены, итоговый count теперь13.

Manifest SHA e423d851175b3acae4e4986526b4e9f553dbe653dd7e06ca9af756389b43cf71
проверен; все216 current inputs совпали с manifest. Frozen copies трёх
изменённых файлов совпали с current hashes:

```text
cc216ad32e39e6abb12e8a81268809e2714ec6e84ea445dba48af6e328c506af apps/windows/RecApp/Audio/WasapiCaptureWorker.cpp
79cc4a9b0cfbcef5d2442db18e9672719dac74e8f2ad86c60e33d7813779fe99 apps/windows/RecApp/Audio/WasapiCaptureWorker.h
5b6ba93c7f7a18f4950a51642043d95a8e5ae6f13157e7b383f4cdff7f80945c apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp
```

Controller.cpp 8c6f50254786353661981b4674f5c89c2d43ec25549f338a37fa40aed4908ac9
с прежним reason-race catch сохранён. SOURCE разрешает следующий scoped
runtime, не заменяет его и не закрывает T120. Native1 execution не утверждается.
Изменён только этот report; VM/build/tests/Git/GitHub/code/norm/markers не тронуты.

## 2026-10-21 / T120 native3: one-line qualification SOURCE GO

Узкий code-reviewer line check: **GO C0/H0**. Diff native2 frozen test →
native3/current ровно одна строка Tests.cpp:237: default-argument lambda
вызывает CaptureSessionTestPeer::resumeSample() вместо unqualified resumeSample().
Это явно выбирает ту же static member function и сохраняет default values,
callback signature, matrix/assertions/synchronization. Других изменений в
test diff нет; native3 changed.json содержит только этот test TU.

Native3 manifest SHA45c9b7e02d3103260515f7161be45af4baa01b8300d559ea666e935951b6438c;
все216 current inputs совпали с manifest, frozen/current test одинаковы:
a3066e2ec5c2259e88fe3ba3ead49970e363e8750d5cff685210c3a41c5b25ad.
Production inputs и прежний M1/M2 SOURCE вывод не меняются. Native2 BUILD1/
C3861/owned0 сообщён main; здесь не выполнялась независимая runtime/log
квалификация, BUILD failure не переименовывается в runtime RED или PASS.
Нативный результат native3 остаётся неизвестным до отдельного terminal receipt.
Изменён только собственный report; VM/build/tests/Git/code/norm не тронуты.

## 2026-10-21 / T120 native3: bounded ponytail-review

Полностью прочитан plugin4.9.0 ponytail-review/SKILL.md. Только complexity
текущего handshake/prefix consumer/receipt и новых synthetic helpers/guards/
unread, не весь accumulated diff. Все216 inputs совпали с frozen native3
manifest45c9b7e02d3103260515f7161be45af4baa01b8300d559ea666e935951b6438c.
VM/runtime/live logs не читались. Две необязательные локальные рекомендации:

- WasapiCaptureWorker.cpp:L110/L453/L463: delete: resumeFrameSerial дублирует локальный serial единственного acquisition worker; убрать поле/assignment, заменить conditional reset обычным resumeFrame.reset() ПОСЛЕ существующего acceptedResumeSerial early return (−1 строка, −1 scalar).
- WindowsCaptureSessionController.cpp:L192–198: shrink: if(completion.applied) уже доказан выходом !applied на L191; раскрыть только эту обёртку, оставить весь CLOSE/fatal/completion body (−2 строки).

Основание первого: resumeFrame и его serial записывает только servicePrivacyResume
единственного worker. На пути к ACK wait текущий вызов уже установил свой frame;
во время wait dispatcher меняет mailbox request/status/acceptedSerial, но не
frame. Новый pending request не может установить следующий frame до возврата
того же worker из текущего service call. start reset возможен только после join.
Таким образом сравнение frameSerial==local serial здесь всегда true. Это НЕ
основание удалять acceptedResumeSerial: он сохраняет irrevocable ACK, когда
mailbox status уже заменён следующим pending request. Matching request serial
при late readClock и final reject также остаются обязательными.

Private resumeRequestSerial query оставлен для M1 evidence; receipt wall/steady
и expected epoch имеют разных потребителей. Prefix scalar/input coordinate,
whole/previous suppression и interpolation tail не дублируют друг друга.
Существующие std::mutex/CV/chrono/std::optional/std::min уже используются;
нового queue/framework/platform dependency нет. Native readClock/actual format
guards не заменять приблизительным helper или общей clock abstraction. Test
helpers reuse реальный consume/mailbox/thread lifecycle; 13 guards, delayedAck,
partial1200 и exception/Stop случаи проверяют разные обязательства и не являются
лишней гибкостью. Дополнительных обоснованных удалений в этой области не найдено.

Рекомендации не блокируют текущий native3, не применялись и не меняют прежний
SOURCE verdict. Любое последующее упрощение — новый exact-source diff с прежними
security/deadline/tests gates. Только этот report append; code/Git/VM/norm/tasks/
checklists не менялись, reviewer builds/tests не запускал. Не runtime/T120 GO.

net: -3 lines possible.

## 2026-10-21 / T120 native4: actual SOURCE gate Ponytail deletions

**GO C0/H0**, только предложенная delta, net−3 строки и−1 scalar. Проверены
actual frozen copies native4 against production hashes native3. Native3 stage
sparse, поэтому before bytes взяты из native2 copies, чьи SHA точно равны
записям native3 manifest (worker cc216ad3…, controller8c6f5025…). Diff содержит
только resumeFrameSerial field/store/conditional-reset и раскрытие CLOSE wrapper.

Worker:110/451–463: принятый serial по-прежнему возвращается ДО reset, поэтому
поздний принятый ACK сохраняет B даже при новом pending status. При rejected/
timeout выполняется reset лишь frame, установленного тем же вызовом до READY:
единственный worker не может установить новую границу до своего возврата.
Late clock до установки candidate по-прежнему проверяет matching seq/status и
возвращается без reset. Final reject условен matching current request serial;
новый request не перезаписывается. Start reset после join, consumer epoch guard,
acceptedResumeSerial, native checks/deadline и M1 private query не изменены.

Controller:191–196: !applied уже завершает функцию; оставшийся CLOSE body
исполняется при ровно прежнем условии, в прежнем порядке done=false/publish →
checkpoint → done=true → storage/fatal. Try/catch и time lifetime прежние.
Assertions/test source не менялись. Новых state/dependencies нет.

Manifest native4 SHA59ad0f4787682aa19fb7b30b5aa6297ad5b17dc6302b49a46fe8d1b29a34569c;
все216 current inputs совпали. changed.json ровно два production cpp. Current и
frozen copies совпали:

```text
179b33626ef1ca8f47c5599f2015c9ae0b3a231f7388c808a87099f463385415 apps/windows/RecApp/Audio/WasapiCaptureWorker.cpp
d18b771754dc443ec51afa180fbcd595a31717e0e803a7475e00e2d21222ee86 apps/windows/RecApp/Capture/WindowsCaptureSessionController.cpp
```

Разрешён следующий scoped run тех же groups, не runtime/T120 acceptance.
Сообщённые main/Fermat native3 7/7/terminal40641 здесь не переквалифицировались.
Изменён только report append, без VM/build/tests/Git/code/norm/markers действий.

## 2026-10-21 / T120 native4: saved scoped runtime qualification

**Scoped runtime GO: все7 direct CLI groups PASS после Ponytail cuts.**
Независимо полностью прочитаны result.json, UTF16LE build.log и все7 group logs
(async.log нулевой длины), source/prior manifests и changed.json. Это custom
direct-CLI runner, не CTest/JUnit: отсутствие XML не является потерянным test
receipt. Runner validate-t120-resume.ps1 SHA
6a24d2a52b4a4769314b43ae31c4005b5d49e3d1ef4c9f309f73b0e8d013b3f7
совпал с сообщённым main runner identity, его logic прочитан целиком.

Receipt: terminal=true, Debug, build0; normalizer/async/fifo/prefetch/unread/
resume-clock/full все exit0, executed_groups7, postflight216, owned_processes0;
failure отсутствует. Полный build log показывает успешную сборку двух targets,
включая пересборку изменённых WasapiCaptureWorker.cpp/Controller.cpp, без build
errors. Сообщённый transport handle7370 exit0 reviewer отдельно не запускал/
не опрашивал; saved receipt согласован с этим сообщением.

Доказательства содержимого групп:

- normalizer: privacy_prefix cases160 invalid16 и все16 комбинаций прежней
  resampler matrix microphone/system, 44100/48000, single/whole, paused0/1 —
  каждый correct1/audio1.
- fifo: все4 extracted0/1 × frames240/480 с suppressed1.
- prefetch: все6 hold_stage0/1/2 × acquired_paused0/1 с suppressed1.
- unread: B1440 и B1200, плюс B1440 delayed_ack1; в каждом releases4/frames4/
  aec4/eos3/finalizer1/old_suppressed1. Это сохраняет partial и late accepted
  ACK consumer proof после удаления resumeFrameSerial.
- resume-clock: rejected13/retry13/eos13/finalizer13; late retry1/stop1/
  late_epoch_commit0; accepted_after_deadline1/stop_after_commit1/throwing_handler1.
- async: пустой stdout/stderr соответствует трём вызываемым assert-based
  functions на --privacy-async; exit0 сохранён runner. Не выдумывается новый
  pass marker. Default/full отдельно вызывает эти же functions, затем все
  FIFO/prefetch/unread/clock cases и остальные default checks; полный log
  содержит все ожидаемые summaries и Native endpoint ID roundtrips2(no capture).

Runner точно вызывает AudioNormalizerTests default; CaptureFaultStateTests
--privacy-async/--privacy-fifo/--privacy-prefetch/--privacy-unread/
--privacy-resume-clock и default без args. Assertions сохраняются (#undef
NDEBUG в обоих test TU), CLI dispatch/calls не изменены. Skip/disabled/filter
в runner нет, отсутствующих CLI markers или abort/error в полных logs не найдено.
Это7 groups, НЕ7 индивидуальных CTests и не полная feature matrix.

Manifest59ad0f4787682aa19fb7b30b5aa6297ad5b17dc6302b49a46fe8d1b29a34569c
повторно подтверждён; все216 CURRENT inputs совпали. prior.sha256 побайтно
равен native3 source.sha256. Независимый manifest diff native3→4 ровно два cpp
(worker179b3362… и controllerd18b7717…), test/helper/header/normalizer hashes
не менялись. Saved changed.json согласован с этим, не только принят на веру.

Receipt PE SHA:

```text
AudioNormalizerTests 654d4da6063c6cb2318bd7599d45773fff12cf36e669e5dccf77633094863ce4
CaptureFaultStateTests 97afec6df09ddeaf4cf812c0d0062d3eba9fe125b9226f1dc2a6315962e1293d
```

Прочитанный runner вычисляет PE перед CLI и сравнивает после всех7 и source
postflight; failure отсутствует. Это сохранённый runner PE guard, не собственное
повторное GetHash reviewer в guest. Дополнительный actual guest GetHash main
ещё не представлен данным запросом — его независимая квалификация не выдумана.

Границы: receipt device_audio_read=false/real_network=false/installed=false;
synthetic device/clock + generated samples, full endpoint enumeration лишь
metadata(no capture), никакого actual microphone/native clock/hardware proof.
Это scoped функциональный runtime GO для frozen source после сокращений, не
T120 close, storage integration/protected-privacy-flow acceptance, installed
parity или release. Объявленный следующий as-is protected-privacy-flow RED не
исполнялся reviewer и не утверждается заранее; production Resume не ослаблялся.
Изменён только этот report append, без VM/build/tests/Git/GitHub/source/norm/
tasks/checklist действий. Предыдущие RED/BUILD failure evidence сохраняются.

## 2026-10-21 / T120: protected-privacy-flow requirements/scoped analyze gate

**GO C0/H0 для следующего existing T120 test-only интеграционного шага.**
Это requirements quality/scoped construction, НЕ approval ещё не предъявленного
diff и НЕ прогноз runtime as-is. High-risk active slice, не новый продуктовый
выбор/задача/нормативный контракт. T120 и зависимость T116 остаются OPEN.
Прочитан полностью speckit-analyze SKILL; анализ проведён read-only отдельно
от разрешённого ниже append собственного report. Hooks before/after analyze
disabled. Feature.json указывает F200/high-risk/b1eb3d5…; prerequisite --help
прочитан (--require-spec отсутствует); обычный prerequisite, использующий Git/
persisted context, не запускался из-за запрета Git. Нужные artifacts проверены
напрямую, live tracker sync не утверждается.

Прочитаны актуальные spec Session2026-10-04/FR002/009/010/SC002/004, plan T120
и same-stream technical amendment1652+, quickstart§15, desktop§3, T120/tasks
и применимые constitution I/II/III/VI/VII, guidance flow/product gates. Нет
конфликта product/spec→plan→task: защищённая интеграция уже явно входит в T120,
metadata/storage остаются T116. Новый test helper не меняет схему/владельца/
authority и не закрывает hardware/installed. Coverage scoped5/5 (3FR+2SC),
все имеют existing taskT120, storage dependencyT116; новых unmapped задач нет.
Конституционных/нормативных C/H findings0, blocking clarifications0.

Privacy12 перечитан целиком и повторно пересчитан: **12 checked/0 unchecked**.
Каждый quality criterion поддержан текущими norms, markers не менялись:

| CHK | Текущее основание |
| --- | --- |
| 001 | spec Session2026-10-04 закрепляет Mac F284 c8d67c… и FR002/009 |
| 002 | desktop§3.1/4, planT120.3/4: mandatory OPEN, best-effort CLOSE |
| 003 | desktop§3.2/5 и quickstart partial/FIFO: old pending/prefetched/timeline suppression без переписывания prefix |
| 004 | desktop§3.3 + plan1652+: producer/read ownership, checked B, prefix, no empty-FIFO wait |
| 005 | desktop§3.3 и quickstart unavailable: paused/OPEN/Stop при отказе boundary |
| 006 | FR009/010, desktop§3.5: system/PTS/count/format/route/AEC/raw validation без fallback |
| 007 | desktop§3.6, planT120.3, taskT120: protected T116, no plaintext journal |
| 008 | desktop§3.6 и specSession: existing logical v5, не новый JSON/clock format |
| 009 | desktop§3.6/7 и quickstart metadata row: full64KiB, прочие budgets неизменны |
| 010 | desktop§3.1/6: failed OPEN не принимает Pause/не режет историю |
| 011 | desktop§3.7, plan1652+: one writer, async Stop/admission/late completion fencing |
| 012 | quickstart§15 after table: codec/source/native/installed/hardware gates разделены |

Actual source gap fixture, не доказанная утечка и не requirements gap:
NativeCaptureStorageIntegrationTests.cpp:632–653 devices ставит только bodies
существующих workers; generatedProducer:3842–3863 создаёт AudioBatch и напрямую
вызывает callback:3857. Не вызывает consumePacket, не устанавливает stream f/r/
releasedEnd baseline и не обслуживает servicePrivacyResume. В конце frameCount
он только спит. CLI:6900–6903 включает privacyFlow для normal vertical path.
Controls:6225–6254 — public Pause, все3000frames во время paused, затем Resume
и второй Pause. Writer/checkpoint настоящие: NativeCapture.h:2985–3047 через
единственный controller/dispatcher вызывает timeline и pausePrivacy/closePrivacy,
проверяет writer status/healthy. Поэтому mock-ACK/fallback в production Resume
исправлял бы не ту сторону границы. As-is отказ на Resume совместим с source,
но actual terminal assertion/reason/cleanup ещё нужно квалифицировать отдельно.

Минимальная реалистичная test-only конструкция для следующего SOURCE gate:

1. Только privacyFlow-selective acquisition fixture; не переделывать все callers
   generatedProducer/прочие vertical cases. Через существующий friend peer и
   devices получить РЕАЛЬНЫЕ worker references после setEndpoints до Start;
   переиспользовать core packet/serviceResume delegation, не создавать второй
   worker/controller, production device adapter или epoch setter.
2. Один owned acquisition loop на worker: локальные ClockMapper/AudioNormalizer,
   generated finite samples/ClockObservation с согласованными D/N/qpc/p/f/r.
   Делегировать actual consumePacket с настоящим capturePrivacyEpoch snapshot
   и synthetic успешным ReleaseBuffer. Именно consumePacket вызывает existing
   production callback/enqueue; bare callback его не заменяет. До допустимого
   Resume нужен хотя бы один valid/released packet для actual stream baseline.
3. Microphone loop обслуживает реальный servicePrivacyResume между пакетами,
   в wait/backpressure/emit=false ветках и ПОСЛЕ последнего generated packet
   вплоть до Stop. Иначе нынешний Resume после frames3000 опять не получит READY.
   Synthetic clock возвращает matched frequency/rate, S_OK/fresh QPC bracket,
   actual steady/system receipt и p/B не позади releasedEnd. Не связывать QPC
   epoch с wall time, не max-repair и не fake production accepted result.
4. Test phases/barriers владеют generated source frontier и >=2 unread paused
   packets, а не пишут privacy epoch. Public NativeCapture Pause/Resume остаются
   единственным control path. Во время paused render продолжает существующий
   system path; consumer сохраняет PTS/count/format/route/AEC. Service не должен
   требовать UI lock, освобождения custody owner или пустой FIFO.
5. Нынешние3000frames/30s все до Resume подтверждают metadata CLOSE, но НЕ
   возврат fresh audio после него. Если заявляется end-to-end suppression proof,
   надо выделить внутри прежнего total generated interval trusted/paused/unread/
   partial/fresh phases и проверить canonical samples/system contribution после
   drain. Не дописывать extra frames незаметно, не выдавать metadata segment
   count за audio proof. Один короткий supplementary consumer slice допустим,
   но граница его acceptance должна быть явной, не заменять существующий flow.
6. Сохранить genuine checkpoint, два OPEN/CLOSE (второй закрывает Stop), EOS/
   finalizer/adoption, queue generation/IDs, no plaintext files, fresh cold
   inspect/hash/AAC/30s и exact memory/resources проверки. Existing native
   waits/timeouts/limits без увеличения. Failure не скрывать swallow/assert
   allowance. Closed segment count через substring — лишь дополнительный
   oracle; semantic inspectProtected остаётся обязательным и уже присутствует.

Минимальный helper поэтому меняет только synthetic device body и его barriers,
а не controller/writer/production policy. Отдельный actual diff перед GREEN;
новые нормативы/продуктовое clarification не требуются для этой конструкции.

Точные SHA текущего normative/source snapshot:

```text
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 .specify/memory/constitution.md
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 specs/200-windows-desktop-app/spec.md
f3009717a5763a74b6207448f83496af1d5db9e1f48b360f5faf59aea7977bd2 specs/200-windows-desktop-app/plan.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f specs/200-windows-desktop-app/tasks.md
be5ad099a424e5d70d41721fc0fedeca59566e07885201cceb9298a5ce5625dc specs/200-windows-desktop-app/quickstart.md
8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4 specs/200-windows-desktop-app/contracts/windows-desktop-contract.md
5e1c0a89ebb33f47876fafd345972e3e627e6597504d6b6a5dc4c8ac1ab10eec specs/200-windows-desktop-app/checklists/privacy-pause.md
fc85c594db6e82a7660b264a0dd58ef6cce4a74343733d73a66d229b5f4e655e apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp
6347083384e8628d9f49a9b729a14fc3e574a39b566f7fd9b1c7960531d5b037 apps/windows/RecApp/Recording/NativeCapture.h
```

Все216 current implementation inputs повторно совпали с frozen native4
59ad0f4787682aa19fb7b30b5aa6297ad5b17dc6302b49a46fe8d1b29a34569c.
Нормы unchanged; ни один checklist marker не изменён. Portable48/48 и новый
as-is live diagnostic здесь не переквалифицировались. Read-only analysis закончен
до append; изменён только этот reviewer report. Нет VM/tests/build/Git/GitHub,
code/norm/tasks/checklist writes или полного T120/T116 acceptance.

## 2026-10-21 / T120: повторный checklist/analyze/issue gate после обслуживания VM

**Scoped requirements GO: CRITICAL0 / HIGH0; прежний допуск следующего
test-only protected-privacy-flow шага сохраняется.** Это не новый SOURCE GO,
не квалификация as-is runtime и не закрытие T120/T116. Обслуживание VM и
свободное место сообщены main; reviewer их самостоятельно не проверял.
Живой `t120-protected-as-is1`/exec58700 и его журналы не открывались.

Повторно прочитаны project-local `speckit-implement` и `speckit-analyze`,
guidance index и применимые spec-kit-flow/product-gates. YAML extensions
успешно разобран: enabled hooks before_implement/before_analyze/after_analyze
отсутствуют; auto-commit не запускался. Feature pointer по-прежнему F200,
high-risk-product, codex/200-windows-followup, source_sha
b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1. Prerequisite/Git-команды не
исполнялись; наличие активных файлов и их точные hashes проверены напрямую.
Read-only cross-artifact analysis завершён отдельно до этой записи.

### Полный пересчёт каталога и чтение критериев

Весь каталог `checklists` проинвентаризован: **198 файлов**, из них **31 файл
с checkbox-пунктами**, **477 checked / 0 unchecked**. Лично перечитаны все
477 пунктов, включая собственные критерии старых source-review файлов;
privacy-pause перечитан целиком. Остальные167 файлов — отчёты/исследования/
analyze без checkbox: проверены их наличие и тематическая принадлежность;
их исторические runtime рассказы не переквалифицировались и не выдаются за
повторное полное чтение всех исторических журналов. Ни один файл не исключён
из механического подсчёта. Повторный readback дал те же counts и digest.

| Файл с пунктами (в checklists/) | Checked | Unchecked |
| --- | ---: | ---: |
| advanced-routing.md | 14 | 0 |
| audio-capture.md | 24 | 0 |
| calendar-launcher.md | 5 | 0 |
| calendar-operation.md | 8 | 0 |
| calendar-wire.md | 5 | 0 |
| cold-prefix-recovery.md | 47 | 0 |
| packed-writer.md | 12 | 0 |
| privacy-pause.md | 12 | 0 |
| requirements.md | 22 | 0 |
| review-2026-10-03-packed-tree-source.md | 38 | 0 |
| review-2026-10-04-calendar-join-gate.md | 12 | 0 |
| review-2026-10-04-calendar-resolver-gate.md | 12 | 0 |
| review-2026-10-04-calendar-url-gate.md | 12 | 0 |
| review-2026-10-04-manifest-cap-source.md | 9 | 0 |
| review-2026-10-04-packed-cadence-gate.md | 12 | 0 |
| review-2026-10-04-packed-cadence-source.md | 18 | 0 |
| review-2026-10-04-packed-live-writer-gate.md | 14 | 0 |
| review-2026-10-04-packed-live-writer-source.md | 9 | 0 |
| review-2026-10-04-packed-package-gate.md | 12 | 0 |
| review-2026-10-04-packed-reader-gate.md | 20 | 0 |
| review-2026-10-04-packed-reader-source.md | 9 | 0 |
| review-2026-10-04-packed-resize-gate.md | 14 | 0 |
| review-2026-10-04-packed-resize-source.md | 9 | 0 |
| review-2026-10-04-packed-rewrite-gate.md | 16 | 0 |
| review-2026-10-04-packed-rewrite-source.md | 9 | 0 |
| review-2026-10-04-packed-tail-gate.md | 14 | 0 |
| review-2026-10-04-packed-tail-source.md | 9 | 0 |
| review-2026-10-04-packed-writer-source.md | 18 | 0 |
| security.md | 27 | 0 |
| start-owner-recovery.md | 10 | 0 |
| ux.md | 25 | 0 |
| **Всего** | **477** | **0** |

Детерминированный inventory digest: SHA-256 конкатенации отсортированных по
полному относительному пути строк `sha256  path\n` для всех198 файлов:
`0ff59d9f2f9b55a38ff814a62343ba9666d194a17fc3b9e7bf06a30b7d82916f`.
Этот digest относится только к checklists/, не включает данный report.

Применимость: privacy12/audio/UX/security непосредственно ограничивают новый
capture fixture; packed/manifest/start-owner/cold-prefix сохраняют protected
OPEN/CLOSE, точную authority, leases, первый fault, ограничения ресурсов и
полную cold inspection. Calendar/URL/wire/routing сохраняются как неизменные
соседние границы, но этот шаг их не реализует и не принимает заново.
Исторические отметки source/runtime относятся к своим снимкам: их нельзя
переносить на новый protected-privacy-flow по одному нынешнему checked count.
Оснований менять checkbox markers не найдено; markers не менялись.

### Current analyze и владелец задачи

Свежо сопоставлены plan:1599–1697 (включая same-stream уточнение), quickstart
§15:534–574, desktop contract §3:75–116, FR-002/009/010, SC-002/004 и
tasks.md:602. Все5 применимых FR/SC имеют покрытие существующей T120;
durable часть явно зависит от T116. Противоречий constitution I/II/III/IV/VI/VII,
непокрытых требований или нового blocking clarification в этом scope нет.
Новых продуктовых решений/задач/порогов не требуется. Это scoped analyze,
не повторная полная приёмка всей Feature200.

Прямой read-only GitHub API `repos/yshishenya/graf/issues/7590` подтвердил:
OPEN, title `[200][P0][security] T120: Не возвращать микрофонные данные паузы
после возобновления записи`; labels feature:200 / priority:P0 / area:security /
gate:pr-blocker / type:bug. Body прямо владеет полным T120, связывает #7444,
текущую ветку/базовый HEAD и exact tasks SHA80fc15…; updated_at
2026-10-12T20:20:50Z. Assignees пусты: это task-backed issue owner, не
подтверждение назначения человеку. Условия закрытия остаются открытыми;
issue sync не изменялся и новый issue не создавался.

### Неизменные нормативные SHA-256

Все перечисленные значения совпали с ранее проверенными нормативами:

```text
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 .specify/memory/constitution.md
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 spec.md
f3009717a5763a74b6207448f83496af1d5db9e1f48b360f5faf59aea7977bd2 plan.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f tasks.md
be5ad099a424e5d70d41721fc0fedeca59566e07885201cceb9298a5ce5625dc quickstart.md
da53a2492e7cc0f1b058ab3d179718fab95aac8bf9957f33b8ff5f3a610bfe9d research.md
d61235b9454564897fdacfdecd127fc0a9676b48a2b2011b1b1df692fcf7db9b data-model.md
8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4 contracts/windows-desktop-contract.md
a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490 contracts/windows-protected-local-custody.md
e6af6d4d402c19fa47b8a71931f7573eb0c4673d3f19365926f78f140c65fc56 contracts/windows-protected-packed-custody.md
5e1c0a89ebb33f47876fafd345972e3e627e6597504d6b6a5dc4c8ac1ab10eec checklists/privacy-pause.md
```

### Identity caveat и точная граница GO

Замороженный native4 manifest имеет SHA
59ad0f4787682aa19fb7b30b5aa6297ad5b17dc6302b49a46fe8d1b29a34569c.
При текущем host readback совпали **215/216** inputs; единственное отличие —
`apps/windows/Tests/GrafWindowsContractTests/NativeCaptureStorageIntegrationTests.cpp`,
current SHA `11573c62b0108200855e5ee1b336d971db4a57fb800f222caf19b36b7bd7a6e7`
вместо frozen `fc85c594db6e82a7660b264a0dd58ef6cce4a74343733d73a66d229b5f4e655e`.
Это не normative drift и не finding против неизменного дизайна. Но нельзя
заявить current host216==native4 или выдать этот gate за SOURCE GO изменённого
test TU. Native4 stage sparse: полной before-копии этого TU в нём нет;
сравнение выполнено по manifest, не по выдуманному полному source diff.
Guest и состав живого as-is1 этим чтением не проверялись. Привязку его будущего
terminal результата следует делать к собственным saved source/receipt.

Допущен прежний минимальный путь realistic synthetic acquisition через
существующие worker.consumePacket + servicePrivacyResume, настоящий public
Pause/Resume и protected checkpoint, без fake ACK/epoch setter/production
fallback. Нужен отдельный actual SOURCE review перед исправленным runtime;
expected RED не становится actual RED до terminal receipt. Все требования
EOS/finalizer, privacy samples/system/PTS/AEC, OPEN/CLOSE, cold semantic
inspection и exact resources из предыдущего раздела сохранены.

Запись ограничена этим собственным отчётом. Нет VM/tests/build/Git mutation,
GitHub write, code/norm/tasks/checklist edits. T116/T120, installed/hardware/
release и старые AAC47/AAC56 ограничения не закрыты.

## 2026-10-21 / T120: shared native ResumeClockSample — construction gate

Scoped requirements/analyze: **C0/H0, GO** для сохранения поведения при
вынесении измерения и подготовки одной metadata-only пробы. Это не actual
SOURCE GO будущего diff, не разрешение считать native freshness доказанной и
не закрытие T120. Применены speckit-analyze и code-reviewer; анализ выполнен
read-only до этой разрешённой записи. Нового продуктового ответа, задачи,
порога точности или ослабления privacy12 не требуется.

### Проверенные входы и применимость

Повторно прочитаны текущие native sampler/guards и прежние внешние
`PairProbe.cpp`, `PairStats.h`, `Run-One.ps1`, `build.cmd` из
`/Users/yshishenya/Documents/graf-windows-followup-200/f200-clock-pair.LXFJPO`.
Сопоставлены plan:1652–1694, quickstart §15:534–573, privacy-pause (12/0),
применимые audio/security критерии, FR-018/021 и существующая T120:602.
Существующий gate остальных тематических checklist сохранён по неизменному
inventory: **198 файлов, 31 с checkbox, 477 checked / 0 unchecked**,
digest `0ff59d9f2f9b55a38ff814a62343ba9666d194a17fc3b9e7bf06a30b7d82916f`.
Checklist markers не менялись. Requirements quality не означает runtime PASS.
Read-only GitHub API подтвердил #7590 OPEN, T120/feature:200/P0/security/
pr-blocker; dependency T116/#7444 остаётся. Это не назначение issue человеку.

Нормативные SHA constitution/spec/plan/tasks/quickstart/privacy совпали с
предыдущим разделом; непосредственно перед записью повторно проверены:

```text
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 constitution
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 spec
f3009717a5763a74b6207448f83496af1d5db9e1f48b360f5faf59aea7977bd2 plan
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f tasks
be5ad099a424e5d70d41721fc0fedeca59566e07885201cceb9298a5ce5625dc quickstart
5e1c0a89ebb33f47876fafd345972e3e627e6597504d6b6a5dc4c8ac1ab10eec privacy-pause
79cc4a9b0cfbcef5d2442db18e9672719dac74e8f2ad86c60e33d7813779fe99 WasapiCaptureWorker.h
179b33626ef1ca8f47c5599f2015c9ae0b3a231f7388c808a87099f463385415 WasapiCaptureWorker.cpp
a7a08a0796491698fdde74618ac82d96caf365a42871ea4c8068ac59f89a0574 apps/windows/CMakeLists.txt
```

### Допущенная конструкция и обязательная поправка линковки

1. Private static `readResumeClockSample(::IAudioClock*, uint64 frequency,
   uint32 rate)` внутри существующих worker h/cpp, Windows-only; глобальный
   forward declaration IAudioClock также Windows-only. Уже существующий
   friend CaptureSessionTestPeer делегирует методу из external diagnostic.
   Native lambda вызывает этот же метод. Нового header/framework/public API
   не нужно. Тело cpp:250–269, `counter100ns`, порядок QPF/QPC-before/native/
   QPC-after, HRESULT, default failure, timepoints и rounding сохраняются.
   Не переносить сюда admission/epoch/READY/ACK и не задавать fake baseline.
2. **M1 / конкретная поправка external build:** current CMake:128 объявляет
   `graf_windows_common` как OBJECT, а :137 включает TARGET_OBJECTS в executable.
   Файл `graf_windows_common.lib` этим CMake не производится/не гарантируется.
   Поэтому буквальная команда линковки с такой .lib пока не подтверждена.
   Минимальный reuse — фактические объекты этой текущей Debug-цели с нужными
   зависимостями и совместимыми toolchain/architecture/CRT/iterator ABI;
   отдельный архив не требуется. Старый build.cmd `/MT /O2` не является
   подходящей командой для автоматического reuse Debug-объектов. Проверить
   точную команду и состав при actual source/build-harness review, до запуска.
   Construction GO относится к private extraction и probe при этой поправке,
   не удостоверяет существование предложенной .lib.
3. Native probe использует genuine clock/frequency/format от того же
   IAudioClient, 10ms profile (`100'000` 100ns units, worker:211); helper вызывается
   между ReleaseBuffer и следующим GetBuffer, без удерживаемого capture buffer.
   Старый PairProbe получает clock внутри GetBuffer/ReleaseBuffer и использует
   100ms — это надо изменить, а не выдать старую PairStats за новую проверку.
   Полный worker.consumePacket не подходит для запрета чтения PCM: он копирует
   samples. Внешняя проба может получать opaque PCM pointer, но не разыменовывать,
   копировать, сохранять или экспортировать содержимое.
4. Убрать 44100/MMCSS и продолжение после fault. Сохранить видимый Start до
   активации, Stop/cancel, bounded onecase/65-packet ceiling, cleanup/watchdog,
   все GetBuffer/ReleaseBuffer counts, native Stop result и подтверждённый
   terminal/owned0 на обоих исходах. Не считать отсутствие процесса заранее
   подтверждённым: перед будущим запуском main проверяет GRAF/другие diagnostics.
5. Все actual S_OK/S_FALSE/native/conversion/bracket failures должны быть
   видны в bounded scalar result; ноль успешных измерений не PASS. Не повторять
   до GREEN, не фильтровать outliers и не расширять tolerance для VM. Проверка
   checked B и реальной released-end metadata не создаёт worker baseline и
   не доказывает READY/ACK. Экспортировать verdict/counts/относительные величины,
   а не endpoint identity, абсолютные position/QPC, audio или content paths.

[Microsoft GetPosition](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getposition)
описывает связанную пару position/QPC; QPC output уже в 100ns, position units
относятся к GetFrequency. S_FALSE отличается от точного S_OK, повтор position
допустим. Это документальная основа измерения, не свидетельство, что конкретный
Parallels stream удовлетворяет действующему before/paired/after bracket.
Сохранить нынешнюю арифметику/порог, а фактический исход установить отдельной
пробой; не заявлять физическую точность субкадра или полный privacy frontier.

Итого: **requirements/analyze C0/H0; bounded construction GO с M1 поправкой
сборки выше**. Следующий gate — actual helper + external diagnostic diff и
точная сборочная привязка; runtime отдельно. Сведения main о consumer d995…/
dac446… здесь не переквалифицировались и не заменяют native clock evidence.
Только append собственного report; нет VM/build/test/Git/GitHub write,
implementation/norm/tasks/checklist изменений. T116/T120, installed/hardware/
release и прежние AAC47/AAC56 ограничения остаются открытыми.

## 2026-10-21 / T120 clock-native1: fresh checklist/analyze/issue reuse gate

**Scoped requirements/checklist/analyze GO — C0/H0.** Переиспользован раздел
«shared native ResumeClockSample — construction gate» (начало:7550) после
свежей проверки входов, не по заявлению main и не по старым runtime PASS.
Новый план, checklist или задача не создавались. Это read-only high-risk
review существующей T120, а не новая полная приёмка Feature200.

### Exact source и неизменные нормативы

Stage `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t120-clock-native1`:

```text
396766d44cf35e929a2abe91a2f345f347f2adef140490f93174053d010f5b2d source.sha256
65ddf184bbb884047f26b3f59176d47180f1f9f6ecdab1752d582a090891a9d4 WasapiCaptureWorker.cpp
061f3a1e36067e86522856cac93c2e8cedfcaeb834130d4854d250f827bf35c2 WasapiCaptureWorker.h
```

Все **216/216** текущих host inputs совпали с source.sha256, missing/mismatch0.
Diff manifest к prior.sha256 — ровно эти два worker файла; changed.json и
обе frozen source-копии совпали. Это host/stage equality, не guest/PE/runtime
receipt и не идентификация внешних probe/build/runner файлов, не входящих
в manifest216. Текущий feature pointer остаётся F200/high-risk-product,
codex/200-windows-followup/source b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1.

Повторно вычислены все11 нормативных SHA, перечисленных перед разделом7550:
constitution/spec/plan/tasks/quickstart/research/data-model/desktop/local-
custody/packed-custody/privacy-pause — **все неизменны**. Основные привязки:

```text
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 constitution
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 spec
f3009717a5763a74b6207448f83496af1d5db9e1f48b360f5faf59aea7977bd2 plan
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f tasks
be5ad099a424e5d70d41721fc0fedeca59566e07885201cceb9298a5ce5625dc quickstart
5e1c0a89ebb33f47876fafd345972e3e627e6597504d6b6a5dc4c8ac1ab10eec privacy-pause
```

Прочитано содержимое всех checklist файлов для свежего inventory/count:
**198 files / 31 с checkbox / 477 checked / 0 unchecked**, digest
`0ff59d9f2f9b55a38ff814a62343ba9666d194a17fc3b9e7bf06a30b7d82916f`.
Каждый файл неизменен относительно предыдущего полного inventory; семантический
review прежних критериев переиспользован, не объявлен новым whole-feature audit.
Privacy12 перечитан отдельно. Applicability остальных тематических gates из7550
сохранена. Checked означает качество требований, не готовность реализации.

### Scoped analyze и tracker

Перечитаны same-stream plan:1652–1694, quickstart §15, текущая T120:602 и
privacy12; исходные FR-002/009/010, SC-002/004 и диагностические FR-018/021
сохраняют покрытие существующими задачами. Неизменные constitution и contracts
сохраняют visible control/Stop, native owner, checked B, strict clock/fault,
bounded metadata, synthetic/native/installed separation и protected dependency.
Нового blocking clarification, uncovered requirement или противоречия не найдено.
Extensions YAML успешно разобран: enabled before_analyze/after_analyze пусты.
Prerequisite paths подтверждены напрямую feature pointer и существующими
артефактами; Git/VM/build/test команд не было. Анализ завершён до этого append.

Свежий read-only GitHub API подтвердил:

- #7590 OPEN, `[200][P0][security] T120: Не возвращать микрофонные данные паузы
  после возобновления записи`; labels priority:P0/area:security/gate:pr-blocker/
  type:bug/feature:200, updated_at2026-10-12T20:20:50Z. Body совпадает по
  tasks SHA80fc15… и прямо связывает T116/#7444. Assignees пусты: подтверждено
  владение областью task-backed issue, не назначение человеку.
- #7444 OPEN, `[200][P0][storage] T116: Защитить всю локальную цепочку записи без
  открытых временных копий`; priority:P0/area:storage/gate:pr-blocker/
  type:hardening/feature:200, updated_at2026-10-02T19:09:23Z.

**Граница verdict:** gate7550 применим к текущему exact source в части требований
и допуска конструкции. Три заявленных исправления Fermat external (4obj,
count/flags до clock read, terminal-priority pure tests) не получили SOURCE GO
этой записью; их actual delta/build-harness review остаётся отдельным pending.
В частности прежний M1 про OBJECT/link/CRT нельзя закрыть одним equality216.
Нет разрешения считать probe запущенной/успешной, guest owned0 или strict native
bracket доказанными. T116/T120, installed/hardware/release и AAC47/AAC56 открыты.
Изменён только собственный report append; norms/tasks/markers/code/Git/GitHub/VM
не менялись, сборки/тесты не запускались.

## 2026-10-21 / T120: cold canonical unread/partial consumer — read-only reuse

Это ограниченное source-исследование следующего test-only consumer, **не
выполненная регрессия, не actual SOURCE GO будущего diff и не native-device
clock evidence**. Native launch остаётся HOLD; VM/Git/GitHub/build/tests не
использовались. Применён code-reviewer; единственная запись — этот append.
Ранее описанный после green1 путь: собственный раздел:7348–7384 перечитан,
нынешние методы проверены заново, старый gap bare callback не перенесён молча.

### Что уже есть и чего текущий smoke не доказывает

- NativeCaptureStorageIntegrationTests.cpp:633–672 — existing friend peer,
  microphoneWorker, resumeGenerated, generatedPacket, devices. Нынешний
  generatedProducer:3861–3897 уже вызывает consumePacket для privacy mic и
  обслуживает servicePrivacyResume во всех ожиданиях и после последнего пакета.
  Это не прежний bare-callback fixture. System branch по-прежнему generated
  normalized callback; реальное render-устройство этим не проверяется.
- privacyFlow:6258–6289 принимает protected Pause до emit, пишет все3000frames
  в paused, затем Resume и второй Pause. Fresh microphone после Resume не
  выдаётся. Cold:6396–6409 проверяет два закрытых segment; :6420–6430 делает
  полный inspectProtected/30s/AAC. Это полезный metadata smoke, не sample oracle.
- Core CaptureFaultStateTests.cpp:816–922 уже даёт подходящий минимальный
  unread/partial protocol: packet0 baseline, два owned unread packets после
  Pause, настоящий serviceResume, public Resume и packet3 fresh; assertions
  после EOS/finalizer. Нельзя переносить его фиктивный checkpoint в protected
  consumer. Также PrivacyAec:647–656 умножает mic на0.5, а интеграционный
  GeneratedAec:678–684 просто копирует mic — ожидаемые значения различаются.
- В текущем apps/windows нет helper с именем `readCanonicalSample` (rg exact).
  Реальные reuse patterns здесь: readGeneratedManifest:4924–4948,
  readProtectedUploadExpected:3084–3116 и ProtectedCustodyReader.h:83–111.
  Они выбирают ref по роли/selectedSlot, открывают genuine BOTH group и читают
  IStream, не физический content.packed-v2/угаданный offset.

### Минимальный конкретный test-only путь

Сохранить нынешний --protected-privacy-flow invocation/его metadata assertions
без замены. Дополнительный режим существующего vertical helper/того же TU
может переиспользовать normal start/adoption/finalization/cold skeleton;
новый файл, публичный API, writer/controller, норма или task не нужны. Не
переводить остальные generatedProducer callers на новый фазовый сценарий.
Прежние3000 canonical frames/30s сохранить: первые4frames управляемые, остальные
2996 — fresh continuation; короткий4-frame standalone вместо30s рискован из-за
реального short-recording discard и теряет нынешнюю normal sealed приемку.

1. Существующие devices устанавливают bodies на тех же workers. Test-local
   фазовые gates принадлежат fixture и живут до join; waits проверяют running
   и прежние deadlines. Permit-through-frame/barriers, а не скорость/sleep,
   разрешают обоим источникам только frame0. Mic через actual generatedPacket
   (ClockMapper/AudioNormalizer/consumePacket/release); дождаться writtenFrames1.
   Это genuine valid released-end baseline для последующего mailbox.
2. Public capture.pause + pollHealth до !privacyPending && paused, то есть
   подтверждён настоящий writer OPEN. Лишь затем microphone acquisition body
   создаёт owned960samples для D=480 и D=960, выставляет unreadReady и держит
   их БЕЗ capturePrivacyEpoch/consume. System producer может выдать frames1/2
   через прежний system callback; mic отсутствует, timeline не должен придумать
   соответствующие frames. No locks custody/capture/dispatch вокруг ожиданий.
3. Public capture.resume. Пока main ждёт recording/!privacyPending, тот же
   mic body обслуживает servicePrivacyResume. Маленькая test-only делегация
   existing peer должна уметь sample p=1200*8-1=9599, f384000/r48000, actual
   now timepoints и прежний synthetic bracket: production checked B получается
   **1200**, не setter/fake ACK. Нынешний resumeGenerated(nextFrame) умеет только
   кратные480, поэтому его нынешний вызов с frame1 НЕ проверит partial boundary.
4. Только после завершённого Resume разрешить consume двух unread packets:
   D480/N480 и D960/N480. Epoch снимается существующим consume wrapper сейчас,
   а не при создании vectors. Обеспечить native-clock metadata не позади
   resume sample: как core fixture, packet1/2 current clock=1440*8, packet3
   current clock=1919*8; D/QPC/offset остаются непрерывны. Текущий generatedPacket
   вычисляет clock из конца каждого packet и не задаёт этот вариант, поэтому
   требуется лишь optional test-peer observation/clock argument, не ослабление
   ClockMapper/worker checks. Ожидаемые prefixes480 и240; данные не подменять
   нулями до actual normalizer.
5. Packet3 D1440 — явно иной fresh marker; затем frames4..2999 в прежних
   quotas/backpressure. Для последнего Resume после полного total body по-прежнему
   остаётся live и обслуживает mailbox до Stop. Второй public Pause после3000
   сохранить; Stop закрывает второй OPEN. Никаких добавленных extra audio frames.

Простейшие двоично-точные markers: system0.125; trusted mic0.25; два unread
mic0.5; fresh mic0.75. GeneratedAec passthrough, суммы ниже1 без clamp:

| canonical позиции (48k mono) | ожидаемый mixed | вычесть known system0.125 |
| --- | --- | --- |
| [0,480) trusted | 0.375 | 0.25, pre-Pause не переписан |
| [480,1200) old prefix | 0.125 | **0**, весь packet1 + первые240 packet2 |
| [1200,1440) допустимый partial suffix | 0.625 | 0.5, не blanket silence |
| [1440,1440000) fresh | 0.875 | **0.75**, микрофон реально вернулся |

Это два unread packets, второй пересекает B. Если нужно отдельно утверждать
два ПОЛНОСТЬЮ suppressed packets плюс третий partial — это иной, больший
fixture; предложенная минимальная конструкция такого утверждения не делает.

### Холодный sample oracle и неизменные защиты

Stop/EOS3, worker/dispatcher completion, writer finalize, genuine queue adoption
2→3, shutdownWorkDrained и уничтожение NativeCapture остаются ДО async cold open
(:6309–6385). Нельзя читать live writer vectors и называть это холодным proof.
В том же cold task (:6390+) store→readPackage/session→selected canonical sealed
ref. По шаблону readGeneratedManifest открыть openProtectedCustodyReaders,
выбрать canonical role/refIndex/selectedSlot и проверить state/length. Canonical
V5::append:322–340 пишет **только frame.mixed**, 1920B на480 float32; отдельных
mic/system и serialized PTS в этом файле НЕТ. Поэтому честный cold oracle —
все mixed samples, известный system marker и вычитание contribution, не
несуществующая canonical microphone дорожка.

Точный total: 3000*1920=5760000B, 1440000 samples. Проверять весь payload
последовательно маленьким charged CustodyBytes блоком, например32frames=61440B,
memcpy float (без alignment cast), конечность/точные binary values/порядок,
каждый Read HRESULT+got, exact EOF и zero-read sticky status; буфер wipe,
отсутствие новых plaintext файлов. Не делать миллионы scalar native Read и не
загружать весь пакет ради нескольких markers. Whole BOTH/hash validation даёт
existing reader group, но НЕ заменяет sample assertions. Освободить всю эту
reader group ДО inspectProtected:577–581 открывает свою, а ProtectedInspection
удерживает её (LocalRecordingPackage.h:90); одновременные группы не нужны и
могут конфликтовать с native leases/jobs. Затем неизменный full semantic/AAC/
duration/segments2, whole-tree snapshot до/после read-only inspection, release.

PTS доказывать отдельно, не приписывать PCM serialized timestamps: existing
timeline.nextFramePts()/processedFrames()/trimmedFrames после EOS, пока объект
ещё жив и dispatcher join исключает race, доступны через существующий peer.
Для commonStart0 ожидаются healthy/processed3000/nextFramePts1440000/trimmed0
обоих источников, writtenFrames3000, release counts3000, worker errors none.
При необходимости test-local GeneratedAec counter подтверждает3000 реальных
AEC-вызовов и system marker на каждом входе; это не доказательство реального
AEC. Последовательные source D/QPC и cold length/sample order сохраняют count/
общий интервал; canonical сам по себе не доказывает отдельную PTS-дорожку.
Не читать timeline concurrent с dispatcher под фиктивным защитным mutex.

Собрать sample verdict как value, отпустить readers/pair/cancellation/owner,
inspection.get и exact original idle/jobs/pins; named privacy assertion только
после обычного завершения/EOS/teardown, как core unread. No changed timeouts,
quota allowances, metadata fallback, epoch setters, boundary-only calls или
новый authority/cache. Именно такой reuse осуществим в нынешнем source;
actual test diff и runtime нужны отдельно. Current metadata smoke остаётся
самостоятельным обязательным контролем. Полные T120/T116/native hardware/
installed/release и прежние AAC47/AAC56 остаются открытыми.

Source identities прочитанных основных входов:

```text
11573c62b0108200855e5ee1b336d971db4a57fb800f222caf19b36b7bd7a6e7 NativeCaptureStorageIntegrationTests.cpp
a3066e2ec5c2259e88fe3ba3ead49970e363e8750d5cff685210c3a41c5b25ad CaptureFaultStateTests.cpp
6347083384e8628d9f49a9b729a14fc3e574a39b566f7fd9b1c7960531d5b037 Recording/NativeCapture.h
d85e1ab669608180b0f32f9b9decadaeb4e9e71ab6671465616eb0a9156f8f09 V5LocalRecordingWriter.cpp
2fe2437d3f3f03e9850b6fad7c49a1464c79fe40c33059c20e3e393da381687a RecordingAudioTimeline.cpp
0fb6450791f7ffc51ffa2d8d7ab03ba59ef0e045bfe742df7b5ca5fcc1f116eb AudioNormalizer.cpp
83d3469dff19e59a9dd25d51e957de5b6dab8ef49faa7bf37422afa1c7434e63 LocalRecordingPackage.cpp
bd1297b8f8e9355c17b708ca584f3620d5360154d9629c43cb16fe8a2ef9b65c ProtectedCustodyReader.h
```

## 2026-10-21 / T120 protected-samples1: scoped requirements applicability

**GO, C0/H0 — requirements/analyze applicability только.** Усиление existing
--protected-privacy-flow без нового CLI/flag остаётся в existing T120/#7590,
с protected dependency T116/#7444. Нужны прежние два durable closed сегмента,
3000frames/30s/AAC/cold/restart и exact teardown; не новый продуктовый выбор,
норма, задача или schema. Настоящий public Resume/service mailbox и cold mixed
oracle конкретизируют уже обязательные unread/partial/fresh критерии privacy12.
Первоначальное предложение отдельного supplementary режима не является
обязательным: сохранение/усиление прежних metadata assertions в том же CLI
согласовано. P=(1200-1)*8=9592 согласуется с delivery clock floor1199*8;
это synthetic metadata, не native device freshness/READY acceptance.

Свежо проверен stage t120-protected-samples1:
source.sha256 `0de1d3b969115c42c9dc30db1c1a10704b6850206a12fd9f5483fe09cc1445c2`,
216/216 current host совпали, missing/mismatch0. Diff manifest/prior/changed.json
согласован: единственное изменение NativeCaptureStorageIntegrationTests.cpp,
SHA `1ef83170385a6ab3c6d077d31fd46238b2847ccda8e46c78936cf2979cc61c1b`;
frozen-копия совпала. Остальные215 inputs неизменны относительно prior.

Пересчитаны все11 normative SHA из предыдущего reuse gate — без изменений,
включая tasks80fc15…, planf30097… и privacy5e1c0a…. Прочитан весь checklist
inventory: 198files/31сcheckbox/**477checked/0unchecked**, прежний digest
`0ff59d9f2f9b55a38ff814a62343ba9666d194a17fc3b9e7bf06a30b7d82916f`.
Применим прежний scoped analyze: FR002/009/010, SC002/004 и privacy12,
bounded diagnostics FR021; нового normative C/H или clarification не выявлено.
Markers/tasks не менялись. Issue mapping переиспользован из непосредственно
предыдущей live read-only проверки; нового GitHub запроса в этом шаге не было.

Это НЕ actual SOURCE GO кандидата: полный Fermat SOURCE review ещё pending,
сборка/runtime не выполнялись reviewer. Даже exact cold sample assertions в
source не считаются пройденными до terminal evidence. Единственная запись —
этот report append; code/VM/tests/build/Git/GitHub/norm/markers не менялись.
T120/T116, installed/hardware/release и старые AAC47/AAC56 не закрыты.

## 2026-10-21 / После samples1: текущий gate и конкретный следующий срез

Независимый scoped requirements/analyze reuse: **C0/H0 для продолжения уже
поставленных задач**, не full feature acceptance. Текущие216 inputs совпали с
samples1 manifest `0de1d3b969115c42c9dc30db1c1a10704b6850206a12fd9f5483fe09cc1445c2`,
missing/mismatch0. Все198 checklist files учтены: **477 checked/0 unchecked**,
digest `0ff59d9f2f9b55a38ff814a62343ba9666d194a17fc3b9e7bf06a30b7d82916f`.
Свежо сверенные нормативные SHA:

```text
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 constitution
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 spec
f3009717a5763a74b6207448f83496af1d5db9e1f48b360f5faf59aea7977bd2 plan
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f tasks
be5ad099a424e5d70d41721fc0fedeca59566e07885201cceb9298a5ce5625dc quickstart
```

Перечитаны27 открытых task descriptions. T120/#7590 и его protected dependency
T116/#7444 остаются открыты; issue mapping переиспользован из прежней прямой
проверки, нового GitHub запроса здесь не было. Samples1 runtime принят Fermat,
не квалифицируется повторно этим выводом. Реальный clock probe остаётся HOLD;
synthetic/cold PCM proof не подменяет native device freshness.

### Уточнение по новому master: следующий выбранный срез — T103, связь T088

Main сообщил remote master `ec0f636543d939f627e8c124f59340240503e246`.
Read-only просмотр доступного локального объекта подтвердил диапазон от
`c4dc6d470446f03acfbafb1d3d80d780f8159314`: F136
`0648784cf9a5365220e421d77c8eb51e3bea6907`, затем два документационных коммита.
Нового remote запроса, fetch/merge/reset или иной Git mutation reviewer не делал.
Прочитан actual F136 diff и соответствующий Mac source из ec0f636.

**Не подтверждён одинаковый дефект ordinary POST:** Windows
WebView2Host.cpp:637–690 не пересоздаёт control из-за метода POST; correlated
method приходит через response headers (:694–702, :1930–1933). safeRecoveryUrl
принимает только GET (WebViewRoutePolicy.cpp:387–406), native reload использует
Navigate безопасного recovery target (:1847–1851), не browser Reload POST.
AppMain.cpp:1181–1240 меняет presentation/authority, а не control identity на
каждую обычную форму. Поэтому переносить Mac sessionBoundaryID буквально нельзя.

**Подтверждён source parity gap: безопасная история и auth boundary.**
WebView2Host.cpp:1023–1039 вызывает nativeBack_/nativeForward_ по browser flags;
:1852–1855 напрямую связывает их с core.GoBack/GoForward/CanGoBack/CanGoForward.
Ни метод конкретной history entry, ни принадлежность текущей session boundary
этими проверками не учитываются. Auth rejection (:895–899) отзывает authority,
но не очищает/не отсекает browser history; AppMain auth callback отменяет
зависимые операции, не выполняет history fence. F136 на Mac отдельно помечает
unsafe committed POST items и публикует session boundary после сохранения
окончательного документа (EmbeddedCabinetWebView.swift в ec0f636:483,725,2672).
Это отсутствующая гарантия Windows, **не доказанный replay POST, утечка или
воспроизведённый доступ к старой сессии**: browser runtime может дополнительно
запрашивать подтверждение/перезагружать документ. Native bridge guards остаются.

Следующая работа main без микрофона: в existing T103 проверить meaningful RED
истории обычная GET → POST → GET и login/session transition, сохраняя обычный
POST документ и отсекая небезопасные/старосессионные Back/Forward. T088 связан
с session semantics, но отдельная новая задача не нужна. Existing
WebView2HostLifecycleTests (:621–644) проверяет POST recovery URL/stale generation,
не фактическую browser history; его PASS недостаточен. Использовать этот
существующий test target для расширения поведения; сначала минимальная проверяемая
конструкция/source gate. Portable test может доказать решение host policy, но
не native WebView2 history/cache behavior; последняя приёмка после unlock.
Никакого production implementation GO этим исследованием не выдано.

### Доступный уже runnable контроль, если main нужен запуск без source edits

T116 existing `ProtectedRecoveryPlaybackPartial` — содержательный незакрытый
Debug criterion, а не новый synthetic test. CMakeLists.txt:202–203 задаёт
existing CLI, RUN_SERIAL/TIMEOUT180; V5LocalRecordingWriterTests.cpp:552–672
проверяет actual MF partial >256KiB/<complete, child cut, полный60s recovery,
сохранность ciphertext/IDs/queue/WAV, cold AAC/history/privacy/EOF/resources.
quickstart.md:1200–1217 прямо содержит Debug команду и final marker:

```text
ctest --test-dir <проверенный Windows build> -C Debug -j 1 -R '^ProtectedRecoveryPlaybackPartial$' --output-on-failure
```

Existing validate-v5.ps1 уже принимает Target=V5LocalRecordingWriterTests,
Configuration=Debug, Test=ProtectedRecoveryPlaybackPartial; новый runner/CLI
не нужен. Запуск main только последовательно, с current216/DebugPE, полными
JUnit/actual log/receipt/post216/owned0; не reviewer execution.
Saved AAC47 result.json/XML перечитаны: Debug build0/test8,1case/0skip,
TIMEOUT180.017, old_partial_proved109062ms после genuine524288-byte/g3 partial;
полного COLD_PARTIAL_RECOVERED нет. Release PASS это не закрывает. Если снова
FAIL, использовать существующие phase stamps для локализации, не повышать180/
child60 и не ослаблять полный cold proof. Это неизвестная причина времени,
не заявленный production defect и не вывод о влиянии VM.

Записан только этот append. Code/norm/tasks/checklist markers/VM/build/tests/
Git/GitHub не менялись. T117/T118 не обходят dependency T116; AAC47/AAC56 и
вся Windows/macOS parity/installed/hardware/release остаются открытыми.

### Уточнение ownership/trace F136 → existing Windows tasks

Bounded read main подтверждён: actual строки back=1025, canGoBack=1030,
forward=1027/1034, bindings=1852–1855. GET-only recovery не ограничивает history.
Точная существующая трассировка без изменения норм:

- spec FR-002 (:397–400) — user-visible auth recovery parity;
  FR-005/006 (:410–425) — approved routes/current nonce и native authority.
- **T103 tasks:447 — основной implementation/test owner**: WebView2Host/route
  policy, сохранение интерактивной формы/return target и запрет повторения
  payment POST. Проверить соседний F136 history gap в этом же host, не создавать
  новую задачу и не выдавать общий запрет всех ordinary POST за существующую норму.
- **T088 tasks:390 — session acceptance**: logout очищает своё, повторный вход
  не создаёт вторую сессию; old/new account browser history проверяется вместе
  с этим сценарием. Это не доказательство, что текущий history уже нарушил logout.
- **T097 tasks:413 — существующая визуальная/installed parity приёмка** меню,
  узкого окна и Windows/macOS-specific controls; НЕ первичный владелец исправления
  auth history. Нельзя закрыть T097 одним host unit test или молча расширить её
  буквальный checklist до нового самостоятельного auth requirement.

Есть готовый native reuse, не только portable text assertions:
Tests/GrafWindowsContractTests/WebView2AuthNativeTests.cpp +
RunWebView2AuthNativeTests.ps1 + WebView2AuthLoopback.py. Existing
`login-post400` действительно отправляет форму и проверяет сохранённый input,
interactive response/no bridge и request counts; cabinet401/billing401/
meeting401/reselect проверяют auth recovery. В текущем сценарном наборе нет
Back/Forward через POST item/другую session boundary. Поэтому эти existing
сценарии — baseline/reuse для следующей meaningful regression, не готовое
доказательство отсутствия history gap. Никакие runner/runtime здесь не запускались.

Конкретный next action main: сначала bounded T103 test construction для actual
ordinary GET→POST→GET history + auth transition в существующей fixture,
с серверными счётчиками POST и наблюдением актуального документа/authority;
не обвинять WebView2 в replay по одному CanGoBack и не лечить обычный POST
пересозданием control. Требуются отдельные construction/source/runtime gates.
Нормы/tasks/checkboxes остаются неизменными; T116 Debug long остаётся вторым
уже исполняемым без source edits контролем, а не заменой этого parity slice.

## 2026-10-21 / T103 history: requirements/analyze и test-only construction gate

**GO, C0/H0 — только написание tests-first расширения existing native auth
fixture/loopback/runner.** Нужен этот bounded construction gate, но не новый
spec/plan/task/issue или полный повтор analyze Feature200. Lane остаётся active
high-risk auth Spec Kit slice, не low-risk только потому, что меняются тесты.
Read-only scoped analysis выполнен до отдельного разрешённого report append.
Навык speckit-analyze прочитан целиком; enabled before/after-analyze hooks нет.
Полный command workflow и state-changing hooks не запускались; prerequisite
identity переиспользована с прочитанным .specify/feature.json F200/b1eb3d5….

Свежо сверены все пять normative SHA из предыдущего раздела — unchanged:
constitution d28f8312…, spec0065a781…, planf3009717…, tasks80fc15cd…,
quickstartbe5ad099…. Повторный подсчёт198files:477checked/0unchecked.
Применимы security CHK001–003/006–011/017–018/022, requirements
CHK003–007/013/019–022 и UX CHK001/002/020; текущий scope не меняет их смысл.
Constitution VI, spec FR002/003/005/006 и SC002, plan «Вход» (:556–561),
bridge §§2/6/9 (:45,134–140,229–254), T103/T088 покрывают форму, безопасный
GET-return, session/document authority и stale callbacks. T097 не становится
primary implementation owner. Нового product answer/clarification не требуется
для наблюдения и проверки этих уже обязательных границ. Текущее source-gap
наблюдение не повышено до доказанного replay/утечки.

Допущена минимальная test-only конструкция:

1. Reuse WebView2AuthNativeTests.cpp, WebView2AuthLoopback.py и existing runner;
   менять только synthetic scenarios/наблюдения/ожидания/соответствующие exact
   counts и ValidateSet при необходимости. Production guards/API/route allowlist,
   метод/тело настоящего запроса, bootstrap/nonce/cookie owner не менять.
2. Ordinary approved GET A → настоящая form POST B → distinct GET C. Дождаться
   actual committed/completed нужного документа, подтвердить сохранённый POST
   документ/ввод, затем вызывать host.back()/forward(), а не подменять их
   core.Navigate(GET)/ручным callback. Отдельный GET-only контроль сохраняет
   рабочие Back/Forward; «запретить всю историю» не становится успешным oracle.
3. Loopback считает фактический POST отдельно от GET; один намеренный submit
   означает baselinePOST=1. После history traversal без нового submit — никаких
   дополнительных POST. **Одного счётчика недостаточно:** page cache может вернуть
   старый POST без сети. Проверять текущий synthetic document identity/marker и
   host runtime/bridge authority; небезопасный POST history item не выдавать за
   разрешённый safe GET. Если браузер показывает confirm/error или никуда не
   переходит, это наблюдаемое поведение, не автоматический PASS и не timeout RED.
4. Session case использует реальные browser document/cookie transitions с двумя
   фиксированными synthetic session identities и серверными ответами, без
   production epoch setters/ручного auth invalidation для «доказательства».
   Проверять старый/новый документ и отсутствие старой native authority после
   boundary, актуальность delayed callbacks и согласованность safe return.
   Synthetic session не доказывает live account persistence/restart T088.
5. Не печатать cookies/tokens/nonce/HTML/private URLs/content; только fixed case/
   phase/boolean/count/error. Existing isolated profile, synthetic TLS, loopback
   only, deadlines/owned-process/server writer drain/PE guards сохранить.
   Не читать final counts до server terminal; очистка только owned fresh temp,
   failure evidence сохраняется. Нет реальных платежей, аккаунтов или микрофона.
6. Expectations определить до запуска, отдельно ordinary POST preservation,
   history safety и session boundary; no either-PASS-or-refusal. Genuine product
   RED должен следовать достигнутому действию и конкретному oracle; build failure,
   недошедшая phase/fixture timeout — отдельные результаты, не meaningful RED.
   Старые login-post400/400/429/reselect/recovery сценарии не ослаблять.

Прочитанные baseline identities до изменений:

```text
a43f9e303509921a6bfe650b8d8f0a82992f5faeaaf9b35c03b68cf47029c0e7 WebView2AuthNativeTests.cpp
27bebbb1416390c2b1141b23a26138675ddc294be3db02b0141b365dac9bfc3f WebView2AuthLoopback.py
9f5fb28436810f644acfe555af8eba91dd127dded64525eb6a04cf6913319bc3 RunWebView2AuthNativeTests.ps1
```

После patch — отдельный actual SOURCE gate перед runtime. Конструкция не требует
нового публичного API/production friend: existing host entrypoints и loopback
наблюдения достаточны для начала. Если конкретная session/stale-callback часть
потребует нового seam, её предъявить отдельно, не вводить скрыто. Изменение
production history policy/механизма fence требует самостоятельного source/design
review по полученным фактам; этот GO не выбирает способ исправления.
ReleaseApp outer0/PEd3e35… сообщён main и здесь не квалифицировался. Ни одной
VM/build/test/Git/GitHub операции, изменения norm/tasks/markers или acceptance
закрытия не выполнено. Единственная запись — этот append.

### 2026-10-21 / Gate8037 applicability refresh: history-get/history-post отдельно

**GO, C0/H0 — прежний construction gate8037 применим к первому test-only
подмножеству из двух независимых сценариев.** `history-get` (GET A/B/C) —
положительный контроль рабочей истории; `history-post` (real GET A→POST B→GET C)
проверяет сохранение POST-документа и безопасный Back/Forward. Fixed synthetic
document IDs + exact server POST counts соответствуют gate8037; нужны оба
наблюдения, а не только отсутствие повторного сетевого POST. Generic disable
Back/Forward не проходит GET-контроль. Actual code этого кандидата не читался
и не получил SOURCE GO этим refresh.

Свежо пересчитаны198 checklist files: **477checked/0unchecked**. Повторно
прочитаны применимые requirements/security/UX критерии; прежние applicability
группы8037 сохраняются, оснований менять markers нет. Все пять нормативных
хешей совпали с8037: constitution d28f8312…, spec0065a781…, planf3009717…,
tasks80fc15cd…, quickstartbe5ad099…. Новых требований/противоречий/clarification
в выделении двух независимых сценариев не обнаружено; новая задача не нужна.

Session-cookie transition, stale callback/old-authority proof **не покрыты**
этими двумя сценариями и остаются следующим самостоятельным подмножеством
того же T103/T088. Их отсутствие здесь не блокирует написание первого тестового
среза, но его PASS не заменит полный gate8037/session acceptance. Точно так же
никакая history проверка не закрывает installed visual T097 или T120.

Новый whole-feature analyze/issue sync не запускался; scope и task ownership
переиспользованы без новых заявлений о live issue state. Изменён только этот
report append: code/VM/build/tests/Git/GitHub/norm/tasks/checklist markers не
трогались. После frozen actual diff по-прежнему нужен SOURCE gate до runtime.

### 2026-10-21 / T103 history: live issue mapping correction и applicability

GO8037/8113 применим без расширения: свежо сверены прежние пять нормативных
SHA (constitution d28f8312…, spec0065a781…, planf3009717…,
tasks80fc15cd…, quickstartbe5ad099…), все совпали;198files/477checked/0unchecked.
Source/runner review и native runtime этим refresh не принимались.

Материальный новый факт из live read-only GitHub fetch/search/fetch:

- **T103 = #7280**, OPEN: `[200][P1][auth] T103: Сохранять рабочие формы входа
  и безопасное место возврата`. Body ссылается на F200/tasks T103, label
  feature:200/priority:P1/area:auth/gate:pr-blocker/type:bug. Native host/auth
  tests принадлежат этому существующему implementation slice.
- **T088 = #7231**, OPEN: `[200][P1][auth] T088: Сохранить сессию и выбранный
  аккаунт без дубликатов`. Body явно связывает F200/tasks T088/restart/logout/
  account lifecycle; feature:200/priority:P1/area:auth/gate:pr-blocker/
  type:hardening. Это связь для следующего session/stale среза, не закрытие
  T088 двумя history сценариями.
- **#7368 НЕ T088**: CLOSED issue `[280][P1][docs] T001: Обосновать упрощение
  всех платежных страниц`, feature:280. Не использовать как owner/mapping F200.

Оба релевантных fetch вернули assignees:null: конкретный назначенный человек
не подтверждён, task ownership здесь означает соответствие задачи и области,
не назначение исполнителя. Нормы/markers/issues/labels/comments не менялись.
Проверка только read-only; VM/compact/build/tests/Git не запускались. Этот append
сохраняет исправленную связь; manual15TU/XML Includes54 ещё не source-qualified.

### 2026-10-21 / T103 history cancellation: checklist/analyze/owner refresh

**Scoped GO, C0/H0 для следующего test-first шага**, не SOURCE/production GO.
Проверка относится к отмене неподтверждённого BackOrForward до
beginDocumentNavigation, сохранению действующего документа и проверке поздних
событий отменённой навигации. Прежние GO8037/8113 применимы; новых требований,
задач или продуктового clarification для написания этого теста не требуется.
Production dispatch, gestures, pre-wire method/entry correlation и session
crossing по-прежнему требуют собственных доказательств, не приняты этим GO.

Активная feature подтверждена feature.json и read-only prerequisites
--json --require-tasks --include-tasks: feature200, high-risk-product,
codex/200-windows-followup, HEAD b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1.
Configured before/after analyze/implement commit hooks disabled; не выполнялись.

Полностью пересчитаны все файлы каталога checklists: **198 файлов**, из них
**31 с checkbox-критериями, 167 сопутствующих отчётов/записей**. Итого
**477 total / 477 checked / 0 unchecked**, non-PASS файлов нет. Это не 198
отдельных checkbox-чеклистов. SHA-256 sorted inventory (для каждого файла
`<contentSHA>  <basename>\n`):
`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`.
Перечитаны применимые criteria security/requirements/UX и scope advanced-routing;
security CHK001–011/022, requirements CHK007/013/016, UX CHK019/022 сохраняют
применимость. Остальные capture/storage/privacy/install criteria этим
test-only шагом не изменяются и не объявляются runtime принятыми. Markers
не менялись. Повторный whole-feature acceptance/analyze не заявляется.

Свежие normative SHA совпали с предыдущим gate:

```text
d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 constitution.md
0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 spec.md
f3009717a5763a74b6207448f83496af1d5db9e1f48b360f5faf59aea7977bd2 plan.md
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f tasks.md
be5ad099a424e5d70d41721fc0fedeca59566e07885201cceb9298a5ce5625dc quickstart.md
```

Scoped cross-artifact analysis: FR-002/005/006 и SC-002, plan §Вход,
bridge navigation lifecycle и tasks T103/T088 согласованы с проверкой
сохранения документа без replay POST/повышения полномочий. Требования к
доверенному документу/nonce/session и исходные отрицательные сценарии не
ослабляются. Test-first не должен объявить нынешний API PASS исправлением host.
Исходный history4 4/5 и original Back RED остаются сохранёнными; runtime в
этом refresh не переквалифицировался.

Свежо прочитаны GitHub issues через gh issue view (без mutations):
**T103/#7280 OPEN**, title `[200][P1][auth] T103: Сохранять рабочие формы входа
и безопасное место возврата`; **T088/#7231 OPEN**, title
`[200][P1][auth] T088: Сохранить сессию и выбранный аккаунт без дубликатов`.
Оба имеют feature:200/priority:P1/area:auth/gate:pr-blocker; type:bug и
type:hardening соответственно. Bodies явно связаны с соответствующими tasks,
обе задачи остаются unchecked. Assignees=[] у обоих: task/issue mapping
подтверждён, назначенный человек не утверждается.

Блокеров для написания ограниченного теста не найдено. Отдельно после
read-only анализа выполнен только этот разрешённый reviewer-report append;
code/norm/tasks/checklists/VM/build/tests/Git/GitHub state не менялись.
