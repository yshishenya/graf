# T119 Round236: независимая проверка launcher/target исходников

Дата: 2026-10-05. Reviewer-owned, ограниченная проверка текущих dirty bytes.

**Approved для указанного source scope: C0 / H0 / M0 / L0.**
Исторический M1, обнаруженный основным агентом во время review, устранён и
независимо перепроверен в финальных байтах. Незакрытых блокирующих findings
в этом срезе нет. Это не приёмка AppMain/bridge/dialog/installed сценария,
не functional handoff и не закрытие T119.

## Область и основание

Canonical repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
HEAD подтверждён свежим read-only чтением; итог привязан к SHA-256 dirty файлов,
не к предположению, что новые исходники уже входят в commit.

Лично полностью прочитаны CalendarNativeLauncher.h/.cpp,
CalendarMeetingOpener.h/.cpp и оба новых test files; прочитан
CalendarJoinOperation.h, затронутые CMake/vcxproj строки. Проверены актуальные
5/0 launcher requirements и принятый контекст operation/work ownership;
собственный pinned Mac CalendarMeetingOpener.swift прочитан заново целиком
на `721b5125d799ea798a4af0b3625e18d3c1109039` для точного target conversion.
Применены полностью прочитанные `code-reviewer` и `ponytail-review`.
Прежний validatedHTTPS review используется как ограниченный контекст; body
validatedHTTPS и строгий host decode также лично перечитаны, без нового
whole-Feature/CIDR/OS-probe исследования.

Полоса — bounded source review внутри существующего high-risk T119.
Issue7540 OPEN и предварительный analyze основного агента не являются
доказательством корректности реализации. Требования/markers не изменялись.

## Findings и финальный recheck

### M1 — некорректный UTF-8 decoded path мог выбрать native target — CLOSED

Обнаружен **основным агентом**, не приписывается независимому reviewer.
Первый opener SHA-256:
`19769469345cf64e5b368bdbcf181358570ab3792caf2e71664f497e08432fee`.
CalendarMeetingOpener.cpp:287–291 прежде декодировал path через permissive
byte decoder без проверки UTF-8. Поэтому Teams `/l/meetup-join/%FF` и Telemost
`/j/%FF` могли пройти prefix check, хотя pinned Mac URLComponents не даёт
соответствующего decoded path. Это actual target parity defect, не дефект
requirements gate и не основание принимать старые байты.

Финальный opener:
`22ab600f9624ad3a320ea9906afe6ff2c6f44bbf4c2a565d3ac83a42413939ca`.
Независимо проверены cpp:181–191,287–291,316–320: один decodedComponent теперь
используется и для path, и для query. Windows вызывает MultiByteToWideChar с
MB_ERR_INVALID_CHARS и явной длиной; invalid UTF-8 даёт nullopt до native
prefix selection. Portable adapter честно принимает только ASCII. Повторное
использование не добавляет отказ для decoded Cc или NUL: это синтаксическая
проверка UTF-8, не повторная host/control policy. Strict decodeHost default
остаётся false, validatedHTTPS:241 использует его без repair opt-in.

CalendarMeetingNativeTargetTests.cpp:31 добавляет оба `%FF` path negatives;
существующие encoded path/query, decoded NUL, malformed-percent, invalid query
UTF-8 и Windows UTF-8 query assertions сохранены. Main сообщает meaningful
portable RED на `assert(!native(url))` до fix; это внешняя квитанция основного
агента, не собственный запуск reviewer. Root cause устранён по фактическому
потоку финального source. Остальные семь source hashes совпали с submission.

## Корректность, безопасность и владение

- **Одно SDK-действие и защита от повторного входа.** Launcher.cpp:21–25
  проверяет busy до изменения старого child и ставит scoped guard до URL/URI,
  options и current callback. Guard сохраняется через statics dispatch;
  poll:54–58 ставит такой же guard до Status/GetResults. Reentrant query/launch
  возвращает busy, reentrant poll — pending. Отмена во время подготовки/current
  проверяется до OS вызова, включая повторную проверку discard после current.
- **Fresh current непосредственно перед dispatch.** Launcher.cpp:39–42
  отделяет trusted native predicate от target conversion. Его false/throw
  до statics — rejected, без owned async work. Adapter не заменяет origin,
  owner/workspace/auth generation/token/document fence общего owner.
- **Cancel не завершает работу.** Header:34 и cpp:43–44,64–71 сохраняют
  полученный handle; cancel только ставит discard. Нет вызовов OS Cancel/Close,
  фонового watchdog, forced timeout, callback/window capture или auto retry.
  Started удерживает pending. Canceled, неизвестный enum и Status exception
  дают indeterminate без сброса handle, также ставят discard, поэтому поздний
  natural terminal уже не возвращает применимый положительный результат.
- **Natural terminal/result failures разделены.** Cpp:64–87 освобождает SDK
  child только после достоверного Completed/Error. Error — failed без чтения
  результата; GetResults exception после Completed — failed с matching API
  completion. Пять query statuses сохраняются раздельно, неизвестное значение
  безопасно отображается в unknown. Launch false не становится launched.
  Reentrant cancel во время Status/GetResults учитывается перед возвратом.
- **Старт без handle имеет только локальный смысл.** Cpp:29,40–47 различает
  preparation/current rejection и throw/null после вызова statics. startFailed
  не означает отсутствие OS side effect; нового запроса/fallback не запускает.
  Полученный handle сохраняется даже при отмене внутри statics. Header и
  CalendarJoinOperation.h:50–54 документируют scope-only основание completion;
  implementation operation здесь не менялась и заново не принималась.
- **Target mapping и параметры.** Opener.cpp:278–306 повторно валидирует HTTPS,
  ограничивает port отсутствующим/443 и выбирает только approved host/path.
  Zoom допускает ровно два непустых сегмента и 9–11 ASCII digits, отбрасывает
  decoded action/confno, добавляет собственные action=join/confno и сохраняет
  остальные query item values/fragment. Empty/nil items различены. Teams
  меняет только scheme для approved prefix; Telemost остаётся validated HTTPS
  association. Нет provider_family authority, произвольных scheme/EXE или
  Mac bundle identifiers в Windows.
- **Границы данных.** Raw input ограничен 8192 bytes; normalized output —
  32768. Percent repair включён только для component semantics, не authority;
  URL encoding предотвращает создание дополнительных query fields из decoded
  `&`/`=`. Native conversion exceptions безопасно возвращают nullopt. Browser
  использует validated HTTPS и IgnoreAppUriHandlers=true; query сам не launch.
  Нет auth/cookie передачи, URL/token logging, resolver/dialog/Record authority.

## Тестовые границы и регистрация

NativeCalendarLauncherTests.cpp лично прочитан полностью. TU-local TestLauncher
заменяет только statics; используются реальные WinRT IAsyncOperation/IAsyncInfo
interfaces. Production class переименован только в test TU, поэтому общий
OBJECT с настоящим CalendarNativeLauncher не создаёт duplicate definition.
Проверки покрывают current false/throw, отсутствие target, busy, пять query
statuses, delayed Started, cancel без Cancel/Close, unsolicited Canceled,
Status fault/неизвестный статус, поздний natural terminal, Error/GetResults
fault, dispatch/Status/GetResults reentry, throw/null start, launch false/true
и browser flags. Fixture не запускает реальные ссылки или приложения.

CMake:12–15 подхватывает оба production cpp существующим CONFIGURE_DEPENDS
glob; :52 регистрирует target test, :91 — native launcher test только Windows.
Существующие OBJECT separation и warning policy не отключены. Vcxproj:130
регистрирует production launcher рядом с opener/operation. SDK windowsapp
подключён штатным pragma, без новой внешней зависимости или factory.

Сведения основного агента, не собственные тестовые квитанции reviewer:

- Tests-first RED missing nativeTarget/header, затем missing launcher cpp MSVC.
- До M1 fix focused native calendar suite 6/6 PASS; полные portable 43/43 и
  native 47/47 относятся к историческим pre-fix bytes.
- Main подтвердил WindowsGetFileHash для финальных двух изменённых файлов;
  canonical SHA-256 независимо вычислены reviewer для всех девяти файлов.
- Полные **финальные** 43/47 прогоны на момент source verdict ещё выполняются.
  Этот отчёт не выдаёт их за PASS и не требует повторного VM/job reviewer.

## Ponytail-review

Lean already. Ship — только в смысле этого ограниченного source slice;
это не release/installed approval. Один concrete SDK child holder, существующий
opener, stdlib scope guard и TU-local statics seam решают заданную задачу без
interfaces/factory/framework. Общий decodedComponent устраняет дублирование
path/query UTF-8 validation. Безопасно удаляемого лишнего слоя не обнаружено.
**net: -0 lines possible.**

## Точные финальные SHA-256

Пути ниже относительно `apps/windows/` canonical repo.

| Файл | SHA-256 |
| --- | --- |
| RecApp/Shell/CalendarMeetingOpener.h | `bf60078007fad2b6f477ebdb810c721782df8fc1078c84f15d665b344b44c730` |
| RecApp/Shell/CalendarMeetingOpener.cpp | `22ab600f9624ad3a320ea9906afe6ff2c6f44bbf4c2a565d3ac83a42413939ca` |
| RecApp/Shell/CalendarNativeLauncher.h | `a2605e186f389691d0cd5e942c3970394e19def8e2015c69bbbd57dacf2838af` |
| RecApp/Shell/CalendarNativeLauncher.cpp | `d285fc9c63cb5bb423c0ec99af09b4837f5acdcf6c14e8eb3508425dde0a4db4` |
| RecApp/Shell/CalendarJoinOperation.h | `b33909c04042e1fa2571d98b9816aa6b43cdeef2acb1d72ad15abed902bfef28` |
| Tests/GrafWindowsContractTests/CalendarMeetingNativeTargetTests.cpp | `ccc6187f75662109b0305ba248205d5e72367100f260d6660fe892453811a3e8` |
| Tests/GrafWindowsContractTests/NativeCalendarLauncherTests.cpp | `79ef362e8705d2193d3e84f31c6e058c6bc3a5d63eb911828501ce20ddad2f0e` |
| CMakeLists.txt | `a8270c052c9108e52bdda099eb0ac51733996d6e5f572af82cd46e299b2d7434` |
| RecApp/GrafWindowsApp.vcxproj | `4af5404cc304839a6002b69a89234b6f4421de2dea1c29677f5b0a156cd20317` |

Ограниченный итог: **Approved, C0/H0/M0/L0; исторический main M1 CLOSED.**
Owner обязан удерживать adapter/ticket до правильного completion и реализовать
предусмотренное indeterminate recovery; этот объект сам не доказывает полный
UI lifecycle или фактическое прекращение работы получателя. AppMain, bridge,
ContentDialog, auth/Record integration и установленный сценарий не wired и
не входят в source acceptance этого среза. Исторические storage/transport,
полная матрица Feature200, builds/probes/VM/GitHub не перепроверялись.

Единственная запись reviewer — этот отчёт. Source, нормы, tasks, requirements
markers, Git/GitHub и dirty работа других участников не изменялись.

## Поздняя квитанция main после source verdict — 2026-10-05

Основной агент сообщил завершение прогонов на тех же финальных opener/target
test bytes: portable **43/43 PASS, 1056.15s**; MSVC Release/x64 Windows
**47/47 PASS, 202.37s**, target test 0.06s, launcher test 0.08s.
Это полученная от main квитанция, не независимо выполненный reviewer прогон;
ранее указанное pending состояние сохранено как история момента оценки.
Portable CaptureFaultStateTests занял 1040.34s; отдельная проверка этого времени
ещё выполняется у main и находится вне bounded launcher review. Общий PASS
не выдаётся за performance proof, причина необычной длительности не установлена
этим отчётом и не приписывается launcher.

Source verdict не изменён: **Approved C0/H0/M0/L0, main M1 CLOSED**.
Это не installed/auth/bridge/dialog/Record acceptance и не закрытие T119.
