# Round246 — независимая проверка исходников нативного календарного меню

Дата: 2026-10-06, Europe/Istanbul. Проверка снимка начата до сообщения о
заморозке; окончательный снимок подтверждён Tesla через пользователя и повторно
прочитан с совпадающими SHA-256. Время контрольного чтения:
`2026-10-05T22:19:06Z`.

**Вердикт: REQUEST CHANGES только для проверенных исходников Tray.
C0 / H0 / M2 / L0; оба M остаются открытыми. SOURCE PASS не выдан.**

Проверяющий не является автором WindowsTray.h/.cpp. Единственная запись этой
проверки — новый настоящий отчёт. Код, нормы, tasks.md, существующие чеклисты,
Git и GitHub не изменялись. Незакоммиченные изменения других исполнителей
сохранены. Использован навык code-reviewer; продуктовые и нативные тесты
принадлежат Main, проверяющий их не запускал.

## Область и точный снимок

Ветка `codex/200-windows-followup`, лично проверенный HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
`.specify/feature.json` и prerequisite paths указывают
`specs/200-windows-desktop-app`. HEAD служит основанием сравнения, а не хешем
незакоммиченной реализации. Применимый режим — независимая проверка исходников
в существующем `high-risk-product` срезе, без выпуска; добавленный отчёт не
меняет продуктовые требования.

| Файл относительно apps/windows/ | Проверенный SHA-256 |
| --- | --- |
| RecApp/Shell/WindowsTray.h | `eceaa7e209a01ab732e65feb2168705c7b8d4b429e5325b04aa18fc2b1e3e0c5` |
| RecApp/Shell/WindowsTray.cpp | `53f064d18a6db702882d2808ddad82b74da0f97d362e7f1016572afcfd1f570e` |
| Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp — только новая Tray-проверка связей, строки 362–381 | `6ba2256d523809e3c9864e13cd8f60e2807caf595b6cce3e696d4c54cb13119a` |

Основание HEAD: SHA-256 WindowsTray.h
`3790e613ba326cbf15830a4f3782d2c60a1da543464023dfb2296448346f8ddf`,
WindowsTray.cpp
`bdaa570a33774cac16616b1d815581554884f0fa8696b27c3dbc126e59926a4d`.
Оригинальное нативное подменю истории уже присутствовало в HEAD; текущая
реализация сохраняет его, а не вводит новую иерархию.

Лично прочитаны root AGENTS.md, индекс guidance, product-gates,
spec-kit-flow/risk, release-and-validation и конституция; активные
spec/plan/tasks/quickstart в части T119, menu/time clarification,
FR-002/005/006/015, SC-002/006/009, data-model §8 и соответствующие desktop/bridge
contracts. PRD и current-product-status использованы для границ пользовательского
контроля, доступности и различия исторической реализации и текущей приёмки.
Полностью прочитаны два файла Tray, их diff относительно HEAD и указанный новый
фрагмент теста. Presenter equality и регистрация/проекция AppMain прочитаны
только для понимания входов/выходов Tray; это не повторная независимая приёмка
изменений Main.

Round246 requirements `18 checked / 0 unchecked`, C0/H0/M0/L0 подтверждает
преемственность требований. Эти отметки не менялись и не являются разрешением
принять нынешние исходники. Предыдущий MAIN-only source review находится в
review-2026-10-05-calendar-host-source.md и исключает собственные файлы Tray
его автора; данный отчёт закрывает именно эту независимую область проверки.

## M1 — замена popupToken не отзывает ещё исполняющийся старый выбор

Место: WindowsTray.cpp462–470, 550–563; invalidateMenu в строках 67–71.

После возврата TrackPopupMenuEx код устанавливает `token->tracking=false`.
`preparing` к этому времени тоже false. Однако showMenu ещё не закончил работу:
впереди DestroyMenu, восстановление фокуса через Shell_NotifyIconW и календарный
callback. Повторный вход в showMenu в этом интервале проходит начальную проверку
и присваивает `popupToken = token` для нового меню. Предыдущий token остаётся
`current=true`; его локальная owning-копия продолжает жить в первом вызове.

Теперь любое изменение rows/auth/time/state и даже cleanupInteraction отзывает
только новый `Impl::popupToken`. Первый вызов после возврата повторно вошедшего
кода проверяет свой прежний `token->current` и IsWindow, но не принадлежность
token текущему popup. Он может вызвать обработчик старой frozen строки после
изменения проекции во втором меню. Это дефект отзыва выбора, не lookup новой
строки по старому индексу. AppMain отдельно защищает полный target и текущую
авторизацию; обход этого guard и реальный внешний запуск здесь не утверждаются.

Сценарий для Main: возврат выбора A → повторный вход до первого calendar
callback → новое меню B/изменение проекции или handler → возврат из B →
продолжение A. Ожидается ноль callback от A. Такой порядок следует из текущего
состояния двух token; нативный повторный вход именно в этом интервале проверяющий
не воспроизводил. Документация Shell_NotifyIconW не обещает отсутствие повторного
входа; нынешний код уже предусматривает уничтожение/отзыв во время возврата
фокуса своей повторной проверкой в строке 560. Конкретная частота этого порядка
на установленном Windows остаётся вопросом нативного теста.

Минимальное исправление: после запрета preparing/tracking и **до замены**
`popupToken` отозвать прежний token, если он существует. Либо удерживать отдельный
признак исполняющегося showMenu до конца локального PopupScope. Не добавлять
обращения к Impl после callback и не отменять уже принятое AppMain действие при
обычном закрытии меню. Добавить одну целевую проверку повторного входа; текущие
asserts наличия `token->current` этот случай не проверяют.

## M2 — исключение после AppendMenuW оставляет двойное владение подменю истории

Место: WindowsTray.cpp381–395 и 527–533.

addItem сначала успешно выполняет AppendMenuW, а затем вызывает потенциально
выделяющий память `menuItems.push_back`. Для строки «История уведомлений» первый
вызов уже связывает historyMenu с родительским menu. Если push_back выбрасывает
std::bad_alloc, addItem не возвращает управление, и
`historyScope.menu = nullptr` в строке 533 не выполняется.

При раскрутке стека historyScope сначала вызывает DestroyMenu(historyMenu),
а затем родительский MenuScope вызывает DestroyMenu(menu), который уничтожает
подменю рекурсивно. Получаются два пути уничтожения одного HMENU и оставшаяся
ссылка родителя на уже уничтоженный child. В том же addItem локальный MenuItem
уничтожается после исключения, хотя его указатель уже передан меню. Исключение
перехватывается внешним WindowProc, но это не исправляет порядок владения.
Конкретный crash или утечка на Windows не воспроизведены и не утверждаются;
двойной путь очистки непосредственно следует из кода и контракта DestroyMenu.

Ошибка достижима при обычных размерах списка, а не только на огромных входах:
в первом меню без календарной проекции и Pause семь записей истории дают
16 элементов перед добавлением родительской строки истории; следующий push
может потребовать роста capacity. Для воспроизведения нужен управляемый отказ
именно этого выделения после успешного AppendMenuW.

Минимальное исправление: поместить owning MenuItem в menuItems **до** AppendMenuW
и использовать уже принадлежащий вектору указатель. Тогда после успешного
присоединения подменю addItem больше не выполняет бросающих операций и
historyScope сразу передаёт владение родителю. Альтернатива — заранее обеспечить
capacity до создания любых HMENU и гарантировать отсутствие бросающих операций
между присоединением child и передачей владения. Проверить один отказ выделения
и один отказ AppendMenuW: ни двойного DestroyMenu, ни callback, повторное
открытие меню возможно.

## Проверенные свойства без отдельных замечаний

- Frozen rows и CalendarHandler копируются до TrackPopupMenuEx; команды
  100–111 адресуют только эту копию. Нет повторного lookup calendarRows после
  вложенного цикла. Callback получает owning UpcomingMeetingRow, не ссылку на
  изменяемую текущую проекцию. Отсутствуют URL launch, resolver и Record внутри
  calendar dispatch Tray; полного допуска к запуску Tray не выдаёт.
- Изменения строк/full target equality, authGeneration, timeRevision и обоих
  серверных флагов вызывают invalidateMenu. Равное состояние не закрывает меню
  на каждом refresh. Failed/unavailable projection передаётся как nullopt.
  Неактивная строка, отсутствующий handler и exiting отключают Join через
  MF_DISABLED/MF_GRAYED. Проверки свежего target/expiry остаются в AppMain.
- Lifecycle/interaction, Explorer recovery, clock/settings/display/DPI changes,
  смена темы и destruction отзывают текущий popup и вызывают EndMenu при
  tracking. Это отзыв выбора, не подтверждение завершения внешней операции.
- Ожидаемый WM_DPICHANGED при собственной подготовке положения не отзывает
  preparing popup: DPI/font читаются после SetWindowPos. prepareMenuStyle
  статический, после потенциального уничтожения владельца проверяются локальный
  token и IsWindow прежде следующего обращения к Impl.
- MenuItem, текст MSAA и shared font/style живут в локальном menuLifetime весь
  вложенный цикл; текущий popup token живёт независимо от Impl. Нормальный путь
  после loop уничтожает меню до item data/font, затем кисть; после calendar
  callback нет обращения к Impl. Основное исключение в построении — M2.
- MSAAMENUINFO — первый член невиртуального MenuItem, подпись MSAA_MENU_SIG;
  cchWText содержит длину без завершающего нуля, pszWText — полную безопасную
  строку. Визуальное многоточие не сокращает accessible name. Реальное чтение
  экранным диктором этой проверкой не доказано.
- Используются lfMenuFont/SPI_GETNONCLIENTMETRICS для DPI окна нужного монитора,
  масштабирование полей и высоты по метрикам шрифта, ограничение ширины рабочей
  областью, DT_END_ELLIPSIS/DT_NOPREFIX. High contrast использует системные цвета.
  Старая история остаётся нативным MF_POPUP; Record/Stop/settings/history
  сохранены. Настоящие keyboard/DPI/text-scale/high-contrast проверки не проведены.

## Новый фрагмент RecordingIndicatorTests.cpp

Строки 362–381 проверены на указанном хеше. Они проверяют порядок создания token,
копирования rows/handler и переноса MenuItem до вложенного цикла; наличие disabled
guard, локальный row dispatch, current/window guard, projection dimensions,
DT_NOPREFIX/font/high-contrast wiring. Неправомерных утверждений о выполнении
нативного меню в этом фрагменте нет. Остальные изменения файла принадлежат
предыдущей MAIN-only проверке и этим вердиктом не принимаются повторно.

Это проверки строк исходника. Они не исполняют TrackPopupMenuEx, не доказывают
отсутствие обращений к Impl вообще и не покрывают M1/M2. Их существующий PASS
совместим с обоими найденными дефектами. Для исправлений нужны узкие проверки
указанных условий; расширение всей тестовой инфраструктуры не требуется.

## Доказательства и границы приёмки

Лично проверено: SHA-256 двух frozen Tray файлов и нового тестового снимка,
ветка/HEAD, diff относительно HEAD, полное чтение исходников и scoped contracts;
`git diff --check` двух Tray файлов завершился без замечаний.

Пользователь сообщил результат Main: portable job 9000 — **45/45 PASS**;
SDK job 13718 ещё выполнялся, его снимок девяти файлов совпадал. Проверяющий
не читал журналы этих запусков; это сведения исполнителя, не самостоятельно
проверенная квитанция и не утверждение, что нативные сценарии уже прошли.

Common menu failure Retry сознательно **NEXT slice**, не замечание о полноте
текущих двух файлов и не принятый реализованный сценарий. Full target identity,
auth/current, исходный steady expiry и общий owner отдельно проверяются в
AppMain; этот отчёт не расширяет ранее данное MAIN-only одобрение.

Не приняты: общий паритет, полный T119, реальный popup/lifecycle/exception
fault-injection, keyboard/screen-reader/DPI матрица, установленный MSIX,
аутентифицированный календарь, физический x64, выпуск/обновление и аппаратное
аудио. T119 остаётся `[ ]`. Private audio, screenshots и account data не читались
и в отчёт не включались. Изменение любого из трёх source hashes требует новой
привязки соответствующей проверки; этот вердикт относится только к снимку выше.

Справка по проверенным контрактам Win32: [MSAAMENUINFO](https://learn.microsoft.com/en-us/windows/win32/api/oleacc/ns-oleacc-msaamenuinfo)
описывает полный доступный текст и положение структуры; [AppendMenuW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-appendmenuw)
описывает MF_POPUP/owner-drawn item data; [DestroyMenu](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-destroymenu)
подтверждает рекурсивное уничтожение; [EndMenu](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-endmenu)
завершает активное меню вызывающего потока; [Shell_NotifyIconW](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shell_notifyiconw)
описывает возврат фокуса NIM_SETFOCUS. Эти документы подтверждают контракты API,
а не воспроизведение найденных порядков выполнения на текущем Windows.

## Round246b — повторная проверка исправлений M1/M2

2026-10-06; контрольное чтение `2026-10-05T22:24:11Z`. Ветка и HEAD повторно
проверены: `codex/200-windows-followup` /
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Независимый reviewer не является
автором исправлений Main. Исторические M1/M2 и первоначальный REQUEST CHANGES
выше сохранены без изменений и относятся к прежним source hashes.

**Текущий вердикт: SOURCE PASS только для ограниченного Tray source gate;
нерешённые C0 / H0 / M0 / L0. M1 и M2 закрыты по доказательствам исходников.**
Новых замечаний в исправлениях и двух добавленных проверках порядка не найдено.
Это не общий паритет, не завершение T119 и не нативная/установленная приёмка.

### Текущий точный снимок

| Файл относительно apps/windows/ | SHA-256 после исправления |
| --- | --- |
| RecApp/Shell/WindowsTray.h — без изменений | `eceaa7e209a01ab732e65feb2168705c7b8d4b429e5325b04aa18fc2b1e3e0c5` |
| RecApp/Shell/WindowsTray.cpp | `b4732d3a37c7c9e54608e0f7dda80b7820374056c170c67a83fe6c7659ada9e6` |
| Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp — только Tray source-wiring delta | `f9f2df46b2c82b4ca122abb16047e2667df32b0a8a548794c61f399460b4930d` |

Все три хеша лично прочитаны до и после повторного чтения; совпали.
WindowsTray.cpp перечитан целиком, исправления сопоставлены с прежним отчётом,
неизменившимися требованиями и соседними lifetime/dispatch/cleanup путями.
`git diff --check` обоих Tray файлов и тестового файла завершился без замечаний.

### M1 — CLOSED, исходники

WindowsTray.cpp465–471: сначала действует прежний запрет повторного входа при
preparing/tracking, затем `invalidateMenu()`, и только после него создаётся
и присваивается новый popupToken. При повторном входе после tracking прежний
локальный token теперь получает current=false до утраты ссылки в Impl.
Его последующая проверка в строках 561–567 не допускает старый callback.
Если выделение нового token не удастся, прежний выбор всё равно уже отозван.
В этой ветке прежний tracking=false, поэтому вызов не завершает чужое активное
меню через EndMenu. Проверка busy остаётся перед отзывом и не мешает своему
подготавливаемому/отслеживаемому меню. После callback по-прежнему нет доступа
к Impl; уже принятое AppMain действие этой заменой token не отменяется.

### M2 — CLOSED, исходники

WindowsTray.cpp393–398: raw pointer взят от owning MenuItem, затем owning
unique_ptr передан в menuItems до AppendMenuW. Перемещение unique_ptr и рост
вектора не перемещают сам MenuItem: Win32 получает стабильный адрес.
Если выделение памяти не удаётся, подменю ещё не присоединено, и локальные
владельцы очищают каждый HMENU один раз. При AppendMenuW=false выполняется
pop_back и исключение; подменю остаётся во владении historyScope.
После AppendMenuW=true addItem не выполняет операций с выделением памяти и
возвращает управление; вызывающий код немедленно делает historyScope.menu=nullptr
в строках 536–537. Последующее исключение при построении других строк очищает
подменю только через родительский MenuScope. Прежний разрыв передачи владения
и прежний dangling MenuItem на этой ветке устранены.

### Две новые проверки порядка и границы доказательства

RecordingIndicatorTests.cpp355 проверяет `menuItems.push_back` перед
`AppendMenuW(`; строка 364 проверяет `invalidateMenu()` перед
`popupToken = token` внутри showMenu. expectBefore198–204 отвергает отсутствующую
строку и неверный порядок; asserts активны благодаря снятию NDEBUG перед
включением cassert. testTrayActionWiring вызывается из main в строке 675.
Проверки соответствуют двум исправлениям и отвергли бы исходный порядок
операций, описанный историческими M1/M2. Это проверка связей и порядка текста
исходника, а не исполнение реального popup, повторного входа или bad_alloc.

Main через пользователя сообщил завершённый RED job63088 и предыдущие PASS
SDK/четырёх нативных случаев. Reviewer не запускал тесты и не читал журналы;
ни RED, ни прежние PASS не объявляются окончательным доказательством нового
снимка. Новые Round246b SDK/native focused и полный portable запуск Main
ещё предстоят по сообщённому плану.

Нативные popup/reentry/fault-injection, доступность/DPI, установленный MSIX,
Retry NEXT slice, полный T119, физический x64 и выпуск остаются открытыми.
Единственная запись повторной проверки — этот append. Код, нормы, tasks.md,
другие чеклисты, Git/GitHub и изменения других исполнителей не менялись.
Current SOURCE PASS связан только с тремя хешами этой секции; последующие
изменения требуют повторной привязки соответствующей проверки.

## Round248 — bounded fixture / resource CMake SOURCE review

2026-10-06, fresh source receipt `2026-10-05T23:04:49Z`.
**REQUEST CHANGES: C0/H0/M1/L1.** M1 concerns the newly mixed CXX/RC target;
L1 is an optional history-presence test gap. Prior product Tray M1/M2 closures
remain historical and are not reopened. Requirements18/0 remain accepted.
Canonical worktree `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch/HEAD submission `codex/200-windows-followup` /
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; no fresh Git invocation.

Fully personally read code-reviewer/ponytail-review; inspected the entire new
_WIN32 NativeCalendarPopup fixture, main registration/init_apartment, complete
CMake file, production .rc, and real Tray public API/menu/message/lifetime paths
needed to interpret this test. Only fixture/CMake changes are evaluated here,
not a new AppMain/Tray/whole-feature approval. High-risk-product lane retained.

### Reviewed exact bytes

| Artifact | SHA-256 |
| --- | --- |
| Tests/GrafWindowsPackageTests/RecordingIndicatorTests.cpp | `be5e3bbbf002e5f1dbf1fa4363baae2424495770ae91dcdc9c9874339b0e161a` |
| CMakeLists.txt | `a41be81cd5eb403b83cdb3e04462d3f99ccfea39a3142852aea3470cad279c12` |
| RecApp/Shell/WindowsTray.cpp — unchanged product | `b4732d3a37c7c9e54608e0f7dda80b7820374056c170c67a83fe6c7659ada9e6` |
| RecApp/Shell/WindowsTray.h — unchanged product | `eceaa7e209a01ab732e65feb2168705c7b8d4b429e5325b04aa18fc2b1e3e0c5` |
| RecApp/GrafWindowsApp.rc — existing resource | `73121f736ebaaaebd22da23ea192b5f231f348d922080b3a29c2e248eaccc8bd` |
| Installer/Assets/Graf.ico — existing asset, hash only | `690bbf6a636f03d1812bd714b3851f8ce253cc2d22c429d40f2a3e740db4cb37` |

Intermediate fixture `d248fc07…` and pre-RC CMake `f9221695…` are not final
resource-wired receipts. Current fixture includes valid synthetic UUIDs generated
with bounded snprintf at104–106. The four Round247b owner/helper source hashes
were independently checked unchanged: header `a22ed3de…`, helper `946f7e45…`,
operation tests `f40c1f0d…`, AppMain `2b7fb97f…`; not re-reviewed as a new slice.
Report before append `5903780feb93d3af8a3fa5f917901c62087846de68360fa100367953669fa1cf`.

### M1 — C++ target options not language-scoped after adding RC

**CMakeLists.txt107–108 and132–134.** RecordingIndicatorTests now compiles the
real RecApp/GrafWindowsApp.rc, but target_compile_options is still gated only by
CXX_COMPILER_ID. `/W4;/WX;/EHsc;/utf-8` (or the non-MSVC C++ options) are target
options without a COMPILE_LANGUAGE restriction, so RC compilation is exposed
to flags belonging to another compiler. A CXX compiler ID is not an RC-language
filter. This was harmless while the target contained only CXX, but is a new
mixed-language configuration defect; do not rely on generator-specific handling.

Official [CMake target_compile_options](https://cmake.org/cmake/help/latest/command/target_compile_options.html)
explicitly applies target options to all target languages and recommends
COMPILE_LANGUAGE for per-language flags. Microsoft documents the distinct
[RC command-line options](https://learn.microsoft.com/en-us/windows/win32/menurc/using-rc-the-rc-command-line-).
Reviewer did not execute RC/native build and does not invent a particular compiler
error or a failed final248 job. Minimal repair: scope existing C++ options to
CXX (COMPILE_LANG_AND_ID/COMPILE_LANGUAGE), retaining unchanged C++ /W4 /WX;
do not disable warnings, alter the resource/icon or add another resource wrapper.

### L1 — history50 assertion can be vacuous

**RecordingIndicatorTests.cpp139–142.** `if (item.hSubMenu)` checks50 entries only
for submenus that happen to exist. If the history submenu is missing, this
assertion passes. The fixture therefore cannot by itself claim history presence
and count50 preservation. Optional minimal addition: count observed history
submenu(s), require the expected one, and retain its entry-count assertion.
No production change is requested. This low finding does not block the slice.

### Fixture truth / lifetime / proof limits

- LoadIcon(resource1), real WindowsTray construction/availability and native
  interaction permit must succeed; no fake constructor, production seam or skip.
  CMake enables RC only on Windows and adds the existing production .rc only to
  RecordingIndicatorTests. Portable main does not call this fixture or claim UI.
- EnumThreadWindows selects the current thread's GRAF.WindowsTray owned by the
  fixture control HWND. Subclass forwarding retains the original WndProc and a
  live fixture throughout tray.reset/WM_DESTROY. Timer1/2 are killed before
  final fixture teardown; active is cleared after the tray HWND is destroyed.
  callbackDestroy deletes tray, not the fixture or selected-row storage.
- The menu is initiated through production icon-message handling. WM_INITMENUPOPUP
  supplies HMENU; actual GUI_INMENUMODE + hwndMenuOwner equality gate timer work.
  PostMessage WM_KEYDOWN Home/Down/Return is queued synthetic navigation, not
  direct callback/WM_COMMAND injection. Microsoft documents the queue behavior
  of [PostMessageW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-postmessagew)
  and menu mode/owner fields of [GUITHREADINFO](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-guithreadinfo).
  Successful posting alone is not successful selection: the final frozen-row
  equality, exact callback count, observed loop and no-timeout assertions matter.
- select/unchanged/reentry/callbackDestroy require one callback after menu mode
  ends; replacement/auth/time/handler/destruction require zero. reentry is during
  active tracking, not proof of a distinct reentry after TrackPopup returns.
  Equal rows do not mutate the frozen target. Synthetic event/URL labels contain
  no private data or credentials, and callback never resolves/launches/records.
- IDs100..111 and absence112 verify actual menu prefix12. MSAAMENUINFO signature,
  full backing text including literal '&'/4096 suffix and current work-area width
  of row101 are read from the real menu. These assertions do not execute a screen
  reader, prove narration/discoverability, or test all DPI/theme combinations.
- disabled checks menu flags without a handler, then EndMenu; it does not attempt
  activation of a disabled row. No GDI/USER resource-growth counter is currently
  asserted; icon existence is not leak/resource-budget proof. Normal selection
  callback counts do not prove already-admitted AppMain flight survival.
- The2s watchdog is fixture-only and fails rather than skips missing loop/input;
  it is not a product resolver/OS timer. This executable now requires an actual
  interactive Windows desktop/Explorer/native permit for its _WIN32 path.
  Headless runners must satisfy that prerequisite or report failure, not call
  portable/assertion/build success native UI proof. No CI config was changed.

Main-reported RED70985/52c14f: native build0,3/4 focused pass, icon1 assertion
failed at82 before RC was linked. This is preserved as controlled expected RED,
not final popup execution proof. No final new-resource native PASS was claimed
at submission. Reviewer executed no VM/build/test/OS action; no live logs were
independently inspected. Microsoft TrackPopupMenuEx's documented return-command
contract was consulted; actual message delivery/navigation must still be shown
by the fixture run, not inferred from static assertions alone.

Ponytail-only: **Lean already. Ship.** net: 0 lines recommended for deletion.
Concrete fixture reuses Win32/public tray/resource/test executable without a
factory/service/framework; this minimality verdict does not override M1.
Only this append was written; code/norm/tasks/markers/Git/GitHub/audio/server
and dirty ownership preserved. Native human keyboard/a11y/DPI, installed T119/
T097, real auth/launch/Retry and full Feature200 acceptance remain open.

## Round248d — final fixture repair recheck, 2026-10-06

**APPROVED, bounded source only: C0 / H0 / M0 / L0 outstanding.**
Historical findings and failed runs above remain intact. Reviewer personally
re-read final NativeCalendarPopup and CMake language/resource registration;
code-reviewer and ponytail-review instructions were read in full. No reviewer
VM, build, test, Git, OS-input or product edit was performed.

Exact current canonical SHA256:

- RecordingIndicatorTests.cpp: `da4aa86d674292478a60a0cb0e273d82bb78df6010993964cbe5111f53ce4373`.
- CMakeLists.txt: `0b2c7322965c523df5fc5a98aabe94900fc11acfcf77bbfbf9298c94ffa68202`.
- Unchanged WindowsTray.cpp: `b4732d3a37c7c9e54608e0f7dda80b7820374056c170c67a83fe6c7659ada9e6`.
- Unchanged WindowsTray.h: `eceaa7e209a01ab732e65feb2168705c7b8d4b429e5325b04aa18fc2b1e3e0c5`.
- Report before this append: `0d732875aa7077c1e9e21cc98bc191bfc377c3a5f4a18efd8781f4b27babc8b6`.

**M1 closed by source.** CMake132–134 now uses COMPILE_LANG_AND_ID:CXX,MSVC
and an explicit COMPILE_LANGUAGE:CXX conjunction for the non-MSVC branch.
C++ warning/error options remain intact, RC is no longer exposed by these
target options. Important correction to the initial assessment: main's actual
RC-enabled build succeeded before this repair; no current-generator RC compile
failure was demonstrated. The original language-scoping concern was a portable
configuration issue, not evidence of that run failing compilation.

**L1 closed by source.** Fixture155–165 requires exactly one submenu as well
as its actual50-entry count. Missing history can no longer pass vacuously.

**Main-found observation/navigation repairs accepted.** The original assumption
that WM_INITMENUPOPUP would supply the menu under TPM_NONOTIFY was disproved by
main's init0/timer0/loop0/timeout1 diagnostics. Current56–81 observes the real
owner-draw HMENU, then forwards the saved production WndProc. Microsoft documents
ODT_MENU's hwndItem as the menu handle in
[DRAWITEMSTRUCT](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-drawitemstruct);
[TrackPopupMenuEx](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-trackpopupmenuex)
documents TPM_NONOTIFY. Current139–141 still requires actual GUI_INMENUMODE and
the exact tray HWND owner before timer work. No synthetic loop flag or callback
replacement was introduced.

The intermediate real-loop/callback0 runs248b/248c are retained as failed
selection evidence, not product Tray defects or PASS. Final130–149 posts Home,
then observes real row101 MFS_HILITE on successive timer ticks; Down is bounded
to24 observations and Enter is posted only when the intended actual menu item
is highlighted. It never sets menu highlight/state or invokes the calendar
callback/WM_COMMAND directly. Final191–195 independently requires no timeout,
exact callback counts and full frozen-row equality; successful posting alone
cannot satisfy the positive case. The diagnostic ODS_SELECTED last-ID field is
not used as authority. The first-HMENU observation count is not a general count
of all popup creations; the reentry assertion should retain its stated bounded
active-tracking meaning, not be extrapolated to every reentry interval.

**Main-reported runtime receipt, not reviewer-executed or log-read:** final248d
native focused4/4 PASS7.73s, RecordingIndicatorTests6.32s, at the two exact hashes
above. Main reports all10 cases reached their assertion counts; this is consistent
with the unskipped ten-case loop200–206. LastTest.log was still being fetched at
submission; this reviewer does not claim an independently inspected per-case log.

**Input / runner / acceptance fences:** only queued PostMessageW WM_KEYDOWN to
the fixture-owned tray HWND is used. No SendInput, keybd_event, mouse_event or
SetCursorPos path exists in this fixture. It does not inject global device input,
but production native menu tracking/foreground activation remains desktop-visible;
this is not a background-safe or headless UI test. The Windows execution requires
an interactive desktop and successful real tray/icon construction. Missing loop
or desktop fails via assertions/watchdog, never skips; portable success is not
native popup proof. No user OS settings, real launch, auth, capture, server data
or production source changed. Physical keyboard, screen-reader output, all DPI/
themes, GDI/USER growth and installed/common-owner end-to-end T119 acceptance
remain outside this approval. Existing MSAA backing text/disabled flags/work-area
checks retain the narrower proof limits recorded above.

Ponytail: **Lean already. Ship.** No deletion recommendation; native/public API,
existing resource and bounded test timer reused without service/factory/framework.
Only this reviewer-owned append was written; no checklist marker was changed.

### Round248d terminal / repeated receipt — final frozen bytes

Final independent static verdict remains **APPROVED: C0/H0/M0/L0**, M1 and L1
closed. A fresh canonical hash read after turn interruption confirmed the same
exact fixture `da4aa86d674292478a60a0cb0e273d82bb78df6010993964cbe5111f53ce4373`,
CMake `0b2c7322965c523df5fc5a98aabe94900fc11acfcf77bbfbf9298c94ffa68202`,
and both unchanged production Tray hashes above. The preceding append survived
intact, SHA256 `8b6ff06ca23d2b56970941b0522ea4a6faf2f3ba975d8062dfd36a2ef1d0adb9`.

Superseding main-reported receipts, not reviewer-executed or independently
log-read: native85519/0935f4 focused4/4 PASS7.73s; repeated37349/c2cd52 focused4/4
PASS8.88s. Main reports LastTest.log receipt `af1c4e` contains all10 cases with
callback1 only for cases0,1,6,8; callback0 for2,3,4,5,7,9; timeout0 throughout.
These map exactly to source select/unchanged/reentry/callbackDestroy positives
and replacement/account/time/handler/destroy/disabled negatives. Main's durable
248d pid14352 and repeated pid11812 are terminal=true with build/test0 and six
matching hashes. Portable49835/a1d65c reports45/45 PASS8.27s. Receipt/log prefixes
are supplied identifiers, not reviewer-verified full artifact hashes.

No further review/test job, VM/global input or implementation action was taken.
The static approval is for repaired fixture/resource wiring only; all runner,
synthetic-input, human keyboard/a11y/DPI, AppMain dialog and installed/T119
acceptance fences in the preceding section remain unchanged and open.
