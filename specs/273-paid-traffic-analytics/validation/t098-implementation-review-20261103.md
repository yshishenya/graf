# T098 — независимое ревью реализации трёх маршрутов, 03.11.2026

Проверяющий: `public_counter_readiness_review`. Полоса существующей F273/T098:
независимое чтение кода и запись только этого отчёта. Основной исполнитель
сообщил ветку `codex/f273-ingress-retirement-20261103` и исходную версию
`e00ffe326d9648732212a065177e6c660b366852`; проверяющий Git/GitHub не запрашивал.
Код, требования, план, задачи, список и сервер не менялись; агенты не создавались.

## Текущий итог повторной проверки исправлений

**SCOPED CODE/ISOLATED VALIDATION PASS, P1=0/P2=0.**
Helper `7212ae2ec66d4da9039b814b10f551966cf7a469924bcaa90a53b7bcee60ff36`
прочитан в затронутой дельте; protocol-third дал88/88PASS,19.334с,
а full-second на том же хеше дал91/91PASS,233.242с с ресурсами и очисткой.
Первый HOLD и промежуточное ожидание ниже сохранены как история.
Это не рабочая приёмка T098, не настоящий REALITY/Stalwart и не допуск выпуска.

## Решение первого прохода

**SCOPED CODE REVIEW HOLD, P1=0, P2=2.** Проверенные nginx-шаблоны соответствуют
принятой схеме I1–I8. Два замечания относятся к достаточности проверочного helper:
фрагментация PP фактически не проверена; проверка утечки через dedicated
error-log скрыта уже отключённым родительским HTTP журналом.

Изолированный успешный прогон сохраняется как доказательство выполненных
сценариев. Он не превращает эти два отсутствующих доказательства в PASS.
После исправления нужен профильный повтор и независимая проверка дельты.
Полная T098, настоящие VLESS/REALITY/Stalwart, рабочее применение, истёкшее
исключение, merge/release и коммерческий результат остаются за этим допуском.
T113 scoped PASS этим ревью не переоткрывается.

## Прочитанный срез и доказательства

Полностью прочитан helper `infra/scripts/check-graf-sni-ingress.py`547строк,
оба nginx-шаблона, изменённая часть `test_compose_hardening.py`, I1–I8 и
принятый checklist10/0. Сравнение теста/nginx с основной плановой копией
использовалось только как контекст: это не самостоятельно проверенный Git diff
от точного исходного SHA. Соответствие кода зафиксировано хешами ниже.

Лично прочитаны:

- `.dev/growth/t098-three-route-protocol-first-20261103.json`: exit1,
  `isolated_protocol_matrix:late_hello_rec_baseline_to_capture`,20.194с,
  старый helper `6e6f70b9...`; рабочей мутации нет, каталог удалён.
- `...protocol-second-20261103.json`: exit0,18.695с, protocol-only,
  тот же helper что в итоговом full; resource явно skipped, all_pass=true.
- `...full-first-20261103.json`: exit0,231.948с, **73 элемента checks,
  73true**, all_pass=true.73 — число элементов объекта checks; агрегат
  all_pass не считается дополнительным независимым тестом. Указаны
  remote_test_directory_removed=true, local_code_unchanged=true.

33pytest PASS сообщены исполнителем; отдельный pytest receipt в этом ревью
не запрашивался и повторный pytest/native прогон reviewer не выполнял.
Выполнены только две локальные проверки без файловых записей/процессов/сети:
AST-опись sendall/slices и исполнение извлечённого config() в памяти с inert
stubs вместо subprocess/path. Их результаты и пределы приведены в замечаниях.

| Вход | SHA-256 лично прочитанного файла |
| --- | --- |
| helper | `e857559a1382896f437eb8600548f364919b90d26d07ae1e503936cb6ee82696` |
| routing | `448024c57914fa353c929f6f259a132e89429fa278db04aaff60b259b0686a65` |
| rec | `700cc6f52696561be96324d34390336633dc0eae0995df36952a51b679b39621` |
| compose hardening test | `7090d68198dda3556063ad6c319f5a060518cd02b6d7e17cdcc493065e8f91c3` |

Три хеша helper/routing/rec совпали с обоими input_sha256 итогового native
receipt. Это привязка доказательства к содержимому; актуальный SHA/база/CI
и размещённая версия независимо здесь не удостоверялись.

## P2-C1 — фрагментация PP header не исполняется

Место: helper145–164 и428–445. Требование: I6, CHK005/010 и окончательное
requirements review — раздельные PP/TLS и фрагментация **PP/ClientHello**,
безопасный отказ неполного PP, без требования успешной поддержки произвольной
PP-фрагментации nginx1.24.

Фактические сценарии:

- coalesced отправляет полный `prefix + data` одним sendall;
- separate отправляет полный prefix, затем полный TLS;
- fragmented_tls отправляет полный prefix, затем только TLS режется
  `data[:7]`/`data[7:]`;
- malformed/truncated отправляют один payload одним sendall и сразу EOF
  через shutdown(SHUT_WR). Это проверяет некорректный/незавершённый ввод,
  но не приход первой части правильного PP до второй части.

Независимая AST-проверка: у prefix/payload нет ни одного slice, все sendall
prefix передают его целиком. Итоговый receipt содержит dedicated/strip
fragmented_tls и truncated, но не содержит fragmented PP ветви. Поэтому
успешные существующие результаты не принимают эту часть I6.

Исправление: отдельная проба обоих receivers, которая передаёт первую часть
правильного envelope, разносит во времени вторую и фиксирует безопасное
документированное поведение nginx1.24. Ожидаемый ранний transport close/reset
не считать HTTP400 и не требовать успешного продолжения PP, которого nginx
может не поддерживать. Не заменять пробу существующим EOF-truncated случаем.
Подтвердить отсутствие достижения API/прежнего upstream и отсутствие нового
сохранения содержимого в журналах; вывести отдельные безопасные итоги.

## P2-C2 — dedicated leakage test скрыт родительским error_log

Место: helper221–224,428–438,515–518. Требование: I2/I3/I6 и CHK003/009 —
отрицательное доказательство отсутствия malformed header/payload на обоих
новых PP-входах в фактических наследуемых/серверных/CLI журналах.

Stream наследует захватываемый `root/inherited-error.log info`, поэтому для
strip эффективный server guard участвует в проверке. Однако родительский HTTP
уже задаёт `error_log /dev/null crit`. Если dedicated server guard исчезнет,
HTTP-вход унаследует тот же молчащий parent, и marker по-прежнему не попадёт
в `root.glob("*.log")`. Проверка `malformed_envelope_not_in_logs` остаётся true,
хотя нужная защита кандидата больше не участвует в доказательстве.

Это подтверждено независимо исполнением только функции построения config()
в памяти с подставными Root/Sink/Subprocess: до и после удаления dedicated
`error_log /dev/null;` сгенерированный parent HTTP всё равно содержит
`error_log /dev/null crit;`. Никакого nginx/файла/сокета эта проверка не запускала.
Это структурный отрицательный контроль генератора; настоящий nginx leak-test
reviewer заново не выполнял.

Текстовый pytest assert присутствия строки полезен, но не заменяет требуемую
причинную проверку эффективного наследования. Конфигурация кандидата сейчас
имеет правильный guard; найден пробел доказательства, не установленная утечка
на рабочем сервере.

Исправление: родительскому HTTP задать собственный захватываемый временный
error-log с уровнем, позволяющим увидеть ERR broken-header; candidate server
`/dev/null` оставить без подстановки. Отрицательным контролем отдельно убрать
защиту dedicated и strip в изолированном варианте и доказать, что marker-test
падает для каждого, затем проверить нормальный кандидат PASS. Все журналы
содержат только учебные данные и удаляются штатно; маркер/envelope/адрес не
экспортируются в evidence. При необходимости вывести отдельные booleans по
каждому receiver вместо одного объединённого утверждения.

## Подтверждённое в конфигурации и helper

- Routing содержит только точный rec→10446 и default→один relay10447.
  Relay имеет точные IPv4/IPv6 PP listeners, ssl_preread on,
  proxy_protocol off, access_log off и отдельный error_log /dev/null.
  Прежний `$kvn_443_backend` используется без дублирования его пяти SNI.
- Dedicated rec имеет обе IP-семьи10446, PP, прежние400/421 guards,
  отдельный server error-log /dev/null. Обе реальные proxy locations
  заменяют XFF/X-Real-IP из envelope и XFP=https; realip не добавлен.
  Прежнего rec10444 в итоговом шаблоне нет. HTTP80/8443 по контекстному
  сравнению не менялись, но этот helper не выполняет реальную8443 приёмку.
- Helper читает шаблоны из переданного repo, строит собственный временный
  nginx с учебными сертификатами/портами/тремя TLS backend. CERT_NONE
  используется только против своего временного сертификата.
- public→dedicated/strip, обе IP-семьи, поддельные HTTP заголовки,
  UNKNOWN/dedicated400, strip UNKNOWN, пять mail SNI, noSNI/default,
  несовпадающий Host421 имеют фактические успешные чеки receipt.
- Стадии baseline/prepare/switch/final и возврат удерживают четыре поздних
  соединения: rec/default/special/mail. Проверяется ответ старого маршрута
  после reload, затем завершение прежних workers. Исправление capture не
  скрывает первый FAIL: ошибка retained в отдельном receipt. В текущем
  helper старый ответ вычисляется по current_stage, не по новому raw capture.
- Raw capture слушает отдельно три прежних пути и сравнивает ClientHello
  побайтово для public/coalesced/fragmentedTLS/UNKNOWN. Полный PP prefix
  или потеря начала TLS не пройдут равенство. Неполный/лишний payload
  сверх длины ClientHello этим сравнением не исследуется, полная семантика
  долгого потока/WebSocket остаётся отдельной рабочей матрицей.
- Процесс запускается с новой собственной session/process-group; cleanup
  учитывает оставшихся работников, TERM-resistant собственный probe,
  затем допускает SIGKILL только своей изолированной группе. Это не
  разрешение kill рабочим/соседним соединениям. Cleanup в receipt успешен.

## Наблюдаемые ресурсы и задержки

Выполненный full receipt относится к одинаковому изолированному узлу/двум
worker по768 connections и soft FD1024,31 отсчёт,120 held TLS соединений
(40 на направление),600 новых TLS/HTTP за окна75.0002/75.0005с.

| Маршрут | Baseline p95, мс | Candidate p95, мс | Прирост, мс |
| --- | ---: | ---: | ---: |
| default | 6.343 | 7.076 | 0.733 |
| special fixture | 6.153 | 7.383 | 1.230 |
| mail fixture | 5.928 | 7.590 | 1.662 |

Максимум candidate FD325/1024≈31.74%, socketFD317/768≈41.28%, ниже70%.
Helper использует монотонное время от connect до первого байта и nearest-rank
p95 по200 запросов каждого маршрута. Это подтверждает выполненный нагрузочный
профиль принятого кандидата, а не исходный запас/производительность общего
рабочего nginx, не полный T097 и не настоящий протокол special/mail.

## Оставшиеся независимые рабочие ограничения

Сам helper честно возвращает `production_config_read=false`,
`production_mutation=false`, `raw_addresses_exported=false`,
`special is HTTPS fixture; not T098 acceptance`.

Он не проверяет реальные VLESS/REALITY и Stalwart; не снимает исходные отказы
443/10445; не доказывает рабочее происхождение посетителя/оператора через
два внешних выхода, актуальный Docker trust и прямые соседние пути. Нужны
все сохранённые scenario8 ворота: реальные семейства/сети/поколения,
совместимость timeout/upload/WebSocket/half-close,8443, логи, writer→DB→reader,
закрытая копия/lock/текущие хеши, конкретный поэтапный операторский путь.

При активном истёкшем исключении merge/release остаются HOLD. Указанное
правилами execute retirement task не создаёт выпускного обхода. Данный кодовый
срез не разрешает изменять работающий443, ставить runtime Legacy Impact remove,
включать IP/provider/writer/T0 или закрывать T098 по зелёному изолированному JSON.

## Повторное ревью двух P2 — текущий helper7212

Самостоятельно прочитаны изменённые config/reload/control/fragmentedPP/log
секции helper и целиком protocol-third receipt. Хеш helper совпал с обоими
input_sha256 receipt:
`7212ae2ec66d4da9039b814b10f551966cf7a469924bcaa90a53b7bcee60ff36`.
Routing/rec/test сохранили три хеша первого прохода.

- **P2-C1 снят.** На dedicated и strip добавлена отдельная передача первой
  части корректного PP, задержка30мс, попытка передачи второй части и
  наблюдение close/reset; это уже не один truncated write. Возвращаются
  отдельные dedicated/strip_fragmented_pp_transport_close. Поддержка
  произвольной PP-фрагментации не обещается; HTTP400 транспортному отказу
  не приписывается. Проба содержит EOF после попытки второй части, поэтому
  из её результата не выводится отдельный момент закрытия до EOF.
- **P2-C2 снят.** HTTP parent теперь пишет в захватываемый временный
  http-inherited-error.log info, stream parent — inherited-error.log info.
  config(log_control=dedicated/strip) снимает защиту соответствующего
  приёмника, обычный кандидат её сохраняет. Две отдельные control стадии
  посылают control-marker и требуют его фактическое наличие в своём
  error-log; это негативный контроль, а не молчание отключённого parent.
  Основной normal-marker отличается от control-marker и после возврата
  защиты должен отсутствовать во всех временных*.log. Control dedicated
  и strip проверяют разные sinks, поэтому отметка второго не наследует
  совпадение первого. Переключения также проверяют lateHello и дренирование.

Лично прочитанный `.dev/growth/t098-three-route-protocol-third-20261103.json`:
exit0,88 checks/88true, all_pass=true,19.334378с, оба negative_control=true,
оба fragmented_pp_transport_close=true, normal malformed marker не записан;
process-group cleanup и temporary_directory_removed=true. Внешний wrapper
подтверждает local_code_unchanged/remote_test_directory_removed=true.
Это protocol-only: resource_probe=skipped, measurements пуст.

Новых P1/P2 по этой дельте не найдено. Полный повтор current helper выполняет
основной исполнитель; на момент этого дополнения full-second JSON ещё не
был сохранён. Старые p95/FD/600запросов относятся к helpere857 и не выдаются
за свежий полный PASS7212. Требуется отдельная сверка завершённого current
full receipt с тем же хешем, код/сервер reviewer не запускал и не менял.
Все рабочие/legacy/release ограничения первого прохода сохраняются.

## Завершённый full-second — окончательный итог18:18UTC

Лично прочитан `.dev/growth/t098-three-route-full-second-20261103.json` целиком.
Exit0,91 checks/91true, all_pass=true,233.241657с, resource_probe=isolated_only.
Оба отрицательных log-control и оба fragmentedPP checks успешны вместе с
основными marker/wire/lateHello/rollback/drain/IPv4/IPv6 проверками.

Три input_sha256 в result и wrapper совпали с текущими helper/routing/rec;
helper7212, routing4480, rec700c. Повторно сверено отсутствие изменений трёх
файлов. Compose-hardening test7090 также остался прежним; его33pytest PASS
по-прежнему — сообщение исполнителя, не отдельный заново выполненный reviewer
прогон. Wrapper подтверждает local_code_unchanged=true и удалённый временный
каталог; inner process-group cleanup и temporary_directory_removed=true.
SHA256 прочитанного full-second receipt:
`32a02204658feb526cdb1ed14f49bd8c65819f046f5513fc1113b4e4ff7272f3`.

| Маршрут | Новый baseline p95, мс | Новый candidate p95, мс | Прирост, мс |
| --- | ---: | ---: | ---: |
| default | 6.157 | 7.228 | 1.071 |
| special fixture | 6.335 | 7.175 | 0.840 |
| mail fixture | 6.363 | 7.652 | 1.289 |

В обоих профилях120 held TLS,31 отсчёт,600 запросов/по200 на направление,
окна75.00047/75.00032с. Candidate максимум FD322/1024≈31.45%,
socketFD313/768≈40.76%, оба ниже70%; дельта p95 каждого ниже10мс.
Старые измерения выше относятся только к историческому helpere857; текущие
числа принимаются из нового receipt на7212 и не переносятся между версиями.

**Окончательный итог: SCOPED CODE/ISOLATED VALIDATION PASS, P1=0/P2=0.**
Изменён только этот отчёт; новые проверки reviewer на сервере не запускались.
Приняты исправления кода и полный изолированный профиль по прочитанным
доказательствам. Существующий accepted requirements checklist10/0 не менялся.

Нужные настоящие baseline/клиенты VLESS/REALITY и Stalwart, рабочий переход
и завершение поколений, exact-peer/реальные сети, полная scenario8, T098,
истёкшее исключение и merge/release по-прежнему HOLD. Этот PASS не разрешает
снять runtime legacy на бумаге, менять рабочий443, включать IP/provider/T0
или объявлять достигнутыми органический трафик/продажи. T113 не переоткрыт.
