# T117: сохранение quarantined-строки без каталога

Область: F200, существующая T117/#7445, high-risk-product. Исходная версия:
`800c9b3da40172e9581d59a4f936a9fc6db981c7`; изменения ниже ещё не приняты
как реализация. Установленный GRAF 0.1.0.17 собран из `de962ce6bbfe8608650e7fd25ad57a621f521dd7`;
новое уточнение и исправление маршрута уведомлений в него не включены.

## Уточнение требований и план

В `contracts/windows-protected-local-custody.md` §8 уточнён только механизм
сохранения уже существующей generic-quarantined строки при доказанном отсутствии
конечного каталога. FR-012/013/022, plan: «Защищённое хранение», data-model §12,
quickstart §12 и T117 сохраняют прежние требования exact copy, same-root lease,
единственного authority, original preservation и отдельной приёмки. Их повторные
копии и новая задача не нужны. Нет нового пользовательского решения, постоянной
схемы, статуса, таймера, parser либо изменения принципа и срока old-reader exception.

Порядок реализации: независимый requirements checklist и read-only analyze →
неизменяющий продукт test-only кандидат → квалифицированный отказ старого кода →
минимальное исправление общего native пути → неизменный положительный тест и
необходимые отказные проверки. Чтение реального профиля и его пригодность к
миграции рассматриваются отдельно; generated PASS не разрешает удалить,
переписать, присвоить владельца либо подменить отсутствующий пакет.

## Первый тест и последующая приёмка

Первый тест использует существующий Files `--migration-pair`: один настоящий
искусственный legacy package и дополнительную отсутствующую quarantined-строку
с допустимой непрозрачной причиной `legacy_opaque_failure`. Это причина только
искусственного примера, не утверждение о пользовательской записи. Полный v3
ledger содержит сохраняемые owners/ranges/attempts и unrelated operation/ACK.
До целевого утверждения должны пройти decoder, private ACL, настоящий package
и полный native lookup; отказ подготовки или сборки не считается воспроизведением
дефекта. Проверяется отсутствие persistent writes при старом per-row directory-open
отказе. Положительное утверждение:
`missing_generic_quarantined_row_must_preserve_exact_ledger_and_admit_valid_inventory`.

После исправления этот же тест должен подтвердить exact initial queue/original
bytes, настоящую историю переноса существующего пакета, сохранность всей строки
и отсутствие выдуманных package/state/receipt для отсутствующего каталога.
Отдельно нужны предикат, неизвестный исход filesystem, появление объекта в текущем
проходе, release/cold reopen и сохранение прежних interrupted cuts.

Конечный Native oracle использует прежний `--protected-read-model`: настоящий
startup остаётся закрытым до adoption ACK; затем existing generated recording
path создаёт и завершает новую запись со свежими IDs, подтверждает durable
readback/adoption, освобождает владельцев и выполняет независимый cold verify
новой записи и сохранности прежних rows/operations/ACK. Одна reservation этого
не доказывает. Volatile отсутствие проверяется до возврата coordinator Owner;
последующий Native ACK не обещает новую проверку namespace. Законные обычные
Start reservations до создания каталога сохраняют прежнюю семантику.

## Проверки и ограничения

- До кода: governance и `git diff --check` PASS для contract-only уточнения.
- Первый отказ воспроизведён в настоящем Windows x64-процессе под Parallels:
  configure/build `0/0`, код теста `3`. После `MISSING_QUARANTINED_SETUP_OK`
  получены `error=6`, `native=2`, `writes=0`, `flushes=0`, `renames=0`,
  `creates=0`; проверки сохранности прошли до целевого положительного утверждения
  `missing_generic_quarantined_row_must_preserve_exact_ledger_and_admit_valid_inventory`.
  Это квалифицированный RED, не успешная миграция. Отказ сборки или подготовки
  не использовался как подтверждение дефекта.
- Тестовый файл SHA256 `d6d91c7a70e9ef29238de8520a3b3e2073188a6161a259ab60575cebfbeb8841`;
  manifest 225 файлов `cdd50f613772c161a93890bab53a12374735ce51da5808b6a0fff87af4586c0a`;
  test EXE `bb8502d960b90d3dfe981e5a2ea539973dabfddd23cf7e2f5ef39d5578616180`.
  Независимое SOURCE review: C0/H0/M0. Запуск завершился без принудительной
  остановки; собственные временные данные удалены после завершения процессов,
  исходники и установленный GRAF 0.1.0.17 не изменились.
- Первый неизменённый положительный Files-тест прошёл после исправления:
  настоящий MSVC x64 Debug configure/build/`--migration-pair` — `0/0/0`.
  Выполнены exact-copy/original/cold проверки и весь прежний CLI до
  `protected_end`. Неизменный тест SHA256 `d6d91c7a70e9ef29238de8520a3b3e2073188a6161a259ab60575cebfbeb8841`;
  manifest `d93f31d5ca596f173ed6c0df0280d103baa8b062b1f282f99b80a4f4dad37fb0`;
  EXE `aabe07db283f91c0e3e4102f236d1c1d55bf3f083389033df058b6f5a3a34986`.
  Независимая проверка исходников и завершённого запуска — C0/H0/M0.
  Собственные процессы завершены, временные файлы удалены штатно; исходники,
  PID, время запуска и EXE установленного GRAF не изменились.
- Расширенные 22 проверки и появление/удаление каталога на cold coordinator
  проходят отдельную приёмку. Первая попытка A/B остановилась при сборке:
  C4389 с `/WX` в сравнении native error внутри теста. Это **не RED** поведения.
  Исправлен только тип сравниваемых положительных констант, без смены ожидаемого
  результата и отключения предупреждений. Необходим повторный запуск.
- Повторная A/B проверка действительно собрана: configure/build `0/0`,
  `--migration-pair` завершился `3` ровно на
  `cold_coordinator_must_not_forget_observed_appearance_via_fresh_fallback`.
  До этого прошли положительный случай, все 22 режима, фактическое появление,
  наблюдение и удаление каталога. Из производственного кандидата удалены только
  комментарий и ранний возврат coordinator при `conflict/native183`; остальной
  код и тесты неизменны. Это доказывает регрессию составного отказа; отдельные
  поля результата не напечатаны, поэтому возврат Owner старым fallback не
  утверждается. Независимая квалификация — C0/H0/M0; postguards/cleanup прошли.
- Полный исправленный кандидат прошёл настоящий MSVC x64 Debug configure/build
  и оба существующих CLI: Files `--migration-pair`, затем Native
  `--protected-read-model` — `0/0/0/0`. Files подтвердил все 22 режима,
  appearance/removal/refusal и отдельный fresh admission; прежний набор дошёл
  до `protected_end`. Native подтвердил прежние v2/v3 migration cases и новый
  startup/adoption → genuine Start reservation → 100 generated 10ms блоков →
  interruption finish → durable readback/adoption → shutdown/drain → cold
  queue/package/playback verify. Старые две строки, operations/ACK и originals
  сохранены; новая запись имеет 1000ms и проверенные BOTH finalizing/sealed slots.
  Микрофон, реальный звук и сеть не использовались.
- Привязка исправленного кандидата: manifest 225 файлов
  `ebdbd467872173c71ecc60c17dd11a734b8d39fdcb84d1b79cdedd2a4345f7d5`;
  Files test EXE `45d8d1436c9f384d563bbb2a01ceb3836cf58edfdba1d7dd2a786bad0ac5f32a`;
  Native test EXE `9180a8fc48af06193d1bf04a80ce53479b29c99e2839e1f9b9f4db761b2cc6c0`.
  Configure/build/case exits и raw markers проверены отдельно от wrapper exit.
  После Native оставался один каталог в собственном временном дереве;
  всё дерево удалено только после terminal, source/installed checks и
  own/other processes `0`. Принудительной остановки не было, установленный
  GRAF и рабочие данные не изменились.
  Независимая квалификация полного завершённого запуска — C0/H0/M0.
  Сообщение `startup refused: error=13 native=3221225506` принадлежит прежнему
  отрицательному сценарию неоднозначного bootstrap rename: искусственная ошибка
  установлена после успешного rename, admission запрещён, cold recovery проверен.
  Это не неизвестный сбой и не тест отказа ключа.
- Переносимая сборка и CTest на macOS: `48/48 PASS`; отдельное временное
  дерево сборки удалено. Это дополнительная проверка совместимости исходников,
  не Windows runtime и не приёмка macOS-приложения.
- Пользовательская миграция, новый установленный пакет и retirement старого
  reader пока не приняты. T117 остаётся открытой.
- Deadline old-reader exception не продлён; публичный выпуск блокируется прежним
  hard stop. Аппаратная x64/60min/AEC, auth/upload E2E, доступность и внешняя
  доверенная подпись не заменяются проверками Parallels.
