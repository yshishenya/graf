# F200: обычный запуск установленного GRAF 0.1.0.15

Дата: 2026-11-03. Existing high-risk-product F200, T097/T109/T117.
Корень: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; проверяется dirty snapshot.
Предыдущая проверка пакета: `validation-2026-11-03-production-package.md`.

## Фактический запуск и наблюдение

Stage: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/installed-ui-5tcw49cr`.
Перед запуском проверены installed Version=0.1.0.15, Status=Ok, прежняя identity,
EXE SHA-256 `e6094e4de8b919ba94db652eae4f11ef9762c89d4d0b16f23e19f9342bfa02c5`,
отсутствие другого процесса GRAF. Запуск запрошен через штатный
`shell:AppsFolder\com.graf.desktop_jqvfym1syd7bp!GRAF`. Process observation:
Responding=true, own window=true, EXE совпадает с установленным.

Исполнитель просмотрел захват экрана Parallels: WebView2 отображает страницу
входа; справа native Record disabled и сообщение о недоступном защищённом
хранилище. Пользователь затем сообщил «вошел». Новый захват показывает
страницу списка встреч; native storage error и disabled Record сохраняются.
Содержимое встреч, персональные подписи и снимки не включены в репозиторий.
Нижняя часть захвата чёрная; это не полная приёмка окна, DPI или T097.

После второго захвата один отдельный read-only process query вернул
PrlJob_GetResult: Invalid argument (255). Это не трактуется как падение GRAF:
повторный read-only query подтвердил Responding=true и MainWindowHandle!=0.
Повторный запуск, завершение процесса или удаление профиля не выполнялись.
Запись/воспроизведение/удаление кнопками теста не запускались; поведение всей
обычной фоновой цепочки по одному снимку не принимается.

## Непустой прежний root: подтверждённая предпосылка отказа

Metadata-only осмотр глобального GRAF recordings root: root существует,
не reparse point, 3 файла и 12 каталогов верхнего уровня. `.custody-v1`,
store.id, protected queue и bootstrap отсутствуют. Дополнительная проверка
канонического `kQueueLedgerFileName=desktop-upload-queue.v2` подтверждает
наличие и legacy ledger, и его `.quarantine`. Packaged LocalCache recordings
root отсутствует. Содержимое этих файлов и записей не читалось; их корректность,
принадлежность, полнота и возможность миграции пока не определены.

`storage-shape.out` содержит неверно названный первоначальный probe
`upload-queue.v2.json`; его legacy_queue_exists=false не используется.
Правильный `storage-fixed-shape.out` сохраняет отдельный результат для точного
production имени, не переписывая первоначальную квитанцию.

При таком root ProtectedCustodyFiles::lockStoreRoot выбирает отсутствие
sentinel, вызывает validateStoreInventory(virgin=true), где первая же запись
отвергается с recoveryRequired до protected birth. Таким образом, показанный
regular startup не может принять этот inventory. Конкретный native error
текущего worker не считан; другие более ранние причины отказа не исключены.
NativeCapture не подменяет старый ledger пустым. Удаление/переименование старых
записей, очереди, quarantine или создание отдельного пустого root не являются
исправлением. Нужна existing T117 migration по local §8 и packed §6.1.
Реальный inventory не мигрируется до generated-data/crash-cut gates.

## Независимая проверка кода

Отдельный reviewer read-only сопоставил актуальный Mac F277 commit
5e5bb23f6fb68d6a9436f71e45c0c16e0f64969d и Windows native-settings цепочку.
Он подтвердил предпосылку отказа nonempty/no-sentinel root и выявил отдельный
P2: initial native notification read может вернуть canEdit=false до /auth/me;
позднее подтверждение аккаунта не обновляет уже открытую страницу. Это вывод
по коду, не живое воспроизведение P2 в установленном приложении. Исправление и
его регрессия проходят отдельный scoped gate; задачи целиком не закрываются.

## Граница результата

Обычный установленный пакет запускается, WebView2 рендерит вход и список
встреч после пользовательского входа. Запись остаётся заблокированной.
T097/T109/T117, полный паритет Mac, аппаратная и release приёмка открыты.
Commit/push/PR/merge, сервер и доверие к сертификатам не менялись.

Собственные два временных снимка удалены после просмотра; сохранена только
квитанция screenshot-cleanup.json с размерами и SHA-256. Пользовательские
файлы и исходные снимки пользователя не удалялись. Установленный GRAF оставлен
открытым после входа пользователя; штатное завершение в этом этапе не принято.

## Уточнение следующего шага по хранилищу

После отдельных нативных проверок ещё один metadata-only postflight подтвердил
тот же installed EXE/0.1.0.15/Ok, один отвечающий обычный процесс и отсутствие
тестового GRAF. Protected store по-прежнему отсутствует, legacy ledger и его
quarantine присутствуют. Точная ошибка storage worker не получена; источник
сообщения UI не объявляется исключённым только по этим наблюдениям.

Local-custody contract §8 запрещает no-intent legacy initialization при
существующем неизвестном quarantine и его перезапись. Это отдельная причина
не запускать автоматическую миграцию рабочего root вслепую. Наличие этого
файла не доказывает порчу, его происхождение, корректность или возможность
восстановления. Копирование в новый пустой root, исключение inventory validator
или обычный plaintext reader не являются исправлением.

Зависимость T116 → T117 сохраняется. Побайтная сверка исторических 216 inputs
последнего пятисценарного native прогона с текущим checkout нашла изменения
в 15 путях, включая writer/package/NativeCapture/ProtectedCustodyFiles/transport
и нативный integration test. Поэтому его прежние пять PASS нельзя автоматически
считать текущей полной проверкой записи. Отдельно запущен свежий generated-data
прогон существующих PendingStart, InspectionPreparation, ShortDiscard и
SchedulerSuccess на настоящем Windows Debug target, с искусственными
источниками/HTTP и отдельной fixtures папкой. Build/runtime результаты должны
приниматься по terminal квитанции; один запущенный процесс не считается PASS.

Независимый анализ нового входа миграции запрошен у reviewer, но он прерван
API 403 до создания отчёта. Новый migration construction/checklist GO не получен;
контракт/план/задачи не изменены и реализация перехода здесь не принята.

## Завершённый текущий generated-data прогон T116

Stage: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t116-current-native-mt25cz_t`.
Свежие configure/build Debug x64: exit 0. Native integration EXE SHA-256
`728ece03e477c1ffd86d2bb74c8bee9d4a8275d3f9ecae48d46cdbd967f7f2a5`.
225 frozen Windows inputs сверены до/после; сохранены source.json, provenance,
build/test logs, настоящий result.xml и actual-test.log. Manifest взят из
рассмотренного notification-context derivative; изменённый AppMain.cpp явно
исключён CMake из этого target. Не все 225 файлов являются compile inputs.

| Существующий сценарий | Результат | Время CTest |
| --- | --- | --- |
| NativeProtectedPendingStart | PASS | 104.56 s |
| NativeProtectedShortDiscard | PASS | 101.34 s |
| NativeProtectedInspectionPreparation | PASS | 54.88 s |
| NativeProtectedSchedulerSuccess | PASS | 64.57 s |

CTest exit 0, 4/4 PASS, total 325.39 s. Terminal result: own_processes=0,
installed_exe_unchanged=true, installed_version=0.1.0.15. Это существующие
проверки настоящих native/writer/storage consumers на generated producers,
с подменённым HTTP, без настоящего audio Start/read, сертификатов и установки.
Тесты и их исходные условия/сроки не ослаблялись. Регрессии подтверждают этот
поднабор текущего кода; это не полное закрытие T116, не legacy migration T117,
не настоящий сервер, не запись с устройств и не установленная UI-приёмка.

После terminal PASS удалены только собственные свежие Windows build/fixtures
этого прогона: 338 файлов, 319345628 байт. Перед удалением сохранён список
размеров/SHA-256; reparse/активные процессы/несовпадающий EXE отклонялись.
`cleanup-result.json`: build_absent=true, fixture_absent=true,
installed_changed=false. Общий reusable base, установленное приложение и
рабочие записи сохранены. Финальные журналы/результаты/контрольные суммы
оставлены в stage; SHA-256 terminal-evidence.json:
`5f802746619a782a656327b44c08189b76abd0b248d652e2c8d3c0d1e22c7cdd`.

Все эти новые результаты проверены исполнителем. Заключительная независимая
сверка остаётся pending из-за уже зафиксированного API 403, а не считается
пройденной по предыдущему review или этому четырёхсценарному PASS.

## Расширенный текущий прогон T116: обнаружен Debug timeout

Stage: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t116-custody-matrix-v4i88a4r`.
Из текущего CMake выбран весь существующий custody/writer/native integration
набор шести executables: 62 сценария. Свежие configure/build Debug x64 прошли;
225 frozen inputs проверены до/после. AppMain derivative исключён из targets
самим CMake. NativeCaptureStorageIntegrationTests EXE SHA-256:
`e7eea37d137d930b7a65aec24f943586fe9abd70537f2f6408f001bca17fd512`.

CTest остановлен на первом отказе: **16 PASS, один TIMEOUT, 45 не исполнены**.
Итог test exit 8 / wrapper exit 1; total 1991.64 s. Это не 62/62 PASS и не
полная проверка T116. Пройдены базовые owner/tree/files/write-stream/writer/
native integration и десять recovery cases; точный список есть в JUnit и
`matrix-terminal-evidence.json`. Отказ:
`ProtectedRecoveryPlaybackPartial`, Debug, TIMEOUT 180.028 s. Его существующие
CTest180/child60 пределы не увеличивались и fixture не сокращалась.

Последние настоящие phase stamps: baseline fixture ready 12328 ms,
baseline recovered 73281 ms, partial fixture ready 84046 ms,
child reached cut 115843 ms, old partial proved 116234 ms. Старый partial —
524288 bytes, complete 732186, generation 3, codec error 6 / c00d36c4.
Последующая partial recovery не выдала следующий stamp до CTest deadline.
Это локализует интервал наблюдения; само по себе не доказывает зависание,
конкретный дорогой метод, регрессию продукта или причину в Parallels.
Исторические AAC47/AAC56 Debug timeout остаются нерешёнными, прежний Release
PASS их не закрывает, как уже требует review-2026-10-19-round460-diagnostic-gate.md.

Terminal postflight: source225/225, own_processes=0,
installed_exe_unchanged=true, installed_version=0.1.0.15. Звук/реальный HTTP/
сертификаты/установка не использовались. Собственные build/fixtures сохранены
для разбора отказа. Обычное приложение и рабочие записи не менялись.
`matrix-terminal-evidence.json` SHA-256:
`b96b0d6733989889e405f38aeb77fb75051a0d1a7048d8389c71591c0ee3e8e4`.

Дополнительно обнаружен дефект внешней квитанции: `requested` после PowerShell
ConvertFrom-Json сериализован как вложенный value/Count вместо массива строк.
Он не вызвал фактический CTest timeout. Полнота этого прогона пересчитана
исполнителем из исходного expected.json и реальных JUnit cases, а не из этого
поля. Будущий aggregate PASS требует явной нормализации массива в новом runner;
исходный Run.ps1/receipt не переписываются задним числом.

Для разбора начат один отдельный повтор **того же** Debug partial test на том же
свежем PE без пересборки/изменения источников/предела180. Stage:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t116-partial-timing-21vs5ltf`.
Добавлено только внешнее наблюдение CPU/IO/process memory counters каждые две
секунды, без чтения памяти или содержимого файлов. Результат принимается отдельно
по terminal receipt, не по одному факту запуска; старый TIMEOUT сохраняется.

Повтор завершён: **1/1 TIMEOUT 180.032 s**, test exit 8 / wrapper exit 1.
Тот же V5LocalRecordingWriterTests EXE SHA-256 до/после:
`faae2d67ad9d9dc90d0515e8048c1b6601a12085406dcb4238cb06cd6e7f527c`.
Source225/225, own_processes=0, installed_exe_unchanged=true. Пересборки,
изменения исходников, fixtures/assertions или пределов не было.

Новое существенное наблюдение: baseline recovered 63094 ms; child reached cut
105688 ms; old partial proved 106157 ms; **partial recovered 174500 ms**;
old extent/originals verified 174579 ms; cold store opened 174641 ms;
cold pair read 174657 ms. Финальных cold_inspection_complete/privacy/readonly/
idle и COLD_PARTIAL_RECOVERED нет. В этом запуске восстановление продвинулось
до следующей независимой холодной проверки; гипотеза постоянного зависания
внутри partial recover не подтверждается. Полнота сценария всё равно не принята.

87 внешних samples сохранены. Последний sample основного процесса, 179753 ms:
120.375 s накопленного CPU, 31952 read operations / 853877248 read bytes,
1142 writes / 30729678 write bytes, working set 38178816 bytes. Отдельный crash
child наблюдался со своими счётчиками. Эти process counters подтверждают
выполнение работы, но не измеряют отдельные методы, фактический physical disk IO
или установленную причину в VM. Для оптимизации нужна адресная стоимость
acquisition/verification/encode/cold-inspection с сохранением всех проверок;
из этого повтора не следует разрешение убрать повторную semantic проверку,
сократить 60-секундный fixture или поднять CTest180/child60.

`t116-partial-timing-21vs5ltf/terminal-evidence.json` SHA-256:
`e937496d7b93658d15ace7f005a7450f2b3397383d923c7e2381a1f768d4bc43`.
Generated fixtures/build сохранены для текущего разбора; новых product/source
решений и закрытия T116/T117 нет. Независимый review этого нового результата
не получен из-за недоступности сервиса. Общий интерфейс проверен отдельно в
`validation-2026-11-03-master-preview.md`; его PASS не заменяет этот TIMEOUT.
