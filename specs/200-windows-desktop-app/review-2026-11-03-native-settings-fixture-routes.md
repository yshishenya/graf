# Независимое ревью F200: маршруты HTTPS-фикстуры настроек

Дата: 2026-11-03. Ветка `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Проверяется рабочий снимок с параллельными изменениями, а не только HEAD.
Рецензент изменяет только этот отчёт. Код, spec/plan/tasks, контрольные
списки, Git и внешние системы не изменяются.

## Текущий допуск

**Фактический test-only патч: APPROVED, C0/H0.** Свежая Release x64 сборка и
отрицательный WebView2 TLS-контроль приняты по сохранённым свидетельствам,
сверенным в финальном дополнении. Ожидание source review снято.
Одно неблокирующее замечание P2 относится к timeout cleanup самостоятельного
теста. Положительная полная цепочка и установленное приложение не приняты.

**Требования к узкому test-only исправлению: C0/H0, PASS.** Можно готовить
минимальные ресурсы `/desktop/settings/account`, перенаправление
`/desktop/settings`, HTML MIME и категоризированную пассивную диагностику.
Это существующий проверочный срез T104 с последующей приёмкой T097/T109;
новая продуктовая задача или изменение контракта не нужны.
Полоса — независимое ревью активного `high-risk-product` F200.

**Исходное состояние до ревью исправления:** в прочитанном
исходном состоянии Python знает HTML только для notifications/meetings,
а response observer ограничен этими двумя документами. Результат проверки
подготовленного исправления приведён в дополнении ниже; исходный допуск
по требованиям сам по себе не принимал будущий код или Windows-запуск.

Перечитаны относящиеся к срезу требования spec, plan, tasks, quickstart,
constitution, product gates, правила независимого ревью и выпуска;
`validation-2026-10-27-native-settings-appmain.md` и предыдущий отчёт
`review-2026-10-27-t097-t109-native-settings-requirements.md`.
Проверка production-маршрутов повторно не выполнялась.

## Состояние контрольных списков

| Список | Подтверждено | Открыто |
| --- | ---: | ---: |
| requirements.md | 22 | 0 |
| security.md | 27 | 0 |
| ux.md | 25 | 0 |
| Итого относящихся к срезу списков | 74 | 0 |

Пункты прочитаны в их нормативном смысле: качество требований и границы
полномочий. Их отметки сохранены. Исторические PASS других срезов не
переносятся на новый код. Полная инвентаризация остальных списков и issues
не повторялась. T097, T104 и T109 в tasks.md остаются `[ ]`.

## Что действительно подтверждает предыдущее исполнение

Независимо прочитаны сохранённые trusted-result.json, trusted-ui.err,
https-postflight.json, resources.json и экспортированный meetings HTML.
Хеши совпали с последней записью validation. Все 22 ресурса соответствуют
manifest; экспортированный HTML содержит обе отсутствующие ссылки.
В manifest есть только два документа: meetings и settings/notifications.

Предыдущий запуск получил настоящий HTTPS GET/200/HTML с browser-owned
Dest/Mode/current tag, затем native read `present=1 quiet=1`. Возврат,
восстановление выбора и preview не прошли: app_exit=3,
https_slice_pass=false, full_chain_pass=false. Postflight сообщает
отсутствие собственных процессов/профилей, synthetic Registry value и
точного сертификата. Это чтение сохранённых квитанций, не самостоятельное
наблюдение Windows или повторное исполнение очистки.

Недостаток allowlist доказан; связь с конкретным прошлым web_error=0/14
остаётся неустановленной. server denied=0 не исключает отказ в C++ до сети.

## Условия ревью фактической правки

1. Настоящие HTML/assets общего кабинета с synthetic account data;
   никаких подставных connect/nonce/native replies или второй Windows UI.
   `/desktop/settings` конфликтует с каталогом notifications на диске:
   точное перенаправление задаётся отдельно от файлового ресурса.
   Цель перенаправления — только фиксированный локальный разрешённый путь,
   без URL из запроса. Данные перенаправления входят в проверяемый снимок.
2. C++ allowlist и Python согласованы: GET, точный localhost HTTPS origin/port,
   известные ресурсы и явные перенаправления. Нельзя разрешать весь префикс
   settings, произвольные файлы, внешнюю сеть или неподдерживаемые методы.
   Документ account получает HTML MIME; extensionless JSON остаётся JSON.
3. Пассивная диагностика различает известные категории документов,
   redirect, static и unknown/denied; показывает метод/статус/ошибку/признаки
   настоящих metadata. Не пишет URL, query, cookies, заголовки целиком,
   страницу, owner или пути профилей. Не создаёт navigation tag и не
   вызывает методы допуска документа.
4. Production AppMain, WebView2Host, route/history/response/TLS guards,
   nonce и обработчик настроек не меняются ради прохождения стенда.
   Генератор сохраняет 11 побайтово совпадающих методов; отдельный
   derivative ctor меняет только origin тестовой копии CabinetWindow.
5. Сохраняются GUID-профиль с проверкой до навигации, deny permissions,
   выключенный захват, exact synthetic Registry cleanup, отдельная
   ограниченная очистка собственных app/server и exact leaf trust.
   full_chain_pass остаётся false; https_slice_pass вычисляется после
   очистки и не переживает failure/drain/trust ошибки.
6. До принятия нового запуска нужны актуальные manifests/source bindings,
   ресурсы/redirects и точный PE hash. Проверка синтаксиса и локальный
   транспортный тест не подтверждают Windows compile/runtime.
   Нужны положительные account/redirect/notifications переходы и отрицательные
   unknown path/Host/method/plain HTTP/untrusted TLS без ослабления guards.
   Смена C++ adapter требует новой сборки, а не старого PE с новым отчётом.

## Непринятые условия полной приёмки

Ручной возврат через общую страницу с повторным native read и отображением
сохранённого выбора, восстановление исходного выбора, preview и клавиатура,
обычный холодный перезапуск процесса и stale-document negative остаются
отдельными проверками quickstart:152–174. Изолированный derivative PE не
является установленным MSIX. Mac parity, доступность, аппаратный x64,
capture/storage и точный CI/release результат не принимаются этим срезом.

## Привязка прочитанного состояния

- spec.md: `69e8b6cadae116cb8b59684738583e64d953c4243e9020653390dc9695befe9f`
- plan.md: `1afadff31435700bcbb599ee9293c0b2a350d59a1e78869d827cd2067ae087b6`
- tasks.md: `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`
- quickstart.md: `8b64709535ccc81a5d2d3fbd869ca02fbe206323ef1b66ba44e7c04ec11c5891`
- trusted-result.json: `624c9fa48809f2191f92fccabf3b5bb501f4d4cca2eaa77366bb321bd7025e03`
- trusted-ui.err: `6ba1d5c08389dd24eb5aa9b57a90125d0a012812b496a9d613db2ecf1c6b5165`
- https-postflight.json: `b36fe25cb24608937343b437b3f9a004ac2202b771703385fec55201291d6f8e`
- resources.json: `b75965b03f1aac37f56f428bf0dd07bc88d1c9558c0520d1872cc5ce2b8e97ac`

На исходном состоянии node --check генератора и ast.parse Python прошли.
Сборка, Windows/UI, изменение trust, capture, сеть и GitHub не запускались.

## Дополнение: проверка готового исправления, 2026-11-03

Файлы прочитаны напрямую, включая untracked Python/C++ adapters и новый
test_appmain_settings_loopback.py. Дельта первых трёх сопоставлена с
сохранённым source10. Plain git diff для них не использовался как доказательство
отсутствия изменений. **Узкий source gate: C0/H0; одно замечание P2 ниже.**
Runtime/installed/full-chain приёмка остаётся HOLD.

### Сохранность границ и корректность маршрутов

- Python разрешает ровно `desktop/settings` как 303 на фиксированный
  `/desktop/settings/account`, только если account включён в проверенный
  manifest. Существующая проверка Host/origin-form/GET и запрет `..`
  сохранены; каталог settings не пытаются прочитать как файл.
  Account/notifications/meetings имеют HTML MIME; extensionless API — JSON.
- C++ требует наличие всех трёх настоящих страниц. Под тем же точным
  HTTPS origin/port разрешён только GET известного ресурса или точного
  `/desktop/settings`; произвольный префикс settings не разрешается.
  Путь query отделяется до проверки списка; redirect остаётся реальным
  сетевым ответом. Synthetic success response и metadata admission не добавлены.
- Категории navigation/document ограничены notifications/account/settings_root/
  meetings/other, добавлены redirect flag, числовой web_error и стадия отказа
  host. failureDetail формируется из фиксированной стадии и числового кода;
  пользовательский URL/исключение туда не подставляются. Диагностика пассивна.
  Это диагностика документов, не полное журналирование каждого static resource.
  URL с query у pageName попадает в other, а response observer его пропускает:
  транспортный допуск query не является доказательством полноты наблюдателя.
- WebView2Host.cpp/.h, WebViewRoutePolicy.cpp/.h, генератор и HTTPS runner
  побайтово совпадают с сохранёнными source10. Рабочий CabinetWindow.h имеет
  обычный default ctor; origin меняется только в производной тестовой копии.
  Производный AppMain реконструирован в памяти; 11 секций совпадают побайтово
  с текущим AppMain. Параллельная ранее описанная startup/Quit правка AppMain
  не приписывается этому исправлению и не переоценивается здесь.
- Cleanup, запрет capture/permissions, profile-before-navigation и exact
  synthetic Registry ownership в дельте не изменены. Условия terminal/native
  success прежние; runner сохраняет full_chain_pass=false и вычисляет
  https_slice_pass только после обязательной очистки без ошибок.

### Проверки рецензента

Прямой запуск `python3 -B apps/windows/Tests/GrafWindowsContractTests/test_appmain_settings_loopback.py`
прошёл. Реальный TLS с временным явным cafile, account/notifications/meetings,
303 Location и пустое тело, HTML/JSON MIME, query, неизвестный путь, traversal,
неверный Host и отказ при content drift проверены исполняемым тестом.
Системное доверие сертификатам не менялось; временные файлы теста очищены.

Дополнительный запуск того же теста с проверками, добавленными только в памяти,
подтвердил HTTP 501 для POST и SSLCertVerificationError при обычном default
TLS context без доверия к leaf. Исходник на диске рецензент не редактировал.
`node --check` генератора и независимое сравнение 11 AppMain секций прошли.

### P2: очистка subprocess при тайм-ауте теста

В новом test_appmain_settings_loopback.py, finally вокруг
`server.communicate(timeout=8)`, TimeoutExpired выходит из cleanup без kill/wait.
При зависании остановки собственный Python/TLS процесс может остаться живым
до серверного срока 660 секунд. TemporaryDirectory не завершает процесс.
Положительный сценарий прошёл, но отказ теста не должен оставлять свой сервер.
Минимальная правка: при TimeoutExpired завершить именно server, выполнить
повторный communicate/wait и сохранить исходный отказ теста. Это замечание
к надёжности нового теста, не обнаруженная регрессия product guards.

### Привязка проверенных байтов и оставшиеся условия

- AppMainSettingsLoopback.py: `6d1b623c34ba6d7f3b2a19e160d9d1bcab350eaed665a35858598b6513ef6598`
- AppMainSettingsUiFixture.h: `c70edfef7cbd487ade077ce70e791e6136b4bba66be0b740315c48d759bd3b72`
- AppMainSettingsUiLaunch.inc: `2198f2394586d1102377212e200cbfb4573a9cb56d478bbf2fe09e88224b754f`
- test_appmain_settings_loopback.py на последнем чтении: `7fca652fcba92ff0e50eb20dcfea92909c4ca4219a7f12736b2a40448f058ae3`
- Текущий AppMain.cpp: `a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0`
- prepare-appmain-problem-ui.mjs: `4939aa1f66f9333217284d4052cf5d7214d8e3fa2d14f94ac5e556a3cea7e818`
- RunAppMainSettingsHttps.ps1: `15823166fee6e4fecabcee5e1ad7406aa579d7a393d29d74d6bf12300dcdc39d`

Главный агент сообщил подготовку свежей нативной сборки 221 исходника и 23
ресурсов. Квитанции новой сборки, точный PE и manifests этого запуска пока
не рассмотрены. Сообщение не заменяет их проверку и не даёт Windows PASS.
Native compile/runtime, actual CUA display/read/return/restore/preview,
cold restart/stale negative и установленный MSIX остаются отдельными.
Requirements/security/ux по-прежнему 74 checked / 0 unchecked; отметки и
T097/T104/T109 не изменены. Изменён только этот отчёт рецензента.

## Финальное решение: source221, resources23, Release x64 и TLS negative

**SCOPED PATCH APPROVED — C0/H0.** Фактический патч прочитан и принят;
формулировка WAIT к нему больше не применяется. P2 об остановке subprocess
самостоятельного Python-теста остаётся неблокирующим замечанием: она не
затрагивает продукт, HTTPS runner или результаты успешных выполненных тестов.
Положительная UI/full-chain и installed приёмка по-прежнему HOLD.

Проверен новый локальный stage `settings-return-20261103.qcbz2uck` рядом с
предыдущими сохранёнными свидетельствами. Рецензент не запускал Windows,
не пересобирал PE, не менял trust или установленный пакет.

### Целостность снимка и привязка сборки

- Все 221 сохранённый файл `source/` совпали с test-source.json.
  Сравнение source.json с текущей рабочей копией дало ровно одно отличие:
  test_appmain_settings_loopback.py. В нём после заморозки добавлены
  самостоятельные POST/plain-HTTP отрицательные проверки. Этот файл не
  входит в компиляцию C++; adapters и продуктовые входы совпали.
- Все 23 ресурса совпали с resources.json; три документа — meetings,
  settings/notifications и settings/account. Все 112 входов shared-source.json
  совпали с текущими общими исходниками. Перенаправление задано прочитанным
  Python-кодом, чей хеш отдельно привязан в untrusted runner.
- Полный производный AppMain повторно получен в памяти теми же преобразованиями
  текущего генератора и побайтово совпал с сохранённым derivative:
  `874baed6b2c7ce04b8476bec44e757fb1dc8c2da0939201b0ea63442da38bd47`.
  Все 11 методов одновременно совпали с текущим production AppMain и hashes
  unchanged_methods в bindings. Origin ctor остаётся только в тестовой копии.
- build-result.json: terminal=true, build_exit=0, source_files=221,
  post_source_files=221, installed/launched/audio_started=false.
  Build.ps1 задаёт Release/x64, проверяет все входы до/после сборки и свежую
  дату AppMain.obj. PE SHA-256:
  `f14dc3a77b4e7ef2556d0f7e3f667f6158172ddbdcac93c17fc3aae14a8afaed`.
  AppMain.obj: `3506370c3387f67190fb07ea0da56b245b42524ea8a7e7d2bbf48f1caaaabedb`.
  WebView2Host.obj прежний:
  `03a6e8adadb1624d7cbeb91fa7972b350f22e9bec68b8e9d7c381f5682011d05`.
  Физический guest PE отдельно рецензентом не хешировался; принят сохранённый
  build receipt и pin того же PE в прочитанном Https-untrusted.ps1.

### Новый отрицательный Windows-контроль

untrusted-ui.err подтверждает profile_verified=1 starts_before_check=0,
native_read present=0 quiet=0, navigation/document=notifications и затем
tls_rejected=1 web_error=5. `document allowed=1` означает только допуск
запроса к настоящему HTTPS; принятым HTML-документом это не является.
Response GET/200/HTML и native_read present=1 отсутствуют; server-counts
served=0/denied=0 согласуется с отказом до HTTP. host_failure=document с
числовым кодом сохраняет отказ, а не обходит его.

Terminal: quiet/restored/preview/settings_loads/meetings_loads=0,
browser_stopped=1 registry_cleaned=1 profile_cleaned=1 exit=3.
untrusted-result.json: terminal=true, untrusted_refused=true,
cleanup_reported/app_stopped/server_stopped/trust_restored=true;
нет failure/app_drain_failure/server_drain_failure/trust_failure.
native_scenario_pass=https_slice_pass=full_chain_pass=false,
installed=audio_started=false. Certificate pin в скрипте соответствует
сохранённому cert.cer. Это negative без импорта trust: trust_restored означает
совпадение snapshot, а не доказанное удаление после positive.

**Принято как сохранённое свидетельство настоящего Windows WebView2 TLS
negative для новой сборки.** Признаков допуска HTML или native mutation в
прочитанном журнале нет; отдельного трассирования всех операций Registry и
самостоятельного наблюдения очистки на VM рецензент не выполнял.

### Регрессионная проверка исправления

Прямой текущий test_appmain_settings_loopback.py повторно PASS, теперь включая
POST=501 и отказ plain HTTP. Запуск того же текущего теста со старым source10
loopback, выбранным только в памяти, дал ожидаемый RED на первом
`/desktop/settings`: HTTP403 вместо 303. Так проверка действительно различает
старую неполную фикстуру и исправленный код. Старый код не заменялся на диске.
Ранее отдельно полученный default-context TLS negative также сохранён в выводе
рецензента; системное доверие не менялось. Исторический конкретный web_error14
не объявляется объяснённым без нового положительного сценария возврата.

### Хеши новых свидетельств

- build-result.json: `0f470bbabc6fda8420cef1d8176c6e5c31987f2931e811677c1ce76815a07937`
- source.json: `dd0cf3c6f192f8ca3307599456418877dfbcb738cdce92d92aa5f246df62de51`
- test-source.json: `d74fec3d11b361319173a2b30c58acf9bf82d0a7a9084894c957f610bed120b3`
- resources.json: `aa839a28a717f46dd90ab8f2d08c6bb60feb240da544afd927ebbd4f109f98b4`
- appmain-test-bindings.json: `dd49a7151849dada242b2b4789bc6d5cb13cfa0c972f9e5157a372598dccf38c`
- untrusted-result.json: `46c60e02f0eec02dac2f8b493480ee7f6dbf0ff27c5dae18d141dea3f148861c`
- untrusted-ui.err: `3a61098f2bfa01e9f6c0b4f240e8d8e002728c3f1fe8e81afb378864ee05416c`
- untrusted-server.err: `dce39212446ee16f9227baf5989f85a0c44f39c6397658014321beb5ffb8ffee`

Контрольные списки сохраняют 74 checked / 0 unchecked; новых отметок нет.
T097/T104/T109 остаются открытыми. Положительный return/read/display/restore/
preview, cold restart, stale negative, Mac, installed MSIX и release/hardware
не принимаются результатами source review, сборки или negative TLS.
Изменён только этот reviewer-owned отчёт; широкий аудит и production route
inspection повторно не выполнялись.
